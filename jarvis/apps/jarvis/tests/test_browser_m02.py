"""UI on set_content + explicit test bridge -> real HTTP service and real CAD.
Browser network access remains blocked by managed policy. No policy is disabled.
Voice UI tests use a synthetic WAV and a controlled transcriber, NOT a real microphone/model.
"""
from pathlib import Path
import array,http.client,io,json,math,sys,tempfile,threading,wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Store
from workbench import Workbench
from voice import LocalVoice
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'preuves';checks=[];errors=[]
def check(name,ok=True,scope='Chromium UI + pont de test explicite + vrai HTTP/CadQuery'):
 if not ok:raise AssertionError(name)
 checks.append({'name':name,'passed':True,'scope':scope});print('PASS',name,flush=True)

def html_with_bridge():
 s=(ROOT/'app/console.html').read_text()
 s=s.replace('<link rel="stylesheet" href="/ui.css">','<style>'+(ROOT/'app/ui.css').read_text()+'</style>')
 for name in ['viewer','capture','ui']:
  code=(ROOT/'app'/f'{name}.js').read_text()
  s=s.replace(f'<script src="/{name}.js"></script>','<script>'+code+'</script>')
 shim=r'''<script>
 const testStorage={};const sessionStorage={getItem:k=>testStorage[k]||null,setItem:(k,v)=>testStorage[k]=v,removeItem:k=>delete testStorage[k]};
 window.fetch=async(path,options={})=>{
  const body=options.body instanceof ArrayBuffer?Array.from(new Uint8Array(options.body)):options.body;
  const r=await window.testHTTP({path,method:options.method||'GET',body,headers:options.headers||{}});
  if(path==='/api/propose'&&window.delayPropose)await new Promise(resolve=>setTimeout(resolve,window.delayPropose));
  return {ok:r.status>=200&&r.status<300,status:r.status,json:async()=>JSON.parse(r.body)};
 };
 </script>'''
 return s.replace('<script>',shim+'<script>',1)

