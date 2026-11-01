"""Observe this host's tools without installing, rendering or controlling equipment."""
from __future__ import annotations

import csv
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 4
MAX_OUTPUT = 65536

# Fixed commands only. Research files and transcripts never supply executable arguments.
# Detection of GUI programs is deliberately separate from executing their projects.
EXECUTABLES = {
    'ffmpeg': (('ffmpeg',), ('-version',), r'^ffmpeg version ([A-Za-z0-9_.+~:-]+)', None),
    'ffprobe': (('ffprobe',), ('-version',), r'^ffprobe version ([A-Za-z0-9_.+~:-]+)', None),
    'blender': (('blender',), ('--factory-startup', '--disable-autoexec', '--version'),
                r'^Blender (\d+\.\d+(?:\.\d+)?)', 'blender'),
    'node': (('node',), ('--version',), r'^v(\d+\.\d+\.\d+)', None),
    'ollama': (('ollama',), (), None, None),
    'orcaslicer': (('OrcaSlicer', 'orca-slicer'), (), None, 'orcaslicer'),
    'uvtools': (('UVtools', 'uvtools'), (), None, 'uvtools'),
    'aftereffects': (('aerender',), (), None, 'aftereffects_native'),
    'nvidia_smi': (('nvidia-smi',), (), None, None),
}
PACKAGES = {
    'langgraph': 'langgraph', 'langgraph-checkpoint-sqlite': 'langgraph',
    'cadquery': 'cadquery', 'trimesh': 'trimesh', 'manifold3d': 'manifold',
    'faster-whisper': 'faster_whisper', 'ctranslate2': 'faster_whisper',
    'pipecat-ai': 'pipecat', 'docling': 'docling',
    'opentimelineio': 'opentimelineio',
}
UNPROBED = {
    'moonraker': 'Firmware, adresse de la machine et procédure opérateur à qualifier.',
    'aftereffects_mcp': 'Bridge, autorisation locale et projet Adobe à essayer dans After Effects.',
    'higgsfield': 'Connecteur Jarvis et reçus à qualifier ; une connexion ChatGPT ne suffit pas.',
    'search_console': 'Propriété, période et export réel à sélectionner.',
    'tiktok_search': 'Compte, requêtes et statistiques natives à relever.',
}
NEXT_STEPS = {
    'ffmpeg': 'Vérifier un export vidéo et son audio avec FFprobe.',
    'ffprobe': 'Vérifier durée, résolution, cadence et pistes du fichier exporté.',
    'blender': 'Ouvrir la référence fidèle, contrôler la géométrie puis un rendu local.',
    'node': 'Tester séparément le bridge choisi ; Node seul ne raccorde aucun outil.',
    'ollama': 'Diagnostiquer les modèles locaux puis mesurer le profil choisi.',
    'orcaslicer': 'Renseigner le profil machine et matière avant un tranchage témoin.',
    'uvtools': 'Analyser un fichier résine du slicer retenu avant la recette opérateur.',
    'aftereffects': 'Ouvrir un projet témoin avec ses polices et plugins, puis vérifier le rendu.',
    'nvidia_smi': 'Vérifier pilote et capacité par GPU avant de choisir les modèles.',
}


def resolve_tools(overrides=None):
    """Explicit local paths override PATH; no command strings or batch wrappers."""
    overrides = overrides or {}
    if not isinstance(overrides, dict) or set(overrides) - set(EXECUTABLES):
        raise ValueError('Identifiant d’outil inconnu.')
    result = {}
    for key, (names, _, _, _) in EXECUTABLES.items():
        if key in overrides:
            path = Path(overrides[key]).expanduser()
            if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
                raise ValueError('Le chemin explicite doit désigner un exécutable local absolu.')
            value = str(path.resolve())
        else:
            value = next((p for name in names if (p := shutil.which(name))), None)
        if value and Path(value).suffix.lower() in {'.cmd', '.bat', '.ps1'}:
            if key in overrides:
                raise ValueError('Utiliser le binaire de l’outil, pas un script de commande.')
            value = None
        result[key] = value
    return result


def command(path, args):
    """Return bounded machine-readable output; discard stderr and exception details."""
    try:
        run = subprocess.run([path, *args], stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             shell=False, timeout=TIMEOUT, cwd=ROOT)
        if run.returncode:
            return 'failed', None
        if len(run.stdout) > MAX_OUTPUT:
            return 'invalid_output', None
        return 'ok', run.stdout.decode('utf-8', errors='strict')
    except subprocess.TimeoutExpired:
        return 'timeout', None
    except (OSError, UnicodeError):
        return 'failed', None


def executable_report(paths):
    rows = {}
    for key, (_, args, pattern, catalog_id) in EXECUTABLES.items():
        path = paths[key]
        row = {'detected': path is not None, 'version': None,
               'version_probe': 'not_run', 'catalog_id': catalog_id,
               'integration_qualified': False}
        if not path:
            row['version_probe'] = 'not_found'
        elif args:
            status, output = command(path, args)
            match = re.search(pattern, output, re.MULTILINE) if output is not None else None
            row['version_probe'] = 'verified' if status == 'ok' and match else (
                'invalid_output' if status == 'ok' else status)
            row['version'] = match[1] if match else None
        rows[key] = row
    return rows


