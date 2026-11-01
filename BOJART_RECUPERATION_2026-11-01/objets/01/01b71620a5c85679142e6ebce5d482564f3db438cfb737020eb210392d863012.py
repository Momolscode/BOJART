"""Original Python reconstruction of a selected NAudio.Core low-pass path.

Recovered from REA CIL Evidence, not from C# source. The wrapper deliberately
restricts inputs to finite, useful audio values. It is not all of NAudio.
"""
import math
import struct


def f32(value):
    """Round one scalar as a CLI r4 / IEEE 754 binary32 storage operation."""
    return struct.unpack('<f', struct.pack('<f', float(value)))[0]


class LowPass:
    def __init__(self, sample_rate, cutoff, q=1 / math.sqrt(2)):
        self.set_low_pass(sample_rate, cutoff, q)

    @staticmethod
    def coefficients(sample_rate, cutoff, q):
        sr, fc, q = (f32(x) for x in (sample_rate, cutoff, q))
        if not all(math.isfinite(v) for v in (sr, fc, q)):
            raise ValueError('Parameters must be finite')
        if sr <= 0 or not 0 < fc < sr / 2 or q <= 0:
            raise ValueError('Require sample_rate > 0, 0 < cutoff < Nyquist, q > 0')
        w = 6.283185307179586 * fc / sr
        c = math.cos(w)
        alpha = math.sin(w) / float(f32(2.0 * q))
        denominator = 1.0 + alpha
        # Binary fields a0..a4 are normalized feedforward b0,b1,b2 and feedback a1,a2.
        return ((1.0 - c) / 2.0 / denominator,
                (1.0 - c) / denominator,
                (1.0 - c) / 2.0 / denominator,
                -2.0 * c / denominator,
                (1.0 - alpha) / denominator)

    def set_low_pass(self, sample_rate, cutoff, q=1 / math.sqrt(2)):
        self.b0, self.b1, self.b2, self.a1, self.a2 = self.coefficients(sample_rate, cutoff, q)
        self.x1 = self.x2 = self.y1 = self.y2 = f32(0)

    def update_low_pass(self, sample_rate, cutoff, q=1 / math.sqrt(2)):
        """Change coefficients while retaining the four sample-history values."""
        self.b0, self.b1, self.b2, self.a1, self.a2 = self.coefficients(sample_rate, cutoff, q)

    def transform(self, sample):
        x = f32(sample)
        if not math.isfinite(x):
            raise ValueError('Audio samples must be finite')
        value = self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2
        value = value - self.a1 * self.y1 - self.a2 * self.y2
        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, f32(value)
        return self.y1

    def process(self, samples):
        return [self.transform(s) for s in samples]


def process_channels(interleaved, channels, sample_rate, cutoff, q=1 / math.sqrt(2)):
    """Independent history per channel; no shared-state stereo crosstalk."""
    if not isinstance(channels, int) or channels <= 0:
        raise ValueError('channels must be a positive integer')
    if len(interleaved) % channels:
        raise ValueError('Input must contain complete interleaved frames')
    filters = [LowPass(sample_rate, cutoff, q) for _ in range(channels)]
    return [filters[i % channels].transform(value) for i, value in enumerate(interleaved)]
