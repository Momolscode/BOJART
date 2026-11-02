"""Browser UI with an explicitly simulated transport.
The managed browser forbids localhost navigation (ERR_BLOCKED_BY_ADMINISTRATOR).
No policy bypass: test HTML via set_content and deterministic response fixtures.
Real HTTP security and CAD execution are tested separately in test_mission01.py.
"""
import sys,json,tempfile,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Store,parse_command
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(name,ok=True):
 if not ok:raise AssertionError(name)
 checks.append({'test':name,'passed':True})

def main():
 with tempfile.TemporaryDirectory() as t:
  store=Store(t);fixtures={}
  for n,d in enumerate([180,240]):
   r=store.run({'operation_id':str(n+1)*32,'project_id':'BOJ-PILOTE-001','expected_revision':n,'params':parse_command(f'Crée un socle de {d} mm')['params']})
   fixtures[str(d)]={'result':r,'mesh':json.loads((store.artifacts/r['operation_id']/'modele.json').read_text()),'parsed':parse_command(f'Crée un socle de {d} mm')}
  context=json.loads((ROOT/'context/CONTEXTE_REFERENCE.json').read_text())
  init='const FIXTURES='+json.dumps(fixtures,ensure_ascii=False)+';const TEST_CONTEXT='+json.dumps(context,ensure_ascii=False)+';'+r'''
  window.testRequests=[];window.testRevision=0;window.testJobs=[];window.testOperationMap={};
  window.fetch=async function(path,options={}){
   testRequests.push(path);await new Promise(r=>setTimeout(r,5));let body=options.body?JSON.parse(options.body):null;
   const response=(x,ok=true)=>({ok,json:async()=>x});
   if(path==='/api/state')return response({revision:testRevision,project_id:'BOJ-PILOTE-001',context:TEST_CONTEXT,jobs:testJobs,capabilities:{cadquery_available:true}});
   if(path==='/api/parse'){
    if(body.command.includes('imprime'))return response({error:'Commande non prise en charge'},false);
    return response(FIXTURES[body.command.includes('24 cm')?'240':'180'].parsed);
   }
   if(path==='/api/mission'){
    const d=String(body.params.diameter_mm),r=JSON.parse(JSON.stringify(FIXTURES[d].result));
    r.operation_id=body.operation_id;testRevision=r.revision;testOperationMap[r.operation_id]={result:r,mesh:FIXTURES[d].mesh};
    testJobs.unshift({id:r.operation_id,project:r.project_id,state:r.state});return response(r);
   }
   if(path.startsWith('/api/jobs/'))return response(testOperationMap[path.split('/').pop()].result);
   if(path.startsWith('/artifacts/'))return response(testOperationMap[path.split('/')[2]].mesh);
   if(path==='/api/backup')return response({url:'/backups/test.zip',files:18,sha256:'SIMULATED-TRANSPORT-NOT-A-REAL-BACKUP'});
   return response({error:'not found'},false);
  };
  '''
  html=(ROOT/'app/index.html').read_text().replace('/*__SNAPSHOT__*/',init)
  # sessionStorage is origin-restricted in about:blank; provide a test-only memory fixture.
  html=html.replace("const OFFLINE=typeof SNAPSHOT", "const testStorage={};const sessionStorage={getItem:k=>testStorage[k]||null,setItem:(k,v)=>testStorage[k]=v,removeItem:k=>delete testStorage[k]};const OFFLINE=typeof SNAPSHOT")
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
   ctx=browser.new_context(viewport={'width':1540,'height':1120},reduced_motion='reduce')
   page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.set_content(html);page.wait_for_selector('#parse')
   page.locator('#parse').click();page.wait_for_function("document.querySelector('#status').textContent.includes('Demande comprise')")
   check('Lecture demande : UI affiche 180 mm',page.locator('#diameter_mm').input_value()=='180')
   page.locator('#generate').click();page.wait_for_function("document.querySelector('#status').textContent.includes('Modèle créé')",timeout=10000)
   check('Rendu du véritable maillage fourni en fixture',int(page.locator('#canvas').get_attribute('data-rendered-triangles'))>100)
   check('Quatre exports disponibles',page.locator('#downloads a').count()==4)
   page.screenshot(path=str(ROOT/'preuves/POSTE_MISSION01_DESKTOP.png'),full_page=True)
   page.locator('#canvas').focus();before=page.locator('#canvas').evaluate('(c)=>c.toDataURL()');page.keyboard.press('ArrowRight');after=page.locator('#canvas').evaluate('(c)=>c.toDataURL()')
   check('Rotation du maillage au clavier',before!=after)
   page.locator('#example').click();page.locator('#parse').click();page.wait_for_function("document.querySelector('#diameter_mm').value==='240'")
   page.locator('#generate').click();page.wait_for_function("document.querySelector('#diameter').textContent==='240 × 24 mm'")
   check('Mise à jour du diamètre et de la révision',page.locator('#revision').inner_text()=='02')
   page.locator('#command').fill('Crée un socle de 180 mm et imprime P01');page.locator('#parse').click();page.wait_for_function("document.querySelector('#status').classList.contains('error')")
   check('Affichage explicite du refus, pas de faux succès',page.locator('#status').inner_text()=='Commande non prise en charge')
   page.locator('#backup').click();page.wait_for_selector('#backupstatus a')
   check('Interface sauvegarde sans confusion avec génération',page.locator('#backupstatus a').inner_text()=='Récupérer la sauvegarde')
   check('Aucun endpoint extérieur appelé par l’UI',all(x.startswith('/') for x in page.evaluate('testRequests')))
   check('Aucune erreur JavaScript',not errors)
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100)
   check('Mobile sans débordement horizontal',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
   page.screenshot(path=str(ROOT/'preuves/POSTE_MISSION01_MOBILE.png'),full_page=True)
   check('Réduction du mouvement reconnue',page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
   page.set_viewport_size({'width':1540,'height':1120})
   page.evaluate("() => {window.fixtureFetch=window.fetch;window.failModel=true;window.fetch=async (p,o)=>p.startsWith('/artifacts/')&&window.failModel?{ok:false,json:async()=>({error:'Fichier indisponible'})}:window.fixtureFetch(p,o);}")
   page.locator('#generate').click();page.wait_for_function("document.querySelector('#status').textContent.includes('affichage du fichier non vérifié')")
   check('Fichier indisponible : aucun faux succès UI',page.locator('#generate').is_disabled() and not page.locator('#retry').is_hidden())
   calls=page.evaluate("testRequests.filter(x=>x==='/api/mission').length")
   page.evaluate('window.failModel=false');page.locator('#retry').click();page.wait_for_function("document.querySelector('#status').textContent.includes('Reçu retrouvé')")
   check('Reprise affichage sans deuxième création',page.evaluate("testRequests.filter(x=>x==='/api/mission').length")==calls)
   offline=ctx.new_page();req=[];offline.on('request',lambda r:req.append(r.url))
   offline.set_content((ROOT/'APERCU_MISSION_01.html').read_text());offline.wait_for_function("document.querySelector('#canvas').dataset.renderedTriangles>0")
   check('Aperçu autonome : génération désactivée',offline.locator('#generate').is_disabled())
   check('Aperçu autonome : aucune requête réseau',not req)
   offline.screenshot(path=str(ROOT/'preuves/APERCU_MISSION01.png'),full_page=True)
   browser.close()
  result={'browser':'Chromium /usr/bin/chromium','scope':'HTML via set_content, transport API simulé, géométries réelles calculées séparément. HTTP réel testé dans test_mission01.py.',
    'limitation':'Navigation localhost bloquée par la politique du navigateur : intégration directe navigateur → HTTP à qualifier sur la tour. Aucune politique modifiée.', 'passed':len(checks),'checks':checks}
  (ROOT/'preuves/TESTS_INTERFACE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
