import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import vm from 'node:vm';
import {createProjectEvidence,preparationReportContext} from '../dist/lib/project-evidence.js';
import {buildMasterMission,buildControlDecision,answerMissionQuestion,buildOperations} from '../dist/lib/control-plane.js';
import {inspectDeclaredPreparation} from '../dist/lib/preparation.js';
import {normalizeFleetRecord} from '../dist/lib/fleet-registry.js';
import {createEditDraft} from '../dist/lib/edit-plan.js';

// Read the actual pure STL inspection function and its bundled decoder. No WebGL is instantiated.
const threeURL=new URL('../dist/vendor/three.module.js',import.meta.url);
const THREE=await import(threeURL.href);
const loaderSource=(await readFile(new URL('../dist/vendor/STLLoader.js',import.meta.url),'utf8')).replace(/from 'three'/g,'from '+JSON.stringify(threeURL.href));
const {STLLoader}=await import('data:text/javascript;base64,'+Buffer.from(loaderSource).toString('base64'));
const appSource=await readFile(new URL('../dist/app.js',import.meta.url),'utf8');
const viewerSource=await readFile(new URL('../dist/lib/viewer.js',import.meta.url),'utf8');
const inspectSource=viewerSource.slice(viewerSource.indexOf('export function inspectSTL'),viewerSource.indexOf('export async function createViewer'));
assert.ok(inspectSource.startsWith('export function inspectSTL'));
const actualInspectSTL=new Function('THREE','STLLoader',inspectSource.replace('export function','return function'))(THREE,STLLoader);
const clone=value=>structuredClone(value),at=Date.UTC(2026,9,19,3),checks=[],failures=[];
async function check(name,run){try{await run();checks.push(name);}catch(error){failures.push({name,message:error.message});}}
const deferred=()=>{let resolve;const promise=new Promise(value=>{resolve=value;});return{promise,resolve};};
function boxSTL([x,y,z]=[10,20,30]){
  const vertices=[[0,0,0],[x,0,0],[x,y,0],[0,y,0],[0,0,z],[x,0,z],[x,y,z],[0,y,z]];
  const faces=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]];
  const buffer=new ArrayBuffer(84+faces.length*50),view=new DataView(buffer);view.setUint32(80,faces.length,true);
  faces.forEach((face,index)=>{let cursor=84+index*50+12;for(const id of face)for(const value of vertices[id]){view.setFloat32(cursor,value,true);cursor+=4;}});
  return buffer;
}
function fixture({assetId='asset-one',unit='mm',record=true}={}){
  const piece={id:'piece-one',revision:2,name:'Pièce test',assetId,unit,tech:'fdm',dims:[999,999,999],triangles:777,machine:'P01'};
  const project={id:'project-one',revision:3,name:'Dossier test',kind:'prototype',quantity:2,height:1000,story:'Ancien texte sans montage enregistré',pieces:[piece]};
  const machine={id:'P01',name:'Exemple',tech:'fdm',volume:[10000,10000,10000],material:'Exemple'};
  if(record)machine.registry=normalizeFleetRecord({origin:'declared',manufacturer:'Banc QA',model:'Modèle de test',serial:'QA1',technology:'fdm',usableVolumeMm:[50,50,50],volumeSource:'Fixture QA',slicer:{name:'Slicer QA',version:'1',machineProfile:'Profil QA',materialProfile:'Matière QA'},qualification:{status:'not_started'}},null,at);
  const other={id:'project-two',revision:1,name:'Autre dossier',kind:'art',quantity:1,height:100,pieces:[{...clone(piece),id:'piece-two',assetId:null,revision:1}]};
  const state={projectId:project.id,selectedPieceId:piece.id,projects:[project,other],machines:[machine],jobs:[{id:'demo-job',projectId:project.id,pieceId:piece.id,revision:piece.revision,machine:'P01',quantity:2,status:'running',simulated:true,duration:1000,elapsed:900,startedAt:at-900}]};
  const buffer=boxSTL(),calls={read:0,inspect:0},events=[];
  const store=createProjectEvidence({getState:()=>state,readAsset:async id=>{calls.read++;return id===assetId?{buffer}:null;},inspectSTL:(bytes,inputUnit)=>{calls.inspect++;return actualInspectSTL(bytes,inputUnit);},now:()=>at,onChange:event=>events.push(clone(event))});
  return{state,project,piece,machine,buffer,store,calls,events};
}

