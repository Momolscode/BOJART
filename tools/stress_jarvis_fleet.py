#!/usr/bin/env python3
"""Seeded offline scheduling experiments; boxes and durations are fictional.

Checks both heuristics against constraints and enumerates exact optima only for
small finite fixtures. Does not create a mesh, slice, contact or run a printer.
"""
import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'jarvis/apps/jarvis/app'))
from fleet_simulation import schedule


def stats(values):
    values = sorted(values)
    return {'count':len(values), 'min':values[0], 'median':values[(len(values)-1)//2],
            'p95':values[math.ceil(.95*len(values))-1], 'max':values[-1]}


def validate(data, result):
    assert result['status'] == 'SIMULATION_ONLY'
    assert not result['can_print'] and not result['geometry_checked']
    parts = {p['id']:p for p in data['parts']}
    printers = {p['id']:p for p in data['printers']}
    expected = {p['id'] for p in data['parts'] if p['state']=='unstarted'}
    assert len(result['jobs']) == len(expected)
    assert {j['part_id'] for j in result['jobs']} == expected
    assert all(j['printer_id'] in printers for j in result['jobs'])
    for pid, printer in printers.items():
        available = printer['ready_after_min']
        for job in sorted((j for j in result['jobs'] if j['printer_id']==pid),key=lambda j:j['start_min']):
            part = parts[job['part_id']]
            assert printer['online'] and part['process']==printer['process']
            assert part['material'] in printer['materials']
            x,y,z = part['bbox_mm'];v = printer['volume'];margin = printer['clearance_mm']*2
            assert z <= v['z']-margin
            assert ((x <= v['x']-margin and y <= v['y']-margin) if v['shape']=='box'
                    else math.hypot(x,y) <= v['diameter']-margin)
            assert job['start_min'] >= available
            assert job['finish_min']-job['start_min'] == part['minutes_by_printer'][pid]
            available = job['finish_min']+printer['turnaround_min']
    assert result['makespan_min'] == max((j['finish_min'] for j in result['jobs']),default=0)
    assert result['optimistic_lower_bound_min'] <= result['makespan_min']


def exact_tiny(data):
    """Enumerate all assignments; all tiny-case boxes/machines are compatible.

Order does not affect a machine's completion time in these fixtures: setup is a
constant per machine and there are no release times or assembly dependencies.
"""
    machines, parts = data['printers'], data['parts']
    best = math.inf
    for assignment in itertools.product(range(len(machines)), repeat=len(parts)):
        finish = []
        for i, machine in enumerate(machines):
            durations = [part['minutes_by_printer'][machine['id']] for part,m in zip(parts,assignment) if m==i]
            finish.append(machine['ready_after_min']+sum(durations)+(len(durations)-1)*machine['turnaround_min']
                          if durations else 0)
        best = min(best,max(finish))
    return best


def run(seed=20261102):
    if not __debug__:raise RuntimeError('Run without -O: invariant assertions must remain enabled.')
    source = ROOT/'jarvis/fixtures/fleet_1000mm_synthetic.json'
    template = json.loads(source.read_text(encoding='utf-8'))
    rng = random.Random(seed)
    samples, elapsed, exact_gaps = [], [], []
    wins = ties = losses = 0
    def compare(data, label, optimum=None):
        nonlocal wins, ties, losses
        results = {}
        for strategy in ('round_robin','earliest_finish'):
            start = time.perf_counter_ns();result = schedule(data,strategy=strategy)
            duration = (time.perf_counter_ns()-start)/1e6
            validate(data,result);elapsed.append(duration)
            if optimum is not None:
                assert result['optimistic_lower_bound_min'] <= optimum <= result['makespan_min']
            results[strategy] = {'makespan_min':result['makespan_min'],'compute_ms':duration}
        old = results['round_robin']['makespan_min'];new = results['earliest_finish']['makespan_min']
        wins += new < old;ties += new == old;losses += new > old
        gap = 100*(new-optimum)/optimum if optimum else None
        if gap is not None:exact_gaps.append(gap)
        samples.append({'case':label,'input_sha256':result['input_sha256'],
                        'machines':len(data['printers']),'parts':len(data['parts']),
                        'strategies':results,'enumerated_optimum_min':optimum,
                        'heuristic_gap_to_optimum_percent':gap})

    for i in range(300):
        data = copy.deepcopy(template)
        for j, printer in enumerate(data['printers']):
            printer['online'] = j==0 or rng.random()>.25
            printer['ready_after_min'] = rng.randint(0,720)
            printer['turnaround_min'] = rng.randint(0,40)
        for part in data['parts']:
            part['minutes_by_printer'] = {p['id']:rng.randint(15,900) for p in data['printers']}
        compare(data, 'variable_availability_'+str(i))

    for i in range(60):
        data = copy.deepcopy(template)
        count = 2+i%2
        data['printers'] = [{**copy.deepcopy(template['printers'][0]),'id':f'TINY-{j}',
                            'ready_after_min':rng.randint(0,30),'turnaround_min':rng.randint(0,10)}
                           for j in range(count)]
        data['parts'] = [{**copy.deepcopy(template['parts'][0]),'id':f'PART-{j}',
                         'minutes_by_printer':{p['id']:rng.randint(5,80) for p in data['printers']}}
                        for j in range(4+i%4)]
        compare(data, 'exact_small_'+str(i),exact_tiny(data))

    for machine_count in (1,8,16,32):
        for part_count in (24,100,500):
            data = copy.deepcopy(template)
            data['printers'] = [{**copy.deepcopy(template['printers'][0]),'id':f'SCALE-{j}'}
                               for j in range(machine_count)]
            data['parts'] = [{**copy.deepcopy(template['parts'][0]),'id':f'PART-{j}',
                             'minutes_by_printer':{p['id']:rng.randint(30,300) for p in data['printers']}}
                            for j in range(part_count)]
            compare(data, f'scale_{machine_count}x{part_count}')

    return {'schema':'bojart.fleet-stress.v1','seed':seed,
            'scope':'synthetic boxes and assumed minutes; no mesh, slicer, voice, printer or fabrication evidence',
            'environment':{'platform':platform.platform(),'python':platform.python_version()},
            'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (Path(__file__),source,ROOT/'jarvis/apps/jarvis/app/fleet_simulation.py')},
            'cases':len(samples),'schedules_checked':len(elapsed),'constraint_failures':0,
            'earliest_finish_vs_round_robin':{'wins':wins,'ties':ties,'losses':losses},
            'tiny_exact_optima':len(exact_gaps),'tiny_heuristic_gap_percent':stats(exact_gaps),
            'compute_ms':stats(elapsed),'samples':samples,
            'limits':['No universal optimality claim','Timing applies only to this host and these inputs',
                      'Availability and all durations are assumptions','Scale is scheduler size, not printer qualification']}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():parser.error('Choose a new output path; evidence is never overwritten.')
    report = run()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as file:json.dump(report,file,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k not in ('samples','source_sha256')},ensure_ascii=False,indent=2))
