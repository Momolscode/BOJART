"""BOJ.ART editorial preparation tied to M03 sources.
No external network, model call, publishing, ads, arbitrary path or credentials.
"""
from __future__ import annotations
from contextlib import closing
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib, json, re, sqlite3, threading, unicodedata, uuid
from core import Rejected, IntegrityError, canonical

ROOT=Path(__file__).resolve().parents[3]
KNOWLEDGE=ROOT/'knowledge/growth'
VERSION='bojart.growth.v1'

def digest(obj):return hashlib.sha256(canonical(obj).encode()).hexdigest()
def read_json(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stamp():return datetime.now(timezone.utc)
def identifier(s):
 if not isinstance(s,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',s):raise Rejected('Identifiant invalide.')
 return s

def hashtags(candidates,limit):
 """Internal editorial budget, not a platform ranking rule."""
 if type(limit)is not int or not 1<=limit<=10:raise Rejected('Budget éditorial invalide.')
 result=[];seen=set()
 for raw in candidates:
  if not isinstance(raw,str):raise Rejected('Hashtag texte attendu.')
  tag=unicodedata.normalize('NFKC',raw).lstrip('#')
  if not tag or len(tag)>60 or not all(c.isalnum() or c=='_' for c in tag):raise Rejected('Hashtag invalide : aucun point, espace ou instruction.')
  key=tag.casefold()
  if key not in seen:
   seen.add(key);result.append('#'+tag)
 return result[:limit]

class GrowthEngine:
 def __init__(self,library,state,knowledge=KNOWLEDGE):
  self.library=library;self.path=Path(state)/'growth.sqlite';self.path.parent.mkdir(parents=True,exist_ok=True)
  self.knowledge=Path(knowledge);self.lock=threading.RLock()
  with closing(self.connect()) as db,db:
   db.execute('CREATE TABLE IF NOT EXISTS packets(id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, request_hash TEXT NOT NULL, body TEXT NOT NULL)')
 def connect(self):
  db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row;return db
 def config(self):
  return {k:read_json(self.knowledge/f) for k,f in [('context','BRAND_CONTEXT.json'),('rules','PLATFORM_RULES.json'),('topics','TOPICS.json')]}
 def status(self):
  c=self.config()
  return {'version':VERSION,'capabilities':{'drafts':True,'persistent_packets':True,'automatic_trends':False,'semantic_media_analysis':False,'connected_accounts':False,'live_publication':False,'ads':False},
   'accounts':c['context']['accounts'],'topics':c['topics']['topics'],'rules':c['rules'],'skills':read_json(self.knowledge/'SKILLS_INSTALLED.json'),
   'notice':'Préparation locale. Horaires, popularités et résultats non mesurés. Aucun envoi réseau.'}
 def snapshot(self,ids):
  out=[]
  for sid in ids:
   s=self.library.segment(sid)
   if s['review']=='rejected':raise Rejected('Un passage refusé ne peut pas être préparé pour publication.')
   self.library.available(s['asset_id'])
   out.append({k:s[k] for k in ['id','asset_id','start','end','kind','review','rights','rights_evidence','revision','tags','label']})
  return out
 def prepare(self,req):
  fields={'request_id','account_key','platform','topic_id','segment_ids','expected_revisions','objective'}
  if not isinstance(req,dict) or set(req)!=fields:raise Rejected('Contrat de préparation invalide.')
  rid=identifier(req['request_id']);c=self.config();platform=req['platform'];key=req['account_key'];topic_id=req['topic_id']
  if not all(isinstance(x,str) for x in [platform,key,topic_id]):raise Rejected('Cibles invalides.')
  if platform not in c['rules']['platforms'] or key not in c['context']['accounts'] or topic_id not in c['topics']['topics']:raise Rejected('Réseau, compte ou thème inconnu.')
  account=c['context']['accounts'][key]
  if account['platform']!=platform:raise Rejected('Le compte ne correspond pas au réseau.')
  if not isinstance(req['objective'],str) or req['objective'] not in {'portfolio','quote'}:raise Rejected('Objectif non pris en charge. Ads et vente automatique absents.')
  ids=req['segment_ids'];revs=req['expected_revisions']
  if not isinstance(ids,list) or not 1<=len(ids)<=12 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):raise Rejected('Sélection unique de 1 à 12 passages requise.')
  if not isinstance(revs,dict) or set(revs)!=set(ids) or any(type(v)is not int or v<1 for v in revs.values()):raise Rejected('Révisions exactes requises.')
  with self.lock:
   selected=self.snapshot(ids)
   if any(s['revision']!=revs[s['id']] for s in selected):raise Rejected('Révision périmée : relire le passage.')
   topic=c['topics']['topics'][topic_id]
   all_tags={t.casefold() for s in selected for t in s['tags']}
   if not set(topic['required_any_tags'])&all_tags:raise Rejected('Les passages ne justifient pas ce sujet. Ajouter une annotation relue, pas un hashtag opportuniste.')
   if not topic['allow_concept'] and any(s['kind']!='authentic_capture' for s in selected):raise Rejected('Ce sujet réel exige des captations authentiques, pas un storyboard ou un extrait mixte.')
   if topic_id=='vfx' and not any(s['kind'] in {'concept','ai_generation','mixed'} for s in selected):raise Rejected('Aucun passage VFX/concept identifié.')
   request_hash=digest(req)
   with closing(self.connect()) as db:
    previous=db.execute('SELECT * FROM packets WHERE request_id=?',(rid,)).fetchone()
   if previous:
    if previous['request_hash']!=request_hash:raise Rejected('Identifiant déjà utilisé pour une autre préparation.')
    packet=json.loads(previous['body']);self.validate(packet['id']);return packet
   rules=c['rules']['platforms'][platform]
   caption=topic.get('account_angle',{}).get(key,topic['caption'])
   if req['objective']=='quote':caption+=' Pour un projet sur mesure, décris ton idée à l’atelier ; faisabilité et devis restent à confirmer.'
   if len(caption)>rules['editorial_caption_budget']:raise Rejected('Légende hors budget interne.')
   tags=hashtags(topic['hashtags'],rules['editorial_hashtag_budget'])
   blockers=['connector_not_connected','rendered_final_video_missing','account_capabilities_not_checked','publication_not_approved','audio_rights_by_destination_unknown']
   if not account.get('handle'):blockers.append('account_identity_unknown')
   if any(s['rights']!='documented' for s in selected):blockers.append('source_publication_rights_unknown')
   if any(s['review']!='approved_internal' for s in selected):blockers.append('artistic_review_required')
   if req['objective']=='quote':blockers+=['offer_and_capacity_not_verified','commercial_disclosure_to_check']
   if topic_id=='vfx':blockers+=['ai_disclosure_to_check','must_not_claim_real_movement']
   if platform=='instagram':blockers.append('current_instagram_limits_to_check')
   created=stamp()
   packet={'schema':VERSION,'id':'post_'+uuid.uuid4().hex,'request_id':rid,'created_at':created.isoformat(),
    'review_after':(created+timedelta(days=c['rules']['review_after_days'])).isoformat(),
    'account_key':key,'account':account,'platform':platform,'objective':req['objective'],'topic_id':topic_id,
    'title':topic['title'],'search_query':topic['query'],'caption':caption,'hashtags':tags,
    'tag_basis':'Taxonomie BOJ.ART et annotations humaines ; aucune tendance ni volume live mesuré.',
    'tag_rationale':[{'tag':t,'reason':'Marque' if t=='#BOJART' else 'Sujet de la rubrique éditoriale corroboré par la sélection'} for t in tags],
    'source_segments':selected,'source_digest':digest(selected),'config_digest':digest(c),'request':req,
    'status':'review_required','blockers':blockers,'live_publish_supported':False,
    'delivery':{'scheduled':False,'published':False,'provider_id':None,'public_url':None},
    'measurement':{'utm_status':'à créer uniquement pour un lien réellement cliquable','unique_audience':None,'performance':None},
    'notes':['Une sélection de passages n’est pas un export vidéo final.','Aucun horaire optimal ni potentiel viral n’est estimé.','Un accord interne ne remplace pas les exigences du réseau.']}
   packet['packet_digest']=digest(packet)
   # Recheck after preparation to avoid silently using a changed context.
   if digest(self.snapshot(ids))!=packet['source_digest'] or digest(self.config())!=packet['config_digest']:raise Rejected('Sources modifiées pendant la préparation.')
   with closing(self.connect()) as db,db:
    db.execute('INSERT OR IGNORE INTO packets VALUES(?,?,?,?)',(packet['id'],rid,request_hash,canonical(packet)))
    stored=db.execute('SELECT request_hash,body FROM packets WHERE request_id=?',(rid,)).fetchone()
    if stored['request_hash']!=request_hash:raise Rejected('Identifiant concurrent utilisé pour une autre préparation.')
    packet=json.loads(stored['body'])
   self.validate(packet['id'])
   return packet
 def get(self,pid):
  identifier(pid)
  with closing(self.connect()) as db:row=db.execute('SELECT body FROM packets WHERE id=?',(pid,)).fetchone()
  if not row:raise Rejected('Préparation inconnue.')
  return json.loads(row['body'])
 def validate(self,pid):
  p=self.get(pid);body={k:v for k,v in p.items() if k!='packet_digest'}
  if digest(body)!=p['packet_digest']:raise IntegrityError('Préparation altérée.')
  if stamp()>datetime.fromisoformat(p['review_after']):raise Rejected('Règles à relire : préparation trop ancienne.')
  if digest(self.config())!=p['config_digest']:raise Rejected('Contexte ou politique modifiés : refaire la préparation.')
  if digest(self.snapshot([s['id'] for s in p['source_segments']]))!=p['source_digest']:raise Rejected('Annotations modifiées : refaire la préparation.')
  return {'packet_id':pid,'sources_intact':True,'live_publish_supported':False,'ready_to_publish':False,'blockers':p['blockers']}
