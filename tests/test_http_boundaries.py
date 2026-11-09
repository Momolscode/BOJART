"""Real HTTP framing and concurrency checks in temporary workspaces.

No optional model, geometry build, media decoder or physical device is used.
"""
import http.client
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'jarvis/apps/jarvis/app'))
from core import Store
from consolidated_workbench import ConsolidatedWorkbench, ConsolidatedHandler


class TrackedReader:
    def __init__(self, original, started):
        self.original = original
        self.started = started

    def read(self, size=-1):
        self.started.set()
        return self.original.read(size)

    def __getattr__(self, name):
        return getattr(self.original, name)


class ObservedHandler(ConsolidatedHandler):
    def setup(self):
        super().setup()
        if hasattr(self.server, 'test_timeout'):
            self.connection.settimeout(self.server.test_timeout)
        self.rfile = TrackedReader(self.rfile, self.server.read_started)


class HttpBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict('os.environ', {'BOJ_JEV_ENABLED': '0'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app = ConsolidatedWorkbench(('127.0.0.1', 0), Store(Path(self.temp.name)/'work'))
        self.app.read_started = threading.Event()
        self.app.RequestHandlerClass = ObservedHandler
        self.thread = threading.Thread(target=self.app.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_app)

    def close_app(self):
        self.app.shutdown()
        self.thread.join(timeout=5)
        self.app.server_close()

    def request(self, path, body=None, *, auth=True, extra=None):
        connection = http.client.HTTPConnection(*self.app.server_address, timeout=5)
        headers = {'Cookie': 'boj_session='+self.app.token} if auth else {}
        if body is not None:
            headers.update({'Content-Type': 'application/json', 'Origin': self.app.origin})
        headers.update(extra or {})
        try:
            connection.request('GET' if body is None else 'POST', path,
                               body=None if body is None else json.dumps(body), headers=headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def begin_partial(self, path, *, length='2', transfer=None, duplicate_length=None):
        connection = http.client.HTTPConnection(*self.app.server_address, timeout=5)
        connection.putrequest('POST', path)
        connection.putheader('Cookie', 'boj_session='+self.app.token)
        connection.putheader('Origin', self.app.origin)
        connection.putheader('Content-Type', 'application/json')
        connection.putheader('Content-Length', length)
        if duplicate_length is not None:
            connection.putheader('Content-Length', duplicate_length)
        if transfer:
            connection.putheader('Transfer-Encoding', transfer)
        connection.endheaders()
        return connection

    def assert_partial_does_not_lock_workspace(self, route):
        slow = self.begin_partial(route)
        completed = threading.Event()
        result = []
        worker = None
        try:
            self.assertTrue(self.app.read_started.wait(2), 'Server never began reading the request body')
            def create_project():
                try:
                    result.append(self.request('/api/projects/create',
                                               {'project_id': 'BOJ-OTHER-001', 'name': 'Autre fenêtre'}))
                except Exception as exc:
                    result.append(exc)
                finally:
                    completed.set()
            worker = threading.Thread(target=create_project, daemon=True)
            worker.start()
            self.assertTrue(completed.wait(2), 'An unfinished HTTP body locked another workspace action')
            self.assertIsInstance(result[0], tuple, result[0])
            self.assertEqual(result[0][0], 200, result[0])
        finally:
            try:
                slow.send(b'{}')
                slow.getresponse().read()
            finally:
                slow.close()
                if worker:
                    worker.join(timeout=5)

    def test_partial_workspace_body_does_not_hold_mutation_lock(self):
        self.assert_partial_does_not_lock_workspace('/api/workspace/check')

    def test_partial_studio_body_does_not_hold_mutation_lock(self):
        self.assert_partial_does_not_lock_workspace('/api/studio/refresh')

    def test_partial_cad_body_does_not_hold_mutation_lock(self):
        self.assert_partial_does_not_lock_workspace('/api/propose')

    def test_valid_buffered_requests_reach_all_three_handlers(self):
        for path, body in [
            ('/api/projects/create', {'project_id': 'BOJ-HTTP-001', 'name': 'Test HTTP'}),
            ('/api/studio/refresh', {}),
            ('/api/propose', {'command': 'Crée un socle de 180 mm', 'revision': 0, 'source': 'typed'}),
        ]:
            with self.subTest(path=path):
                status, _, raw = self.request(path, body)
                self.assertEqual(status, 200, raw)
                self.assertIsInstance(json.loads(raw), dict)
        self.assertEqual(self.app.store.list_jobs(), [])

    def test_unicode_bootstrap_token_is_rejected_with_json(self):
        status, _, raw = self.request('/?session=%C3%A9', auth=False)
        self.assertEqual(status, 401)
        self.assertIn('error', json.loads(raw))

    def test_valid_bootstrap_retains_private_cookie_and_redirect(self):
        status, headers, body = self.request('/?session='+self.app.token, auth=False)
        self.assertEqual(status, 303)
        self.assertEqual(headers['Location'], '/workspace')
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        self.assertEqual(body, b'')

    def test_truncated_body_is_rejected_without_workspace_mutation(self):
        before = self.app.store.list_projects()
        connection = self.begin_partial('/api/projects/create', length='100')
        try:
            connection.send(b'{}')
            connection.sock.shutdown(socket.SHUT_WR)
            response = connection.getresponse()
            self.assertIn(response.status, (400, 409))
            self.assertIn('error', json.loads(response.read()))
        finally:
            connection.close()
        self.assertEqual(self.app.store.list_projects(), before)

    def test_invalid_framing_is_rejected_before_waiting_for_body(self):
        for length, transfer, expected in [('invalid', None, 400), ('16385', None, 413),
                                            ('2', 'chunked', 400)]:
            with self.subTest(length=length, transfer=transfer):
                connection = self.begin_partial('/api/projects/create', length=length, transfer=transfer)
                try:
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    self.assertIn('error', json.loads(response.read()))
                finally:
                    connection.close()

    def test_denied_requests_do_not_read_or_mutate(self):
        before = self.app.store.list_projects()
        for auth, extra, expected in [(False, {}, 401), (True, {'Origin': 'https://foreign.invalid'}, 403)]:
            with self.subTest(auth=auth):
                self.app.read_started.clear()
                status, _, _ = self.request('/api/projects/create', {}, auth=auth, extra=extra)
                self.assertEqual(status, expected)
                self.assertFalse(self.app.read_started.is_set())
        self.assertEqual(self.app.store.list_projects(), before)

    def test_timed_out_bodies_release_capacity_and_leave_workspace_available(self):
        self.app.test_timeout = .2
        for _ in range(13):
            connection = self.begin_partial('/api/workspace/check')
            try:
                response = connection.getresponse()
                self.assertEqual(response.status, 408)
                self.assertIn('error', json.loads(response.read()))
            finally:
                connection.close()
        status, _, _ = self.request('/api/projects/create',
                                    {'project_id': 'BOJ-AFTER-001', 'name': 'Après réception interrompue'})
        self.assertEqual(status, 200)

    def test_saturated_reader_capacity_rejects_before_receiving_body(self):
        acquired = 0
        try:
            while self.app.requests_gate.acquire(blocking=False):
                acquired += 1
            connection = self.begin_partial('/api/workspace/check')
            try:
                response = connection.getresponse()
                self.assertEqual(response.status, 429)
                self.assertIn('error', json.loads(response.read()))
                self.assertFalse(self.app.read_started.is_set())
            finally:
                connection.close()
        finally:
            for _ in range(acquired):
                self.app.requests_gate.release()

    def test_route_specific_smaller_body_limit_is_preserved(self):
        status, _, raw = self.request('/api/projects/create', {'padding': 'x'*9000})
        self.assertEqual(status, 413)
        self.assertIn('error', json.loads(raw))

    def test_duplicate_lengths_are_rejected_without_reading_body(self):
        for repeated in ('2', '100'):
            connection = self.begin_partial('/api/projects/create', duplicate_length=repeated)
            try:
                response = connection.getresponse()
                self.assertEqual(response.status, 400)
                self.assertIn('error', json.loads(response.read()))
                self.assertFalse(self.app.read_started.is_set())
            finally:
                connection.close()


if __name__ == '__main__':
    unittest.main()
