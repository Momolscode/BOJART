"""Commandes : `arms` (comparatif simulé), `simulate` (boucle de peinture), `coupon` (essai STRATES)."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

from .arms import ROOT, load_arms, reach_report
from .coupon import RECIPE, STRATES_BUDGET_MM, simulate_coupons
from .loop import compare_open_closed, run_painting_loop
from .targets import SYNTHETIC, load_ppm, make_target, save_ppm

STYLES_PATH = ROOT / 'configs/painter/styles.json'
CODE = ['bojart_painter/' + p for p in ('arms.py', 'calibration.py', 'canvas.py', 'coupon.py', 'hd.py', 'loop.py', 'planner.py',
                                        'targets.py', '__main__.py')]


def _fingerprints():
    files = CODE + ['configs/painter/arms.json', 'configs/painter/styles.json']
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}


def _psnr(mse):
    return round(10 * math.log10(1 / mse), 2) if mse > 0 else None


def _clean(result, save_dir=None, name=None):
    canvas = result.pop('canvas')
    result['psnr_db'] = _psnr(result['final_loss'])
    if save_dir:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        save_ppm(canvas, Path(save_dir) / f'{name}.ppm')
    return result


def _target(spec, width_px, height_px, mm_per_px):
    kind, _, value = spec.partition(':')
    if kind == 'synthetic':
        return make_target(value, width_px, height_px, mm_per_px), {'kind': 'synthetic', 'name': value}
    if kind == 'ppm':
        raw = Path(value).read_bytes()
        return load_ppm(value, width_px, height_px, mm_per_px), {'kind': 'ppm', 'sha256': hashlib.sha256(raw).hexdigest(),
                                                                 'path_in_git': False}
    raise SystemExit('cible attendue : synthetic:<%s> ou ppm:<chemin>' % '|'.join(SYNTHETIC))


def cmd_arms(a):
    arms = load_arms()
    rows = []
    for arm in arms.values():
        rows.append({'arm': arm['id'], 'name': arm['name'], 'price_indicative': arm['price_indicative'],
                     'simulation_models': arm['simulation_models'],
                     'reach': reach_report(arm, a.canvas_w, a.canvas_h),
                     'coupon_nominal': simulate_coupons(arm, a.trials, a.seed, sigma_divisor=2.0),
                     'coupon_pessimistic': simulate_coupons(arm, a.trials, a.seed, sigma_divisor=1.0)})
    return {'command': 'arms', 'canvas_mm': [a.canvas_w, a.canvas_h], 'trials': a.trials, 'seed': a.seed,
            'strates_budget_mm': STRATES_BUDGET_MM, 'recipe': RECIPE, 'arms': rows}


def cmd_simulate(a):
    arms = load_arms(); styles = json.loads(STYLES_PATH.read_text(encoding='utf-8'))['styles']
    arm = arms[a.arm]
    w, h = int(a.canvas_w / a.mm_per_px), int(a.canvas_h / a.mm_per_px)
    target, tinfo = _target(a.target, w, h, a.mm_per_px)
    if a.save_ppm:
        Path(a.save_ppm).mkdir(parents=True, exist_ok=True); save_ppm(target, Path(a.save_ppm) / 'cible.ppm')
    out = {'command': 'simulate', 'arm': a.arm, 'target': tinfo, 'grid_px': [w, h], 'mm_per_px': a.mm_per_px,
           'rounds': a.rounds, 'strokes_per_round': a.strokes_per_round, 'seed': a.seed, 'styles': {},
           'reach': reach_report(arm, a.canvas_w, a.canvas_h)}
    for name in a.style:
        if a.compare:
            res = compare_open_closed(target, styles[name], arm, a.rounds, a.strokes_per_round, a.seed)
            out['styles'][name] = {k: _clean(v, a.save_ppm, f'{name}-{k}') for k, v in res.items()}
        else:
            res = run_painting_loop(target, styles[name], arm, a.rounds, a.strokes_per_round, seed=a.seed,
                                    episodes_path=a.episodes, until_converged=a.until_converged,
                                    max_strokes=a.max_strokes)
            out['styles'][name] = {'closed_loop_learning': _clean(res, a.save_ppm, name)}
    return out


def cmd_coupon(a):
    arm = load_arms()[a.arm]
    return {'command': 'coupon', 'result': simulate_coupons(arm, a.trials, a.seed, sigma_divisor=a.sigma_divisor),
            'strates_budget_mm': STRATES_BUDGET_MM, 'recipe': RECIPE}


def cmd_hd(a):
    from .hd import Deposit, HDPainter, load_image  # numpy et Pillow requis
    raw = Path(a.image).read_bytes()
    target = load_image(a.image, a.width_px)
    painter = HDPainter(target, a.style, a.mm_per_px, a.seed, hidden=Deposit(a.hidden_gain, a.hidden_opacity),
                        position_sigma_mm=a.position_sigma_mm, color_sigma=a.color_sigma)
    res = painter.run(a.strokes, batches=a.batches, group_by_color=a.group_by_color)
    snaps = res.pop('snapshots')
    if a.save_png:
        from PIL import Image
        import numpy as np
        out = Path(a.save_png); out.mkdir(parents=True, exist_ok=True)
        Image.fromarray((target * 255).astype('uint8')).save(out / 'cible.png')
        for k, v in snaps.items():
            Image.fromarray((np.clip(v, 0, 1) * 255).astype('uint8')).save(out / f'{a.style}-{k:06d}.png')
    return {'command': 'hd', 'image': {'sha256': hashlib.sha256(raw).hexdigest(), 'path_in_git': False},
            'style': a.style, 'seed': a.seed, 'requested_strokes': a.strokes, 'group_by_color': a.group_by_color,
            'world': {'hidden_gain': a.hidden_gain, 'hidden_opacity': a.hidden_opacity,
                      'position_sigma_mm': a.position_sigma_mm, 'color_sigma': a.color_sigma}, **res}


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m bojart_painter', description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('arms', 'simulate', 'coupon', 'hd'):
        s = sub.add_parser(name)
        s.add_argument('--seed', type=int, default=1)
        s.add_argument('--output')
        if name in ('arms', 'simulate'):
            s.add_argument('--canvas-w', type=float, default=900); s.add_argument('--canvas-h', type=float, default=650)
        if name in ('arms', 'coupon'):
            s.add_argument('--trials', type=int, default=59)
        if name in ('simulate', 'coupon'):
            s.add_argument('--arm', default='ufactory_xarm6')
        if name == 'coupon':
            s.add_argument('--sigma-divisor', type=float, default=2.0)
        if name == 'hd':
            s.add_argument('--image', required=True, help='image locale hors Git (domaine public ou droits vérifiés)')
            s.add_argument('--style', default='fin', choices=['reproduction', 'fin', 'empattement', 'tres_fin', 'atelier_3_semaines'])
            s.add_argument('--strokes', type=int, default=8000)
            s.add_argument('--width-px', type=int, default=450)
            s.add_argument('--batches', type=int, default=8)
            s.add_argument('--hidden-gain', type=float, default=1.15)
            s.add_argument('--hidden-opacity', type=float, default=0.82)
            s.add_argument('--position-sigma-mm', type=float, default=0.35)
            s.add_argument('--color-sigma', type=float, default=0.015)
            s.add_argument('--mm-per-px', type=float, default=2.0)
            s.add_argument('--group-by-color', action='store_true',
                           help='exécuter chaque lot pinceau par pinceau puis pot par pot (moins de rinçages)')
            s.add_argument('--save-png', help='dossier hors Git pour les rendus')
        if name == 'simulate':
            s.add_argument('--target', default='synthetic:paysage')
            s.add_argument('--style', nargs='+', default=['reproduction'])
            s.add_argument('--mm-per-px', type=float, default=10.0)
            s.add_argument('--rounds', type=int, default=4); s.add_argument('--strokes-per-round', type=int, default=50)
            s.add_argument('--compare', action='store_true', help='comparer apprentissage, sans apprentissage et boucle ouverte')
            s.add_argument('--until-converged', action='store_true',
                           help="continuer jusqu'à couvrir la toile et stabiliser l'erreur")
            s.add_argument('--max-strokes', type=int, default=3000)
            s.add_argument('--save-ppm', help='dossier hors Git pour les rendus PPM')
            s.add_argument('--episodes', help='journal JSONL des touches (hors Git)')
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    result = {'arms': cmd_arms, 'simulate': cmd_simulate, 'coupon': cmd_coupon, 'hd': cmd_hd}[a.cmd](a)
    result['runtime'] = {'seconds': round(time.perf_counter() - t0, 2), 'python': platform.python_version(),
                         'platform': platform.system(), 'fingerprints': _fingerprints(),
                         'limits': 'Simulation logicielle ; aucun bras, pinceau, peinture ni coupon réel mesuré.'}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True); Path(a.output).write_text(text + '\n', encoding='utf-8')
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
