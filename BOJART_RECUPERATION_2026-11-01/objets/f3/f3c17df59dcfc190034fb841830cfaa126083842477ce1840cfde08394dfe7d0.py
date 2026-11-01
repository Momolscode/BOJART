#!/usr/bin/env python3
"""BOJ.ART - Contrôles techniques automatisés non destructifs.
N'évalue PAS la qualité artistique, les droits, ni la fidélité du visage.
Usage: python qc_video.py video.mp4 [video2.mp4 ...] --out dossier
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
import cv2
import numpy as np

def probe(path):
    raw=subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],text=True)
    return json.loads(raw)

def loudness(path):
    p=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-vn','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True)
    t=p.stderr
    sections=t.split('Summary:')
    if len(sections)<2:
        return {'status':'unavailable','note':'No ebur128 summary; check audio manually'}
    s=sections[-1]
    def extract(pattern):
        m=re.search(pattern,s)
        return float(m.group(1)) if m else None
    return {'integrated_lufs':extract(r'Integrated loudness:\s*I:\s*(-?\d+(?:\.\d+)?)\s*LUFS'),
            'lra_lu':extract(r'Loudness range:\s*LRA:\s*(-?\d+(?:\.\d+)?)\s*LU'),
            'true_peak_dbfs':extract(r'True peak:\s*Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS')}

def scan(path):
    p=Path(path)
    info=probe(p)
    v=next((s for s in info['streams'] if s['codec_type']=='video'),None)
    a=next((s for s in info['streams'] if s['codec_type']=='audio'),None)
    if v is None: raise ValueError('No video stream: '+str(p))
    cap=cv2.VideoCapture(str(p)); fps=cap.get(cv2.CAP_PROP_FPS) or 0
    frame_idx=0; prev=None; black=[]; nearstatic=[]; changes=[]
    while True:
        ok,frame=cap.read()
        if not ok:break
        gray=cv2.cvtColor(cv2.resize(frame,(120,214)),cv2.COLOR_BGR2GRAY).astype(np.float32)
        if float(np.mean(gray))<7.0: black.append(frame_idx)
        if prev is not None:
            mad=float(np.mean(np.abs(gray-prev)))
            changes.append((frame_idx,mad))
            if mad<0.12: nearstatic.append(frame_idx)
        prev=gray;frame_idx+=1
    cap.release()
    def ranges(values):
        groups=[]
        for i in values:
            if not groups or i>groups[-1][-1]+1: groups.append([i])
            else: groups[-1].append(i)
        return [{'start_frame':g[0],'end_frame':g[-1],'duration_s':round(len(g)/fps,3)} for g in groups if fps and len(g)/fps>=0.125]
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    warnings=[]
    w,he=v.get('width'),v.get('height')
    if w/he!=9/16:warnings.append('not_native_9x16')
    if w<1080 or he<1920:warnings.append('below_1080x1920')
    if not a:warnings.append('no_audio')
    if not all(v.get(k) for k in ('color_space','color_primaries','color_transfer')):warnings.append('color_metadata_unspecified')
    if fps not in (24.0,25.0,30.0,50.0,60.0):warnings.append('nonstandard_fps_review')
    return {'file':p.name,'sha256':h.hexdigest(),'size_bytes':p.stat().st_size,
            'duration_s':round(float(info['format'].get('duration',0)),3),
            'video':{'codec':v.get('codec_name'),'resolution':[w,he],'fps':round(fps,3),'frames_probed':v.get('nb_frames'),'frames_decoded':frame_idx,'pixel_format':v.get('pix_fmt'),'color_space':v.get('color_space'),'color_primaries':v.get('color_primaries'),'color_transfer':v.get('color_transfer')},
            'audio':None if not a else {'codec':a.get('codec_name'),'channels':a.get('channels'),'sample_rate':a.get('sample_rate'),'loudness':loudness(p)},
            'black_ranges':ranges(black),'nearly_static_ranges':ranges(nearstatic),
            'largest_frame_changes':[{'time_s':round(i/fps,3),'gray_MAD':round(d,2)} for i,d in sorted(changes,key=lambda x:-x[1])[:8]] if fps else [],
            'warnings':warnings,
            'interpretation_note':'Image brightness/MAE and audio metrics do not certify 3D depth, character fidelity, music quality, SFX alignment, or artistic excellence.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('videos',nargs='+');ap.add_argument('--out',default='.')
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for file in args.videos:
        r=scan(file);dest=out/(Path(file).stem+'_QC.json');dest.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        print(dest, r['duration_s'],r['video']['resolution'],r['warnings'],r['audio']['loudness'] if r['audio'] else 'silent')
