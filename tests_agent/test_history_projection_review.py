"""Counterexamples found during the independent integrity review."""
import tempfile
from pathlib import Path
import unittest

from bojart_memory.agent import AgentMemory
from bojart_memory.core import Memory, canonical, digest
from bojart_memory.conversation import _answer_status
import tests_agent.test_memory_integrity as fixtures


class HistoryProjectionReviewTests(unittest.TestCase):
    def test_legacy_unprojected_evidence_cannot_validate_an_old_answer(self):
        fixture = fixtures.MemoryIntegrityTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        version = fixture.insert_legacy()
        verified = fixture.m.validate_version(version)
        chunk = verified['chunks'][0]
        self.assertIn('artneedle', chunk['text'])
        evidence = {**chunk, 'project': 'bojart.jarvis',
            'source_path': 'data/knowledge/claims.jsonl',
            'sha256': verified['metadata']['sha256'], 'excerpt_matches_source': True,
            'excerpt_sha256': digest(chunk['text'].encode())}
        context = {'schema': 'bojart.agent-context.v2', 'project': 'bojart.jarvis',
            'text': chunk['text'], 'sha256': digest(chunk['text'].encode()),
            'evidence': [evidence], 'reference_facts': []}
        self.assertFalse(fixture.m.search('artneedle', project='bojart.jarvis')['results'])
        self.assertEqual(_answer_status(fixture.m, context, 'bojart.jarvis', {}, {}),
                         'withheld_project_projection_required')

    def test_verified_utf8_bom_registry_is_readable_by_facts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'repo/data/knowledge/claims.jsonl'
            source.parent.mkdir(parents=True)
            source.write_text(canonical({'project': 'bojart.jarvis', 'claim_id': 'bom',
                'subject': 'test', 'predicate': 'value', 'value': 'authentic',
                'status': 'observed', 'sources': ['fixture'], 'observed_on': '2026-11-02',
                'supersedes': []}) + '\n', encoding='utf-8-sig')
            agent = AgentMemory(root / 'state', repo=root / 'repo')
            with Memory(agent.state) as memory:
                memory.ingest_file(source, root=root / 'repo', project='bojart.jarvis',
                                   collection='canonical', provenance='BOM fixture')
                self.assertTrue(memory.verify()['ok'])
            self.assertEqual(agent.facts('bojart.jarvis')[0]['value'], 'authentic')


if __name__ == '__main__':
    unittest.main()
