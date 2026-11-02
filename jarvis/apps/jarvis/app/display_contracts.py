"""Local display proposals, NOT monitor dispatch or machine commands.
No provider or arbitrary code execution. Replay preserves receipt, staleness stays visible.
"""
from __future__ import annotations
import hashlib, json, re, sqlite3, threading, time, unicodedata
from pathlib import Path
from contextlib import contextmanager, closing
from core import Rejected, IntegrityError

def norm(value):
    if not isinstance(value,str) or not value.strip() or len(value)>400:
        raise Rejected('Commande vide ou trop longue.')
    if any(ord(c)<32 for c in value): raise Rejected('Caractère de contrôle refusé.')
    s=''.join(c for c in unicodedata.normalize('NFKD',value.lower()) if not unicodedata.combining(c))
    s=re.sub(r'[.,!?]',' ',s).strip()
    return re.sub(r'\s+',' ',re.sub(r'^jarvis\s*,?\s*','',s))

ROUTES={
 'affiche le modele a droite':('show_model','creation'),
 'montre le modele a droite':('show_model','creation'),
 'montre les sources au centre':('show_sources','pilotage'),
 'ouvre le studio':('show_sources','creation'),
 'affiche le planning a gauche':('show_planning_demo','atelier'),
 'interromps ta reponse':('interrupt_speech','pilotage'),
 'arrete de parler':('interrupt_speech','pilotage'),
 'montre les dossiers au centre':('show_workspace','pilotage'),
 'ouvre les contenus a droite':('show_growth','creation'),
 'ouvre la base metier au centre':('show_knowledge','pilotage'),
 'ouvre la conception au centre':('show_cad','pilotage'),
}
class DisplayProposals:
    def __init__(self,store):
        self.store=store; self.path=store.root/'display-proposals.sqlite3';self.lock=threading.RLock()
        with self.db() as con:
            con.execute('CREATE TABLE IF NOT EXISTS proposals (request_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,payload TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS proposal_invalidations (request_id TEXT PRIMARY KEY,reason TEXT NOT NULL)')
    @contextmanager
    def db(self):
        sessions = getattr(self, '_command_sessions', None)
        if sessions is not None:
            with sessions.connect() as con:
                yield con
            return
        # Transactions and resource lifetime are independent in sqlite3.
        with closing(sqlite3.connect(self.path, timeout=10)) as con:
            with con:
                yield con
    def fingerprint(self,d): return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    def context_hash(self): return hashlib.sha256(self.store.context_path.read_bytes()).hexdigest()
    def invalidate_all(self,reason):
        # Keep original proposal bytes: dispatched receipts compare against them.
        # A separate durable revocation also covers proposals never dispatched.
        with self.lock,self.db() as db:
            return db.execute('INSERT OR IGNORE INTO proposal_invalidations SELECT request_id,? FROM proposals',(reason,)).rowcount
    def prepare(self,d):
        required={'request_id','project_id','revision','turn_id','command','operation_id'}
        if not isinstance(d,dict) or set(d)!=required: raise Rejected('Champs inattendus ou manquants.')
        for k in ['request_id','turn_id']:
            if not isinstance(d[k],str) or not re.fullmatch('[A-Za-z0-9_-]{1,96}',d[k]):raise Rejected('Identifiant invalide.')
        self.store.require_project(d['project_id'])
        if type(d['revision'])is not int or d['revision']<0:raise Rejected('Révision invalide.')
        if d['operation_id'] is not None and not isinstance(d['operation_id'],str):raise Rejected('Référence de modèle invalide.')
        command=norm(d['command'])
        if command not in ROUTES:raise Rejected('Ordre ambigu ou non pris en charge. Aucune action exécutée.')
        action,role=ROUTES[command]; fp=self.fingerprint(d)
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT fingerprint,payload FROM proposals WHERE request_id=?',(d['request_id'],)).fetchone()
            if old:
                if old[0]!=fp:raise Rejected('Identifiant déjà utilisé pour une autre demande.')
                result=json.loads(old[1]); result['current']=self.is_current(result);result['replayed']=True
                return result
            if d['revision']!=self.store.project_revision(d['project_id']):raise Rejected('Dossier modifié depuis la demande.')
            snapshot=self.context_hash();asset=None
            if action=='show_model':
                if not d['operation_id']:raise Rejected('Sélection du modèle obligatoire ; aucune sélection devinée.')
                report=self.store.get(d['operation_id'])
                if report.get('project_id')!=d['project_id']:raise Rejected('Ce modèle appartient à un autre dossier.')
                if report.get('state')!='READY':raise Rejected('Modèle non prêt.')
                meta=report['files']['socle_metres.glb']
                asset={'operation_id':d['operation_id'],'sha256':meta['sha256'],'path':'/artifacts/'+d['operation_id']+'/socle_metres.glb'}
            elif d['operation_id'] is not None:raise Rejected('Référence de modèle sans rapport avec cette action.')
            result={'request_id':d['request_id'],'project_id':d['project_id'],'revision':d['revision'],
                    'turn_id':d['turn_id'],'context_sha256':snapshot,'created_at_epoch':time.time(),
                    'action':action,'target_role':role,'asset':asset,'status':'proposal_only',
                    'executed':False,'display_acknowledged':False,'requires_live_dispatch_validation':True,
                    'current':True,'replayed':False,'decision_source':'deterministic_local_rules','jev_called':False,
                    'physical_commands':False,'data_status':'demonstration' if action=='show_planning_demo' else 'project_data',
                    'blocker':'Transport et appairage des moniteurs physiques non raccordés.'}
            if not self.is_current(result):raise Rejected('Le contexte a changé pendant la préparation.')
            db.execute('INSERT INTO proposals VALUES (?,?,?)',(d['request_id'],fp,json.dumps(result,ensure_ascii=False)))
            return result
    def is_current(self,proposal):
        with self.db() as db:
            if db.execute('SELECT 1 FROM proposal_invalidations WHERE request_id=?',(proposal['request_id'],)).fetchone():return False
        try:self.store.require_project(proposal['project_id'])
        except Rejected:return False
        if proposal['revision']!=self.store.project_revision(proposal['project_id']) or proposal['context_sha256']!=self.context_hash():return False
        asset=proposal.get('asset')
        if asset:
            try:
                r=self.store.get(asset['operation_id'])
                return r.get('state')=='READY' and r.get('project_id')==proposal['project_id'] and r['files']['socle_metres.glb']['sha256']==asset['sha256']
            except (Rejected,IntegrityError,OSError,KeyError):return False
        return True
