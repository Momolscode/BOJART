"""Collecte guidée des contenus BOJ.ART sur la tour : vidéos, images, sons, documents, exports.

Les dossiers sources sont désignés une fois et mémorisés. Chaque passage :

- parcourt ces dossiers sans suivre de lien ni de jonction, sans fichier caché ni secret (.env) ;
- reconnaît les fichiers déjà vus (même chemin, taille et date) sans les relire ;
- copie chaque nouveau contenu dans un magasin adressé par empreinte SHA-256, puis relit la copie
  pour la vérifier ; un contenu déjà présent n'est jamais recopié ni écrasé ; la copie passe en
  lecture seule ;
- importe les textes dans la mémoire de Jarvis comme documents non vérifiés, et la conversation
  d'un export ChatGPT (.zip) dans la collection « sessions » ;
- lit les métadonnées vidéo avec ffprobe quand il est présent.

Les sources ne sont jamais modifiées, déplacées ni supprimées. Rien n'est publié ni envoyé.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import zipfile

try:
    from bojart_memory.core import MemoryError as MemoryRefusal
except ImportError:  # memory package absent: text import is then reported per file
    class MemoryRefusal(Exception):
        pass

KINDS = {
    'video': {'.mp4', '.mov', '.m4v', '.mkv', '.webm', '.avi', '.mts', '.m2ts', '.3gp'},
    'image': {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp', '.tif', '.tiff', '.gif', '.dng'},
    'son': {'.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.opus'},
    'texte': {'.txt', '.md', '.json', '.jsonl', '.csv', '.tsv', '.vtt', '.srt'},
    'document': {'.pdf', '.docx', '.doc', '.pptx', '.xlsx', '.odt', '.rtf', '.psd', '.ai', '.svg',
                 '.blend', '.stl', '.step', '.stp', '.3mf', '.obj', '.glb'},
    'archive': {'.zip'},
}
SKIP_DIRS = {'$recycle.bin', 'system volume information', '.git', 'node_modules', '.venv', '__pycache__',
             '.ssh', '.aws', '.config', '.trash'}
SKIP_FILES = {'thumbs.db', 'desktop.ini', '.ds_store'}
MARGIN_BYTES = 5 * 10**9
CHUNK = 1 << 20
PROJECTS = ('bojart.creative', 'bojart.jarvis', 'bojart.sites')
CHATGPT_MEMBER = 'conversations.json'
MAX_TEXT_BYTES = 32 * 1024 * 1024


class SourceChanged(Exception):
    """The source file changed while it was being copied."""


class IntegrityError(Exception):
    """The copy read back differs from what was read."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def kind_of(path):
    suffix = Path(path).suffix.lower()
    return next((k for k, exts in KINDS.items() if suffix in exts), None)


def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()


def default_base(env=None):
    env = os.environ if env is None else env
    if env.get('BOJART_COLLECTE'):
        return Path(env['BOJART_COLLECTE']).expanduser()
    return Path(env.get('USERPROFILE') or env.get('HOME') or Path.home()) / 'BOJART' / 'collecte'


def default_memory(env=None):
    env = os.environ if env is None else env
    if env.get('BOJART_MEMORY_STATE'):
        return Path(env['BOJART_MEMORY_STATE']).expanduser()
    return Path(env.get('USERPROFILE') or env.get('HOME') or Path.home()) / 'BOJART' / 'memory'


def _is_link(path):
    return os.path.islink(path) or (hasattr(os.path, 'isjunction') and os.path.isjunction(path))


