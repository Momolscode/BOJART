const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const dist=path.resolve(__dirname,'../dist');
const html=fs.readFileSync(path.join(dist,'index.html'),'utf8');
const storageData=new Map(),channels=new Map(),surfaces=[],checks=[],errors=[];
const storage={get length(){return storageData.size;},key:i=>[...storageData.keys()][i]??null,getItem:k=>storageData.get(k)??null,setItem:(k,v)=>storageData.set(k,String(v)),removeItem:k=>storageData.delete(k)};
const tick=()=>new Promise(resolve=>setImmediate(resolve));

async function createSurface(role){
  const dom=new JSDOM(html,{url:`https://bojart.test/?screen=${role}&station=${role}&immersive=1`,runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,context=dom.getInternalVMContext();
  const surface={role,dom,w,modules:new Map(),fail3d:false,viewerCount:0,fetchCalls:[],sentFrames:[],providerStatus:{status:404,body:{}},decide:null};surfaces.push(surface);
  Object.defineProperty(w,'localStorage',{value:storage});
  w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};
  const jsonResponse=(body,status=200)=>({ok:status>=200&&status<300,status,json:async()=>w.JSON.parse(JSON.stringify(body))});
  w.fetch=async(input,options={})=>{
    const pathname=new w.URL(String(input),w.location.href).pathname;
    const call={pathname,method:options.method||'GET',body:options.body?JSON.parse(options.body):null,credentials:options.credentials};
    surface.fetchCalls.push(call);
    if(pathname==='/assets/archive-index.json')return jsonResponse(JSON.parse(fs.readFileSync(path.join(dist,'assets/archive-index.json'),'utf8')));
    if(pathname==='/api/visual-decision/status')return jsonResponse(surface.providerStatus.body,surface.providerStatus.status);
    if(pathname==='/api/visual-decision'&&call.method==='POST')return surface.decide?jsonResponse(await surface.decide(call.body,options)):jsonResponse({ok:false},503);
    return jsonResponse({ok:false},404);
  };
  w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  w.HTMLCanvasElement.prototype.getContext=()=>null;
  w.HTMLMediaElement.prototype.pause=function(){};w.HTMLMediaElement.prototype.play=async function(){};
  w.TextDecoder=TextDecoder;w.TextEncoder=TextEncoder;
  w.addEventListener('error',event=>errors.push(role+': '+(event.error?.message||event.message)));
  w.BroadcastChannel=class {
    constructor(name){this.name=name;this.closed=false;this.listeners=new Set();const peers=channels.get(name)||new Set();peers.add(this);channels.set(name,peers);}
    addEventListener(type,listener){if(type==='message')this.listeners.add(listener);}
    removeEventListener(type,listener){if(type==='message')this.listeners.delete(listener);}
    deliver(serialized){if(this.closed)return;const event={data:w.JSON.parse(serialized)};this.onmessage?.(event);for(const listener of this.listeners)listener(event);}
    postMessage(data){if(this.closed)throw Error('Channel closed');const serialized=JSON.stringify(data);surface.sentFrames.push(JSON.parse(serialized));for(const peer of channels.get(this.name)||[]){if(peer===this||peer.closed)continue;queueMicrotask(()=>peer.deliver(serialized));}}
    close(){this.closed=true;channels.get(this.name)?.delete(this);}
  };
  const stub=new vm.SyntheticModule(['createViewer','inspectSTL'],function(){
    this.setExport('createViewer',async()=>{if(surface.fail3d)throw Error('WebGL unavailable in test');surface.viewerCount++;return{loadSTL:()=>({dims:[20,20,20],triangles:12}),showDemo(){},reset(){},explode:()=>true,setWireframe(){},setAutoRotate(){},setMotion(){},setSection(){},dispose(){}};});
    this.setExport('inspectSTL',()=>({dims:[20,20,20],triangles:12}));
  },{context});
  await stub.link(()=>{});await stub.evaluate();
  function moduleFor(filename){filename=path.resolve(filename);if(surface.modules.has(filename))return surface.modules.get(filename);const mod=new vm.SourceTextModule(fs.readFileSync(filename,'utf8'),{context,identifier:filename,importModuleDynamically:async()=>stub});surface.modules.set(filename,mod);return mod;}
  async function load(filename){const mod=moduleFor(filename);if(mod.status==='unlinked')await mod.link((spec,parent)=>moduleFor(path.resolve(path.dirname(parent.identifier),spec)));return mod;}
  surface.load=load;surface.$=selector=>w.document.querySelector(selector);
  surface.click=async selector=>{const button=surface.$(selector);assert(button,role+' missing '+selector);button.click();await tick();await tick();};
  surface.displayRequests=()=>surface.sentFrames.filter(frame=>frame.protocol==='bojart.display-bus.v1'&&frame.type==='request');
  surface.submitVisual=async(command,provider='local')=>{
    const form=surface.$('#visual-command-form');assert(form,role+' missing visual form');
    const engine=form.querySelector(`input[name="provider"][value="${provider}"]`);assert(engine&&!engine.disabled,role+' unavailable provider '+provider);engine.checked=true;
    form.querySelector('#visual-command-input').value=command;
    form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();
  };
  surface.selectProject=async id=>{const picker=surface.$('#project-picker');assert(picker,role+' missing project picker');picker.value=id;assert.equal(picker.value,id);picker.dispatchEvent(new w.Event('change',{bubbles:true}));await tick();await tick();};
  surface.app=await load(path.join(dist,'app.js'));await surface.app.evaluate();await tick();await tick();return surface;
}

(async()=>{try{
  const {normalizeTypeSafeResponse,DEFAULT_JEV_MODEL}=await import(pathToFileURL(path.join(__dirname,'../local/jev-provider.mjs')).href);
  const providerReply=(request,{choice='model',probabilities={model:.88,art:.04,film:.03,production:.02,none:.03}}={})=>normalizeTypeSafeResponse({model:DEFAULT_JEV_MODEL,answers:{visual:{type:'choice',choice,confidence:.85,probabilities}},usage:{input_tokens:342,output_tokens:22}},request);
  const deferDecision=surface=>{
    let finish,request;
    const pending=new Promise(resolve=>{finish=resolve;});
    surface.decide=input=>{request=input;return pending;};
    return{get request(){return request;},resolve(options){assert(request,'The deferred provider must receive a request before responding.');finish(providerReply(request,options));}};
  };
  const left=await createSurface('atelier');
  const center=await createSurface('pilotage');
  const right=await createSurface('creation');
  await tick();await tick();
  assert.equal(center.w.document.querySelectorAll('.display-constellation .online').length,3);
  checks.push('Three dedicated window roles are discovered and shown at the Jarvis station.');

  await center.app.namespace.executeCommand('Montre le socle sur l’écran droit');await tick();await tick();
  assert.equal(center.$('#main').dataset.screen,'pilotage');assert(center.$('.control-stage'));
  assert(right.$('#model-viewer'));assert.equal(left.$('#main').dataset.screen,'atelier');
  assert(center.$('#command-receipt').textContent.includes('Écran 03'));
  assert(center.$('#command-receipt').textContent.includes('démonstration'));
  assert(right.$('.piece-row.active').textContent.toLowerCase().includes('socle'));
  checks.push('A model command targets the right window, confirms the demo, and leaves Jarvis central.');

  await center.click('[data-screen="creation"]');assert.equal(center.$('#main').dataset.screen,'creation');assert(center.w.location.search.includes('station=pilotage'));await center.app.namespace.executeCommand('Montre le socle à droite');await tick();assert(center.$('#command-receipt').textContent.includes('Écran 03'));assert(right.$('#model-viewer'));await center.click('[data-screen="pilotage"]');checks.push('A station keeps its role through manual navigation; an explicit right-screen request still targets that station.');

  await center.app.namespace.executeCommand('Affiche l’atelier à gauche');await tick();
  assert.equal(center.$('#main').dataset.screen,'pilotage');
  assert(center.$('#command-receipt').textContent.includes('Écran 01'));
  assert(center.$('#command-receipt').textContent.includes('simulés'));
  checks.push('Production view is acknowledged by the left window without changing the central view.');

  await center.app.namespace.executeCommand('Montre le film sur l’écran droit');await tick();
  assert(right.$('#studio-video'));assert(!center.$('#studio-video'));
  assert(center.$('#command-receipt').textContent.includes('lecture manuelle'));
  checks.push('Film view opens only on the right and does not claim automatic playback.');

  await right.click('[data-action="piece"]');
  await center.app.namespace.executeCommand('Montre le modèle sur l’écran droit');await tick();
  assert(right.$('#drawer').open);assert(right.$('#piece-form'));
  assert(center.$('#command-receipt').textContent.includes('panneau'));
  assert.equal(center.$('#main').dataset.screen,'pilotage');
  await right.click('[data-action="close-dialog"]');
  checks.push('An open editor on the receiving screen is preserved; the sender sees a rejection.');

  const busModule=await center.load(path.join(dist,'lib/display-bus.js'));
  const probe=busModule.namespace.createDisplayBus({getRole:()=>null,onChange:()=>{}});
  probe.announce();await tick();await tick();
  const projectId=center.$('#project-picker').value;
  const stale=center.w.JSON.parse(JSON.stringify({kind:'show',view:'art',projectId,projectRevision:9999}));
  const staleResult=await probe.request('creation',stale);
  assert.equal(staleResult.ok,false);assert.equal(staleResult.code,'rejected');assert(staleResult.message.includes('révision'));
  const missing=center.w.JSON.parse(JSON.stringify({kind:'show',view:'model',projectId:'unknown',pieceId:'missing'}));
  const missingResult=await probe.request('creation',missing);
  assert.equal(missingResult.ok,false);assert.equal(center.$('#project-picker').value,projectId);
  probe.dispose();
  checks.push('A stale revision or unknown project is rejected without replacing the active dossier.');

  // New visual desk paths exercise the real UI/router/bus; TypeSafe JSON is an injected fixture.
  const postCount=()=>center.fetchCalls.filter(call=>call.pathname==='/api/visual-decision'&&call.method==='POST').length;
  const receivedLabel=()=>right.$('.visual-transfer-note')?.textContent||'';
  let sent=center.displayRequests().length;
  await center.click('.visual-dock [data-visual-id="film"]');
  assert.equal(center.displayRequests().length,sent+1);assert.equal(center.displayRequests().at(-1).payload.view,'film');
  assert.equal(right.$('#studio-video').getAttribute('src'),'./assets/brand-film-master.mp4');assert(right.$('.studio-film').textContent.includes('22,7 S'));
  assert(!right.$('#studio-video').hasAttribute('autoplay'));assert(right.$('#film-play'));
  assert.equal(center.$('#main').dataset.screen,'pilotage');assert(center.$('.control-stage'));assert(!center.$('#studio-video'));
  assert(center.$('#wall-command-receipt').textContent.includes('Écran 03'));assert(receivedLabel().includes('Le film d’atelier'));assert.equal(right.$('.visual-transfer-note').getAttribute('role'),'status');assert.equal(right.$('.visual-transfer-note>b').textContent,'03');
  checks.push('The central visual dock sends the new 22.7-second BOJ.ART signature edit to screen 03, with receipt and arrival note; central Jarvis stays in place.');

  await center.click('[data-action="visual-desk"]');
  assert(center.$('[data-visual-desk]'));assert.equal(center.$('[data-visual-desk]').dataset.project,projectId);
  await center.submitVisual('Montre le volume du socle');
  assert(right.$('#model-viewer'));assert(!center.$('#drawer').open);assert.equal(center.$('#main').dataset.screen,'pilotage');
  assert(center.displayRequests().at(-1).payload.pieceId.endsWith('socle'));
  await center.click('[data-action="visual-desk"]');
  sent=center.displayRequests().length;
  await center.submitVisual('Montre le modèle et les œuvres');
  assert(center.$('#drawer').open);assert(center.$('[data-visual-status]').textContent.includes('Plusieurs vues'));assert(right.$('#model-viewer'));
  assert.equal(center.displayRequests().length,sent);assert.equal(postCount(),0);
  checks.push('The local visual form selects the requested model; conflicting model/art requests preserve the current view and send no provider or display request.');

  assert(center.$('#visual-command-form input[value="typesafe"]').disabled);
  assert(center.$('[data-visual-provider-state]').textContent.includes('à raccorder'));
  assert(center.fetchCalls.some(call=>call.pathname==='/api/visual-decision/status'));
  await center.app.namespace.executeCommand('Jev, montre le modèle');await tick();
  assert.equal(postCount(),0);assert(center.$('#visual-command-form input[value="typesafe"]').disabled);
  center.providerStatus={status:200,body:{ok:true,configured:false,connected:false,model:DEFAULT_JEV_MODEL}};
  await center.click('[data-action="visual-provider-refresh"]');
  assert(center.$('#visual-command-form input[value="typesafe"]').disabled);
  center.providerStatus={status:200,body:{ok:true,configured:true,connected:false,model:DEFAULT_JEV_MODEL}};
  await center.click('[data-action="visual-provider-refresh"]');
  assert(!center.$('#visual-command-form input[value="typesafe"]').disabled);assert(center.$('[data-visual-provider-state]').textContent.includes('premier appel à tester'));
  assert.equal(postCount(),0);
  checks.push('A missing status endpoint and an unconfigured gateway keep Jev disabled; a configured gateway enables it without inventing a successful call.');

  center.decide=request=>providerReply(request);
  sent=center.displayRequests().length;
  await center.submitVisual('Montre la pièce en volume','typesafe');
  assert.equal(postCount(),1);assert.equal(center.displayRequests().length,sent+1);
  const actualRequest=center.fetchCalls.filter(call=>call.pathname==='/api/visual-decision').at(-1);
  assert.equal(actualRequest.credentials,'same-origin');assert.equal(actualRequest.body.context.projectId,projectId);assert(actualRequest.body.context.pieceId);assert(actualRequest.body.requestId);
  assert.equal(center.displayRequests().at(-1).payload.view,'model');assert(right.$('#model-viewer'));assert.equal(center.$('#main').dataset.screen,'pilotage');
  assert(center.$('#wall-command-receipt').textContent.includes(`Jev (${DEFAULT_JEV_MODEL})`));assert(center.$('#wall-command-receipt').textContent.includes('Écran 03'));
  await center.click('[data-action="visual-desk"]');assert(center.$('[data-visual-provider-state]').textContent.includes('Jev a répondu'));
  checks.push('An injected TypeSafe answer passes through the real server normalizer and browser validator before one model request reaches the right screen.');

  sent=center.displayRequests().length;
  center.decide=request=>providerReply(request,{probabilities:{model:.6,art:.2,film:.1,production:.05,none:.05}});
  await center.submitVisual('Je veux un aperçu de ce projet','typesafe');
  assert(center.$('[data-visual-status]').textContent.includes('Jev conserve'));assert(center.$('#drawer').open);assert(right.$('#model-viewer'));
  assert.equal(center.displayRequests().length,sent);
  center.decide=request=>providerReply(request,{choice:'none',probabilities:{model:.05,art:.02,film:.01,production:.02,none:.9}});
  await center.submitVisual('Conserve la vue actuelle','typesafe');
  assert(center.$('[data-visual-status]').textContent.includes('Jev conserve'));assert.equal(center.displayRequests().length,sent);assert(right.$('#model-viewer'));
  assert.equal(postCount(),3);
  await center.click('[data-action="close-dialog"]');
  checks.push('Uncertain and explicit none provider decisions keep the current scene and emit no cross-screen request.');

  await center.click('.visual-dock [data-visual-id="film"]');
  await center.click('[data-action="visual-desk"]');
  const oldDossier=deferDecision(center);
  await center.submitVisual('Montre la pièce en volume','typesafe');
  assert.equal(oldDossier.request.context.projectId,projectId);assert(center.$('#visual-command-form button[type="submit"]').disabled);
  const nextProject=[...center.$('#project-picker').options].find(option=>option.value!==projectId).value;
  // A different physical screen can change the dossier while Jarvis awaits the provider.
  await left.selectProject(nextProject);
  assert.equal(center.$('#project-picker').value,nextProject);assert.equal(right.$('#project-picker').value,nextProject);sent=center.displayRequests().length;
  oldDossier.resolve();await tick();await tick();
  assert.equal(center.$('#project-picker').value,nextProject);assert.equal(right.$('#project-picker').value,nextProject);
  assert.equal(center.displayRequests().length,sent);assert(right.$('#studio-video'));assert(!right.$('#model-viewer'));
  assert(center.$('#wall-command-receipt').textContent.includes('dossier ou sa pièce a changé'));
  await center.selectProject(projectId);
  checks.push('A delayed Jev response for the previous dossier is refused after project synchronization, without replacing the new dossier or sending a visual command.');

  await center.click('[data-action="visual-desk"]');
  const otherPanel=deferDecision(center);
  await center.submitVisual('Montre la pièce en volume','typesafe');assert(otherPanel.request);
  await center.click('[data-action="close-dialog"]');
  await center.click('[data-pilot-tab="dossiers"]');await center.click('[data-action="project-edit"]');
  const editingForm=center.$('#project-form');assert(editingForm);
  editingForm.querySelector('[name="notes"]').value='Brouillon à conserver pendant le retour Jev.';
  sent=center.displayRequests().length;otherPanel.resolve();await tick();await tick();
  assert(center.$('#drawer').open);assert.equal(center.$('#project-form'),editingForm);assert.equal(editingForm.querySelector('[name="notes"]').value,'Brouillon à conserver pendant le retour Jev.');
  assert.equal(center.displayRequests().length,sent);assert(right.$('#studio-video'));assert(!right.$('#model-viewer'));
  assert(center.$('#wall-command-receipt').textContent.includes('autre panneau est ouvert'));
  await center.click('[data-action="close-dialog"]');await center.click('[data-pilot-tab="controle"]');
  checks.push('A delayed Jev result preserves a different open editor, including its unsaved text, and does not change another screen.');

  await center.click('[data-action="visual-desk"]');await center.click('[data-action="signature"]');
  assert(center.$('#drawer').classList.contains('signature-drawer'));
  const sources=[...center.w.document.querySelectorAll('.signature-sequence-card>a')].map(anchor=>anchor.getAttribute('href').split('/').at(-1));
  assert.deepEqual(sources,['7467517355535404310','7331788287171988768','7376602431603346721','7464268707989114134']);
  assert.equal(center.$('.signature-film').getAttribute('src'),'./assets/atelier-motion.mp4');assert(center.$('.signature-film').controls);assert(!center.$('.signature-film').autoplay);
  const timings=JSON.parse(fs.readFileSync(path.join(dist,'assets/atelier-motion-sources.json'),'utf8'));
  assert.deepEqual([...center.w.document.querySelectorAll('.signature-sequence-output')].map(node=>Number(node.textContent.replace('00:','').replace(',','.'))),timings.sources.map(source=>(source.output_interval_seconds||source.main_output_interval_seconds)[0]));
  sent=center.displayRequests().length;await center.click('.signature-present[data-visual-id="film"]');
  assert.equal(center.displayRequests().length,sent+1);assert(!center.$('#drawer').open);assert(right.$('#studio-video'));assert.equal(center.$('#main').dataset.screen,'pilotage');
  checks.push('The identity drawer presents four verifiable source sequences, manual film controls, source-derived timings, and a working screen-03 presentation action.');

  right.fail3d=true;
  await center.app.namespace.executeCommand('Montre le socle à droite');await tick();
  assert(right.$('.viewer-error'));assert(center.$('#command-receipt').textContent.includes('n’a pas pu afficher'));
  assert(!center.$('#model-viewer'));assert.equal(center.$('#main').dataset.screen,'pilotage');
  checks.push('A renderer failure is returned to Jarvis; no successful model display or local retry is invented.');

  right.w.dispatchEvent(new right.w.Event('pagehide'));await tick();await tick();
  await center.app.namespace.executeCommand('Montre le modèle à droite');await tick();
  assert(center.$('#drawer').open);assert(center.$('#command-receipt').textContent.includes('à ouvrir'));
  assert.equal(center.$('#main').dataset.screen,'pilotage');assert(!center.$('#model-viewer'));
  checks.push('An absent right window opens screen setup, preserving Jarvis and avoiding a silent local fallback.');

  assert.equal(errors.length,0,errors.join('\n'));
  const result={status:'passed',checks,browserRenderingVerified:false,webglRenderingVerified:false,liveJevVerified:false,scope:'Three isolated JSDOM windows, real application/store/display controller and TypeSafe response normalizer, shared storage and BroadcastChannel double. Renderer stub and injected provider HTTP responses only; no browser, socket or live Jev request.'};
  fs.writeFileSync(path.join(__dirname,'multiscreen-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{for(const surface of surfaces){try{surface.w.dispatchEvent(new surface.w.Event('pagehide'));surface.dom.window.close();}catch{}}for(const peers of channels.values())for(const peer of peers)peer.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
