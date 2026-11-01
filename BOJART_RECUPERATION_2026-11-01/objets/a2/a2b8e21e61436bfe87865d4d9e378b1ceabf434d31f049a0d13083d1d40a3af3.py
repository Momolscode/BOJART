#!/usr/bin/env python3
"""Deterministic browser-frame capture + FFmpeg export for clock-controlled Anatomy-like scenes."""
import argparse, json, hashlib, subprocess, pathlib, tempfile
from playwright.sync_api import sync_playwright

def export(scene, output, seconds=7, fps=24, width=540, height=960):
    scene=pathlib.Path(scene).resolve(); output=pathlib.Path(output).resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        folder=pathlib.Path(td); errors=[]; hashes=[]
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-web-security'])
            page=browser.new_page(viewport={'width':width,'height':height}, device_scale_factor=1)
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.goto('about:blank'); page.set_content(scene.read_text(encoding='utf-8'),wait_until='load')
            if not page.evaluate('typeof window.renderAt === "function"'): raise RuntimeError('Scene requires window.renderAt(seconds) deterministic clock adapter')
            for i in range(round(seconds*fps)):
                page.evaluate('(t) => window.renderAt(t)',i/fps)
                data=page.screenshot(type='png',animations='disabled')
                (folder/f'{i:05d}.png').write_bytes(data)
                hashes.append(hashlib.sha256(data).hexdigest())
            browser.close()
        cmd=['ffmpeg','-y','-v','error','-framerate',str(fps),'-i',str(folder/'%05d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-movflags','+faststart',str(output)]
        subprocess.run(cmd,check=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
        report={'source':str(scene),'type':'synthetic reference scene (NOT full Anatomy integration)','output':str(output),'frames':len(hashes),'unique_frame_hashes':len(set(hashes)),'browser_errors':errors,'ffprobe':{'duration':probe['format']['duration'],'width':probe['streams'][0]['width'],'height':probe['streams'][0]['height'],'fps':probe['streams'][0]['r_frame_rate']},'network':'no external network requests required by scene'}
        output.with_suffix('.report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        if errors or len(set(hashes))<len(hashes)*.8: raise RuntimeError('Quality checks failed')
        return report
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('scene');ap.add_argument('output');ap.add_argument('--seconds',type=float,default=7);ap.add_argument('--fps',type=int,default=24);a=ap.parse_args();print(json.dumps(export(a.scene,a.output,a.seconds,a.fps),indent=2))
