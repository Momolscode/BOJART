/* Real local UI, download and stale-response checks. No live model or device. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {chromium}=require('playwright');
(async()=>{
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 assert.match(input.origin,/^http:\/\/127\.0\.0\.1:\d+$/);
 const browser=await chromium.launch({headless:true,executablePath:process.env.BOJ_TEST_CHROMIUM||undefined,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage(),checks=[],errors=[];page.setDefaultTimeout(15000);
 page.on('pageerror',e=>errors.push(e.message));
 async function check(name,fn){await fn();checks.push(name)}
 try{
  await page.goto(input.origin+'/?session='+encodeURIComponent(input.token));await page.goto(input.origin+'/memory');
  await page.waitForFunction(()=>document.getElementById('docs').textContent!=='—');
  await check('Search renders source text without executing embedded HTML',async()=>{
   await page.locator('#question').fill('preuveCitationXYZ');await page.locator('#search').click();
   await page.getByText('1 passages retrouvés',{exact:true}).waitFor();
   assert.equal(await page.locator('#results img').count(),0);
   assert.equal(await page.evaluate(()=>window.__should_not_run),undefined);
   assert.ok((await page.locator('#results').textContent()).includes('<img'));
  });
  await check('Context download preserves citations, project and exact text SHA-256',async()=>{
   await page.locator('#domain').selectOption('bojart.creative');await page.locator('#question').fill('G2');
   await page.waitForFunction(()=>document.getElementById('fact-list').textContent.includes('last_cut.version')&&!document.getElementById('fact-list').textContent.includes('repository.destination'));
   await page.locator('#context').click();await page.getByRole('button',{name:'Télécharger la reprise'}).waitFor();
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Télécharger la reprise'}).click();
   const file=await download,pack=JSON.parse(fs.readFileSync(await file.path(),'utf8'));
   assert.equal(pack.schema,'bojart.agent-context.v2');assert.equal(pack.project,'bojart.creative');
   assert.ok(pack.evidence.length);assert.ok(pack.evidence.every(e=>e.source_bytes_verified&&e.project===pack.project));
   assert.ok(Array.from(pack.text).length<=pack.max_characters);
   assert.equal(crypto.createHash('sha256').update(pack.text).digest('hex'),pack.sha256);
   assert.match(file.suggestedFilename(),/^BOJART_REPRISE_bojart_creative_/);
   if(input.screenshots){fs.mkdirSync(input.screenshots,{recursive:true});await page.screenshot({path:path.join(input.screenshots,'memory-desktop.png'),fullPage:true})}
  });
  await check('Late search response cannot replace results after domain selection changes',async()=>{
   let release,entered;const gate=new Promise(r=>release=r),seen=new Promise(r=>entered=r);
   await page.route('**/api/memory/recall**',async route=>{entered();await gate;await route.continue()});
   await page.locator('#search').click();await seen;
   await page.locator('#domain').selectOption('bojart.jarvis');
   const finished=page.waitForEvent('requestfinished',r=>r.url().includes('/api/memory/recall'));
   release();await finished;await page.unroute('**/api/memory/recall**');
   await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   assert.equal(await page.locator('#results').textContent(),'');
   assert.ok((await page.locator('#notice').textContent()).includes('Contexte modifié'));
  });
  await check('Unconfigured conversation stays disabled without inventing a response',async()=>{
   await page.locator('#ask').click();await page.waitForFunction(()=>document.getElementById('notice').textContent.includes('Conversation désactivée'));
   assert.equal(await page.locator('#results .answer').count(),0);
  });
  await check('Mobile results and controls remain within the viewport',async()=>{
   await page.setViewportSize({width:390,height:844});
   await page.locator('#question').fill('Jev');await page.locator('#context').click();
   await page.getByRole('button',{name:'Télécharger la reprise'}).waitFor();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   if(input.screenshots)await page.screenshot({path:path.join(input.screenshots,'memory-mobile.png'),fullPage:true});
  });
  assert.deepEqual(errors,[]);
  process.stdout.write(JSON.stringify({checks,browser:browser.version(),javascript_errors:errors}));
 }finally{await browser.close()}
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1});
