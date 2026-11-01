/** Original Marwin test fixture. No artist source project was recovered. */
export const DEFAULTS = Object.freeze({
  captureStart: 0.5, captureEnd: 1.4, releaseStart: 2.6, releaseEnd: 3.6,
  centerX: 0.5, centerY: 0.04, radiusX: 0.5, radiusY: 0.12,
  gain: 0.45, warmth: [28, 12, 0], protectFromY: 0.132, feather: 0.025,
});

export function clamp01(x) {
  if (!Number.isFinite(x)) throw new TypeError('Finite value required');
  return Math.min(1, Math.max(0, x));
}

/** Monotone cubic interpolation; zero slope at the endpoints, no overshoot. */
export function smoothstep(x) { const q = clamp01(x); return q * q * (3 - 2 * q); }

export function settings(overrides = {}) {
  const p = { ...DEFAULTS, ...overrides };
  for (const k of ['captureStart','captureEnd','releaseStart','releaseEnd','centerX','centerY','radiusX','radiusY','gain','protectFromY','feather']) {
    if (!Number.isFinite(p[k])) throw new TypeError(`Invalid ${k}`);
  }
  if (!(p.captureStart < p.captureEnd && p.captureEnd <= p.releaseStart && p.releaseStart < p.releaseEnd)) throw new RangeError('Capture and release intervals must be ordered');
  if (p.radiusX <= 0 || p.radiusY <= 0 || p.feather <= 0) throw new RangeError('Radii and feather must be positive');
  if (!Array.isArray(p.warmth) || p.warmth.length !== 3 || !p.warmth.every(Number.isFinite)) throw new TypeError('warmth must contain three finite values');
  return p;
}

export function captureAmount(t, overrides = {}) {
  const p = settings(overrides);
  return smoothstep((t - p.captureStart) / (p.captureEnd - p.captureStart));
}

export function releaseAmount(t, overrides = {}) {
  const p = settings(overrides);
  return smoothstep((t - p.releaseStart) / (p.releaseEnd - p.releaseStart));
}

export function envelope(t, overrides = {}) {
  const p = settings(overrides);
  return captureAmount(t, p) * (1 - releaseAmount(t, p));
}

/** Coordinates are normalized. Protected lower rows have exactly zero weight. */
export function spatialWeight(x, y, overrides = {}, isProtected = false) {
  const p = settings(overrides);
  if (!Number.isFinite(x) || !Number.isFinite(y)) throw new TypeError('Finite coordinates required');
  if (isProtected || y >= p.protectFromY) return 0;
  const gaussian = Math.exp(-0.5 * (((x - p.centerX) / p.radiusX) ** 2 + ((y - p.centerY) / p.radiusY) ** 2));
  const edge = 1 - smoothstep((y - (p.protectFromY - p.feather)) / p.feather);
  return gaussian * edge;
}

/** Integer RGB input; protected pixels are returned unchanged, before encoding. */
export function applyLightPixel(rgb, x, y, t, overrides = {}, isProtected = false) {
  if (!Array.isArray(rgb) || rgb.length !== 3 || !rgb.every(v => Number.isInteger(v) && v >= 0 && v <= 255)) throw new TypeError('RGB must be three bytes');
  const p = settings(overrides);
  const weight = spatialWeight(x, y, p, isProtected) * envelope(t, p);
  if (weight === 0) return [...rgb];
  return rgb.map((v, channel) => Math.min(255, Math.max(0, Math.round(v * (1 + p.gain * weight) + p.warmth[channel] * weight))));
}
