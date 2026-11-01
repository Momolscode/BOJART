"""Connect M03 to the existing knowledge corpus and safe display proposal contracts.
Single-user localhost, no new model, no external request, no dispatch to printers.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, webbrowser
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from core import Store, Rejected, IntegrityError
from dialogue import strict_json
from studio_workbench import StudioWorkbench, StudioHandler
from display_contracts import DisplayProposals, ROUTES
from growth import GrowthEngine
from control_tower import ControlTower
from launch_readiness import assessment
ROOT=Path(__file__).resolve().parents[1]
MONOREPO=Path(__file__).resolve().parents[3]
CORPUS=MONOREPO/'knowledge/metier'
sys.path.insert(0,str(CORPUS/'app'))
from base_metier import KnowledgeBase

class ConsolidatedWorkbench(StudioWorkbench):
    def __init__(self,address,store,**kwargs):
        super().__init__(address,store,**kwargs)
        self.display=DisplayProposals(store)
        self.growth=GrowthEngine(self.library,store.root/"growth")
        self.tower=ControlTower(store,self.display)
        self.RequestHandlerClass=ConsolidatedHandler

class ConsolidatedHandler(StudioHandler):
    def do_GET(self):
        parsed=urlsplit(self.path);route=parsed.path
        routes={'/tower','/tower/screen','/tower.js','/tower.css','/tower_screen.js','/api/tower/state','/api/launch/readiness','/api/control/state','/api/knowledge/search','/api/context/distilled','/knowledge','/knowledge.js','/growth','/growth.js','/growth.css','/api/growth/state','/api/growth/sources'}
        if route not in routes:return super().do_GET()
        if not self.check_host():return
        if not self.authorized():return self.j({'error':'Session locale requise.'},401)
        try:
            if route in {'/tower','/tower/screen','/tower.js','/tower.css','/tower_screen.js'}:
                name='tower.html' if route=='/tower' else 'tower_screen.html' if route=='/tower/screen' else route[1:]
                mime='text/html; charset=utf-8' if name.endswith('.html') else ('text/css; charset=utf-8' if name.endswith('.css') else 'text/javascript; charset=utf-8')
                return self.response(200,(ROOT/'app'/name).read_bytes(),mime)
            if route=='/api/tower/state':return self.j(self.server.tower.status())
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
                return self.j({'version':'m04.2026-10-31','proposal_only':True,'roles':['atelier','pilotage','creation'],
                               'screen_pairing':'browser_tabs_local_only','voice_session':'not_connected','jev':'not_connected',
                               'langgraph':'not_installed','physical_commands':False,'known_commands':list(ROUTES)})
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
        if self.path not in {'/api/control/prepare','/api/growth/prepare','/api/growth/validate','/api/tower/pair','/api/tower/poll','/api/tower/dispatch','/api/tower/ack'}:return super().do_POST()
        if not self.check_host():return
        if not self.authorized():return self.j({'error':'Session requise.'},401)
        if self.headers.get('Origin')!=self.server.origin:return self.j({'error':'Origine refusée.'},403)
        if self.headers.get('Transfer-Encoding'):return self.j({'error':'Encodage refusé.'},400)
        if self.headers.get_content_type()!='application/json':return self.j({'error':'JSON requis.'},415)
        try:
            n=int(self.headers.get('Content-Length','-1'))
            if not 0<n<=8192:return self.j({'error':'Requête hors limites.'},413)
            raw=self.rfile.read(n)
            if len(raw)!=n:raise Rejected('Requête incomplète.')
            data=strict_json(raw)
            if self.path=='/api/tower/pair':
                if not isinstance(data,dict) or set(data)!={'role','label'}:raise Rejected('Rôle et nom de vue requis.')
                return self.j(self.server.tower.pair(data['role'],data['label']))
            if self.path=='/api/tower/poll':
                if not isinstance(data,dict) or set(data)!={'screen_id'}:raise Rejected('Identifiant de vue requis.')
                return self.j(self.server.tower.poll(data['screen_id']))
            if self.path=='/api/tower/dispatch':
                if not isinstance(data,dict) or set(data)!={'request_id'}:raise Rejected('Référence de proposition requise.')
                return self.j(self.server.tower.dispatch(data['request_id']))
            if self.path=='/api/tower/ack':
                if not isinstance(data,dict) or set(data)!={'screen_id','request_id','outcome','message'}:raise Rejected('Accusé de vue invalide.')
                return self.j(self.server.tower.ack(data['screen_id'],data['request_id'],data['outcome'],data['message']))
            if self.path=='/api/growth/prepare':return self.j(self.server.growth.prepare(data))
            if self.path=='/api/growth/validate':
                if not isinstance(data,dict) or set(data)!={'packet_id'}:raise Rejected('Identifiant de préparation requis.')
                return self.j(self.server.growth.validate(data['packet_id']))
            return self.j(self.server.display.prepare(data))
        except (Rejected,ValueError,IntegrityError,UnicodeDecodeError) as e:return self.j({'error':str(e),'executed':False},409)
        except Exception:return self.j({'error':'Préparation interrompue. Aucune action exécutée.'},500)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',default=str(Path.home()/'BOJART'/'mission04'))
    parser.add_argument('--port',type=int,default=8767);parser.add_argument('--no-browser',action='store_true')
    a=parser.parse_args()
    if not 0<=a.port<=65535:raise SystemExit('Port invalide.')
    app=ConsolidatedWorkbench(('127.0.0.1',a.port),Store(a.state))
    url=app.origin+'/?session='+app.token
    print('BOJ.ART — M04: tour de contrôle locale. Aucun pilotage physique ni publication connecté.')
    if a.no_browser:print('URL privée :',url)
    else:webbrowser.open(url)
    try:app.serve_forever()
    except KeyboardInterrupt:pass
    finally:app.server_close()
if __name__=='__main__':main()
