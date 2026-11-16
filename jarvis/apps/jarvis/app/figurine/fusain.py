"""« Fusain, le lutteur au trait de charbon » : combattant original BOJ.ART (3 novembre 2026, fiche D17).

Demande d'Olsen : une figurine d'après les pièces que BOJ montre sur TikTok @boj.art. Ces pièces
représentent toutes des personnages protégés ; on n'en reprend que le savoir-faire : grande pièce
de vitrine, socle qui raconte l'action (chez BOJ, des rochers d'où monte un tourbillon de fumée),
volumes faits pour la peinture à la main. Fusain appartient au même univers que Veille (bandages,
basalte, carmin) : il « dessine » ses coups. Son trait, un ruban de charbon en croissant, sort de
colonnes de basalte et monte jusqu'au talon de sa paume ouverte ; deux volutes de fumée enroulées
montent des blocs.

Signes distinctifs : garde en fente avant, jambe gauche fléchie devant, jambe droite tendue ; paume
droite ouverte en avant, doigts vers le haut ; poing gauche ramené à la hanche ; veste sans manches
ouverte en V, col en bande autour du cou, ceinture large nouée ; pantalon ample serré aux mollets par
des bandes ; pieds nus ; avant-bras bandés ; cheveux tirés en arrière en chignon bas torsadé, barbe
courte en collier. Le trait de charbon en travers des yeux est de la peinture, il n'est pas sculpté.

Garde-fous de distinction : ni torse nu en short, ni garde de boxe poings levés, ni cheveux en
pointes ou ébouriffés, ni yeux rougeoyants, ni tatouage, ni chapelet, ni aura de fumée en anneaux,
ni pose signature d'un personnage protégé.

Mêmes conventions que les autres personnages : millimètres, z vers le haut, face vers -y, droite du
personnage vers +x, appuis à z = 0.
"""
from __future__ import annotations

import numpy as np

from .details import FAR, TAU, engrave, fist, hand_wrist, local, obox, oellipsoid, ortho, pipe_folds, ring, unit, v3
from .sculpt import ellipsoid, limb, smin, sphere, ssub
from .veille import _foot, _rotation, bandage

FUSAIN_VERSION = 'bojart.fusain.sdf.v1'
BOUNDS = ((-80.0, -115.0, -6.0), (85.0, 95.0, 175.0))
DETAIL = {'voxel': 0.4, 'smooth_iterations': 3}
# Même socle que Veille : basalte hexagonal qui suit les appuis (fabrication._basalt_base).
SOCLE = 'basalte'

# « palm » : centre de la paume droite, normale (vers la cible), direction des doigts ;
# « fist_l » : centre du poing gauche ramené à la hanche, axe auriculaire → index ;
# « stroke » : le trait (ruban de pinceau), du sol jusqu'au talon de la main droite : chemin, demi-largeur
# et demi-épaisseur aux points du chemin ; le ruban reste dans le plan moyen du chemin (face au spectateur).
POSES = {
    'trait': {
        'label': 'Le trait : fente avant, paume droite ouverte devant, poing gauche à la hanche',
        'pelvis': (0, 4, 78), 'chest': (2, -1, 112), 'neck': (2, -3, 131), 'head': (3, -5, 146),
        'hip_l': (-10, 3, 76), 'knee_l': (-17, -30, 50), 'ankle_l': (-19, -34, 9),
        'hip_r': (10, 6, 76), 'knee_r': (17, 30, 42), 'ankle_r': (24, 54, 9),
        'sh_l': (-25, 9, 123), 'el_l': (-30, 34, 102),
        'sh_r': (24, -10, 124), 'el_r': (29, -41, 124), 'wr_r': (31, -68, 126),
        'palm': {'centre': (32.0, -71.5, 132.5), 'normal': (0.05, -1.0, 0.1), 'fingers': (0.05, 0.12, 1.0)},
        'fist_l': {'centre': (-24.0, 8.0, 94.0), 'a': (-1.0, 0.0, 0.05)},
        'head_turn': (10.0, 0.0, 20.0),
        'foot_yaw': {'l': 5.0, 'r': 35.0},
        'stroke': {'path': [(20.0, -45.0, 0.5), (38.0, -51.0, 8.0), (54.0, -57.0, 28.0), (61.0, -62.0, 55.0),
                            (58.0, -67.0, 84.0), (48.0, -70.0, 108.0), (36.0, -71.5, 128.5)],
                   'half_w': (7.0, 7.8, 7.6, 7.0, 5.9, 4.4, 2.9),
                   'half_t': (1.8, 1.75, 1.65, 1.55, 1.45, 1.35, 1.3)},
        # Volutes de fumée (motif de nuage enroulé) qui montent des blocs de basalte, de part et d'autre
        # du pied du trait.
        'curls': [{'path': [(15.0, -46.0, 1.0), (6.0, -48.0, 8.0), (1.5, -49.0, 17.5), (4.5, -50.0, 26.0),
                            (11.0, -50.0, 28.0), (14.5, -49.5, 23.0), (12.0, -49.5, 19.0), (8.5, -49.5, 20.5),
                            (8.8, -49.5, 23.6)],
                   'half_w': (4.8, 4.4, 3.9, 3.4, 2.9, 2.5, 2.1, 1.8, 1.6),
                   'half_t': (1.5, 1.45, 1.4, 1.35, 1.3, 1.25, 1.25, 1.2, 1.2)},
                  {'path': [(33.0, -47.0, 1.0), (40.0, -45.0, 6.0), (43.0, -44.0, 13.0), (40.0, -43.5, 18.5),
                            (35.5, -43.5, 17.0), (36.0, -43.5, 13.5), (39.0, -43.5, 14.5)],
                   'half_w': (3.8, 3.4, 2.9, 2.5, 2.1, 1.8, 1.6),
                   'half_t': (1.4, 1.35, 1.3, 1.25, 1.2, 1.2, 1.2)}],
        # Blocs de basalte au pied du trait : centre (x, y), rayon du prisme, hauteur, rotation (degrés).
        'rocks': [((24.0, -37.0), 7.0, 12.0, 8.0), ((35.0, -50.0), 6.0, 7.0, 31.0), ((10.0, -55.0), 5.5, 5.0, 17.0),
                  ((15.0, -40.0), 4.5, 7.5, 44.0)],
    },
}
INTENT_POSES = {'combat': 'trait', 'rest': 'trait', 'iconic': 'trait'}

