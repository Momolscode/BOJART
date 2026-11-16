import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {WorkshopStore,calculateQuote} from '../dist/lib/workshop.js';
import {runProjectPreparation} from '../dist/lib/orchestrator.js';

// Real store and reducer, isolated storage; no browser, network or hardware.
class Storage {
  entries=new Map();
  get length(){return this.entries.size;}
  key(i){return [...this.entries.keys()][i]??null;}
  getItem(key){return this.entries.get(key)??null;}
  setItem(key,value){this.entries.set(key,String(value));}
}
const fixtures=new Set(),checks=[];
function fresh(){
  const storage=new Storage();globalThis.localStorage=storage;
  const store=new WorkshopStore(),calls=[],dispatch=store.dispatch.bind(store);
  store.dispatch=(type,payload={})=>{calls.push({type,payload:structuredClone(payload)});return dispatch(type,payload);};
  fixtures.add(store);return {store,storage,calls};
}
function act(store,type,payload){const result=store.dispatch(type,payload);assert.equal(result.ok,true,result.message);return result;}
const project=(store,id)=>store.state.projects.find(p=>p.id===id);
const result=(outcome,id)=>outcome.results.find(r=>r.id===id);
const jobs=(store,id)=>store.state.jobs.filter(j=>j.projectId===id);
function check(id,label,fn){
  try{fn();checks.push({id,label,status:'passed'});console.log('PASS '+label);}
  catch(error){checks.push({id,label,status:'failed',error:{name:error.name,message:error.message}});console.log('FAIL '+label+' — '+error.message);}
  finally{fixtures.forEach(store=>store.dispose());fixtures.clear();}
}

check('unknown-project','Projet inconnu : aucun état, journal, événement ou stockage modifié',()=>{
  const {store,storage,calls}=fresh(),before=structuredClone(store.state),saved=[...storage.entries];let changes=0;
  store.addEventListener('change',()=>changes++);
  assert.throws(()=>runProjectPreparation(store,'absent'),RangeError);
  assert.throws(()=>runProjectPreparation(store,null),TypeError);
  assert.deepEqual(store.state,before);assert.deepEqual([...storage.entries],saved);assert.equal(changes,0);assert.equal(calls.length,0);
});

check('exact-project','Projet hors sélection : mutations, export et journal ciblent le projet demandé',()=>{
  const {store}=fresh(),before=structuredClone(store.state),outcome=runProjectPreparation(store,'prototype');
  assert.equal(store.state.projectId,'sculpture-xl');assert.equal(store.state.selectedPieceId,'buste');
  assert.equal(outcome.projectId,'prototype');assert.equal(outcome.mission.scope.projectId,'prototype');
  assert.ok(outcome.mission.jobs.every(j=>j.projectId==='prototype'));
  for(const old of before.projects.filter(p=>p.id!=='prototype'))assert.deepEqual(project(store,old.id),old);
  for(const old of before.jobs.filter(j=>j.projectId!=='prototype'))assert.deepEqual(store.state.jobs.find(j=>j.id===old.id),old);
  const journal=store.state.journal.find(j=>j.type==='LOG'&&j.message.includes('orchestration de PROTOTYPE'));
  assert.ok(journal,'Le récapitulatif de la préparation doit figurer au journal.');
  assert.equal(journal.projectId,'prototype','Le journal doit porter la cible de la mission, pas le projet sélectionné.');
  assert.ok(journal.pieceId===null||project(store,'prototype').pieces.some(p=>p.id===journal.pieceId),'La pièce du journal ne doit pas appartenir à un autre projet.');
});

check('repeat','Répétition : aucun doublon de travail ni remplacement du scénario',()=>{
  const {store,calls}=fresh();runProjectPreparation(store,'sculpture-xl');
  const firstJobs=structuredClone(store.state.jobs),story=project(store,'sculpture-xl').story;
  assert.ok(story.includes('BOJ.ART'));calls.length=0;
  const second=runProjectPreparation(store,'sculpture-xl');runProjectPreparation(store,'sculpture-xl');
  assert.deepEqual(store.state.jobs,firstJobs);assert.equal(new Set(store.state.jobs.map(j=>j.id)).size,store.state.jobs.length);
  assert.equal(project(store,'sculpture-xl').story,story);assert.equal(result(second,'story').status,'preserved');
  assert.equal(calls.filter(c=>c.type==='SAVE_STORY').length,0);
});

