"""Behaviour and geometric tests. Temporary directories; no printer/network providers."""
import sys, unittest, json, tempfile, shutil, threading, uuid, zipfile, sqlite3
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import *
from context_guard import validate_context,operational_value,render_brief
from server import AppServer,strict_loads
ROOT=Path(__file__).resolve().parents[1]

class GeometryTests(unittest.TestCase):
    def test_01_default_exports_closed_and_readable(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'out';r=build_geometry(BaseSpec(),p)
            self.assertTrue(r['stl_watertight']);self.assertEqual(r['solid_count'],1)
            import cadquery as cq, trimesh
            step=cq.importers.importStep(str(p/'socle.step'))
            self.assertTrue(step.val().isValid());self.assertEqual(len(step.solids().vals()),1)
            glb=trimesh.load(str(p/'socle_metres.glb'))
            self.assertAlmostEqual(glb.bounds[1][0]-glb.bounds[0][0],.18,places=4)
    def test_02_new_dimensions_really_change_geometry(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'out';spec=BaseSpec.from_dict(parse_command('Crée un socle de 24 cm')['params'])
            r=build_geometry(spec,p);self.assertAlmostEqual(r['bounds_mm'][0],240,places=3)
    def test_03_small_base(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'out';spec=BaseSpec.from_dict(parse_command('Prépare un socle de 12 cm')['params'])
            r=build_geometry(spec,p);self.assertAlmostEqual(r['bounds_mm'][0],120,places=3)

class ContractTests(unittest.TestCase):
    def test_04_parse_mm(self):self.assertEqual(parse_command('Jarvis, crée un socle de 180 mm et affiche-le à droite')['params']['diameter_mm'],180)
    def test_05_parse_cm(self):self.assertEqual(parse_command('Prépare un socle de 18 cm')['params']['diameter_mm'],180)
    def test_06_parse_inches(self):self.assertAlmostEqual(parse_command('Crée un socle de 7 pouces')['params']['diameter_mm'],177.8)
    def test_07_decimal_comma(self):self.assertEqual(parse_command('Génère un socle de 18,5 cm')['params']['diameter_mm'],185)
    def test_08_missing_units_rejected(self):
        with self.assertRaises(Rejected):parse_command('Crée un socle de 180')
    def test_09_extra_constraint_not_silently_ignored(self):
        with self.assertRaises(Rejected):parse_command('Crée un socle de 180 mm pour porter 5 kg')
    def test_10_print_command_not_interpreted(self):
        with self.assertRaises(Rejected):parse_command('Crée un socle de 180 mm et lance P01')
    def test_11_code_not_executed(self):
        with self.assertRaises(Rejected):parse_command("Crée un socle de 180 mm; __import__('os').system('echo bad')")
    def test_12_outside_recipe_limits(self):
        with self.assertRaises(Rejected):parse_command('Crée un socle de 180 cm')
    def test_13_nonfinite_params(self):
        d=asdict(BaseSpec());d['diameter_mm']=float('nan')
        with self.assertRaises(Rejected):BaseSpec.from_dict(d)
    def test_14_boolean_not_dimension(self):
        d=asdict(BaseSpec());d['height_mm']=True
        with self.assertRaises(Rejected):BaseSpec.from_dict(d)
    def test_15_holes_outside_top(self):
        d=asdict(BaseSpec());d['pitch_mm']=149
        with self.assertRaises(Rejected):BaseSpec.from_dict(d)
    def test_16_chamfer_too_large(self):
        d=asdict(BaseSpec());d['chamfer_mm']=3
        with self.assertRaises(Rejected):BaseSpec.from_dict(d)
    def test_17_unknown_field(self):
        d=asdict(BaseSpec());d['execute']=True
        with self.assertRaises(Rejected):BaseSpec.from_dict(d)
    def test_18_no_duplicate_json_keys(self):
        with self.assertRaises(Rejected):strict_loads('{"a":1,"a":2}')
    def test_19_json_nan(self):
        with self.assertRaises(Rejected):strict_loads('{"a": NaN}')

class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.fixture=Path(cls.tmp.name)/'cad'
        cls.proof=build_geometry(BaseSpec(),cls.fixture)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name)/'state')
        self.request={'operation_id':uuid.uuid4().hex,'project_id':'BOJ-PILOTE-001','expected_revision':0,'params':asdict(BaseSpec())};self.calls=0
    def tearDown(self):self.temp.cleanup()
    def builder(self,spec,dest):
        self.calls+=1;shutil.copytree(self.fixture,dest);return self.proof
    def run_one(self):return self.store.run(self.request,self.builder)
    def test_20_mission_receipt(self):
        r=self.run_one();self.assertEqual(r['state'],'READY');self.assertEqual(r['revision'],1);self.assertFalse(r['physical_commands_enabled'])
    def test_21_duplicate_same_id_not_regenerated(self):
        a=self.run_one();b=self.run_one();self.assertEqual(a,b);self.assertEqual(self.calls,1)
    def test_22_idempotent_after_restart(self):
        a=self.run_one();b=Store(self.store.root).run(self.request,self.builder);self.assertEqual(a,b);self.assertEqual(self.calls,1)
    def test_23_duplicate_key_different_content(self):
        self.run_one();self.request['params']['height_mm']=25
        with self.assertRaises(Rejected):self.run_one()
    def test_24_stale_revision_rejected(self):
        self.run_one();self.request['operation_id']=uuid.uuid4().hex
        with self.assertRaises(Rejected):self.run_one()
    def test_25_real_revisions_are_preserved(self):
        a=self.run_one();self.request['operation_id']=uuid.uuid4().hex;self.request['expected_revision']=1
        b=self.run_one();self.assertEqual(b['revision'],2);self.assertTrue((self.store.artifacts/a['operation_id']/'socle.stl').exists())
    def test_26_no_path_traversal_project(self):
        self.request['project_id']='../../bad'
        with self.assertRaises(Rejected):self.run_one()
    def test_27_no_path_traversal_operation(self):
        self.request['operation_id']='../something'
        with self.assertRaises(Rejected):self.run_one()
    def test_28_missing_file_detected(self):
        r=self.run_one();(self.store.artifacts/r['operation_id']/'socle.stl').unlink()
        with self.assertRaises(IntegrityError):self.store.get(r['operation_id'])
    def test_29_altered_file_detected(self):
        r=self.run_one();(self.store.artifacts/r['operation_id']/'socle.step').write_bytes(b'altered')
        with self.assertRaises(IntegrityError):self.store.get(r['operation_id'])
    def test_30_altered_manifest_detected(self):
        r=self.run_one();(self.store.artifacts/r['operation_id']/'manifeste.json').write_text('{}')
        with self.assertRaises(IntegrityError):self.store.get(r['operation_id'])
    def test_31_builder_failure_not_ready(self):
        def fail(s,p):raise RuntimeError('simulated failure')
        with self.assertRaises(RuntimeError):self.store.run(self.request,fail)
        self.assertEqual(self.store.get(self.request['operation_id'])['state'],'FAILED');self.assertEqual(self.store.project_revision(),0)
    def test_32_interrupted_job_not_silently_replayed(self):
        r=self.run_one()
        with self.store.connect() as db:db.execute("UPDATE operations SET state='RUNNING' WHERE id=?",(r['operation_id'],))
        self.assertEqual(self.run_one()['state'],'RUNNING');self.assertEqual(self.calls,1)
    def test_33_interrupted_job_blocks_new_operation(self):
        r=self.run_one()
        with self.store.connect() as db:db.execute("UPDATE operations SET state='RUNNING' WHERE id=?",(r['operation_id'],))
        self.request['operation_id']=uuid.uuid4().hex;self.request['expected_revision']=1
        with self.assertRaises(Rejected):self.run_one()
    def test_34_concurrent_clients_one_result(self):
        results=[];errors=[]
        def work():
            try:results.append(self.store.run(self.request,self.builder))
            except Exception as e:errors.append(e)
        th=[threading.Thread(target=work) for _ in range(2)]
        for t in th:t.start()
        for t in th:t.join()
        self.assertFalse(errors);self.assertEqual(self.calls,1);self.assertEqual(self.store.project_revision(),1)
    def test_35_snapshot_and_restore(self):
        r=self.run_one();dest=Path(self.temp.name)/'snapshot.zip';self.store.backup(dest);self.assertTrue(verify_backup(dest)['ok'])
        restored=Path(self.temp.name)/'restored'
        with zipfile.ZipFile(dest) as z:z.extractall(restored)
        s=Store(restored,restored/'CONTEXTE_REFERENCE.json');self.assertEqual(s.get(r['operation_id']),r)
        self.assertEqual(s.project_revision(),1)
    def test_36_backup_rejects_running(self):
        r=self.run_one()
        with self.store.connect() as db:db.execute("UPDATE operations SET state='RUNNING' WHERE id=?",(r['operation_id'],))
        with self.assertRaises(Rejected):self.store.backup(Path(self.temp.name)/'blocked.zip')
    def test_37_backup_rejects_corruption(self):
        r=self.run_one();(self.store.artifacts/r['operation_id']/'socle.stl').write_bytes(b'bad')
        with self.assertRaises(IntegrityError):self.store.backup(Path(self.temp.name)/'bad.zip')
    def test_38_backup_no_overwrite(self):
        self.run_one();dest=Path(self.temp.name)/'exists.zip';self.store.backup(dest)
        with self.assertRaises(Rejected):self.store.backup(dest)
    def test_39_malicious_archive_path(self):
        p=Path(self.temp.name)/'evil.zip'
        with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','bad');z.writestr('SHA256.json','{}')
        with self.assertRaises(IntegrityError):verify_backup(p)

class ContextTests(unittest.TestCase):
    def setUp(self):self.doc=json.loads((ROOT/'context/CONTEXTE_REFERENCE.json').read_text())
    def test_40_context_valid(self):self.assertTrue(validate_context(self.doc))
    def test_41_conflict_facts_rejected(self):
        self.doc['facts'].append(self.doc['facts'][0])
        with self.assertRaises(ValueError):validate_context(self.doc)
    def test_42_verified_claim_needs_evidence(self):
        self.doc['facts'][0]['status']='verified_here'
        with self.assertRaises(ValueError):validate_context(self.doc)
    def test_43_unknown_not_zero(self):
        self.doc['facts'][0]['status']='unknown'
        with self.assertRaises(ValueError):validate_context(self.doc)
    def test_44_fresh_observation_allowed(self):
        t=datetime.now(timezone.utc);f={'status':'verified_here','value':'ready','observed_at':t.isoformat(),'max_age_seconds':30}
        self.assertEqual(operational_value(f,t+timedelta(seconds=2)),'ready')
    def test_45_stale_observation_rejected(self):
        t=datetime.now(timezone.utc);f={'status':'verified_here','value':'ready','observed_at':t.isoformat(),'max_age_seconds':30}
        self.assertIsNone(operational_value(f,t+timedelta(seconds=31)))
    def test_46_future_timestamp_rejected(self):
        t=datetime.now(timezone.utc);f={'status':'verified_here','value':'ready','observed_at':(t+timedelta(seconds=30)).isoformat(),'max_age_seconds':60}
        self.assertIsNone(operational_value(f,t))
    def test_47_proposal_not_state(self):self.assertIsNone(operational_value({'status':'proposed','value':'ready'}))
    def test_48_scope_not_mixed(self):
        self.doc['project_id']='UNUM'
        with self.assertRaises(ValueError):validate_context(self.doc)
    def test_49_readable_context(self):self.assertIn('3',render_brief(self.doc));self.assertIn('Contraintes',render_brief(self.doc))

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.store=Store(cls.tmp.name)
        cls.server=AppServer(('127.0.0.1',0),cls.store,'test-secret')
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        import http.client
        h={'Host':self.server.host_name,**(headers or {})}
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10);c.request(method,path,body,h)
        r=c.getresponse();s=r.status;b=r.read();hs=dict(r.getheaders());c.close();return s,b,hs
    def test_50_wrong_host_denied(self):self.assertEqual(self.request('GET','/health',headers={'Host':'evil.example'})[0],403)
    def test_51_session_required(self):self.assertEqual(self.request('GET','/api/state')[0],401)
    def test_52_bootstrap_session(self):
        s,b,h=self.request('GET','/?session=test-secret');self.assertEqual(s,303);self.assertIn('HttpOnly',h['Set-Cookie']);self.assertEqual(h['Location'],'/')
    def test_53_foreign_origin_rejected(self):
        s,_,_=self.request('POST','/api/parse','{}',{'Cookie':'boj_session=test-secret','Origin':'https://evil.test','Content-Type':'application/json'});self.assertEqual(s,403)
    def test_54_missing_origin_rejected(self):
        s,_,_=self.request('POST','/api/parse','{}',{'Cookie':'boj_session=test-secret','Content-Type':'application/json'});self.assertEqual(s,403)
    def test_55_valid_parse_without_cloud(self):
        s,b,_=self.request('POST','/api/parse',json.dumps({'command':'Crée un socle de 18 cm'}),{'Cookie':'boj_session=test-secret','Origin':self.server.origin,'Content-Type':'application/json'})
        self.assertEqual(s,200);self.assertFalse(json.loads(b)['llm_used'])
    def test_56_no_machine_endpoint(self):
        s,_,_=self.request('POST','/api/printer/start','{}',{'Cookie':'boj_session=test-secret','Origin':self.server.origin,'Content-Type':'application/json'});self.assertEqual(s,404)
    def test_57_html_auth_and_headers(self):
        s,b,h=self.request('GET','/',headers={'Cookie':'boj_session=test-secret'});self.assertEqual(s,200);self.assertIn('frame-ancestors',h['Content-Security-Policy']);self.assertIn(b'Mission 01',b)
    def test_58_artifact_path_traversal_denied(self):
        s,_,_=self.request('GET','/artifacts/../../etc/passwd',headers={'Cookie':'boj_session=test-secret'});self.assertNotEqual(s,200)

    def test_59_http_real_full_mission_and_download(self):
        req={'operation_id':'d'*32,'project_id':'BOJ-PILOTE-001','expected_revision':0,'params':asdict(BaseSpec())}
        headers={'Cookie':'boj_session=test-secret','Origin':self.server.origin,'Content-Type':'application/json'}
        status,body,_=self.request('POST','/api/mission',json.dumps(req),headers)
        self.assertEqual(status,200);r=json.loads(body);self.assertEqual(r['state'],'READY')
        self.assertTrue(r['proof']['stl_watertight'])
        status,stl,_=self.request('GET','/artifacts/'+r['operation_id']+'/socle.stl',headers={'Cookie':'boj_session=test-secret'})
        self.assertEqual(status,200);self.assertEqual(digest_bytes(stl),r['files']['socle.stl']['sha256'])
        status,again,_=self.request('POST','/api/mission',json.dumps(req),headers)
        self.assertEqual(json.loads(again),r);self.assertEqual(self.store.project_revision(),1)
    def test_60_wrong_content_type(self):
        status,_,_=self.request('POST','/api/parse','{}',{'Cookie':'boj_session=test-secret','Origin':self.server.origin,'Content-Type':'text/plain'})
        self.assertEqual(status,415)
    def test_61_oversized_body(self):
        status,_,_=self.request('POST','/api/parse','x'*17000,{'Cookie':'boj_session=test-secret','Origin':self.server.origin,'Content-Type':'application/json'})
        self.assertEqual(status,413)
    def test_62_http_backup_retrieval(self):
        status,body,_=self.request('POST','/api/backup','{}',{'Cookie':'boj_session=test-secret','Origin':self.server.origin,'Content-Type':'application/json'})
        self.assertEqual(status,200);r=json.loads(body)
        status,backup,_=self.request('GET',r['url'],headers={'Cookie':'boj_session=test-secret'})
        self.assertEqual(status,200);self.assertEqual(digest_bytes(backup),r['sha256'])

if __name__=='__main__':unittest.main(verbosity=2)
