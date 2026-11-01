"""Restoration revokes pending approvals, while retaining completed receipts.

The catalogue is empty and the CAD builder writes explicit test fixtures only.
These tests do not validate geometry, models, media, or physical equipment.
"""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import Mock
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'jarvis/apps/jarvis/app'))
from core import Store, Rejected
from consolidated_workbench import ConsolidatedWorkbench
from workspace_state import restore_snapshot


def fixture_builder(spec, path):
    path.mkdir()
    for name in ('socle.step', 'socle.stl', 'socle_metres.glb', 'modele.json'):
        (path / name).write_text('RESTORE TEST FIXTURE: ' + name, encoding='utf8')
    return {'fixture_only': True}


class WorkspaceRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.open_app(self.root / 'original')

    def open_app(self, path):
        app = ConsolidatedWorkbench(('127.0.0.1', 0), Store(path))
        self.addCleanup(app.server_close)
        return app

    def restore(self, app=None):
        app = app or self.app
        backup = app.workspace.backup(uuid.uuid4().hex)
        destination = self.root / ('restored-' + uuid.uuid4().hex)
        receipt = restore_snapshot(app.store.root / backup['url'].lstrip('/'), destination)
        return self.open_app(destination), receipt

    def visual(self, rid='pending-display'):
        return {'request_id': rid, 'turn_id': 'turn-' + rid,
                'project_id': 'BOJ-PILOTE-001', 'revision': 0,
                'command': 'Montre les sources au centre', 'operation_id': None}

    def test_undispatched_visual_proposal_requires_new_request_after_restore(self):
        request = self.visual()
        original = self.app.display.prepare(request)
        restored, receipt = self.restore()
        self.assertFalse(restored.display.prepare(request)['current'])
        self.assertFalse(restored.display.is_current(original))
        with self.assertRaises(Rejected):
            restored.tower.dispatch(request['request_id'])
        self.assertEqual(restored.tower.status()['commands'], [])
        self.assertEqual(receipt['invalidated_display_proposals'], 1)
        # Restoration must not mutate the source workspace or block new requests.
        self.assertEqual(self.app.tower.dispatch(request['request_id'])['state'], 'queued')
        fresh = self.visual('fresh-display')
        self.assertTrue(restored.display.prepare(fresh)['current'])
        self.assertEqual(restored.tower.dispatch(fresh['request_id'])['state'], 'queued')

    def test_pending_cad_confirmation_is_revoked_without_running_builder(self):
        proposal = self.app.proposals.prepare('Crée un socle de 180 mm', 0)
        request = {'proposal_id': proposal['proposal_id'], 'approved': True}
        restored, receipt = self.restore()
        builder = Mock(side_effect=AssertionError('An old approval reached the CAD builder'))
        with self.assertRaises(Rejected):
            restored.proposals.confirm(request, builder=builder)
        builder.assert_not_called()
        self.assertEqual(restored.store.list_jobs(), [])
        self.assertEqual(receipt['invalidated_cad_proposals'], 1)
        with restored.store.connect() as db:
            row = db.execute('SELECT state,body FROM dialogue_proposals WHERE id=?',
                             (proposal['proposal_id'],)).fetchone()
        self.assertEqual(row['state'], 'RESTORED')
        self.assertEqual(json.loads(row['body']), proposal)
        self.assertEqual(self.app.proposals.confirm(request, builder=fixture_builder)['state'], 'READY')
        fresh = restored.proposals.prepare('Crée un socle de 180 mm', 0)
        self.assertEqual(restored.proposals.confirm(
            {'proposal_id': fresh['proposal_id'], 'approved': True}, builder=fixture_builder)['state'], 'READY')

    def test_completed_cad_receipt_replays_without_recalculation(self):
        proposal = self.app.proposals.prepare('Crée un socle de 180 mm', 0)
        request = {'proposal_id': proposal['proposal_id'], 'approved': True}
        original = self.app.proposals.confirm(request, builder=fixture_builder)
        restored, receipt = self.restore()
        builder = Mock(side_effect=AssertionError('Completed CAD was recalculated'))
        self.assertEqual(restored.proposals.confirm(request, builder=builder), original)
        builder.assert_not_called()
        self.assertEqual(receipt['invalidated_cad_proposals'], 0)
        self.assertTrue(restored.workspace.check()['ok'])

    def test_dispatched_receipts_keep_their_payload_and_terminal_state(self):
        screen = self.app.tower.pair('pilotage')['screen_id']
        rendered = self.visual('already-rendered')
        pending = self.visual('already-queued')
        for request in (rendered, pending):
            self.app.display.prepare(request)
            self.app.tower.dispatch(request['request_id'])
        delivered = self.app.tower.poll(screen)['command']['request_id']
        self.app.tower.ack(screen, delivered, 'rendered', 'Test browser receipt')
        with self.app.display.db() as db:
            original = db.execute('SELECT request_id,payload FROM proposals ORDER BY request_id').fetchall()
        restored, _ = self.restore()
        with restored.display.db() as db:
            self.assertEqual(db.execute('SELECT request_id,payload FROM proposals ORDER BY request_id').fetchall(), original)
        for request in (rendered, pending):
            rid = request['request_id']
            replay = restored.tower.dispatch(rid)
            self.assertTrue(replay['replayed'])
            self.assertEqual(replay['state'], 'rendered' if rid == delivered else 'cancelled_restore')
        fresh_screen = restored.tower.pair('pilotage')['screen_id']
        self.assertIsNone(restored.tower.poll(fresh_screen)['command'])

    def test_legacy_snapshot_without_invalidation_table_is_supported(self):
        request = self.visual()
        self.app.display.prepare(request)
        with self.app.display.db() as db:
            db.execute('DROP TABLE IF EXISTS proposal_invalidations')
        restored, _ = self.restore()
        self.assertFalse(restored.display.prepare(request)['current'])
        with self.assertRaises(Rejected):
            restored.tower.dispatch(request['request_id'])

    def test_revocation_survives_restart_and_second_snapshot(self):
        request = self.visual()
        self.app.display.prepare(request)
        cad = self.app.proposals.prepare('Crée un socle de 180 mm', 0)
        restored, _ = self.restore()
        root = restored.store.root
        restored.server_close()
        reopened = self.open_app(root)
        self.assertFalse(reopened.display.prepare(request)['current'])
        fresh = self.visual('prepared-after-first-restore')
        reopened.display.prepare(fresh)
        twice, _ = self.restore(reopened)
        for request in (request, fresh):
            self.assertFalse(twice.display.prepare(request)['current'])
            with self.assertRaises(Rejected):
                twice.tower.dispatch(request['request_id'])
        builder = Mock(side_effect=AssertionError('Revoked CAD was recalculated'))
        with self.assertRaises(Rejected):
            twice.proposals.confirm({'proposal_id': cad['proposal_id'], 'approved': True}, builder=builder)
        builder.assert_not_called()


if __name__ == '__main__':
    unittest.main()