JITTER = v3((0.0011, 0.0019, 0.0027))
HEAD_SCALE = 1.12


def _face(q, ears=True):
    """Visage construit, repère local (face vers -y, centre du crâne à l'origine), tête de 23 mm :
    même construction que la tête d'Ardoise v6 (fiche D13), sans ses signes propres (cicatrice,
    strates), avec une mâchoire plus carrée. Arcades allégées et yeux avancés : avec des arcades de
    1,35 mm et des orbites creusées, le haut du visage se lisait comme un masque (3 novembre 2026)."""
    d = ellipsoid(q, (0, 1.4, 1.6), (9.2, 10.6, 9.2))                                   # crâne
    d = smin(d, ellipsoid(q, (0, -5.5, 3.0), (7.4, 4.6, 5.8)), 2.5)                     # front
    d = smin(d, obox(q, v3((0, -5.2, -4.2)), v3((1, 0, 0)), v3((0, 1, 0)), (6.6, 4.6, 5.6), 3.2), 2.2)  # masse du visage
    for sx in (-1, 1):
        d = smin(d, limb(q, v3((sx * 8.1, 0.4, -3.4)), v3((sx * 4.4, -6.6, -10.6)), 2.9, 2.6), 2.0)   # mâchoire carrée
        d = smin(d, ellipsoid(q, (sx * 5.7, -7.2, -2.1), (2.3, 1.9, 1.5)), 1.6)                       # pommette
        d = smin(d, limb(q, v3((sx * 6.6, -8.6, 2.5)), v3((sx * 1.4, -10.0, 1.9)), 1.05, 1.05), 1.3)  # arcade
    d = smin(d, ellipsoid(q, (0, -7.6, -10.8), (4.8, 2.9, 2.3)), 1.6)                   # menton
    d = smin(d, sphere(q, (0, -10.0, 1.5), 1.1), 1.0)                                   # glabelle
    for sx in (-1, 1):
        d = ssub(d, sphere(q, (sx * 3.9, -10.6, 0.4), 1.45), 0.5)                      # orbite
        d = np.minimum(d, sphere(q, (sx * 3.9, -8.85, 0.0), 1.5))                       # globe oculaire
        d = smin(d, limb(q, v3((sx * 5.5, -9.85, 0.95)), v3((sx * 2.4, -10.2, 1.05)), 0.55, 0.55), 0.3)  # paupière
    d = smin(d, limb(q, v3((0, -9.9, 0.6)), v3((0, -11.9, -4.6)), 1.1, 1.55), 0.8)      # arête du nez
    d = smin(d, sphere(q, (0, -12.0, -4.9), 1.55), 0.6)                                 # bout du nez
    for sx in (-1, 1):
        d = smin(d, sphere(q, (sx * 1.55, -10.7, -5.4), 1.05), 0.6)                    # ailes du nez
    d = smin(d, oellipsoid(q, v3((0, -10.0, -7.3)), v3((1, 0, 0)), v3((0, 0, 1)), (2.9, 0.95, 1.1)), 0.6)  # lèvre sup.
    d = smin(d, oellipsoid(q, v3((0, -9.7, -8.6)), v3((1, 0, 0)), v3((0, 0, 1)), (2.5, 0.9, 1.1)), 0.6)   # lèvre inf.
    d = engrave(d, np.maximum(np.abs(q[..., 2] + 7.95) - 0.22, np.abs(q[..., 0]) - 2.3), 0.35)          # bouche
    return smin(d, _ears(q), 0.6) if ears else d


def _ears(q):
    d = None
    for sx in (-1, 1):
        ear = oellipsoid(q, v3((sx * 9.4, 1.0, -1.6)), v3((1, 0, 0)), v3((0, 1, 0)), (1.6, 3.0, 4.2))
        ear = ssub(ear, sphere(q, (sx * 10.7, 0.6, -2.0), 1.6), 0.4)                  # conque
        ear = smin(ear, sphere(q, (sx * 9.4, 0.6, -5.4), 1.2), 0.6)                    # lobe
        d = ear if d is None else np.minimum(d, ear)
    return d


def _smax(a, b, k):
    return -smin(-a, -b, k)


