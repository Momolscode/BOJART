"""M08 — chaîne « demande → figurine → visualisation → tranchage ».

N0 : analyse de la demande, contrôles géométriques sur fixtures, découpe, reprise.
N1 : parcours intégré à basse résolution avec pannes injectées.
Aucun microphone, aucune imprimante, aucun service distant. Le cas Végéta n'est testé
que comme texte d'entrée : aucune géométrie ni image de ce personnage n'est produite.
"""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/jarvis/app'))
from figurine.spec import SpecRejected, parse_request  # noqa: E402

try:
    import manifold3d, numpy as np, scipy, skimage, trimesh  # noqa: F401,E401
    HEAVY = True
except ImportError:
    HEAVY = False
SLICER = shutil.which('prusa-slicer') is not None
VEGETA = "Jarvis, crée-moi un Végéta 3D imprimable dans une position stylée, iconique et remarquable."
SENTINELLE = "Jarvis, crée-moi la Sentinelle 3D imprimable dans une position stylée, iconique et remarquable."


class SpecTests(unittest.TestCase):
    def test_reference_request(self):
        s = parse_request(VEGETA)
        self.assertEqual(s['character']['rights'], 'third_party_licensed')
        self.assertEqual(s['geometry_source'], 'import_required')
        self.assertEqual(s['height_mm'], 200.0)
        self.assertEqual(s['field_origin']['height_mm'], 'hypothèse de simulation')
        self.assertEqual((s['process'], s['material'], s['nozzle_mm']), ('FDM', 'PLA', 0.4))
        self.assertFalse(s['asr_tested']); self.assertFalse(s['llm_used'])

    def test_size_and_pose_modification(self):
        s = parse_request("Jarvis, crée la Sentinelle 3D de 30 cm en pose de combat")
        self.assertEqual(s['height_mm'], 300.0)
        self.assertEqual(s['pose_intent'], 'combat')
        self.assertTrue(s['field_origin']['height_mm'].startswith('demande'))

    def test_one_metre_variant_requires_cut_study(self):
        s = parse_request("Jarvis, crée la Sentinelle 3D de 1 m")
        self.assertEqual(s['height_mm'], 1000.0)
        self.assertIn('découpe', s['assembly'])

    def test_ambiguous_and_misheard(self):
        with self.assertRaises(SpecRejected) as c:
            parse_request("Jarvis, crée-moi une figurine")
        self.assertEqual(c.exception.status, 'CLARIFY')
        with self.assertRaises(SpecRejected) as c:
            parse_request("Jarvis, crée-moi un végétal 3D imprimable", source='voice_transcript')
        self.assertIn('Végéta', str(c.exception)); self.assertEqual(c.exception.status, 'CLARIFY')
        with self.assertRaises(SpecRejected):
            parse_request("Jarvis, crée la Sentinelle 3D de 20 cm avec un socle de 8 cm")

    def test_physical_actions_refused(self):
        for text in ("Jarvis, imprime la Sentinelle 3D", "Jarvis, crée la Sentinelle 3D et lance l'imprimante"):
            with self.assertRaises(SpecRejected) as c:
                parse_request(text)
            self.assertEqual(c.exception.status, 'REFUSED')


class EntryPointTests(unittest.TestCase):
    def test_same_text_entry_point_as_jarvis(self):
        from dialogue import interpret
        d = interpret(SENTINELLE)
        self.assertEqual(d['intent'], 'create_figurine')
        self.assertTrue(d['requires_confirmation'])
        self.assertEqual(d['provider'], 'rules_fr')
        # Le parcours socle existant reste inchangé.
        self.assertEqual(interpret('Crée un socle de 180 mm')['intent'], 'create_base')


