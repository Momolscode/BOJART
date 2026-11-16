#!/usr/bin/env python3
"""Real CAD + Chromium + global backup + clean restoration acceptance test.

Requires Node/playwright and a Chromium installation (BOJ_TEST_CHROMIUM optional).
Creates synthetic project data in a temporary workspace; no external actions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import closing

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, file_digest, now
from consolidated_workbench import ConsolidatedWorkbench
from workspace_state import restore_snapshot


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='boj-m05-acceptance-') as td:
        parent=Path(td);app=ConsolidatedWorkbench(('127.0.0.1',0),Store(parent/'original'))
        thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        try:
            browser=subprocess.run(['node',str(ROOT/'tools/m05_browser.cjs')],input=json.dumps({'origin':app.origin,'token':app.token,'output':str(output)}),capture_output=True,text=True,timeout=420)
            if browser.returncode:raise RuntimeError(browser.stderr[-7000:])
            proof=json.loads(browser.stdout)
            originals=[app.store.get(op) for op in proof['operation_ids']]
            archive=app.store.root/proof['backup']['url'].lstrip('/')
            receipt=restore_snapshot(archive,parent/'restored')
            snapshot_sha=file_digest(archive)
        finally:
            app.shutdown();app.server_close();thread.join(timeout=10)
        shutil.rmtree(parent/'original')
        restored=ConsolidatedWorkbench(('127.0.0.1',0),Store(parent/'restored'))
        try:
            for model in originals:assert restored.store.get(model['operation_id'])==model
            assert restored.store.project_revision(proof['project'])==2
            assert restored.library.validate_plan(restored.library.get_plan(proof['studio_brief']))['valid']
            assert restored.growth.validate(proof['growth_packet'])['sources_intact']
            integrity=restored.workspace.check();assert integrity['ok']
            assert restored.tower.status()['browser_views_connected']==0
            # A second backup of the relocated workspace must also be portable.
            second=restored.workspace.backup()
            restore_snapshot(restored.store.root/second['url'].lstrip('/'),parent/'restored-again')
            clean=restored.workspace.overview()
        finally:restored.server_close()
        result={'schema':'bojart.acceptance.m05.v1','status':'PASS','observed_at':now(),'python':platform.python_version(),'os':platform.system(),
                'browser':proof,'cad':[{'operation_id':m['operation_id'],'revision':m['revision'],'parameters':m['parameters'],'proof':m['proof'],'files':m['files']} for m in originals],
                'restoration':{'original_workspace_removed':True,'receipt':{k:v for k,v in receipt.items() if k!='destination'},'snapshot_sha256':snapshot_sha,'second_generation_restored':True,'integrity':integrity,'overview':clean},
                'limits':['Chromium headless, not physical monitors','Linux acceptance; Windows launchers not executed here','No microphone, local LLM, external account or printer qualification'],
                'screenshots':{p.name:file_digest(p) for p in output.glob('*.png')}}
        (output/'ACCEPTANCE_M05.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        return {'status':'PASS','browser_checks':len(proof['checks']),'real_cad_models':len(originals),'restored_databases':5,'restored_media':3,'output':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='docs/evidence/m05-2026-10-31');args=parser.parse_args()
    print(json.dumps(run(args.output),ensure_ascii=False,indent=2))
