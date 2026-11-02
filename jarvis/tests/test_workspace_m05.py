"""Portable workspace, project isolation and interrupted-work regression tests.

Fast CAD fixtures below deliberately are NOT geometry or fabrication evidence.
The separate M05 smoke test exercises the real CAD kernel and a browser.
"""
import hashlib
import concurrent.futures
import http.client
import json
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, Rejected, IntegrityError, canonical, file_digest
from consolidated_workbench import ConsolidatedWorkbench
from workspace_state import DATABASES, restore_snapshot, verify_snapshot, checked_database


def fixture_builder(spec, path):
    path.mkdir()
    for name in ('socle.step','socle.stl','socle_metres.glb','modele.json'):
        (path/name).write_bytes(('TEST FIXTURE ONLY '+name+' '+str(spec.diameter_mm)).encode())
    return {'fixture_only':True}


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(self.root/'original'))
        self.other=[]
    def tearDown(self):
        self.app.server_close()
        for app in self.other:app.server_close()
        self.temp.cleanup()
    def create(self, project='BOJ-ALPHA', name='Sculpture Alpha'):
        return self.app.store.create_project(project,name)
    def model(self, project='BOJ-PILOTE-001'):
        p=self.app.proposals.prepare('Crée un socle de 180 mm',self.app.store.project_revision(project),project_id=project)
        r=self.app.proposals.confirm({'proposal_id':p['proposal_id'],'approved':True},builder=fixture_builder)
        return p,r
    def display(self, rid='display-m05', project='BOJ-PILOTE-001', command='Montre les sources au centre', operation=None):
        return self.app.display.prepare({'request_id':rid,'turn_id':'turn-m05','project_id':project,'revision':self.app.store.project_revision(project),'command':command,'operation_id':operation})
    def backup(self):
        b=self.app.workspace.backup(uuid.uuid4().hex)
        return self.app.store.root/b['url'].lstrip('/')
    def restored(self, archive):
        dest=self.root/('restored-'+uuid.uuid4().hex)
        receipt=restore_snapshot(archive,dest)
        app=ConsolidatedWorkbench(('127.0.0.1',0),Store(dest));self.other.append(app)
        return app,receipt
    def alter_zip(self, original, edit, rehash=True):
        with zipfile.ZipFile(original) as z:files={n:z.read(n) for n in z.namelist()}
        edit(files)
        if rehash:files['SHA256.json']=canonical({n:hashlib.sha256(b).hexdigest() for n,b in files.items() if n!='SHA256.json'}).encode()
        path=self.root/(uuid.uuid4().hex+'.zip')
        with zipfile.ZipFile(path,'w') as z:
            for n,b in files.items():z.writestr(n,b)
        return path
    def interrupted(self, complete=True):
        if complete:
            _,r=self.model();op=r['operation_id']
            with self.app.store.connect() as db:
                db.execute("UPDATE operations SET state='RUNNING',result_json=NULL WHERE id=?",(op,))
                db.execute('UPDATE projects SET revision=0')
        else:
            op=uuid.uuid4().hex
            def crash(spec,path):
                path.mkdir();(path/'partial.step').write_text('unfinished')
                raise KeyboardInterrupt('simulated process interruption')
            p=self.app.proposals.prepare('Crée un socle de 180 mm',0)
            op=p['operation_id']
            with self.assertRaises(KeyboardInterrupt):self.app.proposals.confirm({'proposal_id':p['proposal_id'],'approved':True},builder=crash)
        self.app.server_close()
        self.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(self.root/'original'))
        return op
    def test_context_is_owned_by_each_workspace(self):
        source=ROOT/'apps/jarvis/context/CONTEXTE_REFERENCE.json';before=file_digest(source)
        self.app.store.context_path.write_text(self.app.store.context_path.read_text()+'\n')
        self.assertEqual(file_digest(source),before)
        second=Store(self.root/'second')
        self.assertEqual(file_digest(second.context_path),before)
        self.assertNotEqual(file_digest(self.app.store.context_path),before)
    def test_projects_have_independent_models_and_revisions(self):
        self.create();self.create('BOJ-BETA','Sculpture Beta')
        self.model('BOJ-ALPHA');self.model('BOJ-ALPHA');self.model('BOJ-BETA')
        self.assertEqual(self.app.store.project_revision('BOJ-ALPHA'),2)
        self.assertEqual(self.app.store.project_revision('BOJ-BETA'),1)
        self.assertEqual(self.app.store.project_revision(),0)
        self.assertEqual(len(self.app.store.list_jobs('BOJ-ALPHA')),2)
        self.assertEqual({j['project'] for j in self.app.store.list_jobs('BOJ-BETA')},{'BOJ-BETA'})
    def test_project_creation_replay_and_conflict(self):
        self.assertFalse(self.create()['replayed']);self.assertTrue(self.create()['replayed'])
        with self.assertRaises(Rejected):self.create(name='An entirely different project')
        with self.assertRaises(Rejected):self.create('../outside','bad')
        with self.assertRaises(Rejected):self.create('BOJ-EMPTY','  ')
    def test_unknown_project_cannot_prepare_or_pair(self):
        with self.assertRaises(Rejected):self.app.proposals.prepare('Crée un socle de 180 mm',0,project_id='BOJ-UNKNOWN')
        with self.assertRaises(Rejected):self.app.tower.pair('creation',project_id='BOJ-UNKNOWN')
    def test_cross_project_model_cannot_be_dispatched(self):
        self.create();_,r=self.model('BOJ-ALPHA')
        with self.assertRaises(Rejected):self.display(command='Affiche le modèle à droite',operation=r['operation_id'])
    def test_same_role_screens_are_isolated_by_project(self):
        self.create();a=self.app.tower.pair('pilotage',project_id='BOJ-ALPHA');b=self.app.tower.pair('pilotage')
        self.display(project='BOJ-ALPHA');self.app.tower.dispatch('display-m05')
        self.assertIsNone(self.app.tower.poll(b['screen_id'])['command'])
        cmd=self.app.tower.poll(a['screen_id'])['command'];self.assertEqual(cmd['project_id'],'BOJ-ALPHA')
        with self.assertRaises(Rejected):self.app.tower.ack(b['screen_id'],cmd['request_id'],'rendered','wrong project')
        self.app.tower.ack(a['screen_id'],cmd['request_id'],'rendered','tested')
        self.assertEqual(len(self.app.tower.status('BOJ-ALPHA')['commands']),1)
        self.assertEqual(len(self.app.tower.status('BOJ-PILOTE-001')['commands']),0)
    def test_studio_route_can_dispatch_to_creation_screen(self):
        s=self.app.tower.pair('creation');self.display(command='Ouvre le studio');self.app.tower.dispatch('display-m05')
        self.assertEqual(self.app.tower.poll(s['screen_id'])['command']['action'],'show_sources')
    def test_other_project_revision_does_not_expire_proposal(self):
        self.create();p=self.display(project='BOJ-ALPHA');self.model()
        self.assertTrue(self.app.display.is_current(p))
    def test_full_snapshot_reopens_with_all_work_and_relative_media(self):
        self.create();proposal,model=self.model('BOJ-ALPHA');self.display(project='BOJ-ALPHA')
        self.app.tower.dispatch('display-m05')
        plan=self.app.library.prepare({'request_id':'brief-m05','anchor_id':'ensemble','segment_ids':['ensemble','visage'],'expected_revisions':{'ensemble':1,'visage':1}})
        packet=self.app.growth.prepare({'request_id':'growth-m05','platform':'tiktok','account_key':'tiktok_main','topic_id':'sculpture','objective':'portfolio','segment_ids':['ensemble','visage'],'expected_revisions':{'ensemble':1,'visage':1}})
        archive=self.backup()
        with zipfile.ZipFile(archive) as z:
            self.assertTrue(set(DATABASES)<=set(z.namelist()))
            dbpath=self.root/'media-copy.sqlite';dbpath.write_bytes(z.read('studio/media.sqlite'))
            with sqlite3.connect(dbpath) as db:self.assertTrue(all(p.startswith('media/') for p, in db.execute('SELECT path FROM locations')))
        restored,receipt=self.restored(archive)
        self.assertEqual(restored.store.get(model['operation_id']),model)
        self.assertEqual(restored.store.list_projects(),self.app.store.list_projects())
        self.assertEqual(restored.library.get_plan(plan['id']),plan)
        self.assertTrue(restored.library.validate_plan(plan)['valid'])
        self.assertTrue(restored.growth.validate(packet['id'])['sources_intact'])
        self.assertEqual(restored.proposals.confirm({'proposal_id':proposal['proposal_id'],'approved':True},builder=lambda *a:self.fail('Unexpected recalculation')),model)
        self.app.server_close();shutil.rmtree(self.root/'original')
        self.assertTrue(restored.workspace.check()['ok'])
        self.assertEqual(receipt['media_relocated'],3)
        for path, in restored.library.db.execute('SELECT path FROM locations'):
            self.assertTrue(Path(path).is_relative_to(restored.store.root/'media'))
    def test_pending_display_never_resumes_after_restore(self):
        screen=self.app.tower.pair('pilotage');self.display();self.app.tower.dispatch('display-m05');self.app.tower.poll(screen['screen_id'])
        restored,_=self.restored(self.backup())
        with self.assertRaises(Rejected):restored.tower.poll(screen['screen_id'])
        fresh=restored.tower.pair('pilotage')
        self.assertIsNone(restored.tower.poll(fresh['screen_id'])['command'])
        self.assertEqual(restored.tower.status()['commands'][0]['state'],'cancelled_restore')
        self.assertEqual(restored.tower.dispatch('display-m05')['state'],'cancelled_restore')
    def test_snapshot_request_replay_is_byte_identical(self):
        rid=uuid.uuid4().hex;a=self.app.workspace.backup(rid);self.create();b=self.app.workspace.backup(rid)
        self.assertTrue(b['replayed']);self.assertEqual(a['sha256'],b['sha256'])
    def test_existing_destination_is_never_overwritten(self):
        archive=self.backup();dest=self.root/'existing';dest.mkdir();(dest/'keep.txt').write_text('keep')
        with self.assertRaises(Rejected):restore_snapshot(archive,dest)
        self.assertEqual((dest/'keep.txt').read_text(),'keep')
    def test_damaged_zip_rejected_without_destination(self):
        archive=self.alter_zip(self.backup(),lambda files:files.__setitem__('CONTEXTE_REFERENCE.json',b'{}'),rehash=False)
        dest=self.root/'bad-restore'
        with self.assertRaises(IntegrityError):restore_snapshot(archive,dest)
        self.assertFalse(dest.exists())
    def test_path_escape_and_case_collision_rejected(self):
        archive=self.backup()
        for name in ('../escape','media/../../escape','media/CON.mp4','media/fake.','MEDIA/other','artifacts\\evil'):
            with self.subTest(name=name):
                bad=self.alter_zip(archive,lambda files:files.__setitem__(name,b'bad'))
                with self.assertRaises(IntegrityError):verify_snapshot(bad)
        def duplicate(files):
            files['media/Case.mp4']=b'a';files['media/case.mp4']=b'b'
        with self.assertRaises(IntegrityError):verify_snapshot(self.alter_zip(archive,duplicate))
    def test_symlink_zip_entry_rejected(self):
        archive=self.backup();bad=self.root/'symlink.zip'
        with zipfile.ZipFile(archive) as z,zipfile.ZipFile(bad,'w') as out:
            for info in z.infolist():
                # A database is always present, even without private demo media.
                if info.filename=='missions.sqlite3':
                    info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
                out.writestr(info,z.read(info.filename))
        with self.assertRaises(IntegrityError):verify_snapshot(bad)
    def test_missing_database_and_bad_metadata_rejected(self):
        archive=self.backup()
        bad=self.alter_zip(archive,lambda files:files.pop('growth/growth.sqlite'))
        with self.assertRaises(IntegrityError):verify_snapshot(bad)
        def change(files):
            meta=json.loads(files['snapshot.json']);meta.pop('snapshot_id');files['snapshot.json']=canonical(meta).encode()
        with self.assertRaises(IntegrityError):verify_snapshot(self.alter_zip(archive,change))
    def test_corrupt_database_cleans_failed_restore(self):
        archive=self.alter_zip(self.backup(),lambda files:files.__setitem__('missions.sqlite3',b'not sqlite'))
        dest=self.root/'bad-database'
        with self.assertRaises(sqlite3.Error):restore_snapshot(archive,dest)
        self.assertFalse(dest.exists())
    def test_missing_media_makes_check_and_backup_fail(self):
        aid=self.app.library.db.execute('SELECT id FROM assets LIMIT 1').fetchone()[0]
        with self.app.library.db:self.app.library.db.execute('DELETE FROM locations WHERE asset_id=?',(aid,))
        check=self.app.workspace.check();self.assertFalse(check['ok']);self.assertEqual(check['issues'][0]['kind'],'media')
        with self.assertRaises(IntegrityError):self.backup()
        self.assertEqual(list(self.app.store.root.glob('.snapshot-*')),[])
    def test_interrupted_complete_result_recovers_without_rerun(self):
        op=self.interrupted();self.assertEqual(self.app.store.get(op)['state'],'INTERRUPTED')
        with self.assertRaises(Rejected):self.app.proposals.prepare('Crée un socle de 180 mm',0)
        result=self.app.workspace.recover(op,'verify_completed')
        self.assertFalse(result['rerun']);self.assertEqual(result['state'],'READY')
        self.assertEqual(self.app.store.project_revision(),1)
        self.assertEqual(self.app.store.get(op)['state'],'READY')
        with self.app.store.connect() as db:self.assertEqual(db.execute('SELECT state FROM dialogue_proposals WHERE operation_id=?',(op,)).fetchone()[0],'COMPLETED')
    def test_incomplete_result_cannot_be_promoted_and_files_preserved(self):
        op=self.interrupted(complete=False);partial=self.app.store.root/('.work-'+op)/'partial.step'
        with self.assertRaises(IntegrityError):self.app.workspace.recover(op,'verify_completed')
        result=self.app.workspace.recover(op,'keep_failed')
        self.assertEqual(result['state'],'FAILED');self.assertEqual(partial.read_text(),'unfinished')
        with self.app.store.connect() as db:self.assertEqual(db.execute('SELECT state FROM dialogue_proposals WHERE operation_id=?',(op,)).fetchone()[0],'FAILED')
        self.app.proposals.prepare('Crée un socle de 180 mm',0)
        restored,_=self.restored(self.backup())
        self.assertEqual((restored.store.root/'incomplete'/op/'partial.step').read_text(),'unfinished')
    def test_altered_interrupted_result_cannot_be_promoted(self):
        op=self.interrupted();(self.app.store.artifacts/op/'socle.step').write_text('altered')
        with self.assertRaises(IntegrityError):self.app.workspace.recover(op,'verify_completed')
        self.assertEqual(self.app.store.get(op)['state'],'INTERRUPTED')
    def test_backup_rejects_running_and_does_not_leave_archive(self):
        _,r=self.model()
        with self.app.store.connect() as db:db.execute("UPDATE operations SET state='RUNNING' WHERE id=?",(r['operation_id'],))
        with self.assertRaises(Rejected):self.backup()
        self.assertEqual(list((self.app.store.root/'backups').glob('*.zip')),[])
    def test_two_servers_cannot_open_same_workspace(self):
        with self.assertRaises(Rejected):ConsolidatedWorkbench(('127.0.0.1',0),Store(self.app.store.root))
        self.app.server_close();self.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(self.root/'original'))
        self.assertTrue(self.app.workspace.check()['ok'])
    def test_incomplete_restore_marker_blocks_startup(self):
        root=self.root/'incomplete';Store(root);(root/'.restore-in-progress').write_text('interrupted')
        with self.assertRaises(Rejected):ConsolidatedWorkbench(('127.0.0.1',0),Store(root))
    def test_database_check_does_not_create_missing_files(self):
        missing=self.root/'missing.sqlite'
        with self.assertRaises(IntegrityError):checked_database(missing)
        self.assertFalse(missing.exists())
    def test_bind_failure_releases_workspace_lease(self):
        root=self.root/'different'
        with self.assertRaises(OSError):ConsolidatedWorkbench(self.app.server_address,Store(root))
        recovered=ConsolidatedWorkbench(('127.0.0.1',0),Store(root));self.other.append(recovered)
        self.assertTrue(recovered.workspace.check()['ok'])
    def test_shutdown_waits_for_accepted_mutation(self):
        started=threading.Event();closed=threading.Event()
        def close():
            started.set();self.app.server_close();closed.set()
        with self.app.workspace.lock:
            thread=threading.Thread(target=close);thread.start();self.assertTrue(started.wait(1))
            self.assertFalse(closed.wait(0.05))
        thread.join(timeout=2);self.assertTrue(closed.is_set())
        self.assertTrue(self.app.workspace.closing)


class WorkspaceHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(cls.tmp.name))
        cls.thread=threading.Thread(target=cls.app.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.app.shutdown();cls.app.server_close();cls.thread.join();cls.tmp.cleanup()
    def call(self,path,body=None,auth=True,origin=True):
        headers={'Cookie':'boj_session='+self.app.token} if auth else {}
        if body is not None:headers.update({'Content-Type':'application/json','Origin':self.app.origin if origin else 'https://foreign.invalid'})
        c=http.client.HTTPConnection('127.0.0.1',self.app.server_port,timeout=20)
        c.request('GET' if body is None else 'POST',path,json.dumps(body) if body is not None else None,headers)
        r=c.getresponse();b=r.read();status=r.status;c.close();return status,b
    def test_workspace_requires_session(self):
        self.assertEqual(self.call('/workspace',auth=False)[0],401)
        self.assertEqual(self.call('/api/workspace/state',auth=False)[0],401)
    def test_launcher_lands_on_workspace(self):
        conn=http.client.HTTPConnection('127.0.0.1',self.app.server_port)
        conn.request('GET','/?session='+self.app.token)
        response=conn.getresponse();response.read()
        self.assertEqual(response.status,303);self.assertEqual(response.getheader('Location'),'/workspace');conn.close()
    def test_mutations_require_origin_and_session(self):
        for path in ('/api/workspace/backup','/api/workspace/check','/api/workspace/recover','/api/projects/create'):
            with self.subTest(path=path):
                self.assertEqual(self.call(path,{},auth=False)[0],401)
                self.assertEqual(self.call(path,{},origin=False)[0],403)
    def test_create_and_filter_project(self):
        s,b=self.call('/api/projects/create',{'project_id':'BOJ-HTTP','name':'Dossier HTTP'})
        self.assertEqual(s,200);self.assertEqual(json.loads(b)['name'],'Dossier HTTP')
        s,b=self.call('/api/state?project_id=BOJ-HTTP');self.assertEqual(s,200);self.assertEqual(json.loads(b)['project_id'],'BOJ-HTTP')
        self.assertEqual(self.call('/api/state?project_id=BOJ-HTTP&project_id=BOJ-PILOTE-001')[0],409)
        self.assertEqual(self.call('/api/state?project_id=BOJ-NONE')[0],409)
    def test_snapshot_download_and_integrity(self):
        s,b=self.call('/api/backup',{'request_id':uuid.uuid4().hex});self.assertEqual(s,200);info=json.loads(b)
        s,data=self.call(info['url']);self.assertEqual(s,200);self.assertEqual(hashlib.sha256(data).hexdigest(),info['sha256'])
        self.assertEqual(self.call(info['url'],auth=False)[0],401)
        s,b=self.call('/api/workspace/check',{});self.assertEqual(s,200);self.assertTrue(json.loads(b)['ok'])
    def test_unknown_fields_rejected(self):
        self.assertEqual(self.call('/api/workspace/check',{'execute':True})[0],409)
        self.assertEqual(self.call('/api/workspace/backup',{'destination':'../escape'})[0],409)
    def test_snapshot_waits_for_accepted_cad_mutation_and_contains_its_result(self):
        self.app.store.create_project('BOJ-CONCURRENT','Concurrent acceptance test')
        proposal=self.app.proposals.prepare('Crée un socle de 180 mm',0,project_id='BOJ-CONCURRENT')
        entered=threading.Event();release=threading.Event();original=self.app.proposals.confirm
        def slow_builder(spec,path):
            entered.set()
            if not release.wait(8):raise RuntimeError('Test did not release the builder')
            return fixture_builder(spec,path)
        self.app.proposals.confirm=lambda request:original(request,builder=slow_builder)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                build=pool.submit(self.call,'/api/confirm',{'proposal_id':proposal['proposal_id'],'approved':True})
                self.assertTrue(entered.wait(5))
                snapshot=pool.submit(self.call,'/api/workspace/backup',{'request_id':uuid.uuid4().hex})
                self.assertFalse(snapshot.done());release.set()
                code,body=build.result(timeout=10);self.assertEqual(code,200);model=json.loads(body)
                code,body=snapshot.result(timeout=10);self.assertEqual(code,200);backup=json.loads(body)
            with tempfile.TemporaryDirectory() as td:
                target=Path(td)/'new';restore_snapshot(self.app.store.root/backup['url'].lstrip('/'),target)
                self.assertEqual(Store(target).get(model['operation_id']),model)
        finally:
            release.set();self.app.proposals.confirm=original


if __name__=='__main__':unittest.main()
