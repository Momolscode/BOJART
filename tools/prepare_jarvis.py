#!/usr/bin/env python3
"""Prepare Jarvis knowledge offline; inspect requirements/tools without executing them."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_ops.preinstallation import build, catalog, preparation_status


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    for name in ('requirements', 'tools'):
        item = sub.add_parser(name)
        item.add_argument('query', nargs='?', default='')
        item.add_argument('--limit', type=int, default=20)
    item = sub.add_parser('build')
    item.add_argument('--destination', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'status': result = preparation_status()
    elif a.command == 'build': result = build(a.destination)
    else: result = catalog(a.command, a.query, limit=a.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Préparation refusée : ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
