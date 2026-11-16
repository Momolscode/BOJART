import {validateWorkshopSeed,validateWorkshopOperation,validateWorkshopReceipt,validateWorkshopGenesis,canonicalWorkshopJSON,workshopEntityKey,WORKSHOP_REDUCER_VERSION} from './workshop.js';
import {createWorkshopBackup} from './workshop-backup.js';

const BINDING_KEY='bojart.workshop.local-service.v1';
const clone=value=>JSON.parse(JSON.stringify(value));
const validInt=n=>Number.isSafeInteger(n)&&n>=0;
const MAX_RESPONSE_BYTES=16777216;
function common(raw){
  if(!raw||raw.ok!==true||raw.version!==2||typeof raw.instanceId!=='string'||!/^workshop-[0-9a-f-]{36}$/.test(raw.instanceId)||typeof raw.workspaceId!=='string'||!/^workspace-[0-9a-f-]{36}$/.test(raw.workspaceId)||raw.reducerVersion!==WORKSHOP_REDUCER_VERSION||!validInt(raw.cursor)||raw.operationCount!==raw.cursor)throw new Error('Le service ne fournit pas le protocole v2 avec reçus métier. Actualisez le service et les écrans ensemble.');
  if(raw.seed!==null){validateWorkshopSeed(raw.seed);validateWorkshopGenesis(raw.genesis,raw.seed);}else if(raw.genesis!==null||raw.cursor!==0)throw new Error('Origine du journal local incohérente.');
  return raw;
}
const storageMode=store=>store.persistent?'browser':'memory';
const initialMessage=store=>store.persistent?'Dossiers conservés dans ce navigateur.':'Conservation limitée à cette fenêtre.';
function problem(code,message){const error=new Error(message);error.code=code;return error;}

