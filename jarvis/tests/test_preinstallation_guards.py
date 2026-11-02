"""Regression guards; local fixtures only, no provider, media decoder or machine."""
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'jarvis/apps/jarvis/app'))
from core import Store, Rejected
from media_library import MediaLibrary
from studio_seed import seed, SEED_SOURCE_SHA256
from workbench import Workbench


class SeedIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.media = self.root/'media'
        self.media.mkdir()
        self.fixture_hashes = {}
        for name in SEED_SOURCE_SHA256:
            data = ('synthetic test fixture '+name).encode()
            (self.media/name).write_bytes(data)
            self.fixture_hashes[name] = hashlib.sha256(data).hexdigest()
        self.lib = MediaLibrary(self.root/'state', [self.media], lambda _: {
            'duration': 20., 'width': 32, 'height': 32, 'fps': '1/1', 'codec': 'fixture', 'audio': False})

    def tearDown(self):
        self.lib.close()
        self.temp.cleanup()

    def test_renamed_unrelated_bytes_never_inherit_authentic_annotations(self):
        with self.assertRaisesRegex(Rejected, 'différent'):
            seed(self.lib, self.media)
        self.assertEqual(self.lib.catalogue()['asset_count'], 0)
        self.assertEqual(self.lib.catalogue()['segments'], [])

    def test_seed_digests_match_registered_original_assets(self):
        records = [json.loads(line) for line in (REPO/'data/catalog/assets.jsonl').read_text('utf8').splitlines()]
        for name, digest in SEED_SOURCE_SHA256.items():
            matches = {r['sha256'] for r in records if r['source_path'] == 'apps/jarvis/studio_media/'+name}
            self.assertEqual(matches, {digest})

    def test_matching_explicit_fixture_digests_allow_the_known_annotations(self):
        # Only this test substitutes the expected identities; fixtures are not project media.
        with patch.dict(SEED_SOURCE_SHA256, self.fixture_hashes, clear=True):
            result = seed(self.lib, self.media)
        self.assertEqual(len(result['segments']), 8)
        self.assertEqual(sum(s['identity_anchor'] for s in result['segments']), 4)

    def test_change_between_precheck_and_ingestion_never_promotes_anchors(self):
        ingest = self.lib.ingest
        def changed(path, *args):
            if Path(path).name == 'source_bojart.mp4':
                Path(path).write_bytes(b'changed after identity precheck')
            return ingest(path, *args)
        with patch.dict(SEED_SOURCE_SHA256, self.fixture_hashes, clear=True), patch.object(self.lib, 'ingest', changed):
            with self.assertRaisesRegex(Rejected, 'changé'):
                seed(self.lib, self.media)
        self.assertEqual(self.lib.catalogue()['segments'], [])


class PortOwnershipTests(unittest.TestCase):
    def test_another_workspace_cannot_bind_the_live_listener(self):
        with tempfile.TemporaryDirectory() as td:
            first = Workbench(('127.0.0.1', 0), Store(Path(td)/'first'))
            second = None
            try:
                with self.assertRaises(OSError):
                    second = Workbench(first.server_address, Store(Path(td)/'second'))
            finally:
                if second is not None: second.server_close()
                first.server_close()

    @unittest.skipUnless(hasattr(socket, 'SO_EXCLUSIVEADDRUSE'), 'Windows socket policy')
    def test_windows_listener_is_exclusive_without_reuseaddr(self):
        with tempfile.TemporaryDirectory() as td:
            server = Workbench(('127.0.0.1', 0), Store(td))
            try:
                self.assertEqual(server.socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0)
                self.assertEqual(server.socket.getsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE), 1)
            finally:
                server.server_close()


if __name__ == '__main__': unittest.main()
