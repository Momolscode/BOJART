#!/usr/bin/env python3
"""Animation facultative de la cellule de peinture : bras xArm 7 (MuJoCo Menagerie) rejouant
les touches exécutées par le peintre HD, avec pots, porte-pinceaux, chiffon, caméra et toile.

Dépendances facultatives : numpy, Pillow, mujoco, ffmpeg, plus une copie locale du dossier
`ufactory_xarm7` de MuJoCo Menagerie (licence UFACTORY, hors de ce dépôt). Le xArm 6 recommandé
n'existe pas dans Menagerie ; le xArm 7 de la même famille sert d'illustration.

Visuel de démonstration, pas une preuve d'accès ou de trajectoire : la cinématique inverse est
une moindres-carrés amortis sur la position et l'axe du pinceau, sans dynamique ni collisions.

Exemple (sans GPU : Xvfb :99 puis DISPLAY=:99 MUJOCO_GL=glfw) :
  python tools/render_painter_cell.py --menagerie /chemin/ufactory_xarm7 \
      --image /hors-git/oeuvre-domaine-public.jpg --out /hors-git/atelier
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

CANVAS_MM = (500, 312)            # largeur (y monde), hauteur (x monde)
CX = 0.42                          # centre de la toile, axe x du monde
TIP = 0.12                         # distance TCP → pointe du pinceau (m)
BRUSHES = (20.0, 8.0, 3.0)
RACK = [(0.17, 0.20 + 0.035 * i) for i in range(3)]
POTS = [(0.30 + 0.065 * i, s * 0.31) for s in (1, -1) for i in range(5)]
RAG = (0.17, -0.24)

SCENE = """<mujoco model="atelier BOJART">
  <include file="xarm7.xml"/>
  <visual>
    <headlight diffuse="0.55 0.55 0.55" ambient="0.38 0.38 0.38" specular="0 0 0"/>
    <global offwidth="1280" offheight="960"/>
    <quality shadowsize="4096"/>
  </visual>
  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.92 0.92 0.94" rgb2="0.70 0.72 0.76" width="512" height="3072"/>
    <texture type="2d" name="sol" builtin="checker" rgb1="0.80 0.78 0.74" rgb2="0.75 0.73 0.69" width="300" height="300"/>
    <material name="sol" texture="sol" texuniform="true" texrepeat="8 8"/>
    <texture type="2d" name="toile" builtin="flat" rgb1="1 1 1" width="312" height="500"/>
    <material name="toile" texture="toile"/>
  </asset>
  <worldbody>
    <light pos="0.4 0.3 1.8" dir="-0.1 -0.1 -1" directional="true" castshadow="true"/>
    <geom name="floor" type="plane" size="0 0 0.05" pos="0 0 -0.8" material="sol"/>
    <geom name="table" type="box" size="0.48 0.48 0.4" pos="0.36 0 -0.4" rgba="0.56 0.44 0.32 1"/>
    <geom name="toile" type="box" size="0.156 0.25 0.003" pos="0.42 0 0.003" material="toile"/>
    <geom name="chassis" type="box" size="0.162 0.256 0.002" pos="0.42 0 0.001" rgba="0.85 0.80 0.70 1"/>
    {pots}
    <geom name="rack" type="box" size="0.03 0.07 0.03" pos="0.17 0.235 0.03" rgba="0.30 0.30 0.32 1"/>
    <geom name="chiffon" type="box" size="0.045 0.045 0.006" pos="0.17 -0.24 0.006" rgba="0.90 0.88 0.84 1"/>
    <geom name="mat" type="cylinder" size="0.012 0.45" pos="0.42 -0.52 0.45" rgba="0.2 0.2 0.22 1"/>
    <geom name="potence" type="capsule" fromto="0.42 -0.52 0.9 0.42 -0.08 0.9" size="0.01" rgba="0.2 0.2 0.22 1"/>
    <geom name="camera" type="box" size="0.035 0.025 0.02" pos="0.42 -0.08 0.88" rgba="0.08 0.08 0.1 1"/>
    {brushes}
  </worldbody>
