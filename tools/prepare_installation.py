#!/usr/bin/env python3
"""Prepare local memory; model setup and downloads require explicit arguments."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_ops import verrou_dependances  # noqa: E402


def install_commands(executable, requirements, os_name=os.name, root=ROOT):
    """Windows: install the hashed lock tested by the bench, exactly. Elsewhere, or with a stale lock: pinned requirements."""
    if os_name != 'nt':
        return [[str(executable), '-m', 'pip', 'install', '-r', str(req)] for req in requirements], []
    problems = {p['verrou'] for p in verrou_dependances.verify(root, 'windows')}
    by_file = {path.resolve(): name for name, path in verrou_dependances.profiles(root).items()}
    commands, notes = [], []
    for req in requirements:
        profile = by_file.get(Path(req).resolve())
        lock = verrou_dependances.lock_path(profile, 'windows', root) if profile else None
        if lock and lock.exists() and verrou_dependances.rel(lock, root) not in problems:
            commands.append([str(executable), '-m', 'pip', 'install', '--require-hashes', '--no-deps', '-r', str(lock)])
        else:
            notes.append(f'Verrou Windows absent ou périmé pour {Path(req).name} : versions principales épinglées, '
                         'dépendances indirectes non verrouillées.')
            commands.append([str(executable), '-m', 'pip', 'install', '-r', str(req)])
    if requirements:
        commands.append([str(executable), '-m', 'pip', 'check'])
    return commands, notes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engines', action='store_true', help='Installer aussi CAO et LangGraph depuis les requirements M07.')
    p.add_argument('--voice', action='store_true', help='Installer les bibliothèques voix ; poids à fournir séparément.')
    p.add_argument('--no-venv', action='store_true', help='Utiliser cet interpréteur, pour recette isolée.')
    p.add_argument('--model-profile', choices=('speed', 'balanced', 'quality'), help='Tester et activer ce profil de modèles locaux.')
    p.add_argument('--download-models', action='store_true', help='Télécharger les modèles manquants du profil demandé.')
    a = p.parse_args()
    if a.download_models and not a.model_profile:
        p.error('--download-models exige --model-profile.')
    if sys.version_info[:2] != (3, 12):
        raise SystemExit('Utiliser Python 3.12 pour cette procédure BOJ.ART.')
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE VIRTUAL TABLE check_fts USING fts5(text)')
    executable = Path(sys.executable)
    if not a.no_venv:
        envdir = ROOT / '.venv'
        executable = envdir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not executable.exists(): venv.EnvBuilder(with_pip=True).create(envdir)
        subprocess.run([str(executable), '-c', 'import sys; assert sys.version_info[:2] == (3,12), "Recreer .venv avec Python 3.12"'], check=True)
    requirements = []
    if a.engines: requirements.append(ROOT / 'jarvis/requirements.txt')
    if a.voice: requirements.append(ROOT / 'jarvis/requirements-voice.txt')
    commands, notes = install_commands(executable, requirements)
    for note in notes:
        print(note)
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run([str(executable), '-m', 'bojart_memory.agent_cli', 'index'], cwd=ROOT, check=True)
    if a.model_profile:
        command = [str(executable), str(ROOT / 'tools/setup_local_models.py'), '--profile', a.model_profile, '--apply']
        if a.download_models:
            command.append('--download')
        subprocess.run(command, cwd=ROOT, check=True)
    report = subprocess.run([str(executable), str(ROOT / 'tools/doctor.py')], cwd=ROOT, check=True, capture_output=True, text=True,
                            encoding='utf-8', env=dict(os.environ, PYTHONUTF8='1'))
    state = Path(os.environ.get('BOJART_MEMORY_STATE', str(Path.home() / 'BOJART/memory'))).expanduser()
    state.mkdir(parents=True, exist_ok=True)
    (state / 'installation-report.json').write_text(report.stdout, encoding='utf-8')
    print('Mémoire initialisée. Ouvrir Lancer_BOJART puis Mémoire du projet. Contrôle matériel à effectuer sur place.')
    print(report.stdout)


if __name__ == '__main__':
    try: main()
    except (OSError, sqlite3.Error, subprocess.CalledProcessError) as e:
        raise SystemExit('Installation interrompue, sans effacer les données existantes : ' + str(e))
