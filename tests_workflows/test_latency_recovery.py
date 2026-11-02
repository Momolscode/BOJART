"""Actual SQLite/process failures; synthetic displays, no hardware or provider."""
import concurrent.futures
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from simulate_jarvis_workflows import RuntimeFixture
from sqlite_sessions import SQLiteSessions


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'sessions.sqlite'
        self.pool = SQLiteSessions(self.path, rows=True, foreign_keys=True)
        with self.pool.connect() as db:
            db.execute('CREATE TABLE items (id INTEGER PRIMARY KEY)')

    def tearDown(self):
        self.pool.close()
        self.tmp.cleanup()

    def test_commit_visible_to_external_connection_and_full_durability(self):
        with self.pool.connect() as db:
            db.execute('INSERT INTO items VALUES (1)')
            self.assertEqual(db.execute('PRAGMA synchronous').fetchone()[0], 2)
            self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            self.assertEqual(db.execute('PRAGMA busy_timeout').fetchone()[0], 10000)
        with sqlite3.connect(self.path) as other:
            self.assertEqual(other.execute('SELECT id FROM items').fetchall(), [(1,)])
        other.close()

    def test_error_rolls_back_and_next_lease_works(self):
        with self.assertRaises(ValueError):
            with self.pool.connect() as db:
                db.execute('INSERT INTO items VALUES (1)')
                raise ValueError('rollback')
        with self.pool.connect() as db:
            self.assertFalse(db.in_transaction)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM items').fetchone()[0], 0)

    def test_escaped_handle_cursor_iterator_and_bound_method_expire(self):
        with self.pool.connect() as db:
            cursor = db.execute('SELECT 1 UNION ALL SELECT 2')
            execute, fetch = db.execute, cursor.fetchone
            iterator = iter(cursor)
            self.assertIs(cursor.connection, db)
        with self.pool.connect() as other:
            self.assertEqual(other.execute('SELECT 9').fetchone()[0], 9)
            for call in (lambda:db.execute('SELECT 1'), lambda:execute('SELECT 1'),
                         fetch, lambda:next(iterator), lambda:cursor.connection):
                with self.assertRaises(sqlite3.ProgrammingError):call()

    def test_nested_checkout_has_no_uncommitted_visibility(self):
        with self.pool.connect() as outer:
            outer.execute('INSERT INTO items VALUES (1)')
            with self.pool.connect() as inner:
                self.assertEqual(inner.execute('SELECT COUNT(*) FROM items').fetchone()[0], 0)
        self.assertLessEqual(len(self.pool._idle), 2)

    def test_checkout_cannot_be_shared_with_another_thread(self):
        with self.pool.connect() as db:
            with db as nested:self.assertIs(nested, db)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda:db.execute('SELECT 1').fetchone())
                with self.assertRaises(sqlite3.ProgrammingError):future.result()

    def test_concurrent_borrowers_never_share_transaction(self):
        barrier = threading.Barrier(8)
        def work(i):
            with self.pool.connect() as db:
                barrier.wait(timeout=10)
                db.execute('INSERT INTO items VALUES (?)', (i,))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(work, range(8)))
        with self.pool.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM items').fetchone()[0], 8)
        self.assertLessEqual(len(self.pool._idle), 2)

    def test_close_allows_existing_borrower_to_finish_only(self):
        with self.pool.connect() as db:
            db.execute('INSERT INTO items VALUES (7)')
            self.pool.close()
            self.assertEqual(db.execute('SELECT id FROM items').fetchone()[0], 7)
            with self.assertRaises(sqlite3.ProgrammingError):
                with self.pool.connect():pass
        with sqlite3.connect(self.path) as other:
            self.assertEqual(other.execute('SELECT id FROM items').fetchone()[0], 7)
        other.close()
        self.assertEqual(self.pool._idle, [])

    def test_runtime_close_detaches_pools_and_releases_windows_files(self):
        with RuntimeFixture() as fixture:
            with fixture.server.store.connect() as db:db.execute('SELECT 1')
            fixture.runtime.close()
            for owner in (fixture.server.store, fixture.server.display, fixture.server.tower):
                self.assertIsNone(getattr(owner, '_command_sessions', None))
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
            fixture.restart()
            self.assertEqual(fixture.runtime.submit(fixture.request())['status'], 'QUEUED')


