"""« Ardoise, le duelliste des strates » : guerrier original BOJ.ART (2 novembre 2026).

Création propre à BOJ.ART, choisie par Olsen comme personnage vendable à la place d'un personnage
sous droits. Signes distinctifs : crâne rasé et tresse épaisse passée sur l'épaule droite, long
manteau ouvert devant et fendu dans le dos, une seule épaulière faite de plaques empilées comme des
strates d'ardoise, cuirasse en strates, grande lame à deux mains au profil en gradins. Garde-fous de
distinction : aucune chevelure dressée, aucune armure à épaulettes symétriques ni combinaison, aucune
pose de tir d'énergie ni signature empruntée.

Mêmes conventions que la Sentinelle : millimètres, z vers le haut, face vers -y, semelles à z = 0.
"""
from __future__ import annotations

import numpy as np

from .sculpt import _len, ellipsoid, limb, rounded_box, smin, sphere, ssub

ARDOISE_VERSION = 'bojart.ardoise.sdf.v5'
BOUNDS = ((-95.0, -95.0, -6.0), (95.0, 95.0, 235.0))

# Trois intentions légères. « blade » : garde (ou prise en main), direction de la pointe, axe de la
# largeur, longueurs de lame et de poignée ; « flow » : déport du bas du manteau (mouvement, vent).
POSES = {
    'serment': {
        'label': 'Serment : lame plantée devant, deux mains sur la poignée, menton levé',
        'pelvis': (0, 0, 92), 'chest': (0, 0, 127), 'neck': (0, 1, 146), 'head': (0, 0.5, 160),
        'hip_l': (-11, 0, 90), 'knee_l': (-15, -3, 50), 'ankle_l': (-18, 0, 9),
        'hip_r': (11, 0, 90), 'knee_r': (15, -3, 50), 'ankle_r': (18, 0, 9),
        'sh_l': (-25, 1, 140), 'el_l': (-30, -12, 114), 'wr_l': (-2, -31, 96),
        'sh_r': (25, 1, 140), 'el_r': (30, -12, 117), 'wr_r': (2, -31, 104),
        'blade': {'guard': (0, -32, 84), 'dir': (0, 0, -1), 'width_axis': (1, 0, 0), 'length': 84, 'handle': 25},
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
        'flow': (0, 14, 4),
    },
}
# Intentions de la demande (« combat », « repos ») traduites en pose de ce personnage.
INTENT_POSES = {'combat': 'garde', 'rest': 'serment'}


def _v(t):
    return np.asarray(t, np.float32)


def _unit(t):
    t = _v(t)
    return t / np.linalg.norm(t)


def _frame(u, v):
    u = _unit(u)
    v = _v(v) - u * float(u @ _v(v))
    v = v / np.linalg.norm(v)
    return u, v, np.cross(u, v)


def obox(p, c, u, v, half, r):
    """Boîte arrondie orientée par deux axes : u (premier demi-côté) et v (second), w = u × v."""
    u, v, w = _frame(u, v)
    q = p - _v(c)
    q = np.stack([q @ u, q @ v, q @ w], axis=-1)
    d = np.abs(q) - (_v(half) - r)
    return _len(np.maximum(d, 0)) + np.minimum(d.max(axis=-1), 0) - r


def oellipsoid(p, c, u, v, radii):
    """Ellipsoïde orienté (rayons le long de u, v, w = u × v)."""
    u, v, w = _frame(u, v)
    q = p - _v(c)
    radii = _v(radii)
    q = np.stack([q @ u, q @ v, q @ w], axis=-1) / radii
    return (_len(q) - 1.0) * float(radii.min())


