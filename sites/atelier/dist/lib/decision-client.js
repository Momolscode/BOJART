/** Browser transport to the same-origin local gateway. No TypeSafe credential reaches this module. */
import {DECISION_LIMITS,DECISION_POLICY_VERSION,DecisionError,normalizeDecisionRequest,decisionFingerprint,validateProjectDecision} from './decision-contract.js';

const fail=(code,message,status=502)=>{throw new DecisionError(code,message,status);};
async function boundedJSON(response){
  if(!/^application\/json(?:\s*;|$)/i.test(response.headers?.get?.('content-type')||''))fail('invalid_response','Le service de décision n’a pas renvoyé du JSON.');
  const length=response.headers?.get?.('content-length');
  if(length!=null&&(!/^\d+$/.test(length)||Number(length)>DECISION_LIMITS.responseBytes))fail('invalid_response','La réponse de décision dépasse la taille autorisée.');
  if(!response.body?.getReader)fail('invalid_response','Le corps de décision ne peut pas être contrôlé.');
  const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let bytes=0,text='';
  try{
    for(;;){const{done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>DECISION_LIMITS.responseBytes){await reader.cancel();fail('invalid_response','La réponse de décision dépasse 64 Kio.');}text+=decoder.decode(value,{stream:true});}
    text+=decoder.decode();return JSON.parse(text);
  }catch(error){if(error instanceof DecisionError)throw error;fail('invalid_response','La réponse de décision est illisible.');}finally{reader.releaseLock();}
}
async function checkedCurrent(request,getCurrentRequest){
  const current=await getCurrentRequest();
  if(!current||await decisionFingerprint(current)!==await decisionFingerprint(request))fail('context_changed','Le dossier ou ses preuves ont changé ; ce conseil est périmé.',409);
}

/** Rebuild the packet before AND after the call. Revalidate again when an older card is opened. */
export async function requestProjectDecision(input,{fetchImpl=globalThis.fetch,getCurrentRequest,timeoutMs=10000,now=Date.now}={}){
  const request=normalizeDecisionRequest(input);
  if(typeof fetchImpl!=='function'||typeof getCurrentRequest!=='function'||!Number.isSafeInteger(timeoutMs)||timeoutMs<1||timeoutMs>30000)fail('invalid_configuration','La relecture du contexte est nécessaire pour demander un conseil.',503);
  await checkedCurrent(request,getCurrentRequest);
  const controller=new AbortController();let timer;
  const operation=(async()=>{
    const response=await fetchImpl('/api/decisions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal});
    if(!response||typeof response.ok!=='boolean')fail('invalid_response','Réponse locale inexploitable.');
    if(!response.ok){try{await response.body?.cancel?.();}catch{}const messages={404:'Le service Jev métier n’est pas disponible sur ce site. Ouvrez le dashboard de la tour locale.',409:'Les données ou la version du contrat ont changé. Reprenez la comparaison.',429:'Jev traite déjà une comparaison. Réessayez après son résultat.',503:'Jev n’est pas configuré ou est temporairement indisponible sur cette tour.',504:'Jev n’a pas répondu à temps. Les choix restent disponibles manuellement.'};fail('service_unavailable',messages[response.status]||'Le service Jev n’a pas pu comparer ces options.',response.status);}
    const result=await validateProjectDecision(await boundedJSON(response),request,{now});
    await checkedCurrent(request,getCurrentRequest);
    return result;
  })();
  const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new DecisionError('timeout','Jev n’a pas répondu à temps. Les choix restent disponibles manuellement.',504));},timeoutMs);});
  try{return await Promise.race([operation,deadline]);}catch(error){if(error instanceof DecisionError)throw error;fail('unavailable','Le service de décision est inaccessible. Les choix locaux restent disponibles.');}finally{clearTimeout(timer);}
}

export async function getDecisionProviderStatus({fetchImpl=globalThis.fetch,timeoutMs=2500}={}){
  const unavailable={checked:true,configured:false,connected:false,availability:'unavailable',model:null,policyVersion:DECISION_POLICY_VERSION,advisoryOnly:true};
  if(typeof fetchImpl!=='function'||!Number.isSafeInteger(timeoutMs)||timeoutMs<1||timeoutMs>30000)return unavailable;
  const controller=new AbortController();let timer;
  try{
    const operation=(async()=>{
      const response=await fetchImpl('/api/decisions/status',{signal:controller.signal,credentials:'same-origin',cache:'no-store',redirect:'error'});
      if(!response.ok)return unavailable;
      const value=await boundedJSON(response);
      if(value?.ok!==true||value.provider!=='typesafe'||value.policyVersion!==DECISION_POLICY_VERSION||value.advisoryOnly!==true||typeof value.configured!=='boolean'||typeof value.connected!=='boolean'||typeof value.model!=='string'||!/^jev-(?:\d+\.\d+\.\d+|latest|preview)$/.test(value.model))return unavailable;
      return{checked:true,configured:value.configured,connected:value.configured&&value.connected,availability:!value.configured?'unconfigured':value.connected?'connected':'configured',model:value.model,policyVersion:value.policyVersion,advisoryOnly:true,lastVerifiedAt:value.lastVerifiedAt??null};
    })();
    const deadline=new Promise(resolve=>{timer=setTimeout(()=>{controller.abort();resolve(unavailable);},timeoutMs);});
    return await Promise.race([operation,deadline]);
  }catch{return unavailable;}finally{clearTimeout(timer);}
}
