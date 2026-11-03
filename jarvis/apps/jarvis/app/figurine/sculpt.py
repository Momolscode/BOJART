"""Sculpture procédurale par champs de distance (SDF) du personnage original de contrôle.

« La Sentinelle de l'atelier » est une création BOJ.ART pour ce test : gardienne trapue,
casque arrondi à crête, épaulières, écharpe, maillet de sculpteur. Ce module ne contient
aucun personnage tiers : un personnage sous licence passe par l'import d'un maillage.

Unités internes : millimètres, z vers le haut, figurine nominale d'environ 180 mm
(socle exclu), mise à l'échelle ensuite sur la hauteur demandée.
"""
from __future__ import annotations

import math

import numpy as np

SCULPT_VERSION = 'bojart.sentinelle.sdf.v1'


# ---------------------------------------------------------------- primitives SDF
def _len(v):
    return np.sqrt(np.einsum('...i,...i->...', v, v))


def sphere(p, c, r):
    return _len(p - np.asarray(c, np.float32)) - r


def ellipsoid(p, c, radii):
    radii = np.asarray(radii, np.float32)
    q = (p - np.asarray(c, np.float32)) / radii
    return (_len(q) - 1.0) * float(radii.min())


def limb(p, a, b, ra, rb):
    """Capsule à rayon variable (approximation de distance suffisante pour l'isosurface)."""
    a = np.asarray(a, np.float32)
    b = np.asarray(b, np.float32)
    pa, ba = p - a, b - a
    h = np.clip(np.einsum('...i,i->...', pa, ba) / float(ba @ ba), 0.0, 1.0)
    return _len(pa - h[..., None] * ba) - (ra + (rb - ra) * h)


def rounded_box(p, c, half, r, axis_u=None):
    """Boîte arrondie orientée : axis_u est l'axe long (unitaire) de la boîte."""
    q = p - np.asarray(c, np.float32)
    if axis_u is not None:
        u = np.asarray(axis_u, np.float32)
        u = u / np.linalg.norm(u)
        tmp = np.array([0, 0, 1], np.float32) if abs(u[2]) < 0.9 else np.array([1, 0, 0], np.float32)
        v = np.cross(u, tmp); v /= np.linalg.norm(v)
        w = np.cross(u, v)
        q = np.stack([q @ u, q @ v, q @ w], axis=-1)
    d = np.abs(q) - (np.asarray(half, np.float32) - r)
    return _len(np.maximum(d, 0)) + np.minimum(d.max(axis=-1), 0) - r


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def ssub(a, b, k):
    """Soustraction douce : a moins b."""
    return -smin(-a, b, k) if k > 0 else np.maximum(a, -b)


