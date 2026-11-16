"""Banc B5 : découper un personnage original mis à 1 000 mm en pièces imprimables, avec goujons et numéros.

Méthode (manifold3d) : bissections planes alignées sur les axes jusqu'à ce que chaque pièce tienne dans
le volume d'hypothèse ; à chaque coupe, trous de goujons percés de part et d'autre du plan avant la
séparation (ils sont donc coaxiaux par construction), numéro de joint gravé sur les deux faces, lisible
de chaque côté. Les pièces sont posées dans une orientation qui tient sur le plateau, exportées en STL,
relues, remises en place par la transformation inverse et comparées au modèle d'origine.

Usage : python -I b5_decoupe_1m.py --m08 <racine> --stl <figurine> --work <dossier> --out <json>
        [--height 1000] [--prusa CHEMIN]
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

BED = (250.0, 210.0, 220.0)          # volume d'hypothèse M08
FIT = (240.0, 200.0, 220.0)          # 5 mm de marge en X et Y pour la jupe
DOWELS = [  # (diamètre goujon, jeu radial du trou, profondeur par côté) : hypothèses à calibrer (N3)
    {'d': 8.0, 'clearance': 0.15, 'depth': 12.0},
    {'d': 4.0, 'clearance': 0.15, 'depth': 8.0},
]
WALL = 2.0                            # matière minimale autour d'un trou ou d'une gravure
ENGRAVE_DEPTH = 0.8
DIGIT_H, DIGIT_W, STROKE, GAP = 12.0, 7.0, 1.6, 2.0
FRAGMENT_CM3 = 1.0

SEGMENTS = {  # 7 segments : a b c d e f g
    '0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc',
    '5': 'afgcd', '6': 'afgedc', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg'}

# Matrices monde -> repère local dont l'axe z est l'axe de coupe (rotations, déterminant +1).
R_AXIS = {0: np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float),
          1: np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], float),
          2: np.eye(3)}


def mf():
    import manifold3d
    return manifold3d


def to_manifold(mesh):
    m = mf()
    return m.Manifold(m.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                             tri_verts=np.asarray(mesh.faces, np.uint32)))


def to_trimesh(man):
    import trimesh
    g = man.to_mesh()
    return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=False)


def affine(R, t=(0, 0, 0)):
    return np.hstack([R, np.asarray(t, float).reshape(3, 1)])


def fits(ext):
    return all(e <= b + 1e-6 for e, b in zip(sorted(ext), sorted(FIT)))


def extents(man):
    b = man.bounding_box()
    return [b[3] - b[0], b[4] - b[1], b[5] - b[2]]


def cross_section(man, axis, c):
    """Polygones shapely de la section au plan axe = c, en coordonnées locales (u, v)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    cs = man.transform(affine(R_AXIS[axis])).slice(c)
    polys = [Polygon(p) for p in cs.to_polygons() if len(p) >= 3]
    if not polys:
        return None
    # to_polygons rend contours extérieurs et trous mélangés : règle pair-impair.
    geom = None
    for p in polys:
        p = p.buffer(0)
        geom = p if geom is None else geom.symmetric_difference(p)
    return unary_union(geom) if geom is not None else None


def regions(geom):
    if geom is None or geom.is_empty:
        return []
    return list(geom.geoms) if hasattr(geom, 'geoms') else [geom]


def safe_region(region, man, axis, c, h):
    """Partie de la région présente dans toutes les sections entre c - h et c + h : un trou de cette
    profondeur n'y débouche pas sur la peau (contrôle ajouté après l'exécution v1, trous débouchants)."""
    safe = region
    for off in (-h, -h / 2, h / 2, h):
        g = cross_section(man, axis, c + off)
        if g is None or g.is_empty:
            return None
        safe = safe.intersection(g)
        if safe.is_empty:
            return None
    return safe


