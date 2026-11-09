'use strict';
// Optional energy-based end of recording. This is not semantic turn detection.
// No network, no wake word, no recognition and no persistent audio storage.
//
// 9 November 2026: in steady workshop noise (printer, loud workshop) the fixed threshold heard the
// noise as speech, so a take only ended at the 15 s limit (voice bench: about 12 s of waiting after
// the sentence). The original rule is kept unchanged, chunk by chunk. A second rule only adds a way
// to end: it measures the background as the quietest 20 ms frame of the last few seconds; once
// speech standing clearly above that background has been heard, a stretch of `silence` seconds
// without such salient frames is a pause, even if the noise stays above the fixed threshold.
((root)=>{
 function create({threshold=.015,minSpeech=.25,silence=1.1,noSpeech=6,maxSeconds=15,frame=.02,window=3,ratio=2.5}={}){
  for(const value of [threshold,minSpeech,silence,noSpeech,maxSeconds,frame,window,ratio])if(!Number.isFinite(value)||value<=0)throw Error('Paramètre audio invalide.');
  if(ratio<=1||frame>=window)throw Error('Paramètre audio invalide.');
  let elapsed=0,voiced=0,quiet=0,finished=null;// original rule, per pushed chunk
  let clock=0,salient=0,sinceSalient=0,energy=0,count=0;// background rule, per frame
  const recent=[];// [end time, rms] of the frames inside the background window
  function frameDone(rms,duration){
   clock+=duration;
   recent.push([clock,rms]);while(recent.length&&recent[0][0]<=clock-window)recent.shift();
   let floor=rms;for(const item of recent)if(item[1]<floor)floor=item[1];
   if(rms>=Math.max(threshold,floor*ratio)){salient+=duration;sinceSalient=0;}else sinceSalient+=duration;
  }
  return {push(chunk,rate){
   if(finished)return null;
   if(!Number.isFinite(rate)||rate<=0||!chunk.length)return null;
   for(const value of chunk)if(!Number.isFinite(value))return null;
   const size=Math.max(1,Math.round(frame*rate));let sum=0;
   for(const value of chunk){
    const square=value*value;sum+=square;energy+=square;count+=1;
    if(count>=size){frameDone(Math.sqrt(energy/count),count/rate);energy=0;count=0;}
   }
   const duration=chunk.length/rate,rms=Math.sqrt(sum/chunk.length);elapsed+=duration;
   if(rms>=threshold){voiced+=duration;quiet=0;}else quiet+=duration;
   const backgroundPause=salient>=minSpeech&&sinceSalient>=silence;
   if(elapsed>=maxSeconds)finished='limit';
   else if(voiced>=minSpeech&&(quiet>=silence||backgroundPause))finished='pause';
   else if(voiced<minSpeech&&elapsed>=noSpeech)finished='no_speech';
   return finished;
  }};
 }
 const api=Object.freeze({create});root.BojEndpoint=api;
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
