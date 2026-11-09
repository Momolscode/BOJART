import assert from 'node:assert/strict';
import {EDIT_SERIES,EDIT_FORMATS,EDIT_BEATS,EDIT_LIMITS,createEditDraft,normalizeEditPlan,latestEditVersion,projectEditPlans,exportEditPlan} from '../dist/lib/edit-plan.js';
import {CONTENT_CATALOG,getContentSource} from '../dist/lib/content-catalog.js';
import {WorkshopStore,validateWorkshopOperation,replayWorkshopOperations} from '../dist/lib/workshop.js';

// Business validation and bounded histories. No browser, server, render or media upload.
const checks=[];
const check=(name,run)=>{run();checks.push(name);};
const copy=value=>structuredClone(value);
const seed={version:1,at:Date.UTC(2026,9,18,12)};
const project={id:'sculpture-xl',name:'Dossier à préparer',revision:1,notes:'Les notes de fabrication restent distinctes.',story:'Le scénario conservé devient le brief du prochain édit.'};
const video=CONTENT_CATALOG.find(post=>post.id==='7467517355535404310');
const photo=CONTENT_CATALOG.find(post=>post.type==='image');
const missing=CONTENT_CATALOG.find(post=>!post.available);
const draft=()=>createEditDraft(project);
function sourced(post=video){const plan=draft();plan.sources=[{postId:post.id,relation:'reference'}];plan.beats[0]={...plan.beats[0],postId:post.id,in:null,out:null};return plan;}
function operation(id,plan=draft(),expectedRevision=0,clock=1,planId='edit-qa',expectedVersionId=null){
  return {version:1,id,clock,at:seed.at+clock,type:'SAVE_EDIT_PLAN',payload:{projectId:project.id,planId,expectedRevision,expectedVersionId,plan},expected:{},context:{projectId:project.id,projectName:project.name,pieceId:null,machineId:null,originProjectId:project.id}};
}
function rejectsPlan(change){const plan=draft();change(plan);assert.throws(()=>normalizeEditPlan(plan));}

check('Brouillons des cinq séries : copie du scénario, aucune source supposée',()=>{
  assert.equal(EDIT_SERIES.length,5);assert.deepEqual(EDIT_FORMATS,['9:16','1:1','16:9']);
  assert.deepEqual(EDIT_BEATS.map(beat=>beat.id),['detail','geste','oeuvre','signature']);
  for(const series of EDIT_SERIES){const plan=createEditDraft(project,series.id);assert.equal(plan.series,series.id);assert.equal(plan.brief,project.story);assert.deepEqual(plan.sources,[]);assert.ok(plan.beats.every(beat=>beat.postId===null&&beat.in===null&&beat.out===null));}
  const plan=draft();project.story='Scénario modifié plus tard.';assert.equal(plan.brief,'Le scénario conservé devient le brief du prochain édit.');
  assert.equal(createEditDraft({...project,story:'  '}).brief,project.notes);
  assert.equal(createEditDraft({...project,story:'S'.repeat(6000)}).brief.length,EDIT_LIMITS.brief);
  assert.deepEqual(projectEditPlans(project),[]);assert.equal(latestEditVersion(null),null);
});

check('Plages originales, photographies et indisponibilités explicites',()=>{
  const plan=sourced();plan.beats[0].in=24;plan.beats[0].out=26.2;
  const normalized=normalizeEditPlan(plan);assert.equal(normalized.beats[0].in,24);assert.ok(24>video.previewStart+video.previewSeconds);
  plan.sources[0].relation='project';assert.equal(normalizeEditPlan(plan).sources[0].relation,'project');
  assert.equal(normalizeEditPlan(sourced(photo)).beats[0].in,null);
  assert.equal(normalizeEditPlan(sourced(missing)).sources[0].postId,missing.id);
  assert.equal(getContentSource(missing.id).duration,null);
  const reordered=draft();reordered.beats.reverse();assert.deepEqual(normalizeEditPlan(reordered).beats.map(beat=>beat.id),EDIT_BEATS.map(beat=>beat.id));
});