check('existing-story','Scénario existant : conservation exacte du contenu utilisateur',()=>{
  const {store,calls}=fresh(),text='BOJ.ART — prise validée\nConserver cette phrase et ce rythme.\nPlan final : logo original.';
  act(store,'SAVE_STORY',{projectId:'commande-art',text});calls.length=0;
  const outcome=runProjectPreparation(store,'commande-art');
  assert.equal(project(store,'commande-art').story,text);assert.equal(result(outcome,'story').status,'preserved');
  assert.equal(calls.filter(c=>c.type==='SAVE_STORY').length,0);
});

check('missing-quote','Devis absent : aucun coût, prix ni saisie inventés',()=>{
  const {store,calls}=fresh();const outcome=runProjectPreparation(store,'prototype');
  assert.equal(project(store,'prototype').quote,null);assert.equal(result(outcome,'quote').status,'needs_input');
  assert.equal(calls.filter(c=>c.type==='SAVE_QUOTE').length,0);
});

check('known-quote','Devis renseigné : recalcul réel, convention du lot et quantité conservées',()=>{
  const {store,calls}=fresh(),inputs={material:100,hours:4,rate:40,other:40,margin:30,fee:3,quantity:2};
  act(store,'SAVE_QUOTE',{projectId:'prototype',inputs});calls.length=0;
  const outcome=runProjectPreparation(store,'prototype'),quote=project(store,'prototype').quote;
  assert.equal(result(outcome,'quote').status,'performed');assert.deepEqual(quote.result,calculateQuote(inputs));
  assert.equal(quote.cost,300);assert.equal(quote.unitPrice,quote.price/2);assert.deepEqual(quote.inputs,inputs);
  const writes=calls.filter(c=>c.type==='SAVE_QUOTE');assert.equal(writes.length,1);assert.equal(writes[0].payload.projectId,'prototype');
});

check('external-limits','Limites externes : aucune machine démarrée et aucune capacité raccordée',()=>{
  const {store,calls}=fresh(),before=structuredClone(store.state),outcome=runProjectPreparation(store,'sculpture-xl');
  assert.ok(calls.every(c=>['PLAN_PROJECT','SAVE_QUOTE','SAVE_STORY','LOG'].includes(c.type)));
  for(const old of before.jobs)assert.deepEqual(store.state.jobs.find(j=>j.id===old.id),old);
  for(const added of store.state.jobs.filter(j=>!before.jobs.some(old=>old.id===j.id))){assert.equal(added.status,'queued');assert.equal(added.startedAt,null);assert.equal(added.simulated,true);}
  assert.deepEqual(store.state.machines,before.machines);assert.equal(result(outcome,'external').status,'unconnected');
  for(const key of ['canSlice','canStartPhysicalPrint','canPublish','canExecuteRobot'])assert.equal(outcome.mission.readiness[key],false);
  assert.ok(outcome.mission.steps.filter(s=>s.mode==='unconnected').every(s=>s.status==='not_connected'&&s.futureEndpoint.implemented===false));
});

check('changed-lot','Lot modifié : instantanés préservés, désaccord signalé et devis invalidé',()=>{
  const {store}=fresh();runProjectPreparation(store,'sculpture-xl');
  act(store,'SAVE_QUOTE',{projectId:'sculpture-xl',inputs:{material:100,hours:1,rate:20,other:0,margin:20,quantity:1}});
  const before=structuredClone(jobs(store,'sculpture-xl'));
  act(store,'UPDATE_PROJECT',{id:'sculpture-xl',patch:{quantity:3}});
  const outcome=runProjectPreparation(store,'sculpture-xl');
  assert.deepEqual(jobs(store,'sculpture-xl'),before);assert.equal(project(store,'sculpture-xl').quote,null);
  assert.equal(result(outcome,'quote').status,'needs_input');assert.match(result(outcome,'simulation').detail,/quantité différente/);
  assert.equal(outcome.mission.steps.find(s=>s.id==='simulation').evidence.differentLots.length,6);
  assert.equal(result(outcome,'simulation').status,'needs_input','Un lot sans travaux correspondants demande une nouvelle préparation.');
});

