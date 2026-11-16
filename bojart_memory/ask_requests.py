"""Durable local inference reservations; never retry an ambiguous provider call.

SQLite serializes short state changes. A separate OS lock identifies a live
owner without holding a database transaction during inference. Locks are not
part of Memory.backup: a restored in-flight request has an unknown outcome.
This contract requires one local filesystem, not NFS or multiple hosts.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

from .core import Memory, MemoryError, canonical, now, project_ok


_UNSET = object()

SCHEMA = '''CREATE TABLE IF NOT EXISTS agent_ask_requests(
    request_id TEXT PRIMARY KEY, session TEXT NOT NULL, project TEXT NOT NULL,
    question TEXT NOT NULL, fingerprint TEXT NOT NULL, owner TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('RUNNING','COMPLETED','FAILED','UNKNOWN')),
    phase TEXT NOT NULL CHECK(phase IN ('PREPARING','CALLING','TERMINAL')),
    response TEXT, reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    CHECK((state='COMPLETED') = (response IS NOT NULL)))'''


class AskRequestError(MemoryError):
    """Stable, non-sensitive request state for CLI/HTTP callers."""
    def __init__(self, code, request_id, state, message=None, *, reason=None):
        self.code, self.request_id, self.state = code, request_id, state
        self.reason = reason
        messages = {
            'IN_PROGRESS': 'Cette demande est encore en cours. Consulter son état avec le même identifiant.',
            'CONFLICT': 'Cet identifiant appartient à une autre question, session ou projet.',
            'FAILED': 'La demande a échoué avant tout appel de fournisseur. Une nouvelle demande explicite est nécessaire.',
            'UNKNOWN': "Résultat incertain : le fournisseur peut avoir été appelé. Aucune relance automatique n'est autorisée.",
            'NOT_FOUND': 'Demande inconnue pour cette session et ce projet.',
        }
        if reason == 'chat_not_configured':
            message = 'Conversation désactivée. Configurer un modèle Ollama local, puis créer une nouvelle demande explicite ; la recherche reste disponible.'
        elif reason == 'episode_input_too_large':
            message = 'Contexte et historique trop volumineux pour conserver cet échange. Aucun appel de conversation effectué ; une inférence de recherche peut déjà avoir eu lieu. Réduire le contexte avant une nouvelle demande explicite.'
        super().__init__(message or messages.get(code, 'État de demande indisponible.'))

    def to_dict(self):
        return {'code': self.code, 'state': self.state, 'request_id': self.request_id,
                'message': str(self), 'reason': self.reason, 'automatic_retry': False}


def validate_identity(request_id, session, project, question=_UNSET):
    project_ok(project)
    if not all(isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', v)
               for v in (session, request_id)):
        raise MemoryError('Référence de conversation invalide.')
    if question is not _UNSET and (not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000):
        raise MemoryError('Question hors limites.')


def fingerprint(session, project, question):
    return hashlib.sha256(canonical([session, project, question]).encode('utf-8')).hexdigest()


class OwnerLock:
    """Nonblocking byte lock, including separate handles in the same process."""
    def __init__(self, state, owner):
        if not re.fullmatch(r'[0-9a-f]{32}', owner):
            raise MemoryError('Propriétaire de demande invalide.')
        # Resolve the state first: 8.3 short names (Windows temp folders) or a
        # linked ancestor are not a redirection. Only the lock folder itself
        # must not be a link or junction.
        directory = Path(state).resolve() / '.ask-locks'
        directory.mkdir(exist_ok=True)
        if directory.resolve() != directory:
            raise MemoryError('Répertoire de verrous redirigé.')
        self.path = directory / (owner + '.lock')
        self.owner = owner
        self.fd = None

    def acquire(self, *, create):
        # Do not write byte 0: another handle may already lock it. Windows
        # explicitly permits locking a range beyond EOF (msvcrt docs).
        try:
            self.fd = os.open(self.path, os.O_RDWR | (os.O_CREAT | os.O_EXCL if create else 0), 0o600)
        except FileNotFoundError:
            return False
        try:
            if os.name == 'nt':
                import msvcrt
                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(self.fd)
            self.fd = None
            if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                return False
            raise
        return True

    def close(self):
        if self.fd is not None:
            # Closing the owning descriptor releases the OS lock, including
            # process termination. Keep the empty file to avoid unlink races.
            os.close(self.fd)
            self.fd = None


class AskRequests:
    def __init__(self, state):
        self.state = Path(state)

    @staticmethod
    def initialize(db):
        db.execute(SCHEMA)

    def _reconcile(self, db, row):
        if row['state'] != 'RUNNING':
            return row
        guard = OwnerLock(self.state, row['owner'])
        try:
            # Absent lock files occur after a normal snapshot restore. A lock
            # we can acquire belongs to a dead or interrupted worker.
            absent = not guard.path.exists()
            acquired = guard.acquire(create=False) if not absent else False
            if absent or acquired:
                db.execute("UPDATE agent_ask_requests SET state='UNKNOWN', phase='TERMINAL', reason='owner_lost_or_restored', updated_at=? WHERE request_id=? AND state='RUNNING' AND owner=?",
                           (now(), row['request_id'], row['owner']))
                return db.execute('SELECT * FROM agent_ask_requests WHERE request_id=?', (row['request_id'],)).fetchone()
            return row
        finally:
            guard.close()

    @staticmethod
    def _response(row):
        if row['state'] == 'COMPLETED':
            value = json.loads(row['response'])
            if not isinstance(value, dict) or not isinstance(value.get('answer'), str):
                raise MemoryError('Cache de réponse invalide.')
            return value
        raise AskRequestError('IN_PROGRESS' if row['state'] == 'RUNNING' else row['state'],
                              row['request_id'], row['state'], reason=row['reason'])

    @staticmethod
    def _legacy(db, request_id, session, project, question=None):
        old = db.execute('SELECT session,project,payload FROM agent_episodes WHERE id=?', ('chat-' + request_id,)).fetchone()
        if old is None:
            return None
        try:
            payload = json.loads(old['payload'])
            matches = old['session'] == session and old['project'] == project
            if question is not None:
                matches = matches and payload['question'] == question
            if not matches:
                raise AskRequestError('CONFLICT', request_id, 'CONFLICT')
            value = payload['response']
            if not isinstance(value, dict) or not isinstance(value.get('answer'), str):
                raise MemoryError('Cache de conversation historique invalide.')
            return value
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise MemoryError('Épisode de conversation historique invalide.') from exc

    def claim(self, request_id, session, project, question):
        validate_identity(request_id, session, project, question)
        owner = uuid.uuid4().hex
        guard = OwnerLock(self.state, owner)
        # Lock FIRST. A committed RUNNING row must never have an owner that
        # has not yet acquired its guard.
        if not guard.acquire(create=True):
            raise MemoryError('Verrou de nouvelle demande indisponible.')
        retained = False
        try:
            with Memory(self.state) as m, m.transaction():
                row = m.db.execute('SELECT * FROM agent_ask_requests WHERE request_id=?', (request_id,)).fetchone()
                if row:
                    if (row['session'], row['project'], row['question'], row['fingerprint']) != (session, project, question, fingerprint(session, project, question)):
                        raise AskRequestError('CONFLICT', request_id, 'CONFLICT')
                    row = self._reconcile(m.db, row)
                    # Return/raise AFTER commit, so owner-loss transitions
                    # are durable even when the caller receives an error.
                    existing = dict(row)
                else:
                    cached = self._legacy(m.db, request_id, session, project, question)
                    if cached is not None:
                        return None, cached
                    stamp = now()
                    m.db.execute('INSERT INTO agent_ask_requests VALUES(?,?,?,?,?,?,?, ?,NULL,NULL,?,?)',
                                 (request_id, session, project, question, fingerprint(session, project, question), owner, 'RUNNING', 'PREPARING', stamp, stamp))
                    existing = None
            if existing is not None:
                return None, self._response(existing)
            retained = True
            return guard, None
        finally:
            if not retained:
                guard.close()
                # A replay/failed claim must not leave one orphan per retry.
                # Check the database even after a failed commit: absence of an
                # acknowledgement is not proof the owner was never published.
                # O_EXCL above prevents another new owner from reusing this
                # filename while the short transaction performs this check.
                try:
                    with Memory(self.state) as m, m.transaction():
                        referenced = m.db.execute('SELECT 1 FROM agent_ask_requests WHERE owner=? LIMIT 1', (owner,)).fetchone()
                        if not referenced:
                            guard.path.unlink(missing_ok=True)
                except (OSError, MemoryError, sqlite3.DatabaseError):
                    # Inability to prove absence retains the harmless file.
                    pass

    def calling(self, request_id, owner):
        with Memory(self.state) as m, m.transaction():
            changed = m.db.execute("UPDATE agent_ask_requests SET phase='CALLING',updated_at=? WHERE request_id=? AND owner=? AND state='RUNNING' AND phase='PREPARING'", (now(), request_id, owner)).rowcount
            if changed != 1:
                raise AskRequestError('UNKNOWN', request_id, 'UNKNOWN')

    def complete(self, request_id, owner, payload):
        # Strict JSON round-trip rejects NaN/Infinity and unserializable values.
        # Preserve the existing episode size bound and store exactly what is
        # returned, so every replay is equal to the initial successful result.
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(text) > 64000:
            raise MemoryError('Épisode trop volumineux.')
        payload = json.loads(text)
        response = payload.get('response')
        if not isinstance(response, dict) or not isinstance(response.get('answer'), str) or not response['answer'].strip():
            raise MemoryError('Réponse locale invalide.')
        with Memory(self.state) as m, m.transaction():
            row = m.db.execute('SELECT * FROM agent_ask_requests WHERE request_id=?', (request_id,)).fetchone()
            if not row or row['owner'] != owner or row['state'] != 'RUNNING' or row['phase'] != 'CALLING':
                raise AskRequestError('UNKNOWN', request_id, 'UNKNOWN')
            if payload.get('question') != row['question']:
                raise MemoryError('Question de réponse incohérente.')
            fp = hashlib.sha256(canonical([row['session'], row['project'], payload]).encode('utf-8')).hexdigest()
            m.db.execute('INSERT INTO agent_episodes VALUES(?,?,?,?,?,?)',
                         ('chat-' + request_id, row['session'], row['project'], canonical(payload), fp, now()))
            m.db.execute("UPDATE agent_ask_requests SET state='COMPLETED',phase='TERMINAL',response=?,updated_at=? WHERE request_id=? AND owner=? AND state='RUNNING'",
                         (canonical(response), now(), request_id, owner))
        return response

    def failed(self, request_id, owner, *, reason=None):
        if reason not in (None, 'chat_not_configured', 'episode_input_too_large'):
            raise MemoryError('Motif de demande invalide.')
        with Memory(self.state) as m, m.transaction():
            m.db.execute("""UPDATE agent_ask_requests SET state=CASE WHEN phase='PREPARING' THEN 'FAILED' ELSE 'UNKNOWN' END,
                reason=COALESCE(?,CASE WHEN phase='PREPARING' THEN 'preparation_failed' ELSE 'provider_or_result_uncertain' END),
                phase='TERMINAL',updated_at=? WHERE request_id=? AND owner=? AND state='RUNNING'""", (reason, now(), request_id, owner))

    def status(self, request_id, session, project):
        validate_identity(request_id, session, project)
        with Memory(self.state) as m, m.transaction():
            row = m.db.execute('SELECT * FROM agent_ask_requests WHERE request_id=?', (request_id,)).fetchone()
            if row is None:
                cached = self._legacy(m.db, request_id, session, project)
                if cached is None:
                    raise AskRequestError('NOT_FOUND', request_id, 'NOT_FOUND')
                return {'request_id': request_id, 'state': 'COMPLETED', 'response': cached, 'legacy': True, 'automatic_retry': False}
            if row['session'] != session or row['project'] != project:
                raise AskRequestError('CONFLICT', request_id, 'CONFLICT')
            row = dict(self._reconcile(m.db, row))
        result = {key: row[key] for key in ('request_id', 'state', 'phase', 'reason', 'created_at', 'updated_at')}
        result['automatic_retry'] = False
        if row['state'] == 'COMPLETED':
            result['response'] = self._response(row)
        return result
