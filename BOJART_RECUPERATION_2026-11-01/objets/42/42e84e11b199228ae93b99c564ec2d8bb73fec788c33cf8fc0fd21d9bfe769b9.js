'use strict';
// Explicit microphone gesture only. Audio never goes to a cloud speech-recognition API.
window.BojCapture=(()=>{
  let seq=0,stream=null,context=null,node=null,chunks=[],samples=0,limitTimer=null,onLimit=null;
  const MAX_SECONDS=15;
  const owner='mic_'+crypto.randomUUID().replaceAll('-','');let leaseTimer=null,leased=false;
  async function lease(release=false){
    const r=await fetch('/api/voice/lease',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({client_id:owner,release}),keepalive:release});
    // Standalone M02/M03 servers predate the consolidated audio lease.
    if(r.status===404)return false;
    const result=await r.json();if(!r.ok)throw Error(result.error||'Microphone réservé ailleurs.');return true;
  }
  function endTracks(){if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;}
  async function cleanup(){clearTimeout(limitTimer);limitTimer=null;endTracks();if(node){node.disconnect();node=null;}if(context){const c=context;context=null;await c.close().catch(()=>{});}}
  async function cancel(){seq++;chunks=[];samples=0;clearInterval(leaseTimer);leaseTimer=null;await cleanup();if(leased){leased=false;await lease(true).catch(()=>{});}}
  async function start(callback){
    await cancel();const token=seq;onLimit=callback;
    if(!navigator.mediaDevices?.getUserMedia||!window.AudioContext)throw Error('Capture locale indisponible dans ce navigateur.');
    leased=await lease();
    if(seq!==token){if(leased)await lease(true);leased=false;throw Error('Prise annulée.');}
    if(leased)leaseTimer=setInterval(()=>lease().catch(()=>cancel()),8000);
    let s;try{s=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});}catch(e){await cancel();throw e;}
    if(seq!==token){s.getTracks().forEach(t=>t.stop());throw Error('Prise annulée.');}
    stream=s;
    try{
      context=new AudioContext();await context.audioWorklet.addModule('/audio_worklet.js');
      if(seq!==token)throw Error('Prise annulée.');
      const source=context.createMediaStreamSource(stream);node=new AudioWorkletNode(context,'boj-capture');
      node.port.onmessage=e=>{if(seq!==token||!context)return;const remain=Math.floor(context.sampleRate*MAX_SECONDS)-samples;if(remain<=0)return;const chunk=e.data.subarray(0,remain);chunks.push(chunk);samples+=chunk.length;};
      source.connect(node);node.connect(context.destination);await context.resume();
      limitTimer=setTimeout(()=>{if(seq===token)onLimit?.();},MAX_SECONDS*1000);
    }catch(e){await cancel();throw e;}
  }
  function wav(data,rate){
    const outRate=16000;const n=Math.floor(data.length*outRate/rate);const buf=new ArrayBuffer(44+n*2),v=new DataView(buf);
    const text=(o,s)=>{for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i))};
    text(0,'RIFF');v.setUint32(4,36+n*2,true);text(8,'WAVE');text(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,outRate,true);v.setUint32(28,outRate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);text(36,'data');v.setUint32(40,n*2,true);
    for(let i=0;i<n;i++){const a=Math.floor(i*rate/outRate),b=Math.max(a+1,Math.floor((i+1)*rate/outRate));let sum=0;for(let j=a;j<b&&j<data.length;j++)sum+=data[j];let x=Math.max(-1,Math.min(1,sum/(b-a)));v.setInt16(44+i*2,Math.round(x*(x<0?32768:32767)),true);}
    return buf;
  }
  async function stop(){if(!context)throw Error('Aucune prise en cours.');const rate=context.sampleRate;const flat=new Float32Array(samples);let o=0;for(const c of chunks){flat.set(c,o);o+=c.length;}const out=wav(flat,rate);seq++;chunks=[];samples=0;await cleanup();return out;}
  window.addEventListener('pagehide',()=>{cancel();});
  return {start,stop,cancel,owner,encodeForTest:wav};
})();