# ---------------------------------------------------------------- squelettes de pose
# Trois intentions légères (positions d'articulations en mm). Pas de génération payante.
POSES = {
    'marteau_leve': {
        'label': 'Maillet levé, main gauche tendue — geste de création',
        'pelvis': (0, 0, 78), 'chest': (0, 2, 112), 'neck': (0, 3, 128), 'head': (0, 4, 143),
        'hip_l': (-11, 0, 76), 'knee_l': (-22, -10, 42), 'ankle_l': (-27, -14, 8),
        'hip_r': (11, 0, 76), 'knee_r': (20, 14, 40), 'ankle_r': (24, 22, 8),
        'sh_l': (-20, 2, 120), 'el_l': (-34, -16, 112), 'wr_l': (-38, -38, 118),
        'sh_r': (20, 2, 120), 'el_r': (34, 6, 142), 'wr_r': (26, 4, 166),
        'mallet': {'grip': (26, 4, 166), 'dir': (-0.35, 0.05, 0.94), 'handle': 34, 'head_at': 'end'},
        'scarf_dir': (0.35, 0.9, -0.2),
    },
    'garde_basse': {
        'label': 'Garde basse, maillet en diagonale à deux mains',
        'pelvis': (0, 0, 66), 'chest': (0, -3, 98), 'neck': (0, -5, 113), 'head': (0, -6, 128),
        'hip_l': (-12, 0, 64), 'knee_l': (-30, -14, 36), 'ankle_l': (-34, -10, 8),
        'hip_r': (12, 0, 64), 'knee_r': (28, 16, 34), 'ankle_r': (34, 18, 8),
        'sh_l': (-20, -3, 106), 'el_l': (-24, -22, 88), 'wr_l': (-8, -30, 84),
        'sh_r': (20, -3, 106), 'el_r': (22, -20, 86), 'wr_r': (8, -30, 80),
        'mallet': {'grip': (0, -30, 82), 'dir': (0.8, -0.1, 0.59), 'handle': 44, 'head_at': 'end'},
        'scarf_dir': (0.2, 0.95, -0.1),
    },
    'repos_fier': {
        'label': 'Repos fier, maillet posé au sol',
        'pelvis': (0, 0, 82), 'chest': (0, 0, 116), 'neck': (0, 0, 132), 'head': (0, 0, 147),
        'hip_l': (-11, 0, 80), 'knee_l': (-14, -2, 44), 'ankle_l': (-16, 0, 8),
        'hip_r': (11, 0, 80), 'knee_r': (14, -2, 44), 'ankle_r': (16, 0, 8),
        'sh_l': (-21, 0, 124), 'el_l': (-28, -4, 96), 'wr_l': (-24, -10, 74),
        'sh_r': (21, 0, 124), 'el_r': (30, -6, 98), 'wr_r': (34, -10, 74),
        'mallet': {'grip': (34, -10, 74), 'dir': (0.05, 0.0, -1.0), 'handle': 50, 'head_at': 'end'},
        'scarf_dir': (0.1, 0.8, -0.6),
    },
}


SENTINELLE_BOUNDS = ((-75.0, -75.0, -6.0), (75.0, 75.0, 235.0))


def characters():
    """Personnages originaux sculptables. « tight » : grille fine resserrée sur la figure (gain de
    calcul) ; la Sentinelle garde sa grille fixe pour rester identique aux preuves publiées. « voxel » et
    « smooth_iterations » : pas de grille et lissage par défaut (les détails d'Ardoise demandent 0,4 mm).
    « socle » : style de socle (fabrication.SOCLE_STYLES)."""
    from . import ardoise, veille
    return {
        'sentinelle': {'version': SCULPT_VERSION, 'poses': POSES, 'sdf': figure_sdf, 'bounds': SENTINELLE_BOUNDS,
                       'tight': False, 'intent_poses': {'combat': 'garde_basse', 'rest': 'repos_fier'},
                       'voxel': 0.6, 'smooth_iterations': 6, 'socle': 'lisse'},
        'ardoise': {'version': ardoise.ARDOISE_VERSION, 'poses': ardoise.POSES, 'sdf': ardoise.ardoise_sdf,
                    'bounds': ardoise.BOUNDS, 'tight': True, 'intent_poses': ardoise.INTENT_POSES,
                    'voxel': ardoise.DETAIL['voxel'], 'smooth_iterations': ardoise.DETAIL['smooth_iterations'],
                    'socle': ardoise.SOCLE},
        'veille': {'version': veille.VEILLE_VERSION, 'poses': veille.POSES, 'sdf': veille.veille_sdf,
                   'bounds': veille.BOUNDS, 'tight': True, 'intent_poses': veille.INTENT_POSES,
                   'voxel': veille.DETAIL['voxel'], 'smooth_iterations': veille.DETAIL['smooth_iterations'],
                   'socle': veille.SOCLE},
    }


def character(cid: str = 'sentinelle') -> dict:
    table = characters()
    if cid not in table:
        raise KeyError(f'Aucune sculpture procédurale pour « {cid} ».')
    return table[cid]


def pose_names(cid: str = 'sentinelle'):
    return list(character(cid)['poses'])


