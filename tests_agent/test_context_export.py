import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bojart_memory import Memory
from bojart_memory.agent import AgentMemory, REPO


class ContextExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agent = AgentMemory(self.root/'memory')
        self.agent.index()

    def test_manifest_keeps_verified_source_versions_and_fact_registry(self):
        pack = self.agent.context('Jev', 'bojart.jarvis')
        self.assertEqual(pack['schema'], 'bojart.agent-context.v2')
        self.assertEqual(pack['project'], 'bojart.jarvis')
        self.assertFalse(pack['trusted_instructions'])
        self.assertFalse(pack['facts_automatically_validated'])
        self.assertTrue(pack['evidence'])
        self.assertTrue(pack['reference_facts'])
        for evidence in pack['evidence']:
            self.assertEqual(evidence['project'], pack['project'])
            self.assertTrue(evidence['source_bytes_verified'])
            self.assertIn(evidence['citation'], pack['citations'])
            with Memory(self.agent.state, readonly=True) as memory:
                raw = memory._object(evidence['sha256']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), evidence['sha256'])
        for fact in pack['reference_facts']:
            self.assertEqual(fact['project'], 'bojart.jarvis')
            self.assertTrue(fact['registry_bytes_verified'])
            self.assertEqual(fact['registry_path'], 'data/knowledge/claims.jsonl')

    def test_text_budget_is_exact_and_json_metadata_budget_is_explicit(self):
        pack = self.agent.context('G2', 'bojart.creative', max_chars=3000)
        self.assertEqual(len(pack['text']), pack['characters'])
        self.assertLessEqual(pack['characters'], 3000)
        self.assertEqual(pack['budget_unit'], 'unicode_characters_of_text_only')
        self.assertEqual(hashlib.sha256(pack['text'].encode()).hexdigest(), pack['sha256'])
        self.assertTrue(all(e['citation'] in pack['text'] for e in pack['evidence']))

    def test_proposal_keeps_its_status_in_export(self):
        self.agent.note('machine.essai', 'Contrôle à réaliser', 'Proposition datée de recette', 'bojart.jarvis')
        pack = self.agent.context('machine essai', 'bojart.jarvis')
        proposed = next(f for f in pack['reference_facts'] if f['key'] == 'machine.essai')
        self.assertEqual(proposed['status'], 'proposal')
        self.assertIn('proposal', pack['text'])

    def test_export_survives_restart_and_backup_without_duplicate_versions(self):
        first = self.agent.context('Jev', 'bojart.jarvis')
        before = self.agent.status()['versions']
        reopened = AgentMemory(self.agent.state)
        self.assertEqual(reopened.index()['new_versions'], 0)
        self.assertEqual(reopened.status()['versions'], before)
        self.assertEqual(first['sha256'], reopened.context('Jev', 'bojart.jarvis')['sha256'])
        with Memory(self.agent.state, readonly=True) as memory:
            memory.backup(self.root/'snapshot')
        Memory.restore(self.root/'snapshot', self.root/'restored')
        restored = AgentMemory(self.root/'restored', repo=self.root/'absent-repo')
        self.assertEqual(first['evidence'], restored.context('Jev', 'bojart.jarvis')['evidence'])

    def test_cli_and_agent_share_environment_path_and_explicit_override(self):
        env = dict(os.environ, BOJART_MEMORY_STATE=str(self.root/'selected'))
        def run(module, *args):
            result = subprocess.run([sys.executable, '-m', module, *args], cwd=REPO, env=env,
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        run('bojart_memory', 'index-repo')
        run('bojart_memory.agent_cli', 'index')
        base = run('bojart_memory', 'stats')
        extended = run('bojart_memory.agent_cli', 'status')
        self.assertEqual(base['versions'], extended['versions'])
        self.assertEqual(base['sources'], extended['sources'])
        run('bojart_memory.agent_cli', '--state', str(self.root/'override'), 'index')
        self.assertTrue((self.root/'override/memory.sqlite').is_file())


if __name__ == '__main__':
    unittest.main()
