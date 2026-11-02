#!/usr/bin/env python3
"""Générer ou vérifier les verrous d'installation de Jarvis (versions exactes + empreintes SHA-256).

  python tools/verrouiller_dependances.py --verifier          # hors ligne : verrous cohérents avec les requirements
  python tools/verrouiller_dependances.py --sortie DOSSIER    # réseau : résolution du jour sur CETTE plateforme
  python tools/verrouiller_dependances.py --sortie D --comparer   # écart entre la résolution du jour et les verrous

Les verrous Windows se génèrent sous Windows (workflow du banc), jamais depuis Linux.
Aucun paquet n'est installé par cet outil.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bojart_ops import verrou_dependances as vd  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--verifier', action='store_true', help='Contrôle hors ligne des verrous Windows validés.')
    p.add_argument('--sortie', type=Path, help='Écrire les verrous de cette plateforme dans ce dossier (doit être neuf ou vide).')
    p.add_argument('--comparer', action='store_true', help='Avec --sortie : comparer aux verrous validés du dépôt.')
    a = p.parse_args(argv)
    if not a.verifier and not a.sortie:
        p.error('Choisir --verifier ou --sortie.')
    result = {}
    if a.sortie:
        if a.sortie.exists() and any(a.sortie.iterdir()):
            p.error(f'{a.sortie} existe et n’est pas vide : aucun verrou n’est écrasé.')
        result['generation'] = vd.generate(a.sortie)
        if a.comparer:
            result['ecart_avec_le_depot'] = vd.drift(a.sortie)
    if a.verifier:
        result['verification'] = vd.verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get('verification') else 0


if __name__ == '__main__':
    sys.exit(main())
