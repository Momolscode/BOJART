"""« Ardoise, le duelliste des strates » : guerrier original BOJ.ART (2 novembre 2026).

Création propre à BOJ.ART, choisie par Olsen comme personnage vendable à la place d'un personnage
sous droits. Signes distinctifs : crâne rasé gravé de strates sur la tempe gauche, cicatrice sur le
sourcil gauche, tresse épaisse passée sur l'épaule droite, long manteau ouvert devant et fendu dans le
dos, une seule épaulière faite de plaques empilées comme des strates d'ardoise, cuirasse en strates
rivetée, grande lame à deux mains au profil en gradins. Garde-fous de distinction : aucune chevelure
dressée, aucune armure à épaulettes symétriques ni combinaison, aucune pose de tir d'énergie ni
signature empruntée.

Version 6 (passe « détails », grille `docs/m08/GRILLE_CONCEPTION_FIGURINE.md`) : tête ramenée à
7,4 têtes de haut, visage construit (arcades, orbites, paupières, nez, lèvres, pommettes, mâchoire,
oreilles), mains à doigts refermées sur la poignée, musculature du bras nu, plis tuyaux et ourlet
ondulé du manteau, rivets, gravures, poignée gainée, lame à gouttière et tranchants biseautés.

Mêmes conventions que la Sentinelle : millimètres, z vers le haut, face vers -y, semelles à z = 0.
"""
from __future__ import annotations

import numpy as np

from .details import (engrave, fist, hand_wrist, local, obox, oellipsoid, ortho, pipe_folds, ring, studs, unit,
                      v3, wrapped_grip)
from .sculpt import ellipsoid, limb, rounded_box, smin, sphere, ssub

ARDOISE_VERSION = 'bojart.ardoise.sdf.v6'
BOUNDS = ((-95.0, -95.0, -6.0), (95.0, 95.0, 235.0))
# Les détails (gravures de 0,8 mm) demandent une grille plus fine et un lissage plus court.
DETAIL = {'voxel': 0.4, 'smooth_iterations': 3}
# Socle assorti au personnage : plaques d'ardoise empilées (fabrication._strata_base).
SOCLE = 'strates'

# Trois intentions légères. « blade » : garde (ou prise en main), direction de la pointe, axe de la
# largeur, longueurs de lame et de poignée ; « hands » : main refermée sur la poignée à s mm de la
# garde, ou poing ; « flow » : déport du bas du manteau (mouvement, vent).
POSES = {
    'serment': {
        'label': 'Serment : lame plantée devant, deux mains sur la poignée, menton levé',
        'pelvis': (0, 0, 92), 'chest': (0, 0, 127), 'neck': (0, 1, 146), 'head': (0, 0.5, 160),
        'hip_l': (-11, 0, 90), 'knee_l': (-15, -3, 50), 'ankle_l': (-18, 0, 9),
        'hip_r': (11, 0, 90), 'knee_r': (15, -3, 50), 'ankle_r': (18, 0, 9),
        'sh_l': (-25, 1, 140), 'el_l': (-30, -12, 114), 'wr_l': (-2, -31, 96),
        'sh_r': (25, 1, 140), 'el_r': (30, -12, 117), 'wr_r': (2, -31, 104),
        'blade': {'guard': (0, -32, 84), 'dir': (0, 0, -1), 'width_axis': (1, 0, 0), 'length': 84, 'handle': 25},
        'hands': {'l': ('grip', 7.5), 'r': ('grip', 17.6)},
        'flow': (0, 8, 0),
    },
    'defi': {
        'label': 'Défi : lame posée sur l’épaule, main sur la hanche, appui sur une jambe',
        'pelvis': (2, 0, 90), 'chest': (0, 1, 125), 'neck': (-1, 2, 144), 'head': (-1.5, 1.5, 158),
        'hip_l': (-9, 0, 89), 'knee_l': (-14, 2, 49), 'ankle_l': (-17, 4, 9),
        'hip_r': (13, 0, 88), 'knee_r': (19, -12, 49), 'ankle_r': (21, -14, 9),
        'sh_l': (-25, 2, 138), 'el_l': (-38, 5, 115), 'wr_l': (-22, 3, 97),
        'sh_r': (25, 2, 138), 'el_r': (34, -13, 118), 'wr_r': (19, -19, 134),
        'blade': {'grip': (19, -19, 134), 'dir': (0.25, 0.62, 0.74), 'width_axis': (1, 0, 0), 'length': 80, 'handle': 24},
        'hands': {'l': ('fist', (0.15, -1.0, 0.35), (-24.5, 3.5, 96.0)), 'r': ('grip', 8.0)},
        'flow': (6, 10, 0),
    },
    'garde': {
        'label': 'Garde : lame tenue à deux mains, pointe vers l’avant, fente légère',
        'pelvis': (0, 0, 84), 'chest': (0, -3, 118), 'neck': (0, -5, 136), 'head': (0, -6.5, 150),
        'hip_l': (-11, 0, 82), 'knee_l': (-17, -16, 46), 'ankle_l': (-22, -22, 9),
        'hip_r': (11, 0, 82), 'knee_r': (16, 14, 44), 'ankle_r': (21, 24, 9),
        'sh_l': (-24, -3, 131), 'el_l': (-25, -16, 108), 'wr_l': (-2, -25, 97),
        'sh_r': (24, -3, 131), 'el_r': (25, -15, 112), 'wr_r': (4, -27, 104),
        'blade': {'grip': (2, -26, 101), 'dir': (-0.15, -0.62, 0.77), 'width_axis': (1, 0, 0), 'length': 74, 'handle': 22},
        'hands': {'l': ('grip', 17.0), 'r': ('grip', 7.2)},
        'flow': (0, 14, 4),
    },
}
# Intentions de la demande (« combat », « repos ») traduites en pose de ce personnage.
INTENT_POSES = {'combat': 'garde', 'rest': 'serment'}

