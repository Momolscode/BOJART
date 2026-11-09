"""Débrief de la tour vers GitHub : ce qui part, ce qui est retiré, et où la poussée a le droit d'aller.

Tout se joue sur un faux dépôt distant local : aucun réseau, aucun compte. Le vrai contrôle du dépôt
(secrets, binaires, tailles) est exercé de bout en bout par « tools/publier_debrief.py essai », que le banc lance.
"""
from datetime import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bojart_ops import debrief_tour as dt  # noqa: E402
from bojart_ops import voix_installation as vi  # noqa: E402

SPEC = importlib.util.spec_from_file_location('publier_debrief', ROOT / 'tools/publier_debrief.py')
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)

GIT = dt.find_git()
STAMP = datetime(2026, 11, 9, 12, 0, 0)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='bojart-test-debrief-')).resolve()
        self.addCleanup(self.cleanup)
        self.home = self.tmp / 'Users' / 'Camille Exemple'
        self.env = {'USERPROFILE': str(self.home), 'USERNAME': 'Camille Exemple', 'COMPUTERNAME': 'TOUR-ESSAI'}
        self.base = self.home / 'BOJART'

    def cleanup(self):
        def writable(func, path, _):  # Git objects are read-only under Windows
            os.chmod(path, 0o700)
            func(path)
        shutil.rmtree(self.tmp, onerror=writable)

    def report(self, rel, text='{}', mtime=None):
        path = self.base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text if isinstance(text, bytes) else text.encode('utf-8'))
        if mtime:
            os.utime(path, (mtime, mtime))
        return path


class Collect(Base):
    def test_only_the_latest_text_reports_of_known_folders_are_kept(self):
        self.report('banc/banc-1.json', mtime=1_000)
        self.report('banc/banc-1.md', '# ancien', mtime=1_000)
        self.report('banc/banc-2.json', mtime=2_000)
        self.report('banc/banc-2.md', '# récent', mtime=2_000)
        self.report('banc/banc-2.png', b'\x89PNG', mtime=2_000)
        self.report('banc/banc-2.txt', 'x' * (dt.MAX_BYTES + 1), mtime=2_000)
        self.report('installation/installation-20261109-000000.json')
        self.report('diagnostics/20261109-abcd.json')            # only on request
        self.report('collecte/collecte.sqlite', b'SQLite')        # never a known folder
        self.report('memoire/notes.md', 'privé')
        kept, aside = dt.collect(self.home)
        self.assertEqual(sorted((k['famille'], k['nom']) for k in kept),
                         [('banc', 'banc-2.json'), ('banc', 'banc-2.md'), ('installation', 'installation-20261109-000000.json')])
        self.assertEqual({a['fichier'] for a in aside}, {'banc-2.png', 'banc-2.txt'})
        with_diag, _ = dt.collect(self.home, dt.DEFAULT_FAMILIES + ('diagnostic',))
        self.assertIn('20261109-abcd.json', [k['nom'] for k in with_diag])

    @unittest.skipIf(os.name == 'nt', 'creating a link needs a privilege under Windows')
    def test_a_link_is_never_followed(self):
        secret = self.tmp / 'ailleurs.json'
        secret.write_text('{"cle": "hors du dossier"}', encoding='utf-8')
        (self.base / 'banc').mkdir(parents=True)
        (self.base / 'banc/banc-9.json').symlink_to(secret)
        kept, aside = dt.collect(self.home)
        self.assertEqual(kept, [])
        self.assertEqual(aside, [{'fichier': 'banc-9.json', 'raison': 'lien symbolique'}])

    def test_no_report_refuses_instead_of_pushing_an_empty_debrief(self):
        with self.assertRaises(dt.Refused):
            dt.prepare([], self.home, self.env, 'TOUR-ESSAI')


