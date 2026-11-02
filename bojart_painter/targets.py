"""Cibles de reproduction : motifs synthétiques versionnés, ou image PPM fournie hors Git.

Aucune image n'est stockée dans le dépôt public. Une œuvre réelle n'est chargée que depuis un
fichier local dont les droits de reproduction ont été vérifiés (domaine public ou accord écrit).
"""
from __future__ import annotations

import math
from pathlib import Path

from .canvas import Canvas


def _paysage(u, v):
    if v < 0.55:  # ciel en dégradé + soleil
        sky = (0.55 + 0.35 * v, 0.70 + 0.25 * v, 0.95)
        if math.hypot(u - 0.72, v - 0.22) < 0.09:
            return (0.98, 0.78, 0.25)
        return sky
    hill = 0.55 + 0.08 * math.sin(6.0 * u) + 0.05 * math.sin(13.0 * u + 1.0)
    if v < hill:
        return (0.40, 0.55, 0.75)
    return (0.20 + 0.25 * u, 0.45 - 0.15 * v, 0.18) if v < 0.82 else (0.35, 0.25, 0.15)


def _composition(u, v):
    if 0.30 < u < 0.33 or 0.62 < v < 0.65 or (0.70 < u < 0.73 and v < 0.62):
        return (0.08, 0.08, 0.10)
    if u < 0.30 and v < 0.62:
        return (0.80, 0.18, 0.15)
    if u > 0.73 and v < 0.62:
        return (0.95, 0.85, 0.20)
    if u > 0.33 and v > 0.65:
        return (0.15, 0.30, 0.70)
    return (0.95, 0.94, 0.90)


def _portrait(u, v):
    base = (0.30 + 0.4 * u, 0.22 + 0.2 * v, 0.35)
    r = math.hypot((u - 0.5) / 0.22, (v - 0.45) / 0.30)
    if r < 1.0:
        shade = 0.85 - 0.25 * max(0.0, u - 0.5)
        return (shade, 0.68 * shade, 0.55 * shade)
    if v > 0.78 and abs(u - 0.5) < 0.35:
        return (0.12, 0.16, 0.28)
    return base


SYNTHETIC = {'paysage': _paysage, 'composition': _composition, 'portrait': _portrait}


def make_target(name, width_px, height_px, mm_per_px):
    fn = SYNTHETIC[name]
    data = []
    for y in range(height_px):
        for x in range(width_px):
            data.extend(fn((x + 0.5) / width_px, (y + 0.5) / height_px))
    return Canvas(width_px, height_px, mm_per_px, data=data)


def _tokens(raw: bytes):
    i, n = 0, len(raw)
    while True:
        while i < n and (raw[i:i + 1].isspace() or raw[i:i + 1] == b'#'):
            if raw[i:i + 1] == b'#':
                while i < n and raw[i:i + 1] not in (b'\n', b'\r'):
                    i += 1
            else:
                i += 1
        j = i
        while j < n and not raw[j:j + 1].isspace():
            j += 1
        yield raw[i:j], j
        i = j


def load_ppm(path, width_px, height_px, mm_per_px):
    """Charge un PPM P3/P6 8 bits et le rééchantillonne (moyenne par boîte) à la grille de simulation."""
    raw = Path(path).read_bytes()
    tok = _tokens(raw)
    magic = next(tok)[0]
    if magic not in (b'P3', b'P6'):
        raise ValueError('PPM P3 ou P6 attendu')
    w = int(next(tok)[0]); h = int(next(tok)[0]); mx, end = next(tok); mx = int(mx)
    if magic == b'P6':
        body = raw[end + 1:end + 1 + 3 * w * h]
        values = list(body)
    else:
        values = [int(next(tok)[0]) for _ in range(3 * w * h)]
    if len(values) != 3 * w * h:
        raise ValueError('PPM tronqué')
    data = []
    for y in range(height_px):
        sy0, sy1 = y * h // height_px, max(y * h // height_px + 1, (y + 1) * h // height_px)
        for x in range(width_px):
            sx0, sx1 = x * w // width_px, max(x * w // width_px + 1, (x + 1) * w // width_px)
            acc = [0, 0, 0]; cnt = 0
            for yy in range(sy0, sy1):
                for xx in range(sx0, sx1):
                    i = 3 * (yy * w + xx)
                    acc[0] += values[i]; acc[1] += values[i + 1]; acc[2] += values[i + 2]; cnt += 1
            data.extend(a / (cnt * mx) for a in acc)
    return Canvas(width_px, height_px, mm_per_px, data=data)


def save_ppm(canvas: Canvas, path):
    body = bytes(max(0, min(255, round(c * 255))) for c in canvas.data)
    Path(path).write_bytes(b'P6\n%d %d\n255\n' % (canvas.width, canvas.height) + body)
