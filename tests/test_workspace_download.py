"""Download actual workspace snapshots over HTTP and restore the received bytes."""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'jarvis/apps/jarvis/app'))
from core import Store
from consolidated_workbench import ConsolidatedWorkbench
from workspace_state import restore_snapshot


class WorkspaceDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = ConsolidatedWorkbench(('127.0.0.1', 0), Store(self.root/'work'))
        self.thread = threading.Thread(target=self.app.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_app)

    def close_app(self):
        self.app.shutdown()
        self.thread.join(timeout=5)
        self.app.server_close()

    def request(self, path, body=None, *, auth=True, host=None):
        headers = {'Cookie': 'boj_session='+self.app.token} if auth else {}
        if host:
            headers['Host'] = host
        if body is not None:
            headers.update({'Content-Type': 'application/json', 'Origin': self.app.origin})
        connection = http.client.HTTPConnection(*self.app.server_address, timeout=10)
        try:
            connection.request('GET' if body is None else 'POST', path,
                               body=None if body is None else json.dumps(body), headers=headers)
            response = connection.getresponse()
            return response.status, response.getheaders(), response.read()
        finally:
            connection.close()

    def backup(self):
        status, _, raw = self.request('/api/workspace/backup', {'request_id': uuid.uuid4().hex})
        self.assertEqual(status, 200, raw)
        return json.loads(raw)

    def test_download_has_one_correct_length_and_exact_snapshot_bytes(self):
        receipt = self.backup()
        expected = (self.app.store.root/receipt['url'].lstrip('/')).read_bytes()
        status, headers, body = self.request(receipt['url'])
        self.assertEqual(status, 200)
        lengths = [value for name, value in headers if name.lower() == 'content-length']
        self.assertEqual(lengths, [str(len(expected))])
        self.assertEqual(body, expected)
        self.assertEqual(hashlib.sha256(body).hexdigest(), receipt['sha256'])
        self.assertEqual(dict(headers)['Content-Type'], 'application/zip')

    def test_received_archive_restores_the_project_in_a_new_directory(self):
        self.app.store.create_project('BOJ-DOWNLOAD-001', 'Copie téléchargée')
        receipt = self.backup()
        status, _, body = self.request(receipt['url'])
        self.assertEqual(status, 200)
        self.assertTrue(body, 'HTTP download returned an empty archive')
        downloaded = self.root/'received.zip'
        downloaded.write_bytes(body)
        restored = restore_snapshot(downloaded, self.root/'restored')
        self.assertEqual(restored['archive_sha256'], receipt['sha256'])
        copied = Store(self.root/'restored')
        self.assertEqual(copied.project_revision('BOJ-DOWNLOAD-001'), 0)
        self.assertFalse(restored['physical_actions'])

    def test_download_keeps_session_and_host_guards(self):
        receipt = self.backup()
        self.assertEqual(self.request(receipt['url'], auth=False)[0], 401)
        self.assertEqual(self.request(receipt['url'], host='foreign.invalid')[0], 403)

    def test_json_and_static_responses_keep_their_exact_lengths(self):
        for path in ['/health', '/workspace']:
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                self.assertEqual(status, 200)
                lengths = [value for name, value in headers if name.lower() == 'content-length']
                self.assertEqual(lengths, [str(len(body))])
                self.assertTrue(body)


if __name__ == '__main__':
    unittest.main()
