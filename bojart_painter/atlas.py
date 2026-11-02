"""Atlas de touches mesurées (numpy, facultatif).

Un atlas rassemble des masques d'opacité de touches réelles, ou tirées d'un modèle appris. Chaque
masque est rangé dans le repère de la touche : départ à `origin_px`, tracé vers +x de l'image.
Une courbure positive déplace le milieu vers le haut de l'image, c'est-à-dire à gauche du trajet.
Chaque entrée porte sa longueur, sa courbure et sa largeur mesurée (mm). Le peintre HD peut
peindre avec ces masques à la place de sa touche modélisée (`HDPainter(..., atlas=...)`).

Sources prévues :
- en simulation, un atlas tiré hors dépôt du modèle de pinceau de FRIDA (GPL-3.0, non copié ici) ;
- en semaine 1, les touches de notre propre pinceau, photographiées sur la planche d'étalonnage.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np


class StrokeAtlas:
    def __init__(self, masks, length_mm, bend_mm, width_mm, mm_per_px, origin_px, source=''):
        self.masks = np.asarray(masks, dtype=np.float32)
        self.length_mm = np.asarray(length_mm, dtype=np.float32)
        self.bend_mm = np.asarray(bend_mm, dtype=np.float32)
        self.width_mm = np.asarray(width_mm, dtype=np.float32)
        self.mm = float(mm_per_px)
        self.origin = (float(origin_px[0]), float(origin_px[1]))
        self.source = str(source)
        n = len(self.masks)
        if not (len(self.length_mm) == len(self.bend_mm) == len(self.width_mm) == n) or self.masks.ndim != 3:
            raise ValueError('atlas incohérent : un masque 2D et trois mesures par touche')

    @classmethod
    def load(cls, path):
        d = np.load(Path(path), allow_pickle=False)
        return cls(d['masks'], d['length_mm'], d['bend_mm'], d['width_mm'], float(d['mm_per_px']),
                   tuple(d['origin_px']), str(d['source']) if 'source' in d else '')

    def save(self, path):
        np.savez_compressed(Path(path), masks=self.masks, length_mm=self.length_mm, bend_mm=self.bend_mm,
                            width_mm=self.width_mm, mm_per_px=np.float32(self.mm),
                            origin_px=np.asarray(self.origin, np.float32), source=np.str_(self.source))

    @property
    def width_range(self):
        """Largeurs utiles (5e et 95e centiles) des touches assez longues : une touche très courte
        est un simple dépôt dont la « largeur » ne décrit pas le pinceau."""
        long = self.width_mm[self.length_mm >= 3 * np.median(self.width_mm)]
        w = long if len(long) else self.width_mm
        return float(np.percentile(w, 5)), float(np.percentile(w, 95))

    @property
    def max_length_mm(self):
        return float(self.length_mm.max())

    def nearest(self, length_mm, bend_mm, width_mm):
        dl = (self.length_mm - length_mm) / max(length_mm, 5.0)
        db = (self.bend_mm - bend_mm) / max(length_mm, 5.0)
        dw = (self.width_mm - width_mm) / max(width_mm, 1.0)
        return int(np.argmin(dl * dl + db * db + 4 * dw * dw))

    def footprint(self, p0, p1, p2, width_mm, mm_per_px, gain, opacity, shape):
        """Masque posé sur la toile entre p0 et p2 (pixels), courbé selon p1 ; None hors toile."""
        p0, p1, p2 = (np.asarray(p, dtype=np.float64) for p in (p0, p1, p2))
        chord = (p2 - p0) * mm_per_px
        length = float(np.hypot(*chord))
        if length < 1e-6:
            return None
        u = chord / length
        left = np.array([u[1], -u[0]])                  # à gauche du trajet, image y vers le bas
        mid = (0.25 * p0 + 0.5 * p1 + 0.25 * p2) * mm_per_px
        bend = float((mid - (p0 + p2) / 2 * mm_per_px) @ left) / 0.75
        k = self.nearest(length, bend, width_mm / max(gain, 1e-6))
        mask = self.masks[k]
        stretch = float(self.length_mm[k]) / length if self.length_mm[k] > 0 else 1.0
        # Boîte englobante : touche réelle plus la marge du masque.
        h, w = mask.shape
        corners = np.array([[0, 0], [w, 0], [0, h], [w, h]], dtype=np.float64)
        cu = (corners[:, 0] - self.origin[0]) * self.mm / stretch
        cv = -(corners[:, 1] - self.origin[1]) * self.mm * gain
        pts = (p0 * mm_per_px + cu[:, None] * u + cv[:, None] * left) / mm_per_px
        H, W = shape
        x0 = int(max(0, math.floor(pts[:, 0].min()))); x1 = int(min(W, math.ceil(pts[:, 0].max()) + 1))
        y0 = int(max(0, math.floor(pts[:, 1].min()))); y1 = int(min(H, math.ceil(pts[:, 1].max()) + 1))
        if x1 <= x0 or y1 <= y0:
            return None
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
        rx = (xx + 0.5) * mm_per_px - p0[0] * mm_per_px
        ry = (yy + 0.5) * mm_per_px - p0[1] * mm_per_px
        lu = (rx * u[0] + ry * u[1]) * stretch
        lv = (rx * left[0] + ry * left[1]) / gain
        mx = self.origin[0] + lu / self.mm
        my = self.origin[1] - lv / self.mm
        a = _bilinear(mask, mx, my) * opacity
        return (y0, y1, x0, x1, a.astype(np.float32)) if a.max() > 0.01 else None


def _bilinear(img, x, y):
    h, w = img.shape
    x = x - 0.5; y = y - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    out = np.zeros(x.shape, dtype=np.float64)
    for dy, wy in ((0, 1 - fy), (1, fy)):
        for dx, wx in ((0, 1 - fx), (1, fx)):
            xi, yi = x0 + dx, y0 + dy
            ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
            v = np.zeros(x.shape)
            v[ok] = img[yi[ok], xi[ok]]
            out += wx * wy * v
    return out


def synthetic_atlas(widths_mm=(4.0, 6.0), lengths_mm=(10.0, 30.0, 60.0), bends_mm=(-6.0, 0.0, 6.0), mm_per_px=0.5):
    """Atlas de test : touches pleines, bords nets, courbure en arc (sans mesure réelle)."""
    masks, L, B, Wd = [], [], [], []
    pad = 12.0
    h = int((2 * (max(abs(b) for b in bends_mm) + max(widths_mm)) + 2 * pad) / mm_per_px)
    w = int((max(lengths_mm) + 2 * pad) / mm_per_px)
    origin = (pad / mm_per_px, h / 2)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    ux = (xx + 0.5 - origin[0]) * mm_per_px; vy = -(yy + 0.5 - origin[1]) * mm_per_px
    for wd in widths_mm:
        for ln in lengths_mm:
            for bd in bends_mm:
                if abs(bd) > ln:
                    continue
                t = np.clip(ux / ln, 0, 1)
                centre = 3 * bd * t * (1 - t)  # même profil que la cubique de FRIDA
                inside = (ux >= 0) & (ux <= ln) & (np.abs(vy - centre) <= wd / 2)
                masks.append(inside.astype(np.float32)); L.append(ln); B.append(bd); Wd.append(wd)
    return StrokeAtlas(masks, L, B, Wd, mm_per_px, origin, source='synthétique (test)')
