"""M05 workspace snapshots and recovery. No network, model, or machine actions.

The integrated server serializes mutations and holds an OS workspace lease.
SQLite backup() copies each database while every known writer is reserved.
Restoration only creates a new directory and never executes archived code.
"""
from __future__ import annotations
from contextlib import ExitStack, closing
from pathlib import Path, PurePosixPath
import hashlib, json, os, re, shutil, sqlite3, stat, threading, uuid, zipfile
from core import Store, Rejected, IntegrityError, canonical, file_digest, now
from dialogue import strict_json
from context_guard import validate_context

SCHEMA='bojart.workspace.snapshot.v1'
DATABASES=('missions.sqlite3','display-proposals.sqlite3','control-tower.sqlite3','studio/media.sqlite','growth/growth.sqlite')
MAX_BYTES=1024*1024*1024
MAX_FILES=20000
SHA=re.compile(r'^[0-9a-f]{64}$')

class WorkspaceLease:
    """An OS lock, released after crashes as well as a normal server shutdown."""
    def __init__(self, root):
        root=Path(root)
        if (root/'.restore-in-progress').exists():raise Rejected('Restauration inachevée : conserver ce dossier pour examen.')
        p=root/'.workspace.lock'
        if p.is_symlink():raise Rejected('Verrou symbolique refusé.')
        self.file=p.open('a+b')
        try:
            self.file.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as e:
            self.file.close();self.file=None
            raise Rejected('Ce dossier est déjà ouvert par un autre Jarvis. Réutiliser sa fenêtre.') from e
    def close(self):
        if self.file:
            self.file.close();self.file=None


def safe_member(name):
    p=PurePosixPath(name)
    if not name or str(p)!=name or p.is_absolute() or '\\' in name or ':' in name or any(ord(c)<32 for c in name):
        raise IntegrityError('Chemin d’archive invalide.')
    for part in p.parts:
        if part in ('.','..') or part.endswith((' ','.')) or part.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
            raise IntegrityError('Chemin d’archive non portable.')
    if name not in {*DATABASES,'CONTEXTE_REFERENCE.json','snapshot.json','SHA256.json','integrity-report.json'} and not name.startswith(('artifacts/','media/','incomplete/')):
        raise IntegrityError('Fichier hors du périmètre de sauvegarde.')
    return p


def inspect_zip(z):
    infos=z.infolist();names=[i.filename for i in infos]
    if len(infos)>MAX_FILES or sum(i.file_size for i in infos)>MAX_BYTES:raise IntegrityError('Sauvegarde hors limites : 1 Gio / 20 000 fichiers.')
    if len({n.casefold() for n in names})!=len(names):raise IntegrityError('Entrées dupliquées dans la sauvegarde.')
    for i in infos:
        safe_member(i.filename)
        if i.is_dir() or stat.S_ISLNK(i.external_attr>>16) or i.flag_bits&1:raise IntegrityError('Entrée spéciale refusée.')
    if not {*DATABASES,'CONTEXTE_REFERENCE.json','snapshot.json','SHA256.json'}<=set(names):raise IntegrityError('Sauvegarde globale incomplète.')
    if z.getinfo('SHA256.json').file_size>4*1024*1024 or z.getinfo('snapshot.json').file_size>1024*1024:raise IntegrityError('Manifeste trop volumineux.')
    hashes=strict_json(z.read('SHA256.json'));meta=strict_json(z.read('snapshot.json'))
    if not isinstance(hashes,dict) or set(hashes)!=(set(names)-{'SHA256.json'}):raise IntegrityError('Inventaire de sauvegarde incohérent.')
    if not isinstance(meta,dict) or meta.get('schema')!=SCHEMA or meta.get('databases')!=list(DATABASES):raise IntegrityError('Version de sauvegarde non prise en charge.')
    if not isinstance(meta.get('snapshot_id'),str) or not re.fullmatch('[0-9a-f]{32}',meta['snapshot_id']) or not isinstance(meta.get('created_at'),str) or not isinstance(meta.get('scope'),list):raise IntegrityError('Identité de sauvegarde invalide.')
    for name,expected in hashes.items():
        if not isinstance(expected,str) or not SHA.fullmatch(expected):raise IntegrityError('Empreinte invalide.')
        h=hashlib.sha256()
        with z.open(name) as source:
            for b in iter(lambda:source.read(1024*1024),b''):h.update(b)
        if h.hexdigest()!=expected:raise IntegrityError('Sauvegarde altérée : '+name)
    validate_context(strict_json(z.read('CONTEXTE_REFERENCE.json')))
    return meta,hashes


