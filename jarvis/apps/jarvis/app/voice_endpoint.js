'use strict';
// Optional energy-based end of recording. This is not semantic turn detection.
// No network, no wake word, no recognition and no persistent audio storage.
((root)=>{
 function create({threshold=.015,minSpeech=.25,silence=1.1,noSpeech=6,maxSeconds=15}={}){
  for(const value of [threshold,minSpeech,silence,noSpeech,maxSeconds])if(!Number.isFinite(value)||value<=0)throw Error('Paramètre audio invalide.');
  let elapsed=0,voiced=0,quiet=0,finished=null;
  return {push(chunk,rate){
   if(finished)return null;
   if(!Number.isFinite(rate)||rate<=0||!chunk.length)return null;
   let sum=0;for(const value of chunk){if(!Number.isFinite(value))return null;sum+=value*value;}
   const duration=chunk.length/rate,rms=Math.sqrt(sum/chunk.length);elapsed+=duration;
   if(rms>=threshold){voiced+=duration;quiet=0;}else quiet+=duration;
   if(elapsed>=maxSeconds)finished='limit';
   else if(voiced>=minSpeech&&quiet>=silence)finished='pause';
   else if(voiced<minSpeech&&elapsed>=noSpeech)finished='no_speech';
   return finished;
  }};
 }
 const api=Object.freeze({create});root.BojEndpoint=api;
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
