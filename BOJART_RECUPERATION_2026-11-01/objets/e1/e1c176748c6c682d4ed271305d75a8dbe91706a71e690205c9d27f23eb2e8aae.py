#!/usr/bin/env python3
"""BOJ.ART — cut built from a new material insert and identified existing footage."""
from pathlib import Path
import subprocess,json
root=Path(__file__).resolve().parent
original=root/'sources/v24044gl0000cuei73fog65q7gjmvfc0.mp4'
material=root/'BOJART_INSERT_PEINTURE_BRUT.mp4'
animated=root/'TEST19_SOURCE.mp4'
music=root/'V21_MUSIQUE_ORIGINALE.mp3'
output=root/'BOJART_REPRISE01_L_ART_PREND_CORPS.mp4'
# In/out values in source seconds; durations are exact output-frame counts at 24 fps.
edl=[
{'shot':'S01','source':original.name,'in':9.9,'frames':10,'role':'Authentic eye/face insert'},
{'shot':'S02','source':material.name,'in':0.25,'frames':36,'role':'New generated paint motion; separate material fiction'},
{'shot':'S03','source':original.name,'in':9.5,'frames':10,'role':'Authentic burgundy paint/shorts detail'},
{'shot':'S04','source':original.name,'in':8.25,'frames':16,'role':'Authentic workshop profile'},
{'shot':'S05','source':animated.name,'in':0.125,'frames':84,'role':'Existing TEST19 animated fist/shoulder movement'},
{'shot':'S06','source':original.name,'in':10.0,'frames':28,'role':'Return to real sculpture and camera move'},
{'shot':'S07','source':original.name,'in':0.2,'frames':18,'role':'Existing BOJ.ART emblem, final signature'}
]
def clip(inp,shot,filters):
    end=shot['in']+shot['frames']/24
    return f"{inp}trim=start={shot['in']}:end={end:.9f},setpts=PTS-STARTPTS,{filters},fps=24,trim=end_frame={shot['frames']},setsar=1,format=yuv420p"
filters=[]
base="scale=720:1280"
filters.append(clip('[0:v]',edl[0],"crop=256:455:216:150,"+base)+'[s0]')
filters.append(clip('[1:v]',edl[1],base)+'[s1]')
filters.append(clip('[0:v]',edl[2],"crop=192:342:180:570,"+base)+'[s2]')
filters.append(clip('[0:v]',edl[3],"crop=512:910:0:100,"+base)+'[s3]')
filters.append(clip('[2:v]',edl[4],base)+'[s4]')
filters.append(clip('[0:v]',edl[5],"crop=512:910:0:100,"+base)+'[s5]')
filters.append(clip('[0:v]',edl[6],"crop=512:550:0:100,scale=640:-2,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black")+'[s6]')
filters.append('[s0][s1][s2][s3][s4][s5][s6]concat=n=7:v=1:a=0[v]')
duration=sum(s['frames'] for s in edl)/24
filters.append(f"[3:a]adelay=367|367,atrim=duration={duration:.9f},asetpts=PTS-STARTPTS,volume='if(between(t,1.06,1.16),0.16,0.82)':eval=frame,afade=t=in:st=0.367:d=0.10,afade=t=out:st={duration-.42:.9f}:d=0.42,loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000[a]")
cmd=['ffmpeg','-hide_banner','-loglevel','warning','-y','-i',str(original),'-i',str(material),'-i',str(animated),'-i',str(music),'-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-frames:v',str(sum(s['frames'] for s in edl)),'-t',str(duration),'-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-b:a','256k','-ar','48000','-r','24','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(output)]
subprocess.run(cmd,check=True)
time=0
for s in edl:
    s['timeline_in_frame']=time
    time+=s['frames']
    s['timeline_out_frame_exclusive']=time
data={'title':"L’art prend corps — reprise 01",'fps':24,'frames':time,'duration_s':duration,'output':output.name,'shots':edl,'audio':{'source':music.name,'delay_ms':367,'original_source_audio_used':False,'new_foley_recorded':False,'status':'Work music edit; no headphone/mobile perceptual listening certified'},'status':'First editorial cut for review; not an approved final master'}
(root/'EDL_REPRISE01.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(data,ensure_ascii=False))

