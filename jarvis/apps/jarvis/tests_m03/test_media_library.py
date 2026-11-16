import sys,tempfile,unittest,shutil,json,zipfile,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from media_library import MediaLibrary,Rejected,IntegrityError,MAX_FILE,verify_archive,probe

class MediaTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.media=self.root/'media';self.media.mkdir()
  self.file=self.media/'original.mp4';self.file.write_bytes(b'original footage for unit tests')
  self.fake=lambda p: {'duration':15.1,'width':512,'height':1108,'fps':'30/1','codec':'h264','audio':True}
  self.lib=MediaLibrary(self.root/'state',[self.media],self.fake)
  self.a=self.lib.ingest(self.file,'original','user_upload','test fixture; metadata probe mocked')
  self.s=self.lib.annotate('real',self.a,'Sculpture réelle',5,6,'authentic_capture','approved_internal',identity_anchor=True,evidence='test annotation',tags=['sculpture','référence'])
 def tearDown(self):self.lib.close();self.temp.cleanup()
 def req(self):return {'request_id':'request1','anchor_id':'real','segment_ids':['real'],'expected_revisions':{'real':1}}
 def update(self,**overrides):
  d=dict(sid='real',asset_id=self.a,label='Sculpture réelle',start=5,end=6,kind='authentic_capture',review='approved_internal',identity_anchor=True,evidence='test annotation',tags=['sculpture','référence'],expected_revision=1);d.update(overrides);return self.lib.annotate(**d)
 def test_ingest_metadata(self):self.assertEqual(self.lib.asset(self.a)['metadata']['duration'],15.1)
 def test_duplicate_content_one_asset(self):
  b=self.media/'copy.mp4';shutil.copy2(self.file,b);self.assertEqual(self.a,self.lib.ingest(b,'copy','user_upload','same'));self.assertEqual(self.lib.catalogue()['asset_count'],1)
 def test_relocation_preserves_identity(self):
  b=self.media/'moved.mp4';self.file.rename(b);self.assertEqual(self.a,self.lib.ingest(b,'moved','user_upload','same'));self.assertEqual(self.lib.available(self.a),b)
 def test_missing_keeps_catalogue(self):
  self.file.unlink();c=self.lib.catalogue();self.assertEqual(c['asset_count'],1);self.assertEqual(c['segments'][0]['availability'],'missing_or_changed')
 def test_mutated_source_is_not_substituted(self):
  self.file.write_bytes(b'new');self.assertRaises(IntegrityError,self.lib.available,self.a)
 def test_changed_file_new_id(self):
  self.file.write_bytes(b'new');b=self.lib.ingest(self.file,'new','user_upload','changed');self.assertNotEqual(b,self.a);self.assertEqual(self.lib.segment('real')['asset_id'],self.a)
 def test_no_symlink(self):
  p=self.media/'link.mp4';p.symlink_to(self.file);self.assertRaises(Rejected,self.lib.ingest,p,'x','unknown','x')
 def test_parent_symlink(self):
  p=self.media/'alias';p.symlink_to(self.media,target_is_directory=True);self.assertRaises(Rejected,self.lib.safe_path,p/'original.mp4')
 def test_outside_root(self):
  p=self.root/'secret.mp4';p.write_bytes(b'secret');self.assertRaises(Rejected,self.lib.safe_path,p)
 def test_nonmedia_extension(self):
  p=self.media/'program.sh';p.write_bytes(b'x');self.assertRaises(Rejected,self.lib.safe_path,p)
 def test_empty_file(self):
  p=self.media/'empty.mp4';p.touch();self.assertRaises(Rejected,self.lib.safe_path,p)
 def test_file_size_limit(self):
  p=self.media/'huge.mp4'
  with p.open('wb') as f:f.truncate(MAX_FILE+1)
  self.assertRaises(Rejected,self.lib.safe_path,p)
 def test_origin_conflict(self):self.assertRaises(Rejected,self.lib.ingest,self.file,'x','assistant_render','x')
 def test_invalid_origin(self):self.assertRaises(Rejected,self.lib.ingest,self.file,'x','inferred_authentic','x')
 def test_mid_read_change(self):
  p=self.media/'mutate.mp4';p.write_bytes(b'stable')
  def f(p):p.write_bytes(b'changed');return self.fake(p)
  self.lib.probe_fn=f;self.assertRaises(IntegrityError,self.lib.ingest,p,'x','unknown','x')
 def test_unreadable_no_record(self):
  p=self.media/'bad.mp4';p.write_bytes(b'bad')
  self.lib.probe_fn=lambda p: (_ for _ in ()).throw(Rejected('probe failed'))
  self.assertRaises(Rejected,self.lib.ingest,p,'x','unknown','x');self.assertEqual(self.lib.catalogue()['asset_count'],1)
 def test_timecodes_finite(self):
  for v in [float('nan'),float('inf'),True,-1,20]:
   with self.subTest(v=v):self.assertRaises(Rejected,self.update,start=v)
 def test_end_out_of_range(self):self.assertRaises(Rejected,self.update,end=25)
 def test_zero_length(self):self.assertRaises(Rejected,self.update,start=5,end=5)
 def test_concept_cannot_anchor(self):self.assertRaises(Rejected,self.update,kind='concept')
 def test_unreviewed_cannot_anchor(self):self.assertRaises(Rejected,self.update,review='unreviewed')
 def test_generated_cannot_anchor(self):self.assertRaises(Rejected,self.update,kind='ai_generation')
 def test_documented_rights_require_evidence(self):self.assertRaises(Rejected,self.update,rights='documented')
 def test_annotation_conflict(self):self.assertRaises(Rejected,self.update,expected_revision=0)
 def test_edit_invalidates_prepared_plan(self):
  p=self.lib.prepare(self.req());self.update(label='new');self.assertRaises(Rejected,self.lib.validate_plan,p)
 def test_missing_invalidates_plan(self):
  p=self.lib.prepare(self.req());self.file.unlink();self.assertRaises(IntegrityError,self.lib.validate_plan,p)
 def test_changed_invalidates_plan(self):
  p=self.lib.prepare(self.req());self.file.write_bytes(b'altered');self.assertRaises(IntegrityError,self.lib.validate_plan,p)
 def test_idempotent_preparation(self):self.assertEqual(self.lib.prepare(self.req()),self.lib.prepare(self.req()))
 def test_request_reuse_conflict(self):
  self.lib.prepare(self.req());r=self.req();r['expected_revisions']['real']=2;self.assertRaises(Rejected,self.lib.prepare,r)
 def test_stale_revision_blocked(self):
  r=self.req();r['expected_revisions']['real']=2;self.assertRaises(Rejected,self.lib.prepare,r)
 def test_revision_bool_blocked(self):
  r=self.req();r['expected_revisions']['real']=True;self.assertRaises(Rejected,self.lib.prepare,r)
 def test_missing_revision_blocked(self):
  r=self.req();r['expected_revisions']={};self.assertRaises(Rejected,self.lib.prepare,r)
 def test_duplicate_selection_blocked(self):
  r=self.req();r['segment_ids']=['real','real'];self.assertRaises(Rejected,self.lib.prepare,r)
 def test_rejected_clip_blocked(self):
  self.lib.annotate('bad',self.a,'bad',7,8,'ai_generation','rejected',evidence='rejected fixture')
  r=self.req();r['segment_ids'].append('bad');r['expected_revisions']['bad']=1;self.assertRaises(Rejected,self.lib.prepare,r)
 def test_mixed_clip_blocked(self):
  self.lib.annotate('mixed',self.a,'mixed',0,2,'mixed',evidence='mixed fixture')
  r=self.req();r['segment_ids'].append('mixed');r['expected_revisions']['mixed']=1;self.assertRaises(Rejected,self.lib.prepare,r)
 def test_concept_clip_blocked(self):
  self.lib.annotate('concept',self.a,'concept',0,2,'concept',evidence='fixture')
  r=self.req();r['segment_ids'].append('concept');r['expected_revisions']['concept']=1;self.assertRaises(Rejected,self.lib.prepare,r)
 def test_no_publish_even_when_prepared(self):
  p=self.lib.prepare(self.req());self.assertFalse(p['publish_allowed']);self.assertEqual(p['rights_pending'],['real']);self.assertEqual(p['cost_incurred'],0)
 def test_plan_tamper_detected(self):
  p=copy.deepcopy(self.lib.prepare(self.req()));p['sources'][0]['start']=4;self.assertRaises(IntegrityError,self.lib.validate_plan,p)
 def test_no_absolute_path_in_catalogue_or_brief(self):
  s=json.dumps([self.lib.catalogue(),self.lib.prepare(self.req())]);self.assertNotIn(str(self.media),s)
 def test_accent_search(self):self.assertEqual(len(self.lib.catalogue('reference')['segments']),1)
 def test_no_false_semantic_claim(self):self.assertFalse(self.lib.catalogue()['capabilities']['semantic_search'])
 def test_nonmatching_search(self):self.assertEqual(self.lib.catalogue('aerographe')['segments'],[])
 def test_tags_are_literal_text(self):
  self.update(tags=['<script>alert(1)</script>']);self.assertEqual(self.lib.segment('real')['tags'][0],'<script>alert(1)</script>')
 def test_metadata_persists(self):
  self.lib.prepare(self.req());self.lib.close();self.lib=MediaLibrary(self.root/'state',[self.media],self.fake);self.assertEqual(self.lib.get_plan('request1')['anchor_id'],'real')
 def test_backup_contains_exact_bytes(self):
  p=self.root/'portable.zip';r=self.lib.export_archive(p);self.assertTrue(r['valid'])
  with zipfile.ZipFile(p) as z:self.assertEqual(z.read('media/'+self.a+'.mp4'),self.file.read_bytes())
 def test_backup_no_private_paths(self):
  p=self.root/'portable.zip';self.lib.export_archive(p)
  with zipfile.ZipFile(p) as z:self.assertNotIn(str(self.root),z.read('catalogue.json').decode())
 def test_backup_refuses_missing_media(self):
  self.file.unlink();self.assertRaises(IntegrityError,self.lib.export_archive,self.root/'bad.zip')
 def test_archive_tamper(self):
  p=self.root/'good.zip';self.lib.export_archive(p);q=self.root/'bad.zip'
  with zipfile.ZipFile(p) as src,zipfile.ZipFile(q,'w') as dst:
   for n in src.namelist():dst.writestr(n,b'wrong' if n=='catalogue.json' else src.read(n))
  self.assertRaises(IntegrityError,verify_archive,q)
 def test_archive_path_traversal(self):
  p=self.root/'bad.zip'
  with zipfile.ZipFile(p,'w') as z:z.writestr('../outside',b'x');z.writestr('MANIFESTE.json','{}')
  self.assertRaises(IntegrityError,verify_archive,p)
 def test_no_source_change_after_all_operations(self):self.assertEqual(self.file.read_bytes(),b'original footage for unit tests')

if __name__=='__main__':unittest.main(verbosity=2)
