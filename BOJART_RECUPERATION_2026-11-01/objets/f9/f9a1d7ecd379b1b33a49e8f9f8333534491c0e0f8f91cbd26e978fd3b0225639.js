'use strict';
(()=>{
 const el=id=>document.getElementById(id),project=new URLSearchParams(location.search).get('project_id')||'BOJ-PILOTE-001';
 const key='boj_m06_turn_'+project;let pending=null,epoch=0,busy=false,recording=false,capability=null,spoken=null,permissionPending=false,lastResult=null,recordContext=null,approvalTarget=null;
 const labels={NEW:'EN ATTENTE',RUNNING:'INTERPRÉTATION',INTERRUPTED:'À REPRENDRE',CLARIFY:'À PRÉCISER',STALE:'CONTEXTE MODIFIÉ',FAILED:'ÉCHEC CONTRÔLÉ',CANCELLED:'ANNULÉ',CANCELLED_AFTER_DISPATCH:'ANNULÉ',RESTORED:'À REFORMULER',AWAITING_CONFIRMATION:'PROPOSITION JEV',QUEUED:'ENVOYÉ AUX VUES'};
 async function api(path,data,headers){const r=await fetch(path,{cache:'no-store',...(data===undefined?{}:{method:'POST',headers:headers||{'Content-Type':'application/json'},body:headers?data:JSON.stringify(data)})});const v=await r.json();if(!r.ok)throw Error(v.error||'Service local indisponible.');return v;}
 function state(label,message,bad=false){el('voicePhase').textContent=label;el('voiceFeedback').textContent=message;el('voiceFeedback').className='feedback '+(bad?'bad':'good');}
 function save(){if(pending)sessionStorage.setItem(key,JSON.stringify(pending));else sessionStorage.removeItem(key);}
 function controls(){el('voiceSend').disabled=busy||recording||permissionPending;el('voiceText').disabled=busy||recording||permissionPending;el('voiceConfirm').disabled=busy||recording||permissionPending;el('voiceAutoEnd').disabled=recording||permissionPending;el('voiceRecord').disabled=(busy&&!recording)||permissionPending||capability?.voice?.status!=='available';el('voiceRecord').textContent=recording?'Terminer la prise':'Parler à Jarvis';}
 function speak(text){if(!el('voiceSpeak').checked)return;const v=(window.speechSynthesis?.getVoices()||[]).find(v=>v.localService&&/^fr(?:[-_]|$)/i.test(v.lang));if(!v)return;const u=new SpeechSynthesisUtterance(text);u.voice=v;u.lang=v.lang;window.speechSynthesis.cancel();window.speechSynthesis.speak(u);}
 function result(r){
  lastResult=r;
  el('voiceConfirm').hidden=r.status!=='AWAITING_CONFIRMATION';
  const cancelled=r.status.startsWith('CANCELLED')||r.status==='RESTORED';
  const displayed=!cancelled&&r.display?.state==='rendered',failed=!cancelled&&['failed','stale','cancelled','cancelled_restore'].includes(r.display?.state);
  const progress=r.display?.total_views?r.display.rendered_views+'/'+r.display.total_views+' vues affichées. ':'';
  state(cancelled?labels[r.status]:displayed?'AFFICHÉ · REÇU NAVIGATEUR':failed?'AFFICHAGE INTERROMPU':labels[r.status]||r.status,
   cancelled?r.message:displayed?progress+'Vue '+r.display.target_role+' affichée · '+r.elapsed_to_display_ms+' ms depuis la commande.':failed?r.display.message:progress+(r.message||'Reprendre cette même référence.'),failed||['FAILED','STALE','INTERRUPTED'].includes(r.status));
  el('voiceRef').textContent='Référence '+r.request_id+' · '+(r.decision?.source||'local');
  if((displayed||r.status==='AWAITING_CONFIRMATION')&&spoken!==r.request_id+':'+r.status){spoken=r.request_id+':'+r.status;if(r.status==='AWAITING_CONFIRMATION')speak(r.message+' Dites : Confirme cet affichage.');else if(r.decision?.choice!=='silence')speak(r.display?.total_views?'Les trois vues sont affichées.':'La vue est affichée.');}
 }
 async function submit(source='typed',frozen=null){
  const token=source==='voice'?epoch:++epoch;busy=true;controls();window.speechSynthesis?.cancel();
  try{
   if(!pending){const p=frozen||await api('/api/state?project_id='+encodeURIComponent(project));if(token!==epoch)return;
    pending={request_id:'turn_'+crypto.randomUUID().replaceAll('-',''),client_id:BojCapture.owner,project_id:project,revision:p.revision,text:el('voiceText').value.trim(),operation_id:frozen?frozen.operation_id:el('operation').value||null,source,...(p.context_sha256?{context_sha256:p.context_sha256}:{})};save();}
   state('INTERPRÉTATION','Lecture de la commande dans le dossier courant…');
   const r=await api('/api/jarvis/turn',pending);if(token!==epoch)return;result(r);
   if(!r.busy&&r.status!=='INTERRUPTED')el('voiceSend').textContent='Nouvelle commande';
   else el('voiceSend').textContent='Reprendre cette commande';
  }catch(e){if(token===epoch){state('À REPRENDRE',e.message+' La référence est conservée.',true);el('voiceSend').textContent='Reprendre cette commande';}}
  finally{if(token===epoch){busy=false;controls();}}
 }
 el('voiceSend').onclick=()=>{if(el('voiceSend').textContent==='Nouvelle commande'){pending=null;save();}submit();};
 el('voiceText').addEventListener('input',()=>{epoch++;pending=null;save();el('voiceConfirm').hidden=true;el('voiceSend').textContent='Envoyer la commande';});
 el('voiceText').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!busy&&!recording){e.preventDefault();el('voiceSend').click();}});
 function norm(text){return text.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[.,!?]/g,' ').trim().replace(/^jarvis\s*/,'').replace(/\s+/g,' ');}
 async function stop(reason){
  if(!recording)return;recording=false;busy=true;controls();const token=epoch;
  try{const audio=await BojCapture.stop();state('TRANSCRIPTION','Reconnaissance locale de la prise…');
   const r=await api('/api/voice/transcribe',audio,{'Content-Type':'audio/wav','X-Boj-Voice-Owner':BojCapture.owner});
   if(token!==epoch)return;
   if(r.status==='no_speech'){state('À L’ÉCOUTE','Aucune parole exploitable. Aucun ordre envoyé.');return;}
   const phrases=[...(capability?.voice_confirmation?.approve||[]),...(capability?.voice_confirmation?.cancel||[])].map(norm);
   if(approvalTarget&&pending?.request_id===approvalTarget.request_id&&phrases.includes(norm(r.text))){
    const receipt=await api('/api/jarvis/confirm-voice',{...approvalTarget,project_id:project,text:r.text});if(token!==epoch)return;result(receipt);return;
   }
   el('voiceText').value=r.text;pending=null;save();await submit('voice',recordContext);
  }catch(e){if(token===epoch)state('VOIX INDISPONIBLE',e.message,true);}
  finally{if(token===epoch){busy=true;controls();await BojCapture.cancel();if(token===epoch){recordContext=null;approvalTarget=null;busy=false;controls();}}}
 }
 el('voiceRecord').onclick=async()=>{if(recording)return stop();if(busy||permissionPending)return;
  const token=++epoch;permissionPending=true;controls();window.speechSynthesis?.cancel();
  try{const snapshot=await api('/api/state?project_id='+encodeURIComponent(project));if(token!==epoch)return;
   recordContext={revision:snapshot.revision,context_sha256:snapshot.context_sha256,operation_id:el('operation').value||null};
   approvalTarget=lastResult?.status==='AWAITING_CONFIRMATION'&&pending?{request_id:pending.request_id,client_id:pending.client_id}:null;
   await BojCapture.start(stop,{endpointing:el('voiceAutoEnd').checked});if(token!==epoch){await BojCapture.cancel();return;}recording=true;state('MICROPHONE ACTIF',approvalTarget?'Dites « Confirme cet affichage » ou « Annule cette proposition ».':el('voiceAutoEnd').checked?'Parlez. Une pause terminera la prise ; vous pouvez aussi cliquer Terminer.':'Parlez puis terminez la prise. Limite : 15 secondes.');}
  catch(e){if(token===epoch)state('VOIX INDISPONIBLE',e.message,true);}
  finally{if(token===epoch){permissionPending=false;controls();}}
 };
 el('voiceCancel').onclick=async()=>{const token=++epoch;busy=true;recording=false;permissionPending=false;controls();window.speechSynthesis?.cancel();const old=pending;pending=null;save();await BojCapture.cancel();
  if(token!==epoch)return;recordContext=null;approvalTarget=null;busy=false;el('voiceConfirm').hidden=true;state('ANNULATION','Prise et réponse vocale interrompues.');controls();
  if(old){try{const receipt=await api('/api/jarvis/cancel',{request_id:old.request_id,client_id:old.client_id});if(token===epoch)result(receipt);}catch(e){if(token===epoch)state('À VÉRIFIER',e.message+' Consultez le journal avant de reprendre.',true);}}
 };
 el('voiceConfirm').onclick=async()=>{if(!pending)return;busy=true;controls();const token=epoch;try{const r=await api('/api/jarvis/confirm',{request_id:pending.request_id,client_id:pending.client_id});if(token===epoch)result(r);}catch(e){if(token===epoch)state('CONFIRMATION REFUSÉE',e.message,true);}finally{if(token===epoch){busy=false;controls();}}};
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&(recording||permissionPending))el('voiceCancel').click();});
 async function update(){
  const current=pending,token=epoch;if(!current||busy||recording||permissionPending)return;
  try{const r=await api('/api/jarvis/turn?request_id='+encodeURIComponent(current.request_id));if(token===epoch&&pending===current)result(r);}catch(e){}
 }
 try{pending=JSON.parse(sessionStorage.getItem(key)||'null');if(pending){el('voiceText').value=pending.text;el('voiceSend').textContent='Reprendre cette commande';}}catch(e){sessionStorage.removeItem(key);}
 api('/api/jarvis/status').then(r=>{capability=r;const labels={sqlite_ready:'LangGraph prêt',missing_dependency:'règles locales seules',disabled:'désactivé',missing_key:'clé absente',configured_unverified:'configuré, à tester',cooldown:'temporairement indisponible',available:'fichiers présents, à tester',missing_runtime:'moteur absent',missing_weights:'modèle absent'};el('voiceCapabilities').textContent='Pilotage : '+(labels[r.langgraph]||r.langgraph)+' · Jev : '+(labels[r.jev.status]||r.jev.status)+' · Voix : '+(labels[r.voice.status]||r.voice.status);
  if(r.voice.status!=='available')state('CLAVIER DISPONIBLE','La commande écrite fonctionne. Configurez le moteur vocal local et ses fichiers pour activer le microphone.');controls();update();}).catch(e=>state('SERVICE INDISPONIBLE',e.message,true));
 const events=new EventSource('/api/tower/events');events.onmessage=()=>update();window.addEventListener('pagehide',()=>events.close());setInterval(update,5000);controls();
})();
