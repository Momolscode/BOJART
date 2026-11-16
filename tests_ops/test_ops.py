import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from bojart_ops.audit import audit, strict_json
from bojart_ops.ledger import Ledger, units
from tools.quality_gate import validate, MANDATORY


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def write(self,name,data):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(data,encoding='utf-8');return p

    def scan(self):
        return audit(self.root,[p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()],revision='fixture')

    def test_invalid_json_and_python_fail(self):
        self.write('x.json','{"a":1,"a":2}')
        self.write('x.py','def broken(')
        report=self.scan()
        self.assertFalse(report['ok'])
        self.assertEqual({'invalid_json','python_syntax'},{i['code'] for i in report['issues']})

    def test_nonfinite_json_rejected(self):
        for text in ('{"x": NaN}','{"x": Infinity}','{"x":-Infinity}'):
            with self.assertRaises(ValueError):strict_json(text)

    def test_duplicates_preserve_both_paths(self):
        self.write('a.txt','same');self.write('b.txt','same')
        report=self.scan()
        self.assertEqual(report['duplicates'][0]['paths'],['a.txt','b.txt'])
        self.assertTrue((self.root/'a.txt').exists())

    def test_secrets_not_echoed(self):
        token='gh'+'p_'+'A'*40
        self.write('x.txt',token)
        report=self.scan()
        self.assertEqual(report['issues'][0]['code'],'credential_pattern')
        self.assertNotIn(token,json.dumps(report))

    def test_symlink_outside_is_not_read(self):
        try:
            (self.root/'x.txt').symlink_to(self.root.parent/'outside.txt')
        except OSError as exc:
            if getattr(exc,'winerror',None)==1314:
                self.skipTest('Windows: création de symlink non autorisée (WinError 1314).')
            raise
        report=audit(self.root,['x.txt'],revision='fixture')
        self.assertFalse(report['ok'])
        self.assertEqual(report['issues'][0]['code'],'unsafe_path')

    def test_missing_assets_are_warnings_not_fake_success(self):
        self.write('ASSETS.json',json.dumps({'assets':[{'path':'missing.mp4','bytes':10,'sha256':'a'*64}]}))
        report=self.scan()
        self.assertTrue(report['ok'])
        self.assertEqual(report['issues'][0]['code'],'asset_not_materialized')

    def test_modified_asset_fails(self):
        self.write('a.mp4','changed')
        self.write('ASSETS.json',json.dumps({'assets':[{'path':'a.mp4','bytes':7,'sha256':'a'*64}]}))
        self.assertFalse(self.scan()['ok'])

    def test_asset_path_escape_rejected(self):
        self.write('ASSETS.json',json.dumps({'assets':[{'path':'../x','bytes':1,'sha256':'a'*64}]}))
        self.assertEqual(self.scan()['issues'][0]['code'],'invalid_asset_record')

    def test_timeline_gap_fails(self):
        edl={'fps':24,'frames':24,'duration_seconds':1,'shots':[{'shot':'S1','in':0,'frames':24,'timeline_in_frame':1,'timeline_out_frame_exclusive':25}]}
        self.write('edit.json',json.dumps(edl))
        self.assertFalse(self.scan()['ok'])
        edl['shots'][0].update(timeline_in_frame=0,timeline_out_frame_exclusive=24)
        self.write('edit.json',json.dumps(edl))
        self.assertTrue(self.scan()['ok'])

    def test_every_tracked_extension_hashed(self):
        self.write('binary.unknown','bytes')
        self.assertEqual(self.scan()['files'][0]['sha256'],hashlib.sha256(b'bytes').hexdigest())

    def test_legacy_seconds_duration_is_checked(self):
        edl={'fps':24,'frames':24,'duration_s':1,'shots':[{'shot':'S1','in':0,'frames':24,'timeline_in_frame':0,'timeline_out_frame_exclusive':24}]}
        self.write('edit.json',json.dumps(edl));self.assertTrue(self.scan()['ok'])
        edl['duration_seconds']=2
        self.write('edit.json',json.dumps(edl));self.assertFalse(self.scan()['ok'])

    def test_brand_film_crossfades_are_explicit(self):
        film={'format':'bojart.brand-film.v1','fps':30,'frames':114,'duration_seconds':3.8,
              'shots':[{'id':'a','start':1,'duration':2,'output':[0,2]},
                       {'id':'b','start':5,'duration':2,'output':[1.8,3.8]}],
              'transitions':[{'type':'crossfade','output_seconds':[1.8,2]}]}
        self.write('site.json',json.dumps(film));self.assertTrue(self.scan()['ok'])
        for mode in ('undeclared_overlap','wrong_overlap','gap'):
            bad=copy.deepcopy(film)
            if mode=='undeclared_overlap':bad['transitions']=[]
            elif mode=='wrong_overlap':bad['transitions'][0]['output_seconds']=[1.7,2]
            else:bad['shots'][1].update(output=[2.1,4.1])
            self.write('site.json',json.dumps(bad))
            with self.subTest(mode=mode):self.assertFalse(self.scan()['ok'])

    def test_lfs_media_pointer_reported(self):
        self.write('clip.mp4','version https://git-lfs.github.com/spec/v1\noid sha256:placeholder\n')
        self.assertEqual(self.scan()['issues'][0]['code'],'lfs_pointer')


