"""Contrôle de décodage voix : il doit échouer franchement quand PyAV casse faster-whisper."""
import importlib.util
import io
from pathlib import Path
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('verifier_voix', ROOT / 'tools/verifier_voix.py')
vv = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vv)


class DecodeCheck(unittest.TestCase):
    def test_synthetic_sound_is_one_second_of_16_khz_mono(self):
        with wave.open(io.BytesIO(vv.synthetic_wav())) as w:
            self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()), (1, 2, 16000, 16000))

    def test_av_19_signature_error_is_reported(self):
        def broken(_file, sampling_rate):
            raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")
        result = vv.check(broken)
        self.assertFalse(result['ok'])
        self.assertIn('metadata_errors', result['detail'])

    def test_correct_decoding_passes_and_wrong_length_fails(self):
        self.assertTrue(vv.check(lambda f, sampling_rate: [0.0] * 16000)['ok'])
        self.assertFalse(vv.check(lambda f, sampling_rate: [0.0] * 8000)['ok'])

    def test_voice_requirements_pin_a_compatible_pyav(self):
        pins = dict(line.split('==') for line in (ROOT / 'jarvis/requirements-voice.txt').read_text(encoding='utf-8').splitlines()
                    if '==' in line and not line.startswith('#'))
        self.assertEqual(pins.get('faster-whisper'), '1.2.1')
        major = int(pins['av'].split('.')[0])
        self.assertLess(major, 19, 'PyAV 19 retire metadata_errors, appelé par faster-whisper 1.2.1')


if __name__ == '__main__':
    unittest.main()
