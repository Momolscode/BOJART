"""Peintre haute définition (numpy, facultatif) : touches du gros au fin, texture de poils,
monde « physique » caché, recalage largeur/opacité et replanification par lots.

Même boucle que `loop.py`, vectorisée pour des toiles de quelques centaines de pixels
(2 mm/pixel par défaut). Nécessite numpy ; Pillow seulement pour lire une image.
Le monde physique reste un modèle : aucune peinture réelle n'est mesurée ici.
"""
from __future__ import annotations

import math
import time

import numpy as np

HD_STYLES = {
    'reproduction': dict(width_mm=(30, 4), length_ratio=(0.8, 4.0), curvature=0.25, palette=None),
    'fin': dict(width_mm=(30, 2.5), length_ratio=(1.0, 5.0), curvature=0.3, palette=None),
    'empattement': dict(width_mm=(24, 7), length_ratio=(1.2, 2.5), curvature=0.1, palette=12),
    'tres_fin': dict(width_mm=(30, 1.5), length_ratio=(1.0, 6.0), curvature=0.3, palette=None),
    # Premier atelier réel : 10 peintures pré-mélangées, trois pinceaux, pas de mélange automatique.
    'atelier_3_semaines': dict(width_mm=(20, 3), brushes_mm=(20, 8, 3), brush_phases=(0.25, 0.6),
                               length_ratio=(1.0, 4.0), curvature=0.25, palette=10),
    # Pinceau mesuré : largeurs et longueur maximale lues dans l'atlas (`HDPainter(..., atlas=...)`).
    'pinceau_mesure': dict(width_mm=None, length_ratio=(1.0, 10.0), curvature=0.3, palette=10),
}


def ssim(a, b, k=3):
    """SSIM moyen sur la luminance, fenêtre carrée (2k+1)² : 1 = images identiques."""
    w = np.array([0.299, 0.587, 0.114], dtype=np.float32)
    x, y = a @ w, b @ w
    mx, my = _box_blur(x, k), _box_blur(y, k)
    vx = _box_blur(x * x, k) - mx * mx; vy = _box_blur(y * y, k) - my * my; cxy = _box_blur(x * y, k) - mx * my
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    return float((((2 * mx * my + c1) * (2 * cxy + c2)) / ((mx * mx + my * my + c1) * (vx + vy + c2))).mean())


class Deposit:
    def __init__(self, gain, opacity):
        self.gain, self.opacity = float(gain), float(opacity)

    def as_dict(self):
        return {'width_gain': round(self.gain, 3), 'opacity': round(self.opacity, 3)}


def _box_blur(a, k):
    p = np.pad(a, k, mode='edge')
    c = np.pad(np.cumsum(np.cumsum(p, 0), 1), ((1, 0), (1, 0)))
    s = 2 * k + 1
    return (c[s:, s:] - c[:-s, s:] - c[s:, :-s] + c[:-s, :-s]) / (s * s)


def load_image(path, width_px):
    from PIL import Image  # facultatif
    img = Image.open(path).convert('RGB')
    h = round(width_px * img.height / img.width)
    return np.asarray(img.resize((width_px, h), Image.LANCZOS), dtype=np.float32) / 255


