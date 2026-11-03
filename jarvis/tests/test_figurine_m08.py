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
from figurine.spec import SpecRejected, is_figurine_request, parse_request  # noqa: E402

try:
    import manifold3d, numpy as np, scipy, skimage, trimesh  # noqa: F401,E401
    HEAVY = True
except ImportError:
    HEAVY = False
SLICER = shutil.which('prusa-slicer') is not None
VEGETA = "Jarvis, crée-moi un Végéta 3D imprimable dans une position stylée, iconique et remarquable."
SENTINELLE = "Jarvis, crée-moi la Sentinelle 3D imprimable dans une position stylée, iconique et remarquable."
ARDOISE = "Jarvis, crée-moi Ardoise 3D imprimable dans une position stylée, iconique et remarquable."
VEILLE = "Jarvis, crée-moi la figurine Veille 3D imprimable dans une position stylée, iconique et remarquable."
FUSAIN = "Jarvis, crée-moi la figurine Fusain 3D imprimable dans une position stylée, iconique et remarquable."


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

    def test_original_warrior_and_two_characters(self):
        s = parse_request(ARDOISE)
        self.assertEqual((s['character']['id'], s['character']['rights']), ('ardoise', 'bojart_original'))
        self.assertEqual(s['geometry_source'], 'procedural_sdf')
        with self.assertRaises(SpecRejected) as c:
            parse_request("Jarvis, crée la Sentinelle et Ardoise en 3D")
        self.assertEqual(c.exception.status, 'CLARIFY')

    def test_veille_and_everyday_uses_of_the_word(self):
        s = parse_request(VEILLE)
        self.assertEqual((s['character']['id'], s['character']['rights']), ('veille', 'bojart_original'))
        self.assertEqual(s['geometry_source'], 'procedural_sdf')
        self.assertEqual(parse_request("Jarvis, crée-moi la figurine de Veille de 20 cm")['height_mm'], 200.0)
        self.assertEqual(parse_request("Jarvis, crée la Veille de 15 cm en 3D")['character']['id'], 'veille')
        noel = parse_request("Jarvis, prépare la Sentinelle 3D pour la veille de Noël")
        self.assertEqual(noel['character']['id'], 'sentinelle')
        for text in ("Jarvis, crée Veille", "Jarvis, crée Ardoise et Veille en 3D"):
            with self.assertRaises(SpecRejected) as c:
                parse_request(text)
            self.assertEqual(c.exception.status, 'CLARIFY')
        for text in ("Jarvis, mets-toi en veille", "Passe en mode veille", "Rappelle-moi la veille du salon"):
            self.assertFalse(is_figurine_request(text), text)
        self.assertTrue(is_figurine_request("Jarvis, sculpte Veille en statuette"))

    def test_fusain_and_everyday_uses_of_the_word(self):
        s = parse_request(FUSAIN)
        self.assertEqual((s['character']['id'], s['character']['rights']), ('fusain', 'bojart_original'))
        self.assertEqual(s['geometry_source'], 'procedural_sdf')
        self.assertEqual(parse_request("Jarvis, prépare une figurine de Fusain de 30 cm")['height_mm'], 300.0)
        # Sans mot de figurine, avec deux personnages, ou « au fusain » (la technique) : rien n'est lancé.
        for text in ("Jarvis, crée Fusain", "Jarvis, crée Veille et Fusain en 3D", "Jarvis, fais une statuette au fusain"):
            with self.assertRaises(SpecRejected) as c:
                parse_request(text)
            self.assertEqual(c.exception.status, 'CLARIFY')
        for text in ("Jarvis, dessine un portrait au fusain", "Range les fusains de l'atelier", "Taille le fusain du jardin"):
            self.assertFalse(is_figurine_request(text), text)
        self.assertTrue(is_figurine_request("Jarvis, sculpte Fusain en statuette"))

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

    def test_standby_phrases_never_start_a_figurine(self):
        from core import Rejected
        from dialogue import interpret
        self.assertEqual(interpret(VEILLE)['intent'], 'create_figurine')
        for text in ("Jarvis, mets-toi en veille", "Passe en mode veille"):
            try:
                intent = interpret(text)['intent']
            except Rejected:
                intent = None
            self.assertNotEqual(intent, 'create_figurine', text)


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

    def test_open_residue_does_not_leave_the_figure_inside_out(self):
        # Maillage du marching cubes retourné, avec un résidu ouvert accroché par un sommet : trimesh seul
        # n'inverse rien (l'ensemble n'est pas fermé). La figure doit ressortir fermée et à l'endroit.
        from figurine import sculpt
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=10).invert()
        v0 = sphere.vertices[0]
        sliver = np.array([v0, v0 + (0.1, 0.0, 0.0), v0 + (0.0, 0.1, 0.0)])
        raw = trimesh.Trimesh(np.vstack([sphere.vertices, sliver]),
                              np.vstack([sphere.faces, [[len(sphere.vertices), len(sphere.vertices) + 1,
                                                         len(sphere.vertices) + 2]]]), process=True)
        self.assertEqual(raw.body_count, 1)
        self.assertLess(raw.copy().fix_normals().volume, 0)          # le piège : rien n'est inversé
        mesh, bodies = sculpt.drop_residue_and_orient(raw, 0.4)
        self.assertEqual((bodies, mesh.metadata['marching_cubes_residue_removed']), (1, 1))
        self.assertTrue(mesh.is_watertight)
        self.assertGreater(mesh.volume, 0)

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

    def test_pegs_go_under_the_feet_not_under_a_third_contact(self):
        from figurine import fabrication
        def dense(box):
            v, f = trimesh.remesh.subdivide_to_size(box.vertices, box.faces, max_edge=2.0)
            return trimesh.Trimesh(v, f)
        feet = [dense(trimesh.creation.box((16, 28, 10))).apply_translation((x, 0, 5)) for x in (-20, 20)]
        tip = dense(trimesh.creation.box((14, 4, 60))).apply_translation((0, -30, 30))
        left, right, contacts = fabrication._feet_centres(trimesh.util.concatenate(feet + [tip]))
        self.assertTrue(np.allclose(left, (-20, 0), atol=0.05) and np.allclose(right, (20, 0), atol=0.05))
        self.assertLess(contacts[:, 1].min(), -31)  # la pointe compte pour la taille du socle

    def test_slate_strata_base_prints_upside_down(self):
        from figurine import checks, fabrication, sculpt
        nominal, _ = sculpt.sculpt_figure('repos_fier', voxel=2.0, smooth_iterations=2)
        asm = fabrication.build_assembly(nominal, 200.0, style='strates')
        base, info = asm['socle'], asm['info']
        st = info['base_style']
        self.assertEqual(st['version'], 'bojart.socle.strates.v1')
        self.assertGreaterEqual(st['strata'], 3)
        self.assertGreaterEqual(st['top_margin_beyond_feet_mm'], 5.0)
        self.assertGreaterEqual(st['recess_wall_min_mm'], 2.0)
        self.assertAlmostEqual(base.bounds[1][2], info['base_height_mm'], places=4)   # dessus plat : plan de joint
        printed = base.copy()
        printed.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        r = checks.check_part(printed, 'socle', thickness_samples=300)
        self.assertEqual(r['eliminatory'], [])
        self.assertLess(r['measured']['overhang_area_fraction'], 0.005)
        self.assertTrue(checks.check_fit(asm['figurine'], base, info)['fit_ok'])
        again = fabrication.build_assembly(nominal, 200.0, style='strates')['socle']
        self.assertTrue(np.array_equal(again.vertices, base.vertices))                  # graine fixe
        plain = fabrication.build_assembly(nominal, 200.0)
        self.assertNotIn('base_style', plain['info'])                                    # socle lisse inchangé
        self.assertEqual(fabrication.fab_version('lisse'), fabrication.FAB_VERSION)
        self.assertNotEqual(fabrication.fab_version('strates'), fabrication.FAB_VERSION)
        with self.assertRaises(ValueError):
            fabrication.build_assembly(nominal, 200.0, style='inconnu')

    def test_basalt_base_hugs_the_contacts_and_prints_upside_down(self):
        from shapely.geometry import MultiPoint, Point
        from figurine import checks, fabrication, sculpt, veille
        nominal, bodies = sculpt.sculpt_figure('veille', voxel=2.0, cid='veille')
        self.assertEqual(bodies, 1)
        asm = fabrication.build_assembly(nominal, 200.0, style='basalte')
        base, info = asm['socle'], asm['info']
        st = info['base_style']
        self.assertEqual((st['version'], st['sides']), ('bojart.socle.basalte.v1', 6))
        self.assertGreaterEqual(st['top_margin_beyond_feet_mm'], 10.0)
        self.assertGreaterEqual(st['recess_wall_min_mm'], 3.0)
        self.assertGreater(st['bevel_slope_min'], 1.0)                                    # biseau plus raide que 45°
        front = np.angle(np.exp(1j * (np.radians(st['side_normals_deg']) + np.pi / 2)))
        self.assertGreater(np.abs(front).min(), np.radians(20))                           # un sommet vers l'avant
        # Tenons : Ø4 sous le pied nu, Ø5 sous l'étoffe posée ; la pointe du bâton n'en reçoit pas.
        mirror, sc = np.array((-1.0, 1.0)), info['scale_from_nominal']
        pose = veille.POSES['veille']
        pegs = {p['diameter_mm']: np.array(p['xy']) for p in info['pegs']}
        self.assertLess(np.linalg.norm(pegs[4.0] - np.array(pose['ankle_r'][:2]) * mirror * sc), 15.0)
        self.assertLess(np.linalg.norm(pegs[5.0] - np.array(pose['drape']['pool_centre']) * mirror * sc), 15.0)
        staff = np.array(pose['staff']['foot']) * mirror * sc
        self.assertTrue(all(np.linalg.norm(xy - staff) > 20.0 for xy in pegs.values()))
        top = base.vertices[np.abs(base.vertices[:, 2] - info['base_height_mm']) < 1e-4][:, :2]
        outline = MultiPoint(top.tolist()).convex_hull                                   # dessus hexagonal convexe
        self.assertEqual(len(outline.exterior.coords) - 1, 6)
        for xy in pegs.values():
            self.assertTrue(outline.contains(Point(xy)))
            self.assertGreaterEqual(outline.exterior.distance(Point(xy)), 10.0)
        self.assertAlmostEqual(base.bounds[1][2], info['base_height_mm'], places=4)       # dessus plat : plan de joint
        printed = base.copy()
        printed.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        r = checks.check_part(printed, 'socle', thickness_samples=300)
        self.assertEqual(r['eliminatory'], [])
        self.assertLess(r['measured']['overhang_area_fraction'], 0.005)
        self.assertTrue(checks.check_fit(asm['figurine'], base, info)['fit_ok'])
        again = fabrication.build_assembly(nominal, 200.0, style='basalte')['socle']
        self.assertTrue(np.array_equal(again.vertices, base.vertices))                   # graine fixe
        self.assertEqual(fabrication.fab_version('basalte'), 'bojart.fabrication.v3+bojart.socle.basalte.v1')

    def test_fusain_stroke_carries_the_open_hand_from_the_rocks(self):
        from figurine import fabrication, fusain, sculpt
        nominal, bodies = sculpt.sculpt_figure('trait', voxel=2.0, cid='fusain')
        self.assertEqual(bodies, 1)                                # trait, volutes et blocs tiennent à la figure
        pose = fusain.POSES['trait']
        foot = np.array(pose['stroke']['path'][0], np.float32)
        probes = np.array([[foot[0], foot[1], 0.4], pose['palm']['centre'], pose['stroke']['path'][3]], np.float32)
        self.assertTrue((fusain.fusain_sdf(probes, 'trait') < 0).all())     # du rocher à la paume, sans coupure
        C, hw, ht, W = fusain.stroke_frames(pose['stroke'])
        self.assertGreaterEqual(float(2 * ht.min()), 2.5)                   # ruban imprimable en FDM 0,4
        self.assertLess(float(np.abs(np.einsum('ij,ij->i', W, np.gradient(C, axis=0))).max()), 1e-3)
        asm = fabrication.build_assembly(nominal, 200.0, style='basalte')
        info = asm['info']
        sc = info['scale_from_nominal']
        # Tenons sous les deux plus grands appuis : les blocs du trait (toujours le plus grand) et un pied
        # (les deux semelles ont la même surface : lequel dépend du pas de grille).
        pegs = [np.array(p['xy']) for p in info['pegs']]
        def near(xy, pt):
            return np.linalg.norm(xy - np.array(pt[:2]) * sc) < 15.0
        on_rocks = [near(xy, foot) for xy in pegs]
        self.assertEqual(sum(on_rocks), 1)
        other = pegs[on_rocks.index(False)]
        self.assertTrue(near(other, pose['ankle_l']) or near(other, pose['ankle_r']))
        self.assertEqual(sorted(p['diameter_mm'] for p in info['pegs']), [4.0, 5.0])
        self.assertEqual(info['base_style']['version'], 'bojart.socle.basalte.v1')

    def test_fusain_bandage_ends_flush_with_the_wrist(self):
        from figurine import fusain
        # Coupée net, la bande (4 à 4,45 mm de rayon au poignet) dépassait du raccord du poing gauche
        # (3,3 mm) en anneau à dents de scie : lèvre de 0,13 mm au contrôle local.
        a, b = np.zeros(3, np.float32), np.array([0.0, 0.0, 13.5], np.float32)
        th = np.linspace(0.0, 2.0 * np.pi, 72, endpoint=False)
        def circle(r, z):
            return np.stack([r * np.cos(th), r * np.sin(th), np.full_like(th, z)], -1).astype(np.float32)
        for r_end in fusain.WRIST_R.values():
            self.assertTrue((fusain._forearm_wrap(circle(r_end + 0.05, 13.45), a, b, r_end) > 0).all())
            self.assertTrue((fusain._forearm_wrap(circle(3.0, 6.0), a, b, r_end) < 0).all())   # bande pleine

    def test_ring_detail_stays_within_its_band(self):
        from figurine import details
        axis = np.array([0.0, 0.0, 1.0], np.float32)
        pts = np.array([[0, 0, 0.9], [5.4, 0, 0], [0, 6.2, 0], [5.0, 0, 0.5]], np.float32)
        d = details.ring(pts, (0, 0, 0), axis, 6.0, 0.6, 0.3)
        self.assertGreater(d[0], 0)    # une capsule de rayon 6 contiendrait ce point : pas de « bouée »
        self.assertLess(d[1], 0); self.assertGreater(d[2], 0); self.assertLess(d[3], 0)

    def test_display_socle_holds_an_original_base_and_prints_upright(self):
        from shapely.geometry import Polygon
        from figurine import checks, fabrication

        def holes_at(mesh, z):
            sec, _ = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]).to_planar()
            return [Polygon(h).area for p in sec.polygons_full for h in p.interiors]

        mesh, info = fabrication.display_socle('ovale', 90, 70)
        hb, (a, b) = info['height_mm'], info['pocket']['semi_axes_mm']
        self.assertEqual((a, b), (45.4, 35.4))                                           # cotes + jeu de 0,4 mm
        r = checks.check_part(mesh, 'socle_vitrine', thickness_samples=300)
        self.assertEqual(r['eliminatory'], [])
        self.assertEqual(r['measured']['overhang_area_fraction'], 0.0)                  # à l'endroit, sans support
        self.assertAlmostEqual(mesh.bounds[0][2], 0.0, places=4)
        self.assertAlmostEqual(mesh.bounds[1][2], hb, places=4)
        holes = holes_at(mesh, hb - 1.5)
        self.assertEqual(len(holes), 1)
        self.assertAlmostEqual(holes[0] / (np.pi * a * b), 1.0, delta=0.002)           # empreinte à la cote
        floor = mesh.ray.intersects_location([[0, 0, hb + 5]], [[0, 0, -1]], multiple_hits=False)[0]
        self.assertAlmostEqual(float(floor[0][2]), hb - info['pocket']['depth_mm'], places=3)
        self.assertGreaterEqual(info['rim_min_mm'], fabrication.VITRINE_HYPOTHESES['min_pocket_wall_mm'])
        self.assertTrue(np.array_equal(fabrication.display_socle('ovale', 90, 70)[0].vertices, mesh.vertices))
        flat, finfo = fabrication.display_socle('libre', 100, 60)
        self.assertIsNone(finfo['pocket']); self.assertEqual(holes_at(flat, hb - 1.5), [])
        for bad in (('carree', 80, None), ('ovale', 90, None), ('ronde', 15, None), ('ronde', 200, None)):
            with self.assertRaises(ValueError):
                fabrication.display_socle(*bad)
        with self.assertRaises(ValueError):                                              # empreinte traversante
            fabrication.display_socle('ronde', 80, hyp={**fabrication.VITRINE_HYPOTHESES, 'pocket_depth_mm': 14.0})

    @unittest.skipUnless(SLICER, 'PrusaSlicer absent')
    def test_display_socle_tool_reports_without_any_character(self):
        import subprocess
        tool = ROOT / 'tools/socle_vitrine.py'
        with tempfile.TemporaryDirectory() as d:
            bad = subprocess.run([sys.executable, str(tool), '--forme', 'ovale', '--largeur', '90', '--out', d],
                                 capture_output=True, text=True, timeout=300)
            self.assertEqual(bad.returncode, 2); self.assertIn('REFUSED', bad.stdout)
            self.assertEqual(list(Path(d).iterdir()), [])                                   # refus avant toute écriture
            ok = subprocess.run([sys.executable, str(tool), '--forme', 'ronde', '--largeur', '80', '--out', d],
                                capture_output=True, text=True, timeout=600)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            rep = json.loads((Path(d) / 'rapport.json').read_text(encoding='utf8'))
            self.assertEqual(rep['slicing']['status'], 'DONE'); self.assertFalse(rep['slicing']['sent_to_machine'])
            self.assertTrue(rep['slicing']['stats']['forbidden_header_present'])
            self.assertTrue(rep['socle']['character_geometry'].startswith('aucune'))
            self.assertEqual(list(Path(d).rglob('*.png')), [])                              # pas de rendu sans --rendus

    def test_character_defaults_keep_published_identities(self):
        from figurine import fabrication, pipeline
        from figurine.spec import parse_request
        with tempfile.TemporaryDirectory() as d:
            run = pipeline.FigurineRun(SENTINELLE, Path(d))
            _, ident = run._identity(parse_request(SENTINELLE))
            self.assertEqual((ident['voxel'], ident['fab']), (0.6, fabrication.FAB_VERSION))
            run = pipeline.FigurineRun(ARDOISE, Path(d))
            _, ident = run._identity(parse_request(ARDOISE))
            self.assertEqual((ident['voxel'], run.socle_style), (0.4, 'strates'))
            self.assertEqual(ident['fab'], fabrication.fab_version('strates'))
            run = pipeline.FigurineRun(VEILLE, Path(d))
            _, ident = run._identity(parse_request(VEILLE))
            self.assertEqual((ident['voxel'], run.socle_style, ident['sculpt']), (0.4, 'basalte', 'bojart.veille.sdf.v1'))
            self.assertEqual(ident['fab'], fabrication.fab_version('basalte'))
            run = pipeline.FigurineRun(FUSAIN, Path(d))
            _, ident = run._identity(parse_request(FUSAIN))
            self.assertEqual((ident['voxel'], run.socle_style, ident['sculpt']), (0.4, 'basalte', 'bojart.fusain.sdf.v1'))

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
        partial = json.loads((Path(res['dir']) / 'manifest_partiel.json').read_text(encoding='utf8'))
        self.assertTrue(partial['evidence_level'].startswith('INCOMPLET — BLOCKED'))
        self.assertEqual(set(partial['files']), {'spec.json'})

    def test_third_party_mesh_without_provenance_is_blocked(self):
        mesh = self.out / 'fourni.stl'
        trimesh.creation.box((10, 10, 10)).export(mesh)
        res = self.run_(VEGETA, mesh=mesh)
        self.assertEqual(res['status'], 'BLOCKED')
        self.assertIn('provenance', self.state(res)['steps']['geometry']['reason'])

    def test_licensed_third_party_mesh_is_processed_without_any_image(self):
        # Fichier fourni : un maillage abstrait de substitution (géométrie de la Sentinelle), jamais une
        # ressemblance. Le personnage demandé reste sous droits de tiers : contrôle, socle et tranchage
        # oui, aucune image (rendus, aperçu des couches).
        from figurine import sculpt
        nominal, _ = sculpt.sculpt_figure('repos_fier', voxel=2.0, smooth_iterations=2)
        mesh, licence = self.out / 'fourni.stl', self.out / 'licence.txt'
        nominal.export(mesh)
        licence.write_text('Fiche de provenance de test : aucune licence réelle.', encoding='utf8')
        res = self.run_(VEGETA, mesh=mesh, provenance=licence)
        st = self.state(res)
        self.assertEqual(st['steps']['geometry']['status'], 'DONE')
        self.assertEqual(st['steps']['checks']['status'], 'DONE')
        self.assertEqual(st['steps']['renders']['status'], 'SKIPPED')
        self.assertEqual(list(Path(res['dir']).rglob('*.png')), [])
        self.assertFalse((Path(res['dir']) / 'rendus').exists())
        if SLICER:
            self.assertEqual(res['status'], 'DONE', res)
            sl = json.loads((Path(res['dir']) / 'tranchage/tranchage.json').read_text(encoding='utf8'))
            self.assertEqual(sl['preview']['status'], 'SKIPPED')

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

    def test_original_warrior_rest_pose_until_renders(self):
        res = self.run_(text="Jarvis, crée-moi Ardoise 3D au repos", faults=['no_blender'])
        st = self.state(res)
        self.assertEqual(st['pose'], 'serment')
        self.assertEqual(st['steps']['geometry']['result']['bodies'], 1)
        self.assertEqual(st['steps']['checks']['result']['verdict'], 'CONFORME_AUX_CRITERES_CALCULES')
        self.assertEqual(st['steps']['renders']['status'], 'BLOCKED')
        pegs = json.loads((Path(res['dir']) / 'assembly.json').read_text(encoding='utf8'))['pegs']
        self.assertTrue(all(abs(p['xy'][0]) > 10 for p in pegs))  # sous les pieds, pas sous la lame plantée

    def test_heroine_kneels_on_foot_and_robe_until_renders(self):
        res = self.run_(text=VEILLE, faults=['no_blender'])
        st = self.state(res)
        self.assertEqual(st['pose'], 'veille')
        self.assertEqual(st['steps']['geometry']['result']['bodies'], 1)
        self.assertEqual(st['steps']['checks']['result']['verdict'], 'CONFORME_AUX_CRITERES_CALCULES')
        self.assertEqual(st['steps']['renders']['status'], 'BLOCKED')
        asm = json.loads((Path(res['dir']) / 'assembly.json').read_text(encoding='utf8'))
        self.assertEqual(asm['base_style']['version'], 'bojart.socle.basalte.v1')
        self.assertEqual(sorted(p['diameter_mm'] for p in asm['pegs']), [4.0, 5.0])

    def test_wrestler_stands_on_his_stroke_until_renders(self):
        # Pas de 1,5 mm : à 2 mm, les doigts de la main ouverte (Ø 2 à 2,4 mm) ne sont pas résolus et le
        # contrôle d'épaisseur les signale à juste titre.
        res = self.run_(text=FUSAIN, faults=['no_blender'], voxel=1.5)
        st = self.state(res)
        self.assertEqual(st['pose'], 'trait')
        self.assertEqual(st['steps']['geometry']['result']['bodies'], 1)
        self.assertEqual(st['steps']['checks']['result']['verdict'], 'CONFORME_AUX_CRITERES_CALCULES')
        self.assertEqual(st['steps']['renders']['status'], 'BLOCKED')
        asm = json.loads((Path(res['dir']) / 'assembly.json').read_text(encoding='utf8'))
        self.assertEqual(asm['base_style']['version'], 'bojart.socle.basalte.v1')
        self.assertEqual(sorted(p['diameter_mm'] for p in asm['pegs']), [4.0, 5.0])

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


