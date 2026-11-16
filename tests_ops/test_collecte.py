"""Collecte guidée : copie vérifiée, jamais d'écrasement, sources intactes, reprise sans relecture."""
import io
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bojart_ops import collecte as co  # noqa: E402

SPEC = importlib.util.spec_from_file_location('collecte_guidee', ROOT / 'tools/collecte_guidee.py')
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.src = self.root / 'Vidéos BOJ.ART'
        self.src.mkdir()
        self.c = co.Collecte(self.root / 'collecte', self.root / 'memoire')
        self.addCleanup(self.c.close)

    def put(self, name, data):
        path = self.src / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path


class Sources(Base):
    def test_designated_once_and_remembered(self):
        first = self.c.add_source(self.src)
        self.assertTrue(self.c.add_source(self.src)['deja_designe'])
        self.c.close()
        self.c = co.Collecte(self.root / 'collecte', self.root / 'memoire')
        self.addCleanup(self.c.close)
        self.assertEqual([s['id'] for s in self.c.sources()], [first['id']])

    def test_refuses_folders_overlapping_the_store_or_memory(self):
        for folder in (self.root, self.root / 'collecte' / 'originaux'):
            with self.assertRaises(ValueError):
                self.c.add_source(folder)
        (self.root / 'memoire').mkdir()
        with self.assertRaises(ValueError):
            self.c.add_source(self.root / 'memoire')

    def test_missing_folder_and_unknown_project_are_refused(self):
        with self.assertRaises(ValueError):
            self.c.add_source(self.root / 'absent')
        with self.assertRaises(ValueError):
            self.c.add_source(self.src, project='autre')


class Copy(Base):
    def test_copy_is_verified_read_only_and_never_overwritten(self):
        self.put('a.mp4', b'video-a' * 1000)
        self.put('b/copie.mp4', b'video-a' * 1000)
        self.c.add_source(self.src)
        result = self.c.collect(self.c.plan())
        self.assertEqual((result['comptes']['copie'], result['comptes']['doublon']), (1, 1))
        stored = [p for p in self.c.store.rglob('*') if p.is_file()]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].name, co.file_sha(self.src / 'a.mp4') + '.mp4')
        self.assertFalse(stored[0].stat().st_mode & stat.S_IWUSR)
        self.assertEqual(list((self.c.store / '.en-cours').iterdir()), [])

    def test_second_pass_reads_nothing_and_changed_files_are_taken_again(self):
        path = self.put('a.mov', b'1' * 10)
        self.c.add_source(self.src)
        self.c.collect(self.c.plan())
        self.assertEqual(self.c.plan()['elements'], [])
        path.write_bytes(b'2' * 12)
        plan = self.c.plan()
        self.assertEqual([i['relatif'] for i in plan['elements']], ['a.mov'])
        self.assertEqual(self.c.collect(plan)['comptes']['copie'], 1)

    def test_source_changing_during_copy_is_not_kept(self):
        self.put('a.mp4', b'x' * 100)
        self.c.add_source(self.src)
        plan = self.c.plan()
        plan['elements'][0]['mtime_ns'] -= 1  # as if the file had been rewritten since the scan
        result = self.c.collect(plan)
        self.assertEqual(result['comptes']['erreur'], 1)
        self.assertIn('modifiée pendant la copie', result['problemes'][0]['detail'])
        self.assertEqual([p for p in self.c.store.rglob('*') if p.is_file()], [])
        self.assertEqual(len(self.c.plan()['elements']), 1)  # retried next time

    def test_hidden_private_links_and_unknown_formats_are_skipped(self):
        self.put('.env', b'TOKEN=x')
        self.put('.cache/v.mp4', b'v')
        self.put('Thumbs.db', b't')
        self.put('outil.exe', b'MZ')
        self.put('ok.jpg', b'jpg')
        self.c.add_source(self.src)
        plan = self.c.plan()
        self.assertEqual([i['relatif'] for i in plan['elements']], ['ok.jpg'])
        ignored = plan['par_source'][0]['ignores']
        self.assertEqual((ignored['caches_ou_prives'], ignored['autres']), (3, {'.exe': 1}))

    def test_space_check_blocks_before_any_copy(self):
        self.put('a.mp4', b'x')
        self.c.add_source(self.src)
        with mock.patch.object(co.shutil, 'disk_usage', return_value=mock.Mock(free=co.MARGIN_BYTES)):
            plan = self.c.plan()
        self.assertFalse(plan['espace_suffisant'])
        with mock.patch.object(co.shutil, 'disk_usage', return_value=mock.Mock(free=co.MARGIN_BYTES)), \
             mock.patch.object(sys, 'stdin', io.StringIO('o\n')), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.run_collect(self.c, assume_yes=True), 2)
        self.assertEqual([p for p in self.c.store.rglob('*') if p.is_file()], [])

    def test_alteration_and_loss_are_reported(self):
        self.put('a.mp4', b'a')
        self.put('b.mp4', b'b')
        self.c.add_source(self.src)
        self.c.collect(self.c.plan())
        first, second = sorted(p for p in self.c.store.rglob('*') if p.is_file())
        os.chmod(first, stat.S_IREAD | stat.S_IWRITE)
        first.write_bytes(b'z')
        os.chmod(second, stat.S_IREAD | stat.S_IWRITE)
        second.unlink()
        report = self.c.verify()
        self.assertFalse(report['ok'])
        self.assertEqual((len(report['alteres']), len(report['manquants'])), (1, 1))


class Memory(Base):
    def test_text_goes_to_memory_as_unverified_document(self):
        self.put('notes.md', 'Vernis Zéphyrine, séchage 24 h.\n'.encode('utf-8'))
        self.c.add_source(self.src, project='bojart.creative')
        result = self.c.collect(self.c.plan())
        self.assertEqual(result['comptes']['memoire'], 1)
        from bojart_memory import Memory as M
        with M(self.c.memory_state, readonly=True) as memory:
            hits = memory.search('Zéphyrine', project='bojart.creative', limit=3)['results']
        self.assertTrue(hits)

    def test_chatgpt_export_only_reads_conversations(self):
        import zipfile
        archive = self.src / 'export.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('conversations.json', json.dumps([{'title': 'Quasarine'}]))
            z.writestr('../evasion.txt', 'non')
        self.c.add_source(self.src)
        result = self.c.collect(self.c.plan())
        self.assertEqual(result['comptes']['sessions'], 1)
        extracted = [p.name for p in (self.c.base / 'exports').rglob('*') if p.is_file()]
        self.assertEqual(extracted, ['conversations.json'])
        self.assertFalse((self.root / 'evasion.txt').exists())

    def test_zip_without_conversations_is_only_kept(self):
        import zipfile
        with zipfile.ZipFile(self.src / 'photos.zip', 'w') as z:
            z.writestr('a.jpg', 'x')
        self.c.add_source(self.src)
        result = self.c.collect(self.c.plan())
        self.assertEqual((result['comptes']['copie'], result['comptes']['sessions']), (1, 0))
        self.assertFalse((self.c.base / 'exports').exists())


class Cli(unittest.TestCase):
    def test_end_to_end_simulation_passes(self):
        with redirect_stdout(io.StringIO()):
            result = cli.simulation()
        self.assertTrue(result['ok'], result['controles'])

    def test_launcher_is_ascii_crlf(self):
        raw = (ROOT / 'Collecter_BOJART.cmd').read_bytes()
        raw.decode('ascii')
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        self.assertIn(b'tools\\collecte_guidee.py %*', raw)


if __name__ == '__main__':
    unittest.main()
