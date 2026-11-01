#!/usr/bin/env python3
"""Numerical motion/affine/audio bench visualization; not a narrative film."""
from pathlib import Path
import math
import json
import subprocess
import sys
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'motion'))
from motion_primitives import cubic_in_out, sine_in_out, bounce_out, Affine2D


def main():
    out = ROOT / 'demo'
    internal = out / 'internal'
    internal.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ROOT / 'audio/filtre_passe_bas_1200hz.wav'), 'rb') as w:
        params = w.getparams()
        filtered_raw = w.readframes(w.getnframes())
    with wave.open(str(ROOT / 'audio/source_synthetique.wav'), 'rb') as w:
        source_raw = w.readframes(w.getnframes())
    audio = out / 'demo_audio.wav'
    with wave.open(str(audio), 'wb') as w:
        w.setparams(params)
        w.writeframes(filtered_raw * 2)
    source = np.frombuffer(source_raw, dtype='<i2').reshape(-1, params.nchannels)[:, 0] / 32768
    filtered = np.frombuffer(filtered_raw, dtype='<i2').reshape(-1, params.nchannels)[:, 0] / 32768
    font_dir = Path('/usr/share/fonts/truetype/dejavu')
    def font(size, bold=False):
        return ImageFont.truetype(str(font_dir / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)
    bg = (238, 235, 222); ink = (33, 48, 39); card = (250, 248, 240)
    blue = (45, 114, 140); green = (103, 128, 73); muted = (119, 125, 115)
    video = out / 'MARWIN_REA_Briques_Verifiees_6s.mp4'
    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y', '-f', 'rawvideo',
           '-pixel_format', 'rgb24', '-video_size', '720x1280', '-framerate', '30',
           '-i', 'pipe:0', '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-shortest', str(video)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    samples = []
    for frame in range(180):
        progress = frame / 179
        im = Image.new('RGB', (720, 1280), bg)
        d = ImageDraw.Draw(im)
        d.text((42, 34), 'MARWIN STUDIO / LAB', font=font(30, True), fill=ink)
        d.text((42, 82), 'Briques reconstruites avec REA', font=font(23), fill=muted)
        d.text((42, 119), 'BANC D’ESSAI TECHNIQUE', font=font(18, True), fill=blue)
        for y0, y1 in [(175, 477), (497, 840), (860, 1198)]:
            d.rounded_rectangle((28, y0, 692, y1), radius=23, fill=card)
        d.text((48, 192), '01  MOUVEMENT', font=font(25, True), fill=ink)
        d.text((48, 230), '3 courbes lues dans le binaire', font=font(20), fill=muted)
        x0, y0, width, height = 65, 420, 580, 130
        d.line((x0, y0, x0 + width, y0), fill=(201, 204, 190), width=2)
        d.line((x0, y0, x0, y0 - height), fill=(201, 204, 190), width=2)
        curves = [(cubic_in_out, blue, 'Cubic'), (sine_in_out, green, 'Sine'),
                  (bounce_out, (166, 119, 67), 'Bounce')]
        for i, (f, color, name) in enumerate(curves):
            pts = [(x0 + width * t, y0 - height * f(t)) for t in np.linspace(0, 1, 180)]
            d.line(pts, fill=color, width=3)
            cx, cy = x0 + width * progress, y0 - height * f(progress)
            d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=color)
            d.text((65 + i*190, 442), name, font=font(17, True), fill=color)
        d.text((48, 515), '02  TRANSFORMATION', font=font(25, True), fill=ink)
        d.text((48, 554), 'Matrice affine : ordre contrôlé', font=font(20), fill=muted)
        scale = .83 + .17 * bounce_out(progress)
        angle = .13 * math.sin(2 * math.pi * progress)
        matrix = Affine2D.scale(scale, scale).append(Affine2D.rotation(angle)).append(
            Affine2D.translation(260 + 200*cubic_in_out(progress), 694))
        corners = [matrix.transform(x,y) for x,y in [(-132,-65),(132,-65),(132,65),(-132,65)]]
        d.polygon(corners, fill=(222, 226, 205))
        d.line(corners + [corners[0]], fill=ink, width=4)
        def segment(a, b, fill=ink, width=3):
            d.line([matrix.transform(*a), matrix.transform(*b)], fill=fill, width=width)
        segment((-132, -20), (132, -20), green)
        for k in range(11):
            segment((-88+k*10, 12), (-88+k*10, 43), blue, 2 if k%3 else 4)
        pivot = matrix.transform(0,0)
        d.ellipse((pivot[0]-6,pivot[1]-6,pivot[0]+6,pivot[1]+6),fill=(176,85,58))
        d.text((48, 797), 'Translation • rotation • échelle', font=font(20), fill=muted)
        d.text((48, 879), '03  SON', font=font(25, True), fill=ink)
        d.text((48, 918), 'Passe-bas reconstruit : 1 200 Hz', font=font(20), fill=muted)
        # Same 240 original PCM samples shown throughout; a cursor indicates progress.
        positions = np.arange(240) + round(.7 * params.framerate)
        for signal, baseline, color, label in [(source, 1010, (173,178,166), 'Source'),
                                               (filtered, 1100, blue, 'Filtré')]:
            pts = [(62 + i*2.48, baseline - 100*float(signal[j])) for i,j in enumerate(positions)]
            d.line(pts,fill=color,width=2)
            d.text((58,baseline-56),label,font=font(17),fill=color)
        d.text((48, 1160), 'Signal original • fenêtre réelle de 5 ms',font=font(18),fill=muted)
        d.text((42, 1230), 'Prototype de briques / 6 s / 30 i/s',font=font(19),fill=muted)
        p.stdin.write(im.tobytes())
        if frame in [0,59,119,179]:
            im.save(internal/f'frame_{frame:03d}.png')
            samples.append({'frame':frame,'progress':progress,'pivot':pivot})
    p.stdin.close()
    error=p.stderr.read().decode();rc=p.wait()
    if rc:raise RuntimeError(error)
    qa={'kind':'numerical_bench_visualization_not_finished_narrative_film',
        'frames':180,'fps':30,'duration_s':6,'size':[720,1280],
        'uses_reconstructed_motion_and_affine':True,'audio_source':'original synthetic test tone, lowpass output repeated twice',
        'actor_or_identity_generated':False,'audience_test':False,'human_listening':False,
        'static_waveform_display':'240 PCM samples at 0.7 seconds; static 5 ms comparison, no playback cursor',
        'sampled_visual_states':samples}
    (out/'demo_recipe.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    print(video)


if __name__=='__main__':
    main()
