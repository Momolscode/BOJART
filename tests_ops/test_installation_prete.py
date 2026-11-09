"""Installation réelle du 9 novembre 2026 : ce qui empêchait Jarvis d'être prêt après l'installateur.

1. Copie « Code → Download ZIP » ou tour sans Git : le banc et le validateur s'arrêtaient sur
   ``git ls-files`` et l'installation finissait en échec.
2. Voix installée mais éteinte : ni poids ni réglage.
Aucun réseau, aucun micro : téléchargement simulé, dossiers temporaires.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'jarvis/apps/jarvis/app'))

from bojart_ops import banc_statique as st  # noqa: E402
from bojart_ops import voix_installation as vi  # noqa: E402

SPEC = importlib.util.spec_from_file_location('validate_repository', ROOT / 'tools/validate_repository.py')
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

POIDS = b'poids de test'
FAUX = {'test': {'depot': 'exemple/faux', 'revision': '0123456789abcdef', 'model_bin_sha256': hashlib.sha256(POIDS).hexdigest()}}


def no_git(*args, **kwargs):
    raise FileNotFoundError('git')


def zip_copy(dest, names):
    """The published files only, without .git: what « Download ZIP » gives."""
    for name in names:
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)


class SansGit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_tracked_files_fall_back_to_the_manifest(self):
        published = st.manifest_files(ROOT)
        self.assertIn(st.MANIFEST, published)
        self.assertIn('tools/start_jarvis.py', published)
        with mock.patch.object(st.subprocess, 'run', no_git):
            self.assertEqual(st.tracked_files(ROOT), published)
        # A folder that is not a checkout (Git present, exit 128) gives the same list.
        names = [n for n in published if n.startswith(('data/catalog/', 'sites/atelier/dist/', '.gitignore'))]
        zip_copy(self.tmp, names)
        self.assertEqual(st.tracked_files(self.tmp), st.manifest_files(self.tmp))

    def test_web_media_left_out_of_git_stay_preconditions_without_git(self):
        names = [n for n in st.manifest_files(ROOT) if n.startswith('sites/atelier/dist/') or n in ('.gitignore', st.MANIFEST)]
        zip_copy(self.tmp, names)
        with mock.patch.object(st.subprocess, 'run', no_git):
            found = st.check_web_references(st.tracked_files(self.tmp), self.tmp)
        logo = [f for f in found if 'logo.webp' in f['detail']]
        self.assertTrue(logo)
        self.assertTrue(all(f.get('precondition') for f in logo), logo)

    def test_fallback_ignore_rules_match_git(self):
        if shutil.which('git') is None or not (ROOT / '.git').exists():
            self.skipTest('Git absent : comparaison impossible.')
        files = st.tracked_files(ROOT)
        paths = sorted(set(files[::7] + [
            'sites/atelier/dist/assets/logo.webp', 'docs/historical/BOJART_BREAK_THE_FRAME_V6_STORYBOARD_AUDIT.pdf', 'docs/x/a.pdf',
            '.env', '.env.example', 'a/b/.env.prod', 'jarvis/apps/jarvis/config.json', 'jarvis/runtime/x.json', 'state/a',
            'runs/figurine/a.json', 'runs/autre/a.json', 'x/node_modules/a.js', 'jarvis/docs/evidence/m06-2026-10-31/s/a.png',
            'media/raw/a.txt', 'x/media/raw/a.txt']))
        proc = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin', '-z'], cwd=ROOT,
                              input='\0'.join(paths).encode('utf-8'), capture_output=True)
        expected = {x for x in proc.stdout.decode('utf-8').split('\0') if x}
        rules = st._gitignore_rules(ROOT, files)
        self.assertEqual({p for p in paths if st._ignored_by_rules(p, rules)}, expected)

    def test_validator_checks_the_published_paths_without_git(self):
        (self.tmp / 'data/catalog').mkdir(parents=True)
        manifest = {'files': [{'path': 'a.txt', 'bytes': 1, 'sha256': 'x'}, {'path': 'b/c.md', 'bytes': 1, 'sha256': 'y'}]}
        (self.tmp / validator.MANIFEST).write_text(json.dumps(manifest), encoding='utf-8')
        with mock.patch.object(validator.subprocess, 'run', no_git):
            self.assertEqual(validator.names(self.tmp), ['a.txt', 'b/c.md', validator.MANIFEST])
        # Inside a real checkout, Git's view (tracked and new files) is kept.
        if shutil.which('git') and (ROOT / '.git').exists():
            self.assertIn('tools/validate_repository.py', validator.names(ROOT))


class Voix(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home)
        patcher = mock.patch.dict(vi.MODELES, FAUX)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.calls = []

    def download(self, name, dest, poids=POIDS):
        self.calls.append((name, Path(dest)))
        dest = Path(dest)
        dest.mkdir(parents=True)
        (dest / 'model.bin').write_bytes(poids)
        (dest / 'config.json').write_text('{}', encoding='utf-8')
        (dest / 'tokenizer.json').write_text('{}', encoding='utf-8')

    def test_weights_are_downloaded_once_into_a_pinned_folder(self):
        first = vi.ensure_weights('test', self.home, self.download)
        self.assertEqual(first['statut'], 'telecharge')
        self.assertTrue(first['dossier'].endswith('faster-whisper-test-01234567'))
        second = vi.ensure_weights('test', self.home, self.download)
        self.assertEqual(second['statut'], 'present')
        self.assertEqual(len(self.calls), 1)

    def test_altered_or_interrupted_weights_are_set_aside_never_deleted(self):
        target = vi.target_dir('test', self.home)
        self.download('test', target, poids=b'autre')
        partial = target.with_name(target.name + '.telechargement')
        partial.mkdir()
        (partial / 'model.bin').write_bytes(b'moitie')
        result = vi.ensure_weights('test', self.home, self.download)
        self.assertEqual(result['statut'], 'telecharge')
        self.assertEqual(len(result['mis_de_cote']), 2)
        kept = sorted(p.name for p in target.parent.iterdir())
        self.assertTrue(any('.altere-' in n for n in kept) and any('.interrompu-' in n for n in kept), kept)
        self.assertEqual((target / 'model.bin').read_bytes(), POIDS)

    def test_a_bad_download_is_refused(self):
        with self.assertRaises(RuntimeError):
            vi.ensure_weights('test', self.home, lambda n, d: self.download(n, d, poids=b'faux'))
        self.assertFalse(vi.target_dir('test', self.home).exists())

    def test_voice_is_enabled_in_a_new_private_config_that_jarvis_accepts(self):
        weights = vi.ensure_weights('test', self.home, self.download)
        config = self.home / 'config.json'
        self.assertEqual(vi.enable_voice(weights['dossier'], config)['statut'], 'cree')
        from workbench import load_config
        from voice import LocalVoice
        loaded = load_config(str(config))
        self.assertTrue(loaded['voice']['enabled'])
        self.assertFalse(loaded['ollama']['enabled'])
        self.assertEqual(LocalVoice(loaded['voice'], loader=lambda: None).status()['status'], 'available')
        self.assertEqual(vi.enable_voice(weights['dossier'], config)['statut'], 'inchange')

    def test_existing_config_only_changes_its_voice_section(self):
        weights = vi.ensure_weights('test', self.home, self.download)
        config = self.home / 'config.json'
        data = json.loads(vi.EXAMPLE.read_text(encoding='utf-8'))
        data['ollama'].update(enabled=True, model='qwen-local')
        config.write_text(json.dumps(data), encoding='utf-8')
        self.assertEqual(vi.enable_voice(weights['dossier'], config)['statut'], 'active')
        saved = json.loads(config.read_text(encoding='utf-8'))
        self.assertEqual(saved['ollama'], data['ollama'])
        self.assertEqual(saved['voice'], {'enabled': True, 'model_dir': str(Path(weights['dossier']).resolve())})

    def test_unexpected_config_is_left_untouched(self):
        config = self.home / 'config.json'
        config.write_text('{"version": "autre"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            vi.enable_voice(self.home, config)
        self.assertEqual(config.read_text(encoding='utf-8'), '{"version": "autre"}')


if __name__ == '__main__':
    unittest.main()
