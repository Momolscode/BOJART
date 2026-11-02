'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const app=path.resolve(__dirname,'../apps/jarvis/app');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject};};
async function until(check){for(let i=0;i<30;i++){if(check())return;await tick();}throw Error('Fixture did not reach expected stage');}

async function studio(segments){
 const nodes=new Map(),posts=[],all=[];
 const element=(tag='div')=>({tagName:tag.toUpperCase(),textContent:'',value:'',checked:false,children:[],hidden:false,disabled:false,dataset:{},style:{},classList:{add(){},remove(){}},append(...items){this.children.push(...items)},replaceChildren(...items){this.children=items},pause(){},play(){return Promise.resolve()},load(){},getAttribute(name){return this[name]??null},removeAttribute(name){delete this[name]}});
 // Reflect the production HTML's initial disabled controls, including play.
 const html=fs.readFileSync(path.join(app,'studio.html'),'utf8');
 for(const match of html.matchAll(/<([\w-]+)\b([^>]*\bid="([^"]+)"[^>]*)>/g)){
  const el=element(match[1]);el.disabled=/\bdisabled\b/.test(match[2]);el.hidden=/\bhidden\b/.test(match[2]);nodes.set(match[3],el);
 }
 const document={getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)},createElement(tag){const el=element(tag);all.push(el);return el},querySelectorAll(selector){
  const match=selector.match(/^input\[name="([^"]+)"\](:checked)?$/);
  return match?all.filter(el=>el.tagName==='INPUT'&&el.name===match[1]&&(!match[2]||el.checked)):[];
 }};
 const fetch=async(_url,options)=>{if(options?.body){posts.push(JSON.parse(options.body));return {ok:true,json:async()=>({id:'fixture',segment_order:['profil','troisquarts','visage']})};}return {ok:true,json:async()=>({segments,asset_count:segments.length?1:0})}};
 vm.runInNewContext(fs.readFileSync(path.join(app,'studio.js'),'utf8'),{document,window:{},fetch,URL,Blob,crypto:require('node:crypto').webcrypto,structuredClone,setTimeout,clearTimeout});
 await tick();await tick();return {nodes,posts,choices:()=>document.querySelectorAll('input[name="studio-segment"]')};
}
const segment=id=>({id,label:id,tags:[],start:0,end:1,kind:'authentic_capture',review:'approved_internal',identity_anchor:true,availability:'verified',revision:1,asset_id:'a'.repeat(64),metadata:{width:32,height:32,duration:16,audio:false}});

test('Empty Studio shows its empty state and cannot prepare a brief',async()=>{
 const {nodes,posts}=await studio([]);assert.match(nodes.get('feedback').textContent,/bibliothèque vide|aucun passage/i);
 for(const id of ['play','prepare','verify','export'])assert.equal(nodes.get(id).disabled,true);
 await nodes.get('prepare').onclick();assert.equal(nodes.get('prepare').disabled,true);assert.deepEqual(posts,[]);
});
test('A catalogue with arbitrary IDs requires explicit selections before preparing its brief',async()=>{
 const {nodes,posts,choices}=await studio([segment('custom')]);assert.equal(nodes.get('selectedTitle').textContent,'custom');
 assert.equal(nodes.get('prepare').disabled,true);assert.doesNotMatch(nodes.get('feedback').textContent,/undefined|indisponible/);assert.deepEqual(posts,[]);
 nodes.get('anchor').value='custom';nodes.get('anchor').onchange();
 const chosen=choices().find(el=>el.value==='custom');assert.ok(chosen);chosen.checked=true;chosen.onchange();
 assert.equal(nodes.get('prepare').disabled,false);await nodes.get('prepare').onclick();
 assert.deepEqual(posts[0].segment_ids,['custom']);assert.equal(posts[0].anchor_id,'custom');assert.deepEqual(posts[0].expected_revisions,{custom:1});
});
test('The verified demo retains its exact three segments and revisions',async()=>{
 const {nodes,posts}=await studio(['profil','troisquarts','visage'].map(segment));assert.equal(nodes.get('prepare').disabled,false);
 await nodes.get('prepare').onclick();assert.deepEqual(posts[0].segment_ids,['profil','troisquarts','visage']);assert.equal(posts[0].anchor_id,'visage');assert.deepEqual(posts[0].expected_revisions,{profil:1,troisquarts:1,visage:1});
});

