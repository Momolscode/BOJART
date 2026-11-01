import math
import unittest
from motion_primitives import Affine2D, cubic_in_out, sine_in_out, bounce_out


class MotionTests(unittest.TestCase):
    def test_cubic_midpoint_and_symmetry(self):
        self.assertEqual(cubic_in_out(.5), .5)
        for t in [.01, .12, .25, .49]:
            self.assertAlmostEqual(cubic_in_out(t), 1-cubic_in_out(1-t), places=14)

    def test_raw_progress_is_not_clamped(self):
        self.assertLess(cubic_in_out(-.1), 0)
        self.assertGreater(cubic_in_out(1.1), 1)

    def test_sine_endpoints_and_midpoint(self):
        self.assertEqual(sine_in_out(0), 0)
        self.assertEqual(sine_in_out(1), 1)
        self.assertAlmostEqual(sine_in_out(.5), .5)

    def test_bounce_internal_seams(self):
        for t in [4/11, 8/11, .9]:
            self.assertAlmostEqual(bounce_out(t-1e-10), bounce_out(t+1e-10), places=7)
        self.assertAlmostEqual(bounce_out(0), 0)
        self.assertAlmostEqual(bounce_out(1), 1)

    def test_append_and_prepend_have_different_order(self):
        scale = Affine2D.scale(2, 3)
        translation = Affine2D.translation(5, 7)
        self.assertEqual(scale.append(translation).transform(1, 1), (7, 10))
        self.assertEqual(scale.prepend(translation).transform(1, 1), (12, 24))

    def test_rotation_keeps_pivot_fixed(self):
        p = (13, -4)
        m = Affine2D.rotation(.91, p)
        actual = m.transform(*p)
        self.assertAlmostEqual(actual[0], p[0])
        self.assertAlmostEqual(actual[1], p[1])


if __name__ == '__main__':
    unittest.main()
