#!/usr/bin/env python3
"""Map R03 media to the recovery catalogue, or prepare a verified private copy."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_ops.production_recovery import build_plan, prepare_workspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, help='Dossier restauré BOJART_RECUPERATION_2026-11-01.')
    parser.add_argument('--destination', type=Path, help='Nouveau dossier hors du dépôt, dans un parent existant.')
    args = parser.parse_args()
    if (args.collection is None) != (args.destination is None):
        parser.error('--collection et --destination doivent être fournis ensemble.')
    result = (build_plan(ROOT) if args.collection is None
              else prepare_workspace(ROOT, args.collection, args.destination))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('complete', result.get('copied_bytes_verified', False)) else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Préparation refusée : ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
