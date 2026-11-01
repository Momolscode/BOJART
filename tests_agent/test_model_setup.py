"""Optional-model failures must not take down the document memory."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from bojart_memory import Memory, MemoryError
from bojart_memory.agent import AgentMemory, REPO
from bojart_memory.model_config import inspect_models, load_config, save_config
from bojart_memory.ollama import ModelError, Ollama
from tools import doctor

PROJECT = 'bojart.jarvis'


class MetadataServer:
    def __init__(self):
        self.requests = []
        self.tags = {'models': [
            {'name': 'embed:latest', 'digest': 'a' * 64},
            {'name': 'talk:latest', 'digest': 'b' * 64},
        ]}
        self.details = {'embed': {'capabilities': ['embedding']},
                        'talk': {'capabilities': ['completion', 'tools']}}
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, value, status=200):
                raw = value if isinstance(value, bytes) else json.dumps(value).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                owner.requests.append((self.path, None))
                self.reply(owner.tags if self.path == '/api/tags' else {}, 200 if self.path == '/api/tags' else 405)

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append((self.path, data))
                name = data.get('model', '').split(':')[0]
                self.reply(owner.details.get(name, {}) if self.path == '/api/show' else {},
                           200 if self.path == '/api/show' else 405)

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


class ModelSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'memory'

    def server(self):
        service = MetadataServer()
        self.addCleanup(service.close)
        return service

    def config(self, config):
        self.state.mkdir(exist_ok=True)
        (self.state / 'models.json').write_text(json.dumps(config), encoding='utf-8')

    def agent(self):
        agent = AgentMemory(self.state)
        source = self.root / 'proof.md'
        source.write_text('Mémoire persistante vérifiée.', encoding='utf-8')
        with Memory(agent.state) as memory:
            memory.ingest_file(source, root=self.root, project=PROJECT,
                               collection='fixture', provenance='regression fixture')
        return agent

    def test_empty_diagnostic_does_not_initialize_memory_or_use_network(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network forbidden')):
            result = inspect_models(self.state, probe=True)
        self.assertTrue(result['ok'])
        self.assertFalse(self.state.exists())
        self.assertTrue(all(role['status'] == 'not_configured' for role in result['roles'].values()))
        self.assertEqual(result['local_metadata_requests'], 0)

    def test_invalid_configurations_preserve_search_context_status_and_file(self):
        agent = self.agent()
        configs = [
            b'{broken', b'[]', b'\xff', b'{"chat_model": false}',
            b'{"embedding_model": 42}', b'{"embedding_model": ""}',
            b'{"chat_model":"one","chat_model":"two"}',
            b'{"ollama_url":"https://example.invalid"}',
            b'{"ollama_url":"http://127.0.0.1:0"}',
            b'{"ollama_url":"http://127.0.0.1:bad"}',
            b'{"api_key":"PRIVATE_FIXTURE_DO_NOT_PRINT"}',
            b' ' * 16385,
        ]
        for raw in configs:
            with self.subTest(raw=raw[:50]):
                (self.state / 'models.json').write_bytes(raw)
                with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network forbidden')):
                    result = agent.search('persistante', PROJECT)
                    context = agent.context('persistante', PROJECT)
                    status = agent.status()
                self.assertTrue(result['results'])
                self.assertIn('unavailable', result['semantic_status'])
                self.assertTrue(context['evidence'])
                self.assertEqual(status['models']['configuration_status'], 'invalid')
                self.assertNotIn('PRIVATE_FIXTURE_DO_NOT_PRINT', json.dumps(status))
                self.assertEqual((self.state / 'models.json').read_bytes(), raw)
                with self.assertRaises(MemoryError):
                    agent.ask('persistante', PROJECT, 'session', 'request')

    def test_invalid_models_do_not_hide_source_integrity_failure(self):
        agent = self.agent()
        directory = self.root / 'ledger/data/knowledge'
        directory.mkdir(parents=True)
        registry = directory / 'claims.jsonl'
        registry.write_text('{}\n', encoding='utf-8')
        with Memory(self.state) as memory:
            source = memory.ingest_file(registry, root=self.root/'ledger', project=PROJECT,
                                        collection='canonical', provenance='fixture')
            memory._object(source['sha256']).write_text('tampered', encoding='utf-8')
        (self.state / 'models.json').write_text('{broken', encoding='utf-8')
        with self.assertRaisesRegex(MemoryError, 'faits altérée'):
            agent.context('persistante', PROJECT)

    def test_passive_status_does_not_probe_configured_models(self):
        agent = self.agent()
        self.config({'embedding_model': 'embed', 'chat_model': 'talk'})
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network forbidden')):
            result = agent.status()
        self.assertTrue(result['chat_configured'])
        self.assertTrue(result['embeddings_configured'])
        self.assertEqual(result['models']['roles']['chat_model']['status'], 'not_probed')

    def test_probe_checks_role_metadata_without_inference_or_download(self):
        service = self.server()
        self.config({'embedding_model': 'embed', 'chat_model': 'talk', 'ollama_url': service.url})
        result = inspect_models(self.state, probe=True)
        self.assertTrue(result['ok'])
        self.assertFalse(result['inference_qualified'])
        self.assertEqual(result['inference_calls'], 0)
        self.assertEqual(result['model_downloads'], 0)
        self.assertEqual(result['local_metadata_requests'], 4)
        self.assertTrue(all(role['status'] == 'metadata_available' for role in result['roles'].values()))
        self.assertTrue(result['roles']['embedding_model']['model_key'].endswith('@' + 'a' * 64))
        self.assertEqual([p for p, _ in service.requests], ['/api/tags', '/api/show'] * 2)
        self.assertTrue(all(payload is None or set(payload) == {'model'} for _, payload in service.requests))
        self.assertFalse((self.state / 'memory.sqlite').exists())

    def test_wrong_model_role_is_explicit(self):
        service = self.server()
        self.config({'embedding_model': 'talk', 'chat_model': 'embed', 'ollama_url': service.url})
        result = inspect_models(self.state, probe=True)
        self.assertFalse(result['ok'])
        self.assertTrue(all(role['status'] == 'wrong_capability' for role in result['roles'].values()))

    def test_missing_model_is_not_downloaded(self):
        service = self.server()
        self.config({'chat_model': 'absent', 'ollama_url': service.url})
        result = inspect_models(self.state, probe=True)
        self.assertEqual(result['roles']['chat_model']['status'], 'model_missing')
        self.assertEqual(service.requests, [('/api/tags', None)])

    def test_undeclared_capability_is_not_assumed(self):
        service = self.server()
        service.details['talk'] = {}
        self.config({'chat_model': 'talk', 'ollama_url': service.url})
        result = inspect_models(self.state, probe=True)
        self.assertEqual(result['roles']['chat_model']['status'], 'capabilities_unknown')

    def test_remote_alias_is_rejected_before_show_or_inference(self):
        service = self.server()
        service.tags['models'][1]['remote_host'] = 'https://example.invalid'
        self.config({'chat_model': 'talk', 'ollama_url': service.url})
        result = inspect_models(self.state, probe=True)
        self.assertEqual(result['roles']['chat_model']['status'], 'remote_refused')
        self.assertEqual(service.requests, [('/api/tags', None)])

    def test_remote_details_are_not_treated_as_local_capabilities(self):
        service = self.server()
        service.details['talk']['remote_model'] = 'upstream'
        self.config({'chat_model': 'talk', 'ollama_url': service.url})
        result = inspect_models(self.state, probe=True)
        self.assertEqual(result['roles']['chat_model']['status'], 'remote_refused')
        self.assertEqual(len(service.requests), 2)

    def test_malformed_metadata_keeps_lexical_search(self):
        service = self.server()
        agent = self.agent()
        self.config({'embedding_model': 'embed', 'ollama_url': service.url})
        for response in ({'models': [42]}, {'models': {}},
                         {'models': [{'name': 'embed:latest', 'digest': 'broken'}]},
                         b'not JSON'):
            with self.subTest(response=response):
                service.tags = response
                result = agent.search('persistante', PROJECT)
                self.assertTrue(result['results'])
                self.assertIn('unavailable', result['semantic_status'])
                self.assertFalse(inspect_models(self.state, probe=True)['ok'])

    def test_local_outage_keeps_search_and_reports_unavailability(self):
        service = MetadataServer()
        service.close()
        agent = self.agent()
        self.config({'embedding_model': 'embed', 'ollama_url': service.url})
        result = agent.search('persistante', PROJECT)
        self.assertTrue(result['results'])
        status = inspect_models(self.state, probe=True)
        self.assertEqual(status['roles']['embedding_model']['status'], 'unavailable')
        self.assertEqual(status['local_metadata_requests'], 1)

    def test_configuration_keeps_previous_bytes_if_one_role_fails(self):
        service = self.server()
        agent = self.agent()
        self.config({'chat_model': 'talk', 'ollama_url': service.url})
        before = (self.state / 'models.json').read_bytes()
        with self.assertRaises(ModelError):
            agent.configure(embedding_model='embed', chat_model='absent')
        self.assertEqual((self.state / 'models.json').read_bytes(), before)

    def test_configure_validates_capabilities_and_preserves_custom_local_port(self):
        service = self.server()
        agent = self.agent()
        self.config({'chat_model': 'talk', 'ollama_url': service.url})
        result = agent.configure(embedding_model='embed')
        self.assertEqual(result['ollama_url'], service.url)
        self.assertEqual(result['chat_model'], 'talk')
        self.assertEqual(load_config(self.state)['embedding_model'], 'embed')
        self.assertFalse(list(self.state.glob('.models-*.tmp')))
        self.assertEqual([p for p, _ in service.requests], ['/api/tags', '/api/show'])

    def test_configuration_rejects_wrong_capability_without_writing(self):
        service = self.server()
        agent = self.agent()
        self.config({'ollama_url': service.url})
        before = (self.state / 'models.json').read_bytes()
        with self.assertRaises(ModelError):
            agent.configure(embedding_model='talk')
        self.assertEqual((self.state / 'models.json').read_bytes(), before)

    def test_failed_atomic_replace_keeps_old_config_and_cleans_temporary(self):
        self.config({'chat_model': 'old'})
        before = (self.state / 'models.json').read_bytes()
        with patch('bojart_memory.model_config.os.replace', side_effect=OSError('fixture')):
            with self.assertRaises(OSError):
                save_config(self.state, {'chat_model': 'new'})
        self.assertEqual((self.state / 'models.json').read_bytes(), before)
        self.assertFalse(list(self.state.glob('.models-*.tmp')))

    def test_cli_models_never_initializes_a_memory(self):
        run = subprocess.run([sys.executable, '-m', 'bojart_memory.agent_cli',
                              '--state', str(self.state), 'models'], cwd=REPO,
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(json.loads(run.stdout)['ok'])
        self.assertFalse(self.state.exists())

    def test_cli_reports_missing_model_with_machine_readable_failure(self):
        service = self.server()
        self.config({'chat_model': 'absent', 'ollama_url': service.url})
        run = subprocess.run([sys.executable, '-m', 'bojart_memory.agent_cli',
                              '--state', str(self.state), 'models'], cwd=REPO,
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertEqual(json.loads(run.stdout)['roles']['chat_model']['status'], 'model_missing')
        self.assertFalse((self.state / 'memory.sqlite').exists())

    def test_default_doctor_reports_optional_config_without_blocking_memory(self):
        self.state.mkdir()
        (self.state / 'models.json').write_text('{broken', encoding='utf-8')
        with patch.object(doctor, 'configuration', return_value={'ok': True}), \
                patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network forbidden')):
            result = doctor.report(memory_state=self.state, runtime_state=self.root/'work')
        self.assertEqual(result['launch_blockers'], [])
        self.assertEqual(result['models']['configuration_status'], 'invalid')
        self.assertEqual(result['models']['local_metadata_requests'], 0)
        self.assertFalse((self.state / 'memory.sqlite').exists())

    def test_doctor_can_explicitly_check_local_model_metadata(self):
        service = self.server()
        self.config({'chat_model': 'talk', 'ollama_url': service.url})
        with patch.object(doctor, 'configuration', return_value={'ok': True}):
            result = doctor.report(memory_state=self.state, runtime_state=self.root/'work', check_models=True)
        self.assertTrue(result['models']['ok'])
        self.assertEqual(result['models']['local_metadata_requests'], 2)
        self.assertEqual(result['models']['roles']['chat_model']['status'], 'metadata_available')
        self.assertFalse(result['production_ready'])
        self.assertFalse((self.state / 'memory.sqlite').exists())


if __name__ == '__main__':
    unittest.main()