class QualityTests(unittest.TestCase):
    def review(self):
        return {'shot_id':'S01','checks':{key:True for key in MANDATORY},'status':'approved','reviewer':'Named reviewer'}

    def test_null_reviewer_rejected(self):
        for invalid in (None,False,123,[],{},' ',''):
            r=self.review();r['reviewer']=invalid
            self.assertFalse(validate(r)[0])

    def test_missing_gate_rejected(self):
        r=self.review();r['checks'].pop(next(iter(MANDATORY)))
        self.assertFalse(validate(r)[0])

    def test_truthy_nonboolean_rejected(self):
        r=self.review();r['checks'][next(iter(MANDATORY))]=1
        self.assertFalse(validate(r)[0])

    def test_unknown_gate_and_invalid_shot_rejected(self):
        r=self.review();r['checks']['invented']=True
        self.assertFalse(validate(r)[0])
        r=self.review();r['shot_id']=3
        self.assertFalse(validate(r)[0])

    def test_complete_declared_review_accepted(self):
        self.assertTrue(validate(self.review())[0])


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.db=self.root/'ledger.db'
        self.ledger=Ledger(self.db);self.addCleanup(self.ledger.close)
        self.ledger.set_budget('test',30)
        self.request={'project':'bojart.creative','shot_id':'S01','model':'fixture-only','prompt':'a controlled action','variation':'v1','parameters':{'duration':4},'inputs':[]}

    def plan(self,id='run1',cost=28):
        return self.ledger.plan(id,self.request,'test',cost)

    def test_idempotent_plan_and_different_id_duplicate_rejected(self):
        self.plan();self.plan()
        self.assertEqual(len(self.ledger.export()['runs']),1)
        with self.assertRaises(ValueError):self.plan('run2')

    def test_claim_only_once_and_restart(self):
        self.plan();self.ledger.begin('run1')
        with Ledger(self.db) as second:
            self.assertEqual(second.get('run1')['state'],'submitting')
            with self.assertRaises(ValueError):second.begin('run1')

    def test_unknown_never_auto_resubmits(self):
        self.plan();self.ledger.begin('run1');self.ledger.unknown('run1')
        with self.assertRaises(ValueError):self.ledger.begin('run1')
        self.ledger.receipt('run1','provider-1','completed')
        self.assertEqual(self.ledger.get('run1')['state'],'completed')

    def test_ambiguous_provider_status_preserved(self):
        self.plan();self.ledger.begin('run1')
        self.ledger.receipt('run1','provider-1','future_status')
        self.assertEqual(self.ledger.get('run1')['state'],'unknown')
        self.assertEqual(self.ledger.get('run1')['raw_status'],'future_status')

    def test_blocked_status_is_terminal(self):
        self.plan();self.ledger.begin('run1');self.ledger.receipt('run1','p1','ip_detected')
        self.assertEqual(self.ledger.get('run1')['state'],'blocked')
        with self.assertRaises(ValueError):self.ledger.receipt('run1','p1','running')

    def test_duplicate_receipt_does_not_duplicate_event(self):
        self.plan();self.ledger.begin('run1');self.ledger.receipt('run1','p1','completed')
        n=len(self.ledger.export()['events']);self.ledger.receipt('run1','p1','completed')
        self.assertEqual(n,len(self.ledger.export()['events']))

    def test_no_receipt_before_claim(self):
        self.plan()
        with self.assertRaises(ValueError):self.ledger.receipt('run1','p1','completed')

    def test_receipt_identity_conflict(self):
        self.plan();self.ledger.begin('run1');self.ledger.receipt('run1','p1','running')
        with self.assertRaises(ValueError):self.ledger.receipt('run1','p2','completed')

    def test_out_of_order_status_does_not_downgrade(self):
        self.plan();self.ledger.begin('run1');self.ledger.receipt('run1','p1','running')
        with self.assertRaises(ValueError):self.ledger.receipt('run1','p1','queued')
        self.assertEqual(self.ledger.get('run1')['state'],'running')

    def test_failed_job_does_not_infer_refund(self):
        self.plan();self.ledger.begin('run1');self.ledger.receipt('run1','p1','failed')
        self.request['variation']='v2'
        with self.assertRaises(ValueError):self.plan('run2',3)

    def test_credit_validation(self):
        for value in (-1,'NaN','Infinity',0.0001,True):
            with self.assertRaises(ValueError):units(value)

    def test_parallel_claim_has_single_winner(self):
        self.plan()
        def claim(_):
            with Ledger(self.db) as ledger:
                try:ledger.begin('run1');return True
                except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sum(executor.map(claim,range(2))),1)

    def test_budget_transaction_prevents_overspend(self):
        def attempt(i):
            payload=copy.deepcopy(self.request);payload['variation']=str(i)
            with Ledger(self.db) as ledger:
                try:ledger.plan('run'+str(i),payload,'test',20);return True
                except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sum(executor.map(attempt,range(2))),1)

    def test_download_and_artistic_approval_are_separate(self):
        self.plan();self.ledger.begin('run1');self.ledger.receipt('run1','p1','completed')
        self.assertFalse(self.ledger.get('run1')['media_verified'])
        f=self.root/'media.mp4';f.write_bytes(b'fixture bytes, not a decoded film')
        sha=hashlib.sha256(f.read_bytes()).hexdigest()
        self.ledger.attach('run1',f,sha)
        self.assertTrue(self.ledger.get('run1')['media_verified'])
        self.assertEqual(self.ledger.get('run1')['artistic_approval'],'not_recorded_by_this_ledger')

    def test_bad_hash_rejected(self):
        self.plan();self.ledger.begin('run1');self.ledger.receipt('run1','p1','completed')
        f=self.root/'media';f.write_bytes(b'bytes')
        with self.assertRaises(ValueError):self.ledger.attach('run1',f,'0'*64)

    def test_backup_restores_receipt(self):
        self.plan();self.ledger.begin('run1');self.ledger.receipt('run1','p1','completed')
        snapshot=self.root/'backup.db';self.ledger.backup(snapshot)
        with Ledger(snapshot) as restored:
            self.assertEqual(restored.get('run1')['provider_job_id'],'p1')
            self.assertEqual(len(restored.export()['events']),3)
        with self.assertRaises(FileExistsError):self.ledger.backup(snapshot)

    def test_input_bytes_required(self):
        self.request['inputs']=[{'asset_id':'photo','role':'image_references'}]
        with self.assertRaises(ValueError):self.plan()

    def test_existing_budget_cannot_be_reduced_below_reservation(self):
        self.plan()
        with self.assertRaises(ValueError):self.ledger.set_budget('test',20)


if __name__=='__main__':unittest.main()