# Ligne des cheveux selon l'angle autour de la verticale (0° : milieu du front, 180° : nuque) :
# front, tempes, départ des favoris (la barbe monte à leur rencontre), dessus de l'oreille, nuque.
# Un favori de cheveux descendu jusqu'à la joue faisait une plaque plate coupée par deux plans.
HAIRLINE_DEG = (0.0, 40.0, 58.0, 63.0, 72.0, 77.0, 112.0, 125.0, 180.0)
HAIRLINE_Z = (5.8, 4.4, 3.4, 2.6, 2.6, 3.4, 3.6, -5.5, -8.5)
# Les mèches sont des méridiens autour d'un axe qui sort sous le visage et entre dans le chignon :
# parallèles sur le dessus, elles convergent vers le chignon (cheveux tirés en arrière).
HAIR_POLE_FRONT = v3((0.0, -14.0, -8.0))
BEARD_JAW = ((8.3, -0.4, -3.0), (4.4, -6.6, -10.6), (0.0, -7.6, -10.8))   # axe de la mâchoire (côté droit)
BUN_CENTRE = v3((0.0, 14.0, -2.2))


def _head(q):
    """Tête complète : visage, barbe courte en collier (1,25 mm, des favoris au menton, mèches à peine
    marquées au menton, lèvres dégagées sous la moustache), cheveux tirés en arrière (1,3 mm, mèches
    larges et douces de 0,5 mm de relief) noués en chignon bas torsadé, tenu par un lien."""
    face = _face(q, ears=False)                      # barbe et cheveux tirés du visage sans les oreilles
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    # Barbe courte en collier : bande le long de la mâchoire, du favori au menton, épaisse de 1,25 mm
    # et nulle sur ses bords (aucune marche ni lame). L'épaisseur ne peut que diminuer quand on s'éloigne
    # du visage (distance à l'axe de la mâchoire) : une épaisseur qui grandissait vers l'extérieur
    # (bord réglé sur |x|) décollait la barbe des joues en lame (3 novembre 2026). Joues dégagées.
    d_jaw = d_side = None
    for sx in (-1.0, 1.0):
        jaw = [v3((sx * a, b, c)) for a, b, c in BEARD_JAW]
        for a, b in zip(jaw[:-1], jaw[1:]):
            dd = _seg_dist(q, a, b)
            d_jaw = dd if d_jaw is None else np.minimum(d_jaw, dd)
        dd = _seg_dist(q, v3((sx * 8.9, -1.6, 2.6)), v3((sx * 8.3, -0.4, -3.0)))      # favori
        d_side = dd if d_side is None else np.minimum(d_side, dd)
    band = np.maximum(np.clip((5.0 - d_jaw) / 1.6, 0.0, 1.0), np.clip((3.0 - d_side) / 1.2, 0.0, 1.0))
    band = band * np.clip(ellipsoid(q, (0, -10.2, -7.9), (3.0, 2.6, 1.6)) / 0.6, 0.0, 1.0)   # lèvres dégagées
    fade = band * band * (3.0 - 2.0 * band)
    tuft = np.clip((-z - 9.5) / 3.0, 0.0, 1.0)
    beard = face - fade * (1.25 + 0.16 * tuft * np.cos(TAU * x / 2.6))
    beard = smin(beard, ellipsoid(q, (0, -8.3, -12.4), (3.8, 2.9, 2.3)), 1.2)           # barbe carrée au menton
    d = smin(np.minimum(face, beard), _ears(q), 0.6)
    for sx in (-1, 1):                                                                   # moustache
        d = smin(d, limb(q, v3((sx * 0.35, -10.6, -6.35)), v3((sx * 3.4, -9.6, -8.4)), 0.75, 0.5), 0.35)
    # Cheveux : calotte de 1,3 mm au-dessus de la ligne des cheveux.
    hair = ellipsoid(q, (0, 1.4, 1.7), (10.5, 12.0, 10.6))
    psi = np.degrees(np.abs(np.arctan2(x, -y)))
    line = np.interp(psi.ravel(), HAIRLINE_DEG, HAIRLINE_Z).reshape(psi.shape)
    hair = _smax(hair, line - z, 0.8)
    # Couche qui épouse la tête et s'amincit sur ses 2 derniers millimètres (bord de cheveux sans
    # marche) ; l'ellipsoïde seul remplissait le creux des tempes.
    hair = np.maximum(hair, face - (0.35 + 1.25 * np.clip((z - line) / 2.0, 0.0, 1.0)))
    axis = unit(BUN_CENTRE - HAIR_POLE_FRONT)
    e1 = v3((1.0, 0.0, 0.0))
    e2 = unit(np.cross(axis, e1))
    if e2[2] < 0:
        e2 = -e2
    r = q - BUN_CENTRE
    th = np.arctan2(r @ e1, r @ e2)
    hair = hair + 0.25 * np.cos(18.0 * th + 0.05 * (r @ axis)) + 0.06 * np.cos(54.0 * th + 0.7)
    d = np.minimum(d, hair)
    # Chignon bas torsadé et son lien.
    bun = ellipsoid(q, BUN_CENTRE, (4.8, 3.9, 4.4))
    rb = q - BUN_CENTRE
    ang = np.arctan2(rb[..., 2], rb[..., 0])
    rad = np.sqrt(rb[..., 0] ** 2 + rb[..., 2] ** 2)
    bun = bun + 0.3 * np.cos(2.0 * ang - 2.3 * rad) * np.clip(rad / 2.0, 0.0, 1.0)
    tie = ring(q, BUN_CENTRE - v3((0.0, 2.6, 0.0)), v3((0.0, 1.0, 0.1)), 3.4, 0.75, 0.45)
    return smin(d, np.minimum(bun, tie), 0.8)


