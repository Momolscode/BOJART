#!/usr/bin/env python3
"""Paired ABBA comparisons on one host; instrumented runs are kept separate.

The baseline is an explicit checkout, never downloaded by this script. Workers
import exactly that checkout's runtime and workflow fixture. No model, network,
audio or physical display/printer is exercised. SQLite commits stay synchronous.
"""
import argparse
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = 'b49101e3acad6257e2d1a610dac5fb95ec0a8bfb'
BASELINE_MANIFEST_SHA256 = '9073f8c0538660ddc147563a4d47884885813e17ccafcb826b86b5e4f0734b0a'


def distribution(values):
    ordered = sorted(values)
    return {'count':len(ordered), **{f'p{p}_ms':ordered[math.ceil(p/100*len(ordered))-1]
            for p in (50, 95, 99)}, 'max_ms':ordered[-1],
            'over_1000ms':sum(v>1000 for v in ordered)}


def worker(repo, repeats, instrument=False, variant='default'):
    sys.path.insert(0, str(repo/'tools'))
    import simulate_jarvis_workflows as simulation
    timings = []
    def measure(label, call, *args, **kwargs):
        start = time.perf_counter_ns()
        try:return call(*args, **kwargs)
        finally:timings.append((label, (time.perf_counter_ns()-start)/1e6))
    class Cursor(sqlite3.Cursor):
        def execute(self, sql, *args, **kwargs):
            return measure(self.connection.label+':sql:'+sql.split()[0].upper(),
                           super().execute, sql, *args, **kwargs)
        def executemany(self, sql, *args, **kwargs):
            return measure(self.connection.label+':sql:'+sql.split()[0].upper(),
                           super().executemany, sql, *args, **kwargs)
    class Connection(sqlite3.Connection):
        def cursor(self, *args, **kwargs):
            return super().cursor(factory=Cursor)
        def execute(self, sql, *args, **kwargs):
            return self.cursor().execute(sql, *args, **kwargs)
        def __exit__(self, *args):
            return measure(self.label+':transaction_exit', super().__exit__, *args)
        def commit(self):return measure(self.label+':commit', super().commit)
        def close(self):return measure(self.label+':close', super().close)
    connect = sqlite3.connect
    def measured_connect(database, *args, **kwargs):
        label = Path(database).name
        connection = measure(label+':connect', connect, database, *args, factory=Connection, **kwargs)
        connection.label = label
        return connection
    with ExitStack() as stack:
        if variant != 'default':
            options = {'pool_sync':{'checkpoint_durability':'sync','reuse_connections':True},
                       'no_pool_exit':{'reuse_connections':False}}[variant]
            original = simulation.JarvisRuntime
            stack.enter_context(patch.object(simulation, 'JarvisRuntime',
                side_effect=lambda *args, **kw:original(*args, **kw, **options)))
        if instrument:
            stack.enter_context(patch.object(sqlite3, 'connect', measured_connect))
            runtime = simulation.JarvisRuntime
            # Used only with the default variant; no instrumentation in ABBA data.
            for name in ('_route','_guard','_dispatch','_receipt'):
                method = getattr(runtime, name)
                def timed(self, *a, _method=method, _name=name, **kw):
                    return measure('phase:'+_name, _method, self, *a, **kw)
                stack.enter_context(patch.object(runtime, name, timed))
        start = time.perf_counter_ns()
        result = simulation.transcript_trials(repeats)
        wall_ms = (time.perf_counter_ns()-start)/1e6
    grouped = defaultdict(list)
    for label, duration in timings:grouped[label].append(duration)
    result['sql_and_phase_profile'] = {k:{**distribution(v),'total_ms':sum(v)} for k,v in sorted(grouped.items())}
    result['instrumented'] = instrument
    result['variant'] = variant
    result['fixture_lifecycle_and_trials_ms'] = wall_ms
    return result


def invoke(repo, repeats, *, instrument=False, variant='default'):
    command = [sys.executable, __file__, '--worker', str(repo), '--repeats', str(repeats), '--variant', variant]
    if instrument:command.append('--instrument')
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=600)
    if result.returncode:
        raise RuntimeError('Benchmark worker failed:\n'+result.stderr[-6000:])
    return json.loads(result.stdout)


