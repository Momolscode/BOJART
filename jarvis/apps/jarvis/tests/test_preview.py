from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 checks=[]
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=b.new_page(viewport={'width':1600,'height':1140},reduced_motion='reduce');errors=[];requests=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
  page.set_content((ROOT/'APERCU_MISSION_02.html').read_text());page.wait_for_function("document.getElementById('canvas').dataset.renderedTriangles>100")
  assert page.locator('#record').is_disabled();checks.append('Microphone désactivé dans aperçu')
  page.locator('#prepare').click();page.wait_for_function("!document.getElementById('confirm').disabled")
  page.locator('#confirm').click();assert '180' in page.locator('#modelTitle').inner_text();checks.append('Exemple 180 mm')
  page.screenshot(path=str(ROOT/'preuves/APERCU_M02_DESKTOP.png'),full_page=True)
  page.locator('#sample24').click();page.locator('#prepare').click();page.wait_for_function("!document.getElementById('confirm').disabled");page.locator('#confirm').click();assert '240' in page.locator('#modelTitle').inner_text();checks.append('Exemple 240 mm distinct')
  page.locator('#command').fill('Crée un autre objet');page.locator('#prepare').click();page.wait_for_function("document.getElementById('feedback').classList.contains('error')");assert page.locator('#confirm').is_disabled();checks.append('Pas de fausse interprétation libre dans aperçu')
  page.locator('#diagnose').click();assert 'PC cible non analysé' in page.locator('#hardwareHealth').inner_text();checks.append('Pas de faux diagnostic')
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(ROOT/'preuves/APERCU_M02_MOBILE.png'),full_page=True);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');checks.append('Mobile sans débordement')
  assert not errors and not requests;checks.extend(['Aucune erreur JavaScript','Aucun appel réseau'])
  b.close()
 (ROOT/'preuves/TESTS_APERCU.json').write_text(json.dumps({'passed':len(checks),'checks':checks},indent=2,ensure_ascii=False));print('PASS',len(checks))
if __name__=='__main__':main()
