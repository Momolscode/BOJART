#!/usr/bin/env python3
"""Check the local installation, index selected context, then start Jarvis."""
import argparse
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_memory.paths import default_state
from doctor import report

MESSAGES = {
    'python_or_sqlite_fts5': 'Python ou moteur de recherche SQLite indisponible',
    'overlapping_memory_and_work_state': 'les dossiers mémoire et travail doivent être distincts et non imbriqués',
    'memory_integrity_or_schema': 'la mémoire existante exige une vérification ou une migration',
    'private_configuration': 'configuration locale absente ou invalide',
    'cad_runtime': 'moteurs CAO absents ou import impossible',
    'ffmpeg': 'FFmpeg absent', 'ffprobe': 'FFprobe absent',
    'requested_voice_unavailable': 'la voix demandée manque de moteur ou de poids locaux',
}


def choose_state():
    try:
        import tkinter as tk
        from tkinter import filedialog
        window = tk.Tk()
        window.withdraw()
        try:
            return filedialog.askdirectory(title='Dossier de travail Jarvis existant ou restauré')
        finally:
            window.destroy()
    except Exception:
        raise ValueError('Sélecteur indisponible. Utiliser --state CHEMIN_DU_DOSSIER.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=Path.home()/'BOJART/mission05')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--choose-state', action='store_true')
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--check-only', action='store_true', help='Diagnostic complet sans indexer ni démarrer.')
    parser.add_argument('--check-models', action='store_true', help='Vérifier les métadonnées des modèles locaux, sans génération.')
    parser.add_argument('--require-workstation', action='store_true', help='Exiger aussi CAO, outils média et voix configurée disponibles.')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('Port invalide.')
    if args.choose_state:
        selected = choose_state()
        if not selected:
            return 0
        args.state = Path(selected)
    memory = default_state().resolve()
    work = args.state.expanduser().resolve()
    config = args.config.expanduser().resolve() if args.config is not None else None
    result = report(config=config, memory_state=memory, runtime_state=work,
                    probe_imports=True, verify_memory=args.check_only, check_models=args.check_models)
    if args.check_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result['workstation_blockers'] or (args.check_models and not result['models']['ok']) else 0
    blockers = result['launch_blockers'] or (result['workstation_blockers'] if args.require_workstation else [])
    if blockers:
        print('Démarrage interrompu : ' + '; '.join(MESSAGES[x] for x in blockers), file=sys.stderr)
        print('Diagnostic : python tools/start_jarvis.py --check-only', file=sys.stderr)
        print('Dépendances : python -m pip install -r jarvis/requirements.txt', file=sys.stderr)
        print('La mémoire seule fonctionne avec le profil par défaut ; --require-workstation exige les moteurs du poste.', file=sys.stderr)
        return 2
    if result['workstation_blockers']:
        print('Poste limité : ' + '; '.join(MESSAGES[x] for x in result['workstation_blockers']), flush=True)
    if not result['models']['ok']:
        print('Modèles IA indisponibles ou mal configurés : la recherche par mots reste disponible. '
              'Diagnostic : python -m bojart_memory.agent_cli models', flush=True)
    env = dict(os.environ, BOJART_MEMORY_STATE=str(memory), PYTHONUTF8='1')
    command = [sys.executable, '-m', 'bojart_memory.agent_cli', '--state', str(memory), 'index']
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
    if completed.returncode:
        print('Indexation interrompue. Les sources et versions antérieures sont conservées.', file=sys.stderr)
        print(completed.stderr.strip(), file=sys.stderr)
        return completed.returncode
    server = [sys.executable, str(ROOT/'jarvis/apps/jarvis/app/consolidated_workbench.py'),
              '--state', str(work), '--port', str(args.port)]
    if config is not None:
        server += ['--config', str(config)]
    if args.no_browser:
        server.append('--no-browser')
    os.chdir(ROOT/'jarvis')
    if os.name == 'nt':
        # Windows execve starts a replacement process without preserving the
        # launcher's lifetime. Keep the actual server in this process so a
        # stop/restart cannot leave an untracked server and locked state.
        os.environ.update(env)
        sys.argv = server[1:]
        sys.path.insert(0, str(Path(server[1]).parent))
        runpy.run_path(server[1], run_name='__main__')
        return 0
    os.execve(sys.executable, server, env)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc))
