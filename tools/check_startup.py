#!/usr/bin/env python3
"""Exercise the real launcher twice in temporary state; optional Chromium UI check."""
import argparse
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_memory import Memory
from bojart_memory.agent import AgentMemory


def start(root, environment, number):
    log = root/f'start-{number}.log'
    with log.open('w') as stream:
        process = subprocess.Popen([sys.executable, str(ROOT/'tools/start_jarvis.py'),
                                    '--state', str(root/'work'), '--port', '0', '--no-browser'],
                                   cwd=ROOT, env=environment, stdout=stream, stderr=stream)
    deadline = time.monotonic()+45
    while time.monotonic() < deadline:
        text = log.read_text(encoding='utf-8', errors='replace')
        found = re.search(r'(http://127\.0\.0\.1:\d+/\?session=[A-Za-z0-9_-]+)\r?\n', text)
        if found:
            url = found[1]
            parsed = urllib.parse.urlsplit(url)
            origin = 'http://'+parsed.netloc
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            with opener.open(url, timeout=10) as response:
                assert response.status == 200
            return process, opener, origin, urllib.parse.parse_qs(parsed.query)['session'][0]
        if process.poll() is not None:
            safe = re.sub(r'session=[^\s]+', 'session=<redacted>', text[-1800:])
            raise RuntimeError('Launcher exited before HTTP startup: '+safe)
        time.sleep(.1)
    stop(process)
    raise RuntimeError('Launcher startup timeout.')


def stop(process, *, abrupt=False):
    if process.poll() is None:
        if abrupt:
            process.kill()
        else:
            process.send_signal(signal.SIGINT) if os.name != 'nt' else process.terminate()
        try: process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)


def get(opener, origin, route):
    with opener.open(origin+route, timeout=10) as response:
        return json.load(response)


def acceptance(*, browser=False, chromium=None, screenshots=None, abrupt=False):
    with tempfile.TemporaryDirectory(prefix='bojart-startup-') as directory:
        root = Path(directory)
        environment = dict(os.environ, BOJART_MEMORY_STATE=str(root/'memory'), BOJ_JEV_ENABLED='0',
                           TYPESAFE_API_KEY='', PYTHONUNBUFFERED='1',
                           LANGSMITH_TRACING='false', LANGCHAIN_TRACING_V2='false')
        agent = AgentMemory(root/'memory')
        agent.note('recette.reprise', 'À vérifier sur la tour', 'Fixture locale de recette', 'bojart.jarvis')
        source = root/'preuve.md'
        source.write_text('preuveCitationXYZ <img src=x onerror="window.__should_not_run=true">', encoding='utf-8')
        with Memory(agent.state) as memory:
            memory.ingest_file(source, root=root, project='bojart.jarvis', collection='acceptance', provenance='Browser test fixture')
        process = None
        try:
            process, opener, origin, token = start(root, environment, 1)
            health = get(opener, origin, '/health')
            assert health['status'] == 'local_ready' and health['physical_commands'] is False
            route = '/api/memory/context?project=bojart.creative&q=G2'
            first = get(opener, origin, route)
            assert first['evidence'] and first['characters'] <= first['max_characters']
            assert hashlib.sha256(first['text'].encode()).hexdigest() == first['sha256']
            browser_report = None
            if browser:
                env = dict(environment)
                if chromium: env['BOJ_TEST_CHROMIUM'] = str(chromium)
                payload = {'origin': origin, 'token': token, 'screenshots': str(screenshots) if screenshots else None}
                run = subprocess.run(['node', str(ROOT/'tools/memory_browser.cjs')], input=json.dumps(payload),
                                     cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
                if run.returncode: raise RuntimeError('Browser check failed: '+run.stderr[-2000:])
                browser_report = json.loads(run.stdout)
            before = AgentMemory(agent.state).status()
            stop(process, abrupt=abrupt)
            process, opener, origin, _ = start(root, environment, 2)
            second = get(opener, origin, route)
            after = AgentMemory(agent.state).status()
            counters = ('assets', 'sources', 'versions', 'agent_notes', 'agent_episodes', 'agent_vectors')
            assert all(before[k] == after[k] for k in counters), 'Startup duplicated persistent records.'
            assert first['sha256'] == second['sha256'], 'Context changed across an unchanged restart.'
            assert any(f['key'] == 'recette.reprise' for f in AgentMemory(agent.state).facts('bojart.jarvis'))
            stop(process); process = None
            with Memory(agent.state, readonly=True) as memory:
                assert memory.verify()['ok']
                memory.backup(root/'snapshot')
            Memory.restore(root/'snapshot', root/'restored')
            restored = AgentMemory(root/'restored', repo=root/'missing-source-repo')
            assert first['sha256'] == restored.context('G2', 'bojart.creative')['sha256']
            assert restored.status()['agent_notes'] == after['agent_notes']
            files = ['tools/start_jarvis.py', 'tools/doctor.py', 'bojart_memory/paths.py',
                     'bojart_memory/agent.py', 'bojart_memory/core.py',
                     'jarvis/apps/jarvis/app/consolidated_workbench.py',
                     'jarvis/apps/jarvis/app/memory.html', 'jarvis/apps/jarvis/app/memory.js',
                     'jarvis/apps/jarvis/app/memory.css']
            return {'schema': 'bojart.startup-acceptance.v1', 'observed_at': datetime.now(timezone.utc).isoformat(),
                    'python': sys.version.split()[0], 'platform': sys.platform,
                    'launcher_started_twice': True, 'context_survives_restart': True,
                    'unclean_shutdown_tested': abrupt or os.name == 'nt',
                    'restart_method': 'forced_process_kill' if abrupt else ('terminate_process' if os.name == 'nt' else 'graceful_sigint'),
                    'no_duplicate_versions_or_notes': True, 'backup_restore_verified': True,
                    'restored_without_source_repo': True,
                    'browser': browser_report, 'provider_calls': 0,
                    'live_models_tested': False, 'physical_hardware_tested': False,
                    'data_scope': 'temporary fixtures and selected public project context',
                    'tested_files_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}}
        finally:
            if process is not None: stop(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--abrupt', action='store_true', help='Force-stop the first launcher process before restart.')
    parser.add_argument('--chromium', type=Path)
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    result = acceptance(browser=args.browser, chromium=args.chromium, screenshots=args.screenshots, abrupt=args.abrupt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'browser_checks': len(result['browser']['checks']) if result['browser'] else 0}))


if __name__ == '__main__':
    main()
