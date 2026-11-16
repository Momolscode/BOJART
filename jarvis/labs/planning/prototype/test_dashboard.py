from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
    errors=[]; requests=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.on('request',lambda r: requests.append(r.url))
    page.set_content((ROOT/'APERCU_PLANNING.html').read_text(encoding='utf-8'), wait_until='load')
    def check(name,predicate):
        if not predicate: raise AssertionError(name)
        checks.append({'name':name,'pass':True})
    check('Données fictives visibles',page.get_by_text('LABORATOIRE · DONNÉES FICTIVES · HORS MACHINES').is_visible())
    check('Baseline',page.locator('#status').inner_text()=='Plan trouvé')
    check('Trois dossiers',page.locator('#rows tr').count()==3)
    check('Aucun débordement desktop',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    page.screenshot(path=str(ROOT/'preuves/APERCU_DESKTOP.png'),full_page=True)
    page.get_by_role('button',name='Une résine indisponible').click()
    check('Scénario indisponibilité',page.locator('#scenario').inner_text()=='Machine résine B indisponible')
    check('Machine B non affectée', 'RESINE-B' not in page.locator('#rows').inner_text())
    page.get_by_role('button',name='Finition × 2').click()
    check('Finition retard',page.locator('#status').inner_text()=='Échéance dépassée')
    page.get_by_role('button',name='Échéance courte').click()
    check('Échéance courte',page.locator('#status').inner_text()=='Échéance dépassée')
    page.get_by_role('button',name='Compatibilité absente').click()
    check('Bloqué sans compatibilité',page.locator('#status').inner_text()=='Bloqué')
    page.get_by_role('button',name='Situation de départ').focus();page.keyboard.press('Enter')
    check('Clavier',page.locator('#status').inner_text()=='Plan trouvé')
    page.set_viewport_size({'width':390,'height':844})
    check('Pas de débordement mobile',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    page.screenshot(path=str(ROOT/'preuves/APERCU_MOBILE.png'),full_page=True)
    page.emulate_media(reduced_motion='reduce')
    check('Réduction de mouvement',page.locator('.block').first.evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s')
    check('Aucune erreur JS',not errors)
    check('Aucune requête HTTP externe',not any(x.startswith(('https:','http:')) for x in requests))
    browser.close()
(ROOT/'preuves/TESTS_INTERFACE.json').write_text(json.dumps({'checks':checks,'count':len(checks),'errors':errors,'scope':'HTML injecté dans Chromium headless avec set_content. Navigation file:// interdite par la politique du navigateur. Aucun backend, modèle IA ou matériel.'},indent=2,ensure_ascii=False),encoding='utf-8')
print(f'{len(checks)} contrôles interface réussis')
