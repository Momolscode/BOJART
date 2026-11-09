"""Tranchage hors ligne avec PrusaSlicer en ligne de commande.

Le profil est une HYPOTHÈSE DE SIMULATION (aucune machine du parc n'est identifiée).
Le G-code produit sert à l'estimation et à l'aperçu des couches : il porte un en-tête
d'interdiction et n'est jamais envoyé. Aucun port série ni réseau n'est ouvert ici.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

SIM_BED_MM = (250.0, 210.0, 220.0)   # volume d'hypothèse, pas une machine inventoriée

PROFILE = {
    'bed_shape': f'0x0,{SIM_BED_MM[0]:g}x0,{SIM_BED_MM[0]:g}x{SIM_BED_MM[1]:g},0x{SIM_BED_MM[1]:g}',
    'max_print_height': f'{SIM_BED_MM[2]:g}',
    'nozzle_diameter': '0.4', 'filament_diameter': '1.75', 'filament_type': 'PLA',
    'filament_density': '1.24', 'temperature': '215', 'first_layer_temperature': '215',
    'bed_temperature': '60', 'first_layer_bed_temperature': '60',
    'layer_height': '0.15', 'first_layer_height': '0.2', 'perimeters': '3',
    'top_solid_layers': '5', 'bottom_solid_layers': '4', 'fill_density': '15%', 'fill_pattern': 'gyroid',
    'support_material': '1', 'support_material_auto': '1', 'support_material_style': 'organic',
    'support_material_threshold': '50', 'support_material_contact_distance': '0.2',
    'gcode_flavor': 'marlin2', 'use_relative_e_distances': '1',
    'start_gcode': '; BOJART SIMULATION - PROFIL NON VERIFIE - NE PAS ENVOYER A UNE MACHINE',
    'end_gcode': '; fin simulation',
    'layer_gcode': 'G92 E0',
    'autoemit_temperature_commands': '0',
}


class SlicerUnavailable(RuntimeError):
    pass


def find_slicer():
    for name in ('prusa-slicer', 'PrusaSlicer', 'prusa-slicer-console'):
        path = shutil.which(name)
        if path:
            return path
    return None


def slicer_version(exe):
    out = subprocess.run([exe, '--help'], capture_output=True, text=True, timeout=60)
    first = (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else ''
    return first.strip()


def write_profile(path: Path):
    path.write_text(''.join(f'{k} = {v}\n' for k, v in PROFILE.items()), encoding='utf8')


def parse_gcode_stats(gcode: Path) -> dict:
    keys = {
        'estimated_time_normal': r'; estimated printing time \(normal mode\) = (.+)',
        'filament_mm': r'; filament used \[mm\] = ([\d.]+)',
        'filament_cm3': r'; filament used \[cm3\] = ([\d.]+)',
        'filament_g': r'; total filament used \[g\] = ([\d.]+)',
        'layer_count': None,
    }
    text = gcode.read_text(encoding='utf8', errors='replace')
    out = {}
    for k, rx in keys.items():
        if rx:
            m = re.search(rx, text)
            out[k] = m.group(1).strip() if m else None
    out['layer_count'] = text.count(';LAYER_CHANGE')
    out['forbidden_header_present'] = 'NE PAS ENVOYER A UNE MACHINE' in text[:4000]
    for k in ('filament_mm', 'filament_cm3', 'filament_g'):
        if out[k] is not None:
            out[k] = float(out[k])
    return out


def slice_part(stl: Path, out_dir: Path, *, exe=None, timeout=900, fault=None) -> dict:
    exe = exe or find_slicer()
    if fault == 'slicer_missing':
        exe = None
    if not exe:
        raise SlicerUnavailable('Trancheur PrusaSlicer introuvable : étape BLOQUÉE, aucun chiffre inventé.')
    profile = out_dir / 'profil_simulation.ini'
    if not profile.exists():
        write_profile(profile)
    gcode = out_dir / f'{stl.stem}.SIMULATION-NE-PAS-IMPRIMER.gcode'
    args = [exe, '--export-gcode', '--load', str(profile), '--center',
            f'{SIM_BED_MM[0] / 2:g},{SIM_BED_MM[1] / 2:g}', '--output', str(gcode), str(stl)]
    if fault == 'slicer_fail':
        args = [exe, '--export-gcode', '--load', str(profile), '--output', str(gcode), str(out_dir / 'absent.stl')]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    log = (proc.stdout + '\n' + proc.stderr).strip()
    warnings = [l for l in log.splitlines() if re.search(r'warn|attention|error', l, re.I)]
    if proc.returncode != 0 or not gcode.exists():
        return {'status': 'FAILED', 'returncode': proc.returncode, 'log_tail': log[-1500:], 'warnings': warnings}
    stats = parse_gcode_stats(gcode)
    return {'status': 'DONE', 'gcode': gcode.name, 'stats': stats, 'warnings': warnings,
            'nature': 'estimation de tranchage, pas une durée mesurée d’impression'}


def export_3mf(parts: dict, out: Path) -> dict:
    """Projet 3MF géométrique multi-objets (trimesh). La CLI PrusaSlicer 2.7.2 n'écrit
    qu'un seul objet par --export-3mf : constat de cette session, d'où ce repli explicite."""
    import trimesh
    scene = trimesh.Scene()
    for name, mesh in parts.items():
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    out.write_bytes(scene.export(file_type='3mf'))
    back = trimesh.load(str(out))
    n = len(back.geometry) if hasattr(back, 'geometry') else 1
    return {'status': 'DONE' if n == len(parts) else 'FAILED', 'objects_reread': n,
            'writer': f'trimesh {trimesh.__version__}', 'slicer_settings_included': False}


def layer_previews(gcode: Path, out_png: Path, fractions=(0.1, 0.35, 0.6, 0.9)) -> dict:
    """Aperçu des couches à partir des mouvements d'extrusion réels du G-code."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    layers, cur, z, x, y = [], [], 0.0, None, None
    for line in gcode.read_text(encoding='utf8', errors='replace').splitlines():
        if line.startswith(';LAYER_CHANGE'):
            if cur:
                layers.append((z, cur))
            cur = []
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith('G1') or line.startswith('G0'):
            mx = re.search(r'X([-\d.]+)', line); my = re.search(r'Y([-\d.]+)', line); me = re.search(r'E([-\d.]+)', line)
            nx = float(mx.group(1)) if mx else x; ny = float(my.group(1)) if my else y
            if me and float(me.group(1)) > 0 and x is not None and (mx or my):
                cur.append((x, y, nx, ny))
            x, y = nx, ny
    if cur:
        layers.append((z, cur))
    if not layers:
        return {'status': 'FAILED', 'reason': 'aucune couche lue'}
    picks = [layers[min(len(layers) - 1, int(f * len(layers)))] for f in fractions]
    fig, axes = plt.subplots(1, len(picks), figsize=(4 * len(picks), 4), dpi=110)
    for ax, (zz, segs) in zip(axes, picks):
        for x0, y0, x1, y1 in segs:
            ax.plot((x0, x1), (y0, y1), lw=0.25, color='#c0492b')
        ax.set_title(f'z = {zz:.2f} mm'); ax.set_aspect('equal'); ax.axis('off')
    fig.suptitle('Aperçu couches (G-code de simulation)')
    fig.tight_layout(); fig.savefig(out_png); plt.close(fig)
    return {'status': 'DONE', 'layers_read': len(layers), 'preview_z_mm': [round(p[0], 2) for p in picks]}
