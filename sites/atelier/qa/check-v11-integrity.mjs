import assert from 'node:assert/strict';
import {mkdtemp,rm,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';
import {WorkshopStore,canonicalWorkshopJSON} from '../dist/lib/workshop.js';
import {createWorkshopBackup} from '../dist/lib/workshop-backup.js';
import {createWorkshopRepository} from '../local/workshop-repository.mjs';
import {createWorkshopAssetRepository} from '../local/workshop-assets.mjs';
import {createWorkshopAssetClient} from '../dist/lib/workshop-assets.js';

const SEED='bojart.workshop.v1.seed',OP='bojart.workshop.v1.op.',AUTH='bojart.workshop.v1.authority.v2';
class Storage {
  constructor(entries=[]){this.data=new Map(entries);this.failWrites=false;this.failReads=false;}
  get length(){if(this.failReads)throw new Error('Lecture du stockage interrompue');return this.data.size;}
  key(index){return [...this.data.keys()][index]??null;}
  getItem(key){if(this.failReads)throw new Error('Lecture du stockage interrompue');return this.data.get(key)??null;}
  setItem(key,value){if(this.failWrites)throw new Error('Quota atteint');this.data.set(key,String(value));}
}
const checks=[],stores=new Set(),repositories=new Set(),originalStorage=globalThis.localStorage;
const root=await mkdtemp(join(tmpdir(),'boj-v11-integrity-'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const snapshot=storage=>JSON.stringify([...storage.data]);
const check=async(name,run)=>{await run();checks.push(name);};
function open(storage=new Storage()) {globalThis.localStorage=storage;const store=new WorkshopStore();stores.add(store);return store;}
function fixture(){const storage=new Storage(),store=open(storage);assert.equal(store.dispatch('ADD_PROJECT',{name:'Dossier QA à préserver',height:125,notes:'Synthèse technique QA'}).ok,true);return{storage,store,projectId:store.state.projectId,opKey:[...storage.data.keys()].find(key=>key.startsWith(OP))};}
function assertBlocked(store,storage,before){
  assert.ok(store.integrityError);assert.equal(store.authorityError,store.integrityError);
  assert.equal(store.dispatch('LOG',{message:'Ajout bloqué'}).ok,false);
  assert.throws(()=>store.exportJournal());
  assert.throws(()=>store.mergeJournal({version:1,seed:{version:1,at:1700000000000},operations:[]}));
  assert.equal(snapshot(storage),before);
}
try {
  await check('Opération JSON corrompue au redémarrage : aucun dossier fictif, aucune réécriture, actions et fusion bloquées',()=>{
    const f=fixture();f.storage.setItem(f.opKey,'{ broken json');const before=snapshot(f.storage),reopened=open(f.storage);
    assert.equal(reopened.state.projects.length,0);assert.equal(reopened.getProject(),null);assertBlocked(reopened,f.storage,before);
  });
  await check('Origine invalide ou supprimée avec historique : refus sans nouvelle graine',()=>{
    for(const value of ['{ broken json','null',JSON.stringify({version:99,at:1}),undefined]){
      const f=fixture();if(value===undefined)f.storage.data.delete(SEED);else f.storage.setItem(SEED,value);
      const before=snapshot(f.storage),reopened=open(f.storage);assertBlocked(reopened,f.storage,before);assert.equal(reopened.state.projects.length,0);
    }
  });
  await check('Origine illisible sans opérations : elle demeure intacte au premier chargement',()=>{
    const storage=new Storage([[SEED,'{ broken origin']]),before=snapshot(storage),store=open(storage);assertBlocked(store,storage,before);assert.equal(store.state.projects.length,0);
  });
  await check('Une enveloppe valide en JSON mais hors contrat ou sous une mauvaise clé est bloquée',()=>{
    for(const change of [op=>{op.type='EXECUTE_SHELL';},op=>{op.id='different-id';},op=>{op.extra='unknown';},op=>{op.payload.height=-1;}]){
      const f=fixture(),operation=JSON.parse(f.storage.getItem(f.opKey));change(operation);f.storage.setItem(f.opKey,JSON.stringify(operation));
      const before=snapshot(f.storage),store=open(f.storage);assertBlocked(store,f.storage,before);
    }
  });
  await check('Corruption en session : dernier dossier lisible conservé et copie brute exacte sans autres données locales',()=>{
    const f=fixture(),lastGood=canonicalWorkshopJSON(f.store.state),oldOperation=f.storage.getItem(f.opKey);
    f.storage.setItem('unrelated.application','not part of the workshop');f.storage.setItem(f.opKey,'{ corrupt preserved bytes');f.store.refresh();
    assert.equal(canonicalWorkshopJSON(f.store.state),lastGood);
    const before=snapshot(f.storage),copy=f.store.recoverRawStorage();assert.equal(copy.format,'bojart.workshop.recovery.v1');assert.equal(copy.entries.find(entry=>entry.key===f.opKey).value,'{ corrupt preserved bytes');assert.equal(copy.entries.some(entry=>entry.key==='unrelated.application'),false);
    assert.equal(canonicalWorkshopJSON(copy.lastValidatedJournal.operations[0]),canonicalWorkshopJSON(JSON.parse(oldOperation)));assert.equal(snapshot(f.storage),before);assertBlocked(f.store,f.storage,before);
  });
  await check('Réexamen explicite après restauration des octets : état retrouvé, nouvelle opération possible',()=>{
    const f=fixture(),old=f.storage.getItem(f.opKey);f.storage.setItem(f.opKey,'{ invalid');assert.equal(f.store.recheckIntegrity().ok,false);
    f.storage.setItem(f.opKey,old);const result=f.store.recheckIntegrity();assert.equal(result.ok,true);assert.equal(result.retainedState,true);assert.equal(f.store.integrityError,null);assert.equal(f.store.state.projectId,f.projectId);assert.equal(f.store.dispatch('LOG',{message:'Après récupération QA'}).ok,true);
  });
  await check('Disparition ou substitution valide d’une opération déjà lue : aucun retour en arrière silencieux',()=>{
    for(const mode of ['remove','replace']){
      const f=fixture(),lastGood=canonicalWorkshopJSON(f.store.state),old=f.storage.getItem(f.opKey);
      if(mode==='remove')f.storage.data.delete(f.opKey);else{const operation=JSON.parse(old);operation.payload.notes='Texte substitué';f.storage.setItem(f.opKey,JSON.stringify(operation));}
      f.store.refresh();assert.equal(canonicalWorkshopJSON(f.store.state),lastGood);assert.ok(f.store.integrityError);f.storage.setItem(f.opKey,old);assert.equal(f.store.recheckIntegrity().ok,true);
    }
  });
  await check('Panne de lecture du navigateur : état préservé puis réexamen réussi',()=>{
    const f=fixture(),lastGood=canonicalWorkshopJSON(f.store.state);f.storage.failReads=true;f.store.refresh();assert.ok(f.store.integrityError);assert.equal(canonicalWorkshopJSON(f.store.state),lastGood);f.storage.failReads=false;assert.equal(f.store.recheckIntegrity().ok,true);
  });
  await check('Quota d’écriture : opération volatile conservée et exportable, sans confusion avec une corruption',()=>{
    const f=fixture();f.storage.failWrites=true;const result=f.store.dispatch('UPDATE_PROJECT',{id:f.projectId,patch:{notes:'Note conservée dans cette fenêtre'}});assert.equal(result.ok,true);assert.equal(result.persisted,false);assert.equal(f.store.integrityError,null);assert.equal(f.store.getProject().notes,'Note conservée dans cette fenêtre');assert.equal(f.store.recoverRawStorage().volatileOperations.length,1);
  });
  await check('Nouveau stockage intégralement non inscriptible : démonstration explicitement volatile encore utilisable',()=>{
    const storage=new Storage();storage.failWrites=true;const store=open(storage);assert.equal(store.persistent,false);assert.equal(store.integrityError,null);assert.equal(store.dispatch('LOG',{message:'Volatile QA'}).ok,true);assert.equal(storage.data.size,0);assert.equal(store.recoverRawStorage().volatileOperations.length,1);
  });
  await check('Reçus absents ou invalides et genèse manquante : état confirmé préservé, aucune autorité substituée',async()=>{
    for(const mode of ['missing','corrupt','genesis','prefix']){
      const f=fixture(),repo=createWorkshopRepository({directory:join(root,'authority-'+mode)});repositories.add(repo);repo.restore(await createWorkshopBackup(f.store.exportJournal()));const backup=repo.backup();f.store.mergeJournal({version:2,seed:backup.seed,operations:backup.operations,authority:backup.authority});
      const lastGood=canonicalWorkshopJSON(f.store.state),old=f.storage.getItem(AUTH);
      if(mode==='missing')f.storage.data.delete(AUTH);else if(mode==='corrupt')f.storage.setItem(AUTH,'{ invalid receipt');else{const authority=JSON.parse(old);if(mode==='genesis')delete authority.genesis;else authority.receipts=[];f.storage.setItem(AUTH,JSON.stringify(authority));}
      const before=snapshot(f.storage);f.store.refresh();assert.equal(canonicalWorkshopJSON(f.store.state),lastGood);assertBlocked(f.store,f.storage,before);f.storage.setItem(AUTH,old);assert.equal(f.store.recheckIntegrity().ok,true);
    }
  });
  await check('Échec d’écriture du nouveau reçu : les reçus déjà persistés restent valides et le nouveau reçu demeure en mémoire',async()=>{
    const f=fixture(),repo=createWorkshopRepository({directory:join(root,'authority-quota')});repositories.add(repo);repo.restore(await createWorkshopBackup(f.store.exportJournal()));let backup=repo.backup();f.store.mergeJournal({version:2,seed:backup.seed,operations:backup.operations,authority:backup.authority});
    const result=f.store.dispatch('UPDATE_PROJECT',{id:f.projectId,patch:{notes:'Nouvelle note QA'}});const operation=f.store.exportJournal().operations.find(item=>item.id===result.operationId);repo.append({version:2,workspaceId:backup.authority.workspaceId,seed:backup.seed,operations:[operation]});backup=repo.backup();f.storage.failWrites=true;
    const merged=f.store.mergeJournal({version:2,seed:backup.seed,operations:backup.operations,authority:backup.authority});assert.equal(merged.ok,true);assert.equal(merged.persisted,false);assert.equal(f.store.integrityError,null);assert.equal(f.store.exportJournal().authority.receipts.length,2);
  });
  await check('Deux écrans sur le même stockage restent compatibles avec les opérations ajoutées',()=>{
    const f=fixture(),other=open(f.storage);assert.equal(other.dispatch('UPDATE_PROJECT',{id:f.projectId,patch:{notes:'Ajout légitime autre écran'}}).ok,true);assert.equal(f.store.recheckIntegrity().ok,true);assert.equal(f.store.getProject().notes,'Ajout légitime autre écran');
  });
  await check('Coffre : les octets sont capturés avant écriture ; mutation du tampon appelant sans effet sur le fichier confirmé',async()=>{
    for(const mode of ['arraybuffer','view']){
      const repo=createWorkshopAssetRepository({directory:join(root,'vault-'+mode)});repositories.add(repo);const bytes=new Uint8Array(134);bytes[80]=1;const original=Buffer.from(bytes),buffer=mode==='arraybuffer'?bytes.buffer:bytes,hash=sha(original);
      const pending=repo.put({id:'file',name:'original.stl',buffer,sha256:hash,createdAt:1});bytes[84]=99;const receipt=await pending,stored=await repo.get('file');assert.equal(receipt.ok,true);assert.equal(stored.sha256,hash);assert.deepEqual(stored.buffer,original);assert.deepEqual((await repo.put({id:'file',name:'original.stl',buffer:original,sha256:hash,createdAt:1})).duplicates,['file']);
    }
  });
  await check('Client coffre : fichier et manifeste capturés avant SHA, y compris une vue partielle de tampon',async()=>{
    const all=new Uint8Array(200);all.fill(7);const bytes=new Uint8Array(all.buffer,12,134),original=Buffer.from(bytes),hash=sha(original),record={id:'expected-file',name:'original.stl',createdAt:1,buffer:bytes,sha256:hash};let request;
    const client=createWorkshopAssetClient({fetchImpl:async(url,options)=>{request={url,options};return new Response(JSON.stringify({ok:true,asset:{id:'expected-file',name:'original.stl',createdAt:1,sha256:hash,byteLength:134,format:'stl'}}));}});
    const pending=client.putAsset(record);all.fill(99);record.id='replacement';record.name='changed.stl';record.createdAt=99;record.sha256='0'.repeat(64);
    const receipt=await pending;assert.equal(receipt.id,'expected-file');assert.equal(request.url,'/api/workshop/assets/expected-file');assert.deepEqual(Buffer.from(request.options.body),original);assert.equal(request.options.headers['X-BOJ-SHA256'],hash);assert.equal(request.options.headers['X-BOJ-File-Name'],'original.stl');assert.equal(request.options.headers['X-BOJ-Created-At'],'1');
  });
  await check('Client coffre sans date fournie : reprise après reçu perdu et nouvelle instance sans conflit de manifeste',async()=>{
    let now=1700000000000,lost=true;const repo=createWorkshopAssetRepository({directory:join(root,'vault-retry'),now:()=>now++});repositories.add(repo);
    const transport=async(url,{body,headers})=>{
      assert.equal(Object.hasOwn(headers,'X-BOJ-Created-At'),false);
      const result=await repo.put({id:url.split('/').at(-1),name:decodeURIComponent(headers['X-BOJ-File-Name']),buffer:body,sha256:headers['X-BOJ-SHA256']});
      if(lost){lost=false;throw new Error('Réponse perdue après conservation');}
      return new Response(JSON.stringify(result));
    };
    const record={id:'retry-file',name:'stable.stl',buffer:new Uint8Array([1,2,3]).buffer};
    await assert.rejects(()=>createWorkshopAssetClient({fetchImpl:transport}).putAsset(record),/perdue/);
    const stored=await repo.get('retry-file'),retried=await createWorkshopAssetClient({fetchImpl:transport}).putAsset(record);assert.equal(retried.createdAt,stored.createdAt);assert.equal(retried.sha256,stored.sha256);assert.equal(repo.status().fileCount,1);assert.equal(now,1700000000001);
  });
  const result={ok:true,node:process.version,checks,checksCount:checks.length,scope:'Pure browser-storage model plus real temporary SQLite and STL files; no browser, listener, machine or account.',physicalCommands:0,listenersStarted:0};
  await writeFile(new URL('./v11-integrity-results.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
} finally {for(const store of stores)store.dispose();for(const repo of repositories)repo.close();globalThis.localStorage=originalStorage;await rm(root,{recursive:true,force:true});}
