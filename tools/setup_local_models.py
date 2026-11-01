#!/usr/bin/env python3
"""Plan offline; explicitly download, test and activate local models on this host."""
import argparse
from http.client import HTTPException
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_memory.core import MemoryError
from bojart_memory.model_setup import PROFILES, plan, prepare
from bojart_memory.paths import default_state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=sorted(PROFILES))
    parser.add_argument('--state', default=default_state())
    parser.add_argument('--apply', action='store_true', help='Tester et activer le profil sur cet ordinateur.')
    parser.add_argument('--download', action='store_true', help='Télécharger les seuls modèles manquants de ce profil via Ollama.')
    parser.add_argument('--max-followup-ms', type=int, help='Seuil explicite du test synthétique, pas une mesure annoncée.')
    args = parser.parse_args(argv)
    if args.apply and not args.profile:
        parser.error('--apply exige --profile ; choisir après inventaire du GPU.')
    if args.download and not args.apply:
        parser.error('--download exige --apply.')
    if not args.apply:
        print(json.dumps({'mode': 'plan_only', 'network_requests': 0,
            'profiles': [plan(args.profile)] if args.profile else [plan(p) for p in PROFILES]}, ensure_ascii=False, indent=2))
        return 0
    result = prepare(args.state, args.profile, download=args.download, max_followup_ms=args.max_followup_ms)
    state = Path(args.state).expanduser()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt = state / ('model-qualification-' + uuid.uuid4().hex + '.json')
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'ok': result['ok'], 'activated': result['activated'],
                      'report': str(receipt.resolve()), 'production_ready': False,
                      'error_code': result.get('error_code')}, ensure_ascii=False, indent=2))
    return 0 if result['ok'] and result['activated'] else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (MemoryError, ValueError, OSError, HTTPException) as exc:
        raise SystemExit('Préparation interrompue : ' + str(exc))
