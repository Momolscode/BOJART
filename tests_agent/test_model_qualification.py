"""Real loopback transport; no weights downloaded and no real inference claimed."""
import contextlib
import http.server
import io
from http.client import IncompleteRead
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from bojart_memory.agent import AgentMemory
from bojart_memory.core import Memory
from bojart_memory.inference_settings import chat_settings
from bojart_memory.model_config import inspect_models, load_config, save_config
from bojart_memory.model_setup import EMBEDDING, PROFILES, plan, prepare, pull_candidate, qualify
from bojart_memory.ollama import ModelError, Ollama
from tools.setup_local_models import main


class LocalModelServer:
    def __init__(self):
        self.requests = []
        self.chat_model = PROFILES['speed']['chat_model']
        self.digests = {self.chat_model: 'a' * 64, EMBEDDING: 'b' * 64}
        self.after_chat = None
        self.after_embed = None
        self.bad_answer = False
        self.constant_vectors = False
        self.truncated = False
        self.remote = False
        self.invalid_chat = False
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, data):
                raw = json.dumps(data).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                owner.requests.append((self.path, None))
                if self.path == '/api/version':
                    self.reply({'version': 'test-fixture-only'})
                    return
                self.reply({'models': [{'name': name, 'digest': digest,
                    **({'remote_host': 'https://example.invalid'} if owner.remote else {})}
                    for name, digest in owner.digests.items()]})

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append((self.path, data))
                if self.path == '/api/show':
                    self.reply({'capabilities': ['embedding' if data['model'] == EMBEDDING else 'completion']})
                elif self.path == '/api/embed':
                    vectors = [[1., 0.] if owner.constant_vectors or 'météo' not in text else [0., 1.]
                               for text in data['input']]
                    if owner.after_embed:
                        owner.after_embed()
                    self.reply({'embeddings': vectors})
                elif self.path == '/api/chat':
                    text = data['messages'][-1]['content']
                    answer = ('INCONNU [tour]' if 'quantité de VRAM' in text
                              else 'ATELIER-42 [actif]' if 'code du dossier actif' in text
                              else 'BOJ.ART [atelier]')
                    if owner.bad_answer:
                        answer = 'PIRATE : imprimé.'
                    if owner.after_chat:
                        owner.after_chat()
                    self.reply([] if owner.invalid_chat else {'done': True,
                        'done_reason': 'length' if owner.truncated else 'stop',
                        'message': {'role': 'assistant', 'content': answer},
                        'load_duration': 1000, 'eval_count': 8, 'eval_duration': 200000000})
                else:
                    self.reply({'error': 'unexpected endpoint'})

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'memory'
        self.service = LocalModelServer()
        self.addCleanup(self.service.close)

    def config(self):
        save_config(self.state, {'ollama_url': self.service.url, 'chat_model': self.service.chat_model})
        return (self.state / 'models.json').read_bytes()

    def fixture_repo(self):
        root = self.root / 'repo'
        (root / 'data/knowledge').mkdir(parents=True)
        (root / 'proof.md').write_text('Mémoire persistante BOJ.ART.', encoding='utf-8')
        (root / 'data/knowledge/index.json').write_text(json.dumps([{'path': 'proof.md',
            'project': 'bojart.jarvis', 'provenance': 'synthetic test'}]), encoding='utf-8')
        return root

    def test_plan_is_offline_and_does_not_create_state(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')), \
                patch('subprocess.run', side_effect=AssertionError('process')), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['--state', str(self.state)]), 0)
        self.assertEqual(json.loads(out.getvalue())['network_requests'], 0)
        self.assertFalse(self.state.exists())
        self.assertEqual(len(json.loads(out.getvalue())['profiles']), 3)

    def test_explicit_profile_required_for_activation(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['--apply'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['--download'])

    def test_settings_and_identity_validation(self):
        for value in ({'num_ctx': 12}, {'num_predict': True}, {'keep_alive': -1},
                      {'think': 'high'}, {'secret': 'x'}, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                chat_settings(value)
        with self.assertRaises(ValueError):
            save_config(self.state, {'chat_model': 'one', 'model_keys': {'chat_model': 'other@' + 'a' * 64}})

    def test_runtime_chat_uses_explicit_bounds_and_returns_measured_timing(self):
        result = Ollama(self.service.chat_model, self.service.url).chat('Projet ?', '[atelier] BOJ.ART')
        request = next(payload for path, payload in self.service.requests if path == '/api/chat')
        self.assertFalse(request['think'])
        self.assertEqual(request['options']['num_ctx'], 32768)
        self.assertEqual(request['keep_alive'], 300)
        self.assertNotIn('tools', request)
        self.assertEqual(result['performance']['generated_tokens_per_second'], 40)
        self.assertIsNone(result['performance']['first_token_ms'])
        self.assertFalse(result['automatically_verified'])

    def test_oversized_context_is_rejected_before_network_instead_of_cut(self):
        with self.assertRaises(ValueError):
            Ollama(self.service.chat_model, self.service.url).chat('Question', '🎨' * 20000)
        self.assertEqual(self.service.requests, [])

    def test_pinned_identity_rejects_updated_alias_before_inference(self):
        client = Ollama(self.service.chat_model, self.service.url,
                        expected_key=self.service.chat_model + '@' + 'c' * 64)
        with self.assertRaises(ModelError) as caught:
            client.chat('Question', 'Contexte')
        self.assertEqual(caught.exception.code, 'model_changed')
        self.assertFalse(any(path == '/api/chat' for path, _ in self.service.requests))

    def test_change_during_chat_discards_response(self):
        self.service.after_chat = lambda: self.service.digests.update({self.service.chat_model: 'c' * 64})
        with self.assertRaises(ModelError):
            Ollama(self.service.chat_model, self.service.url).chat('Question', 'Contexte')

    def test_change_during_embed_discards_vectors(self):
        self.service.after_embed = lambda: self.service.digests.update({EMBEDDING: 'c' * 64})
        with self.assertRaises(ModelError):
            Ollama(EMBEDDING, self.service.url).embed(['Test'])

    def test_change_between_embedding_batches_cannot_relabel_vectors(self):
        client = Ollama(EMBEDDING, self.service.url)
        self.assertEqual(client.embed(['Premier lot']), [[1., 0.]])
        self.service.digests[EMBEDDING] = 'c' * 64
        with self.assertRaises(ModelError):
            client.embed(['Deuxième lot'])
        self.assertEqual(sum(p == '/api/embed' for p, _ in self.service.requests), 1)

    def test_malformed_chat_fails_cleanly(self):
        self.service.invalid_chat = True
        with self.assertRaises(ValueError):
            Ollama(self.service.chat_model, self.service.url).chat('Question', 'Contexte')

    def test_remote_alias_is_never_run_or_pulled(self):
        self.service.remote = True
        with patch('bojart_memory.model_setup.pull_candidate', side_effect=AssertionError('download')):
            result = qualify('speed', url=self.service.url, download=True)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error_code'], 'remote_refused')

    def test_missing_model_does_not_download_implicitly(self):
        self.service.digests.pop(EMBEDDING)
        with patch('bojart_memory.model_setup.pull_candidate', side_effect=AssertionError('download')):
            result = qualify('speed', url=self.service.url)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error_code'], 'model_missing')

    def test_explicit_download_only_fetches_missing_curated_model(self):
        self.service.digests.pop(EMBEDDING)
        def install(name, url):
            self.assertEqual((name, url), (EMBEDDING, self.service.url))
            self.service.digests[name] = 'b' * 64
        with patch('bojart_memory.model_setup.pull_candidate', side_effect=install) as pull:
            result = qualify('speed', url=self.service.url, download=True)
        self.assertTrue(result['ok'])
        self.assertEqual(pull.call_count, 1)
        self.assertEqual(result['downloads'], [EMBEDDING])

    def test_puller_uses_fixed_argv_and_local_endpoint(self):
        with patch('shutil.which', return_value='/fixture/ollama'), patch('subprocess.run') as run:
            pull_candidate(EMBEDDING, self.service.url)
        self.assertEqual(run.call_args.args[0], ['/fixture/ollama', 'pull', EMBEDDING])
        self.assertEqual(run.call_args.kwargs['env']['OLLAMA_HOST'], self.service.url)
        self.assertFalse(run.call_args.kwargs['shell'])
        with self.assertRaises(ValueError):
            pull_candidate('other;echo command', self.service.url)

    def test_qualification_reports_only_synthetic_scope(self):
        result = qualify('speed', url=self.service.url)
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['samples']), 4)
        self.assertEqual(result['scope'], 'executing_host_synthetic_smoke')
        self.assertFalse(result['production_ready'])
        self.assertFalse(result['profile']['hardware_qualified'])
        self.assertGreater(result['local_requests'], 0)
        self.assertEqual(result['ollama_version'], 'test-fixture-only')
        self.assertEqual(len(result['implementation_sha256']), 3)

    def test_bad_answer_or_truncation_preserves_configuration(self):
        before = self.config()
        for attribute in ('bad_answer', 'truncated'):
            setattr(self.service, attribute, True)
            result = prepare(self.state, 'speed')
            self.assertFalse(result['ok'])
            self.assertFalse(result['activated'])
            self.assertEqual((self.state / 'models.json').read_bytes(), before)
            self.assertFalse((self.state / 'memory.sqlite').exists())
            setattr(self.service, attribute, False)

    def test_constant_embeddings_do_not_pass_as_semantic_model(self):
        self.service.constant_vectors = True
        result = qualify('speed', url=self.service.url)
        self.assertFalse(result['ok'])
        self.assertFalse(result['embedding']['ok'])

    def test_latency_gate_uses_observed_elapsed_time(self):
        clock = iter(range(10000))
        with patch('time.monotonic', side_effect=lambda: next(clock)):
            result = qualify('speed', url=self.service.url, max_followup_ms=100)
        self.assertFalse(result['ok'])
        self.assertFalse(result['latency_ok'])

    def test_success_indexes_one_database_then_pins_both_models(self):
        self.config()
        repo = self.fixture_repo()
        with patch('bojart_memory.model_setup.AgentMemory', side_effect=lambda state: AgentMemory(state, repo=repo)):
            result = prepare(self.state, 'speed')
        self.assertTrue(result['ok'])
        self.assertTrue(result['activated'])
        config = load_config(self.state)
        self.assertEqual(config['embedding_model'], EMBEDDING)
        self.assertEqual(len(config['model_keys']), 2)
        with Memory(self.state, readonly=True) as memory:
            self.assertEqual(memory.db.execute('SELECT count(*) FROM agent_vectors').fetchone()[0], 1)
        self.assertEqual(len(list(self.state.glob('*.sqlite'))), 1)
        self.assertTrue(inspect_models(self.state, probe=True)['ok'])

    def test_failed_index_keeps_prior_config(self):
        before = self.config()
        with patch.object(AgentMemory, 'index', side_effect=ValueError('fixture missing')):
            result = prepare(self.state, 'speed')
        self.assertFalse(result['ok'])
        self.assertFalse(result['activated'])
        self.assertEqual((self.state / 'models.json').read_bytes(), before)

    def test_changed_pin_keeps_lexical_search_available(self):
        repo = self.fixture_repo()
        memory = AgentMemory(self.state, repo=repo)
        memory.index()
        save_config(self.state, {'ollama_url': self.service.url, 'embedding_model': EMBEDDING,
            'model_keys': {'embedding_model': EMBEDDING + '@' + 'c' * 64}})
        result = memory.search('persistante', 'bojart.jarvis')
        self.assertTrue(result['results'])
        self.assertIn('unavailable', result['semantic_status'])
        self.assertEqual(inspect_models(self.state, probe=True)['roles']['embedding_model']['status'], 'model_changed')

    def test_concurrent_configuration_change_is_preserved(self):
        self.config()
        newer = {'ollama_url': self.service.url, 'chat_model': 'new-user-choice'}
        def change():
            save_config(self.state, newer)
            return {'fixture': True}
        with patch.object(AgentMemory, 'index', side_effect=change):
            result = prepare(self.state, 'speed')
        self.assertFalse(result['ok'])
        self.assertFalse(result['activated'])
        self.assertEqual(load_config(self.state), newer)

    def test_incomplete_transport_response_is_a_failed_report(self):
        before = self.config()
        with patch.object(Ollama, 'request', side_effect=IncompleteRead(b'')):
            result = prepare(self.state, 'speed')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error_type'], 'IncompleteRead')
        self.assertEqual((self.state / 'models.json').read_bytes(), before)

    def test_cli_writes_distinct_receipt_after_real_loopback_setup(self):
        self.config()
        repo = self.fixture_repo()
        with patch('bojart_memory.model_setup.AgentMemory', side_effect=lambda state: AgentMemory(state, repo=repo)), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = main(['--state', str(self.state), '--profile', 'speed', '--apply'])
        self.assertEqual(code, 0)
        summary = json.loads(out.getvalue())
        result = json.loads(Path(summary['report']).read_text('utf-8'))
        self.assertTrue(result['activated'])
        self.assertFalse(result['production_ready'])
        self.assertEqual(len(result['samples']), 4)


if __name__ == '__main__':
    unittest.main()