def _v(t):
    return np.asarray(t, np.float32)


def figure_sdf(p, pose: str):
    """SDF de la figurine seule (sans socle), en mm, semelles à z = 0."""
    P = POSES[pose]
    j = {k: _v(v) for k, v in P.items() if isinstance(v, tuple) and len(v) == 3}
    d = ellipsoid(p, (j['pelvis'] + j['chest']) / 2, (17, 12, 22))           # tronc
    d = smin(d, ellipsoid(p, j['chest'] + _v((0, 0, 4)), (21, 13, 13)), 6)   # cage thoracique
    d = smin(d, ellipsoid(p, j['pelvis'], (15, 11, 10)), 5)                   # bassin
    d = smin(d, limb(p, j['chest'], j['neck'], 7, 6), 4)                       # cou
    # casque arrondi + crête vers l'arrière + visière
    head = ellipsoid(p, j['head'], (11, 12, 12.5))
    crest = limb(p, j['head'] + _v((0, -4, 10)), j['head'] + _v((0, 14, 6)), 3.2, 2.2)
    head = smin(head, crest, 3)
    visor = rounded_box(p, j['head'] + _v((0, -10.5, 1)), (9, 2.2, 2.6), 1.2)
    head = smin(head, visor, 1.5)
    d = smin(d, head, 3)
    # plastron et ceinture : volumes lisibles à 30 cm
    d = smin(d, rounded_box(p, j['chest'] + _v((0, -7, 2)), (15, 5, 12), 4.0), 3)
    belt_c = j['pelvis'] + _v((0, 0, 9))
    d = smin(d, ellipsoid(p, belt_c, (18.5, 13.5, 4.2)), 1.5)
    d = smin(d, rounded_box(p, belt_c + _v((0, -13, 0)), (5, 2.2, 5), 1.2), 1)
    # épaulières
    for s in ('sh_l', 'sh_r'):
        d = smin(d, ellipsoid(p, j[s] + _v((0, 0, 2)), (9.5, 9, 7)), 3)
    # bras
    for side in ('l', 'r'):
        d = smin(d, limb(p, j['sh_' + side], j['el_' + side], 6.2, 5.0), 3)
        d = smin(d, limb(p, j['el_' + side], j['wr_' + side], 5.0, 4.0), 2.5)
        d = smin(d, limb(p, j['el_' + side] * 0.35 + j['wr_' + side] * 0.65, j['wr_' + side], 5.6, 5.4), 1.5)  # gantelet
        d = smin(d, sphere(p, j['wr_' + side], 6.0), 2)                        # poing / main
    # jambes et bottes
    for side in ('l', 'r'):
        d = smin(d, limb(p, j['hip_' + side], j['knee_' + side], 8.5, 6.5), 4)
        d = smin(d, limb(p, j['knee_' + side], j['ankle_' + side], 6.5, 5.5), 3)
        a = j['ankle_' + side]
        boot = smin(rounded_box(p, a + _v((0, -4, -3.5)), (8.5, 14, 5.5), 3.0), limb(p, a, a + _v((0, 0, 14)), 7.2, 7.0), 2.5)
        d = smin(d, boot, 3)
    # écharpe : bande épaisse qui flotte dans le dos (épaisseur ≥ 3 mm à 200 mm)
    sd = _v(P['scarf_dir']); sd = sd / np.linalg.norm(sd)
    root = j['neck'] + _v((0, 6, -2))
    tip = root + sd * 30
    scarf = rounded_box(p, (root + tip) / 2, (15.5, 9, 2.6), 1.6, axis_u=sd)
    d = smin(d, scarf, 3)
    # maillet de sculpteur
    m = P['mallet']
    grip = _v(m['grip']); md = _v(m['dir']); md = md / np.linalg.norm(md)
    end = grip + md * m['handle']
    start = grip - md * 8
    d = smin(d, limb(p, start, end, 2.8, 3.2), 1.5)
    mallet_head = rounded_box(p, end + md * 9, (10, 8.5, 8.5), 2.5, axis_u=md)
    d = smin(d, mallet_head, 1.5)
    # semelles planes à z = 0 : intersection avec le demi-espace z >= 0
    return np.maximum(d, -p[..., 2])


