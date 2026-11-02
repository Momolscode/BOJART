"""Archive restoration contracts, using tiny local fixtures and no real media."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'tools/restore_archive_2026_11_01.py'
SPEC = importlib.util.spec_from_file_location('archive_restore', SCRIPT)
restore = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(restore)


def record(path, data):
    return {'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class RestoreArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'chunks').mkdir()
        (self.root / 'direct.txt').write_bytes(b'direct')
        (self.root / 'chunks/a').write_bytes(b'abc')
        (self.root / 'chunks/b').write_bytes(b'def')
        direct = record('direct.txt', b'direct')
        direct['source_path'] = direct.pop('path')
        split = record('nested/out.bin', b'abcdef')
        split['parts'] = [record('chunks/a', b'abc'), record('chunks/b', b'def')]
        self.manifest = {'direct_files': [direct], 'split_files': [split]}
        self.manifest_path = self.root / 'manifest.json'
        self.destination = self.root / 'restored'

    def run_restore(self):
        self.manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')
        output = io.StringIO()
        with patch.object(restore, 'ROOT', self.root), patch.object(restore, 'MANIFEST', self.manifest_path), \
             patch('sys.argv', [str(SCRIPT), '--destination', str(self.destination)]), \
             contextlib.redirect_stdout(output):
            result = restore.main()
        return result, json.loads(output.getvalue())

    def test_success_includes_direct_and_reconstructed_bytes(self):
        code, receipt = self.run_restore()
        self.assertEqual(code, 0)
        self.assertEqual(receipt['result'], 'verified')
        self.assertEqual(len(receipt['files']), 2)
        self.assertEqual((self.destination / 'direct.txt').read_bytes(), b'direct')
        self.assertEqual((self.destination / 'nested/out.bin').read_bytes(), b'abcdef')

    def test_corrupt_late_part_leaves_no_destination_and_retry_works(self):
        (self.root / 'chunks/b').write_bytes(b'bad')
        with self.assertRaises(ValueError):
            self.run_restore()
        self.assertFalse(self.destination.exists())
        (self.root / 'chunks/b').write_bytes(b'def')
        self.assertEqual(self.run_restore()[0], 0)

    def test_invalid_combined_hash_leaves_no_destination(self):
        self.manifest['split_files'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.run_restore()
        self.assertFalse(self.destination.exists())

    def test_invalid_part_size_leaves_no_destination(self):
        self.manifest['split_files'][0]['parts'][1]['bytes'] = 2
        with self.assertRaises(ValueError):
            self.run_restore()
        self.assertFalse(self.destination.exists())

    def test_corrupt_direct_source_leaves_no_destination(self):
        (self.root / 'direct.txt').write_bytes(b'broken')
        with self.assertRaises(ValueError):
            self.run_restore()
        self.assertFalse(self.destination.exists())

    def test_missing_late_part_leaves_no_destination(self):
        (self.root / 'chunks/b').unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_restore()
        self.assertFalse(self.destination.exists())

    def test_existing_destination_is_preserved(self):
        self.destination.mkdir()
        marker = self.destination / 'keep.txt'
        marker.write_bytes(b'untouched')
        with self.assertRaises(FileExistsError):
            self.run_restore()
        self.assertEqual(list(self.destination.iterdir()), [marker])
        self.assertEqual(marker.read_bytes(), b'untouched')

    def test_corrupt_direct_copy_never_emits_a_success_receipt(self):
        def corrupt_copy(source, output):
            output.write_bytes(b'broken')
        with patch.object(restore.shutil, 'copyfile', side_effect=corrupt_copy):
            with self.assertRaises(ValueError):
                self.run_restore()

    def test_escaping_output_is_rejected_before_writing(self):
        self.manifest['split_files'][0]['path'] = '../escape.bin'
        with self.assertRaises(ValueError):
            self.run_restore()
        self.assertFalse(self.destination.exists())
        self.assertFalse((self.root / 'escape.bin').exists())

    def test_duplicate_output_is_rejected_before_writing(self):
        self.manifest['split_files'][0]['path'] = 'direct.txt'
        with self.assertRaises(ValueError):
            self.run_restore()
        self.assertFalse(self.destination.exists())


if __name__ == '__main__':
    unittest.main()
