"""Mission 03 extends Mission 02 in one local process and one session.
Studio contains no generation, upload, publishing or printer execution endpoint.
"""
from __future__ import annotations
import argparse, json, re, webbrowser
from pathlib import Path
from urllib.parse import urlsplit
from core import Store, Rejected, IntegrityError
from dialogue import strict_json
from workbench import Workbench, Handler as M02Handler, load_config
from media_library import MediaLibrary
from studio_seed import seed
ROOT=Path(__file__).resolve().parents[1]

class StudioWorkbench(Workbench):
 def __init__(self,address,store,**kwargs):
  super().__init__(address,store,**kwargs)
  media=store.root/'media';media.mkdir(exist_ok=True)
  roots=[media]
  if (ROOT/'studio_media').is_dir():roots.append(ROOT/'studio_media')
  self.library=MediaLibrary(store.root/'studio',roots)
  # Never repopulate or relabel an existing/restored catalogue at startup.
  # A source-only public checkout does not contain the private demo media.
  # Require the complete set before seeding; preserve an empty, usable catalogue.
  demo_files=('source_bojart.mp4','animatique_v4.mp4','essai_vfx_2d.mp4')
  if (not self.library.db.execute('SELECT 1 FROM assets LIMIT 1').fetchone()
      and all((ROOT/'studio_media'/name).is_file() for name in demo_files)):
   seed(self.library,ROOT/'studio_media')
  self.RequestHandlerClass=StudioHandler
 def server_close(self):
  super().server_close()
  if hasattr(self,'library'):self.library.close()

class StudioHandler(M02Handler):
 def do_GET(self):
  route=urlsplit(self.path).path
  if route=='/health':
   if not self.check_host():return
   return self.j({'status':'local_ready','version':'0.3.0','physical_commands':False,'studio':'sources_and_briefs_only'})
  if not (route.startswith('/studio') or route.startswith('/api/studio/')):return super().do_GET()
  if not self.check_host():return
  if not self.authorized():return self.j({'error':'Session locale requise.'},401)
  try:
   if route=='/studio':return self.response(200,(ROOT/'app/studio.html').read_bytes(),'text/html; charset=utf-8')
   if route in {'/studio.js','/studio.css'}:
    return self.response(200,(ROOT/'app'/route[1:]).read_bytes(),'text/javascript' if route.endswith('.js') else 'text/css')
   if re.fullmatch(r'/studio-assets/(intro|profil|ensemble|troisquarts|visage|outro|concept-v4|vfx-2d)\.jpg',route):
    return self.response(200,(ROOT/'studio_assets'/route.rsplit('/',1)[1]).read_bytes(),'image/jpeg')
   if route=='/api/studio/catalogue':return self.j(self.server.library.catalogue())
   if route.startswith('/api/studio/media/'):
    aid=route.rsplit('/',1)[1]
    if not re.fullmatch('[0-9a-f]{64}',aid):raise Rejected('Identifiant média invalide.')
    data=self.server.library.read_blob(aid);length=len(data);extra={'Accept-Ranges':'bytes'}
    rang=self.headers.get('Range')
    if rang:
     m=re.fullmatch(r'bytes=(\d+)-(\d*)',rang)
     if not m:return self.response(416,extra={'Content-Range':f'bytes */{length}'})
     a=int(m[1]);b=int(m[2]) if m[2] else length-1;b=min(b,length-1)
     if a>=length or b<a:return self.response(416,extra={'Content-Range':f'bytes */{length}'})
     extra['Content-Range']=f'bytes {a}-{b}/{length}'
     return self.response(206,data[a:b+1],'video/mp4',extra)
    return self.response(200,data,'video/mp4',extra)
   return self.j({'error':'Route Studio inconnue.'},404)
  except (Rejected,IntegrityError) as e:return self.j({'error':str(e)},409)
  except OSError:return self.j({'error':'Média local indisponible.'},500)
 def do_POST(self):
  if not self.path.startswith('/api/studio/'):return super().do_POST()
  if not self.check_host():return
  if not self.authorized():return self.j({'error':'Session requise.'},401)
  if self.headers.get('Origin')!=self.server.origin:return self.j({'error':'Origine refusée.'},403)
  if self.headers.get('Transfer-Encoding'):return self.j({'error':'Encodage refusé.'},400)
  if self.headers.get_content_type()!='application/json':return self.j({'error':'JSON requis.'},415)
  try:
   n=int(self.headers.get('Content-Length','-1'))
   if not 0<n<=16384:return self.j({'error':'Requête hors limites.'},413)
   raw=self.rfile.read(n)
   if len(raw)!=n:raise Rejected('Requête incomplète.')
   d=strict_json(raw)
   if not isinstance(d,dict):raise Rejected('Objet requis.')
   if self.path=='/api/studio/prepare':return self.j(self.server.library.prepare(d))
   if self.path=='/api/studio/verify':
    if set(d)!={'plan_id'} or not isinstance(d['plan_id'],str):raise Rejected('Identifiant requis.')
    return self.j(self.server.library.validate_plan(self.server.library.get_plan(d['plan_id'])))
   if self.path=='/api/studio/refresh':
    if d!={}:raise Rejected('Aucun chemin libre n’est accepté.')
    return self.j(self.server.library.catalogue())
   return self.j({'error':'Ni génération, ni publication, ni commande physique disponible.'},404)
  except (Rejected,ValueError,IntegrityError) as e:return self.j({'error':str(e)},409)
  except Exception:return self.j({'error':'Traitement interrompu. Rien n’a été envoyé.'},500)

def main():
 p=argparse.ArgumentParser();p.add_argument('--state',default=str(Path.home()/'BOJART'/'mission03'))
 p.add_argument('--port',type=int,default=8767);p.add_argument('--no-browser',action='store_true');a=p.parse_args()
 if not 0<=a.port<=65535:raise SystemExit('Port invalide.')
 app=StudioWorkbench(('127.0.0.1',a.port),Store(a.state),config=load_config())
 url=app.origin+'/?session='+app.token
 print('BOJ.ART — Mission 03. Catalogue local et préparation uniquement.')
 if a.no_browser:print('URL privée :',url)
 else:webbrowser.open(url)
 try:app.serve_forever()
 except KeyboardInterrupt:pass
 finally:app.server_close()
if __name__=='__main__':main()
