"""Agent memory routes within Jarvis' authenticated loopback-only HTTP service."""
import json
import sqlite3
import uuid
from urllib.parse import parse_qs
from .agent import AgentMemory
from .core import Memory, MemoryError

GETS = {'/memory.css', '/api/memory/recall', '/api/memory/context', '/api/memory/facts', '/api/memory/status'}
POSTS = {'/api/memory/note', '/api/memory/ask', '/api/memory/reindex', '/api/memory/backup'}


def get(h, parsed, app):
    if not h.check_host(): return
    if not h.authorized(): return h.j({'error': 'Session locale requise.'}, 401)
    try:
        if parsed.path == '/memory.css': return h.response(200, (app / 'memory.css').read_bytes(), 'text/css; charset=utf-8')
        q = parse_qs(parsed.query, keep_blank_values=True)
        if set(q) - {'q', 'project'} or any(len(v) != 1 for v in q.values()):
            raise MemoryError('Paramètres invalides.')
        m = AgentMemory(); project = q.get('project', ['bojart.jarvis'])[0]
        if parsed.path.endswith('/status'): result = m.status()
        elif parsed.path.endswith('/facts'): result = {'facts': m.facts(project)}
        else:
            fn = m.context if parsed.path.endswith('/context') else m.search
            result = fn(q.get('q', [''])[0], project)
        return h.j(result)
    except (MemoryError, ValueError, TypeError) as e: return h.j({'error': str(e)}, 400)
    except (OSError, sqlite3.Error): return h.j({'error': 'Mémoire locale indisponible.'}, 503)


def post(h):
    if not h.check_host(): return
    if not h.authorized(): return h.j({'error': 'Session locale requise.'}, 401)
    if h.headers.get('Origin') != h.server.origin: return h.j({'error': 'Origine refusée.'}, 403)
    if h.headers.get('Transfer-Encoding'): return h.j({'error': 'Encodage refusé.'}, 400)
    if h.headers.get_content_type() != 'application/json': return h.j({'error': 'JSON requis.'}, 415)
    try:
        n = int(h.headers.get('Content-Length', '-1'))
        if not 0 < n <= 16000: return h.j({'error': 'Requête hors limites.'}, 413)
        raw = h.rfile.read(n)
        if len(raw) != n: raise MemoryError('Requête incomplète.')
        def unique(pairs):
            d = {}
            for k, v in pairs:
                if k in d: raise MemoryError('Clé dupliquée.')
                d[k] = v
            return d
        data = json.loads(raw, object_pairs_hook=unique)
        fields = {'/api/memory/note': {'key', 'value', 'source', 'project'},
                  '/api/memory/ask': {'text', 'project', 'session', 'request_id'},
                  '/api/memory/reindex': set(), '/api/memory/backup': set()}
        if not isinstance(data, dict) or set(data) != fields[h.path]: raise MemoryError('Champs invalides.')
        m = AgentMemory()
        if h.path.endswith('/note'): result = m.note(**data)
        elif h.path.endswith('/ask'): result = m.ask(**data)
        elif h.path.endswith('/reindex'): result = m.index()
        else:
            destination = m.state.parent / 'memory-backups' / ('snapshot-' + uuid.uuid4().hex)
            with Memory(m.state, readonly=True) as db: result = db.backup(destination)
            result['path'] = str(destination)
        return h.j(result)
    except (MemoryError, ValueError, TypeError, KeyError) as e: return h.j({'error': str(e)}, 400)
    except (OSError, sqlite3.Error): return h.j({'error': 'Mémoire ou modèle local indisponible.'}, 503)
