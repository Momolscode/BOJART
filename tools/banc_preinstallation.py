#!/usr/bin/env python3
"""Banc de simulation pré-installation : chaque action de Jarvis, sans matériel réel.

Exemples :
  python tools/banc_preinstallation.py --output banc.json --markdown banc.md
  python tools/banc_preinstallation.py --quick            # suites rapides + HTTP + statique
  python tools/banc_preinstallation.py --reseau           # ajoute la résolution des roues Windows

Le rapport n'écrase jamais un fichier existant. Code de sortie : 0 si aucun constat
bloquant, 1 sinon, 2 en cas d'erreur d'usage.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bojart_ops.banc_simulation import markdown, run_bench  # noqa: E402


def write_new(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as fh:
        fh.write(text)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--output', type=Path, help='Rapport JSON (nouveau fichier).')
    p.add_argument('--markdown', type=Path, help='Rapport lisible (nouveau fichier).')
    p.add_argument('--python', default=sys.executable, help='Interpréteur à tester (par défaut celui-ci).')
    p.add_argument('--quick', action='store_true', help='Suites courtes, sans émulation d’encodage.')
    p.add_argument('--reseau', action='store_true', help='Résoudre les roues Windows cp312 sur PyPI (lecture seule).')
    p.add_argument('--sans-suites', action='store_true')
    p.add_argument('--sans-http', action='store_true')
    p.add_argument('--sans-outils', action='store_true')
    p.add_argument('--sans-encodage', action='store_true')
    a = p.parse_args(argv)
    for target in (a.output, a.markdown):
        if target is not None and target.exists():
            p.error(f'{target} existe déjà : choisir un chemin neuf.')
    results = run_bench(a.python, suites=not a.sans_suites, http=not a.sans_http, tools=not a.sans_outils,
                        encoding=not a.sans_encodage, network=a.reseau, quick=a.quick)
    text = markdown(results)
    if a.output:
        write_new(a.output, json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    if a.markdown:
        write_new(a.markdown, text)
    s = results['synthese']
    print(f"Actions : {s['actions_par_statut']} ; constats : {s['constats_par_severite']} ; tests : {s['tests_executes']}")
    if a.output:
        print('Rapport JSON :', a.output)
    if a.markdown:
        print('Rapport lisible :', a.markdown)
    print('Simulation uniquement : pas de micro, de moniteur physique ni d’imprimante.')
    return 1 if s['constats_par_severite'].get('bloquant') else 0


if __name__ == '__main__':
    raise SystemExit(main())