def plan_dowels(region, man, axis, c):
    """Positions des goujons dans une région de section : deux si possible, sinon un, sinon aucun."""
    for spec in DOWELS:
        r = spec['d'] / 2 + spec['clearance']
        safe = safe_region(region, man, axis, c, spec['depth'] + 0.5)
        if safe is None:
            continue
        inset = safe.buffer(-(r + WALL))
        if inset.is_empty:
            continue
        parts = regions(inset)
        big = max(parts, key=lambda g: g.area)
        pts = np.asarray(big.exterior.coords)[:-1]
        if len(pts) > 160:
            pts = pts[np.linspace(0, len(pts) - 1, 160).astype(int)]
        if len(pts) >= 2:
            d = np.linalg.norm(pts[:, None] - pts[None], axis=2)
            i, j = np.unravel_index(np.argmax(d), d.shape)
            if d[i, j] >= 2 * r + 10.0:
                return spec, [tuple(pts[i]), tuple(pts[j])]
        p = big.representative_point()
        return spec, [(p.x, p.y)]
    return None, []


def digit_shapes(text, mirror):
    """Rectangles shapely d'un numéro en 7 segments, centrés sur (0, 0)."""
    from shapely.geometry import box
    s, w, h = STROKE, DIGIT_W, DIGIT_H
    seg = {'a': (0, h - s, w, h), 'g': (0, h / 2 - s / 2, w, h / 2 + s / 2), 'd': (0, 0, w, s),
           'f': (0, h / 2, s, h), 'b': (w - s, h / 2, w, h), 'e': (0, 0, s, h / 2), 'c': (w - s, 0, w, h / 2)}
    total = len(text) * w + (len(text) - 1) * GAP
    out = []
    for k, ch in enumerate(text):
        x0 = k * (w + GAP) - total / 2
        for sname in SEGMENTS[ch]:
            a, b, c, d = seg[sname]
            r = (x0 + a, b - h / 2, x0 + c, d - h / 2)
            if mirror:
                r = (-r[2], r[1], -r[0], r[3])
            out.append(box(*r))
    return out, total


def place_label(region, holes_uv, r_hole, text):
    from shapely.geometry import Point, box
    _, width = digit_shapes(text, False)
    free = region.buffer(-WALL)
    for (x, y) in holes_uv:
        free = free.difference(Point(x, y).buffer(r_hole + WALL))
    if free.is_empty:
        return None
    minx, miny, maxx, maxy = free.bounds
    c = free.representative_point()
    cands = [(c.x, c.y)] + [(x, y) for x in np.linspace(minx, maxx, 12) for y in np.linspace(miny, maxy, 12)]
    cands.sort(key=lambda p: (p[0] - c.x) ** 2 + (p[1] - c.y) ** 2)
    for (x, y) in cands:
        if free.contains(box(x - width / 2, y - DIGIT_H / 2, x + width / 2, y + DIGIT_H / 2)):
            return (x, y)
    return None


def prism(shapes_uv, axis, c, z0, z1, at_uv):
    """Extrusion des formes (u, v) entre z0 et z1 (repère local), renvoyée en coordonnées monde."""
    m = mf()
    polys = [np.asarray(s.exterior.coords)[:-1] + np.asarray(at_uv) for s in shapes_uv]
    cs = m.CrossSection(polys)
    solid = cs.extrude(z1 - z0).translate((0, 0, z0))
    return solid.transform(affine(R_AXIS[axis].T))


def cylinder(axis, uv, c, radius, half_len):
    m = mf()
    cyl = m.Manifold.cylinder(2 * half_len, radius, radius, 48, True).translate((uv[0], uv[1], c))
    return cyl.transform(affine(R_AXIS[axis].T))


