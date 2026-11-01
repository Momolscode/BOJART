"""Original Python reconstruction from REA-decoded Avalonia 12.1.4 CIL.

Scope: finite progress values and affine 2D matrices. These primitives do not
track a person, recover an artist's project, or predict audience retention.
"""
from dataclasses import dataclass
import math


def cubic_in_out(t: float) -> float:
    """Raw cubic timing curve; deliberately does not clamp progress."""
    if t < 0.5:
        return 4.0 * t * t * t
    q = 2.0 * (t - 1.0)
    return 0.5 * q * q * q + 1.0


def sine_in_out(t: float) -> float:
    """Raw sinusoidal timing curve, using radians internally."""
    return 0.5 * (1.0 - math.cos(t * math.pi))


def bounce_out(t: float) -> float:
    """The coefficients observed in this DLL, not a substituted generic bounce."""
    if t < 0.36363636363636365:
        return 121.0 * t * t / 16.0
    if t < 0.7272727272727273:
        return 9.075 * t * t - 9.9 * t + 3.4
    if t < 0.9:
        return 12.066481994459833 * t * t - 19.63545706371191 * t + 8.898060941828255
    return 10.8 * t * t - 20.52 * t + 10.72


@dataclass(frozen=True)
class Affine2D:
    """Row-vector convention: [x y 1] times this matrix.

    Matrix rows are (m11,m12,0), (m21,m22,0), (m31,m32,1).
    Perspective is intentionally excluded; original Matrix supports more cases.
    """
    m11: float = 1.0
    m12: float = 0.0
    m21: float = 0.0
    m22: float = 1.0
    m31: float = 0.0
    m32: float = 0.0

    def transform(self, x: float, y: float):
        return (x * self.m11 + y * self.m21 + self.m31,
                x * self.m12 + y * self.m22 + self.m32)

    def append(self, other):
        """Apply self, then other. Multiplication order is significant."""
        a, b = self, other
        return Affine2D(
            a.m11 * b.m11 + a.m12 * b.m21,
            a.m11 * b.m12 + a.m12 * b.m22,
            a.m21 * b.m11 + a.m22 * b.m21,
            a.m21 * b.m12 + a.m22 * b.m22,
            a.m31 * b.m11 + a.m32 * b.m21 + b.m31,
            a.m31 * b.m12 + a.m32 * b.m22 + b.m32,
        )

    def prepend(self, other):
        """Apply other, then self."""
        return other.append(self)

    @staticmethod
    def translation(x, y):
        return Affine2D(1.0, 0.0, 0.0, 1.0, x, y)

    @staticmethod
    def scale(x, y):
        return Affine2D(x, 0.0, 0.0, y, 0.0, 0.0)

    @staticmethod
    def rotation(radians, center=(0.0, 0.0)):
        c, s = math.cos(radians), math.sin(radians)
        x, y = center
        return Affine2D(c, s, -s, c,
                        x * (1.0 - c) + y * s,
                        y * (1.0 - c) - x * s)
