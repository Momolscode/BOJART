"""Benchmark accounting and isolated real memory/fault execution."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bojart_memory.agent import REPO
from bojart_memory.benchmarks import distribution, model_trials, run_memory
from tests_agent.test_model_qualification import LocalModelServer
from tools.benchmark_jarvis import main


class BenchmarkTests(unittest.TestCase):
    def test_quantiles_keep_samples_and_do_not_invent_empty_measurements(self):
        summary = distribution(list(range(1, 101)))
        self.assertEqual(summary['p50'], 50.5)
        self.assertEqual(summary['p95'], 95)
        self.assertEqual(summary['n'], 100)
        self.assertIsNone(distribution([])['p95'])
        for invalid in ([float('nan')], [float('inf')], [-1], [True]):
            with self.subTest(values=invalid), self.assertRaises(ValueError):
                distribution(invalid)

    def test_small_complete_simulation_keeps_live_memory_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            live = Path(directory) / 'private-memory'
            live.mkdir()
            sentinel = live / 'sentinel.txt'
            sentinel.write_text('private original', encoding='utf-8')
            with patch.dict('os.environ', {'BOJART_MEMORY_STATE': str(live)}), \
                    patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
                report = run_memory(REPO, repeats=1, scales=(6, 12), workers=2, operations=10, crashes=1)
            self.assertTrue(report['ok'])
            self.assertEqual(list(live.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_text(), 'private original')
        self.assertFalse(report['llm_inference'])
        self.assertEqual(report['scale']['mixed_load']['operations'], 10)
        self.assertEqual(report['scale']['mixed_load']['successes'], 10)
        self.assertEqual(report['scale']['backup_restore']['persisted_notes'], 2)
        self.assertEqual(report['faults']['forced_process_stops'], 2)
        self.assertEqual(report['faults']['attempts'], 5)
        self.assertEqual(report['repository']['search_ms']['n'], 14)

    def test_invalid_workloads_fail_before_state_or_network(self):
        for arguments in ({'repeats': 0}, {'workers': 17}, {'scales': (100, 10)},
                          {'crashes': 0}, {'operations': 1}, {'scales': (True,)}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                run_memory(**arguments)

    def test_model_benchmark_excludes_first_call_and_never_activates(self):
        server = LocalModelServer()
        self.addCleanup(server.close)
        with patch('bojart_memory.model_setup.pull_candidate', side_effect=AssertionError('download')), \
                patch('bojart_memory.model_config.save_config', side_effect=AssertionError('configuration')):
            report = model_trials(repeats=4, url=server.url)
        self.assertTrue(report['ok'])
        self.assertEqual(report['followup_ms']['n'], 4)
        self.assertEqual(len(report['samples']), 5)
        self.assertEqual(report['tokens_per_second']['p50'], 40)
        self.assertEqual(report['completed_followups'], report['requested_followups'])
        self.assertEqual(report['literal_checks_passed'], 4)
        self.assertIsNone(report['first_token_ms'])
        self.assertFalse(report['production_ready'])

    def test_model_failure_does_not_become_a_fast_success(self):
        server = LocalModelServer()
        self.addCleanup(server.close)
        server.invalid_chat = True
        report = model_trials(repeats=4, url=server.url)
        self.assertFalse(report['ok'])
        self.assertEqual(report['followup_ms']['n'], 0)
        self.assertIsNone(report['followup_ms']['p50'])
        self.assertEqual(report['completed_followups'], 0)
        self.assertEqual(report['requested_followups'], 4)

    def test_remote_inference_is_refused(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            result = model_trials(repeats=4, url='https://example.invalid')
        self.assertFalse(result['ok'])
        self.assertEqual(result['completed_followups'], 0)

    def test_cli_refuses_overwriting_a_report_before_starting_work(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            path.write_text('original', encoding='utf-8')
            with patch('tools.benchmark_jarvis.run_memory', side_effect=AssertionError('benchmark started')), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['--output', str(path)])
            self.assertEqual(path.read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
