"""Mise à l'échelle, socle détrompé, découpe multi-pièces et réparation surveillée.

Toutes les cotes d'assemblage sont des HYPOTHÈSES À CALIBRER (aucun profil machine vérifié).
"""
from __future__ import annotations

import numpy as np

FAB_VERSION = 'bojart.fabrication.v3'
# Styles de socle. « lisse » : cylindre chanfreiné de la v3, inchangé. « strates » : plaques d'ardoise
# empilées (2 novembre 2026, passe « détails » d'Ardoise). Un style autre que « lisse » ajoute sa
# version à celle de la fabrication dans l'identité de tâche : les tâches à socle lisse gardent leur
# identifiant et restent comparables aux preuves publiées.
SOCLE_STYLES = {'lisse': None, 'strates': 'bojart.socle.strates.v1'}


def fab_version(style: str = 'lisse') -> str:
    extra = SOCLE_STYLES[style]
    return FAB_VERSION if extra is None else f'{FAB_VERSION}+{extra}'

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


def _slate_outline(rng, theta, radius, amp, vertices):
    """Contour d'une plaque d'ardoise aux bords cassés, en rayon selon l'angle theta : polygone
    étoilé (sommets à angles et rayons tirés avec une graine fixe), arêtes droites entre sommets."""
    ang = (np.arange(vertices) + rng.uniform(-0.32, 0.32, vertices)) * (2 * np.pi / vertices)
    rad = radius + rng.uniform(-amp, amp, vertices)
    pts = np.stack([rad * np.cos(ang), rad * np.sin(ang)], axis=1)
    th = np.mod(theta - ang[0], 2 * np.pi) + ang[0]
    i = np.clip(np.searchsorted(np.append(ang, ang[0] + 2 * np.pi), th, side='right') - 1, 0, vertices - 1)
    a, e = pts[i], pts[(i + 1) % vertices] - pts[i]
    d = np.stack([np.cos(theta), np.sin(theta)], axis=1)
    # Intersection du rayon issu du centre avec l'arête : rho = (a × e) / (d × e).
    return (a[:, 0] * e[:, 1] - a[:, 1] * e[:, 0]) / (d[:, 0] * e[:, 1] - d[:, 1] * e[:, 0])