class Sanitize(Base):
    def clean(self, text, **env):
        return dt.sanitize(text, self.home, {**self.env, **env}, 'TOUR-ESSAI', root=self.tmp / 'Disque D' / 'BOJART')[0]

    def test_home_session_host_and_mail_leave_in_every_spelling(self):
        home = str(self.home)
        for spelling in (home, home.replace('\\', '/'), home.replace('/', '\\'), json.dumps(home.replace('/', '\\'))[1:-1]):
            out = self.clean(f'python : {spelling}/BOJART/.venv ; poste TOUR-ESSAI ; tour-essai.local')
            self.assertNotIn('Camille', out, spelling)
            self.assertNotIn('TOUR-ESSAI', out.upper().replace('<POSTE>', ''), spelling)
            self.assertIn('~', out)
        out = self.clean(r'C:\Users\Camille Exemple\AppData\Local et /home/Camille Exemple/x ; écrire à camille.exemple+atelier@exemple.fr')
        self.assertNotIn('Camille', out)
        self.assertNotIn('exemple.fr', out)
        self.assertIn('<session>', out)
        self.assertIn('<courriel>', out)

    def test_the_installation_folder_leaves_wherever_it_sits(self):
        root = self.tmp / 'Disque D' / 'BOJART'
        out = self.clean(json.dumps({'python_teste': str(root / '.venv' / 'python.exe'), 'autre': str(root) + '-ancien'}))
        self.assertEqual(json.loads(out)['python_teste'].replace('\\', '/'), '<projet>/.venv/python.exe')
        self.assertNotIn('<projet>-ancien', out)  # the neighbouring folder is another place

    def test_ordinary_text_is_left_alone(self):
        text = 'Détour par la tourelle : 1 148 tests, 16/16 scénarios, modèle small@536b0662, C:\\Users\\Public\\x'
        self.assertEqual(dt.sanitize(text, self.home, self.env, 'TOUR-ESSAI'), (text, 0))
        # A short machine or account name would rewrite ordinary words: left alone rather than guessed.
        self.assertEqual(dt.sanitize('PC de test, session a', self.home, {'USERNAME': 'a', 'COMPUTERNAME': 'PC'}, 'PC')[0], 'PC de test, session a')

    def test_a_longer_folder_name_is_not_cut_in_the_middle(self):
        out = self.clean(str(self.home) + '-sauvegarde/x')
        self.assertNotIn('~-sauvegarde', out)       # another folder, not the home
        self.assertIn('<session>-sauvegarde', out)  # yet the account name it carries does not leave
        self.assertNotIn('Camille', out)
        self.assertIn('Camille Exempleaire', self.clean(str(self.home) + 'aire/x'))  # another name: not rewritten by halves

    def test_prepare_publishes_clean_copies_and_says_what_stayed(self):
        self.report('installation/installation-20261109-000000.json', json.dumps({
            'journal': str(self.base / 'installation'), 'poste': 'TOUR-ESSAI', 'synthese': {'termine': False, 'reste_a_faire': ['Git (echec)']}}))
        self.report('banc/banc-1.json', json.dumps({'synthese': {'tests_executes': 1148, 'scenarios_http': {'ok': 16}}}))
        self.report('banc/banc-1.md', b'# Banc\r\n\r\nLatin-1 : \xe9\r\n')   # not UTF-8: stays on the tower
        kept, aside = dt.collect(self.home)
        folder, files, refused = dt.prepare(kept, self.home, self.env, 'TOUR-ESSAI', note=f'essai  depuis\n{self.home}', stamp=STAMP, aside=aside)
        self.assertEqual(folder, 'docs/evidence/tour-2026-11-09-120000')
        self.assertEqual(sorted(files), [f'{folder}/README.md', f'{folder}/banc/banc-1.json', f'{folder}/installation/installation-20261109-000000.json'])
        self.assertEqual([r['fichier'] for r in refused], ['banc-1.md'])
        everything = ''.join(files.values())
        for private in ('Camille', 'TOUR-ESSAI', str(self.tmp)):
            self.assertNotIn(private, everything)
        readme = files[f'{folder}/README.md']
        self.assertIn('Note de l’opérateur : essai depuis ~', readme)
        self.assertIn('installation incomplète : Git (echec)', readme)
        self.assertIn('1148 tests ; scénarios HTTP : ok 16 ; actions : aucun', readme)
        self.assertIn('`banc-1.md` : pas du texte UTF-8', readme)
        self.assertIn('ni réception, ni décision', ' '.join(readme.split()))


