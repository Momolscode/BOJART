"""Workflow and scheduling contracts. No ASR, LLM, browser or machine doubles hidden."""
import copy
import itertools
import json
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from simulate_jarvis_workflows import RuntimeFixture, guard_trials, transcript_trials, fleet_trials
from fleet_simulation import schedule, preparation_requirements
from core import Rejected
from jarvis_runtime import ALIASES, COMMANDS, AMBIGUOUS_DASHBOARDS
from jev_decider import JevDecider


def fixture():
    return json.loads((ROOT/'jarvis/fixtures/fleet_1000mm_synthetic.json').read_text(encoding='utf-8'))


class TranscriptTests(unittest.TestCase):
    def test_all_local_aliases_and_ambiguities_bypass_provider(self):
        with RuntimeFixture() as app:
            app.runtime.decider=JevDecider(enabled=True,key='test-only',transport=lambda _:self.fail('unexpected provider'))
            # Mocking decide itself also catches attempts whose exceptions the adapter would absorb.
            with patch.object(app.runtime.decider,'decide',side_effect=AssertionError('provider must be bypassed')) as decide:
                for text, choice in ALIASES.items():
                    with self.subTest(text=text):
                        r=app.runtime.submit(app.request(text))
                        self.assertEqual(r['decision']['choice'],choice)
                        self.assertEqual(r['status'],'CLARIFY' if choice=='model' else 'QUEUED')
                before=app.count()
                for text in AMBIGUOUS_DASHBOARDS:
                    r=app.runtime.submit(app.request(text));self.assertEqual(r['status'],'CLARIFY')
                    self.assertIn('Quel tableau de bord',r['message'])
                self.assertEqual(app.count(),before);self.assertEqual(decide.call_count,0)

    def test_end_to_end_python_trials(self):
        result=transcript_trials(2)
        self.assertEqual(result['trials'],18)
        self.assertTrue(all(s['synthetic_receipt_ms']>=s['submit_ms'] for s in result['samples']))

    def test_failure_and_recovery_scenarios(self):
        result=guard_trials();self.assertEqual(len(result),16)
        self.assertTrue(all(r['passed'] for r in result))


