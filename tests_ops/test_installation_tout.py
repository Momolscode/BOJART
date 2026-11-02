"""Installation complète : plan, accord, enchaînement et reprise, sans rien installer pour de vrai."""
import io
import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bojart_ops import installation_tout as it  # noqa: E402

SPEC = importlib.util.spec_from_file_location('installer_tout', ROOT / 'tools/installer_tout.py')
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def state(**over):
    base = {'systeme': 'windows', 'python': '3.12.10', 'python_312': True, 'winget': r'C:\winget.exe', 'ollama': None,
            'ollama_actif': None, 'ffmpeg': None, 'venv': False, 'verrous_windows': [], 'espace_libre_go': 120.0}
    base.update(over)
    return base


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()

    def steps(self, st, **kw):
        return it.plan(st, python='py312', root=Path('R'), os_name='nt', stamp='S', home=self.home, **kw)

    def journal(self, name='j.json'):
        return it.Journal(self.home / name, {'etapes': []})


class Plan(Base):
    def test_bare_tower_installs_everything_in_order(self):
        steps = self.steps(state())
        self.assertEqual([s['id'] for s in steps],
                         ['ollama_installation', 'ffmpeg_installation', 'ollama_demarrage', 'jarvis', 'modeles', 'banc'])
        self.assertEqual(steps[0]['commande'][:4], ['winget', 'install', '--id', 'Ollama.Ollama'])
        self.assertIn('Gyan.FFmpeg', steps[1]['commande'])
        self.assertEqual(steps[3]['commande'][-2:], ['--engines', '--voice'])
        self.assertEqual(steps[4]['commande'][-3:], ['--model-profile', 'speed', '--download-models'])
        self.assertTrue(steps[5]['commande'][0].endswith(str(Path('.venv/Scripts/python.exe'))))
        self.assertTrue(steps[5]['commande'][-1].endswith('banc-installation-S.md'))

    def test_present_tools_are_not_reinstalled(self):
        steps = self.steps(state(ollama='C:/o/ollama.exe', ollama_actif='0.12.6', ffmpeg='C:/f/ffmpeg.exe'))
        self.assertEqual([s['type'] for s in steps[:3]], ['present', 'present', 'demarrer_ollama'])
        self.assertFalse(any(s.get('commande', [''])[0] == 'winget' for s in steps))

    def test_without_winget_the_tools_become_manual(self):
        steps = self.steps(state(winget=None))
        self.assertEqual([s['type'] for s in steps[:2]], ['manuel', 'manuel'])

    def test_options_drop_models_voice_and_bench(self):
        steps = self.steps(state(), models=False, voice=False, bench=False)
        self.assertEqual([s['id'] for s in steps], ['ffmpeg_installation', 'jarvis'])
        self.assertNotIn('--voice', steps[1]['commande'])


