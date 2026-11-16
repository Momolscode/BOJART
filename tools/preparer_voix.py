#!/usr/bin/env python3
"""Rendre la voix de Jarvis utilisable : poids faster-whisper épinglés puis réglage local.

  python tools/preparer_voix.py              # télécharge une fois les poids « small », active la voix
  python tools/preparer_voix.py --modele base

À lancer avec le Python de .venv (bibliothèques voix installées). Le micro n'est pas ouvert ;
la qualité réelle se mesure ensuite sur la tour. Lancé par Installer_Tout_BOJART.cmd.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bojart_ops import voix_installation as vi  # noqa: E402
from bojart_ops.banc_voix import MODELES  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--modele', choices=sorted(MODELES), default=vi.DEFAULT_MODEL,
                   help='Poids épinglés (small : référence du banc vocal du 2 novembre 2026).')
    p.add_argument('--configuration', type=Path, default=vi.CONFIG, help='Configuration privée de Jarvis.')
    a = p.parse_args(argv)
    try:
        result = vi.prepare(a.modele, config_path=a.configuration)
    except ImportError:
        print('Bibliothèques voix absentes : lancer avec .venv après prepare_installation.py --voice.', file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError, SystemExit) as exc:
        print('Voix non préparée, rien d’autre n’a été modifié : ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('Voix prête : ouvrir Lancer_BOJART.cmd, page « Trois vues », puis autoriser le micro dans le navigateur.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
