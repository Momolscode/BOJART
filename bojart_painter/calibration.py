"""Semaine 1 : planche d'étalonnage simulée (bibliothèque de touches mesurées).

Le bras peint, pour chaque pinceau et chaque pot, une touche droite sur un carton blanc. Une photo
bruitée sert ensuite à mesurer la largeur réellement déposée et l'opacité, comme le ferait la
caméra de l'atelier. Le dépôt « réel » est un modèle caché : ce module montre la méthode de
mesure, il ne remplace pas la planche peinte en G1. Nécessite numpy.
"""
from __future__ import annotations

import numpy as np

from .hd import Deposit, HDPainter


def stroke_library(palette, brushes_mm=(20.0, 8.0, 3.0), hidden=Deposit(1.25, 0.75), mm_per_px=0.5,
                   camera_sigma=0.01, seed=1):
    palette = np.asarray(palette, dtype=np.float32)
    n = len(palette)
    row_h = [max(30.0, 2.6 * b) for b in brushes_mm]
    lengths = [max(26.0, 2.5 * b) for b in brushes_mm]
    spacing = [L + 1.6 * b + 6 for L, b in zip(lengths, brushes_mm)]
    per_line = (n + 1) // 2
    W = int((20 + per_line * max(spacing)) / mm_per_px); H = int((10 + 2 * sum(row_h)) / mm_per_px)
    board = np.ones((H, W, 3), np.float32)
    painter = HDPainter(board.copy(), 'reproduction', mm_per_px, seed)
    painter.T = board  # cible sans objet ici : seule la géométrie de touche sert
    rng = np.random.default_rng(seed)
    rows, y_mm = [], 5.0
    for bi, b in enumerate(brushes_mm):
        for line in range(2):
            y_mm += row_h[bi] / 2
            for ci in range(line * per_line, min(n, (line + 1) * per_line)):
                length = lengths[bi]; x0 = 10 + 0.8 * b + (ci - line * per_line) * max(spacing)
                p0 = np.array([x0, y_mm]) / mm_per_px; p2 = np.array([x0 + length, y_mm]) / mm_per_px
                fp = painter.footprint(p0, (p0 + p2) / 2, p2, b, hidden, int(rng.integers(1 << 30)), bristle=True)
                painter._apply(board, fp, palette[ci])
                rows.append({'brush_mm': b, 'pot': ci, 'x_mm': x0 + length / 2, 'y_mm': y_mm})
            y_mm += row_h[bi] / 2
    photo = np.clip(board + rng.normal(0, camera_sigma, board.shape).astype(np.float32), 0, 1)
    for r in rows:  # mesure sur la photo, colonne au milieu de la touche
        col = int(r['x_mm'] / mm_per_px); cy = int(r['y_mm'] / mm_per_px)
        half = int(1.6 * r['brush_mm'] / mm_per_px)
        strip = photo[max(0, cy - half):cy + half, col - 2:col + 3].mean(1)
        paint = palette[r['pot']]
        contrast = np.abs(paint - 1.0)
        k = int(contrast.argmax())
        if contrast[k] < 0.15:
            r.update(measured_width_mm=None, measured_opacity=None)
            continue
        cover = (1.0 - strip[:, k]) / (1.0 - paint[k])
        r['measured_width_mm'] = round(float((cover > 0.5 * np.median(cover[len(cover) // 2 - 2:len(cover) // 2 + 3])).sum() * mm_per_px), 2)
        r['measured_opacity'] = round(float(np.median(cover[len(cover) // 2 - 2:len(cover) // 2 + 3])), 3)
    fit = {}
    for b in brushes_mm:
        ws = [r['measured_width_mm'] / b for r in rows if r['brush_mm'] == b and r.get('measured_width_mm')]
        ops = [r['measured_opacity'] for r in rows if r['brush_mm'] == b and r.get('measured_opacity')]
        fit[str(b)] = {'width_gain_median': round(float(np.median(ws)), 3) if ws else None,
                       'opacity_median': round(float(np.median(ops)), 3) if ops else None, 'samples': len(ws)}
    return {'board': board, 'photo': photo, 'rows': rows, 'fit': fit, 'hidden': hidden.as_dict(),
            'mm_per_px': mm_per_px}
