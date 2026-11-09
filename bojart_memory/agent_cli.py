"""Local agent memory commands; uses the canonical memory.sqlite database."""
import argparse
import json
from .agent import AgentMemory, state_path
from .core import MemoryError, PROJECTS
from .model_config import inspect_models


def main():
    p = argparse.ArgumentParser(description='Contexte, épisodes et recherche locale BOJ.ART')
    p.add_argument('--state', default=state_path())
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('index'); sub.add_parser('status'); sub.add_parser('embed')
    sub.add_parser('models', help='Vérifier la configuration et les métadonnées des modèles locaux, sans inférence.')
    for name in ('context', 'search'):
        q = sub.add_parser(name); q.add_argument('query')
        q.add_argument('--project', choices=sorted(PROJECTS), default='bojart.jarvis')
    n = sub.add_parser('note')
    for key in ('key', 'value', 'source'): n.add_argument('--' + key, required=True)
    n.add_argument('--project', choices=sorted(PROJECTS), default='bojart.jarvis')
    c = sub.add_parser('configure')
    c.add_argument('--embedding-model'); c.add_argument('--chat-model')
    h = sub.add_parser('history'); h.add_argument('--session', required=True)
    h.add_argument('--project', choices=sorted(PROJECTS), default='bojart.jarvis')
    a = p.parse_args()
    if a.command == 'models':
        result = inspect_models(a.state, probe=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['ok'] else 2
    m = AgentMemory(a.state)
    if a.command in ('context', 'search'): result = getattr(m, a.command)(a.query, a.project)
    elif a.command == 'note': result = m.note(a.key, a.value, a.source, a.project)
    elif a.command == 'configure': result = m.configure(a.embedding_model, a.chat_model)
    elif a.command == 'history': result = m.history(a.session, a.project)
    else: result = getattr(m, a.command)()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (MemoryError, ValueError, OSError) as e: raise SystemExit(str(e))
