"""Reproducible local measurements; synthetic data never enter live memory."""
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import queue
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import time

from .agent import AgentMemory, REPO
from .conversation import select_exchanges
from .core import Memory, MemoryError, canonical, file_sha, now
from .model_setup import FIXTURES, plan
from .ollama import Ollama
from .vectors import cosine

PROJECTS = ('bojart.jarvis', 'bojart.creative', 'bojart.sites')


def distribution(values):
    values = sorted(values)
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Mesures finies et positives requises.')
    if not values:
        return {'n': 0, 'p50': None, 'p95': None, 'min': None, 'max': None, 'mean': None}
    return {'n': len(values), 'p50': round(statistics.median(values), 3),
            'p95': round(values[math.ceil(.95 * len(values)) - 1], 3),
            'min': round(values[0], 3), 'max': round(values[-1], 3),
            'mean': round(statistics.mean(values), 3)}


def elapsed(start):
    return (time.perf_counter_ns() - start) / 1e6


def measured(call):
    start = time.perf_counter_ns()
    result = call()
    return result, elapsed(start)


def host_info():
    result = {'os': platform.system(), 'machine': platform.machine(),
              'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
              'logical_cpus': os.cpu_count(), 'gpu_snapshot': None}
    for path, key in [('/sys/fs/cgroup/cpu.max', 'cgroup_cpu_max'),
                      ('/sys/fs/cgroup/memory.max', 'cgroup_memory_max_bytes')]:
        try:
            result[key] = Path(path).read_text().strip()
        except OSError:
            result[key] = None
    command = shutil.which('nvidia-smi')
    if command:
        try:
            output = subprocess.run([command,
                '--query-gpu=name,memory.total,memory.free,driver_version',
                '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5, check=True)
            result['gpu_snapshot'] = {'fields': ['name', 'memory_total_mib', 'memory_free_mib', 'driver'],
                                      'rows': output.stdout.strip().splitlines()[:8], 'peak_memory': False}
        except (OSError, subprocess.SubprocessError):
            result['gpu_probe_failed'] = True
    return result


def provenance(repo):
    paths = sorted({r['path'] for r in json.loads((repo / 'data/knowledge/index.json').read_text('utf-8'))}
                   | {'data/knowledge/index.json', 'data/knowledge/retrieval_cases.json'})
    corpus = [{'path': p, 'sha256': file_sha(repo / p), 'bytes': (repo / p).stat().st_size} for p in paths]
    implementation = {p.relative_to(REPO).as_posix(): file_sha(p)
                      for p in sorted((REPO / 'bojart_memory').glob('*.py'))}
    implementation['tools/benchmark_jarvis.py'] = file_sha(REPO / 'tools/benchmark_jarvis.py')
    return {'corpus': corpus, 'corpus_sha256': hashlib.sha256(canonical(corpus).encode()).hexdigest(),
            'implementation_sha256': implementation}


def retrieval_probe(agent, query, project, limit=5):
    with Memory(agent.state, readonly=True) as memory:
        return memory.search(query, project=project, limit=limit)


def repository_trials(root, repo, repeats):
    agent = AgentMemory(root / 'reference-memory', repo=repo)
    _, index_ms = measured(agent.index)
    cases = json.loads((repo / 'data/knowledge/retrieval_cases.json').read_text('utf-8'))
    first_pass, reads, contexts, larger_contexts = [], [], [], []
    for iteration in range(repeats + 1):
        for case_id, case in enumerate(cases):
            result, ms = measured(lambda: retrieval_probe(agent, case['question'], case['project']))
            paths = [r['source_path'] for r in result['results']]
            row = {'case': case_id, 'iteration': iteration, 'ms': round(ms, 4),
                   'hit_at_5': case['expected_source'] in paths,
                   'verified': all(r['source_bytes_verified'] and r['project'] == case['project']
                                   for r in result['results'])}
            (first_pass if iteration == 0 else reads).append(row)
            if iteration == 0:
                continue
            pack, ms = measured(lambda: agent.context(case['question'], case['project'], _max_utf8_bytes=8000))
            contexts.append({'case': case_id, 'iteration': iteration, 'ms': round(ms, 4),
                'bytes': pack['utf8_bytes'], 'omitted': pack['omitted'],
                'expected_source_present': any(e['source_path'] == case['expected_source'] for e in pack['evidence']),
                'valid': (pack['utf8_bytes'] <= 8000 and pack['sha256'] == hashlib.sha256(pack['text'].encode()).hexdigest()
                          and all(e['source_bytes_verified'] and e['project'] == case['project'] for e in pack['evidence'])
                          and all('[' + ref + ']' in pack['text'] for ref in pack['citations']))})
            larger, ms = measured(lambda: agent.context(case['question'], case['project'], _max_utf8_bytes=13000))
            larger_contexts.append({'case': case_id, 'iteration': iteration, 'ms': round(ms, 4),
                'bytes': larger['utf8_bytes'],
                'expected_source_present': any(e['source_path'] == case['expected_source'] for e in larger['evidence']),
                'valid': larger['utf8_bytes'] <= 13000 and larger['sha256'] == hashlib.sha256(larger['text'].encode()).hexdigest()})
    return {'index_ms': round(index_ms, 3), 'counts': agent.status(), 'unique_cases': len(cases),
            'first_pass_load_state': 'filesystem_already_read_during_indexing_not_cold', 'first_pass': first_pass,
            'search_ms': distribution([s['ms'] for s in reads]),
            'hit_at_5': sum(s['hit_at_5'] for s in reads), 'attempts': len(reads),
            'context_ms': distribution([s['ms'] for s in contexts]),
            'valid_contexts': sum(s['valid'] for s in contexts),
            'expected_source_in_context': sum(s['expected_source_present'] for s in contexts),
            'larger_context': {'budget_bytes': 13000, 'samples': larger_contexts,
                'context_ms': distribution([s['ms'] for s in larger_contexts]),
                'expected_source_in_context': sum(s['expected_source_present'] for s in larger_contexts)},
            'search_samples': reads, 'context_samples': contexts,
            'ok': all(s['hit_at_5'] and s['verified'] for s in reads) and all(s['valid'] for s in contexts + larger_contexts)}


def scale_trials(root, scales, repeats, workers, operations):
    state, docs = root / 'scale-memory', root / 'synthetic-documents'
    docs.mkdir()
    agent = AgentMemory(state)
    levels, previous = [], 0
    for count in scales:
        start = time.perf_counter_ns()
        with Memory(state) as memory, memory.transaction():
            for i in range(previous, count):
                path = docs / ('dossier' + str(i).zfill(6) + '.md')
                path.write_text(f'# dossier{i:06d}\nProjet {PROJECTS[i % 3]}. Donnée synthétique.\n'
                                + ('atelier simulation mémoire couleur matière géométrie.\n' * 18), encoding='utf-8')
                memory.ingest_file(path, root=docs, project=PROJECTS[i % 3], collection='simulation',
                                   provenance='Generated benchmark fixture; no customer or workshop observation')
        ingest_ms = elapsed(start)
        samples = []
        for i in range(repeats):
            target = (i * 997) % count
            for kind, query in [('identifier', f'dossier{target:06d}'), ('broad', 'atelier simulation')]:
                result, ms = measured(lambda: retrieval_probe(agent, query, PROJECTS[target % 3]))
                ok = bool(result['results']) and all(r['source_bytes_verified'] and r['project'] == PROJECTS[target % 3]
                                                    for r in result['results'])
                if kind == 'identifier':
                    ok = ok and result['results'][0]['source_path'] == f'dossier{target:06d}.md'
                samples.append({'kind': kind, 'ms': round(ms, 4), 'ok': ok})
        levels.append({'documents': count, 'added_documents': count - previous, 'ingest_ms': round(ingest_ms, 3),
            'identifier_ms': distribution([s['ms'] for s in samples if s['kind'] == 'identifier']),
            'broad_ms': distribution([s['ms'] for s in samples if s['kind'] == 'broad']),
            'samples': samples, 'ok': all(s['ok'] for s in samples)})
        previous = count

    def operation(i, queued_at):
        start = time.perf_counter_ns()
        row = {'id': i, 'kind': 'write' if i % 5 == 0 else 'read', 'queue_ms': round((start - queued_at) / 1e6, 4)}
        try:
            if row['kind'] == 'write':
                agent.note('charge-' + str(i), 'Note synthétique ' + str(i), 'Benchmark local synthétique', PROJECTS[0])
                row['ok'] = True
            else:
                target = i % scales[-1]
                result = agent.search(f'dossier{target:06d}', PROJECTS[target % 3])
                row['ok'] = bool(result['results']) and result['results'][0]['source_path'] == f'dossier{target:06d}.md'
        except (ValueError, OSError, sqlite3.Error) as exc:
            row.update(ok=False, error_type=type(exc).__name__)
        row['service_ms'], row['total_ms'] = round(elapsed(start), 4), round(elapsed(queued_at), 4)
        return row

    start = time.perf_counter_ns()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(operation, i, time.perf_counter_ns()) for i in range(operations)]
        samples = [f.result() for f in futures]
    wall_ms = elapsed(start)
    with Memory(state, readonly=True) as memory:
        persisted = memory.db.execute('SELECT count(*) FROM agent_notes').fetchone()[0]
        before = memory.stats()
        _, backup_ms = measured(lambda: memory.backup(root / 'snapshot'))
    restored, restore_ms = measured(lambda: Memory.restore(root / 'snapshot', root / 'restored'))
    copy = AgentMemory(root / 'restored')
    with Memory(copy.state, readonly=True) as memory:
        after = memory.stats()
        restored_notes = memory.db.execute('SELECT count(*) FROM agent_notes').fetchone()[0]
    persistence_ok = (restored['ok'] and before == after and persisted == restored_notes
                      and persisted == sum(s['kind'] == 'write' and s['ok'] for s in samples))
    return {'levels': levels, 'mixed_load': {'workers': workers, 'operations': operations,
                'successes': sum(s['ok'] for s in samples), 'errors': sum(not s['ok'] for s in samples),
                'wall_ms': round(wall_ms, 3), 'completed_per_second': round(operations / (wall_ms / 1000), 2),
                'service_ms': distribution([s['service_ms'] for s in samples]),
                'including_queue_ms': distribution([s['total_ms'] for s in samples]), 'samples': samples},
            'backup_restore': {'backup_ms': round(backup_ms, 3), 'restore_ms': round(restore_ms, 3),
                'documents': before['sources'], 'persisted_notes': persisted, 'ok': persistence_ok},
            'ok': all(s['ok'] for s in levels) and all(s['ok'] for s in samples) and persistence_ok}


CRASH_WORKER = '''import sys
from pathlib import Path
from bojart_memory.core import Memory
state, docs, phase = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
with Memory(state) as m:
    with m.transaction():
        m.ingest_file(docs/'crash.md', root=docs, project='bojart.jarvis',
                      collection='simulation', provenance='Forced-stop fixture')
        if phase == 'pending':
            print('ready', flush=True)
            sys.stdin.read()
    if phase == 'committed':
        print('ready', flush=True)
        sys.stdin.read()
'''


def fault_trials(root, repetitions):
    state, docs = root / 'fault-memory', root / 'fault-documents'
    docs.mkdir()
    agent = AgentMemory(state)
    samples = []
    path = docs / 'crash.md'
    for trial in range(repetitions):
        for phase in ('pending', 'committed'):
            path.write_text('arrêt-' + str(trial) + '-' + phase, encoding='utf-8')
            with Memory(state, readonly=True) as memory:
                before = [tuple(r) for r in memory.db.execute('SELECT source_id,current_version FROM sources ORDER BY source_id')]
            process = subprocess.Popen([sys.executable, '-c', CRASH_WORKER, str(state), str(docs), phase],
                cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=dict(os.environ, PYTHONUTF8='1'))
            lines = queue.Queue()
            reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
            reader.start()
            try:
                if lines.get(timeout=20).strip() != 'ready':
                    raise RuntimeError('Processus de panne non prêt.')
                process.kill()
                process.wait(timeout=15)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=15)
                reader.join(timeout=5)
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()
            with Memory(state, readonly=True) as memory:
                after = [tuple(r) for r in memory.db.execute('SELECT source_id,current_version FROM sources ORDER BY source_id')]
                valid = memory.verify()['ok']
            samples.append({'trial': trial, 'fault': 'kill_' + phase,
                            'ok': valid and ((after == before) if phase == 'pending' else (after != before))})

    reference = docs / 'reference.md'
    reference.write_text('référence stable alpha', encoding='utf-8')
    with Memory(state) as memory:
        imported = memory.ingest_file(reference, root=docs, project=PROJECTS[0], collection='simulation', provenance='Fault fixture')
        obj = memory._object(imported['sha256'])
    original = obj.read_bytes()
    try:
        obj.write_bytes(b'CORRUPTED FIXTURE')
        found = agent.search('référence stable', PROJECTS[0])
        samples.append({'fault': 'changed_original', 'ok': bool(found['warnings']) and not any(
            r['sha256'] == imported['sha256'] for r in found['results'])})
    finally:
        obj.write_bytes(original)
    config = state / 'models.json'
    try:
        config.write_text('{invalid', encoding='utf-8')
        found = agent.search('référence stable', PROJECTS[0])
        samples.append({'fault': 'invalid_model_config', 'ok': bool(found['results']) and found['semantic_status'].startswith('unavailable:')})
    finally:
        config.unlink()
    pack = agent.context('référence stable', PROJECTS[0])
    agent.episode('synthetic-history', 'benchmark', PROJECTS[0],
                  {'question': 'Référence ?', 'context': pack, 'response': {'answer': 'Réponse de test synthétique, non générée.'}})
    before_history = agent.history('benchmark', PROJECTS[0])
    reference.write_text('référence stable beta', encoding='utf-8')
    with Memory(state) as memory:
        memory.ingest_file(reference, root=docs, project=PROJECTS[0], collection='simulation', provenance='Changed fixture')
    with Memory(state, readonly=True) as memory:
        history = select_exchanges(memory, session='benchmark', project=PROJECTS[0], facts=[])
    samples.append({'fault': 'outdated_answer', 'ok': len(history) == 1 and 'answer' not in history[0]
                    and history[0]['answer_status'] == 'withheld_sources_changed'
                    and agent.history('benchmark', PROJECTS[0]) == before_history})
    return {'forced_process_stops': repetitions * 2, 'power_loss_tested': False,
            'samples': samples, 'successes': sum(s['ok'] for s in samples),
            'attempts': len(samples), 'ok': all(s['ok'] for s in samples)}


