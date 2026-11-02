#!/usr/bin/env python3
"""Point d'entrée : « demande → figurine → visualisation → tranchage » (simulation N2).

Exemples :
  python tools/figurine_pipeline.py "Jarvis, crée-moi la Sentinelle 3D imprimable dans une pose iconique"
  python tools/figurine_pipeline.py "Jarvis, prépare la Sentinelle 3D de 30 cm" --mesh piece_fournie.stl
Un personnage tiers exige en plus --provenance (fiche de licence) ; sans elle, l'étape géométrie est BLOQUÉE.
Aucune commande n'est envoyée à une imprimante.
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/jarvis/app'))
from figurine.pipeline import FigurineRun  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('text')
ap.add_argument('--out', default=str(ROOT.parent / 'runs/figurine'))
ap.add_argument('--mesh', type=Path)
ap.add_argument('--provenance', type=Path, help='fiche de provenance/licence du maillage fourni')
ap.add_argument('--audio', type=Path)
ap.add_argument('--voxel', type=float, default=0.6)
ap.add_argument('--fault', action='append', default=[], help='injection de panne (tests)')
ap.add_argument('--render-size', type=int, default=900)
a = ap.parse_args()
res = FigurineRun(a.text, Path(a.out), mesh=a.mesh, provenance=a.provenance, audio=a.audio, voxel=a.voxel, faults=a.fault,
                  render_size=a.render_size).run()
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(0 if res['status'] in ('DONE',) else 2)