class Cutter:
    def __init__(self):
        self.joints = []
        self.dowel_solids = []

    def choose_cut(self, man):
        ext = extents(man)
        b = man.bounding_box()
        lo, hi = b[:3], b[3:]
        axis = int(np.argmax(ext))
        best = None
        for f in np.linspace(0.35, 0.65, 7):
            c = lo[axis] + f * ext[axis]
            geom = cross_section(man, axis, c)
            regs = regions(geom)
            if not regs:
                continue
            no_dowel = sum(plan_dowels(r, man, axis, c)[0] is None for r in regs)
            score = (no_dowel, sum(r.area for r in regs))
            if best is None or score < best[0]:
                best = (score, c, regs)
        return axis, best

    def cut(self, man):
        axis, best = self.choose_cut(man)
        if best is None:
            raise RuntimeError('aucune section exploitable')
        _, c, regs = best
        jid = len(self.joints) + 1
        text = str(jid)
        joint = {'joint': jid, 'axis': 'XYZ'[axis], 'plane_mm': round(float(c), 3), 'regions': []}
        holes = []
        for reg in regs:
            spec, pts = plan_dowels(reg, man, axis, c)
            info = {'area_mm2': round(reg.area, 1), 'dowels': [], 'label': None}
            if spec:
                r_hole = spec['d'] / 2 + spec['clearance']
                for (u, v) in pts:
                    holes.append(cylinder(axis, (u, v), c, r_hole, spec['depth'] + 0.5))
                    self.dowel_solids.append(cylinder(axis, (u, v), c, spec['d'] / 2, spec['depth'] - 0.5))
                    info['dowels'].append({'uv': [round(u, 2), round(v, 2)], 'd_mm': spec['d'],
                                           'hole_d_mm': round(2 * r_hole, 2),
                                           'depth_each_side_mm': spec['depth'] + 0.5,
                                           'dowel_length_mm': 2 * spec['depth'] - 1})
                lab_reg = safe_region(reg, man, axis, c, ENGRAVE_DEPTH + 0.2)
                lab = place_label(lab_reg, pts, r_hole, text) if lab_reg is not None else None
            else:
                lab_reg = safe_region(reg, man, axis, c, ENGRAVE_DEPTH + 0.2)
                lab = place_label(lab_reg, [], 0, text) if lab_reg is not None else None
                info['note'] = 'section trop étroite pour un goujon : collage seul'
            info['label'] = None if lab is None else [round(lab[0], 2), round(lab[1], 2)]
            if lab is None:
                info['label_note'] = 'pas de place pour graver le numéro : repère dans le manifeste seulement'
            info['_lab'] = lab
            joint['regions'].append(info)
        m = mf()
        if holes:
            man = man - m.Manifold.batch_boolean(holes, m.OpType.Add)
        normal = [0.0, 0.0, 0.0]; normal[axis] = 1.0
        first, second = man.split_by_plane(normal, float(c))
        # Côté positif = celui dont la boîte englobante est au-delà du plan (vérifié, pas supposé).
        def above(x):
            if x.is_empty():
                return False
            bb = x.bounding_box()
            return (bb[axis] + bb[axis + 3]) / 2 > c
        pos, neg = (first, second) if above(first) or (not second.is_empty() and not above(second)) else (second, first)
        # Gravures : côté négatif lu depuis +axe, côté positif lu depuis -axe (miroir en u).
        for info in joint['regions']:
            lab = info.pop('_lab')
            if lab is None:
                continue
            shapes_n, _ = digit_shapes(text, mirror=False)
            shapes_p, _ = digit_shapes(text, mirror=True)
            neg = neg - prism(shapes_n, axis, c, c - ENGRAVE_DEPTH, c + 0.01, lab)
            pos = pos - prism(shapes_p, axis, c, c - 0.01, c + ENGRAVE_DEPTH, lab)
        self.joints.append(joint)
        return [pos, neg]

    def run(self, man):
        todo, done = [man], []
        guard = 0
        while todo:
            guard += 1
            if guard > 500:
                raise RuntimeError('trop de coupes')
            piece = todo.pop()
            if piece.is_empty():
                continue
            if fits(extents(piece)):
                done.append(piece)
                continue
            for half in self.cut(piece):
                todo.extend([p for p in half.decompose() if not p.is_empty()])
        return done