check('Catalogue, relation et quatre moments strictement validés',()=>{
  rejectsPlan(plan=>plan.sources=[{postId:'9999999999999999999',relation:'reference'}]);
  rejectsPlan(plan=>plan.sources=[{postId:Number(video.id),relation:'reference'}]);
  rejectsPlan(plan=>plan.sources=[{postId:video.id,relation:'verified_project'}]);
  rejectsPlan(plan=>plan.sources=[{postId:video.id,relation:'reference'},{postId:video.id,relation:'project'}]);
  rejectsPlan(plan=>plan.beats[0].postId=video.id);
  rejectsPlan(plan=>plan.beats.pop());
  rejectsPlan(plan=>plan.beats[1].id='detail');
  rejectsPlan(plan=>plan.beats[0].id='render');
  rejectsPlan(plan=>plan.sources=new Array(2));
  rejectsPlan(plan=>plan.sources=Array.from({length:EDIT_LIMITS.sources+1},()=>({postId:video.id,relation:'reference'})));
  rejectsPlan(plan=>plan.sources=[{postId:video.id,relation:'reference',available:true}]);
  rejectsPlan(plan=>plan.beats[0].generated=true);
});

check('Durées : pas de coercition, de plage partielle ni de dépassement du média',()=>{
  for(const duration of [9,61,10.2,'23',NaN,Infinity,null])rejectsPlan(plan=>plan.duration=duration);
  for(const [start,end] of [[null,1],[0,null],[-1,1],[1,1],[2,1],[0,video.duration+0.01],['0',1],[0,'1'],[NaN,1],[0,Infinity]]){
    const plan=sourced();plan.beats[0].in=start;plan.beats[0].out=end;assert.throws(()=>normalizeEditPlan(plan));
  }
  for(const post of [photo,missing]){const plan=sourced(post);plan.beats[0].in=0;plan.beats[0].out=1;assert.throws(()=>normalizeEditPlan(plan));}
  rejectsPlan(plan=>{plan.beats[0].in=0;plan.beats[0].out=1;});
  const edge=sourced();edge.beats[0].in=0;edge.beats[0].out=video.duration;assert.equal(normalizeEditPlan(edge).beats[0].out,video.duration);
});

check('Textes, octets et champs exécutables bornés avant sérialisation',()=>{
  for(const [field,max] of [['title',EDIT_LIMITS.title],['brief',EDIT_LIMITS.brief],['caption',EDIT_LIMITS.caption],['audioNotes',EDIT_LIMITS.audioNotes]])rejectsPlan(plan=>plan[field]='A'.repeat(max+1));
  rejectsPlan(plan=>plan.beats[0].note='A'.repeat(EDIT_LIMITS.beatNote+1));
  rejectsPlan(plan=>plan.title='  ');rejectsPlan(plan=>plan.status='published');rejectsPlan(plan=>plan.series='all');rejectsPlan(plan=>plan.format='4:3');
  rejectsPlan(plan=>plan.renderRequested=true);rejectsPlan(plan=>Object.defineProperty(plan,'caption',{get(){throw new Error('Accesseur exécuté');},enumerable:true}));
  rejectsPlan(plan=>plan.caption=()=>{});
  const heavy=draft();heavy.brief='漢'.repeat(4000);heavy.caption='漢'.repeat(2200);heavy.audioNotes='漢'.repeat(2000);heavy.beats.forEach(beat=>beat.note='漢'.repeat(1000));assert.throws(()=>normalizeEditPlan(heavy),/32 Kio/);
  const original=draft(),clean=normalizeEditPlan(original);clean.beats[0].note='Copie modifiée';assert.notEqual(original.beats[0].note,clean.beats[0].note);
});

check('Cible et révision attendue strictes dans le contrat de journal',()=>{
  const clean=validateWorkshopOperation(operation('valid'));assert.equal(clean.payload.plan.title,draft().title);
  for(const value of ['0',-1,0.1,NaN,EDIT_LIMITS.versions+1]){const op=operation('bad-revision');op.payload.expectedRevision=value;assert.throws(()=>validateWorkshopOperation(op));}
  const wrong=operation('wrong-project');wrong.context.projectId='prototype';assert.throws(()=>validateWorkshopOperation(wrong),/contexte/);
  const invalidId=operation('bad-id');invalidId.payload.planId='../plan';assert.throws(()=>validateWorkshopOperation(invalidId),/Identifiant de plan/);
  const unknown=operation('unknown-field');unknown.payload.currentProject='prototype';assert.throws(()=>validateWorkshopOperation(unknown));
  const missingRevision=operation('missing-revision');delete missingRevision.payload.expectedRevision;assert.throws(()=>validateWorkshopOperation(missingRevision));
  const missingVersionId=operation('missing-version-id');delete missingVersionId.payload.expectedVersionId;assert.throws(()=>validateWorkshopOperation(missingVersionId));
  const creationIdentity=operation('creation-identity');creationIdentity.payload.expectedVersionId='another-operation';assert.throws(()=>validateWorkshopOperation(creationIdentity));
  const updateWithoutIdentity=operation('update-without-identity',draft(),1);assert.throws(()=>validateWorkshopOperation(updateWithoutIdentity));
  const updateIdentity=operation('update-identity',draft(),1,2,'edit-qa','valid-base');assert.equal(validateWorkshopOperation(updateIdentity).payload.expectedVersionId,'valid-base');
  updateIdentity.payload.expectedVersionId='../base';assert.throws(()=>validateWorkshopOperation(updateIdentity));
});

