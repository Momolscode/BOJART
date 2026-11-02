"""Passerelle de plans FRIDA → bojart_painter, sans code FRIDA.

FRIDA (cmubig/Frida, licence GPL-3.0) reste installé hors de ce dépôt, sur le poste de l'atelier.
Son plan est exporté en JSON : touches (xt, yt, angle, length_m, bend_m, z, color), dimensions de
la toile et table « pression z → largeur » mesurée sur son modèle de touche. Ce module convertit ce
plan en touches de Bézier pour le rejouer dans le monde simulé (`replay`) ou dans l'animation du
bras (`tools/render_painter_cell.py --frida-plan`).

Géométrie reprise du format publié par FRIDA : la touche part du point (xt, yt) de la toile
(proportions de -1 à 1, y de l'image vers le bas). Elle suit la cubique (0, 0), (L/3, b),
(2L/3, b), (L, 0), tournée de l'angle dans le repère du bras (y vers le haut). Ici, cette cubique
devient une quadratique de même milieu, dont le point de contrôle vaut 1,5 × b. Nécessite numpy.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .hd import Deposit, HDPainter, ssim


def load_plan(path):
    plan = json.loads(Path(path).read_text(encoding='utf-8'))
    for key in ('strokes', 'canvas_m', 'width_table'):
        if key not in plan:
            raise ValueError(f'plan FRIDA incomplet : clé {key!r} absente')
    return plan


def width_mm(z, table, length_m=0.05):
    rows = [r for r in table if r.get('length_m', length_m) == length_m] or list(table)
    zs, ws = zip(*sorted((r['z'], r['width_mm_median']) for r in rows))
    return float(np.interp(z, zs, ws))


def to_strokes(plan, mm_per_px=1.0):
    """Touches au format `HDPainter.run(record=True)['executed']`, dans l'ordre d'exécution de FRIDA."""
    w_mm, h_mm = (v * 1000 for v in plan['canvas_m'])
    out = []
    for i, s in enumerate(plan['strokes']):
        sx, sy = (s['xt'] * 0.5 + 0.5) * w_mm, (s['yt'] * 0.5 + 0.5) * h_mm
        length, bend, ca, sa = s['length_m'] * 1000, s['bend_m'] * 1000, math.cos(s['angle']), math.sin(s['angle'])

        def point(lx, ly):
            return np.array([sx + ca * lx - sa * ly, sy - (sa * lx + ca * ly)]) / mm_per_px

        out.append({'batch': 0, 'p': [point(0, 0), point(length / 2, 1.5 * bend), point(length, 0)],
                    'width_mm': width_mm(s['z'], plan['width_table']), 'seed': i,
                    'color': np.clip(np.asarray(s['color'], dtype=np.float32), 0, 1)})
    return out


def replay(target, strokes, mm_per_px=1.0, hidden=Deposit(1.0, 1.0), seed=1):
    """Exécute les touches en boucle ouverte dans le monde simulé et mesure l'écart à la cible."""
    painter = HDPainter(target, 'reproduction', mm_per_px, seed, hidden=hidden)
    world = np.ones_like(painter.T)
    for e in strokes:
        fp = painter.footprint(*e['p'], e['width_mm'], hidden, e['seed'])
        if fp is not None:
            painter._apply(world, fp, e['color'])
    mse = float(((world - painter.T) ** 2).mean())
    return {'world': world, 'strokes': len(strokes), 'ssim': round(ssim(world, painter.T), 4),
            'psnr_db': round(10 * math.log10(1 / mse), 2) if mse > 0 else None, 'hidden': hidden.as_dict()}
