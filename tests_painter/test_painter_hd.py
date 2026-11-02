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

    def test_palette_style_uses_palette(self):
        from bojart_painter.hd import HDPainter
        p = HDPainter(self.target(), 'empattement', mm_per_px=5.0, seed=1)
        self.assertEqual(len(p.palette), 12)


if __name__ == '__main__':
    unittest.main()
