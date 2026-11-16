"""Contrôles statiques du banc de pré-installation BOJ.ART / Jarvis.

Lecture seule : aucun fichier du dépôt n'est modifié, aucun réseau, aucun
périphérique. Chaque contrôle rend une liste de constats normalisés
``{check, severity, path, detail, fix}``. Les sévérités sont :

- ``bloquant`` : empêchera une fonction de marcher sur la tour ;
- ``majeur`` : corruption ou comportement faux probable dans un cas réaliste ;
- ``mineur`` : risque latent ou dette ; ne casse rien aujourd'hui ;
- ``info`` : observation utile, sans défaut.
"""
from __future__ import annotations

import ast
from fnmatch import fnmatchcase
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'data/catalog/repository_manifest.json'

WINDOWS_RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
WINDOWS_INVALID = set('<>:"|?*') | {chr(i) for i in range(32)}
# Racine réaliste sur la tour : C:\Users\<nom>\Documents\BOJART\ (~45 caractères).
WINDOWS_ROOT_ALLOWANCE = 60
WINDOWS_MAX_PATH = 260
TEXT_SUFFIXES = {'.py', '.js', '.cjs', '.mjs', '.html', '.css', '.json', '.jsonl', '.md', '.txt', '.cmd', '.sh', '.yml', '.yaml', '.ini', '.toml'}


def finding(check, severity, path, detail, fix=''):
    return {'check': check, 'severity': severity, 'path': path, 'detail': detail, 'fix': fix}


def manifest_files(root=ROOT):
    """Public tree as published: every path of the repository manifest, plus the manifest itself."""
    data = json.loads((Path(root) / MANIFEST).read_text(encoding='utf-8'))
    return sorted({f['path'] for f in data['files']} | {MANIFEST})


def tracked_files(root=ROOT):
    """Files of the repository. Git when this folder is a checkout; otherwise the published manifest.

    The tower may receive Jarvis as « Code → Download ZIP » or have no Git installed: the bench must
    still examine the same files instead of stopping the installation.
    """
    try:
        out = subprocess.run(['git', 'ls-files', '-z'], cwd=root, capture_output=True, check=True).stdout
        files = sorted(x for x in out.decode('utf-8').split('\0') if x)
    except (OSError, subprocess.CalledProcessError):
        files = []
    return files or manifest_files(root)


def _read(root, name):
    try:
        return (Path(root) / name).read_bytes()
    except OSError:
        return None


# --- Chemins Windows ---------------------------------------------------------

def check_windows_paths(files):
    out = []
    lowered = {}
    for name in files:
        parts = PurePosixPath(name).parts
        for part in parts:
            stem = part.split('.')[0].upper()
            if stem in WINDOWS_RESERVED:
                out.append(finding('chemins_windows', 'bloquant', name, f'Nom réservé Windows : {part}', 'Renommer le fichier.'))
            if any(c in WINDOWS_INVALID for c in part):
                out.append(finding('chemins_windows', 'bloquant', name, f'Caractère interdit sous Windows dans « {part} »', 'Renommer le fichier.'))
            if part.endswith(('.', ' ')):
                out.append(finding('chemins_windows', 'bloquant', name, f'Nom terminé par un point ou une espace : « {part} »', 'Renommer le fichier.'))
        key = name.casefold()
        if key in lowered and lowered[key] != name:
            out.append(finding('chemins_windows', 'bloquant', name, f'Collision de casse avec {lowered[key]}', 'Renommer l’un des deux fichiers.'))
        lowered.setdefault(key, name)
        if len(name) + WINDOWS_ROOT_ALLOWANCE > WINDOWS_MAX_PATH:
            out.append(finding('chemins_windows', 'majeur', name,
                               f'{len(name)} caractères : dépasse 260 avec une racine type C:\\Users\\…\\Documents\\BOJART',
                               'Raccourcir le chemin ou activer LongPathsEnabled et git core.longpaths.'))
    return out


# --- Scripts Windows ---------------------------------------------------------

