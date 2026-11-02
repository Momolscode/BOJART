"""Installation complète de Jarvis sur la tour, en une fois.

Le programme détecte ce qui manque, montre le plan, demande un seul accord, puis :

1. installe Ollama et FFmpeg avec winget (Windows) s'ils manquent ;
2. démarre Ollama s'il ne répond pas ;
3. installe Jarvis complet (mémoire, CAO, LangGraph, voix) depuis les verrous Windows ;
4. télécharge et qualifie les modèles locaux du profil choisi ;
5. lance le banc de contrôle.

Chaque étape est écrite dans un journal neuf, au fil de l'eau. Une étape dont une autre dépend
et qui échoue arrête seulement ses dépendantes. Rien ici ne pilote une imprimante, ne publie,
n'achète ni n'efface de données : l'installation de Jarvis garde la mémoire existante.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OLLAMA_URL = 'http://127.0.0.1:11434'
WINGET_IDS = {'ollama': 'Ollama.Ollama', 'ffmpeg': 'Gyan.FFmpeg'}
MIN_FREE_GB = 25  # environnement Python (CAO, voix) ~3 Go + modèles speed ~4 Go + marge pour médias et sauvegardes


def home_dir(env=None):
    env = os.environ if env is None else env
    return Path(env.get('USERPROFILE') or env.get('HOME') or Path.home())


def _first(paths):
    for path in paths:
        if path and Path(path).is_file():
            return Path(path)
    return None


def find_ollama(env=None, which=shutil.which):
    env = os.environ if env is None else env
    found = which('ollama', path=env.get('PATH'))
    if found:
        return Path(found)
    local = env.get('LOCALAPPDATA')
    return _first([Path(local) / 'Programs/Ollama/ollama.exe'] if local else [])


def find_ffmpeg(env=None, which=shutil.which):
    """FFmpeg installed by winget is not on this process PATH until a new console: look where winget puts it."""
    env = os.environ if env is None else env
    found = which('ffmpeg', path=env.get('PATH'))
    if found:
        return Path(found)
    local = env.get('LOCALAPPDATA')
    if not local:
        return None
    winget = Path(local) / 'Microsoft/WinGet'
    return _first([winget / 'Links/ffmpeg.exe', *sorted(winget.glob('Packages/Gyan.FFmpeg*/*/bin/ffmpeg.exe'))])


def find_winget(env=None, which=shutil.which):
    env = os.environ if env is None else env
    found = which('winget', path=env.get('PATH'))
    return Path(found) if found else None


def ollama_version(url=OLLAMA_URL, timeout=2):
    """Local Ollama answer, without any proxy. None when it does not answer."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url + '/api/version', timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
        return data.get('version') if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def venv_python(root=ROOT, os_name=os.name):
    return Path(root) / '.venv' / ('Scripts/python.exe' if os_name == 'nt' else 'bin/python')


def detect(root=ROOT, env=None, which=shutil.which, os_name=os.name, probe=ollama_version):
    from bojart_ops import verrou_dependances
    env = os.environ if env is None else env
    ollama = find_ollama(env, which)
    ffmpeg = find_ffmpeg(env, which)
    try:
        free = round(shutil.disk_usage(home_dir(env)).free / 1e9, 1)
    except OSError:
        free = None
    return {
        'systeme': 'windows' if os_name == 'nt' else sys.platform,
        'python': platform.python_version(),
        'python_312': sys.version_info[:2] == (3, 12),
        'winget': str(find_winget(env, which) or '') or None,
        'ollama': str(ollama) if ollama else None,
        'ollama_actif': probe(),
        'ffmpeg': str(ffmpeg) if ffmpeg else None,
        'venv': venv_python(root, os_name).exists(),
        'verrous_windows': [p['detail'] for p in verrou_dependances.verify(Path(root), 'windows')] if os_name == 'nt' else None,
        'espace_libre_go': free,
    }


