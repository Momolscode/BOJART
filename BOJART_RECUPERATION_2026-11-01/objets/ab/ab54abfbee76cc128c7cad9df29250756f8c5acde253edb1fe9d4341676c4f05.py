#!/usr/bin/env python3
"""File éditoriale locale, inventaire média et retour mesuré. Pas de service en arrière-plan."""
from pathlib import Path
from datetime import date, datetime, timezone
import argparse, json, hashlib, subprocess

ROOT=Path(__file__).resolve().parent
def load(path):
    return json.loads(path.read_text(encoding='utf8'))
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    tmp.replace(path)
def utc():return datetime.now(timezone.utc).isoformat()
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()
def inventory(folder,ledger):
    known={m['sha256'] for m in ledger['media']};added=[]
    for p in sorted(folder.iterdir()):
        if not p.is_file() or p.suffix.lower() not in ['.mp4','.mov','.m4v']:continue
        sha=digest(p)
        if sha in known:continue
        try:
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)],stderr=subprocess.STDOUT))
            v=next(s for s in probe['streams'] if s['codec_type']=='video')
        except (subprocess.CalledProcessError, StopIteration) as e:
            added.append({'file':str(p),'error':'Média non lisible : '+str(e)});continue
        try: media_path=str(p.resolve().relative_to(ROOT))
        except ValueError: media_path=str(p.resolve())
        item={'id':'media_'+sha[:12],'file':media_path,'sha256':sha,'width':v['width'],'height':v['height'],'duration':float(probe['format']['duration']),'created':utc(),'state':'à examiner'}
        ledger['media'].append(item);known.add(sha);added.append(item)
    return added
def stats(ledger):
    groups={}
    for post in ledger['posts']:
        f=post.get('feedback')
        if not f or f['views']<=0:continue
        g=groups.setdefault(post['pillar'],{'posts':0,'views':0,'responses':0})
        g['posts']+=1;g['views']+=f['views'];g['responses']+=f['responses']
    for g in groups.values():g['responses_per_100_views']=round(100*g['responses']/g['views'],2)
    return groups

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,default=ROOT/'state'/'journal.json')
    p.add_argument('--config',type=Path,default=ROOT/'EAGLEMIC_Studio_Creatif.json')
    s=p.add_subparsers(dest='command',required=True)
    scan=s.add_parser('scan');scan.add_argument('folder',type=Path)
    brief=s.add_parser('brief');brief.add_argument('--date',default=date.today().isoformat());brief.add_argument('--out',type=Path,default=ROOT/'briefs')
    feedback=s.add_parser('feedback');feedback.add_argument('id');feedback.add_argument('--views',type=int,required=True);feedback.add_argument('--responses',type=int,required=True);feedback.add_argument('--completion',type=float)
    s.add_parser('status')
    a=p.parse_args();conf=load(a.config)
    ledger=load(a.state) if a.state.exists() else {'version':1,'media':[],'posts':[]}
    if a.command=='scan':
        result=inventory(a.folder,ledger)
    elif a.command=='brief':
        day=date.fromisoformat(a.date)
        previous=next((x for x in ledger['posts'] if x['date']==a.date),None)
        if previous:
            print(json.dumps(previous,ensure_ascii=False,indent=2));return
        ideas=conf['ideas'];used={x['idea_id'] for x in ledger['posts'][-len(ideas)+1:]}
        pool=[x for x in ideas if x['id'] not in used] or ideas
        # Une priorité n'est tirée des résultats qu'après trois publications mesurées par famille.
        evidence=stats(ledger);eligible={k:v for k,v in evidence.items() if v['posts']>=3}
        if len(eligible)>=2 and len(ledger['posts'])%3==2:
            best=max(eligible,key=lambda k:eligible[k]['responses_per_100_views'])
            selected=next((x for x in pool if x['pillar']==best),pool[0]);reason='Essai priorisé sur des réponses réellement renseignées ; ne démontre pas une causalité.'
        else:
            selected=pool[0];reason='Rotation éditoriale sans supposer des performances.'
        result={'id':'brief_'+day.isoformat(),'date':day.isoformat(),'idea_id':selected['id'],'pillar':selected['pillar'],'state':'préparé / à tourner selon les plans','decision':reason,'brief':selected,'media_ids':[m['id'] for m in ledger['media']],'feedback':None}
        ledger['posts'].append(result)
        save(a.out/(day.isoformat()+'.json'),result)
    elif a.command=='feedback':
        if a.views<0 or a.responses<0 or (a.completion is not None and not 0<=a.completion<=1):p.error('Vues et réponses positives ; rétention entre 0 et 1.')
        post=next((x for x in ledger['posts'] if x['id']==a.id),None)
        if not post:p.error('Identifiant de brief introuvable.')
        post['feedback']={'views':a.views,'responses':a.responses,'completion':a.completion,'recorded':utc()}
        post['state']='retour renseigné';result={'recorded':post['id'],'metrics':stats(ledger)}
    else:
        result={'media':len(ledger['media']),'briefs':len(ledger['posts']),'metrics':stats(ledger),'background_worker':False,'publishing_connection':False}
    save(a.state,ledger)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