def coat(p, top, bot, r_top, r_bot, half_t, front_open=0.32, slit_from=0.45):
    """Manteau : coque elliptique conique ouverte devant et fendue dans le dos (pans libres)."""
    top, bot = _v(top), _v(bot)
    zt, zb = float(top[2]), float(bot[2])
    t = np.clip((zt - p[..., 2]) / (zt - zb), 0.0, 1.0)
    cx = top[0] + (bot[0] - top[0]) * t
    cy = top[1] + (bot[1] - top[1]) * t
    rx = r_top[0] + (r_bot[0] - r_top[0]) * t
    ry = r_top[1] + (r_bot[1] - r_top[1]) * t
    xr, yr = p[..., 0] - cx, p[..., 1] - cy
    rho = np.sqrt((xr / rx) ** 2 + (yr / ry) ** 2)
    shell = np.abs((rho - 1.0) * np.minimum(rx, ry)) - (half_t + 0.8 * np.clip((t - 0.9) * 10, 0, 1))  # ourlet
    d = np.maximum(shell, np.maximum(p[..., 2] - zt, zb - p[..., 2]))
    d = np.maximum(d, -(yr + front_open * ry))                     # ouvert devant
    slit = np.maximum(np.abs(xr) - 1.4, np.maximum(-yr, (t < slit_from) * 1e3 - 1e-3))
    return np.maximum(d, -slit)                                     # fente dans le dos