def _strata_base(centre, r, hb, ch, k, seed=23, n_theta=720):
    """Socle « en strates » : plaques d'ardoise empilées aux bords cassés, plus larges vers le bas,
    avec des stries de clivage en V. Même repère que le socle lisse : dessus plat à z = 0 (plan de
    joint des semelles), dessous à z = -hb.

    Imprimable retourné (dessus sur le plateau) sans support : chaque élargissement vers le bas est un
    chanfrein plus raide que 45° (pente 1,15), une plaque qui déborde de celle du dessous ne forme
    qu'une contre-dépouille tournée vers le haut à l'impression, et les stries ont des flancs à 42°.
    Le contour du dessus reste à r - ch/1,15 - amp au moins : la marge autour des pieds est gardée.
    Retourne (maillage trimesh fermé, informations)."""
    import trimesh
    rng = np.random.default_rng(seed)
    n = int(np.clip(round(hb / 3.6), 3, 6))
    h = rng.uniform(0.8, 1.25, n)
    h = hb * h / h.sum()
    if h[-1] < ch + 1.2:                                  # la plaque du dessus porte le chanfrein du bord
        h[:-1] *= (hb - ch - 1.2) / h[:-1].sum()
        h[-1] = ch + 1.2
    z = np.concatenate([[0.0], np.cumsum(h)])             # du dessous (0) au dessus (hb)
    theta = np.arange(n_theta) * (2 * np.pi / n_theta)
    step, amp, slope = 0.8 * k, 0.7 * k, 1.15
    R = [_slate_outline(rng, theta, r + step * (n - 1 - i), amp, 17 + i % 3) for i in range(n)]
    for i in range(n - 1):                                # chanfrein contenu dans 60 % de la plaque
        R[i + 1] = np.maximum(R[i + 1], R[i] - 0.6 * h[i] / slope)
    rings, grooves = [(np.zeros(n_theta), R[0])], 0
    for i in range(n):
        if i < n - 1:
            c = np.maximum(slope * (R[i] - R[i + 1]), 0.3)
            upper = (np.full(n_theta, z[i + 1]), R[i + 1])
        else:
            c = np.full(n_theta, ch)
            upper = (np.full(n_theta, hb), R[i] - ch / slope)
        band_top = z[i + 1] - c
        if float(band_top.min()) - z[i] >= 2.0:           # strie de clivage, profondeur variable autour du socle
            zg = z[i] + 0.55 * (float(band_top.min()) - z[i])
            g = 0.45 * k * np.clip(1.6 * np.sin(2 * theta + rng.uniform(0, 2 * np.pi)) + 0.4, 0, 1)
            rings += [(np.full(n_theta, zg - 0.5), R[i]), (np.full(n_theta, zg), R[i] - g), (np.full(n_theta, zg + 0.5), R[i])]
            grooves += 1
        rings += [(band_top, R[i]), upper]
    Z = np.stack([zz for zz, _ in rings]) - hb
    RR = np.stack([rr for _, rr in rings])
    m = len(rings)
    verts = np.concatenate([np.stack([centre[0] + RR * np.cos(theta), centre[1] + RR * np.sin(theta), Z], axis=-1).reshape(-1, 3),
                            [[centre[0], centre[1], -hb], [centre[0], centre[1], 0.0]]])
    idx = np.arange(m * n_theta).reshape(m, n_theta)
    nxt = np.roll(idx, -1, axis=1)
    a, b, c3, d = idx[:-1], nxt[:-1], nxt[1:], idx[1:]
    faces = np.concatenate([np.stack([a, b, c3], -1).reshape(-1, 3), np.stack([a, c3, d], -1).reshape(-1, 3),
                            np.stack([np.full(n_theta, m * n_theta), nxt[0], idx[0]], -1),
                            np.stack([np.full(n_theta, m * n_theta + 1), idx[-1], nxt[-1]], -1)])
    mesh = trimesh.Trimesh(verts, faces, process=True)
    info = {'strata': n, 'strata_heights_mm': [round(float(x), 2) for x in h], 'cleavage_grooves': grooves,
            'seed': seed, 'outline_jitter_mm': round(amp, 2), 'step_per_stratum_mm': round(step, 2),
            'top_outline_min_radius_mm': round(float((R[-1] - ch / slope).min()), 2),
            'bottom_outline_max_radius_mm': round(float(R[0].max()), 2),
            'chamfer_slope': f'{slope} (plus raide que 45° dans le sens d’impression)'}
    return mesh, info


def build_assembly(figure_nominal, total_height_mm: float, hyp=ASSEMBLY_HYPOTHESES, style: str = 'lisse'):
    """Retourne {'figurine': trimesh, 'socle': trimesh, 'info': dict} en mm, socle z ∈ [0, hb].

    style : « lisse » (cylindre chanfreiné) ou « strates » (plaques d'ardoise, voir _strata_base)."""
    if style not in SOCLE_STYLES:
        raise ValueError(f'Style de socle inconnu : {style}')
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
    strata = None
    if style == 'strates':
        slab, strata = _strata_base(centre, r, hb, ch, k)
        base = to_manifold(slab)
    else:
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
    if strata is not None:
        # Marges réelles du socle en strates : autour des pieds (dessus) et autour de l'évidement.
        foot = float(np.max(np.linalg.norm(soles - centre, axis=1)))
        strata['top_margin_beyond_feet_mm'] = round(strata['top_outline_min_radius_mm'] - foot, 2)
        if recess_h:
            # Paroi la plus mince autour de l'évidement : sommets du contour jusqu'à 1 mm au-dessus de
            # son plafond (borne prudente : les arêtes entre anneaux sont droites).
            v = slab.vertices
            rad = np.linalg.norm(v[:, :2] - centre, axis=1)
            low = (rad > 1.0) & (v[:, 2] <= -hb + recess_h + 1.0)
            strata['recess_radius_mm'] = round(r - hyp['base_wall_mm'] * k, 2)
            strata['recess_wall_min_mm'] = round(float(rad[low].min()) - (r - hyp['base_wall_mm'] * k), 2)
        info['base_style'] = {'style': style, 'version': SOCLE_STYLES[style], **strata}
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