HANDLE_R = 2.7


def _blade_frame(P):
    b = P['blade']
    u = unit(b['dir'])
    width = ortho(b['width_axis'], u)
    guard = v3(b['guard']) if 'guard' in b else v3(b['grip']) + u * 8
    return u, width, guard, b['length'], b['handle']


def coat(p, top, bot, r_top, r_bot, half_t, front_open=0.32, slit_from=0.45, folds=13, fold_amp=1.8, phase=0.0):
    """Manteau : coque elliptique conique ouverte devant, fendue dans le dos, plis tuyaux qui
    s'ouvrent vers le bas et ourlet ondulé (épaisseur constante : les plis déplacent la coque)."""
    top, bot = v3(top), v3(bot)
    zt, zb = float(top[2]), float(bot[2])
    t = np.clip((zt - p[..., 2]) / (zt - zb), 0.0, 1.0)
    cx = top[0] + (bot[0] - top[0]) * t
    cy = top[1] + (bot[1] - top[1]) * t
    rx = r_top[0] + (r_bot[0] - r_top[0]) * t
    ry = r_top[1] + (r_bot[1] - r_top[1]) * t
    xr, yr = p[..., 0] - cx, p[..., 1] - cy
    theta = np.arctan2(yr / ry, xr / rx)
    rho = np.sqrt((xr / rx) ** 2 + (yr / ry) ** 2)
    radial = (rho - 1.0) * np.minimum(rx, ry) - pipe_folds(theta, t, folds, fold_amp, phase)
    shell = np.abs(radial) - (half_t + 0.8 * np.clip((t - 0.9) * 10, 0, 1))   # ourlet épaissi
    hem = zb + 1.3 * np.sin(folds * theta + phase + 0.9 * np.sin(3.0 * theta))
    d = np.maximum(shell, np.maximum(p[..., 2] - zt, hem - p[..., 2]))
    d = np.maximum(d, -(yr + front_open * ry))                                   # ouvert devant
    slit = np.maximum(np.abs(xr) - 1.4, np.maximum(-yr, (t < slit_from) * 1e3 - 1e-3))
    return np.maximum(d, -slit)                                                  # fente dans le dos


