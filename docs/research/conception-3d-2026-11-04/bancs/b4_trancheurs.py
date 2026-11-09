"""Banc B4 : PrusaSlicer 2.7.2 (référence M08) contre PrusaSlicer 2.9.7 et OrcaSlicer 2.4.2.

Même profil d'hypothèse que la chaîne M08 (slicing.PROFILE). PrusaSlicer le lit tel quel ;
OrcaSlicer reçoit sa traduction JSON, avec les vitesses, accélérations et limites machine
de PrusaSlicer écrites en clair (sinon Orca applique ses propres valeurs par défaut).
Chaque G-code est relu par un relecteur à liste blanche. Rien n'est envoyé à une machine.

Usage : python -I b4_trancheurs.py --m08 <racine> --work <dossier> --out <json>
        --model NOM=STL [--model ...] --runs NOM=N [...] --slicer NOM=CHEMIN [...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

BED = (250.0, 210.0, 220.0)
CENTER = (BED[0] / 2, BED[1] / 2)
PLA_NOZZLE_C = (180, 230)
PLA_BED_C = (0, 70)

WHITELIST = {
    'G0', 'G1', 'G2', 'G3', 'G4', 'G10', 'G11', 'G21', 'G28', 'G29', 'G90', 'G92',
    'M73', 'M82', 'M83', 'M84', 'M104', 'M105', 'M106', 'M107', 'M109', 'M117', 'M140', 'M190',
    'M201', 'M203', 'M204', 'M205', 'M220', 'M221', 'M486', 'M900',
}
FORBIDDEN_HEADER = 'NE PAS ENVOYER A UNE MACHINE'

# Traduction PrusaSlicer -> OrcaSlicer, valeurs relevées dans le bloc de configuration
# d'un G-code PrusaSlicer 2.7.2 produit avec le profil M08 (voir le rapport).
ORCA_MACHINE = {
    'type': 'machine', 'name': 'BOJART simulation 250x210x220', 'from': 'system', 'inherits': '',
    'version': '2.4.0.0', 'printer_technology': 'FFF', 'gcode_flavor': 'marlin2',
    'printable_area': ['0x0', '250x0', '250x210', '0x210'], 'printable_height': '220',
    'nozzle_diameter': ['0.4'], 'use_relative_e_distances': '1',
    'machine_start_gcode': '; BOJART SIMULATION - PROFIL NON VERIFIE - NE PAS ENVOYER A UNE MACHINE',
    'machine_end_gcode': '; fin simulation', 'layer_change_gcode': 'G92 E0',
    'retraction_length': ['2'], 'retraction_speed': ['40'], 'z_hop': ['0'],
    'emit_machine_limits_to_gcode': '0',
    'machine_max_acceleration_extruding': ['1500', '1250'], 'machine_max_acceleration_retracting': ['1500', '1250'],
    'machine_max_acceleration_travel': ['1500', '1250'], 'machine_max_acceleration_x': ['9000', '1000'],
    'machine_max_acceleration_y': ['9000', '1000'], 'machine_max_acceleration_z': ['500', '200'],
    'machine_max_acceleration_e': ['10000', '5000'], 'machine_max_speed_x': ['500', '200'],
    'machine_max_speed_y': ['500', '200'], 'machine_max_speed_z': ['12', '12'], 'machine_max_speed_e': ['120', '120'],
    'machine_max_jerk_x': ['10', '10'], 'machine_max_jerk_y': ['10', '10'], 'machine_max_jerk_z': ['0.2', '0.4'],
    'machine_max_jerk_e': ['2.5', '2.5'],
}
ORCA_PROCESS = {
    'type': 'process', 'name': 'BOJART simulation 0.15', 'from': 'User', 'inherits': '', 'version': '2.4.0.0',
    'compatible_printers': ['BOJART simulation 250x210x220'],
    'layer_height': '0.15', 'initial_layer_print_height': '0.2', 'wall_loops': '3',
    'top_shell_layers': '5', 'bottom_shell_layers': '4', 'sparse_infill_density': '15%',
    'sparse_infill_pattern': 'gyroid', 'enable_support': '1', 'support_type': 'tree(auto)',
    'support_style': 'organic', 'support_threshold_angle': '50', 'support_top_z_distance': '0.2',
    'outer_wall_speed': '30', 'inner_wall_speed': '60', 'sparse_infill_speed': '80',
    'internal_solid_infill_speed': '20', 'top_surface_speed': '15', 'support_speed': '60',
    'support_interface_speed': '60', 'travel_speed': '130', 'initial_layer_speed': '30',
    'initial_layer_infill_speed': '30', 'bridge_speed': '60', 'gap_infill_speed': '20',
    'small_perimeter_speed': '15', 'enable_overhang_speed': '0',
    'default_acceleration': '1500', 'outer_wall_acceleration': '1500', 'inner_wall_acceleration': '1500',
    'initial_layer_acceleration': '1500', 'top_surface_acceleration': '1500', 'travel_acceleration': '1500',
    'bridge_acceleration': '100%', 'sparse_infill_acceleration': '100%',
    'internal_solid_infill_acceleration': '100%', 'default_jerk': '0',
    'skirt_loops': '1', 'skirt_distance': '6', 'skirt_height': '1', 'brim_type': 'no_brim',
    'thick_bridges': '1', 'top_surface_pattern': 'monotonic', 'bottom_surface_pattern': 'monotonic',
    'seam_position': 'aligned',
}
ORCA_FILAMENT = {
    'type': 'filament', 'name': 'BOJART PLA simulation', 'from': 'User', 'inherits': '', 'version': '2.4.0.0',
    'compatible_printers': ['BOJART simulation 250x210x220'],
    'filament_type': ['PLA'], 'filament_diameter': ['1.75'], 'filament_density': ['1.24'],
    'nozzle_temperature': ['215'], 'nozzle_temperature_initial_layer': ['215'],
    **{f'{p}_plate_temp{s}': ['60'] for p in ('hot', 'cool', 'eng', 'textured') for s in ('', '_initial_layer')},
    'filament_max_volumetric_speed': ['50'],
    'fan_min_speed': ['35'], 'fan_max_speed': ['100'], 'slow_down_layer_time': ['5'],
    'slow_down_min_speed': ['10'], 'close_fan_the_first_x_layers': ['3'], 'fan_cooling_layer_time': ['60'],
    'overhang_fan_speed': ['100'],
}
# Réglages relus dans le bloc de configuration de chaque G-code (nom Prusa, nom Orca).
COMPARE_KEYS = [
    ('layer_height', 'layer_height'), ('perimeters', 'wall_loops'), ('fill_density', 'sparse_infill_density'),
    ('fill_pattern', 'sparse_infill_pattern'), ('perimeter_speed', 'inner_wall_speed'),
    ('external_perimeter_speed', 'outer_wall_speed'), ('infill_speed', 'sparse_infill_speed'),
    ('solid_infill_speed', 'internal_solid_infill_speed'), ('travel_speed', 'travel_speed'),
    ('support_material_style', 'support_style'), ('support_material_threshold', 'support_threshold_angle'),
    ('filament_max_volumetric_speed', 'filament_max_volumetric_speed'), ('retract_length', 'retraction_length'),
    ('skirt_distance', 'skirt_distance'), ('perimeter_generator', 'wall_generator'),
    ('ensure_vertical_shell_thickness', 'ensure_vertical_shell_thickness'),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def normalized_sha(p: Path) -> str:
    """Empreinte sans les lignes d'horodatage, pour juger le déterminisme."""
    h = hashlib.sha256()
    with p.open('rb') as f:
        for line in f:
            if line.startswith(b'; generated by'):
                continue
            h.update(line)
    return h.hexdigest()


