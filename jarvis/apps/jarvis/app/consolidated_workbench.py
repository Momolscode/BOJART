"""Local BOJ.ART workspace, with persistent visual orchestration and optional Jev.
Single-user localhost; model calls require explicit configuration. No printer API.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, sqlite3, sys, webbrowser
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from core import Store, Rejected, IntegrityError
from dialogue import strict_json
from studio_workbench import StudioWorkbench, StudioHandler
from workbench import load_config
from display_contracts import DisplayProposals, ROUTES
from growth import GrowthEngine
from control_tower import ControlTower
from launch_readiness import assessment
from workspace_state import WorkspaceLease, WorkspaceState, verify_snapshot
from jarvis_runtime import JarvisRuntime
from tower_events import TowerEvents
import jarvis_http
# Root memory package shares one database with the canonical document index.
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from bojart_memory import http_api as memory_http
ROOT=Path(__file__).resolve().parents[1]
MONOREPO=Path(__file__).resolve().parents[3]
CORPUS=MONOREPO/'knowledge/metier'
sys.path.insert(0,str(CORPUS/'app'))
from base_metier import KnowledgeBase

class ConsolidatedWorkbench(StudioWorkbench):
    landing_path='/workspace'
    app_version='m07.2026-11-01'
    def __init__(self,address,store,**kwargs):
        self.workspace_lease=WorkspaceLease(store.root)
        try:
            super().__init__(address,store,**kwargs)
            self.display=DisplayProposals(store)
            self.growth=GrowthEngine(self.library,store.root/"growth")
            self.tower=ControlTower(store,self.display)
            self.workspace=WorkspaceState(self)
            self.events=TowerEvents()
            self.jarvis=JarvisRuntime(self)
            self.RequestHandlerClass=ConsolidatedHandler
        except Exception:
            self.server_close()
            raise

    def capabilities(self,probe=False):
        result=super().capabilities(probe)
        if hasattr(self,'jarvis'):
            result['jev']=self.jarvis.decider.status()
            result['cloud_enabled']=bool(self.jarvis.decider.enabled and self.jarvis.decider.key)
            result['langgraph']=self.jarvis.graph_status
        return result

    def server_close(self):
        if hasattr(self,'events'):self.events.close()
        if hasattr(self,'workspace'):
            # Finish any accepted mutation before releasing the process lease.
            with self.workspace.lock:
                self.workspace.closing=True
            # A decision can be outside the workspace lock. Let it observe closing
            # before waiting for its worker, otherwise shutdown would deadlock.
            if hasattr(self,'jarvis'):self.jarvis.close()
            self._close_resources()
        else:self._close_resources()

    def _close_resources(self):
        try:
            if hasattr(self,'socket'):super().server_close()
        finally:
            if hasattr(self,'workspace_lease'):self.workspace_lease.close()

class ConsolidatedHandler(StudioHandler):
    def do_GET(self):
        parsed=urlsplit(self.path);route=parsed.path
        if route in memory_http.GETS:return memory_http.get(self,parsed,ROOT/'app')
        if route in jarvis_http.GETS:return jarvis_http.get(self,parsed,ROOT)
        if route=='/health':
            if not self.check_host():return
            return self.j({'status':'local_ready','version':self.server.app_version,'physical_commands':False,'production_ready':False})
        if route.startswith('/backups/bojart-global-'):
            if not self.check_host():return
            if not self.authorized():return self.j({'error':'Session locale requise.'},401)
            try:
                if not re.fullmatch(r'/backups/bojart-global-[0-9a-f]{32}\.zip',route):raise Rejected('Chemin de sauvegarde invalide.')
                p=self.server.store.root/route[1:]
                if p.is_symlink() or not p.is_file():raise Rejected('Sauvegarde absente.')
                verify_snapshot(p)
                with p.open('rb') as source:
                    self.response(200,b'','application/zip',{'Content-Length':str(p.stat().st_size),'Content-Disposition':'attachment; filename="'+p.name+'"'})
                    shutil.copyfileobj(source,self.wfile,1024*1024)
                return
            except (Rejected,IntegrityError,OSError) as e:return self.j({'error':str(e)},409)
        routes={'/tower','/tower/screen','/tower.js','/tower.css','/tower_screen.js','/api/tower/state','/api/launch/readiness','/api/control/state','/api/knowledge/search','/api/context/distilled','/knowledge','/knowledge.js','/growth','/growth.js','/growth.css','/api/growth/state','/api/growth/sources'}
        routes.update({'/workspace','/workspace.js','/workspace.css','/api/workspace/state'})
        routes.update({'/memory','/memory.js','/api/memory/search'})
        if route not in routes:return super().do_GET()
        if not self.check_host():return
        if not self.authorized():return self.j({'error':'Session locale requise.'},401)
        try:
            if route in {'/memory','/memory.js'}:
                name='memory.html' if route=='/memory' else 'memory.js'
                return self.response(200,(ROOT/'app'/name).read_bytes(),'text/html; charset=utf-8' if route=='/memory' else 'text/javascript; charset=utf-8')
            if route=='/api/memory/search':
                # This route can only retrieve. Import and reconciliation are local CLI operations.
                sys.path.insert(0,str(MONOREPO.parent)) if str(MONOREPO.parent) not in sys.path else None
                from bojart_memory import Memory, MemoryError
                from bojart_memory.paths import default_state
                q=parse_qs(parsed.query,keep_blank_values=True)
                if set(q)-{'q','project','limit'} or any(len(v)!=1 for v in q.values()):raise Rejected('Paramètres invalides.')
                state=default_state()
                if not (state/'memory.sqlite').is_file():return self.j({'available':False,'results':[],'message':'La mémoire locale doit être initialisée avec le lanceur BOJART.'})
                try:
                    with Memory(state,readonly=True) as memory:
                        result=memory.search(q.get('q',[''])[0],project=q.get('project',[''])[0],limit=int(q.get('limit',['6'])[0]))
                    return self.j({'available':True,**result})
                except MemoryError as e:return self.j({'error':str(e)},400)
            if route in {'/workspace','/workspace.js','/workspace.css'}:
                name='workspace.html' if route=='/workspace' else route[1:]
                mime='text/html; charset=utf-8' if name.endswith('.html') else 'text/css; charset=utf-8' if name.endswith('.css') else 'text/javascript; charset=utf-8'
                return self.response(200,(ROOT/'app'/name).read_bytes(),mime)
            if route=='/api/workspace/state':return self.j(self.server.workspace.overview())
            if route in {'/tower','/tower/screen','/tower.js','/tower.css','/tower_screen.js'}:
                name='tower.html' if route=='/tower' else 'tower_screen.html' if route=='/tower/screen' else route[1:]
                mime='text/html; charset=utf-8' if name.endswith('.html') else ('text/css; charset=utf-8' if name.endswith('.css') else 'text/javascript; charset=utf-8')
                return self.response(200,(ROOT/'app'/name).read_bytes(),mime)
            if route=='/api/tower/state':
                q=parse_qs(parsed.query,keep_blank_values=True)
                if set(q)-{'project_id'} or any(len(v)!=1 for v in q.values()):raise Rejected('Paramètres de dossier invalides.')
                return self.j(self.server.tower.status(q.get('project_id',[None])[0]))
            if route=='/api/launch/readiness':return self.j(assessment(self.server.store,self.server.tower,self.server.config))
            if route in {'/growth','/growth.js','/growth.css'}:
                name='growth.html' if route=='/growth' else route[1:]
                mime='text/html; charset=utf-8' if name.endswith('.html') else ('text/css; charset=utf-8' if name.endswith('.css') else 'text/javascript; charset=utf-8')
                return self.response(200,(ROOT/'app'/name).read_bytes(),mime)
            if route=='/api/growth/state':return self.j(self.server.growth.status())
            if route=='/api/growth/sources':return self.j(strict_json((MONOREPO/'knowledge/growth/SOURCES.json').read_bytes()))
            if route in {'/knowledge','/knowledge.js'}:
                name='knowledge.html' if route=='/knowledge' else 'knowledge.js'
                return self.response(200,(ROOT/'app'/name).read_bytes(),'text/html; charset=utf-8' if route=='/knowledge' else 'text/javascript; charset=utf-8')
            if route=='/api/control/state':
                return self.j({'version':self.server.app_version,'proposal_only':True,'roles':['atelier','pilotage','creation'],
                               'screen_pairing':'browser_tabs_local_only','voice_session':'not_connected','jev':'not_connected',
                               'langgraph':self.server.jarvis.graph_status,'physical_commands':False,'known_commands':list(ROUTES),
                               'runtime':self.server.jarvis.status()})
            if route=='/api/context/distilled':
                data=(MONOREPO/'context/DECISIONS.json').read_bytes()
                return self.j({'context':strict_json(data),'sha256':hashlib.sha256(data).hexdigest(),'operational_authority':False})
            query=parse_qs(parsed.query,keep_blank_values=True)
            if set(query)-{'q','domain','limit'} or any(len(v)!=1 for v in query.values()):raise Rejected('Paramètres inconnus ou dupliqués.')
            text=query.get('q',[''])[0]
            if not text.strip():raise Rejected('Terme de recherche requis.')
            kb=KnowledgeBase(CORPUS)
            try:
                result=kb.search(text,domain=query.get('domain',[None])[0],limit=int(query.get('limit',['6'])[0]))
                result['corpus_digest']=hashlib.sha256((CORPUS/'data/fiches.json').read_bytes()).hexdigest()
                return self.j(result)
            finally:kb.con.close()
        except (ValueError,Rejected,IntegrityError,UnicodeDecodeError) as e:return self.j({'error':str(e)},400)
        except OSError:return self.j({'error':'Source locale indisponible.'},500)
    def do_POST(self):
        self._buffered_request_body=None
        if self.path in memory_http.POSTS:return memory_http.post(self)
        if self.path in jarvis_http.POSTS:return jarvis_http.post(self)
        if not self.buffer_workspace_body():return
        if self.path in {'/api/tower/poll','/api/tower/ack','/api/tower/pair'}:
            # These short SQLite-only writes take the tower lock and participate
            # in snapshot DB reservations, without waiting for a long CAD job.
            if self.server.workspace.closing:return self.j({'error':'Fermeture en cours.'},503)
            return self.workspace_post()
        # Includes inherited CAD/Studio routes: no mixed-state snapshot between
        # the reservation, file writes and commit of a long-running operation.
        with self.server.workspace.lock:
            if self.server.workspace.closing:return self.j({'error':'Fermeture en cours ; reprendre depuis le lanceur.'},503)
            return self.workspace_post()

    def buffer_workspace_body(self):
        # Receive at most 16 KiB outside the mutation lock. Slow or disconnected
        # clients cannot stall another window or a global snapshot. Route-specific
        # contracts and their smaller limits are still enforced by each handler.
        if not self.check_host():return False
        if not self.authorized():self.j({'error':'Session requise.'},401);return False
        if self.headers.get('Origin')!=self.server.origin:
            self.j({'error':'Origine refusée.'},403);return False
        if self.headers.get('Transfer-Encoding'):
            self.j({'error':'Encodage refusé.'},400);return False
        if self.headers.get_content_type()!='application/json':
            self.j({'error':'JSON requis.'},415);return False
        if self.server.workspace.closing:
            self.j({'error':'Fermeture en cours.'},503);return False
        lengths=self.headers.get_all('Content-Length',[])
        try:
            if len(lengths)!=1 or not re.fullmatch('[0-9]+',lengths[0].strip()):
                raise ValueError('Unique decimal length required')
            n=int(lengths[0])
        except ValueError:
            self.j({'error':'Taille de requête invalide ou ambiguë.'},400);return False
        if not 0<n<=16384:
            self.j({'error':'Requête hors limites.'},413);return False
        if not self.server.requests_gate.acquire(blocking=False):
            self.j({'error':'Trop de requêtes. Réessayez.'},429);return False
        try:
            raw=self.read_request_body(n)
            if len(raw)!=n:
                self.j({'error':'Requête incomplète.'},400);return False
            self._buffered_request_body=raw
            return True
        except (TimeoutError,OSError):
            self.j({'error':'Délai de réception dépassé. Aucune action commencée.'},408)
            return False
        finally:self.server.requests_gate.release()

    def workspace_post(self):
        if self.path not in {'/api/backup','/api/workspace/backup','/api/workspace/check','/api/workspace/recover','/api/projects/create','/api/control/prepare','/api/growth/prepare','/api/growth/validate','/api/tower/pair','/api/tower/poll','/api/tower/dispatch','/api/tower/ack'}:return super().do_POST()
        if not self.check_host():return
        if not self.authorized():return self.j({'error':'Session requise.'},401)
        if self.headers.get('Origin')!=self.server.origin:return self.j({'error':'Origine refusée.'},403)
        if self.headers.get('Transfer-Encoding'):return self.j({'error':'Encodage refusé.'},400)
        if self.headers.get_content_type()!='application/json':return self.j({'error':'JSON requis.'},415)
        try:
            n=int(self.headers.get('Content-Length','-1'))
            if not 0<n<=8192:return self.j({'error':'Requête hors limites.'},413)
            raw=self.read_request_body(n)
            if len(raw)!=n:raise Rejected('Requête incomplète.')
            data=strict_json(raw)
            if not isinstance(data,dict):raise Rejected('Objet JSON requis.')
            if self.path in {'/api/backup','/api/workspace/backup'}:
                if set(data) not in (set(),{'request_id'}):raise Rejected('Identifiant de sauvegarde attendu.')
                return self.j(self.server.workspace.backup(data.get('request_id')))
            if self.path=='/api/workspace/check':
                if data:raise Rejected('Aucun paramètre attendu.')
                return self.j(self.server.workspace.check())
            if self.path=='/api/workspace/recover':
                if set(data)!={'operation_id','resolution'}:raise Rejected('Opération et résolution requises.')
                return self.j(self.server.workspace.recover(data['operation_id'],data['resolution']))
            if self.path=='/api/projects/create':
                if set(data)!={'project_id','name'}:raise Rejected('Identifiant et nom du dossier requis.')
                return self.j(self.server.store.create_project(data['project_id'],data['name']))
            if self.path=='/api/tower/pair':
                if set(data) not in ({'role','label'},{'role','label','project_id'}):raise Rejected('Rôle et nom de vue requis.')
                return self.j(self.server.tower.pair(data['role'],data['label'],data.get('project_id','BOJ-PILOTE-001')))
            if self.path=='/api/tower/poll':
                if not isinstance(data,dict) or set(data)!={'screen_id'}:raise Rejected('Identifiant de vue requis.')
                return self.j(self.server.tower.poll(data['screen_id']))
            if self.path=='/api/tower/dispatch':
                if not isinstance(data,dict) or set(data)!={'request_id'}:raise Rejected('Référence de proposition requise.')
                result=self.server.tower.dispatch(data['request_id']);self.server.events.notify()
                return self.j(result)
            if self.path=='/api/tower/ack':
                if not isinstance(data,dict) or set(data)!={'screen_id','request_id','outcome','message'}:raise Rejected('Accusé de vue invalide.')
                result=self.server.tower.ack(data['screen_id'],data['request_id'],data['outcome'],data['message']);self.server.events.notify()
                return self.j(result)
            if self.path=='/api/growth/prepare':return self.j(self.server.growth.prepare(data))
            if self.path=='/api/growth/validate':
                if not isinstance(data,dict) or set(data)!={'packet_id'}:raise Rejected('Identifiant de préparation requis.')
                return self.j(self.server.growth.validate(data['packet_id']))
            return self.j(self.server.display.prepare(data))
        except (Rejected,ValueError,IntegrityError,UnicodeDecodeError) as e:return self.j({'error':str(e),'executed':False},409)
        except Exception:return self.j({'error':'Traitement interrompu. Vérifier la référence dans le journal avant de reprendre.'},500)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',default=str(Path.home()/'BOJART'/'mission05'))
    parser.add_argument('--config',help='Configuration locale des moteurs voix/Ollama (aucun secret Jev dans ce fichier).')
    parser.add_argument('--choose-state',action='store_true',help='Choisir un espace existant ou restauré avec le sélecteur de dossiers.')
    parser.add_argument('--port',type=int,default=8767);parser.add_argument('--no-browser',action='store_true')
    a=parser.parse_args()
    if a.choose_state:
        try:
            import tkinter as tk
            from tkinter import filedialog
            window=tk.Tk();window.withdraw()
            selected=filedialog.askdirectory(title='Dossier de travail Jarvis existant ou restauré')
            window.destroy()
            if not selected:return
            a.state=selected
        except Exception as e:raise SystemExit('Sélecteur indisponible. Utiliser --state CHEMIN_DU_DOSSIER. '+str(e))
    if not 0<=a.port<=65535:raise SystemExit('Port invalide.')
    try:app=ConsolidatedWorkbench(('127.0.0.1',a.port),Store(a.state),config=load_config(a.config))
    except (Rejected,IntegrityError,OSError) as e:raise SystemExit('Lancement interrompu : '+str(e))
    except sqlite3.DatabaseError as e:
        # Never recreate or repair a damaged workspace implicitly: the user restores a verified backup.
        raise SystemExit('Lancement interrompu : une base du dossier de travail est illisible ('+str(e)+'). '
                         'Aucune base n’a été recréée. Restaurer une sauvegarde vérifiée dans un nouveau dossier '
                         '(Restaurer_Jarvis.cmd) puis relancer avec ce dossier.')
    url=app.origin+'/?session='+app.token
    print('BOJ.ART — M07: commandes, dossiers et reprise locale. Voix et matériel à qualifier.')
    if a.no_browser:print('URL privée :',url)
    else:webbrowser.open(url)
    try:app.serve_forever()
    except KeyboardInterrupt:pass
    finally:app.server_close()
if __name__=='__main__':main()
