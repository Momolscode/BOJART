"""Détails sculptés réutilisables pour les personnages originaux BOJ.ART (2 novembre 2026).

Ajoutés après la remarque d'Olsen sur le manque de détails. Les tailles suivent la grille de
conception (`docs/m08/GRILLE_CONCEPTION_FIGURINE.md`) : un relief ou une gravure destiné au FDM
0,4 mm mesure au moins 0,8 mm de large et 0,5 mm de profondeur ; plus fin, il relève du niveau
« résine » et peut s'effacer en FDM sans fragiliser la pièce.

Toutes les fonctions prennent des points (..., 3) en millimètres et rendent une distance signée
approchée (négative à l'intérieur). Aucun personnage tiers n'est décrit ici.
"""
from __future__ import annotations

import numpy as np

from .sculpt import _len, limb, smin, sphere

FAR = np.float32(1e3)
TAU = 2.0 * np.pi


def v3(t):
    return np.asarray(t, np.float32)


def unit(t):
    t = v3(t)
    return t / np.linalg.norm(t)


def ortho(v, axis):
    """Composante de v orthogonale à axis, normalisée."""
    v, axis = v3(v), unit(axis)
    w = v - axis * float(axis @ v)
    return w / np.linalg.norm(w)


def local(p, c, half, fn):
    """N'évalue fn que dans la boîte de centre c et de demi-côtés half ; ailleurs FAR.

    Gain de calcul pour les petits éléments. La boîte doit dépasser la pièce d'au moins le rayon de
    fusion utilisé autour d'elle, sinon la fusion serait coupée net au bord de la boîte."""
    lo, hi = v3(c) - v3(half), v3(c) + v3(half)
    m = np.all((p >= lo) & (p <= hi), axis=-1)
    out = np.full(p.shape[:-1], FAR, np.float32)
    if m.any():
        out[m] = fn(p[m])
    return out


def engrave(d, band, depth):
    """Grave une rainure dans la pièce d : band < 0 dans la bande gravée, sur depth mm sous la surface."""
    return np.maximum(d, np.minimum(-band, d + depth))


def oriented(p, c, u, v):
    """Coordonnées locales (le long de u, de v et de w = u × v) ; u et v orthonormés."""
    q = p - v3(c)
    w = np.cross(u, v)
    return q @ u, q @ v, q @ w


def obox(p, c, u, v, half, r):
    """Boîte arrondie orientée (u, v orthonormés)."""
    a, b, c3 = oriented(p, c, u, v)
    q = np.stack([a, b, c3], axis=-1)
    dd = np.abs(q) - (v3(half) - r)
    return _len(np.maximum(dd, 0)) + np.minimum(dd.max(axis=-1), 0) - r


def oellipsoid(p, c, u, v, radii):
    a, b, c3 = oriented(p, c, u, v)
    radii = v3(radii)
    q = np.stack([a / radii[0], b / radii[1], c3 / radii[2]], axis=-1)
    return (_len(q) - 1.0) * float(radii.min())


def studs(p, centers, r):
    """Rivets : demi-sphères posées sur une surface (seule la moitié extérieure reste visible)."""
    centers = [v3(c) for c in centers]
    lo = np.min(centers, axis=0) - r - 2.0
    hi = np.max(centers, axis=0) + r + 2.0

    def fn(q):
        d = None
        for c in centers:
            s = sphere(q, c, r)
            d = s if d is None else np.minimum(d, s)
        return d
    return local(p, (lo + hi) / 2, (hi - lo) / 2, fn)


def ring(p, c, axis, r, half, rr=0.0):
    """Anneau plein (cylindre court) d'axe axis : rayon r, demi-épaisseur half, arêtes arrondies de rr.

    À préférer à une capsule pour un bord roulé ou un bourrelet : une capsule de même rayon s'étend
    d'un rayon de part et d'autre et se lit comme une boule (« bouée »)."""
    axis = unit(axis)
    q = p - v3(c)
    s = q @ axis
    rad = _len(q - s[..., None] * axis)
    dx, dy = rad - (r - rr), np.abs(s) - (half - rr)
    return (np.minimum(np.maximum(dx, dy), 0) + np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dy, 0) ** 2) - rr)


