"""Simulation du bras peintre : déterminisme, apprentissage du dépôt, géométrie et coupon STRATES."""
import json
import tempfile
import unittest
from pathlib import Path

from bojart_painter import (BrushModel, Canvas, Stroke, clopper_pearson_lower, load_arms, load_ppm,
                            make_target, reach_report, run_painting_loop, save_ppm, simulate_coupons)
from bojart_painter.__main__ import main
from bojart_painter.loop import HIDDEN_WORLD

ROOT = Path(__file__).resolve().parents[1]
STYLES = json.loads((ROOT / 'configs/painter/styles.json').read_text(encoding='utf-8'))['styles']


class PainterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arms = load_arms()
        cls.target = make_target('paysage', 30, 22, 30.0)

    def test_binomial_bounds_match_strates_audit(self):
        self.assertAlmostEqual(clopper_pearson_lower(19, 20), 0.784, places=3)
        self.assertGreater(clopper_pearson_lower(59, 59), 0.95)
        self.assertLess(clopper_pearson_lower(58, 58), 0.95)

    def test_stroke_paints_inside_its_width(self):
        c = Canvas(40, 20, 1.0)
        c.paint(Stroke((5, 10), (20, 10), (35, 10), 6.0, (0, 0, 0)), BrushModel(1.0, 1.0, 1.0))
        self.assertLess(c.pixel(20, 10)[0], 0.05)
        self.assertEqual(c.pixel(20, 1), (1.0, 1.0, 1.0))

    def test_loop_is_deterministic_and_learns_hidden_deposit(self):
        arm = self.arms['ufactory_xarm6']
        a = run_painting_loop(self.target, STYLES['aplats_geometriques'], arm, rounds=2, strokes_per_round=15, seed=3)
        b = run_painting_loop(self.target, STYLES['aplats_geometriques'], arm, rounds=2, strokes_per_round=15, seed=3)
        self.assertEqual(a['final_loss'], b['final_loss'])
        self.assertLess(a['final_loss'], a['blank_loss'] / 2)
        self.assertAlmostEqual(a['learned_model']['width_gain'], HIDDEN_WORLD.width_gain, delta=0.1)
        self.assertAlmostEqual(a['learned_model']['opacity'], HIDDEN_WORLD.opacity, delta=0.1)

    def test_palette_style_uses_only_palette_colours(self):
        res = run_painting_loop(self.target, STYLES['aplats_geometriques'], self.arms['agilex_piper'], 1, 10, seed=1, learn=False)
        self.assertEqual(len(res['palette']), STYLES['aplats_geometriques']['palette_size'])

    def test_reach_separates_small_and_large_arms(self):
        self.assertEqual(reach_report(self.arms['universal_robots_ur5e'])['coverage_overhead'], 1.0)
        self.assertLess(reach_report(self.arms['ufactory_lite6'])['coverage_overhead'], 0.5)
        self.assertFalse(reach_report(self.arms['robotstudio_so101'])['known'])

    def test_coupon_penalises_low_repeatability(self):
        lite = simulate_coupons(self.arms['ufactory_lite6'], 40, seed=1)
        ur = simulate_coupons(self.arms['universal_robots_ur5e'], 40, seed=1)
        self.assertLess(lite['passed'], ur['passed'])
        self.assertEqual(simulate_coupons(self.arms['ufactory_xarm6'], 10, seed=1, sigma_divisor=1.0)['passed'], 0)

    def test_ppm_round_trip_outside_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cible.ppm'
            save_ppm(self.target, path)
            back = load_ppm(path, 30, 22, 30.0)
            self.assertLess(max(abs(a - b) for a, b in zip(back.data, self.target.data)), 1 / 255 + 1e-9)

    def test_arm_sources_are_registered(self):
        sources = {s['source_id'] for s in json.loads((ROOT / 'data/knowledge/sources.json').read_text(encoding='utf-8'))}
        for arm in self.arms.values():
            self.assertTrue(set(arm['sources']) <= sources, arm['id'])

    def test_cli_report_has_fingerprints_and_no_raster(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'r.json'
            main(['simulate', '--target', 'synthetic:composition', '--canvas-w', '600', '--canvas-h', '450',
                  '--mm-per-px', '30', '--rounds', '1', '--strokes-per-round', '5', '--output', str(out)])
            data = json.loads(out.read_text(encoding='utf-8'))
            self.assertIn('bojart_painter/loop.py', data['runtime']['fingerprints'])
            self.assertNotIn('canvas', data['styles']['reproduction']['closed_loop_learning'])


if __name__ == '__main__':
    unittest.main()
