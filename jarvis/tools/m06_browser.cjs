/* Real Chromium integration. Synthetic microphone and deterministic ASR fixture;
   this verifies wiring, cancellation and display, not speech recognition quality. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 const browser=await chromium.launch({headless:true,executablePath:process.env.BOJ_TEST_CHROMIUM,
  args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-audio-capture='+input.wav]});
 const context=await browser.newContext({viewport:{width:1440,height:1000},permissions:['microphone']});
 const errors=[],checks=[],timings=[],loadTimings=[];context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
 const page=await context.newPage();page.setDefaultTimeout(20000);
 async function get(url){const r=await context.request.get(input.origin+url);assert.equal(r.status(),200);return r.json();}
 async function post(url,data){const r=await context.request.post(input.origin+url,{data,headers:{Origin:input.origin}});assert.equal(r.status(),200);return r.json();}
 async function check(name,fn){await fn();checks.push(name);}
 async function until(fn,ms=15000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await page.waitForTimeout(40);}throw Error('Timed out awaiting verified receipt');}
 const make=(id,text)=>({request_id:id,client_id:'browser_acceptance',project_id:'BOJ-PILOTE-001',revision:0,text,operation_id:null,source:'typed'});
 try{
  await page.goto(input.origin+'/?session='+encodeURIComponent(input.token));await page.goto(input.origin+'/tower');
  await page.waitForFunction(()=>document.querySelectorAll('#roles button').length===3);
  const views={};for(const [i,role]of ['atelier','pilotage','creation'].entries()){
   const popup=page.waitForEvent('popup');await page.locator('#roles button').nth(i).click();views[role]=await popup;
   await views[role].waitForFunction(()=>document.querySelector('#connection').textContent==='VUE LOCALE CONNECTÉE');
  }
  await check('Free text UI -> LangGraph -> pushed browser view -> rendered ACK',async()=>{
   await page.locator('#voiceText').fill('Montre les dossiers au centre');await page.locator('#voiceSend').click();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent.startsWith('AFFICHÉ'));
   await views.pilotage.getByRole('heading',{name:'Dossiers et continuité'}).waitFor();
  });
  for(const [id,text,role,heading]of [
   ['studio','Ouvre le studio','creation','Studio sources BOJ.ART'],
   ['growth','Ouvre les contenus à droite','creation','Contenus BOJ.ART'],
   ['knowledge','Ouvre la base métier au centre','pilotage','Base métier'],
   ['cad','Ouvre la conception au centre','pilotage','Conception du dossier']]){
   await check('Connected visual module: '+id,async()=>{
    const req=make('visual_'+id,text);await post('/api/jarvis/turn',req);
    await until(async()=>((await get('/api/jarvis/turn?request_id='+req.request_id)).display?.state==='rendered'));
    await views[role].getByRole('heading',{name:heading,exact:true}).waitFor();
   });
  }
  await check('Local latency sample: twelve complete text-to-view receipts',async()=>{
   for(let i=0;i<12;i++){
    const req=make('latency_'+i,'Montre les dossiers au centre');await post('/api/jarvis/turn',req);let receipt;
    await until(async()=>{receipt=await get('/api/jarvis/turn?request_id='+req.request_id);return receipt.display?.state==='rendered';});
    timings.push(receipt.elapsed_to_display_ms);
   }
  });
  await check('Display orders and receipts continue during an actual CAD calculation',async()=>{
   await post('/api/projects/create',{project_id:'BOJ-LOAD-06',name:'Charge CAO M06'});
   const proposal=await post('/api/propose',{project_id:'BOJ-LOAD-06',command:'Jarvis, crée un socle de dix-huit centimètres et affiche-le à droite.',revision:0,source:'typed'});
   let finished=false;const cad=post('/api/confirm',{proposal_id:proposal.proposal_id,approved:true}).finally(()=>{finished=true;});
   for(let i=0;i<6;i++){
    const startedWhileCadPending=!finished,req=make('load_'+i,'Montre les dossiers au centre');await post('/api/jarvis/turn',req);let receipt;
    await until(async()=>{receipt=await get('/api/jarvis/turn?request_id='+req.request_id);return receipt.display?.state==='rendered';});
    loadTimings.push({ms:receipt.elapsed_to_display_ms,started_while_cad_pending:startedWhileCadPending,rendered_before_cad_response:!finished});
   }
   const model=await cad;assert.equal(model.state,'READY');assert.ok(loadTimings.some(x=>x.rendered_before_cad_response));
  });
  await check('Lost HTTP response + reload reuses one immutable turn',async()=>{
   await page.locator('#voiceText').fill('Ouvre les contenus à droite');
   await page.route('**/api/jarvis/turn',async route=>{if(route.request().method()==='POST'){await route.fetch();await route.abort('failed');}else await route.continue();});
   await page.locator('#voiceSend').click();await page.waitForFunction(()=>document.querySelector('#voiceSend').textContent.includes('Reprendre'));
   const req=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('boj_m06_turn_BOJ-PILOTE-001')));
   await page.unroute('**/api/jarvis/turn');await page.reload();await page.locator('#voiceSend').click();
   await until(async()=>((await get('/api/jarvis/turn?request_id='+req.request_id)).display?.state==='rendered'));
   assert.equal((await get('/api/tower/state')).commands.filter(c=>c.request_id===req.request_id).length,1);
  });
  await check('Synthetic microphone -> WAV -> ASR fixture -> same graph and actual display',async()=>{
   await page.waitForFunction(()=>!document.querySelector('#voiceRecord').disabled);await page.locator('#voiceRecord').click();
   await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='MICROPHONE ACTIF');await page.waitForTimeout(700);
   await page.locator('#voiceRecord').click();await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent.startsWith('AFFICHÉ'));
   assert.equal(await page.locator('#voiceText').inputValue(),'Montre les dossiers au centre');
  });
  await check('Second browser cannot take the microphone lease',async()=>{
   const second=await context.newPage();await second.goto(input.origin+'/tower');await second.waitForFunction(()=>!document.querySelector('#voiceRecord').disabled);
   await page.locator('#voiceRecord').click();await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='MICROPHONE ACTIF');
   await second.locator('#voiceRecord').click();await second.waitForFunction(()=>document.querySelector('#voiceFeedback').textContent.includes('autre fenêtre'));
   await page.locator('#voiceCancel').click();await second.close();
  });
  await check('Cancel during transcription drops the late ASR result',async()=>{
   const before=(await get('/api/tower/state')).commands.map(c=>c.request_id);
   await page.locator('#voiceRecord').click();await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='MICROPHONE ACTIF');await page.waitForTimeout(400);
   await page.locator('#voiceRecord').click();await page.waitForFunction(()=>document.querySelector('#voicePhase').textContent==='TRANSCRIPTION');
   await page.locator('#voiceCancel').click();await page.waitForTimeout(1000);
   assert.deepEqual((await get('/api/tower/state')).commands.map(c=>c.request_id),before);
  });
  await check('Polling fallback survives an unavailable event stream',async()=>{
   await views.pilotage.route('**/api/tower/events',r=>r.abort('failed'));await views.pilotage.reload();
   await views.pilotage.waitForFunction(()=>document.querySelector('#connection').textContent==='VUE LOCALE CONNECTÉE');
   const req=make('fallback','Montre les dossiers au centre');await post('/api/jarvis/turn',req);
   await until(async()=>((await get('/api/jarvis/turn?request_id=fallback')).display?.state==='rendered'),9000);
  });
  await page.screenshot({path:path.join(input.output,'M06_DESKTOP.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(input.output,'M06_MOBILE.png'),fullPage:true});
  await check('Mobile layout stays within the viewport',async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true));
  assert.deepEqual(errors,[]);
  timings.sort((a,b)=>a-b);
  process.stdout.write(JSON.stringify({status:'PASS',checks,browser:await browser.version(),
   latency_ms:{samples:timings,p50:timings[Math.floor(timings.length*.5)],p95:timings[Math.ceil(timings.length*.95)-1],max:timings.at(-1),scope:'final text submitted -> actual browser rendered ACK; one local Linux session; excludes ASR/Jev'},
   load_latency_ms:loadTimings,real_asr:false,real_microphone:false,real_jev:false,physical_screens:false,browser_errors:errors}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exit(1)});
