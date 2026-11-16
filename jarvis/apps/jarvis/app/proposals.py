"""Short-lived review receipts. The client cannot substitute parameters on confirm."""
from __future__ import annotations
import json, threading, time, uuid
from core import Store, Rejected, IntegrityError, canonical, file_digest, build_geometry, now
from dialogue import interpret, strict_json
from context_guard import validate_context

class ProposalBook:
    def __init__(self,store:Store,clock=time.time,ttl=600):
        self.store=store;self.clock=clock;self.ttl=ttl
        self.lock=threading.Lock()
        with store.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS dialogue_proposals (
              id TEXT PRIMARY KEY, project TEXT NOT NULL, revision INTEGER NOT NULL,
              context_hash TEXT NOT NULL, issued REAL NOT NULL, expires REAL NOT NULL,
              operation_id TEXT UNIQUE NOT NULL, body TEXT NOT NULL, outcome TEXT, state TEXT NOT NULL);
            ''')
    def prepare(self,text,revision,provider=None,source='typed',project_id='BOJ-PILOTE-001'):
        if type(revision)is not int or revision<0:raise Rejected('Révision invalide.')
        if source not in {'typed','transcript_reviewed'}:raise Rejected('Origine de demande invalide.')
        p=self.store.require_project(project_id);h=file_digest(self.store.context_path)
        snapshot=strict_json(self.store.context_path.read_bytes());validate_context(snapshot)
        if self.store.project_revision(p)!=revision:raise Rejected('Le dossier a changé. Relisez-le.')
        decision=interpret(text,provider)
        # A slow model call may finish after another client created a revision.
        if file_digest(self.store.context_path)!=h or self.store.project_revision(p)!=revision:
            raise Rejected('Contexte modifié pendant l’interprétation. Proposition écartée.')
        if decision['intent']=='create_figurine':
            return {**decision,'project_id':p,'revision':revision,'physical_commands':False,
                    'message':decision['message']+' Chaîne figurine exécutable par jarvis/tools/figurine_pipeline.py ; '
                              'pas encore raccordée à ce bouton de confirmation.'}
        if decision['intent']!='create_base':
            return {**decision,'project_id':p,'revision':revision,'jobs':self.store.list_jobs(p),
                    'message':'État lu dans le journal local ; aucune action physique.'}
        key=uuid.uuid4().hex;op=uuid.uuid4().hex;t=self.clock()
        result={**decision,'proposal_id':key,'project_id':p,'expected_revision':revision,
                'context_sha256':h,'created_at':now(),'expires_at_unix':t+self.ttl,
                'source':source,'operation_id':op,'physical_commands':False,
                'context_snapshot':snapshot}
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT revision FROM projects WHERE id=?',(p,)).fetchone()
            actual=current[0] if current else 0
            if actual!=revision or file_digest(self.store.context_path)!=h:raise Rejected('Contexte devenu différent.')
            if db.execute("SELECT 1 FROM operations WHERE project=? AND state IN ('RUNNING','INTERRUPTED')",(p,)).fetchone():
                raise Rejected('Une création est déjà en cours ou son interruption doit être examinée.')
            db.execute('INSERT INTO dialogue_proposals VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (key,p,revision,h,t,t+self.ttl,op,canonical(result),None,'PROPOSED'))
        return result
    def confirm(self,request,builder=build_geometry):
        if not isinstance(request,dict) or set(request)!={'proposal_id','approved'} or request['approved'] is not True:
            raise Rejected('Validation explicite de la proposition requise.')
        key=request['proposal_id']
        if not isinstance(key,str) or len(key)!=32 or any(c not in '0123456789abcdef' for c in key):raise Rejected('ID invalide.')
        # Model workers and audio never call this path; it is a separate reviewed UI operation.
        with self.lock:
            with self.store.connect() as db:
                row=db.execute('SELECT * FROM dialogue_proposals WHERE id=?',(key,)).fetchone()
                if not row:raise Rejected('Proposition inconnue.')
                proposal=json.loads(row['body'])
                existing=db.execute('SELECT state FROM operations WHERE id=?',(row['operation_id'],)).fetchone()
            if existing:
                # Idempotent replay even after expiry, without changing parameters or rerunning work.
                result=self.store.get(row['operation_id'])
                self.record_outcome(key,result)
                return result
            if row['state']!='PROPOSED':raise Rejected('Proposition arrêtée ou restaurée : préparez une nouvelle demande.')
            if self.clock()>row['expires']:raise Rejected('Proposition expirée : relisez la demande.')
            if file_digest(self.store.context_path)!=row['context_hash']:raise Rejected('Le contexte a changé ; proposition à recalculer.')
            if self.store.project_revision(row['project'])!=row['revision']:raise Rejected('Le dossier a changé ; proposition à recalculer.')
            try:
                result=self.store.run({'operation_id':row['operation_id'],'project_id':row['project'],
                         'expected_revision':row['revision'],'params':proposal['params']},builder=builder)
            except Exception:
                try:self.record_outcome(key,self.store.get(row['operation_id']))
                except (Rejected,IntegrityError):pass
                raise
            self.record_outcome(key,result)
            return result

    def record_outcome(self,key,result):
        state={'READY':'COMPLETED','FAILED':'FAILED','INTERRUPTED':'INTERRUPTED','RUNNING':'IN_PROGRESS'}[result['state']]
        with self.store.connect() as db:
            db.execute('UPDATE dialogue_proposals SET state=?,outcome=? WHERE id=?',
                       (state,canonical({'operation_id':result['operation_id'],'state':result['state']}),key))
