"""Research must remain searchable without displacing current reference sources."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bojart_memory import Memory, MemoryError
from bojart_memory.agent import AgentMemory, REPO
from bojart_memory.indexing import index_repository

PROJECT = 'bojart.jarvis'


class PreferResearchEmbedding:
    def key(self):
        return 'research-preference-fixture'

    def embed(self, texts):
        return [[0.2, 0.98] if 'courante' in text else [1.0, 0.0] for text in texts]


class ResearchIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        (self.repo / 'data/knowledge').mkdir(parents=True)
        (self.repo / 'current.md').write_text('source courante orchestration validée', encoding='utf-8')
        (self.repo / 'research.md').write_text(('orchestration '*80+' expérimental\n')*50, encoding='utf-8')
        self.records = [
            {'path': 'current.md', 'project': PROJECT, 'provenance': 'reference fixture'},
            {'path': 'research.md', 'project': PROJECT, 'provenance': 'proposal fixture', 'collection': 'research'},
        ]
        self.write_index()
        self.agent = AgentMemory(self.root / 'state', repo=self.repo)

    def write_index(self):
        (self.repo / 'data/knowledge/index.json').write_text(json.dumps(self.records), encoding='utf-8')

    def test_bm25_keeps_current_source_before_keyword_dense_research(self):
        self.agent.index()
        with Memory(self.agent.state, readonly=True) as memory:
            result = memory.search('orchestration', project=PROJECT, limit=2)
        self.assertEqual([r['source_path'] for r in result['results']], ['current.md', 'research.md'])
        self.assertEqual(result['results'][1]['collection'], 'research')

    def test_semantic_and_fused_ranking_preserve_reference_priority(self):
        self.agent.index()
        model = PreferResearchEmbedding()
        self.agent.embed(model)
        for query in ('orchestration', 'souvenir'):
            result = self.agent.search(query, PROJECT, limit=2, embedder=model)
            self.assertEqual([r['source_path'] for r in result['results']], ['current.md', 'research.md'])

    def test_removal_retires_research_without_erasing_history(self):
        self.agent.index()
        self.records = self.records[:1]
        self.write_index()
        result = self.agent.index()
        self.assertEqual(result['research_retired'][PROJECT], ['research.md'])
        with Memory(self.agent.state, readonly=True) as memory:
            self.assertFalse(memory.search('expérimental', project=PROJECT)['results'])
            self.assertTrue(memory.search('expérimental', project=PROJECT, history=True)['results'])

    def test_reclassification_retires_previous_canonical_selection(self):
        self.records[1].pop('collection')
        self.write_index()
        self.agent.index()
        self.records[1]['collection'] = 'research'
        self.write_index()
        self.assertEqual(self.agent.index()['retired'][PROJECT], ['research.md'])
        with Memory(self.agent.state, readonly=True) as memory:
            rows = memory.search('orchestration', project=PROJECT, limit=2)['results']
        self.assertEqual([(r['source_path'], r['collection']) for r in rows],
                         [('current.md', 'canonical'), ('research.md', 'research')])
        self.assertEqual(self.agent.index()['new_versions'], 0)

    def test_invalid_or_duplicate_routing_is_rejected_before_ingestion(self):
        self.records[1]['collection'] = 'unreviewed-privileged'
        self.write_index()
        with self.assertRaises(MemoryError):
            self.agent.index()
        self.assertEqual(self.agent.status()['sources'], 0)
        self.records[1]['collection'] = 'research'
        self.records.append(dict(self.records[1], collection='canonical'))
        self.write_index()
        with self.assertRaises(MemoryError):
            self.agent.index()
        self.assertEqual(self.agent.status()['sources'], 0)

    def test_cli_and_agent_keep_same_classification_without_duplicate_versions(self):
        result = subprocess.run([sys.executable, '-m', 'bojart_memory', '--state', str(self.agent.state),
                                 'index-repo', '--repo', str(self.repo)], cwd=REPO,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.agent.index()['new_versions'], 0)

    def test_export_labels_research_and_keeps_collection_in_evidence(self):
        self.agent.index()
        pack = self.agent.context('orchestration', PROJECT)
        self.assertIn('PROPOSITION DE RECHERCHE', pack['text'])
        self.assertEqual({r['collection'] for r in pack['evidence']}, {'canonical', 'research'})
        with Memory(self.agent.state, readonly=True) as memory:
            memory.backup(self.root / 'snapshot')
        Memory.restore(self.root / 'snapshot', self.root / 'restored')
        restored = AgentMemory(self.root / 'restored', repo=self.repo)
        self.assertEqual(pack['evidence'], restored.context('orchestration', PROJECT)['evidence'])


if __name__ == '__main__':
    unittest.main()
