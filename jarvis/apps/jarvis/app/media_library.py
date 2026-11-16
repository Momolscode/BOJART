"""BOJ.ART studio media register. Local, bounded, no model, no paid call.
File origin and segment semantics are deliberately distinct. A montage uploaded by
its owner is not proof that every frame is an authentic capture of the sculpture.
"""
from __future__ import annotations
import contextlib, hashlib, json, math, os, re, sqlite3, subprocess, threading, unicodedata, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
from core import Rejected, IntegrityError, canonical

VERSION='bojart.studio.v1'
KINDS={'authentic_capture','ai_generation','concept','mixed','unknown'}
ORIGINS={'user_upload','assistant_render','unknown'}
REVIEWS={'unreviewed','approved_internal','rejected'}
RIGHTS={'unknown','internal_only','documented'}
MAX_FILE=64*1024*1024

def now():return datetime.now(timezone.utc).isoformat()
def sha(data):return hashlib.sha256(data).hexdigest()
def digest_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def normalized(s):return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))
def text(value,n=200):
 if not isinstance(value,str) or not value.strip() or len(value)>n:raise Rejected('Texte vide ou trop long.')
 return value.strip()
def number(v):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise Rejected('Nombre fini requis.')
 return float(v)
def probe(path):
 """Metadata only. FFprobe network protocols are not permitted."""
 args=['ffprobe','-v','error','-max_alloc','67108864','-protocol_whitelist','file','-format_whitelist','mov,matroska,webm','-probesize','10000000',
       '-analyzeduration','3000000','-of','json','-show_entries',
       'format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate',str(path)]
 try:p=subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15,check=False)
 except (OSError,subprocess.TimeoutExpired) as e:raise Rejected('FFprobe absent ou délai dépassé.') from e
 if p.returncode or len(p.stdout)>200000:raise Rejected('Média illisible : aucun état prêt enregistré.')
 try:
  data=json.loads(p.stdout);video=next(s for s in data['streams'] if s['codec_type']=='video')
  dur=float(data['format']['duration']);w=int(video['width']);h=int(video['height'])
  if not math.isfinite(dur) or not 0<dur<=86400 or not 0<w<=32768 or not 0<h<=32768:raise ValueError()
  return {'duration':dur,'width':w,'height':h,'fps':video.get('avg_frame_rate','unknown'),
          'codec':video.get('codec_name','unknown'),'audio':any(s.get('codec_type')=='audio' for s in data['streams'])}
 except (ValueError,KeyError,StopIteration,TypeError) as e:raise Rejected('Métadonnées vidéo invalides.') from e

