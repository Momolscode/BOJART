"""Versioned local documents, immutable bytes, FTS5 and verified snapshots."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

PROJECTS = {'bojart.jarvis', 'bojart.creative', 'bojart.sites'}
TEXT_EXT = {'.txt', '.md', '.json', '.jsonl', '.csv', '.tsv', '.vtt', '.srt'}
IGNORED_PARTS = {'.git', '.env', 'node_modules', '.venv', '__pycache__', '.ssh', '.aws', '.config'}
MAX_BYTES = 32 * 1024 * 1024
MAX_FILES = 10000
SCHEMA_VERSION = 1


class MemoryError(ValueError):
    """Input or integrity failure; no automatic retry of external effects."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def chunks(text, max_chars=2800):
    """Line-addressable chunks; huge single lines are split with shared line numbers."""
    buf, size, start = [], 0, 1
    for line_no, line in enumerate(text.splitlines(), 1):
        if buf and size + len(line) + 1 > max_chars:
            yield start, line_no - 1, '\n'.join(buf)
            buf, size = [], 0
        if not buf:
            start = line_no
        if len(line) > max_chars:
            for pos in range(0, len(line), max_chars):
                yield line_no, line_no, line[pos:pos + max_chars]
        else:
            buf.append(line)
            size += len(line) + 1
    if buf:
        yield start, len(text.splitlines()), '\n'.join(buf)


def project_ok(project):
    if project not in PROJECTS:
        raise MemoryError('Projet obligatoire : bojart.jarvis, bojart.creative ou bojart.sites.')


def safe_relative(value):
    p = PurePosixPath(value)
    if not value or p.is_absolute() or '..' in p.parts or '\\' in value:
        raise MemoryError('Chemin relatif invalide.')
    return p


