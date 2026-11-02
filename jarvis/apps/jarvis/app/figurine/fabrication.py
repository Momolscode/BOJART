"""Mise à l'échelle, socle détrompé, découpe multi-pièces et réparation surveillée.

Toutes les cotes d'assemblage sont des HYPOTHÈSES À CALIBRER (aucun profil machine vérifié).
"""
from __future__ import annotations

import numpy as np

FAB_VERSION = 'bojart.fabrication.v3'

# Hypothèses FDM 0,4 mm / PLA, à remplacer par un profil mesuré (pièce test d'ajustement).
ASSEMBLY_HYPOTHESES = {
    'clearance_per_side_mm': 0.20,
    'peg_diameters_mm': (4.0, 5.0),      # diamètres différents = détrompeur gauche/droite
    'peg_length_mm': 6.0,
    'hole_extra_depth_mm': 0.8,
    'base_height_ratio': 0.09,           # socle = 9 % de la hauteur totale (18 mm à 200 mm)
    'base_margin_mm': 10.0,
    'hollow_base': True,                 # évidement par dessous (boucle coût du 2026-11-02)
    'base_wall_mm': 3.0,
    'base_floor_above_holes_mm': 2.0,
    'status': 'hypothèse à calibrer par une pièce test, pas un réglage de production',
}


def to_manifold(mesh):
    import manifold3d as m3
    mm = m3.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                 tri_verts=np.asarray(mesh.faces, np.uint32))
    man = m3.Manifold(mm)
    if man.status() != m3.Error.NoError:
        raise ValueError(f'Maillage non manifold pour les booléens : {man.status()}')
    return man


def to_trimesh(man):
    import trimesh
    out = man.to_mesh()
    return trimesh.Trimesh(np.asarray(out.vert_properties)[:, :3], np.asarray(out.tri_verts), process=True)


def _feet_centres(mesh, sole_z=0.6):
    """Centres des deux plus grands appuis (les pieds) ; tous les appuis (pieds, pointe de lame…)
    dimensionnent le socle, mais les tenons ne vont que sous les pieds."""
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    v = mesh.vertices[mesh.vertices[:, 2] < mesh.bounds[0][2] + sole_z]
    if len(v) < 20:
        raise ValueError('Deux appuis de pieds distincts sont requis pour les tenons détrompés.')
    link_mm = max(2.5, 2.2 * float(np.median(mesh.edges_unique_length)))  # suit la résolution du maillage
    graph = cKDTree(v[:, :2]).sparse_distance_matrix(cKDTree(v[:, :2]), link_mm, output_type='coo_matrix')
    n, labels = connected_components(graph, directed=False)
    sizes = np.bincount(labels, minlength=n)
    feet = [v[labels == k] for k in np.argsort(-sizes)[:2] if sizes[k] >= 10]
    if len(feet) < 2:
        raise ValueError('Deux appuis de pieds distincts sont requis pour les tenons détrompés.')
    left, right = sorted(feet, key=lambda f: f[:, 0].mean())
    return left[:, :2].mean(axis=0), right[:, :2].mean(axis=0), v[:, :2]


def build_assembly(figure_nominal, total_height_mm: float, hyp=ASSEMBLY_HYPOTHESES):
    """Retourne {'figurine': trimesh, 'socle': trimesh, 'info': dict} en mm, socle z ∈ [0, hb]."""
    import manifold3d as m3
    fig = figure_nominal.copy()
    hb = round(total_height_mm * hyp['base_height_ratio'], 3)
    scale = (total_height_mm - hb) / float(fig.extents[2])
    fig.apply_translation([0, 0, -fig.bounds[0][2]])
    fig.apply_scale(scale)
    cl, cr, soles = _feet_centres(fig)
    # Tenons : les pieds sont à z=0 ; tenons sous les semelles, dans le socle.
    k = max(1.0, total_height_mm / 200.0)  # proportionnels au-delà de 200 mm
    d_l, d_r = (d * k for d in hyp['peg_diameters_mm'])
    L = hyp['peg_length_mm'] * k
    if L >= hb - 2:
        raise ValueError('Socle trop mince pour la longueur de tenon.')
    seg = 48
    man = to_manifold(fig)
    pegs = (m3.Manifold.cylinder(L + 0.5, d_l / 2, d_l / 2, seg).translate([cl[0], cl[1], -L])
            + m3.Manifold.cylinder(L + 0.5, d_r / 2, d_r / 2, seg).translate([cr[0], cr[1], -L]))
    fig_man = man + pegs
    # Socle : cylindre chanfreiné, centré sous l'empreinte des pieds.
    centre = (soles.min(axis=0) + soles.max(axis=0)) / 2
    r = float(np.max(np.linalg.norm(soles - centre, axis=1))) + hyp['base_margin_mm'] * k
    ch = min(1.5 * k, hb / 4)
    base = (m3.Manifold.cylinder(hb - ch, r, r, 128).translate([centre[0], centre[1], -hb])
            + m3.Manifold.cylinder(ch, r, r - ch, 128).translate([centre[0], centre[1], -ch]))
    c = hyp['clearance_per_side_mm']
    depth = L + hyp['hole_extra_depth_mm']
    holes = (m3.Manifold.cylinder(depth + 0.1, d_l / 2 + c, d_l / 2 + c, seg).translate([cl[0], cl[1], -depth])
             + m3.Manifold.cylinder(depth + 0.1, d_r / 2 + c, d_r / 2 + c, seg).translate([cr[0], cr[1], -depth]))
    base = base - holes
    recess_h = 0.0
    if hyp.get('hollow_base'):
        wall = hyp['base_wall_mm'] * k
        recess_h = hb - depth - hyp['base_floor_above_holes_mm'] * k
        if recess_h > 2.0:
            recess = m3.Manifold.cylinder(recess_h + 0.01, r - wall, r - wall, 128).translate([centre[0], centre[1], -hb - 0.01])
            base = base - recess
        else:
            recess_h = 0.0
    figure_mesh = to_trimesh(fig_man); figure_mesh.apply_translation([0, 0, hb])
    base_mesh = to_trimesh(base); base_mesh.apply_translation([0, 0, hb])
    info = {
        'scale_from_nominal': round(scale, 5), 'base_height_mm': hb, 'base_radius_mm': round(r, 2),
        'base_centre_xy_mm': [round(float(x), 2) for x in centre],
        'pegs': [{'side': 'gauche', 'diameter_mm': round(d_l, 3), 'xy': [round(float(x), 2) for x in cl]},
                 {'side': 'droite', 'diameter_mm': round(d_r, 3), 'xy': [round(float(x), 2) for x in cr]}],
        'peg_length_mm': round(L, 3), 'hole_clearance_per_side_mm': c,
        'keying': 'diamètres différents : impossible d’inverser les pieds',
        'joint_plane': 'semelles / dessus du socle (joint masqué par le contact des bottes)',
        'base_recess_height_mm': round(recess_h, 3),
        'base_print_orientation': 'retourné (dessus sur le plateau) : évidement sans pont ni support' if recess_h else 'à plat',
        'hypotheses': hyp['status'],
    }
    return {'figurine': figure_mesh, 'socle': base_mesh, 'info': info}


