#!/usr/bin/env python3
"""R03: cut on the existing fist movement before the face leaves TEST19."""
from pathlib import Path
import argparse
import json
import subprocess

root = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--legacy', type=Path, default=root.parent)
p.add_argument('--r02', type=Path, default=root.parent / 'R02_LE_DERNIER_GESTE')
a = p.parse_args()
original = a.legacy / 'sources/v24044gl0000cuei73fog65q7gjmvfc0.mp4'
brush = a.r02 / 'BOJART_G1_DERNIER_TRAIT_BRUT.mp4'
animated = a.legacy / 'TEST19_SOURCE.mp4'
music = a.legacy / 'V21_MUSIQUE_ORIGINALE.mp3'
foley = a.r02 / 'FOLEY_PINCEAU_BenDrain_preview.mp3'
out = root / 'BOJART_LE_DERNIER_GESTE_R03.mp4'
edl = [
    {'shot': 'S01', 'input': 0, 'source': original.name, 'in': 9.9, 'frames': 10, 'role': 'Regard réel', 'filters': 'crop=256:455:216:150,scale=720:1280'},
    {'shot': 'S02', 'input': 1, 'source': brush.name, 'in': 1.25, 'frames': 48, 'role': 'G1 déjà généré — contact, trait et retrait du pinceau', 'filters': 'scale=720:1280'},
    {'shot': 'S03', 'input': 0, 'source': original.name, 'in': 9.8, 'frames': 10, 'role': 'Peinture authentique', 'filters': 'crop=220:391:150:380,scale=720:1280'},
    {'shot': 'S04', 'input': 2, 'source': animated.name, 'in': 3/24, 'frames': 40, 'role': 'TEST19 historique — mouvement du corps, visage encore cadré', 'filters': 'scale=720:1280'},
    {'shot': 'S05', 'input': 2, 'source': animated.name, 'in': 43/24, 'frames': 24, 'role': 'Même TEST19 — raccord continu sur la fermeture du poing', 'filters': 'crop=360:640:80:570,scale=720:1280'},
    {'shot': 'S06', 'input': 0, 'source': original.name, 'in': 8.1, 'frames': 72, 'role': 'Révélation authentique', 'filters': 'crop=512:910:0:100,scale=720:1280'},
    {'shot': 'S07', 'input': 0, 'source': original.name, 'in': 0.2, 'frames': 18, 'role': 'Emblème original', 'filters': 'crop=512:550:0:100,scale=640:-2,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black'},
]
vf = []
frame = 0
for i, s in enumerate(edl):
    s['timeline_in_frame'] = frame
    frame += s['frames']
    s['timeline_out_frame_exclusive'] = frame
    end = s['in'] + s['frames']/24
    vf.append(f"[{s['input']}:v]trim=start={s['in']:.9f}:end={end:.9f},setpts=PTS-STARTPTS,{s['filters']},fps=24,trim=end_frame={s['frames']},setsar=1,format=yuv420p[v{i}]")
vf.append(''.join(f'[v{i}]' for i in range(len(edl))) + f'concat=n={len(edl)}:v=1:a=0[v]')
duration = frame/24
vf += [
    '[3:a]asplit=2[bedin][scorein]',
    '[bedin]atrim=start=1.5:end=4.237,asetpts=PTS-STARTPTS,highpass=f=90,lowpass=f=700,volume=0.13,afade=t=in:st=0:d=0.25,afade=t=out:st=2.567:d=0.17[bed]',
    '[scorein]atrim=start=4.75:end=11.167,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.22,afade=t=out:st=5.917:d=0.5,volume=0.65,adelay=2833|2833[score]',
    '[4:a]atrim=start=0.49:end=2.07,asetpts=PTS-STARTPTS,atempo=0.9,highpass=f=120,lowpass=f=10000,afade=t=in:st=0:d=0.025,afade=t=out:st=1.64:d=0.115,volume=1.25,adelay=467|467[brush]',
    f'[bed][score][brush]amix=inputs=3:duration=longest:normalize=0,atrim=duration={duration:.9f},loudnorm=I=-16:TP=-1.5:LRA=8,aresample=48000[a]',
]
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y']
for src in [original, brush, animated, music, foley]:
    cmd += ['-i', str(src)]
cmd += ['-filter_complex', ';'.join(vf), '-map', '[v]', '-map', '[a]', '-frames:v', str(frame), '-t', str(duration), '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', '24', '-c:a', 'aac', '-ar', '48000', '-b:a', '256k', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart', str(out)]
subprocess.run(cmd, check=True)
info = {
    'title': 'Le dernier geste — R03', 'date': '2026-11-01',
    'duration_seconds': duration, 'fps': 24, 'frames': frame, 'output': out.name,
    'shots': edl,
    'change_from_R02': 'Passage de 10,5 à 9,25 s. Coupe avant la sortie du visage ; détail du poing raccordé dans la continuité du même TEST19. G1 resserré de six images, emblème tenu trois images de plus.',
    'new_generations_this_pass': 0, 'generation_credits_spent_this_pass': 0,
    'audio': {
        'score': 'Composition originale V21 existante, nouvelle coupe',
        'score_source_in_s': 4.75, 'score_timeline_in_s': 2.833,
        'brush_timeline_in_s': 0.467,
        'recorded_foley': foley.name, 'author': 'BenDrain',
        'page': 'https://freesound.org/people/BenDrain/sounds/488027/',
        'license_declared_by_page': 'CC0',
        'asset_quality': 'Préécoute MP3 publique, pas original WAV',
        'perceptual_listening': 'non vérifiée',
    },
    'status': 'Nouvelle coupe de prévisualisation. G2 définitif non produit ; TEST19 reste un essai historique.',
}
(root/'EDL_R03.json').write_text(json.dumps(info, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'output': str(out), 'frames': frame, 'duration': duration}, ensure_ascii=False))
