"""Contrats du banc de pré-installation : détection réelle des défauts, sans faux positifs connus."""
import ast
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'jarvis/apps/jarvis/app'))

from bojart_ops import banc_statique as st  # noqa: E402
from bojart_ops import banc_simulation as bs  # noqa: E402


class Fixture:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
        return name

    def close(self):
        self.tmp.cleanup()


class StaticChecks(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)

    def test_windows_path_hazards(self):
        files = ['docs/CON.md', 'a/b:c.txt', 'a/fin.', 'Doc/A.md', 'doc/a.md', 'x/' + 'n' * 210 + '.md', 'ok/fichier.md']
        found = {(f['path'], f['severity']) for f in st.check_windows_paths(files)}
        self.assertIn(('docs/CON.md', 'bloquant'), found)
        self.assertIn(('a/b:c.txt', 'bloquant'), found)
        self.assertIn(('a/fin.', 'bloquant'), found)
        self.assertIn(('doc/a.md', 'bloquant'), found)
        self.assertTrue(any(p.startswith('x/') and s == 'majeur' for p, s in found))
        self.assertFalse(any(p == 'ok/fichier.md' for p, _ in found))

    def test_cmd_line_endings_labels_and_utf8_mode(self):
        lf = self.fx.write('a.cmd', '@echo off\ncall :x\nexit /b\n:x\npy -3.12 tools\\t.py\n')
        crlf = self.fx.write('b.cmd', '@echo off\r\nset PYTHONUTF8=1\r\npy -3.12 tools\\t.py\r\n')
        accent = self.fx.write('c.cmd', '@echo off\r\necho Installation terminée\r\n')
        found = st.check_cmd_scripts([lf, crlf, accent], self.fx.root)
        by = {(f['path'], f['severity'], f['detail'][:20]) for f in found}
        self.assertTrue(any(p == 'a.cmd' and s == 'majeur' and 'étiquettes' in f['detail'] for f in found for p, s in [(f['path'], f['severity'])]))
        self.assertTrue(any(f['path'] == 'a.cmd' and 'PYTHONUTF8' in f['detail'] for f in found))
        self.assertFalse(any(f['path'] == 'b.cmd' for f in found), by)
        self.assertTrue(any(f['path'] == 'c.cmd' and 'ASCII' in f['detail'] for f in found))

    def test_text_io_without_encoding_is_detected_and_safe_forms_are_not(self):
        code = '\n'.join([
            "from pathlib import Path", "import subprocess",
            "Path('a').read_text()",                       # 3 risky
            "Path('a').read_text('utf-8')",                # positional: safe
            "Path('a').write_text('é', encoding='utf-8')", # safe
            "open('a')",                                   # 6 risky
            "open('a', 'rb')",                             # binary: safe
            "open('a', 'w', encoding='utf-8')",            # safe
            "subprocess.run(['x'], text=True)",            # 9 risky
            "subprocess.run(['x'], text=True, encoding='utf-8')",
        ])
        hits = st._text_io_calls(ast.parse(code))
        self.assertEqual([line for line, _ in hits], [3, 6, 9])

    def test_json_duplicate_keys_bom_and_nan_are_corruption(self):
        names = [self.fx.write('a.json', '{"a": 1, "a": 2}'), self.fx.write('b.json', '﻿{"a": 1}'),
                 self.fx.write('c.jsonl', '{"a": 1}\n{"b": NaN}\n'), self.fx.write('d.json', '{"ok": "é"}')]
        found = {f['path'] for f in st.check_json(names, self.fx.root)}
        self.assertEqual(found, {'a.json', 'b.json', 'c.jsonl'})

    def test_missing_es_module_and_import_map_resolution(self):
        # Import-map targets resolve against the HTML document, not the importing module.
        self.fx.write('site/index.html', '<script type="importmap">{"imports":{"three":"./vendor/three.module.js"}}</script>'
                                         '<script type="module" src="./lib/app.js"></script>')
        self.fx.write('site/vendor/three.module.js', "import {A} from './three.core.js';export {A};")
        self.fx.write('site/lib/app.js', "import * as THREE from 'three';\nimport {x} from './util.js';\n// import {y} from './commentaire.js'\n")
        self.fx.write('site/lib/util.js', 'export const x=1;')
        files = ['site/index.html', 'site/vendor/three.module.js', 'site/lib/app.js', 'site/lib/util.js']
        found = st.check_web_references(files, self.fx.root)
        self.assertEqual([(f['path'], f['severity']) for f in found], [('site/vendor/three.module.js', 'bloquant')])
        self.assertIn('three.core.js', found[0]['detail'])
        self.fx.write('site/vendor/three.core.js', 'export const A=1;')
        self.assertEqual(st.check_web_references(files + ['site/vendor/three.core.js'], self.fx.root), [])

    def test_conflicting_pins_across_requirement_files(self):
        a = self.fx.write('jarvis/apps/jarvis/requirements.txt', 'cadquery==2.8.0\ntrimesh==4.11.1\n')
        b = self.fx.write('jarvis/requirements-figurine.txt', '# commentaire\nTrimesh==5.2.0\nnumpy==2.5.3\n')
        c = self.fx.write('jarvis/requirements-voice.txt', 'faster-whisper==1.2.1\n')
        found = st.check_requirement_pins([a, b, c], self.fx.root)
        self.assertEqual([f['path'] for f in found], ['trimesh'])
        self.assertIn('4.11.1', found[0]['detail'])
        self.assertIn('5.2.0', found[0]['detail'])
        self.assertEqual(st.check_requirement_pins(st.tracked_files(ROOT), ROOT), [])

    def test_current_atelier_three_core_dependency_is_present(self):
        files = st.tracked_files(ROOT)
        found = [f for f in st.check_web_references(files, ROOT) if 'three.core' in f['detail'] or f['severity'] == 'bloquant']
        self.assertEqual(found, [])