def check_cmd_scripts(files, root=ROOT):
    out = []
    for name in files:
        if not name.lower().endswith(('.cmd', '.bat')):
            continue
        raw = _read(root, name)
        if raw is None:
            continue
        lines = raw.split(b'\n')
        lf_only = any(not line.endswith(b'\r') for line in lines[:-1])
        has_labels = any(line.lstrip().startswith(b':') and not line.lstrip().startswith(b'::') for line in lines)
        if lf_only:
            severity = 'majeur' if has_labels else 'mineur'
            out.append(finding('scripts_cmd', severity, name,
                               'Fins de ligne LF seules' + (' avec étiquettes goto/call : cmd.exe peut ne pas trouver une étiquette selon sa position (lecture par blocs de 512 octets).' if has_labels else '.'),
                               'Enregistrer le script en CRLF (le dépôt conserve les octets exacts : * -text).'))
        if any(b > 127 for b in raw):
            out.append(finding('scripts_cmd', 'majeur', name, 'Caractères non ASCII : affichage et chemins dépendent de la page de code de la console.',
                               'Garder les .cmd en ASCII.'))
        text = raw.decode('utf-8', 'replace').lower()
        runs_python = re.search(r'(^|[\s"\\])(py(\.exe)?\s+-3|python(\.exe)?\b|\.venv\\scripts\\python)', text, re.M)
        if runs_python and 'pythonutf8=1' not in text.replace(' ', ''):
            out.append(finding('scripts_cmd', 'majeur', name,
                               'Lance Python sans PYTHONUTF8=1 : sous Windows, les lectures de texte sans encodage explicite utilisent cp1252.',
                               'Ajouter « set PYTHONUTF8=1 » comme les autres lanceurs.'))
    return out


# --- Python ------------------------------------------------------------------

def check_python_syntax(files, root=ROOT):
    out = []
    for name in files:
        if not name.endswith('.py'):
            continue
        raw = _read(root, name)
        try:
            compile(raw, name, 'exec', dont_inherit=True)
        except (SyntaxError, ValueError) as exc:
            out.append(finding('python_syntaxe', 'bloquant', name, f'{type(exc).__name__}: {exc}', 'Corriger la syntaxe.'))
    return out


def _text_io_calls(tree):
    """Text-mode I/O whose encoding depends on the Windows locale (cp1252)."""
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        keywords = {k.arg for k in node.keywords}
        if 'encoding' in keywords:
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ''
        if name in {'read_text', 'write_text'}:
            # Path.read_text(encoding) can also be passed positionally.
            if name == 'read_text' and node.args:
                continue
            if name == 'write_text' and len(node.args) >= 2:
                continue
            hits.append((node.lineno, name + '()'))
        elif name == 'open' and isinstance(func, ast.Name):
            mode = None
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for k in node.keywords:
                if k.arg == 'mode' and isinstance(k.value, ast.Constant):
                    mode = k.value.value
            if len(node.args) >= 4:  # encoding passed positionally
                continue
            if isinstance(mode, str) and 'b' in mode:
                continue
            if mode is None and (len(node.args) >= 2 or 'mode' in keywords):
                continue  # mode is dynamic: cannot decide statically
            hits.append((node.lineno, 'open()'))
        elif name in {'run', 'check_output', 'Popen'} and isinstance(func, ast.Attribute):
            text_mode = any(k.arg in {'text', 'universal_newlines'} and isinstance(k.value, ast.Constant) and k.value.value for k in node.keywords)
            if text_mode:
                hits.append((node.lineno, f'subprocess.{name}(text=True)'))
    return sorted(hits)


def check_python_text_io(files, root=ROOT, runtime_prefixes=('bojart_memory/', 'bojart_ops/', 'tools/', 'jarvis/apps/jarvis/app/', 'jarvis/tools/', 'jarvis/knowledge/metier/app/', 'jarvis/labs/', 'productions/')):
    out = []
    for name in files:
        if not name.endswith('.py'):
            continue
        is_test = '/tests' in '/' + name or name.startswith('tests') or PurePosixPath(name).name.startswith('test_')
        if not is_test and not name.startswith(runtime_prefixes):
            continue
        raw = _read(root, name)
        try:
            tree = ast.parse(raw, name)
        except SyntaxError:
            continue
        hits = _text_io_calls(tree)
        if not hits:
            continue
        lines = ', '.join(f'{line} {kind}' for line, kind in hits[:8]) + (' …' if len(hits) > 8 else '')
        live = name.startswith(('bojart_memory/', 'bojart_ops/', 'tools/', 'jarvis/apps/jarvis/app/'))
        out.append(finding('python_encodage', 'majeur' if live and not is_test else 'mineur', name,
                           f'{len(hits)} lecture(s)/écriture(s) texte sans encodage explicite (lignes {lines}). '
                           'Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError.',
                           'Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs.'))
    return out