class HDPainter:
    def __init__(self, target, style='reproduction', mm_per_px=2.0, seed=1,
                 hidden=Deposit(1.15, 0.82), believed=Deposit(1.0, 0.95),
                 position_sigma_mm=0.35, color_sigma=0.015, camera_sigma=0.006, atlas=None):
        self.T = np.asarray(target, dtype=np.float32)
        self.atlas = atlas
        if self.style_needs_atlas(style) and atlas is None:
            raise ValueError(f'le style {style!r} demande un atlas de touches mesurées')
        self.H, self.W = self.T.shape[:2]
        self.mm, self.style = mm_per_px, HD_STYLES[style]
        self.rng = np.random.default_rng(seed)
        self.hidden, self.believed = hidden, believed
        self.pos_sigma, self.color_sigma, self.cam_sigma = position_sigma_mm, color_sigma, camera_sigma
        lum = self.T @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        gy, gx = np.gradient(_box_blur(lum, 3))
        self.gx, self.gy = _box_blur(gx, 4), _box_blur(gy, 4)
        self.mag = np.hypot(self.gx, self.gy)
        self.palette = self._palette(self.style['palette']) if self.style['palette'] else None
        self.world = np.ones_like(self.T)

    def _palette(self, k):
        px = self.T.reshape(-1, 3)[self.rng.choice(self.W * self.H, min(4000, self.W * self.H))]
        c = px[self.rng.choice(len(px), k, replace=False)]
        for _ in range(20):
            lab = ((px[:, None] - c[None]) ** 2).sum(-1).argmin(1)
            c = np.array([px[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
        return c

    @staticmethod
    def style_needs_atlas(style):
        return HD_STYLES[style]['width_mm'] is None

    def footprint(self, p0, p1, p2, width_mm, dep, seed, bristle=True):
        if self.atlas is not None:  # touche mesurée : sa texture remplace les stries modélisées
            return self.atlas.footprint(p0, p1, p2, width_mm, self.mm, dep.gain, dep.opacity, (self.H, self.W))
        t = np.linspace(0, 1, 12)[:, None]
        P = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
        half = width_mm * dep.gain / 2 / self.mm
        x0 = int(max(0, P[:, 0].min() - half - 2)); x1 = int(min(self.W, P[:, 0].max() + half + 3))
        y0 = int(max(0, P[:, 1].min() - half - 2)); y1 = int(min(self.H, P[:, 1].max() + half + 3))
        if x1 <= x0 or y1 <= y0:
            return None
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        best = np.full(xx.shape, 1e9, np.float32); along = np.zeros_like(best); side = np.zeros_like(best)
        for i in range(11):
            a, v = P[i], P[i + 1] - P[i]
            lv = float(v @ v) or 1e-6
            u = np.clip(((xx + .5 - a[0]) * v[0] + (yy + .5 - a[1]) * v[1]) / lv, 0, 1)
            dx = xx + .5 - a[0] - u * v[0]; dy = yy + .5 - a[1] - u * v[1]
            d = np.hypot(dx, dy); m = d < best
            best[m] = d[m]; along[m] = (i + u[m]) / 11
            side[m] = (np.sign(dx * v[1] - dy * v[0]) * d)[m]
        cov = np.clip(0.5 - (best - half) / 1.2, 0, 1)
        if bristle:  # stries de poils parallèles au tracé, charge qui s'épuise en fin de touche
            r = np.random.default_rng(seed)
            k, ph = r.uniform(0.6, 1.4), r.uniform(0, 6.28)
            rel = side / max(half, 1)
            cov = cov * (0.82 + 0.18 * np.sin(rel * 7 * k + ph) * np.sin(rel * 2.3 + ph * 1.7)) * (1 - 0.35 * along ** 1.5)
        a = dep.opacity * cov
        return (y0, y1, x0, x1, a) if a.max() > 0.01 else None

    def _delta(self, C, fp, col):
        y0, y1, x0, x1, a = fp
        old, tg = C[y0:y1, x0:x1], self.T[y0:y1, x0:x1]
        new = old + a[..., None] * (col - old)
        return float(((new - tg) ** 2).sum() - ((old - tg) ** 2).sum())

    @staticmethod
    def _apply(C, fp, col):
        y0, y1, x0, x1, a = fp
        C[y0:y1, x0:x1] += a[..., None] * (col - C[y0:y1, x0:x1])

    def _propose(self, err, progress):
        flat = err.ravel(); idx = self.rng.integers(0, flat.size, 48)
        y, x = divmod(int(idx[flat[idx].argmax()]), self.W)
        if 'brushes_mm' in self.style:  # pinceaux discrets : le grand, puis le moyen, puis le fin
            phase = sum(progress >= x for x in self.style['brush_phases'])
            width = self.style['brushes_mm'][phase] * self.rng.uniform(0.95, 1.05)
        else:
            w0, w1 = self.style['width_mm'] or self.atlas.width_range[::-1]
            width = w0 * (w1 / w0) ** progress * self.rng.uniform(0.8, 1.2)
        length = width * self.rng.uniform(*self.style['length_ratio'])
        if self.atlas is not None:
            width = float(np.clip(width, *self.atlas.width_range))
            length = min(length, self.atlas.max_length_mm)
        if self.mag[y, x] > 0.004:
            ang = math.atan2(self.gy[y, x], self.gx[y, x]) + math.pi / 2 + self.rng.normal(0, 0.12)
        else:
            ang = self.rng.uniform(0, math.pi)
        c = np.array([x + .5, y + .5])
        dv = np.array([math.cos(ang), math.sin(ang)]) * length / 2 / self.mm
        nv = np.array([-dv[1], dv[0]]) * self.style['curvature'] * self.rng.uniform(-1, 1)
        return c - dv, c + nv, c + dv, width

    def _color(self, fp):
        y0, y1, x0, x1, a = fp
        w = a[..., None]
        col = (self.T[y0:y1, x0:x1] * w).sum((0, 1)) / max(float(w.sum()), 1e-6)
        if self.palette is not None:
            col = self.palette[((self.palette - col) ** 2).sum(1).argmin()]
        return col

    def observe(self):
        noise = self.rng.normal(0, self.cam_sigma, self.world.shape).astype(np.float32)
        return np.clip(self.world + noise, 0, 1)

    def run(self, n_strokes, batches=8, candidates=8, calibration_strokes=4, snapshots=(0.125, 1 / 3, 2 / 3),
            record=False, group_by_color=False):
        """`record=True` ajoute `executed` : chaque touche telle qu'exécutée (pixels, largeur, graine,
        couleur), pour la rejouer à l'identique, par exemple dans une animation du bras.

        `group_by_color=True` exécute chaque lot du plus gros au plus fin pinceau puis pot par pot, comme
        un peintre qui limite les rinçages ; l'ordre des recouvrements change, la boucle fermée corrige
        au lot suivant."""
        executed = []
        gains = np.arange(0.85, 1.36, 0.05); ops = np.arange(0.6, 1.01, 0.05)
        table = np.zeros((len(gains), len(ops)))
        per = max(1, n_strokes // batches); done = 0; log = []; snaps = {}
        marks = {int(n_strokes * s) for s in snapshots}
        t0 = time.perf_counter(); obs = self.observe()
        for b in range(batches):
            C = obs.copy(); err = ((C - self.T) ** 2).sum(-1); plan = []
            for i in range(per):
                progress = min(1.0, (b * per + i) / n_strokes); best = None
                for _ in range(candidates):
                    p0, p1, p2, w = self._propose(err, progress)
                    seed = int(self.rng.integers(1 << 30))
                    fp = self.footprint(p0, p1, p2, w, self.believed, seed)
                    if fp is None:
                        continue
                    col = self._color(fp); dl = self._delta(C, fp, col)
                    if best is None or dl < best[0]:
                        best = (dl, (p0, p1, p2, w, seed), fp, col)
                if best is None or best[0] >= 0:
                    continue
                self._apply(C, best[2], best[3])
                y0, y1, x0, x1, _ = best[2]
                err[y0:y1, x0:x1] = ((C[y0:y1, x0:x1] - self.T[y0:y1, x0:x1]) ** 2).sum(-1)
                plan.append((best[1], best[3]))
            if group_by_color and self.palette is not None:
                sizes = self.style.get('brushes_mm')
                brush = (lambda w: min(range(len(sizes)), key=lambda k: abs(sizes[k] - w))) if sizes else (lambda w: -round(w))  # noqa: E731
                pot = lambda c: int(((self.palette - c) ** 2).sum(1).argmin())  # noqa: E731
                plan.sort(key=lambda item: (brush(item[0][3]), pot(item[1])))
            for j, ((p0, p1, p2, w, seed), col) in enumerate(plan):
                jit = self.rng.normal(0, self.pos_sigma / self.mm, 2)
                colr = np.clip(col + self.rng.normal(0, self.color_sigma, 3), 0, 1)
                fp = self.footprint(p0 + jit, p1 + jit, p2 + jit, w, self.hidden, seed)
                before = self.observe() if j < calibration_strokes else None
                if fp is not None:
                    self._apply(self.world, fp, colr)
                    if record:
                        executed.append({'batch': b, 'p': [p0 + jit, p1 + jit, p2 + jit], 'width_mm': float(w),
                                         'seed': seed, 'color': colr.copy()})
                if before is not None:
                    after = self.observe()
                    for gi, g in enumerate(gains):
                        f = self.footprint(p0, p1, p2, w, Deposit(g, 1.0), seed)
                        if f is None:
                            continue
                        y0, y1, x0, x1, a = f
                        for oi, o in enumerate(ops):
                            pred = before[y0:y1, x0:x1] + (o * a)[..., None] * (col - before[y0:y1, x0:x1])
                            table[gi, oi] += ((pred - after[y0:y1, x0:x1]) ** 2).sum()
                done += 1
                if done in marks:
                    snaps[done] = self.world.copy()
            if table.any():
                gi, oi = np.unravel_index(table.argmin(), table.shape)
                self.believed = Deposit(gains[gi], ops[oi])
            obs = self.observe()
            mse = float(((self.world - self.T) ** 2).mean())
            log.append({'batch': b + 1, 'strokes': done, 'mse': round(mse, 5),
                        'psnr_db': round(10 * math.log10(1 / mse), 2), 'ssim': round(ssim(self.world, self.T), 4),
                        'believed': self.believed.as_dict(),
                        'seconds': round(time.perf_counter() - t0, 1)})
        snaps[done] = self.world.copy()
        extra = {'executed': executed} if record else {}
        return {**extra, 'log': log, 'strokes': done, 'final_mse': log[-1]['mse'], 'psnr_db': log[-1]['psnr_db'],
                'ssim': log[-1]['ssim'],
                'hidden': self.hidden.as_dict(), 'learned': self.believed.as_dict(),
                'grid_px': [self.W, self.H], 'mm_per_px': self.mm, 'snapshots': snaps}
