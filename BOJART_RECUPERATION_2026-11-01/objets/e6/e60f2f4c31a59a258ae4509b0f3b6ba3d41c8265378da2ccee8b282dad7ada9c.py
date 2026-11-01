"""Entrée hors ligne : python connector_cli.py capture.har --origin URL --authority REF."""
import argparse
import json
from pathlib import Path
from reverse_api_adapter import Scope, inspect_and_record, rae_preflight_plan

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('har', type=Path)
    p.add_argument('--origin', required=True)
    p.add_argument('--authority', required=True)
    p.add_argument('--runtime', type=Path, default=Path('runtime'))
    p.add_argument('--allow-loopback', action='store_true')
    a = p.parse_args()
    scope = Scope('marwin-studio', a.origin, a.authority, a.allow_loopback)
    report = inspect_and_record(json.loads(a.har.read_text()), scope, a.runtime)
    report['rae_preflight'] = rae_preflight_plan(scope)
    print(json.dumps(report, ensure_ascii=False, indent=2))