# --- JSON --------------------------------------------------------------------

def _strict_pairs(items):
    seen = {}
    for key, value in items:
        if key in seen:
            raise ValueError(f'clé dupliquée {key!r}')
        seen[key] = value
    return seen


def _no_constant(value):
    raise ValueError(f'nombre non fini {value}')


def check_json(files, root=ROOT):
    out = []
    for name in files:
        lower = name.lower()
        if not lower.endswith(('.json', '.jsonl')):
            continue
        raw = _read(root, name)
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            out.append(finding('json', 'majeur', name, f'Non UTF-8 : {exc}', 'Réencoder en UTF-8.'))
            continue
        if text.startswith('\ufeff'):
            out.append(finding('json', 'majeur', name, 'BOM UTF-8 en tête : json.loads le refuse.', 'Retirer le BOM.'))
            continue
        docs = [(1, text)] if lower.endswith('.json') else [(i, line) for i, line in enumerate(text.splitlines(), 1) if line.strip()]
        for line_no, doc in docs:
            try:
                json.loads(doc, object_pairs_hook=_strict_pairs, parse_constant=_no_constant)
            except ValueError as exc:
                out.append(finding('json', 'majeur', name, f'ligne {line_no} : {exc}', 'Corriger ou régénérer le fichier.'))
                break
    return out


# --- JavaScript et HTML ---------------------------------------------------------

IMPORT_RE = re.compile(r'''(?:^|[;\s}])(?:import|export)\s[^'";]*?from\s*['"]([^'"]+)['"]|(?:^|[;\s(=,])import\s*\(\s*['"]([^'"]+)['"]\s*\)|^\s*import\s*['"]([^'"]+)['"]''', re.M)
IMPORTMAP_RE = re.compile(r'<script[^>]*type=["\']importmap["\'][^>]*>(.*?)</script>', re.S | re.I)
HTML_REF_RE = re.compile(r'''<(?:script|img|link|source|video|audio|iframe)\b[^>]*?\s(?:src|href)\s*=\s*["']([^"'#?]+)''', re.I)
CSS_URL_RE = re.compile(r'''url\(\s*['"]?([^'")#?]+)''', re.I)


def _strip_js_comments(text):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    return re.sub(r'(^|[^:\\])//[^\n]*', r'\1', text)


def _gitignore_rules(root, files):
    """(base folder, pattern, negated, folder only, anchored) for each published .gitignore line, in Git order."""
    rules = []
    for name in sorted((f for f in files if PurePosixPath(f).name == '.gitignore'), key=lambda f: (f.count('/'), f)):
        raw = _read(root, name)
        if raw is None:
            continue
        base = str(PurePosixPath(name).parent)
        base = '' if base == '.' else base
        for line in raw.decode('utf-8', 'replace').splitlines():
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            negated = line.startswith('!')
            pattern = line[1:] if negated else line
            folder_only = pattern.endswith('/')
            anchored = pattern.startswith('/') or '/' in pattern.strip('/')
            rules.append((base, pattern.strip('/'), negated, folder_only, anchored))
    return rules


def _ignored_by_rules(path, rules):
    """Subset of .gitignore semantics used by this repository: globs, anchors, folders, negation; last rule wins."""
    parts = PurePosixPath(path).parts
    ignored = False
    for base, pattern, negated, folder_only, anchored in rules:
        prefix = PurePosixPath(base).parts if base else ()
        if parts[:len(prefix)] != prefix:
            continue
        rel = parts[len(prefix):]
        for i in range(1, len(rel) + 1):
            is_folder = i < len(rel)  # every parent folder, then the file itself
            if folder_only and not is_folder:
                continue
            if fnmatchcase('/'.join(rel[:i]) if anchored else rel[i - 1], pattern):
                ignored = not negated
                break
    return ignored