def config_block(p: Path) -> dict:
    d = {}
    with p.open(encoding='utf8', errors='replace') as f:
        for line in f:
            m = re.match(r'^; ([a-z_0-9]+) = (.*)$', line.rstrip('\n'))
            if m:
                d[m.group(1)] = m.group(2)
    return d


def stats(p: Path) -> dict:
    text = p.read_text(encoding='utf8', errors='replace')

    def grab(rx):
        m = re.search(rx, text)
        return m.group(1).strip() if m else None
    out = {'estimated_time_normal': grab(r'; estimated printing time \(normal mode\) = (.+)'),
           'filament_mm': grab(r'; filament used \[mm\] = ([\d.]+)'),
           'filament_g': grab(r'; (?:total )?filament used \[g\] = ([\d.]+)'),
           'layer_changes': text.count(';LAYER_CHANGE')}
    for k in ('filament_mm', 'filament_g'):
        out[k] = float(out[k]) if out[k] else None
    out['estimated_seconds'] = to_seconds(out['estimated_time_normal'])
    return out


def to_seconds(s):
    if not s:
        return None
    total = 0
    for v, u in re.findall(r'(\d+)([dhms])', s):
        total += int(v) * {'d': 86400, 'h': 3600, 'm': 60, 's': 1}[u]
    return total


