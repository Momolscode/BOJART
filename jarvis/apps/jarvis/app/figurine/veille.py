"""« Veille, la gardienne du trait » : personnage original BOJ.ART (2 novembre 2026).

Personnage du contenu premium V.02 de BOJ.ART (film « Un seul trait », images de référence du
2 novembre). Signes distinctifs : figure androgyne agenouillée, genou gauche au sol, pied droit nu posé
devant ; yeux clos ; côtés du crâne rasés, dessus long plaqué en arrière avec une mèche relevée ; robe
sombre tombée de l'épaule droite, haut col sur la gauche, bord croisé sur le devant, jupe étalée au
sol ; avant-bras bandés jusque sur le dos des mains ; grand bâton-pinceau de calligraphe tenu droit à
deux mains ; socle de basalte. Le trait carmin de l'œil n'est pas sculpté : c'est de la peinture.

Garde-fous de distinction : aucun personnage existant ni sosie ; ni arme, ni armure, ni pose de combat
(personnage de veille). Les volumes cachés par la robe (jambe agenouillée, mollet droit) ne sont pas
sculptés : la robe est un volume plein, plus solide à l'impression qu'une coque de tissu.

Mêmes conventions que la Sentinelle et Ardoise : millimètres, z vers le haut, face vers -y, appuis à
z = 0. Les poses sont données dans un repère de construction miroir en x (voir veille_sdf).
"""
from __future__ import annotations

import numpy as np

from .details import TAU, engrave, fist, hand_frame, hand_wrist, local, obox, oellipsoid, ortho, pipe_folds, ring, unit, v3
from .sculpt import ellipsoid, limb, smin, sphere, ssub

VEILLE_VERSION = 'bojart.veille.sdf.v1'
BOUNDS = ((-75.0, -75.0, -6.0), (65.0, 65.0, 172.0))
# Détails de 0,7 à 0,8 mm (paupières, sillons de peigne, bandages) : même grille fine qu'Ardoise.
DETAIL = {'voxel': 0.4, 'smooth_iterations': 3}
# Socle assorti : basalte hexagonal (fabrication._basalt_base), comme sur les images de référence.
SOCLE = 'basalte'

# Une seule intention : la veille. « staff » : pied du bâton au sol, longueur, hauteur des deux prises ;
# « drape » : centre et demi-axes de la robe étalée au sol, hauteur de l'ourlet du pan tombé du genou.
POSES = {
    'veille': {
        'label': 'Veille : à genou, bâton-pinceau tenu droit à deux mains, yeux clos',
        'pelvis': (0, 6, 50), 'chest': (0, 5, 84), 'neck': (0, 4, 101), 'head': (0, 2.5, 117),
        'hip_l': (-10, 6, 46), 'knee_l': (-14, -6, 6.5),
        'hip_r': (10, 6, 46), 'knee_r': (24, -31, 47), 'ankle_r': (25, -34, 8.5),
        'sh_l': (-16.5, 5, 96.5), 'el_l': (-42, 5.8, 85),
        'sh_r': (16.5, 5, 96.5), 'el_r': (12, -5, 70),
        'staff': {'foot': (-25.0, -16.0), 'length': 165.0, 'grips': {'l': 108.0, 'r': 70.0}},
        'head_tilt': (5.0, 0.0, 0.0),
        'foot_r_yaw': 18.0,
        'drape': {'pool_centre': (-7.0, 12.0), 'pool_radii': (21.5, 23.5), 'panel_hem': 9.5},
    },
}
# Veille n'a pas de pose de combat : une demande « combat » ou « repos » garde la veille.
INTENT_POSES = {'combat': 'veille', 'rest': 'veille'}

STAFF_R = 2.5


def _rotation(pitch, roll, yaw):
    """Matrice du repère de la tête vers le monde (degrés) : tangage autour de x (positif = tête
    penchée vers l'avant), roulis autour de y, lacet autour de z."""
    a, b, c = np.radians([pitch, roll, yaw])
    rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    rz = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    return (rz @ ry @ rx).astype(np.float32)


