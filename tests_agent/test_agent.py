import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bojart_memory import Memory, MemoryError
from bojart_memory.agent import AgentMemory, REPO
from bojart_memory.mcp import Protocol
from bojart_memory.ollama import Ollama

J = 'bojart.jarvis'
C = 'bojart.creative'


class FakeEmbedder:
    def __init__(self, digest='one'): self.digest = digest
    def key(self): return self.digest
    def embed(self, texts):
        return [[1.0, 0.0] if any(x in s.lower() for x in ('souvenir', 'persistante')) else [0.0, 1.0] for s in texts]


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.m = AgentMemory(self.root / 'state')

    def tearDown(self): self.tmp.cleanup()

    def ingest(self, text, name='test.md', project=J):
        p = self.root / name; p.write_text(text, encoding='utf-8')
        with Memory(self.m.state) as m:
            return m.ingest_file(p, root=self.root, project=project, collection='test', provenance='test fixture')

    def test_one_database_and_original_api_compatibility(self):
        self.ingest('Mémoire persistante de Jarvis')
        self.assertTrue((self.m.state / 'memory.sqlite').is_file())
        self.assertEqual(len(list(self.m.state.glob('*.sqlite*'))), 1)
        self.assertEqual(self.m.search('persistante', J)['results'][0]['source_path'], 'test.md')

    def test_index_idempotent(self):
        self.assertGreater(self.m.index()['new_versions'], 0)
        self.assertEqual(self.m.index()['new_versions'], 0)

    def test_reference_facts_supersession(self):
        self.m.index(); facts = self.m.facts(C)
        self.assertTrue(any(f['id'] == 'claim-render-current' for f in facts))
        self.assertFalse(any(f['id'] == 'claim-audit-render-old' for f in facts))
        self.assertTrue(all(f['project'] == C for f in facts))

    def test_note_is_proposal_idempotent_and_conflict_visible(self):
        a = self.m.note('machine', 'A', 'observation datée', J)
        b = self.m.note('machine', 'A', 'observation datée', J)
        self.assertEqual(a, b); self.assertEqual(a['status'], 'proposal')
        self.m.note('machine', 'B', 'autre observation', J)
        self.assertEqual(len(self.m.facts(J)), 2)
        self.assertTrue(all(f['conflict'] for f in self.m.facts(J)))

    def test_notes_require_provenance_and_valid_project(self):
        with self.assertRaises(MemoryError): self.m.note('a', 'b', '', J)
        with self.assertRaises(MemoryError): self.m.note('a', 'b', 'c', 'unum')

    def test_episodes_persist_and_are_scoped(self):
        self.m.episode('e', 's', J, {'question': 'test'})
        reopened = AgentMemory(self.m.state)
        self.assertEqual(reopened.history('s', J), [{'question': 'test'}])
        self.assertEqual(reopened.history('s', C), [])
        self.assertEqual(reopened.history('other', J), [])

    def test_episode_idempotency_and_collision(self):
        self.m.episode('e', 's', J, {'x': 1}); self.m.episode('e', 's', J, {'x': 1})
        self.assertEqual(len(self.m.history('s', J)), 1)
        with self.assertRaises(MemoryError): self.m.episode('e', 's', J, {'x': 2})

    def test_semantic_synonym_and_hybrid(self):
        self.ingest('Mémoire persistante du projet')
        self.assertEqual(self.m.search('souvenir', J)['results'], [])
        self.m.embed(FakeEmbedder())
        result = self.m.search('souvenir', J, embedder=FakeEmbedder())
        self.assertEqual(result['semantic_status'], 'ready')
        self.assertEqual(result['results'][0]['source_path'], 'test.md')

    def test_embedding_model_digest_isolation(self):
        self.ingest('Mémoire persistante'); self.m.embed(FakeEmbedder())
        result = self.m.search('souvenir', J, embedder=FakeEmbedder('two'))
        self.assertEqual(result['semantic_status'], 'not_indexed')
        self.assertEqual(result['results'], [])

    def test_model_outage_falls_back(self):
        self.ingest('persistante')
        class Broken(FakeEmbedder):
            def key(self): raise OSError('offline')
        result = self.m.search('persistante', J, embedder=Broken())
        self.assertTrue(result['results']); self.assertIn('unavailable', result['semantic_status'])

    def test_semantic_scope(self):
        self.ingest('persistante', project=C); self.m.embed(FakeEmbedder())
        self.assertEqual(self.m.search('souvenir', J, embedder=FakeEmbedder())['results'], [])

    def test_obsolete_vectors_not_retrieved(self):
        self.ingest('persistante'); self.m.embed(FakeEmbedder())
        self.ingest('nouvelle version entièrement différente')
        self.assertEqual(self.m.search('souvenir', J, embedder=FakeEmbedder())['results'], [])

    def test_tampered_source_excluded(self):
        self.ingest('persistante'); self.m.embed(FakeEmbedder())
        with Memory(self.m.state) as db:
            h = db.db.execute('SELECT sha256 FROM assets').fetchone()[0]
            db._object(h).write_text('altered')
        self.assertEqual(self.m.search('souvenir', J, embedder=FakeEmbedder())['results'], [])

    def test_context_budget_provenance_and_claim_scope(self):
        self.m.index(); pack = self.m.context('G2 Jev', J, max_chars=3000)
        self.assertLessEqual(pack['characters'], 3000)
        self.assertFalse(pack['operational_authority'])
        self.assertTrue(pack['citations']); self.assertIn('DÉCISIONS', pack['text'])
        self.assertNotIn('claim-render-current', pack['citations'])
        self.assertNotIn('data/knowledge/claims.jsonl lignes', pack['text'])

    def test_backup_restore_includes_agent_tables_and_facts(self):
        self.m.index(); self.m.note('a', 'b', 'source', J)
        self.m.episode('e', 's', J, {'x': 1}); self.m.embed(FakeEmbedder())
        before = self.m.status()
        with Memory(self.m.state) as db: db.backup(self.root / 'snapshot')
        Memory.restore(self.root / 'snapshot', self.root / 'restored')
        restored = AgentMemory(self.root / 'restored', repo=self.root / 'missing-repo')
        self.assertEqual(restored.status()['agent_vectors'], before['agent_vectors'])
        self.assertEqual(restored.facts(J), self.m.facts(J))
        self.assertEqual(restored.history('s', J), [{'x': 1}])

    def test_chat_requires_local_configuration(self):
        with self.assertRaises(MemoryError): self.m.ask('test', J, 's', 'one')

    def test_chat_keeps_exact_context_and_retry_response(self):
        self.ingest('persistante')
        (self.m.state / 'models.json').write_text(json.dumps({'chat_model': 'fake-local'}))
        with patch.object(Ollama, 'chat', return_value={'answer': 'Réponse [inconnue]', 'automatically_verified': False}) as chat:
            result = self.m.ask('persistante', J, 's', 'one')
            again = self.m.ask('persistante', J, 's', 'one')
            self.assertEqual(result, again); self.assertEqual(chat.call_count, 1)
        episode = self.m.history('s', J)[0]
        self.assertEqual(episode['context']['sha256'], result['context_sha256'])
        self.assertEqual(result['citation_warnings'], ['inconnue'])
        with self.assertRaises(MemoryError): self.m.ask('different', J, 's', 'one')

    def test_ollama_rejects_remote_cloud_and_redirects(self):
        for url in ('https://127.0.0.1:11434', 'http://evil.test', 'http://127.0.0.1@evil.test'):
            with self.assertRaises(ValueError): Ollama('test', url)
        with self.assertRaises(ValueError): Ollama('test-cloud')

    def test_mcp_initialization_and_proposal(self):
        p = Protocol(self.m)
        request = lambda method, **params: p.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
        self.assertIn('error', request('tools/list'))
        request('initialize', protocolVersion='2025-06-18')
        p.dispatch({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        self.assertEqual(len(request('tools/list')['result']['tools']), 4)
        result = request('tools/call', name='memory_note', arguments={'key': 'a', 'value': 'b', 'source': 'c'})
        self.assertFalse(result['result']['isError']); self.assertEqual(self.m.facts(J)[0]['status'], 'proposal')

    def test_mcp_invalid_arguments(self):
        p = Protocol(self.m); p.ready = True
        for args in ({'query': 42}, {'query': 'x', 'shell': 'no'}, {'project': J}):
            result = p.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'memory_search', 'arguments': args}})
            self.assertIn('error', result)

    def test_real_mcp_stdio(self):
        messages = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
                    {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                    {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}]
        run = subprocess.run([sys.executable, str(REPO / 'tools/memory_mcp.py'), '--state', str(self.m.state)],
                             input=''.join(json.dumps(m) + '\n' for m in messages), capture_output=True, text=True, check=True)
        replies = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual(len(replies), 2); self.assertEqual(len(replies[-1]['result']['tools']), 4)


if __name__ == '__main__': unittest.main()
