"""Real Chromium + local backend integration, not a mock of the UI."""
from pathlib import Path
import sys,json,tempfile,threading,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Store,verify_backup
from server import AppServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(label,value=True):
 if not value: raise AssertionError(label)
 checks.append({'test':label,'passed':True})

def main():
 with tempfile.TemporaryDirectory() as td:
  store=Store(Path(td)/'state');srv=AppServer(('127.0.0.1',0),store,'browser-test-secret')
  th=threading.Thread(target=srv.serve_forever,daemon=True);th.start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':1540,'height':1120},reduced_motion='reduce')
    page=ctx.new_page();errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
    page.goto(srv.origin+'/?session=browser-test-secret');page.wait_for_selector('#parse')
    check('Session ouverte, URL nettoyée',page.url==srv.origin+'/')
    page.locator('#parse').click();page.wait_for_function("document.querySelector('#status').textContent.includes('Demande comprise')")
    check('Commande française → paramètres 180 mm',page.locator('#diameter_mm').input_value()=='180')
    page.locator('#generate').click();page.wait_for_function("document.querySelector('#status').textContent.includes('Modèle créé')",timeout=45000)
    check('CAO réelle calculée via interface',page.locator('#diameter').inner_text()=='180 × 24 mm')
    check('Vrai maillage rendu dans le Canvas',int(page.locator('#canvas').get_attribute('data-rendered-triangles'))>100)
    check('Liens STEP, STL, GLB et reçu',page.locator('#downloads a').count()==4)
    page.screenshot(path=str(ROOT/'preuves/POSTE_MISSION01_DESKTOP.png'),full_page=True)
    page.locator('#canvas').focus();before=page.locator('#canvas').evaluate('(c)=>c.toDataURL()');page.keyboard.press('ArrowRight');after=page.locator('#canvas').evaluate('(c)=>c.toDataURL()')
    check('Rotation clavier change le vrai maillage',before!=after)
    page.locator('#example').click();page.locator('#parse').click();page.wait_for_function("document.querySelector('#diameter_mm').value==='240'")
    page.locator('#generate').click();page.wait_for_function("document.querySelector('#diameter').textContent==='240 × 24 mm'",timeout=45000)
    check('Deuxième dimension, deuxième révision',store.project_revision()==2)
    page.locator('#command').fill('Crée un socle de 180 mm et imprime sur P01');page.locator('#parse').click();page.wait_for_function("document.querySelector('#status').classList.contains('error')")
    check('Action machine refusée sans modifier le dossier',store.project_revision()==2)
    page.locator('#backup').click();page.wait_for_selector('#backupstatus a',timeout=20000)
    bpath=store.root/'backups'/Path(page.locator('#backupstatus a').get_attribute('href')).name
    check('Sauvegarde UI créée et vérifiée',verify_backup(bpath)['ok'])
    page.reload();page.wait_for_function("document.querySelector('#revision').textContent==='02'",timeout=15000)
    check('Rouvrir conserve version et modèle',page.locator('#modelTitle').inner_text().startswith('Socle Ø 240'))
    check('Aucun appel à un site extérieur',all(x.startswith(srv.origin) for x in requests))
    check('Pas d’erreur JavaScript',not errors)
    mobile=ctx.new_page(viewport={'width':390,'height':844});mobile.goto(srv.origin+'/');mobile.wait_for_function("document.querySelector('#canvas').dataset.renderedTriangles>0",timeout=15000)
    check('Mobile sans débordement horizontal',mobile.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    mobile.screenshot(path=str(ROOT/'preuves/POSTE_MISSION01_MOBILE.png'),full_page=True)
    check('Mode réduction du mouvement',mobile.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
    # The autonomous copy is really opened via file://, not injected into a DOM.
    offline=ctx.new_page();oreq=[];offline.on('request',lambda r:oreq.append(r.url))
    offline.goto((ROOT/'APERCU_MISSION_01.html').as_uri());offline.wait_for_function("document.querySelector('#canvas').dataset.renderedTriangles>0")
    check('Aperçu file:// réel, moteur désactivé',offline.locator('#generate').is_disabled() and not any(x.startswith(('http:','https:')) for x in oreq))
    offline.screenshot(path=str(ROOT/'preuves/APERCU_MISSION01.png'),full_page=True)
    browser.close()
  finally:srv.shutdown();srv.server_close()
 result={'browser':'Chromium /usr/bin/chromium','scope':'backend local réel + UI ; aucun matériel cible, voix ou fournisseur connecté','checks':checks,'passed':len(checks)}
 (ROOT/'preuves/TESTS_NAVIGATEUR.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