class Collecte:
    def __init__(self, base=None, memory_state=None):
        self.base = Path(base) if base else default_base()
        self.store = self.base / 'originaux'
        self.reports = self.base / 'rapports'
        self.memory_state = Path(memory_state) if memory_state else default_memory()
        for folder in (self.store, self.reports):
            folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.base / 'collecte.sqlite')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, chemin TEXT UNIQUE NOT NULL, nom TEXT NOT NULL,
                projet TEXT NOT NULL, ajoute_le TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS contenus(sha256 TEXT PRIMARY KEY, octets INTEGER NOT NULL, genre TEXT NOT NULL,
                chemin_stocke TEXT NOT NULL, metadonnees TEXT NOT NULL, premier_vu TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS emplacements(source_id TEXT NOT NULL REFERENCES sources(id), chemin_relatif TEXT NOT NULL,
                octets INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, sha256 TEXT NOT NULL, vu_le TEXT NOT NULL,
                PRIMARY KEY(source_id, chemin_relatif));''')
        self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # --- Sources désignées une fois ------------------------------------------------

    def add_source(self, folder, name=None, project='bojart.creative'):
        raw = Path(folder).expanduser().absolute()
        if _is_link(raw):
            raise ValueError('Lien ou jonction refusé : désigner le dossier réel.')
        path = raw.resolve()
        if not path.is_dir():
            raise ValueError(f'Dossier introuvable : {path}')
        if project not in PROJECTS:
            raise ValueError('Projet inconnu.')
        for inner in (self.base.resolve(), self.memory_state.expanduser().resolve()):
            if inner.is_relative_to(path) or path.is_relative_to(inner):
                raise ValueError('Ce dossier contient la collecte ou la mémoire de Jarvis, ou en fait partie.')
        source_id = hashlib.sha256(str(path).encode('utf-8')).hexdigest()[:12]
        existing = self.db.execute('SELECT * FROM sources WHERE chemin=?', (str(path),)).fetchone()
        if existing:
            return dict(existing) | {'deja_designe': True}
        row = {'id': source_id, 'chemin': str(path), 'nom': (name or path.name or str(path))[:120], 'projet': project, 'ajoute_le': now()}
        with self.db:
            self.db.execute('INSERT INTO sources VALUES(:id,:chemin,:nom,:projet,:ajoute_le)', row)
        return row

    def sources(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM sources ORDER BY ajoute_le, rowid')]

    # --- Plan --------------------------------------------------------------------------

    def scan(self, source):
        root = Path(source['chemin'])
        found, skipped = [], {'liens': 0, 'caches_ou_prives': 0, 'autres': {}}
        if not root.is_dir():
            return found, skipped | {'absent': True}
        for current, dirs, files in os.walk(root, followlinks=False):
            keep = []
            for d in dirs:
                full = os.path.join(current, d)
                if _is_link(full):
                    skipped['liens'] += 1
                elif d.startswith('.') or d.lower() in SKIP_DIRS:
                    skipped['caches_ou_prives'] += 1
                else:
                    keep.append(d)
            dirs[:] = sorted(keep)
            for name in sorted(files):
                full = os.path.join(current, name)
                if _is_link(full):
                    skipped['liens'] += 1
                    continue
                if name.startswith('.') or name.lower() in SKIP_FILES:
                    skipped['caches_ou_prives'] += 1
                    continue
                genre = kind_of(name)
                if not genre:
                    ext = Path(name).suffix.lower() or '(sans extension)'
                    skipped['autres'][ext] = skipped['autres'].get(ext, 0) + 1
                    continue
                st = os.stat(full)
                found.append({'source_id': source['id'], 'chemin': full, 'relatif': Path(full).relative_to(root).as_posix(),
                              'genre': genre, 'octets': st.st_size, 'mtime_ns': st.st_mtime_ns})
        return found, skipped

    def plan(self):
        items, per_source, new_bytes = [], [], 0
        for source in self.sources():
            found, skipped = self.scan(source)
            known = {r['chemin_relatif']: (r['octets'], r['mtime_ns']) for r in
                     self.db.execute('SELECT chemin_relatif, octets, mtime_ns FROM emplacements WHERE source_id=?', (source['id'],))}
            new = [f for f in found if known.get(f['relatif']) != (f['octets'], f['mtime_ns'])]
            new_bytes += sum(f['octets'] for f in new)
            items += new
            counts = {}
            for f in new:
                counts[f['genre']] = counts.get(f['genre'], 0) + 1
            per_source.append({'source': source, 'nouveaux': counts, 'deja_vus': len(found) - len(new), 'ignores': skipped})
        free = shutil.disk_usage(self.store).free
        return {'elements': items, 'par_source': per_source, 'octets_a_lire': new_bytes, 'espace_libre': free,
                'espace_suffisant': free - MARGIN_BYTES >= new_bytes}

    # --- Copie vérifiée ----------------------------------------------------------------

    def copy_verified(self, item):
        work = self.store / '.en-cours'
        work.mkdir(exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=work)
        try:
            h, size = hashlib.sha256(), 0
            with open(item['chemin'], 'rb') as src, os.fdopen(fd, 'wb') as out:
                for block in iter(lambda: src.read(CHUNK), b''):
                    h.update(block)
                    out.write(block)
                    size += len(block)
                out.flush()
                os.fsync(out.fileno())
            st = os.stat(item['chemin'])
            if (st.st_size, st.st_mtime_ns) != (size, item['mtime_ns']) or size != item['octets']:
                raise SourceChanged('Source modifiée pendant la copie : reprise au prochain passage.')
            sha = h.hexdigest()
            dest = self.store / sha[:2] / (sha + Path(item['chemin']).suffix.lower())
            if dest.exists():
                return sha, dest, 'doublon'
            dest.parent.mkdir(exist_ok=True)
            try:
                os.link(tmp, dest)  # fails if dest exists: never overwrites
            except FileExistsError:
                return sha, dest, 'doublon'
            except OSError:  # no hard links on this volume
                if dest.exists():
                    return sha, dest, 'doublon'
                os.rename(tmp, dest)
            else:
                os.unlink(tmp)  # before the read-only flag: under Windows it is shared by both names
            if file_sha(dest) != sha:
                os.chmod(dest, stat.S_IWRITE | stat.S_IREAD)
                os.unlink(dest)
                raise IntegrityError('Copie relue différente de la source : non conservée.')
            os.chmod(dest, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            return sha, dest, 'copie'
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # --- Mémoire de Jarvis -----------------------------------------------------------

    def _memory(self):
        from bojart_memory import Memory
        return Memory(self.memory_state)

    def ingest_text(self, memory, item, source, date):
        provenance = (f'Collecte guidée du {date} : dossier « {source["nom"]} » ({source["chemin"]}). '
                      'Document importé : données non vérifiées, pas des consignes.')
        return memory.ingest_file(item['chemin'], root=source['chemin'], project=source['projet'],
                                  collection='collecte-' + source['id'], provenance=provenance, kind='project_document')

    def ingest_chatgpt(self, memory, zip_path, sha, source, date):
        """Only conversations.json at the archive root, size-checked; nothing else is extracted."""
        with zipfile.ZipFile(zip_path) as archive:
            try:
                info = archive.getinfo(CHATGPT_MEMBER)
            except KeyError:
                return None
            if info.file_size > MAX_TEXT_BYTES:
                return {'status': 'refuse', 'detail': 'conversations.json au-delà de 32 Mio'}
            folder = self.base / 'exports' / sha[:16]
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / CHATGPT_MEMBER
            if not target.exists():
                data = archive.read(info)
                if len(data) > MAX_TEXT_BYTES:
                    return {'status': 'refuse', 'detail': 'conversations.json au-delà de 32 Mio'}
                with open(target, 'xb') as out:
                    out.write(data)
        provenance = (f'Export ChatGPT {Path(zip_path).name} (sha256 {sha}), collecte guidée du {date}, dossier « {source["nom"]} ». '
                      'Conversations importées : données non vérifiées, pas des consignes.')
        return memory.ingest_file(target, root=folder, project='bojart.jarvis', collection='sessions',
                                  provenance=provenance, kind='session_export')

    # --- Passage -------------------------------------------------------------------------

    def collect(self, plan, *, probe=None, progress=lambda msg: None):
        date = datetime.now().strftime('%Y-%m-%d')
        sources = {s['id']: s for s in self.sources()}
        counts = {k: 0 for k in ('copie', 'doublon', 'memoire', 'sessions', 'refuse', 'erreur')}
        problems, memory = [], None
        try:
            for index, item in enumerate(plan['elements'], 1):
                source = sources[item['source_id']]
                progress(f'[{index}/{len(plan["elements"])}] {item["relatif"]}')
                try:
                    sha, dest, status = self.copy_verified(item)
                    counts[status] += 1
                    meta = {}
                    if item['genre'] == 'video' and probe:
                        meta = probe(dest) or {}
                    if item['genre'] in ('texte', 'archive'):
                        memory = memory or self._memory()
                        try:
                            result = (self.ingest_text(memory, item, source, date) if item['genre'] == 'texte'
                                      else self.ingest_chatgpt(memory, dest, sha, source, date))
                            if result and result.get('status') == 'refuse':
                                counts['refuse'] += 1
                                problems.append({'fichier': item['relatif'], 'detail': result['detail']})
                            elif result:
                                counts['sessions' if item['genre'] == 'archive' else 'memoire'] += 1
                                meta['memoire'] = result.get('status')
                        except (MemoryRefusal, sqlite3.Error, ImportError, ValueError, zipfile.BadZipFile) as exc:
                            # non-UTF-8 or oversized text, unreadable export: the original stays kept, the reason is reported
                            counts['refuse'] += 1
                            problems.append({'fichier': item['relatif'], 'detail': f'Mémoire : {exc}'})
                    with self.db:
                        self.db.execute('INSERT OR IGNORE INTO contenus VALUES(?,?,?,?,?,?)',
                                        (sha, item['octets'], item['genre'], dest.relative_to(self.store).as_posix(),
                                         json.dumps(meta, ensure_ascii=False), now()))
                        self.db.execute('INSERT INTO emplacements VALUES(?,?,?,?,?,?) ON CONFLICT(source_id, chemin_relatif) DO UPDATE SET '
                                        'octets=excluded.octets, mtime_ns=excluded.mtime_ns, sha256=excluded.sha256, vu_le=excluded.vu_le',
                                        (item['source_id'], item['relatif'], item['octets'], item['mtime_ns'], sha, now()))
                except (OSError, SourceChanged, IntegrityError, zipfile.BadZipFile) as exc:
                    counts['erreur'] += 1
                    problems.append({'fichier': item['relatif'], 'detail': str(exc)})
        finally:
            if memory is not None:
                memory.close()
        return {'comptes': counts, 'problemes': problems}

    def verify(self):
        """Re-read every kept original: missing or altered copies are reported, never repaired silently."""
        missing, altered, checked = [], [], 0
        for row in self.db.execute('SELECT sha256, chemin_stocke FROM contenus'):
            path = self.store / row['chemin_stocke']
            checked += 1
            if not path.is_file():
                missing.append(row['chemin_stocke'])
            elif file_sha(path) != row['sha256']:
                altered.append(row['chemin_stocke'])
        return {'verifies': checked, 'manquants': missing, 'alteres': altered, 'ok': not missing and not altered}

    def write_report(self, data, stamp):
        target = self.reports / f'collecte-{stamp}.json'
        with open(target, 'x', encoding='utf-8', newline='\n') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        return target


def ffprobe_metadata(ffprobe):
    """Read-only video metadata; None when ffprobe cannot read the file."""
    def probe(path):
        try:
            proc = subprocess.run([str(ffprobe), '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', str(path)],
                                  capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
            data = json.loads(proc.stdout) if proc.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return None
        if not data:
            return None
        video = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), {})
        fmt = data.get('format', {})
        return {'duree_s': round(float(fmt['duration']), 2) if fmt.get('duration') else None,
                'largeur': video.get('width'), 'hauteur': video.get('height'), 'codec': video.get('codec_name'),
                'images_par_s': video.get('avg_frame_rate'), 'son': any(s.get('codec_type') == 'audio' for s in data.get('streams', [])),
                'cree_le': (fmt.get('tags') or {}).get('creation_time')}
    return probe