def bandage(p, a, b, ra, rb, pitch=3.6, step=0.45):
    """Bande enroulée en hélice : chaque tour recouvre le précédent (relief en dents de scie de step mm,
    niveau FDM limite), bouts coupés net (cachés par la manche et la main)."""
    a, b = v3(a), v3(b)
    ax = b - a
    L = float(np.linalg.norm(ax))
    ax = ax / L
    e1 = ortho(v3((0, 0, 1)) if abs(ax[2]) < 0.9 else v3((1, 0, 0)), ax)
    e2 = np.cross(ax, e1)
    q = p - a
    s = q @ ax
    th = np.arctan2(q @ e2, q @ e1)
    u = np.mod(s / pitch - th / TAU, 1.0)
    rr = ra + (rb - ra) * np.clip(s / L, 0.0, 1.0) + step * u
    radial = np.sqrt(np.maximum(np.einsum('...i,...i->...', q, q) - s * s, 0.0))
    return np.maximum(radial - rr, np.maximum(-s, s - L))


def drape(p, top, bot, r_top, r_bot, folds, amp, phase=0.0, shell=0.0, flare=1.0, z_floor=None, fold_window=None):
    """Drapé : cône elliptique du haut (top) vers le bas (bot), plis tuyaux qui s'ouvrent vers le bas.
    Plein par défaut (aucun vide caché) ; shell > 0 : étoffe d'épaisseur 2 × shell mm ; flare > 1 :
    l'étoffe tombe presque droit puis s'évase près de l'ourlet. z_floor : section figée sous cette
    hauteur (ourlet d'aplomb sur le socle, sans biseau fin au ras du sol). fold_window(theta) : gain
    des plis selon l'angle (plis effacés près d'un bord coupé, qui reste ainsi d'équerre)."""
    top, bot = v3(top), v3(bot)
    zt, zb = float(top[2]), float(bot[2])
    z = p[..., 2] if z_floor is None else np.maximum(p[..., 2], z_floor)
    t = np.clip((zt - z) / (zt - zb), 0.0, 1.0)
    cx = top[0] + (bot[0] - top[0]) * t
    cy = top[1] + (bot[1] - top[1]) * t
    tf = t ** flare
    rx = r_top[0] + (r_bot[0] - r_top[0]) * tf
    ry = r_top[1] + (r_bot[1] - r_top[1]) * tf
    xr, yr = p[..., 0] - cx, p[..., 1] - cy
    theta = np.arctan2(yr / ry, xr / rx)
    rho = np.sqrt((xr / rx) ** 2 + (yr / ry) ** 2)
    fold = pipe_folds(theta, t, folds, amp, phase)
    if fold_window is not None:
        fold = fold * fold_window(theta)
    radial = (rho - 1.0) * np.minimum(rx, ry) - fold
    if shell:
        radial = np.abs(radial) - shell
    return np.maximum(radial, p[..., 2] - zt), theta


