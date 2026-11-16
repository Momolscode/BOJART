import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bojart_ops.qualification import load_qualification, qualify_plan, runtime_gates

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'docs/research/launch-toolchain-2026-11-01'


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.tools = json.loads((FOLDER / 'TOOLCHAIN.json').read_text(encoding='utf-8'))
        self.data = json.loads((FOLDER / 'DATA_REQUIREMENTS.json').read_text(encoding='utf-8'))
        self.acceptance = json.loads((FOLDER / 'ACCEPTANCE.json').read_text(encoding='utf-8'))
        self.config = json.loads((ROOT / 'ops/orchestration.json').read_text(encoding='utf-8'))
        self.gates = runtime_gates((ROOT / self.config['qualification_sources']['runtime_gates']).read_text(encoding='utf-8'))

    def plan(self):
        return qualify_plan(self.tools, self.data, self.acceptance, self.gates, self.config['tasks'])

    def test_live_catalogs_link_every_gate_without_qualifying_any(self):
        result = self.plan()
        self.assertEqual(result['summary'], {'tool_records': 26, 'data_requirements': 14,
                         'runtime_gates': 12, 'target_gates_qualified_by_this_report': 0})
        self.assertFalse(result['target_production_qualified'])
        self.assertEqual(result['tools_executed'], 0)
        self.assertTrue(all(g['task_ids'] for g in result['gates']))

    def test_collect_priority_uses_real_dependency_counts(self):
        result = self.plan()
        top = result['datasets'][0]
        self.assertEqual(top['id'], 'printer_profiles')
        self.assertEqual(top['gate_count'], 4)
        self.assertEqual(set(top['gate_ids']), {'cad_runtime', 'printer_fdm', 'printer_resin', 'production_safety'})

    def test_excluded_and_deferred_tools_do_not_inflate_priority(self):
        result = self.plan()
        social = next(d for d in result['datasets'] if d['id'] == 'social_metrics')
        self.assertNotIn('metricool', social['active_tool_ids'])
        self.assertIn('metricool', social['deferred_tool_ids'])
        printer = next(d for d in result['datasets'] if d['id'] == 'printer_profiles')
        self.assertNotIn('ortools', printer['active_tool_ids'])

    def test_actual_values_never_enter_derived_report(self):
        self.data['datasets'][0]['values'] = {'credential': 'PRIVATE_FIXTURE_VALUE'}
        self.assertNotIn('PRIVATE_FIXTURE_VALUE', json.dumps(self.plan()))

    def test_unknown_tool_data_refused(self):
        self.tools['tools'][0]['required_datasets'].append('unknown')
        with self.assertRaises(ValueError):
            self.plan()

    def test_unknown_acceptance_data_refused(self):
        self.acceptance['tests'][0]['required_datasets'].append('unknown')
        with self.assertRaises(ValueError):
            self.plan()

    def test_runtime_gate_addition_cannot_silently_escape_plan(self):
        self.gates['new_runtime_gate'] = ('New', 'Requires proof')
        with self.assertRaises(ValueError):
            self.plan()

    def test_missing_task_binding_refused(self):
        for task in self.config['tasks']:
            task['qualification_gates'] = [x for x in task.get('qualification_gates', []) if x != 'restore_drill']
        with self.assertRaises(ValueError):
            self.plan()

    def test_duplicates_rejected_in_each_catalog(self):
        for obj, key in ((self.tools, 'tools'), (self.data, 'datasets'), (self.acceptance, 'tests')):
            with self.subTest(key=key):
                obj[key].append(copy.deepcopy(obj[key][0]))
                with self.assertRaises(ValueError):
                    self.plan()
                obj[key].pop()

    def test_mutable_repo_reference_refused(self):
        self.tools['tools'][0]['examined_commit'] = 'main'
        with self.assertRaises(ValueError):
            self.plan()

    def test_proposals_cannot_fake_target_completion(self):
        for key, value in (('status', 'passed'), ('evidence', {'result': 'success'})):
            old = self.acceptance['tests'][0][key]
            self.acceptance['tests'][0][key] = value
            with self.assertRaises(ValueError):
                self.plan()
            self.acceptance['tests'][0][key] = old
        next(t for t in self.config['tasks'] if t['id'] == 'target-install')['status'] = 'done'
        with self.assertRaises(ValueError):
            self.plan()

    def test_runtime_declaration_does_not_execute_module(self):
        source = "raise RuntimeError('must not execute')\nREQUIRED_GATES={'x': ('Name', 'Criterion')}\n"
        self.assertEqual(runtime_gates(source), {'x': ('Name', 'Criterion')})
        for source in ("REQUIRED_GATES=compute()", "REQUIRED_GATES={'x':('a','b'),'x':('c','d')}",
                       "REQUIRED_GATES={}\nREQUIRED_GATES={}"):
            with self.assertRaises(ValueError):
                runtime_gates(source)

    def test_rank_is_deterministic_and_inputs_unchanged(self):
        original = copy.deepcopy((self.tools, self.data, self.acceptance))
        first = self.plan()
        self.assertEqual(original, (self.tools, self.data, self.acceptance))
        self.data['datasets'].reverse()
        self.tools['tools'].reverse()
        self.acceptance['tests'].reverse()
        self.assertEqual(first, self.plan())

    def test_qualification_is_bound_to_audited_bytes(self):
        inventory = []
        for path in self.config['qualification_sources'].values():
            raw = (ROOT / path).read_bytes()
            inventory.append({'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        self.assertEqual(len(load_qualification(ROOT, {'files': inventory}, self.config)['sources']), 4)
        inventory[0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            load_qualification(ROOT, {'files': inventory}, self.config)

    def test_unsafe_source_path_refused(self):
        self.config['qualification_sources']['tools'] = '../outside.json'
        with self.assertRaises(ValueError):
            load_qualification(ROOT, {'files': []}, self.config)

    def test_absent_integration_config_remains_compatible(self):
        self.assertIsNone(load_qualification(ROOT, {'files': []}, {}))


if __name__ == '__main__':
    unittest.main()
