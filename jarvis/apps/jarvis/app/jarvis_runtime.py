"""M06: persistent, bounded orchestration of visual turns, with optional Jev.

The turn journal and LangGraph checkpoints live in missions.sqlite3, so M05
snapshots include both without a sixth database. No autonomous background resume.
The metadata lock orders cancellation/dispatch without waiting for long CAD jobs.
SQLite writer reservations provide the common boundary with global snapshots.
"""
from __future__ import annotations
import hashlib, json, re, sqlite3, threading, time
from typing import TypedDict
from core import Rejected, canonical
from display_contracts import ROUTES, norm
from control_tower import safe_id
from jev_decider import JevDecider
from sqlite_sessions import SQLiteSessions

COMMANDS = {
    'model': ('Affiche le modèle à droite', 'Afficher le modèle sélectionné sur la vue création'),
    'sources': ('Montre les sources au centre', 'Afficher la bibliothèque des sources au centre'),
    'studio': ('Ouvre le studio', 'Afficher la bibliothèque Studio à droite'),
    'planning': ('Affiche le planning à gauche', 'Afficher le planning démonstratif à gauche'),
    'workspace': ('Montre les dossiers au centre', 'Afficher les dossiers et les sauvegardes au centre'),
    'growth': ('Ouvre les contenus à droite', 'Afficher les préparations éditoriales à droite, sans publier'),
    'knowledge': ('Ouvre la base métier au centre', 'Afficher la base documentaire métier au centre'),
    'cad': ('Ouvre la conception au centre', 'Afficher le poste de conception du dossier au centre'),
    'silence': ('Arrête de parler', 'Interrompre seulement la réponse vocale, jamais une machine'),
    'tower': ('Ouvre la tour de contrôle', 'Composer les trois vues du dossier : planning démonstratif à gauche, dossiers au centre, modèle sélectionné ou Studio à droite'),
}
CATALOG = {key: value[1] for key, value in COMMANDS.items()}
ALIASES = {norm(value[0]): key for key, value in COMMANDS.items()}
ALIASES.update({'montre le modele a droite':'model', 'interromps ta reponse':'silence',
                'ouvre les dossiers':'workspace', 'ouvre la base metier':'knowledge',
                'ouvre la conception':'cad', 'ouvre les contenus':'growth',
                'affiche la tour de controle':'tower', 'affiche tout':'tower'})
# Exact, bounded phrases: a negation or an additional action is never stripped.
for _label, _choice in {'atelier':'planning', 'planning':'planning', 'dossiers':'workspace',
                        'studio':'studio', 'contenus':'growth', 'conception':'cad',
                        'base métier':'knowledge'}.items():
    for _verb in ('Affiche', 'Montre', 'Ouvre'):
        for _noun in ('le dashboard', 'le tableau de bord'):
            ALIASES[norm(f'{_verb} {_noun} {_label}')] = _choice
ALIASES[norm('Affiche les trois dashboards')] = 'tower'
ALIASES[norm('Affiche les trois tableaux de bord')] = 'tower'
AMBIGUOUS_DASHBOARDS = {norm(s) for s in (
    'Affiche le dashboard', 'Ouvre le dashboard', 'Montre le dashboard',
    'Affiche un des dashboards', 'Affiche le tableau de bord')}
VOICE_CONFIRM = ('Confirme cet affichage', 'Je confirme cet affichage')
VOICE_CANCEL = ('Annule cette proposition', 'Annule cet affichage')
TERMINAL = {'CLARIFY', 'STALE', 'CANCELLED', 'CANCELLED_AFTER_DISPATCH', 'QUEUED', 'FAILED', 'RESTORED'}


class TurnState(TypedDict, total=False):
    request_id: str
    decision: dict
    status: str
    message: str