class SuiteParsing(unittest.TestCase):
    OUTPUT = '\n'.join([
        'ERROR: test_full_snapshot_reopens_with_all_work_and_relative_media (test_workspace_m05.WorkspaceTests.test_full_snapshot_reopens_with_all_work_and_relative_media)',
        'FAIL: test_nouveau (test_jarvis_m07.M07Tests.test_nouveau)',
        'ERROR: setUpClass (test_studio_http.HTTPTests)',
        '----------------------------------------------------------------------',
        'Ran 280 tests in 13.7s', '', 'FAILED (failures=1, errors=2, skipped=1)'])

    def test_counts_and_failing_tests(self):
        counts, failing, verdict = bs.parse_unittest(self.OUTPUT)
        self.assertEqual(verdict, 'FAILED')
        self.assertEqual((counts['tests'], counts['failures'], counts['errors'], counts['skipped']), (280, 1, 2, 1))
        self.assertEqual(len(failing), 3)

    def test_precondition_failures_are_not_hidden_regressions(self):
        _, failing, _ = bs.parse_unittest(self.OUTPUT)
        explained, regressions = bs.classify_failures(failing)
        self.assertEqual([r['test'] for r in regressions], ['test_jarvis_m07.M07Tests.test_nouveau'])
        if not (bs.STUDIO_MEDIA.is_dir() and any(bs.STUDIO_MEDIA.iterdir())):
            self.assertEqual({e['cause'] for e in explained}, {'medias_m07'})
        else:  # media present: the same failures become regressions
            self.assertEqual(explained, [])

    def test_ok_with_skips(self):
        counts, failing, verdict = bs.parse_unittest('Ran 41 tests in 0.03s\n\nOK (skipped=2)\n')
        self.assertEqual((verdict, counts['tests'], counts['skipped'], failing), ('OK', 41, 2, []))

    def test_failure_keeps_the_exception_line(self):
        sep, dash = '=' * 70, '-' * 70
        output = '\n'.join([
            sep, 'ERROR: test_success (test_archive_restore.RestoreArchiveTests.test_success)', dash,
            'Traceback (most recent call last):', '  File "x.py", line 1, in ensure_inside',
            '    raise ValueError("Unsafe archive path")', 'ValueError: Unsafe archive path', '',
            sep, 'FAIL: test_move (test_media_library.MediaTests.test_move)', dash,
            'Traceback (most recent call last):', "AssertionError: WindowsPath('C:/a') != WindowsPath('C:/b')", '',
            dash, 'Ran 2 tests in 0.1s', '', 'FAILED (failures=1, errors=1)'])
        _, failing, _ = bs.parse_unittest(output)
        self.assertEqual([f['erreur'] for f in failing],
                         ['ValueError: Unsafe archive path', "AssertionError: WindowsPath('C:/a') != WindowsPath('C:/b')"])

    def test_failure_already_present_in_utf8_is_not_blamed_on_cp1252(self):
        suite = {'status': 'echec', 'regressions': [{'kind': 'ERROR', 'test': 'a.A.test_path'}, {'kind': 'FAIL', 'test': 'b.B.test_accent'}]}
        out = bs.separate_utf8_failures(dict(suite), {'a.A.test_path'})
        self.assertEqual(([r['test'] for r in out['regressions']], out['status']), (['b.B.test_accent'], 'echec'))
        only_baseline = bs.separate_utf8_failures({'status': 'echec', 'regressions': [{'kind': 'ERROR', 'test': 'a.A.test_path'}]},
                                                  {'a.A.test_path'})
        self.assertEqual((only_baseline['regressions'], only_baseline['status']), ([], 'partiel'))
        self.assertEqual(only_baseline['echecs_aussi_en_utf8'][0]['test'], 'a.A.test_path')