check('Limite de plans : vingt historiques conservés, suivant refusé sans purge',()=>{
  const operations=Array.from({length:EDIT_LIMITS.plans+1},(_,index)=>operation('plan-limit-'+String(index).padStart(2,'0'),draft(),0,index+1,'edit-plan-'+index));
  const result=replayWorkshopOperations(seed,operations),target=result.state.projects.find(item=>item.id===project.id);
  assert.equal(target.contentPlans.length,EDIT_LIMITS.plans);assert.equal(result.results.get(operations.at(-1).id).ok,false);
  assert.equal(target.contentPlans[0].versions.length,1);assert.equal(target.revision,1);assert.equal(target.story,'');assert.equal(target.quote,null);
});

check('Limite de versions : cinquante snapshots append-only, suivant refusé',()=>{
  const operations=Array.from({length:EDIT_LIMITS.versions+1},(_,index)=>operation('version-limit-'+String(index).padStart(2,'0'),{...draft(),caption:'Version '+(index+1)},index,index+1,'edit-qa',index?'version-limit-'+String(index-1).padStart(2,'0'):null));
  const result=replayWorkshopOperations(seed,operations),target=result.state.projects.find(item=>item.id===project.id),record=target.contentPlans[0];
  assert.equal(record.versions.length,EDIT_LIMITS.versions);assert.equal(result.results.get(operations.at(-1).id).ok,false);assert.equal(record.versions[0].plan.caption,'Version 1');assert.equal(record.versions.at(-1).plan.caption,'Version 50');
  const copied=projectEditPlans(target);copied[0].versions[0].plan.caption='Autre texte';assert.equal(record.versions[0].plan.caption,'Version 1');
  const exported=exportEditPlan(target,record,1);assert.equal(exported.version.revision,1);assert.equal(exported.version.operationId,operations[0].id);assert.equal(exported.plan.caption,'Version 1');assert.equal(exported.execution.renderRequested,false);assert.ok(Object.isFrozen(exported.plan.beats[0]));
  const foreign=copy(record.versions[0]);foreign.operationId='foreign-operation';assert.throws(()=>exportEditPlan(target,record,foreign),/autre état/);
  const oldShape=copy(record);delete oldShape.versions.at(-1).operationId;assert.throws(()=>latestEditVersion(oldShape),/operationId/);
});

check('Dispatch et reprise navigateur : NaN refusé avant clonage, opérations mal formées sans mutation',()=>{
  const previous=Object.getOwnPropertyDescriptor(globalThis,'localStorage');
  const entries=new Map([['bojart.workshop.v1.seed',JSON.stringify(seed)]]);
  const storage={get length(){return entries.size;},key(index){return [...entries.keys()][index]??null;},getItem(key){return entries.get(key)??null;},setItem(key,value){entries.set(key,String(value));}};
  Object.defineProperty(globalThis,'localStorage',{value:storage,configurable:true});
  let store;
  try{
    store=new WorkshopStore();const broken=sourced();broken.beats[0].in=NaN;broken.beats[0].out=null;
    const refused=store.dispatch('SAVE_EDIT_PLAN',{projectId:project.id,planId:'edit-nan',expectedRevision:0,expectedVersionId:null,plan:broken});assert.equal(refused.ok,false);assert.equal(store.exportJournal().operations.length,0);
    const saved=store.dispatch('SAVE_EDIT_PLAN',{projectId:project.id,planId:'edit-stored',expectedRevision:0,expectedVersionId:null,plan:draft()});assert.equal(saved.ok,true);assert.equal(saved.persisted,true);
    store.dispose();store=new WorkshopStore();assert.equal(store.state.projects.find(item=>item.id===project.id).contentPlans.length,1);
    const malformed=operation('malformed-local',sourced(photo),0,100,'edit-corrupt');malformed.payload.plan.beats[0].in=0;malformed.payload.plan.beats[0].out=1;
    storage.setItem('bojart.workshop.v1.op.'+malformed.id,JSON.stringify(malformed));store.refresh();
    assert.equal(store.state.projects.find(item=>item.id===project.id).contentPlans.length,1);assert.equal(store._results.get(malformed.id).ok,false);
    assert.throws(()=>replayWorkshopOperations(seed,store.exportJournal().operations));
  }finally{store?.dispose();if(previous)Object.defineProperty(globalThis,'localStorage',previous);else delete globalThis.localStorage;}
});