def crash_worker(root, point):
    fixture = RuntimeFixture(state_root=root)
    request = fixture.request('Ouvre la tour de contrôle', request_id='crash_scene')
    if point in ('pending', 'provider_unknown'):
        request['text'] = 'des dossiers s’il te plaît'
    (root/'request.json').write_text(json.dumps(request), encoding='utf-8')
    original_write = fixture.runtime._write
    def write(rid, **fields):
        original_write(rid, **fields)
        if ((point == 'pending' and fields.get('decision') == 'pending') or
            (point == 'decision' and 'decision' in fields and fields['decision'] != 'pending') or
            (point == 'plan' and 'plan' in fields)):
            os._exit(73)
    fixture.runtime._write = write
    if point == 'input':fixture.runtime._run = lambda *a, **k:os._exit(73)
    if point == 'provider_unknown':
        def decide(*args):
            # Provider call receipt is test evidence, not the runtime's journal.
            with (root/'provider_calls.txt').open('a', encoding='utf-8') as file:
                file.write('called\n');file.flush();os.fsync(file.fileno())
            os._exit(73)
        fixture.runtime.decider.decide = decide
    if point == 'first_dispatch':
        original_dispatch = fixture.server.tower.dispatch
        def dispatch(rid):
            original_dispatch(rid)
            os._exit(73)
        fixture.server.tower.dispatch = dispatch
    fixture.runtime.submit(request)
    if point == 'receipt':fixture.receive('atelier')
    if point == 'cancel':fixture.runtime.cancel(request['request_id'], request['client_id'])
    os._exit(73)


class RecoveryTests(unittest.TestCase):
    def test_real_process_termination_at_eight_durable_boundaries(self):
        for point in ('input', 'pending', 'provider_unknown', 'decision', 'plan',
                      'first_dispatch', 'receipt', 'cancel'):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                child = subprocess.run([sys.executable, __file__, '--crash-worker', str(root), point],
                                       capture_output=True, text=True, timeout=40)
                self.assertEqual(child.returncode, 73, child.stderr)
                request = json.loads((root/'request.json').read_text(encoding='utf-8'))
                with RuntimeFixture(state_root=root) as fixture:
                    with patch.object(fixture.runtime.decider, 'decide', side_effect=AssertionError('no provider retry')):
                        result = fixture.runtime.submit(request)
                    if point in ('pending', 'provider_unknown'):
                        self.assertEqual(result['status'], 'CLARIFY')
                        self.assertEqual(fixture.count(), 0)
                        calls = root/'provider_calls.txt'
                        self.assertEqual(calls.read_text().count('called') if calls.exists() else 0,
                                         1 if point == 'provider_unknown' else 0)
                    elif point == 'cancel':
                        self.assertEqual(result['status'], 'CANCELLED_AFTER_DISPATCH')
                        self.assertTrue(all(fixture.receive(role) is None for role in fixture.screens))
                    else:
                        self.assertEqual(result['status'], 'QUEUED')
                        self.assertEqual(fixture.count(), 3)
                        for role in fixture.screens:fixture.receive(role)
                        final = fixture.runtime.get(request['request_id'])
                        self.assertEqual(final['display']['rendered_views'], 3)
                        self.assertEqual(fixture.count(), 3)
                        self.assertEqual(len({r['request_id'] for r in final['displays']}), 3)

    def test_burst_24_distinct_commands_and_retries_preserve_every_id(self):
        with RuntimeFixture() as fixture:
            requests = [fixture.request() for _ in range(24)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                first = list(executor.map(fixture.runtime.submit, requests))
            self.assertTrue(all(r['status'] in ('NEW', 'RUNNING', 'QUEUED') for r in first))
            for request in requests:
                self.assertEqual(fixture.runtime.submit(request)['status'], 'QUEUED')
            self.assertEqual(fixture.count(), 24)
            for _ in requests:self.assertIsNotNone(fixture.receive('pilotage'))
            self.assertTrue(all(fixture.runtime.get(r['request_id'])['display']['state']=='rendered' for r in requests))

    def test_burst_same_scene_never_duplicates_children(self):
        with RuntimeFixture() as fixture:
            request = fixture.request('Ouvre la tour de contrôle')
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(fixture.runtime.submit, [request]*24))
            self.assertEqual(fixture.runtime.submit(request)['status'], 'QUEUED')
            self.assertEqual(fixture.count(), 3)

    def test_context_replacement_is_observed_after_warm_connections(self):
        with RuntimeFixture() as fixture:
            old = fixture.server.display.context_hash()
            fixture.runtime.submit(fixture.request())
            fixture.server.store.context_path.write_text('{"changed":true}', encoding='utf-8')
            result = fixture.runtime.submit(fixture.request(context_sha256=old))
            self.assertEqual(result['status'], 'STALE')
            self.assertIsNone(fixture.receive('pilotage'))


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--crash-worker':
        crash_worker(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()
