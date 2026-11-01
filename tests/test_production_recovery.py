"""Exact media reconstruction with small local fixtures, never live providers."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bojart_ops.production_recovery import (
    CATALOG, MANIFEST, PROJECT, RECEIPT, build_plan, load_production, prepare_workspace,
)

ROOT = Path(__file__).resolve().parents[1]


def record(path, raw):
    return {'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class ProductionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.collection = self.root / 'collection'
        self.destination = self.root / 'production'
        self.recipe = self.repo / PROJECT
        self.recipe.mkdir(parents=True)
        (self.repo / CATALOG).mkdir(parents=True)
        self.assets, self.catalogues = [], {1: [], 2: [], 3: []}
        for part, name, raw in ((1, 'source.mp4', b'VIDEO FIXTURE'), (2, 'audio/score.mp3', b'AUDIO FIXTURE')):
            asset = {**record(name, raw), 'role': 'Historical test fixture'}
            self.assets.append(asset)
            path = f"objets/{asset['sha256'][:2]}/{asset['sha256']}{Path(name).suffix}"
            archived = {**record(path, raw), 'part': part}
            self.catalogues[part].append(archived)
            target = self.collection / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        empty = hashlib.sha256(b'').hexdigest()
        self.catalogues[3].append({'path': f'objets/{empty[:2]}/{empty}.txt', 'bytes': 0, 'sha256': empty, 'part': 3})
        (self.recipe / '.gitignore').write_text('*.mp4\n*.mp3\n', encoding='utf-8')
        (self.recipe / 'build.py').write_text("raise RuntimeError('A recipe must not be executed during preparation')\n", encoding='utf-8')
        self.save_metadata()

    def save_metadata(self):
        (self.recipe / 'ASSETS.json').write_text(json.dumps({'assets': self.assets}), encoding='utf-8')
        for part, rows in self.catalogues.items():
            (self.repo / CATALOG / f'contents-part-{part:02d}.jsonl').write_text(
                ''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        self.manifest()

    def manifest(self):
        files = [record(p.relative_to(self.repo).as_posix(), p.read_bytes())
                 for p in sorted(self.repo.rglob('*')) if p.is_file() and p != self.repo / MANIFEST]
        (self.repo / MANIFEST).write_text(json.dumps({'schema_version': 1, 'files': files}), encoding='utf-8')

    def prepare(self):
        return prepare_workspace(self.repo, self.collection, self.destination)

    def test_current_five_assets_match_exact_hashes_without_claiming_artistic_approval(self):
        result = build_plan(ROOT)
        self.assertEqual(result['summary']['assets'], 5)
        self.assertEqual(result['summary']['catalogued_assets'], 5)
        self.assertEqual(result['summary']['required_bytes'], 14276962)
        self.assertFalse(result['source_bytes_verified'])
        self.assertFalse(result['artistic_approval'])
        test19 = next(row for row in result['assets'] if row['path'] == 'TEST19_SOURCE.mp4')
        self.assertIn('provisoire', test19['role'])
        self.assertEqual(test19['archive']['part'], 1)

    def test_preparation_copies_media_and_recipes_without_running_them(self):
        before = {p: p.read_bytes() for p in self.collection.rglob('*') if p.is_file()}
        receipt = self.prepare()
        output = self.destination / 'le-dernier-geste'
        for row in self.assets:
            raw = (output / row['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
        self.assertEqual((output / 'build.py').read_bytes(), (self.recipe / 'build.py').read_bytes())
        self.assertEqual(json.loads((output / RECEIPT).read_text()), receipt)
        self.assertTrue(receipt['source_bytes_verified'] and receipt['copied_bytes_verified'])
        self.assertEqual(receipt['scripts_executed'], 0)
        self.assertEqual(receipt['provider_calls'], 0)
        self.assertTrue(all(row['status'] == 'copied_verified' for row in receipt['assets']))
        self.assertEqual(before, {p: p.read_bytes() for p in self.collection.rglob('*') if p.is_file()})

    def test_missing_catalogue_match_is_visible_and_cannot_be_prepared(self):
        self.catalogues[2] = []; self.save_metadata()
        plan = build_plan(self.repo)
        self.assertFalse(plan['complete'])
        self.assertEqual(plan['assets'][1]['status'], 'not_found_in_catalogue')
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.destination.exists())

    def test_similar_name_never_replaces_a_missing_digest(self):
        self.assets[0]['sha256'] = 'a' * 64; self.save_metadata()
        self.assertIsNone(build_plan(self.repo)['assets'][0]['archive'])

    def test_corrupt_late_source_leaves_no_partial_destination_and_retry_works(self):
        path = self.collection / self.catalogues[2][0]['path']
        original = path.read_bytes(); path.write_bytes(b'X' * len(original))
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.destination.exists())
        self.assertFalse(list(self.root.glob('.bojart-production-*')))
        path.write_bytes(original)
        self.assertTrue(self.prepare()['copied_bytes_verified'])

    def test_missing_source_leaves_no_destination(self):
        (self.collection / self.catalogues[2][0]['path']).unlink()
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.destination.exists())

    def test_existing_destination_is_never_overwritten(self):
        self.destination.mkdir(); marker = self.destination / 'keep.txt'; marker.write_bytes(b'original')
        with self.assertRaises(FileExistsError): self.prepare()
        self.assertEqual(marker.read_bytes(), b'original')
        self.assertEqual(list(self.destination.iterdir()), [marker])

    def test_destination_must_remain_outside_repo_and_archive_collection(self):
        for parent in (self.repo, self.collection):
            with self.subTest(parent=parent), self.assertRaises(ValueError):
                prepare_workspace(self.repo, self.collection, parent / 'new')
            self.assertFalse((parent / 'new').exists())

    def test_unsafe_and_nonportable_asset_paths_are_rejected(self):
        for name in ('../escape.mp4', '/absolute.mp4', 'C:/escape.mp4', 'bad\\file.mp4',
                     '.git/config', 'NUL.mp4', 'trailing./file.mp4', 'bad?.mp4'):
            with self.subTest(name=name):
                self.assets[0]['path'] = name; self.save_metadata()
                with self.assertRaises(ValueError): build_plan(self.repo)

    def test_case_and_file_directory_collisions_are_rejected(self):
        for first, second in (('SOURCE.mp4', 'source.mp4'), ('nested', 'nested/score.mp3'), ('ASSETS.json', 'other.mp3')):
            with self.subTest(first=first):
                self.assets[0]['path'], self.assets[1]['path'] = first, second; self.save_metadata()
                with self.assertRaises(ValueError): build_plan(self.repo)

    def test_stale_repository_manifest_refuses_changed_recipe(self):
        (self.recipe / 'build.py').write_text('different recipe', encoding='utf-8')
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.destination.exists())

    def test_duplicate_catalogue_digest_and_wrong_part_are_refused(self):
        self.catalogues[1].append(copy.deepcopy(self.catalogues[1][0])); self.save_metadata()
        with self.assertRaises(ValueError): build_plan(self.repo)
        self.catalogues[1].pop(); self.catalogues[1][0]['part'] = 3; self.save_metadata()
        with self.assertRaises(ValueError): build_plan(self.repo)

    def test_catalogue_size_conflict_is_not_silently_accepted(self):
        self.catalogues[1][0]['bytes'] += 1; self.save_metadata()
        with self.assertRaises(ValueError): build_plan(self.repo)

    def test_empty_archive_documents_are_allowed_but_empty_required_media_are_not(self):
        self.assertTrue(build_plan(self.repo)['complete'])
        self.assets[0]['bytes'] = 0; self.save_metadata()
        with self.assertRaises(ValueError): build_plan(self.repo)

    def test_duplicate_json_fields_are_rejected(self):
        (self.recipe / 'ASSETS.json').write_text('{"assets":[],"assets":[]}', encoding='utf-8'); self.manifest()
        with self.assertRaises(ValueError): build_plan(self.repo)

    def make_link(self, path, target):
        try: path.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError): self.skipTest('Symbolic links unavailable on this host')

    def test_object_symlink_is_not_followed(self):
        source = self.collection / self.catalogues[1][0]['path']
        elsewhere = self.root / 'outside.mp4'; elsewhere.write_bytes(source.read_bytes()); source.unlink()
        self.make_link(source, elsewhere)
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.destination.exists())

    def test_destination_parent_symlink_is_not_followed(self):
        elsewhere = self.root / 'elsewhere'; elsewhere.mkdir()
        link = self.root / 'linked'; self.make_link(link, elsewhere)
        with self.assertRaises(ValueError):
            prepare_workspace(self.repo, self.collection, link / 'new')
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_destination_created_by_another_process_is_preserved(self):
        original_mkdir = Path.mkdir
        def concurrent_mkdir(path, *args, **kwargs):
            if path == self.destination:
                original_mkdir(path)
                (path / 'concurrent.txt').write_bytes(b'keep')
            return original_mkdir(path, *args, **kwargs)
        with patch.object(Path, 'mkdir', concurrent_mkdir), self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual((self.destination / 'concurrent.txt').read_bytes(), b'keep')
        self.assertFalse((self.destination / 'le-dernier-geste').exists())

    def test_orchestration_binds_the_plan_to_audited_inputs(self):
        result = build_plan(self.repo)
        audit = {'files': [{'path': name, **row} for name, row in result['inputs'].items()]}
        config = {'production_recovery': {'project': PROJECT}}
        self.assertEqual(load_production(self.repo, audit, config), result)
        audit['files'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError): load_production(self.repo, audit, config)
        self.assertIsNone(load_production(self.repo, audit, {}))


if __name__ == '__main__':
    unittest.main()