await check('Dimensions de métadonnées et jobs simulés ne constituent aucune preuve de STL',()=>{
  const f=fixture(),report=f.store.report(f.project.id),mission=buildMasterMission(f.state,f.project.id);
  assert.deepEqual(report.pieces[0].storedDimensionsMm,[999,999,999]);assert.equal(report.pieces[0].dimensionsMm,null);assert.equal(report.summary.measuredFiles,0);assert.equal(mission.readiness.binariesVerified,false);assert.equal(mission.readiness.compatibleEnvelopes,0);assert.equal(mission.preparation.report.pieces[0].file.status,'unchecked');assert.equal(f.calls.read,0);f.store.dispose();
});
await check('Vrai binaire STL décodé par le code livré, dimensions et SHA partagés avec la mission centrale',async()=>{
  const f=fixture(),before=clone(f.state);await f.store.inspect(f.project.id);const snapshot=f.store.snapshot(f.project.id),report=snapshot.report;
  assert.equal(snapshot.status,'checked');assert.equal(report.summary.measuredFiles,1);assert.deepEqual(report.pieces[0].dimensionsMm,[10,20,30]);assert.equal(report.pieces[0].file.triangles,12);assert.equal(report.pieces[0].file.sha256,createHash('sha256').update(new Uint8Array(f.buffer)).digest('hex'));assert.equal(report.pieces[0].measurementsMatchRecord,false);assert.equal(report.summary.piecesWithEnvelopeFit,1);
  const mission=buildMasterMission(f.state,f.project.id,{preparationReport:report,evidenceStatus:snapshot.status});assert.equal(mission.format,'bojart.master-mission.v2');assert.equal(mission.readiness.binariesVerified,true);assert.equal(mission.readiness.measuredFiles,1);assert.equal(mission.readiness.compatibleEnvelopes,1);assert.deepEqual(mission.pieces[0].dimensionsMm,[10,20,30]);assert.equal(mission.preparation.evidenceStatus,'checked');assert.deepEqual(f.state,before);f.store.dispose();
});
await check('Unité pouces mesurée dans le fichier, hauteur du brief sans effet sur la géométrie',async()=>{
  const f=fixture({unit:'inch'});await f.store.inspect(f.project.id);const report=f.store.report(f.project.id);assert.deepEqual(report.pieces[0].dimensionsMm,[254,508,762]);assert.equal(report.project.targetHeightMm,1000);assert.equal(report.summary.piecesWithEnvelopeFit,0);f.store.dispose();
});
await check('Relecture dédupliquée ; force relit le binaire et retire les preuves pendant le contrôle',async()=>{
  const f=fixture();await Promise.all([f.store.inspect(f.project.id),f.store.inspect(f.project.id)]);assert.equal(f.calls.read,1);assert.equal(f.calls.inspect,1);await f.store.inspect(f.project.id);assert.equal(f.calls.read,1);
  const pending=f.store.inspect(f.project.id,{force:true});assert.equal(f.store.snapshot(f.project.id).status,'checking');assert.equal(f.store.report(f.project.id).summary.measuredFiles,0);await pending;assert.equal(f.calls.read,2);f.store.dispose();
});
await check('Fichier absent et STL invalide restent distingués après une lecture',async()=>{
  const f=fixture();let bytes=null;
  const store=createProjectEvidence({getState:()=>f.state,readAsset:async()=>bytes?{buffer:bytes}:null,inspectSTL:actualInspectSTL,now:()=>at});await store.inspect(f.project.id);assert.equal(store.report(f.project.id).pieces[0].file.status,'missing');bytes=new TextEncoder().encode('this is not a valid STL').buffer;await store.inspect(f.project.id,{force:true});assert.equal(store.report(f.project.id).pieces[0].file.status,'invalid');assert.equal(store.report(f.project.id).summary.measuredFiles,0);store.dispose();f.store.dispose();
});
await check('Une panne de calcul SHA ne transforme pas un STL décodable en fichier géométriquement invalide',async()=>{
  const f=fixture();const store=createProjectEvidence({getState:()=>f.state,readAsset:async()=>({buffer:f.buffer}),inspectSTL:actualInspectSTL,cryptoImpl:{subtle:{digest:async()=>{throw new Error('digest unavailable');}}},now:()=>at});await store.inspect(f.project.id);const piece=store.report(f.project.id).pieces[0];assert.equal(piece.file.status,'measured');assert.equal(piece.file.sha256,null);assert.deepEqual(piece.dimensionsMm,[10,20,30]);store.dispose();f.store.dispose();
});
await check('Pièce modifiée pendant la lecture : le résultat ancien est rejeté',async()=>{
  const f=fixture(),read=deferred(),entered=deferred();const store=createProjectEvidence({getState:()=>f.state,readAsset:async()=>{entered.resolve();return read.promise;},inspectSTL:actualInspectSTL,now:()=>at});const pending=store.inspect(f.project.id);await entered.promise;f.piece.revision++;f.piece.assetId='asset-replacement';read.resolve({buffer:f.buffer});assert.equal(await pending,null);assert.equal(store.snapshot(f.project.id).status,'unchecked');assert.equal(store.report(f.project.id).summary.measuredFiles,0);store.dispose();f.store.dispose();
});
await check('Pièce modifiée pendant la mesure ou le SHA : aucun résultat tardif absorbé',async()=>{
  for(const phase of ['inspect','hash']){
    const f=fixture(),gate=deferred(),entered=deferred();
    const store=createProjectEvidence({getState:()=>f.state,readAsset:async()=>({buffer:f.buffer}),inspectSTL:async(bytes,unit)=>{const result=actualInspectSTL(bytes,unit);if(phase==='inspect'){entered.resolve();await gate.promise;}return result;},cryptoImpl:{subtle:{digest:async()=>{if(phase==='hash'){entered.resolve();await gate.promise;}return new Uint8Array(32).buffer;}}},now:()=>at});
    const pending=store.inspect(f.project.id);await entered.promise;f.piece.unit='inch';gate.resolve();assert.equal(await pending,null);assert.equal(store.report(f.project.id).summary.measuredFiles,0);store.dispose();f.store.dispose();
  }
});
await check('Changement de dossier actif sans modification du dossier cible : preuve attachée au bon dossier',async()=>{
  const f=fixture(),gate=deferred(),entered=deferred();const store=createProjectEvidence({getState:()=>f.state,readAsset:async()=>{entered.resolve();await gate.promise;return{buffer:f.buffer};},inspectSTL:actualInspectSTL,now:()=>at});const pending=store.inspect(f.project.id);await entered.promise;f.state.projectId='project-two';gate.resolve();await pending;assert.equal(store.report(f.project.id).summary.measuredFiles,1);assert.equal(store.report('project-two').summary.measuredFiles,0);store.dispose();f.store.dispose();
});
await check('Destruction du contrôleur ou suppression du dossier pendant la lecture : résultat abandonné',async()=>{
  for(const phase of ['dispose','delete']){const f=fixture(),gate=deferred(),entered=deferred();const store=createProjectEvidence({getState:()=>f.state,readAsset:async()=>{entered.resolve();await gate.promise;return{buffer:f.buffer};},inspectSTL:actualInspectSTL,now:()=>at});const pending=store.inspect(f.project.id);await entered.promise;if(phase==='dispose')store.dispose();else f.state.projects=f.state.projects.filter(project=>project.id!==f.project.id);gate.resolve();assert.equal(await pending,null);store.dispose();f.store.dispose();}
});
await check('Rapport d’un autre projet ou d’une ancienne révision refusé par la mission',async()=>{
  const f=fixture();await f.store.inspect(f.project.id);const report=f.store.report(f.project.id);
  const foreign=buildMasterMission(f.state,'project-two',{preparationReport:report,evidenceStatus:'checked'});assert.equal(foreign.readiness.measuredFiles,0);assert.equal(foreign.preparation.evidenceStatus,'unchecked');
  f.project.revision++;const stale=buildMasterMission(f.state,f.project.id,{preparationReport:report,evidenceStatus:'checked'});assert.equal(stale.readiness.measuredFiles,0);assert.equal(stale.preparation.evidenceStatus,'unchecked');assert.equal(f.store.absorb(report),false);f.store.dispose();
});
await check('Changement de profil machine : rapport ancien écarté, mesures de fichier réutilisables avec fiche actuelle',async()=>{
  const f=fixture();await f.store.inspect(f.project.id);const report=f.store.report(f.project.id);f.machine.registry.slicer.machineProfile='Profil remplacé';f.machine.registry.revision++;
  assert.equal(f.store.absorb(report),false);const stale=buildMasterMission(f.state,f.project.id,{preparationReport:report,evidenceStatus:'checked'});assert.equal(stale.readiness.measuredFiles,0);
  const current=f.store.report(f.project.id);assert.equal(current.summary.measuredFiles,1);assert.equal(current.machines[0].record.revision,2);assert.equal(f.calls.read,1);f.store.dispose();
});
await check('Absorption : format, marque et limites exigés, anciennes métadonnées rejetées',async()=>{
  const f=fixture();await f.store.inspect(f.project.id);const report=f.store.report(f.project.id);
  for(const change of [r=>{r.format='foreign';},r=>{r.brand='Other';},r=>{r.canSlice=true;},r=>{r.canStartPhysicalPrint=true;},r=>{r.project.id='unknown';},r=>{r.pieces[0].revision++;}]){const bad=clone(report);change(bad);assert.equal(f.store.absorb(bad),false);}
  const fresh=createProjectEvidence({getState:()=>f.state,readAsset:async()=>null,inspectSTL:actualInspectSTL,now:()=>at});assert.equal(fresh.absorb(report),true);assert.equal(fresh.report(f.project.id).summary.measuredFiles,1);fresh.dispose();f.store.dispose();
});
await check('Le résumé fourni n’est jamais une autorité : compteurs recalculés depuis les preuves individuelles',()=>{
  const f=fixture();const unverified=inspectDeclaredPreparation(f.state,f.project.id);unverified.summary.measuredFiles=1;unverified.summary.piecesWithEnvelopeFit=1;const mission=buildMasterMission(f.state,f.project.id,{preparationReport:unverified,evidenceStatus:'checked'});assert.equal(mission.readiness.measuredFiles,0);assert.equal(mission.readiness.binariesVerified,false);assert.equal(mission.readiness.compatibleEnvelopes,0);f.store.dispose();
});
await check('Preuve individuelle corrompue : rejet par les validations de préparation',async()=>{
  const f=fixture();await f.store.inspect(f.project.id);const report=f.store.report(f.project.id);report.pieces[0].file.sha256='bad';report.summary.measuredFiles=1;
  const mission=buildMasterMission(f.state,f.project.id,{preparationReport:report,evidenceStatus:'checked'});assert.equal(mission.readiness.binariesVerified,false);assert.equal(mission.preparation.report.pieces[0].file.status,'invalid');f.store.dispose();
});
await check('Empreinte de fichier attendue : un autre binaire ne devient pas la preuve de cette référence',async()=>{
  const f=fixture();f.piece.assetSha256='b'.repeat(64);await f.store.inspect(f.project.id);const report=f.store.report(f.project.id);assert.equal(report.pieces[0].file.status,'invalid');assert.equal(report.summary.measuredFiles,0);f.store.dispose();
});
await check('La prochaine décision et la mission partagent les mêmes faits et gardent les besoins de procédé',async()=>{
  const f=fixture();const before=buildControlDecision(f.state,f.project.id);assert.equal(before.primary.action,'audit-project');await f.store.inspect(f.project.id);const snapshot=f.store.snapshot(f.project.id),options={preparationReport:snapshot.report,evidenceStatus:snapshot.status};const mission=buildMasterMission(f.state,f.project.id,options),decision=buildControlDecision(f.state,f.project.id,options);assert.equal(decision.facts[0].value,'1 / 1');assert.equal(mission.readiness.measuredFiles,1);assert.match(decision.title,/procédé|assemblage/);assert.equal(mission.readiness.canStartPhysicalPrint,false);f.store.dispose();
});
await check('La démonstration ne devient pas le chemin nominal vers la fabrication',async()=>{
  const f=fixture();await f.store.inspect(f.project.id);const mission=buildMasterMission(f.state,f.project.id,{preparationReport:f.store.report(f.project.id)}),simulation=mission.steps.find(step=>step.id==='simulation');assert.equal(simulation.mode,'simulation');assert.equal(mission.edges.some(edge=>edge.from==='simulation'&&edge.to!=='simulation'),false);
  for(const id of ['prepare','slice','approve','fabricate','finish']){const step=mission.steps.find(step=>step.id===id);assert.equal(step.status,'not_connected');assert.equal(step.mode,'unconnected');}
  for(const capability of ['canSlice','canStartPhysicalPrint','canPublish','canExecuteRobot'])assert.equal(mission.readiness[capability],false);
  assert.ok(buildOperations(f.state).filter(operation=>operation.mode==='unconnected').every(operation=>operation.available===false));f.store.dispose();
});
await check('Les versions d’édit enregistrées remontent dans la mission sans prétendre un rendu vidéo',()=>{
  const f=fixture(),plan=createEditDraft(f.project);f.project.contentPlans=[{id:'plan-one',versions:[{revision:1,operationId:'plan-op-1',at,projectRevision:3,projectName:f.project.name,plan},{revision:2,operationId:'plan-op-2',at:at+1,projectRevision:3,projectName:f.project.name,plan:{...clone(plan),title:'Nouvelle intention',series:'prototype'}}]}];
  const mission=buildMasterMission(f.state,f.project.id);assert.equal(mission.editPlans.length,1);assert.equal(mission.editPlans[0].revision,2);assert.equal(mission.editPlans[0].operationId,'plan-op-2');assert.equal(mission.editPlans[0].title,'Nouvelle intention');assert.equal(mission.editPlans[0].renderVerified,false);assert.deepEqual(mission.steps.find(step=>step.id==='story').evidence.savedPlans,mission.editPlans);f.store.dispose();
});
await check('Questions Pourquoi et Où : réponse descriptive, ni modification métier ni navigation',async()=>{
  const f=fixture(),mission=buildMasterMission(f.state,f.project.id),before=clone(mission);
  for(const question of ['Pourquoi la pièce attend ?','Où sont les fichiers STL','Pourquoi mettre en pause P01','Jev, pourquoi mon montage attend ?'])assert.equal(typeof answerMissionQuestion(question,mission),'string');assert.equal(answerMissionQuestion('Mets P01 en pause',mission),null);assert.deepEqual(mission,before);
  const commandSource=appSource.slice(appSource.indexOf('async function executeCommand(raw)'),appSource.indexOf('\nfunction applyMotion()'));
  assert.ok(commandSource.startsWith('async function executeCommand(raw)'));
  const effects=[],sandbox={answerMissionQuestion,currentMasterMission:()=>mission,getProject:()=>f.project,intentSequence:0,lastReceipt:'',setDisplayReceipt:text=>effects.push({type:'receipt',text}),dispatch:(type,payload)=>{effects.push({type,payload});return{ok:true};}};
  vm.createContext(sandbox);vm.runInContext(commandSource,sandbox);
  for(const question of ['Pourquoi la pièce est bloquée ?','Où sont les STL','Pourquoi mettre P01 en pause ?'])await sandbox.executeCommand(question);
  assert.equal(effects.filter(item=>item.type==='receipt').length,3);assert.ok(effects.every(item=>['receipt','LOG'].includes(item.type)));assert.equal(f.state.jobs[0].status,'running');f.store.dispose();
});

const result={ok:failures.length===0,checks:checks.length,names:checks,failures,scope:'Actual bundled STL decoder on synthetic binary geometry; pure mission and mocked I/O. No browser/WebGL, server, account, slicer or physical printer.'};
await writeFile(new URL('./project-evidence-results.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));if(failures.length)process.exitCode=1;