def _fits(extents, bed):
    return all(e <= b + 1e-6 for e, b in zip(sorted(extents), sorted(bed)))


def plan_cuts(mesh, bed_mm, max_parts=64):
    """Découpe récursive par plans au milieu de l'axe le plus long jusqu'à tenir dans `bed_mm`.
    Étude de répartition seulement : clés d'assemblage des coupes à concevoir ensuite."""
    import trimesh  # noqa: F401
    pending = [(to_manifold(mesh), 'P')]
    done, cuts = [], []
    while pending:
        man, name = pending.pop()
        bb = man.bounding_box()
        lo, hi = np.array(bb[:3]), np.array(bb[3:])
        ext = hi - lo
        if _fits(ext, bed_mm):
            done.append((name, man)); continue
        if len(done) + len(pending) + 2 > max_parts:
            raise ValueError('Découpe : nombre maximal de pièces dépassé.')
        axis = int(np.argmax(ext))
        normal = [0.0, 0.0, 0.0]; normal[axis] = 1.0
        offset = float((lo[axis] + hi[axis]) / 2)
        upper, lower = man.split_by_plane(normal, offset)
        origin = [0.0, 0.0, 0.0]; origin[axis] = offset
        section = to_trimesh(man).section(plane_origin=origin, plane_normal=normal)
        area = float(section.to_2D()[0].area) if section is not None else 0.0
        cuts.append({'piece': name, 'axis': 'xyz'[axis], 'at_mm': round(offset, 2), 'section_area_mm2': round(area, 1)})
        for suffix, part in (('a', lower), ('b', upper)):
            if not part.is_empty():
                pending.append((part, name + suffix))
    pieces = []
    for name, man in sorted(done, key=lambda t: t[0]):
        bb = man.bounding_box(); ext = np.array(bb[3:]) - np.array(bb[:3])
        pieces.append({'name': name, 'extents_mm': [round(float(e), 1) for e in ext],
                       'volume_cm3': round(man.volume() / 1000, 1), 'bodies': len(man.decompose())})
    return {'bed_mm': list(bed_mm), 'pieces': pieces, 'cuts': cuts}


def guarded_repair(mesh, max_deviation_mm=0.3, samples=4000, seed=7):
    """Répare (normales, faces dégénérées, trous) puis compare à l'original.
    Refuse la réparation si elle déplace la surface au-delà du seuil (fidélité)."""
    import trimesh
    before = {'watertight': bool(mesh.is_watertight), 'winding': bool(mesh.is_winding_consistent)}
    fixed = mesh.copy()
    fixed.update_faces(fixed.nondegenerate_faces())
    fixed.merge_vertices()
    trimesh.repair.fix_winding(fixed)
    trimesh.repair.fix_inversion(fixed)
    trimesh.repair.fill_holes(fixed)
    fixed.fix_normals()
    pts, _ = trimesh.sample.sample_surface(mesh, samples, seed=seed)
    _, dist, _ = trimesh.proximity.closest_point(fixed, pts)
    dev = float(np.max(dist)) if len(dist) else 0.0
    after = {'watertight': bool(fixed.is_watertight), 'winding': bool(fixed.is_winding_consistent)}
    accepted = after['watertight'] and dev <= max_deviation_mm
    return {'accepted': accepted, 'before': before, 'after': after,
            'max_surface_deviation_mm': round(dev, 4), 'threshold_mm': max_deviation_mm,
            'mesh': fixed if accepted else mesh,
            'reason': None if accepted else ('toujours ouvert après réparation' if not after['watertight']
                                             else 'réparation trop destructive pour la fidélité')}