def run_memory(repo=REPO, *, repeats=30, scales=(100, 1000, 5000), workers=8, operations=320,
               crashes=10, progress=lambda message: None):
    if (type(repeats) is not int or not 1 <= repeats <= 100 or type(workers) is not int or not 1 <= workers <= 16
            or type(operations) is not int or not 5 <= operations <= 2000
            or type(crashes) is not int or not 1 <= crashes <= 30
            or not scales or any(type(n) is not int or not 3 <= n <= 10000 for n in scales)
            or list(scales) != sorted(set(scales))):
        raise ValueError('Paramètres de simulation hors limites.')
    report = {'schema': 'bojart.memory-benchmark.v1', 'created_at': now(), 'host': host_info(),
              'scope': 'real_memory_code_on_this_host_with_reference_and_synthetic_data',
              'llm_inference': False, 'physical_actions': 0, 'target_hardware_qualified': False,
              'percentiles': 'p50 median; p95 nearest rank; no confidence interval; samples are not independent users',
              'parameters': {'repeats': repeats, 'scales': list(scales), 'workers': workers,
                             'operations': operations, 'crashes_per_phase': crashes}, **provenance(Path(repo))}
    with tempfile.TemporaryDirectory(prefix='bojart-benchmark-') as directory:
        root = Path(directory)
        progress('Mesure des recherches et contextes du corpus de référence.')
        report['repository'] = repository_trials(root, Path(repo), repeats)
        progress('Mesure du corpus synthétique, de la concurrence et de la restauration.')
        report['scale'] = scale_trials(root, scales, repeats, workers, operations)
        progress('Arrêts forcés et erreurs injectées dans des états temporaires.')
        report['faults'] = fault_trials(root, crashes)
    report['ok'] = all(report[key]['ok'] for key in ('repository', 'scale', 'faults'))
    return report


