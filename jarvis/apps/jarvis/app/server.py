"""Single-user localhost workbench. Not a public web service.
No external calls, no subprocess derived from a prompt, no printer endpoints.
"""
from __future__ import annotations
import argparse, hmac, http.cookies, importlib.util, json, mimetypes, os, secrets, socket, sys, threading, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from core import APP_VERSION, Store, Rejected, IntegrityError, parse_command, verify_backup

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_FILES={'socle.step','socle.stl','socle_metres.glb','modele.json','manifeste.json','parametres.json','recette_core.py'}


def strict_loads(raw):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise Rejected('Clé JSON dupliquée.')
            d[k]=v
        return d
    def bad_num(s):raise Rejected('Nombre JSON non fini.')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad_num)


class AppServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=not hasattr(socket,'SO_EXCLUSIVEADDRUSE')
    def server_bind(self):
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()
    def __init__(self,address,store,token=None):
        self.store=store;self.token=token or secrets.token_urlsafe(32)
        super().__init__(address,Handler)
        self.host_name='127.0.0.1:'+str(self.server_port)
        self.origin='http://'+self.host_name


class Handler(BaseHTTPRequestHandler):
    server: AppServer
    def log_message(self,*args):pass  # no token/path logging
    def response(self,status,body=b'',ctype='application/json; charset=utf-8',extra=None):
        self.send_response(status)
        self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
        for k,v in (extra or {}).items(): self.send_header(k,v)
        self.end_headers()
        if body:self.wfile.write(body)
    def j(self,obj,status=200):self.response(status,json.dumps(obj,ensure_ascii=False,allow_nan=False).encode('utf8'))
    def read_request_body(self,length):
        """Reuse a bounded body received before taking the workspace mutation lock."""
        buffered=getattr(self,'_buffered_request_body',None)
        if buffered is not None:
            if len(buffered)!=length:raise Rejected('Taille de requête incohérente.')
            return buffered
        return self.rfile.read(length)
    def authorized(self):
        try:
            cookie=http.cookies.SimpleCookie(self.headers.get('Cookie',''))
            value=cookie['boj_session'].value if 'boj_session' in cookie else ''
            return hmac.compare_digest(value,self.server.token)
        except Exception:return False
    def check_host(self):
        if self.headers.get('Host')!=self.server.host_name:
            self.j({'error':'Hôte non autorisé.'},403);return False
        return True
    def do_GET(self):
        if not self.check_host():return
        parsed=urllib.parse.urlsplit(self.path)
        if parsed.path=='/health':return self.j({'status':'local_ready','version':APP_VERSION,'physical_commands':False})
        args=urllib.parse.parse_qs(parsed.query)
        bootstrap=args.get('session',[''])[0]
        if parsed.path=='/' and bootstrap:
            if not bootstrap.isascii() or not hmac.compare_digest(bootstrap,self.server.token):return self.j({'error':'Session invalide.'},401)
            return self.response(303,extra={'Location':getattr(self.server,'landing_path','/'),'Set-Cookie':'boj_session='+self.server.token+'; HttpOnly; SameSite=Strict; Path=/'})
        if not self.authorized():return self.j({'error':'Ouvrir la fenêtre depuis le lanceur local autorisé.'},401)
        try:
            if parsed.path=='/':
                self.response(200,(ROOT/'app/index.html').read_bytes(),'text/html; charset=utf-8');return
            if parsed.path=='/api/state':
                self.j({'version':APP_VERSION,'project_id':'BOJ-PILOTE-001','revision':self.server.store.project_revision(),
                        'jobs':self.server.store.list_jobs(), 'context':json.loads(self.server.store.context_path.read_text(encoding='utf-8')),
                        'capabilities':{'cadquery_available':importlib.util.find_spec('cadquery') is not None,
                          'local_model_connected':False,'voice_connected':False,'printers_connected':False,'paid_services_connected':False}});return
            if parsed.path.startswith('/api/jobs/'):
                return self.j(self.server.store.get(parsed.path.rsplit('/',1)[-1]))
            if parsed.path.startswith('/artifacts/'):
                parts=parsed.path.split('/')
                if len(parts)!=4 or parts[3] not in ALLOWED_FILES:raise Rejected('Fichier non autorisé.')
                op,name=parts[2],parts[3];report=self.server.store.get(op)
                if report['state']!='READY':raise Rejected('Mission non prête.')
                p=self.server.store.artifacts/op/name
                mime=({'json':'application/json','stl':'model/stl','step':'application/step','glb':'model/gltf-binary','py':'text/plain'}).get(p.suffix[1:],'application/octet-stream')
                extra={} if name=='modele.json' else {'Content-Disposition':f'attachment; filename="{name}"'}
                return self.response(200,p.read_bytes(),mime,extra)
            if parsed.path.startswith('/backups/'):
                name=parsed.path.split('/')[-1]
                if not name.startswith('bojart-') or not name.endswith('.zip') or len(parsed.path.split('/'))!=3:raise Rejected('Chemin invalide.')
                p=self.server.store.root/'backups'/name
                if not p.is_file() or p.is_symlink():raise Rejected('Sauvegarde absente.')
                verify_backup(p)
                return self.response(200,p.read_bytes(),'application/zip',{'Content-Disposition':f'attachment; filename="{name}"'})
            self.j({'error':'Route inconnue.'},404)
        except Rejected as exc:self.j({'error':str(exc)},409)
        except IntegrityError as exc:self.j({'error':str(exc),'integrity':False},409)
        except Exception:self.j({'error':'Erreur interne ; aucune action physique envoyée.'},500)
    def do_POST(self):
        if not self.check_host():return
        if not self.authorized():return self.j({'error':'Session absente.'},401)
        # A loopback binding alone does not prevent malicious websites posting to it.
        if self.headers.get('Origin')!=self.server.origin:return self.j({'error':'Origine non autorisée.'},403)
        if self.headers.get_content_type()!='application/json':return self.j({'error':'JSON requis.'},415)
        try:
            length=int(self.headers.get('Content-Length','-1'))
            if not 0<length<=16384:return self.j({'error':'Taille de requête invalide.'},413)
            data=strict_loads(self.read_request_body(length))
            if self.path=='/api/parse':
                if not isinstance(data,dict) or set(data)!={'command'}:raise Rejected('Champ command unique requis.')
                return self.j(parse_command(data['command']))
            if self.path=='/api/mission':return self.j(self.server.store.run(data))
            if self.path=='/api/backup':
                if data!={}:raise Rejected('Aucun chemin fourni par le client accepté.')
                import uuid
                name='bojart-'+uuid.uuid4().hex+'.zip'
                result=self.server.store.backup(self.server.store.root/'backups'/name)
                return self.j({'url':'/backups/'+name,'sha256':result['sha256'],'files':result['files']})
            return self.j({'error':'Action non disponible : ce module ne pilote pas de machine ni de fournisseur.'},404)
        except (Rejected,json.JSONDecodeError,UnicodeDecodeError) as exc:self.j({'error':str(exc)},400)
        except IntegrityError as exc:self.j({'error':str(exc),'integrity':False},409)
        except Exception:self.j({'error':'Le moteur a échoué. Le dossier ne passe pas à « prêt ». Examiner le journal local.'},500)


def main():
    p=argparse.ArgumentParser();p.add_argument('--state',default=str(Path.home()/'BOJART'/'mission01'))
    p.add_argument('--port',type=int,default=8765);p.add_argument('--no-browser',action='store_true');args=p.parse_args()
    if args.port<0 or args.port>65535:raise SystemExit('Port invalide.')
    store=Store(args.state)
    server=AppServer(('127.0.0.1',args.port),store)
    url=server.origin+'/?session='+server.token
    print('BOJ.ART Mission 01 : géométrie locale. Aucune machine / IA / publication raccordée.')
    print('Dossiers conservés dans :',store.root)
    if args.no_browser:print('URL privée de session (ne pas partager) :',url)
    else:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
