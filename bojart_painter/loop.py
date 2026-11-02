"""Boucle réel → simulation → réel, entièrement simulée.

1. Planifier un lot de touches sur la dernière observation, avec le modèle de dépôt supposé.
2. Les « exécuter » sur une toile tenue à l'écart : modèle de dépôt caché, erreur de position
   du bras, erreur de teinte. Cette toile joue le rôle du monde physique.
3. Photographier (bruit de capteur) ; isoler quelques touches pour recaler largeur et opacité.
4. Replanifier depuis l'observation. Comparer à une exécution en boucle ouverte.

Le monde « physique » est lui-même un modèle : ce prototype vérifie la logique de la boucle et
de l'apprentissage du modèle de dépôt, pas la qualité d'une peinture réelle.
"""
from __future__ import annotations

import json
import math
import random

from .arms import execution_time_s
from .canvas import BrushModel, Canvas
from .planner import Planner

GAINS = [round(0.80 + 0.05 * i, 2) for i in range(15)]      # 0,80 → 1,50
OPACITIES = [round(0.50 + 0.05 * i, 2) for i in range(11)]  # 0,50 → 1,00

HIDDEN_WORLD = BrushModel(width_gain=1.2, opacity=0.72, edge_mm=6.0)
NOMINAL = BrushModel(width_gain=1.0, opacity=0.9, edge_mm=6.0)


class World:
    """Toile « physique » simulée : le planificateur n'y a accès que par `observe`."""

    def __init__(self, width, height, mm_per_px, model: BrushModel, position_sigma_mm, color_sigma, rng):
        self.canvas = Canvas(width, height, mm_per_px)
        self.model, self.pos_sigma, self.color_sigma, self.rng = model, position_sigma_mm, color_sigma, rng

    def execute(self, stroke):
        dx, dy = self.rng.gauss(0, self.pos_sigma), self.rng.gauss(0, self.pos_sigma)
        real = stroke.shifted(dx, dy)
        real.color = tuple(min(1, max(0, c + self.rng.gauss(0, self.color_sigma))) for c in stroke.color)
        self.canvas.paint(real, self.model)

    def observe(self, noise=0.01):
        obs = self.canvas.copy()
        obs.data = [min(1.0, max(0.0, v + self.rng.gauss(0, noise))) for v in obs.data]
        return obs


def _accumulate_calibration(table, before: Canvas, after: Canvas, stroke):
    """Ajoute à `table[(gain, opacité)]` l'écart entre l'effet prédit et l'effet observé d'une touche."""
    unit = BrushModel(1.0, 1.0, NOMINAL.edge_mm)
    region = None
    for g in GAINS:
        unit.width_gain = g
        foot = before.footprint(stroke, unit)
        if region is None:  # région d'évaluation : la touche la plus large possible
            unit.width_gain = GAINS[-1]
            region = {i for i, _ in before.footprint(stroke, unit)}
            unit.width_gain = g
        alpha = dict(foot)
        for o in OPACITIES:
            sse = 0.0
            for idx in region:
                a = alpha.get(idx, 0.0) * o
                for k in range(3):
                    old = before.data[3 * idx + k]
                    pred = old + a * (stroke.color[k] - old)
                    sse += (pred - after.data[3 * idx + k]) ** 2
            table[(g, o)] = table.get((g, o), 0.0) + sse


def unpainted_fraction(canvas: Canvas, target: Canvas, background=(1.0, 1.0, 1.0), tol=0.05):
    """Part de la toile encore vierge là où la cible demande de la peinture."""
    n = canvas.width * canvas.height
    bare = 0
    for i in range(n):
        c = canvas.data[3 * i:3 * i + 3]; t = target.data[3 * i:3 * i + 3]
        if max(abs(a - b) for a, b in zip(c, background)) < tol and max(abs(a - b) for a, b in zip(t, background)) >= tol:
            bare += 1
    return bare / n