ROLE_GROUPS = {
    'parois': ('perimeter', 'external perimeter', 'overhang perimeter', 'outer wall', 'inner wall', 'overhang wall'),
    'remplissage': ('internal infill', 'sparse infill'),
    'pleins': ('solid infill', 'top solid infill', 'internal solid infill', 'top surface', 'bottom surface',
               'bridge infill', 'bridge', 'internal bridge', 'gap fill', 'gap infill'),
    'supports': ('support material', 'support material interface', 'support', 'support interface',
                 'support transition'),
    'jupe': ('skirt/brim', 'skirt', 'brim'),
}


def extrusion_by_role(p: Path) -> dict:
    """Filament déposé (mm, extrusion relative M83) par rôle ;TYPE: du G-code, regroupé en familles.
    Seuls les mouvements X/Y qui extrudent comptent : les réarmements après rétraction (E seul) sont exclus."""
    per, role, rel = {}, None, False
    with p.open(encoding='utf8', errors='replace') as f:
        for line in f:
            if line.startswith(';TYPE:'):
                role = line[6:].strip().lower()
                continue
            if line.startswith('M83'):
                rel = True
            code = line.split(';', 1)[0]
            if code.startswith('G1') and ' E' in code and (' X' in code or ' Y' in code):  # hors désarmement
                m = re.search(r' E(-?[\d.]+)', code)
                if m and rel:
                    e = float(m.group(1))
                    if e > 0:
                        per[role] = per.get(role, 0.0) + e
    groups = {g: 0.0 for g in ROLE_GROUPS}
    other = {}
    for r, e in per.items():
        for g, names in ROLE_GROUPS.items():
            if r in names:
                groups[g] += e
                break
        else:
            other[r or 'sans rôle'] = round(e, 1)
    out = {g: round(v, 1) for g, v in groups.items()}
    out['autres'] = other
    return out