def model_trials(profile='speed', *, repeats=30, url='http://127.0.0.1:11434', progress=lambda message: None):
    if type(repeats) is not int or not 4 <= repeats <= 100:
        raise ValueError('Prévoir 4 à 100 appels mesurés.')
    choice = plan(profile)
    report = {'schema': 'bojart.model-benchmark.v1', 'created_at': now(), 'host': host_info(),
              'profile': choice, 'scope': 'synthetic_prompts_on_executing_host', 'samples': [], 'ok': False,
              'downloads': 0, 'configuration_writes': 0, 'physical_actions': 0, 'production_ready': False,
              'first_token_ms': None, 'prompt_cache_may_be_reused': True,
              'criteria': 'Literal expected terms and no truncation; not a general quality score.',
              'fixture_sha256': hashlib.sha256(canonical(FIXTURES).encode()).hexdigest()}
    attempt = None
    try:
        chat = Ollama(choice['chat_model'], url, timeout=90)
        embed = Ollama(choice['embedding_model'], url, timeout=90)
        version = chat.request('/api/version')
        report['ollama_version'] = version.get('version') if isinstance(version, dict) else None
        report['chat_metadata'] = chat.inspect('completion')
        report['embedding_metadata'] = embed.inspect('embedding')
        # Keep the first call separate; never unload a user's model to fake a cold start.
        for i in range(repeats + 1):
            fixture = FIXTURES[i % len(FIXTURES)]
            progress(f'Modèle local : appel {i + 1}/{repeats + 1}.')
            start = time.perf_counter_ns()
            attempt = {'case': fixture['id'], 'phase': 'first_call_load_state_unknown' if i == 0 else 'followup'}
            result = chat.chat(fixture['question'], fixture['context'], settings=choice['chat_options'])
            text = result['answer'].lower()
            row = {'case': fixture['id'], 'ms': round(elapsed(start), 3), 'answer': result['answer'],
                   'phase': 'first_call_load_state_unknown' if i == 0 else 'followup',
                   'ok': all(s in text for s in fixture['required']) and not any(s in text for s in fixture['forbidden'])
                         and not result['output_truncated'], 'performance': result['performance'],
                   'prompt_budget': result['prompt_budget'], 'output_truncated': result['output_truncated']}
            report['samples'].append(row)
            attempt = None
        vectors, ms = measured(lambda: embed.embed(['Mémoire persistante du projet BOJ.ART.',
            'Mémoire persistante du projet BOJ.ART.', 'La météo annonce de la neige demain.']))
        report['embedding'] = {'ms': round(ms, 3), 'dimensions': len(vectors[0]),
            'ok': cosine(vectors[0], vectors[1]) >= .99 and cosine(vectors[0], vectors[1]) > cosine(vectors[0], vectors[2]) + .001}
        try:
            loaded = chat.request('/api/ps')
            report['loaded_models_snapshot'] = [{k: row.get(k) for k in ('name', 'digest', 'size', 'size_vram', 'context_length')}
                for row in loaded['models'] if row.get('name') in (chat.model, embed.model)]
        except (ValueError, OSError, KeyError, TypeError, HTTPException):
            report['loaded_models_snapshot'] = None
        chat.key(refresh=True)
        embed.key(refresh=True)
        report['ok'] = all(s['ok'] for s in report['samples']) and report['embedding']['ok']
    except (ValueError, OSError, KeyError, TypeError, HTTPException) as exc:
        report['error_type'] = type(exc).__name__
        report['error_code'] = getattr(exc, 'code', 'local_benchmark_failed')
        if attempt is not None:
            report['failed_attempt'] = {**attempt, 'ms': round(elapsed(start), 3), 'error_type': type(exc).__name__}
    followups = [s for s in report['samples'] if s['phase'] == 'followup']
    report['requested_followups'] = repeats
    report['completed_followups'] = len(followups)
    report['literal_checks_passed'] = sum(s['ok'] for s in followups)
    report['followup_ms'] = distribution([s['ms'] for s in followups])
    report['tokens_per_second'] = distribution([s['performance']['generated_tokens_per_second'] for s in followups
        if s['performance']['generated_tokens_per_second'] is not None])
    report['latency_goal_ms'] = choice['max_followup_ms']
    report['within_latency_goal'] = sum(s['ms'] <= choice['max_followup_ms'] for s in followups)
    report['performance_measured_on_target'] = False  # User must identify the executing host separately.
    return report
