"""Peintre haute définition : ignoré si numpy est absent (dépendance facultative)."""
import unittest

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

from bojart_painter import make_target


@unittest.skipIf(np is None, 'numpy absent : peintre HD facultatif')
class HDPainterTests(unittest.TestCase):
    def target(self):
        t = make_target('paysage', 60, 40, 5.0)
        return np.array(t.data, dtype=np.float32).reshape(40, 60, 3)

    def test_hd_loop_paints_learns_and_is_deterministic(self):
        from bojart_painter.hd import HDPainter
        a = HDPainter(self.target(), 'reproduction', mm_per_px=5.0, seed=4).run(400, batches=4)
        b = HDPainter(self.target(), 'reproduction', mm_per_px=5.0, seed=4).run(400, batches=4)
        self.assertEqual(a['final_mse'], b['final_mse'])
        blank = float(((np.ones((40, 60, 3)) - self.target()) ** 2).mean())
        self.assertLess(a['final_mse'], blank / 5)
        self.assertAlmostEqual(a['learned']['width_gain'], a['hidden']['width_gain'], delta=0.1)
        self.assertAlmostEqual(a['learned']['opacity'], a['hidden']['opacity'], delta=0.1)

    def test_ssim_is_one_for_identical_images(self):
        from bojart_painter.hd import ssim
        t = self.target()
        self.assertAlmostEqual(ssim(t, t), 1.0, places=5)
        self.assertLess(ssim(np.ones_like(t), t), 0.9)

    def test_workshop_style_uses_three_discrete_brushes(self):
        from bojart_painter.hd import HDPainter
        p = HDPainter(self.target(), 'atelier_3_semaines', mm_per_px=5.0, seed=2)
        err = np.ones((40, 60))
        widths = {round(p._propose(err, prog)[3]) for prog in (0.1, 0.4, 0.9) for _ in range(5)}
        self.assertTrue(widths <= {19, 20, 21, 8, 3})
        self.assertEqual(len(p.palette), 10)

    def test_calibration_board_measures_hidden_width_gain(self):
        from bojart_painter.calibration import stroke_library
        from bojart_painter.hd import Deposit
        palette = [(0.1, 0.2, 0.6), (0.8, 0.7, 0.1), (0.2, 0.2, 0.2), (0.6, 0.1, 0.1)]
        res = stroke_library(palette, brushes_mm=(20.0, 8.0), hidden=Deposit(1.3, 0.8))
        self.assertAlmostEqual(res['fit']['20.0']['width_gain_median'], 1.3, delta=0.06)
        self.assertAlmostEqual(res['fit']['8.0']['width_gain_median'], 1.3, delta=0.1)
        self.assertEqual(res['fit']['20.0']['samples'], 4)

    def test_recorded_strokes_replay_to_the_same_canvas(self):
        from bojart_painter.hd import HDPainter
        p = HDPainter(self.target(), 'atelier_3_semaines', mm_per_px=5.0, seed=3)
        res = p.run(120, batches=2, record=True)
        replay = np.ones_like(p.world)
        for e in res['executed']:
            fp = p.footprint(*e['p'], e['width_mm'], p.hidden, e['seed'])
            p._apply(replay, fp, e['color'])
        self.assertLess(float(np.abs(replay - p.world).max()), 1e-5)

    def test_grouping_by_pot_cuts_color_changes(self):
        from bojart_painter.hd import HDPainter

        def changes(group):
            p = HDPainter(self.target(), 'atelier_3_semaines', mm_per_px=5.0, seed=3)
            ex = p.run(160, batches=2, record=True, group_by_color=group)['executed']
            pots = [int(((p.palette - e['color']) ** 2).sum(1).argmin()) for e in ex]
            return sum(a != b for a, b in zip(pots, pots[1:])), len(ex)

        loose, n_loose = changes(False)
        grouped, n_grouped = changes(True)
        self.assertGreater(n_grouped, 100)
        self.assertLess(grouped, loose / 2)
        self.assertLessEqual(grouped, 2 * 10 * 2)  # au plus un passage par pot, pinceau et lot

    def test_frida_plan_bridge_geometry_and_replay(self):
        import math
        from bojart_painter.frida_bridge import replay, to_strokes, width_mm
        table = [{'z': 0.1, 'length_m': 0.05, 'width_mm_median': 3.5}, {'z': 0.9, 'length_m': 0.05, 'width_mm_median': 7.5}]
        plan = {'canvas_m': [0.30, 0.20], 'width_table': table, 'strokes': [
            {'xt': 0.0, 'yt': 0.0, 'angle': 0.0, 'length_m': 0.05, 'bend_m': 0.0, 'z': 0.5, 'color': [0.1, 0.2, 0.7]},
            {'xt': -0.5, 'yt': 0.5, 'angle': math.pi / 2, 'length_m': 0.04, 'bend_m': 0.01, 'z': 0.9, 'color': [0.9, 0.8, 0.1]}]}
        self.assertAlmostEqual(width_mm(0.5, table), 5.5)
        a, b = to_strokes(plan, mm_per_px=5.0)
        np.testing.assert_allclose(a['p'][0], [30, 20])      # centre de la toile 300 × 200 mm, 5 mm/px
        np.testing.assert_allclose(a['p'][2], [40, 20])      # angle 0 : vers la droite de l'image
        np.testing.assert_allclose(b['p'][0], [15, 30])
        np.testing.assert_allclose(b['p'][2], [15, 22])      # angle 90° : vers le haut de l'image
        self.assertLess(b['p'][1][0], 15)                     # courbure positive : à gauche du trajet montant
        target = np.ones((40, 60, 3), dtype=np.float32)
        res = replay(target, [a, b], mm_per_px=5.0)
        self.assertEqual(res['strokes'], 2)
        self.assertLess(float(res['world'][20, 33].max()), 0.9)  # la première touche a bien été peinte

    def test_stroke_atlas_places_measured_masks(self):
        import tempfile
        from bojart_painter.atlas import StrokeAtlas, synthetic_atlas
        atlas = synthetic_atlas()
        fp = atlas.footprint((10, 20), (20, 20), (40, 20), 6.0, 1.0, 1.0, 1.0, (40, 60))
        y0, y1, x0, x1, a = fp
        cover = np.zeros((40, 60)); cover[y0:y1, x0:x1] = a
        self.assertGreater(cover[20, 25], 0.9)                       # sur le tracé
        self.assertLess(cover[20, 45], 0.1)                          # après la fin de la touche
        self.assertAlmostEqual(float((cover[:, 25] > 0.5).sum()), 6, delta=1)  # largeur 6 mm à 1 mm/px
        up = atlas.footprint((10, 20), (25, 12), (40, 20), 6.0, 1.0, 1.0, 1.0, (40, 60))
        cu = np.zeros((40, 60)); cu[up[0]:up[1], up[2]:up[3]] = up[4]
        self.assertGreater(cu[15:19, 25].max(), 0.9)                 # milieu courbé vers le haut
        wide = atlas.footprint((10, 20), (20, 20), (40, 20), 4.0, 1.0, 1.5, 1.0, (40, 60))
        cw = np.zeros((40, 60)); cw[wide[0]:wide[1], wide[2]:wide[3]] = wide[4]
        self.assertAlmostEqual(float((cw[:, 25] > 0.5).sum()), 6, delta=1)     # gain 1,5 sur 4 mm
        with tempfile.TemporaryDirectory() as d:
            atlas.save(d + '/a.npz'); again = StrokeAtlas.load(d + '/a.npz')
        np.testing.assert_array_equal(again.masks, atlas.masks)

    def test_hd_painter_paints_and_learns_with_an_atlas(self):
        from bojart_painter.atlas import synthetic_atlas
        from bojart_painter.hd import Deposit, HDPainter
        with self.assertRaises(ValueError):
            HDPainter(self.target(), 'pinceau_mesure', mm_per_px=5.0)
        p = HDPainter(self.target(), 'pinceau_mesure', mm_per_px=5.0, seed=2, hidden=Deposit(1.2, 0.8),
                      atlas=synthetic_atlas())
        res = p.run(300, batches=3)
        blank = float(((np.ones((40, 60, 3)) - self.target()) ** 2).mean())
        self.assertLess(res['final_mse'], blank / 2)
        self.assertAlmostEqual(res['learned']['opacity'], 0.8, delta=0.1)

    def test_palette_style_uses_palette(self):
        from bojart_painter.hd import HDPainter
        p = HDPainter(self.target(), 'empattement', mm_per_px=5.0, seed=1)
        self.assertEqual(len(p.palette), 12)


if __name__ == '__main__':
    unittest.main()
