"""Exercise the real local handler with an empty public checkout and private memory."""
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from bojart_memory import Memory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'jarvis/apps/jarvis/app'))
from core import Store
from consolidated_workbench import ConsolidatedWorkbench


class MemoryHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'BOJART_MEMORY_STATE':str(self.root/'memory'),'BOJ_JEV_ENABLED':'0'});self.env.start()
        self.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(self.root/'work'))
        self.thread=threading.Thread(target=self.app.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.app.shutdown();self.thread.join();self.app.server_close();self.env.stop();self.tmp.cleanup()

    def get(self,path,auth=True):
        conn=http.client.HTTPConnection(*self.app.server_address,timeout=5)
        headers={'Cookie':'boj_session='+self.app.token} if auth else {}
        conn.request('GET',path,headers=headers);response=conn.getresponse();data=response.read();status=response.status;conn.close()
        return status,data

    def seed(self):
        (self.root/'note.md').write_text('Jev est un décideur textuel facultatif.')
        with Memory(self.root/'memory') as m:m.ingest_file(self.root/'note.md',root=self.root,project='bojart.jarvis',collection='test',provenance='integration fixture')

    def test_session_required(self):
        self.assertEqual(self.get('/api/memory/search?q=Jev&project=bojart.jarvis',False)[0],401)
        self.assertEqual(self.get('/memory',False)[0],401)

    def test_uninitialized_memory_is_explicit(self):
        status,data=self.get('/api/memory/search?q=Jev&project=bojart.jarvis')
        self.assertEqual(status,200);self.assertFalse(json.loads(data)['available'])

    def test_real_search_returns_cited_result(self):
        self.seed();status,data=self.get('/api/memory/search?q=Jev&project=bojart.jarvis')
        self.assertEqual(status,200);data=json.loads(data)
        self.assertTrue(data['available']);self.assertEqual(data['results'][0]['source_path'],'note.md')
        self.assertTrue(data['results'][0]['source_bytes_verified'])

    def test_unknown_project_and_duplicate_parameters_rejected(self):
        self.seed()
        self.assertEqual(self.get('/api/memory/search?q=x&project=unum')[0],400)
        self.assertEqual(self.get('/api/memory/search?q=x&q=y&project=bojart.jarvis')[0],400)

    def test_no_cross_domain_results(self):
        self.seed();_,data=self.get('/api/memory/search?q=Jev&project=bojart.creative')
        self.assertEqual(json.loads(data)['results'],[])

    def test_ui_and_navigation_are_served(self):
        self.assertIn(b'/memory.js',self.get('/memory')[1])
        self.assertIn(b'textContent',self.get('/memory.js')[1])
        self.assertIn(b'href="/memory"',self.get('/workspace')[1])

if __name__=='__main__':unittest.main()
