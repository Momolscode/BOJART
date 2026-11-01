"""Offline preview only. Chromium receives self-contained HTML with actual proxies.
The real server is tested separately by test_studio_http.py.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
ROOT=Path(__file__).resolve().parents[1];proof=ROOT/'preuves_m03';checks=[]
def check(name,value):
 if not value:raise AssertionError(name)
 checks.append({'name':name,'passed':True})
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
 errors=[];req=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:req.append(r.url))
 page.set_content((ROOT/'APERCU_STUDIO_M03.html').read_text(),wait_until='load')
 page.wait_for_function("document.getElementById('segmentCount').textContent==='8'")
 check('three_sources',page.locator('#assetCount').inner_text()=='3')
 check('eight_segments',page.locator('.segment').count()==8)
 check('four_authentic_anchors',page.locator('#anchorCount').inner_text()=='4')
 check('offline_label', 'PRÉCALCULÉS' in page.locator('#mode').inner_text())
 page.wait_for_function("document.querySelector('video').readyState>=1")
 check('proxy_video_loaded',abs(page.evaluate('document.querySelector("video").duration')-15.1)<.2)
 page.locator('#search').fill('référence');check('accent_search',page.locator('.segment').count()==3)
 page.locator('#search').fill('aerographe');check('no_invented_result',page.locator('#empty').is_visible())
 page.locator('#search').fill('');page.locator('#authentic').click();check('original_filter',page.locator('.segment').count()==4)
 page.locator('[data-segment="profil"]').click();page.wait_for_timeout(100);check('timecode_seek',abs(page.evaluate('document.querySelector("video").currentTime')-5)<.2)
 page.locator('#play').click();page.wait_for_timeout(1800);check('segment_stops',page.evaluate('document.querySelector("video").paused') and page.evaluate('document.querySelector("video").currentTime')<6.3)
 page.locator('#prepare').click();check('example_brief_flagged', 'précalculé' in page.locator('#feedback').inner_text())
 page.locator('#verify').click();check('verification_dated', 'construire cet aperçu' in page.locator('#feedback').inner_text())
 with page.expect_download() as d:page.locator('#export').click()
 out=proof/'BRIEF_EXPORT_APERCU.json';d.value.save_as(out);body=json.loads(out.read_text());check('export_traceable',body['anchor_id']=='visage' and not body['publish_allowed'])
 page.locator('[data-segment="visage"]').click();page.wait_for_timeout(100)
 check('desktop_no_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.screenshot(path=str(proof/'STUDIO_DESKTOP.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100)
 check('mobile_no_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.screenshot(path=str(proof/'STUDIO_MOBILE.png'),full_page=True)
 page.emulate_media(reduced_motion='reduce');check('reduced_motion',page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
 page.locator('#search').focus();page.keyboard.type('socle');check('keyboard_search',page.locator('.segment').count()==2)
 check('no_script_errors',not errors)
 check('no_external_requests',all(u.startswith(('data:','blob:')) for u in req))
 browser.close()
(proof/'TESTS_APERCU_M03.json').write_text(json.dumps({'passed':len(checks),'scope':'offline self-contained preview, not direct browser-server integration','checks':checks},ensure_ascii=False,indent=2))
print(json.dumps({'passed':len(checks),'scope':'offline_preview'}))
