#!/usr/bin/env python3
"""Render Le dernier geste R02 with the generated brush macro and recorded Foley."""
from pathlib import Path
import argparse,json,subprocess
p=argparse.ArgumentParser()
p.add_argument('--legacy',type=Path,default=Path(__file__).resolve().parent.parent)
a=p.parse_args()
root=Path(__file__).resolve().parent
legacy=a.legacy
original=legacy/'sources/v24044gl0000cuei73fog65q7gjmvfc0.mp4'
brush=root/'BOJART_G1_DERNIER_TRAIT_BRUT.mp4'
animated=legacy/'TEST19_SOURCE.mp4'
music=legacy/'V21_MUSIQUE_ORIGINALE.mp3'
foley=root/'FOLEY_PINCEAU_BenDrain_preview.mp3'
out=root/'BOJART_LE_DERNIER_GESTE_R02.mp4'
edl=[
{'shot':'S01','input':0,'source':original.name,'in':9.9,'frames':10,'role':'Regard réel','filters':'crop=256:455:216:150,scale=720:1280'},
{'shot':'S02','input':1,'source':brush.name,'in':1.0,'frames':54,'role':'Nouveau trait de pinceau','filters':'scale=720:1280'},
{'shot':'S03','input':0,'source':original.name,'in':9.8,'frames':12,'role':'Détail de peinture authentique','filters':'crop=220:391:150:380,scale=720:1280'},
{'shot':'S04','input':2,'source':animated.name,'in':0.125,'frames':89,'role':'TEST19 existant — prévisualisation de l’éveil','filters':'scale=720:1280'},
{'shot':'S05','input':0,'source':original.name,'in':8.1,'frames':72,'role':'Révélation authentique','filters':'crop=512:910:0:100,scale=720:1280'},
{'shot':'S06','input':0,'source':original.name,'in':0.2,'frames':15,'role':'Emblème original','filters':'crop=512:550:0:100,scale=640:-2,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black'}
]
vf=[]
frame=0
for i,s in enumerate(edl):
    s['timeline_in_frame']=frame
    frame+=s['frames']
    s['timeline_out_frame_exclusive']=frame
    end=s['in']+s['frames']/24
    vf.append(f"[{s['input']}:v]trim=start={s['in']}:end={end:.9f},setpts=PTS-STARTPTS,{s['filters']},fps=24,trim=end_frame={s['frames']},setsar=1,format=yuv420p[v{i}]")
vf.append(''.join(f'[v{i}]' for i in range(len(edl)))+f'concat=n={len(edl)}:v=1:a=0[v]')
duration=frame/24
# A subdued opening bed, a real recorded brush stroke, then the existing score.
vf += [
'[3:a]asplit=2[bedin][scorein]',
'[bedin]atrim=start=1.5:end=4.6,asetpts=PTS-STARTPTS,highpass=f=90,lowpass=f=700,volume=0.13,afade=t=in:st=0:d=0.25,afade=t=out:st=2.90:d=0.17[bed]',
'[scorein]atrim=start=4.5:end=11.833333,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.22,afade=t=out:st=6.90:d=0.433333,volume=0.65,adelay=3167|3167[score]',
'[4:a]atrim=start=0.49:end=2.07,asetpts=PTS-STARTPTS,atempo=0.9,highpass=f=120,lowpass=f=10000,afade=t=in:st=0:d=0.025,afade=t=out:st=1.64:d=0.115,volume=1.25,adelay=667|667[brush]',
f'[bed][score][brush]amix=inputs=3:duration=longest:normalize=0,atrim=duration={duration:.9f},loudnorm=I=-16:TP=-1.5:LRA=8,aresample=48000[a]'
]
cmd=['ffmpeg','-hide_banner','-loglevel','warning','-y','-i',str(original),'-i',str(brush),'-i',str(animated),'-i',str(music),'-i',str(foley),'-filter_complex',';'.join(vf),'-map','[v]','-map','[a]','-frames:v',str(frame),'-t',str(duration),'-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p','-r','24','-c:a','aac','-ar','48000','-b:a','256k','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(out)]
subprocess.run(cmd,check=True)
info={'title':'Le dernier geste — R02','duration_seconds':duration,'fps':24,'frames':frame,'output':out.name,'shots':edl,'audio':{'recorded_foley':foley.name,'author':'BenDrain','page':'https://freesound.org/people/BenDrain/sounds/488027/','license_declared_by_page':'CC0','asset_quality':'Public high-quality MP3 preview, not original 24-bit WAV','brush_onset_timeline_s':0.667,'score_start_timeline_s':3.167,'score':'Original V21 existing composition, remixed','perceptual_listening':'not_certified'},'status':'Montage d’intention avec G1 terminé ; G2 définitif reste à produire'}
(root/'EDL_R02.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(info,ensure_ascii=False))

