#!/usr/bin/env python3
"""Produce an evidence inventory and nonzero exit on structural errors."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bojart_ops.audit import audit, markdown


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--revision')
    a = p.parse_args()
    report = audit(a.root, revision=a.revision)
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (a.output / 'audit.md').write_text(markdown(report), encoding='utf-8')
    print(json.dumps(report['summary']))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
