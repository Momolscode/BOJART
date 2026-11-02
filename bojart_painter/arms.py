"""Profils de bras et contrôles géométriques simples sur la toile.

Ce n'est pas la cinématique constructeur : la portée est traitée comme une sphère autour de
l'épaule, réduite d'une marge pour garder le pinceau perpendiculaire. Le modèle MuJoCo/URDF
réel doit confirmer l'accès avant tout achat (jalon G2 STRATES).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMS_PATH = ROOT / 'configs/painter/arms.json'


def load_arms(path=ARMS_PATH):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return {a['id']: a for a in data['arms']}


def _coverage(arm, canvas_w, canvas_h, base, shoulder_dz, margin, grid_mm):
    reach = arm['reach_mm'] * margin
    min_r = 0.2 * arm['reach_mm']
    ok = total = 0
    y = grid_mm / 2
    while y < canvas_h:
        x = grid_mm / 2
        while x < canvas_w:
            d = math.sqrt((x - base[0]) ** 2 + (y - base[1]) ** 2 + shoulder_dz ** 2)
            ok += min_r <= d <= reach
            total += 1
            x += grid_mm
        y += grid_mm
    return ok / total


def reach_report(arm, canvas_w_mm=900, canvas_h_mm=650, margin=0.85, grid_mm=10):
    """Part de la toile atteignable pour deux implantations : bord de table et surplomb central."""
    if not arm.get('reach_mm'):
        return {'arm': arm['id'], 'known': False, 'reason': 'portée non publiée'}
    edge = _coverage(arm, canvas_w_mm, canvas_h_mm, (canvas_w_mm / 2, canvas_h_mm + 80), 150, margin, grid_mm)
    over = _coverage(arm, canvas_w_mm, canvas_h_mm, (canvas_w_mm / 2, canvas_h_mm / 2), 300, margin, grid_mm)
    best = max(edge, over)
    # Surface utile par implantation ≈ part couverte ; nombre de zones = indication, pas un plan de recalage.
    zones = 1 if best >= 0.999 else math.ceil(1 / max(best, 1e-6)) + 1
    return {'arm': arm['id'], 'known': True, 'canvas_mm': [canvas_w_mm, canvas_h_mm],
            'usable_reach_mm': round(arm['reach_mm'] * margin), 'coverage_edge': round(edge, 3),
            'coverage_overhead': round(over, 3), 'placements_estimate': zones,
            'assumptions': 'sphère de portée × marge, épaule 150 mm (bord) ou 300 mm (surplomb) au-dessus du plan, rayon mort 20 %'}


def execution_time_s(strokes, arm, paint_speed_mm_s=80.0, travel_speed_mm_s=250.0, approach_s=0.8, dip_every=6, dip_s=6.0):
    """Durée estimée : tracé à vitesse de peinture, déplacements, approches et recharges de pinceau."""
    tcp = arm.get('max_tcp_speed_mm_s') or 250.0
    paint_v = min(paint_speed_mm_s, tcp); travel_v = min(travel_speed_mm_s, tcp)
    t, last = 0.0, None
    for i, s in enumerate(strokes):
        if last is not None:
            t += math.dist(last, s.p0) / travel_v
        t += s.length_mm() / paint_v + approach_s
        if i % dip_every == 0:
            t += dip_s
        last = s.p2
    return t
