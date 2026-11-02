"""Essai virtuel du coupon STRATES : un trait de 7 mm sur 150 mm, débordement ≤ 1 mm.

Modèle par colonnes (pas de 0,1 mm le long du trait). Chaque poste du budget d'erreur proposé
par l'audit STRATES est tiré au hasard avec un écart type = allocation / `sigma_divisor`
(2 par défaut : ≈ 95 % des tirages dans l'allocation ; 1 : scénario pessimiste). La zone autorisée
est lue de façon prudente comme le bord nominal du trait (± 3,5 mm). C'est une hypothèse de travail, pas une mesure : le jalon G1 remplacera ces
écarts types par ceux mesurés sur coupons réels.
"""
from __future__ import annotations

import math
import random

STRATES_BUDGET_MM = {  # allocation proposée par l'audit STRATES (somme 1,00 mm)
    'recalage': 0.10, 'calibration_pointe': 0.15, 'suivi_trajectoire': 0.10,
    'deformation_pinceau': 0.20, 'etalement': 0.25, 'incertitude_mesure': 0.20,
}

RECIPE = {'length_mm': 150.0, 'nominal_width_mm': 7.0, 'width_min_mm': 6.0, 'width_max_mm': 8.0,
          'width_ok_fraction': 0.90, 'allowed_half_width_mm': 3.5, 'overflow_max_mm': 1.0, 'step_mm': 0.1}


def _smooth_noise(rng, n, sigma, corr_len):
    """Bruit gaussien lissé (AR(1)) d'écart type stationnaire `sigma`."""
    if sigma <= 0:
        return [0.0] * n
    a = math.exp(-1.0 / max(corr_len, 1.0))
    s = sigma * math.sqrt(1 - a * a)
    v, out = rng.gauss(0, sigma), []
    for _ in range(n):
        v = a * v + rng.gauss(0, s)
        out.append(v)
    return out


def coupon_trial(rng, arm_repeatability_mm, budget=STRATES_BUDGET_MM, recipe=RECIPE, width_bias_mm=0.0, sigma_divisor=2.0):
    n = int(recipe['length_mm'] / recipe['step_mm'])
    sig = {k: v / sigma_divisor for k, v in budget.items()}
    offset = rng.gauss(0, sig['recalage']) + rng.gauss(0, sig['calibration_pointe'])
    # Répétabilité ISO 9283 ≈ moyenne + 3σ : σ_bras ≈ valeur annoncée / 3.
    track_sigma = math.hypot(sig['suivi_trajectoire'], arm_repeatability_mm / 3)
    track = _smooth_noise(rng, n, track_sigma, 200)
    wdev = _smooth_noise(rng, n, sig['deformation_pinceau'], 300)
    spread_l = [abs(x) for x in _smooth_noise(rng, n, sig['etalement'], 80)]
    spread_r = [abs(x) for x in _smooth_noise(rng, n, sig['etalement'], 80)]
    meas = sig['incertitude_mesure']
    half = recipe['nominal_width_mm'] / 2
    overflow, ok_cols = 0.0, 0
    for i in range(n):
        w = recipe['nominal_width_mm'] + width_bias_mm + wdev[i]
        c = offset + track[i]
        left = c - w / 2 - spread_l[i] + rng.gauss(0, meas)
        right = c + w / 2 + spread_r[i] + rng.gauss(0, meas)
        overflow = max(overflow, -recipe['allowed_half_width_mm'] - left, right - recipe['allowed_half_width_mm'])
        ok_cols += recipe['width_min_mm'] <= right - left <= recipe['width_max_mm']
    overflow = max(0.0, overflow)
    width_ok = ok_cols / n
    passed = overflow + budget['incertitude_mesure'] <= recipe['overflow_max_mm'] and width_ok >= recipe['width_ok_fraction']
    return {'overflow_mm': round(overflow, 3), 'width_ok_fraction': round(width_ok, 3), 'passed': passed,
            'offset_mm': round(offset, 3), 'nominal_half_width_mm': half}


def _binom_tail_ge(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def clopper_pearson_lower(successes, n, confidence=0.95):
    """Borne inférieure unilatérale exacte (19/20 → ≈ 0,784 ; 59/59 → ≈ 0,950)."""
    if successes <= 0:
        return 0.0
    alpha, lo, hi = 1 - confidence, 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _binom_tail_ge(successes, n, mid) < alpha:
            lo = mid
        else:
            hi = mid
    return lo


def simulate_coupons(arm, trials=20, seed=0, budget=STRATES_BUDGET_MM, width_bias_mm=0.0, sigma_divisor=2.0):
    rep = arm.get('repeatability_mm')
    if rep is None:
        return {'arm': arm['id'], 'known': False, 'reason': 'répétabilité non publiée'}
    rng = random.Random(f"{seed}:{arm['id']}")
    runs = [coupon_trial(rng, rep, budget, width_bias_mm=width_bias_mm, sigma_divisor=sigma_divisor) for _ in range(trials)]
    ok = sum(r['passed'] for r in runs)
    ovf = sorted(r['overflow_mm'] for r in runs)
    return {'arm': arm['id'], 'known': True, 'trials': trials, 'passed': ok,
            'lower_bound_95': round(clopper_pearson_lower(ok, trials), 4),
            'overflow_median_mm': ovf[len(ovf) // 2], 'overflow_max_mm': ovf[-1],
            'width_bias_mm': width_bias_mm, 'sigma_divisor': sigma_divisor,
            'status': 'simulation sous hypothèses du budget STRATES, pas une mesure de coupon'}