</mujoco>
"""


def scene_xml():
    pots = []
    for i, (x, y) in enumerate(POTS):
        pots.append(f'<geom name="pot{i}" type="cylinder" size="0.022 0.022" pos="{x} {y} 0.022" rgba="0.95 0.95 0.95 1"/>')
        pots.append(f'<geom name="peinture{i}" type="cylinder" size="0.019 0.001" pos="{x} {y} 0.044" rgba="0.5 0.5 0.5 1"/>')
    brushes = []
    for i, w in enumerate(BRUSHES):
        r = max(w / 2000, 0.0015)
        brushes.append(f"""<body name="pinceau{i}" mocap="true" pos="{RACK[i][0]} {RACK[i][1]} 0.06" quat="0 1 0 0">
      <geom name="poils{i}" type="capsule" fromto="0 0 -0.002 0 0 -0.022" size="{r:.4f}" rgba="0.15 0.12 0.10 1" contype="0" conaffinity="0"/>
      <geom name="virole{i}" type="cylinder" fromto="0 0 -0.022 0 0 -0.04" size="{max(r, 0.004):.4f}" rgba="0.75 0.75 0.78 1" contype="0" conaffinity="0"/>
      <geom name="manche{i}" type="capsule" fromto="0 0 -0.04 0 0 -0.17" size="0.0045" rgba="0.62 0.38 0.20 1" contype="0" conaffinity="0"/>
    </body>""")
    return SCENE.replace('{pots}', '\n    '.join(pots)).replace('{brushes}', '\n    '.join(brushes))


def to_world(p_px, mm_per_px):
    """Pixel toile (x à droite, y vers le bas) → point monde sur la surface peinte."""
    x_mm, y_mm = p_px[0] * mm_per_px, p_px[1] * mm_per_px
    return np.array([CX - CANVAS_MM[1] / 2000 + y_mm / 1000, CANVAS_MM[0] / 2000 - x_mm / 1000, 0.0065])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--menagerie', required=True, help='dossier ufactory_xarm7 de MuJoCo Menagerie')
    ap.add_argument('--image', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--strokes', type=int, default=6000)
    ap.add_argument('--detail', type=int, default=10, help='touches détaillées par pinceau')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--no-grouping', action='store_true', help='ordre du planificateur, sans regrouper par pot')
    ap.add_argument('--frida-plan', help='plan JSON exporté de FRIDA (voir bojart_painter/frida_bridge.py)')
    ap.add_argument('--title', default='Atelier simulé — fin de semaine 3')
    a = ap.parse_args()

    import mujoco
    from PIL import Image, ImageDraw, ImageFont
    from bojart_painter.hd import Deposit, HDPainter

    out = Path(a.out); frames = out / 'frames'; frames.mkdir(parents=True, exist_ok=True)
    for f in frames.glob('*.png'):
        f.unlink()
    mm = 1.0
    target = np.asarray(Image.open(a.image).convert('RGB').resize(CANVAS_MM, Image.LANCZOS), dtype=np.float32) / 255
    if a.frida_plan:  # plan calculé par FRIDA hors dépôt, rejoué en boucle ouverte
        from bojart_painter.frida_bridge import load_plan, replay, to_strokes
        plan = load_plan(a.frida_plan)
        if [round(v * 1000) for v in plan['canvas_m']] != list(CANVAS_MM):
            raise SystemExit(f"plan FRIDA pour une toile {plan['canvas_m']} m, scène prévue pour {CANVAS_MM} mm")
        executed = to_strokes(plan, mm)
        palette = np.clip(np.asarray(plan['palette'], dtype=np.float32), 0, 1)
        painter = HDPainter(target, 'reproduction', mm, a.seed, hidden=Deposit(1.0, 1.0))
        rep = replay(target, executed, mm)
        res = {'learned': None, 'hidden': rep['hidden'], 'psnr_db': rep['psnr_db'], 'ssim': rep['ssim']}
    else:
        painter = HDPainter(target, 'atelier_3_semaines', mm, a.seed, hidden=Deposit(1.25, 0.75),
                            position_sigma_mm=0.5, color_sigma=0.03)
        res = painter.run(a.strokes, record=True, group_by_color=not a.no_grouping)
        executed = res['executed']; palette = painter.palette

    model_path = Path(a.menagerie) / 'scene_bojart_atelier.xml'
    model_path.write_text(scene_xml(), encoding='utf-8')
    m = mujoco.MjModel.from_xml_path(str(model_path)); d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 0); mujoco.mj_forward(m, d)
    for i, c in enumerate(palette):
        m.geom_rgba[m.geom(f'peinture{i}').id][:3] = c
    site = m.site('link_tcp').id; tex = m.texture('toile').id
    tw, th, adr = int(m.tex_width[tex]), int(m.tex_height[tex]), int(m.tex_adr[tex])
    W3, H3 = 800, 600
    r = mujoco.Renderer(m, H3, W3)
    cam = mujoco.MjvCamera(); cam.lookat[:] = [0.38, 0.0, 0.06]; cam.distance = 1.3; cam.azimuth = 215; cam.elevation = -34
    mocap = [m.body(f'pinceau{i}').mocapid[0] for i in range(3)]
    held = None
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    bold = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 19)

    def solve(goal, iters):
        for _ in range(iters):
            mujoco.mj_forward(m, d)
            x = d.site_xpos[site]; z = d.site_xmat[site].reshape(3, 3)[:, 2]
            err = np.concatenate([goal - x, 0.5 * np.cross(z, [0, 0, -1.0])])
            if np.linalg.norm(err) < 2e-5:
                break
            jp = np.zeros((3, m.nv)); jr = np.zeros((3, m.nv)); mujoco.mj_jacSite(m, d, jp, jr, site)
            J = np.vstack([jp, 0.5 * jr])[:, :7]
            JJ = J.T @ np.linalg.inv(J @ J.T + 1e-4 * np.eye(6))
            # Posture de repos dans le noyau : le 7e degré de liberté ne dérive pas vers une butée.
            dq = JJ @ err + 0.05 * (np.eye(7) - JJ @ J) @ (rest - d.qpos[:7])
            d.qpos[:7] += np.clip(dq, -0.15, 0.15)
            for j in range(7):
                if m.jnt_limited[j]:
                    d.qpos[j] = np.clip(d.qpos[j], *m.jnt_range[j])
        mujoco.mj_forward(m, d)
        return float(np.linalg.norm(goal - d.site_xpos[site]))

    def ik(tip, iters=80):
        goal = tip + np.array([0, 0, TIP])
        e = solve(goal, iters)
        if e > 1e-3:  # minimum local : on repart de la posture de peinture, puis du repos usine
            for seed_q in (rest, home):
                d.qpos[:7] = seed_q; e = solve(goal, 400)
                if e <= 1e-3:
                    break
            retries[0] += 1
        if held is not None:
            R = d.site_xmat[site].reshape(3, 3)
            q = np.zeros(4); mujoco.mju_mat2Quat(q, R.reshape(-1))
            d.mocap_pos[mocap[held]] = d.site_xpos[site] + R[:, 2] * TIP
            d.mocap_quat[mocap[held]] = q
            mujoco.mj_forward(m, d)
        return e

    home = d.qpos[:7].copy(); rest = home.copy(); retries = [0]
    solve(np.array([CX, 0.0, 0.0065 + TIP + 0.06]), 400)
    rest = d.qpos[:7].copy()  # posture « au-dessus de la toile », servant de repère

    world = np.ones_like(target)

    def upload():
        tex_img = np.ascontiguousarray(np.clip(world, 0, 1).transpose(1, 0, 2))
        arr = np.asarray(Image.fromarray((tex_img * 255).astype(np.uint8)).resize((tw, th), Image.NEAREST))
        m.tex_data[adr:adr + tw * th * 3] = arr.reshape(-1)
        r._gl_context.make_current(); mujoco.mjr_uploadTexture(m, r._mjr_context, tex)

    state = {'n': 0, 'brush': None, 'color': None, 'seconds': 0.0, 'note': '', 'speed': 'temps réel',
             'dips': 0, 'rinses': 0}
    fi = [0]; errs = []; canvas_errs = []

    def frame(camera=None):
        r.update_scene(d, camera or cam); img = Image.fromarray(r.render())
        panel = Image.new('RGB', (W3 + 430, H3), (250, 249, 246)); panel.paste(img, (0, 0))
        g = ImageDraw.Draw(panel); X = W3 + 25
        g.text((X, 16), a.title, fill='black', font=bold)
        panel.paste(Image.fromarray((np.clip(world, 0, 1) * 255).astype(np.uint8)).resize((380, 237), Image.LANCZOS), (X, 50))
        y = 305
        lines = [f"Touches : {state['n']:,} / {len(executed):,}".replace(',', ' '),
                 ('Pinceau : modèle FRIDA, 3,5–7,5 mm' if a.frida_plan else f"Pinceau : {BRUSHES[state['brush']]:.0f} mm")
                 if state['brush'] is not None else 'Pinceau : —',
                 f"Temps de bras estimé : {int(state['seconds'] // 3600)} h {int(state['seconds'] % 3600 // 60):02d}",
                 f"Vitesse de la vidéo : {state['speed']}", state['note']]
        for line in lines:
            g.text((X, y), line, fill='black', font=font); y += 28
        if state['color'] is not None:
            g.text((X, y + 4), 'Couleur :', fill='black', font=font)
            g.rectangle([X + 90, y + 2, X + 150, y + 26], fill=tuple(int(c * 255) for c in state['color']), outline='black')
        g.text((X, H3 - 52), 'Toile 50 × 31 cm · 10 peintures pré-mélangées', fill=(80, 80, 80), font=font)
        g.text((X, H3 - 28), 'Modèle MuJoCo xArm 7 (Menagerie) · simulation', fill=(80, 80, 80), font=font)
        panel.save(frames / f'{fi[0]:05d}.png'); fi[0] += 1

    def move(tip, steps=4, show=True):
        start = d.site_xpos[site].copy() - np.array([0, 0, TIP])
        for k in range(1, steps + 1):
            errs.append(ik(start + (tip - start) * k / steps))
            if show:
                frame()

    up = np.array([0, 0, 0.06])

    def change_brush(new, show=True):
        nonlocal held
        if held is not None:
            rag = np.array([RAG[0], RAG[1], 0.02]); state['note'] = 'nettoyage du pinceau'
            move(rag + up, 4, show); move(rag, 2, show); move(rag + up, 2, show)
            rack = np.array([RACK[held][0], RACK[held][1], 0.06]); state['note'] = 'pinceau reposé'
            move(rack + up, 4, show); move(rack, 2, show)
            d.mocap_pos[mocap[held]] = rack; d.mocap_quat[mocap[held]] = [0, 1, 0, 0]; held = None
            move(rack + up, 2, show)
        rack = np.array([RACK[new][0], RACK[new][1], 0.06]); state['note'] = f'prise du pinceau de {BRUSHES[new]:.0f} mm'
        move(rack + up, 4, show); move(rack, 2, show); held = new; move(rack + up, 2, show)
        state['brush'] = new; state['seconds'] += 30

    def dip(pot, show=True, rinse=False):
        n = (lambda k: k if show else 1)
        if rinse:  # changement de couleur : essuyage sur le chiffon avant le nouveau pot
            rag = np.array([RAG[0], RAG[1], 0.02]); state['note'] = 'essuyage (changement de couleur)'
            move(rag + up, n(4), show); move(rag, n(2), show); move(rag + up, n(2), show)
            state['seconds'] += 8; state['rinses'] += 1
        x, y = POTS[pot]; p = np.array([x, y, 0.046]); state['note'] = 'recharge au pot'
        move(p + up, n(4), show); move(p, n(2), show); move(p + up, n(2), show)
        state['seconds'] += 6; state['dips'] += 1
        for i in range(3):
            m.geom_rgba[m.geom(f'poils{i}').id][:3] = palette[pot] if i == held else (0.15, 0.12, 0.10)

    # Ouverture : tour de la cellule.
    upload()
    for k in range(36):
        c = mujoco.MjvCamera(); c.lookat[:] = cam.lookat; c.distance = 1.5; c.elevation = -28
        c.azimuth = 120 + k * 2.6; state['note'] = 'la cellule de peinture'
        frame(c)
    if a.frida_plan:  # FRIDA peint avec un seul pinceau (modèle de touche mesuré) : celui du milieu du support
        phase_of = [1] * len(executed)
    else:
        phase_of = [int(np.argmin([abs(e['width_mm'] - b) for b in BRUSHES])) for e in executed]
    pot_of = [int(((palette - e['color']) ** 2).sum(1).argmin()) for e in executed]
    shown = {0: 0, 1: 0, 2: 0}; current_pot = None; since_dip = 0
    for idx, e in enumerate(executed):
        ph = phase_of[idx]
        detail = shown[ph] < a.detail
        if state['brush'] != ph:
            change_brush(ph, show=True); current_pot = None
            state['speed'] = 'temps réel'
        if pot_of[idx] != current_pot or since_dip >= 6:
            dip(pot_of[idx], show=detail, rinse=current_pot is not None and pot_of[idx] != current_pot)
            current_pot = pot_of[idx]; since_dip = 0
        state['color'] = palette[pot_of[idx]]
        t = np.linspace(0, 1, 10)[:, None]
        p0, p1, p2 = (np.asarray(v) for v in e['p'])
        P = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
        pts = [to_world(p, mm) for p in P]
        length_mm = float(sum(np.linalg.norm(P[i + 1] - P[i]) for i in range(9)) * mm)
        if detail:
            state['note'] = 'tracé'
            move(pts[0] + up, 4); move(pts[0], 2)
            for k, p in enumerate(pts[1:]):
                errs.append(ik(p)); canvas_errs.append(errs[-1])
                if k % 2 == 1:
                    frame()
        else:
            for p in (pts[0], pts[-1]):
                errs.append(ik(p)); canvas_errs.append(errs[-1])
        fp = painter.footprint(p0, p1, p2, e['width_mm'], painter.hidden, e['seed'])
        if fp is not None:
            painter._apply(world, fp, e['color'])
        state['n'] = idx + 1; since_dip += 1
        state['seconds'] += length_mm / 80 + 0.8 + 0.3
        if detail:
            upload(); move(pts[-1] + up, 2); shown[ph] += 1
            if shown[ph] == a.detail:
                state['speed'] = 'accélérée'
        elif idx % 25 == 0 or idx == len(executed) - 1:
            state['note'] = 'peinture en cours'; upload(); frame()
    change_brush(0, show=False); state['note'] = 'terminé'; upload()
    for k in range(50):
        c = mujoco.MjvCamera(); c.lookat[:] = [0.42, 0, 0.0]; c.distance = 1.1 - k * 0.006
        c.elevation = -35 - k * 0.9; c.azimuth = 215 - k * 0.6
        frame(c)
    stats = {'frames': fi[0], 'strokes': len(executed), 'ik_error_p95_m': float(np.percentile(errs, 95)),
             'ik_error_max_m': float(max(errs)), 'ik_canvas_error_max_m': float(max(canvas_errs)),
             'ik_retries': retries[0], 'grouped_by_color': not a.no_grouping and not a.frida_plan, 'frida_plan': bool(a.frida_plan), 'dips': state['dips'],
             'color_changes': state['rinses'], 'arm_time_estimate_s': round(state['seconds']),
             'learned': res['learned'], 'hidden': res['hidden'], 'psnr_db': res['psnr_db'], 'ssim': res['ssim']}
    (out / 'stats.json').write_text(json.dumps(stats, indent=2), encoding='utf-8')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', '20', '-i', str(frames / '%05d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '22', str(out / 'atelier.mp4')], check=True)
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
