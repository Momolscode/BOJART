"""Banc de simulation pré-installation BOJ.ART / Jarvis.

Réunit, dans un seul rapport daté et relié à son SHA :

1. les suites de tests existantes, y compris celles du runtime Jarvis (M02–M07)
   qui ne tournent dans aucun workflow CI ;
2. les outils de simulation existants (tours vocaux synthétiques, flotte fictive,
   mémoire, redémarrage brutal, manifeste) ;
3. des contrôles statiques de corruption et de compatibilité Windows ;
4. des scénarios HTTP bout en bout contre le vrai serveur ;
5. une émulation de l'encodage par défaut de Windows (cp1252) sous Linux ;
6. en option, la résolution des roues Windows cp312 des dépendances épinglées.

Puis il évalue chaque action du catalogue ``data/preinstallation/actions-jarvis.json``.
Aucun micro, écran physique, imprimante, modèle ou service payant n'est sollicité.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/preinstallation/actions-jarvis.json'

# id, dossier de tests, motif, domaine, délai (s). Les suites Jarvis M02–M07 ne
# sont exécutées par aucun workflow GitHub au 2026-11-02 : le banc les reprend.
SUITES = [
    ('tests', 'tests', 'test*.py', 'Mémoire, lanceurs, installation', 900, True),
    ('tests_agent', 'tests_agent', 'test*.py', 'Mémoire agent, MCP, modèles simulés', 900, True),
    ('tests_ops', 'tests_ops', 'test*.py', 'Orchestration, préinstallation', 600, True),
    ('tests_workflows', 'tests_workflows', 'test*.py', 'Tours vocaux synthétiques, flotte fictive', 600, True),
    ('jarvis_tests', 'jarvis/tests', 'test*.py', 'Runtime Jarvis M04–M07 (régie, voix, Jev, Studio, Growth)', 900, False),
    ('jarvis_app_tests', 'jarvis/apps/jarvis/tests', 'test*.py', 'CAO M01–M02, interface et navigateur', 900, False),
    ('jarvis_app_tests_m03', 'jarvis/apps/jarvis/tests_m03', 'test*.py', 'Bibliothèque Studio M03', 600, False),
    ('metier', 'jarvis/knowledge/metier/tests', 'test*.py', 'Base métier', 300, False),
]
NODE_TESTS = ['jarvis/tests/voice_endpoint.test.cjs', 'jarvis/tests/memory_context.test.cjs', 'jarvis/tests/studio_growth.test.cjs',
              'jarvis/tests/voice_cancel_generation.test.cjs', 'jarvis/tests/preinstallation_ui.test.cjs']

STUDIO_MEDIA = ROOT / 'jarvis/apps/jarvis/studio_media'
# Échecs dont la cause est une précondition absente, vérifiée à chaque exécution.
# Si la précondition est satisfaite, l'échec redevient une régression.
PRECONDITIONS = [
    {'match': re.compile(r'test_workspace_m05\.WorkspaceTests\.test_(full_snapshot_reopens_with_all_work_and_relative_media|missing_media_makes_check_and_backup_fail)'),
     'cause': 'medias_m07', 'present': lambda: STUDIO_MEDIA.is_dir() and any(STUDIO_MEDIA.iterdir())},
    {'match': re.compile(r'test_growth\.GrowthHTTP\.test_prepare_from_actual_studio'),
     'cause': 'medias_m07', 'present': lambda: STUDIO_MEDIA.is_dir() and any(STUDIO_MEDIA.iterdir())},
    {'match': re.compile(r'setUpClass \(test_studio_http\.HTTPTests\)|test_studio_http'),
     'cause': 'medias_m07', 'present': lambda: STUDIO_MEDIA.is_dir() and any(STUDIO_MEDIA.iterdir())},
    {'match': re.compile(r'(test_browser|test_browser_direct|test_browser_m02|test_preview|test_ui|test_preview_m03|test_studio_browser)\b'),
     'cause': 'navigateur_python', 'present': None},
    {'match': re.compile(r'\btest_m02\b'), 'cause': 'pytest', 'present': None},
]
CAUSES = {
    'medias_m07': 'Médias d’exemple M07 non hydratés (tools/hydrate_m07_media.py avec l’archive M07 vérifiée).',
    'navigateur_python': 'Playwright Python ou Chromium absent ; ces tests visent aussi /usr/bin/chromium, introuvable sous Windows.',
    'pytest': 'pytest absent de l’interpréteur (jarvis/requirements-tests.txt).',
}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def git(*args):
    try:
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def repo_state(root=ROOT):
    """Revision of the tested tree. A copy without Git (Download ZIP) is named by the digest of its
    manifest, the same digest as the installation journal."""
    sha = git('rev-parse', 'HEAD')
    if sha:
        return {'sha': sha, 'branche': git('rev-parse', '--abbrev-ref', 'HEAD'), 'modifications_locales': bool(git('status', '--porcelain'))}
    manifest = Path(root) / 'data/catalog/repository_manifest.json'
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None
    return {'sha': None, 'branche': None, 'modifications_locales': None, 'copie_sans_git': True, 'manifeste_sha256': digest}


def module_available(python, module):
    return subprocess.run([python, '-c', f'import {module}'], capture_output=True).returncode == 0


def child_env(extra=None):
    env = dict(os.environ)
    env.update({'PYTHONUTF8': '1', 'LANGSMITH_TRACING': 'false', 'PYTHONDONTWRITEBYTECODE': '1'})
    env.update(extra or {})
    return env


RAN = re.compile(r'^Ran (\d+) tests? in ([\d.]+)s', re.M)
SUMMARY = re.compile(r'^(OK|FAILED)(?: \(([^)]*)\))?\s*$', re.M)
FAILED_TEST = re.compile(r'^(ERROR|FAIL): (\S+) \(([^)]+)\)', re.M)
BLOCK_SEP = re.compile(r'^={50,}$', re.M)
DASH_SEP = re.compile(r'^-{50,}$', re.M)
EXCEPTION_LINE = re.compile(r'^[A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt)\b.*$', re.M)


def failure_excerpts(output):
    """Last exception line of each failing test, so a report from the tower can be diagnosed."""
    excerpts = {}
    for block in BLOCK_SEP.split(output)[1:]:
        head = FAILED_TEST.search(block)
        if not head:
            continue
        parts = DASH_SEP.split(block)
        body = parts[1] if len(parts) > 1 else ''
        found = EXCEPTION_LINE.findall(body)
        line = found[-1] if found else next((x for x in reversed(body.strip().splitlines()) if x.strip()), '')
        excerpts[(head.group(2), head.group(3))] = line.strip()[:300]
    return excerpts


def parse_unittest(output):
    ran = RAN.findall(output)
    summary = SUMMARY.findall(output)
    counts = {'tests': int(ran[-1][0]) if ran else 0, 'failures': 0, 'errors': 0, 'skipped': 0, 'expected_failures': 0}
    if summary:
        for part in (summary[-1][1] or '').split(','):
            if '=' in part:
                key, value = part.strip().split('=')
                key = {'expected failures': 'expected_failures'}.get(key, key)
                if key in counts:
                    counts[key] = int(value)
    failing = []
    excerpts = failure_excerpts(output)
    for kind, name, where in FAILED_TEST.findall(output):
        item = {'kind': kind, 'test': f'{name} ({where})' if name in ('setUpClass', 'tearDownClass') else where}
        if excerpts.get((name, where)):
            item['erreur'] = excerpts[(name, where)]
        failing.append(item)
    return counts, failing, (summary[-1][0] if summary else None)


def classify_failures(failing):
    explained, regressions = [], []
    for item in failing:
        rule = next((r for r in PRECONDITIONS if r['match'].search(item['test'])), None)
        if rule and (rule['present'] is None or not rule['present']()):
            explained.append({**item, 'cause': rule['cause'], 'explication': CAUSES[rule['cause']]})
        else:
            regressions.append(item)
    return explained, regressions


def run_unittest_suite(python, suite_id, directory, pattern, domain, timeout, extra_env=None):
    start = time.perf_counter()
    try:
        proc = subprocess.run([python, '-m', 'unittest', 'discover', '-s', directory, '-t', directory, '-p', pattern],
                              cwd=ROOT, env=child_env(extra_env), capture_output=True, text=True, encoding='utf-8', errors='replace',
                              timeout=timeout)
        output, code = proc.stdout + proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or '') + (exc.stderr or '') if isinstance(exc.stdout, str) else ''
        return {'id': suite_id, 'domaine': domain, 'status': 'echec', 'detail': f'Délai de {timeout} s dépassé',
                'duree_s': round(time.perf_counter() - start, 1)}
    counts, failing, verdict = parse_unittest(output)
    explained, regressions = classify_failures(failing)
    if code == 0:
        status = 'ok'
    elif regressions or not failing:
        status = 'echec'
    else:
        status = 'partiel'
    return {'id': suite_id, 'domaine': domain, 'status': status, 'code_retour': code, **counts,
            'echecs_expliques': explained, 'regressions': regressions, 'duree_s': round(time.perf_counter() - start, 1),
            'sortie_fin': output.strip().splitlines()[-1:] if status == 'echec' and not failing else []}


def run_node_suite():
    node = shutil.which('node')
    if not node:
        return {'id': 'node_jarvis', 'domaine': 'Interface voix, mémoire, Studio/Growth (JS)', 'status': 'non_execute', 'detail': 'Node.js absent'}
    start = time.perf_counter()
    proc = subprocess.run([node, '--test', *NODE_TESTS], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    out = proc.stdout + proc.stderr
    def count(key):
        m = re.search(rf'^# {key} (\d+)', out, re.M)
        return int(m.group(1)) if m else 0
    return {'id': 'node_jarvis', 'domaine': 'Interface voix, mémoire, Studio/Growth (JS)', 'status': 'ok' if proc.returncode == 0 else 'echec',
            'tests': count('tests'), 'failures': count('fail'), 'skipped': count('skipped'), 'duree_s': round(time.perf_counter() - start, 1),
            'regressions': re.findall(r'^not ok \d+ - (.+)$', out, re.M)[:20], 'echecs_expliques': []}


def run_tool(tool_id, args, python, timeout=900, check_json=None):
    start = time.perf_counter()
    try:
        proc = subprocess.run([python, *args], cwd=ROOT, env=child_env(), capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'id': tool_id, 'status': 'echec', 'detail': f'Délai de {timeout} s dépassé'}
    result = {'id': tool_id, 'status': 'ok' if proc.returncode == 0 else 'echec', 'code_retour': proc.returncode,
              'duree_s': round(time.perf_counter() - start, 1)}
    if proc.returncode:
        result['detail'] = (proc.stdout + proc.stderr).strip()[-800:]
    if check_json:
        try:
            result.update(check_json(proc.stdout))
            result.pop('detail', None)  # the parsed report replaces the raw output tail
        except (ValueError, KeyError, TypeError) as exc:
            result.update({'status': 'echec', 'detail': f'Rapport illisible : {exc}'})
    return result


def run_tools(python, workdir):
    out = []
    report = Path(workdir) / 'workflows.json'

    def workflows(_stdout):
        data = json.loads(report.read_text(encoding='utf-8'))
        transcripts = data.get('transcripts', {})
        guards = data.get('guards') or []
        return {'moteur': transcripts.get('engine'), 'essais': transcripts.get('trials'),
                'depot_p95_ms': (transcripts.get('submit') or {}).get('p95_ms'),
                'gardes_et_pannes': len(guards) if isinstance(guards, list) else None, 'rapport_ok': data.get('ok') is True}
    out.append(run_tool('simulation_workflows', ['tools/simulate_jarvis_workflows.py', '--repeats', '3', '--output', str(report)], python,
                        check_json=workflows))

    def validate(stdout):
        data = json.loads(stdout)
        return {'fichiers': data['files'], 'anomalies': data['issues'][:20], 'status': 'ok' if data['ok'] else 'echec'}
    out.append(run_tool('validate_repository', ['tools/validate_repository.py'], python, check_json=validate))
    out.append(run_tool('evaluate_memory', ['tools/evaluate_memory.py'], python))
    startup = Path(workdir) / 'startup.json'
    out.append(run_tool('check_startup_abrupt', ['tools/check_startup.py', '--abrupt', '--output', str(startup)], python))

    def install_plan(stdout):
        data = json.loads(stdout)
        plan = data['plan']
        return {'plan': [f'{s["id"]}:{s["type"]}' for s in plan], 'avertissements': data['avertissements'],
                'status': 'ok' if data['simulation'] is True and any(s['id'] == 'jarvis' for s in plan) else 'echec'}
    out.append(run_tool('installation_tout_simulation', ['tools/installer_tout.py', '--simulation'], python, timeout=120,
                        check_json=install_plan))

    def collection(stdout):
        data = json.loads(stdout)
        failed = sorted(k for k, ok in data['controles'].items() if not ok)
        return {'controles': len(data['controles']), 'echecs': failed, 'premier_passage': data['premier_passage'],
                'status': 'ok' if data['ok'] and not failed else 'echec'}
    out.append(run_tool('collecte_simulation', ['tools/collecte_guidee.py', 'simulation'], python, timeout=300, check_json=collection))

    def voice(stdout):
        data = json.loads(stdout)
        return {'status': 'ok' if data['ok'] else 'echec', 'versions': data['versions'],
                **({'detail': data['detail']} if data.get('detail') else {})}
    if module_available(python, 'faster_whisper'):
        out.append(run_tool('voix_decodage', ['tools/verifier_voix.py'], python, timeout=120, check_json=voice))
    else:
        out.append({'id': 'voix_decodage', 'status': 'non_execute',
                    'detail': 'faster-whisper absent de l’interpréteur testé (jarvis/requirements-voice.txt).'})
    return out


# --- Émulation de l'encodage Windows ----------------------------------------------

def cp1252_environment(workdir):
    """Linux only: a French cp1252 locale reproduces Windows' default text encoding."""
    if os.name == 'nt':
        # Native Windows: switch UTF-8 mode off and use the machine's real ANSI code page.
        return {'PYTHONUTF8': '0'}, None
    localedef = shutil.which('localedef')
    if not localedef:
        return None, 'localedef absent : émulation cp1252 impossible sur cet hôte.'
    target = Path(workdir) / 'locale'
    target.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([localedef, '-i', 'fr_FR', '-f', 'CP1252', str(target / 'fr_FR.CP1252')],
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    env = {'LOCPATH': str(target), 'LC_ALL': 'fr_FR.CP1252', 'PYTHONUTF8': '0'}
    probe = subprocess.run([sys.executable, '-c', 'import locale;print(locale.getencoding())'],
                           env={**os.environ, **env}, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    if probe.stdout.strip().lower() != 'cp1252':
        return None, 'Locale cp1252 non disponible : ' + (proc.stderr or probe.stderr).strip()[-200:]
    return env, None


ENCODING_SUITES = [
    # Les tests de lanceurs ne sont pas représentatifs : sous Linux la locale change aussi
    # l'encodage des chemins, alors que Windows garde des chemins Unicode.
    ('enc_tests_memoire', 'tests', 'test_memory*.py'),
    ('enc_tests_production', 'tests', 'test_production_recovery.py'),
    ('enc_tests_workflows', 'tests_workflows', 'test*.py'),
    ('enc_jarvis_tests', 'jarvis/tests', 'test*.py'),
    ('enc_tests_ops', 'tests_ops', 'test*.py'),
]


ENCODING_HTTP = {'http_demarrage_securite', 'http_ecrans_appairage', 'http_dashboard_atelier', 'http_dashboards_nommes',
                 'http_refus_physique_negation', 'http_coupure_reprise', 'http_cao_socle'}


def separate_utf8_failures(suite, baseline):
    """A test that already fails in UTF-8 is not an encoding defect: keep it visible, outside the cp1252 verdict."""
    same = [r for r in suite.get('regressions', []) if r['test'] in baseline]
    if same:
        suite['regressions'] = [r for r in suite['regressions'] if r['test'] not in baseline]
        suite['echecs_aussi_en_utf8'] = same
        if suite['status'] == 'echec' and not suite['regressions']:
            suite['status'] = 'partiel'
    return suite


def run_encoding(python, workdir, baseline=None):
    env, reason = cp1252_environment(workdir)
    if env is None:
        return {'status': 'non_execute', 'detail': reason, 'suites': []}
    from bojart_ops import banc_http
    actual = subprocess.run([python, '-c', 'import locale;print(locale.getencoding())'], env={**os.environ, **env},
                            capture_output=True, text=True, encoding='utf-8').stdout.strip()
    suites = [separate_utf8_failures(run_unittest_suite(python, sid, d, p, 'Encodage ' + actual, 900, extra_env=env), baseline or set())
              for sid, d, p in ENCODING_SUITES]
    http = banc_http.run_http(python, only=ENCODING_HTTP, env=env)
    worst = ('echec' if any(s['status'] == 'echec' for s in suites + http) else
             'partiel' if any(s['status'] in ('partiel', 'non_execute') for s in suites + http) else 'ok')
    return {'status': worst, 'encodage_par_defaut': actual, 'environnement': {k: ('<temporaire>' if k == 'LOCPATH' else v) for k, v in env.items()},
            'suites': suites, 'http': http, 'comparaison_utf8': baseline is not None,
            'limite': ('Windows natif, mode UTF-8 de Python désactivé.' if os.name == 'nt' else
                       'Émulation sous Linux : encodage des fichiers et sous-processus comme Windows, pas la console ni le système de fichiers Windows.')}


# --- Roues Windows ----------------------------------------------------------------

def run_windows_wheels(python, workdir):
    target = Path(workdir) / 'roues'
    report = Path(workdir) / 'roues.json'
    args = [python, '-m', 'pip', 'install', '--dry-run', '--ignore-installed', '--quiet', '--platform', 'win_amd64', '--python-version', '3.12',
            '--implementation', 'cp', '--only-binary=:all:', '--target', str(target), '--report', str(report)]
    # One tower environment: resolve every Jarvis requirement file together (tests excluded).
    req_files = ['requirements.txt'] + sorted(p.name for p in (ROOT / 'jarvis').glob('requirements-*.txt')
                                              if p.name not in ('requirements-tests.txt',))
    for name in req_files:
        args += ['-r', name]
    try:
        proc = subprocess.run(args, cwd=ROOT / 'jarvis', capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'status': 'non_execute', 'detail': str(exc)}
    if proc.returncode:
        tail = proc.stderr.strip()[-600:]
        network = any(k in tail for k in ('ProxyError', 'Max retries', 'Temporary failure', 'Could not fetch', 'Network'))
        return {'status': 'non_execute' if network else 'echec', 'detail': tail, 'fichiers': req_files}
    data = json.loads(report.read_text(encoding='utf-8'))
    wheels = sorted((i['metadata']['name'], i['metadata']['version'], i['download_info']['url'].rsplit('/', 1)[-1]) for i in data['install'])
    sdists = [w for w in wheels if not w[2].endswith('.whl')]
    pinned = {}
    for req in req_files + ['requirements-orchestration.txt', 'apps/jarvis/requirements.txt']:
        for line in (ROOT / 'jarvis' / req).read_text(encoding='utf-8').splitlines():
            m = re.match(r'^([A-Za-z0-9_.-]+)==', line.strip())
            if m:
                pinned[re.sub(r'[-_.]+', '-', m.group(1)).lower()] = True
    from bojart_ops import verrou_dependances as vd
    locked = {}
    for lock in sorted((ROOT / 'jarvis/locks').glob('windows-cp312-*.txt')):
        locked.update({k: e['version'] for k, e in vd.parse_lock(lock)[1].items()})
    unpinned = [f'{n}=={v}' for n, v, _ in wheels if vd.canonical(n) not in pinned and vd.canonical(n) not in locked]
    moved = sorted(f'{n} {locked[vd.canonical(n)]}→{v}' for n, v, _ in wheels if vd.canonical(n) in locked and locked[vd.canonical(n)] != v)
    return {'status': 'echec' if sdists else 'ok', 'fichiers': req_files, 'paquets': len(wheels), 'compilation_requise': sdists,
            'dependances_transitives_non_epinglees': len(unpinned), 'non_verrouillees': unpinned,
            'verrou_windows': {'paquets': len(locked), 'nouvelles_versions_depuis_le_verrou': moved},
            'resolution_du_jour': [f'{n}=={v}' for n, v, _ in wheels],
            'limite': ('Résolution PyPI du jour pour win_amd64/cp312, marqueurs évalués sur l’hôte du banc ; pas une installation. '
                       'L’installation réelle du verrou est faite par la CI Windows.')}


# --- Catalogue et synthèse --------------------------------------------------------

def evaluate_catalog(results):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    index = {}
    for s in results.get('suites', []):
        index['suite:' + s['id']] = s['status']
    for t in results.get('outils', []):
        index['outil:' + t['id']] = t['status']
    for name, check in results.get('statique', {}).items():
        index['statique:' + name] = check['status']
    for sc in results.get('http', []):
        index['http:' + sc['id']] = 'ok' if sc['status'] == 'ok_reserve' else sc['status']
    if 'encodage' in results:
        index['encodage:cp1252'] = results['encodage']['status']
    if 'reseau' in results:
        index['reseau:roues_windows'] = results['reseau']['status']
    evaluated = []
    for action in catalog['actions']:
        checks = {v: index.get(v, 'non_execute') for v in action['verifications']}
        reserves = [sc['id'] for sc in results.get('http', []) if 'http:' + sc['id'] in checks and sc['status'] == 'ok_reserve']
        if action['etat_code'] == 'absent':
            status = 'non_code'
        elif any(s == 'echec' for s in checks.values()):
            status = 'echec'
        elif not checks or any(s in ('non_execute', 'partiel') for s in checks.values()):
            status = 'partiel'
        elif action['etat_code'] == 'partiel':
            status = 'partiel'  # code incomplete (weights, service, sources): never better than partial
        else:
            status = 'simule_ok'
        evaluated.append({**action, 'statut_banc': status, 'verifications_resultat': checks, 'reserves': reserves,
                          'qualification_reelle': 'à faire sur la tour'})
    return evaluated


SEVERITY_ORDER = {'bloquant': 0, 'majeur': 1, 'mineur': 2, 'info': 3}


def collect_findings(results):
    findings = []
    for name, check in results.get('statique', {}).items():
        findings += check['findings']
    for s in results.get('suites', []):
        for r in s.get('regressions', []):
            error = r.get('erreur') if isinstance(r, dict) else None
            findings.append({'check': 'suite:' + s['id'], 'severity': 'bloquant', 'path': r.get('test', r) if isinstance(r, dict) else r,
                             'detail': 'Test en échec' + (' : ' + error if error else ''), 'fix': 'Analyser et corriger.'})
        causes = {}
        for e in s.get('echecs_expliques', []):
            causes.setdefault(e['cause'], []).append(e['test'])
        for cause, tests in causes.items():
            findings.append({'check': 'suite:' + s['id'], 'severity': 'majeur', 'path': f'{len(tests)} test(s)',
                             'detail': CAUSES[cause] + ' Non exécutés : ' + ', '.join(t.split(' (')[-1].rstrip(')').split('.')[-1] for t in tests[:6]),
                             'fix': 'Fournir la précondition sur la tour avant la recette.'})
    for sc in results.get('http', []):
        if sc['status'] == 'echec':
            findings.append({'check': 'http:' + sc['id'], 'severity': 'bloquant', 'path': 'serveur Jarvis', 'detail': sc.get('detail', ''), 'fix': ''})
        elif sc['status'] == 'ok_reserve':
            findings.append({'check': 'http:' + sc['id'], 'severity': 'mineur', 'path': 'serveur Jarvis', 'detail': sc['mesures']['reserve'], 'fix': ''})
    for t in results.get('outils', []):
        if t['status'] == 'echec':
            detail = t.get('detail') or ', '.join(f"{a.get('path', '')} {a.get('error', '')}".strip() for a in t.get('anomalies', [])[:8])
            findings.append({'check': 'outil:' + t['id'], 'severity': 'bloquant', 'path': t['id'], 'detail': detail[-400:], 'fix': ''})
    enc = results.get('encodage', {})
    for s in enc.get('suites', []):
        for r in s.get('regressions', []):
            detail = ('Échoue avec l’encodage par défaut de Windows (cp1252) alors qu’il passe en UTF-8.' if enc.get('comparaison_utf8')
                      else 'Échoue avec l’encodage par défaut de Windows (cp1252) ; suite UTF-8 non exécutée pour comparaison.')
            findings.append({'check': 'encodage:cp1252', 'severity': 'majeur', 'path': r['test'],
                             'detail': detail + (' ' + r['erreur'] if r.get('erreur') else ''), 'fix': 'Passer encoding="utf-8".'})
    for sc in enc.get('http', []):
        if sc['status'] == 'echec':
            findings.append({'check': 'encodage:cp1252', 'severity': 'majeur', 'path': 'serveur Jarvis (' + sc['id'] + ')',
                             'detail': 'Scénario en échec avec l’encodage par défaut de Windows : ' + sc.get('detail', '')[:300], 'fix': ''})
    net = results.get('reseau', {})
    if net.get('status') == 'echec' and net.get('detail'):
        findings.append({'check': 'reseau:roues_windows', 'severity': 'bloquant', 'path': ', '.join(net.get('fichiers', [])),
                         'detail': 'Installation Windows cp312 impossible : ' + net['detail'][-300:], 'fix': 'Aligner les versions épinglées.'})
    if net.get('compilation_requise'):
        findings.append({'check': 'reseau:roues_windows', 'severity': 'bloquant', 'path': 'jarvis/requirements*.txt',
                         'detail': 'Paquets sans roue Windows : ' + ', '.join(f'{n}=={v}' for n, v, _ in net['compilation_requise']), 'fix': ''})
    if net.get('dependances_transitives_non_epinglees'):
        findings.append({'check': 'reseau:roues_windows', 'severity': 'mineur', 'path': 'jarvis/requirements*.txt',
                         'detail': f"{net['dependances_transitives_non_epinglees']} dépendances transitives ni épinglées ni verrouillées : "
                                   "l’installation de la tour peut résoudre d’autres versions que celles testées. "
                                   + ', '.join(net.get('non_verrouillees', [])[:12]),
                         'fix': 'Regénérer les verrous Windows (tools/verrouiller_dependances.py, workflow du banc).'})
    if (net.get('verrou_windows') or {}).get('nouvelles_versions_depuis_le_verrou'):
        moved = net['verrou_windows']['nouvelles_versions_depuis_le_verrou']
        findings.append({'check': 'reseau:roues_windows', 'severity': 'info', 'path': 'jarvis/locks',
                         'detail': f'{len(moved)} paquet(s) se résolvent aujourd’hui dans une autre version que le verrou (un verrou valide reste installé tel quel) : '
                                   + ', '.join(moved[:12]),
                         'fix': 'Mettre à jour seulement après un nouveau passage du banc.'})
    return sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f['severity'], 9), f['check'], str(f['path'])))


