"""Verrous d'installation : la tour doit installer exactement l'environnement testé, sinon le dire."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bojart_ops import verrou_dependances as vd  # noqa: E402

SPEC = importlib.util.spec_from_file_location('prepare_installation', ROOT / 'tools/prepare_installation.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)

H = 'a' * 64


class LockFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.write('jarvis/requirements.txt', '-r apps/jarvis/requirements.txt\n-r requirements-orchestration.txt\n')
        self.write('jarvis/apps/jarvis/requirements.txt', 'cadquery==2.8.0\n')
        self.write('jarvis/requirements-orchestration.txt', 'langgraph==1.2.18\n')
        self.write('jarvis/requirements-voice.txt', 'faster-whisper==1.2.1\n')
        self.write('jarvis/requirements-tests.txt', 'pytest==9.0.2\n')

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))
        return path

    def lock(self, profile, entries, sources=None):
        req = vd.profiles(self.root)[profile]
        files = sources if sources is not None else vd.requirement_closure(req)
        lines = ['# Verrou de test'] + [f'# source {vd.rel(f, self.root)} sha256={hashlib.sha256(f.read_bytes()).hexdigest()}' for f in files]
        lines += [f'{name}=={version} \\\n    --hash=sha256:{digest}' if digest else f'{name}=={version}' for name, version, digest in entries]
        return self.write(f'jarvis/locks/windows-cp312-{profile}.txt', '\n'.join(lines) + '\n')

    def good_locks(self):
        self.lock('moteurs', [('cadquery', '2.8.0', H), ('langgraph', '1.2.18', H), ('Typing_Extensions', '4.15.0', H)])
        self.lock('voice', [('faster-whisper', '1.2.1', H), ('ctranslate2', '4.8.4', H)])


class Profiles(LockFixture):
    def test_top_level_files_only_and_tests_excluded(self):
        self.assertEqual({k: v.name for k, v in vd.profiles(self.root).items()},
                         {'moteurs': 'requirements.txt', 'voice': 'requirements-voice.txt'})
        self.assertEqual(vd.top_level_pins(vd.profiles(self.root)['moteurs']), {'cadquery': '2.8.0', 'langgraph': '1.2.18'})


class Verify(LockFixture):
    def test_consistent_locks_pass(self):
        self.good_locks()
        self.assertEqual(vd.verify(self.root), [])
        self.assertEqual(vd.parse_lock(vd.lock_path('moteurs', 'windows', self.root))[1]['typing-extensions'],
                         {'version': '4.15.0', 'hashes': [H]})

    def test_missing_lock_is_reported(self):
        self.lock('moteurs', [('cadquery', '2.8.0', H), ('langgraph', '1.2.18', H)])
        problems = vd.verify(self.root)
        self.assertEqual([p['verrou'] for p in problems], ['jarvis/locks/windows-cp312-voice.txt'])

    def test_requirement_change_makes_the_lock_stale(self):
        self.good_locks()
        self.write('jarvis/requirements-orchestration.txt', 'langgraph==1.2.19\n')
        details = ' '.join(p['detail'] for p in vd.verify(self.root))
        self.assertIn('Verrou périmé', details)
        self.assertIn('langgraph==1.2.19', details)

    def test_entry_without_hash_is_reported(self):
        self.lock('moteurs', [('cadquery', '2.8.0', H), ('langgraph', '1.2.18', None)])
        self.lock('voice', [('faster-whisper', '1.2.1', H)])
        self.assertIn('Sans empreinte : langgraph.', [p['detail'] for p in vd.verify(self.root)])


class InstallCommands(LockFixture):
    def test_windows_installs_the_hashed_lock_then_checks(self):
        self.good_locks()
        reqs = [self.root / 'jarvis/requirements.txt', self.root / 'jarvis/requirements-voice.txt']
        commands, notes = prepare.install_commands('py', reqs, os_name='nt', root=self.root)
        self.assertEqual(notes, [])
        self.assertEqual([c[3:6] for c in commands[:2]], [['install', '--require-hashes', '--no-deps']] * 2)
        self.assertTrue(commands[0][-1].endswith('windows-cp312-moteurs.txt'))
        self.assertEqual(commands[-1][-2:], ['pip', 'check'])

    def test_stale_lock_falls_back_visibly(self):
        self.good_locks()
        self.write('jarvis/requirements-voice.txt', 'faster-whisper==1.2.2\n')
        commands, notes = prepare.install_commands('py', [self.root / 'jarvis/requirements-voice.txt'], os_name='nt', root=self.root)
        self.assertEqual(len(notes), 1)
        self.assertNotIn('--require-hashes', commands[0])

    def test_other_systems_keep_the_pinned_requirements(self):
        commands, notes = prepare.install_commands('python', [self.root / 'jarvis/requirements.txt'], os_name='posix', root=self.root)
        self.assertEqual((len(commands), notes), (1, []))
        self.assertNotIn('--no-deps', commands[0])


if __name__ == '__main__':
    unittest.main()