def hand_frame(a, f, side):
    """Repère de la main : a (auriculaire → index), f (avant-bras, orthogonalisé), g (dos de la main)."""
    a = unit(a)
    f = ortho(f, a)
    return a, f, np.cross(a, f) * side


def hand_wrist(c, a, f, side, length=5.4):
    """Point du poignet où raccorder l'avant-bras."""
    a, f, g = hand_frame(a, f, side)
    return v3(c) - f * (length + 3.0) + g * 0.9


def fist(p, c, a, f, side, fw=2.45, length=5.4, depth=4.6):
    """Poing fermé, éventuellement serré sur un manche d'axe a passant par c.

    a : de l'auriculaire vers l'index ; f : direction de l'avant-bras ; side : +1 main droite,
    -1 main gauche. Construction de sculpteur de figurines : masse en bloc (10 mm environ pour une
    tête de 23 mm), rangée de quatre jointures sur l'arête dos/avant, trois sillons entre les doigts
    sur l'avant et la paume (0,7 mm, niveau FDM limite), pouce replié sur l'index, raccord du poignet.
    Le manche, s'il existe, traverse la masse et dépasse de part et d'autre."""
    a, f, g = hand_frame(a, f, side)
    c = v3(c)
    hw = 2.0 * fw + 0.3
    core = obox(p, c + g * 0.9 + f * 0.4, f, a, (length, hw, depth), 2.0)
    q = p - c
    s, x = q @ a, q @ g
    for k in (-1, 0, 1):                                            # sillons entre les doigts
        core = engrave(core, np.maximum(np.abs(s - k * fw) - 0.36, x - 3.0), 0.65)
    knuckles = [c + a * ((1.5 - k) * fw) + g * (depth - 0.1) + f * (length - 0.6) for k in range(4)]
    d = smin(core, studs(p, knuckles, 1.45), 0.6)
    t0 = c + a * (hw + 0.2) - f * (length - 1.4) - g * (depth * 0.25)   # base du pouce (éminence)
    t1 = c + a * (hw - 0.4) + f * 0.8 - g * (depth - 0.2)
    t2 = c + a * (fw * 0.9) + f * (length - 0.4) - g * (depth - 1.4)    # pouce posé sur l'index
    d = smin(d, limb(p, t0, t1, 2.0, 1.6), 0.8)
    d = smin(d, limb(p, t1, t2, 1.6, 1.3), 0.5)
    w = hand_wrist(c, a, f, side, length)
    return smin(d, limb(p, w, c - f * (length - 1.5) + g * 0.9, 3.3, 3.6), 1.2)


def wrapped_grip(p, a, b, r, pitch=3.6, amp=0.3):
    """Poignée gainée : cuir enroulé en hélice (deux rubans, reliefs de 0,3 mm, niveau résine)."""
    a, b = v3(a), v3(b)
    ax = unit(b - a)
    e1 = ortho(np.array([0.0, 0.0, 1.0], np.float32) if abs(ax[2]) < 0.9 else np.array([1.0, 0.0, 0.0], np.float32), ax)
    e2 = np.cross(ax, e1)
    q = p - a
    s = q @ ax
    th = np.arctan2(q @ e2, q @ e1)
    ripple = amp * np.sin(TAU * s / pitch + 2.0 * th)
    return limb(p, a, b, r, r) - ripple


def pipe_folds(theta, t, n=13, amp=1.8, phase=0.0):
    """Plis tuyaux d'un tissu suspendu : amplitude nulle au point d'attache, maximale à l'ourlet."""
    return amp * (t ** 1.35) * np.sin(n * theta + phase + 0.9 * np.sin(3.0 * theta))
