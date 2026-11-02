"""Real SQLite/OS reservations with deterministic, fake-provider boundaries."""
from concurrent.futures import ThreadPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from bojart_memory.agent import AgentMemory
from bojart_memory.ask_requests import AskRequestError, AskRequests, OwnerLock
from bojart_memory.core import Memory, MemoryError as MemoryRefusal
from bojart_memory.ollama import Ollama

PROJECT = 'bojart.jarvis'
QUESTION = 'version mémoire'


def process_ask(state, repo, barrier, entered, release, outputs, question=QUESTION):
    """Spawn-compatible child; never contacts an HTTP endpoint."""
    agent = AgentMemory(state, repo=repo)

    def provider(*args, **kwargs):
        outputs.put(('provider', 'entered'))
        entered.set()
        if not release.wait(15):
            raise TimeoutError('fixture boundary not released')
        return {'answer': 'Réponse enfant', 'generated': True}

    with patch.object(Ollama, 'chat', side_effect=provider):
        if barrier is not None:
            barrier.wait(10)
        try:
            outputs.put(('result', agent.ask(question, PROJECT, 'session', 'request')))
        except AskRequestError as exc:
            outputs.put(('error', exc.to_dict()))


class AskRequestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'state'
        self.agent = AgentMemory(self.state, repo=self.root / 'repo')
        (self.state / 'models.json').write_text(json.dumps({'chat_model': 'fake-local'}), encoding='utf-8')

    def ask(self, request='request', question=QUESTION, session='session', project=PROJECT, agent=None):
        return (agent or self.agent).ask(question, project, session, request)

    def rows(self):
        with Memory(self.state, readonly=True) as m:
            return [dict(r) for r in m.db.execute('SELECT * FROM agent_ask_requests')]

    def assert_code(self, code, action):
        with self.assertRaises(AskRequestError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        self.assertFalse(caught.exception.to_dict()['automatic_retry'])

    def test_two_threads_two_instances_one_call_and_writes_remain_available(self):
        entered, release = threading.Event(), threading.Event()
        other = AgentMemory(self.state, repo=self.root / 'repo')

        def provider(*args, **kwargs):
            entered.set()
            self.assertTrue(release.wait(10))
            return {'answer': 'exact response', 'generated': True}

        with patch.object(Ollama, 'chat', side_effect=provider) as chat, ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.ask)
            try:
                self.assertTrue(entered.wait(10))
                duplicate = pool.submit(self.ask, agent=other)
                self.assert_code('IN_PROGRESS', lambda: duplicate.result(3))
                self.assertEqual(other.request_status('request', 'session', PROJECT)['state'], 'RUNNING')
                other.note('during-call', 'write succeeds', 'fixture', PROJECT)
                self.assertEqual(other.facts(PROJECT)[0]['value'], 'write succeeds')
            finally:
                release.set()
            result = first.result(10)
            self.assertEqual(self.ask(agent=other), result)
            self.assertEqual(chat.call_count, 1)
        self.assertEqual(len(self.agent.history('session', PROJECT)), 1)
        self.assertEqual(self.rows()[0]['state'], 'COMPLETED')

    def test_conflicts_before_and_after_completion_do_not_infer(self):
        store = AskRequests(self.state)
        guard, _ = store.claim('request', 'session', PROJECT, QUESTION)
        try:
            for question, session, project in [(QUESTION + ' ', 'session', PROJECT),
                    (QUESTION, 'different', PROJECT), (QUESTION, 'session', 'bojart.creative')]:
                self.assert_code('CONFLICT', lambda: self.ask(question=question, session=session, project=project))
            store.calling('request', guard.owner)
            store.complete('request', guard.owner, {'question': QUESTION, 'response': {'answer': 'done'}})
        finally:
            guard.close()
        with patch.object(Ollama, 'chat', side_effect=AssertionError('forbidden')):
            self.assert_code('CONFLICT', lambda: self.ask(question='changed'))
            self.assertEqual(self.ask()['answer'], 'done')
            self.assert_code('CONFLICT', lambda: self.agent.request_status('request', 'other', PROJECT))
            self.assert_code('CONFLICT', lambda: self.agent.request_status('request', 'session', 'bojart.sites'))

    def test_legacy_response_survives_without_configuration_and_identity_stays_strict(self):
        expected = {'answer': 'historical', 'automatically_verified': False}
        self.agent.episode('chat-legacy', 'session', PROJECT, {'question': QUESTION, 'response': expected})
        before = self.agent.history('session', PROJECT)
        (self.state / 'models.json').unlink()
        with patch.object(Ollama, 'chat', side_effect=AssertionError('forbidden')):
            self.assertEqual(self.ask(request='legacy'), expected)
            self.assertEqual(self.agent.request_status('legacy', 'session', PROJECT)['response'], expected)
            self.assert_code('CONFLICT', lambda: self.ask(request='legacy', question='changed'))
        self.assertEqual(self.agent.history('session', PROJECT), before)
        self.assertEqual(self.rows(), [])

    def test_pre_provider_failure_is_terminal_failed_without_retry(self):
        (self.state / 'models.json').unlink()
        with patch.object(Ollama, 'chat') as chat:
            self.assert_code('FAILED', self.ask)
            (self.state / 'models.json').write_text(json.dumps({'chat_model': 'fake-local'}), encoding='utf-8')
            self.assert_code('FAILED', self.ask)
            chat.assert_not_called()
        self.assertEqual(self.rows()[0]['state'], 'FAILED')
        self.assertEqual(self.rows()[0]['reason'], 'chat_not_configured')
        with self.assertRaisesRegex(AskRequestError, 'Configurer un modèle Ollama local'):
            self.ask()

    def test_oversized_input_is_rejected_before_chat_with_explicit_persistence_reason(self):
        original = self.agent.context

        def oversized(*args, **kwargs):
            pack = original(*args, **kwargs)
            pack['large_metadata_fixture'] = 'x' * 54001
            return pack

        with patch.object(self.agent, 'context', side_effect=oversized), patch.object(Ollama, 'chat') as chat:
            self.assert_code('UNKNOWN', self.ask)
            chat.assert_not_called()
        self.assertEqual(self.rows()[0]['reason'], 'episode_input_too_large')
        self.assertEqual(self.agent.history('session', PROJECT), [])

    def test_provider_timeout_and_exception_are_unknown_without_retry(self):
        for exception in [TimeoutError('private provider text'), ValueError('private invalid payload')]:
            request = type(exception).__name__
            with patch.object(Ollama, 'chat', side_effect=exception) as chat:
                self.assert_code('UNKNOWN', lambda: self.ask(request=request))
                self.assert_code('UNKNOWN', lambda: self.ask(request=request))
                self.assertEqual(chat.call_count, 1)
            self.assertNotIn('private', json.dumps(self.agent.request_status(request, 'session', PROJECT)))
        self.assertEqual(self.agent.history('session', PROJECT), [])

    def test_invalid_provider_json_cannot_be_committed(self):
        for index, response in enumerate([None, {'answer': 12}, {'answer': ''}, {'answer': 'x', 'score': float('nan')},
                {'answer': 'x', 'bad': object()}, {'answer': 'x' * 65000}]):
            with patch.object(Ollama, 'chat', return_value=response):
                self.assert_code('UNKNOWN', lambda: self.ask(request='invalid' + str(index)))
        self.assertEqual(self.agent.history('session', PROJECT), [])
        self.assertTrue(all(r['response'] is None and r['state'] == 'UNKNOWN' for r in self.rows()))

    def test_abandoned_owner_is_unknown_and_fenced_from_late_completion(self):
        store = AskRequests(self.state)
        guard, _ = store.claim('request', 'session', PROJECT, QUESTION)
        store.calling('request', guard.owner)
        guard.close()
        self.assertEqual(self.agent.request_status('request', 'session', PROJECT)['state'], 'UNKNOWN')
        with patch.object(Ollama, 'chat') as chat:
            self.assert_code('UNKNOWN', self.ask)
            self.assert_code('UNKNOWN', lambda: store.complete('request', guard.owner, {'question': QUESTION, 'response': {'answer': 'late'}}))
            chat.assert_not_called()
        self.assertEqual(self.agent.history('session', PROJECT), [])

    def test_atomic_completion_rolls_back_episode_when_terminal_update_fails(self):
        with Memory(self.state) as m:
            m.db.execute("CREATE TRIGGER reject_completion BEFORE UPDATE OF state ON agent_ask_requests WHEN NEW.state='COMPLETED' BEGIN SELECT RAISE(ABORT,'fixture rollback'); END")
            m.db.commit()
        with patch.object(Ollama, 'chat', return_value={'answer': 'not committed'}) as chat:
            self.assert_code('UNKNOWN', self.ask)
            self.assert_code('UNKNOWN', self.ask)
            self.assertEqual(chat.call_count, 1)
        self.assertEqual(self.agent.history('session', PROJECT), [])
        self.assertIsNone(self.rows()[0]['response'])

    def test_response_loss_after_commit_is_replayed_without_reinference(self):
        original = AskRequests.complete

        def lose_return(store, *args):
            original(store, *args)
            raise OSError('client never received commit acknowledgement')

        with patch.object(AskRequests, 'complete', lose_return), patch.object(Ollama, 'chat', return_value={'answer': 'durable'}) as chat:
            result = self.ask()
            self.assertEqual(self.ask(), result)
            self.assertEqual(chat.call_count, 1)
        self.assertEqual(len(self.agent.history('session', PROJECT)), 1)
        self.assertEqual(self.rows()[0]['state'], 'COMPLETED')

    def test_changed_model_config_replays_original_completed_identity(self):
        with patch.object(Ollama, 'chat', return_value={'answer': 'model one'}) as chat:
            original = self.ask()
            (self.state / 'models.json').write_text('{invalid', encoding='utf-8')
            self.assertEqual(self.ask(), original)
            self.assertEqual(chat.call_count, 1)

    def test_agent_passes_pinned_identity_before_loopback_chat(self):
        from tests_agent.test_model_qualification import LocalModelServer
        service = LocalModelServer()
        self.addCleanup(service.close)
        (self.state / 'models.json').write_text(json.dumps({
            'chat_model': service.chat_model, 'ollama_url': service.url,
            'model_keys': {'chat_model': service.chat_model + '@' + 'c' * 64}}), encoding='utf-8')
        self.assert_code('UNKNOWN', self.ask)
        self.assertFalse(any(path == '/api/chat' for path, _ in service.requests))
        self.assertEqual(self.agent.history('session', PROJECT), [])

    def test_model_change_after_loopback_chat_cannot_commit_or_retry(self):
        from tests_agent.test_model_qualification import LocalModelServer
        service = LocalModelServer()
        self.addCleanup(service.close)
        (self.state / 'models.json').write_text(json.dumps({
            'chat_model': service.chat_model, 'ollama_url': service.url,
            'model_keys': {'chat_model': service.chat_model + '@' + 'a' * 64}}), encoding='utf-8')
        service.after_chat = lambda: service.digests.update({service.chat_model: 'c' * 64})
        self.assert_code('UNKNOWN', self.ask)
        count = len(service.requests)
        self.assert_code('UNKNOWN', self.ask)
        self.assertEqual(len(service.requests), count)
        self.assertEqual(sum(path == '/api/chat' for path, _ in service.requests), 1)
        self.assertEqual(self.agent.history('session', PROJECT), [])

    def test_repeated_replays_and_conflicts_do_not_accumulate_unused_locks(self):
        with patch.object(Ollama, 'chat', return_value={'answer': 'durable'}):
            result = self.ask()
        original = set((self.state / '.ask-locks').iterdir())
        self.assertEqual(len(original), 1)
        for _ in range(12):
            self.assertEqual(self.ask(), result)
            self.assert_code('CONFLICT', lambda: self.ask(question='other'))
        self.assertEqual(set((self.state / '.ask-locks').iterdir()), original)

    def test_owner_uuid_collision_never_reuses_or_removes_existing_owner_file(self):
        store = AskRequests(self.state)
        guard, _ = store.claim('request', 'session', PROJECT, QUESTION)
        try:
            with patch('bojart_memory.ask_requests.uuid.uuid4') as identifier:
                identifier.return_value.hex = guard.owner
                with self.assertRaises(FileExistsError):
                    store.claim('another', 'session', PROJECT, QUESTION)
            self.assertTrue(guard.path.exists())
            self.assertEqual(self.agent.request_status('request', 'session', PROJECT)['state'], 'RUNNING')
            self.assertEqual(len(self.rows()), 1)
        finally:
            guard.close()

    def link_or_skip(self, link, target):
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'symbolic links unavailable: {exc}')

    def test_state_reached_through_linked_parent_is_not_a_redirection(self):
        # Same class as Windows 8.3 temp names: the unresolved state path
        # differs from its resolved form without the lock folder moving.
        alias = self.root / 'alias'
        self.link_or_skip(alias, self.root)
        guard, _ = AskRequests(alias / 'state').claim('request', 'session', PROJECT, QUESTION)
        try:
            self.assertEqual(guard.path.parent, (self.state / '.ask-locks').resolve())
            self.assertEqual(self.agent.request_status('request', 'session', PROJECT)['state'], 'RUNNING')
        finally:
            guard.close()

    def test_redirected_lock_directory_is_refused_before_reservation(self):
        elsewhere = self.root / 'elsewhere'
        elsewhere.mkdir()
        self.link_or_skip(self.state / '.ask-locks', elsewhere)
        with self.assertRaisesRegex(MemoryRefusal, 'redirigé'):
            AskRequests(self.state).claim('request', 'session', PROJECT, QUESTION)
        self.assertEqual(list(elsewhere.iterdir()), [])
        self.assertEqual(self.rows(), [])

    def test_missing_and_invalid_status_never_exposes_other_request(self):
        self.assert_code('NOT_FOUND', lambda: self.agent.request_status('missing', 'session', PROJECT))
        for value in ['../escape', '', 'x' * 101]:
            with self.assertRaises(ValueError):
                self.agent.request_status(value, 'session', PROJECT)

    def test_invalid_question_is_rejected_before_reservation_or_provider(self):
        with patch.object(Ollama, 'chat') as chat:
            for question in (None, False, 7, {}, '', '   ', 'x' * 2001):
                with self.subTest(question=question), self.assertRaises(ValueError):
                    self.ask(question=question)
            chat.assert_not_called()
        self.assertEqual(self.rows(), [])
        self.assertFalse((self.state / '.ask-locks').exists())

    def test_new_identity_must_be_explicit_after_unknown(self):
        with patch.object(Ollama, 'chat', side_effect=TimeoutError()):
            self.assert_code('UNKNOWN', self.ask)
        with patch.object(Ollama, 'chat', return_value={'answer': 'explicit new request'}) as chat:
            self.assert_code('UNKNOWN', self.ask)
            self.assertEqual(self.ask(request='new-request')['answer'], 'explicit new request')
            self.assertEqual(chat.call_count, 1)

    def test_backup_during_call_restores_unknown_but_original_completes(self):
        entered, release = threading.Event(), threading.Event()

        def provider(*args, **kwargs):
            entered.set()
            self.assertTrue(release.wait(10))
            return {'answer': 'original completed'}

        with patch.object(Ollama, 'chat', side_effect=provider) as chat, ThreadPoolExecutor(1) as pool:
            first = pool.submit(self.ask)
            try:
                self.assertTrue(entered.wait(10))
                with Memory(self.state) as m:
                    m.backup(self.root / 'snapshot')
                Memory.restore(self.root / 'snapshot', self.root / 'restored')
                restored = AgentMemory(self.root / 'restored', repo=self.root / 'repo')
                self.assert_code('UNKNOWN', lambda: self.ask(agent=restored))
                self.assertEqual(restored.request_status('request', 'session', PROJECT)['reason'], 'owner_lost_or_restored')
                self.assertEqual(self.agent.request_status('request', 'session', PROJECT)['state'], 'RUNNING')
            finally:
                release.set()
            result = first.result(10)
            self.assertEqual(chat.call_count, 1)
        with Memory(self.state) as m:
            m.backup(self.root / 'completed-snapshot')
        Memory.restore(self.root / 'completed-snapshot', self.root / 'completed-restored')
        restored = AgentMemory(self.root / 'completed-restored', repo=self.root / 'repo')
        with patch.object(Ollama, 'chat', side_effect=AssertionError('forbidden')):
            self.assertEqual(self.ask(agent=restored), result)

    def test_distinct_requests_can_both_enter_provider(self):
        barrier = threading.Barrier(2)

        def provider(*args, **kwargs):
            barrier.wait(10)
            return {'answer': 'parallel distinct requests'}

        with patch.object(Ollama, 'chat', side_effect=provider) as chat, ThreadPoolExecutor(2) as pool:
            a, b = pool.submit(self.ask, 'a'), pool.submit(self.ask, 'b')
            self.assertEqual(a.result(15)['answer'], b.result(15)['answer'])
            self.assertEqual(chat.call_count, 2)

    def launch(self, *args):
        ctx = multiprocessing.get_context('spawn')
        process = ctx.Process(target=process_ask, args=(str(self.state), str(self.root / 'repo'), *args))
        process.start()

        def cleanup():
            if process.is_alive():
                process.terminate()
            process.join(10)
            process.close()
        self.addCleanup(cleanup)
        return process

    def test_two_processes_start_together_and_only_one_enters_provider(self):
        ctx = multiprocessing.get_context('spawn')
        barrier, entered, release, outputs = ctx.Barrier(2), ctx.Event(), ctx.Event(), ctx.Queue()
        self.addCleanup(outputs.close)
        a = self.launch(barrier, entered, release, outputs)
        b = self.launch(barrier, entered, release, outputs)
        self.assertTrue(entered.wait(10))
        first = [outputs.get(timeout=10), outputs.get(timeout=10)]
        self.assertEqual(sorted(x[0] for x in first), ['error', 'provider'])
        error = next(v for kind, v in first if kind == 'error')
        self.assertEqual(error['code'], 'IN_PROGRESS')
        release.set()
        self.assertEqual(outputs.get(timeout=10)[0], 'result')
        a.join(10); b.join(10)
        self.assertEqual((a.exitcode, b.exitcode), (0, 0))
        self.assertEqual(len(self.agent.history('session', PROJECT)), 1)

    def test_killed_provider_process_is_unknown_in_new_instance(self):
        ctx = multiprocessing.get_context('spawn')
        entered, release, outputs = ctx.Event(), ctx.Event(), ctx.Queue()
        self.addCleanup(outputs.close)
        child = self.launch(None, entered, release, outputs)
        self.assertTrue(entered.wait(10))
        self.assertEqual(outputs.get(timeout=10)[0], 'provider')
        self.assert_code('IN_PROGRESS', self.ask)
        child.terminate(); child.join(10)
        self.assertIsNotNone(child.exitcode)
        fresh = AgentMemory(self.state, repo=self.root / 'repo')
        with patch.object(Ollama, 'chat') as chat:
            self.assert_code('UNKNOWN', lambda: self.ask(agent=fresh))
            self.assertEqual(fresh.request_status('request', 'session', PROJECT)['state'], 'UNKNOWN')
            chat.assert_not_called()
        self.assertEqual(self.agent.history('session', PROJECT), [])


if __name__ == '__main__':
    unittest.main()