def _open_hand(p, c, n, fingers, side):
    """Main ouverte en frappe de paume : paume en bloc, quatre doigts serrés tendus vers le haut et
    légèrement creusés, pouce replié le long de l'index. n : normale de la paume (vers la cible).
    Les doigts se touchent sur toute leur longueur (un pli les sépare) : une fente de 0,2 à 0,3 mm
    entre deux doigts ne s'imprime pas et se maillait en voiles minces (3 novembre 2026)."""
    n = unit(n)
    u = ortho(fingers, n)                            # vers le bout des doigts
    a = np.cross(n, u) * side                        # de l'auriculaire vers l'index
    c = v3(c)
    d = obox(p, c, u, a, (5.6, 5.0, 2.4), 1.7)                                          # paume
    d = smin(d, oellipsoid(p, c - u * 3.4 + a * 3.2 + n * 0.4, u, a, (3.8, 2.6, 2.6)), 1.2)   # éminence du pouce
    for k, L in enumerate((9.8, 10.8, 10.2, 8.4)):
        off = (1.5 - k) * 2.3
        base = c + u * 4.6 + a * off
        tip = base + u * L + n * (0.5 + 0.25 * k)                                         # doigts un peu creusés
        d = smin(d, limb(p, base, tip, 1.2, 1.15), 0.35)
    t0 = c - u * 2.6 + a * 4.6 - n * 0.4
    t1 = c + u * 3.4 + a * 5.8 - n * 0.9
    return smin(d, limb(p, t0, t1, 1.6, 1.25), 0.6)                                     # pouce le long de l'index


def _catmull(pts, n):
    """Rééchantillonne un chemin par une spline de Catmull-Rom (n points, extrémités comprises)."""
    P = np.array([v3(t) for t in pts])
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    m = len(P) - 3
    for i in range(n):
        u = i / (n - 1) * m
        k = min(int(u), m - 1)
        t = u - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out, np.float32)


def _ribbon(p, C, hw, ht, W, r=0.7):
    """Ruban continu balayé le long du chemin C (m points) : section rectangulaire arrondie de
    demi-largeur hw et de demi-épaisseur ht (par point), largeur selon W (par point) ; bouts coupés
    d'équerre. Un ruban fait de boîtes successives montrait des festons à chaque raccord.
    Renvoie la SDF, l'abscisse relative s (0 → 1), la position dans la largeur u (mm) et hw local."""
    m = len(C)
    shape = p.shape[:-1]
    best = np.full(shape, np.inf, np.float32)
    bi = np.zeros(shape, np.int32)
    bt = np.zeros(shape, np.float32)
    for i in range(m - 1):
        a = C[i]
        ab = C[i + 1] - a
        t = np.clip(((p - a) @ ab) / float(ab @ ab), 0.0, 1.0)
        q = p - (a + t[..., None] * ab)
        d2 = np.einsum('...k,...k->...', q, q)
        better = d2 < best
        best = np.where(better, d2, best)
        bi = np.where(better, i, bi)
        bt = np.where(better, t, bt)
    w = bt[..., None]
    S = C[bi] * (1.0 - w) + C[bi + 1] * w
    T = C[bi + 1] - C[bi]
    T = T / np.linalg.norm(T, axis=-1, keepdims=True)
    Wm = W[bi] * (1.0 - w) + W[bi + 1] * w
    Wm = Wm - np.einsum('...k,...k->...', Wm, T)[..., None] * T
    Wm = Wm / np.linalg.norm(Wm, axis=-1, keepdims=True)
    V = np.cross(T, Wm)
    q = p - S
    u = np.einsum('...k,...k->...', q, Wm)
    v = np.einsum('...k,...k->...', q, V)
    al = np.einsum('...k,...k->...', q, T)
    hwi = hw[bi] * (1.0 - bt) + hw[bi + 1] * bt
    hti = ht[bi] * (1.0 - bt) + ht[bi + 1] * bt
    dx = np.abs(u) - (hwi - r)
    dy = np.abs(v) - (hti - r)
    d = np.minimum(np.maximum(dx, dy), 0.0) + np.sqrt(np.maximum(dx, 0.0) ** 2 + np.maximum(dy, 0.0) ** 2) - r
    end = ((bi == 0) & (bt <= 0.0)) | ((bi == m - 2) & (bt >= 1.0))
    e = np.where(end, np.abs(al), -1e3)
    d = np.minimum(np.maximum(d, e), 0.0) + np.sqrt(np.maximum(d, 0.0) ** 2 + np.maximum(e, 0.0) ** 2)
    return d, (bi + bt) / (m - 1), u, hwi