class Execute(Base):
    def run_steps(self, st, codes, found=None, start=lambda exe: '0.12.6'):
        calls = []

        def run(cmd, cwd=None, env=None):
            calls.append((cmd, env))
            return SimpleNamespace(returncode=codes.get(cmd[3], 0) if cmd[0] == 'winget' else 0)
        redetect = lambda key, env: (found or {}).get(key)  # noqa: E731
        journal = self.journal()
        records = it.execute(self.steps(st), st, journal, run=run, start=start, redetect=redetect, env={'PATH': 'P'}, out=lambda *_: None)
        return records, calls, journal

    def test_everything_succeeds_and_new_tools_reach_the_children(self):
        st = state()
        records, calls, journal = self.run_steps(st, {}, found={'ollama': 'C:/O/ollama.exe', 'ffmpeg': 'C:/F/bin/ffmpeg.exe'})
        self.assertEqual({r['id']: r['statut'] for r in records},
                         dict.fromkeys(['ollama_installation', 'ffmpeg_installation', 'ollama_demarrage', 'jarvis', 'modeles', 'banc'], 'ok'))
        model_env = [env for cmd, env in calls if '--model-profile' in cmd][0]
        self.assertTrue(model_env['PATH'].startswith('C:/O' + __import__('os').pathsep + 'C:/F/bin'))
        self.assertEqual(model_env['PYTHONUTF8'], '1')
        self.assertTrue(it.summary(records)['termine'])
        saved = json.loads((self.home / 'j.json').read_text(encoding='utf-8'))
        self.assertEqual(len(saved['etapes']), 6)

    def test_failed_ollama_only_stops_the_models(self):
        records, calls, _ = self.run_steps(state(), {'Ollama.Ollama': 1}, found={'ffmpeg': 'C:/F/ffmpeg.exe'})
        status = {r['id']: r['statut'] for r in records}
        self.assertEqual(status, {'ollama_installation': 'echec', 'ffmpeg_installation': 'ok', 'ollama_demarrage': 'non_lance',
                                  'jarvis': 'ok', 'modeles': 'non_lance', 'banc': 'ok'})
        self.assertFalse(any('--model-profile' in cmd for cmd, _ in calls))
        self.assertEqual(len(it.summary(records)['reste_a_faire']), 3)

    def test_winget_non_zero_but_tool_present_counts_as_installed(self):
        records, _, _ = self.run_steps(state(), {'Gyan.FFmpeg': -1978335189},
                                       found={'ollama': 'C:/O/ollama.exe', 'ffmpeg': 'C:/F/ffmpeg.exe'})
        self.assertEqual(records[1]['statut'], 'ok')

    def test_ollama_that_never_answers_blocks_models_not_jarvis(self):
        records, _, _ = self.run_steps(state(ollama='C:/O/ollama.exe', ffmpeg='C:/F/ffmpeg.exe'), {}, start=lambda exe: None)
        status = {r['id']: r['statut'] for r in records}
        self.assertEqual((status['ollama_demarrage'], status['jarvis'], status['modeles']), ('echec', 'ok', 'non_lance'))

    def test_journal_never_overwrites(self):
        self.journal()
        with self.assertRaises(FileExistsError):
            self.journal()


class Detection(Base):
    def test_ffmpeg_from_winget_packages_is_found_without_path(self):
        exe = self.home / 'Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.0-full_build/bin/ffmpeg.exe'
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b'')
        self.assertEqual(it.find_ffmpeg({'LOCALAPPDATA': str(self.home), 'PATH': ''}, which=lambda *a, **k: None), exe)

    def test_ollama_default_location(self):
        exe = self.home / 'Programs/Ollama/ollama.exe'
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b'')
        self.assertEqual(it.find_ollama({'LOCALAPPDATA': str(self.home)}, which=lambda *a, **k: None), exe)

    def test_start_ollama_waits_for_an_answer(self):
        answers = iter([None, None, '0.12.6'])
        popen = mock.Mock()
        self.assertEqual(it.start_ollama('C:/O/ollama.exe', probe=lambda: next(answers), popen=popen, sleep=lambda s: None), '0.12.6')
        self.assertEqual(popen.call_args.args[0], ['C:/O/ollama.exe', 'serve'])


class Cli(Base):
    def test_simulation_runs_nothing_and_writes_a_new_journal(self):
        target = self.home / 'plan.json'
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('rien ne doit tourner')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('rien ne doit démarrer')), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(['--simulation', '--journal', str(target)]), 0)
        result = json.loads(out.getvalue())
        self.assertTrue(result['simulation'])
        self.assertIn('jarvis', [s['id'] for s in result['plan']])
        self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['plan'], result['plan'])

    def test_no_console_and_no_consent_installs_nothing(self):
        with mock.patch.object(it, 'execute', side_effect=AssertionError('aucune étape sans accord')), \
             mock.patch.object(sys, 'stdin', io.StringIO('o\n')), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--sans-banc']), 2)

    def test_launcher_is_ascii_crlf_and_calls_the_orchestrator(self):
        raw = (ROOT / 'Installer_Tout_BOJART.cmd').read_bytes()
        raw.decode('ascii')
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        self.assertIn(b'tools\\installer_tout.py %*', raw)
        self.assertIn(b'set PYTHONUTF8=1', raw)


if __name__ == '__main__':
    unittest.main()