def _gitignored(root, paths, files=None):
    if not paths:
        return set()
    try:
        proc = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin', '-z'], cwd=root,
                              input='\0'.join(paths).encode('utf-8'), capture_output=True)
        if proc.returncode in (0, 1):  # 1: nothing ignored; 128: not a Git checkout (ZIP copy)
            return {x for x in proc.stdout.decode('utf-8').split('\0') if x}
    except OSError:
        pass  # Git absent from the tower
    rules = _gitignore_rules(root, files if files is not None else manifest_files(root))
    return {p for p in paths if _ignored_by_rules(p, rules)}


def _site_root(name, files_set):
    """Folder served at '/' for absolute URLs: nearest ancestor containing index.html."""
    parent = PurePosixPath(name).parent
    while True:
        if str(parent / 'index.html') in files_set or parent == PurePosixPath('.'):
            return parent
        parent = parent.parent


def check_web_references(files, root=ROOT):
    """Relative ES-module imports and local HTML/CSS references must exist."""
    out = []
    files_set = set(files)
    missing = []  # (source, target, kind)
    import_maps = {}
    for name in files:
        if name.lower().endswith('.html'):
            raw = (_read(root, name) or b'').decode('utf-8', 'replace')
            for block in IMPORTMAP_RE.findall(raw):
                try:
                    # Import-map URLs resolve against the document, not the importing module.
                    base_dir = PurePosixPath(name).parent
                    import_maps.update({k: (base_dir, v) for k, v in json.loads(block).get('imports', {}).items()})
                except ValueError:
                    out.append(finding('web_references', 'majeur', name, 'importmap illisible', 'Corriger le JSON de l’importmap.'))
    for name in files:
        lower = name.lower()
        if not lower.endswith(('.js', '.mjs', '.html', '.css')) or '/node_modules/' in name:
            continue
        raw = (_read(root, name) or b'').decode('utf-8', 'replace')
        base = PurePosixPath(name).parent
        refs = []
        if lower.endswith(('.js', '.mjs')):
            for groups in IMPORT_RE.findall(_strip_js_comments(raw)):
                refs += [(g, 'import') for g in groups if g]
        if lower.endswith('.html'):
            refs += [(r, 'html') for r in HTML_REF_RE.findall(raw)]
            for block in re.findall(r'<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>', raw, re.S | re.I):
                refs += [(g, 'import') for groups in IMPORT_RE.findall(_strip_js_comments(block)) for g in groups if g]
        if lower.endswith('.css'):
            refs += [(r, 'css') for r in CSS_URL_RE.findall(raw)]
        for ref, kind in refs:
            ref = ref.strip()
            base = PurePosixPath(name).parent
            if not ref or re.match(r'^(?:[a-z][a-z0-9+.-]*:|//|\$\{|data:|#)', ref, re.I) or '${' in ref or '{{' in ref:
                continue
            if kind == 'import' and not ref.startswith(('.', '/')):
                mapped = import_maps.get(ref)
                if mapped is None:
                    continue  # bare specifier resolved by a bundler / node
                base, ref = mapped
                if re.match(r'^(?:[a-z][a-z0-9+.-]*:|//)', ref, re.I):
                    continue
            if ref.startswith('/'):
                target = _site_root(name, files_set) / ref.lstrip('/')
            else:
                target = base / ref
            parts = []
            for part in target.parts:
                if part == '..':
                    if parts:
                        parts.pop()
                elif part != '.':
                    parts.append(part)
            resolved = '/'.join(parts)
            if resolved in files_set or (Path(root) / resolved).is_dir():
                continue
            missing.append((name, resolved, kind, ref))
    ignored = _gitignored(root, sorted({m[1] for m in missing}), files)
    for source, target, kind, ref in missing:
        if target in ignored:
            item = finding('web_references', 'majeur', source,
                           f'« {ref} » absent du dépôt (exclu par .gitignore : média à hydrater sur la tour).',
                           'Fournir le média ou un repli explicite ; vérifier le rendu après hydratation.')
            item['precondition'] = True  # policy keeps media out of Git: not a code defect
            out.append(item)
        else:
            severity = 'bloquant' if kind == 'import' else 'majeur'
            out.append(finding('web_references', severity, source, f'« {ref} » introuvable ({target}).',
                               'Restaurer le fichier référencé ou corriger le chemin.'))
    return out