def verify_snapshot(path):
    try:
        with zipfile.ZipFile(path) as z:meta,hashes=inspect_zip(z)
    except (zipfile.BadZipFile,KeyError,ValueError,RuntimeError) as e:
        raise IntegrityError('Sauvegarde illisible ou invalide : '+str(e)) from e
    return {'schema':SCHEMA,'ok':True,'snapshot_id':meta['snapshot_id'],'files':len(hashes),
            'created_at':meta['created_at'],'sha256':file_digest(Path(path)),'scope':meta['scope']}


def checked_database(path):
    if not Path(path).is_file() or Path(path).is_symlink():raise IntegrityError('Base absente ou symbolique.')
    with closing(sqlite3.connect(path)) as db:
        db.execute('PRAGMA trusted_schema=OFF')
        if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:raise IntegrityError('Base SQLite altérée : '+Path(path).name)
        if db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view') LIMIT 1").fetchone():raise IntegrityError('Schéma SQLite inattendu.')
        if db.execute('PRAGMA foreign_key_check').fetchone():raise IntegrityError('Référence SQLite incohérente.')


def restore_snapshot(archive, destination):
    """Validate then create a *new* workspace. Never overlay an existing state."""
    archive=Path(archive).resolve(strict=True);destination=Path(destination).absolute()
    if destination.exists() or destination.is_symlink():raise Rejected('Choisir un dossier de restauration qui n’existe pas.')
    if any(p.is_symlink() for p in destination.parents):raise Rejected('Destination symbolique refusée.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    owned=False
    try:
        with zipfile.ZipFile(archive) as z:
            meta,hashes=inspect_zip(z)
            destination.mkdir();owned=True
            (destination/'.restore-in-progress').write_text('Restauration en cours',encoding='utf8')
            for name,expected in hashes.items():
                target=destination.joinpath(*safe_member(name).parts);target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(name) as source,target.open('xb') as out:shutil.copyfileobj(source,out,1024*1024)
                if file_digest(target)!=expected:raise IntegrityError('Source modifiée pendant la restauration.')
        for rel in DATABASES:checked_database(destination/rel)
        with closing(sqlite3.connect(destination/'studio/media.sqlite')) as db,db:
            db.execute('PRAGMA trusted_schema=OFF')
            locations=db.execute('SELECT path,asset_id FROM locations').fetchall()
            assets={r[0] for r in db.execute('SELECT id FROM assets')}
            if assets!={r[1] for r in locations}:raise IntegrityError('Inventaire des médias incomplet.')
            for path,aid in locations:
                rel=safe_member(path)
                if rel.parts[0]!='media' or not SHA.fullmatch(aid) or file_digest(destination/path)!=aid:raise IntegrityError('Lien média incohérent.')
                db.execute('UPDATE locations SET path=? WHERE path=?',(str(destination/path),path))
        restored=Store(destination)
        with restored.connect() as db:
            ready=db.execute("SELECT id,project,expected_revision FROM operations WHERE state='READY'").fetchall()
        for op,project,revision in ready:
            restored.get(op)
            if restored.project_revision(project)<revision+1:raise IntegrityError('Révision de dossier incohérente.')
        with closing(sqlite3.connect(destination/'control-tower.sqlite3')) as db,db:
            db.execute('PRAGMA trusted_schema=OFF')
            db.execute('DELETE FROM screens')
            db.execute("UPDATE commands SET state='cancelled_restore',screen_id=NULL,message='Restauration : relire puis émettre une nouvelle commande.' WHERE state IN ('queued','delivered')")
        with closing(sqlite3.connect(destination/'missions.sqlite3')) as db,db:
            db.execute('PRAGMA trusted_schema=OFF')
            db.execute("UPDATE operations SET state='INTERRUPTED',error='Restauration : opération non terminée à examiner.' WHERE state='RUNNING'")
        receipt={'schema':'bojart.restore.receipt.v1','restored_at':now(),'snapshot_id':meta['snapshot_id'],
                 'archive_sha256':file_digest(archive),'verified_files':len(hashes),'databases':list(DATABASES),
                 'media_relocated':len(locations),'pending_display_commands':'cancelled_restore','physical_actions':False}
        (destination/'RESTORE_RECEIPT.json').write_text(canonical(receipt),encoding='utf8')
        (destination/'.restore-in-progress').unlink()
        return {**receipt,'destination':str(destination)}
    except Exception:
        if owned:shutil.rmtree(destination)
        raise

class WorkspaceState:
    def __init__(self,server):
        self.server=server;self.store=server.store;self.root=self.store.root
        self.lock=threading.RLock();self.closing=False
        # Only called after acquiring the exclusive process lease. These jobs
        # cannot still be running in another supported server instance.
        with self.store.connect() as db:
            db.execute("UPDATE operations SET state='INTERRUPTED',error='Arrêt avant confirmation ; fichiers conservés, examen nécessaire.' WHERE state='RUNNING'")
            for op, in db.execute("SELECT id FROM operations WHERE state='INTERRUPTED'").fetchall():
                db.execute("UPDATE dialogue_proposals SET state='INTERRUPTED',outcome=? WHERE operation_id=?",(canonical({'operation_id':op,'state':'INTERRUPTED'}),op))

    def overview(self):
        with self.store.connect() as db:
            counts={r[0]:r[1] for r in db.execute('SELECT state,COUNT(*) FROM operations GROUP BY state')}
            interrupted=[dict(r) for r in db.execute("SELECT id,project,state,error FROM operations WHERE state='INTERRUPTED'")]
            proposals=db.execute('SELECT COUNT(*) FROM dialogue_proposals').fetchone()[0]
        with self.server.library.lock:
            media=self.server.library.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
            segments=self.server.library.db.execute('SELECT COUNT(*) FROM segments').fetchone()[0]
            briefs=self.server.library.db.execute('SELECT COUNT(*) FROM plans').fetchone()[0]
        with closing(self.server.growth.connect()) as db:packets=db.execute('SELECT COUNT(*) FROM packets').fetchone()[0]
        snapshots=[]
        for p in (self.root/'backups').glob('bojart-global-*.zip'):
            if p.is_file() and not p.is_symlink() and re.fullmatch(r'bojart-global-[0-9a-f]{32}\.zip',p.name):
                info=p.stat();snapshots.append({'name':p.name,'url':'/backups/'+p.name,'bytes':info.st_size,'modified_at_unix':info.st_mtime})
        snapshots.sort(key=lambda x:x['modified_at_unix'],reverse=True)
        integrity=None
        if (self.root/'integrity-report.json').is_file():
            try:integrity=strict_json((self.root/'integrity-report.json').read_bytes())
            except (ValueError,OSError):pass
        return {'schema':'bojart.workspace.state.v1','observed_at':now(),'projects':self.store.list_projects(),
                'operations':counts,'interrupted':interrupted,'dialogue_proposals':proposals,
                'media':media,'segments':segments,'studio_briefs':briefs,'growth_drafts':packets,
                'recent_snapshots':snapshots[:8],'last_integrity_check':integrity,
                'shared_catalogue':True,'backup_scope':list(DATABASES),'production_ready':False,
                'restore_receipt':strict_json((self.root/'RESTORE_RECEIPT.json').read_bytes()) if (self.root/'RESTORE_RECEIPT.json').is_file() else None}

    def check(self):
        issues=[];ready=0;media=0
        with self.lock:
            for rel in DATABASES:
                try:checked_database(self.root/rel)
                except (sqlite3.Error,IntegrityError,OSError) as e:issues.append({'kind':'database','id':rel,'message':str(e)})
            with self.store.connect() as db:ops=[r[0] for r in db.execute("SELECT id FROM operations WHERE state='READY'")]
            for op in ops:
                try:self.store.get(op);ready+=1
                except (IntegrityError,Rejected,OSError) as e:issues.append({'kind':'artifact','id':op,'message':str(e)})
            with self.server.library.lock:assets=[r[0] for r in self.server.library.db.execute('SELECT id FROM assets')]
            for aid in assets:
                try:self.server.library.available(aid);media+=1
                except (IntegrityError,Rejected,OSError) as e:issues.append({'kind':'media','id':aid,'message':str(e)})
            report={'schema':'bojart.integrity.v1','observed_at':now(),'ok':not issues,'databases':len(DATABASES),
                    'verified_operations':ready,'verified_media':media,'issues':issues,'scope':'Intégrité numérique ; pas de qualification matérielle.'}
            temp=self.root/('.integrity-'+uuid.uuid4().hex)
            temp.write_text(canonical(report),encoding='utf8');os.replace(temp,self.root/'integrity-report.json')
            return report

    def recover(self,operation_id,resolution):
        if resolution not in ('verify_completed','keep_failed'):raise Rejected('Résolution inconnue.')
        self.store.get(operation_id)  # validates the identifier and existence
        with self.lock,self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM operations WHERE id=?',(operation_id,)).fetchone()
            if row['state']!='INTERRUPTED':raise Rejected('Seule une opération interrompue peut être examinée ici.')
            if resolution=='keep_failed':
                db.execute("UPDATE operations SET state='FAILED',finished=?,error='Clôture manuelle après interruption ; fichiers conservés.' WHERE id=?",(now(),operation_id))
                db.execute("UPDATE dialogue_proposals SET state='FAILED',outcome=? WHERE operation_id=?",(canonical({'operation_id':operation_id,'state':'FAILED'}),operation_id))
                return {'operation_id':operation_id,'state':'FAILED','files_preserved':True,'rerun':False}
            folder=self.store.artifacts/operation_id
            try:
                report=strict_json((folder/'manifeste.json').read_bytes())
                if folder.is_symlink() or (folder/'manifeste.json').is_symlink():raise IntegrityError('Lien symbolique refusé.')
                self.store.validate_result(row,report)
                if self.store.project_revision(row['project'])!=row['expected_revision']:raise Rejected('Le dossier a évolué ; ne pas appliquer une ancienne révision.')
            except (KeyError,ValueError,OSError) as e:raise IntegrityError('Récupération complète impossible : '+str(e)) from e
            db.execute('UPDATE projects SET revision=? WHERE id=?',(report['revision'],row['project']))
            db.execute("UPDATE operations SET state='READY',finished=?,result_json=?,error=NULL WHERE id=?",(now(),canonical(report),operation_id))
            db.execute("UPDATE dialogue_proposals SET state='COMPLETED',outcome=? WHERE operation_id=?",(canonical({'operation_id':operation_id,'state':'READY'}),operation_id))
            return {'operation_id':operation_id,'state':'READY','files_preserved':True,'rerun':False}

    def backup(self,request_id=None):
        rid=request_id or uuid.uuid4().hex
        if not isinstance(rid,str) or not re.fullmatch('[0-9a-f]{32}',rid):raise Rejected('Identifiant de sauvegarde invalide.')
        target=self.root/'backups'/('bojart-global-'+rid+'.zip');target.parent.mkdir(exist_ok=True)
        with self.lock:
            if target.exists():
                result=verify_snapshot(target)
                if result['snapshot_id']!=rid:raise IntegrityError('Identifiant de sauvegarde divergent.')
                return {**result,'url':'/backups/'+target.name,'replayed':True}
            stage=self.root/('.snapshot-'+uuid.uuid4().hex);stage.mkdir();created=False
            try:
                with ExitStack() as stack:
                    stack.enter_context(self.server.library.lock)
                    for rel in DATABASES:
                        con=stack.enter_context(closing(sqlite3.connect(self.root/rel,timeout=10)))
                        con.execute('BEGIN IMMEDIATE');stack.callback(con.rollback)
                    with self.store.connect() as db:
                        if db.execute("SELECT 1 FROM operations WHERE state='RUNNING'").fetchone():raise Rejected('Création en cours : attendre son reçu avant la sauvegarde.')
                        ready=[r[0] for r in db.execute("SELECT id FROM operations WHERE state='READY'")]
                    for op in ready:self.store.get(op)
                    for rel in DATABASES:
                        dest=stage/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                        with closing(sqlite3.connect(self.root/rel)) as source,closing(sqlite3.connect(dest)) as out:source.backup(out)
                        checked_database(dest)
                    shutil.copyfile(self.store.context_path,stage/'CONTEXTE_REFERENCE.json')
                    def copy_tree(source,dest):
                        if source.is_symlink():raise IntegrityError('Dossier symbolique refusé.')
                        for p in source.rglob('*'):
                            if p.is_symlink():raise IntegrityError('Lien symbolique dans les fichiers de travail.')
                            if p.is_file():
                                q=dest/p.relative_to(source);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
                    copy_tree(self.store.artifacts,stage/'artifacts')
                    for p in self.root.glob('.work-*'):
                        if p.is_symlink():raise IntegrityError('Dossier incomplet symbolique refusé.')
                        if p.is_dir():copy_tree(p,stage/'incomplete'/p.name[6:])
                    if (self.root/'incomplete').is_dir():copy_tree(self.root/'incomplete',stage/'incomplete')
                    if (self.root/'integrity-report.json').is_file():shutil.copyfile(self.root/'integrity-report.json',stage/'integrity-report.json')
                    assets=[r[0] for r in self.server.library.db.execute('SELECT id FROM assets')]
                    with closing(sqlite3.connect(stage/'studio/media.sqlite')) as db,db:
                        db.execute('DELETE FROM locations')
                        for aid in assets:
                            source=self.server.library.available(aid);rel='media/'+aid+source.suffix.lower();dest=stage/rel;dest.parent.mkdir(exist_ok=True)
                            shutil.copyfile(source,dest)
                            if file_digest(dest)!=aid:raise IntegrityError('Média modifié pendant la copie.')
                            db.execute('INSERT INTO locations VALUES(?,?)',(rel,aid))
                meta={'schema':SCHEMA,'snapshot_id':rid,'created_at':now(),'databases':list(DATABASES),
                      'scope':['CAO et propositions','dossiers et révisions','Studio et médias exacts','brouillons Growth','régie et reçus','contexte','fichiers incomplets conservés'],
                      'excluded':['secrets et cookies','modèles IA externes','pilotes et profils machine externes','anciens fichiers de sauvegarde','états privés des sites hébergés'],
                      'restore_rule':'Nouveau dossier exclusivement ; commandes visuelles en attente neutralisées.'}
                (stage/'snapshot.json').write_text(canonical(meta),encoding='utf8')
                paths=sorted(p for p in stage.rglob('*') if p.is_file())
                if len(paths)+1>MAX_FILES or sum(p.stat().st_size for p in paths)>MAX_BYTES-4*1024*1024:raise Rejected('Sauvegarde hors limites : 1 Gio / 20 000 fichiers.')
                hashes={p.relative_to(stage).as_posix():file_digest(p) for p in paths}
                (stage/'SHA256.json').write_text(canonical(hashes),encoding='utf8')
                with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
                    created=True
                    for p in [*paths,stage/'SHA256.json']:z.write(p,p.relative_to(stage).as_posix())
                result=verify_snapshot(target)
                return {**result,'url':'/backups/'+target.name,'replayed':False}
            except Exception:
                if created:target.unlink(missing_ok=True)
                raise
            finally:shutil.rmtree(stage)
