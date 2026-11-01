#!/usr/bin/env python3
"""Local readiness: no installation, microphone, provider call or model download."""
import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_memory import Memory, MemoryError
from bojart_memory.paths import default_state

PACKAGES = ('cadquery', 'trimesh', 'langgraph', 'langgraph-checkpoint-sqlite',
            'faster-whisper', 'ctranslate2')


def runtime_probe():
    """Import installed CAD/graph engines in a bounded, isolated process.

    Package stdout and exception messages are never included in the report.
    No geometry, audio, GPU job or network request is initiated.
    """
    code = """
import importlib, json
result = {}
for name in ('cadquery', 'trimesh', 'langgraph.graph', 'langgraph.checkpoint.sqlite'):
    try:
        importlib.import_module(name)
        result[name] = {'ok': True}
    except Exception as exc:
        result[name] = {'ok': False, 'error_type': type(exc).__name__}
print('BOJART_PROBE:' + json.dumps(result))
"""
    env = dict(os.environ, LANGSMITH_TRACING='false', LANGCHAIN_TRACING_V2='false',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    try:
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=30)
        lines = [s for s in result.stdout.splitlines() if s.startswith('BOJART_PROBE:')]
        if result.returncode or not lines:
            return {'status': 'failed', 'error_type': 'RuntimeImportFailed'}
        return {'status': 'checked', 'modules': json.loads(lines[-1].split(':', 1)[1])}
    except subprocess.TimeoutExpired:
        return {'status': 'failed', 'error_type': 'ImportTimeout'}
    except (OSError, ValueError):
        return {'status': 'failed', 'error_type': 'RuntimeProbeFailed'}


def configuration(config=None):
    # The original runtime allows fallback for a missing path; an explicitly
    # requested private configuration must be diagnosed before that fallback.
    if config is not None and not Path(config).expanduser().is_file():
        return {'ok': False, 'error_type': 'ExplicitConfigurationMissing'}
    sys.path.insert(0, str(ROOT / 'jarvis/apps/jarvis/app'))
    try:
        from workbench import load_config
        from voice import LocalVoice
        from jev_decider import JevDecider
        loaded = load_config(str(Path(config).expanduser()) if config is not None else None)
        voice = LocalVoice(loaded['voice']).status()
        decider = JevDecider()
        jev = decider.status()
        return {'ok': True, 'voice': voice,
                'voice_requested': loaded['voice']['enabled'],
                'ollama_requested': loaded['ollama']['enabled'],
                'jev_enabled': decider.enabled, 'jev_status': jev['status'],
                'jev_key_present': bool(os.environ.get('TYPESAFE_API_KEY'))}
    except Exception as exc:
        return {'ok': False, 'error_type': type(exc).__name__}


def report(*, config=None, memory_state=None, runtime_state=None,
           probe_imports=False, verify_memory=False):
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    with sqlite3.connect(':memory:') as db:
        try:
            db.execute('CREATE VIRTUAL TABLE t USING fts5(text)')
            fts = True
        except sqlite3.OperationalError:
            fts = False
    memory_path = Path(memory_state if memory_state is not None else default_state()).expanduser().resolve()
    work_path = Path(runtime_state if runtime_state is not None else Path.home()/'BOJART/mission05').expanduser().resolve()
    separate = not (memory_path.is_relative_to(work_path) or work_path.is_relative_to(memory_path))
    document_memory = {'initialized': (memory_path/'memory.sqlite').is_file(),
                       'integrity': 'not_checked'}
    if document_memory['initialized']:
        try:
            with Memory(memory_path, readonly=True) as memory:
                if verify_memory:
                    check = memory.verify()
                    document_memory['integrity'] = 'verified' if check['ok'] else 'failed'
                    document_memory['issues'] = check['issues']
                else:
                    memory.stats()  # Confirm the current schema, without migrating it.
        except (MemoryError, sqlite3.Error, OSError):
            document_memory['integrity'] = 'unreadable_or_incompatible'
    engines = runtime_probe() if probe_imports else {'status': 'not_checked'}
    modules = engines.get('modules', {})
    cad_present = bool(versions['cadquery'] and versions['trimesh'])
    cad_ok = cad_present and probe_imports and (
        modules.get('cadquery', {}).get('ok', False) and modules.get('trimesh', {}).get('ok', False))
    media = {name: bool(shutil.which(name)) for name in ('ffmpeg', 'ffprobe')}
    settings = configuration(config)
    memory_ready = sys.version_info >= (3, 11) and fts
    memory_data_ok = document_memory['integrity'] not in {'failed', 'unreadable_or_incompatible'}
    launch_blockers = []
    if not memory_ready: launch_blockers.append('python_or_sqlite_fts5')
    if not separate: launch_blockers.append('overlapping_memory_and_work_state')
    if not memory_data_ok: launch_blockers.append('memory_integrity_or_schema')
    if not settings['ok']: launch_blockers.append('private_configuration')
    workstation_blockers = list(launch_blockers)
    if not cad_ok: workstation_blockers.append('cad_runtime')
    for name, available in media.items():
        if not available: workstation_blockers.append(name)
    if settings.get('voice_requested') and settings['voice']['status'] != 'available':
        workstation_blockers.append('requested_voice_unavailable')
    return {'schema': 'bojart.installation-check.v2',
            'python': platform.python_version(), 'recommended_python': '3.12',
            'platform': platform.system(), 'sqlite': sqlite3.sqlite_version,
            'fts5': fts, 'packages': versions, 'imports': engines,
            'ffmpeg': media['ffmpeg'], 'ffprobe': media['ffprobe'],
            'configuration': settings, 'documentary_memory': document_memory,
            'separate_state_directories': separate,
            'memory_ready': memory_ready, 'launch_blockers': launch_blockers,
            'workstation_ready': not workstation_blockers,
            'workstation_blockers': workstation_blockers,
            'physical_hardware_qualified': False, 'production_ready': False,
            'models_installed_by_this_command': False, 'provider_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('memory', 'workstation'), default='memory')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--memory-state', type=Path)
    parser.add_argument('--state', type=Path, help='Données opérationnelles M07.')
    parser.add_argument('--probe-imports', action='store_true')
    parser.add_argument('--verify-memory', action='store_true')
    args = parser.parse_args()
    result = report(config=args.config, memory_state=args.memory_state, runtime_state=args.state,
                    probe_imports=args.probe_imports or args.profile == 'workstation', verify_memory=args.verify_memory)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    blockers = result['launch_blockers'] if args.profile == 'memory' else result['workstation_blockers']
    return 2 if blockers else 0


if __name__ == '__main__':
    raise SystemExit(main())
