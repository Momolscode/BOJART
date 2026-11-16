#!/usr/bin/env python3
"""Socle d'exposition BOJ.ART pour une figurine du commerce (fiche D15 du registre M08).

Exemples :
  python tools/socle_vitrine.py --forme ronde --largeur 80 --out SORTIE --rendus
  python tools/socle_vitrine.py --forme ovale --largeur 90 --profondeur 70 --out SORTIE
  python tools/socle_vitrine.py --forme libre --largeur 100 --profondeur 60 --out SORTIE
--forme : forme du socle d'origine de la figurine (« libre » : irrégulier ou absent, dessus plat).
--largeur / --profondeur : cotes du socle d'origine en mm, relevées au pied à coulisse.

Dessin original en plaques d'ardoise : seule l'empreinte du socle d'origine est creusée. Aucune
géométrie ni image du personnage n'est produite ; les rendus montrent le socle seul. Le tranchage est
une estimation sous profil d'hypothèse (G-code marqué SIMULATION), jamais envoyé à une machine.
"""
import argparse, json, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/jarvis/app'))
from figurine import checks, fabrication, slicing  # noqa: E402
from figurine.pipeline import HERE, environment, sha256_file  # noqa: E402

ap = argparse.ArgumentParser(description='Socle d’exposition BOJ.ART pour une figurine du commerce.')
ap.add_argument('--forme', choices=fabrication.VITRINE_SHAPES, required=True)
ap.add_argument('--largeur', type=float, required=True, help='mm')
ap.add_argument('--profondeur', type=float, help='mm (ovale ou libre)')
ap.add_argument('--hauteur', type=float, help=f"mm (hypothèse : {fabrication.VITRINE_HYPOTHESES['height_mm']:g})")
ap.add_argument('--empreinte', type=float, help=f"profondeur de l'empreinte en mm "
                                               f"(hypothèse : {fabrication.VITRINE_HYPOTHESES['pocket_depth_mm']:g})")
ap.add_argument('--graine', type=int, default=23, help='tirage des bords cassés (même graine = même socle)')
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--rendus', action='store_true', help='rendus Blender du socle seul, si Blender est installé')
a = ap.parse_args()

hyp = dict(fabrication.VITRINE_HYPOTHESES)
if a.hauteur:
    hyp['height_mm'] = a.hauteur
if a.empreinte:
    hyp['pocket_depth_mm'] = a.empreinte
t0 = time.time()
try:
    mesh, info = fabrication.display_socle(a.forme, a.largeur, a.profondeur, hyp=hyp, seed=a.graine)
except ValueError as exc:
    print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, ensure_ascii=False, indent=1))
    sys.exit(2)
a.out.mkdir(parents=True, exist_ok=True)
stl = a.out / 'socle_vitrine.stl'
mesh.export(stl)
report = {'status': 'DONE', 'inputs': {'forme': a.forme, 'largeur_mm': a.largeur, 'profondeur_mm': a.profondeur,
                                       'graine': a.graine},
          'socle': info, 'checks': checks.check_part(mesh, 'socle_vitrine'),
          'files': {'socle_vitrine.stl': sha256_file(stl)}}

exe = slicing.find_slicer()
if exe:
    sd = a.out / 'tranchage'
    sd.mkdir(exist_ok=True)
    r = slicing.slice_part(stl, sd, exe=exe)
    report['slicing'] = {**r, 'profile': slicing.PROFILE, 'bed_hypothesis_mm': slicing.SIM_BED_MM,
                         'orientation': 'à l’endroit, tel quel', 'sent_to_machine': False}
    if r['status'] != 'DONE':
        report['status'] = 'FAILED'
else:
    report['slicing'] = {'status': 'BLOCKED', 'reason': 'PrusaSlicer introuvable : aucun chiffre inventé'}

if a.rendus:
    blender = shutil.which('blender')
    if not blender:
        report['renders'] = {'status': 'BLOCKED', 'reason': 'Blender absent : aucune image substituée'}
    else:
        rd = a.out / 'rendus'
        rd.mkdir(exist_ok=True)
        proc = subprocess.run([blender, '-b', '--factory-startup', '--python', str(HERE / 'blender_render.py'), '--',
                               str(rd), '900', '32', str(stl)], capture_output=True, text=True, timeout=1800)
        if 'BOJART_RENDER_OK' not in proc.stdout:
            report['renders'] = {'status': 'FAILED', 'log_tail': (proc.stdout + proc.stderr)[-600:]}
        else:
            # Le script nomme ses sorties pour une figurine : noms rendus justes pour un socle seul.
            for old, new in (('vue_buste.png', 'vue_rapprochee.png'), ('figurine.blend', 'socle_vitrine.blend')):
                if (rd / old).exists():
                    (rd / old).replace(rd / new)
            report['renders'] = {'status': 'DONE', 'files': sorted(p.name for p in rd.iterdir()),
                                 'note': 'rendus argile du socle seul ; appréciation visuelle, pas une mesure'}

report['environment'] = environment()
report['duration_s'] = round(time.time() - t0, 1)
(a.out / 'rapport.json').write_text(json.dumps(report, ensure_ascii=False, indent=1, default=float), encoding='utf8')
print(json.dumps({'status': report['status'], 'socle_mm': info['outer_extents_mm'], 'rim_min_mm': info['rim_min_mm'],
                  'eliminatory': report['checks']['eliminatory'],
                  'slicing': report['slicing'].get('stats', report['slicing'].get('reason'))}, ensure_ascii=False, indent=1))
sys.exit(0 if report['status'] == 'DONE' and not report['checks']['eliminatory'] else 1)