def check_js_syntax(files, root=ROOT, node='node'):
    out = []
    targets = [n for n in files if n.lower().endswith(('.js', '.mjs', '.cjs')) and '/node_modules/' not in n]
    for name in targets:
        try:
            proc = subprocess.run([node, '--check', str(Path(root) / name)], capture_output=True, timeout=60)
        except FileNotFoundError:
            return [finding('js_syntaxe', 'info', '', 'Node.js absent : contrôle de syntaxe JavaScript non exécuté.', 'Installer Node.js 22.')]
        if proc.returncode:
            msg = proc.stderr.decode('utf-8', 'replace').strip().splitlines()
            out.append(finding('js_syntaxe', 'bloquant', name, ' | '.join(msg[-3:])[:400], 'Corriger la syntaxe.'))
    return out


# --- Provenance des dépendances embarquées ------------------------------------------

def check_vendor_provenance(files, root=ROOT):
    out = []
    for name in files:
        if not name.endswith('THREE-PROVENANCE.json'):
            continue
        data = json.loads(_read(root, name))
        base = PurePosixPath(name).parent
        for entry in data.get('files', []):
            path = Path(root) / base / entry['path']
            if not path.is_file():
                out.append(finding('provenance_vendor', 'bloquant', str(base / entry['path']), 'Fichier tiers déclaré mais absent.', 'Restaurer depuis la source épinglée.'))
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != entry['sha256']:
                out.append(finding('provenance_vendor', 'majeur', str(base / entry['path']), 'Empreinte différente de la provenance épinglée.', 'Restaurer l’octet exact amont.'))
    return out


# --- Épinglages de dépendances -----------------------------------------------------

REQ_LINE = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*==\s*([^\s;#]+)')


def check_requirement_pins(files, root=ROOT):
    """The tower installs every Jarvis requirement file into one environment: pins must agree."""
    pins = {}
    for name in files:
        base = PurePosixPath(name).name
        if not (base.startswith('requirements') and base.endswith('.txt')) or name.startswith(('archive/', 'docs/')):
            continue
        for line in (_read(root, name) or b'').decode('utf-8', 'replace').splitlines():
            m = REQ_LINE.match(line)
            if m:
                key = re.sub(r'[-_.]+', '-', m.group(1)).lower()
                pins.setdefault(key, {}).setdefault(m.group(2), []).append(name)
    out = []
    for package, versions in sorted(pins.items()):
        if len(versions) > 1:
            detail = ' ; '.join(f'{v} dans {", ".join(sorted(set(f)))}' for v, f in sorted(versions.items()))
            out.append(finding('dependances_epinglees', 'majeur', package, f'Versions épinglées contradictoires : {detail}.',
                               'Aligner la version ou séparer explicitement les environnements.'))
    return out


def check_install_lock(files, root=ROOT):
    """The tower must install the exact environment the bench tested: hashed Windows lock, up to date with the requirements."""
    from bojart_ops import verrou_dependances
    if not (Path(root) / 'jarvis').is_dir():
        return []
    return [finding('verrou_installation', p['gravite'], p['verrou'], p['detail'],
                    'Regénérer sous Windows : python tools/verrouiller_dependances.py --sortie <dossier neuf> (workflow du banc).')
            for p in verrou_dependances.verify(Path(root), 'windows')]


CHECKS = {
    'dependances_epinglees': check_requirement_pins,
    'verrou_installation': check_install_lock,
    'chemins_windows': lambda files, root: check_windows_paths(files),
    'scripts_cmd': check_cmd_scripts,
    'python_syntaxe': check_python_syntax,
    'python_encodage': check_python_text_io,
    'json': check_json,
    'web_references': check_web_references,
    'js_syntaxe': check_js_syntax,
    'provenance_vendor': check_vendor_provenance,
}


def run_static(root=ROOT, only=None):
    files = tracked_files(root)
    results = {}
    for name, fn in CHECKS.items():
        if only and name not in only:
            continue
        found = fn(files, root)
        serious = [f for f in found if f['severity'] in {'bloquant', 'majeur'}]
        defects = [f for f in serious if not f.get('precondition')]
        status = 'echec' if defects else 'partiel' if serious else 'ok'
        results[name] = {'status': status, 'findings': found, 'files_examined': len(files)}
    return results