def review(p: Path) -> dict:
    """Relecteur G-code : liste blanche, bornes du volume, températures, chauffe avant extrusion."""
    abs_xyz, abs_e = True, True
    pos = {'X': None, 'Y': None, 'Z': 0.0}
    lo = {'X': float('inf'), 'Y': float('inf'), 'Z': float('inf')}
    hi = {'X': float('-inf'), 'Y': float('-inf'), 'Z': float('-inf')}
    unknown, temps, issues = {}, [], []
    heated_wait = False
    first_extrusion_before_wait = None
    header = False
    with p.open(encoding='utf8', errors='replace') as f:
        for n, raw in enumerate(f, 1):
            if FORBIDDEN_HEADER in raw and n < 400:
                header = True
            line = raw.split(';', 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].upper()
            if cmd not in WHITELIST:
                unknown[cmd] = unknown.get(cmd, 0) + 1
                continue
            args = {a[0].upper(): a[1:] for a in parts[1:] if a}
            if cmd == 'G91':
                abs_xyz = False
            elif cmd == 'G90':
                abs_xyz = True
            elif cmd == 'M83':
                abs_e = False
            elif cmd == 'M82':
                abs_e = True
            elif cmd in ('M104', 'M109', 'M140', 'M190') and 'S' in args:
                t = float(args['S']); temps.append((cmd, t))
                rng = PLA_NOZZLE_C if cmd in ('M104', 'M109') else PLA_BED_C
                if t and not rng[0] <= t <= rng[1]:
                    issues.append(f'ligne {n} : {cmd} S{t:g} hors plage PLA {rng}')
                if cmd == 'M109' and t >= PLA_NOZZLE_C[0]:
                    heated_wait = True
            elif cmd in ('G0', 'G1', 'G2', 'G3'):
                for ax in 'XYZ':
                    if ax in args:
                        v = float(args[ax])
                        pos[ax] = v if abs_xyz else (pos[ax] or 0) + v
                        lo[ax] = min(lo[ax], pos[ax]); hi[ax] = max(hi[ax], pos[ax])
                if 'E' in args and float(args['E']) > 0 and not heated_wait and first_extrusion_before_wait is None:
                    first_extrusion_before_wait = n
    for ax, lim in zip('XYZ', BED):
        if hi[ax] > lim + 1e-6 or lo[ax] < -1e-6:
            issues.append(f'{ax} parcourt {lo[ax]:.2f}..{hi[ax]:.2f} mm, hors 0..{lim:g}')
    if unknown:
        issues.append(f'commandes hors liste blanche : {unknown}')
    if not header:
        issues.append("en-tête d'interdiction absent")
    heating = [t for t in temps if t[1] > 0]
    notes = []
    if not heating:
        notes.append('aucune consigne de chauffe : fichier de simulation, non imprimable tel quel (voulu par le profil)')
    elif first_extrusion_before_wait:
        notes.append(f"chauffe émise sans attente M109 avant la première extrusion (ligne {first_extrusion_before_wait}) : "
                     'sur une machine réelle, extrusion possible buse froide')
    if heating:
        notes.append(f'consignes de chauffe émises malgré le profil de simulation : {sorted(set(heating))}')
    return {'accepted': not issues, 'issues': issues, 'notes': notes,
            'travel_bounds_mm': {ax: [round(lo[ax], 2), round(hi[ax], 2)] for ax in 'XYZ'},
            'relative_xyz_seen': not abs_xyz, 'absolute_e': abs_e}


def run_prusa(exe, ini, stl, out_dir: Path, tag):
    g = out_dir / f'{tag}.gcode'
    cmd = [exe, '--export-gcode', '--load', str(ini), '--center', f'{CENTER[0]:g},{CENTER[1]:g}',
           '--output', str(g), str(stl)]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    dt = time.perf_counter() - t0
    log = (p.stdout + p.stderr)
    ok = p.returncode == 0 and g.exists()
    return ok, dt, g if ok else None, {'returncode': p.returncode,
                                       'warnings': [l.strip() for l in log.splitlines()
                                                    if re.search(r'warn|error', l, re.I)][:6]}


