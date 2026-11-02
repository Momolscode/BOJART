"""Regression corpus: a long source must not hide a smaller relevant one."""
import tempfile
import unittest
from pathlib import Path

from bojart_memory import Memory
from bojart_memory.agent import AgentMemory

PROJECT = 'bojart.jarvis'


class LocalEmbeddingFixture:
    """Deterministic test double; no model or provider is called."""
    def __init__(self, opposing=False):
        self.opposing = opposing

    def key(self):
        return 'diversity-test-opposing' if self.opposing else 'diversity-test'

    def embed(self, texts):
        return [([-1.0, 0.0] if self.opposing else [0.8, 0.6])
                if 'contexte' in text else [1.0, 0.0] for text in texts]


class RetrievalDiversityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agent = AgentMemory(self.root/'state')
        self.versions = {}
        with Memory(self.agent.state) as memory:
            for name, text in (
                ('dense.md', ('rare '*100+'\n')*1100),
                ('other.md', 'rare '+'contexte '*200),
            ):
                path = self.root/name
                path.write_text(text, encoding='utf-8')
                self.versions[name] = memory.ingest_file(
                    path, root=self.root, project=PROJECT, collection='test',
                    provenance='Synthetic regression corpus; not project evidence')
            self.assertGreater(memory.stats()['chunks'], 200)

    def assert_sources(self, response):
        self.assertEqual(len(response['results']), 2)
        self.assertEqual({r['source_path'] for r in response['results']},
                         {'dense.md', 'other.md'})
        self.assertTrue(all(r['source_bytes_verified'] for r in response['results']))

    def corrupt_dense(self):
        with Memory(self.agent.state) as memory:
            memory._object(self.versions['dense.md']['sha256']).write_text('changed')

    def test_lexical_search_reaches_shorter_source_beyond_early_passage_window(self):
        with Memory(self.agent.state, readonly=True) as memory:
            self.assert_sources(memory.search('rare', project=PROJECT, limit=2))

    def test_agent_lexical_search_preserves_source_diversity(self):
        self.assert_sources(self.agent.search('rare', PROJECT, limit=2))

    def test_corrupt_long_source_does_not_hide_intact_source(self):
        self.corrupt_dense()
        with Memory(self.agent.state, readonly=True) as memory:
            response = memory.search('rare', project=PROJECT, limit=2)
        self.assertEqual([r['source_path'] for r in response['results']], ['other.md'])
        self.assertEqual(len(response['warnings']), 1)

    def test_semantic_search_reaches_shorter_source_beyond_forty_chunks(self):
        model = LocalEmbeddingFixture()
        self.agent.embed(model)
        self.assert_sources(self.agent.search('souvenir', PROJECT, limit=2, embedder=model))

    def test_rank_fusion_keeps_lexical_source_even_when_semantic_prefers_long_source(self):
        model = LocalEmbeddingFixture(opposing=True)
        self.agent.embed(model)
        self.assert_sources(self.agent.search('rare', PROJECT, limit=2, embedder=model))

    def test_semantic_only_corruption_keeps_fallback_and_integrity_warning(self):
        model = LocalEmbeddingFixture()
        self.agent.embed(model)
        self.corrupt_dense()
        response = self.agent.search('souvenir', PROJECT, limit=2, embedder=model)
        self.assertEqual([r['source_path'] for r in response['results']], ['other.md'])
        self.assertEqual(response['warnings'],
                         [{'sha256': self.versions['dense.md']['sha256'],
                           'reason': 'source_missing_or_changed'}])

    def test_context_keeps_both_cited_sources_after_restart_and_restore(self):
        first = self.agent.context('rare', PROJECT)
        self.assertEqual({e['source_path'] for e in first['evidence']},
                         {'dense.md', 'other.md'})
        self.assertLessEqual(first['characters'], first['max_characters'])
        reopened = AgentMemory(self.agent.state)
        self.assertEqual(first['sha256'], reopened.context('rare', PROJECT)['sha256'])
        with Memory(self.agent.state, readonly=True) as memory:
            memory.backup(self.root/'snapshot')
        Memory.restore(self.root/'snapshot', self.root/'restored')
        restored = AgentMemory(self.root/'restored', repo=self.root/'absent')
        self.assertEqual(first['evidence'], restored.context('rare', PROJECT)['evidence'])


if __name__ == '__main__':
    unittest.main()
