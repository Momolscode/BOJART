import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bojart_memory import Memory
from tools import doctor

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = {'ok': True, 'voice_requested': False, 'voice': {'status': 'disabled'}}
IMPORTS_OK = {'status': 'checked', 'modules': {name: {'ok': True} for name in
              ('cadquery', 'trimesh', 'langgraph.graph', 'langgraph.checkpoint.sqlite')}}


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def report(self, **kwargs):
        with patch.object(doctor.importlib.metadata, 'version', return_value='fixture'), \
             patch.object(doctor.shutil, 'which', return_value='/fixture/tool'), \
             patch.object(doctor, 'configuration', return_value=SETTINGS):
            return doctor.report(memory_state=self.root/'memory', runtime_state=self.root/'work', **kwargs)

    def test_installed_metadata_does_not_prove_native_imports(self):
        result = self.report()
        self.assertTrue(result['memory_ready'])
        self.assertFalse(result['workstation_ready'])
        self.assertEqual(result['imports']['status'], 'not_checked')

    def test_broken_native_import_blocks_workstation(self):
        failed = {'status': 'checked', 'modules': {'cadquery': {'ok': False, 'error_type': 'OSError'}, 'trimesh': {'ok': True}}}
        with patch.object(doctor, 'runtime_probe', return_value=failed):
            result = self.report(probe_imports=True)
        self.assertIn('cad_runtime', result['workstation_blockers'])
        self.assertFalse(result['workstation_ready'])

    def test_healthy_software_keeps_hardware_unqualified(self):
        with patch.object(doctor, 'runtime_probe', return_value=IMPORTS_OK):
            result = self.report(probe_imports=True)
        self.assertTrue(result['workstation_ready'])
        self.assertFalse(result['physical_hardware_qualified'])
        self.assertFalse(result['production_ready'])
        self.assertEqual(result['provider_calls'], 0)

    def test_corrupt_stored_object_is_reported_before_launch(self):
        source = self.root/'note.md';source.write_text('Jev optionnel.')
        with Memory(self.root/'memory') as memory:
            result = memory.ingest_file(source, root=self.root, project='bojart.jarvis', collection='test', provenance='fixture')
            memory._object(result['sha256']).write_text('Une version altérée.')
        result = self.report(verify_memory=True)
        self.assertEqual(result['documentary_memory']['integrity'], 'failed')
        self.assertIn('memory_integrity_or_schema', result['launch_blockers'])

    def test_overlapping_state_is_rejected_without_creating_directories(self):
        result = doctor.report(memory_state=self.root/'work/memory', runtime_state=self.root/'work')
        self.assertIn('overlapping_memory_and_work_state', result['launch_blockers'])
        self.assertFalse((self.root/'work').exists())

    def test_explicit_missing_configuration_cannot_fall_back_silently(self):
        result = doctor.configuration(self.root/'missing.json')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error_type'], 'ExplicitConfigurationMissing')

    def test_diagnostic_never_calls_jev_or_exposes_key(self):
        private = 'fixture-private-value-that-must-never-be-printed'
        with patch.dict(os.environ, {'BOJ_JEV_ENABLED': '1', 'TYPESAFE_API_KEY': private}), \
             patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network forbidden')):
            result = doctor.configuration()
        self.assertTrue(result['jev_enabled'])
        self.assertTrue(result['jev_key_present'])
        self.assertNotIn(private, json.dumps(result))

    def test_check_only_launcher_does_not_initialize_or_start_server(self):
        env = dict(os.environ, BOJART_MEMORY_STATE=str(self.root/'selected-memory'),
                   BOJ_JEV_ENABLED='0', TYPESAFE_API_KEY='')
        run = subprocess.run([sys.executable, 'tools/start_jarvis.py', '--check-only',
                              '--state', str(self.root/'work')], cwd=ROOT, env=env,
                             capture_output=True, text=True, timeout=40)
        self.assertIn(run.returncode, (0, 2), run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report['imports']['status'], 'checked')
        self.assertEqual(report['provider_calls'], 0)
        self.assertFalse((self.root/'selected-memory').exists())
        self.assertFalse((self.root/'work').exists())


if __name__ == '__main__':
    unittest.main()
