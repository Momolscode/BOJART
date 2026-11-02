"""Planification gloutonne de touches : chercher la touche qui réduit le plus l'écart à la cible."""
from __future__ import annotations

import math

from .canvas import BrushModel, Canvas, Stroke


def palette_kmeans(target: Canvas, k, rng, iters=12, sample=600):
    n = target.width * target.height
    idx = [rng.randrange(n) for _ in range(min(sample, n))]
    pts = [tuple(target.data[3 * i:3 * i + 3]) for i in idx]
    centers = [pts[rng.randrange(len(pts))]]
    while len(centers) < k:  # initialisation k-means++
        d = [min(sum((a - b) ** 2 for a, b in zip(p, c)) for c in centers) for p in pts]
        r, acc = rng.random() * sum(d), 0.0
        for p, w in zip(pts, d):
            acc += w
            if acc >= r:
                centers.append(p); break
        else:
            centers.append(pts[-1])
    for _ in range(iters):
        groups = [[] for _ in centers]
        for p in pts:
            groups[min(range(len(centers)), key=lambda j: sum((a - b) ** 2 for a, b in zip(p, centers[j])))].append(p)
        centers = [tuple(sum(c) / len(g) for c in zip(*g)) if g else centers[j] for j, g in enumerate(groups)]
    return centers


def _nearest(color, palette):
    return min(palette, key=lambda c: sum((a - b) ** 2 for a, b in zip(color, c)))


class Planner:
    def __init__(self, target: Canvas, style: dict, rng, candidates=12):
        self.target, self.style, self.rng, self.candidates = target, style, rng, candidates
        k = style.get('palette_size')
        self.palette = palette_kmeans(target, k, rng) if k else None
        lum = [0.299 * target.data[3 * i] + 0.587 * target.data[3 * i + 1] + 0.114 * target.data[3 * i + 2]
               for i in range(target.width * target.height)]
        self.lum = lum

    def _grad(self, x, y):
        w, h, L = self.target.width, self.target.height, self.lum
        gx = L[y * w + min(w - 1, x + 1)] - L[y * w + max(0, x - 1)]
        gy = L[min(h - 1, y + 1) * w + x] - L[max(0, y - 1) * w + x]
        return gx, gy

    def _angle(self, x, y):
        mode = self.style.get('orientation', 'libre')
        if mode == 'orthogonale':
            return self.rng.choice((0.0, math.pi / 2))
        if mode == 'contours':
            gx, gy = self._grad(x, y)
            if math.hypot(gx, gy) > 0.02:
                return math.atan2(gy, gx) + math.pi / 2 + self.rng.gauss(0, 0.15)
        return self.rng.uniform(0, math.pi)

    def _pick_pixel(self, err, tournament=24):
        n = len(err)
        best = max((self.rng.randrange(n) for _ in range(tournament)), key=lambda i: err[i])
        return best % self.target.width, best // self.target.width

    def propose(self, err, progress):
        x, y = self._pick_pixel(err)
        m = self.target.mm_per_px
        cx, cy = (x + 0.5) * m, (y + 0.5) * m
        w0, w1 = self.style['width_mm']
        width = max(m, (w0 + (w1 - w0) * progress) * self.rng.uniform(0.8, 1.2))
        length = self.rng.uniform(*self.style['length_mm'])
        a = self._angle(x, y)
        dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
        bend = self.style.get('curvature', 0.0) * length * self.rng.uniform(-1, 1)
        p1 = (cx - math.sin(a) * bend, cy + math.cos(a) * bend)
        return Stroke((cx - dx, cy - dy), p1, (cx + dx, cy + dy), width, (0, 0, 0))

    def best_stroke(self, canvas: Canvas, model: BrushModel, err, progress):
        best = None
        for _ in range(self.candidates):
            s = self.propose(err, progress)
            foot = canvas.footprint(s, model)
            if not foot:
                continue
            color = self.target.mean_color(foot)
            s.color = _nearest(color, self.palette) if self.palette else color
            delta = canvas.delta_loss(self.target, foot, s.color)
            if best is None or delta < best[0]:
                best = (delta, s, foot)
        return best

    def plan(self, canvas: Canvas, model: BrushModel, n, progress0=0.0, progress1=1.0):
        """Planifie `n` touches sur une copie de la toile observée, avec le modèle de dépôt supposé."""
        work = canvas.copy()
        err = work.error_map(self.target)
        out = []
        for i in range(n):
            progress = progress0 + (progress1 - progress0) * i / max(1, n)
            best = self.best_stroke(work, model, err, progress)
            if best is None or best[0] >= 0:
                continue
            delta, s, foot = best
            work.apply(foot, s.color)
            for idx, _ in foot:
                err[idx] = sum((work.data[3 * idx + k] - self.target.data[3 * idx + k]) ** 2 for k in range(3))
            s.meta['expected_delta'] = delta
            out.append(s)
        return out
