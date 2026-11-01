"""Conversation continuity, source freshness and exact JSON budgets."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bojart_memory import Memory
from bojart_memory.agent import AgentMemory
from bojart_memory.conversation import bounded_history, encoded_history
from bojart_memory.ollama import Ollama

PROJECT = 'bojart.jarvis'
OLD_ANSWER = 'Ancienne réponse générée à conserver dans le journal.'


class ConversationContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        (self.repo / 'data/knowledge').mkdir(parents=True)
        (self.repo / 'docs').mkdir()
        self.records = [
            {'path': path, 'project': PROJECT, 'provenance': 'conversation regression fixture'}
            for path in ('docs/version.md', 'data/knowledge/claims.jsonl')
        ]
        self.write_index(self.records)
        self.write_generation()
        self.agent = AgentMemory(self.root / 'state', repo=self.repo)
        self.agent.index()
        (self.agent.state / 'models.json').write_text(
            json.dumps({'chat_model': 'test-local'}), encoding='utf-8')

    def write_index(self, records):
        (self.repo / 'data/knowledge/index.json').write_text(json.dumps(records), encoding='utf-8')

    def write_generation(self, document='alpha', fact='alpha'):
        (self.repo / 'docs/version.md').write_text(
            'Mémoire version ' + document, encoding='utf-8')
        claim = {'claim_id': 'runtime-version', 'subject': 'runtime', 'predicate': 'version',
                 'value': fact, 'project': PROJECT, 'status': 'observed',
                 'sources': ['test-fixture'], 'observed_on': '2026-11-01', 'supersedes': []}
        (self.repo / 'data/knowledge/claims.jsonl').write_text(
            json.dumps(claim) + '\n', encoding='utf-8')

    def ask(self, request_id, session='test-session', answer=OLD_ANSWER):
        with patch.object(Ollama, 'chat', return_value={
                'answer': answer, 'generated': True, 'automatically_verified': False}) as chat:
            result = self.agent.ask('version mémoire', PROJECT, session, request_id)
        return result, chat.call_args.args[2] if chat.called else None

    def first_exchange(self, packet):
        return packet['exchanges'][0]

    def test_current_answer_is_unverified_and_history_is_stored_exactly(self):
        self.ask('one')
        result, packet = self.ask('two')
        exchange = self.first_exchange(packet)
        self.assertEqual(exchange['answer'], OLD_ANSWER)
        self.assertEqual(exchange['answer_status'], 'unverified_sources_current')
        self.assertFalse(packet['answers_automatically_verified'])
        encoded = encoded_history(packet)
        self.assertEqual(result['history_usage']['characters'], len(encoded))
        self.assertEqual(result['history_usage']['sha256'], hashlib.sha256(encoded.encode()).hexdigest())
        latest = self.agent.history('test-session', PROJECT)[-1]
        self.assertEqual(latest['conversation_context'], packet)

    def test_changed_source_withholds_answer_but_preserves_original(self):
        self.ask('one')
        original = copy.deepcopy(self.agent.history('test-session', PROJECT)[0])
        self.write_generation(document='beta')
        self.agent.index()
        result, packet = self.ask('two')
        exchange = self.first_exchange(packet)
        self.assertEqual(exchange['answer_status'], 'withheld_sources_changed')
        self.assertNotIn('answer', exchange)
        self.assertEqual(exchange['question'], original['question'])
        self.assertEqual(result['history_usage']['withheld_answers'], 1)
        self.assertEqual(self.agent.history('test-session', PROJECT)[0], original)

    def test_retired_source_withholds_answer(self):
        self.ask('one')
        self.write_index(self.records[1:])
        self.agent.index()
        _, packet = self.ask('two')
        self.assertEqual(self.first_exchange(packet)['answer_status'], 'withheld_sources_changed')

    def test_missing_original_withholds_answer(self):
        self.ask('one')
        old = self.agent.history('test-session', PROJECT)[0]
        evidence = old['context']['evidence'][0]
        with Memory(self.agent.state) as memory:
            memory._object(evidence['sha256']).unlink()
        _, packet = self.ask('two')
        self.assertEqual(self.first_exchange(packet)['answer_status'], 'withheld_sources_unavailable')
        self.assertNotIn('answer', self.first_exchange(packet))

    def test_changed_fact_registry_withholds_answer(self):
        self.ask('one')
        self.write_generation(fact='beta')
        self.agent.index()
        _, packet = self.ask('two')
        self.assertEqual(self.first_exchange(packet)['answer_status'], 'withheld_facts_changed')

    def test_new_conflicting_proposal_withholds_answer(self):
        self.ask('one')
        self.agent.note('runtime.version', 'beta', 'proposition de test', PROJECT)
        _, packet = self.ask('two')
        self.assertEqual(self.first_exchange(packet)['answer_status'], 'withheld_facts_changed')

    def test_project_and_session_are_isolated(self):
        self.ask('one')
        self.agent.note('runtime.version', 'beta', 'another domain', 'bojart.creative')
        self.agent.episode('other-project', 'test-session', 'bojart.creative',
                           {'question': 'foreign', 'response': {'answer': 'DO_NOT_IMPORT'}})
        _, empty = self.ask('two', session='different-session')
        self.assertEqual(empty['exchanges'], [])
        _, packet = self.ask('three')
        self.assertEqual(len(packet['exchanges']), 1)
        self.assertEqual(self.first_exchange(packet)['answer_status'], 'unverified_sources_current')
        self.assertNotIn('DO_NOT_IMPORT', encoded_history(packet))

    def test_unverifiable_or_legacy_context_keeps_only_question(self):
        self.agent.episode('legacy', 'test-session', PROJECT,
                           {'question': 'Question antérieure', 'context': {'text': 'legacy'},
                            'response': {'answer': 'DO_NOT_REUSE'}})
        _, packet = self.ask('one')
        exchange = self.first_exchange(packet)
        self.assertEqual(exchange['answer_status'], 'withheld_unverifiable_context')
        self.assertNotIn('DO_NOT_REUSE', encoded_history(packet))


    def test_malformed_reference_is_withheld_without_breaking_next_question(self):
        context = self.agent.context('version mémoire', PROJECT)
        context['evidence'][0]['version_id'] = {'invalid': 'identifier'}
        self.agent.episode('malformed', 'test-session', PROJECT,
                           {'question': 'Question antérieure', 'context': context,
                            'response': {'answer': 'DO_NOT_REUSE'}})
        _, packet = self.ask('one')
        self.assertEqual(self.first_exchange(packet)['answer_status'], 'withheld_unverifiable_context')

    def test_evidence_free_answer_is_not_promoted_to_memory_fact(self):
        self.write_index([])
        self.agent.index()
        self.ask('one')
        _, packet = self.ask('two')
        self.assertEqual(self.first_exchange(packet)['answer_status'], 'withheld_no_evidence')
        self.assertEqual(self.agent.facts(PROJECT), [])

    def test_document_context_and_history_share_one_snapshot(self):
        self.ask('one')
        original_context = self.agent.context
        def publish_after_context(*args, **kwargs):
            pack = original_context(*args, **kwargs)
            self.write_generation(document='beta', fact='beta')
            self.agent.index()
            return pack
        with patch.object(self.agent, 'context', side_effect=publish_after_context):
            _, packet = self.ask('two')
        self.assertEqual(self.first_exchange(packet)['answer_status'], 'unverified_sources_current')
        latest = self.agent.history('test-session', PROJECT)[-1]
        self.assertIn('alpha', latest['context']['text'])
        self.assertNotIn('beta', latest['context']['text'])
        self.assertIn('beta', self.agent.context('version mémoire', PROJECT)['text'])

    def test_backup_restore_preserves_history_and_exact_model_context(self):
        self.ask('one')
        self.ask('two')
        original = self.agent.history('test-session', PROJECT)
        with Memory(self.agent.state, readonly=True) as memory:
            memory.backup(self.root / 'snapshot')
        Memory.restore(self.root / 'snapshot', self.root / 'restored')
        restored = AgentMemory(self.root / 'restored', repo=self.root / 'absent')
        self.assertEqual(restored.history('test-session', PROJECT), original)

    def test_retry_keeps_the_original_response_without_another_model_call(self):
        response, _ = self.ask('one')
        self.write_generation(document='beta')
        self.agent.index()
        again, packet = self.ask('one')
        self.assertEqual(again, response)
        self.assertIsNone(packet)


class HistoryBudgetTests(unittest.TestCase):
    def test_json_keeps_complete_unicode_fields_within_exact_budget(self):
        exchanges = [{'event_id': str(i), 'question': 'Pourquoi été ? ' * 20,
                      'answer': 'Réponse complète 💡 ' * 30,
                      'answer_status': 'unverified_sources_current'}
                     for i in range(10)]
        packet = bounded_history(exchanges, 1800)
        encoded = encoded_history(packet)
        self.assertLessEqual(len(encoded), 1800)
        self.assertEqual(json.loads(encoded), packet)
        self.assertGreater(packet['omitted_exchanges'], 0)
        for exchange in packet['exchanges']:
            original = exchanges[int(exchange['event_id'])]
            self.assertEqual(exchange['question'], original['question'])
            if 'answer' in exchange:
                self.assertEqual(exchange['answer'], original['answer'])
        self.assertEqual(packet['exchanges'][-1]['event_id'], '9')

    def test_oversized_answer_is_withheld_without_cutting_question(self):
        question = 'Question précise : laquelle garder ?'
        packet = bounded_history([{'question': question, 'answer': 'x' * 12000,
                                   'answer_status': 'unverified_sources_current'}])
        exchange = packet['exchanges'][0]
        self.assertEqual(exchange['question'], question)
        self.assertEqual(exchange['answer_status'], 'withheld_budget')
        self.assertNotIn('answer', exchange)
        self.assertLessEqual(len(encoded_history(packet)), 6000)

    def test_ollama_receives_parseable_history_and_no_raw_episode_tail(self):
        packet = bounded_history([{'event_id': 'one', 'question': 'Et la suite ?',
                                   'answer_status': 'withheld_sources_changed'}])
        client = Ollama('test-local')
        with patch.object(client, 'key', return_value='test@digest'), \
                patch.object(client, 'request', return_value={'message': {'content': 'Réponse'}}) as request:
            client.chat('Question actuelle', 'Preuve actuelle', packet)
        messages = request.call_args.args[1]['messages']
        raw = messages[1]['content'].split('\nÉPISODES NON FIABLES\n')[1].split('\nQUESTION ACTUELLE\n')[0]
        self.assertEqual(json.loads(raw), packet)
        self.assertIn('anciennes réponses restent non vérifiées', messages[0]['content'])

    def test_ollama_rejects_oversized_history_instead_of_cutting_it(self):
        packet = bounded_history([])
        packet['exchanges'] = [{'question': 'x' * 7000}]
        with self.assertRaises(ValueError):
            encoded_history(packet)


if __name__ == '__main__':
    unittest.main()