def source_hashes(repo):
    files = sorted((repo/'jarvis/apps/jarvis/app').glob('*.py'))
    files.append(repo/'tools/simulate_jarvis_workflows.py')
    return {p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def compare(baseline, repeats, expected_engine):
    manifest_bytes = (baseline/'data/catalog/repository_manifest.json').read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != BASELINE_MANIFEST_SHA256:
        raise ValueError('Baseline manifest differs from the pinned commit.')
    expected = {entry['path']:entry['sha256'] for entry in json.loads(manifest_bytes)['files']}
    for path, digest in source_hashes(baseline).items():
        if expected.get(path) != digest:
            raise ValueError('Baseline source differs from the pinned manifest: '+path)
    rounds = []
    for index, (label, repo) in enumerate((('baseline',baseline),('candidate',ROOT),
                                          ('candidate',ROOT),('baseline',baseline))):
        result = invoke(repo, repeats)
        if expected_engine and result['engine'] != expected_engine:
            raise AssertionError(f'{label}: expected {expected_engine}, got {result["engine"]}')
        rounds.append({'index':index, 'label':label, **result})
    summary = {}
    for label in ('baseline','candidate'):
        samples = [s for r in rounds if r['label']==label for s in r['samples']]
        summary[label] = {scope:{field:distribution([s[field] for s in samples if scope=='all' or
                            s['views']==(1 if scope=='one_view' else 3)])
                            for field in ('submit_ms','synthetic_receipt_ms')}
                          for scope in ('all','one_view','three_views')}
    gains = {scope:{metric:100*(1-summary['candidate'][scope]['synthetic_receipt_ms'][metric]/
                               summary['baseline'][scope]['synthetic_receipt_ms'][metric])
                    for metric in ('p50_ms','p95_ms','p99_ms')}
             for scope in ('all','one_view','three_views')}
    profiles = {label:invoke(repo, 3, instrument=True) for label,repo in (('baseline',baseline),('candidate',ROOT))}
    ablations = {variant:invoke(ROOT, 3, variant=variant) for variant in ('pool_sync','no_pool_exit')}
    return {'schema':'bojart.latency.abba.v1', 'created_at':datetime.now(timezone.utc).isoformat(),
            'baseline_sha':BASELINE_SHA, 'environment':{'platform':platform.platform(), 'python':sys.version,
                'sqlite':sqlite3.sqlite_version, 'langgraph':next((d.version for d in importlib.metadata.distributions()
                             if d.metadata['Name']=='langgraph'), None)},
            'scope':{'audio':False,'http':False,'browser':False,'gpu_or_llm':False,'physical_machine':False,
                     'receipts':'synthetic', 'independent_hosts':1,
                     'method':'ABBA; fresh child process and temporary database per block; first turn retained',
                     'profile_caveat':'instrumented phases overlap SQL; do not sum profiles or compare their latency to ABBA'},
            'source_sha256':{'baseline':source_hashes(baseline),'candidate':source_hashes(ROOT)},
            'summary':summary,'receipt_reduction_percent':gains,'rounds':rounds,
            'profiles':profiles,'exploratory_ablations':ablations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--repeats',type=int,default=30)
    parser.add_argument('--expected-engine',choices=['sqlite_ready','missing_dependency'])
    parser.add_argument('--worker',type=Path)
    parser.add_argument('--instrument',action='store_true')
    parser.add_argument('--variant',choices=['default','pool_sync','no_pool_exit'],default='default')
    args = parser.parse_args()
    if not 1 <= args.repeats <= 100:parser.error('--repeats must be in 1..100')
    if args.worker:
        print(json.dumps(worker(args.worker.resolve(), args.repeats, args.instrument, args.variant), ensure_ascii=False))
        return
    if not args.baseline or not args.output:parser.error('--baseline and --output required')
    if args.output.exists():parser.error('output already exists; keep earlier evidence')
    report = compare(args.baseline.resolve(), args.repeats, args.expected_engine)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as file:json.dump(report,file,ensure_ascii=False,indent=2)
    print(json.dumps({'summary':report['summary'],'receipt_reduction_percent':report['receipt_reduction_percent']},indent=2))


if __name__ == '__main__':main()