def _head(q):
    """Tête de 24 mm dans son repère (centre à l'origine, face vers -y) : visage ovale à mâchoire fine,
    pommettes hautes, visage qui fuit vers les oreilles (pas d'arête de masque), yeux clos (paupières
    bombées, coin externe en retrait, ligne des cils gravée), nez droit, bouche fermée,
    oreilles dégagées, côtés rasés et dessus long plaqué en arrière (sillons de peigne de 0,7 mm)."""
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    skull = ellipsoid(q, (0, 1.4, 2.2), (8.0, 9.7, 9.4))
    d = smin(skull, ellipsoid(q, (0, -4.8, 3.4), (6.6, 4.5, 5.6)), 2.4)                # front
    d = smin(d, ellipsoid(q, (0, -3.6, -4.8), (6.3, 6.4, 7.4)), 3.0)                    # masse du visage (ovale)
    for sx in (-1, 1):
        d = smin(d, limb(q, v3((sx * 6.6, 0.8, -3.0)), v3((sx * 2.5, -5.9, -10.3)), 2.0, 1.45), 2.0)   # mâchoire
        # Le visage fuit vers les oreilles : pommette et joue orientées vers l'arrière, masse zygomatique
        # entre la pommette et l'oreille (sans elle, le devant du visage tombe à pic comme un masque).
        d = smin(d, ellipsoid(q, (sx * 5.0, -3.4, -2.8), (2.4, 4.4, 2.7)), 2.5)                       # zygomatique
        d = smin(d, oellipsoid(q, v3((sx * 4.6, -6.8, -1.8)), unit((1.0, 0.6 * sx, 0.0)), v3((0, 0, 1)),
                               (2.2, 1.3, 1.4)), 1.6)                                                   # pommette
        d = smin(d, limb(q, v3((sx * 5.8, -7.0, 2.4)), v3((sx * 1.3, -9.2, 1.9)), 0.85, 0.85), 1.4)   # arcade
    d = smin(d, ellipsoid(q, (0, -7.7, -10.5), (2.6, 2.4, 2.1)), 1.5)                  # menton étroit, sous les lèvres
    for sx in (-1, 1):
        d = ssub(d, sphere(q, (sx * 3.6, -10.0, 0.5), 1.25), 0.7)                       # orbite peu creuse
        d = smin(d, oellipsoid(q, v3((sx * 3.5, -7.5, -4.5)), unit((1.0, 0.5 * sx, 0.0)), v3((0, 0, 1)),
                               (2.5, 2.1, 1.6)), 1.6)                                                   # joue pleine
        lu = unit((1.0, 0.4 * sx, 0.12 * sx))                                             # coin externe en retrait
        lid = oellipsoid(q, v3((sx * 3.6, -8.05, 0.1)), lu, ortho((0, 0, 1), lu), (2.35, 1.25, 1.2))
        d = smin(d, lid, 0.5)                                                           # paupière close
    # Ligne des cils : arc tourné vers le bas (yeux clos, apaisés), gravé 0,55 × 0,35 mm.
    ax_ = np.abs(x)
    arc = -0.25 - 0.55 * np.sin(np.pi * np.clip((ax_ - 1.6) / 3.9, 0.0, 1.0)) + 0.18 * np.clip((ax_ - 4.2), 0, 2)
    lash = np.maximum(np.abs(z - arc) - 0.27, np.maximum(np.maximum(1.6 - ax_, ax_ - 5.2), y + 6.0))
    d = engrave(d, lash, 0.35)
    d = smin(d, limb(q, v3((0, -9.4, 0.6)), v3((0, -11.0, -4.3)), 0.9, 1.2), 0.8)       # arête du nez
    d = smin(d, sphere(q, (0, -11.2, -4.75), 1.3), 0.6)                                 # bout du nez
    for sx in (-1, 1):
        d = smin(d, sphere(q, (sx * 1.35, -10.1, -5.15), 0.95), 0.6)                   # ailes du nez
    d = smin(d, oellipsoid(q, v3((0, -9.55, -7.25)), v3((1, 0, 0)), v3((0, 0, 1)), (2.45, 0.85, 0.95)), 0.6)   # lèvre sup.
    d = smin(d, oellipsoid(q, v3((0, -9.25, -8.45)), v3((1, 0, 0)), v3((0, 0, 1)), (2.05, 0.85, 0.95)), 0.6)   # lèvre inf.
    d = engrave(d, np.maximum(np.maximum(np.abs(z + 7.9) - 0.3, ax_ - 2.2), y + 8.6), 0.3)   # fente de la bouche
    for sx in (-1, 1):
        ear = oellipsoid(q, v3((sx * 8.0, 0.9, -1.3)), v3((1, 0, 0)), v3((0, 1, 0)), (1.4, 2.8, 3.9))
        ear = ssub(ear, sphere(q, (sx * 9.2, 0.6, -1.6), 1.45), 0.4)                   # conque
        ear = smin(ear, sphere(q, (sx * 8.0, 0.5, -4.6), 1.05), 0.5)                   # lobe
        d = smin(d, ear, 0.6)
    # Cheveux : masse arrondie de 13 mm sur le dessus, coupe nette sur les côtés (undercut), mèche relevée
    # au-dessus du front, finie au-dessus de la nuque.
    half_w = 6.4 - 0.7 * np.clip((y - 1.0) / 9.0, 0.0, 1.0)
    thick = 2.0 + 1.3 * np.exp(-((y + 5.0) / 4.5) ** 2)
    thick = 0.5 + (thick - 0.5) * np.sqrt(np.clip(1.0 - (ax_ / half_w) ** 2, 0.0, 1.0))   # masse arrondie
    z_cut = 0.6 - 0.35 * np.clip(y, 0.0, None)
    thick = thick * np.clip((z - z_cut) / 4.0, 0.0, 1.0)                                # se fond dans la nuque
    hair = skull - thick
    hair = np.maximum(hair, ax_ - half_w)
    hair = np.maximum(hair, z_cut - z)                                                  # fin sur l'occiput
    front = -(y + 7.9) - 0.55 * (z - 5.0)                                               # ligne du front
    hair = -smin(-hair, -front, 1.4)                                                    # bord avant arrondi
    groove = np.minimum(0.45, 0.6 * thick)                    # jamais plus profond que la mèche : pas d'éclat
    for k in range(-3, 4):                                                              # sillons de peigne
        xk = 1.6 * k + 0.25 * np.sin(y / 4.5 + k)
        hair = engrave(hair, np.abs(x - xk) - 0.35, groove)
    return np.minimum(d, hair)


