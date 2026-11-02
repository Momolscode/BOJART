"""Toile raster et modèle de touche de pinceau (Python standard, déterministe)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class BrushModel:
    """Comportement de dépôt supposé : ce que le planificateur croit, ou la « réalité » simulée."""
    width_gain: float = 1.0      # largeur déposée / largeur commandée
    opacity: float = 0.9         # couverture au centre de la touche
    edge_mm: float = 2.0         # largeur de la transition douce du bord (étalement)

    def as_dict(self):
        return {'width_gain': round(self.width_gain, 4), 'opacity': round(self.opacity, 4),
                'edge_mm': round(self.edge_mm, 4)}


@dataclass
class Stroke:
    """Touche : Bézier quadratique p0 → p2 contrôlée par p1, coordonnées en mm sur la toile."""
    p0: tuple
    p1: tuple
    p2: tuple
    width_mm: float
    color: tuple
    meta: dict = field(default_factory=dict)

    def points(self, step_mm: float):
        approx = math.dist(self.p0, self.p1) + math.dist(self.p1, self.p2)
        n = max(2, int(approx / max(step_mm, 1e-6)) + 1)
        out = []
        for i in range(n + 1):
            t = i / n
            a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
            out.append((a * self.p0[0] + b * self.p1[0] + c * self.p2[0],
                        a * self.p0[1] + b * self.p1[1] + c * self.p2[1]))
        return out

    def length_mm(self):
        pts = self.points(1.0)
        return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

    def shifted(self, dx, dy, width_scale=1.0):
        mv = lambda p: (p[0] + dx, p[1] + dy)
        return Stroke(mv(self.p0), mv(self.p1), mv(self.p2), self.width_mm * width_scale, self.color, dict(self.meta))

    def as_dict(self):
        r = lambda p: [round(p[0], 2), round(p[1], 2)]
        return {'p0': r(self.p0), 'p1': r(self.p1), 'p2': r(self.p2), 'width_mm': round(self.width_mm, 2),
                'color': [round(c, 4) for c in self.color]}


def _seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


class Canvas:
    """Image RVB en flottants 0–1, origine en haut à gauche, `mm_per_px` millimètres par pixel."""

    def __init__(self, width, height, mm_per_px, background=(1.0, 1.0, 1.0), data=None):
        self.width, self.height, self.mm_per_px = width, height, mm_per_px
        self.data = list(data) if data is not None else [c for _ in range(width * height) for c in background]

    def copy(self):
        return Canvas(self.width, self.height, self.mm_per_px, data=self.data)

    @property
    def size_mm(self):
        return self.width * self.mm_per_px, self.height * self.mm_per_px

    def pixel(self, x, y):
        i = 3 * (y * self.width + x)
        return self.data[i], self.data[i + 1], self.data[i + 2]

    def footprint(self, stroke: Stroke, model: BrushModel):
        """Liste (indice pixel, alpha) couverte par la touche selon `model`."""
        m = self.mm_per_px
        half = stroke.width_mm * model.width_gain / 2
        edge = max(model.edge_mm, 1e-6)
        pts = stroke.points(max(half, m))
        reach = half + edge / 2
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        x0 = max(0, int((min(xs) - reach) / m)); x1 = min(self.width - 1, int((max(xs) + reach) / m))
        y0 = max(0, int((min(ys) - reach) / m)); y1 = min(self.height - 1, int((max(ys) + reach) / m))
        segs = list(zip(pts, pts[1:]))
        out = []
        for y in range(y0, y1 + 1):
            cy = (y + 0.5) * m
            for x in range(x0, x1 + 1):
                cx = (x + 0.5) * m
                d = min(_seg_dist(cx, cy, a[0], a[1], b[0], b[1]) for a, b in segs)
                cover = 0.5 - (d - half) / edge
                if cover > 0:
                    out.append((y * self.width + x, model.opacity * min(1.0, cover)))
        return out

    def delta_loss(self, target: 'Canvas', foot, color):
        """Variation de l'erreur quadratique si la touche était posée (sans modifier la toile)."""
        d, t, delta = self.data, target.data, 0.0
        for idx, a in foot:
            i = 3 * idx
            for k in range(3):
                old = d[i + k]; new = old + a * (color[k] - old)
                delta += (new - t[i + k]) ** 2 - (old - t[i + k]) ** 2
        return delta

    def apply(self, foot, color):
        d = self.data
        for idx, a in foot:
            i = 3 * idx
            for k in range(3):
                d[i + k] += a * (color[k] - d[i + k])

    def paint(self, stroke: Stroke, model: BrushModel):
        foot = self.footprint(stroke, model)
        self.apply(foot, stroke.color)
        return foot

    def loss(self, target: 'Canvas'):
        """Erreur quadratique moyenne par canal (0 = reproduction identique)."""
        return sum((a - b) ** 2 for a, b in zip(self.data, target.data)) / len(self.data)

    def error_map(self, target: 'Canvas'):
        d, t = self.data, target.data
        return [sum((d[3 * i + k] - t[3 * i + k]) ** 2 for k in range(3)) for i in range(self.width * self.height)]

    def mean_color(self, foot):
        if not foot:
            return (0.5, 0.5, 0.5)
        s, w = [0.0, 0.0, 0.0], 0.0
        for idx, a in foot:
            for k in range(3):
                s[k] += a * self.data[3 * idx + k]
            w += a
        return tuple(c / w for c in s)
