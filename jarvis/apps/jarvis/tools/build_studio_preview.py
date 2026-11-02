from pathlib import Path
import sys,tempfile,subprocess,json,base64,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from media_library import MediaLibrary
from studio_seed import seed

def run(args):subprocess.run(args,check=True,stdin=subprocess.DEVNULL,capture_output=True)
def b64(p,mime):return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode()
with tempfile.TemporaryDirectory() as td:
 lib=MediaLibrary(td,[ROOT/'studio_media']);cat=seed(lib,ROOT/'studio_media')
 thumbs={};proxies={}
 for s in cat['segments']:
  src=lib.available(s['asset_id']);out=ROOT/'studio_assets'/f'{s["id"]}.jpg'
  run(['ffmpeg','-y','-v','error','-ss',str((s['start']+s['end'])/2),'-i',str(src),'-frames:v','1','-vf','scale=240:-2','-q:v','3',str(out)])
  thumbs[s['id']]=b64(out,'image/jpeg')
  if s['asset_id'] not in proxies:
   proxy=Path(td)/(s['asset_id']+'.mp4')
   run(['ffmpeg','-y','-v','error','-i',str(src),'-map','0:v:0','-map','0:a?','-vf','scale=360:-2','-c:v','libx264','-preset','veryfast','-crf','26','-c:a','aac','-b:a','64k','-movflags','+faststart',str(proxy)])
   proxies[s['asset_id']]=b64(proxy,'video/mp4')
 req={'request_id':'studio-demo-001','anchor_id':'visage','segment_ids':['profil','troisquarts','visage'],'expected_revisions':{'profil':1,'troisquarts':1,'visage':1}}
 plan=lib.prepare(req);ver=lib.validate_plan(plan)
 verified_backup=lib.export_archive(Path(td)/'sources.zip')
 for name,data in [('CATALOGUE_VERIFIE.json',cat),('BRIEF_PREPARE.json',plan),('VERIFICATION_BRIEF.json',ver),('VERIFICATION_ARCHIVE.json',verified_backup)]:
  (ROOT/'preuves_m03'/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
 data={'catalogue':cat,'thumbs':thumbs,'proxies':proxies,'plan':plan,'verification':ver}
 html=(ROOT/'app/studio.html').read_text().replace('<link rel="stylesheet" href="/studio.css">','<style>'+(ROOT/'app/studio.css').read_text()+'</style>')
 js=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
 html=html.replace('<script src="/studio.js"></script>','<script>window.DEMO_STUDIO='+js+';</script><script>'+(ROOT/'app/studio.js').read_text()+'</script>')
 (ROOT/'APERCU_STUDIO_M03.html').write_text(html)
 lib.close()
 print(json.dumps({'assets':cat['asset_count'],'segments':len(cat['segments']),'html_bytes':len(html.encode()),'backup':verified_backup},ensure_ascii=False))