def plan(state, *, profile='speed', voice=True, models=True, bench=True, python=sys.executable, root=ROOT,
         os_name=os.name, stamp='0', home=None):
    """Ordered steps. Each one says what it needs; nothing here runs anything."""
    home = Path(home) if home else home_dir()
    steps = []

    def tool(key, label, needed_by_models=False):
        if state[key]:
            steps.append({'id': f'{key}_installation', 'titre': f'{label} déjà présent', 'type': 'present', 'detail': state[key]})
        elif os_name == 'nt' and state['winget']:
            steps.append({'id': f'{key}_installation', 'titre': f'Installer {label} avec winget', 'type': 'winget',
                          'commande': ['winget', 'install', '--id', WINGET_IDS[key], '--exact', '--source', 'winget',
                                       '--accept-package-agreements', '--accept-source-agreements']})
        else:
            steps.append({'id': f'{key}_installation', 'titre': f'{label} à installer à la main', 'type': 'manuel',
                          'detail': 'winget absent : https://ollama.com/download' if key == 'ollama'
                          else 'winget absent : installer FFmpeg et FFprobe (https://ffmpeg.org/download.html)'})

    if models:
        tool('ollama', 'Ollama')
    tool('ffmpeg', 'FFmpeg')
    if models:
        steps.append({'id': 'ollama_demarrage', 'type': 'demarrer_ollama', 'depend_de': ['ollama_installation'],
                      'titre': 'Ollama répond déjà' if state['ollama_actif'] else 'Démarrer Ollama et attendre sa réponse'})
    jarvis = [str(python), str(Path(root) / 'tools/prepare_installation.py'), '--engines'] + (['--voice'] if voice else [])
    steps.append({'id': 'jarvis', 'type': 'commande', 'commande': jarvis,
                  'titre': 'Installer Jarvis complet ' + ('depuis les verrous Windows' if os_name == 'nt' else '(versions épinglées)')
                  + (', voix comprise' if voice else '')})
    if models:
        steps.append({'id': 'modeles', 'type': 'commande', 'depend_de': ['ollama_demarrage', 'jarvis'],
                      'commande': [str(python), str(Path(root) / 'tools/prepare_installation.py'), '--model-profile', profile,
                                   '--download-models'],
                      'titre': f'Télécharger, tester et activer les modèles locaux « {profile} »'})
    if bench:
        out = home / 'BOJART' / 'banc'
        steps.append({'id': 'banc', 'type': 'commande', 'depend_de': ['jarvis'], 'dossier': str(out),
                      'commande': [str(venv_python(root, os_name)), str(Path(root) / 'tools/banc_preinstallation.py'),
                                   '--output', str(out / f'banc-installation-{stamp}.json'),
                                   '--markdown', str(out / f'banc-installation-{stamp}.md')],
                      'titre': 'Lancer le banc de contrôle (tests, scénarios, Windows)'})
    return steps


def warnings(state, models=True, profile='speed'):
    out = []
    if not state['python_312']:
        out.append(f'Python {state["python"]} : la procédure BOJ.ART exige Python 3.12.')
    if state['espace_libre_go'] is not None and state['espace_libre_go'] < MIN_FREE_GB:
        out.append(f'Espace libre {state["espace_libre_go"]} Go : prévoir au moins {MIN_FREE_GB} Go (environnement, modèles, médias).')
    if state['verrous_windows']:
        out.append('Verrou Windows à regénérer : ' + ' '.join(state['verrous_windows']))
    if models:
        try:
            from bojart_memory.model_setup import EMBEDDING, PROFILES
            out.append(f'Modèles : {PROFILES[profile]["chat_model"]} (~{PROFILES[profile]["weights_gb_approx"]} Go) et {EMBEDDING}, '
                       'téléchargés depuis Ollama, puis testés localement avant activation.')
        except (ImportError, KeyError):
            pass
    return out


