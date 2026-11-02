'use strict';
// Explicit microphone gesture only. Audio never goes to a cloud speech-recognition API.
window.BojCapture=(()=>{
  let active=null,leaseHolder=null,leaseQueue=Promise.resolve();
  const MAX_SECONDS=15;
  const owner='mic_'+crypto.randomUUID().replaceAll('-','');
  async function sendLease(release=false){
    const r=await fetch('/api/voice/lease',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({client_id:owner,release}),keepalive:release});
    // Standalone M02/M03 servers predate the consolidated audio lease.
    if(r.status===404)return false;
    const result=await r.json();if(!r.ok)throw Error(result.error||'Microphone réservé ailleurs.');return true;
  }
  function queuedLease(fn){const pending=leaseQueue.then(fn);leaseQueue=pending.catch(()=>{});return pending;}
  async function acquire(s){
    return queuedLease(async()=>{
      if(active!==s)throw Error('Prise annulée.');
      const leased=await sendLease();
      // Finish a cancelled acquisition before a newer session can claim.
      if(active!==s){if(leased)await sendLease(true);throw Error('Prise annulée.');}
      if(leased)leaseHolder=s;return leased;
    });
  }
  async function cleanupAudio(s){
    clearTimeout(s.limitTimer);s.limitTimer=null;
    if(s.stream){s.stream.getTracks().forEach(t=>t.stop());s.stream=null;}
    if(s.node){s.node.disconnect();s.node=null;}
    if(s.context){const c=s.context;s.context=null;await c.close().catch(()=>{});}
  }
  async function dispose(s){
    if(!s)return;s.stopped=true;s.chunks=[];s.samples=0;
    clearInterval(s.leaseTimer);s.leaseTimer=null;
    await cleanupAudio(s);
    await queuedLease(async()=>{if(leaseHolder===s){leaseHolder=null;await sendLease(true);}}).catch(()=>{});
  }
  async function cancel(){const previous=active;active=null;await dispose(previous);}
  async function start(callback,options={}){
    const previous=active,s={stream:null,context:null,node:null,chunks:[],samples:0,limitTimer:null,leaseTimer:null,stopped:false};active=s;
    try{
      await dispose(previous);if(active!==s)throw Error('Prise annulée.');
      const endpoint=options.endpointing?window.BojEndpoint?.create():null;let finishIssued=false;
      if(options.endpointing&&!endpoint)throw Error('Détection de pause indisponible ; rechargez la régie.');
      function finish(reason){if(active!==s||s.stopped||finishIssued)return;finishIssued=true;Promise.resolve().then(()=>{if(active===s&&!s.stopped)callback?.(reason);});}
      if(!navigator.mediaDevices?.getUserMedia||!window.AudioContext)throw Error('Capture locale indisponible dans ce navigateur.');
      if(await acquire(s))s.leaseTimer=setInterval(()=>queuedLease(async()=>{if(active===s&&leaseHolder===s)await sendLease();}).catch(()=>{if(active===s)cancel();}),8000);
      const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
      if(active!==s){stream.getTracks().forEach(t=>t.stop());throw Error('Prise annulée.');}
      s.stream=stream;const context=new AudioContext();s.context=context;
      await context.audioWorklet.addModule('/audio_worklet.js');
      if(active!==s)throw Error('Prise annulée.');
      const source=context.createMediaStreamSource(stream);s.node=new AudioWorkletNode(context,'boj-capture');
      s.node.port.onmessage=e=>{if(active!==s||s.stopped)return;const remain=Math.floor(context.sampleRate*MAX_SECONDS)-s.samples;if(remain<=0)return;const chunk=e.data.subarray(0,remain);s.chunks.push(chunk);s.samples+=chunk.length;const reason=endpoint?.push(chunk,context.sampleRate);if(reason)finish(reason);};
      source.connect(s.node);s.node.connect(context.destination);await context.resume();
      if(active!==s)throw Error('Prise annulée.');
      s.limitTimer=setTimeout(()=>finish('limit'),MAX_SECONDS*1000);
    }catch(e){if(active===s)active=null;await dispose(s);throw e;}
  }
  function wav(data,rate){
    const outRate=16000;const n=Math.floor(data.length*outRate/rate);const buf=new ArrayBuffer(44+n*2),v=new DataView(buf);
    const text=(o,s)=>{for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i))};
    text(0,'RIFF');v.setUint32(4,36+n*2,true);text(8,'WAVE');text(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,outRate,true);v.setUint32(28,outRate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);text(36,'data');v.setUint32(40,n*2,true);
    for(let i=0;i<n;i++){const a=Math.floor(i*rate/outRate),b=Math.max(a+1,Math.floor((i+1)*rate/outRate));let sum=0;for(let j=a;j<b&&j<data.length;j++)sum+=data[j];let x=Math.max(-1,Math.min(1,sum/(b-a)));v.setInt16(44+i*2,Math.round(x*(x<0?32768:32767)),true);}
    return buf;
  }
  async function stop(){const s=active;if(!s?.context||s.stopped)throw Error('Aucune prise en cours.');s.stopped=true;const rate=s.context.sampleRate;const flat=new Float32Array(s.samples);let o=0;for(const c of s.chunks){flat.set(c,o);o+=c.length;}const out=wav(flat,rate);s.chunks=[];s.samples=0;await cleanupAudio(s);return out;}
  window.addEventListener('pagehide',()=>{cancel();});
  return {start,stop,cancel,owner,encodeForTest:wav};
})();