def summarize(results):
    actions = results.get('actions', [])
    by_status = {}
    for a in actions:
        by_status[a['statut_banc']] = by_status.get(a['statut_banc'], 0) + 1
    findings = results.get('constats', [])
    by_sev = {}
    for f in findings:
        by_sev[f['severity']] = by_sev.get(f['severity'], 0) + 1
    tests = sum(s.get('tests', 0) for s in results.get('suites', []))
    return {'actions': len(actions), 'actions_par_statut': by_status, 'constats_par_severite': by_sev, 'tests_executes': tests,
            'scenarios_http': {k: sum(1 for s in results.get('http', []) if s['status'] == k) for k in ('ok', 'ok_reserve', 'echec', 'non_execute')}}


def run_bench(python=sys.executable, *, suites=True, http=True, static=True, tools=True, encoding=True, network=False, quick=False):
    from bojart_ops import banc_statique, banc_http
    started = utc_now()
    results = {'schema': 'bojart.banc-preinstallation.v1', 'debut': started,
               'depot': repo_state(),
               'environnement': {'os': platform.platform(), 'python_banc': sys.version.split()[0], 'python_teste': python,
                                 'langgraph': module_available(python, 'langgraph'), 'cadquery': module_available(python, 'cadquery'),
                                 'playwright': module_available(python, 'playwright'), 'node': shutil.which('node') is not None},
               'perimetre': 'Simulation logicielle uniquement : aucun micro, moniteur physique, imprimante, modèle local, service distant ou publication.'}
    with tempfile.TemporaryDirectory(prefix='bojart-banc-') as workdir:
        if static:
            results['statique'] = banc_statique.run_static(ROOT)
        if suites:
            chosen = [s for s in SUITES if not quick or s[5]]
            results['suites'] = [run_unittest_suite(python, *s[:5]) for s in chosen] + [run_node_suite()]
        if tools:
            results['outils'] = run_tools(python, workdir)
        if http:
            results['http'] = banc_http.run_http(python)
        if encoding and not quick:
            baseline = ({r['test'] for s in results['suites'] for r in s.get('regressions', []) if isinstance(r, dict)}
                        if 'suites' in results else None)
            results['encodage'] = run_encoding(python, workdir, baseline)
        if network:
            results['reseau'] = run_windows_wheels(python, workdir)
    results['actions'] = evaluate_catalog(results)
    results['constats'] = collect_findings(results)
    results['fin'] = utc_now()
    results['synthese'] = summarize(results)
    return results