class Journal:
    """A new file, rewritten after each step: an interrupted install still leaves its trace."""

    def __init__(self, path, data):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('x', encoding='utf-8', newline='\n') as handle:  # never overwrite an earlier journal
            json.dump(data, handle, ensure_ascii=False, indent=2)
        self.data = data

    def save(self):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        os.replace(tmp, self.path)


def child_env(state, env=None):
    """PATH for child processes, with tools winget just installed (this console does not see them yet)."""
    env = dict(os.environ if env is None else env)
    extra = [str(Path(state[k]).parent) for k in ('ollama', 'ffmpeg') if state.get(k)]
    env['PATH'] = os.pathsep.join(extra + [env.get('PATH', '')])
    env['PYTHONUTF8'] = '1'
    return env


def start_ollama(executable, probe=ollama_version, wait_s=60, popen=subprocess.Popen, sleep=time.sleep):
    flags = getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    popen([str(executable), 'serve'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
          creationflags=flags, close_fds=True)
    for _ in range(int(wait_s)):
        version = probe()
        if version:
            return version
        sleep(1)
    return None


def execute(steps, state, journal, *, run=subprocess.run, start=start_ollama, redetect=None, env=None, out=print):
    """Run the steps in order. A failed or manual step only stops the steps that depend on it."""
    redetect = redetect or (lambda key, e: {'ollama': find_ollama, 'ffmpeg': find_ffmpeg}[key](e))
    done = {}
    for step in steps:
        blockers = [d for d in step.get('depend_de', []) if done.get(d) not in ('ok', 'present')]
        began = time.perf_counter()
        record = {'id': step['id'], 'titre': step['titre']}
        if blockers:
            record.update(statut='non_lance', detail='En attente de : ' + ', '.join(blockers))
        elif step['type'] in ('present', 'manuel'):
            record.update(statut=step['type'], detail=step.get('detail'))
        else:
            out(f'\n== {step["titre"]}')
            if step['type'] == 'demarrer_ollama':
                version = state['ollama_actif'] or (start(state['ollama']) if state['ollama'] else None)
                state['ollama_actif'] = version
                record.update(statut='ok' if version else 'echec',
                              detail=f'Ollama {version}' if version else 'Ollama ne répond pas sur ' + OLLAMA_URL)
            else:
                if step.get('dossier'):
                    Path(step['dossier']).mkdir(parents=True, exist_ok=True)
                code = run(step['commande'], cwd=ROOT, env=child_env(state, env)).returncode
                record.update(statut='ok' if code == 0 else 'echec', code_retour=code)
                if step['type'] == 'winget':
                    key = step['id'].removesuffix('_installation')
                    found = redetect(key, child_env(state, env))
                    if found:
                        state[key] = str(found)
                        record.update(statut='ok', detail=str(found))  # winget returns non-zero when already installed
                    elif code == 0:
                        record.update(statut='echec', detail='winget a réussi mais l’exécutable reste introuvable : relancer après ouverture d’une nouvelle session.')
                if step['id'] == 'banc':
                    record['rapports'] = [step['commande'][-3], step['commande'][-1]]
        record['duree_s'] = round(time.perf_counter() - began, 1)
        done[step['id']] = record['statut']
        journal.data['etapes'].append(record)
        journal.save()
        out(f'   -> {record["statut"]}' + (f' : {record["detail"]}' if record.get('detail') else ''))
    return journal.data['etapes']


def summary(records):
    remaining = [r for r in records if r['statut'] not in ('ok', 'present')]
    return {'termine': not remaining, 'reste_a_faire': [f'{r["titre"]} ({r["statut"]})' for r in remaining]}


def new_journal_path(home=None, now=None):
    now = now or datetime.now()
    folder = (Path(home) if home else home_dir()) / 'BOJART' / 'installation'
    return folder / f'installation-{now:%Y%m%d-%H%M%S}.json'
