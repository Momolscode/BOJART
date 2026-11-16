import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'jarvis/apps/jarvis/app'))
from core import Store
from consolidated_workbench import ConsolidatedWorkbench
from bojart_memory.agent import AgentMemory
from bojart_memory.core import Memory


class AgentHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'BOJART_MEMORY_STATE': str(self.root / 'memory'), 'BOJ_JEV_ENABLED': '0'})
        self.env.start(); AgentMemory().index()
        self.app = ConsolidatedWorkbench(('127.0.0.1', 0), Store(self.root / 'work'))
        self.thread = threading.Thread(target=self.app.serve_forever, daemon=True); self.thread.start()

    def tearDown(self):
        self.app.shutdown(); self.thread.join(); self.app.server_close(); self.env.stop(); self.tmp.cleanup()

    def request(self, path, body=None, auth=True, origin=True):
        c = http.client.HTTPConnection(*self.app.server_address, timeout=5)
        headers = {'Cookie': 'boj_session=' + self.app.token} if auth else {}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            if origin: headers['Origin'] = self.app.origin
        c.request('GET' if body is None else 'POST', path, body=None if body is None else json.dumps(body), headers=headers)
        r = c.getresponse(); status, raw = r.status, r.read(); c.close()
        return status, raw

    def test_read_and_write_require_session(self):
        self.assertEqual(self.request('/api/memory/status', auth=False)[0], 401)
        self.assertEqual(self.request('/api/memory/reindex', {}, auth=False)[0], 401)

    def test_note_requires_origin_and_explicit_source(self):
        data = {'key': 'a', 'value': 'b', 'source': 'fixture', 'project': 'bojart.jarvis'}
        self.assertEqual(self.request('/api/memory/note', data, origin=False)[0], 403)
        status, raw = self.request('/api/memory/note', data)
        self.assertEqual(status, 200); self.assertEqual(json.loads(raw)['status'], 'proposal')
        del data['source']
        self.assertEqual(self.request('/api/memory/note', data)[0], 400)

    def test_context_and_unknown_project(self):
        status, raw = self.request('/api/memory/context?q=Jev&project=bojart.jarvis')
        self.assertEqual(status, 200); self.assertTrue(json.loads(raw)['citations'])
        self.assertEqual(self.request('/api/memory/context?q=Jev&project=unum')[0], 400)
        self.assertEqual(self.request('/api/memory/recall?q=Jev&q=G2')[0], 400)

    def test_invalid_model_config_keeps_memory_http_available(self):
        configuration = self.root / 'memory/models.json'
        configuration.write_text('{broken', encoding='utf-8')
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network forbidden')):
            status, raw = self.request('/api/memory/status')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)['models']['configuration_status'], 'invalid')
            status, raw = self.request('/api/memory/recall?q=Jev&project=bojart.jarvis')
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(raw)['results'])
            status, raw = self.request('/api/memory/context?q=Jev&project=bojart.jarvis')
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(raw)['citations'])
            self.assertEqual(self.request('/api/memory/reindex', {})[0], 200)
            self.assertEqual(self.request('/api/memory/note', {
                'key': 'offline', 'value': 'Mémoire disponible',
                'source': 'HTTP regression fixture', 'project': 'bojart.jarvis'})[0], 200)
        self.assertEqual(configuration.read_text('utf-8'), '{broken')

    def test_backup_and_ui_assets(self):
        status, raw = self.request('/api/memory/backup', {})
        self.assertEqual(status, 200); self.assertTrue(Path(json.loads(raw)['path']).is_dir())
        self.assertIn(b'/memory.css', self.request('/memory')[1])
        self.assertIn(b'@media', self.request('/memory.css')[1])
        self.assertIn(b'textContent', self.request('/memory.js')[1])

    def test_deep_verify_detects_derived_corruption_while_structure_remains_ok(self):
        self.assertEqual(self.request('/api/memory/verify',auth=False)[0],401)
        self.assertTrue(json.loads(self.request('/api/memory/verify')[1])['ok'])
        with Memory(self.root/'memory') as m,m.db:
            m.db.execute("UPDATE chunks SET text='tampered' WHERE id=(SELECT min(id) FROM chunks)")
        status=json.loads(self.request('/api/memory/status')[1])
        self.assertEqual(status['database_integrity'],'ok')
        self.assertFalse(status['full_integrity_verified'])
        self.assertFalse(json.loads(self.request('/api/memory/verify')[1])['ok'])

    def test_http_concurrent_request_and_cached_replay(self):
        entered=threading.Event();release=threading.Event();calls=[];answer=[]
        class Model:
            def __init__(self,*args,**kwargs):pass
            def chat(self,*args,**kwargs):
                calls.append(1);entered.set()
                if not release.wait(5):raise TimeoutError('fixture')
                return {'answer':'Réponse du double local.'}
        (self.root/'memory/models.json').write_text(json.dumps({'chat_model':'fixture'}),encoding='utf-8')
        body={'text':'Jev','project':'bojart.jarvis','session':'s','request_id':'http-concurrent'}
        with patch('bojart_memory.agent.Ollama',Model):
            t=threading.Thread(target=lambda:answer.append(self.request('/api/memory/ask',body)))
            t.start()
            try:
                self.assertTrue(entered.wait(3))
                code,raw=self.request('/api/memory/ask',body)
                self.assertEqual(code,409);self.assertEqual(json.loads(raw)['code'],'IN_PROGRESS')
                self.assertFalse(json.loads(raw)['automatic_retry'])
                status='/api/memory/request-status?project=bojart.jarvis&session=s&request_id=http-concurrent'
                self.assertEqual(json.loads(self.request(status)[1])['state'],'RUNNING')
                self.assertEqual(self.request(status,auth=False)[0],401)
                self.assertEqual(self.request(status.replace('session=s','session=other'))[0],409)
            finally:release.set();t.join(6)
            self.assertEqual(answer[0][0],200)
            self.assertEqual(self.request('/api/memory/ask',body),answer[0])
            self.assertEqual(calls,[1])


if __name__ == '__main__': unittest.main()
