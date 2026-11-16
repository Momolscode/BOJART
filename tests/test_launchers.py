"""Run the actual entry scripts against isolated Python routing probes.

The probes exercise interpreter selection, quoting, arguments and exit status.
The full HTTP launcher/restart acceptance remains in tools/check_startup.py.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    'Lancer_BOJART',
    'jarvis/Lancer_Jarvis',
    'jarvis/Ouvrir_un_dossier_Jarvis',
    'jarvis/Restaurer_Jarvis',
    'jarvis/apps/jarvis/Lancer_Jarvis',
]
PROBE = '''import json, os, sys
print('BOJART_TEST_RESULT=' + json.dumps({
    'target': TARGET, 'arguments': sys.argv[1:], 'prefix': sys.prefix,
    'cwd': os.getcwd(), 'utf8': sys.flags.utf8_mode,
}, ensure_ascii=False), flush=True)
raise SystemExit(next((int(a.split('=', 1)[1]) for a in sys.argv[1:]
                     if a.startswith('--exit-code=')), 0))
'''


class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='bojart-launchers-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)/'Dossier partagé BOJART'
        cls.other = cls.root/'autre dossier'
        cls.other.mkdir(parents=True)
        cls.suffix = '.cmd' if os.name == 'nt' else '.sh'
        for stem in SCRIPTS:
            source = ROOT/(stem+cls.suffix)
            target = cls.root/(stem+cls.suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if os.name != 'nt':
                target.chmod(0o644)  # Matches the tracked scripts and ZIP extractions.
        cls.write_probe(cls.root/'tools/start_jarvis.py', 'canonical')
        cls.write_probe(cls.root/'jarvis/apps/jarvis/app/consolidated_workbench.py', 'legacy-direct')
        cls.write_probe(cls.root/'jarvis/tools/restore_workspace.py', 'restore')
        venv.EnvBuilder(with_pip=False).create(cls.root/'.venv')

        # A separately extracted historical Jarvis package still has its fallback.
        cls.archive = Path(cls.tmp.name)/'archive autonome'
        for stem in SCRIPTS[1:]:
            relative = stem.removeprefix('jarvis/')+cls.suffix
            target = cls.archive/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/(stem+cls.suffix), target)
            if os.name != 'nt':
                target.chmod(0o644)
        cls.write_probe(cls.archive/'apps/jarvis/app/consolidated_workbench.py', 'legacy-direct')
        cls.write_probe(cls.archive/'tools/restore_workspace.py', 'restore')
        venv.EnvBuilder(with_pip=False).create(cls.archive/'.venv')

    @staticmethod
    def write_probe(path, target):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('TARGET = '+repr(target)+'\n'+PROBE, encoding='utf-8')

    def run_script(self, stem, arguments=(), *, archive=False):
        base = self.archive if archive else self.root
        script = base/(stem+self.suffix)
        work = base/'autre dossier'
        work.mkdir(exist_ok=True)
        if os.name == 'nt':
            command = [os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c',
                       os.path.relpath(script, work), *arguments]
        else:
            command = ['bash', str(script), *arguments]
        result = subprocess.run(command, cwd=work, input='',
                                env=dict(os.environ, PYTHONUTF8='1'),
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=20)
        rows = [line.partition('=')[2] for line in result.stdout.splitlines()
                if line.startswith('BOJART_TEST_RESULT=')]
        self.assertEqual(len(rows), 1, result.stdout+'\n'+result.stderr)
        return result, json.loads(rows[0])

    def assert_environment(self, probe, *, archive=False):
        expected = (self.archive if archive else self.root)/'.venv'
        self.assertEqual(os.path.normcase(os.path.normpath(probe['prefix'])),
                         os.path.normcase(str(expected)))

    def test_canonical_launcher_preserves_arguments_and_environment(self):
        args = ['--state', 'Dossier épreuve & sources', '--no-browser', '--check-only']
        result, probe = self.run_script('Lancer_BOJART', args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(probe['target'], 'canonical')
        self.assertEqual(probe['arguments'], args)
        self.assert_environment(probe)

    def test_legacy_launcher_reaches_canonical_diagnostics_and_indexing(self):
        args = ['--state', 'Dossier épreuve & sources', '--check-only']
        result, probe = self.run_script('jarvis/Lancer_Jarvis', args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(probe['target'], 'canonical')
        self.assertEqual(probe['arguments'], args)
        self.assert_environment(probe)

    def test_nested_launcher_reaches_canonical_diagnostics_and_indexing(self):
        args = ['--state', 'Espace à reprendre', '--no-browser']
        result, probe = self.run_script('jarvis/apps/jarvis/Lancer_Jarvis', args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(probe['target'], 'canonical')
        self.assertEqual(probe['arguments'], args)
        self.assert_environment(probe)

    def test_open_helper_works_with_nonexecutable_extracted_scripts(self):
        args = ['--no-browser', '--port', '0']
        result, probe = self.run_script('jarvis/Ouvrir_un_dossier_Jarvis', args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(probe['target'], 'canonical')
        self.assertEqual(probe['arguments'], ['--choose-state', *args])
        self.assert_environment(probe)

    def test_restore_uses_installed_environment_and_preserves_paths(self):
        args = ['archive épreuve.zip', 'nouveau dossier & copie']
        result, probe = self.run_script('jarvis/Restaurer_Jarvis', args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(probe['target'], 'restore')
        self.assertEqual(probe['arguments'], args)
        self.assert_environment(probe)

    def test_restore_without_arguments_opens_chooser(self):
        result, probe = self.run_script('jarvis/Restaurer_Jarvis')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(probe['arguments'], ['--choose'])
        self.assert_environment(probe)

    def test_launchers_propagate_failure(self):
        for stem in ['Lancer_BOJART', 'jarvis/Lancer_Jarvis', 'jarvis/Ouvrir_un_dossier_Jarvis',
                     'jarvis/apps/jarvis/Lancer_Jarvis']:
            with self.subTest(stem=stem):
                result, probe = self.run_script(stem, ['--exit-code=7'])
                self.assertEqual(result.returncode, 7, result.stdout+result.stderr)
                self.assertEqual(probe['target'], 'canonical')

    def test_restore_propagates_failure(self):
        result, _ = self.run_script('jarvis/Restaurer_Jarvis', ['--exit-code=7'])
        self.assertEqual(result.returncode, 7, result.stdout+result.stderr)

    def test_standalone_package_preserves_its_local_environment(self):
        for stem, target, args in [
            ('Lancer_Jarvis', 'legacy-direct', ['--state', 'dossier autonome']),
            ('apps/jarvis/Lancer_Jarvis', 'legacy-direct', ['--no-browser']),
            ('Restaurer_Jarvis', 'restore', ['sauvegarde.zip', 'copie']),
        ]:
            with self.subTest(stem=stem):
                result, probe = self.run_script(stem, args, archive=True)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertEqual(probe['target'], target)
                self.assertEqual(probe['arguments'], args)
                self.assert_environment(probe, archive=True)

    def test_standalone_scripts_preserve_failure_status(self):
        for stem in ['Lancer_Jarvis', 'apps/jarvis/Lancer_Jarvis', 'Restaurer_Jarvis']:
            with self.subTest(stem=stem):
                result, _ = self.run_script(stem, ['--exit-code=7'], archive=True)
                self.assertEqual(result.returncode, 7, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
