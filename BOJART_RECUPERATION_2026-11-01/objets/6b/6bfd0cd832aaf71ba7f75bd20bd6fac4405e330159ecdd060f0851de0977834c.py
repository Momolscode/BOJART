#!/usr/bin/env python3
"""Inspecter un export et créer une image de contact, sans jugement artistique automatique."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video',type=Path)
    p.add_argument('--contact',type=Path)
    p.add_argument('--report',type=Path)
    a=p.parse_args()
    if not a.video.is_file():p.error('Fichier vidéo introuvable.')
    probe=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(a.video)],capture_output=True,text=True,check=True)
    meta=json.loads(probe.stdout)
    videos=[s for s in meta['streams'] if s['codec_type']=='video']
    if not videos:p.error('Aucun flux vidéo.')
    v=videos[0];duration=float(meta['format']['duration'])
    if duration<=0:p.error('Durée invalide.')
    check=subprocess.run(['ffmpeg','-hide_banner','-v','error','-i',str(a.video),'-f','null','-'],capture_output=True,text=True)
    h=hashlib.sha256()
    with a.video.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    result={'file':str(a.video.resolve()),'sha256':h.hexdigest(),'duration_seconds':duration,'width':v['width'],'height':v['height'],'fps':v.get('avg_frame_rate'),'video_codec':v['codec_name'],'audio_streams':sum(s['codec_type']=='audio' for s in meta['streams']),'decode_ok':check.returncode==0 and not check.stderr.strip(),'decode_error':check.stderr.strip()[:1500],'artistic_review':'À effectuer visuellement ; le script ne valide aucune ressemblance, narration ou qualité sonore.'}
    if a.contact:
        a.contact.parent.mkdir(parents=True,exist_ok=True)
        vf=f'fps=9/{duration},scale=270:480:force_original_aspect_ratio=decrease,pad=270:480:(ow-iw)/2:(oh-ih)/2,tile=3x3'
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(a.video),'-vf',vf,'-frames:v','1',str(a.contact)],check=True)
        result['contact']=str(a.contact.resolve())
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(text+'\n',encoding='utf8')
    print(text)
    return 0 if result['decode_ok'] else 1

if __name__=='__main__':sys.exit(main())

