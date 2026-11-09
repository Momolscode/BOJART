/* Actual browser capture and rendering. ASR and Jev are server fixtures. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 const browser=await chromium.launch({headless:true,executablePath:process.env.BOJ_TEST_CHROMIUM,args:[
  '--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader',
  '--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-audio-capture='+input.wav]});
 const context=await browser.newContext({viewport:{width:1440,height:1000},permissions:['microphone']});
 const checks=[],errors=[];context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
 await context.addInitScript(()=>{window.__captureTracks=[];if(!navigator.mediaDevices?.getUserMedia)return;const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=async constraints=>{const s=await original(constraints);window.__captureTracks.push(...s.getTracks());return s;};});
 const page=await context.newPage();page.setDefaultTimeout(25000);
 const get=async url=>{const r=await context.request.get(input.origin+url);assert.equal(r.status(),200);return r.json();};
 const post=async(url,data)=>{const r=await context.request.post(input.origin+url,{data,headers:{Origin:input.origin},timeout:120000});assert.equal(r.status(),200);return r.json();};
 const check=async(name,fn)=>{await fn();checks.push(name);};
 const pending=()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('boj_m06_turn_BOJ-PILOTE-001')));
 const turn=async()=>get('/api/jarvis/turn?request_id='+(await pending()).request_id);
 const ids=async()=>(await get('/api/tower/state')).commands.map(c=>c.request_id);
 async function record(){await page.bringToFront();await page.waitForFunction(()=>!document.querySelector('#voiceRecord').disabled);await page.locator('#voiceRecord').click();await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='MICROPHONE ACTIF');}
 try{
  await page.goto(input.origin+'/?session='+encodeURIComponent(input.token));await page.goto(input.origin+'/tower');
  await page.waitForFunction(()=>document.querySelectorAll('#roles button').length===3);
  const views={};for(const [i,role]of ['atelier','pilotage','creation'].entries()){
   const popup=page.waitForEvent('popup');await page.locator('#roles button').nth(i).click();views[role]=await popup;
   await views[role].waitForFunction(()=>document.querySelector('#connection').textContent==='VUE LOCALE CONNECTÉE');
  }
  await check('One captured utterance ends on a pause and renders all three actual views',async()=>{
   await record();await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent.startsWith('AFFICHÉ'));
   const r=await turn();assert.equal(r.decision.choice,'tower');assert.equal(r.displays.length,3);assert.equal(r.display.rendered_views,3);
   assert.equal(r.display.state,'rendered');assert.ok((await pending()).context_sha256);
   await views.pilotage.getByRole('heading',{name:'Dossiers et continuité'}).waitFor();
   await views.creation.getByRole('heading',{name:'Studio sources BOJ.ART'}).waitFor();
   await views.atelier.getByText('TABLEAU ATELIER',{exact:false}).waitFor();
  });
  await check('Jev proposal is confirmed by a scoped captured voice phrase',async()=>{
   await page.locator('#voiceText').fill('Le tableau des dossiers, merci');await page.locator('#voiceSend').click();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='PROPOSITION JEV');
   const original=(await pending()).request_id;await record();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent.startsWith('AFFICHÉ'));
   assert.equal((await pending()).request_id,original);assert.equal((await turn()).approval_source,'voice_explicit');
  });
  await check('A spoken cancellation leaves the proposed action undistributed',async()=>{
   await page.locator('#voiceText').fill('Mon tableau des dossiers, merci');await page.locator('#voiceSend').click();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='PROPOSITION JEV');
   await record();await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='ANNULÉ');
   const r=await turn();assert.equal(r.status,'CANCELLED');assert.equal(r.display,null);
  });
  await check('Context captured before listening prevents a stale ASR result from acting',async()=>{
   const before=await ids();await record();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='CONTEXTE MODIFIÉ');
   assert.equal((await turn()).status,'STALE');assert.deepEqual(await ids(),before);
  });
  await check('Cancelling ASR then starting again keeps the new microphone alive',async()=>{
   await page.locator('#voiceAutoEnd').uncheck();await record();await page.waitForTimeout(450);await page.locator('#voiceRecord').click();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='TRANSCRIPTION');
   await page.locator('#voiceCancel').click();await page.waitForFunction(()=>!document.querySelector('#voiceRecord').disabled);
   await record();await page.waitForTimeout(1100);
   assert.equal(await page.locator('#voicePhase').textContent(),'MICROPHONE ACTIF');
   assert.equal(await page.evaluate(()=>window.__captureTracks.at(-1).readyState),'live');
   await page.locator('#voiceCancel').click();await page.locator('#voiceAutoEnd').check();
  });
  await check('Lost scene response and reload do not duplicate the three child commands',async()=>{
   await page.locator('#voiceText').fill('Ouvre la tour de contrôle');
   await page.route('**/api/jarvis/turn',async route=>{if(route.request().method()==='POST'){await route.fetch();await route.abort('failed');}else await route.continue();});
   await page.locator('#voiceSend').click();await page.waitForFunction(()=>document.querySelector('#voiceSend').textContent.includes('Reprendre'));
   const request=await pending();const first=await get('/api/jarvis/turn?request_id='+request.request_id);
   await page.unroute('**/api/jarvis/turn');await page.reload();await page.locator('#voiceSend').click();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent.startsWith('AFFICHÉ'));
   assert.deepEqual((await turn()).displays.map(d=>d.request_id),first.displays.map(d=>d.request_id));
  });
  await check('A second window cannot take an active microphone reservation',async()=>{
   await page.locator('#voiceAutoEnd').uncheck();
   const other=await context.newPage();await other.goto(input.origin+'/tower');await other.waitForFunction(()=>!document.querySelector('#voiceRecord').disabled);
   await record();await other.locator('#voiceRecord').click();await other.waitForFunction(()=>document.querySelector('#voiceFeedback').textContent.includes('autre fenêtre'));
   await page.locator('#voiceCancel').click();await other.close();
  });
  await check('The three-view scene renders an explicitly selected actual CAD model',async()=>{
   const state=await get('/api/state');
   const proposal=await post('/api/propose',{project_id:'BOJ-PILOTE-001',revision:state.revision,source:'typed',command:'Crée un socle de 18 cm de diamètre'});
   const model=await post('/api/confirm',{proposal_id:proposal.proposal_id,approved:true});assert.equal(model.state,'READY');
   await page.waitForFunction(id=>[...document.querySelector('#operation').options].some(o=>o.value===id),model.operation_id);
   await page.locator('#operation').selectOption(model.operation_id);await page.locator('#voiceText').fill('Ouvre la tour de contrôle');await page.locator('#voiceSend').click();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent.startsWith('AFFICHÉ'));
   await views.creation.waitForFunction(()=>Number(document.querySelector('#canvas').dataset.renderedTriangles)>0);
   const receipt=await turn();assert.equal(receipt.display.rendered_views,3);assert.equal(receipt.decision.choice,'tower');
  });
  await check('Mobile control panel remains within the viewport',async()=>{
   await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  });
  await page.screenshot({path:path.join(input.output,'M07_QA.png'),fullPage:true});
  assert.deepEqual(errors,[]);process.stdout.write(JSON.stringify({status:'PASS',checks,browser:await browser.version(),browser_errors:errors}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exit(1)});