def orient_on_bed(ext):
    """Permutation d'axes (rotation propre) qui fait tenir la pièce dans FIT."""
    for perm in itertools.permutations(range(3)):
        R = np.zeros((3, 3))
        for i, p in enumerate(perm):
            R[i, p] = 1.0
        if np.linalg.det(R) < 0:
            R[0] *= -1  # rend la permutation propre (miroir interdit)
        e = np.abs(R @ np.asarray(ext))
        if all(e[i] <= FIT[i] + 1e-6 for i in range(3)):
            return R
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--m08', required=True, type=Path)
    ap.add_argument('--stl', required=True, type=Path)
    ap.add_argument('--work', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--height', type=float, default=1000.0)
    ap.add_argument('--prusa', default=None)
    a = ap.parse_args()
    sys.path.insert(0, str(a.m08 / 'jarvis' / 'apps' / 'jarvis' / 'app'))
    from figurine import checks  # noqa: E402
    import trimesh

    t0 = time.perf_counter()
    a.work.mkdir(parents=True, exist_ok=True)
    src = trimesh.load(str(a.stl), force='mesh')
    k = a.height / src.extents[2]
    scaled = src.copy(); scaled.apply_scale(k)
    scaled.apply_translation(-scaled.bounds[0] * [0, 0, 1])
    orig = to_manifold(scaled)
    status = str(orig.status())
    cutter = Cutter()
    pieces = cutter.run(orig)
    t_cut = time.perf_counter() - t0

    parts, reassembled = [], []
    pieces.sort(key=lambda p: (-p.bounding_box()[2], p.bounding_box()[0], p.bounding_box()[1]))
    for i, p in enumerate(pieces, 1):
        ext = extents(p)
        mesh = to_trimesh(p)
        R = orient_on_bed(ext)
        row = {'part': i, 'triangles': int(p.num_tri()), 'volume_cm3': round(p.volume() / 1000, 2),
               'extents_assembly_mm': [round(x, 1) for x in ext], 'fragment': p.volume() / 1000 < FRAGMENT_CM3}
        if R is None:
            row['fits_bed'] = False
        else:
            row['fits_bed'] = True
            placed = mesh.copy(); placed.apply_transform(np.vstack([affine(R), [0, 0, 0, 1]]))
            shift = -placed.bounds[0] + np.array([(BED[0] - placed.extents[0]) / 2, (BED[1] - placed.extents[1]) / 2, 0])
            placed.apply_translation(shift)
            f = a.work / f'piece_{i:02d}.stl'
            placed.export(str(f))
            back = trimesh.load(str(f), force='mesh')
            row['stl_sha256'] = hashlib.sha256(f.read_bytes()).hexdigest()
            row['print_extents_mm'] = [round(x, 1) for x in back.extents]
            row['print_transform'] = {'rotation': R.astype(int).tolist(), 'then_translate_mm': [round(x, 4) for x in shift]}
            res = checks.check_part(back, f.name, thickness_samples=400)
            row['watertight'] = bool(back.is_watertight)
            row['m08_eliminatory'] = res['eliminatory']; row['m08_warnings'] = res['warnings']
            # remise en place virtuelle à partir du fichier relu
            inv = back.copy(); inv.apply_translation(-shift)
            inv.apply_transform(np.vstack([affine(R.T), [0, 0, 0, 1]]))
            reassembled.append(inv)
            # Parois fines : près d'un plan de coupe (biseau où la peau rejoint la coupe) ou ailleurs ?
            th, _, tp = checks.wall_thickness(inv, 400)
            thin = tp[th < checks.THRESHOLDS['min_wall_mm']]
            near = 0
            for q in thin:
                d = min(abs(q['XYZ'.index(j['axis'])] - j['plane_mm']) for j in cutter.joints)
                near += d <= 3.0
            row['thin_samples'] = {'n': int(len(th)), 'under_min_wall': int(len(thin)), 'within_3mm_of_a_cut': int(near)}
        parts.append(row)

    # Écart de remontage : points de la surface d'origine contre la surface remontée.
    union = trimesh.util.concatenate(reassembled)
    pts, _ = trimesh.sample.sample_surface(scaled, 3000, seed=7)
    _, dist, _ = trimesh.proximity.closest_point(union, pts)
    m = mf()
    dowels = m.Manifold.batch_boolean(cutter.dowel_solids, m.OpType.Add) if cutter.dowel_solids else None
    parts_union = m.Manifold.batch_boolean(pieces, m.OpType.Add)
    interference = float((parts_union ^ dowels).volume()) if dowels else 0.0
    v_parts = sum(p.volume() for p in pieces)

    prusa_cut = None
    if a.prusa:
        sc = a.work / 'figurine_1m.stl'; scaled.export(str(sc))
        outp = a.work / 'prusa_cut.stl'
        pr = subprocess.run([a.prusa, '--cut', '220', '--export-stl', '--output', str(outp), str(sc)],
                            capture_output=True, text=True, timeout=1800)
        prusa_cut = {'command': 'prusa-slicer --cut 220 --export-stl', 'returncode': pr.returncode,
                     'log_tail': (pr.stdout + pr.stderr)[-300:],
                     'outputs': sorted(x.name for x in a.work.glob('prusa_cut*'))}
        sc.unlink(missing_ok=True)

    joints_total = len(cutter.joints)
    dowel_count = sum(len(r['dowels']) for j in cutter.joints for r in j['regions'])
    no_dowel = sum(1 for j in cutter.joints for r in j['regions'] if not r['dowels'])
    no_label = sum(1 for j in cutter.joints for r in j['regions'] if r['label'] is None)
    max_gap = float(dist.max())
    summary = {
        'height_mm': a.height, 'scale_factor': round(float(k), 5),
        'assembly_extents_mm': [round(float(x), 1) for x in scaled.extents],
        'parts': len(parts), 'fragments_under_1cm3': sum(p['fragment'] for p in parts),
        'parts_out_of_volume': sum(not p['fits_bed'] for p in parts),
        'parts_not_watertight': sum(not p.get('watertight', False) for p in parts),
        'parts_with_m08_eliminatory': sum(bool(p.get('m08_eliminatory')) for p in parts),
        'joints': joints_total, 'joint_regions': sum(len(j['regions']) for j in cutter.joints),
        'dowels': dowel_count, 'regions_without_dowel': no_dowel, 'regions_without_label': no_label,
        'reassembly_gap_mm': {'max': round(max_gap, 5), 'p99': round(float(np.percentile(dist, 99)), 5),
                              'samples': len(pts)},
        'dowel_interference_mm3': round(interference, 4),
        'volume_cm3': {'original': round(orig.volume() / 1000, 1), 'parts_sum': round(v_parts / 1000, 1),
                       'removed_by_holes_and_engraving': round((orig.volume() - v_parts) / 1000, 2)},
        'seconds': {'cutting': round(t_cut, 1), 'total': round(time.perf_counter() - t0, 1)},
    }
    summary['pass'] = (summary['parts_out_of_volume'] == 0 and summary['parts_not_watertight'] == 0
                       and max_gap <= 0.1 and interference < 1e-3 and dowel_count > 0)
    summary['pass_rule'] = ('toutes les pièces étanches et dans le volume ; goujons et numéros présents ; '
                            'écart ≤ 0,1 mm (BANCS.json)')
    report = {
        'bench': 'B5-decoupe-1m', 'status': 'executed',
        'executed_on': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'input': {'file': a.stl.name, 'sha256': hashlib.sha256(a.stl.read_bytes()).hexdigest(),
                  'triangles': int(len(src.faces)), 'source_extents_mm': [round(float(x), 2) for x in src.extents],
                  'manifold_status': status},
        'environment': {'where': 'conteneur Linux de session, sans GPU (pas la tour)', 'python': platform.python_version(),
                        'trimesh': trimesh.__version__, 'm08_checks': checks.CHECKS_VERSION},
        'hypotheses': {'bed_mm': BED, 'fit_mm': FIT, 'dowels': DOWELS, 'wall_mm': WALL,
                       'engrave_depth_mm': ENGRAVE_DEPTH, 'digit_mm': [DIGIT_W, DIGIT_H, STROKE],
                       'note': 'jeux et profondeurs non mesurés : à calibrer sur un coupon imprimé (N3)'},
        'summary': summary, 'joints': cutter.joints, 'parts': parts, 'prusaslicer_cut_fallback': prusa_cut,
        'limits': ['pièces pleines : ni évidement ni trous de drainage étudiés ici',
                   'coupes planes alignées sur les axes, choisies par la plus petite section : pas de coupe cachée '
                   'dans le dessin du personnage',
                   'remontage virtuel ; aucun assemblage réel, aucune impression'],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=1).replace(str(a.work.resolve()), '<travail>')
    a.out.write_text(text.replace(str(a.work), '<travail>') + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
