'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const app=path.resolve(__dirname,'../apps/jarvis/app');
const tick=()=>new Promise(resolve=>setImmediate(resolve));

// Execute both production scripts. Only browser devices, DOM and HTTP are doubles.
async function fixture(){
 const nodes=new Map(),contexts=[],worklets=[],transcriptions=[],turns=[];
 let releaseClose,leaseOwner=null;
 const element=()=>({textContent:'',value:'',hidden:false,disabled:false,checked:false,className:'',addEventListener(){},click(){return this.onclick?.();}});
 const document={getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);},addEventListener(){}};
 class AudioContext{
  constructor(){this.sampleRate=48000;this.audioWorklet={addModule:async()=>{}};this.number=contexts.push(this);}
  createMediaStreamSource(){return{connect(){}}}async resume(){}
  close(){return this.number===1?new Promise(resolve=>releaseClose=resolve):Promise.resolve();}
 }
 class AudioWorkletNode{constructor(){this.port={};worklets.push(this);}connect(){}disconnect(){}}
 const window={AudioContext,addEventListener(){},speechSynthesis:{cancel(){},getVoices(){return[]}}};
 const ctx={window,document,AudioContext,AudioWorkletNode,location:{search:'?project_id=TEST'},URLSearchParams,
  navigator:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop(){}}]})}},
  crypto:require('node:crypto').webcrypto,sessionStorage:{getItem:()=>null,setItem(){},removeItem(){}},EventSource:class{close(){}},
  setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){},Float32Array,ArrayBuffer,DataView,
  fetch:async(url,options={})=>{
   let data={};
   if(url==='/api/jarvis/status')data={langgraph:'sqlite_ready',jev:{status:'disabled'},voice:{status:'available'}};
   else if(url.startsWith('/api/state'))data={revision:1,context_sha256:'a'.repeat(64)};
   else if(url==='/api/voice/lease'){const b=JSON.parse(options.body);leaseOwner=b.release?null:b.client_id;data={owned:!b.release};}
   else if(url==='/api/voice/transcribe'){
    transcriptions.push({bytes:options.body.byteLength,owner:options.headers['X-Boj-Voice-Owner'],leaseOwner});
    data={status:'no_speech'};
   }else if(url==='/api/jarvis/turn'){turns.push(JSON.parse(options.body));data={status:'CLARIFY'};}
   else throw Error('Unexpected request '+url);
   return{ok:true,status:200,json:async()=>data};
  }};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(app,'capture.js'),'utf8'),ctx);ctx.BojCapture=window.BojCapture;
 vm.runInContext(fs.readFileSync(path.join(app,'tower_voice.js'),'utf8'),ctx);await tick();await tick();
 return{nodes,transcriptions,turns,capture:window.BojCapture,
  async start(){await nodes.get('voiceRecord').onclick();worklets.at(-1).port.onmessage({data:new Float32Array(48000).fill(.1)});},
  async stopPending(){const promise=nodes.get('voiceRecord').onclick();await tick();assert.equal(typeof releaseClose,'function');return{promise,releaseClose};}};
}

test('A cancelled stop cannot transcribe or replace the phase of a newer capture',async()=>{
 const f=await fixture();await f.start();const old=await f.stopPending();
 await f.nodes.get('voiceCancel').onclick();await f.start();
 assert.equal(f.nodes.get('voicePhase').textContent,'MICROPHONE ACTIF');
 old.releaseClose();await old.promise;
 assert.deepEqual(f.transcriptions,[]);assert.deepEqual(f.turns,[]);
 assert.equal(f.nodes.get('voicePhase').textContent,'MICROPHONE ACTIF');
 assert.equal(f.nodes.get('voiceRecord').textContent,'Terminer la prise');
 await f.capture.cancel();
});

test('A current stop still submits its complete WAV under its active lease',async()=>{
 const f=await fixture();await f.start();const current=await f.stopPending();current.releaseClose();await current.promise;
 assert.equal(f.transcriptions.length,1);assert.equal(f.transcriptions[0].bytes,32044);
 assert.equal(f.transcriptions[0].owner,f.transcriptions[0].leaseOwner);
 assert.equal(f.nodes.get('voicePhase').textContent,'À L’ÉCOUTE');assert.deepEqual(f.turns,[]);
});
