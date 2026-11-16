"""Compact inference must keep complete, sourced records and exact history."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bojart_memory.agent import AgentMemory
from bojart_memory.core import MemoryError
from bojart_memory.inference_settings import prompt_budget
from bojart_memory.model_config import save_config
from bojart_memory.model_setup import EMBEDDING, plan
from bojart_memory.ollama import chat_messages
from tests_agent.test_model_qualification import LocalModelServer

PROJECT = 'bojart.jarvis'


class CompactContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        (self.repo / 'data/knowledge').mkdir(parents=True)
        self.claims = [{'claim_id': 'fixture-' + str(i), 'subject': 'atelier',
                       'predicate': 'mémoire-' + str(i), 'value': 'mémoire 🎨 ' * 100,
                       'project': PROJECT, 'status': 'source_reported',
                       'sources': ['fixture'], 'observed_on': '2026-11-02', 'supersedes': []}
                      for i in range(8)]
        claims = self.repo / 'data/knowledge/claims.jsonl'
        claims.write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in self.claims), encoding='utf-8')
        records = [{'path': 'data/knowledge/claims.jsonl', 'project': PROJECT, 'provenance': 'test'}]
        for i in range(5):
            name = 'atelier-' + str(i) + '.md'
            (self.repo / name).write_text(('mémoire atelier été 🎨 ' * 45 + '\n') * 3, encoding='utf-8')
            records.append({'path': name, 'project': PROJECT, 'provenance': 'test'})
        (self.repo / 'data/knowledge/index.json').write_text(json.dumps(records), encoding='utf-8')
        self.agent = AgentMemory(Path(self.tmp.name) / 'state', repo=self.repo)
        self.agent.index()
        self.service = LocalModelServer()
        self.addCleanup(self.service.close)
        self.options = plan('speed')['chat_options']
        self.configure(self.options)

    def configure(self, options):
        save_config(self.agent.state, {'chat_model': self.service.chat_model,
            'embedding_model': EMBEDDING, 'ollama_url': self.service.url, 'chat_options': options})

    def test_multibyte_context_selects_complete_facts_and_passages(self):
        with patch.object(self.agent, 'search', wraps=self.agent.search) as search:
            pack = self.agent.context('mémoire atelier', PROJECT, _max_utf8_bytes=6000)
        self.assertEqual(search.call_count, 1)
        self.assertGreater(pack['omitted'], 0)
        self.assertLessEqual(len(pack['text'].encode('utf-8')), 6000)
        self.assertEqual(pack['utf8_bytes'], len(pack['text'].encode('utf-8')))
        self.assertEqual(pack['sha256'], hashlib.sha256(pack['text'].encode()).hexdigest())
        self.assertTrue(pack['reference_facts'])
        self.assertTrue(pack['evidence'])
        for fact in pack['reference_facts']:
            original = next(c for c in self.claims if 'claim-' + c['claim_id'] == fact['id'])
            self.assertEqual(fact['value'], original['value'])
            self.assertIn(json.dumps(original['value'], ensure_ascii=False), pack['text'])
        hits = self.agent.search('mémoire atelier', PROJECT)['results']
        for evidence in pack['evidence']:
            hit = next(h for h in hits if h['citation'] == evidence['citation'])
            self.assertIn(hit['text'] + '\nFIN EXTRAIT\n', pack['text'])
            self.assertTrue(evidence['source_bytes_verified'])

    def test_compact_chat_reduces_history_without_altering_original_or_retrieving_twice(self):
        old = {'question': '🎨' * 1800, 'context': self.agent.context('mémoire atelier', PROJECT),
               'response': {'answer': '💡' * 1800}}
        self.agent.episode('previous', 'session', PROJECT, old)
        original = copy.deepcopy(self.agent.history('session', PROJECT)[0])
        self.service.requests.clear()
        with patch.object(self.agent, 'search', wraps=self.agent.search) as search:
            result = self.agent.ask('mémoire atelier', PROJECT, 'session', 'next')
        self.assertEqual(search.call_count, 1)
        self.assertEqual(sum(path == '/api/embed' for path, _ in self.service.requests), 1)
        self.assertEqual(sum(path == '/api/chat' for path, _ in self.service.requests), 1)
        episodes = self.agent.history('session', PROJECT)
        self.assertEqual(episodes[0], original)
        latest = episodes[-1]
        conversation = latest['conversation_context']
        self.assertLess(conversation['max_characters'], 6000)
        exchange = conversation['exchanges'][0]
        self.assertEqual(exchange['question'], old['question'])
        self.assertEqual(exchange['answer_status'], 'withheld_budget')
        self.assertNotIn('answer', exchange)
        request = next(data for path, data in self.service.requests if path == '/api/chat')
        self.assertEqual(request['messages'], chat_messages('mémoire atelier', latest['context']['text'], conversation))
        self.assertEqual(request['options']['num_ctx'], 16384)
        self.assertEqual(request['options']['num_predict'], 512)
        self.assertEqual(result['prompt_budget'], prompt_budget(request['messages'], self.options))
        self.assertLessEqual(result['prompt_budget']['utf8_content_bytes'], 15360)
        self.assertTrue(latest['context']['citations'])

    def test_minimum_supported_context_retains_evidence(self):
        self.configure({**self.options, 'num_ctx': 8192, 'num_predict': 2048})
        result = self.agent.ask('mémoire atelier', PROJECT, 'session', 'small')
        self.assertLessEqual(result['prompt_budget']['utf8_content_bytes'], 5632)
        self.assertTrue(result['sources'])

    def test_oversized_question_fails_before_retrieval_or_inference(self):
        self.configure({**self.options, 'num_ctx': 8192, 'num_predict': 2048})
        with self.assertRaisesRegex(MemoryError, 'Question trop volumineuse'):
            self.agent.ask('🎨' * 2000, PROJECT, 'session', 'too-big')
        self.assertEqual(self.service.requests, [])
        self.assertEqual(self.agent.history('session', PROJECT), [])

    def test_byte_budget_validation_precedes_retrieval(self):
        for value in (True, 2999, 65537, '6000'):
            with self.subTest(value=value), self.assertRaises(MemoryError):
                self.agent.context('mémoire atelier', PROJECT, _max_utf8_bytes=value)
        self.assertEqual(self.service.requests, [])


if __name__ == '__main__':
    unittest.main()
