import unittest,sys,tempfile,threading,http.client,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Store
from studio_workbench import StudioWorkbench

class HTTPTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.server=StudioWorkbench(('127.0.0.1',0),Store(cls.temp.name))
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.token=cls.server.token;cls.port=cls.server.server_port;cls.origin=cls.server.origin
  cls.original=cls.server.library.segment('visage')['asset_id']
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()
 def request(self,path,body=None,headers=None,auth=True):
  h={'Cookie':'boj_session='+self.token} if auth else {}
  if body is not None:h.update({'Content-Type':'application/json','Origin':self.origin})
  h.update(headers or {});c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=20)
  c.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body),headers=h)
  r=c.getresponse();status=r.status;rh=dict(r.getheaders());data=r.read();c.close();return status,rh,data
 def plan(self,rid='http01'):
  return {'request_id':rid,'anchor_id':'visage','segment_ids':['profil','troisquarts','visage'],'expected_revisions':{'profil':1,'troisquarts':1,'visage':1}}
 def test_health(self):self.assertEqual(self.request('/health',auth=False)[0],200)
 def test_no_session_denied(self):self.assertEqual(self.request('/studio',auth=False)[0],401)
 def test_wrong_host_denied(self):self.assertEqual(self.request('/studio',headers={'Host':'evil.invalid'})[0],403)
 def test_studio_page(self):
  s,h,b=self.request('/studio');self.assertEqual(s,200);self.assertIn(b'MISSION 03',b)
 def test_m02_retained(self):
  s,h,b=self.request('/');self.assertEqual(s,200);self.assertIn(b'/studio',b)
 def test_security_headers(self):
  s,h,b=self.request('/studio');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy']);self.assertEqual(h['X-Content-Type-Options'],'nosniff')
 def test_catalogue_actual_probe(self):
  s,h,b=self.request('/api/studio/catalogue');d=json.loads(b);self.assertEqual(s,200);self.assertEqual(d['asset_count'],3);self.assertEqual(len(d['segments']),8);self.assertEqual(next(x for x in d['segments'] if x['id']=='visage')['metadata']['width'],512)
 def test_media_range(self):
  s,h,b=self.request('/api/studio/media/'+self.original,headers={'Range':'bytes=0-99'});self.assertEqual(s,206);self.assertEqual(len(b),100);self.assertTrue(h['Content-Range'].startswith('bytes 0-99/'))
 def test_media_full_integrity(self):
  s,h,b=self.request('/api/studio/media/'+self.original);self.assertEqual(s,200);self.assertEqual(hashlib.sha256(b).hexdigest(),self.original)
 def test_media_invalid_range(self):self.assertEqual(self.request('/api/studio/media/'+self.original,headers={'Range':'bytes=9999999999-'})[0],416)
 def test_media_path_not_accepted(self):self.assertEqual(self.request('/api/studio/media/../../etc/passwd')[0],409)
 def test_foreign_origin(self):self.assertEqual(self.request('/api/studio/prepare',self.plan(),headers={'Origin':'https://evil.invalid'})[0],403)
 def test_unauthenticated_post(self):self.assertEqual(self.request('/api/studio/prepare',self.plan(),auth=False)[0],401)
 def test_plan_real_persist_and_verify(self):
  s,h,b=self.request('/api/studio/prepare',self.plan());d=json.loads(b);self.assertEqual(s,200);self.assertFalse(d['publish_allowed'])
  s,h,b=self.request('/api/studio/verify',{'plan_id':d['id']});self.assertEqual(s,200);self.assertTrue(json.loads(b)['valid'])
 def test_plan_rejects_concept(self):
  d=self.plan('concept-test');d['segment_ids'].append('concept-v4');d['expected_revisions']['concept-v4']=1;self.assertEqual(self.request('/api/studio/prepare',d)[0],409)
 def test_plan_rejects_bad_anchor(self):
  d=self.plan('mixed-anchor');d['anchor_id']='intro';d['expected_revisions']['intro']=1;self.assertEqual(self.request('/api/studio/prepare',d)[0],409)
 def test_no_publish_endpoint(self):self.assertEqual(self.request('/api/studio/publish',{})[0],404)
 def test_no_generation_endpoint(self):self.assertEqual(self.request('/api/studio/generate',{})[0],404)
 def test_refresh_no_arbitrary_path(self):self.assertEqual(self.request('/api/studio/refresh',{'path':'/home'})[0],409)
 def test_no_media_paths_leaked(self):
  s,h,b=self.request('/api/studio/catalogue');self.assertNotIn(b'/mnt/data/',b)

if __name__=='__main__':unittest.main(verbosity=2)