check('Identité de base : une branche perdante ne peut pas ajouter une version sur le gagnant',()=>{
  const winner=operation('a-create',{...draft(),caption:'Branche A'}),loser=operation('z-create',{...draft(),caption:'Branche Z'});
  const followup=operation('z-followup',{...draft(),caption:'Suite de Z'},1,2,'edit-qa',loser.id);
  const replay=replayWorkshopOperations(seed,[followup,loser,winner]);
  const record=replay.state.projects.find(item=>item.id===project.id).contentPlans[0];
  assert.equal(record.versions.length,1);assert.equal(record.versions[0].operationId,winner.id);assert.equal(record.versions[0].plan.caption,'Branche A');
  assert.equal(replay.results.get(loser.id).ok,false);assert.equal(replay.results.get(followup.id).ok,false);
  const rebased=operation('rebased-update',{...draft(),caption:'Reprise explicite'},1,3,'edit-qa',winner.id);
  const corrected=replayWorkshopOperations(seed,[followup,loser,winner,rebased]);
  const latest=latestEditVersion(corrected.state.projects.find(item=>item.id===project.id).contentPlans[0]);
  assert.equal(latest.revision,2);assert.equal(latest.operationId,rebased.id);assert.equal(latest.plan.caption,'Reprise explicite');
});

check('Concurrence avant notification : dispatch relit et refuse une version 1 remplacée à numéro identique',()=>{
  const previous=Object.getOwnPropertyDescriptor(globalThis,'localStorage');
  const entries=new Map([['bojart.workshop.v1.seed',JSON.stringify(seed)]]);
  const storage={get length(){return entries.size;},key(index){return [...entries.keys()][index]??null;},getItem(key){return entries.get(key)??null;},setItem(key,value){entries.set(key,String(value));}};
  Object.defineProperty(globalThis,'localStorage',{value:storage,configurable:true});
  let store;
  try{
    store=new WorkshopStore();
    const first=store.dispatch('SAVE_EDIT_PLAN',{projectId:project.id,planId:'edit-race',expectedRevision:0,expectedVersionId:null,plan:{...draft(),caption:'Version affichée'}});
    assert.equal(first.ok,true);
    const captured=latestEditVersion(store.state.projects.find(item=>item.id===project.id).contentPlans[0]);
    assert.equal(captured.operationId,first.operationId);
    const firstOperation=store.exportJournal().operations.find(op=>op.id===first.operationId);
    const offline=operation('000-offline-create',{...draft(),caption:'Version concurrente'},0,firstOperation.clock,'edit-race');
    storage.setItem('bojart.workshop.v1.op.'+offline.id,JSON.stringify(offline));
    assert.equal(latestEditVersion(store.state.projects.find(item=>item.id===project.id).contentPlans[0]).plan.caption,'Version affichée');
    const attempted={...draft(),caption:'Saisie à conserver'};
    const refused=store.dispatch('SAVE_EDIT_PLAN',{projectId:project.id,planId:'edit-race',expectedRevision:captured.revision,expectedVersionId:captured.operationId,plan:attempted});
    assert.equal(refused.ok,false);assert.equal(refused.persisted,false);assert.match(refused.message,/changé/);
    const current=latestEditVersion(store.state.projects.find(item=>item.id===project.id).contentPlans[0]);
    assert.equal(current.revision,captured.revision);assert.equal(current.operationId,offline.id);assert.equal(current.plan.caption,'Version concurrente');
    assert.equal(attempted.caption,'Saisie à conserver');assert.equal(store.exportJournal().operations.length,2);
  }finally{store?.dispose();if(previous)Object.defineProperty(globalThis,'localStorage',previous);else delete globalThis.localStorage;}
});

console.log(JSON.stringify({ok:true,checks,limits:EDIT_LIMITS,physicalActions:0},null,2));
