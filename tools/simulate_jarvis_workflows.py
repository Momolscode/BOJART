#!/usr/bin/env python3
"""Reproducible transcript -> runtime trials and synthetic fleet planning.

Uses real Store/DisplayProposals/ControlTower/JarvisRuntime, but a minimal server
fixture and direct synthetic acknowledgements. Does not start HTTP, a browser,
audio, Ollama, Jev, a slicer or a printer. Every SQLite database is temporary.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import platform
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'jarvis/apps/jarvis/app'
sys.path.insert(0, str(APP))
from core import Store, Rejected
from control_tower import ControlTower
from display_contracts import DisplayProposals
from fleet_simulation import preparation_requirements, schedule
from jarvis_runtime import JarvisRuntime
from jev_decider import JevDecider
from tower_events import TowerEvents

PHRASES = [
    ('Affiche le planning à gauche', 'planning', 'atelier'),
    ('Montre les dossiers au centre', 'workspace', 'pilotage'),
    ('Ouvre la tour de contrôle', 'tower', 'three'),
    ('Jarvis, affiche le dashboard atelier !', 'planning', 'atelier'),
    ('Affiche le dashboard dossiers', 'workspace', 'pilotage'),
    ('Affiche le dashboard Studio', 'studio', 'creation'),
    ('Affiche le dashboard contenus', 'growth', 'creation'),
    ('Affiche le dashboard conception', 'cad', 'pilotage'),
    ('Affiche les trois dashboards', 'tower', 'three'),
]


def stats(values):
    values = sorted(values)
    return {'count':len(values), 'p50_ms':values[(len(values)-1)//2],
            'p95_ms':values[math.ceil(.95*len(values))-1], 'max_ms':values[-1]}


class RuntimeFixture:
    """Only server peripherals are fixtures. Routing, guards and SQL are real."""
    def __init__(self, state_root=None, runtime_options=None):
        self.runtime_options = runtime_options or {}
        self.tmp = tempfile.TemporaryDirectory(prefix='bojart-workflow-simulation-') if state_root is None else None
        root = Path(self.tmp.name) if self.tmp else Path(state_root)
        root.mkdir(parents=True, exist_ok=True)
        context = root/'context.json'
        if not context.exists():context.write_text('{"data_kind":"synthetic_test_context"}', encoding='utf-8')
        store = Store(root/'state', context)
        display = DisplayProposals(store)
        self.server = SimpleNamespace(store=store, display=display, tower=ControlTower(store, display),
            workspace=SimpleNamespace(closing=False), events=TowerEvents(),
            voice=SimpleNamespace(status=lambda:{'enabled':False, 'fixture':True}))
        self.restart()
        self.screens = {role:self.server.tower.pair(role, 'synthetic receipt client')['screen_id']
                        for role in ('atelier', 'pilotage', 'creation')}

    def restart(self):
        if hasattr(self, 'runtime'):self.runtime.close()
        self.runtime = JarvisRuntime(self.server, decider=JevDecider(enabled=False, key=''), **self.runtime_options)

    def request(self, text='Montre les dossiers au centre', **kw):
        data = dict(request_id='test_'+uuid.uuid4().hex, client_id='fixture', project_id='BOJ-PILOTE-001',
                    revision=0, text=text, operation_id=None, source='voice')
        data.update(kw);return data

    def receive(self, role, outcome='rendered'):
        screen = self.screens[role]
        command = self.server.tower.poll(screen)['command']
        if command is not None:
            self.server.tower.ack(screen, command['request_id'], outcome, 'synthetic client receipt; no browser rendered')
        return command

    def count(self):
        with self.server.tower.db() as db:return db.execute('SELECT COUNT(*) FROM commands').fetchone()[0]

    def close(self):
        self.runtime.close();self.server.events.close()
        if self.tmp:self.tmp.cleanup()

    def __enter__(self):return self
    def __exit__(self, *args):self.close()


def transcript_trials(repeats):
    samples, traces, submit_ms, receipt_ms = [], [], [], []
    with RuntimeFixture() as fixture:
        engine = fixture.runtime.graph_status
        for repeat in range(repeats):
            for text, choice, role in PHRASES:
                request = fixture.request(text)
                before = fixture.count()
                start = time.perf_counter_ns()
                result = fixture.runtime.submit(request)
                dispatched = time.perf_counter_ns()
                check(result['status']=='QUEUED' and result['decision']['choice']==choice, text)
                check(result['elapsed_to_display_ms'] is None, 'no premature receipt')
                roles = ('atelier','pilotage','creation') if role=='three' else (role,)
                for target in roles:
                    command = fixture.receive(target)
                    check(command is not None and command['target_role']==target, 'correct view')
                receipt = fixture.runtime.get(request['request_id'])
                end = time.perf_counter_ns()
                check(receipt['display']['state']=='rendered', 'synthetic receipt persisted')
                check(fixture.count()-before==len(roles), 'exact command count')
                submit = (dispatched-start)/1e6;total=(end-start)/1e6
                submit_ms.append(submit);receipt_ms.append(total)
                samples.append({'repeat':repeat, 'text':text, 'choice':choice, 'views':len(roles),
                                'submit_ms':submit, 'synthetic_receipt_ms':total, 'passed':True})
                if repeat==0:
                    traces.append({'transcript':text, 'decision':receipt['decision'], 'status':receipt['status'],
                                   'message':receipt['message'], 'roles':list(roles), 'receipt':'synthetic_rendered',
                                   'physical_display_verified':False})
    return {'engine':engine, 'unique_phrases':len(PHRASES), 'trials':len(samples),
            'submit':stats(submit_ms), 'through_synthetic_receipt':stats(receipt_ms),
            'samples':samples, 'traces':traces}


def check(condition, label):
    if not condition:raise AssertionError(label)


def guard_trials():
    results = []
    def run(label, fn):
        with RuntimeFixture() as fixture:
            detail = fn(fixture)
            results.append({'case':label, 'passed':True, 'detail':detail})

    for text in ('Affiche un des dashboards', 'Affiche le modèle à droite',
                 'Prépare un Végéta 3D d’un mètre de haut à répartir sur toutes les imprimantes',
                 'Lance toutes les impressions', "N’affiche pas le dashboard Studio",
                 'Affiche le dashboard Studio et imprime tout'):
        def refused(f, text=text):
            r=f.runtime.submit(f.request(text));check(r['status']=='CLARIFY' and f.count()==0, text)
            return {'status':r['status'], 'reply':r['message'], 'dispatched':f.count()}
        run(text, refused)

    def stale(f):
        r=f.runtime.submit(f.request(revision=99));check(r['status']=='STALE' and f.count()==0, 'stale revision')
        return r['status']
    run('revision_changed', stale)
    def context(f):
        old=f.server.display.context_hash();f.server.store.context_path.write_text('{}', encoding='utf-8')
        r=f.runtime.submit(f.request(context_sha256=old));check(r['status']=='STALE' and f.count()==0, 'frozen context')
        return r['status']
    run('context_changed_after_listening', context)
    def replay(f):
        data=f.request();f.runtime.submit(data);f.runtime.submit(data);f.restart();f.runtime.submit(data)
        check(f.count()==1, 'replay/restart duplicate');return {'attempts':3, 'commands':f.count()}
    run('lost_response_then_restart_same_id', replay)
    def conflict(f):
        data=f.request();f.runtime.submit(data)
        try:f.runtime.submit({**data,'text':'Ouvre le studio'})
        except Rejected:return 'rejected'
        raise AssertionError('conflicting id accepted')
    run('same_id_different_request', conflict)
    def partial(f):
        data=f.request('Ouvre la tour de contrôle');original=f.server.tower.dispatch;calls=[]
        def fail_second(rid):
            calls.append(rid)
            if len(calls)==2:raise OSError('injected response loss')
            return original(rid)
        with patch.object(f.server.tower, 'dispatch', side_effect=fail_second):first=f.runtime.submit(data)
        check(first['status']=='INTERRUPTED' and f.count()==1, 'partial delivery')
        second=f.runtime.submit(data)
        check(second['status']=='QUEUED' and f.count()==3, 'reconcile scene')
        check(calls[0] in [r['request_id'] for r in second['displays']], 'same child IDs')
        return {'first':first['status'],'resumed':second['status'],'commands':f.count()}
    run('partial_scene_delivery', partial)
    def missing(f):
        data=f.request('Ouvre la tour de contrôle');f.runtime.submit(data)
        for role in ('atelier','pilotage'):f.receive(role)
        partial=f.runtime.get(data['request_id'])['display']
        check(partial['state']!='rendered' and partial['rendered_views']==2, 'missing view cannot succeed')
        f.receive('creation');r=f.runtime.get(data['request_id'])
        check(r['display']['rendered_views']==3 and f.count()==3, 'reconnected view')
        return {'before':'2/3', 'after':'3/3', 'duplicate_commands':0}
    run('one_view_absent_then_returns', missing)
    def failed(f):
        data=f.request('Ouvre la tour de contrôle');f.runtime.submit(data);f.receive('atelier','failed')
        check(f.runtime.get(data['request_id'])['display']['state']=='failed', 'failed view')
        return 'failed, never complete'
    run('failed_view', failed)
    def cancel(f):
        data=f.request();f.runtime.submit(data);f.runtime.cancel(data['request_id'],data['client_id'])
        check(f.receive('pilotage') is None, 'cancelled view');return 'cancelled before receipt'
    run('cancel_pending', cancel)
    def project(f):
        f.server.store.create_project('BOJ-OTHER','Other fixture')
        screen=f.server.tower.pair('pilotage', project_id='BOJ-OTHER')
        f.runtime.submit(f.request());check(f.server.tower.poll(screen['screen_id'])['command'] is None, 'project isolation')
        check(f.receive('pilotage') is not None, 'original project delivery');return 'isolated'
    run('other_project_screen', project)
    def stale_ack(f):
        data=f.request();f.runtime.submit(data);sid=f.screens['pilotage'];f.server.tower.poll(sid)
        f.server.store.context_path.write_text('{}', encoding='utf-8')
        try:f.server.tower.ack(sid,data['request_id'],'rendered','synthetic late receipt')
        except Rejected:
            check(f.runtime.get(data['request_id'])['display']['state']=='stale', 'late receipt persisted')
            return 'stale receipt rejected'
        raise AssertionError('late receipt accepted')
    run('context_changed_before_ack', stale_ack)
    return results


def fleet_trials(data):
    start=time.perf_counter_ns();planned=schedule(data);elapsed=(time.perf_counter_ns()-start)/1e6
    simple=schedule(data, strategy='round_robin')
    check(planned['status']=='SIMULATION_ONLY' and len(planned['jobs'])==len(data['parts']), 'all synthetic jobs planned')
    offline=copy.deepcopy(data);offline['printers'][0]['online']=False
    offline_plan=schedule(offline)
    check(offline_plan['status']=='SIMULATION_ONLY' and all(j['printer_id']!=offline['printers'][0]['id'] for j in offline_plan['jobs']), 'offline exclusion')
    impossible=copy.deepcopy(data);impossible['parts'][0]['bbox_mm']=[1000,1000,1000]
    impossible_plan=schedule(impossible);check(impossible_plan['status']=='INFEASIBLE' and not impossible_plan['jobs'], 'oversized part')
    unknown=copy.deepcopy(data);unknown['parts'][0]['state']='unknown'
    unknown_plan=schedule(unknown);check(unknown_plan['status']=='NEEDS_RECONCILIATION' and not unknown_plan['jobs'], 'unknown print not repeated')
    incompatible=copy.deepcopy(data);incompatible['parts'][0]['process']='RESIN'
    incompatible_plan=schedule(incompatible);check(incompatible_plan['status']=='INFEASIBLE', 'FDM cannot replace resin')
    changed=copy.deepcopy(data);changed['target_height_mm']=1200
    try:schedule(changed)
    except Rejected:height_rejected=True
    else:height_rejected=False
    check(height_rejected, 'new height requires new slicing')
    return {'planning_compute_ms':elapsed, 'intake':preparation_requirements('Végéta',1000),
            'baseline':simple, 'balanced':planned, 'one_printer_offline_before_start':offline_plan,
            'oversized_part':impossible_plan, 'lost_print_receipt':unknown_plan,
            'incompatible_process':incompatible_plan, 'changed_height_rejected':height_rejected,
            'comparison':{'reduction_vs_round_robin_percent':100*(simple['makespan_min']-planned['makespan_min'])/simple['makespan_min'],
                          'scope':'synthetic schedule only; not a real print time or universal speedup'}}


def run(repeats=30):
    if type(repeats) is not int or not 1 <= repeats <= 100:raise ValueError('repeats must be 1..100')
    fixture_path=ROOT/'jarvis/fixtures/fleet_1000mm_synthetic.json'
    data=json.loads(fixture_path.read_text(encoding='utf-8'))
    source_paths=[Path(__file__).relative_to(ROOT), fixture_path.relative_to(ROOT)]
    source_paths += [p.relative_to(ROOT) for p in sorted(APP.glob('*.py')) if p.name in (
        'core.py','dialogue.py','control_tower.py','display_contracts.py','jarvis_runtime.py',
        'jev_decider.py','tower_events.py','fleet_simulation.py','sqlite_sessions.py')]
    report={'schema':'bojart.workflow-simulation.v1', 'created_at':datetime.now(timezone.utc).isoformat(),
            'host':{'os':platform.system(),'python':platform.python_version(),'machine':platform.machine()},
            'scope':{'transcripts':'synthetic post-ASR text', 'sqlite':'real temporary databases',
                     'server':'minimal fixture, no HTTP', 'display_receipts':'synthetic direct acknowledgements, no browser',
                     'audio_measured':False, 'llm_measured':False, 'jev_enabled':False,
                     'gpu_measured':False, 'printers':'fictitious, no network or device commands',
                     'vegeta_mesh_created':False, 'production_ready':False},
            'source_sha256':{p.as_posix():hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths}}
    report['transcripts']=transcript_trials(repeats)
    report['guards']=guard_trials()
    report['fleet']=fleet_trials(data)
    report['ok']=True
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,default=30)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output and args.output.exists():parser.error('Le rapport existe déjà ; choisir un nouveau chemin.')
    report=run(args.repeats)
    raw=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8',newline='\n') as stream:stream.write(raw)
        print(str(args.output.resolve()))
    else:print(raw)
    return 0


if __name__=='__main__':raise SystemExit(main())
