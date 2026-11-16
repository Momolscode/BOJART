"""M06 integration contracts. Mock Jev/ASR fixtures are not live AI qualification."""
import concurrent.futures, copy, http.client, json, sqlite3, sys, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, Rejected
from consolidated_workbench import ConsolidatedWorkbench
from jarvis_runtime import CATALOG, COMMANDS, JarvisRuntime, VoiceLease
from jev_decider import JevDecider, MODEL
from workspace_state import restore_snapshot


def response(choice='workspace', confidence=1.0):
    n=len(CATALOG)+1
    top=confidence*(1-1/n)+1/n
    probabilities={k:(top if k==choice else (1-top)/(n-1)) for k in [*CATALOG,'clarify']}
    return {'model':MODEL,'answers':{'intent':{'type':'choice','choice':choice,'confidence':confidence,'probabilities':probabilities}}}


class JevTests(unittest.TestCase):
    def run_jev(self, answer):
        return JevDecider(enabled=True,key='fixture-not-a-key',transport=lambda p:answer).decide({'text':'le dossier','operation_id':None},CATALOG)
    def test_valid_choice(self):self.assertEqual(self.run_jev(response())['choice'],'workspace')
    def test_low_confidence(self):self.assertEqual(self.run_jev(response(confidence=.4))['choice'],'clarify')
    def test_unknown_choice(self):
        r=response();r['answers']['intent']['choice']='shell';self.assertEqual(self.run_jev(r)['choice'],'clarify')
    def test_missing_option(self):
        r=response();del r['answers']['intent']['probabilities']['model'];self.assertEqual(self.run_jev(r)['reason'],'unavailable_or_invalid')
    def test_nan(self):
        r=response();r['answers']['intent']['probabilities']['model']=float('nan');self.assertEqual(self.run_jev(r)['choice'],'clarify')
    def test_boolean_probability(self):
        r=response();r['answers']['intent']['probabilities']['model']=False;self.assertEqual(self.run_jev(r)['choice'],'clarify')
    def test_false_confidence(self):
        r=response(confidence=.3);r['answers']['intent']['confidence']=1.;self.assertEqual(self.run_jev(r)['choice'],'clarify')
    def test_confidence_out_of_range(self):
        r=response();r['answers']['intent']['confidence']=1.01;self.assertEqual(self.run_jev(r)['choice'],'clarify')
    def test_wrong_model(self):
        r=response();r['model']='jev-latest';self.assertEqual(self.run_jev(r)['choice'],'clarify')
    def test_no_key_no_call(self):
        with patch.object(JevDecider,'_http',side_effect=AssertionError('network')):
            self.assertFalse(JevDecider(enabled=True,key='').decide({'text':'x'},CATALOG)['called'])
    def test_payload_minimal(self):
        payloads=[]
        d=JevDecider(enabled=True,key='fixture',transport=lambda p:(payloads.append(p) or response()))
        d.decide({'text':'Ouvre les dossiers','operation_id':'opaque','secret':'hidden','project_id':'PRIVATE'},CATALOG)
        raw=json.dumps(payloads);self.assertNotIn('hidden',raw);self.assertNotIn('PRIVATE',raw);self.assertNotIn('opaque',raw)
    def test_failure_no_retry_and_cooldown(self):
        calls=[]
        def failed(p):calls.append(p);raise TimeoutError('secret must not leak')
        d=JevDecider(enabled=True,key='fixture',transport=failed)
        a=d.decide({'text':'x'},CATALOG);b=d.decide({'text':'x'},CATALOG)
        self.assertEqual(len(calls),1);self.assertNotIn('secret',json.dumps(a));self.assertFalse(b['called'])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(self.root/'work'))
        self.runtime=self.app.jarvis
    def tearDown(self):self.app.server_close();self.tmp.cleanup()
    def request(self,**kw):
        d={'request_id':'request01','client_id':'client01','project_id':'BOJ-PILOTE-001','revision':0,'text':'Montre les dossiers au centre','operation_id':None,'source':'typed'};d.update(kw);return d
    def mock_jev(self, transport=None):
        self.runtime.decider=JevDecider(enabled=True,key='fixture',transport=transport or (lambda p:response()))
    def test_local_path_never_calls_jev(self):
        self.mock_jev(lambda p:self.fail('Unexpected external call'))
        self.assertEqual(self.runtime.submit(self.request())['status'],'QUEUED')
    def test_every_catalog_command_routes_or_requests_model(self):
        for i,(key,(text,_)) in enumerate(COMMANDS.items()):
            r=self.runtime.submit(self.request(request_id='case'+str(i),text=text))
            self.assertEqual(r['status'],'CLARIFY' if key=='model' else 'QUEUED')
    def test_replay_one_command(self):
        a=self.runtime.submit(self.request());b=self.runtime.submit(self.request())
        self.assertEqual(a,b);self.assertEqual(len(self.app.tower.status()['commands']),1)
    def test_conflicting_request(self):
        self.runtime.submit(self.request())
        with self.assertRaises(Rejected):self.runtime.submit(self.request(text='Ouvre le studio'))
    def test_cross_project(self):
        with self.assertRaises(Rejected):self.runtime.submit(self.request(project_id='BOJ-ABSENT'))
    def test_boolean_revision(self):
        with self.assertRaises(Rejected):self.runtime.submit(self.request(revision=True))
    def test_extra_command_parameter(self):
        with self.assertRaises(Rejected):self.runtime.submit(self.request(shell='rm'))
    def test_stale_never_calls_jev(self):
        self.mock_jev(lambda p:self.fail('No stale external calls'))
        self.assertEqual(self.runtime.submit(self.request(text='ouvre ça',revision=3))['status'],'STALE')
    def test_unsupported_physical_request(self):
        self.assertEqual(self.runtime.submit(self.request(text='Imprime toutes les pièces'))['status'],'CLARIFY')
        self.assertEqual(len(self.app.tower.status()['commands']),0)
    def test_jev_requires_confirmation(self):
        self.mock_jev();r=self.runtime.submit(self.request(text='Le tableau des dossiers, s’il te plaît'))
        self.assertEqual(r['status'],'AWAITING_CONFIRMATION');self.assertIsNone(r['display'])
        self.assertEqual(self.runtime.confirm('request01','client01')['status'],'QUEUED')
    def test_confirmation_cannot_change_action(self):
        self.mock_jev();self.runtime.submit(self.request(text='mes dossiers'))
        with self.assertRaises(Rejected):self.runtime.confirm('request01','another_client')
        self.assertIsNone(self.runtime.get('request01')['display'])
    def test_expired_confirmation(self):
        self.mock_jev();self.runtime.submit(self.request(text='mes dossiers'))
        with self.app.store.connect() as db:db.execute('UPDATE jarvis_turns SET created=created-121')
        self.assertEqual(self.runtime.confirm('request01','client01')['status'],'STALE')
    def test_context_changes_while_deciding(self):
        def change(p):
            path=self.app.store.context_path;path.write_bytes(path.read_bytes()+b'\n');return response()
        self.mock_jev(change)
        self.assertEqual(self.runtime.submit(self.request(text='mes dossiers'))['status'],'STALE')
    def test_cancel_during_remote_decision(self):
        entered=threading.Event();finish=threading.Event()
        def slow(p):entered.set();finish.wait(5);return response()
        self.mock_jev(slow)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            f=pool.submit(self.runtime.submit,self.request(text='mes dossiers'))
            self.assertTrue(entered.wait(4));self.runtime.cancel('request01','client01');finish.set()
            self.assertEqual(f.result()['status'],'CANCELLED')
        self.assertEqual(len(self.app.tower.status()['commands']),0)
    def test_cancel_removes_queued_command(self):
        self.runtime.submit(self.request());self.runtime.cancel('request01','client01')
        screen=self.app.tower.pair('pilotage')
        self.assertIsNone(self.app.tower.poll(screen['screen_id'])['command'])
    def test_receipt_is_not_rendered_before_browser_ack(self):
        r=self.runtime.submit(self.request());self.assertIsNone(r['elapsed_to_display_ms'])
        screen=self.app.tower.pair('pilotage');self.app.tower.poll(screen['screen_id'])
        self.app.tower.ack(screen['screen_id'],'request01','rendered','fixture receipt')
        self.assertIsNotNone(self.runtime.get('request01')['elapsed_to_display_ms'])
    def test_restart_preserves_receipt_and_checkpoint(self):
        self.runtime.submit(self.request());self.runtime.close()
        self.app.jarvis=JarvisRuntime(self.app);self.runtime=self.app.jarvis
        self.assertEqual(self.runtime.submit(self.request())['status'],'QUEUED')
        self.assertEqual(len(self.app.tower.status()['commands']),1)
        if self.runtime.graph:
            self.assertEqual(self.runtime.graph.get_state({'configurable':{'thread_id':'boj-m06-request01'}}).values['status'],'QUEUED')
    def test_unknown_provider_outcome_not_recalled(self):
        self.runtime.submit(self.request(text='mes dossiers'))
        self.runtime._write('request01',status='INTERRUPTED',decision='pending')
        self.mock_jev(lambda p:self.fail('Do not repeat unknown request'))
        r=self.runtime.submit(self.request(text='mes dossiers'))
        self.assertEqual(r['status'],'CLARIFY');self.assertEqual(r['decision']['reason'],'provider_outcome_unknown_no_retry')
    def test_backup_includes_checkpoint_and_restore_neutralizes_approval(self):
        self.mock_jev();self.runtime.submit(self.request(text='mes dossiers'))
        backup=self.app.workspace.backup();target=self.root/'restored'
        restore_snapshot(self.app.store.root/backup['url'].lstrip('/'),target)
        other=ConsolidatedWorkbench(('127.0.0.1',0),Store(target))
        try:
            self.assertEqual(other.jarvis.get('request01')['status'],'RESTORED')
            with self.assertRaises(Rejected):other.jarvis.confirm('request01','client01')
            if other.jarvis.graph:self.assertTrue(other.jarvis.graph.get_state({'configurable':{'thread_id':'boj-m06-request01'}}).values)
        finally:other.server_close()
    def test_missing_graph_local_fallback(self):
        self.runtime.graph=None;self.runtime.graph_status='missing_dependency'
        self.assertEqual(self.runtime.submit(self.request())['status'],'QUEUED')
    def test_lease_exclusive_and_expires(self):
        now=[0];lease=VoiceLease(clock=lambda:now[0]);lease.claim('window1')
        with self.assertRaises(Rejected):lease.claim('window2')
        lease.claim('window2',release=True);self.assertTrue(lease.owns('window1'))
        now[0]=31;self.assertFalse(lease.owns('window1'));self.assertTrue(lease.claim('window2')['owned'])
    def test_backup_while_decision_pending_is_recoverable(self):
        entered=threading.Event();release=threading.Event()
        def slow(payload):entered.set();release.wait(10);return response()
        self.mock_jev(slow)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(self.runtime.submit,self.request(text='mes dossiers'))
            self.assertTrue(entered.wait(4))
            try:backup=self.app.workspace.backup()
            finally:release.set()
            self.assertEqual(future.result()['status'],'AWAITING_CONFIRMATION')
        target=self.root/'restore-pending';restore_snapshot(self.app.store.root/backup['url'].lstrip('/'),target)
        restored=ConsolidatedWorkbench(('127.0.0.1',0),Store(target))
        try:self.assertEqual(restored.jarvis.get('request01')['status'],'RESTORED')
        finally:restored.server_close()


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(self.tmp.name))
        self.thread=threading.Thread(target=self.app.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.app.shutdown();self.app.server_close();self.thread.join();self.tmp.cleanup()
    def req(self,path,body=None,auth=True,origin=True):
        h={'Cookie':'boj_session='+self.app.token} if auth else {}
        if body is not None:h.update({'Content-Type':'application/json','Origin':self.app.origin if origin else 'https://invalid.test'})
        c=http.client.HTTPConnection('127.0.0.1',self.app.server_port,timeout=5)
        c.request('GET' if body is None else 'POST',path,json.dumps(body) if body is not None else None,h)
        r=c.getresponse();b=r.read();c.close();return r.status,b
    def test_status_auth(self):self.assertEqual(self.req('/api/jarvis/status',auth=False)[0],401)
    def test_turn_origin(self):self.assertEqual(self.req('/api/jarvis/turn',{},origin=False)[0],403)
    def test_duplicate_query(self):self.assertEqual(self.req('/api/jarvis/turn?request_id=x&request_id=y')[0],409)
    def test_lease_api(self):self.assertEqual(self.req('/api/voice/lease',{'client_id':'window1','release':False})[0],200)
    def test_sse_auth(self):self.assertEqual(self.req('/api/tower/events',auth=False)[0],401)
    def test_voice_script(self):self.assertEqual(self.req('/tower_voice.js')[0],200)
    def test_view_poll_does_not_wait_for_cad_lock(self):
        screen=self.app.tower.pair('pilotage')
        with self.app.workspace.lock:
            self.assertEqual(self.req('/api/tower/poll',{'screen_id':screen['screen_id']})[0],200)
    def test_new_display_order_does_not_wait_for_cad_lock(self):
        body={'request_id':'during-cad','client_id':'window1','project_id':'BOJ-PILOTE-001','revision':0,'text':'Montre les dossiers au centre','operation_id':None,'source':'typed'}
        with self.app.workspace.lock:
            code,raw=self.req('/api/jarvis/turn',body)
            self.assertEqual(code,200);self.assertEqual(json.loads(raw)['status'],'QUEUED')


if __name__=='__main__':unittest.main()