class FleetTests(unittest.TestCase):
    def test_intake_never_claims_geometry_or_voice(self):
        r=preparation_requirements('Végéta',1000)
        self.assertEqual(r['status'],'NEEDS_INPUT');self.assertEqual(len(r['missing']),4)
        self.assertFalse(r['mesh_created']);self.assertFalse(r['spoken_command_connected'])

    def test_eight_machine_example_and_failures(self):
        r=fleet_trials(fixture())
        self.assertEqual(r['balanced']['printers_used'],8)
        self.assertEqual(len(r['balanced']['jobs']),24)
        self.assertEqual(r['one_printer_offline_before_start']['printers_used'],7)

    def test_input_is_unchanged_and_results_deterministic(self):
        data=fixture();original=copy.deepcopy(data);a=schedule(data);b=schedule(data)
        self.assertEqual(data,original);self.assertEqual(a,b)

    def test_duplicate_identifiers_rejected(self):
        for key in ('printers','parts'):
            data=fixture();data[key][1]['id']=data[key][0]['id']
            with self.subTest(key=key),self.assertRaises(Rejected):schedule(data)

    def test_nonfinite_bool_and_zero_dimensions_rejected(self):
        for value in (float('nan'),float('inf'),-1,0,True,'100'):
            data=fixture();data['parts'][0]['bbox_mm'][0]=value
            with self.subTest(value=value),self.assertRaises(Rejected):schedule(data)

    def test_nonfinite_bool_and_zero_durations_rejected(self):
        for value in (float('nan'),float('inf'),-1,0,True):
            data=fixture();data['parts'][0]['minutes_by_printer']['SIM-FDM-01']=value
            with self.subTest(value=value),self.assertRaises(Rejected):schedule(data)

    def test_real_data_is_not_silently_accepted(self):
        data=fixture();data['data_kind']='real_inventory'
        with self.assertRaises(Rejected):schedule(data)

    def one(self):
        data=fixture();data['printers']=data['printers'][:1];data['parts']=data['parts'][:1]
        data['parts'][0]['minutes_by_printer']={'SIM-FDM-01':60}
        return data

    def test_box_clearance_boundary(self):
        data=self.one();data['parts'][0]['bbox_mm']=[250,250,290]
        self.assertEqual(schedule(data)['status'],'SIMULATION_ONLY')
        data['parts'][0]['bbox_mm'][0]=250.01
        self.assertEqual(schedule(data)['status'],'INFEASIBLE')

    def test_circular_plate_rejects_corners(self):
        data=self.one();data['printers'][0]['volume']={'shape':'cylinder','diameter':200,'z':300}
        data['parts'][0]['bbox_mm']=[150,150,100]
        self.assertEqual(schedule(data)['status'],'INFEASIBLE')
        data['parts'][0]['bbox_mm']=[100,100,100]
        self.assertEqual(schedule(data)['status'],'SIMULATION_ONLY')

    def test_missing_estimate_has_no_default(self):
        data=self.one();data['parts'][0]['minutes_by_printer']={}
        r=schedule(data);self.assertEqual(r['status'],'INFEASIBLE')
        self.assertEqual(r['excluded_candidates']['SIM-PART-01']['SIM-FDM-01'],'missing_time_estimate')

    def test_all_offline_and_material_mismatch_block(self):
        for field, value in (('online',False),('materials',['PETG'])):
            data=self.one();data['printers'][0][field]=value
            self.assertEqual(schedule(data)['status'],'INFEASIBLE')

    def test_new_height_requires_new_parts_and_times(self):
        data=fixture();data['target_height_mm']=1200
        with self.assertRaises(Rejected):schedule(data)

    def test_unknown_or_active_part_prevents_automatic_reprint(self):
        for state in ('unknown','printing'):
            data=fixture();data['parts'][0]['state']=state;r=schedule(data)
            self.assertEqual(r['status'],'NEEDS_RECONCILIATION');self.assertEqual(r['jobs'],[])

    def test_completed_parts_excluded(self):
        data=fixture();data['parts'][0]['state']='completed';r=schedule(data)
        self.assertEqual(len(r['jobs']),23)
        self.assertNotIn('SIM-PART-01',[j['part_id'] for j in r['jobs']])
        for part in data['parts']:part['state']='completed'
        r=schedule(data);self.assertEqual(r['makespan_min'],0);self.assertEqual(r['jobs'],[])

    def test_turnaround_and_existing_work_included(self):
        data=self.one();data['parts'].append({**copy.deepcopy(data['parts'][0]),'id':'second'})
        data['printers'][0]['ready_after_min']=120
        r=schedule(data)
        self.assertEqual([j['start_min'] for j in r['jobs']],[120,195])
        self.assertEqual(r['makespan_min'],255)

    def test_lower_bound_does_not_exceed_enumerated_optimum(self):
        data=self.one();data['printers'].append({**copy.deepcopy(data['printers'][0]),'id':'second'})
        for p in data['printers']:p['turnaround_min']=0;p['ready_after_min']=0
        data['parts']=[{**copy.deepcopy(data['parts'][0]),'id':f'job{i}',
                       'minutes_by_printer':dict(zip(('SIM-FDM-01','second'),times))}
                       for i,times in enumerate(((10,13),(7,9),(4,6),(14,8)))]
        optimum=min(max(sum(p['minutes_by_printer']['SIM-FDM-01'] for p,a in zip(data['parts'],assignment) if a==0),
                        sum(p['minutes_by_printer']['second'] for p,a in zip(data['parts'],assignment) if a==1))
                    for assignment in itertools.product(range(2),repeat=4))
        r=schedule(data)
        self.assertLessEqual(r['optimistic_lower_bound_min'],optimum)
        self.assertGreaterEqual(r['makespan_min'],optimum)

    def test_seeded_variable_durations_preserve_schedule_invariants(self):
        rng=random.Random(20261102)
        for sample in range(40):
            data=fixture()
            for printer in data['printers']:
                printer['ready_after_min']=rng.randint(0,400)
                printer['turnaround_min']=rng.randint(0,30)
            for part in data['parts']:
                part['minutes_by_printer']={p['id']:rng.randint(15,900) for p in data['printers']}
            for strategy in ('earliest_finish','round_robin'):
                r=schedule(data,strategy=strategy)
                self.assertEqual(len({j['part_id'] for j in r['jobs']}),24)
                self.assertFalse(r['can_print']);self.assertFalse(r['geometry_checked'])
                self.assertLessEqual(r['optimistic_lower_bound_min'],r['makespan_min'])
                for printer in data['printers']:
                    jobs=sorted((j for j in r['jobs'] if j['printer_id']==printer['id']),key=lambda j:j['start_min'])
                    after=printer['ready_after_min']
                    for job in jobs:
                        self.assertGreaterEqual(job['start_min'],after)
                        self.assertEqual(job['finish_min']-job['start_min'],job['assumed_duration_min'])
                        after=job['finish_min']+printer['turnaround_min']


if __name__=='__main__':unittest.main()
