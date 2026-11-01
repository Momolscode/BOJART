import math
import unittest
from biquad import LowPass, f32, process_channels


class BiquadTests(unittest.TestCase):
    def test_impulse_and_dc_settle_without_instability(self):
        out = LowPass(48000, 1200).process([1.0] + [0.0] * 4095)
        self.assertTrue(all(math.isfinite(x) for x in out))
        self.assertLess(abs(out[-1]), 1e-12)
        out = LowPass(48000, 1200).process([.25] * 4096)
        self.assertAlmostEqual(out[-1], .25, places=6)

    def test_treble_is_attenuated_and_low_tone_kept(self):
        def gain(freq):
            src = [.25 * math.sin(2 * math.pi * freq * i / 48000) for i in range(4800)]
            out = LowPass(48000, 1200).process(src)
            rms = lambda x: math.sqrt(sum(v * v for v in x) / len(x))
            return rms(out[2400:]) / rms(src[2400:])
        self.assertGreater(gain(100), .99)
        self.assertLess(gain(6000), .04)

    def test_update_keeps_memory_but_set_resets_it(self):
        f = LowPass(48000, 1200)
        f.process([.25] * 16)
        state = (f.x1, f.x2, f.y1, f.y2)
        f.update_low_pass(48000, 3000)
        self.assertEqual(state, (f.x1, f.x2, f.y1, f.y2))
        f.set_low_pass(48000, 3000)
        self.assertEqual((0, 0, 0, 0), (f.x1, f.x2, f.y1, f.y2))

    def test_stereo_has_independent_history(self):
        data = [value for i in range(256) for value in ((1.0 if i == 0 else 0.0), 0.0)]
        result = process_channels(data, 2, 48000, 1200)
        self.assertTrue(any(abs(x) > 0 for x in result[0::2]))
        self.assertEqual([0.0] * 256, result[1::2])

    def test_storage_is_float32(self):
        f = LowPass(48000, 1200)
        self.assertEqual(f.transform(.123456789), f32(f.y1))
        self.assertEqual(f.x1, f32(.123456789))

    def test_reject_invalid_wrapper_domain(self):
        for args in [(0, 1000, .7), (48000, 24000, .7), (48000, 1200, 0),
                     (48000, float('nan'), .7)]:
            with self.assertRaises(ValueError):
                LowPass(*args)
        with self.assertRaises(ValueError):
            process_channels([0, 1, 2], 2, 48000, 1200)


if __name__ == '__main__':
    unittest.main()
