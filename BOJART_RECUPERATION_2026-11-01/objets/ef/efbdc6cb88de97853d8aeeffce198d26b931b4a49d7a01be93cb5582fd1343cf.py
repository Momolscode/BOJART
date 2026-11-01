"""BOJ.ART M04: durable, *visual-only* command routing to authenticated local browser views.

This is NOT a physical monitor driver, a speech recognizer, or a printer controller.
A browser ACK is an application-level receipt, not proof of physical display visibility.
"""
from __future__ import annotations
import json, re, secrets, sqlite3, threading, time
from contextlib import closing, contextmanager
from pathlib import Path
from core import Rejected, IntegrityError
from display_contracts import DisplayProposals

ROLES = ('atelier', 'pilotage', 'creation')
ACTIONS = {'show_model': {'creation'}, 'show_sources': {'pilotage','creation'},
           'show_planning_demo': {'atelier'}, 'interrupt_speech': {'pilotage'}}
ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,96}$')
HEARTBEAT_TTL = 20.0
DELIVERY_LEASE_TTL = 25.0


def safe_id(value):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise Rejected('Identifiant invalide.')
    return value


class ControlTower:
    def __init__(self, store, display: DisplayProposals):
        self.store, self.display = store, display
        self.path = Path(store.root) / 'control-tower.sqlite3'
        self.lock = threading.RLock()
        with self.db() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS screens (
                screen_id TEXT PRIMARY KEY, role TEXT NOT NULL, created REAL NOT NULL,
                last_seen REAL NOT NULL, client_label TEXT NOT NULL)''')
            con.execute('''CREATE TABLE IF NOT EXISTS commands (
                request_id TEXT PRIMARY KEY, proposal TEXT NOT NULL, target_role TEXT NOT NULL,
                state TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
                screen_id TEXT, message TEXT NOT NULL DEFAULT '')''')
            con.execute('CREATE INDEX IF NOT EXISTS command_target ON commands(target_role,state,created)')
            for table in ('screens','commands'):
                if 'project_id' not in {r[1] for r in con.execute('PRAGMA table_info('+table+')')}:
                    con.execute("ALTER TABLE "+table+" ADD COLUMN project_id TEXT NOT NULL DEFAULT 'BOJ-PILOTE-001'")

    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as con:
            con.row_factory = sqlite3.Row
            with con:
                yield con

    def pair(self, role, label='Vue locale', project_id='BOJ-PILOTE-001'):
        self.store.require_project(project_id)
        if role not in ROLES: raise Rejected('Rôle d’écran inconnu.')
        if not isinstance(label, str) or not 1 <= len(label) <= 50 or any(ord(c) < 32 for c in label):
            raise Rejected('Nom de vue invalide.')
        screen_id = secrets.token_urlsafe(24)
        now = time.time()
        with self.lock, self.db() as con:
            active = con.execute('SELECT COUNT(*) FROM screens WHERE role=? AND project_id=? AND last_seen>?',
                                 (role, project_id, now-HEARTBEAT_TTL)).fetchone()[0]
            if active >= 3: raise Rejected('Trop de vues actives pour ce rôle.')
            # Multiple local views per role are allowed, but bounded.
            con.execute('INSERT INTO screens(screen_id,role,created,last_seen,client_label,project_id) VALUES(?,?,?,?,?,?)', (screen_id, role, now, now, label, project_id))
        return {'screen_id': screen_id, 'role': role, 'project_id':project_id, 'paired': True,
                'scope': 'onglet navigateur local ; moniteur physique non identifié'}

    def screen(self, screen_id):
        safe_id(screen_id)
        with self.db() as con:
            row = con.execute('SELECT * FROM screens WHERE screen_id=?', (screen_id,)).fetchone()
        if not row: raise Rejected('Vue non appairée.')
        return dict(row)

    def heartbeat(self, screen_id):
        screen = self.screen(screen_id)
        now = time.time()
        with self.lock, self.db() as con:
            con.execute('UPDATE screens SET last_seen=? WHERE screen_id=?', (now, screen_id))
        return {'role': screen['role'], 'screen_id': screen_id, 'online': True}

    def status(self, project_id=None):
        if project_id is not None:self.store.require_project(project_id)
        now = time.time()
        with self.db() as con:
            screens = [dict(r) for r in con.execute('SELECT * FROM screens WHERE (? IS NULL OR project_id=?) AND last_seen>?', (project_id,project_id,now-HEARTBEAT_TTL))]
            commands = [dict(r) for r in con.execute('SELECT * FROM commands WHERE (? IS NULL OR project_id=?) ORDER BY created DESC LIMIT 25',(project_id,project_id))]
        counts = {role: sum(s['role'] == role and now - s['last_seen'] <= HEARTBEAT_TTL for s in screens) for role in ROLES}
        return {'schema': 'bojart.tower.v1', 'roles': counts,
                'browser_views_connected': sum(counts.values()), 'physical_monitor_mapping_verified': False,
                'voice_connected': False, 'jev_connected': False, 'langgraph_connected': False,
                'printer_commands_enabled': False, 'publication_enabled': False,
                'commands': [{'request_id': c['request_id'], 'project_id':c['project_id'], 'target_role': c['target_role'],
                              'state': c['state'], 'message': c['message'], 'updated': c['updated']} for c in commands],
                'scope': 'Régie d’onglets navigateur locaux, pas encore de moniteurs physiques.'}

    def _proposal(self, request_id):
        safe_id(request_id)
        with self.display.db() as con:
            row = con.execute('SELECT payload FROM proposals WHERE request_id=?', (request_id,)).fetchone()
        if not row: raise Rejected('Proposition inconnue : préparer une commande avant de l’envoyer.')
        proposal = json.loads(row[0])
        if proposal['action'] not in ACTIONS or proposal['target_role'] not in ACTIONS[proposal['action']]:
            raise Rejected('Action ou écran non autorisé.')
        if proposal.get('physical_commands') or proposal.get('executed'):
            raise Rejected('Seules les propositions d’affichage sont admises.')
        return proposal

    def dispatch(self, request_id):
        proposal = self._proposal(request_id)
        stale_after_commit = False
        with self.lock, self.db() as con:
            row = con.execute('SELECT * FROM commands WHERE request_id=?', (request_id,)).fetchone()
            if row:
                # A repeated request cannot dispatch a second independent operation.
                stored = json.loads(row['proposal'])
                if stored != proposal: raise IntegrityError('Proposition modifiée après l’envoi.')
                return {'request_id': request_id, 'state': row['state'], 'replayed': True,
                        'target_role': row['target_role'], 'message': row['message']}
            if not self.display.is_current(proposal):
                raise Rejected('Proposition périmée : dossier, référence ou contexte modifié.')
            now = time.time()
            con.execute('INSERT INTO commands(request_id,proposal,target_role,state,created,updated,project_id) VALUES(?,?,?,?,?,?,?)',
                        (request_id, json.dumps(proposal, ensure_ascii=False, sort_keys=True), proposal['target_role'], 'queued', now, now,proposal['project_id']))
        return {'request_id': request_id, 'state': 'queued', 'replayed': False,
                'target_role': proposal['target_role'], 'executed': False,
                'message': 'Commande visuelle en file ; pas encore affichée.'}

    def poll(self, screen_id):
        screen = self.screen(screen_id)
        now = time.time()
        with self.lock, self.db() as con:
            con.execute('UPDATE screens SET last_seen=? WHERE screen_id=?', (now, screen_id))
            # A lost browser must not hold a display command forever.
            con.execute('''UPDATE commands SET state='queued',screen_id=NULL,updated=?,
                           message='Vue perdue ; reprise de distribution possible.'
                           WHERE state='delivered' AND updated<? AND screen_id IN
                           (SELECT screen_id FROM screens WHERE last_seen<?)''',
                        (now, now-DELIVERY_LEASE_TTL, now-HEARTBEAT_TTL))
            rows = con.execute('''SELECT * FROM commands WHERE target_role=? AND project_id=? AND state IN ('queued','delivered')
                                  ORDER BY created LIMIT 30''', (screen['role'],screen['project_id'])).fetchall()
            for row in rows:
                # Once delivered to one browser view, do not duplicate across other tabs.
                if row['state'] == 'delivered' and row['screen_id'] != screen_id:
                    continue
                p = json.loads(row['proposal'])
                if not self.display.is_current(p):
                    con.execute('UPDATE commands SET state=?,updated=?,message=? WHERE request_id=?',
                                ('stale', now, 'Révision ou fichier modifié avant affichage.', row['request_id']))
                    continue
                if row['state'] == 'queued':
                    con.execute('UPDATE commands SET state=?,screen_id=?,updated=? WHERE request_id=?',
                                ('delivered', screen_id, now, row['request_id']))
                return {'screen_id': screen_id, 'command': {
                    'request_id': row['request_id'], 'action': p['action'], 'target_role': p['target_role'],
                    'asset': p['asset'], 'data_status': p['data_status'], 'project_id': p['project_id'],
                    'revision': p['revision'], 'state': 'delivered'}}
        return {'screen_id': screen_id, 'command': None}

    def ack(self, screen_id, request_id, outcome, message):
        self.screen(screen_id); safe_id(request_id)
        if outcome not in ('rendered', 'failed'): raise Rejected('État d’affichage invalide.')
        if not isinstance(message, str) or len(message) > 200 or any(ord(c) < 32 for c in message):
            raise Rejected('Message invalide.')
        stale_after_commit = False
        with self.lock, self.db() as con:
            row = con.execute('SELECT * FROM commands WHERE request_id=?', (request_id,)).fetchone()
            if not row or row['screen_id'] != screen_id: raise Rejected('Ce navigateur ne possède pas cette commande.')
            if row['state'] in ('rendered', 'failed'):
                if row['state'] != outcome: raise Rejected('Accusé déjà enregistré avec un autre état.')
                return {'request_id': request_id, 'state': outcome, 'replayed': True}
            if row['state'] != 'delivered': raise Rejected('Commande non distribuée.')
            proposal = json.loads(row['proposal'])
            if not self.display.is_current(proposal):
                con.execute('UPDATE commands SET state=?,updated=?,message=? WHERE request_id=?',
                            ('stale', time.time(), 'Contexte modifié avant l’accusé.', request_id))
                stale_after_commit = True
            else:
                con.execute('UPDATE commands SET state=?,updated=?,message=? WHERE request_id=?',
                            (outcome, time.time(), message, request_id))
        if stale_after_commit: raise Rejected('Révision périmée : accusé refusé.')
        return {'request_id': request_id, 'state': outcome, 'replayed': False,
                'proof_scope': 'déclaration du navigateur ; écran physique non certifié'}
