import json
import tempfile
import unittest
from pathlib import Path

from bojart_memory import Memory
from bojart_memory.agent import AgentMemory

PROJECT = 'bojart.jarvis'


class SessionIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        (self.repo / 'data/knowledge').mkdir(parents=True)
        (self.repo / 'reference.md').write_text('restauration sauvegarde actuelle', encoding='utf-8')
        (self.repo / 'session.md').write_text(('restauration sauvegarde historique\n' * 300), encoding='utf-8')
        self.records = [
            {'project': PROJECT, 'path': 'reference.md', 'provenance': 'Current reference'},
            {'project': PROJECT, 'path': 'session.md', 'provenance': 'Historical log', 'collection': 'session_log'},
        ]
        self.write_index()
        self.agent = AgentMemory(self.root / 'state', repo=self.repo)

    def write_index(self):
        (self.repo / 'data/knowledge/index.json').write_text(json.dumps(self.records), encoding='utf-8')

    def test_session_stays_searchable_after_current_reference(self):
        self.agent.index()
        found = self.agent.search('restauration sauvegarde', PROJECT, limit=2)['results']
        self.assertEqual([r['source_path'] for r in found], ['reference.md', 'session.md'])
        self.assertEqual(found[1]['collection'], 'session_log')

    def test_export_does_not_label_history_as_research_or_current_state(self):
        self.agent.index()
        pack = self.agent.context('restauration sauvegarde', PROJECT)
        self.assertIn('JOURNAL DE SESSION : HISTORIQUE, PAS ÉTAT COURANT', pack['text'])
        self.assertNotIn('PROPOSITION DE RECHERCHE', pack['text'])
        self.assertTrue(any(e['collection'] == 'session_log' for e in pack['evidence']))

    def test_migration_retires_old_selection_without_deleting_history(self):
        self.records[1]['collection'] = 'canonical'; self.write_index(); self.agent.index()
        self.records[1]['collection'] = 'session_log'; self.write_index()
        result = self.agent.index()
        self.assertEqual(result['retired'][PROJECT], ['session.md'])
        with Memory(self.agent.state, readonly=True) as memory:
            rows = memory.search('historique', project=PROJECT, history=True)['results']
        self.assertEqual({r['collection'] for r in rows}, {'canonical', 'session_log'})
        self.assertEqual(self.agent.index()['new_versions'], 0)

    def test_removed_session_is_retired_but_recoverable(self):
        self.agent.index(); self.records = self.records[:1]; self.write_index()
        self.assertEqual(self.agent.index()['session_retired'][PROJECT], ['session.md'])
        with Memory(self.agent.state, readonly=True) as memory:
            self.assertFalse(memory.search('historique', project=PROJECT)['results'])
            self.assertTrue(memory.search('historique', project=PROJECT, history=True)['results'])

    def test_classification_survives_backup_restore(self):
        self.agent.index()
        before = self.agent.context('restauration sauvegarde', PROJECT)
        with Memory(self.agent.state, readonly=True) as memory:
            memory.backup(self.root / 'backup')
        Memory.restore(self.root / 'backup', self.root / 'restored')
        restored = AgentMemory(self.root / 'restored', repo=self.root / 'absent')
        self.assertEqual(before['evidence'], restored.context('restauration sauvegarde', PROJECT)['evidence'])


if __name__ == '__main__':
    unittest.main()
