#!/usr/bin/env python3
"""Actual Chromium M06 integration, with explicit synthetic audio/ASR fixtures."""
import argparse, json, math, platform, struct, subprocess, sys, tempfile, threading, time, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, now
from voice import validate_audio
from consolidated_workbench import ConsolidatedWorkbench


class ASRFixture:
    def status(self):return {'status':'available','message':'Synthetic ASR test fixture, not a real recognizer.'}
    def transcribe(self, raw):
        validate_audio(raw)
        time.sleep(.6)
        return {'status':'draft','text':'Montre les dossiers au centre','audio_stored':False,'requires_review':True,'fixture':True}


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='boj-m06-acceptance-') as tmp:
        root=Path(tmp);wav=root/'synthetic.wav'
        with wave.open(str(wav),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(48000)
            out.writeframes(b''.join(struct.pack('<h',int(7000*math.sin(2*math.pi*440*i/48000))) for i in range(48000*12)))
        app=ConsolidatedWorkbench(('127.0.0.1',0),Store(root/'work'),voice=ASRFixture())
        thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        try:
            result=subprocess.run(['node',str(ROOT/'tools/m06_browser.cjs')],input=json.dumps({'origin':app.origin,'token':app.token,'wav':str(wav),'output':str(output)}),capture_output=True,text=True,timeout=180)
            if result.returncode:raise RuntimeError(result.stderr[-7000:])
            report=json.loads(result.stdout)
            report.update({'schema':'bojart.acceptance.m06.v1','observed_at':now(),'python':platform.python_version(),'platform':platform.system(),'graph':app.jarvis.graph_status})
            (output/'ACCEPTANCE_M06.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            return report
        finally:app.shutdown();app.server_close();thread.join(timeout=10)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='docs/evidence/m06-2026-10-31');args=parser.parse_args()
    print(json.dumps(run(args.output),ensure_ascii=False,indent=2))