# --- Rapport lisible ---------------------------------------------------------------

LABELS = {'simule_ok': 'Simulé OK', 'echec': 'ÉCHEC', 'partiel': 'Partiel', 'non_code': 'Non codé', 'non_execute': 'Non exécuté',
          'ok': 'OK', 'ok_reserve': 'OK avec réserve'}


def revision_line(depot):
    if depot.get('sha'):
        return f"Révision `{depot['sha']}` ({depot['branche']}), modifications locales : {'oui' if depot['modifications_locales'] else 'non'}."
    return f"Copie sans Git : manifeste `{depot.get('manifeste_sha256')}` (même empreinte que le journal d'installation) ; modifications locales non vérifiables sans Git."


def markdown(results):
    s = results['synthese']
    lines = [f"# Banc de simulation pré-installation — {results['debut'][:10]}", '',
             revision_line(results['depot']),
             f"Hôte : {results['environnement']['os']} ; Python testé : `{results['environnement']['python_teste']}` ; LangGraph : {results['environnement']['langgraph']} ; CadQuery : {results['environnement']['cadquery']}.",
             '', results['perimetre'], '', '## Synthèse', '',
             f"- {s['tests_executes']} tests exécutés ; scénarios HTTP : {s['scenarios_http']}.",
             f"- Actions : {s['actions']} — " + ', '.join(f"{LABELS.get(k, k)} {v}" for k, v in sorted(s['actions_par_statut'].items())),
             '- Constats : ' + ', '.join(f'{k} {v}' for k, v in sorted(s['constats_par_severite'].items(), key=lambda x: SEVERITY_ORDER.get(x[0], 9))),
             '', '## Actions de Jarvis', '', '| Domaine | Action | Banc | Hors simulation |', '|---|---|---|---|']
    for a in results['actions']:
        extra = '; '.join(a['hors_simulation'][:2]) or '—'
        status = LABELS.get(a['statut_banc'], a['statut_banc']) + (' (réserve)' if a['reserves'] else '')
        lines.append(f"| {a['domaine']} | {a['action']} | {status} | {extra} |")
    if results.get('suites'):
        lines += ['', '## Suites de tests', '', '| Suite | Domaine | Tests | Résultat | Non exécutés (cause) |', '|---|---|---|---|---|']
        for x in results['suites']:
            explained = len(x.get('echecs_expliques', []))
            lines.append(f"| {x['id']} | {x['domaine']} | {x.get('tests', '—')} | {LABELS.get(x['status'], x['status'])} | {explained or '—'} |")
    if results.get('http'):
        lines += ['', '## Scénarios HTTP bout en bout', '', '| Scénario | Résultat | Détail |', '|---|---|---|']
        for x in results['http']:
            detail = x.get('detail') or json.dumps(x.get('mesures', {}), ensure_ascii=False)
            lines.append(f"| {x['id']} | {LABELS.get(x['status'], x['status'])} | {detail[:220].replace('|', '/')} |")
    if results.get('encodage'):
        e = results['encodage']
        lines += ['', '## Émulation de l’encodage Windows (cp1252)', '', f"Résultat : {LABELS.get(e['status'], e['status'])}. {e.get('detail') or e.get('limite', '')}"]
        for x in e.get('suites', []):
            lines.append(f"- {x['id']} : {LABELS.get(x['status'], x['status'])}, {x.get('tests', 0)} tests" +
                         (f", régressions : {', '.join(r['test'] for r in x['regressions'][:4])}" if x.get('regressions') else ''))
    if results.get('reseau'):
        r = results['reseau']
        lines += ['', '## Roues Windows cp312', '', f"Résultat : {LABELS.get(r['status'], r['status'])} — {r.get('paquets', '?')} paquets, "
                  f"{len(r.get('compilation_requise', []))} à compiler, {r.get('dependances_transitives_non_epinglees', '?')} dépendances transitives non épinglées. {r.get('limite', r.get('detail', ''))}"]
    lines += ['', '## Constats', '', '| Sévérité | Contrôle | Fichier | Détail | Correction |', '|---|---|---|---|---|']
    for f in results['constats']:
        lines.append(f"| {f['severity']} | {f['check']} | {str(f['path'])[:80]} | {f['detail'][:260].replace('|', '/')} | {f.get('fix', '')[:120]} |")
    lines += ['', 'Un statut « Simulé OK » signifie que le logiciel se comporte comme prévu avec des doubles d’essai. '
              'Il ne qualifie ni la tour, ni le micro, ni les moniteurs, ni les imprimantes, ni la qualité artistique.', '']
    return '\n'.join(lines)