def run_painting_loop(target: Canvas, style: dict, arm: dict, rounds=4, strokes_per_round=60,
                      calibration_strokes=4, seed=0, hidden=HIDDEN_WORLD, believed=NOMINAL,
                      learn=True, episodes_path=None, until_converged=False, max_strokes=3000,
                      min_relative_gain=0.02, max_unpainted=0.005):
    """`until_converged` : continuer par lots tant que la toile a des zones vierges ou que
    l'erreur baisse d'au moins `min_relative_gain` par lot, dans la limite de `max_strokes`.
    Sinon, exactement `rounds` lots. La progression du gros au fin suit les lots prévus."""
    rng = random.Random(f'{seed}:plan')
    world_rng = random.Random(f'{seed}:world')
    rep = arm.get('repeatability_mm') or 2.0
    # Position : répétabilité (≈3σ) + recalage et calibration de pointe STRATES (σ = allocation/2).
    pos_sigma = math.sqrt((rep / 3) ** 2 + 0.05 ** 2 + 0.075 ** 2) + 0.5  # +0,5 mm : jeu du pinceau
    world = World(target.width, target.height, target.mm_per_px, hidden, pos_sigma, 0.02, world_rng)
    planner = Planner(target, style, rng)
    model = BrushModel(believed.width_gain, believed.opacity, believed.edge_mm)
    table, history, all_strokes = {}, [], []
    episodes = open(episodes_path, 'w', encoding='utf-8') if episodes_path else None
    try:
        obs = world.observe()
        r, stop_reason = 0, 'rounds'
        while True:
            if not until_converged and r >= rounds:
                break
            p0, p1 = min(1.0, r / rounds), min(1.0, (r + 1) / rounds)
            plan = planner.plan(obs, model, strokes_per_round, p0, p1)
            for i, s in enumerate(plan):
                isolate = learn and i < calibration_strokes
                before = world.observe() if isolate else None
                world.execute(s)
                if isolate:
                    _accumulate_calibration(table, before, world.observe(), s)
                if episodes:
                    episodes.write(json.dumps({'round': r, 'stroke': s.as_dict(),
                                               'expected_delta': round(s.meta.get('expected_delta', 0), 6),
                                               'believed_model': model.as_dict()}) + '\n')
            all_strokes += plan
            if learn and table:
                g, o = min(table, key=table.get)
                model = BrushModel(g, o, model.edge_mm)
            obs = world.observe()
            loss = world.canvas.loss(target)
            bare = unpainted_fraction(world.canvas, target)
            history.append({'round': r + 1, 'strokes': len(plan), 'loss': round(loss, 6),
                            'unpainted_fraction': round(bare, 4), 'believed_model': model.as_dict()})
            r += 1
            if until_converged:
                prev = history[-2]['loss'] if len(history) > 1 else Canvas(target.width, target.height, target.mm_per_px).loss(target)
                gain = (prev - loss) / prev if prev > 0 else 0.0
                if not plan:
                    stop_reason = 'aucune touche utile'; break
                if len(all_strokes) >= max_strokes:
                    stop_reason = 'max_strokes'; break
                if r >= rounds and bare <= max_unpainted and gain < min_relative_gain:
                    stop_reason = 'convergence'; break
    finally:
        if episodes:
            episodes.close()
    return {
        'final_loss': history[-1]['loss'] if history else world.canvas.loss(target),
        'blank_loss': round(Canvas(target.width, target.height, target.mm_per_px).loss(target), 6),
        'rounds': history, 'strokes': len(all_strokes), 'stop_reason': stop_reason,
        'unpainted_fraction': history[-1]['unpainted_fraction'] if history else 1.0,
        'hidden_model': hidden.as_dict(), 'learned_model': model.as_dict(), 'learning': learn,
        'position_sigma_mm': round(pos_sigma, 3),
        'execution_time_estimate_s': round(execution_time_s(all_strokes, arm)),
        'palette': [[round(c, 3) for c in p] for p in planner.palette] if planner.palette else None,
        'canvas': world.canvas,
    }


def compare_open_closed(target, style, arm, rounds=4, strokes_per_round=60, seed=0):
    """Même budget de touches : boucle fermée avec recalage, puis boucle fermée sans apprentissage."""
    closed = run_painting_loop(target, style, arm, rounds, strokes_per_round, seed=seed, learn=True)
    fixed = run_painting_loop(target, style, arm, rounds, strokes_per_round, seed=seed, learn=False)
    single = run_painting_loop(target, style, arm, 1, rounds * strokes_per_round, seed=seed, learn=False)
    return {'closed_loop_learning': closed, 'closed_loop_no_learning': fixed, 'open_loop_single_plan': single}
