"""Débrief de la tour vers GitHub : Jarvis pousse ses propres rapports, et rien d'autre.

Après une installation ou une séance d'essais, les rapports écrits par Jarvis dans ``~/BOJART``
(journal d'installation, banc de contrôle, mesures de la voix, diagnostic du poste) sont réunis
dans un dossier ``docs/evidence/tour-AAAA-MM-JJ-HHMMSS/`` et poussés sur une branche neuve
``tour/debrief-AAAAMMJJ-HHMMSS`` du dépôt approuvé. Les fils de travail peuvent alors les lire et
mettre à jour le contexte sans que personne ne recopie un rapport à la main.

Le dépôt est public. Garde-fous, vérifiés par ``tests_ops/test_debrief_tour.py`` et par l'essai de bout en bout
``tools/publier_debrief.py essai`` que le banc lance :

- seuls des rapports texte (.json, .md, .txt) de moins de 1 Mo partent ; jamais un média, une base,
  un fichier de configuration ni un dossier choisi librement ;
- le dossier personnel, le dossier d'installation, le nom de session Windows, le nom du poste et les
  adresses de courriel sont retirés avant la copie ;
- le contrôle du dépôt (``tools/validate_repository.py`` : secrets, binaires, tailles) doit passer sur
  l'arbre préparé, sinon rien n'est créé ;
- la destination est le dépôt approuvé et lui seul, sur une branche ``tour/debrief-…`` neuve :
  jamais ``main``, jamais une branche existante, jamais de poussée forcée ;
- la copie de travail de la tour n'est pas touchée : tout se passe dans un arbre temporaire ;
- l'identité Git du poste n'est pas publiée : les commits sont signés « Jarvis BOJ.ART (tour) » ;
- aucun jeton n'est lu ni stocké : la connexion à GitHub est celle de Git sur la tour.

Une commande vocale ne peut pas déclencher cette poussée : elle passe par le lanceur
``Publier_Debrief_BOJART.cmd``, qui montre ce qui part et demande l'accord.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

from bojart_ops.installation_tout import find_git, home_dir  # noqa: F401  (find_git is part of this module's interface)

ROOT = Path(__file__).resolve().parents[1]
APPROVED = 'github.com/momolscode/bojart'  # AGENTS.md: the approved destination
REMOTE_URL = 'https://github.com/Momolscode/BOJART.git'
WEB_URL = 'https://github.com/Momolscode/BOJART'
BRANCH = re.compile(r'^tour/debrief-\d{8}-\d{6}$')
MANIFEST = 'data/catalog/repository_manifest.json'
MAX_BYTES = 1_000_000  # same limit as tools/validate_repository.py
SUFFIXES = ('.json', '.md', '.txt')
IDENTITY = ('Jarvis BOJ.ART (tour)', 'jarvis@tour.invalid')  # reserved domain: maps to no account
# Reports Jarvis writes under ~/BOJART: (folder, number of most recent runs kept).
FAMILIES = {
    'installation': ('installation', 1),
    'banc': ('banc', 1),
    'voix': ('banc-voix/rapports', 2),  # the measurement and the noise-only probe
    'mesures': ('benchmarks', 1),
    'diagnostic': ('diagnostics', 1),
}
DEFAULT_FAMILIES = ('installation', 'banc', 'voix', 'mesures')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}')


class Refused(Exception):
    """Nothing was pushed; the message says why."""


# --- What leaves the tower ----------------------------------------------------

def collect(home=None, families=DEFAULT_FAMILIES):
    """Most recent reports of each family. Returns (kept, set_aside); nothing is read yet."""
    base = (Path(home) if home else home_dir()) / 'BOJART'
    kept, aside = [], []
    for family in families:
        folder, runs = FAMILIES[family]
        files = [p for p in sorted((base / folder).glob('*')) if p.is_file() or p.is_symlink()]
        stems = sorted({p.stem for p in files}, key=lambda s: max(p.lstat().st_mtime for p in files if p.stem == s), reverse=True)[:runs]
        for path in files:
            if path.stem not in stems:
                continue
            if path.is_symlink():
                aside.append({'fichier': path.name, 'raison': 'lien symbolique'})
            elif path.suffix.lower() not in SUFFIXES:
                aside.append({'fichier': path.name, 'raison': 'type non autorisé (seuls .json, .md et .txt partent)'})
            elif path.stat().st_size > MAX_BYTES:
                aside.append({'fichier': path.name, 'raison': f'plus de {MAX_BYTES // 1000} ko'})
            else:
                kept.append({'famille': family, 'source': path, 'nom': path.name, 'octets': path.stat().st_size})
    return kept, aside


def _spellings(path):
    """A path as tools write it: native, with slashes, and with the doubled backslashes of JSON."""
    path = str(path)
    found = {path, path.replace('\\', '/'), path.replace('\\', '\\\\'), path.replace('/', '\\'), path.replace('/', '\\\\')}
    return sorted((v for v in found if len(v) > 3), key=len, reverse=True)


def sanitize(text, home=None, env=None, node=None, root=ROOT):
    """Remove what names the Windows account, the machine or the place of the installation. Returns (text, replacements)."""
    env = os.environ if env is None else env
    count = 0
    home = home if home else home_dir(env)
    # The installation folder first: it can sit anywhere (« D:\\Prénom\\BOJART ») and says nothing about a result.
    for path, mark in ((root, '<projet>'), (home, '~')):
        for variant in _spellings(path):
            text, n = re.subn(re.escape(variant) + r'(?![\w-])', lambda _: mark, text)
            count += n
    user = env.get('USERNAME') or env.get('USER') or ''
    if len(user) >= 2:  # what is left of the account name sits in other profile paths (« Users\\name-old », « name.POSTE »)
        text, n = re.subn(r'(?i)((?:users|home|utilisateurs)(?:\\\\|[\\/]))' + re.escape(user) + r'(?!\w)', r'\1<session>', text)
        count += n
    node = platform.node() if node is None else node
    for name in {node, env.get('COMPUTERNAME') or ''}:
        if len(name) >= 4:
            text, n = re.subn(r'(?i)(?<![\w.-])' + re.escape(name) + r'(?![\w-])', '<poste>', text)
            count += n
    text, n = EMAIL.subn('<courriel>', text)
    return text, count + n


def _summary(family, name, text):
    """One line per report, read from fields the tools already write. Never fails the publication."""
    try:
        data = json.loads(text) if name.endswith('.json') else None
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    s = data.get('synthese')
    if family == 'installation' and isinstance(s, dict):
        rest = s.get('reste_a_faire') or []
        return 'installation terminée' if s.get('termine') else 'installation incomplète : ' + ' ; '.join(map(str, rest))
    if family == 'banc' and isinstance(s, dict):
        def counts(value):
            return ', '.join(f'{k} {v}' for k, v in value.items() if v) if isinstance(value, dict) and any(value.values()) else 'aucun'
        return (f"{s.get('tests_executes')} tests ; scénarios HTTP : {counts(s.get('scenarios_http'))} ; "
                f"actions : {counts(s.get('actions_par_statut'))} ; constats : {counts(s.get('constats_par_severite'))}")
    if family == 'voix' and isinstance(s, dict) and 'erreurs_critiques' in s:
        return f"erreurs critiques : {s.get('erreurs_critiques')}"
    return None


def prepare(kept, home=None, env=None, node=None, note='', stamp=None, aside=(), root=ROOT):
    """Sanitized copies and their README, in memory: {relative path: text}. Raises Refused when nothing can go."""
    stamp = stamp or datetime.now()
    folder = f'docs/evidence/tour-{stamp:%Y-%m-%d-%H%M%S}'
    out, rows, refused = {}, [], list(aside)
    for item in kept:
        raw = Path(item['source']).read_bytes()
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            refused.append({'fichier': item['nom'], 'raison': 'pas du texte UTF-8'})
            continue
        if '\x00' in text:
            refused.append({'fichier': item['nom'], 'raison': 'contenu binaire'})
            continue
        clean, replaced = sanitize(text.replace('\r\n', '\n'), home, env, node, root)
        out[f'{folder}/{item["famille"]}/{item["nom"]}'] = clean
        rows.append((item['famille'], item['nom'], len(clean.encode('utf-8')), hashlib.sha256(raw).hexdigest(), replaced,
                     _summary(item['famille'], item['nom'], clean)))
    if not out:
        raise Refused('Aucun rapport à publier : lancer d’abord l’installateur, le banc ou la mesure de la voix.')
    note, _ = sanitize(' '.join(str(note).split()), home, env, node, root)
    lines = [f'# Débrief de la tour — {stamp:%Y-%m-%d %H:%M}', '',
             'Poussé depuis la tour par `tools/publier_debrief.py`. Ce sont les rapports écrits par Jarvis, tels quels, après '
             'retrait du dossier personnel, du dossier d’installation, du nom de session, du nom du poste et des adresses de courriel. '
             'Aucun média, aucune base, aucune donnée client. Ce dossier décrit ce que la tour a mesuré ; il ne vaut ni '
             'réception, ni décision.', '']
    if note:
        lines += [f'Note de l’opérateur : {note}', '']
    lines += ['| Famille | Fichier | Octets publiés | SHA-256 de l’original sur la tour | Retraits |', '|---|---|---:|---|---:|']
    lines += [f'| {f} | `{f}/{n}` | {size} | `{digest}` | {replaced} |' for f, n, size, digest, replaced, _ in rows]
    summaries = [f'- `{f}/{n}` : {summary}' for f, n, _, _, _, summary in rows if summary]
    if summaries:
        lines += ['', '## Ce que disent les rapports', ''] + summaries
    if refused:
        lines += ['', '## Laissés sur la tour', ''] + [f'- `{r["fichier"]}` : {r["raison"]}' for r in refused]
    out[f'{folder}/README.md'] = '\n'.join(lines) + '\n'
    return folder, out, refused


# --- Git ----------------------------------------------------------------------

def _git(git, args, cwd, run=subprocess.run, timeout=300, check=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', LC_ALL='C')
    proc = run([str(git), *args], cwd=str(cwd), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, env=env)
    if check and proc.returncode:
        raise Refused(f'git {" ".join(args[:2])} a échoué : ' + (proc.stderr or proc.stdout).strip()[-400:])
    return proc


def approved_url(url, approved=APPROVED):
    """True when a remote URL is the approved repository (https, ssh or scp form; credentials in the URL ignored)."""
    text = str(url).strip()
    if text == approved:
        return True
    m = re.match(r'^(?:https?|ssh)://(?:[^@/]+@)?([^/:]+)(?::\d+)?/(.+)$', text) or re.match(r'^(?:[^@/]+@)?([^:/\\]{2,}):(.+)$', text)
    if not m:
        return False
    return (m.group(1) + '/' + re.sub(r'\.git$', '', m.group(2).rstrip('/'))).lower() == approved.lower()


def find_clone(root=ROOT, home=None, *, git, approved=APPROVED, remote_url=REMOTE_URL, run=subprocess.run, out=print):
    """A clone of the approved repository: the installation folder when it is one, else a dedicated bare clone.

    A « Download ZIP » installation has no .git: a shallow bare clone is kept in ~/BOJART/depot-github.
    """
    if (Path(root) / '.git').exists():
        url = _git(git, ['remote', 'get-url', 'origin'], root, run, check=False)
        if url.returncode == 0 and approved_url(url.stdout, approved):
            return Path(root)
    clone = (Path(home) if home else home_dir()) / 'BOJART' / 'depot-github' / 'BOJART.git'
    if not clone.exists():
        out(f'Copie Git de travail absente : clonage de {remote_url} (une seule fois).')
        clone.parent.mkdir(parents=True, exist_ok=True)
        _git(git, ['clone', '--bare', '--depth', '1', '--single-branch', '--branch', 'main', remote_url, str(clone)], clone.parent, run, timeout=900)
    url = _git(git, ['remote', 'get-url', 'origin'], clone, run)
    if not approved_url(url.stdout, approved):
        raise Refused(f'{clone} ne pointe pas vers le dépôt approuvé : rien n’est poussé.')
    return clone


def default_validate(worktree, python=sys.executable, run=subprocess.run):
    """The repository's own gate, on the prepared tree: manifest regenerated, then secrets, binaries and sizes checked."""
    env = dict(os.environ, PYTHONUTF8='1')
    tool = str(Path(worktree) / 'tools/validate_repository.py')
    wrote = run([python, tool, '--write-manifest'], cwd=str(worktree), capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    proc = run([python, tool], cwd=str(worktree), capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    try:
        issues = json.loads(proc.stdout).get('issues')
    except ValueError:
        issues = [{'error': 'rapport_illisible', 'detail': (proc.stderr or proc.stdout)[-300:]}]
    if wrote.returncode and not issues:
        issues = [{'error': 'manifeste_non_regenere', 'detail': (wrote.stderr or wrote.stdout)[-300:]}]
    return issues or []


def publish(files, folder, *, clone, git, stamp=None, push=True, validate=default_validate, remote='origin', base='main',
            approved=APPROVED, run=subprocess.run, out=print):
    """Commit the prepared files on top of the remote base, in a temporary tree, and push a new tour/debrief branch."""
    stamp = stamp or datetime.now()
    branch = f'tour/debrief-{stamp:%Y%m%d-%H%M%S}'
    if not BRANCH.match(branch) or not folder.startswith('docs/evidence/tour-'):
        raise Refused('Nom de branche ou de dossier inattendu : rien n’est poussé.')
    url = _git(git, ['remote', 'get-url', remote], clone, run).stdout.strip()
    if not approved_url(url, approved):
        raise Refused('Le dépôt distant n’est pas le dépôt approuvé : rien n’est poussé.')
    shallow = _git(git, ['rev-parse', '--is-shallow-repository'], clone, run).stdout.strip() == 'true'
    _git(git, ['fetch', '--no-tags'] + (['--depth', '1'] if shallow else []) + [remote, base], clone, run, timeout=900)
    start = _git(git, ['rev-parse', 'FETCH_HEAD'], clone, run).stdout.strip()
    if _git(git, ['ls-remote', '--exit-code', '--heads', remote, branch], clone, run, check=False).returncode == 0:
        raise Refused(f'La branche {branch} existe déjà sur GitHub : relancer dans une minute.')
    tmp = Path(tempfile.mkdtemp(prefix='bojart-debrief-'))
    tree = tmp / 'arbre'
    try:
        _git(git, ['worktree', 'add', '--detach', str(tree), start], clone, run)
        for rel, text in files.items():
            target = tree / rel
            inside = rel.startswith(folder + '/') and not ({'..', '.', ''} & set(rel.split('/'))) and '\\' not in rel
            if not inside or not target.resolve().is_relative_to(tree.resolve()) or target.exists():
                raise Refused(f'Chemin inattendu ou déjà présent : {rel}')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8', newline='\n')
        issues = validate(tree)
        if issues:
            raise Refused('Le contrôle du dépôt refuse ce débrief : ' + json.dumps(issues[:5], ensure_ascii=False))
        _git(git, ['add', '--', folder, MANIFEST], tree, run)
        changed = [line[3:].strip('"') for line in _git(git, ['status', '--porcelain'], tree, run).stdout.splitlines()]
        stray = [p for p in changed if p != MANIFEST and not p.startswith(folder + '/')]
        if stray:
            raise Refused('Fichiers inattendus dans l’arbre préparé : ' + ', '.join(stray[:5]))
        message = (f'Tower debrief {stamp:%Y-%m-%d %H:%M}: {len(files) - 1} report(s) from Jarvis\n\n'
                   'Pushed by tools/publier_debrief.py. Text reports only, cleared of the home folder,\n'
                   'session name, host name and e-mail addresses. Not a qualification, not a decision.')
        _git(git, ['-c', f'user.name={IDENTITY[0]}', '-c', f'user.email={IDENTITY[1]}', 'commit', '--no-gpg-sign', '-q', '-m', message], tree, run)
        commit = _git(git, ['rev-parse', 'HEAD'], tree, run).stdout.strip()
        result = {'branche': branch, 'dossier': folder, 'commit': commit, 'base': start, 'fichiers': sorted(files),
                  'pousse': False, 'depot': url}
        if push:
            out(f'Poussée de {branch} vers {url} (une fenêtre de connexion GitHub peut s’ouvrir la première fois).')
            _git(git, ['push', remote, f'{commit}:refs/heads/{branch}'], tree, run, timeout=900)  # new branch, never forced
            result.update(pousse=True, voir=f'{WEB_URL}/tree/{branch}/{folder}', proposer=f'{WEB_URL}/compare/{branch}?expand=1')
        return result
    finally:
        _git(git, ['worktree', 'remove', '--force', str(tree)], clone, run, check=False)
        _git(git, ['worktree', 'prune'], clone, run, check=False)
        shutil.rmtree(tmp, ignore_errors=True)