/** Same-origin server authority. No printer endpoints or remote credentials. */
export function createWorkshopSync({store,fetchImpl=(...args)=>globalThis.fetch(...args),onStatus=()=>{}}={}){
  if(!store||typeof store.exportJournal!=='function'||typeof store.mergeJournal!=='function')throw new Error('Journal de l’atelier requis.');
  let status={mode:storageMode(store),message:initialMessage(store),pending:0,lastSavedAt:null,instanceId:null,available:false,durable:false,conflicts:0};
  let binding=null;try{const saved=JSON.parse(globalThis.localStorage?.getItem(BINDING_KEY)||'null');if([1,2].includes(saved?.version)&&typeof saved.instanceId==='string')binding=saved;}catch{}
  let enabled=false,stopped=false,flight=null,timer=null,merging=false,known=new Set(),verifiedInstance=null;const controllers=new Set();
  function countPending(){try{return store.exportJournal().operations.filter(op=>!known.has(op.id)).length;}catch{return status.pending;}}
  function update(patch){if(stopped)return;status={...status,...patch};onStatus(clone(status));}
  function defer(delay=5000){clearTimeout(timer);if(enabled&&!stopped)timer=setTimeout(()=>sync(),delay);}
  async function request(path,options={}){
    const controller=new AbortController();controllers.add(controller);const timeout=setTimeout(()=>controller.abort(),10000);
    try{
      const response=await fetchImpl('/api/workshop/'+path,{...options,credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal,headers:{Accept:'application/json',...(options.body?{'Content-Type':'application/json'}:{})}});
      let data;
      if(typeof response.text==='function'){const content=await response.text();if(new TextEncoder().encode(content).byteLength>MAX_RESPONSE_BYTES)throw new Error('Réponse du journal trop volumineuse.');try{data=JSON.parse(content);}catch{throw problem(response.status===404?'service_absent':'invalid_response',response.status===404?'Service local absent.':'La réponse du service n’est pas un journal valide.');}}
      else data=await response.json();
      if(stopped)throw new Error('Synchronisation arrêtée.');
      if(!response.ok){const error=problem(data?.code,typeof data?.message==='string'?data.message.slice(0,600):'Le journal local ne répond pas.');error.httpStatus=response.status;throw error;}
      return data;
    }finally{clearTimeout(timeout);controllers.delete(controller);}
  }
  async function readStatus(){const result=common(await request('status'));if(result.storage!=='sqlite'||result.durable!==true||result.capabilities?.printerCommands!==false||result.capabilities?.businessReceipts!==true||result.capabilities?.persistedGenesis!==true||!validInt(result.limits?.maxBatchOperations)||result.limits.maxBatchOperations<1)throw new Error('Le service ne confirme pas les garanties du journal v2.');return result;}
  function checkInstance(info){if(binding&&binding.instanceId!==info.instanceId)throw problem('instance_changed','Le journal local a changé d’identité. Reconnectez-le explicitement pour reprendre.');}
  function merge(journal,options){merging=true;try{return store.mergeJournal(journal,options);}finally{merging=false;}}
  function fail(error){
    if(stopped)return;
    verifiedInstance=null;
    const conflict=['seed_conflict','operation_id_conflict','instance_changed','authority_conflict','legacy_merge_requires_review','expected_version_required','upgrade_required'].includes(error.code)||/autre atelier|identifiant|conflit|séquence|autorité|reçu|protocole/i.test(error.message);
    update({mode:conflict?'conflict':enabled?'offline':storageMode(store),message:error.message||'Synchronisation indisponible.',pending:countPending(),durable:false});if(conflict)enabled=false;
  }
  async function inspect(){
    try{const info=await readStatus();checkInstance(info);update({available:true,instanceId:info.instanceId,mode:enabled?status.mode:'available',message:'Journal local v2 disponible. Vous pouvez activer sa conservation sur la tour.',pending:countPending()});if(binding&&binding.instanceId===info.instanceId){enabled=true;return sync();}}
    catch(error){if(error.httpStatus===404||error.code==='service_absent'||/n’est pas un journal valide/.test(error.message))update({available:false,mode:storageMode(store),message:initialMessage(store),durable:false,pending:0});else fail(error);}
    return clone(status);
  }
  async function connect(){
    if(flight)return flight;
    try{
      const info=await readStatus(),log=store.exportJournal();
      if(info.seed&&info.seed.at!==log.seed.at&&log.operations.length)throw problem('seed_conflict','Ce navigateur et la tour contiennent deux ateliers différents. Exportez leurs dossiers avant de les rapprocher.');
      if(log.authority&&info.seed&&log.authority.workspaceId!==info.workspaceId)throw problem('authority_conflict','Ce navigateur contient les reçus d’une autre autorité. Exportez ses données avant de changer de tour.');
      binding={version:2,instanceId:info.instanceId};try{globalThis.localStorage?.setItem(BINDING_KEY,JSON.stringify(binding));}catch{}
      known=new Set();verifiedInstance=null;enabled=true;update({available:true,instanceId:info.instanceId});return sync();
    }catch(error){fail(error);return clone(status);}
  }
  async function pull(info){
    let local=store.exportJournal(),receipts=local.authority?.receipts||[];
    if(local.authority&&(local.authority.workspaceId!==info.workspaceId||canonicalWorkshopJSON(local.authority.genesis)!==canonicalWorkshopJSON(info.genesis)))throw problem('authority_conflict','Les reçus du navigateur appartiennent à une autre autorité.');
    if(receipts.length>info.cursor)throw problem('authority_conflict','La tour possède une séquence plus courte que les reçus déjà confirmés. Aucun retour en arrière automatique.');
    // A restored clone can share a workspace ID while owning a different DB
    // identity. Verify the complete old prefix once per connection/reconnection.
    if(verifiedInstance!==info.instanceId)receipts=[];
    let cursor=receipts.length;
    known=new Set(receipts.map(receipt=>receipt.operationId));
    let pages=0,hasMore=true;
    while(hasMore){
      if(++pages>500)throw new Error('Le journal nécessite une reprise en plusieurs passages.');
      const page=common(await request('operations?after='+cursor));checkInstance(page);
      if(page.workspaceId!==info.workspaceId||page.seed?.at!==local.seed.at||!Array.isArray(page.operations)||!Array.isArray(page.receipts)||page.operations.length!==page.receipts.length||!validInt(page.nextCursor)||page.nextCursor!==cursor+page.receipts.length||page.nextCursor>page.cursor||typeof page.hasMore!=='boolean'||page.hasMore!==(page.nextCursor<page.cursor)||page.hasMore&&page.nextCursor===cursor)throw new Error('Page de journal et séquence de reçus incohérentes.');
      const operations=page.operations.map(validateWorkshopOperation),incoming=page.receipts.map(validateWorkshopReceipt);
      for(let i=0;i<incoming.length;i++)if(incoming[i].seq!==cursor+i+1||incoming[i].operationId!==operations[i].id)throw new Error('La page ne lie pas chaque opération au bon reçu.');
      receipts=[...receipts,...incoming];
      merge({version:2,seed:page.seed,operations,authority:{workspaceId:page.workspaceId,reducerVersion:page.reducerVersion,genesis:page.genesis,receipts}},{allowEmptyAdoption:true});
      for(const receipt of incoming)known.add(receipt.operationId);
      cursor=page.nextCursor;hasMore=page.hasMore;
    }
    verifiedInstance=info.instanceId;
  }
  function sync(){
    if(stopped||!enabled)return Promise.resolve(clone(status));if(flight)return flight;clearTimeout(timer);
    flight=(async()=>{
      try{
        if(status.mode!=='saved'||countPending())update({mode:'syncing',message:'Validation du journal par la tour…',pending:countPending(),durable:false});
        let info=await readStatus();checkInstance(info);if(!binding)throw problem('instance_changed','Activez explicitement la conservation sur cette tour.');
        let local=store.exportJournal();
        if(info.seed&&info.seed.at!==local.seed.at){if(local.operations.length)throw problem('seed_conflict','Ce navigateur appartient à un autre atelier. Aucun historique remplacé.');merge({version:1,seed:info.seed,operations:[]},{allowEmptyAdoption:true});local=store.exportJournal();}
        if(!info.seed){
          // One migration transaction preserves all legacy logical history; batches
          // could freeze a different winner halfway through an old journal.
          const backup=await createWorkshopBackup(local,{sourceInstanceId:store.clientId||'browser'});
          try {const initialized=common(await request('backup',{method:'POST',body:JSON.stringify(backup)}));checkInstance(initialized);}
          catch(error) {
            // Another screen may initialize the empty service in the meantime.
            // New guarded commands can proceed normally; legacy unguarded history
            // still requires explicit review rather than a reordered migration.
            if(error.code!=='legacy_merge_requires_review'||local.operations.some(op=>workshopEntityKey(op)&&op.expected?.entityVersion===undefined))throw error;
          }
          info=await readStatus();
        }
        await pull(info);
        const pending=store.exportJournal().operations.filter(op=>!known.has(op.id));
        if(pending.some(op=>workshopEntityKey(op)&&op.expected?.entityVersion===undefined))throw problem('legacy_merge_requires_review','Des commandes v1 inédites proviennent d’un autre historique. Elles restent dans le navigateur ; exportez-les pour les examiner avant de les rapprocher de la séquence confirmée.');
        const batchSize=Math.min(info.limits.maxBatchOperations,100);
        for(let offset=0;offset<pending.length;){
          const batch=[];let size=1000;
          while(offset<pending.length&&batch.length<batchSize){const op=pending[offset],length=new TextEncoder().encode(canonicalWorkshopJSON(op)).byteLength;if(batch.length&&size+length>1500000)break;batch.push(op);size+=length;offset++;}
          const result=common(await request('operations',{method:'POST',body:JSON.stringify({version:2,workspaceId:info.workspaceId,seed:store.exportJournal().seed,operations:batch})}));checkInstance(result);
          const sent=new Set(batch.map(op=>op.id));
          if(result.workspaceId!==info.workspaceId||!Array.isArray(result.accepted)||!Array.isArray(result.duplicates)||!Array.isArray(result.receipts))throw new Error('Accusé de conservation invalide.');
          const acknowledged=[...result.accepted,...result.duplicates];
          if(acknowledged.length!==sent.size||new Set(acknowledged).size!==sent.size||acknowledged.some(id=>!sent.has(id))||result.receipts.length!==sent.size||new Set(result.receipts.map(receipt=>validateWorkshopReceipt(receipt).operationId)).size!==sent.size||result.receipts.some(receipt=>!sent.has(receipt.operationId)))throw new Error('Le service n’a pas confirmé exactement les commandes envoyées.');
          // A concurrent writer may occupy a sequence between pull and append.
          // Pull the complete prefix before marking this batch confirmed locally.
          await pull(await readStatus());
          for(const receipt of result.receipts){const actual=store.exportJournal().authority.receipts[receipt.seq-1];if(canonicalWorkshopJSON(actual)!==canonicalWorkshopJSON(receipt))throw new Error('Le reçu renvoyé par POST diffère du reçu conservé.');}
        }
        const conflicts=[...(store._results?.values()||[])].filter(result=>!result.ok&&result.confirmed).length,remaining=countPending();
        update({mode:conflicts?'conflict':remaining?'syncing':'saved',message:conflicts?'Journal conservé ; '+conflicts+' commande(s) refusée(s) à examiner.':remaining?'Nouvelles modifications en attente.':'Journal et reçus métier conservés sur la tour. Les STL ont une sauvegarde séparée.',pending:remaining,lastSavedAt:Date.now(),durable:true,conflicts,available:true});
      }catch(error){fail(error);}finally{flight=null;defer(status.pending?750:5000);}
      return clone(status);
    })();return flight;
  }
  function changed(){if(merging||stopped)return;if(enabled){update({mode:'syncing',message:'Modifications provisoires en attente de décision de la tour.',pending:countPending(),durable:false});defer(250);}else update({mode:status.mode==='conflict'?'conflict':storageMode(store),message:status.mode==='conflict'?status.message:initialMessage(store),durable:false,pending:0});}
  store.addEventListener('change',changed);
  function stop(){stopped=true;enabled=false;clearTimeout(timer);for(const controller of controllers)controller.abort();store.removeEventListener('change',changed);}
  return {get status(){return clone(status);},inspect,connect,sync,stop};
}
