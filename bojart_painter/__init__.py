"""Simulation BOJ.ART d'un bras peintre : boucle plan → exécution → observation → recalage.

Prototype de recherche en Python standard. Il ne pilote aucun robot, n'achète rien et
ne remplace ni la fiche d'acceptation STRATES (G0) ni une mesure physique sur coupon.
"""

from .arms import load_arms, reach_report
from .canvas import BrushModel, Canvas, Stroke
from .coupon import clopper_pearson_lower, simulate_coupons
from .loop import run_painting_loop
from .targets import load_ppm, make_target, save_ppm

__all__ = [
    'BrushModel', 'Canvas', 'Stroke', 'clopper_pearson_lower', 'load_arms', 'load_ppm',
    'make_target', 'reach_report', 'run_painting_loop', 'save_ppm', 'simulate_coupons',
]
