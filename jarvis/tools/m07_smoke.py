#!/usr/bin/env python3
"""M07 Chromium acceptance: real capture/rendering, explicit synthetic ASR/Jev."""
import argparse, json, math, platform, struct, subprocess, sys, tempfile, threading, time, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, now
from voice import validate_audio
from consolidated_workbench import ConsolidatedWorkbench
from jev_decider import JevDecider


class SpeechFixture:
    def __init__(self):self.calls=0;self.store=None
    def status(self):return {'status':'available','message':'Synthetic speech fixture, not an ASR model.'}
    def transcribe(self, raw):
        validate_audio(raw);self.calls+=1;call=self.calls
        time.sleep(.65)
        if call==4:self.store.context_path.write_bytes(self.store.context_path.read_bytes()+b'\n')
        text={1:'Ouvre la tour de contrôle',2:'Confirme cet affichage',3:'Annule cette proposition'}.get(call,'Montre les dossiers au centre')
        return {'status':'draft','text':text,'audio_stored':False,'fixture':True}


def decision_fixture(payload):
    options=payload['questions']['intent']['criteria']
    return {'model':payload['model'],'answers':{'intent':{'type':'choice','choice':'workspace','confidence':1.,
            'probabilities':{k:float(k=='workspace') for k in options}}}}


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='boj-m07-acceptance-') as temp:
        root=Path(temp);wav=root/'tone-and-pause.wav'
        with wave.open(str(wav),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(48000)
            out.writeframes(b''.join(struct.pack('<h',int(6500*math.sin(2*math.pi*440*i/48000))) for i in range(48000)) + b'\0\0'*(48000*5))
        voice=SpeechFixture();app=ConsolidatedWorkbench(('127.0.0.1',0),Store(root/'work'),voice=voice);voice.store=app.store
        app.jarvis.decider=JevDecider(enabled=True,key='synthetic-fixture-only',transport=decision_fixture)
        thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        try:
            completed=subprocess.run(['node',str(ROOT/'tools/m07_browser.cjs')],input=json.dumps({'origin':app.origin,'token':app.token,'wav':str(wav),'output':str(output)}),capture_output=True,text=True,timeout=180)
            if completed.returncode:raise RuntimeError(completed.stderr[-7000:])
            result=json.loads(completed.stdout)
            result.update({'schema':'bojart.acceptance.m07.v1','observed_at':now(),'python':platform.python_version(),'platform':platform.system(),
                           'graph':app.jarvis.graph_status,'speech_fixture_calls':voice.calls,'live_jev':False,'real_asr':False,'physical_microphone':False,'physical_monitor_mapping':False})
            (output/'ACCEPTANCE_M07.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
            return result
        finally:app.shutdown();app.server_close();thread.join(timeout=10)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='docs/evidence/m07-2026-11-01');args=parser.parse_args()
    print(json.dumps(run(args.output),ensure_ascii=False,indent=2))