def _foot(p, ank, yaw_deg):
    """Pied droit nu, posé à plat (appui continu pour le tenon) : talon, voûte, coussinet, cinq orteils
    séparés (gros orteil Ø 3,8 mm, petits orteils Ø 2,1 à 2,7 mm), malléoles."""
    a = np.radians(yaw_deg)
    F = v3((np.sin(a), -np.cos(a), 0.0))            # vers les orteils
    S = v3((np.cos(a), np.sin(a), 0.0))             # vers l'extérieur du pied droit
    U = v3((0, 0, 1))
    base = v3((ank[0], ank[1], 0.0))

    def at(f, s, z):
        return base + F * f + S * s + U * z
    d = oellipsoid(p, at(-3.4, 0.3, 3.1), F, S, (4.4, 3.6, 3.6))                     # talon
    d = smin(d, oellipsoid(p, at(5.5, 0.0, 2.9), F, S, (8.6, 4.1, 3.0)), 3.0)          # voûte
    d = smin(d, oellipsoid(p, at(13.0, -0.4, 2.2), F, S, (3.4, 5.0, 2.5)), 2.4)        # coussinet
    d = smin(d, limb(p, at(0.0, 0.0, 8.5), at(11.0, -0.6, 3.3), 3.7, 2.8), 2.5)        # cou-de-pied
    d = smin(d, obox(p, at(5.0, -0.2, 0.3), F, S, (10.5, 3.9, 1.3), 0.9), 1.5)         # plante à plat
    d = smin(d, limb(p, at(0.0, 0.0, 8.5), at(0.3, 0.0, 16.0), 3.4, 3.7), 2.0)         # cheville
    d = smin(d, sphere(p, at(0.4, -2.8, 9.1), 1.35), 0.8)                              # malléole interne
    d = smin(d, sphere(p, at(-0.4, 2.9, 8.2), 1.35), 0.8)                              # malléole externe
    d = smin(d, limb(p, at(-4.6, 0.2, 4.0), at(-2.6, 0.1, 14.0), 2.2, 2.4), 1.4)       # tendon d'Achille
    toes = limb(p, at(15.0, -3.0, 1.6), at(20.5, -3.1, 1.55), 1.9, 1.8)                # gros orteil
    for s0, f1, r in ((-0.5, 19.6, 1.35), (1.4, 18.7, 1.27), (3.1, 17.4, 1.18), (4.6, 15.6, 1.08)):
        toes = smin(toes, limb(p, at(f1 - 4.6, s0, r - 0.25), at(f1, s0 + 0.2, r - 0.3), r, r - 0.12), 0.3)
    return smin(d, toes, 1.0)