class PortabilityTests(unittest.TestCase):
    """Installation commune avec Jarvis et import sous Windows (tour), vérifiés sans réseau."""

    def test_shared_pins_do_not_conflict(self):
        pins = {}
        for req in sorted(ROOT.glob('requirements*.txt')) + [ROOT / 'apps/jarvis/requirements.txt']:
            for line in req.read_text(encoding='utf8').splitlines():
                line = line.split('#')[0].strip()
                if '==' in line:
                    name, version = (part.strip() for part in line.split('==', 1))
                    pins.setdefault(name.lower().replace('_', '-'), {})[version] = req.name
        self.assertEqual({n: v for n, v in pins.items() if len(v) > 1}, {})

    @unittest.skipUnless(HEAVY, 'dépendances géométriques absentes (requirements-figurine.txt)')
    @unittest.skipIf(sys.platform == 'win32', 'vérifie le repli hors Windows')
    def test_pipeline_imports_without_posix_resource_module(self):
        import importlib.util
        from unittest import mock
        path = ROOT / 'apps/jarvis/app/figurine/pipeline.py'
        spec = importlib.util.spec_from_file_location('figurine.pipeline_sans_resource', path)
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {'resource': None}):
            spec.loader.exec_module(module)
        self.assertIsNone(module.resource)
        self.assertEqual(module.peak_memory_mb(), (None, None))


if __name__ == '__main__':
    unittest.main()
