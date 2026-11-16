const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const {JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'..'),dist=path.join(root,'dist');
const seedKey='bojart.workshop.v1.seed',opKey='bojart.workshop.v1.op.qa-recovery-operation';
const seed={version:1,at:1760000000000};
const operation={version:1,id:'qa-recovery-operation',clock:1,at:1760000000001,type:'ADD_PROJECT',payload:{id:'qa-recovery-project',name:'DOSSIER QA CONSERVÉ',height:125,kind:'prototype',quantity:1,notes:'Note de référence QA'},expected:{entityVersion:0},context:{projectId:'qa-recovery-project',projectName:'DOSSIER QA CONSERVÉ',pieceId:null,machineId:null,originProjectId:'sculpture-xl'}};
const validEntries=()=>[[seedKey,JSON.stringify(seed)],[opKey,JSON.stringify(operation)]];
class Storage {
  constructor(entries=validEntries()){this.entries=new Map(entries);this.writes=0;}
  get length(){return this.entries.size;}
  key(index){return [...this.entries.keys()][index]??null;}
  getItem(key){return this.entries.get(key)??null;}
  setItem(key,value){this.writes++;this.entries.set(key,String(value));}
  removeItem(key){this.entries.delete(key);}
  snapshot(){return JSON.stringify([...this.entries].sort(([a],[b])=>a.localeCompare(b)));}
}
const fixtures=new Set(),checks=[],unhandled=[];
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function settle(){for(let i=0;i<6;i++)await tick();}
const rejectListener=error=>unhandled.push(String(error?.stack||error));
process.on('unhandledRejection',rejectListener);
async function surface(storage=new Storage()){
  const dom=new JSDOM(fs.readFileSync(path.join(dist,'index.html'),'utf8'),{url:'https://bojart.test/?screen=pilotage&station=pilotage',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,context=dom.getInternalVMContext(),f={dom,w,context,storage,modules:new Map(),errors:[],fetchCalls:[],downloads:[],blobs:new Map()};fixtures.add(f);
  Object.defineProperty(w,'localStorage',{value:storage});w.matchMedia=()=>({matches:true,addEventListener(){}});w.scrollTo=()=>{};w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.Blob=Blob;
  Object.defineProperty(w.crypto,'subtle',{value:webcrypto.subtle});
  w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');this.dispatchEvent(new w.Event('close'));};
  w.HTMLCanvasElement.prototype.getContext=()=>null;w.HTMLMediaElement.prototype.pause=function(){};w.HTMLMediaElement.prototype.play=async()=>{};
  w.URL.createObjectURL=blob=>{const url='blob:qa-recovery-'+f.blobs.size;f.blobs.set(url,blob);return url;};w.URL.revokeObjectURL=()=>{};
  w.HTMLAnchorElement.prototype.click=function(){f.downloads.push({href:this.href,name:this.download});};
  w.addEventListener('error',event=>{f.errors.push(event.error?.message||event.message);event.preventDefault();});
  w.BroadcastChannel=class{postMessage(){}addEventListener(){}removeEventListener(){}close(){}};
  const json=(value,status=200)=>({ok:status>=200&&status<300,status,json:async()=>w.JSON.parse(JSON.stringify(value)),text:async()=>JSON.stringify(value)});
  w.fetch=async(input,options={})=>{const url=new w.URL(String(input),w.location.href);f.fetchCalls.push({path:url.pathname,method:options.method||'GET'});if(url.pathname==='/assets/archive-index.json')return json([]);return json({ok:false,code:'service_absent'},404);};
  const viewer=new vm.SyntheticModule(['createViewer','inspectSTL'],function(){this.setExport('createViewer',async()=>({dispose(){},showDemo(){},setWireframe(){},setAutoRotate(){},setMotion(){},setSection(){}}));this.setExport('inspectSTL',()=>({dims:[10,20,30],triangles:12}));},{context});await viewer.link(()=>{});await viewer.evaluate();
  function moduleFor(filename){filename=path.resolve(filename);if(f.modules.has(filename))return f.modules.get(filename);let source=fs.readFileSync(filename,'utf8');if(filename===path.join(dist,'app.js'))source+='\nexport {store as __qaStore};\n';const mod=new vm.SourceTextModule(source,{context,identifier:filename,importModuleDynamically:async(spec,parent)=>spec.endsWith('/viewer.js')||spec==='./viewer.js'?viewer:f.load(path.resolve(path.dirname(parent.identifier),spec))});f.modules.set(filename,mod);return mod;}
  f.load=async filename=>{const mod=moduleFor(filename);if(mod.status==='unlinked')await mod.link((spec,parent)=>moduleFor(path.resolve(path.dirname(parent.identifier),spec)));if(mod.status!=='evaluated')await mod.evaluate();return mod;};
  f.$=selector=>w.document.querySelector(selector);f.$$=selector=>[...w.document.querySelectorAll(selector)];
  f.click=async selector=>{const node=f.$(selector);assert(node,'Contrôle absent : '+selector);node.click();await settle();};
  f.submit=async selector=>{const form=f.$(selector);assert(form,'Formulaire absent : '+selector);form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await settle();};
  f.notify=async key=>{w.dispatchEvent(new w.StorageEvent('storage',{key}));await settle();};
  f.app=await f.load(path.join(dist,'app.js'));f.store=f.app.namespace.__qaStore;await settle();return f;
}
async function check(name,run){await run();checks.push(name);}
(async()=>{
  try{
    await check('Premier démarrage : origine ou opération illisible affiche la récupération, sans démonstration ni appel au service de journal',async()=>{
      for(const [key,value] of [[seedKey,'{ bad origin'],[opKey,'{ bad operation']]){
        const storage=new Storage();storage.setItem(key,value);const before=storage.snapshot(),writes=storage.writes,f=await surface(storage);
        assert.ok(f.$('.integrity-view'));assert.equal(f.store.state.projects.length,0);assert.equal(f.store.integrityError!==null,true);assert.match(f.$('#main').textContent,/Aucun état complet|Aucun atelier de démonstration/);assert.match(f.$('#save-status').textContent,/Journal à vérifier/);assert.equal(storage.snapshot(),before);assert.equal(storage.writes,writes);assert.equal(f.fetchCalls.some(call=>call.path.startsWith('/api/workshop/')),false);assert.deepEqual(f.errors,[]);
      }
    });
    await check('Copie de récupération téléchargée : octets exacts, nom explicite et aucune réécriture',async()=>{
      const storage=new Storage();storage.setItem(opKey,'{ original malformed bytes');storage.setItem('another.application','unrelated private value');const before=storage.snapshot(),f=await surface(storage);
      await f.click('#main [data-action="integrity-export"]');assert.equal(f.downloads.length,1);assert.match(f.downloads[0].name,/BOJ_ART_Recuperation_.*\.json$/);const copy=JSON.parse(await f.blobs.get(f.downloads[0].href).text());assert.equal(copy.format,'bojart.workshop.recovery.v1');assert.equal(copy.entries.find(entry=>entry.key===opKey).value,'{ original malformed bytes');assert.equal(copy.entries.some(entry=>entry.key==='another.application'),false);assert.equal(storage.snapshot(),before);assert.deepEqual(f.errors,[]);
    });
    await check('Réexamens répétés sans réparation : état stable, aucun cycle de rendu ou reprise des services',async()=>{
      const storage=new Storage();storage.removeItem(seedKey);const before=storage.snapshot(),f=await surface(storage);
      for(let i=0;i<5;i++)await f.click('#main [data-action="integrity-recheck"]');assert.equal(f.$$('.integrity-view').length,1);assert.equal(f.$$('.integrity-banner').length,0);assert.equal(storage.snapshot(),before);assert.equal(f.fetchCalls.some(call=>call.path.startsWith('/api/workshop/')),false);assert.deepEqual(f.errors,[]);
    });
    await check('Origine réparée à l’identique puis réexaminée : dossier retrouvé et contrôle de disponibilité relancé',async()=>{
      const storage=new Storage();storage.removeItem(seedKey);const f=await surface(storage);storage.setItem(seedKey,JSON.stringify(seed));await f.click('#main [data-action="integrity-recheck"]');assert.equal(f.store.integrityError,null);assert.equal(f.store.getProject().id,'qa-recovery-project');assert.equal(f.$('.integrity-view'),null);assert.equal(f.w.document.documentElement.classList.contains('integrity-blocked'),false);assert.equal(f.fetchCalls.some(call=>call.path==='/api/workshop/status'),true);assert.deepEqual(f.errors,[]);
    });
    await check('Corruption avec formulaire ouvert : brouillon préservé, bannière unique, soumission bloquée et reprise après réparation',async()=>{
      const storage=new Storage(),f=await surface(storage);await f.click('[data-action="project-edit"]');const form=f.$('#project-form');assert(form);const notes=form.elements.namedItem('notes');notes.value='Brouillon personnel QA à conserver';const old=storage.getItem(opKey);storage.setItem(opKey,'{ corrupt during editing');const before=storage.snapshot();await f.notify(opKey);
      assert.equal(f.$('#project-form'),form);assert.equal(notes.value,'Brouillon personnel QA à conserver');assert.equal(f.$('#drawer').open,true);assert.equal(f.$$('#drawer [data-integrity-banner]').length,1);await f.submit('#project-form');assert.equal(storage.snapshot(),before);assert.equal(notes.value,'Brouillon personnel QA à conserver');
      await f.click('#drawer [data-action="integrity-recheck"]');assert.equal(f.$$('#drawer [data-integrity-banner]').length,1);assert.equal(f.$('#project-form'),form);assert.equal(notes.value,'Brouillon personnel QA à conserver');
      storage.setItem(opKey,old);await f.click('#drawer [data-action="integrity-recheck"]');assert.equal(f.$('#project-form'),form);assert.equal(f.$$('#drawer [data-integrity-banner]').length,0);assert.equal(notes.value,'Brouillon personnel QA à conserver');await f.submit('#project-form');assert.equal(f.store.getProject().notes,'Brouillon personnel QA à conserver');assert.equal(f.$('#drawer').open,false);assert.deepEqual(f.errors,[]);
    });
    await check('Navigation et commandes restent bloquées ; fermeture de panneau reste possible sans ajouter d’opération',async()=>{
      const storage=new Storage(),f=await surface(storage);await f.click('[data-action="project-edit"]');storage.setItem(opKey,'{ corrupt');await f.notify(opKey);const before=storage.snapshot();await f.click('[data-screen="atelier"]');assert.ok(f.$('.integrity-view'));await f.app.namespace.executeCommand('Mets P01 en pause');await settle();assert.equal(storage.snapshot(),before);assert.equal(f.$('#command-dialog').open,false);await f.click('#drawer [data-action="close-dialog"]');assert.equal(f.$('#drawer').open,false);assert.ok(f.$('.integrity-view'));assert.deepEqual(f.errors,[]);
    });
    for(const f of fixtures)assert.deepEqual(f.errors,[]);assert.deepEqual(unhandled,[]);
    const result={ok:true,checksCount:checks.length,checks,scope:'Actual app.js and WorkshopStore in isolated JSDOM surfaces. Only viewer/media/service adapters are stubs. No browser engine, network, SQLite changes or physical commands.'};fs.writeFileSync(path.join(__dirname,'v11-recovery-ui-results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
  }finally{
    for(const f of fixtures){try{f.w.dispatchEvent(new f.w.Event('pagehide'));f.store?.dispose();f.w.close();}catch{}}
    process.removeListener('unhandledRejection',rejectListener);
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
