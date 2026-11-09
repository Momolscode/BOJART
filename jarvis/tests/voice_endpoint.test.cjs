const {test}=require('node:test');
const assert=require('node:assert/strict');
const {create}=require('../apps/jarvis/app/voice_endpoint.js');
const audio=(amp,seconds)=>new Float32Array(Math.round(seconds*1000)).fill(amp);
test('speech then pause ends a single turn',()=>{const gate=create();assert.equal(gate.push(audio(.1,.5),1000),null);assert.equal(gate.push(audio(0,1.2),1000),'pause');assert.equal(gate.push(audio(0,1.2),1000),null);});
test('silence does not create a speech turn',()=>{const gate=create();assert.equal(gate.push(audio(0,6.1),1000),'no_speech');});
test('short hesitation does not end speech',()=>{const gate=create();gate.push(audio(.1,.4),1000);assert.equal(gate.push(audio(0,.6),1000),null);assert.equal(gate.push(audio(.1,.3),1000),null);assert.equal(gate.push(audio(0,1.2),1000),'pause');});
test('short impulse does not count as enough speech',()=>{const gate=create();gate.push(audio(.4,.05),1000);assert.equal(gate.push(audio(0,2),1000),null);assert.equal(gate.push(audio(0,4.1),1000),'no_speech');});
test('continuous noise is bounded by the maximum recording duration',()=>{const gate=create();assert.equal(gate.push(audio(.1,15.1),1000),'limit');});
test('sample rate does not change the timing meaning',()=>{const gate=create();assert.equal(gate.push(new Float32Array(48000).fill(.1),48000),null);assert.equal(gate.push(new Float32Array(57600),48000),'pause');});
test('invalid settings cannot start a detector',()=>{assert.throws(()=>create({silence:NaN}));assert.throws(()=>create({threshold:-1}));});
// 9 November 2026: steady workshop noise must not hold a take open until the 15 s limit.
const RATE=16000;
function noise(seconds,level,seed=7){let s=seed;const out=new Float32Array(Math.round(seconds*RATE));
 for(let i=0;i<out.length;i++){s=(s*1103515245+12345)%2147483648;out[i]=((s/2147483648)*2-1)*level*Math.sqrt(3);}return out;}
function speech(seconds,level,bed){const out=noise(seconds,bed,11);
 for(let i=0;i<out.length;i++){const t=i/RATE,syllable=.55+.45*Math.sin(2*Math.PI*4*t);out[i]+=level*syllable*Math.sin(2*Math.PI*220*t);}return out;}
function feed(gate,signal){for(let i=0;i<signal.length;i+=128){const r=gate.push(signal.subarray(i,i+128),RATE);if(r)return [r,(i+128)/RATE];}return [null,signal.length/RATE];}
test('steady workshop noise after a sentence counts as a pause',()=>{const gate=create();
 assert.deepEqual(feed(gate,noise(1,.05)),[null,1]);assert.equal(feed(gate,speech(2,.3,.05))[0],null);
 const [reason,after]=feed(gate,noise(4,.05,3));assert.equal(reason,'pause');assert.ok(after<1.6,`pause after ${after} s`);});
test('steady noise alone runs to the limit',()=>{const gate=create();
 const [reason,at]=feed(gate,noise(15.2,.05));assert.equal(reason,'limit');assert.ok(at>=15);});
test('a short bang in the noise does not end the take before speech',()=>{const gate=create();
 feed(gate,noise(1,.05));const bang=new Float32Array(Math.round(.06*RATE)).fill(.6);assert.equal(feed(gate,bang)[0],null);
 assert.equal(feed(gate,noise(2,.05,5))[0],null);assert.equal(feed(gate,speech(1.5,.3,.05))[0],null);assert.equal(feed(gate,noise(2,.05,9))[0],'pause');});
test('background ratio must stay above one',()=>{assert.throws(()=>create({ratio:1}));assert.throws(()=>create({frame:3,window:3}));});
