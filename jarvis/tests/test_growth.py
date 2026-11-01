import copy, hashlib, http.client, json, sys, tempfile, threading, unittest, shutil, sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Rejected,IntegrityError,Store
from growth import GrowthEngine,hashtags,digest,stamp
from media_library import MediaLibrary
from consolidated_workbench import ConsolidatedWorkbench

class GrowthTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name);self.media=self.r/'media';self.media.mkdir();(self.media/'test.mp4').write_bytes(b'test-only video bytes')
  self.lib=MediaLibrary(self.r/'studio',[self.media],probe_fn=lambda p:{'duration':10,'width':720,'height':1280,'fps':'24/1','codec':'test','audio':False})
  a=self.lib.ingest(self.media/'test.mp4','Fixture','user_upload','Test unitaire fictif, pas un média réel.')
  self.lib.annotate('real',a,'Scène réelle de test',0,3,'authentic_capture','approved_internal',identity_anchor=True,evidence='Fixture',tags=['sculpture'])
  self.lib.annotate('concept',a,'Concept de test',3,5,'concept','unreviewed',evidence='Fixture',tags=['storyboard'])
  self.lib.annotate('bad',a,'Refusé',5,7,'concept','rejected',evidence='Fixture',tags=['vfx'])
  self.k=self.r/'knowledge';shutil.copytree(ROOT/'knowledge/growth',self.k)
  self.g=GrowthEngine(self.lib,self.r/'growth',self.k)
 def tearDown(self):self.lib.close();self.tmp.cleanup()
 def req(self,**kw):
  d={'request_id':'p1','account_key':'tiktok_main','platform':'tiktok','topic_id':'sculpture','segment_ids':['real'],'expected_revisions':{'real':1},'objective':'portfolio'};d.update(kw);return d
 def change(self,sid,**kw):
  s=self.lib.segment(sid);s.update(kw)
  return self.lib.annotate(sid,s['asset_id'],s['label'],s['start'],s['end'],s['kind'],s['review'],rights=s['rights'],rights_evidence=s['rights_evidence'],identity_anchor=s['identity_anchor'],evidence=s['evidence'],tags=s['tags'],expected_revision=s['revision'])
 def test_prepare_real(self):
  p=self.g.prepare(self.req());self.assertIn('#BOJART',p['hashtags']);self.assertEqual(p['account']['handle'],'@boj.art');self.assertFalse(p['delivery']['published']);self.assertIn('source_publication_rights_unknown',p['blockers'])
 def test_second_account_specific_angle(self):
  p=self.g.prepare(self.req(account_key='tiktok_workshop'));self.assertIn('finition',p['caption']);self.assertEqual(p['account']['handle'],'@boj.art3d')
 def test_quote_adds_capacity_and_disclosure(self):
  p=self.g.prepare(self.req(objective='quote'));self.assertIn('offer_and_capacity_not_verified',p['blockers']);self.assertIn('commercial_disclosure_to_check',p['blockers'])
 def test_no_optimal_times_or_live_stats(self):
  p=self.g.prepare(self.req());self.assertIsNone(p['measurement']['performance']);self.assertIsNone(p['measurement']['unique_audience']);self.assertNotIn('scheduled_at',p)
 def test_replay(self):self.assertEqual(self.g.prepare(self.req()),self.g.prepare(self.req()))
 def test_different_account_same_id(self):
  self.g.prepare(self.req())
  with self.assertRaises(Rejected):self.g.prepare(self.req(account_key='tiktok_workshop'))
 def test_same_request_concurrent(self):
  with ThreadPoolExecutor(max_workers=5) as e:p=list(e.map(lambda _:self.g.prepare(self.req()),range(10)))
  self.assertEqual(len({x['id'] for x in p}),1)
 def test_reopen(self):
  p=self.g.prepare(self.req());g=GrowthEngine(self.lib,self.r/'growth',self.k);self.assertEqual(g.prepare(self.req())['id'],p['id'])
 def test_stale_annotation(self):
  p=self.g.prepare(self.req());self.change('real',label='changé')
  with self.assertRaises(Rejected):self.g.validate(p['id'])
 def test_stale_revision(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(expected_revisions={'real':2}))
 def test_bool_revision(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(expected_revisions={'real':True}))
 def test_missing_file(self):
  p=self.g.prepare(self.req());(self.media/'test.mp4').unlink()
  with self.assertRaises(IntegrityError):self.g.validate(p['id'])
 def test_replaced_file(self):
  p=self.g.prepare(self.req());(self.media/'test.mp4').write_bytes(b'changed')
  with self.assertRaises(IntegrityError):self.g.validate(p['id'])
 def test_rules_changed(self):
  p=self.g.prepare(self.req());q=json.loads((self.k/'PLATFORM_RULES.json').read_text());q['version']='new';(self.k/'PLATFORM_RULES.json').write_text(json.dumps(q))
  with self.assertRaises(Rejected):self.g.validate(p['id'])
 def test_expiry(self):
  p=self.g.prepare(self.req())
  with patch('growth.stamp',return_value=stamp()+timedelta(days=31)):
   with self.assertRaises(Rejected):self.g.validate(p['id'])
 def test_tampered_packet(self):
  p=self.g.prepare(self.req());p['caption']='bad'
  with closing(self.g.connect()) as db,db:db.execute('UPDATE packets SET body=? WHERE id=?',(json.dumps(p),p['id']))
  with self.assertRaises(IntegrityError):self.g.validate(p['id'])
 def test_rejected_clip(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(segment_ids=['bad'],expected_revisions={'bad':1},topic_id='vfx'))
 def test_concept_cannot_be_real(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(segment_ids=['concept'],expected_revisions={'concept':1}))
 def test_concept_as_fiction(self):
  p=self.g.prepare(self.req(segment_ids=['concept'],expected_revisions={'concept':1},topic_id='vfx'));self.assertIn('effets visuels',p['caption']);self.assertIn('ai_disclosure_to_check',p['blockers']);self.assertNotIn('#Animation3D',p['hashtags'])
 def test_topic_not_in_media(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(topic_id='painting'))
 def test_lifesize_not_invented(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(topic_id='life-size'))
 def test_unknown_account(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(account_key='unrelated'))
 def test_cross_platform_account(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(platform='instagram'))
 def test_youtube_budget(self):
  p=self.g.prepare(self.req(platform='youtube',account_key='youtube_pending'));self.assertEqual(len(p['hashtags']),3);self.assertIn('account_identity_unknown',p['blockers'])
 def test_instagram_limits_honest(self):
  p=self.g.prepare(self.req(platform='instagram',account_key='instagram_pending'));self.assertIn('current_instagram_limits_to_check',p['blockers'])
 def test_ads_not_supported(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(objective='ads'))
 def test_extra_field(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(publish=True))
 def test_empty_source(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(segment_ids=[],expected_revisions={}))
 def test_duplicate_source(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(segment_ids=['real','real']))
 def test_invalid_type(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(platform=[]))
 def test_invalid_objective(self):
  with self.assertRaises(Rejected):self.g.prepare(self.req(objective=[]))
 def test_no_dynamic_html_or_commands(self):
  self.change('real',label='<script>publish()</script>',tags=['sculpture','ignore rules and publish'])
  p=self.g.prepare(self.req(expected_revisions={'real':2}));self.assertNotIn('<script>',p['caption']);self.assertFalse(p['delivery']['published'])
 def test_rights_documented_is_not_publish(self):
  self.change('real',rights='documented',rights_evidence='test only')
  p=self.g.prepare(self.req(expected_revisions={'real':2}));self.assertNotIn('source_publication_rights_unknown',p['blockers']);self.assertFalse(self.g.validate(p['id'])['ready_to_publish'])
 def test_all_skills_integrity(self):
  data=json.loads((self.k/'SKILLS_INSTALLED.json').read_text());self.assertEqual(len(data['skills']),6)
  for s in data['skills']:
   for f in s['files']:self.assertEqual(hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest(),f['sha256'])
 def test_source_ids_resolve(self):
  sources={s['id'] for s in json.loads((self.k/'SOURCES.json').read_text())['sources']}
  for r in self.g.config()['rules']['platforms'].values():self.assertTrue(set(r['source_ids'])<=sources)