def stroke_frames(st, n=64):
    """Chemin rééchantillonné du trait, demi-largeurs, demi-épaisseurs et direction de la largeur
    (dans le plan moyen du chemin, orthogonale au chemin)."""
    pts = st['path']
    C = _catmull(pts, n)
    k = np.arange(n) / (n - 1) * (len(pts) - 1)
    hw = np.interp(k, np.arange(len(pts)), st['half_w']).astype(np.float32)
    ht = np.interp(k, np.arange(len(pts)), st['half_t']).astype(np.float32)
    P = np.array([v3(t) for t in pts])
    normal = np.linalg.svd(P - P.mean(axis=0))[2][2]
    if normal[1] > 0:
        normal = -normal                                       # face tournée vers l'avant (-y)
    T = np.gradient(C, axis=0)
    W = np.cross(normal[None, :], T)
    W = (W / np.linalg.norm(W, axis=1, keepdims=True)).astype(np.float32)
    return C, hw, ht, W


def _hex_prism(p, c, r, h, yaw_deg):
    """Prisme hexagonal vertical (colonne de basalte) posé à z = 0 : rayon inscrit r, hauteur h, arêtes
    adoucies de 0,6 mm, dessus légèrement penché pour casser la régularité."""
    a = np.radians(yaw_deg)
    x = (p[..., 0] - c[0]) * np.cos(a) + (p[..., 1] - c[1]) * np.sin(a)
    y = -(p[..., 0] - c[0]) * np.sin(a) + (p[..., 1] - c[1]) * np.cos(a)
    k = (-0.8660254, 0.5, 0.57735)
    qx, qy = np.abs(x), np.abs(y)
    dot = np.minimum(k[0] * qx + k[1] * qy, 0.0)
    qx, qy = qx - 2.0 * dot * k[0], qy - 2.0 * dot * k[1]
    rr = r - 0.6
    dx = np.sqrt((qx - np.clip(qx, -k[2] * rr, k[2] * rr)) ** 2 + (qy - rr) ** 2) * np.sign(qy - rr)
    top = h - 0.6 + 0.12 * x
    dz = p[..., 2] - top
    return np.minimum(np.maximum(dx, dz), 0.0) + np.sqrt(np.maximum(dx, 0.0) ** 2 + np.maximum(dz, 0.0) ** 2) - 0.6


def _curl(p, st):
    """Volute de fumée de charbon : ruban qui sort des blocs, monte et s'enroule sur lui-même (motif
    de nuage enroulé de la peinture à l'encre), une strie au milieu."""
    C, hw, ht, W = stroke_frames(st, n=48)
    d, s, u, hwi = _ribbon(p, C, hw, ht, W)
    return engrave(d, np.maximum(np.abs(u) - 0.2, s - 0.8), 0.3)


# Stries de poils du trait : position dans la largeur (-1 → 1), début et fin (abscisse relative),
# demi-largeur, profondeur, demi-largeur du trait sous laquelle la strie s'efface. Irrégulières et
# interrompues : des stries parallèles sur toute la longueur se lisaient comme une tôle ondulée. Une
# strie sur deux s'efface quand le trait s'affine, pour garder des crêtes d'au moins 0,8 mm entre deux
# sillons à 20 cm ; la première version en gardait neuf jusqu'à la main : leurs sillons se chevauchaient,
# creusaient deux fois et perçaient le ruban (contrôle d'épaisseur à 0,4 mm, 3 novembre 2026).
STREAKS = ((-0.66, 0.00, 0.62, 0.28, 0.30, 6.2), (-0.44, 0.22, 1.00, 0.26, 0.42, 2.0),
           (-0.22, 0.00, 0.50, 0.30, 0.26, 6.2), (0.00, 0.30, 0.90, 0.26, 0.38, 3.6),
           (0.22, 0.00, 0.70, 0.27, 0.32, 6.2), (0.44, 0.12, 1.00, 0.26, 0.45, 2.0),
           (0.66, 0.05, 0.58, 0.28, 0.28, 6.2))


def _stroke(p, st):
    """Le trait : ruban plat de 2,6 à 3,6 mm d'épaisseur, tracé comme un coup de pinceau qui sort des
    blocs de basalte (appui large, posé à plat), monte en croissant devant le spectateur et s'affine
    jusqu'au talon de la main (troisième appui du bras tendu). Stries de poils irrégulières et
    interrompues, plus profondes vers le haut (pinceau qui sèche), gravées en une seule passe (le sillon
    le plus proche décide de la profondeur, rien ne se cumule) et jamais plus profondes que 30 % de la
    demi-épaisseur : l'âme du ruban garde 70 % de son épaisseur. Il se peint en charbon et carmin, la
    couleur du geste dans la DA BOJ.ART."""
    C, hw, ht, W = stroke_frames(st)
    d, s, u, hwi = _ribbon(p, C, hw, ht, W)
    hti = np.interp(s * (len(C) - 1), np.arange(len(C)), ht)
    band = depth = None
    for k, s0, s1, w, dep, h_min in STREAKS:                   # stries de poils
        uk = k * hwi + 0.035 * hwi * np.sin(7.0 * s) + 0.06 * np.sin(11.0 * s + 5.0 * k)
        bk = np.maximum(np.abs(u - uk) - w, np.maximum(s0 - s, s - s1))
        dk = (np.minimum(dep * (0.7 + 0.6 * s), np.minimum(0.55, 0.3 * hti))
              * np.clip((hwi - h_min) / 0.8, 0.0, 1.0))
        if band is None:
            band, depth = bk, dk
        else:
            nearer = bk < band
            band, depth = np.where(nearer, bk, band), np.where(nearer, dk, depth)
    d = engrave(d, band, depth)
    foot = C[0]
    d = smin(d, ellipsoid(p, foot + v3((2.0, -1.0, 0.6)), (11.5, 8.0, 2.4)), 2.5)        # appui écrasé
    return d