class MediaLibrary:
 def __init__(self,state,roots,probe_fn=probe):
  self.state=Path(state);self.state.mkdir(parents=True,exist_ok=True)
  self.roots=[Path(r).resolve(strict=True) for r in roots]
  if not self.roots or any(not r.is_dir() for r in self.roots):raise Rejected('Dossiers explicitement autorisés requis.')
  self.probe_fn=probe_fn;self.lock=threading.RLock()
  self.db=sqlite3.connect(self.state/'media.sqlite',check_same_thread=False)
  self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA foreign_keys=ON')
  self.db.executescript('''CREATE TABLE IF NOT EXISTS assets(
   id TEXT PRIMARY KEY, label TEXT NOT NULL, origin TEXT NOT NULL, metadata TEXT NOT NULL,
   provenance TEXT NOT NULL, created TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS locations(path TEXT PRIMARY KEY,asset_id TEXT NOT NULL REFERENCES assets(id));
   CREATE TABLE IF NOT EXISTS segments(id TEXT PRIMARY KEY,asset_id TEXT NOT NULL REFERENCES assets(id),
   label TEXT NOT NULL,start REAL NOT NULL,end REAL NOT NULL,kind TEXT NOT NULL,review TEXT NOT NULL,
   rights TEXT NOT NULL,rights_evidence TEXT NOT NULL,identity_anchor INTEGER NOT NULL,
   evidence TEXT NOT NULL,tags TEXT NOT NULL,revision INTEGER NOT NULL);
   CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,request_hash TEXT NOT NULL,body TEXT NOT NULL);
   ''');self.db.commit()
 def close(self):self.db.close()
 def safe_path(self,path):
  p=Path(path).absolute()
  if p.is_symlink() or any(x.is_symlink() for x in p.parents):raise Rejected('Lien symbolique refusé.')
  try:resolved=p.resolve(strict=True)
  except OSError as e:raise Rejected('Fichier indisponible.') from e
  if not any(resolved.is_relative_to(r) for r in self.roots):raise Rejected('Fichier hors dossiers autorisés.')
  if resolved.suffix.lower() not in {'.mp4','.mov','.mkv','.webm'} or not resolved.is_file():raise Rejected('Vidéo locale attendue.')
  if not 0<resolved.stat().st_size<=MAX_FILE:raise Rejected('Ce pilote accepte au maximum 64 Mio par fichier.')
  return resolved
 def ingest(self,path,label,origin,provenance):
  if origin not in ORIGINS:raise Rejected('Origine inconnue.')
  label=text(label);provenance=text(provenance,2000);p=self.safe_path(path)
  before=digest_file(p);meta=self.probe_fn(p)
  if before!=digest_file(p):raise IntegrityError('Source modifiée pendant la lecture.')
  with self.lock,self.db:
   existing=self.db.execute('SELECT * FROM assets WHERE id=?',(before,)).fetchone()
   if not existing:self.db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?)',(before,label,origin,canonical(meta),provenance,now()))
   elif existing['origin']!=origin:raise Rejected('Origine contradictoire pour un contenu déjà connu.')
   self.db.execute('INSERT INTO locations VALUES(?,?) ON CONFLICT(path) DO UPDATE SET asset_id=excluded.asset_id',(str(p),before))
  return before
 def asset(self,asset_id):
  with self.lock:
   row=self.db.execute('SELECT * FROM assets WHERE id=?',(asset_id,)).fetchone()
   if not row:raise Rejected('Média inconnu.')
   d=dict(row);d['metadata']=json.loads(d['metadata']);return d
 def available(self,asset_id):
  """No stale path is silently rebound to a newly changed file."""
  with self.lock:paths=[r[0] for r in self.db.execute('SELECT path FROM locations WHERE asset_id=?',(asset_id,))]
  for path in paths:
   try:
    p=self.safe_path(path)
    if digest_file(p)==asset_id:return p
   except (Rejected,OSError):continue
  raise IntegrityError('Original absent ou modifié ; ne pas substituer un autre fichier.')
 def read_blob(self,asset_id):
  p=self.available(asset_id);data=p.read_bytes()
  if sha(data)!=asset_id:raise IntegrityError('Le fichier a changé pendant sa lecture.')
  return data
 def segment(self,sid):
  with self.lock:row=self.db.execute('SELECT * FROM segments WHERE id=?',(sid,)).fetchone()
  if not row:raise Rejected('Passage inconnu.')
  d=dict(row);d['tags']=json.loads(d['tags']);d['identity_anchor']=bool(d['identity_anchor']);return d
 def annotate(self,sid,asset_id,label,start,end,kind,review='unreviewed',rights='unknown',rights_evidence='',
              identity_anchor=False,evidence='',tags=None,expected_revision=None):
  if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',sid):raise Rejected('Identifiant de passage invalide.')
  a=self.asset(asset_id);start=number(start);end=number(end)
  if not 0<=start<end<=a['metadata']['duration']:raise Rejected('Timecodes hors du média.')
  if kind not in KINDS or review not in REVIEWS or rights not in RIGHTS:raise Rejected('État de passage invalide.')
  if type(identity_anchor)is not bool:raise Rejected('Référence booléenne requise.')
  evidence=text(evidence,2000);label=text(label)
  if rights=='documented':rights_evidence=text(rights_evidence,2000)
  elif not isinstance(rights_evidence,str):raise Rejected('Justificatif invalide.')
  if identity_anchor and (kind!='authentic_capture' or review!='approved_internal'):
   raise Rejected('La référence d’identité exige une captation authentique relue.')
  tags=tags or []
  if not isinstance(tags,list) or len(tags)>20:raise Rejected('Liste de mots-clés invalide.')
  tags=[text(t,60) for t in tags]
  with self.lock,self.db:
   prev=self.db.execute('SELECT * FROM segments WHERE id=?',(sid,)).fetchone()
   if prev:
    if type(expected_revision)is not int or expected_revision!=prev['revision']:raise Rejected('Annotation périmée : relire la version.')
    rev=prev['revision']+1
   else:
    if expected_revision is not None:raise Rejected('Passage inexistant.')
    rev=1
   values=(sid,asset_id,label,start,end,kind,review,rights,rights_evidence,int(identity_anchor),evidence,canonical(tags),rev)
   self.db.execute('INSERT OR REPLACE INTO segments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',values)
  return self.segment(sid)
 def catalogue(self,query='',kind=None):
  if not isinstance(query,str) or len(query)>300:raise Rejected('Recherche trop longue.')
  tokens=normalized(query).split()
  with self.lock:ids=[r[0] for r in self.db.execute('SELECT id FROM segments ORDER BY asset_id,start,id')]
  out=[]
  for sid in ids:
   s=self.segment(sid)
   if kind and s['kind']!=kind:continue
   hay=normalized(s['label']+' '+' '.join(s['tags']))
   if any(t not in hay for t in tokens):continue
   a=self.asset(s['asset_id'])
   try:self.available(a['id']);status='verified'
   except IntegrityError:status='missing_or_changed'
   s.update({'asset_label':a['label'],'metadata':a['metadata'],'availability':status,
             'origin':a['origin'],'provenance':a['provenance']})
   out.append(s)
  return {'version':VERSION,'search_mode':'keywords_human_annotations','checked_at':now(),'segments':out,
          'asset_count':self.db.execute('SELECT count(*) FROM assets').fetchone()[0],
          'capabilities':{'semantic_search':False,'auto_artistic_review':False,'rendering':False,'publication':False}}
 def prepare(self,request):
  if not isinstance(request,dict) or set(request)!={'request_id','anchor_id','segment_ids','expected_revisions'}:raise Rejected('Contrat de sélection invalide.')
  rid=request['request_id']
  if not isinstance(rid,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}',rid):raise Rejected('Identifiant de demande invalide.')
  ids=request['segment_ids']
  if not isinstance(ids,list) or not 1<=len(ids)<=12 or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):raise Rejected('Sélection unique de 1 à 12 passages.')
  if not isinstance(request['anchor_id'],str) or not isinstance(request['expected_revisions'],dict):raise Rejected('Références invalides.')
  reqhash=sha(canonical(request).encode())
  with self.lock:
   old=self.db.execute('SELECT * FROM plans WHERE id=?',(rid,)).fetchone()
   if old:
    if old['request_hash']!=reqhash:raise Rejected('Cet identifiant appartient à une autre sélection.')
    body=json.loads(old['body']);self.validate_plan(body);return body
   anchor=self.segment(request['anchor_id'])
   if not anchor['identity_anchor'] or anchor['kind']!='authentic_capture' or anchor['review']!='approved_internal':raise Rejected('Référence d’identité non validée.')
   allids=list(dict.fromkeys([anchor['id']]+ids));snapshots=[]
   if set(request['expected_revisions'])!=set(allids):raise Rejected('Toutes les révisions doivent être explicites.')
   for sid in allids:
    s=self.segment(sid)
    if type(request['expected_revisions'][sid])is not int or request['expected_revisions'][sid]!=s['revision']:raise Rejected('La sélection a changé : relecture nécessaire.')
    if s['kind'] not in {'authentic_capture','ai_generation'}:raise Rejected('Concept ou contenu mélangé : isoler d’abord un plan admissible.')
    if s['review']=='rejected':raise Rejected('Plan artistiquement refusé : bloqué pour ce montage.')
    self.available(s['asset_id']);snapshots.append(s)
   body={'schema':'bojart.edit_brief.v1','id':rid,'created_at':now(),'anchor_id':anchor['id'],
         'segment_order':ids,'sources':snapshots,'source_digest':sha(canonical(snapshots).encode()),
         'status':'PREPARED_NOT_RENDERED','publish_allowed':False,'cost_incurred':0,
         'requires_review':['assemblage_et_raccords','son_et_droits','validation_artistique_finale'],
         'rights_pending':[s['id'] for s in snapshots if s['rights']!='documented'],
         'note':'Un brief n’est ni une vidéo rendue ni une autorisation de publier.'}
   with self.db:self.db.execute('INSERT INTO plans VALUES(?,?,?)',(rid,reqhash,canonical(body)))
   return body
 def validate_plan(self,body):
  if body.get('schema')!='bojart.edit_brief.v1':raise Rejected('Format de brief inconnu.')
  snapshots=body.get('sources',[])
  if sha(canonical(snapshots).encode())!=body.get('source_digest'):raise IntegrityError('Brief altéré.')
  for snap in snapshots:
   current=self.segment(snap['id'])
   if current!=snap:raise Rejected('Les références du montage sont périmées.')
   self.available(snap['asset_id'])
  anchor=self.segment(body['anchor_id'])
  if not anchor['identity_anchor'] or anchor['review']!='approved_internal':raise Rejected('Référence d’identité retirée.')
  return {'valid':True,'publish_allowed':False,'status':'PREPARED_NOT_RENDERED'}
 def get_plan(self,planid):
  with self.lock:r=self.db.execute('SELECT body FROM plans WHERE id=?',(planid,)).fetchone()
  if not r:raise Rejected('Brief inconnu.')
  return json.loads(r[0])
 def export_archive(self,path):
  """Portable catalogue + exact media bytes; no absolute source paths exported."""
  path=Path(path)
  with self.lock:
   assets=[self.asset(r[0]) for r in self.db.execute('SELECT id FROM assets')]
   segs=[self.segment(r[0]) for r in self.db.execute('SELECT id FROM segments')]
   entries={f'media/{a["id"]}.mp4':self.read_blob(a['id']) for a in assets}
   entries['catalogue.json']=canonical({'version':VERSION,'assets':assets,'segments':segs,'plans':[json.loads(r[0]) for r in self.db.execute('SELECT body FROM plans')]}).encode()
   manifest={name:{'sha256':sha(data),'bytes':len(data)} for name,data in entries.items()}
   # Explicitly do not restore or claim an application backup: exports are read-only.
   entries['MANIFESTE.json']=canonical(manifest).encode()
   path.parent.mkdir(exist_ok=True,parents=True)
   temp=path.with_suffix(path.suffix+'.tmp')
   with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in entries.items():z.writestr(name,data)
   os.replace(temp,path)
  return verify_archive(path)

def verify_archive(path):
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>1000:raise IntegrityError('Archive ambiguë ou trop grande.')
  if any(n.startswith('/') or '..' in Path(n).parts or '\\' in n for n in names):raise IntegrityError('Chemin non sûr.')
  if sum(i.file_size for i in z.infolist())>512*1024*1024:raise IntegrityError('Archive trop volumineuse.')
  try:m=json.loads(z.read('MANIFESTE.json'))
  except Exception as e:raise IntegrityError('Manifeste absent.') from e
  if set(names)!=(set(m)|{'MANIFESTE.json'}):raise IntegrityError('Manifeste incomplet.')
  for name,info in m.items():
   b=z.read(name)
   if sha(b)!=info['sha256'] or len(b)!=info['bytes']:raise IntegrityError('Archive altérée.')
 return {'valid':True,'files':len(m),'note':'Vérification de copie ; restauration applicative non implémentée.'}
