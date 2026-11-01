"""Run with python -m bojart_memory; all actions are local and explicit."""
import argparse
import json
from pathlib import Path
from .core import Memory, MemoryError, MAX_FILES, TEXT_EXT, IGNORED_PARTS, PROJECTS
from .paths import default_state
from .indexing import index_repository


def main():
    p=argparse.ArgumentParser(description='Mémoire BOJ.ART sourcée, locale, sans appel de modèle.')
    p.add_argument('--state',type=Path,default=default_state())
    sub=p.add_subparsers(dest='cmd',required=True)
    i=sub.add_parser('ingest');i.add_argument('root',type=Path);i.add_argument('--project',required=True);i.add_argument('--collection',required=True);i.add_argument('--provenance',required=True)
    r=sub.add_parser('index-repo');r.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    q=sub.add_parser('search');q.add_argument('query');q.add_argument('--project',required=True);q.add_argument('--history',action='store_true');q.add_argument('--limit',type=int,default=6)
    sub.add_parser('stats');sub.add_parser('verify')
    b=sub.add_parser('backup');b.add_argument('destination',type=Path)
    x=sub.add_parser('restore');x.add_argument('snapshot',type=Path);x.add_argument('destination',type=Path)
    a=p.parse_args()
    if a.cmd=='restore':
        result=Memory.restore(a.snapshot,a.destination)
    else:
        with Memory(a.state,readonly=a.cmd in {'search','stats','verify','backup'}) as m:
            if a.cmd=='ingest':
                if a.root.is_symlink():raise MemoryError('Dossier symbolique refusé.')
                root=a.root.resolve()
                if not root.is_dir() or m.state.is_relative_to(root):raise MemoryError('Dossier source invalide ou contenant la mémoire.')
                paths=[f for f in root.rglob('*') if f.is_file() and f.suffix.lower() in TEXT_EXT and not any(part in IGNORED_PARTS or part.startswith('.env') for part in f.relative_to(root).parts)]
                if len(paths)>MAX_FILES:raise MemoryError('Lot trop grand.')
                result={'files':[m.ingest_file(f,root=root,project=a.project,collection=a.collection,provenance=a.provenance) for f in sorted(paths)]}
            elif a.cmd=='index-repo':
                result=index_repository(m,a.repo)
            elif a.cmd=='search':result=m.search(a.query,project=a.project,limit=a.limit,history=a.history)
            elif a.cmd=='stats':result=m.stats()
            elif a.cmd=='verify':
                result=m.verify()
                if not result['ok']:raise MemoryError(json.dumps(result))
            elif a.cmd=='backup':result=m.backup(a.destination)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (MemoryError,OSError,ValueError) as e:raise SystemExit(str(e))