def evaluate_grid(fn, lo, hi, voxel, chunk_z=24):
    """Évalue la SDF sur une grille régulière, par tranches pour borner la mémoire."""
    lo = np.asarray(lo, np.float32); hi = np.asarray(hi, np.float32)
    n = np.ceil((hi - lo) / voxel).astype(int) + 1
    xs = lo[0] + np.arange(n[0], dtype=np.float32) * voxel
    ys = lo[1] + np.arange(n[1], dtype=np.float32) * voxel
    zs = lo[2] + np.arange(n[2], dtype=np.float32) * voxel
    out = np.empty((n[0], n[1], n[2]), np.float32)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    for z0 in range(0, n[2], chunk_z):
        zz = zs[z0:z0 + chunk_z]
        pts = np.empty((n[0], n[1], len(zz), 3), np.float32)
        pts[..., 0] = X[..., None]; pts[..., 1] = Y[..., None]; pts[..., 2] = zz[None, None, :]
        out[:, :, z0:z0 + chunk_z] = fn(pts)
    return out, lo, n


def figure_bounds(pose: str, cid: str = 'sentinelle', margin: float = 6.0):
    """Grille de calcul : fixe, ou resserrée sur la figure repérée à 2 mm (+ marge, plan z = -6)."""
    c = character(cid)
    lo, hi = c['bounds']
    if not c['tight']:
        return lo, hi
    field, origin, _ = evaluate_grid(lambda q: c['sdf'](q, pose), lo, hi, 2.0)
    idx = np.argwhere(field <= 0)
    if not len(idx):
        raise ValueError(f'Pose « {pose} » vide pour « {cid} ».')
    pts_lo = origin + idx.min(axis=0) * 2.0 - margin
    pts_hi = origin + idx.max(axis=0) * 2.0 + margin
    return ((float(max(pts_lo[0], lo[0])), float(max(pts_lo[1], lo[1])), lo[2]),
            (float(min(pts_hi[0], hi[0])), float(min(pts_hi[1], hi[1])), float(min(pts_hi[2], hi[2]))))


def grid_mb(lo, hi, voxel: float) -> float:
    n = [int((h - l) / voxel) + 3 for l, h in zip(lo, hi)]
    return n[0] * n[1] * n[2] * 4 / 1e6 + n[0] * n[1] * 24 * 12 / 1e6


def sculpt_figure(pose: str, voxel: float = 0.6, smooth_iterations: int | None = None, cid: str = 'sentinelle',
                  bounds=None):
    """Retourne un trimesh fermé de la figurine nominale (mm, semelles à z = 0)."""
    import trimesh
    from skimage import measure
    c = character(cid)
    sdf = c['sdf']
    if smooth_iterations is None:
        smooth_iterations = c['smooth_iterations']
    lo, hi = bounds or figure_bounds(pose, cid)
    field, origin, _ = evaluate_grid(lambda q: sdf(q, pose), lo, hi, voxel)
    # Les bords de la grille sont à l'extérieur (sauf le plan z=0 coupé) : on ferme le volume.
    field = np.pad(field, 1, constant_values=1.0)
    verts, faces, _n, _v2 = measure.marching_cubes(field, 0.0, spacing=(voxel, voxel, voxel), allow_degenerate=False)
    verts += origin - voxel
    mesh = trimesh.Trimesh(verts, faces[:, ::-1], process=True)
    mesh.fix_normals()
    if smooth_iterations:
        z0 = mesh.vertices[:, 2] < 0.25 * voxel
        flat = mesh.vertices[z0].copy()
        trimesh.smoothing.filter_taubin(mesh, lamb=0.5, nu=-0.53, iterations=smooth_iterations)
        mesh.vertices[z0] = flat  # garder les semelles planes pour le contact au socle
    parts = mesh.split(only_watertight=False)
    # Résidus numériques du marching cubes : volume < 1 mm³ et plus petits que deux voxels. Retirés et
    # comptés ; un vrai élément flottant (volume réel) reste et sera éliminatoire aux contrôles.
    residue = [q for q in parts if abs(q.volume) < 1.0 and float(q.extents.max()) < 2 * voxel]
    if residue and len(residue) < len(parts):
        kept = [q for q in parts if not any(q is r for r in residue)]
        mesh = kept[0] if len(kept) == 1 else trimesh.util.concatenate(kept)
    mesh.metadata['marching_cubes_residue_removed'] = len(residue) if len(residue) < len(parts) else 0
    return mesh, len(parts) - mesh.metadata['marching_cubes_residue_removed']


