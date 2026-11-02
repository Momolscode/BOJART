"""Real Chromium against the actual local HTTP server. No mock transport."""
from pathlib import Path
import sys,tempfile,threading,json,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Store
from studio_workbench import StudioWorkbench
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];proof=ROOT/'preuves_m03';checks=[]
def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append({'name':name,'passed':True})
with tempfile.TemporaryDirectory() as td:
 app=StudioWorkbench(('127.0.0.1',0),Store(td));thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
   page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
   errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
   page.goto(app.origin+'/?session='+app.token,wait_until='networkidle')
   check('real_local_M02_route',page.locator('a[href="/studio"]').count()==1)
   page.locator('a[href="/studio"]').click();page.wait_for_function("document.getElementById('segmentCount').textContent==='8'")
   check('catalogue_real_http',page.locator('.segment').count()==8)
   check('three_actual_media',page.locator('#assetCount').inner_text()=='3')
   check('four_authentic_anchors',page.locator('#anchorCount').inner_text()=='4')
   page.wait_for_function("document.querySelector('video').readyState>=1")
   check('real_video_metadata_loaded',abs(page.evaluate('document.querySelector("video").duration')-15.1)<.2)
   page.locator('#search').fill('référence');check('accent_keyword_search',page.locator('.segment').count()==3)
   page.locator('#search').fill('aerographe');check('absent_search_no_invention',page.locator('#empty').is_visible())
   page.locator('#search').fill('');page.locator('#authentic').click();check('authentic_filter',page.locator('.segment').count()==4)
   page.locator('[data-segment="profil"]').click();page.wait_for_timeout(100)
   check('source_timecode_seek',abs(page.evaluate('document.querySelector("video").currentTime')-5)<.2)
   page.locator('#prepare').click();page.wait_for_function("!document.getElementById('export').disabled")
   check('brief_prepared_actual_sqlite',len(app.library.db.execute('select * from plans').fetchall())==1)
   page.locator('#prepare').click();page.wait_for_timeout(100)
   check('repeat_no_duplicate_brief',len(app.library.db.execute('select * from plans').fetchall())==1)
   page.locator('#verify').click();page.wait_for_timeout(100)
   check('verification_live', 'cette vérification' in page.locator('#feedback').inner_text())
   with page.expect_download() as download:page.locator('#export').click()
   saved=proof/'BRIEF_EXPORT_NAVIGATEUR.json';download.value.save_as(saved)
   exported=json.loads(saved.read_text());check('export_matches_source',exported['anchor_id']=='visage' and not exported['publish_allowed'])
   page.locator('[data-segment="visage"]').click();page.wait_for_timeout(250)
   check('desktop_no_horizontal_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
   page.screenshot(path=str(proof/'STUDIO_DESKTOP.png'),full_page=True)
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100)
   check('mobile_no_horizontal_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
   page.screenshot(path=str(proof/'STUDIO_MOBILE.png'),full_page=True)
   page.emulate_media(reduced_motion='reduce');check('reduced_motion',page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
   check('no_js_errors',not errors)
   check('no_external_network',all(u.startswith(app.origin) or u.startswith(('blob:','data:')) for u in requests))
   browser.close()
 finally:app.shutdown();app.server_close();thread.join()
(proof/'TESTS_NAVIGATEUR.json').write_text(json.dumps({'count':len(checks),'transport':'direct HTTP to real server; no bridge or mock','checks':checks},ensure_ascii=False,indent=2))
print(json.dumps({'passed':len(checks),'transport':'real_local_http'},ensure_ascii=False))
