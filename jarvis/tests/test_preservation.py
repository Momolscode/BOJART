import unittest,tempfile,json,hashlib,zipfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from preservation import verify_vault,restore_vault,safe_path
from legacy_publish_github import validate_repo,require_private,validate_delivery,publish
class Tests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
 def tearDown(self):self.t.cleanup()
 def vault(self,path='a/original.txt',content=b'original bytes',sha=None,extra=False):
  h=sha or hashlib.sha256(content).hexdigest();p=self.root/'vault.zip'
  d={'schema':1,'files':[{'original_path':path,'sha256':h,'bytes':len(content),'object':'objects/'+h}]}
  with zipfile.ZipFile(p,'w') as z:
   z.writestr('inventory.json',json.dumps(d));z.writestr('objects/'+h,content)
   if extra:z.writestr('surprise.txt','bad')
  return p
 def test_exact_restore(self):
  p=self.vault();d=self.root/'restored';r=restore_vault(p,d);self.assertTrue(r['verified']);self.assertEqual((d/'a/original.txt').read_bytes(),b'original bytes')
 def test_existing_refused(self):
  d=self.root/'exists';d.mkdir()
  with self.assertRaises(FileExistsError):restore_vault(self.vault(),d)
 def test_corruption_refused(self):
  with self.assertRaises(ValueError):verify_vault(self.vault(sha='a'*64))
 def test_traversal_refused(self):
  with self.assertRaises(ValueError):verify_vault(self.vault(path='../outside'))
 def test_absolute_refused(self):
  with self.assertRaises(ValueError):safe_path('/etc/passwd')
 def test_drive_refused(self):
  with self.assertRaises(ValueError):safe_path('C:/danger')
 def test_windows_refused(self):
  with self.assertRaises(ValueError):safe_path('x\\..\\y')
 def test_unlisted_entry_refused(self):
  with self.assertRaises(ValueError):verify_vault(self.vault(extra=True))
 def test_no_partial_restore_on_error(self):
  dest=self.root/'restored'
  with self.assertRaises(ValueError):restore_vault(self.vault(sha='a'*64),dest)
  self.assertFalse(dest.exists())
 def test_public_refused(self):
  with self.assertRaises(ValueError):require_private({'private':False,'full_name':'Momolscode/bojart'},'Momolscode/bojart')
 def test_other_repo_refused(self):
  with self.assertRaises(ValueError):require_private({'private':True,'full_name':'Momolscode/unum'},'Momolscode/bojart')
 def test_owner_ambiguous_not_defaulted(self):
  with self.assertRaises(ValueError):validate_repo('bojart')
 def test_other_owner_refused(self):
  with self.assertRaises(ValueError):validate_repo('other/bojart')
 def test_repo_injection_refused(self):
  with self.assertRaises(ValueError):validate_repo('Momolscode/bojart;rm')
 def test_repo_valid(self):self.assertEqual(validate_repo('Momolscode/bojart-jarvis'),'Momolscode/bojart-jarvis')
 def test_no_execute_plan(self):
  p=self.root/'code.bundle';p.write_bytes(b'test')
  d={'schema':'bojart.delivery.v1','branch':'recovery/test','tag':'test','commit':'a'*40,'bundle':p.name,'files':[{'name':p.name,'bytes':4,'sha256':hashlib.sha256(b'test').hexdigest()}]}
  (self.root/'DELIVERY_MANIFEST.json').write_text(json.dumps(d))
  r=publish('Momolscode/bojart-jarvis',self.root);self.assertEqual(r['status'],'plan_only')
  self.assertFalse((self.root/'delivery_result.json').exists())
 def test_unselected_linked_account_refused(self):
  with self.assertRaises(ValueError):validate_repo('eaglemic/bojart-jarvis')
 def test_other_project_same_account_refused(self):
  with self.assertRaises(ValueError):validate_repo('Momolscode/unum-continuite')
 def test_destination_case_insensitive(self):
  self.assertEqual(validate_repo('momolscode/bojart-jarvis'),'momolscode/bojart-jarvis')
 def test_invalid_commit(self):
  (self.root/'DELIVERY_MANIFEST.json').write_text(json.dumps({'schema':'bojart.delivery.v1','files':[{}],'commit':'abc'}))
  with self.assertRaises(ValueError):validate_delivery(self.root)
 def test_invalid_branch(self):
  d={'schema':'bojart.delivery.v1','files':[{}],'commit':'a'*40,'branch':'../escape','tag':'v1'}
  (self.root/'DELIVERY_MANIFEST.json').write_text(json.dumps(d))
  with self.assertRaises(ValueError):validate_delivery(self.root)
 def test_invalid_tag(self):
  d={'schema':'bojart.delivery.v1','files':[{}],'commit':'a'*40,'branch':'recovery/v1','tag':'-bad'}
  (self.root/'DELIVERY_MANIFEST.json').write_text(json.dumps(d))
  with self.assertRaises(ValueError):validate_delivery(self.root)
 def test_unverified_bundle(self):
  p=self.root/'test.txt';p.write_bytes(b'test')
  d={'schema':'bojart.delivery.v1','branch':'recovery/test','tag':'test','commit':'a'*40,'bundle':'../outside.bundle','files':[{'name':p.name,'bytes':4,'sha256':hashlib.sha256(b'test').hexdigest()}]}
  (self.root/'DELIVERY_MANIFEST.json').write_text(json.dumps(d))
  with self.assertRaises(ValueError):validate_delivery(self.root)
 def test_delivery_integrity(self):
  (self.root/'DELIVERY_MANIFEST.json').write_text(json.dumps({'schema':'bojart.delivery.v1','files':[{'name':'x','bytes':0,'sha256':'a'*64}]}))
  with self.assertRaises(ValueError):validate_delivery(self.root)
if __name__=='__main__':unittest.main()
