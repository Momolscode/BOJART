"""Mission 02 workbench. Local single-user service, not for public hosting.
Optional local model/voice are off by default. No software installation or printer API.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, secrets, socket, threading, urllib.parse, uuid, webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from core import Store, Rejected, IntegrityError, verify_backup
from context_guard import validate_context
from dialogue import LocalOllama, strict_json
from proposals import ProposalBook
from voice import LocalVoice, MAX_BYTES
from diagnostics import collect
from server import Handler as LegacyHandler

ROOT=Path(__file__).resolve().parents[1]
APP_VERSION='0.2.0'
STATIC={'/ui.css':'text/css; charset=utf-8','/ui.js':'text/javascript; charset=utf-8',
        '/viewer.js':'text/javascript; charset=utf-8','/capture.js':'text/javascript; charset=utf-8',
        '/audio_worklet.js':'text/javascript; charset=utf-8'}

def load_config(path=None):
    p=Path(path) if path else ROOT/'config.json'
    if not p.exists():p=ROOT/'config.example.json'
    config=strict_json(p.read_text('utf-8'))
    if set(config)!={'version','ollama','voice'} or config['version']!='bojart.config.v2':raise Rejected('Configuration invalide.')
    if not isinstance(config['ollama'],dict) or not isinstance(config['voice'],dict):raise Rejected('Configuration invalide.')
    if set(config['ollama'])!={'enabled','url','model','model_digest','offline_verified'} or set(config['voice'])!={'enabled','model_dir'}:
        raise Rejected('Champs de configuration inattendus.')
    if any(type(config[g]['enabled'])is not bool for g in ['ollama','voice']):raise Rejected('enabled booléen requis.')
    if type(config['ollama']['offline_verified'])is not bool:raise Rejected('Contrôle hors ligne booléen requis.')
    for k in ['url','model','model_digest']:
        if not isinstance(config['ollama'][k],str):raise Rejected('Champ modèle invalide.')
    if not isinstance(config['voice']['model_dir'],str):raise Rejected('Chemin de modèle vocal invalide.')
    return config

class Workbench(ThreadingHTTPServer):
    daemon_threads=True
    request_queue_size=12
    # Windows SO_REUSEADDR allows another listener to take the same port.
    allow_reuse_address=not hasattr(socket,'SO_EXCLUSIVEADDRUSE')
    def server_bind(self):
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()
    def __init__(self,address,store,config=None,token=None,voice=None,provider=None):
        self.store=store;self.token=token or secrets.token_urlsafe(32)
        self.config=config or load_config();self.provider=provider or LocalOllama(self.config['ollama'])
        self.voice=voice or LocalVoice(self.config['voice']);self.proposals=ProposalBook(store)
        self.model_gate=threading.Lock();self.requests_gate=threading.BoundedSemaphore(12)
        self.cached_diagnostic=None
        super().__init__(address,Handler)
        self.host_name='127.0.0.1:'+str(self.server_port);self.origin='http://'+self.host_name
    def get_request(self):
        sock,addr=super().get_request();sock.settimeout(35);return sock,addr
    def capabilities(self,probe=False):
        try:llm=self.provider.check() if probe else {'status':'configured' if self.config['ollama']['enabled'] else 'disabled'}
        except Rejected as e:llm={'status':'unavailable','message':str(e)}
        return {'cadquery_available':importlib.util.find_spec('cadquery') is not None,
                'trimesh_available':importlib.util.find_spec('trimesh') is not None,
                'llm':llm,'voice':self.voice.status(),
                'printers_connected':False,'cloud_enabled':False,'paid_services_connected':False,
                'mode':'local_pilot','llm_quality_tested':False,'microphone_tested':False}

class Handler(LegacyHandler):
    server:Workbench
    def response(self,status,body=b'',ctype='application/json; charset=utf-8',extra=None):
        self.send_response(status)
        headers={'Content-Type':ctype,'Content-Length':str(len(body)),'Cache-Control':'no-store',
                 'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY',
                 'Permissions-Policy':'microphone=(self), camera=(), geolocation=()',
                 'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; media-src 'self' blob:; worker-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"}
        headers.update(extra or {})
        for k,v in headers.items():self.send_header(k,v)
        try:
            self.end_headers()
            if body:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):
            # Navigating away from a video cancels its HTTP body normally.
            self.close_connection=True
    def do_GET(self):
        if not self.check_host():return
        parsed=urllib.parse.urlsplit(self.path)
        # Base class handles token bootstrap, health, artifacts and verified backups.
        if parsed.path=='/health':return self.j({'status':'local_ready','version':APP_VERSION,'physical_commands':False})
        if parsed.path=='/' and urllib.parse.parse_qs(parsed.query).get('session'):return super().do_GET()
        if not self.authorized():return self.j({'error':'Session requise. Ouvrir depuis le lanceur.'},401)
        try:
            if parsed.path=='/':return self.response(200,(ROOT/'app/console.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path in STATIC:
                return self.response(200,(ROOT/'app'/parsed.path[1:]).read_bytes(),STATIC[parsed.path])
            if parsed.path=='/api/state':
                query=urllib.parse.parse_qs(parsed.query,keep_blank_values=True)
                if set(query)-{'project_id'} or any(len(v)!=1 for v in query.values()):raise Rejected('Paramètres de dossier invalides.')
                project=self.server.store.require_project(query.get('project_id',['BOJ-PILOTE-001'])[0])
                context_bytes=self.server.store.context_path.read_bytes()
                context=strict_json(context_bytes);validate_context(context)
                return self.j({'version':getattr(self.server,'app_version',APP_VERSION),'project_id':project,'revision':self.server.store.project_revision(project),
                  'jobs':self.server.store.list_jobs(project),'projects':self.server.store.list_projects(),'context':context,
                  'context_sha256':hashlib.sha256(context_bytes).hexdigest(),'capabilities':self.server.capabilities()})
            return super().do_GET()
        except (Rejected,IntegrityError,ValueError) as e:return self.j({'error':str(e),'integrity':False},409)
        except OSError:return self.j({'error':'Fichier local indisponible.'},500)
    def do_POST(self):
        if not self.check_host():return
        if not self.authorized():return self.j({'error':'Session absente.'},401)
        if self.headers.get('Origin')!=self.server.origin:return self.j({'error':'Origine non autorisée.'},403)
        if self.headers.get('Transfer-Encoding'):return self.j({'error':'Encodage non pris en charge.'},400)
        if not self.server.requests_gate.acquire(blocking=False):return self.j({'error':'Poste occupé. Réessayez.'},429)
        try:
            is_audio=self.path=='/api/transcribe'
            if self.headers.get_content_type()!=('audio/wav' if is_audio else 'application/json'):
                return self.j({'error':'Type de fichier non pris en charge.'},415)
            try:length=int(self.headers.get('Content-Length','-1'))
            except ValueError:return self.j({'error':'Taille invalide.'},400)
            if not 0<length<=(MAX_BYTES if is_audio else 16384):return self.j({'error':'Requête hors limites.'},413)
            raw=self.read_request_body(length)
            if len(raw)!=length:raise Rejected('Requête incomplète.')
            if is_audio:return self.j(self.server.voice.transcribe(raw))
            data=strict_json(raw)
            if not isinstance(data,dict):raise Rejected('Objet JSON requis.')
            if self.path=='/api/propose':
                if set(data) not in ({'command','revision','source'},{'command','revision','source','project_id'}):raise Rejected('Contrat de demande invalide.')
                if not self.server.model_gate.acquire(blocking=False):raise Rejected('Une demande est déjà en cours.')
                try:result=self.server.proposals.prepare(data['command'],data['revision'],self.server.provider,source=data['source'],project_id=data.get('project_id','BOJ-PILOTE-001'))
                finally:self.server.model_gate.release()
                return self.j(result)
            if self.path=='/api/confirm':return self.j(self.server.proposals.confirm(data))
            if self.path=='/api/diagnostic':
                if data!={}:raise Rejected('Aucun chemin ou commande libre accepté.')
                self.server.cached_diagnostic=collect(self.server.store.root)
                return self.j({'hardware':self.server.cached_diagnostic,'capabilities':self.server.capabilities(probe=True)})
            if self.path=='/api/backup':
                if data!={}:raise Rejected('Aucun chemin fourni par le client accepté.')
                name='bojart-'+uuid.uuid4().hex+'.zip'
                r=self.server.store.backup(self.server.store.root/'backups'/name)
                return self.j({'url':'/backups/'+name,'sha256':r['sha256'],'files':r['files']})
            return self.j({'error':'Action non disponible. Ce poste n’envoie aucune commande physique.'},404)
        except (Rejected,ValueError,UnicodeDecodeError) as e:return self.j({'error':str(e)},400)
        except IntegrityError as e:return self.j({'error':str(e),'integrity':False},409)
        except (socket.timeout,TimeoutError):return self.j({'error':'Délai dépassé. Vérifiez le journal avant une nouvelle tentative.'},408)
        except Exception:return self.j({'error':'Traitement local interrompu. Aucun résultat déclaré prêt ; vérifier le journal.'},500)
        finally:self.server.requests_gate.release()

def main():
    a=argparse.ArgumentParser();a.add_argument('--state',default=str(Path.home()/'BOJART'/'mission02'))
    a.add_argument('--config');a.add_argument('--port',type=int,default=8766);a.add_argument('--no-browser',action='store_true');args=a.parse_args()
    if not 0<=args.port<=65535:raise SystemExit('Port invalide.')
    store=Store(args.state);validate_context(strict_json(store.context_path.read_bytes()))
    server=Workbench(('127.0.0.1',args.port),store,load_config(args.config))
    url=server.origin+'/?session='+server.token
    print('BOJ.ART Mission 02 — poste local, aucune imprimante connectée.')
    if args.no_browser:print('URL privée de session :',url)
    else:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