class Destination(unittest.TestCase):
    def test_only_the_approved_repository_is_a_destination(self):
        for url in ('https://github.com/Momolscode/BOJART.git', 'https://github.com/momolscode/bojart', 'https://github.com/Momolscode/BOJART/',
                    'https://quelquun@github.com/Momolscode/BOJART.git', 'git@github.com:Momolscode/BOJART.git',
                    'ssh://git@github.com/Momolscode/BOJART.git', 'ssh://git@github.com:22/Momolscode/BOJART'):
            self.assertTrue(dt.approved_url(url), url)
        for url in ('https://github.com/Autre/BOJART.git', 'https://github.com/Momolscode/BOJART-jarvis.git',
                    'https://github.com.exemple.invalid/Momolscode/BOJART.git', 'https://exemple.invalid/github.com/Momolscode/BOJART',
                    'git@gitlab.com:Momolscode/BOJART.git', 'https://github.com/Momolscode/BOJART.git/../../Autre/depot',
                    '/tmp/github.com/momolscode/bojart', r'C:\depots\BOJART', '', 'github.com/momolscode/bojart.git'):
            self.assertFalse(dt.approved_url(url), url)


@unittest.skipUnless(GIT, 'Git absent')
class Publish(Base):
    def setUp(self):
        super().setUp()
        seed, self.origin, self.clone = self.tmp / 'graine', self.tmp / 'github' / 'BOJART.git', self.tmp / 'tour' / 'BOJART'
        (seed / 'data/catalog').mkdir(parents=True)
        (seed / dt.MANIFEST).write_text('{}\n', encoding='utf-8')
        (seed / 'README.md').write_text('# BOJART\n', encoding='utf-8')
        self.git(['init', '-q', '-b', 'main'], seed)
        self.git(['add', '-A'], seed)
        self.git(['-c', 'user.name=essai', '-c', 'user.email=essai@exemple.invalid', 'commit', '-q', '--no-gpg-sign', '-m', 'graine'], seed)
        self.origin.parent.mkdir(parents=True)
        self.git(['clone', '-q', '--bare', str(seed), str(self.origin)], self.tmp)
        self.git(['clone', '-q', str(self.origin), str(self.clone)], self.tmp)
        self.approved = self.git(['remote', 'get-url', 'origin'], self.clone).strip()  # the name Git gives the fake remote
        self.folder = 'docs/evidence/tour-2026-11-09-120000'
        self.files = {f'{self.folder}/README.md': '# Débrief\n', f'{self.folder}/banc/banc-1.json': '{"ok": true}\n'}
        self.validated, self.commands = [], []

    def git(self, args, cwd):
        return subprocess.run([str(GIT), *args], cwd=str(cwd), capture_output=True, text=True, encoding='utf-8', errors='replace', check=True).stdout

    def validate(self, tree):
        self.validated.append(sorted(p.relative_to(tree).as_posix() for p in Path(tree).rglob('*') if p.is_file() and '.git' not in p.parts))
        (Path(tree) / dt.MANIFEST).write_text('{"fichiers": 3}\n', encoding='utf-8')  # the real gate rewrites the manifest
        return []

    def publish(self, files=None, stamp=STAMP, **over):
        def run(command, **kw):
            self.commands.append(command[1:])
            return subprocess.run(command, **kw)
        options = dict(clone=self.clone, git=GIT, approved=self.approved, validate=self.validate, out=lambda *_: None, run=run)
        return dt.publish(self.files if files is None else files, self.folder, stamp=stamp, **{**options, **over})

    def heads(self):
        return self.git(['for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads'], self.origin)

    def test_a_new_branch_carries_the_folder_and_the_manifest_and_nothing_else_moves(self):
        main = self.git(['rev-parse', 'refs/heads/main'], self.origin)
        head, status = self.git(['rev-parse', 'HEAD'], self.clone), self.git(['status', '--porcelain'], self.clone)
        result = self.publish()
        self.assertEqual(result['branche'], 'tour/debrief-20261109-120000')
        self.assertTrue(result['pousse'])
        self.assertTrue(result['voir'].endswith('/tree/tour/debrief-20261109-120000/' + self.folder))
        self.assertEqual(self.git(['rev-parse', 'refs/heads/main'], self.origin), main)
        self.assertEqual(self.git(['diff', '--name-only', 'main', result['branche']], self.origin).split(), sorted([dt.MANIFEST, *self.files]))
        self.assertEqual(self.git(['show', f'{result["branche"]}:{self.folder}/banc/banc-1.json'], self.origin), '{"ok": true}\n')
        self.assertEqual(self.git(['log', '-1', '--format=%an <%ae>|%cn <%ce>', result['branche']], self.origin).strip(),
                         'Jarvis BOJ.ART (tour) <jarvis@tour.invalid>|Jarvis BOJ.ART (tour) <jarvis@tour.invalid>')
        self.assertEqual(self.git(['rev-list', '--count', f'main..{result["branche"]}'], self.origin).strip(), '1')
        # The tower's own working copy is not the place where the commit is made.
        self.assertEqual((self.git(['rev-parse', 'HEAD'], self.clone), self.git(['status', '--porcelain'], self.clone)), (head, status))
        self.assertEqual(self.git(['worktree', 'list', '--porcelain'], self.clone).count('worktree '), 1)
        self.assertEqual(self.validated, [sorted(['README.md', dt.MANIFEST, *self.files])])
        # One push, of that commit, to that new branch: no force, no other reference.
        self.assertEqual([c for c in self.commands if c[0] == 'push'], [['push', 'origin', f'{result["commit"]}:refs/heads/{result["branche"]}']])

    def test_simulation_prepares_and_checks_but_pushes_nothing(self):
        before = self.heads()
        result = self.publish(push=False)
        self.assertFalse(result['pousse'])
        self.assertNotIn('voir', result)
        self.assertEqual(self.heads(), before)
        self.assertEqual(len(self.validated), 1)

    def test_the_repository_gate_decides(self):
        before = self.heads()
        with self.assertRaises(dt.Refused) as refused:
            self.publish(validate=lambda tree: [{'path': 'x', 'error': 'possible_secret'}])
        self.assertIn('possible_secret', str(refused.exception))
        self.assertEqual(self.heads(), before)
        self.assertEqual(self.git(['worktree', 'list', '--porcelain'], self.clone).count('worktree '), 1)

    def test_never_main_never_an_existing_branch_never_another_repository(self):
        self.publish()
        before = self.heads()
        with self.assertRaises(dt.Refused):  # same second: the branch exists
            self.publish()
        with self.assertRaises(dt.Refused):  # the clone points elsewhere than the approved repository
            self.publish(stamp=datetime(2026, 11, 9, 12, 0, 1), approved=dt.APPROVED)
        with self.assertRaises(dt.Refused):  # a file outside the debrief folder
            self.publish({**self.files, 'README.md': 'écrasé'}, stamp=datetime(2026, 11, 9, 12, 0, 2))
        for escape in (f'{self.folder}/../../../sortie.md', f'{self.folder}/../../../../../sortie.md', f'{self.folder}/a\\..\\b.md'):
            with self.assertRaises(dt.Refused):
                self.publish({**self.files, escape: 'x'}, stamp=datetime(2026, 11, 9, 12, 0, 3))
        self.assertFalse(list(self.tmp.rglob('sortie.md')))
        with self.assertRaises(dt.Refused):  # the gate touched something else than the manifest
            self.publish(stamp=datetime(2026, 11, 9, 12, 0, 4), validate=lambda tree: (Path(tree) / 'README.md').write_text('x') and [])
        self.assertEqual(self.heads(), before)
        self.assertEqual(len([c for c in self.commands if c[0] == 'push']), 1)  # the first publication, and no other

    def test_the_installation_folder_is_used_only_when_it_is_the_approved_clone(self):
        said = []
        self.assertEqual(dt.find_clone(self.clone, self.home, git=GIT, approved=self.approved, out=said.append), self.clone)
        # A « Download ZIP » copy has no .git: a dedicated bare clone is made once, then reused.
        plain = self.tmp / 'copie-zip'
        plain.mkdir()
        made = dt.find_clone(plain, self.home, git=GIT, approved=self.approved, remote_url=self.approved, out=said.append)
        self.assertEqual(made, self.home / 'BOJART' / 'depot-github' / 'BOJART.git')
        self.assertEqual(len(said), 1)
        self.assertEqual(dt.find_clone(plain, self.home, git=GIT, approved=self.approved, remote_url=self.approved, out=said.append), made)
        self.assertEqual(len(said), 1)
        self.assertTrue(self.publish(clone=made, stamp=datetime(2026, 11, 9, 12, 0, 5))['pousse'])
        # A clone of something else is not trusted, wherever it sits.
        with self.assertRaises(dt.Refused):
            dt.find_clone(plain, self.home, git=GIT, approved=dt.APPROVED, out=said.append)