class Memory:
    def __init__(self, state, *, readonly=False):
        self.state = Path(state).expanduser().resolve()
        self.readonly = readonly
        db = self.state / 'memory.sqlite'
        if readonly:
            if not db.is_file():
                raise MemoryError('Mémoire non initialisée.')
            self.db = sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, timeout=10)
            self.db.execute('PRAGMA query_only=ON')
        else:
            self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
            (self.state / 'objects').mkdir(exist_ok=True, mode=0o700)
            self.db = sqlite3.connect(db, timeout=10)
            self.db.execute('PRAGMA journal_mode=WAL')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=10000')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, SCHEMA_VERSION) or (readonly and version != SCHEMA_VERSION):
            self.close()
            raise MemoryError('Schéma inconnu : migration explicite requise.')
        if not readonly:
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS assets(
                    sha256 TEXT PRIMARY KEY, bytes INTEGER NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sources(
                    source_id TEXT PRIMARY KEY, project TEXT NOT NULL, collection TEXT NOT NULL,
                    source_path TEXT NOT NULL, current_version TEXT);
                CREATE TABLE IF NOT EXISTS versions(
                    version_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
                    sha256 TEXT NOT NULL REFERENCES assets(sha256), observed_at TEXT NOT NULL,
                    provenance TEXT NOT NULL, kind TEXT NOT NULL, extraction TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chunks(
                    id INTEGER PRIMARY KEY, version_id TEXT NOT NULL REFERENCES versions(version_id),
                    start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, text TEXT NOT NULL);
                CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(
                    text, tokenize='unicode61 remove_diacritics 2');
                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY, event_type TEXT NOT NULL, source_id TEXT NOT NULL,
                    version_id TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS chunks_version ON chunks(version_id);
                CREATE INDEX IF NOT EXISTS versions_source ON versions(source_id);
                PRAGMA user_version=1;
            ''')
            self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _object(self, sha):
        if not re.fullmatch('[0-9a-f]{64}', sha):
            raise MemoryError('Empreinte invalide.')
        return self.state / 'objects' / sha

    def ingest_file(self, path, *, root, project, collection, provenance, kind='session_export'):
        project_ok(project)
        if self.readonly:
            raise MemoryError('Mémoire ouverte en lecture seule.')
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}', collection):
            raise MemoryError('Collection invalide.')
        if kind not in {'session_export', 'project_document', 'reference'}:
            raise MemoryError('Nature de source invalide.')
        if not isinstance(provenance, str) or not provenance.strip() or len(provenance) > 2000:
            raise MemoryError('Provenance explicite requise.')
        # A root grants access only to its real files, never symlink targets.
        raw_path = Path(path).expanduser().absolute()
        raw_root = Path(root).expanduser().absolute()
        if raw_root.is_symlink() or raw_path.is_symlink():
            raise MemoryError('Lien symbolique refusé.')
        root = raw_root.resolve()
        path = raw_path.resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise MemoryError('Source en dehors du dossier autorisé ou absente.')
        rel = path.relative_to(root)
        cursor = raw_path
        while cursor != raw_root and cursor != cursor.parent:
            if cursor.is_symlink():
                raise MemoryError('Lien symbolique refusé.')
            cursor = cursor.parent
        if any(part in IGNORED_PARTS or part.startswith('.env') for part in rel.parts):
            raise MemoryError('Fichier de configuration privé exclu.')
        if path.suffix.lower() not in TEXT_EXT:
            raise MemoryError('Import textuel uniquement ; médias conservés dans le catalogue externe.')
        if path.stat().st_size > MAX_BYTES:
            raise MemoryError('Source au-delà de la limite de 32 Mio.')
        data = path.read_bytes()
        if len(data) > MAX_BYTES:
            raise MemoryError('Source devenue trop grande.')
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError as e:
            raise MemoryError('UTF-8 requis ; source non importée.') from e
        if '\x00' in text:
            raise MemoryError('Données binaires refusées.')
        sha = digest(data)
        source_id = digest(canonical([project, collection, rel.as_posix()]).encode())
        version_id = digest(canonical([source_id, sha]).encode())
        obj = self._object(sha)
        if obj.exists():
            if obj.is_symlink() or file_sha(obj) != sha:
                raise MemoryError('Objet existant altéré.')
        else:
            fd, tmp = tempfile.mkstemp(prefix='import-', dir=self.state)
            try:
                with os.fdopen(fd, 'wb') as out:
                    out.write(data)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(tmp, obj)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            previous = self.db.execute('SELECT current_version FROM sources WHERE source_id=?', (source_id,)).fetchone()
            if previous and previous[0] == version_id:
                return {'status':'unchanged', 'source_id':source_id, 'version_id':version_id, 'sha256':sha}
            self.db.execute('INSERT OR IGNORE INTO assets VALUES(?,?,?)', (sha, len(data), now()))
            self.db.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?,NULL)', (source_id, project, collection, rel.as_posix()))
            exists = self.db.execute('SELECT 1 FROM versions WHERE version_id=?', (version_id,)).fetchone()
            if not exists:
                self.db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?)', (version_id, source_id, sha, now(), provenance, kind, 'utf8_lines_v1'))
                for first, last, chunk in chunks(text):
                    row = self.db.execute('INSERT INTO chunks(version_id,start_line,end_line,text) VALUES(?,?,?,?)', (version_id, first, last, chunk))
                    self.db.execute('INSERT INTO search(rowid,text) VALUES(?,?)', (row.lastrowid, chunk))
            self.db.execute('UPDATE sources SET current_version=? WHERE source_id=?', (version_id, source_id))
            self.db.execute('INSERT INTO events(event_type,source_id,version_id,created_at) VALUES(?,?,?,?)', ('source_version_selected', source_id, version_id, now()))
        return {'status':'version_selected', 'source_id':source_id, 'version_id':version_id, 'sha256':sha, 'previous_version':previous[0] if previous else None}

    def search(self, query, *, project, limit=6, history=False):
        project_ok(project)
        if not isinstance(query, str) or len(query) > 2000 or not 1 <= limit <= 30:
            raise MemoryError('Recherche hors limites.')
        terms = re.findall(r'[^\W_]+', query, re.UNICODE)[:32]
        if not terms:
            return {'project':project, 'results':[], 'trusted_instructions':False}
        match = ' OR '.join('"'+word+'"' for word in terms)
        current = '' if history else 'AND s.current_version=v.version_id'
        rows = self.db.execute(f'''
            SELECT s.project,s.collection,s.source_path,v.version_id,v.sha256,v.observed_at,
                   v.provenance,v.kind,c.start_line,c.end_line,c.text,
                   s.current_version=v.version_id AS current_version, bm25(search) AS rank
            FROM search JOIN chunks c ON c.id=search.rowid
            JOIN versions v ON v.version_id=c.version_id
            JOIN sources s ON s.source_id=v.source_id
            WHERE search MATCH ? AND s.project=? {current}
            ORDER BY CASE WHEN s.collection='canonical' THEN 0 ELSE 1 END,
                     rank,v.observed_at DESC,c.start_line LIMIT ?
        ''', (match, project, limit)).fetchall()
        verified, results, warnings = {}, [], []
        for row in rows:
            sha = row['sha256']
            if sha not in verified:
                obj = self._object(sha)
                verified[sha] = obj.is_file() and not obj.is_symlink() and file_sha(obj) == sha
                if not verified[sha]:warnings.append({'sha256':sha,'reason':'source_missing_or_changed'})
            if verified[sha]:results.append({**dict(row),'source_bytes_verified':True})
        return {'project':project, 'query':query, 'retrieval':'sqlite_fts5_bm25', 'trusted_instructions':False,
                'facts_automatically_validated':False, 'results':results, 'warnings':warnings}

    def stats(self):
        result={name:self.db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] for name in ('assets','sources','versions','chunks','events')}
        result['projects']=[dict(r) for r in self.db.execute('SELECT project,COUNT(*) AS sources FROM sources GROUP BY project')]
        return result

    def reconcile_collection(self, *, project, collection, source_paths):
        """Retire removed canonical documents without deleting their versions or objects."""
        project_ok(project)
        if self.readonly:raise MemoryError('Mémoire en lecture seule.')
        keep={safe_relative(p).as_posix() for p in source_paths}
        retired=[]
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            rows=self.db.execute('SELECT source_id,source_path,current_version FROM sources WHERE project=? AND collection=? AND current_version IS NOT NULL',(project,collection)).fetchall()
            for row in rows:
                if row['source_path'] in keep:continue
                self.db.execute('UPDATE sources SET current_version=NULL WHERE source_id=?',(row['source_id'],))
                self.db.execute('INSERT INTO events(event_type,source_id,version_id,created_at) VALUES(?,?,?,?)',('source_retired',row['source_id'],row['current_version'],now()))
                retired.append(row['source_path'])
        return retired

    def verify(self):
        issues=[]
        if self.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            issues.append('sqlite_integrity')
        if self.db.execute('PRAGMA foreign_key_check').fetchall():
            issues.append('foreign_keys')
        for row in self.db.execute('SELECT sha256,bytes FROM assets'):
            p=self._object(row['sha256'])
            if not p.is_file() or p.is_symlink() or p.stat().st_size!=row['bytes'] or file_sha(p)!=row['sha256']:
                issues.append('object:'+row['sha256'])
        return {'ok':not issues,'issues':issues,**self.stats()}

    def backup(self, destination):
        destination=Path(destination).expanduser().absolute()
        if destination.exists() or destination.is_symlink() or destination.resolve().is_relative_to(self.state):
            raise MemoryError('La sauvegarde exige un nouveau dossier hors de la mémoire.')
        destination.parent.mkdir(parents=True,exist_ok=True)
        temp=Path(tempfile.mkdtemp(prefix='bojart-backup-',dir=destination.parent))
        try:
            with closing(sqlite3.connect(temp/'memory.sqlite')) as target:
                self.db.backup(target)
                target.execute('PRAGMA journal_mode=DELETE')
                hashes=[r[0] for r in target.execute('SELECT sha256 FROM assets')]
                target.commit()
            (temp/'objects').mkdir()
            for sha in hashes:
                p=self._object(sha)
                if not p.is_file() or p.is_symlink() or file_sha(p)!=sha:
                    raise MemoryError('Sauvegarde interrompue : objet altéré.')
                shutil.copy2(p,temp/'objects'/sha)
            files=[p for p in temp.rglob('*') if p.is_file()]
            manifest={'schema_version':1,'created_at':now(),'files':[{'path':p.relative_to(temp).as_posix(),'sha256':file_sha(p),'bytes':p.stat().st_size} for p in sorted(files)]}
            (temp/'snapshot.json').write_text(canonical(manifest)+'\n',encoding='utf-8')
            temp.rename(destination)
        finally:
            if temp.exists():shutil.rmtree(temp)
        return {'snapshot':str(destination),'files':len(files)}

    @staticmethod
    def restore(snapshot, destination):
        snapshot=Path(snapshot).expanduser().resolve()
        destination=Path(destination).expanduser().absolute()
        if destination.exists() or destination.is_symlink():
            raise MemoryError('Restauration uniquement dans un nouveau dossier.')
        manifest=json.loads((snapshot/'snapshot.json').read_text(encoding='utf-8'))
        if manifest.get('schema_version')!=1 or not isinstance(manifest.get('files'),list):
            raise MemoryError('Manifeste invalide.')
        seen=set()
        for item in manifest['files']:
            rel=safe_relative(item['path']);p=snapshot/rel
            if str(rel) in seen or not (str(rel)=='memory.sqlite' or (rel.parts[0]=='objects' and len(rel.parts)==2 and re.fullmatch('[0-9a-f]{64}',rel.name))):
                raise MemoryError('Chemin inattendu dans la sauvegarde.')
            seen.add(str(rel))
            if p.is_symlink() or not p.resolve().is_relative_to(snapshot) or not p.is_file() or p.stat().st_size!=item['bytes'] or file_sha(p)!=item['sha256']:
                raise MemoryError('Sauvegarde altérée.')
        if 'memory.sqlite' not in seen:
            raise MemoryError('Base absente de la sauvegarde.')
        destination.parent.mkdir(parents=True,exist_ok=True)
        temp=Path(tempfile.mkdtemp(prefix='bojart-restore-',dir=destination.parent))
        try:
            for item in manifest['files']:
                rel=safe_relative(item['path']);p=temp/rel;p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(snapshot/rel,p)
            with Memory(temp,readonly=True) as restored:
                result=restored.verify()
            if not result['ok']:
                raise MemoryError('La mémoire restaurée échoue au contrôle.')
            temp.rename(destination)
        finally:
            if temp.exists():shutil.rmtree(temp)
        return {'restored':str(destination),**result}