def _braid(p, pts, r=3.7, spacing=4.2):
    """Tresse à trois brins : mèches en ellipsoïdes inclinés, alternés de part et d'autre de l'axe."""
    pts = [v3(x) for x in pts]
    d = None
    i = 0
    for a, b in zip(pts[:-1], pts[1:]):
        seg = b - a
        ax = unit(seg)
        n = max(1, int(np.linalg.norm(seg) // spacing))
        side = np.cross(ax, v3((0, 0, 1)) if abs(ax[2]) < 0.9 else v3((1, 0, 0)))
        side = side / np.linalg.norm(side)
        for k in range(n):
            sgn = 1.0 if i % 2 else -1.0
            c = a + seg * (k / n) + side * (1.15 * sgn)
            lobe_ax = unit(ax - side * (0.85 * sgn))
            s = oellipsoid(p, c, lobe_ax, ortho(side, lobe_ax), (r * 0.98, r * 0.66, r * 0.7))
            d = s if d is None else smin(d, s, 0.45)
            i += 1
    core = None
    for a, b in zip(pts[:-1], pts[1:]):
        c2 = limb(p, a, b, r * 0.55, r * 0.55)
        core = c2 if core is None else np.minimum(core, c2)
    d = smin(d, core, 0.6)
    end = pts[-1]
    d = smin(d, limb(p, end - v3((0, 0, 0.9)), end + v3((0, 0, 0.9)), r + 0.55, r + 0.55), 0.5)   # ligature
    tuft = limb(p, end - v3((0, 0, 1.2)), end + v3((0, -0.6, -7.5)), r * 0.85, 0.9)
    return smin(d, tuft, 0.8)                                                    # mèche finale effilée


def _blade(p, P):
    """Lame à trois gradins, section en losange (tranchants biseautés), gouttière gravée, garde à
    embouts, poignée gainée de cuir, pommeau à gorge."""
    u, width, guard, L, H = _blade_frame(P)
    w = np.cross(u, width)
    q = p - guard
    a, b, c = q @ u, q @ width, q @ w
    d = None
    for k, half_w in enumerate((7.6, 6.7, 5.8)):                               # trois gradins (strates)
        a0, a1 = L * k / 3.0 + 1.5, L * (k + 1) / 3.0 + 1.5
        along = np.abs(a - (a0 + a1) / 2) - ((a1 - a0) / 2 + 0.6)               # recouvrement : pas de face interne
        across = np.abs(b) - half_w
        thick = np.abs(c) - (2.05 - 0.95 * np.clip(np.abs(b) / 7.6, 0, 1))      # faces continues d'un gradin à l'autre
        seg = np.maximum(np.maximum(along, across), thick * 0.85)
        d = seg if d is None else np.minimum(d, seg)
    tip = guard + u * (L + 1.5)
    d = smin(d, obox(p, tip - u * 3, u, width, (4.0, 4.3, 1.5), 1.2), 1.0)     # pointe émoussée
    fuller = np.maximum(np.abs(b) - 1.1, np.maximum(np.abs(a - L * 0.38) - L * 0.32, -1e3))
    d = engrave(d, fuller, 0.7)                                                 # gouttière, deux faces
    gd = obox(p, guard, u, width, (3.0, 20.0, 3.4), 1.4)                        # garde droite
    for sgn in (-1, 1):
        gd = smin(gd, sphere(p, guard + width * (21.2 * sgn), 3.7), 1.0)       # embouts
    gd = np.minimum(gd, obox(p, guard - u * 0.2, u, width, (4.4, 5.2, 4.6), 1.6))   # bloc central
    gd = engrave(gd, np.abs(a + 0.2) - 0.45, 0.5)                               # filet sur la garde
    d = smin(d, gd, 0.8)
    d = smin(d, wrapped_grip(p, guard - u * 2, guard - u * H, HANDLE_R), 0.8)   # poignée gainée
    pom = limb(p, guard - u * (H + 1.5), guard - u * (H + 5.5), 4.6, 4.6)
    pom = engrave(pom, np.abs(a + H + 3.5) - 0.45, 0.55)                        # gorge du pommeau
    d = smin(d, pom, 0.8)
    return d


def _plate(p, c, u, v, radii, out_dir, rivets=2):
    """Plaque d'armure : ellipsoïde aplati, filet gravé parallèle au bord, rivets sur la face extérieure."""
    u, v = unit(u), ortho(v, u)
    w = np.cross(u, v)
    q = p - v3(c)
    a, b = q @ u, q @ v
    plate = oellipsoid(p, c, u, v, radii)
    n2 = np.sqrt((a / radii[0]) ** 2 + (b / radii[1]) ** 2)
    plate = engrave(plate, np.abs(n2 - 0.72) * min(radii[0], radii[1]) - 0.42, 0.5)
    sgn = 1.0 if float(w @ v3(out_dir)) >= 0 else -1.0
    pts = []
    for k in range(rivets):                                                       # 0 : sans rivet
        aa = radii[0] * (0.5 if rivets == 1 else (-0.5 + k / (rivets - 1))) * 0.9
        bb = radii[1] * 0.0
        ww = radii[2] * np.sqrt(max(0.0, 1 - (aa / radii[0]) ** 2 - (bb / radii[1]) ** 2))
        pts.append(v3(c) + u * aa + v * bb + w * (ww * sgn))
    return np.minimum(plate, studs(p, pts, 0.8)) if pts else plate


def _head(p, h):
    """Tête de 22,8 mm (7,4 têtes de haut) : crâne rasé, visage construit, oreilles, cicatrice et
    strates gravées sur la tempe gauche."""
    def at(x, y, z):
        return h + v3((x, y, z))
    d = ellipsoid(p, at(0, 1.4, 1.6), (9.2, 10.6, 9.2))                          # crâne
    d = smin(d, ellipsoid(p, at(0, -5.5, 3.0), (7.4, 4.6, 5.8)), 2.5)            # front
    d = smin(d, rounded_box(p, at(0, -5.2, -4.2), (6.4, 4.6, 5.4), 3.2), 2.2)    # masse du visage
    for sx in (-1, 1):
        d = smin(d, limb(p, at(sx * 7.9, 0.4, -3.6), at(sx * 3.9, -6.4, -10.4), 2.6, 2.3), 2.0)   # mâchoire
        d = smin(d, ellipsoid(p, at(sx * 5.6, -7.2, -2.2), (2.2, 1.8, 1.4)), 1.6)                  # pommette
        d = smin(d, limb(p, at(sx * 6.6, -8.6, 2.6), at(sx * 1.4, -10.0, 1.7), 1.15, 1.15), 1.4)   # arcade
    d = smin(d, ellipsoid(p, at(0, -7.4, -10.6), (4.4, 2.8, 2.2)), 1.6)          # menton
    d = smin(d, sphere(p, at(0, -10.0, 1.5), 1.2), 1.0)                          # glabelle
    for sx in (-1, 1):
        d = ssub(d, sphere(p, at(sx * 3.9, -10.4, 0.4), 1.6), 0.5)              # orbite
        d = np.minimum(d, sphere(p, at(sx * 3.9, -8.6, 0.0), 1.5))              # globe oculaire
        d = smin(d, limb(p, at(sx * 5.5, -9.6, 0.9), at(sx * 2.4, -9.95, 1.05), 0.55, 0.55), 0.3)  # paupière
    d = smin(d, limb(p, at(0, -9.9, 0.6), at(0, -11.9, -4.6), 1.1, 1.55), 0.8)  # arête du nez
    d = smin(d, sphere(p, at(0, -12.0, -4.9), 1.55), 0.6)                       # bout du nez
    for sx in (-1, 1):
        d = smin(d, sphere(p, at(sx * 1.55, -10.7, -5.4), 1.05), 0.6)          # ailes du nez
    d = smin(d, oellipsoid(p, at(0, -10.0, -7.3), v3((1, 0, 0)), v3((0, 0, 1)), (2.9, 0.95, 1.1)), 0.6)  # lèvre sup.
    d = smin(d, oellipsoid(p, at(0, -9.7, -8.6), v3((1, 0, 0)), v3((0, 0, 1)), (2.5, 0.9, 1.1)), 0.6)   # lèvre inf.
    d = engrave(d, np.maximum(np.abs(p[..., 2] - (h[2] - 7.95)) - 0.25, np.abs(p[..., 0] - h[0]) - 2.4), 0.45)  # bouche
    for sx in (-1, 1):
        ear = oellipsoid(p, at(sx * 9.4, 1.0, -1.6), v3((1, 0, 0)), v3((0, 1, 0)), (1.6, 3.0, 4.2))
        ear = ssub(ear, sphere(p, at(sx * 10.7, 0.6, -2.0), 1.6), 0.4)        # conque
        ear = smin(ear, sphere(p, at(sx * 9.4, 0.6, -5.4), 1.2), 0.6)          # lobe
        d = smin(d, ear, 0.6)
    # Cicatrice sur le sourcil gauche (gravée, 0,85 mm).
    scar = limb(p, at(-6.4, -9.2, 4.6), at(-3.8, -10.3, -1.0), 0.4, 0.4)
    d = engrave(d, scar, 0.4)
    # Strates gravées sur la tempe gauche du crâne rasé : deux lignes ondulées.
    rel = p - h
    for k in range(2):
        band = np.abs(rel[..., 2] - (4.2 + 2.4 * k) - 0.4 * np.sin(0.55 * rel[..., 1])) - 0.42
        band = np.maximum(band, np.maximum(rel[..., 0] + 5.2, np.abs(rel[..., 1] - 2.0) - 7.0))
        d = engrave(d, band, 0.45)
    return d


def _arm(p, sh, el, wr, up, bare):
    """Bras : deltoïde, biceps, triceps, avant-bras (long supinateur), brassard cerclé et riveté."""
    sh, el, wr = v3(sh), v3(el), v3(wr)
    ua = unit(el - sh)
    fa = unit(wr - el)
    front = ortho(v3((0, -1, 0)), ua)
    out = ortho(v3((sh[0], 0, 0)) if abs(sh[0]) > 1 else v3((1, 0, 0)), ua)
    L1 = float(np.linalg.norm(el - sh))
    d = limb(p, sh, el, 6.6, 5.2)
    if bare:
        d = smin(d, limb(p, sh + up * 1.2 + out * 1.8, sh + ua * (L1 * 0.45) + out * 1.2, 7.4, 3.9), 2.0)  # deltoïde
    d = smin(d, oellipsoid(p, sh + ua * (L1 * 0.58) + front * 2.3, ua, front, (L1 * 0.27, 3.7, 3.9)), 1.6)  # biceps
    d = smin(d, oellipsoid(p, sh + ua * (L1 * 0.45) - front * 2.2, ua, front, (L1 * 0.32, 3.5, 3.9)), 1.6)  # triceps
    d = smin(d, limb(p, el, wr, 5.6, 4.1), 2.0)
    fo = ortho(out, fa)
    d = smin(d, oellipsoid(p, el + fa * 5.0 + fo * 1.5, fa, fo, (7.0, 3.5, 3.5)), 1.6)   # long supinateur
    # Brassard : tube évasé vers le coude et coupé net aux deux bouts, deux bords roulés (1,2 mm de
    # large, 0,55 mm de relief : niveau FDM), deux rivets. Des capsules à la place des bords roulés
    # faisaient des « bouées » (v6, premier rendu).
    a, b = el * 0.45 + wr * 0.55, wr - fa * 0.8
    lb = float(np.linalg.norm(b - a))
    s = (p - a) @ fa
    br = np.maximum(limb(p, a, b, 5.3, 4.4), np.maximum(-s, s - lb))
    for t in (0.07, 0.93):
        br = np.minimum(br, ring(p, a + (b - a) * t, fa, 5.3 - 0.9 * t + 0.55, 0.6, 0.3))
    br = np.minimum(br, studs(p, [a + (b - a) * t + fo * (5.3 - 0.9 * t) for t in (0.36, 0.64)], 0.85))
    return smin(d, br, 1.0)


def _leg(p, hip, knee, ank):
    """Jambe : pantalon (plis de compression au-dessus de la botte, plis derrière le genou),
    genouillère en deux plaques rivetées, botte à semelle, talon, sangles et boucle."""
    hip, knee, ank = v3(hip), v3(knee), v3(ank)
    d = smin(limb(p, hip, knee, 9.4, 7.2), limb(p, knee, ank, 7.2, 5.8), 3.0)
    kd = unit(knee - hip)
    kf = ortho(v3((0, -1, 0)), kd)
    rel = p - knee
    for zk in (-2.6, 0.4):                                                       # plis derrière le genou
        band = np.maximum(np.abs(rel @ kd - zk) - 0.45, rel @ kf + 3.5)
        d = engrave(d, band, 0.6)
    shin = unit(knee - ank)
    ls = float(np.linalg.norm(knee - ank))
    for hz in (18.2, 20.0, 21.8):                     # plis de compression : bourrelets de 1,1 mm, relief 0,6 mm
        d = smin(d, ring(p, ank + shin * hz, shin, 5.8 + 1.4 * hz / ls + 0.6, 0.55, 0.45), 0.3)
    side = ortho(v3((1, 0, 0)), kd)
    # Genouillère en strates, comme la cuirasse : trois bandes horizontales décalées en marches. Pas
    # d'arête centrale ni de rivets côte à côte (lecture « visage » constatée sur les rendus).
    cop_c = knee + kf * 5.4 - kd * 0.4
    hk = (p - cop_c) @ kd
    for (h0, h1), off in (((-6.2, -2.1), 1.4), ((-2.1, 2.0), 0.7), ((2.0, 6.0), 0.0)):   # tuiles : le haut recouvre
        shell = oellipsoid(p, cop_c + kf * off, side, kd, (6.6, 6.4, 2.9))
        d = np.minimum(d, np.maximum(shell, np.abs(hk - (h0 + h1) / 2) - (h1 - h0) / 2))
    boot = smin(rounded_box(p, ank + v3((0, -4, -3.8)), (8.6, 14.0, 5.2), 3.0),
                limb(p, ank, ank + v3((0, 0, 15)), 7.6, 7.4), 2.5)
    boot = smin(boot, ellipsoid(p, ank + v3((0, -14.5, -4.6)), (7.2, 4.6, 4.2)), 1.5)        # bout renforcé
    boot = np.minimum(boot, limb(p, ank + v3((0, 0, 14.5)), ank + v3((0, 0, 17)), 8.4, 8.4))  # revers
    boot = np.minimum(boot, rounded_box(p, v3((ank[0], ank[1] - 4, 1.2)), (9.4, 14.8, 1.2), 0.6))   # semelle
    boot = np.minimum(boot, rounded_box(p, v3((ank[0], ank[1] + 6.5, 2.4)), (8.0, 4.6, 2.4), 0.8))  # talon
    boot = np.minimum(boot, limb(p, ank + v3((0, 0, 4.2)), ank + v3((0, 0, 6.6)), 8.2, 8.2))        # sangle
    sx = 1.0 if ank[0] >= 0 else -1.0
    buckle = obox(p, ank + v3((sx * 8.4, 0, 5.4)), v3((0, 1, 0)), v3((0, 0, 1)), (2.0, 2.2, 1.0), 0.5)
    boot = np.minimum(boot, engrave(buckle, obox(p, ank + v3((sx * 8.4, 0, 5.4)), v3((0, 1, 0)),
                                                 v3((0, 0, 1)), (1.0, 1.1, 3.0), 0.3), 0.6))
    n_strap = unit((0, 0.42, 1.0))                                             # sangle du cou-de-pied :
    strap = np.maximum(np.abs((p - (ank + v3((0, -8.0, 0)))) @ n_strap) - 1.3, boot - 0.7)   # bande en relief
    boot = np.minimum(boot, strap)
    return smin(d, boot, 3.0)


def _hands(p, P, j):
    """Mains et points de poignet (pour raccorder les avant-bras)."""
    u, width, guard, L, H = _blade_frame(P)
    out, wrists = None, {}
    for sd, side in (('l', -1.0), ('r', 1.0)):
        mode, arg = P['hands'][sd][0], P['hands'][sd][1]
        el = j['el_' + sd]
        if mode == 'grip':
            c = guard - u * float(arg)
            a = u
        else:                                                    # poing fermé (sur la hanche)
            c = v3(P['hands'][sd][2])                            # posé contre la hanche, hors du manteau
            a = unit(arg)
        f = unit(c - el)
        wrists[sd] = hand_wrist(c, a, f, side)
        hd = local(p, c, 15.0, lambda q, c=c, a=a, f=f, side=side: fist(q, c, a, f, side))
        out = hd if out is None else np.minimum(out, hd)
    return out, wrists


def ardoise_sdf(p, pose: str):
    """SDF d'Ardoise seul (sans socle), en mm, semelles à z = 0."""
    P = POSES[pose]
    j = {k: v3(v) for k, v in P.items() if isinstance(v, tuple) and len(v) == 3}
    up = unit(j['neck'] - j['pelvis'])
    fwd = ortho(v3((0, -1, 0)), up)
    side = np.cross(up, fwd)
    # Tronc en V : cage large, taille marquée, bassin.
    d = oellipsoid(p, (j['pelvis'] + j['chest']) / 2, up, side, (21, 16.5, 12.5))
    d = smin(d, oellipsoid(p, j['chest'] + up * 3, side, up, (23.5, 14.5, 14)), 7)
    d = smin(d, oellipsoid(p, j['pelvis'], side, up, (16, 10.5, 12)), 5)
    d = smin(d, limb(p, j['chest'] + up * 8, j['neck'] + up * 2, 8.4, 6.9), 4)
    # Trapèzes, sterno-cléido-mastoïdiens.
    for sx in (-1, 1):
        d = smin(d, limb(p, j['neck'] - up * 3, j['sh_' + ('r' if sx > 0 else 'l')] + up * 2, 6.5, 6.0), 5)
        d = smin(d, limb(p, j['head'] + v3((sx * 6.2, 2.0, -6.4)), j['chest'] + up * 15.5 + fwd * 6.5 + side * (sx * 1.6),
                         1.9, 1.5), 1.6)
    # Cuirasse en strates : quatre tranches jointives décalées en avant, rivets aux extrémités.
    hz = (p - j['chest']) @ up
    depth = (p - j['chest']) @ fwd
    rivets = []
    for (z0, z1), off in (((-13.0, -5.5), 2.2), ((-5.5, 2.0), 3.4), ((2.0, 9.5), 2.2), ((9.5, 17.0), 3.4)):
        c = j['chest'] + up * 2.0 + fwd * off
        shell = oellipsoid(p, c, side, up, (22.0, 16.0, 13.0))
        layer = np.maximum(shell, np.maximum(np.abs(hz - (z0 + z1) / 2) - (z1 - z0) / 2, -(depth + 3.0)))
        d = np.minimum(d, layer)
        ze = (z0 + z1) / 2 - 2.0
        for sx in (-1, 1):
            x = 15.0 * sx
            ye = 13.0 * np.sqrt(max(0.0, 1 - (x / 22.0) ** 2 - (ze / 16.0) ** 2))
            rivets.append(c + side * x + up * ze + fwd * ye)
    d = np.minimum(d, studs(p, rivets, 0.85))
    # Ceinture large, boucle en cadre, clous, bourse sur la hanche gauche.
    belt = j['pelvis'] + up * 8
    d = smin(d, oellipsoid(p, belt, side, up, (17.8, 4.4, 13.2)), 1.5)
    bk = obox(p, belt + fwd * 13.4, side, up, (5.4, 5.0, 1.6), 1.2)
    bk = np.maximum(bk, -obox(p, belt + fwd * 13.4, side, up, (3.0, 2.7, 4.0), 0.6))      # cadre ajouré
    bk = np.minimum(bk, limb(p, belt + fwd * 13.0 - side * 3.0, belt + fwd * 13.4 + side * 1.2, 0.75, 0.75))  # ardillon
    d = np.minimum(d, bk)
    d = np.minimum(d, studs(p, [belt + side * (17.8 * np.sin(phi)) + fwd * (13.2 * np.cos(phi))
                               for phi in (-1.35, -1.0, 1.0, 1.35, 1.7, -1.7)], 0.85))
    pouch_c = belt + side * 17.4 - fwd * 13.0 - up * 5.5                         # bourse sur la hanche droite, en arrière
    pouch_u = ortho(-fwd * 0.6 + side * 0.8, up)
    pouch = obox(p, pouch_c, pouch_u, up, (4.4, 5.4, 2.8), 1.4)
    pouch = np.minimum(pouch, obox(p, pouch_c + up * 2.6 + np.cross(pouch_u, up) * -0.6, pouch_u, up,
                                   (4.7, 2.4, 2.9), 1.0))                         # rabat
    d = np.minimum(d, pouch)
    # Tête.
    h = j['head']
    d = smin(d, local(p, h + v3((0, 0, -1)), (14, 16, 15), lambda q: _head(q, h)), 2.6)
    # Tresse : du sommet du crâne, derrière la nuque, sur l'épaule droite, jusque sur le plastron.
    n, sr = j['neck'], j['sh_r']
    braid_pts = [h + v3((0, 6.0, 8.6)), h + v3((0, 11.6, 0.5)), h + v3((2, 12, -9)), n + v3((7, 11, -2)),
                 sr + v3((-5, 6, 7)), sr + v3((-6, -7, 4)), j['chest'] + up * 3 + fwd * 15 + side * 10,
                 j['chest'] + up * -4 + fwd * 16 + side * 9.5]
    lo = np.min(braid_pts, axis=0) - 8.0
    hi = np.max(braid_pts, axis=0) + 8.0
    d = smin(d, local(p, (lo + hi) / 2, (hi - lo) / 2, lambda q: _braid(q, braid_pts)), 1.0)
    # Épaulière unique (côté gauche) : trois plaques empilées qui suivent le bras.
    s = j['sh_l']
    arm = unit(j['el_l'] - s)
    outv = ortho(v3((-1, 0, 0)), arm)
    for k, (along, rad) in enumerate(((-2.0, (12.5, 12.0, 3.8)), (7.0, (11.0, 10.8, 3.6)), (15.0, (9.2, 9.2, 3.4)))):
        c = s + arm * along + outv * (4.2 + 2.4 * k) + up * (3.0 - 1.5 * k)
        d = np.minimum(d, local(p, c, 16.0, lambda q, c=c, rad=rad: _plate(q, c, arm, ortho(v3((0, 1, 0)), arm),
                                                                         rad, outv, rivets=2)))
    # Bras et mains.
    hands, wrists = _hands(p, P, j)
    for sd in ('l', 'r'):
        sh, el = j['sh_' + sd], j['el_' + sd]
        wr = wrists[sd]
        box_lo = np.minimum(np.minimum(sh, el), wr) - 12.0
        box_hi = np.maximum(np.maximum(sh, el), wr) + 12.0
        d = smin(d, local(p, (box_lo + box_hi) / 2, (box_hi - box_lo) / 2,
                          lambda q, sh=sh, el=el, wr=wr, sd=sd: _arm(q, sh, el, wr, up, bare=(sd == 'r'))), 3.0)
    d = smin(d, hands, 1.4)
    # Jambes.
    for sd in ('l', 'r'):
        hip, knee, ank = j['hip_' + sd], j['knee_' + sd], j['ankle_' + sd]
        box_lo = np.minimum(np.minimum(hip, knee), ank) - v3((14, 22, 14))
        box_hi = np.maximum(np.maximum(hip, knee), ank) + v3((14, 14, 14))
        box_lo[2] = -2.0
        d = smin(d, local(p, (box_lo + box_hi) / 2, (box_hi - box_lo) / 2,
                          lambda q, hip=hip, knee=knee, ank=ank: _leg(q, hip, knee, ank)), 4.0)
    # Manteau long : ouvert devant, fendu dans le dos, plis tuyaux, bas déporté selon la pose.
    top = j['pelvis'] + up * 9
    bot = j['pelvis'] + v3((0, 6, -60)) + v3(P['flow'])
    d = smin(d, coat(p, top, bot, (18.8, 14.4), (31.0, 25.0), 2.3, phase=0.7), 2.0)
    # Lame.
    u, width, guard, L, H = _blade_frame(P)
    ends = np.array([guard + u * (L + 6), guard - u * (H + 9)])
    lo, hi = ends.min(axis=0) - 24.0, ends.max(axis=0) + 24.0
    d = smin(d, local(p, (lo + hi) / 2, (hi - lo) / 2, lambda q: _blade(q, P)), 1.0)
    return np.maximum(d, -p[..., 2])