class Cli(Base):
    def run_cli(self, argv, answers=(), tty=True, **patches):
        self.report('banc/banc-1.json', json.dumps({'synthese': {'tests_executes': 3}}))
        stdin = mock.Mock(isatty=lambda: tty)
        published = mock.Mock(return_value={'pousse': '--simulation' not in argv, 'voir': 'https://exemple.invalid/voir'})
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, self.env), mock.patch.object(cli.dt, 'find_git', return_value=patches.get('git', Path('git'))), \
             mock.patch.object(cli.dt, 'find_clone', return_value=self.tmp), mock.patch.object(cli.dt, 'publish', published), \
             mock.patch.object(sys, 'stdin', stdin), mock.patch('builtins.input', side_effect=list(answers)), \
             redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, published, out.getvalue() + err.getvalue()

    def test_the_operator_sees_the_list_and_can_say_no(self):
        code, published, text = self.run_cli([], answers=['', 'n'])
        self.assertEqual(code, 1)
        published.assert_not_called()
        self.assertIn('banc-1.json', text)
        self.assertIn('PUBLIC', text)
        self.assertIn('Rien n’a été poussé.', text)

    def test_yes_publishes_with_the_typed_note(self):
        code, published, _ = self.run_cli([], answers=['micro OK', 'o'])
        self.assertEqual(code, 0)
        files = published.call_args.args[0]
        self.assertIn('Note de l’opérateur : micro OK', next(v for k, v in files.items() if k.endswith('README.md')))
        self.assertTrue(published.call_args.kwargs['push'])

    def test_without_a_console_nothing_is_pushed_unless_agreed_in_advance(self):
        code, published, text = self.run_cli([], tty=False)
        self.assertEqual(code, 2)
        published.assert_not_called()
        self.assertIn('Accord requis', text)
        code, published, _ = self.run_cli(['--oui', '--note', 'accord donné'], tty=False)
        self.assertEqual(code, 0)
        published.assert_called_once()

    def test_simulation_never_pushes(self):
        code, published, text = self.run_cli(['--simulation'], tty=False)
        self.assertEqual(code, 0)
        self.assertFalse(published.call_args.kwargs['push'])
        self.assertIn('rien n’a été poussé', text)

    def test_without_git_the_operator_is_told_how_to_get_it(self):
        code, published, text = self.run_cli(['--oui'], git=None)
        self.assertEqual(code, 2)
        published.assert_not_called()
        self.assertIn('Installer_Tout_BOJART.cmd', text)

    def test_a_refused_connection_gets_a_plain_hint(self):
        self.assertIn('Git Bash', cli.hint('git push a échoué : fatal: could not read Username for https://github.com: terminal prompts disabled'))
        self.assertIn('Internet', cli.hint('git fetch a échoué : fatal: unable to access … Could not resolve host: github.com'))
        self.assertIsNone(cli.hint('Le contrôle du dépôt refuse ce débrief'))


class Launchers(unittest.TestCase):
    def test_launcher_is_ascii_crlf_and_calls_the_tool(self):
        raw = (ROOT / 'Publier_Debrief_BOJART.cmd').read_bytes()
        raw.decode('ascii')
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        self.assertIn(b'tools\\publier_debrief.py %*', raw)
        self.assertIn(b'set PYTHONUTF8=1', raw)
        self.assertIn(b'pause', raw)

    def test_voice_measure_reuses_the_weights_the_installer_put_in_place(self):
        raw = (ROOT / 'Mesurer_Voix_BOJART.cmd').read_bytes().decode('ascii')
        self.assertIn('%USERPROFILE%\\BOJART\\modeles\\voix\\' + vi.target_dir('small').name, raw)
        self.assertNotIn('\n', raw.replace('\r\n', ''))


if __name__ == '__main__':
    unittest.main()