def fusain_sdf(p, pose: str):
    """SDF de Fusain seul (sans socle), en mm, appuis à z = 0."""
    return np.maximum(_built(p + JITTER, POSES[pose]), -p[..., 2])


def _seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / float(ab @ ab), 0.0, 1.0)
    q = p - (a + t[..., None] * ab)
    return np.sqrt(np.einsum('...k,...k->...', q, q))


# Rayon du raccord du poignet : poing gauche (`details.fist`, 3,3 mm) et main ouverte (4 mm).
WRIST_R = {'l': 3.3, 'r': 4.0}


def _forearm_wrap(q, a, b, r_end):
    """Avant-bras bandé, de 5,4 à 4 mm de rayon, dont les deux derniers millimètres se resserrent en cône
    jusqu'au rayon du raccord du poignet. Coupée net, la bande dépassait du raccord du poing gauche en
    anneau à dents de scie de 0,7 à 1,15 mm : lèvre de 0,13 mm d'épaisseur au contrôle local
    (3 novembre 2026)."""
    ax = unit(b - a)
    L = float(np.linalg.norm(b - a))
    s = (q - a) @ ax
    radial = np.sqrt(np.maximum(np.einsum('...i,...i->...', q - a, q - a) - s * s, 0.0))
    return np.maximum(bandage(q, a, b, 5.4, 4.0), radial - (r_end + (L - s) * 0.6))


# Sommets d'un tétraèdre : gradient par différences en quatre évaluations (somme des k·f(p + h·k) = 4h·∇f).
_TETRA = np.array([[1.0, -1.0, -1.0], [-1.0, -1.0, 1.0], [-1.0, 1.0, -1.0], [1.0, 1.0, 1.0]], np.float32)


def _garment(p, trunk, trunk_at, upper_arm_at, j, up, lat, sfw, upl, neck_a, neck_b, belt_c):
    """Veste, col, ourlets d'emmanchure et ceinture : couches de 2, 3, 2,7 et 3,2 mm sur le tronc. Chaque
    coupe est lue au pied de la normale (le point du tronc sous le point évalué), si bien que chaque bord
    traverse la couche d'équerre, quelle que soit la forme du tronc. Calculée seulement près du tronc ;
    FAR ailleurs (dans le tronc, le corps est déjà plein)."""
    out = np.full(p.shape[:-1], FAR, np.float32)
    near = (trunk < 3.5) & (trunk > -1.5)
    if not near.any():
        return out
    q = p[near]
    tq = trunk[near]
    g = sum(k * trunk_at(q + 0.3 * k)[..., None] for k in _TETRA)
    n = g / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-6)
    b = (q - tq[..., None] * n).astype(np.float32)                                      # pied de la normale
    rel = b - j['chest']
    hgt = rel @ up
    lx = rel @ lat
    front = rel @ sfw
    hw_v = np.clip(9.5 * (hgt + 14.0) / 28.0, 0.0, None)                                # V : pointe au plexus
    opening = np.minimum(_seg_dist(b, neck_a, neck_b) - 10.5, np.maximum(np.abs(lx) - hw_v, -front))  # < 0 : nu
    bottom = -(hgt + 27.0)
    # Emmanchure : ellipsoïde autour de l'épaule, élargie jusqu'à 4 mm du bras, mesurés sur le tronc. Le
    # bord monte d'au plus 3 mm : il reste à 1 mm au moins du bras, même là où le bras couvre le dos
    # (bras gauche). Au contact, le bord fermait une poche creuse sous le deltoïde ou une lame sous le bras
    # gauche (3 novembre 2026).
    holes = [np.minimum(oellipsoid(b, j['sh_' + sd] - up * 2.5 + lat * (sx * 1.5), lat, upl, (9.5, 12.5, 10.5)),
                        upper_arm_at(b, sd, sx) - 4.0)
             for sd, sx in (('l', -1.0), ('r', 1.0))]
    keep = np.maximum(np.maximum(bottom, -opening), np.maximum(-holes[0], -holes[1]))
    vest = np.maximum(tq - 2.0, keep)
    collar = np.maximum(tq - 3.0, np.maximum(np.maximum(opening - 4.0, keep), -opening))
    vest = np.minimum(vest, collar)
    for hole in holes:                                                                   # ourlets d'emmanchure
        hem = np.maximum(tq - 2.7, np.maximum(np.maximum(bottom, -opening), np.maximum(hole - 1.6, -hole)))
        vest = np.minimum(vest, hem)
    # Ceinture large : bande de 10,4 mm de haut, mesurée sur le tronc. Coupée par deux plans dans l'espace,
    # son arête haute faisait un coin aigu (67°) là où la cage s'évase au-dessus de la taille, côté droit :
    # 0,25 mm d'épaisseur sur la contre-vérification à 12 000 points (3 novembre 2026).
    belt = np.maximum(tq - 3.2, np.abs((b - belt_c) @ up) - 5.2)
    out[near] = np.minimum(vest, belt)
    return out