def pose_proxy_metrics(pose: str, voxel: float = 2.0, cid: str = 'sentinelle'):
    """Mesures bon marché pour choisir une pose avant la génération fine."""
    c = character(cid)
    (x0, y0, _z0), (x1, y1, z1) = c['bounds']
    field, origin, n = evaluate_grid(lambda q: c['sdf'](q, pose), (x0, y0, -2), (x1, y1, z1), voxel)
    inside = field <= 0
    vol = inside.sum() * voxel ** 3
    idx = np.argwhere(inside)
    pts = origin + idx * voxel
    com = pts.mean(axis=0)
    soles = pts[pts[:, 2] < 2.5]
    from scipy.spatial import ConvexHull, Delaunay
    hull = ConvexHull(soles[:, :2])
    tri = Delaunay(soles[:, :2][hull.vertices])
    com_inside_feet = bool(tri.find_simplex(com[:2]) >= 0)
    # Silhouette de face (plan xz) et de profil (plan yz) : remplissage de la boîte englobante.
    front = inside.any(axis=1); side = inside.any(axis=0)
    def fill(sil):
        ii = np.argwhere(sil)
        box = (np.ptp(ii[:, 0]) + 1) * (np.ptp(ii[:, 1]) + 1)
        return float(sil.sum() / box)
    # Négatif : une silhouette trop pleine (bloc) se lit mal ; trop vide = fragile.
    z_top = float(pts[:, 2].max())
    return {
        'pose': pose, 'label': c['poses'][pose]['label'], 'volume_cm3_nominal': round(vol / 1000, 1),
        'height_nominal_mm': round(z_top, 1),
        'center_of_mass_mm': [round(float(c), 1) for c in com],
        'com_inside_feet_hull': com_inside_feet,
        'front_silhouette_fill': round(fill(front), 3), 'side_silhouette_fill': round(fill(side), 3),
        'stance_width_mm': round(float(np.ptp(soles[:, 0])), 1),
    }


def choose_pose(metrics: list[dict]) -> tuple[str, list[str]]:
    """Règle documentée : éliminer l'instable, puis préférer la silhouette la plus ouverte
    de face (lisibilité du geste), sans dépasser 0,55 de remplissage (fragilité)."""
    notes = []
    stable = [m for m in metrics if m['com_inside_feet_hull']]
    for m in metrics:
        if not m['com_inside_feet_hull']:
            notes.append(f"{m['pose']} écartée : centre de masse hors appui des pieds.")
    if not stable:
        return metrics[0]['pose'], notes + ['Aucune pose stable sans socle ; le socle porte la stabilité.']
    ranked = sorted(stable, key=lambda m: (abs(m['front_silhouette_fill'] - 0.42), -m['height_nominal_mm']))
    notes.append(f"Retenue : {ranked[0]['pose']} (remplissage de face {ranked[0]['front_silhouette_fill']}, "
                 'cible 0,42 = geste lisible sans membres grêles). Critère artistique non validé par un tiers.')
    return ranked[0]['pose'], notes