def _hand(q, c, a, f, side):
    """Poing serré sur le bâton (details.fist) et deux bandes croisées sur le dos de la main."""
    d = fist(q, c, a, f, side)
    a_, f_, g = hand_frame(a, f, side)
    r = q - v3(c)
    s, x, y = r @ a_, r @ f_, r @ g
    band = np.minimum(np.abs(s - 0.8 * (x + 1.5)), np.abs(s + 0.8 * (x + 1.5))) * 0.78 - 1.05
    band = np.maximum(band, np.maximum(1.5 - y, np.maximum(x - 3.0, -x - 6.5)))
    return np.minimum(d, np.maximum(d - 0.5, band))


def _staff(p, foot, length):
    """Bâton-pinceau : hampe de Ø 5 mm, embout au sol, virole bombée à filet gravé, touffe en fuseau
    à quatorze mèches gravées, pointe arrondie (Ø 1,6 mm) pour rester imprimable."""
    base = v3((foot[0], foot[1], 0.0))
    U = v3((0, 0, 1))

    def at(z):
        return base + U * z
    top = float(length)
    d = limb(p, at(-1.0), at(top - 39.0), STAFF_R, STAFF_R)                          # hampe
    d = np.minimum(d, limb(p, at(-1.0), at(3.6), 2.95, 2.95))                         # embout
    fer = smin(limb(p, at(top - 39.5), at(top - 31.5), 2.9, 3.75), limb(p, at(top - 31.5), at(top - 26.0), 3.75, 3.3), 1.0)
    fer = engrave(fer, np.abs(p[..., 2] - (top - 36.0)) - 0.4, 0.4)                   # filet de la virole
    d = np.minimum(d, fer)
    tuft = smin(ellipsoid(p, at(top - 19.5), (4.7, 4.7, 7.5)), limb(p, at(top - 20.0), at(top - 0.8), 4.4, 0.8), 3.0)
    rel = p - base
    th = np.arctan2(rel[..., 1], rel[..., 0])
    rho = np.sqrt(rel[..., 0] ** 2 + rel[..., 1] ** 2)
    n = 14
    arc = np.abs(np.mod(th * n / TAU + 0.5, 1.0) - 0.5) * (TAU / n) * rho
    band = np.maximum(arc - 0.35, np.maximum((top - 24.5) - p[..., 2], p[..., 2] - (top - 4.0)))
    return np.minimum(d, engrave(tuft, band, 0.35))


MIRROR = v3((-1.0, 1.0, 1.0))
# Décalage de quelques micromètres : sans lui, des cylindres centrés sur des cotes rondes (bâton de rayon
# 2,5 mm) tombent pile sur les nœuds de la grille, le champ y vaut exactement zéro et le marching cubes
# a produit une arête non manifold à la main haute (pas de 0,5 mm, 3 novembre 2026).
JITTER = v3((0.0013, 0.0021, 0.0031))
HEAD_SCALE = 1.14


def veille_sdf(p, pose: str):
    """SDF de Veille seule (sans socle), en mm, appuis à z = 0.

    Les articulations des poses sont données dans le repère de construction, miroir du résultat en x :
    la figure y est bâtie bâton à gauche (x < 0), puis retournée pour que, vue de face, le bâton soit à
    droite de l'image comme sur les références (main gauche du personnage en haut du bâton, épaule
    droite nue)."""
    return np.maximum(_built(p * MIRROR + JITTER, POSES[pose]), -p[..., 2])


