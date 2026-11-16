"""M04: test local browser routing and readiness, no physical equipment or paid service."""
import concurrent.futures, http.client, json, sys, tempfile, threading, unittest, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, Rejected
from display_contracts import DisplayProposals
from control_tower import ControlTower
from launch_readiness import assessment, REQUIRED_GATES
from consolidated_workbench import ConsolidatedWorkbench

class TowerContracts(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
  self.book=DisplayProposals(self.store);self.tower=ControlTower(self.store,self.book)
 def tearDown(self):self.temp.cleanup()
 def prepare(self,request_id='req1',command='Montre les sources au centre'):
  return self.book.prepare({'request_id':request_id,'turn_id':'t1','project_id':'BOJ-PILOTE-001','revision':self.store.project_revision(),'command':command,'operation_id':None})
 def test_pair(self):
  s=self.tower.pair('pilotage','Vue centre');self.assertEqual(s['role'],'pilotage');self.assertTrue(s['paired'])
 def test_pair_unknown_role(self):
  with self.assertRaises(Rejected):self.tower.pair('machine','x')
 def test_pair_bad_label(self):
  with self.assertRaises(Rejected):self.tower.pair('pilotage','\n')
 def test_pair_unique(self):
  self.assertNotEqual(self.tower.pair('pilotage')['screen_id'],self.tower.pair('pilotage')['screen_id'])
 def test_pair_bounded(self):
  for _ in range(3):self.tower.pair('atelier')
  with self.assertRaises(Rejected):self.tower.pair('atelier')
 def test_status_online(self):
  self.tower.pair('atelier');self.assertEqual(self.tower.status()['roles']['atelier'],1)
 def test_unknown_screen(self):
  with self.assertRaises(Rejected):self.tower.poll('unknown')
 def test_heartbeat(self):
  s=self.tower.pair('creation');self.assertTrue(self.tower.heartbeat(s['screen_id'])['online'])
 def test_dispatch_requires_proposal(self):
  with self.assertRaises(Rejected):self.tower.dispatch('none')
 def test_dispatch_known(self):
  self.prepare();self.assertEqual(self.tower.dispatch('req1')['state'],'queued')
 def test_dispatch_idempotent(self):
  self.prepare();self.tower.dispatch('req1');self.assertTrue(self.tower.dispatch('req1')['replayed'])
 def test_dispatch_stale_context(self):
  self.prepare();self.store.context_path.write_text(self.store.context_path.read_text()+'\n')
  with self.assertRaises(Rejected):self.tower.dispatch('req1')
 def test_poll_wrong_role(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('atelier')
  self.assertIsNone(self.tower.poll(s['screen_id'])['command'])
 def test_poll_correct_role(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage')
  self.assertEqual(self.tower.poll(s['screen_id'])['command']['action'],'show_sources')
 def test_second_view_does_not_duplicate(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage');other=self.tower.pair('pilotage')
  self.tower.poll(s['screen_id']);self.assertIsNone(self.tower.poll(other['screen_id'])['command'])
 def test_lost_browser_requeues_after_lease(self):
  self.prepare();self.tower.dispatch('req1');old=self.tower.pair('pilotage');self.tower.poll(old['screen_id'])
  with self.tower.db() as con:
   con.execute('UPDATE commands SET updated=0 WHERE request_id=?',('req1',))
   con.execute('UPDATE screens SET last_seen=0 WHERE screen_id=?',(old['screen_id'],))
  new=self.tower.pair('pilotage');p=self.tower.poll(new['screen_id'])
  self.assertEqual(p['command']['request_id'],'req1')
  with self.assertRaises(Rejected):self.tower.ack(old['screen_id'],'req1','rendered','old')
 def test_ack_success(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage');self.tower.poll(s['screen_id'])
  self.assertEqual(self.tower.ack(s['screen_id'],'req1','rendered','Vue prête')['state'],'rendered')
 def test_ack_failed(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage');self.tower.poll(s['screen_id'])
  self.assertEqual(self.tower.ack(s['screen_id'],'req1','failed','Fichier absent')['state'],'failed')
 def test_ack_not_delivered(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage')
  with self.assertRaises(Rejected):self.tower.ack(s['screen_id'],'req1','rendered','OK')
 def test_ack_wrong_view(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage');o=self.tower.pair('pilotage');self.tower.poll(s['screen_id'])
  with self.assertRaises(Rejected):self.tower.ack(o['screen_id'],'req1','rendered','OK')
 def test_ack_idempotent(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage');self.tower.poll(s['screen_id']);self.tower.ack(s['screen_id'],'req1','rendered','OK')
  self.assertTrue(self.tower.ack(s['screen_id'],'req1','rendered','OK')['replayed'])
 def test_ack_conflict(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage');self.tower.poll(s['screen_id']);self.tower.ack(s['screen_id'],'req1','rendered','OK')
  with self.assertRaises(Rejected):self.tower.ack(s['screen_id'],'req1','failed','error')
 def test_ack_bad_status(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage');self.tower.poll(s['screen_id'])
  with self.assertRaises(Rejected):self.tower.ack(s['screen_id'],'req1','printed','OK')
 def test_ack_stale(self):
  self.prepare();self.tower.dispatch('req1');s=self.tower.pair('pilotage');self.tower.poll(s['screen_id'])
  self.store.context_path.write_text(self.store.context_path.read_text()+'\n')
  with self.assertRaises(Rejected):self.tower.ack(s['screen_id'],'req1','rendered','OK')
  self.assertEqual(self.tower.status()['commands'][0]['state'],'stale')
 def test_poll_stale(self):
  self.prepare();self.tower.dispatch('req1');self.store.context_path.write_text(self.store.context_path.read_text()+'\n')
  s=self.tower.pair('pilotage');self.assertIsNone(self.tower.poll(s['screen_id'])['command'])
  self.assertEqual(self.tower.status()['commands'][0]['state'],'stale')
 def test_reopen_persists(self):
  self.prepare();self.tower.dispatch('req1');other=ControlTower(self.store,self.book)
  self.assertEqual(other.status()['commands'][0]['state'],'queued')
 def test_no_physical(self):
  self.prepare();self.tower.dispatch('req1');self.assertFalse(self.tower.status()['printer_commands_enabled'])
 def test_parallel_idempotency(self):
  self.prepare();
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
   rows=list(pool.map(lambda _:self.tower.dispatch('req1'),range(8)))
  self.assertEqual(sum(not x['replayed'] for x in rows),1)
 def test_gate_count(self):
  c={'voice':{'enabled':False},'ollama':{'enabled':False}}
  a=assessment(self.store,self.tower,c);self.assertEqual(len(a['gates']),len(REQUIRED_GATES));self.assertFalse(a['production_ready'])
 def test_no_green_without_hardware(self):
  c={'voice':{'enabled':True},'ollama':{'enabled':True}}
  a=assessment(self.store,self.tower,c);self.assertFalse(a['production_ready'])
  self.assertEqual(next(g for g in a['gates'] if g['id']=='screen_physical')['state'],'unverified')
 def test_status_no_claim_of_monitor(self):
  self.tower.pair('atelier');self.tower.pair('pilotage');self.tower.pair('creation')
  self.assertFalse(self.tower.status()['physical_monitor_mapping_verified'])
 def test_unknown_action_rejected_by_book(self):
  with self.assertRaises(Rejected):self.prepare(command='Imprime la figurine et publie sur TikTok')

class TowerHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.server=ConsolidatedWorkbench(('127.0.0.1',0),Store(cls.temp.name))
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()
 def req(self,path,body=None,auth=True,origin=True):
  headers={'Cookie':'boj_session='+self.server.token} if auth else {}
  if body is not None:
   headers['Content-Type']='application/json'
   if origin:headers['Origin']=self.server.origin
  con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
  con.request('GET' if body is None else 'POST',path,body=json.dumps(body) if body is not None else None,headers=headers)
  resp=con.getresponse();b=resp.read();status=resp.status;con.close();return status,b
 def test_readiness_http(self):
  s,b=self.req('/api/launch/readiness');self.assertEqual(s,200);self.assertFalse(json.loads(b)['production_ready'])
 def test_tower_html(self):
  s,b=self.req('/tower');self.assertEqual(s,200);self.assertIn(b'JARVIS',b)
 def test_tower_screen_html(self):
  s,b=self.req('/tower/screen?role=creation');self.assertEqual(s,200);self.assertIn(b'canvas',b)
 def test_tower_js(self):self.assertEqual(self.req('/tower.js')[0],200)
 def test_screen_js(self):self.assertEqual(self.req('/tower_screen.js')[0],200)
 def test_no_auth(self):self.assertEqual(self.req('/api/tower/state',auth=False)[0],401)
 def test_post_origin(self):self.assertEqual(self.req('/api/tower/pair',{'role':'atelier','label':'Vue'},origin=False)[0],403)
 def test_pair_http(self):
  s,b=self.req('/api/tower/pair',{'role':'atelier','label':'Vue'});self.assertEqual(s,200);self.assertTrue(json.loads(b)['paired'])
 def test_dispatch_requires_proposal_http(self):
  s,b=self.req('/api/tower/dispatch',{'request_id':'absent'});self.assertEqual(s,409)
 def test_unexpected_fields_http(self):
  s,b=self.req('/api/tower/pair',{'role':'atelier','label':'Vue','execute':True});self.assertEqual(s,409)
 def test_tower_status_http(self):
  s,b=self.req('/api/tower/state');self.assertEqual(s,200);self.assertFalse(json.loads(b)['printer_commands_enabled'])
 def test_no_printer_route(self):
  s,b=self.req('/api/tower/start_printer',{'printer':'P01'});self.assertEqual(s,404)

if __name__=='__main__':unittest.main()
