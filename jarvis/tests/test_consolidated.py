import unittest, sys, tempfile, threading, http.client, json, sqlite3, concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, Rejected
from display_contracts import DisplayProposals
from consolidated_workbench import ConsolidatedWorkbench

class ContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name);self.book=DisplayProposals(self.store)
 def tearDown(self): self.tmp.cleanup()
 def request(self,**kw):
  p={'request_id':'request01','turn_id':'turn01','project_id':'BOJ-PILOTE-001','revision':0,'command':'Montre les sources au centre.','operation_id':None};p.update(kw);return p
 def test_known_command_local(self):
  p=self.book.prepare(self.request());self.assertEqual(p['action'],'show_sources');self.assertFalse(p['jev_called']);self.assertFalse(p['executed']);self.assertFalse(p['display_acknowledged'])
 def test_replay_no_duplicate(self):
  a=self.book.prepare(self.request());b=self.book.prepare(self.request());self.assertTrue(b['replayed']);self.assertEqual(a['created_at_epoch'],b['created_at_epoch'])
 def test_id_conflict(self):
  self.book.prepare(self.request())
  with self.assertRaises(Rejected):self.book.prepare(self.request(command='Ouvre le studio'))
 def test_wrong_project(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(project_id='UNUM'))
 def test_wrong_revision(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(revision=9))
 def test_bool_revision(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(revision=False))
 def test_extra_key(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(shell='ls'))
 def test_no_printer(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(command='Imprime toutes les pièces'))
 def test_no_delete(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(command='Supprime le dossier'))
 def test_ambiguous_stop(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(command='Arrête'))
 def test_speech_interrupt_not_machine_stop(self):
  p=self.book.prepare(self.request(command='Arrête de parler'));self.assertEqual(p['action'],'interrupt_speech');self.assertFalse(p['physical_commands'])
 def test_selection_required(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(command='Affiche le modèle à droite'))
 def test_unknown_selection(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(command='Affiche le modèle à droite',operation_id='a'*32))
 def test_planning_explicit_demo(self):
  p=self.book.prepare(self.request(command='Affiche le planning à gauche'));self.assertEqual(p['data_status'],'demonstration')
 def test_revision_after_request(self):
  self.book.prepare(self.request())
  with self.store.connect() as con:con.execute('INSERT INTO projects VALUES (?,?)',('BOJ-PILOTE-001',1))
  p=self.book.prepare(self.request());self.assertFalse(p['current']);self.assertFalse(p['executed'])
 def test_context_change_after_request(self):
  ctx=Path(self.tmp.name)/'ctx.json';ctx.write_bytes(self.store.context_path.read_bytes());self.store.context_path=ctx
  self.book.prepare(self.request());ctx.write_text(ctx.read_text()+'\n')
  self.assertFalse(self.book.prepare(self.request())['current'])
 def test_unicode(self):
  p=self.book.prepare(self.request(command='Jarvis, montre les sources au centre!'))
  self.assertEqual(p['target_role'],'pilotage')
 def test_long_command(self):
  with self.assertRaises(Rejected):self.book.prepare(self.request(command='x'*401))
 def test_parallel_retries(self):
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rs=list(pool.map(lambda _:self.book.prepare(self.request()),range(8)))
  self.assertEqual(sum(not r['replayed'] for r in rs),1)
 def test_reopen_preserves_receipt(self):
  a=self.book.prepare(self.request());b=DisplayProposals(self.store).prepare(self.request());self.assertEqual(a['created_at_epoch'],b['created_at_epoch'])

class HTTPTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(cls.tmp.name));cls.thread=threading.Thread(target=cls.app.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.app.shutdown();cls.app.server_close();cls.thread.join();cls.tmp.cleanup()
 def req(self,path,body=None,auth=True,headers=None):
  h={'Cookie':'boj_session='+self.app.token} if auth else {}
  if body is not None:h.update({'Origin':self.app.origin,'Content-Type':'application/json'})
  h.update(headers or {});c=http.client.HTTPConnection('127.0.0.1',self.app.server_port,timeout=15);c.request('GET' if body is None else 'POST',path,body=json.dumps(body) if body is not None else None,headers=h);r=c.getresponse();status=r.status;b=r.read();c.close();return status,b
 def test_knowledge_real_results(self):
  s,b=self.req('/api/knowledge/search?q=resine');d=json.loads(b);self.assertEqual(s,200);self.assertGreater(d['total_returned'],0);self.assertFalse(d['allowed_to_execute']);self.assertEqual(len(d['corpus_digest']),64)
 def test_no_auth_knowledge(self):self.assertEqual(self.req('/api/knowledge/search?q=resine',auth=False)[0],401)
 def test_wrong_host(self):self.assertEqual(self.req('/api/control/state',headers={'Host':'example.org'})[0],403)
 def test_no_auth_context(self):self.assertEqual(self.req('/api/context/distilled',auth=False)[0],401)
 def test_context(self):self.assertIn('decisions',json.loads(self.req('/api/context/distilled')[1])['context'])
 def test_capabilities_honest(self):
  d=json.loads(self.req('/api/control/state')[1]);self.assertEqual(d['jev'],'not_connected');self.assertEqual(d['screen_pairing'],'browser_tabs_local_only')
 def test_unknown_query_parameter(self):self.assertEqual(self.req('/api/knowledge/search?q=test&path=/etc/passwd')[0],400)
 def test_duplicate_query(self):self.assertEqual(self.req('/api/knowledge/search?q=a&q=b')[0],400)
 def test_limit_validation(self):self.assertEqual(self.req('/api/knowledge/search?q=test&limit=999')[0],400)
 def test_empty_search(self):self.assertEqual(self.req('/api/knowledge/search?q=')[0],400)
 def test_original_studio_retained(self):self.assertEqual(self.req('/api/studio/catalogue')[0],200)
 def test_original_cad_retained(self):self.assertEqual(self.req('/api/state')[0],200)
 def test_knowledge_page(self):self.assertIn(b'/knowledge.js',self.req('/knowledge')[1])
 def test_original_console_link(self):self.assertIn(b'href="/knowledge"',self.req('/')[1])
 def test_propose(self):
  p={'request_id':'http-control','turn_id':'t1','project_id':'BOJ-PILOTE-001','revision':0,'command':'ouvre le studio','operation_id':None}
  s,b=self.req('/api/control/prepare',p);self.assertEqual(s,200);self.assertFalse(json.loads(b)['executed'])
 def test_origin_rejected(self):self.assertEqual(self.req('/api/control/prepare',{},headers={'Origin':'https://evil.invalid'})[0],403)
 def test_unauth_write_rejected(self):self.assertEqual(self.req('/api/control/prepare',{},auth=False)[0],401)
 def test_unbounded_actions_absent(self):self.assertEqual(self.req('/api/control/execute',{})[0],404)

if __name__=='__main__':unittest.main()
