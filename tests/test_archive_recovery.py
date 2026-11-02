import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import restore_recovery_2026_11_01 as recovery
from tools import validate_repository as policy


class RecoveryGuardTests(unittest.TestCase):
    def test_archive_paths_cannot_escape_destination(self):
        for name in ('../outside', '/outside', 'a/../../outside', 'a\\outside',
                     'C:/outside', '.git/config', 'a//b', 'a/./b', 'a\nb', 'a\x00b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                recovery.safe_path(name)

    def test_existing_destination_is_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);marker=path/'keep.txt';marker.write_text('keep')
            with patch.object(recovery.subprocess, 'run') as command:
                with self.assertRaises(FileExistsError):recovery.restore(path, fetch=True)
                command.assert_not_called()
            self.assertEqual(marker.read_text(), 'keep')

    def test_corrupt_content_is_rejected_even_when_length_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'object';path.write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                recovery.check_file(path, 5, hashlib.sha256(b'right').hexdigest())

    def test_dangling_destination_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'destination'
            try:path.symlink_to(Path(folder)/'absent', target_is_directory=True)
            except OSError:self.skipTest('Symlinks unavailable')
            with self.assertRaises(FileExistsError):recovery.restore(path)


class ApprovedArchivePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.path='docs/historical/approved.pdf'
        p=self.root/self.path;p.parent.mkdir(parents=True);p.write_bytes(b'\xffapproved')
        self.manifest=self.root/policy.ARCHIVE_MANIFEST;self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(json.dumps({'direct_files':[{'source_path':self.path,
            'bytes':9,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}], 'split_files':[]}))
        self.pin=patch.object(policy,'ARCHIVE_MANIFEST_SHA256',hashlib.sha256(self.manifest.read_bytes()).hexdigest())
        self.pin.start()

    def tearDown(self):
        self.pin.stop();self.temp.cleanup()

    def test_unlisted_binary_never_receives_an_exception(self):
        (self.root/'unlisted.mp4').write_bytes(b'\xffprivate')
        approved,issues=policy.verified_archive_files(self.root)
        self.assertFalse(issues);self.assertEqual(set(approved),{self.path})

    def test_changed_approved_binary_remains_rejected(self):
        (self.root/self.path).write_bytes(b'\xffmodified')
        approved,issues=policy.verified_archive_files(self.root)
        self.assertNotIn(self.path,approved)
        self.assertEqual(issues[0]['error'],'archive_checksum_mismatch')

    def test_changed_manifest_cannot_expand_exception(self):
        self.manifest.write_text(self.manifest.read_text()+'\n')
        approved,issues=policy.verified_archive_files(self.root)
        self.assertFalse(approved);self.assertEqual(issues[0]['error'],'archive_manifest_changed')


if __name__ == '__main__':unittest.main()
