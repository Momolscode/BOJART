#!/usr/bin/env python3
"""M04 self-test: actual CAD + HTTP routes + three simulated browser receipts.
No external network, no physical monitor or printer, no paid service.
"""
from __future__ import annotations
import hashlib, http.client, json, sys, tempfile, threading, uuid
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, BaseSpec
from consolidated_workbench import ConsolidatedWorkbench


def run():
    with tempfile.TemporaryDirectory(prefix='bojart-m04-smoke-') as tmp:
        store=Store(tmp)
        op=uuid.uuid4().hex
        receipt=store.run({'operation_id':op,'project_id':'BOJ-PILOTE-001','expected_revision':0,
                           'params':asdict(BaseSpec())})
        assert receipt['state']=='READY'
        server=ConsolidatedWorkbench(('127.0.0.1',0),store)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            origin=server.origin
            def req(path,data=None,raw=False):
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=20)
                headers={'Cookie':'boj_session='+server.token}
                if data is not None:headers.update({'Origin':origin,'Content-Type':'application/json'})
                conn.request('POST' if data is not None else 'GET',path,
                             body=json.dumps(data) if data is not None else None,headers=headers)
                response=conn.getresponse();body=response.read();status=response.status;conn.close()
                if status!=200:raise RuntimeError(f'{path} -> HTTP {status}: {body[:180]!r}')
                return body if raw else json.loads(body)
            role_ids={role:req('/api/tower/pair',{'role':role,'label':'Test '+role})['screen_id']
                      for role in ('atelier','pilotage','creation')}
            verified={}
            for command,role in [('Montre les sources au centre','pilotage'),
                                 ('Affiche le planning à gauche','atelier'),
                                 ('Affiche le modèle à droite','creation')]:
                rid='smoke'+uuid.uuid4().hex
                proposal=req('/api/control/prepare',{'request_id':rid,'turn_id':'smoke'+uuid.uuid4().hex,
                           'project_id':'BOJ-PILOTE-001','revision':1,'command':command,
                           'operation_id':op if role=='creation' else None})
                req('/api/tower/dispatch',{'request_id':rid})
                task=req('/api/tower/poll',{'screen_id':role_ids[role]})['command']
                assert task and task['request_id']==rid
                if role=='creation':
                    asset=task['asset'];blob=req(asset['path'],raw=True)
                    assert hashlib.sha256(blob).hexdigest()==asset['sha256']
                    mesh=json.loads(req('/artifacts/'+op+'/modele.json',raw=True))
                    assert mesh['positions'] and mesh['normals']
                ack=req('/api/tower/ack',{'screen_id':role_ids[role],'request_id':rid,
                        'outcome':'rendered','message':'Test logiciel sans écran physique'})
                assert ack['state']=='rendered'
                verified[role]={'action':proposal['action'],'ack':ack['state']}
            launch=req('/api/launch/readiness')
            assert launch['production_ready'] is False
            return {'status':'PASS','scope':'test HTTP avec accusés simulés, sans navigateur réel',
                    'real_cad_model':True,'sha256_glb_verified':True,'roles':verified,
                    'launch_ready':launch['production_ready'],'physical_commands':False}
        finally:
            server.shutdown();server.server_close();thread.join(timeout=10)

if __name__=='__main__':
    try:print(json.dumps(run(),ensure_ascii=False,indent=2))
    except Exception as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)