class VoiceLease:
    """One browser audio owner; expires after a lost browser, never steals a lease."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.owner = None
        self.expires = 0.0

    def owns(self, owner):
        with self.lock:
            return self.owner == owner and self.expires > self.clock()

    def claim(self, owner, release=False):
        safe_id(owner)
        with self.lock:
            if release:
                if self.owner == owner: self.owner = None; self.expires = 0
                return {'released': True}
            if self.expires > self.clock() and self.owner != owner:
                raise Rejected('Le microphone est réservé par une autre fenêtre. Terminez cette prise.')
            self.owner = owner; self.expires = self.clock()+30
            return {'owned': True, 'ttl_seconds': 30}


class JarvisRuntime:
    def __init__(self, server, decider=None, *, reuse_connections=None, checkpoint_durability='exit'):
        if checkpoint_durability not in ('sync', 'exit'):
            raise ValueError('Unsupported checkpoint durability.')
        if reuse_connections is not None and type(reuse_connections) is not bool:
            raise ValueError('reuse_connections must be None, True or False.')
        self.server = server
        self.store = server.store
        self.decider = decider or JevDecider()
        self.voice_lease = VoiceLease()
        self.run_lock = threading.Lock()
        self.lock = threading.RLock()
        self.graph = None
        self.connection = None
        self.checkpoint_durability = checkpoint_durability
        self._reuse_connections = reuse_connections
        self._sessions = []
        owners = [(self.store, self.store.dbpath, True, True),
                  (server.display, server.display.path, False, False),
                  (server.tower, server.tower.path, True, False)]
        if any(getattr(owner, '_command_sessions', None) is not None for owner, *_ in owners):
            raise Rejected('Un runtime possède déjà ces connexions. Fermez-le avant la reprise.')
        if reuse_connections is not False:
            for owner, path, rows, foreign_keys in owners:
                pool = SQLiteSessions(path, rows=rows, foreign_keys=foreign_keys)
                owner._command_sessions = pool
                self._sessions.append((owner, pool))
        try:
            self._initialize()
        except BaseException:
            self.close()
            raise

    def _initialize(self):
        with self.store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS jarvis_turns (
                request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
                created REAL NOT NULL, updated REAL NOT NULL, status TEXT NOT NULL,
                decision TEXT, result TEXT, approved INTEGER NOT NULL DEFAULT 0,
                cancelled INTEGER NOT NULL DEFAULT 0)''')
            columns={r[1] for r in db.execute('PRAGMA table_info(jarvis_turns)')}
            for column,definition in [('plan','TEXT'),('approval_source',"TEXT NOT NULL DEFAULT ''")]:
                if column not in columns:db.execute('ALTER TABLE jarvis_turns ADD COLUMN '+column+' '+definition)
            db.execute("UPDATE jarvis_turns SET status='INTERRUPTED' WHERE status='RUNNING'")
        try:
            from langgraph.graph import StateGraph, START, END
            from langgraph.checkpoint.sqlite import SqliteSaver
            from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        except ImportError:
            # A missing optional package must not break the recovered workshop.
            self.graph_status = 'missing_dependency'
            # Auto mode keeps the original connection lifetime for rules fallback.
            # Windows trials did not qualify its pooled tail latency. Explicit
            # True is an experimental constructor override, never an HTTP option.
            if self._reuse_connections is None:self._release_sessions()
        else:
            self.connection = sqlite3.connect(self.store.dbpath, check_same_thread=False, timeout=10)
            saver = SqliteSaver(self.connection, serde=JsonPlusSerializer(
                pickle_fallback=False, allowed_msgpack_modules=[], allowed_json_modules=[]))
            # Initialize schema/WAL before the server accepts concurrent writers.
            # Use the public read API; do not call the saver's internal setup().
            saver.get_tuple({'configurable':{'thread_id':'boj-runtime-initialize'}})
            graph = StateGraph(TurnState)
            graph.add_node('route', self._route)
            graph.add_node('guard', self._guard)
            graph.add_node('dispatch', self._dispatch)
            graph.add_node('receipt', self._receipt)
            graph.add_edge(START, 'route'); graph.add_edge('route', 'guard')
            graph.add_conditional_edges('guard', lambda s: 'dispatch' if s['status']=='ACCEPTED' else 'receipt',
                                        {'dispatch':'dispatch','receipt':'receipt'})
            graph.add_edge('dispatch', 'receipt'); graph.add_edge('receipt', END)
            self.graph = graph.compile(checkpointer=saver)
            self.graph_status = 'sqlite_ready'

    def close(self):
        with self.run_lock:
            if self.connection: self.connection.close(); self.connection = None
            self._release_sessions()

    def _release_sessions(self):
        for owner, pool in self._sessions:
            if getattr(owner, '_command_sessions', None) is pool:
                del owner._command_sessions
            pool.close()
        self._sessions.clear()

    def status(self):
        return {'schema':'bojart.jarvis.m07.v1', 'langgraph':self.graph_status,
                'jev':self.decider.status(), 'voice':self.server.voice.status(),
                'voice_transport':'bounded_local_wav', 'continuous_conversation':False,
                'audio_owners_max':1, 'display_transport':'sse_with_poll_fallback',
                'physical_commands':False, 'publication':False,
                'voice_confirmation':{'approve':list(VOICE_CONFIRM),'cancel':list(VOICE_CANCEL),'scope':'current_visual_proposal'},
                'endpointing':'optional_browser_energy_gate_unqualified',
                'commands':[{'id':k,'text':v[0],'description':v[1]} for k,v in COMMANDS.items()]}

    def _row(self, request_id):
        safe_id(request_id)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM jarvis_turns WHERE request_id=?',(request_id,)).fetchone()
        if not row: raise Rejected('Tour inconnu.')
        return dict(row)

    def _write(self, request_id, **fields):
        with self.store.connect() as db:
            db.execute('UPDATE jarvis_turns SET '+','.join(k+'=?' for k in fields)+',updated=? WHERE request_id=?',
                       (*fields.values(),time.time(),request_id))

    def submit(self, data):
        fields={'request_id','client_id','project_id','revision','text','operation_id','source'}
        if not isinstance(data,dict) or set(data) not in (fields,fields|{'context_sha256'}): raise Rejected('Contrat de tour invalide.')
        for key in ('request_id','client_id'): safe_id(data[key])
        self.store.require_project(data['project_id']); norm(data['text'])
        if type(data['revision']) is not int or data['revision'] < 0: raise Rejected('Révision invalide.')
        if data['source'] not in ('typed','voice'): raise Rejected('Source du tour invalide.')
        if data['operation_id'] is not None: safe_id(data['operation_id'])
        if 'context_sha256' in data and (not isinstance(data['context_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',data['context_sha256'])):
            raise Rejected('Empreinte du contexte invalide.')
        fp=hashlib.sha256(canonical(data).encode()).hexdigest()
        with self.lock:
            if self.server.workspace.closing: raise Rejected('Fermeture en cours.')
            with self.store.connect() as db:
                old=db.execute('SELECT fingerprint FROM jarvis_turns WHERE request_id=?',(data['request_id'],)).fetchone()
                if old and old[0]!=fp: raise Rejected('Référence déjà utilisée pour une autre demande.')
                if not old:
                    frozen={**data,'context_sha256':data.get('context_sha256',self.server.display.context_hash())}
                    db.execute('INSERT INTO jarvis_turns(request_id,fingerprint,payload,created,updated,status) VALUES(?,?,?,?,?,?)',
                               (data['request_id'],fp,canonical(frozen),time.time(),time.time(),'NEW'))
        return self._run(data['request_id'])

    def confirm(self, request_id, client_id, *, source='button'):
        with self.lock:
            row=self._row(request_id)
            if json.loads(row['payload'])['client_id']!=client_id: raise Rejected('Fenêtre de confirmation différente.')
            if row['status'] not in ('AWAITING_CONFIRMATION','QUEUED'): raise Rejected('Aucune proposition à confirmer.')
            self._write(request_id,approved=1,approval_source=source)
        return self._run(request_id, confirm=True)

    def confirm_speech(self, request_id, client_id, project_id, text):
        """Explicit phrase, bound to the one visual proposal shown in this window."""
        with self.lock:
            self.store.require_project(project_id)
            row=self._row(request_id);data=json.loads(row['payload'])
            if data['project_id']!=project_id or data['client_id']!=client_id:
                raise Rejected('La proposition appartient à un autre dossier ou une autre fenêtre.')
            if row['status'] not in ('AWAITING_CONFIRMATION','QUEUED') or row['cancelled']:
                raise Rejected('Aucune proposition visuelle active à confirmer.')
            phrase=norm(text)
            if phrase in {norm(s) for s in VOICE_CANCEL}:return self.cancel(request_id,client_id)
            if phrase not in {norm(s) for s in VOICE_CONFIRM}:
                raise Rejected('Dites « Confirme cet affichage » ou « Annule cette proposition ».')
        return self.confirm(request_id,client_id,source='voice_explicit')

    def _plan(self, row):
        if row['plan']:return json.loads(row['plan'])
        data=json.loads(row['payload']);decision=json.loads(row['decision'])
        choice=decision['choice']
        if choice=='tower':
            entries=[('atelier',COMMANDS['planning'][0],None),('pilotage',COMMANDS['workspace'][0],None),
                     ('creation',COMMANDS['model' if data['operation_id'] else 'studio'][0],data['operation_id'])]
        else:entries=[(None,COMMANDS[choice][0],data['operation_id'] if choice=='model' else None)]
        plan=[]
        for role,command,operation in entries:
            rid='scene_'+hashlib.sha256((data['request_id']+':'+role).encode()).hexdigest()[:32] if role else data['request_id']
            plan.append({'request_id':rid,'turn_id':data['request_id'],'project_id':data['project_id'],
                         'revision':data['revision'],'command':command,'operation_id':operation})
        self._write(data['request_id'],plan=canonical(plan))
        return plan

    @staticmethod
    def _ids(row):
        return [p['request_id'] for p in json.loads(row['plan'])] if row['plan'] else [row['request_id']]

    def cancel(self, request_id, client_id):
        with self.lock:
            row=self._row(request_id)
            if json.loads(row['payload'])['client_id']!=client_id: raise Rejected('Fenêtre de commande différente.')
            ids=self._ids(row)
            with self.server.tower.lock, self.server.tower.db() as db:
                count=0
                for rid in ids:
                    if db.execute('SELECT 1 FROM commands WHERE request_id=?',(rid,)).fetchone():count+=1
                    db.execute("UPDATE commands SET state='cancelled',updated=?,message='Annulation demandée.' WHERE request_id=? AND state IN ('queued','delivered')",(time.time(),rid))
            state='CANCELLED_AFTER_DISPATCH' if count else 'CANCELLED'
            self._write(request_id,cancelled=1,status=state,result=canonical({'status':state,
                'message':'Tour annulé. Un affichage déjà commencé peut rester visible.' if count else 'Tour annulé avant distribution.'}))
        self.server.events.notify()
        return self.get(request_id)

    def get(self, request_id):
        row=self._row(request_id)
        result=json.loads(row['result'] or '{}')
        with self.server.tower.db() as db:
            rows=[dict(r) for rid in self._ids(row) for r in db.execute('SELECT request_id,state,updated,target_role,message FROM commands WHERE request_id=?',(rid,))]
        if len(self._ids(row))>1:
            total=len(self._ids(row));rendered=sum(r['state']=='rendered' for r in rows)
            failed=any(r['state'] in ('failed','stale','cancelled','cancelled_restore') for r in rows)
            command={'state':'rendered' if rendered==total else 'failed' if failed else 'in_progress',
                     'target_role':'trois vues','updated':max((r['updated'] for r in rows),default=row['updated']),
                     'message':str(rendered)+'/'+str(total)+' vues affichées.', 'rendered_views':rendered,'total_views':total}
        else:command=rows[0] if rows else None
        return {**result,'request_id':request_id,'status':row['status'],
                'decision':json.loads(row['decision']) if row['decision'] and row['decision']!='pending' else None,
                'display':command,'displays':rows,'approval_source':row['approval_source'],
                'elapsed_to_display_ms':round((command['updated']-row['created'])*1000,1) if command and command['state']=='rendered' else None,
                'physical_effect':False}

    def _run(self, request_id, confirm=False):
        if not self.run_lock.acquire(blocking=False): return {**self.get(request_id),'busy':True}
        try:
            with self.lock:
                row=self._row(request_id)
                if row['status'] in TERMINAL or (row['status']=='AWAITING_CONFIRMATION' and not confirm): return self.get(request_id)
                self._write(request_id,status='RUNNING')
            state={'request_id':request_id}
            if self.graph:
                # Explicitly disable external tracing even when a host has global LangSmith settings.
                from langsmith import tracing_context
                with tracing_context(enabled=False):
                    # Recovery replays the independently committed business journal:
                    # input, provider-pending marker, decision, plan and receipts.
                    # Intermediate graph state is deliberately not a recovery source.
                    self.graph.invoke(state,{'configurable':{'thread_id':'boj-m06-'+request_id},'recursion_limit':12},durability=self.checkpoint_durability)
            else:
                state.update(self._route(state));state.update(self._guard(state))
                if state['status']=='ACCEPTED':state.update(self._dispatch(state))
                self._receipt(state)
            return self.get(request_id)
        except Exception:
            # Keep frozen input and the provider decision for explicit reconciliation.
            # Never claim a failed HTTP response means no visual effect occurred.
            row=self._row(request_id)
            if not row['cancelled']:
                self._write(request_id,status='INTERRUPTED',result=canonical({'message':'Traitement interrompu. Reprendre cette référence pour vérifier son résultat.'}))
            return self.get(request_id)
        finally:self.run_lock.release()

    def _route(self, state):
        row=self._row(state['request_id']); data=json.loads(row['payload'])
        if row['cancelled'] or data['revision']!=self.store.project_revision(data['project_id']) or data['context_sha256']!=self.server.display.context_hash() or time.time()-row['created']>120:
            return {'decision':{'source':'local','choice':'clarify','called':False,'reason':'stale_or_cancelled'}}
        if row['decision']:
            decision=json.loads(row['decision']) if row['decision']!='pending' else {
                'source':'local','choice':'clarify','called':False,'reason':'provider_outcome_unknown_no_retry'}
            if row['decision']=='pending':self._write(state['request_id'],decision=canonical(decision))
        else:
            key=ALIASES.get(norm(data['text']))
            if key: decision={'source':'local','choice':key,'called':False,'reason':'known_command'}
            elif norm(data['text']) in AMBIGUOUS_DASHBOARDS:
                decision={'source':'local','choice':'clarify','called':False,'reason':'dashboard_unspecified'}
            elif row['cancelled']: decision={'source':'local','choice':'clarify','called':False,'reason':'cancelled'}
            else:
                # Persist BEFORE the remote call: a crash will never auto-repeat it.
                self._write(state['request_id'],decision='pending')
                decision=self.decider.decide(data,CATALOG)
            self._write(state['request_id'],decision=canonical(decision))
        return {'decision':decision}

    def _guard(self, state):
        with self.lock:
            row=self._row(state['request_id']);data=json.loads(row['payload'])
            if row['cancelled']: return {'status':row['status'],'message':'Tour annulé.'}
            if self.server.workspace.closing: return {'status':'CANCELLED','message':'Fermeture en cours.'}
            if data['revision']!=self.store.project_revision(data['project_id']) or data['context_sha256']!=self.server.display.context_hash() or time.time()-row['created']>120:
                return {'status':'STALE','message':'Le dossier, le contexte ou le délai a changé. Reformulez la commande.'}
            choice=state['decision']['choice']
            if choice not in COMMANDS:
                if state['decision'].get('reason')=='dashboard_unspecified':
                    return {'status':'CLARIFY','message':'Quel tableau de bord : atelier (planning démonstratif), dossiers, Studio, contenus, conception ou base métier ?'}
                return {'status':'CLARIFY','message':'Commande non reconnue avec certitude. Choisissez un des ordres proposés.'}
            if choice=='model' and not data['operation_id']:
                return {'status':'CLARIFY','message':'Sélectionnez le modèle à afficher dans ce dossier.'}
            if state['decision']['source']=='jev' and not row['approved']:
                return {'status':'AWAITING_CONFIRMATION','message':'Jev propose : '+COMMANDS[choice][0]+'. Confirmez cet affichage.'}
            return {'status':'ACCEPTED','message':'Commande vérifiée.'}

    def _dispatch(self, state):
        with self.lock:
            guard=self._guard(state)
            if guard['status']!='ACCEPTED':return guard
            row=self._row(state['request_id']); data=json.loads(row['payload']);choice=state['decision']['choice']
            try:
                plan=self._plan(row)
                # Validate every component before distributing the first one.
                for entry in plan:self.server.display.prepare(entry)
            except Rejected as exc:return {'status':'FAILED','message':str(exc)}
            try:
                for entry in plan:self.server.tower.dispatch(entry['request_id'])
            except Exception:
                self.server.events.notify()
                return {'status':'INTERRUPTED','message':'Distribution incomplète. Reprendre cette référence pour réconcilier les vues.'}
        self.server.events.notify()
        return {'status':'QUEUED','message':('Composition envoyée aux trois vues.' if choice=='tower' else 'Commande envoyée à la vue.')+' En attente des reçus d’affichage.'}

    def _receipt(self, state):
        with self.lock:
            row=self._row(state['request_id'])
            if not row['cancelled']:
                self._write(state['request_id'],status=state['status'],result=canonical({
                    'status':state['status'],'message':state['message'],'engine':self.graph_status}))
        self.server.events.notify()
        return {}
