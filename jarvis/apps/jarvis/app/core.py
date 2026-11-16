"""BOJ.ART Mission 01: bounded local CAD workflow, no LLM or physical adapter.
Only recipe-controlled geometry is executed. No prompt text is executed as code.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, fields
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, math, re, shutil, sqlite3, threading, unicodedata, uuid

APP_VERSION = '0.1.0'
RECIPE_VERSION = 'bojart.socle.v1'
CAD_LOCK = threading.Lock()

class Rejected(ValueError):
    """Expected, readable input/conflict rejection."""

class IntegrityError(RuntimeError):
    """A registered artifact is absent or has changed."""


def now():
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class BaseSpec:
    diameter_mm: float = 180.0
    height_mm: float = 24.0
    upper_diameter_mm: float = 150.0
    upper_height_mm: float = 4.0
    hole_diameter_mm: float = 6.0
    pitch_mm: float = 96.0
    chamfer_mm: float = 1.0

    @classmethod
    def from_dict(cls, data: dict) -> 'BaseSpec':
        names = {f.name for f in fields(cls)}
        if not isinstance(data, dict) or set(data) != names:
            raise Rejected('Les sept paramètres sont obligatoires ; aucun champ libre supplémentaire.')
        normalized = {}
        for name, value in data.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise Rejected(f'Valeur numérique finie requise : {name}')
            normalized[name] = float(value)
        spec = cls(**normalized)
        spec.validate()
        return spec

    def validate(self):
        vals = asdict(self)
        if not all(math.isfinite(v) and v > 0 for v in vals.values()):
            raise Rejected('Dimensions strictement positives et finies requises.')
        d, h, u, uh, hole, pitch, c = (vals[f.name] for f in fields(self))
        # Deliberate computational and template limits, not machine capabilities.
        if not (50 <= d <= 400 and 8 <= h <= 80):
            raise Rejected('Recette limitée à Ø 50–400 mm et hauteur 8–80 mm.')
        if not (10 <= u < d-2*c and 1 <= uh < h-2*c):
            raise Rejected('Plateau supérieur ou chanfrein incompatible avec le corps.')
        if not (2 <= hole <= 20 and 2*hole < pitch and pitch+hole+2*c+2 < u):
            raise Rejected('Les quatre perçages doivent rester distincts et dans le plateau.')
        if c > 3 or 2*c >= min(h-uh, uh):
            raise Rejected('Chanfrein trop grand pour cette hauteur.')


def normalize_text(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn').replace('’', "'").strip()


def parse_command(text: str) -> dict:
    """Strict grammar. Never silently ignore load requirements or physical actions."""
    if not isinstance(text, str) or len(text) > 500:
        raise Rejected('Demande trop longue ou invalide.')
    s = normalize_text(text)
    pattern = (r"(?:jarvis\s*[, :]\s*)?(?:cree|prepare|genere)\s+(?:moi\s+)?un\s+socle"
               r"(?:\s+d'exposition)?\s+de\s+(\d+(?:[.,]\d+)?)\s*(mm|cm|pouces?)"
               r"(?:\s+et\s+affiche[- ]le\s+(?:a\s+droite|sur\s+l'ecran\s+de\s+droite))?[.!]?$")
    m = re.fullmatch(pattern, s)
    if not m:
        raise Rejected("Commande non prise en charge. Exemple : « Crée un socle de 180 mm et affiche-le à droite ». Les contraintes supplémentaires ne sont pas interprétées.")
    value, unit = float(m.group(1).replace(',', '.')), m.group(2)
    d = value * (10 if unit == 'cm' else 25.4 if unit.startswith('pouce') else 1)
    spec = BaseSpec(diameter_mm=round(d, 5), upper_diameter_mm=round(d*5/6, 5), pitch_mm=round(d*8/15, 5))
    spec.validate()
    return {'params': asdict(spec), 'input_unit': unit, 'diameter_from_request_mm': d,
            'parser': 'grammar-fr.v1', 'llm_used': False,
            'assumptions': ['Hauteur 24 mm ; plateau supérieur 4 mm ; quatre trous Ø 6 mm ; chanfrein 1 mm.',
                            'Diamètre supérieur = 5/6 du diamètre ; cercle de perçages = 8/15.',
                            'Ces paramètres de recette sont à relire avant création. Ni charge ni procédé ne sont validés.']}


def build_geometry(spec: BaseSpec, dest: Path) -> dict:
    """Generate real CAD exports and re-read the STL. Serialized for the CAD kernel."""
    spec.validate()
    import cadquery as cq
    import trimesh
    with CAD_LOCK:
        d, h, u, uh, hole, pitch, c = (getattr(spec, f.name) for f in fields(spec))
        lower = cq.Workplane('XY').circle(d/2).extrude(h-uh)
        lower = lower.edges('%CIRCLE').chamfer(c)
        upper = cq.Workplane('XY').workplane(offset=h-uh).circle(u/2).extrude(uh)
        upper = upper.edges('>Z').chamfer(c)
        model = lower.union(upper)
        points = [(pitch/2, 0), (-pitch/2, 0), (0, pitch/2), (0, -pitch/2)]
        model = model.faces('>Z').workplane().pushPoints(points).hole(hole)
        if len(model.solids().vals()) != 1 or not model.val().isValid():
            raise IntegrityError('La géométrie CAO ne constitue pas un solide valide.')
        dest.mkdir(parents=True, exist_ok=False)
        cq.exporters.export(model, str(dest/'socle.step'))
        cq.exporters.export(model, str(dest/'socle.stl'), tolerance=0.03, angularTolerance=0.08)
        mesh = trimesh.load_mesh(str(dest/'socle.stl'), process=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
            raise IntegrityError('Le STL exporté ne passe pas les contrôles de fermeture/normales/volume.')
        bounds = mesh.extents.tolist()
        if any(abs(a-b) > 0.15 for a,b in zip(bounds,[d,d,h])):
            raise IntegrityError('Dimensions du maillage hors tolérance numérique de 0,15 mm.')
        si_mesh = mesh.copy(); si_mesh.apply_scale(0.001)
        (dest/'socle_metres.glb').write_bytes(si_mesh.export(file_type='glb'))
        centered = mesh.copy(); centered.apply_translation(-mesh.bounds.mean(axis=0))
        positions = centered.triangles.reshape(-1).round(5).tolist()
        # Per-face normals are used by the offline viewer. No invented render mesh.
        normals = mesh.face_normals.repeat(3, axis=0).reshape(-1).round(6).tolist()
        (dest/'modele.json').write_text(canonical({'positions':positions, 'normals':normals, 'units':'mm', 'diameter_mm':d}), encoding='utf8')
        proof = {'cadquery':cq.__version__, 'trimesh':trimesh.__version__,
                 'solid_count':1, 'cad_brep_valid':True, 'stl_watertight':bool(mesh.is_watertight),
                 'stl_winding_consistent':bool(mesh.is_winding_consistent), 'triangles':len(mesh.faces),
                 'bounds_mm':bounds, 'geometric_volume_cm3':round(float(mesh.volume)/1000,3),
                 'units':{'step':'mm','stl':'mm : convention du manifeste','glb':'m'},
                 'numerical_tolerance_mm':0.15,
                 'not_validated':['résistance / stabilité','ajustements réels','matière et profil','slicing','impression physique']}
        return proof


class Store:
    def __init__(self, root: str | Path, context_path: str | Path | None = None):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True)
        self.dbpath = self.root/'missions.sqlite3'
        self.artifacts = self.root/'artifacts'; self.artifacts.mkdir(exist_ok=True)
        # A workspace owns its context. Tests and live edits must never mutate
        # the source distribution; a restored context takes precedence.
        self.context_path = Path(context_path) if context_path else self.root/'CONTEXTE_REFERENCE.json'
        if context_path is None and not self.context_path.exists():
            source = Path(__file__).resolve().parents[1]/'context'/'CONTEXTE_REFERENCE.json'
            try:
                with self.context_path.open('xb') as target:
                    target.write(source.read_bytes())
            except FileExistsError:
                pass
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, revision INTEGER NOT NULL);
              CREATE TABLE IF NOT EXISTS project_profiles (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, created TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS operations (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, expected_revision INTEGER NOT NULL,
                fingerprint TEXT NOT NULL, params_json TEXT NOT NULL, context_sha256 TEXT NOT NULL,
                state TEXT NOT NULL, created TEXT NOT NULL, finished TEXT, result_json TEXT, error TEXT);
              CREATE UNIQUE INDEX IF NOT EXISTS one_running_per_project ON operations(project) WHERE state='RUNNING';
            ''')

    @contextmanager
    def connect(self):
        """Commit/rollback a short transaction, then always close the connection.

        SQLite's own context manager does not close its resource. Keep this
        separate from transaction control so exceptions still roll back.
        """
        db = sqlite3.connect(self.dbpath, timeout=10)
        try:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA busy_timeout=10000')
            db.execute('PRAGMA foreign_keys=ON')
            with db:
                yield db
        finally:
            db.close()

    def project_revision(self, project='BOJ-PILOTE-001'):
        with self.connect() as db:
            r = db.execute('SELECT revision FROM projects WHERE id=?',(project,)).fetchone()
        return r['revision'] if r else 0

    def require_project(self, project):
        if not isinstance(project, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{1,63}', project):
            raise Rejected('Identifiant de dossier invalide.')
        with self.connect() as db:
            exists = db.execute('SELECT id FROM projects WHERE id=? UNION SELECT id FROM project_profiles WHERE id=?', (project, project)).fetchone()
        if project != 'BOJ-PILOTE-001' and not exists:
            raise Rejected('Dossier inconnu : le créer avant de préparer une commande.')
        return project

    def create_project(self, project, name):
        if not isinstance(project,str) or not re.fullmatch(r'BOJ-[A-Z0-9_-]{2,59}',project):
            raise Rejected('Identifiant BOJ-… requis.')
        if not isinstance(name,str) or not 1 <= len(name.strip()) <= 120 or any(ord(c)<32 for c in name):
            raise Rejected('Nom de dossier invalide.')
        name=name.strip()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT name FROM project_profiles WHERE id=?',(project,)).fetchone()
            if old and old['name']!=name:raise Rejected('Cet identifiant désigne déjà un autre dossier.')
            db.execute('INSERT OR IGNORE INTO project_profiles VALUES(?,?,?)',(project,name,now()))
        return {'project_id':project,'name':name,'revision':self.project_revision(project),'replayed':bool(old)}

    def list_projects(self):
        with self.connect() as db:
            rows=db.execute('''SELECT ids.id, COALESCE(p.name,ids.id) AS name, COALESCE(r.revision,0) AS revision
              FROM (SELECT id FROM projects UNION SELECT id FROM project_profiles UNION SELECT 'BOJ-PILOTE-001' AS id) ids
              LEFT JOIN project_profiles p ON p.id=ids.id LEFT JOIN projects r ON r.id=ids.id ORDER BY ids.id''').fetchall()
        return [dict(r) for r in rows]

    def list_jobs(self, project=None):
        if project is not None:self.require_project(project)
        with self.connect() as db:
            rows = db.execute('SELECT id, project, expected_revision, state, created, finished, error FROM operations WHERE (? IS NULL OR project=?) ORDER BY created DESC LIMIT 50',(project,project)).fetchall()
        return [dict(r) for r in rows]

    def get(self, operation_id: str):
        if not isinstance(operation_id,str) or not re.fullmatch(r'[0-9a-f]{32}', operation_id): raise Rejected('Identifiant invalide.')
        with self.connect() as db:
            row = db.execute('SELECT * FROM operations WHERE id=?',(operation_id,)).fetchone()
        if not row: raise Rejected('Mission inconnue.')
        if row['state'] != 'READY':
            return {'operation_id':row['id'],'state':row['state'],'error':row['error'],'project_id':row['project']}
        try:
            report = json.loads(row['result_json'])
        except (ValueError, TypeError) as e:
            raise IntegrityError('Reçu de mission illisible.') from e
        folder = self.artifacts/operation_id
        manifest_path = folder/'manifeste.json'
        try:
            same_manifest = canonical(json.loads(manifest_path.read_text(encoding='utf8'))) == canonical(report)
        except (OSError, ValueError):
            same_manifest = False
        if not same_manifest or manifest_path.is_symlink():
            raise IntegrityError('Manifeste absent ou altéré ; reçu conservé en base.')
        self.validate_result(row, report)
        return report

    def validate_result(self, row, report):
        """Validate a saved receipt without following paths supplied by it."""
        expected={'socle.step','socle.stl','socle_metres.glb','modele.json','recette_core.py','parametres.json'}
        folder=self.artifacts/row['id']
        try:
            if not isinstance(report,dict) or folder.is_symlink():raise ValueError('Dossier ou reçu invalide.')
            if report['schema']!='bojart.mission01.receipt.v1' or report['state']!='READY' or report['physical_commands_enabled'] is not False:raise ValueError('Type de reçu invalide.')
            if report['operation_id']!=row['id'] or report['project_id']!=row['project'] or report['revision']!=row['expected_revision']+1:raise ValueError('Identité ou révision divergente.')
            if report['context_sha256']!=row['context_sha256'] or canonical(report['parameters'])!=row['params_json']:raise ValueError('Contexte ou paramètres divergents.')
            if not isinstance(report['files'],dict) or set(report['files'])!=expected:raise ValueError('Inventaire de résultat divergent.')
            for name,meta in report['files'].items():
                p=folder/name
                if not isinstance(meta,dict) or type(meta.get('bytes')) is not int or not isinstance(meta.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',meta['sha256']):raise ValueError('Empreinte ou taille invalide.')
                if not p.is_file() or p.is_symlink() or p.stat().st_size!=meta['bytes'] or file_digest(p)!=meta['sha256']:raise ValueError('Fichier absent ou altéré : '+name)
        except (KeyError,TypeError,ValueError,OSError) as e:
            raise IntegrityError('Résultat non vérifié : '+str(e)) from e

    def run(self, request: dict, builder=build_geometry):
        keys={'operation_id','project_id','expected_revision','params'}
        if not isinstance(request,dict) or set(request)!=keys: raise Rejected('Contrat de mission incomplet ou champs inconnus.')
        op, project, revision = request['operation_id'],request['project_id'],request['expected_revision']
        if not isinstance(op,str) or not re.fullmatch(r'[0-9a-f]{32}',op): raise Rejected('ID opération attendu : 32 caractères hexadécimaux.')
        if not isinstance(project,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{1,63}',project): raise Rejected('Identifiant de projet invalide.')
        if type(revision) is not int or revision<0: raise Rejected('Révision entière positive ou nulle requise.')
        spec=BaseSpec.from_dict(request['params'])
        # Fingerprint is on the effective explicit recipe, not transient presentation text.
        effective={'project_id':project,'expected_revision':revision,'params':asdict(spec),'recipe_version':RECIPE_VERSION}
        fingerprint=digest_bytes(canonical(effective).encode())
        context_hash=file_digest(self.context_path)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT fingerprint FROM operations WHERE id=?',(op,)).fetchone()
            if old:
                if old['fingerprint']!=fingerprint: raise Rejected('Identifiant déjà utilisé avec une autre demande.')
                return self.get(op)
            db.execute('INSERT OR IGNORE INTO projects VALUES(?,0)',(project,))
            actual=db.execute('SELECT revision FROM projects WHERE id=?',(project,)).fetchone()[0]
            if actual!=revision: raise Rejected(f'Le dossier a changé : révision attendue {revision}, actuelle {actual}.')
            if db.execute("SELECT 1 FROM operations WHERE project=? AND state IN ('RUNNING','INTERRUPTED')",(project,)).fetchone():
                raise Rejected('Une mission est en cours ou son interruption reste à examiner dans ce dossier.')
            db.execute('INSERT INTO operations(id,project,expected_revision,fingerprint,params_json,context_sha256,state,created) VALUES(?,?,?,?,?,?,?,?)',
                       (op,project,revision,fingerprint,canonical(asdict(spec)),context_hash,'RUNNING',now()))
        work=self.root/('.work-'+op); final=self.artifacts/op
        try:
            proof=builder(spec,work)
            # Full recipe travels with its result, so geometry remains reproducible.
            shutil.copy2(Path(__file__), work/'recette_core.py')
            (work/'parametres.json').write_text(canonical({'recipe_version':RECIPE_VERSION,'params':asdict(spec)}),encoding='utf8')
            expected={'socle.step','socle.stl','socle_metres.glb','modele.json','recette_core.py','parametres.json'}
            if {p.name for p in work.iterdir()}!=expected or any(p.is_symlink() for p in work.iterdir()):
                raise IntegrityError('Le moteur a produit des fichiers inattendus.')
            files={p.name:{'sha256':file_digest(p),'bytes':p.stat().st_size} for p in sorted(work.iterdir())}
            report={'schema':'bojart.mission01.receipt.v1','operation_id':op,'project_id':project,
                    'revision':revision+1,'state':'READY','created_at':now(),'recipe_version':RECIPE_VERSION,
                    'context_sha256':context_hash,'parameters':asdict(spec),'proof':proof,'files':files,
                    'physical_commands_enabled':False,'llm_used':False,'approval':'géométrie numérique uniquement'}
            (work/'manifeste.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
            if final.exists(): raise IntegrityError('Le dossier de sortie existe déjà ; refus d’écraser.')
            work.rename(final)
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                actual=db.execute('SELECT revision FROM projects WHERE id=?',(project,)).fetchone()[0]
                if actual!=revision: raise Rejected('Révision concurrente modifiée pendant la construction.')
                db.execute('UPDATE projects SET revision=? WHERE id=?',(revision+1,project))
                db.execute('UPDATE operations SET state=?,finished=?,result_json=? WHERE id=?',('READY',now(),canonical(report),op))
            return self.get(op)
        except Exception as exc:
            with self.connect() as db:
                db.execute('UPDATE operations SET state=?,finished=?,error=? WHERE id=?',('FAILED',now(),str(exc)[:800],op))
            raise

    def backup(self, destination: Path):
        """Coherent local snapshot: block reservations/completions while reading files.
        Not an authenticated signature; restore is deliberately a separate review step.
        """
        import zipfile
        destination=Path(destination)
        if destination.exists(): raise Rejected('Refus d’écraser une sauvegarde.')
        staging=self.root/('.backup-'+uuid.uuid4().hex);staging.mkdir()
        try:
            with self.connect() as lock:
                lock.execute('BEGIN IMMEDIATE')
                if lock.execute("SELECT 1 FROM operations WHERE state='RUNNING'").fetchone():
                    raise Rejected('Sauvegarde refusée : une mission est encore en cours ou interrompue.')
                ops=[x[0] for x in lock.execute("SELECT id FROM operations WHERE state='READY'")]
                for op in ops: self.get(op)
                with self.connect() as read, closing(sqlite3.connect(staging/'missions.sqlite3')) as target, target:
                    read.backup(target)
                shutil.copy2(self.context_path,staging/'CONTEXTE_REFERENCE.json')
                for op in ops: shutil.copytree(self.artifacts/op,staging/'artifacts'/op)
                lock.commit()
            manifest={str(p.relative_to(staging)).replace('\\','/'):file_digest(p) for p in staging.rglob('*') if p.is_file()}
            (staging/'SHA256.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
            destination.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as z:
                for p in staging.rglob('*'):
                    if p.is_file():z.write(p,p.relative_to(staging))
            return {'path':str(destination),'files':len(manifest),'sha256':file_digest(destination)}
        finally:
            shutil.rmtree(staging,ignore_errors=True)


def verify_backup(path: Path):
    import zipfile
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)>5000 or sum(i.file_size for i in z.infolist())>1024*1024*1024:
            raise IntegrityError('Archive hors limites de ce module.')
        if 'SHA256.json' not in names or z.getinfo('SHA256.json').file_size>1024*1024:
            raise IntegrityError('Manifeste de sauvegarde absent ou trop volumineux.')
        if len(names)!=len(set(names)):raise IntegrityError('Entrées dupliquées dans la sauvegarde.')
        if any(Path(n).is_absolute() or '..' in Path(n).parts or '\\' in n or ':' in n for n in names):raise IntegrityError('Chemin non sûr.')
        expected=json.loads(z.read('SHA256.json'))
        if set(names)!=set(expected)|{'SHA256.json'}:raise IntegrityError('Liste de fichiers incohérente.')
        for name,sha in expected.items():
            h=hashlib.sha256()
            with z.open(name) as f:
                for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
            if h.hexdigest()!=sha:raise IntegrityError('Sauvegarde altérée : '+name)
    return {'ok':True,'verified_files':len(expected)}
