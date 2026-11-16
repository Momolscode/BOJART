#!/usr/bin/env python3
"""Measure isolated memory; optionally measure already installed local models."""
import argparse
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_memory.benchmarks import model_trials, run_memory
from bojart_memory.paths import default_state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('memory', 'models'), default='memory')
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--profile', choices=('speed', 'balanced', 'quality'), default='speed')
    parser.add_argument('--url', default='http://127.0.0.1:11434')
    parser.add_argument('--repeats', type=int, default=30)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    output = (args.output or (Path(default_state()).parent / 'benchmarks' / (args.mode + '-' + uuid.uuid4().hex + '.json'))).expanduser()
    # Refuse replacement before starting expensive work.
    if output.exists() or output.is_symlink():
        parser.error('Le rapport exige un nouveau fichier ; aucun rapport existant remplacé.')
    progress = lambda message: print(message, file=sys.stderr, flush=True)
    result = (run_memory(args.repo, repeats=args.repeats, progress=progress) if args.mode == 'memory'
              else model_trials(args.profile, repeats=args.repeats, url=args.url, progress=progress))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'ok': result['ok'], 'report': str(output.resolve()), 'mode': args.mode,
                      'target_hardware_qualified': False}, ensure_ascii=False))
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
