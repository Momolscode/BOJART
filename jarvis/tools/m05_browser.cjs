/* Real browser acceptance test; only a localhost app and fresh browser context. */
const fs=require('fs');
const path=require('path');
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 const browser=await chromium.launch({headless:true,...(process.env.BOJ_TEST_CHROMIUM?{executablePath:process.env.BOJ_TEST_CHROMIUM}:{}),args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const errors=[];context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
 const page=await context.newPage();page.setDefaultTimeout(20000);
 const checks=[];
 async function checked(name,fn){await fn();checks.push(name);}
 async function read(url){const r=await context.request.get(input.origin+url);assert.equal(r.status(),200);return r.json();}
 let project,models,backup,plan,packet;
 try{
  await checked('Launcher opens the workspace after private-session bootstrap',async()=>{
   await page.goto(input.origin+'/?session='+encodeURIComponent(input.token));await page.waitForURL('**/workspace');
   await page.waitForFunction(()=>document.querySelector('#projectCount').textContent==='1');
  });
  await checked('Create a named project using the workspace form',async()=>{
   await page.locator('#projectName').fill('Socle — recette M05');await page.locator('#create').click();
   await page.waitForFunction(()=>document.querySelector('#projectCount').textContent==='2');
   const s=await read('/api/workspace/state');project=s.projects.find(p=>p.name==='Socle — recette M05');assert.ok(project);
  });
  await page.locator('.projectCard').filter({hasText:'Socle — recette M05'}).getByRole('link',{name:'Ouvrir le dossier'}).click();
  for(const [sample,diameter,revision] of [['sample18',180,1],['sample24',240,2]]){
   await checked('Create and render actual CAD '+diameter+' mm in project revision '+revision,async()=>{
    await page.locator('#'+sample).click();await page.locator('#prepare').click();
    await page.waitForFunction(()=>!document.querySelector('#confirm').disabled);
    await page.locator('#confirm').click();
    await page.waitForFunction(({diameter,revision})=>document.querySelector('#modelTitle').textContent.includes('Ø '+diameter+' mm')&&document.querySelector('#modelRev').textContent==='R'+revision,{diameter,revision},{timeout:120000});
    await page.waitForFunction(()=>Number(document.querySelector('#canvas').dataset.renderedTriangles)>0);
    await page.waitForFunction(()=>!document.querySelector('#prepare').disabled);
   });
  }
  models=(await read('/api/state?project_id='+project.id)).jobs;
  await page.screenshot({path:path.join(input.output,'CAO_M05.png'),fullPage:true});
  await page.goto(input.origin+'/studio');
  await checked('Studio creates and revalidates a brief from authentic source segments',async()=>{
   await page.waitForFunction(()=>document.querySelector('#segmentCount').textContent==='8');
   const response=page.waitForResponse(r=>r.url().endsWith('/api/studio/prepare')&&r.request().method()==='POST');
   await page.locator('#prepare').click();plan=await (await response).json();assert.equal(plan.status,'PREPARED_NOT_RENDERED');
   await page.locator('#verify').click();await page.waitForFunction(()=>document.querySelector('#feedback').textContent.includes('Références cohérentes'));
  });
  await page.goto(input.origin+'/growth');
  await checked('Growth creates a source-linked draft and validates it without publishing',async()=>{
   await page.waitForFunction(()=>document.querySelector('#feedback').textContent.startsWith('Catalogue lu'));
   await page.locator('#account').selectOption('tiktok_main');await page.locator('#topic').selectOption('sculpture');
   const response=page.waitForResponse(r=>r.url().endsWith('/api/growth/prepare')&&r.request().method()==='POST');
   await page.locator('#prepare').click();packet=await (await response).json();assert.equal(packet.delivery.published,false);
   await page.locator('#check').click();await page.waitForFunction(()=>document.querySelector('#feedback').textContent.startsWith('Sources et règles cohérentes'));
  });
  await page.goto(input.origin+'/tower?project_id='+project.id);
  await page.waitForFunction(()=>document.querySelectorAll('#roles button').length===3);
  const screens={};
  for(const [index,role]of ['atelier','pilotage','creation'].entries()){
   const popup=page.waitForEvent('popup');await page.locator('#roles button').nth(index).click();screens[role]=await popup;
   await screens[role].waitForFunction(()=>document.querySelector('#connection').textContent==='VUE LOCALE CONNECTÉE');
  }
  for(const [command,role]of [['Montre les sources au centre','pilotage'],['Affiche le planning à gauche','atelier'],['Affiche le modèle à droite','creation']]){
   await checked('Actual browser view '+role+' renders and acknowledges its command',async()=>{
    await page.locator('#command').selectOption(command);
    if(role==='creation')await page.locator('#operation').selectOption(models[0].id);
    await page.locator('#send').click();
    await screens[role].waitForFunction(()=>document.querySelector('#receipt').textContent.startsWith('rendered'));
    if(role==='creation')await screens[role].waitForFunction(()=>Number(document.querySelector('#canvas').dataset.renderedTriangles)>0);
   });
  }
  await screens.creation.screenshot({path:path.join(input.output,'VUE_3D_M05.png'),fullPage:true});
  await checked('Lost dispatch response survives reload and retries the same request without duplicate',async()=>{
   const before=(await read('/api/tower/state?project_id='+project.id)).commands.length;
   await page.locator('#command').selectOption('Montre les sources au centre');
   await page.route('**/api/tower/dispatch',async route=>{await route.fetch();await route.abort('failed');});
   await page.locator('#send').click();await page.waitForFunction(()=>document.querySelector('#send').textContent.includes('Reprendre'));
   await page.unroute('**/api/tower/dispatch');await page.reload();
   await page.waitForFunction(()=>document.querySelector('#send').textContent.includes('Reprendre'));
   await page.locator('#send').click();await page.waitForFunction(()=>!sessionStorage.getItem('boj_m05_display_'+new URLSearchParams(location.search).get('project_id')));
   assert.equal((await read('/api/tower/state?project_id='+project.id)).commands.length,before+1);
  });
  await page.goto(input.origin+'/workspace');
  await checked('Workspace verifies both CAD revisions, all databases and all three media files',async()=>{
   await page.locator('#check').click();await page.waitForFunction(()=>document.querySelector('#integrity').textContent.includes('5 bases, 2 modèles et 3 médias vérifiés.'));
  });
  await checked('Global snapshot is created, verified and available for authenticated download',async()=>{
   const response=page.waitForResponse(r=>r.url().endsWith('/api/workspace/backup')&&r.request().method()==='POST');
   await page.locator('#backup').click();backup=await (await response).json();assert.equal(backup.ok,true);
   await page.waitForFunction(()=>document.querySelector('#backupResult a'));
   const download=await context.request.get(input.origin+backup.url);assert.equal(download.status(),200);
   assert.equal(require('crypto').createHash('sha256').update(await download.body()).digest('hex'),backup.sha256);
  });
  await page.screenshot({path:path.join(input.output,'DOSSIERS_M05.png'),fullPage:true});
  const mobile=await context.newPage();await mobile.setViewportSize({width:390,height:844});await mobile.goto(input.origin+'/workspace');
  await checked('Narrow workspace has no horizontal overflow and keeps project actions visible',async()=>{
   await mobile.waitForFunction(()=>document.querySelector('#projectCount').textContent==='2');
   assert.equal(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await mobile.locator('.projectCard').first().getByRole('link',{name:'Ouvrir le dossier'}).isVisible();
  });
  await mobile.screenshot({path:path.join(input.output,'DOSSIERS_M05_MOBILE.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  process.stdout.write(JSON.stringify({status:'PASS',browser:await browser.version(),checks,project:project.id,operation_ids:models.map(m=>m.id),studio_brief:plan.id,growth_packet:packet.id,backup,roles:['atelier','pilotage','creation'],browser_errors:errors,physical_qualification:false}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exit(1)});
