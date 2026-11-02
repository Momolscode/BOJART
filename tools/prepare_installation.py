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
    for req in requirements:
        subprocess.run([str(executable), '-m', 'pip', 'install', '-r', str(req)], cwd=ROOT, check=True)
    subprocess.run([str(executable), '-m', 'bojart_memory.agent_cli', 'index'], cwd=ROOT, check=True)
    if a.model_profile:
        command = [str(executable), str(ROOT / 'tools/setup_local_models.py'), '--profile', a.model_profile, '--apply']
        if a.download_models:
            command.append('--download')
        subprocess.run(command, cwd=ROOT, check=True)
    report = subprocess.run([str(executable), str(ROOT / 'tools/doctor.py')], cwd=ROOT, check=True, capture_output=True, text=True)
    state = Path(os.environ.get('BOJART_MEMORY_STATE', str(Path.home() / 'BOJART/memory'))).expanduser()
    state.mkdir(parents=True, exist_ok=True)
    (state / 'installation-report.json').write_text(report.stdout, encoding='utf-8')
    print('Mémoire initialisée. Ouvrir Lancer_BOJART puis Mémoire du projet. Contrôle matériel à effectuer sur place.')
    print(report.stdout)


if __name__ == '__main__':
    try: main()
    except (OSError, sqlite3.Error, subprocess.CalledProcessError) as e:
        raise SystemExit('Installation interrompue, sans effacer les données existantes : ' + str(e))
