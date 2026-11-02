"""Contrôles géométriques calculés (pas d'appréciation visuelle ici).

Seuils = HYPOTHÈSES FDM buse 0,4 mm / PLA, fixés AVANT l'évaluation (voir THRESHOLDS).
"""
from __future__ import annotations

import numpy as np

CHECKS_VERSION = 'bojart.checks.v2'

THRESHOLDS = {
    'min_wall_mm': 0.8,            # 2 lignes d'extrusion de 0,4 mm
    'fragile_wall_mm': 1.2,        # sous ce seuil : détail fragile à signaler
    'max_fragile_fraction': 0.02,  # part des échantillons de surface sous le seuil fragile
    'max_thin_fraction': 0.002,    # part des échantillons sous l'épaisseur minimale (éliminatoire)
    'height_tolerance_rel': 0.01,
    'overhang_angle_deg': 45.0,
    'stability_margin_mm': 3.0,
    'source': 'hypothèse de simulation FDM 0,4 mm, à remplacer par un profil mesuré',
}


def _nonmanifold_edges(mesh):
    import trimesh
    edges = np.sort(mesh.edges, axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int((counts != 2).sum())


def wall_thickness(mesh, samples=2500, seed=11, batch=100):
    """Épaisseur locale : rayon lancé vers l'intérieur depuis des points de surface."""
    import trimesh
    pts, fidx = trimesh.sample.sample_surface(mesh, samples, seed=seed)
    normals = mesh.face_normals[fidx]
    origins = pts - normals * 1e-3
    thick = np.full(len(pts), np.inf)
    # Par paquets : sans Embree, trimesh alloue des candidats par rayon (pic mesuré à 4 Go
    # pour 1 500 rayons d'un coup sur 180 k triangles).
    for start in range(0, len(pts), batch):
        sl = slice(start, start + batch)
        locs, ray_idx, _ = mesh.ray.intersects_location(origins[sl], -normals[sl], multiple_hits=False)
        if len(ray_idx):
            thick[start + ray_idx] = np.linalg.norm(locs - origins[sl][ray_idx], axis=1)
    finite = thick[np.isfinite(thick)]
    return finite, int(len(pts) - len(finite)), pts[np.isfinite(thick)]


def check_part(mesh, name, *, expected_height_mm=None, thickness_samples=2500):
    t = THRESHOLDS
    res = {'part': name, 'measured': {}, 'eliminatory': [], 'warnings': []}
    m = res['measured']
    m['triangles'] = int(len(mesh.faces))
    m['watertight'] = bool(mesh.is_watertight)
    m['winding_consistent'] = bool(mesh.is_winding_consistent)
    m['nonmanifold_edges'] = _nonmanifold_edges(mesh)
    bodies = mesh.split(only_watertight=False)
    m['bodies'] = int(len(bodies))
    m['volume_cm3'] = round(float(mesh.volume) / 1000, 3) if mesh.is_watertight else None
    m['extents_mm'] = [round(float(x), 2) for x in mesh.extents]
    m['euler_number'] = int(mesh.euler_number)
    if not m['watertight']:
        res['eliminatory'].append('volume non fermé')
    if not m['winding_consistent']:
        res['eliminatory'].append('normales incohérentes')
    if m['nonmanifold_edges']:
        res['eliminatory'].append(f"{m['nonmanifold_edges']} arêtes non-manifold")
    if m['bodies'] > 1:
        res['eliminatory'].append(f"{m['bodies'] - 1} élément(s) flottant(s)")
    if m['watertight'] and mesh.volume <= 0:
        res['eliminatory'].append('volume négatif (normales inversées)')
    if expected_height_mm is not None:
        rel = abs(mesh.extents[2] - expected_height_mm) / expected_height_mm
        m['height_error_rel'] = round(float(rel), 5)
        if rel > t['height_tolerance_rel']:
            res['eliminatory'].append(f'hauteur {mesh.extents[2]:.1f} mm au lieu de {expected_height_mm} mm')
    if m['watertight']:
        th, misses, pts = wall_thickness(mesh, thickness_samples)
        m['thickness_samples'] = int(len(th)); m['thickness_ray_misses'] = misses
        if len(th):
            m['thickness_mm'] = {'min': round(float(th.min()), 3), 'p1': round(float(np.percentile(th, 1)), 3),
                                 'p5': round(float(np.percentile(th, 5)), 3), 'median': round(float(np.median(th)), 3)}
            thin = float((th < t['min_wall_mm']).mean()); fragile = float((th < t['fragile_wall_mm']).mean())
            m['thin_fraction'] = round(thin, 5); m['fragile_fraction'] = round(fragile, 5)
            if thin > t['max_thin_fraction']:
                z = pts[th < t['min_wall_mm']][:, 2]
                res['eliminatory'].append(f'{thin:.1%} de la surface sous {t["min_wall_mm"]} mm '
                                          f'(z {z.min():.0f}–{z.max():.0f} mm)')
            elif fragile > t['max_fragile_fraction']:
                res['warnings'].append(f'{fragile:.1%} de la surface sous {t["fragile_wall_mm"]} mm : détails fragiles')
    # Surplombs : faces orientées vers le bas au-delà de l'angle, hors plan d'appui.
    nz = mesh.face_normals[:, 2]
    lim = -np.cos(np.radians(t['overhang_angle_deg']))
    zc = mesh.triangles_center[:, 2]
    on_bed = zc < mesh.bounds[0][2] + 0.3
    area = mesh.area_faces
    over = (nz < lim) & ~on_bed
    m['overhang_area_fraction'] = round(float(area[over].sum() / area.sum()), 4)
    return res


def check_stability(figure, base, info):
    """Centre de masse de l'assemblage (densité uniforme) projeté dans le disque du socle."""
    vol_f, vol_b = float(figure.volume), float(base.volume)
    com = (figure.center_mass * vol_f + base.center_mass * vol_b) / (vol_f + vol_b)
    c = np.array(info['base_centre_xy_mm'])
    dist = float(np.linalg.norm(com[:2] - c))
    margin = info['base_radius_mm'] - dist
    ok = margin >= THRESHOLDS['stability_margin_mm']
    return {'assembly_com_mm': [round(float(x), 2) for x in com], 'com_offset_from_base_centre_mm': round(dist, 2),
            'margin_to_base_edge_mm': round(margin, 2), 'stable_static_estimate': bool(ok),
            'method': 'densité uniforme (remplissage réel non pris en compte) ; estimation statique, pas un essai'}


def check_fit(figure, base, info):
    """Tenons dans les logements : interférence nulle attendue avec le jeu d'hypothèse."""
    import manifold3d  # noqa: F401
    from .fabrication import to_manifold
    inter = to_manifold(figure) ^ to_manifold(base)
    vol = float(inter.volume())
    return {'interference_volume_mm3': round(vol, 4), 'fit_ok': vol < 1e-3,
            'clearance_per_side_mm': info['hole_clearance_per_side_mm'],
            'note': 'jeu numérique ; jeu réel à calibrer par une pièce test'}


def detail_vs_process(min_feature_mm, process='FDM', nozzle=0.4, layer=0.15):
    """Le procédé peut-il restituer le plus petit détail voulu à cette échelle ?"""
    xy = nozzle * 1.1 if process == 'FDM' else 0.05
    return {'process': process, 'xy_resolution_estimate_mm': round(xy, 3), 'layer_mm': layer,
            'smallest_intended_feature_mm': min_feature_mm,
            'reproducible': bool(min_feature_mm >= 2 * xy),
            'note': 'estimation géométrique, pas une mesure sur pièce'}