def gpu_report(path):
    if not path:
        return {'status': 'not_detected', 'devices': [], 'other_gpu_vendors': 'not_probed'}
    status, output = command(path, ('--query-gpu=name,memory.total,driver_version',
                                    '--format=csv,noheader,nounits'))
    result = {'status': status, 'devices': [], 'other_gpu_vendors': 'not_probed'}
    if output is None:
        return result
    try:
        rows = list(csv.reader(io.StringIO(output), strict=True))
        if not rows or len(rows) > 32:
            raise ValueError('GPU rows')
        for row in rows:
            if len(row) != 3:
                raise ValueError('GPU columns')
            name, memory, driver = [v.strip() for v in row]
            if not re.fullmatch(r'[A-Za-z0-9 ()+./_-]{1,120}', name):
                raise ValueError('GPU name')
            if memory in {'N/A', '[N/A]', '[Not Supported]'}:
                mib = None
            elif re.fullmatch(r'\d+(?:\.\d+)?', memory) and 0 < float(memory) < 10_000_000:
                mib = float(memory)
            else:
                raise ValueError('GPU memory')
            if driver in {'N/A', '[N/A]'}:
                driver = None
            elif not re.fullmatch(r'\d+(?:\.\d+){1,3}', driver):
                raise ValueError('GPU driver')
            result['devices'].append({'name': name, 'vram_mib': mib,
                                      'vram_gib': mib / 1024 if mib is not None else None,
                                      'driver_version': driver})
        result['status'] = 'observed'
    except (ValueError, csv.Error):
        result.update(status='invalid_output', devices=[])
    return result


def ram_bytes(system):
    try:
        if system == 'Windows':
            class MemoryStatus(ctypes.Structure):
                _fields_ = [('length', ctypes.c_uint32), ('load', ctypes.c_uint32)] + [
                    (name, ctypes.c_uint64) for name in (
                        'total_phys', 'available_phys', 'total_page', 'available_page',
                        'total_virtual', 'available_virtual', 'available_extended')]
            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return None
            return int(status.total_phys) or None
        if system == 'Linux':
            total = int(os.sysconf('SC_PHYS_PAGES')) * int(os.sysconf('SC_PAGE_SIZE'))
            return total if total > 0 else None
    except (AttributeError, OSError, ValueError, OverflowError):
        pass
    return None


def report(*, tool_paths=None):
    paths = resolve_tools(tool_paths)
    executables = executable_report(paths)
    gpu = gpu_report(paths['nvidia_smi'])
    system = platform.system()
    ram = ram_bytes(system)
    packages = {}
    for name, catalog_id in PACKAGES.items():
        try:
            version = importlib.metadata.version(name)
            status = 'metadata_found'
        except importlib.metadata.PackageNotFoundError:
            version, status = None, 'not_found'
        except (OSError, ValueError):
            version, status = None, 'unreadable_metadata'
        packages[name] = {'status': status, 'version': version, 'catalog_id': catalog_id,
                          'import_tested': False, 'integration_qualified': False}
    values = {
        'os_version': f'{system} {platform.release()}', 'cpu': platform.processor() or None,
        'ram_gib': ram / 1024**3 if ram is not None else None,
        'gpu_model': [d['name'] for d in gpu['devices']] or None,
        'vram_gib': [d['vram_gib'] for d in gpu['devices']] or None,
        'driver': [d['driver_version'] for d in gpu['devices']] or None,
        'cuda_runtime': None, 'microphone': None, 'monitor_ids': None,
        'blender_version': executables['blender']['version'],
        'after_effects_version': None, 'plugins_and_fonts': None,
    }
    missing = [key for key, value in values.items()
               if value is None or isinstance(value, list) and any(v is None for v in value)]
    return {
        'schema': 'bojart.environment-observation.v1',
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'host_running_this_command', 'target_identity_confirmed': False,
        'python': platform.python_version(), 'architecture': platform.machine(),
        'cpu_logical_count': os.cpu_count(), 'ram_bytes': ram, 'gpu': gpu,
        'executables': executables, 'python_packages': packages,
        'target_hardware_dataset': {'id': 'target_hardware', 'status': 'partially_observed',
                                    'values': values, 'missing_fields': missing, 'complete': False},
        'next_actions': [
            {'id': key, 'reason': 'not_found_in_checked_environment' if not row['detected'] else row['version_probe'],
             'action': ('Localiser ou installer le binaire. ' if not row['detected'] else '') + NEXT_STEPS[key]}
            for key, row in executables.items()
        ],
        'services_not_probed': dict(UNPROBED),
        'limits': [
            'Observation du poste exécutant la commande ; aucune identité de tour présumée.',
            'PATH ou chemins explicites seulement ; un outil non trouvé peut être installé ailleurs.',
            'Métadonnées Python et versions binaires ne prouvent ni imports ni intégrations.',
            'RAM visible par le système ; une limite de conteneur peut être inférieure.',
            'NVIDIA uniquement ; VRAM totale par carte, jamais additionnée pour choisir un modèle.',
            'Le pilote NVIDIA ne prouve pas la présence du runtime CUDA ni une inférence réussie.',
        ],
        'probe_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'production_ready': False, 'physical_hardware_qualified': False,
        'models_downloaded': False, 'render_jobs': 0, 'physical_commands': 0,
        'provider_calls': 0,
    }
