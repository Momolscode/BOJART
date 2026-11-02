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

    def test_palette_style_uses_palette(self):
        from bojart_painter.hd import HDPainter
        p = HDPainter(self.target(), 'empattement', mm_per_px=5.0, seed=1)
        self.assertEqual(len(p.palette), 12)


if __name__ == '__main__':
    unittest.main()
