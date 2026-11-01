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

    def test_backup_and_ui_assets(self):
        status, raw = self.request('/api/memory/backup', {})
        self.assertEqual(status, 200); self.assertTrue(Path(json.loads(raw)['path']).is_dir())
        self.assertIn(b'/memory.css', self.request('/memory')[1])
        self.assertIn(b'@media', self.request('/memory.css')[1])
        self.assertIn(b'textContent', self.request('/memory.js')[1])


if __name__ == '__main__': unittest.main()