function captureFixture({permission=[],modules=[],resumes=[],firstLease=null}={}){
 const streams=[],contexts=[],leaseCalls=[];let acquisitions=0,resumesStarted=0;
 const newStream=()=>{const stream={stops:0,getTracks:()=>[{stop(){stream.stops++}}]};streams.push(stream);return stream};
 class AudioContext{
  constructor(){const i=contexts.length;this.closed=0;this.sampleRate=48000;this.audioWorklet={addModule:()=>modules[i]?.promise||Promise.resolve()};this.resume=()=>{resumesStarted++;return resumes[i]?.promise||Promise.resolve()};contexts.push(this);}
  createMediaStreamSource(){return {connect(){}}}async close(){this.closed++}
 }
 class AudioWorkletNode{constructor(){this.port={}}connect(){}disconnect(){}}
 const fetch=async(_url,options)=>{const release=JSON.parse(options.body).release;leaseCalls.push(release?'release':'claim');if(!release&&++acquisitions===1&&firstLease)await firstLease.promise;return {status:200,ok:true,json:async()=>({owned:!release})}};
 let calls=0;const window={AudioContext,addEventListener(){}};
 vm.runInNewContext(fs.readFileSync(path.join(app,'capture.js'),'utf8'),{window,AudioContext,AudioWorkletNode,navigator:{mediaDevices:{getUserMedia(){const p=permission[calls++];return p?p.promise:Promise.resolve(newStream())}}},crypto:require('node:crypto').webcrypto,fetch,setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){},Float32Array,ArrayBuffer,DataView});
 return {capture:window.BojCapture,streams,contexts,leaseCalls,newStream,get calls(){return calls},get resumesStarted(){return resumesStarted}};
}
async function newCaptureSurvives(f,late,stage){
 const old=f.capture.start(()=>{}).then(()=>null,e=>e);await until(stage);
 await f.capture.cancel();await f.capture.start(()=>{});const currentStream=f.streams.at(-1),currentContext=f.contexts.at(-1);
 late();const error=await old;assert.ok(error?.message);assert.equal(currentStream.stops,0);assert.equal(currentContext.closed,0);
 assert.equal(f.leaseCalls.at(-1),'claim');await f.capture.stop();await f.capture.cancel();
}
test('Rejected permission from a cancelled capture cannot close a newer capture',async()=>{
 const p=deferred(),f=captureFixture({permission:[p]});await newCaptureSurvives(f,()=>p.reject(Error('old permission')),()=>f.calls===1);
});
test('A late successful permission stops only its own old stream',async()=>{
 const p=deferred(),f=captureFixture({permission:[p]}),oldStream=f.newStream();await newCaptureSurvives(f,()=>p.resolve(oldStream),()=>f.calls===1);assert.equal(oldStream.stops,1);
});
for(const reject of [false,true])test('Late AudioWorklet '+(reject?'rejection':'completion')+' does not cancel the current capture',async()=>{
 const p=deferred(),f=captureFixture({modules:[p]});await newCaptureSurvives(f,()=>reject?p.reject(Error('old module')):p.resolve(),()=>f.contexts.length===1);
});
test('Late AudioContext resume failure is isolated to its capture',async()=>{
 const p=deferred(),f=captureFixture({resumes:[p]});await newCaptureSurvives(f,()=>p.reject(Error('old resume')),()=>f.resumesStarted===1);
});
test('A cancelled pending lease releases before the next capture acquires',async()=>{
 const lease=deferred(),f=captureFixture({firstLease:lease});const old=f.capture.start(()=>{}).catch(e=>e);await until(()=>f.leaseCalls.length===1);
 const cancel=f.capture.cancel();const next=f.capture.start(()=>{});lease.resolve();await Promise.all([old,cancel,next]);
 assert.deepEqual(f.leaseCalls,['claim','release','claim']);assert.equal(f.streams.at(-1).stops,0);await f.capture.stop();await f.capture.cancel();
});
