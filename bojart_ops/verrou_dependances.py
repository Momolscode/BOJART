"""Verrous d'installation de Jarvis : versions exactes et empreintes de chaque roue.

Un verrou fige tout l'environnement d'un profil (dépendances indirectes comprises) pour une
plateforme. La tour installe alors exactement ce que le banc a testé :

    python -m pip install --require-hashes --no-deps -r jarvis/locks/windows-cp312-moteurs.txt
    python -m pip check

Les verrous Windows se génèrent sous Windows (CI du banc) : les marqueurs d'environnement
(`sys_platform == "win32"`) sont évalués par pip sur la plateforme qui résout, pas sur la cible.
"""
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JARVIS = ROOT / 'jarvis'
LOCKS = JARVIS / 'locks'
EXCLUDED = {'requirements-tests.txt'}
PIN = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*([^\s;#]+)')
INCLUDE = re.compile(r'^\s*-r\s+(\S+)')
ENTRY = re.compile(r'^([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+)')
HASH = re.compile(r'--hash=sha256:([0-9a-f]{64})')
SOURCE = re.compile(r'^# source (\S+) sha256=([0-9a-f]{64})$')


def canonical(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def platform_tag():
    return 'windows' if os.name == 'nt' else sys.platform


def lock_path(profile, tag=None, root=ROOT):
    return root / 'jarvis/locks' / f'{tag or platform_tag()}-cp312-{profile}.txt'


def requirement_closure(path, seen=None):
    """A requirement file and every file it includes with -r, relative to the jarvis folder."""
    seen = [] if seen is None else seen
    path = Path(path)
    if path in seen:
        return seen
    seen.append(path)
    for line in path.read_text(encoding='utf-8').splitlines():
        m = INCLUDE.match(line)
        if m:
            requirement_closure(path.parent / m.group(1), seen)
    return seen


def profiles(root=ROOT):
    """Top-level requirement files: every jarvis/requirements*.txt not included by another one (tests excluded)."""
    jarvis = root / 'jarvis'
    files = sorted(p for p in jarvis.glob('requirements*.txt') if p.name not in EXCLUDED)
    included = {f.resolve() for p in files for f in requirement_closure(p)[1:]}
    out = {}
    for p in files:
        if p.resolve() in included:
            continue
        name = 'moteurs' if p.name == 'requirements.txt' else p.stem.removeprefix('requirements-')
        out[name] = p
    return out


def top_level_pins(path):
    pins = {}
    for f in requirement_closure(path):
        for line in f.read_text(encoding='utf-8').splitlines():
            m = PIN.match(line)
            if m:
                pins[canonical(m.group(1))] = m.group(2)
    return pins


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path, root=ROOT):
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def parse_lock(path):
    text = Path(path).read_text(encoding='utf-8')
    sources, entries, current = {}, {}, None
    for raw in text.splitlines():
        line = raw.strip()
        m = SOURCE.match(line)
        if m:
            sources[m.group(1)] = m.group(2)
            continue
        if not line or line.startswith('#'):
            continue
        m = ENTRY.match(line)
        if m:
            current = canonical(m.group(1))
            entries[current] = {'version': m.group(2), 'hashes': []}
        if current:
            entries[current]['hashes'] += HASH.findall(line)
        if not line.endswith('\\'):
            current = None
    return sources, entries


def verify(root=ROOT, tag='windows'):
    """Offline consistency of the committed locks with the requirement files. Returns a list of problems."""
    problems = []
    for name, req in profiles(root).items():
        path = lock_path(name, tag, root)
        label = rel(path, root)
        if not path.exists():
            problems.append({'verrou': label, 'gravite': 'majeur', 'detail': f'Aucun verrou {tag} pour le profil « {name} » ({rel(req, root)}).'})
            continue
        sources, entries = parse_lock(path)
        expected = {rel(f, root): sha256_file(f) for f in requirement_closure(req)}
        stale = sorted(f for f, digest in expected.items() if sources.get(f) != digest)
        if stale or set(sources) != set(expected):
            problems.append({'verrou': label, 'gravite': 'majeur',
                             'detail': 'Verrou périmé : ' + ', '.join(stale or sorted(set(sources) ^ set(expected))) + ' a changé depuis sa génération.'})
        for pkg, version in sorted(top_level_pins(req).items()):
            got = entries.get(pkg)
            if not got or got['version'] != version:
                problems.append({'verrou': label, 'gravite': 'majeur',
                                 'detail': f'{pkg}=={version} épinglé mais {"absent du verrou" if not got else "verrouillé en " + got["version"]}.'})
        missing = sorted(p for p, e in entries.items() if not e['hashes'])
        if missing:
            problems.append({'verrou': label, 'gravite': 'majeur', 'detail': 'Sans empreinte : ' + ', '.join(missing) + '.'})
    return problems


# --- Génération (réseau : index PyPI) -------------------------------------------------

def _resolve(python, requirement_args, constraints=None, cwd=JARVIS):
    with tempfile.TemporaryDirectory(prefix='bojart-verrou-') as tmp:
        report = Path(tmp) / 'report.json'
        args = [python, '-m', 'pip', 'install', '--dry-run', '--ignore-installed', '--quiet', '--only-binary=:all:',
                '--report', str(report)]
        if constraints:
            cfile = Path(tmp) / 'c.txt'
            cfile.write_text(''.join(f'{n}=={v}\n' for n, v in sorted(constraints.items())), encoding='utf-8', newline='\n')
            args += ['-c', str(cfile)]
        args += requirement_args
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if proc.returncode:
            raise RuntimeError('Résolution impossible : ' + proc.stderr.strip()[-800:])
        data = json.loads(report.read_text(encoding='utf-8'))
    items = {}
    for item in data['install']:
        info = item['download_info']
        url = info['url']
        hashes = (info.get('archive_info') or {}).get('hashes') or {}
        digest = hashes.get('sha256') or ((info.get('archive_info') or {}).get('hash') or '').removeprefix('sha256=')
        items[canonical(item['metadata']['name'])] = {'name': item['metadata']['name'], 'version': item['metadata']['version'],
                                                       'file': url.rsplit('/', 1)[-1], 'sha256': digest}
    return items


def generate(output_dir, python=sys.executable, root=ROOT, today=None):
    """Resolve every profile together on this platform, then write one hashed lock per profile."""
    if sys.version_info[:2] != (3, 12):
        raise SystemExit('Générer les verrous avec Python 3.12, comme sur la tour.')
    jarvis = root / 'jarvis'
    profs = profiles(root)
    combined = _resolve(python, [a for p in profs.values() for a in ('-r', str(p))], cwd=jarvis)
    pins = {k: v['version'] for k, v in combined.items()}
    pip_version = subprocess.run([python, '-m', 'pip', '--version'], capture_output=True, text=True,
                                 encoding='utf-8', errors='replace').stdout.split()[1]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, req in profs.items():
        items = _resolve(python, ['-r', str(req)], constraints=pins, cwd=jarvis)
        bad = sorted(i['file'] for i in items.values() if not i['file'].endswith('.whl') or not re.fullmatch(r'[0-9a-f]{64}', i['sha256']))
        if bad:
            raise RuntimeError('Roue ou empreinte manquante : ' + ', '.join(bad))
        lines = [f'# Verrou BOJ.ART, profil « {name} » : généré par tools/verrouiller_dependances.py, ne pas éditer.',
                 f'# plateforme {platform.system()} {platform.machine()} ; Python {platform.python_version()} ; pip {pip_version} ; '
                 f'date {today or __import__("datetime").date.today().isoformat()}',
                 '# Installer : python -m pip install --require-hashes --no-deps -r <ce fichier> puis python -m pip check']
        lines += [f'# source {rel(f, root)} sha256={sha256_file(f)}' for f in requirement_closure(req)]
        for key in sorted(items):
            i = items[key]
            lines.append(f'{i["name"]}=={i["version"]} \\\n    --hash=sha256:{i["sha256"]}')
        target = output_dir / lock_path(name, root=root).name
        target.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        written.append({'profil': name, 'fichier': target.name, 'paquets': len(items)})
    return {'plateforme': platform_tag(), 'paquets_total': len(combined), 'verrous': written}


def drift(generated_dir, root=ROOT):
    """Compare a fresh resolution with the committed locks: versions that moved on the index since the lock."""
    out = []
    for path in sorted(Path(generated_dir).glob('*.txt')):
        committed = root / 'jarvis/locks' / path.name
        if not committed.exists():
            out.append({'verrou': path.name, 'detail': 'pas de verrou validé dans le dépôt'})
            continue
        _, fresh = parse_lock(path)
        _, held = parse_lock(committed)
        moved = sorted(f'{k} {held[k]["version"]}→{fresh[k]["version"]}' for k in fresh.keys() & held.keys()
                       if fresh[k]['version'] != held[k]['version'])
        added, gone = sorted(fresh.keys() - held.keys()), sorted(held.keys() - fresh.keys())
        if moved or added or gone:
            out.append({'verrou': path.name, 'versions_changees': moved, 'ajoutes': added, 'retires': gone})
    return out