def _braid(p, pts, r=3.9, spacing=4.4):
    """Tresse : perles alternées le long d'une polyligne (diamètre ≥ 6 mm à 200 mm)."""
    pts = [_v(x) for x in pts]
    d, i = None, 0
    for a, b in zip(pts[:-1], pts[1:]):
        seg = b - a
        n = max(1, int(np.linalg.norm(seg) // spacing))
        side = np.cross(_unit(seg), _v((0, 0, 1)) if abs(_unit(seg)[2]) < 0.9 else _v((1, 0, 0)))
        side = side / np.linalg.norm(side)
        for k in range(n):
            c = a + seg * (k / n) + side * (0.9 if i % 2 else -0.9)
            s = sphere(p, c, r if i % 2 else r - 0.4)
            d = s if d is None else smin(d, s, 1.1)
            i += 1
    end = pts[-1]
    d = smin(d, sphere(p, end, r + 0.6), 1.0)                      # ligature
    return smin(d, ellipsoid(p, end + _v((0, -0.5, -5.5)), (3.2, 2.6, 4.8)), 1.2)  # mèche


def _blade(p, P):
    b = P['blade']
    u = _unit(b['dir'])
    width = _v(b['width_axis'])
    guard = _v(b['guard']) if 'guard' in b else _v(b['grip']) + u * 8
    L, H = b['length'], b['handle']
    d = None
    for k, half_w in enumerate((7.6, 6.7, 5.8)):                   # trois gradins (strates)
        c = guard + u * (L * (k + 0.5) / 3.0 + 1.5)
        seg = obox(p, c, u, width, (L / 6.0 + 0.6, half_w, 1.9), 0.7)
        d = seg if d is None else np.minimum(d, seg)
    tip = guard + u * (L + 1.5)
    d = smin(d, obox(p, tip - u * 3, u, width, (4.0, 4.3, 1.8), 1.2), 1.0)      # pointe émoussée
    d = smin(d, obox(p, guard, u, width, (3.2, 21.0, 3.6), 1.5), 0.8)           # garde droite
    d = np.minimum(d, obox(p, guard - u * 0.2, u, width, (4.4, 5.0, 4.4), 1.6))  # bloc central
    d = smin(d, limb(p, guard - u * 2, guard - u * H, 3.2, 3.4), 0.8)           # poignée
    for t in (0.3, 0.55, 0.8):                                                  # bandes de cuir
        c = guard - u * (H * t)
        d = np.minimum(d, limb(p, c - u * 0.8, c + u * 0.8, 3.9, 3.9))
    d = smin(d, limb(p, guard - u * (H + 2.5), guard - u * (H + 6.5), 6.4, 6.4), 0.8)  # pommeau
    return d


def ardoise_sdf(p, pose: str):
    """SDF d'Ardoise seul (sans socle), en mm, semelles à z = 0."""
    P = POSES[pose]
    j = {k: _v(v) for k, v in P.items() if isinstance(v, tuple) and len(v) == 3}
    up = _unit(j['neck'] - j['pelvis'])
    fwd = _v((0, -1, 0)) - up * float(up @ _v((0, -1, 0)))
    fwd = fwd / np.linalg.norm(fwd)
    side = np.cross(up, fwd)
    # Tronc en V : cage large, taille marquée, bassin.
    d = oellipsoid(p, (j['pelvis'] + j['chest']) / 2, up, side, (21, 16.5, 12.5))
    d = smin(d, oellipsoid(p, j['chest'] + up * 3, side, up, (23.5, 14.5, 14)), 7)
    d = smin(d, oellipsoid(p, j['pelvis'], side, up, (16, 10.5, 12)), 5)
    d = smin(d, limb(p, j['chest'] + up * 8, j['neck'] + up * 2, 9.0, 7.6), 4)
    # Trapèzes et pectoraux pour la carrure.
    for sx in (-1, 1):
        d = smin(d, limb(p, j['neck'] - up * 3, j['sh_' + ('r' if sx > 0 else 'l')] + up * 2, 6.5, 6.0), 5)
    # Cuirasse en strates : quatre tranches jointives décalées en avant, sans rainure (marches nettes).
    hz = (p - j['chest']) @ up
    depth = (p - j['chest']) @ fwd
    for (z0, z1), off in (((-13.0, -5.5), 2.2), ((-5.5, 2.0), 3.4), ((2.0, 9.5), 2.2), ((9.5, 17.0), 3.4)):
        shell = oellipsoid(p, j['chest'] + up * 2.0 + fwd * off, side, up, (22.0, 16.0, 13.0))
        layer = np.maximum(shell, np.maximum(np.abs(hz - (z0 + z1) / 2) - (z1 - z0) / 2, -(depth + 3.0)))
        d = np.minimum(d, layer)
    # Ceinture large et boucle.
    belt = j['pelvis'] + up * 8
    d = smin(d, oellipsoid(p, belt, side, up, (17.8, 4.4, 13.2)), 1.5)
    d = np.minimum(d, obox(p, belt + fwd * 13.2, side, up, (5.4, 5.0, 2.4), 1.3))
    # Tête : crâne rasé, mâchoire carrée, pommettes, arcade, nez, oreilles, orbites.
    h = j['head']
    head = ellipsoid(p, h, (10.2, 11.2, 12.4))
    head = smin(head, rounded_box(p, h + _v((0, -4.5, -8)), (7.4, 6.4, 4.6), 3.9), 3.2)
    for sx in (-1, 1):
        head = smin(head, ellipsoid(p, h + _v((sx * 6.0, -8.0, -2.5)), (3.4, 3.0, 2.6)), 1.6)
        head = smin(head, ellipsoid(p, h + _v((sx * 10.6, 1, -1)), (1.8, 3.2, 4.2)), 1.0)
        head = ssub(head, sphere(p, h + _v((sx * 4.2, -10.7, 0.8)), 1.7), 0.6)
    head = smin(head, rounded_box(p, h + _v((0, -9.3, 3.4)), (7.6, 1.6, 1.5), 1.4), 1.6)
    head = smin(head, limb(p, h + _v((0, -11.4, 1.8)), h + _v((0, -13.2, -2.6)), 1.5, 2.2), 1.0)
    d = smin(d, head, 3)
    # Tresse : du sommet du crâne, derrière la nuque, sur l'épaule droite, jusque sur le plastron.
    n, sr = j['neck'], j['sh_r']
    braid_pts = [h + _v((0, 7, 9.5)), h + _v((0, 12.5, 1)), h + _v((2, 13, -9)), n + _v((7, 11, -2)),
                 sr + _v((-5, 6, 7)), sr + _v((-6, -7, 4)), j['chest'] + up * 3 + fwd * 15 + side * 10,
                 j['chest'] + up * -4 + fwd * 16 + side * 9.5]
    d = smin(d, _braid(p, braid_pts), 1.2)
    # Épaulière unique (côté gauche) : trois plaques empilées qui suivent le bras.
    s = j['sh_l']
    arm = _unit(j['el_l'] - s)
    out = _unit(_v((-1, 0, 0)) - arm * float(arm @ _v((-1, 0, 0))))
    for k, (along, rad) in enumerate(((-2.0, (12.5, 12.0, 3.8)), (7.0, (11.0, 10.8, 3.6)), (15.0, (9.2, 9.2, 3.4)))):
        c = s + arm * along + out * (4.2 + 2.4 * k) + up * (3.0 - 1.5 * k)
        d = np.minimum(d, oellipsoid(p, c, arm, _unit(_v((0, 1, 0)) - arm * float(arm @ _v((0, 1, 0)))), rad))
    d = smin(d, ellipsoid(p, j['sh_r'] + _v((1, 0, 0.5)), (8.6, 8.6, 7.6)), 3)   # épaule droite nue
    # Bras, brassards cerclés, poings.
    for sd in ('l', 'r'):
        sh, el, wr = j['sh_' + sd], j['el_' + sd], j['wr_' + sd]
        d = smin(d, limb(p, sh, el, 7.8, 6.4), 3)
        d = smin(d, limb(p, el, wr, 6.4, 5.2), 2.5)
        a, b = el * 0.45 + wr * 0.55, wr
        d = smin(d, limb(p, a, b, 6.4, 6.0), 1.2)
        axis = _unit(b - a)
        for t in (0.2, 0.62):
            c = a + (b - a) * t
            d = np.minimum(d, limb(p, c - axis * 1.0, c + axis * 1.0, 7.1, 7.1))
        d = smin(d, sphere(p, wr + axis * 3.0, 6.0), 2)
    # Jambes, genouillères en strates, bottes à semelle épaisse.
    for sd in ('l', 'r'):
        hip, knee, ank = j['hip_' + sd], j['knee_' + sd], j['ankle_' + sd]
        d = smin(d, limb(p, hip, knee, 9.4, 7.2), 4)
        d = smin(d, limb(p, knee, ank, 7.2, 5.8), 3)
        kd = _unit(knee - hip)
        kf = _unit(_v((0, -1, 0)) - kd * float(kd @ _v((0, -1, 0))))
        d = np.minimum(d, oellipsoid(p, knee + kf * 5.6 + kd * -1.5, (1, 0, 0), kd, (6.8, 4.6, 4.2)))
        d = np.minimum(d, oellipsoid(p, knee + kf * 6.4 + kd * 4.0, (1, 0, 0), kd, (5.6, 3.8, 3.6)))
        boot = smin(rounded_box(p, ank + _v((0, -4, -3.8)), (8.6, 14.0, 5.2), 3.0),
                    limb(p, ank, ank + _v((0, 0, 15)), 7.6, 7.4), 2.5)
        boot = np.minimum(boot, limb(p, ank + _v((0, 0, 14.5)), ank + _v((0, 0, 17)), 8.4, 8.4))  # revers
        boot = np.minimum(boot, rounded_box(p, _v((ank[0], ank[1] - 4, 1.2)), (9.4, 14.8, 1.2), 0.6))
        d = smin(d, boot, 3)
    # Manteau long : ouvert devant, fendu dans le dos, bas déporté selon la pose.
    top = j['pelvis'] + up * 9
    bot = j['pelvis'] + _v((0, 6, -60)) + _v(P['flow'])
    d = smin(d, coat(p, top, bot, (18.8, 14.4), (31.0, 25.0), 2.3), 2.0)
    # Lame.
    d = smin(d, _blade(p, P), 1.0)
    return np.maximum(d, -p[..., 2])
