"""Banc B3 : 12 fichiers piégés passés aux contrôles de la chaîne M08 puis à une porte d'import proposée.

Les classes attendues sont écrites AVANT l'exécution (EXPECTED). Le banc mesure :
  1. « M08 seul » : chargement trimesh + checks.check_part de la PR #15, tels quels ;
  2. « porte proposée » : contrôle d'octets, unités, volume machine, coques, puis check_part ;
  3. un second avis `--info` de chaque trancheur fourni.
Aucun fichier n'est envoyé à une machine. Les fichiers générés restent hors du dépôt (empreintes seules).

Usage : python -I b3_q12.py --m08 <racine contenant jarvis/apps/jarvis/app> --work <dossier> --out <json>
        [--slicer NOM=CHEMIN ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

BED_MM = (250.0, 210.0, 220.0)  # volume d'hypothèse de la chaîne M08 (slicing.SIM_BED_MM)
MIN_PLAUSIBLE_MM = 5.0           # sous cette plus grande dimension, l'échelle est suspecte

# Classes, de la plus grave à la moins grave.
CLASSES = ['ILLISIBLE', 'A_REPRENDRE', 'A_REPARER', 'A_DECOUPER', 'A_CONFIRMER', 'PRET']

EXPECTED = {
    'q01_cube_20mm': ('PRET', 'cube fermé de 20 mm'),
    'q02_cube_pouces': ('A_CONFIRMER', 'échelle : pouces probables (×25,4 → 20 mm)'),
    'q03_cube_metres': ('A_CONFIRMER', 'échelle : mètres probables (×1000 → 20 mm)'),
    'q04_face_retiree': ('A_REPARER', 'trou : bords libres'),
    'q05_normales_inversees': ('A_REPARER', 'normales inversées'),
    'q06_cubes_chevauchants': ('A_REPARER', 'corps qui se chevauchent : union à faire'),
    'q07_paroi_0_3mm': ('A_REPRENDRE', 'paroi sous 0,8 mm'),
    'q08_piece_400mm': ('A_DECOUPER', 'hors du volume machine'),
    'q09_arete_non_variete': ('A_REPRENDRE', 'arête partagée par plus de deux faces'),
    'q10_faces_dupliquees_degenerees': ('A_REPARER', 'faces dupliquées et dégénérées'),
    'q11_stl_tronque': ('ILLISIBLE', 'STL binaire tronqué'),
    'q12_cavite_fermee': ('A_CONFIRMER', 'cavité fermée : drainage en résine'),
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- génération des pièges
def build_files(work: Path) -> dict:
    import trimesh
    import manifold3d as mf

    def box(ext, at=(0, 0, 0)):
        m = trimesh.creation.box(extents=ext)
        m.apply_translation(np.array(at, float) + np.array(ext, float) / 2)
        return m

    def to_mf(m):
        return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                                   tri_verts=np.asarray(m.faces, np.uint32)))

    def from_mf(man):
        g = man.to_mesh()
        return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=False)

    def raw_export(m, path):  # sans retraitement : on veut écrire le défaut tel quel
        path.write_bytes(trimesh.exchange.stl.export_stl(m))

    work.mkdir(parents=True, exist_ok=True)
    out = {}
    cube = box((20, 20, 20))
    out['q01_cube_20mm'] = cube.copy()
    out['q02_cube_pouces'] = cube.copy().apply_scale(1 / 25.4)
    out['q03_cube_metres'] = cube.copy().apply_scale(1 / 1000)
    top = np.where(cube.face_normals[:, 2] > 0.99)[0]
    out['q04_face_retiree'] = trimesh.Trimesh(cube.vertices, np.delete(cube.faces, top, axis=0), process=False)
    inv = cube.copy(); inv.invert()
    out['q05_normales_inversees'] = inv
    out['q06_cubes_chevauchants'] = trimesh.util.concatenate([cube.copy(), box((20, 20, 20), (10, 5, 0))])
    out['q07_paroi_0_3mm'] = from_mf(to_mf(box((20, 10, 2))) + to_mf(box((20, 0.3, 15), (0, 4.85, 2))))
    out['q08_piece_400mm'] = box((40, 40, 400))
    out['q09_arete_non_variete'] = trimesh.util.concatenate([cube.copy(), box((20, 20, 20), (20, 20, 0))])
    dup = cube.copy()
    e0, e1 = (int(i) for i in dup.faces[0][:2])
    v = np.vstack([dup.vertices, (dup.vertices[e0] + dup.vertices[e1]) / 2])   # milieu d'une arête existante
    f = np.vstack([dup.faces, dup.faces[:2],                       # deux faces en double
                   [[e0, len(v) - 1, e1]]])                        # triangle plat (aire nulle)
    out['q10_faces_dupliquees_degenerees'] = trimesh.Trimesh(v, f, process=False)
    out['q11_stl_tronque'] = trimesh.creation.icosphere(subdivisions=3, radius=10).apply_translation((0, 0, 10))
    out['q12_cavite_fermee'] = from_mf(to_mf(cube) - to_mf(box((10, 10, 10), (5, 5, 5))))

    files = {}
    for name, mesh in out.items():
        p = work / f'{name}.stl'
        raw_export(mesh, p)
        if name == 'q11_stl_tronque':
            data = p.read_bytes(); p.write_bytes(data[: int(len(data) * 0.6)])
        files[name] = p
    return files


# ---------------------------------------------------------------- M08 seul
def m08_alone(path: Path, checks) -> dict:
    import trimesh
    t0 = time.perf_counter()
    try:
        mesh = trimesh.load(str(path), force='mesh')
    except Exception as exc:  # noqa: BLE001 - on consigne le comportement réel
        return {'loaded': False, 'error': f'{type(exc).__name__}: {exc}'[:300], 'ready': False,
                'seconds': round(time.perf_counter() - t0, 3)}
    res = checks.check_part(mesh, path.stem, thickness_samples=1500)
    return {'loaded': True, 'triangles_loaded': int(len(mesh.faces)), 'ready': not res['eliminatory'],
            'eliminatory': res['eliminatory'], 'warnings': res['warnings'],
            'seconds': round(time.perf_counter() - t0, 3)}


# ---------------------------------------------------------------- porte d'import proposée
def stl_bytes_check(raw: bytes):
    """Un STL binaire doit faire exactement 84 + 50 n octets."""
    if len(raw) < 84:
        return f'{len(raw)} octets : trop court pour un STL'
    head = raw[:5].lower() == b'solid'
    n = struct.unpack('<I', raw[80:84])[0]
    if len(raw) == 84 + 50 * n:
        return None
    if head and b'endsolid' in raw[-512:].lower():
        return None  # STL ASCII complet
    return f'STL binaire annonçant {n} faces : {len(raw)} octets au lieu de {84 + 50 * n}'


def edge_counts(faces):
    e = np.sort(np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, c = np.unique(e, axis=0, return_counts=True)
    return int((c == 1).sum()), int((c > 2).sum())


def fits_bed(ext):
    xy = sorted(ext[:2], reverse=True)
    bed = sorted(BED_MM[:2], reverse=True)
    return xy[0] <= bed[0] and xy[1] <= bed[1] and ext[2] <= BED_MM[2]


def proposed_gate(path: Path, checks) -> dict:
    import trimesh
    import manifold3d as mf
    t0 = time.perf_counter()
    reasons = []  # (classe, motif)

    def done(extra=None):
        cls = min((c for c, _ in reasons), key=CLASSES.index) if reasons else 'PRET'
        out = {'class': cls, 'reasons': [f'{c} : {m}' for c, m in reasons],
               'seconds': round(time.perf_counter() - t0, 3)}
        out.update(extra or {})
        return out

    raw = path.read_bytes()
    bad = stl_bytes_check(raw)
    if bad:
        reasons.append(('ILLISIBLE', bad))
        return done()
    try:
        mesh = trimesh.load(str(path), force='mesh', process=False)
    except Exception as exc:  # noqa: BLE001
        reasons.append(('ILLISIBLE', f'chargement : {type(exc).__name__}'))
        return done()

    m = mesh.copy(); m.merge_vertices()
    tri = m.triangles
    area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) / 2
    degenerate = int((area < 1e-9).sum())
    key = np.sort(m.faces, axis=1)
    _, first, cnt = np.unique(key, axis=0, return_index=True, return_counts=True)
    duplicates = int((cnt - 1).sum())
    if degenerate or duplicates:
        reasons.append(('A_REPARER', f'{duplicates} face(s) dupliquée(s), {degenerate} dégénérée(s) : nettoyage avec accord'))
    keep = np.zeros(len(m.faces), bool); keep[first] = True; keep &= area >= 1e-9
    clean = trimesh.Trimesh(m.vertices, m.faces[keep], process=False)
    clean.remove_unreferenced_vertices()

    boundary, nonmanifold = edge_counts(clean.faces)
    if boundary:
        reasons.append(('A_REPARER', f'{boundary} bord(s) libre(s) : trou à boucher avec accord'))
    if nonmanifold:
        reasons.append(('A_REPRENDRE', f'{nonmanifold} arête(s) partagée(s) par plus de deux faces : jonction à épaissir ou séparer'))

    ext = [float(x) for x in clean.extents]
    info = {'extents': [round(x, 4) for x in ext]}
    scale_ok = max(ext) >= MIN_PLAUSIBLE_MM
    if not scale_ok:
        guesses = []
        for label, k in (('pouces', 25.4), ('mètres', 1000.0)):
            e = [x * k for x in ext]
            if max(e) >= MIN_PLAUSIBLE_MM and fits_bed(e):
                guesses.append(f'{label} (×{k:g} → {max(e):.1f} mm)')
        reasons.append(('A_CONFIRMER', 'échelle suspecte (plus grande dimension '
                        f'{max(ext):.3g}) ; unités candidates : {", ".join(guesses) or "aucune"} ; '
                        'épaisseurs non évaluées avant confirmation'))
    elif not fits_bed(ext):
        reasons.append(('A_DECOUPER', f'{ext[0]:.0f}×{ext[1]:.0f}×{ext[2]:.0f} mm hors du volume '
                        f'{BED_MM[0]:g}×{BED_MM[1]:g}×{BED_MM[2]:g} mm (rotation en Z comprise) : découpe B5'))

    if not boundary and not nonmanifold and clean.is_winding_consistent:
        bodies = clean.split(only_watertight=False)
        vols = [float(b.volume) for b in bodies]
        if len(bodies) == 1 and vols[0] < 0:
            reasons.append(('A_REPARER', 'normales inversées (volume négatif) : retournement avec accord'))
        positive = [b for b, v in zip(bodies, vols) if v > 0]
        negative = [b for b, v in zip(bodies, vols) if v < 0]
        if positive and negative and len(bodies) > 1:
            inside = all(any(p.contains([n.vertices[0]])[0] for p in positive) for n in negative)
            if inside:
                reasons.append(('A_CONFIRMER', f'{len(negative)} cavité(s) fermée(s) : sans effet en FDM, '
                                'trous de drainage obligatoires en résine'))
        if len(positive) > 1:
            mans = [mf.Manifold(mf.Mesh(vert_properties=np.asarray(b.vertices, np.float32),
                                        tri_verts=np.asarray(b.faces, np.uint32))) for b in positive]
            union = mans[0]
            for x in mans[1:]:
                union = union + x
            total = sum(float(b.volume) for b in positive)
            if union.volume() < total - 1e-3 * max(total, 1):
                reasons.append(('A_REPARER', f'{len(positive)} corps qui se chevauchent '
                                f'({total - union.volume():.1f} mm³ en commun) : union avec accord'))
            elif union.volume() >= total - 1e-6:
                reasons.append(('A_CONFIRMER', f'{len(positive)} pièces disjointes : voulu ?'))

    gate_ready_for_m08 = not any(c in ('ILLISIBLE', 'A_REPARER', 'A_REPRENDRE') for c, _ in reasons) and scale_ok
    if gate_ready_for_m08:
        res = checks.check_part(clean, path.stem, thickness_samples=1500)
        info['m08_eliminatory'] = res['eliminatory']; info['m08_warnings'] = res['warnings']
        for e in res['eliminatory']:
            if 'sous' in e and 'mm' in e:
                reasons.append(('A_REPRENDRE', f'paroi : {e}'))
            elif 'flottant' in e and any(c == 'A_CONFIRMER' and ('cavité' in r or 'disjointes' in r)
                                           for c, r in reasons):
                continue  # déjà expliqué : cavité ou pièces séparées, pas un élément flottant
            elif 'flottant' in e and any('chevauchent' in r for _, r in reasons):
                continue
            else:
                reasons.append(('A_REPARER', f'M08 : {e}'))
    return done(info)


# ---------------------------------------------------------------- second avis des trancheurs
def slicer_info(exe: str, path: Path, cwd: Path) -> dict:
    t0 = time.perf_counter()
    try:
        p = subprocess.run([exe, '--info', str(path)], capture_output=True, text=True, timeout=180, cwd=cwd)
    except subprocess.TimeoutExpired:
        return {'status': 'TIMEOUT'}
    txt = (p.stdout or '') + '\n' + (p.stderr or '')
    kv = dict(re.findall(r'^(\w+) = +(.+)$', txt, re.M))
    out = {'returncode': p.returncode, 'seconds': round(time.perf_counter() - t0, 2)}
    for k in ('size_x', 'size_y', 'size_z', 'number_of_facets', 'manifold', 'number_of_parts', 'volume',
              'open_edges', 'facets_removed', 'facets_reversed', 'backwards_edges', 'degenerate_facets',
              'edges_fixed', 'facets_added'):
        if k in kv:
            out[k] = kv[k].strip()
    errs = [l.strip() for l in txt.splitlines() if re.search(r'error|fail|cannot|invalid|warning', l, re.I)]
    if errs:
        out['messages'] = errs[:4]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--m08', required=True, type=Path)
    ap.add_argument('--work', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--slicer', action='append', default=[], help='NOM=CHEMIN')
    a = ap.parse_args()
    sys.path.insert(0, str(a.m08 / 'jarvis' / 'apps' / 'jarvis' / 'app'))
    from figurine import checks  # noqa: E402
    import trimesh
    import manifold3d

    files = build_files(a.work)
    slicers = dict(s.split('=', 1) for s in a.slicer)
    rows = []
    for name, path in files.items():
        exp_cls, exp_why = EXPECTED[name]
        alone = m08_alone(path, checks)
        gate = proposed_gate(path, checks)
        row = {'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha256(path),
               'expected': {'class': exp_cls, 'why': exp_why},
               'm08_alone': alone,
               'm08_alone_verdict_ok': (alone['ready'] == (exp_cls == 'PRET')),
               'proposed_gate': gate,
               'proposed_gate_ok': gate['class'] == exp_cls,
               'slicers_info': {k: slicer_info(v, path, a.work) for k, v in slicers.items()}}
        rows.append(row)

    # La chaîne M08 complète tranche après les contrôles : le trancheur arrête-t-il la pièce de 400 mm ?
    probe = {}
    ref = slicers.get('prusaslicer_2_7_2')
    if ref:
        from figurine import slicing
        d = a.work / 'tranchage_q08'; d.mkdir(exist_ok=True)
        r = slicing.slice_part(files['q08_piece_400mm'], d, exe=ref, timeout=300)
        probe['q08_m08_slicing_stage'] = {'status': r['status'], 'returncode': r.get('returncode'),
                                          'log_tail': (r.get('log_tail') or '')[-200:]}

    def false_ready(key, ready):
        return [r['file'] for r in rows if ready(r[key]) and r['expected']['class'] != 'PRET']

    summary = {
        'm08_alone': {
            'ready_verdict_correct': sum(r['m08_alone_verdict_ok'] for r in rows),
            'false_ready': false_ready('m08_alone', lambda x: x['ready']),
            'note': 'M08 ne connaît que « prêt » / « non prêt » : on juge le verdict, pas la classe.',
        },
        'proposed_gate': {
            'class_correct': sum(r['proposed_gate_ok'] for r in rows),
            'false_ready': false_ready('proposed_gate', lambda x: x['class'] == 'PRET'),
        },
        'slicers_manifold_no': {k: [r['file'] for r in rows if r['slicers_info'][k].get('manifold') == 'no']
                                for k in slicers},
        'pass_rule': '12/12 bien classés, 0 déclaré prêt à tort (BANCS.json)',
    }
    summary['proposed_gate']['pass'] = (summary['proposed_gate']['class_correct'] == len(rows)
                                        and not summary['proposed_gate']['false_ready'])
    report = {
        'bench': 'B3-controles-q12', 'status': 'executed',
        'executed_on': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'environment': {'where': 'conteneur Linux de session, sans GPU (pas la tour)',
                        'python': platform.python_version(), 'trimesh': trimesh.__version__,
                        'manifold3d': getattr(manifold3d, '__version__', 'non exposé (épinglé 3.5.4)'),
                        'm08_checks': checks.CHECKS_VERSION, 'bed_hypothesis_mm': BED_MM},
        'classes': CLASSES, 'summary': summary, 'chain_probe': probe, 'files': rows,
        'limits': ['fichiers synthétiques simples : un vrai scan ou une sortie IA cumule plusieurs défauts',
                   'la porte proposée est écrite pour ce banc, pas intégrée à la chaîne M08',
                   'classes attendues fixées avant exécution dans EXPECTED'],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=1).replace(str(a.work.resolve()), '<travail>')
    a.out.write_text(text.replace(str(a.work), '<travail>') + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
