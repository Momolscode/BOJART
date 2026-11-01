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
ROOT=Path(__file__).resolve().parents[1]
MONOREPO=Path(__file__).resolve().parents[3]
CORPUS=MONOREPO/'knowledge/metier'
sys.path.insert(0,str(CORPUS/'app'))
from base_metier import KnowledgeBase

class ConsolidatedWorkbench(StudioWorkbench):
    def __init__(self,address,store,**kwargs):
        super().__init__(address,store,**kwargs)
        self.display=DisplayProposals(store)
        self.RequestHandlerClass=ConsolidatedHandler

class ConsolidatedHandler(StudioHandler):
    def do_GET(self):
        parsed=urlsplit(self.path);route=parsed.path
        routes={'/api/control/state','/api/knowledge/search','/api/context/distilled','/knowledge','/knowledge.js'}
        if route not in routes:return super().do_GET()
        if not self.check_host():return
        if not self.authorized():return self.j({'error':'Session locale requise.'},401)
        try:
            if route in {'/knowledge','/knowledge.js'}:
                name='knowledge.html' if route=='/knowledge' else 'knowledge.js'
                return self.response(200,(ROOT/'app'/name).read_bytes(),'text/html; charset=utf-8' if route=='/knowledge' else 'text/javascript; charset=utf-8')
            if route=='/api/control/state':
                return self.j({'version':'consolidation.2026-10-30','proposal_only':True,'roles':['atelier','pilotage','creation'],
                               'screen_pairing':'not_connected','voice_session':'not_connected','jev':'not_connected',
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
        if self.path!='/api/control/prepare':return super().do_POST()
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
            return self.j(self.server.display.prepare(strict_json(raw)))
        except (Rejected,ValueError,IntegrityError,UnicodeDecodeError) as e:return self.j({'error':str(e),'executed':False},409)
        except Exception:return self.j({'error':'Préparation interrompue. Aucune action exécutée.'},500)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',default=str(Path.home()/'BOJART'/'consolidated-2026-10-30'))
    parser.add_argument('--port',type=int,default=8767);parser.add_argument('--no-browser',action='store_true')
    a=parser.parse_args()
    if not 0<=a.port<=65535:raise SystemExit('Port invalide.')
    app=ConsolidatedWorkbench(('127.0.0.1',a.port),Store(a.state))
    url=app.origin+'/?session='+app.token
    print('BOJ.ART — consolidation locale. Aucune imprimante ni dépense connectée.')
    if a.no_browser:print('URL privée :',url)
    else:webbrowser.open(url)
    try:app.serve_forever()
    except KeyboardInterrupt:pass
    finally:app.server_close()
if __name__=='__main__':main()