check('incompatible-pieces','Pièces incompatibles : répartition signalée comme nécessitant une entrée',()=>{
  const {store}=fresh();const added=act(store,'ADD_PROJECT',{name:'Pièce hors volume',kind:'prototype',quantity:1,height:1200});
  act(store,'UPDATE_PIECE',{projectId:added.projectId,id:'hors-volume',patch:{name:'Pièce hors volume',tech:'fdm',dims:[9999,9999,9999]}});
  const outcome=runProjectPreparation(store,added.projectId);
  assert.equal(jobs(store,added.projectId).length,0);assert.equal(outcome.mission.readiness.compatibleEnvelopes,0);
  assert.equal(result(outcome,'simulation').status,'needs_input','Zéro pièce affectable ne doit pas apparaître comme une répartition effectuée.');
});

check('changed-revision','Nouvelle révision : un nouveau travail, ancien instantané intact',()=>{
  const {store}=fresh();runProjectPreparation(store,'sculpture-xl');
  const before=structuredClone(jobs(store,'sculpture-xl')),old=before.find(j=>j.pieceId==='buste');
  act(store,'UPDATE_PIECE',{projectId:'sculpture-xl',id:'buste',patch:{dims:[172,110,230],assetId:'asset-revision-test'}});
  const outcome=runProjectPreparation(store,'sculpture-xl'),piece=project(store,'sculpture-xl').pieces.find(p=>p.id==='buste');
  assert.equal(piece.revision,2);assert.equal(jobs(store,'sculpture-xl').length,before.length+1);
  assert.deepEqual(store.state.jobs.find(j=>j.id===old.id),old);
  const added=jobs(store,'sculpture-xl').filter(j=>j.pieceId==='buste'&&j.revision===2);assert.equal(added.length,1);assert.equal(added[0].status,'queued');assert.deepEqual(added[0].dims,[172,110,230]);
  assert.equal(outcome.projectRevision,project(store,'sculpture-xl').revision);assert.equal(outcome.mission.projectRevision,outcome.projectRevision);
  runProjectPreparation(store,'sculpture-xl');assert.equal(jobs(store,'sculpture-xl').length,before.length+1);
});

check('empty-project','Dossier sans pièce : aucune file créée, besoins exprimés',()=>{
  const {store,calls}=fresh();const added=act(store,'ADD_PROJECT',{name:'Prototype sans fichier',kind:'prototype',quantity:1,height:100,notes:''});
  const before=structuredClone(store.state.jobs);calls.length=0;
  const outcome=runProjectPreparation(store,added.projectId);
  assert.deepEqual(store.state.jobs,before);assert.equal(result(outcome,'simulation').status,'needs_input');assert.equal(result(outcome,'quote').status,'needs_input');
  assert.equal(calls.filter(c=>c.type==='PLAN_PROJECT').length,0);assert.equal(project(store,added.projectId).quote,null);
  assert.equal(outcome.mission.readiness.canStartPhysicalPrint,false);
});

const failed=checks.filter(c=>c.status==='failed').length;
const sources=Object.fromEntries(['orchestrator','workshop','control-plane'].map(name=>{
  const data=fs.readFileSync(new URL('../dist/lib/'+name+'.js',import.meta.url));
  return ['dist/lib/'+name+'.js',createHash('sha256').update(data).digest('hex')];
}));
const report={format:'bojart.orchestration-qa.v1',checkedAt:new Date().toISOString(),runtime:process.version,
  scope:'Real WorkshopStore and orchestrator with isolated in-memory localStorage; no browser or external calls.',
  sources,summary:{total:checks.length,passed:checks.length-failed,failed},checks};
const output=new URL('./orchestration-results.json',import.meta.url);fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report.summary));console.log(fileURLToPath(output));
process.exitCode=failed?1:0;