@unittest.skipUnless(HEAVY, 'dépendances géométriques absentes (requirements-figurine.txt)')
class GeometryTests(unittest.TestCase):
    def test_defective_fixture_is_rejected(self):
        from figurine import checks
        box = trimesh.creation.box((20, 20, 20))
        holed = trimesh.Trimesh(box.vertices, box.faces[2:], process=False)
        floating = trimesh.util.concatenate([box, trimesh.creation.icosphere(radius=3).apply_translation((40, 0, 0))])
        plate = trimesh.creation.box((40, 40, 0.4))
        r = checks.check_part(holed, 'trou')
        self.assertIn('volume non fermé', r['eliminatory'])
        r = checks.check_part(floating, 'flottant')
        self.assertTrue(any('flottant' in e for e in r['eliminatory']))
        r = checks.check_part(plate, 'plaque', thickness_samples=400)
        self.assertTrue(any('sous 0.8 mm' in e for e in r['eliminatory']), r)
        r = checks.check_part(box, 'cube', expected_height_mm=30)
        self.assertTrue(any('hauteur' in e for e in r['eliminatory']))

    def test_guarded_repair_keeps_fidelity(self):
        from figurine import fabrication
        sphere = trimesh.creation.icosphere(subdivisions=3, radius=10)
        holed = trimesh.Trimesh(sphere.vertices, sphere.faces[1:], process=False)
        rep = fabrication.guarded_repair(holed)
        self.assertTrue(rep['accepted']); self.assertTrue(rep['after']['watertight'])
        self.assertLessEqual(rep['max_surface_deviation_mm'], 0.3)
        torn = trimesh.Trimesh(sphere.vertices, sphere.faces[: len(sphere.faces) // 2], process=False)
        rep = fabrication.guarded_repair(torn)
        self.assertFalse(rep['accepted'])

    def test_keyed_assembly_and_cut_study(self):
        from figurine import checks, fabrication, sculpt
        nominal, bodies = sculpt.sculpt_figure('repos_fier', voxel=2.0, smooth_iterations=2)
        self.assertEqual(bodies, 1)
        asm = fabrication.build_assembly(nominal, 200.0)
        info = asm['info']
        self.assertNotEqual(info['pegs'][0]['diameter_mm'], info['pegs'][1]['diameter_mm'])
        self.assertTrue(checks.check_fit(asm['figurine'], asm['socle'], info)['fit_ok'])
        self.assertTrue(checks.check_stability(asm['figurine'], asm['socle'], info)['stable_static_estimate'])
        total = trimesh.util.concatenate([asm['figurine'], asm['socle']])
        self.assertAlmostEqual(total.extents[2], 200.0, delta=0.5)
        big = fabrication.build_assembly(nominal, 1000.0)['figurine']
        plan = fabrication.plan_cuts(big, (250, 210, 220))
        self.assertGreater(len(plan['pieces']), 1)
        for p in plan['pieces']:
            self.assertTrue(all(e <= b + 1e-6 for e, b in zip(sorted(p['extents_mm']), sorted((250, 210, 220)))))
        self.assertAlmostEqual(sum(p['volume_cm3'] for p in plan['pieces']), big.volume / 1000, delta=big.volume / 1000 * 0.01)

    def test_gcode_stats_parser(self):
        from figurine import slicing
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / 'x.gcode'
            g.write_text('; BOJART SIMULATION - PROFIL NON VERIFIE - NE PAS ENVOYER A UNE MACHINE\n;LAYER_CHANGE\n;Z:0.2\n'
                         'G1 X1 Y1 E0.1\n;LAYER_CHANGE\n; estimated printing time (normal mode) = 1h 2m 3s\n'
                         '; filament used [mm] = 100.5\n; total filament used [g] = 2.5\n', encoding='utf8')
            s = slicing.parse_gcode_stats(g)
        self.assertEqual(s['layer_count'], 2); self.assertEqual(s['filament_g'], 2.5)
        self.assertEqual(s['estimated_time_normal'], '1h 2m 3s'); self.assertTrue(s['forbidden_header_present'])


@unittest.skipUnless(HEAVY, 'dépendances géométriques absentes (requirements-figurine.txt)')
class PipelineFaultTests(unittest.TestCase):
    """Parcours intégré à basse résolution (voxel 2 mm) : orchestration, pas qualité."""

    def setUp(self):
        from figurine.pipeline import FigurineRun
        self.Run = FigurineRun
        self.tmp = tempfile.TemporaryDirectory(); self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_(self, text=SENTINELLE, **kw):
        kw.setdefault('voxel', 2.0); kw.setdefault('render_size', 96); kw.setdefault('render_samples', 2)
        return self.Run(text, self.out, **kw).run()

    def state(self, res):
        return json.loads((Path(res['dir']) / 'state.json').read_text(encoding='utf8'))

    def test_third_party_character_is_blocked_without_geometry(self):
        res = self.run_(VEGETA)
        self.assertEqual(res['status'], 'BLOCKED')
        st = self.state(res)
        self.assertEqual(st['steps']['geometry']['status'], 'BLOCKED')
        self.assertFalse((Path(res['dir']) / 'nominal.stl').exists())
        self.assertFalse((Path(res['dir']) / 'rendus').exists())
        self.assertEqual(st['steps']['transcription']['status'], 'NOT_TESTED')

    def test_third_party_mesh_without_provenance_is_blocked(self):
        mesh = self.out / 'fourni.stl'
        trimesh.creation.box((10, 10, 10)).export(mesh)
        res = self.run_(VEGETA, mesh=mesh)
        self.assertEqual(res['status'], 'BLOCKED')
        self.assertIn('provenance', self.state(res)['steps']['geometry']['reason'])

    def test_rejections_happen_before_any_task(self):
        for text, status in (("Jarvis, crée-moi une figurine", 'CLARIFY'), ("Jarvis, imprime la Sentinelle 3D", 'REFUSED'),
                             ("Crée un socle de 180 mm", 'NOT_FIGURINE')):
            res = self.run_(text)
            self.assertEqual(res['status'], status, text); self.assertIsNone(res['task_id'])
        self.assertEqual(list(self.out.iterdir()), [])

    def test_low_memory_blocks_instead_of_degrading(self):
        res = self.run_(faults=['low_memory'])
        self.assertEqual(res['status'], 'BLOCKED')
        self.assertIn('Mémoire insuffisante', self.state(res)['steps']['geometry']['reason'])

    def test_interruption_resume_and_missing_renderer(self):
        first = self.run_(faults=['interrupt_after:geometry', 'no_blender'])
        self.assertEqual(first['status'], 'INTERRUPTED')
        second = self.run_(faults=['no_blender'])
        self.assertEqual(second['task_id'], first['task_id'])
        st = self.state(second)
        self.assertTrue(st['steps']['geometry'].get('reused'))
        self.assertEqual(st['steps']['geometry']['attempts'], 1)  # pas de recalcul coûteux
        self.assertEqual(st['steps']['checks']['status'], 'DONE')
        self.assertEqual(st['steps']['renders']['status'], 'BLOCKED')
        self.assertEqual(second['status'], 'BLOCKED')

    def test_retry_limit(self):
        from figurine.pipeline import FigurineRun
        run = FigurineRun(SENTINELLE, self.out)
        run.dir = self.out; run.state = {'steps': {}}
        def boom():
            raise RuntimeError('panne')
        for _ in range(3):
            with self.assertRaises(RuntimeError):
                run._run_step('x', boom)
        with self.assertRaisesRegex(RuntimeError, 'trois tentatives'):
            run._run_step('x', boom)

    @unittest.skipUnless(SLICER, 'PrusaSlicer absent')
    def test_slicer_failures_are_not_successes(self):
        res = self.run_(faults=['slicer_fail'], render_size=64)
        if shutil.which('blender') is None:
            self.skipTest('Blender absent : le parcours s’arrête avant le tranchage')
        self.assertEqual(res['status'], 'FAILED')
        st = self.state(res)
        self.assertEqual(st['steps']['slicing']['status'], 'FAILED')
        self.assertNotIn('result', st['steps']['slicing'])
        res = self.run_(faults=['slicer_missing'], render_size=64)
        self.assertEqual(self.state(res)['steps']['slicing']['status'], 'BLOCKED')

    @unittest.skipUnless(SLICER and shutil.which('blender'), 'PrusaSlicer ou Blender absent')
    def test_one_metre_variant_stops_at_cut_study(self):
        res = self.run_("Jarvis, crée la Sentinelle 3D de 1 m", render_size=64)
        self.assertEqual(res['status'], 'BLOCKED')
        st = self.state(res)
        self.assertEqual(st['steps']['slicing']['status'], 'BLOCKED')
        plan = json.loads((Path(res['dir']) / 'cut_plan.json').read_text(encoding='utf8'))
        self.assertGreater(len(plan['pieces']), 1)
        self.assertFalse((Path(res['dir']) / 'tranchage').exists())

    @unittest.skipUnless(SLICER and shutil.which('blender'), 'PrusaSlicer ou Blender absent')
    def test_complete_low_res_journey_and_duplicate(self):
        res = self.run_()
        self.assertEqual(res['status'], 'DONE', res)
        d = Path(res['dir'])
        manifest = json.loads((d / 'manifest.json').read_text(encoding='utf8'))
        self.assertIn('slicing', manifest['executed'])
        self.assertIn('transcription', manifest['not_tested_or_simulated'])
        for rel, meta in manifest['files'].items():
            self.assertEqual(len(meta['sha256']), 64, rel)
        sl = json.loads((d / 'tranchage/tranchage.json').read_text(encoding='utf8'))
        for part in sl['parts'].values():
            self.assertTrue(part['stats']['forbidden_header_present'])
            gcode = (d / 'tranchage' / part['gcode']).read_text(encoding='utf8')
            self.assertNotRegex(gcode, r'(?m)^M10[49] ')  # aucune commande de chauffe
        before = json.loads((d / 'state.json').read_text(encoding='utf8'))['steps']
        dup = self.run_()
        self.assertTrue(dup['duplicate']); self.assertEqual(dup['status'], 'DONE')
        after = json.loads((d / 'state.json').read_text(encoding='utf8'))['steps']
        self.assertEqual({k: v.get('finished') for k, v in before.items()}, {k: v.get('finished') for k, v in after.items()})


if __name__ == '__main__':
    unittest.main()