def run_orca(exe, cfg_dir: Path, stl, out_dir: Path, tag):
    od = out_dir / tag; od.mkdir(parents=True, exist_ok=True)
    cmd = [exe, '--datadir', str(cfg_dir / 'datadir'),
           '--load-settings', f"{cfg_dir / 'machine.json'};{cfg_dir / 'process.json'}",
           '--load-filaments', str(cfg_dir / 'filament.json'), '--arrange', '1', '--slice', '0',
           '--outputdir', str(od), str(stl)]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    dt = time.perf_counter() - t0
    res = {}
    if (od / 'result.json').exists():
        res = json.loads((od / 'result.json').read_text(encoding='utf8'))
    g = od / 'plate_1.gcode'
    ok = p.returncode == 0 and g.exists()
    warn = [pl.get('warning_message') for pl in res.get('sliced_plates', []) if pl.get('warning_message')]
    return ok, dt, g if ok else None, {'returncode': p.returncode, 'result': res.get('error_string'),
                                       'warnings': warn}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--m08', required=True, type=Path)
    ap.add_argument('--work', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--model', action='append', required=True)
    ap.add_argument('--runs', action='append', default=[])
    ap.add_argument('--slicer', action='append', required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(a.m08 / 'jarvis' / 'apps' / 'jarvis' / 'app'))
    from figurine import slicing  # noqa: E402

    a.work.mkdir(parents=True, exist_ok=True)
    ini = a.work / 'profil_m08.ini'; slicing.write_profile(ini)
    cfg = a.work / 'orca_profil'; cfg.mkdir(exist_ok=True)
    for name, d in (('machine', ORCA_MACHINE), ('process', ORCA_PROCESS), ('filament', ORCA_FILAMENT)):
        (cfg / f'{name}.json').write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf8')
    models = dict(m.split('=', 1) for m in a.model)
    runs = {k: int(v) for k, v in (r.split('=', 1) for r in a.runs)}
    slicers = dict(s.split('=', 1) for s in a.slicer)

    results = {}
    for mname, stl in models.items():
        stl = Path(stl)
        results[mname] = {'stl_sha256': sha(stl), 'bytes': stl.stat().st_size, 'slicers': {}}
        for sname, exe in slicers.items():
            times, hashes, last, info_runs = [], [], None, []
            for i in range(runs.get(mname, 3)):
                tag = f'{mname}__{sname}__{i}'
                if sname.startswith('orca'):
                    ok, dt, g, info = run_orca(exe, cfg, stl, a.work, tag)
                else:
                    ok, dt, g, info = run_prusa(exe, ini, stl, a.work, tag)
                info_runs.append(dict(info, ok=ok, seconds=round(dt, 2)))
                if not ok:
                    break
                times.append(dt); hashes.append(normalized_sha(g))
                if last and last != g:
                    last.unlink(missing_ok=True)  # garder une seule sortie par trancheur
                last = g
            row = {'runs': info_runs, 'errors': sum(not r['ok'] for r in info_runs)}
            if times:
                st = sorted(times)
                row['slicing_seconds'] = {'n': len(st), 'min': round(st[0], 2),
                                          'median': round(statistics.median(st), 2), 'max': round(st[-1], 2)}
                row['deterministic'] = len(set(hashes)) == 1
                row['gcode_sha256_normalized'] = hashes[-1]
                row['stats'] = stats(last)
                row['review'] = review(last)
                row['extrusion_mm_by_role'] = extrusion_by_role(last)
                c = config_block(last)
                row['effective_settings'] = {pk: c.get(ok_ if sname.startswith('orca') else pk)
                                             for pk, ok_ in COMPARE_KEYS}
                row['gcode_bytes'] = last.stat().st_size
            results[mname]['slicers'][sname] = row
            print(mname, sname, row.get('slicing_seconds'), row.get('stats', {}).get('estimated_time_normal'),
                  row.get('stats', {}).get('filament_g'), row.get('review', {}).get('accepted'), flush=True)

    vers = {}
    for sname, exe in slicers.items():
        p = subprocess.run([exe, '--help'], capture_output=True, text=True, timeout=120)
        vers[sname] = ((p.stdout or p.stderr).splitlines() or [''])[0].strip()
    report = {
        'bench': 'B4-trancheurs', 'status': 'executed',
        'executed_on': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'environment': {'where': 'conteneur Linux de session, 4 cœurs, sans GPU (pas la tour)',
                        'python': platform.python_version(), 'slicers': vers,
                        'install': 'PrusaSlicer 2.7.2 par apt (Ubuntu) ; 2.9.7 et OrcaSlicer 2.4.2 par Flathub, '
                                   'lancés hors bac à sable avec le chargeur du runtime GNOME 50'},
        'profile': {'prusaslicer': slicing.PROFILE, 'orcaslicer': {'machine': ORCA_MACHINE, 'process': ORCA_PROCESS,
                                                                   'filament': ORCA_FILAMENT}},
        'reviewer': {'whitelist': sorted(WHITELIST), 'bed_mm': BED, 'pla_nozzle_c': PLA_NOZZLE_C,
                     'pla_bed_c': PLA_BED_C},
        'results': results,
        'limits': ['temps de tranchage mesurés dans un conteneur partagé : ordre de grandeur, pas une mesure de la tour',
                   'n petit : médiane et maximum, pas de p95',
                   'temps et matière = estimations des trancheurs, aucune impression réelle',
                   'Orca : traduction du profil, pas une équivalence parfaite (moteurs de supports et de remplissage différents)'],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=1).replace(str(a.work.resolve()), '<travail>')
    a.out.write_text(text.replace(str(a.work), '<travail>') + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