class Catalogue(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(bs.CATALOG.read_text(encoding='utf-8'))

    def test_every_verification_names_an_existing_check(self):
        from bojart_ops import banc_http
        from launch_readiness import REQUIRED_GATES
        known = {'suite:' + s[0] for s in bs.SUITES} | {'suite:node_jarvis'}
        known |= {'outil:' + t for t in ('simulation_workflows', 'validate_repository', 'evaluate_memory', 'check_startup_abrupt',
                                            'installation_tout_simulation', 'collecte_simulation')}
        known |= {'statique:' + c for c in st.CHECKS} | {'http:' + name for name, _ in banc_http.SCENARIOS}
        known |= {'encodage:cp1252', 'reseau:roues_windows'}
        ids = [a['id'] for a in self.catalog['actions']]
        self.assertEqual(len(ids), len(set(ids)))
        for action in self.catalog['actions']:
            self.assertLessEqual(set(action['verifications']), known, action['id'])
            self.assertIn(action['etat_code'], {'code', 'partiel', 'absent'})
            self.assertTrue(action['porte_reelle'] is None or action['porte_reelle'] in REQUIRED_GATES, action['id'])
            if action['etat_code'] == 'absent':
                self.assertTrue(action.get('note'), action['id'])

    def test_status_never_promotes_missing_or_failed_checks(self):
        results = {'suites': [{'id': 'tests', 'status': 'ok'}, {'id': 'tests_workflows', 'status': 'echec'}],
                   'http': [{'id': 'http_dashboard_atelier', 'status': 'ok_reserve', 'mesures': {'reserve': 'x'}}],
                   'outils': [], 'statique': {}}
        statuses = {a['id']: a for a in bs.evaluate_catalog(results)}
        self.assertEqual(statuses['ecrans.dashboard_atelier']['statut_banc'], 'echec')      # tests_workflows failed
        self.assertEqual(statuses['demarrage.securite_locale']['statut_banc'], 'partiel')   # checks not executed
        self.assertEqual(statuses['devis.calcul']['statut_banc'], 'non_code')
        results['suites'].append({'id': 'tests_agent', 'status': 'ok'})
        self.assertEqual({a['id']: a for a in bs.evaluate_catalog(results)}['memoire.llm_local']['statut_banc'], 'partiel')
        self.assertEqual(statuses['ecrans.dashboard_atelier']['reserves'], ['http_dashboard_atelier'])
        for action in statuses.values():
            self.assertEqual(action['qualification_reelle'], 'à faire sur la tour')


class Report(unittest.TestCase):
    def test_existing_report_is_never_overwritten(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import banc_preinstallation
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'r.json'
            target.write_text('original', encoding='utf-8')
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                banc_preinstallation.main(['--output', str(target), '--sans-suites', '--sans-http', '--sans-outils'])
            self.assertEqual(target.read_text(encoding='utf-8'), 'original')

    def test_markdown_keeps_simulation_limits_visible(self):
        results = {'debut': '2026-11-02T00:00:00+00:00', 'depot': {'sha': 'abc', 'branche': 'b', 'modifications_locales': False},
                   'environnement': {'os': 'Linux', 'python_teste': 'py', 'langgraph': True, 'cadquery': False},
                   'perimetre': 'Simulation logicielle uniquement.', 'actions': bs.evaluate_catalog({}), 'constats': []}
        results['synthese'] = bs.summarize(results)
        text = bs.markdown(results)
        self.assertIn('Simulation logicielle uniquement.', text)
        self.assertIn('ne qualifie ni la tour', text)
        self.assertRegex(text, re.compile(r'Devis .* Non codé', re.S))


if __name__ == '__main__':
    unittest.main()