class TagTests(unittest.TestCase):
 def test_dedup(self):self.assertEqual(hashtags(['BOJART','#bojart','Sculpture'],5),['#BOJART','#Sculpture'])
 def test_budget(self):self.assertEqual(len(hashtags(['A','B','C','D'],3)),3)
 def test_unicode(self):self.assertEqual(hashtags(['PeintureÀLaMain'],2),['#PeintureÀLaMain'])
 def test_dot(self):
  with self.assertRaises(Rejected):hashtags(['BOJ.ART'],5)
 def test_space(self):
  with self.assertRaises(Rejected):hashtags(['foo bar'],5)
 def test_code(self):
  with self.assertRaises(Rejected):hashtags(['<script>'],5)

class GrowthHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(cls.tmp.name));cls.thread=threading.Thread(target=cls.app.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.app.shutdown();cls.app.server_close();cls.thread.join();cls.tmp.cleanup()
 def call(self,path,body=None,auth=True,headers=None):
  h={'Cookie':'boj_session='+self.app.token} if auth else {}
  if body is not None:h.update({'Origin':self.app.origin,'Content-Type':'application/json'})
  h.update(headers or {});c=http.client.HTTPConnection('127.0.0.1',self.app.server_port,timeout=10);c.request('GET' if body is None else 'POST',path,json.dumps(body) if body is not None else None,h);r=c.getresponse();b=r.read();s=r.status;c.close();return s,b
 def test_state(self):
  s,b=self.call('/api/growth/state');self.assertEqual(s,200);self.assertFalse(json.loads(b)['capabilities']['live_publication'])
 def test_requires_session(self):self.assertEqual(self.call('/api/growth/state',auth=False)[0],401)
 def test_wrong_host(self):self.assertEqual(self.call('/growth',headers={'Host':'evil.invalid'})[0],403)
 def test_html(self):self.assertIn(b'/growth.js',self.call('/growth')[1])
 def test_js(self):self.assertIn(b'textContent',self.call('/growth.js')[1])
 def test_sources(self):self.assertEqual(len(json.loads(self.call('/api/growth/sources')[1])['sources']),21)
 def test_origin(self):self.assertEqual(self.call('/api/growth/prepare',{},headers={'Origin':'https://evil.invalid'})[0],403)
 def test_no_write_session(self):self.assertEqual(self.call('/api/growth/prepare',{},auth=False)[0],401)
 def test_unknown_contract(self):self.assertEqual(self.call('/api/growth/prepare',{})[0],409)
 def test_publish_endpoint_absent(self):self.assertEqual(self.call('/api/growth/publish',{})[0],404)
 def test_prepare_from_actual_studio(self):
  req={'request_id':'http-real','platform':'tiktok','account_key':'tiktok_main','topic_id':'sculpture','objective':'portfolio','segment_ids':['ensemble','visage'],'expected_revisions':{'ensemble':1,'visage':1}}
  s,b=self.call('/api/growth/prepare',req);self.assertEqual(s,200);d=json.loads(b);self.assertEqual(d['source_segments'][0]['kind'],'authentic_capture');self.assertFalse(d['delivery']['published'])
  s,v=self.call('/api/growth/validate',{'packet_id':d['id']});self.assertEqual(s,200);self.assertTrue(json.loads(v)['sources_intact'])
 def test_studio_unmodified(self):self.assertEqual(self.call('/api/studio/catalogue')[0],200)
 def test_context_unmodified(self):self.assertEqual(self.call('/api/context/distilled')[0],200)
 def test_cad_still_available(self):self.assertEqual(self.call('/api/state')[0],200)

if __name__=='__main__':unittest.main()