def _built(p, P):
    j = {k: v3(v) for k, v in P.items() if isinstance(v, tuple) and len(v) == 3}
    up = unit(j['neck'] - j['pelvis'])
    fwd = ortho(v3((0, -1, 0)), up)
    side = np.cross(up, fwd)
    R = _rotation(*P['head_tilt'])
    h = j['head']

    def head_pt(x, y, z):
        return h + R @ (v3((x, y, z)) * HEAD_SCALE)

    # Corps : tronc fin, bassin, trapèzes, deltoïdes, cou long, clavicules.
    torso = oellipsoid(p, (j['pelvis'] + j['chest']) / 2, side, up, (12.4, 16.5, 9.2))
    torso = smin(torso, oellipsoid(p, j['chest'] + up * 2.5, side, up, (14.2, 12.3, 9.9)), 6.0)
    torso = smin(torso, oellipsoid(p, j['pelvis'], side, up, (15.2, 10.5, 10.8)), 5.0)
    torso = smin(torso, oellipsoid(p, j['chest'] + up * 9.0 + fwd * 2.0, side, up, (12.8, 6.5, 8.3)), 4.0)   # haut du buste
    for sx, sd in ((-1, 'l'), (1, 'r')):
        sh = j['sh_' + sd]
        torso = smin(torso, limb(p, j['neck'] - up * 1.0 + v3((0, 1.5, 0)), sh + up * 1.4, 4.0, 3.4), 4.0)   # trapèze
        ua0 = unit(j['el_' + sd] - sh)
        torso = smin(torso, oellipsoid(p, sh + ua0 * 4.2 + side * (sx * 0.9), ua0, ortho(side, ua0), (8.2, 4.9, 4.7)), 3.0)   # deltoïde
        torso = smin(torso, limb(p, j['chest'] + up * 10.0 + fwd * 3.0, sh + fwd * 1.0, 4.6, 3.9), 3.0)       # ceinture scapulaire
    neck_base = j['chest'] + up * 11.0
    body = smin(torso, limb(p, neck_base, head_pt(0, 1.6, -7.2), 4.4, 3.9), 3.0)
    notch = j['chest'] + up * 13.0 + fwd * 7.6
    for sx, sd in ((-1, 'l'), (1, 'r')):
        body = smin(body, limb(p, notch + side * (sx * 1.6), j['sh_' + sd] + up * 2.2 + fwd * 1.8 - side * (sx * 1.2),
                               1.05, 0.95), 1.2)                                                         # clavicule
        body = smin(body, limb(p, head_pt(sx * 5.6, 1.2, -5.6), notch + side * (sx * 1.4), 1.5, 1.2), 1.4)   # sterno-cléido
    body = ssub(body, sphere(p, notch + fwd * 1.2 + up * 0.6, 1.4), 0.8)                               # fossette sus-sternale
    lo, hi = h - 18.0, h + 18.0
    body = smin(body, local(p, (lo + hi) / 2, (hi - lo) / 2,
                            lambda q: _head(((q - h) @ R) / HEAD_SCALE) * HEAD_SCALE), 2.2)

    # Bâton et prises : main haute du côté du col, main basse croisée devant le ventre.
    st = P['staff']
    sx0, sy0 = st['foot']
    hands, wrists = None, {}
    for sd, side_sign in (('l', -1.0), ('r', 1.0)):
        c = v3((sx0, sy0, st['grips'][sd]))
        a = v3((0, 0, 1))
        f = unit(c - j['el_' + sd])
        wrists[sd] = hand_wrist(c, a, f, side_sign)
        hd = local(p, c, 15.0, lambda q, c=c, a=a, f=f, s=side_sign: _hand(q, c, a, f, s))
        hands = hd if hands is None else np.minimum(hands, hd)
    arms_up = None
    for sd in ('l', 'r'):
        sh, el, wr = j['sh_' + sd], j['el_' + sd], wrists[sd]
        upper = limb(p, sh, el, 4.2, 3.5)
        arms_up = upper if arms_up is None else np.minimum(arms_up, upper)
        lo = np.minimum(el, wr) - 8.0
        hi = np.maximum(el, wr) + 8.0
        fore = local(p, (lo + hi) / 2, (hi - lo) / 2, lambda q, el=el, wr=wr: bandage(q, el, wr, 3.8, 3.0))
        body = smin(body, fore, 2.0)
    body = smin(body, arms_up, 3.0)
    body = smin(body, hands, 1.0)

    # Jambes : cuisses (sous la robe), genou posé au sol, jambe de pantalon et pied nu devant.
    for sd in ('l', 'r'):
        body = smin(body, limb(p, j['hip_' + sd], j['knee_' + sd], 7.8, 6.0), 3.0)
    body = smin(body, sphere(p, j['knee_l'], 6.4), 2.0)
    kr, ar = j['knee_r'], j['ankle_r']
    leg = limb(p, kr, ar + up * 7.0, 6.4, 5.0)
    leg = np.maximum(leg, (ar[2] + 6.5) - p[..., 2])                                     # bas du pantalon
    leg = np.minimum(leg, np.maximum(ring(p, ar + up * 7.4, up, 5.6, 0.9, 0.4), leg - 0.6))   # ourlet
    body = smin(body, leg, 2.0)
    lo, hi = ar - v3((26, 26, 9)), ar + v3((26, 26, 12))
    body = smin(body, local(p, (lo + hi) / 2, (hi - lo) / 2, lambda q: _foot(q, ar, P['foot_r_yaw'])), 1.5)

    # Robe, haut : tronc et manches couverts sous le plan de l'encolure (épaule nue du côté de la main
    # basse), bord roulé le long de l'encolure, étoffe tombée en bourrelets autour du bras nu, manche
    # entière jusqu'au coude de l'autre côté, haut col du côté de la main haute.
    n_neck = unit((0.8, 0.1, 1.0))
    above = (p - (j['neck'] - up * 6.0)) @ n_neck
    sleeves = None
    for sd, rad0, rad1 in (('l', 6.0, 5.8), ('r', 7.0, 6.6)):
        sh, el = j['sh_' + sd], j['el_' + sd]
        ua = unit(el - sh)
        L = float(np.linalg.norm(el - sh))
        sl = limb(p, sh, el, rad0, rad1)
        sl = np.maximum(sl, (p - el) @ ua - 0.8)                                       # manche coupée au coude
        cuff = np.maximum(limb(p, sh, el, rad0 + 0.8, rad1 + 0.8), np.abs((p - el) @ ua + 1.6) - 2.4)
        sl = np.minimum(sl, cuff)                                                      # revers
        if sd == 'r':                                                                  # étoffe tombée : bourrelets
            for t in (0.56, 0.74):
                sl = np.minimum(sl, np.maximum(ring(p, sh + ua * (t * L), ua, rad0 + 1.2, 1.1, 0.7), sl - 1.3))
        sleeves = sl if sleeves is None else np.minimum(sleeves, sl)
    garment = smin(torso - 1.6, sleeves, 2.5)
    folds = 0.45 * np.clip(np.cos(TAU * (above + 9.5) / 7.0), 0.0, None) ** 2 * (above > -13.0) * (p[..., 1] < 3.0)
    robe = np.maximum(garment - folds, above)                                            # plis sous l'encolure
    # Bord roulé : 1,7 mm d'étoffe le long de l'encolure, qui s'amincit en pente douce vers le bas de la
    # bande. Coupée net en bas, la bande débordait sur l'épaule couverte en lame de 0,5 mm au-dessus d'un
    # creux (contrôle d'épaisseur du 3 novembre) ; une pente plus raide que l'étoffe elle-même (profil en
    # racine) recreusait ce surplomb, d'où le raccord en S, de pente bornée.
    tr = np.clip((above + 3.8) / 3.2, 0.0, 1.0)
    roll = tr * tr * (3.0 - 2.0 * tr)
    lip = np.maximum(garment - 1.7 * roll, np.abs(above + 1.9) - 1.9)
    robe = np.minimum(robe, lip)
    nb = neck_base
    na = unit(head_pt(0, 1.6, -7.2) - nb)
    qn = p - nb
    hz = qn @ na
    radial = qn - hz[..., None] * na
    rad = np.sqrt(np.einsum('...i,...i->...', radial, radial))
    ang = np.arctan2(radial @ fwd, radial @ side)                                        # 0 : côté nu, π/2 : devant
    span = (np.abs(np.mod(ang - 3.415 + np.pi, TAU) - np.pi) - 1.5) * rad               # côté du col, nuque, devant
    top_c = 6.0 + 1.4 * (1.0 + np.cos(ang - 3.3))                                        # plus haut du côté du col
    collar = np.maximum(np.maximum(rad - (6.8 + 0.13 * hz), 3.6 - rad), np.maximum(-hz - 3.0, hz - top_c))
    robe = np.minimum(robe, np.maximum(collar, span))

    # Robe, bas : jupe pleine étalée au sol autour du genou posé ; cuisse avant couverte ; pan tombé du
    # genou avant, devant et en dehors du tibia, ourlet au-dessus du pied nu.
    dr = P['drape']
    pool, _ = drape(p, j['pelvis'] + up * 8.0, v3((dr['pool_centre'][0], dr['pool_centre'][1], 0.0)),
                    (14.6, 11.2), dr['pool_radii'], folds=10, amp=2.3, phase=0.4, z_floor=1.5)
    pool = smin(pool, sphere(p, j['knee_l'], 8.0), 3.0)                                  # genou sous l'étoffe
    pool = smin(pool, limb(p, j['hip_l'], j['knee_l'], 9.6, 8.0), 3.0)
    thigh = limb(p, j['hip_r'] + v3((0, 2, 0)), kr + unit(kr - j['hip_r']) * 1.5, 10.0, 8.3)
    hem = dr['panel_hem']
    kc = kr + unit(kr - j['hip_r']) * 1.5                                                # centre de la rotule couverte
    # Le pan part de l'équateur du genou (bord extérieur = surface de la rotule couverte, donc sans
    # rebord), tombe presque droit devant le tibia puis s'ouvre à peine sur le pied.
    def edge_fade(theta):                                                               # plis effacés près des bords
        return np.clip((1.571 - np.abs(np.mod(theta + 0.785 + np.pi, TAU) - np.pi)) / 0.6, 0.0, 1.0)
    flap, th = drape(p, kc, kr + v3((1.5, -3.5, hem - kr[2])), (6.6, 6.6), (14.5, 13.0),
                     folds=6, amp=2.4, phase=1.9, shell=1.6, flare=1.7, fold_window=edge_fade)
    flap = np.maximum(flap, (np.abs(np.mod(th + 0.785 + np.pi, TAU) - np.pi) - 1.571) * 11.0)   # devant et dehors seulement
    flap = np.maximum(flap, (hem - 3.0 * np.sin(th) - 3.2 + 0.7 * np.sin(5 * th + 2.0)) - p[..., 2])
    # Union franche : le haut du pan est tangent à l'équateur de la rotule couverte ; une union douce y
    # gonflerait la jonction d'un bourrelet (deux surfaces confondues).
    lower = np.minimum(smin(pool, thigh, 4.0), flap)
    robe = smin(robe, lower, 3.5)
    # Bord croisé du devant : le pan du côté nu recouvre l'autre le long d'une ligne qui descend du col.
    x_edge = -5.0 - 0.12 * (j['neck'][2] - p[..., 2])
    over = (p[..., 0] > x_edge) * np.clip((3.0 - p[..., 1]) / 6.0, 0.0, 1.0)
    robe = robe - 0.9 * over

    d = np.minimum(body, robe)
    lo = v3((sx0 - 7, sy0 - 7, -2.0))
    hi = v3((sx0 + 7, sy0 + 7, st['length'] + 2.0))
    d = np.minimum(d, local(p, (lo + hi) / 2, (hi - lo) / 2, lambda q: _staff(q, st['foot'], st['length'])))
    return np.maximum(d, -p[..., 2])
