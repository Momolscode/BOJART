"""M07 scene reconciliation and scoped voice approval. No live provider calls."""
import http.client, json, sqlite3, sys, tempfile, threading, unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, Rejected
from consolidated_workbench import ConsolidatedWorkbench
from jarvis_runtime import JarvisRuntime
from jev_decider import JevDecider
from workspace_state import restore_snapshot


class M07Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(self.root/'work'))
        self.runtime=self.app.jarvis
    def tearDown(self):self.app.server_close();self.tmp.cleanup()
    def request(self,**kw):
        data={'request_id':'scene01','client_id':'window01','project_id':'BOJ-PILOTE-001','revision':0,
              'text':'Ouvre la tour de contrôle','operation_id':None,'source':'typed'};data.update(kw);return data
    def mock_jev(self):
        def transport(payload):
            options=payload['questions']['intent']['criteria']
            return {'model':payload['model'],'answers':{'intent':{'type':'choice','choice':'workspace','confidence':1.0,
                    'probabilities':{k:float(k=='workspace') for k in options}}}}
        self.runtime.decider=JevDecider(enabled=True,key='fixture-only',transport=transport)
    def await_proposal(self):
        self.mock_jev();return self.runtime.submit(self.request(text='Le tableau des dossiers, merci'))
    def test_single_utterance_produces_exactly_three_commands(self):
        result=self.runtime.submit(self.request())
        self.assertEqual(result['status'],'QUEUED');self.assertEqual(len(result['displays']),3)
        self.assertEqual({d['target_role'] for d in result['displays']},{'atelier','pilotage','creation'})
        self.assertNotEqual(result['display']['state'],'rendered');self.assertIsNone(result['elapsed_to_display_ms'])
    def test_scene_ids_bounded_for_max_length_request(self):
        result=self.runtime.submit(self.request(request_id='r'*96))
        self.assertTrue(all(len(d['request_id'])<=96 for d in result['displays']))
    def test_replay_does_not_duplicate_scene(self):
        self.runtime.submit(self.request());self.runtime.submit(self.request())
        self.assertEqual(len(self.app.tower.status()['commands']),3)
    def test_scene_requires_all_three_render_receipts(self):
        self.runtime.submit(self.request())
        for i,role in enumerate(['atelier','pilotage','creation']):
            screen=self.app.tower.pair(role);command=self.app.tower.poll(screen['screen_id'])['command']
            self.assertIsNotNone(command)
            self.app.tower.ack(screen['screen_id'],command['request_id'],'rendered','test browser receipt')
            result=self.runtime.get('scene01')
            self.assertEqual(result['display']['rendered_views'],i+1)
            self.assertEqual(result['display']['state']=='rendered',i==2)
        self.assertIsNotNone(result['elapsed_to_display_ms'])
    def test_one_failed_view_prevents_success(self):
        self.runtime.submit(self.request());screen=self.app.tower.pair('atelier');command=self.app.tower.poll(screen['screen_id'])['command']
        self.app.tower.ack(screen['screen_id'],command['request_id'],'failed','test failure')
        self.assertEqual(self.runtime.get('scene01')['display']['state'],'failed')
    def test_cancel_neutralizes_all_pending_views(self):
        self.runtime.submit(self.request());result=self.runtime.cancel('scene01','window01')
        self.assertEqual(result['status'],'CANCELLED_AFTER_DISPATCH')
        self.assertEqual({d['state'] for d in result['displays']},{'cancelled'})
    def test_model_from_unknown_project_distributes_nothing(self):
        result=self.runtime.submit(self.request(operation_id='a'*32))
        self.assertEqual(result['status'],'FAILED');self.assertEqual(len(self.app.tower.status()['commands']),0)
    def test_scene_survives_restart_without_duplicate(self):
        self.runtime.submit(self.request());self.runtime.close();self.app.jarvis=JarvisRuntime(self.app);self.runtime=self.app.jarvis
        self.runtime.submit(self.request());self.assertEqual(len(self.app.tower.status()['commands']),3)
    def test_m06_schema_is_upgraded_without_replaying_old_command(self):
        original=self.request(text='Montre les dossiers au centre');self.runtime.submit(original)
        self.app.server_close()
        with closing(sqlite3.connect(self.root/'work/missions.sqlite3')) as db, db:
            db.execute('ALTER TABLE jarvis_turns DROP COLUMN plan')
            db.execute('ALTER TABLE jarvis_turns DROP COLUMN approval_source')
        self.app=ConsolidatedWorkbench(('127.0.0.1',0),Store(self.root/'work'));self.runtime=self.app.jarvis
        self.assertEqual(self.runtime.submit(original)['display']['state'],'queued')
        self.assertEqual(len(self.app.tower.status()['commands']),1)
    def test_partial_delivery_is_reconciled_under_same_identifiers(self):
        dispatch=self.app.tower.dispatch;calls=[0]
        def fail_second(rid):
            calls[0]+=1
            if calls[0]==2:raise OSError('lost local response')
            return dispatch(rid)
        with patch.object(self.app.tower,'dispatch',side_effect=fail_second):
            first=self.runtime.submit(self.request())
        self.assertEqual(first['status'],'INTERRUPTED');self.assertEqual(len(first['displays']),1)
        result=self.runtime.submit(self.request())
        self.assertEqual(result['status'],'QUEUED');self.assertEqual(len(result['displays']),3)
    def test_frozen_context_changes_are_rejected(self):
        snapshot=self.app.display.context_hash();path=self.app.store.context_path;path.write_bytes(path.read_bytes()+b'\n')
        result=self.runtime.submit(self.request(source='voice',context_sha256=snapshot))
        self.assertEqual(result['status'],'STALE');self.assertEqual(result['displays'],[])
    def test_invalid_context_hash_is_rejected(self):
        with self.assertRaises(Rejected):self.runtime.submit(self.request(context_sha256='invalid'))
    def test_scene_restore_preserves_plan_and_cancels_distribution(self):
        self.runtime.submit(self.request());backup=self.app.workspace.backup();destination=self.root/'restore'
        restore_snapshot(self.app.store.root/backup['url'].lstrip('/'),destination)
        restored=ConsolidatedWorkbench(('127.0.0.1',0),Store(destination))
        try:
            result=restored.jarvis.get('scene01');self.assertEqual(len(result['displays']),3)
            self.assertEqual({d['state'] for d in result['displays']},{'cancelled_restore'})
            self.assertNotEqual(result['display']['state'],'rendered')
        finally:restored.server_close()
    def test_spoken_approval_only_confirms_current_visual_proposal(self):
        self.assertEqual(self.await_proposal()['status'],'AWAITING_CONFIRMATION')
        result=self.runtime.confirm_speech('scene01','window01','BOJ-PILOTE-001','Jarvis, confirme cet affichage !')
        self.assertEqual(result['status'],'QUEUED');self.assertEqual(result['approval_source'],'voice_explicit')
    def test_spoken_yes_is_not_sufficient(self):
        self.await_proposal()
        with self.assertRaises(Rejected):self.runtime.confirm_speech('scene01','window01','BOJ-PILOTE-001','Oui')
        self.assertEqual(self.runtime.get('scene01')['status'],'AWAITING_CONFIRMATION')
    def test_spoken_approval_wrong_window(self):
        self.await_proposal()
        with self.assertRaises(Rejected):self.runtime.confirm_speech('scene01','window02','BOJ-PILOTE-001','Confirme cet affichage')
    def test_spoken_approval_wrong_project(self):
        self.app.store.create_project('BOJ-OTHER','Other');self.await_proposal()
        with self.assertRaises(Rejected):self.runtime.confirm_speech('scene01','window01','BOJ-OTHER','Confirme cet affichage')
    def test_spoken_approval_rechecks_revision(self):
        self.await_proposal()
        with self.app.store.connect() as db:db.execute('INSERT INTO projects VALUES (?,?)',('BOJ-PILOTE-001',1))
        self.assertEqual(self.runtime.confirm_speech('scene01','window01','BOJ-PILOTE-001','Confirme cet affichage')['status'],'STALE')
    def test_spoken_approval_expiry(self):
        self.await_proposal()
        with self.app.store.connect() as db:db.execute('UPDATE jarvis_turns SET created=created-121')
        self.assertEqual(self.runtime.confirm_speech('scene01','window01','BOJ-PILOTE-001','Confirme cet affichage')['status'],'STALE')
    def test_spoken_cancel(self):
        self.await_proposal()
        self.assertEqual(self.runtime.confirm_speech('scene01','window01','BOJ-PILOTE-001','Annule cette proposition')['status'],'CANCELLED')
    def test_spoken_approval_cannot_revive_cancelled_turn(self):
        self.await_proposal();self.runtime.cancel('scene01','window01')
        with self.assertRaises(Rejected):self.runtime.confirm_speech('scene01','window01','BOJ-PILOTE-001','Confirme cet affichage')
    def test_spoken_approval_replay_is_idempotent(self):
        self.await_proposal()
        for _ in range(2):self.runtime.confirm_speech('scene01','window01','BOJ-PILOTE-001','Confirme cet affichage')
        self.assertEqual(len(self.app.tower.status()['commands']),1)


if __name__=='__main__':unittest.main()