def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);server=Workbench(('127.0.0.1',0),Store(root/'state'),token='ui-test')
  threading.Thread(target=server.serve_forever,daemon=True).start();calls=[]
  def bridge(_source,r):
   assert r['path'].startswith('/') and not r['path'].startswith('//')
   headers={'Host':server.host_name,'Origin':server.origin,'Cookie':'boj_session=ui-test','Content-Type':r['headers'].get('Content-Type','application/json')}
   body=bytes(r['body']) if isinstance(r.get('body'),list) else r.get('body')
   if isinstance(body,str):body=body.encode('utf-8')
   conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=60)
   try:
    conn.request(r['method'],r['path'],body,headers);res=conn.getresponse();raw=res.read();calls.append({'path':r['path'],'status':res.status})
    return {'status':res.status,'body':raw.decode('utf-8')}
   finally:conn.close()
  try:
   with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=b.new_context(viewport={'width':1600,'height':1140},reduced_motion='reduce');page=ctx.new_page();page.expose_binding('testHTTP',bridge)
    page.on('pageerror',lambda e:errors.append(str(e)));browser_requests=[];page.on('request',lambda r:browser_requests.append(r.url))
    page.set_content(html_with_bridge());page.wait_for_function("document.getElementById('cadHealth').textContent.includes('présentes')")
    check('UI reçoit le vrai état du service via pont explicite')
    check('Micro désactivé sans moteur configuré',page.locator('#record').is_disabled())
    page.locator('#prepare').click();page.wait_for_function("!document.getElementById('confirm').disabled")
    check('Dix-huit centimètres devient 180 mm','180' in page.locator('#proposedDiameter').inner_text())
    check('Aucune construction à la seule interprétation',server.store.project_revision()==0)
    page.screenshot(path=str(E/'M02_PROPOSITION_DESKTOP.png'),full_page=True)
    page.locator('#confirm').click();page.wait_for_function("document.getElementById('modelRev').textContent==='R1'",timeout=60000);page.wait_for_function("!document.getElementById('refresh').disabled")
    check('Vraie création CAO, une révision seulement',server.store.project_revision()==1)
    check('Affichage du véritable maillage',int(page.locator('#canvas').get_attribute('data-rendered-triangles') or 0)>100)
    check('Exports liés à la bonne opération',page.locator('#downloads a').count()==4)
    before=page.locator('#canvas').screenshot();page.locator('#canvas').focus();page.keyboard.press('ArrowRight');after=page.locator('#canvas').screenshot();check('Rotation clavier',before!=after)
    page.locator('#sample24').click();page.locator('#prepare').click();page.wait_for_function("!document.getElementById('confirm').disabled")
    check('Variante proposée séparément','240' in page.locator('#proposedDiameter').inner_text())
    page.locator('#command').fill('Crée un socle de 180 mm sans trous');page.locator('#prepare').click();page.wait_for_function("document.getElementById('feedback').classList.contains('error')")
    check('Pas de contrainte ignorée',page.locator('#confirm').is_disabled() and server.store.project_revision()==1)
    page.evaluate('window.delayPropose=300');page.locator('#sample18').click();page.locator('#prepare').click();page.locator('#command').fill('Crée un socle de 30 cm');page.wait_for_function("!document.getElementById('prepare').disabled");page.evaluate('window.delayPropose=0')
    check('Réponse tardive écartée après édition','écartée' in page.locator('#feedback').inner_text() and page.locator('#confirm').is_disabled())
    page.locator('#sampleState').click();page.locator('#prepare').click();page.wait_for_function("!document.getElementById('prepare').disabled")
    check('État du dossier lu sans création',server.store.project_revision()==1)
    page.locator('#diagnose').click();page.wait_for_function("!document.getElementById('diagnose').disabled",timeout=20000)
    check('Diagnostic de l’hôte de test, sans scan privé',page.locator('#exportDiagnostic').is_visible())
    page.locator('#backup').click();page.wait_for_selector('#backupNote a',timeout=20000)
    check('Sauvegarde réelle produite via serveur','fichiers vérifiés' in page.locator('#backupNote').inner_text())
    page.locator('#sample18').click();page.locator('#prepare').click();page.wait_for_function("!document.getElementById('confirm').disabled")
    page.screenshot(path=str(E/'M02_DESKTOP_RESULTAT.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(E/'M02_MOBILE.png'),full_page=True)
    check('Aucun débordement mobile',page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'))
    check('Pas d’appels réseau navigateur',not browser_requests)
    # Exercise browser WAV encoder independently of microphone availability.
    encoded=page.evaluate('Array.from(new Uint8Array(BojCapture.encodeForTest(new Float32Array(48000).map((_,i)=>0.1*Math.sin(i*0.04)),48000)))')
    from voice import validate_audio
    q=validate_audio(bytes(encoded));check('Encodeur PCM navigateur : 1 seconde WAV 16k',q['seconds']==1 and not q['silence'])
    # Configure a controlled transcript backend and synthetic capture to verify review boundaries.
    weights=root/'fakeweights';weights.mkdir()
    for n in ['model.bin','config.json','tokenizer.json']:(weights/n).write_text('test fixture, not weights')
    class M:
     def transcribe(self,stream,**opts):return iter([type('Seg',(),{'text':'Crée un socle de dix-huit centimètres'})()]),None
    server.voice=LocalVoice({'enabled':True,'model_dir':str(weights)},loader=lambda:M())
    page.locator('#refresh').click();page.wait_for_function("!document.getElementById('record').disabled")
    page.evaluate('''window.BojCapture.start=async callback=>{};window.BojCapture.cancel=async()=>{};window.BojCapture.stop=async()=>BojCapture.encodeForTest(new Float32Array(48000).map((_,i)=>0.1*Math.sin(i*0.04)),48000)''')
    page.locator('#record').click();page.wait_for_function("document.body.classList.contains('recording')");page.locator('#record').click();page.wait_for_function("!document.getElementById('prepare').disabled")
    check('Prise simulée → WAV → HTTP réel → transcription contrôlée','dix-huit' in page.locator('#command').input_value(),'capture simulée et transcripteur doublure ; aucune précision vocale mesurée')
    check('Transcription seule n’exécute rien',server.store.project_revision()==1 and page.locator('#confirm').is_disabled(),'transcripteur doublure')
    check('Fin de prise éteint le témoin',not page.evaluate("document.body.classList.contains('recording')"),'capture simulée')
    check('Aucune erreur JavaScript',not errors)
    b.close()
  finally:server.shutdown();server.server_close()
 E.joinpath('TESTS_INTERFACE_M02.json').write_text(json.dumps({'transport':'set_content + binding Python de test vers vrai serveur HTTP ; accès direct localhost non qualifié','checks':checks,'errors':errors,'http_calls':calls},ensure_ascii=False,indent=2))
 print(json.dumps({'passed':len(checks),'errors':errors,'voice_inference_real':False,'browser_direct_localhost':False},ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception:
  E.joinpath('TESTS_INTERFACE_PARTIAL.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));raise