def _built(p, P):
    j = {k: v3(v) for k, v in P.items() if isinstance(v, tuple) and len(v) == 3}
    up = unit(j['neck'] - j['pelvis'])
    fwd = ortho(v3((0, -1, 0)), up)
    side = np.cross(up, fwd)
    lat = unit(j['sh_r'] - j['sh_l'])                     # épaules tournées : la droite pousse devant
    sfw = ortho(np.cross(up, lat), up)
    if float(sfw @ fwd) < 0:
        sfw = -sfw
    upl = ortho(up, lat)

    # Tronc héroïque : cage large, pectoraux, grands dorsaux, taille, bassin, trapèzes, cou épais.
    def trunk_at(q):
        t = oellipsoid(q, j['chest'] + up * 2.0, lat, up, (23.5, 15.0, 14.0))
        t = smin(t, oellipsoid(q, j['pelvis'] + up * 16.0, lat, up, (17.5, 12.0, 11.5)), 6.0)
        t = smin(t, oellipsoid(q, j['pelvis'], side, up, (16.5, 11.0, 12.0)), 5.0)
        for sx, sd in ((-1, 'l'), (1, 'r')):
            sh = j['sh_' + sd]
            t = smin(t, oellipsoid(q, j['chest'] + up * 4.0 + lat * (sx * 9.5) + sfw * 9.5, lat, up,
                                   (10.5, 7.6, 5.0)), 3.0)                                    # pectoral
            t = smin(t, oellipsoid(q, j['chest'] - up * 5.0 + lat * (sx * 16.5) - sfw * 2.0, up, lat,
                                   (12.0, 6.0, 7.5)), 4.0)                                    # grand dorsal
            t = smin(t, limb(q, j['neck'] - up * 3.0 - sfw * 2.0, sh + up * 2.0, 7.0, 5.4), 4.0)   # trapèze
        return t

    # Le tronc sans le cou porte l'étoffe ; avec le cou, la couche de 3 mm du col faisait autour du cou un
    # cylindre presque confondu avec le bord de l'encolure : lame derrière la nuque (3 novembre 2026).
    trunk = trunk_at(p)
    neck_a, neck_b = j['chest'] + up * 12.0, j['head'] + v3((0, 2.0, -9.0))
    body = smin(trunk, limb(p, neck_a, neck_b, 7.4, 6.2), 3.0)                                    # cou

    # Bras nus, musclés, avant-bras bandés jusqu'au poignet (peau : fusion douce avec le tronc).
    palm = P['palm']
    pc, pn, pf = v3(palm['centre']), unit(palm['normal']), unit(palm['fingers'])
    fl = P['fist_l']
    fc, fa = v3(fl['centre']), unit(fl['a'])
    f_l = unit(fc - j['el_l'])
    wrists = {'l': hand_wrist(fc, fa, f_l, -1.0), 'r': j['wr_r']}

    def upper_arm_at(q, sd, sx):
        sh, el = j['sh_' + sd], j['el_' + sd]
        ua = unit(el - sh)
        out = ortho(lat * sx, ua)
        arm = limb(q, sh, el, 7.6, 5.8)
        return smin(arm, oellipsoid(q, sh + ua * 4.0 + up * 1.2 + out * 1.5, ua, out, (10.5, 7.6, 7.6)), 2.5)   # deltoïde

    for sd, sx in (('l', -1.0), ('r', 1.0)):
        sh, el, wr = j['sh_' + sd], j['el_' + sd], wrists[sd]
        ua = unit(el - sh)
        L1 = float(np.linalg.norm(el - sh))
        fr = ortho(sfw, ua)
        out = ortho(lat * sx, ua)
        arm = upper_arm_at(p, sd, sx)
        arm = smin(arm, oellipsoid(p, sh + ua * (L1 * 0.6) + fr * 2.8, ua, fr, (L1 * 0.3, 4.9, 5.0)), 1.8)      # biceps
        arm = smin(arm, oellipsoid(p, sh + ua * (L1 * 0.45) - fr * 2.8, ua, fr, (L1 * 0.34, 4.6, 5.0)), 1.8)    # triceps
        fa_ax = unit(wr - el)
        fo = ortho(out, fa_ax)
        arm = smin(arm, limb(p, el, el + (wr - el) * 0.4, 6.4, 5.4), 2.0)
        arm = smin(arm, oellipsoid(p, el + fa_ax * 5.5 + fo * 2.0, fa_ax, fo, (7.5, 4.2, 4.0)), 1.6)            # long supinateur
        lo, hi = np.minimum(el, wr) - 9.0, np.maximum(el, wr) + 9.0
        a0 = el + (wr - el) * 0.32
        r_end = WRIST_R[sd]
        wrap = local(p, (lo + hi) / 2, (hi - lo) / 2, lambda q, a=a0, b=wr, r=r_end: _forearm_wrap(q, a, b, r))
        body = smin(body, smin(arm, wrap, 1.2), 3.0)

    hand_r = local(p, pc, 19.0, lambda q: _open_hand(q, pc, pn, pf, 1.0))
    body = smin(body, smin(hand_r, limb(p, j['wr_r'], pc - pf * 4.0, 4.0, 3.8), 1.5), 1.0)
    hand_l = local(p, fc, 15.0, lambda q: fist(q, fc, fa, f_l, -1.0))
    body = smin(body, hand_l, 1.0)

    # Tête agrandie de 12 % (lisibilité à 20 cm, comme Veille), tournée vers la main ouverte.
    R = _rotation(*P['head_turn'])
    h = j['head']
    body = smin(body, local(p, h, 24.0, lambda q: _head(((q - h) @ R) / HEAD_SCALE) * HEAD_SCALE), 2.0)

    # Veste sans manches (étoffe, union franche : ses bords restent nets) : coque de 2 mm sur le tronc,
    # emmanchures dégagées autour des épaules avec ourlet roulé, encolure ronde, V croisé au plexus ;
    # col en bande de 4 mm (relief 1 mm) qui fait le tour du cou et descend le long du V ; le bas
    # disparaît sous la ceinture. Les coupes (encolure, V, emmanchures, bas) sont lues au pied de la
    # normale, sur le tronc : chaque bord est extrudé d'équerre à travers la couche. Des coupes lues dans
    # l'espace passaient presque parallèles à la couche (bord d'encolure autour de la bosse des trapèzes,
    # ourlet d'emmanchure en capuchon au-dessus du deltoïde, ourlet le long du bras gauche couché dans le
    # dos) et laissaient des lames de 0,05 à 0,4 mm (contrôle à 0,4 mm, 3 novembre 2026).
    #
    # Ceinture large qui épouse la taille (3,2 mm sur le tronc, 1,2 mm sur la veste ; un ellipsoïde
    # bombait en dôme sous le V), coupée elle aussi au pied de la normale (dans `_garment`), nouée sur la
    # hanche gauche, deux pans pendants.
    belt_c = j['pelvis'] + up * 9.5
    body = np.minimum(body, _garment(p, trunk, trunk_at, upper_arm_at, j, up, lat, sfw, upl, neck_a, neck_b,
                                     belt_c))
    knot_c = belt_c - side * 11.5 + fwd * 9.0
    body = smin(body, ellipsoid(p, knot_c, (3.8, 3.2, 3.6)), 0.8)
    for dx, L in ((-1.6, 16.0), (2.6, 12.5)):
        tail = obox(p, knot_c + side * dx - up * (L / 2 + 2.0) + fwd * 0.8, up, side, (L / 2, 2.5, 1.4), 0.8)
        body = np.minimum(body, tail)

    # Jambes dans un pantalon ample (plis tuyaux), serré au mollet par des bandes, pieds nus.
    for sd in ('l', 'r'):
        hip, knee, ank = j['hip_' + sd], j['knee_' + sd], j['ankle_' + sd]
        leg = smin(limb(p, hip, knee, 11.6, 9.6), limb(p, knee, knee + (ank - knee) * 0.55, 9.6, 8.8), 3.0)
        kd = unit(knee - hip)
        kf = ortho(fwd, kd)
        th = np.arctan2((p - hip) @ np.cross(kd, kf), (p - hip) @ kf)
        along = (p - hip) @ kd
        tt = np.clip(along / float(np.linalg.norm(knee - hip)), 0.0, 1.0)
        # Plis effacés près de l'axe de la cuisse : prolongé sous le genou plié, cet axe ressort devant le
        # tibia, où les sept plis se rejoignaient en étoile de lames (genou gauche, 3 novembre 2026).
        axis_r = np.sqrt(np.maximum(np.einsum('...k,...k->...', p - hip, p - hip) - along * along, 0.0))
        leg = leg - (pipe_folds(th, tt, n=7, amp=1.2, phase=1.3 if sd == 'l' else 0.2)
                     * np.clip((axis_r - 3.0) / 4.0, 0.0, 1.0))
        shin_mid = knee + (ank - knee) * 0.55
        lo, hi = np.minimum(shin_mid, ank) - 9.0, np.maximum(shin_mid, ank) + 9.0
        wrap = local(p, (lo + hi) / 2, (hi - lo) / 2,
                     lambda q, a=shin_mid, b=ank + v3((0, 0, 3.0)): bandage(q, a, b, 5.8, 4.0, pitch=3.4, step=0.45))
        mx = v3((-1.0 if sd == 'l' else 1.0, 1.0, 1.0))
        foot = local(p, v3((ank[0], ank[1], 10.0)), v3((24.0, 24.0, 12.0)),
                     lambda q, ank=ank, yaw=P['foot_yaw'][sd], mx=mx: _foot(q * mx, ank * mx, yaw))
        body = smin(body, smin(smin(leg, wrap, 1.5), foot, 2.0), 3.0)

    # Le trait, du rocher jusqu'à la main, sa volute de fumée et les blocs de basalte d'où il sort.
    st = P['stroke']
    sm = np.array(st['path'])
    lo, hi = sm.min(axis=0) - 16.0, sm.max(axis=0) + 16.0
    body = smin(body, local(p, (lo + hi) / 2, (hi - lo) / 2, lambda q: _stroke(q, st)), 1.2)
    for cl in P['curls']:
        cu = np.array(cl['path'])
        lo, hi = cu.min(axis=0) - 9.0, cu.max(axis=0) + 9.0
        body = smin(body, local(p, (lo + hi) / 2, (hi - lo) / 2, lambda q, cl=cl: _curl(q, cl)), 1.5)
    for (cx, cy), r, hgt_r, yaw in P['rocks']:
        rock = local(p, v3((cx, cy, hgt_r / 2)), v3((r + 4.0, r + 4.0, hgt_r / 2 + 4.0)),
                     lambda q, c=(cx, cy), r=r, h=hgt_r, a=yaw: _hex_prism(q, c, r, h, a))
        body = smin(body, rock, 1.0)
    return body
