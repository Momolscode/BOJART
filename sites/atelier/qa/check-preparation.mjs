import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {WorkshopStore,replayWorkshopOperations,validateWorkshopOperation} from '../dist/lib/workshop.js';
import {normalizeFleetRecord} from '../dist/lib/fleet-registry.js';
import {PREPARATION_ORIENTATIONS,inspectDeclaredPreparation,exportDeclaredPreparation} from '../dist/lib/preparation.js';

const at=Date.parse('2026-10-18T23:50:00Z'),copy=value=>JSON.parse(JSON.stringify(value)),checks=[];
const raw=(patch={})=>({origin:'declared',manufacturer:'Machine du test',model:'Banc géométrique',serial:'atelier-test',technology:'fdm',usableVolumeMm:[200,120,100],volumeSource:'Dimensions fournies pour ce test',material:'PLA déclaré',slicer:{name:'Slicer déclaré',version:'Version déclarée',machineProfile:'Profil machine déclaré',materialProfile:'Profil matière déclaré'},connection:{kind:'manual',endpoint:''},fileFormats:['gcode'],qualification:{status:'documented',testedOn:'2026-10-18',operator:'Atelier de test',report:'Rapport fictif du banc de test'},...patch});
function fixture({dims=[180,110,80],volume=[200,120,100],tech='fdm',unit='mm',assetId='asset-local'}={}) {
  const state=replayWorkshopOperations({version:1,at},[]).state;
  state.machines[0].registry=normalizeFleetRecord(raw({usableVolumeMm:volume,technology:tech}),null,at);
  const project=state.projects.find(p=>p.id==='prototype');
  project.pieces=[{id:'piece-test',name:'Pièce du contrôle',tech,dims:[...dims],assetId,triangles:12,unit,revision:2,machine:'P01'}];
  const piece=project.pieces[0];
  const evidence={projectId:project.id,pieceId:piece.id,pieceRevision:piece.revision,assetId,unit,status:'measured',dimsMm:[...dims],triangles:12,byteLength:684,checkedAt:at,sha256:'a'.repeat(64)};
  return {state,project,piece,evidence};
}
const inspect=fixture=>inspectDeclaredPreparation(fixture.state,fixture.project.id,{assetEvidence:[fixture.evidence]});
const pair=report=>report.pieces[0].assessments.find(a=>a.machineId==='P01');
function check(label,fn) { fn();checks.push(label); }

check('The exact requested project is required; unknown or ambiguous identities cannot fall back to the active dossier.',()=>{
  const f=fixture(),before=copy(f.state);
  assert.equal(f.state.projectId,'sculpture-xl');
  assert.equal(inspect(f).project.id,'prototype');
  assert.throws(()=>inspectDeclaredPreparation(f.state,'absent'),RangeError);
  assert.throws(()=>inspectDeclaredPreparation(f.state,null),TypeError);
  f.state.projects.push(copy(f.project));assert.throws(()=>inspect(f),RangeError);f.state.projects.pop();
  assert.deepEqual(f.state,before);
});

check('No demo slot, material, name, procedure or volume can become a real candidate without a declared registry.',()=>{
  const f=fixture();delete f.state.machines[0].registry;
  const first=inspect(f);assert.equal(first.summary.declaredMachines,0);assert.equal(first.summary.piecesWithEnvelopeFit,0);
  assert.ok(first.pieces[0].assessments.every(a=>a.status==='not_declared' && !a.orientations.length));
  for(const machine of f.state.machines){machine.tech='fdm';machine.volume=[1000000,1000000,1000000];machine.material='Invention';machine.name='Données de démonstration';}
  assert.deepEqual(inspect(f),first);
});

check('A real FDM declaration overrides the resin demo slot; changing only declared dimensions changes the geometric conclusion.',()=>{
  const f=fixture();assert.equal(f.state.machines[0].tech,'resin');
  const first=inspect(f);assert.equal(pair(first).technologyStatus,'match');assert.equal(pair(first).status,'fits');assert.equal(first.machines[0].record.material,'PLA déclaré');
  f.state.machines[0].registry=normalizeFleetRecord(raw({usableVolumeMm:[50,50,50]}),f.state.machines[0].registry,at+1);
  const changed=inspect(f);assert.equal(pair(changed).status,'exceeds');assert.equal(changed.summary.piecesWithEnvelopeFit,0);
});

check('All six dimensional orientations are proper rotations, never reflected geometry, with stable source-axis mappings.',()=>{
  const expected={xyz:[0,1,2],yxz:[1,0,2],xzy:[0,2,1],zxy:[2,0,1],yzx:[1,2,0],zyx:[2,1,0]};
  assert.equal(PREPARATION_ORIENTATIONS.length,6);
  for(const orientation of PREPARATION_ORIENTATIONS){
    assert.deepEqual(orientation.axes,expected[orientation.id]);
    const m=Array.from({length:3},(_,row)=>Array.from({length:3},(_,column)=>orientation.axes[row]===column?orientation.signs[row]:0));
    const determinant=m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])-m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])+m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]);
    assert.equal(determinant,1);
    assert.ok(Object.isFrozen(orientation) && Object.isFrozen(orientation.axes) && Object.isFrozen(orientation.signs));
  }
});

check('Axis-specific limits preserve orientation meaning, and exact equality reports zero raw clearance without claiming support space.',()=>{
  const f=fixture({dims:[80,180,110],volume:[180,110,80]});
  const report=inspect(f),a=pair(report);
  assert.deepEqual(a.fitOrientationIds,['yzx']);assert.equal(a.bestOrientationId,'yzx');
  assert.deepEqual(a.orientations.find(o=>o.id==='xyz').dimensionsMm,[80,180,110]);
  assert.deepEqual(a.orientations.find(o=>o.id==='xyz').clearanceMm,[100,-70,-30]);
  assert.deepEqual(a.orientations.find(o=>o.id==='yzx').clearanceMm,[0,0,0]);
  assert.equal(report.canSlice,false);assert.equal(report.canStartPhysicalPrint,false);
  assert.ok(report.limitations.some(text=>text.includes('Supports, brim, raft')));
});

check('Unknown and mismatched technologies cannot qualify a geometrically fitting envelope.',()=>{
  const f=fixture();f.state.machines[0].registry=normalizeFleetRecord(raw({technology:'resin'}),null,at);
  const mismatch=pair(inspect(f));assert.equal(mismatch.envelopeStatus,'fits');assert.equal(mismatch.status,'technology_mismatch');assert.deepEqual(mismatch.fitOrientationIds,[]);assert.equal(mismatch.bestOrientationId,null);
  f.state.machines[0].registry=normalizeFleetRecord(raw({technology:'unknown'}),null,at);
  const unknown=pair(inspect(f));assert.equal(unknown.status,'technology_unknown');assert.deepEqual(unknown.fitOrientationIds,[]);
});

check('The useful machine volume must be present in the registry; no demo volume fills an empty declaration.',()=>{
  const f=fixture();f.state.machines[0].registry=normalizeFleetRecord(raw({usableVolumeMm:null}),null,at);
  const report=inspect(f);assert.equal(pair(report).status,'volume_missing');assert.deepEqual(pair(report).orientations,[]);assert.equal(report.summary.piecesWithEnvelopeFit,0);
});

check('An asset reference or stored piece dimensions alone do not prove a locally accessible measured STL.',()=>{
  const f=fixture();const unchecked=inspectDeclaredPreparation(f.state,f.project.id);
  assert.equal(unchecked.pieces[0].file.status,'unchecked');assert.equal(unchecked.pieces[0].dimensionsMm,null);assert.deepEqual(unchecked.pieces[0].storedDimensionsMm,[180,110,80]);assert.equal(unchecked.summary.measuredFiles,0);assert.deepEqual(pair(unchecked).orientations,[]);
  f.evidence.status='missing';const missing=inspect(f);assert.equal(missing.summary.missingFiles,1);assert.equal(pair(missing).status,'file_missing');
  f.piece.assetId=null;const unreferenced=inspect(f);assert.equal(unreferenced.pieces[0].file.status,'unreferenced');assert.equal(unreferenced.summary.unreferencedFiles,1);
});

check('File evidence is tied to the exact dossier, piece revision, asset and unit; stale or duplicate checks are not silently selected.',()=>{
  const f=fixture();
  for(const change of [{projectId:'sculpture-xl'},{pieceId:'other'},{pieceRevision:1},{assetId:'old'},{unit:'inch'}]){
    const report=inspectDeclaredPreparation(f.state,f.project.id,{assetEvidence:[{...f.evidence,...change}]});assert.equal(report.pieces[0].file.status,'unchecked');assert.equal(report.summary.measuredFiles,0);
  }
  const duplicate=inspectDeclaredPreparation(f.state,f.project.id,{assetEvidence:[f.evidence,copy(f.evidence)]});assert.equal(duplicate.pieces[0].file.status,'unchecked');assert.equal(duplicate.summary.measuredFiles,0);
});

check('Actual measured millimetres remain authoritative, including inch imports, without rescaling by stored dimensions or requested project height.',()=>{
  const f=fixture({dims:[25.4,50.8,76.2],unit:'inch'});f.piece.dims=[1,2,3];f.project.height=1000;
  const report=inspect(f);assert.deepEqual(report.pieces[0].dimensionsMm,[25.4,50.8,76.2]);assert.deepEqual(pair(report).orientations[0].dimensionsMm,[25.4,50.8,76.2]);assert.equal(report.pieces[0].measurementsMatchRecord,false);
  assert.ok(pair(report).issues.some(issue=>issue.code==='stored_measurements_differ'));
  for(const unit of ['cm','m','in','inches']){f.piece.unit=unit;f.evidence.unit=unit;assert.equal(inspect(f).pieces[0].file.status,'invalid');}
});

check('Malformed measurements, evidence metadata or fingerprints cannot yield measured geometry or candidates.',()=>{
  const f=fixture();
  for(const change of [{dimsMm:[1,2]},{dimsMm:[1,-2,3]},{dimsMm:[0,0,0]},{dimsMm:[NaN,2,3]},{dimsMm:[Infinity,2,3]},{dimsMm:['1',2,3]},{triangles:0},{triangles:2000001},{byteLength:14},{byteLength:MAX_SAFE_BYTES()},{checkedAt:-1},{checkedAt:'today'},{sha256:'invalid'}]){
    const report=inspectDeclaredPreparation(f.state,f.project.id,{assetEvidence:[{...f.evidence,...change}]});assert.equal(report.pieces[0].file.status,'invalid');assert.equal(report.summary.measuredFiles,0);assert.equal(report.summary.piecesWithEnvelopeFit,0);
  }
  function MAX_SAFE_BYTES(){return 50*1024*1024+1;}
});

check('A measured planar STL remains inspectable but has no volumetric candidate; raw box fitting does not claim mesh closure.',()=>{
  const f=fixture({dims:[180,110,0]});const report=inspect(f);
  assert.equal(report.pieces[0].file.status,'measured');assert.equal(report.summary.measuredFiles,1);assert.equal(report.summary.nonVolumetricPieces,1);assert.equal(pair(report).status,'non_volumetric');assert.deepEqual(pair(report).orientations,[]);
  assert.ok(report.limitations.some(text=>text.includes('fermeture du maillage')));assert.equal(report.canStartPhysicalPrint,false);
});

check('Material names, complete slicer references and a documented test remain declarations, never automatic readiness.',()=>{
  const report=inspect(fixture()),a=pair(report);
  assert.equal(a.profiles.declared,true);assert.deepEqual(a.profiles.missing,[]);assert.equal(a.material.status,'unspecified');assert.equal(a.qualification.status,'documented');assert.equal(a.qualification.verified,false);
  assert.equal(report.canSlice,false);assert.equal(report.canStartPhysicalPrint,false);
  const f=fixture();f.state.machines[0].registry=normalizeFleetRecord(raw({slicer:{},volumeSource:'',qualification:{status:'needs_review',testedOn:'2026-10-18',operator:'Test',report:'Test ancien'}}),null,at);
  const incomplete=pair(inspect(f));assert.equal(incomplete.profiles.declared,false);assert.equal(incomplete.profiles.missing.length,4);assert.ok(incomplete.issues.some(i=>i.code==='volume_source_missing'));assert.ok(incomplete.issues.some(i=>i.code==='test_not_documented'));
});

check('Project quantity produces no invented nesting, duration, assignments or geometry scaling.',()=>{
  const f=fixture();f.project.quantity=37;f.project.height=3000;const before=copy(f.state),report=inspect(f);
  assert.equal(report.project.quantity,37);assert.equal(report.project.targetHeightMm,3000);assert.equal(report.pieces.length,1);assert.deepEqual(report.pieces[0].dimensionsMm,f.evidence.dimsMm);assert.deepEqual(f.state,before);
  assert.equal('jobs' in report,false);assert.equal('duration' in report,false);assert.equal('assignedMachine' in report.pieces[0],false);
});

check('Exports freeze the inspected dossier, registry revisions and SHA256 even after the workshop selection or source records change.',()=>{
  const f=fixture(),before=copy(f.state),proofBefore=copy(f.evidence),report=inspect(f);
  const exported=exportDeclaredPreparation(report,{pieceId:f.piece.id,machineId:'P01',orientationId:'xyz'},at+1);
  assert.deepEqual(f.state,before);assert.deepEqual(f.evidence,proofBefore);
  f.state.projectId='sculpture-xl';f.project.name='Nouveau nom';f.state.machines[0].registry.material='Autre matière';
  assert.equal(exported.project.id,'prototype');assert.equal(exported.project.name,'PROTOTYPE');assert.equal(exported.report.machines[0].record.revision,1);assert.equal(exported.report.machines[0].record.material,'PLA déclaré');assert.equal(exported.report.pieces[0].file.sha256,'a'.repeat(64));
  assert.deepEqual(exported.selectedOrientation.dimensionsMm,[180,110,80]);assert.ok(Object.values(exported.execution).every(value=>value===false));
  exported.report.pieces[0].dimensionsMm[0]=999;exported.selectedAssessment.qualification.report='Mutation';assert.equal(report.pieces[0].dimensionsMm[0],180);assert.notEqual(pair(report).qualification.report,'Mutation');
});

check('Exports reject foreign selection identities and uncomputed orientations while allowing incomplete reports without an invented selection.',()=>{
  const f=fixture(),report=inspect(f);
  for(const selection of [{pieceId:'absent'},{machineId:'absent'},{orientationId:'xyz'},{pieceId:f.piece.id,machineId:'P01',orientationId:'invalid'}])assert.throws(()=>exportDeclaredPreparation(report,selection,at),RangeError);
  assert.throws(()=>exportDeclaredPreparation(report,{},undefined),TypeError);assert.throws(()=>exportDeclaredPreparation(report,{unexpected:true},at),TypeError);
  assert.throws(()=>exportDeclaredPreparation({...report,canSlice:true},{},at),TypeError);
  const unchecked=inspectDeclaredPreparation(f.state,f.project.id);const exported=exportDeclaredPreparation(unchecked,{pieceId:f.piece.id,machineId:'P01',orientationId:null},at);
  assert.equal(exported.selectedOrientation,null);assert.equal(exported.report.summary.measuredFiles,0);
  assert.throws(()=>exportDeclaredPreparation(unchecked,{pieceId:f.piece.id,machineId:'P01',orientationId:'xyz'},at),RangeError);
});

class Storage {
  entries=new Map();
  get length(){return this.entries.size;}
  key(index){return [...this.entries.keys()][index]??null;}
  getItem(key){return this.entries.get(key)??null;}
  setItem(key,value){this.entries.set(key,String(value));}
}
function withGuardStores(fn) {
  const previousStorage=globalThis.localStorage,storage=new Storage();globalThis.localStorage=storage;
  const first=new WorkshopStore(),second=new WorkshopStore();
  try{return fn(first,second,storage);}finally{first.dispose();second.dispose();if(previousStorage===undefined)delete globalThis.localStorage;else globalThis.localStorage=previousStorage;}
}
function pieceOperation(operationId,clock,payload,contextProjectId=payload.projectId) {
  return {version:1,id:operationId,clock,at:at+clock,type:'UPDATE_PIECE',payload,expected:{},context:{projectId:contextProjectId,projectName:'Contrôle import',pieceId:payload.id,machineId:null,originProjectId:'sculpture-xl'}};
}

check('A delayed targeted import cannot replace a file changed by another screen while the STL was being read.',()=>{
  withGuardStores((first,second,storage)=>{
    const target=first.state.projects.find(p=>p.id==='prototype').pieces[0];
    const pendingPayload={projectId:'prototype',id:target.id,expectedPieceRevision:target.revision,expectedAssetId:target.assetId||null,patch:{assetId:'asset-late-read',dims:[100,50,20],unit:'mm',triangles:12}};
    const winner=second.dispatch('UPDATE_PIECE',{projectId:'prototype',id:target.id,patch:{assetId:'asset-newer-file',dims:[110,55,22],unit:'mm',triangles:12}});assert.equal(winner.ok,true,winner.message);
    first.refresh();const before=copy(first.state),saved=[...storage.entries];
    const late=first.dispatch('UPDATE_PIECE',pendingPayload);assert.equal(late.ok,false);assert.equal(late.persisted,false);assert.match(late.message,/changé pendant la lecture/);
    assert.deepEqual(first.state,before);assert.deepEqual([...storage.entries],saved);
    assert.equal(first.state.projects.find(p=>p.id==='prototype').pieces[0].assetId,'asset-newer-file');
  });
});

check('A guarded association succeeds only on its original piece and leaves other dossiers and selection unchanged.',()=>{
  withGuardStores(first=>{
    const original=copy(first.state),target=first.state.projects.find(p=>p.id==='prototype').pieces[0];
    const result=first.dispatch('UPDATE_PIECE',{projectId:'prototype',id:target.id,expectedPieceRevision:target.revision,expectedAssetId:target.assetId||null,patch:{assetId:'asset-associated',dims:[100,50,20],unit:'mm',triangles:12}});assert.equal(result.ok,true,result.message);
    assert.equal(first.state.projectId,original.projectId);assert.equal(first.state.selectedPieceId,original.selectedPieceId);
    for(const other of original.projects.filter(p=>p.id!=='prototype'))assert.deepEqual(first.state.projects.find(p=>p.id===other.id),other);
    const updated=first.state.projects.find(p=>p.id==='prototype').pieces.find(p=>p.id===target.id);assert.equal(updated.assetId,'asset-associated');assert.equal(updated.revision,target.revision+1);
    const operation=first.exportJournal().operations.find(op=>op.id===result.operationId);assert.equal(operation.context.projectId,'prototype');assert.equal(operation.payload.expectedAssetId,null);
  });
});

check('Replay guards require the exact previous asset as well as revision, reject a missing target, and preserve legacy operations.',()=>{
  const initial=replayWorkshopOperations({version:1,at},[]).state,target=initial.projects.find(p=>p.id==='prototype').pieces[0];
  const legacy=pieceOperation('legacy-file',1,{projectId:'prototype',id:target.id,patch:{assetId:'asset-branch-a',dims:[100,50,20]}});
  const first=replayWorkshopOperations({version:1,at},[legacy]),current=first.state.projects.find(p=>p.id==='prototype').pieces[0];assert.equal(first.results.get('legacy-file').ok,true);
  const differentAsset=pieceOperation('late-branch-b',2,{projectId:'prototype',id:target.id,expectedPieceRevision:current.revision,expectedAssetId:'asset-branch-b',patch:{assetId:'asset-late',dims:[99,49,19]}});
  const missing=pieceOperation('missing-target',3,{projectId:'prototype',id:'missing-piece',expectedPieceRevision:1,expectedAssetId:null,patch:{assetId:'asset-absent-target',dims:[1,2,3]}});
  const replay=replayWorkshopOperations({version:1,at},[differentAsset,legacy,missing]);assert.equal(replay.results.get('late-branch-b').ok,false);assert.equal(replay.results.get('missing-target').ok,false);
  assert.deepEqual(replay.state.projects,first.state.projects);assert.deepEqual(replay.state.jobs,first.state.jobs);
  const legacyAdd=pieceOperation('legacy-add',4,{projectId:'prototype',id:'legacy-piece',patch:{assetId:'asset-legacy',dims:[1,2,3]}});
  const oldBehavior=replayWorkshopOperations({version:1,at},[legacyAdd]);assert.equal(oldBehavior.results.get('legacy-add').ok,true);assert.ok(oldBehavior.state.projects.find(p=>p.id==='prototype').pieces.some(p=>p.id==='legacy-piece'));
});

check('Import guards are paired, typed and context bound before persistence; undefined or invalid inputs cannot disappear through JSON cloning.',()=>{
  const payload={projectId:'prototype',id:'piece-id',patch:{assetId:'asset-incoming',dims:[1,2,3]},expectedPieceRevision:1,expectedAssetId:null};
  assert.doesNotThrow(()=>validateWorkshopOperation(pieceOperation('guard-valid',1,payload)));
  for(const change of [{expectedPieceRevision:0},{expectedPieceRevision:'1'},{expectedPieceRevision:1.5},{expectedPieceRevision:NaN},{expectedAssetId:7},{expectedAssetId:''},{expectedAssetId:undefined}])assert.throws(()=>validateWorkshopOperation(pieceOperation('guard-invalid',1,{...payload,...change})));
  for(const key of ['expectedPieceRevision','expectedAssetId']){const partial={...payload};delete partial[key];assert.throws(()=>validateWorkshopOperation(pieceOperation('guard-partial',1,partial)));}
  assert.throws(()=>validateWorkshopOperation(pieceOperation('guard-wrong-context',1,payload,'sculpture-xl')),/contexte/);
  withGuardStores((first,_second,storage)=>{
    const target=first.state.projects.find(p=>p.id==='prototype').pieces[0],before=copy(first.state),saved=[...storage.entries];
    const result=first.dispatch('UPDATE_PIECE',{...payload,id:target.id,expectedPieceRevision:undefined,expectedAssetId:undefined});assert.equal(result.ok,false);assert.equal(result.persisted,false);assert.deepEqual(first.state,before);assert.deepEqual([...storage.entries],saved);
  });
});

const source=await readFile(new URL('../dist/lib/preparation.js',import.meta.url));
const workshopSource=await readFile(new URL('../dist/lib/workshop.js',import.meta.url));
const result={format:'bojart.preparation-qa.v1',status:'passed',checkedAt:new Date().toISOString(),runtime:process.version,sourceSha256:createHash('sha256').update(source).digest('hex'),workshopSourceSha256:createHash('sha256').update(workshopSource).digest('hex'),scope:'Preparation module, declared registry fixtures and actual WorkshopStore dispatch/replay with isolated in-memory storage; no browser, network or hardware.',summary:{total:checks.length,passed:checks.length,failed:0},checks,browserRenderingVerified:false,hardwareVerified:false,livePrinterConnections:0};
await writeFile(new URL('./preparation-results.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
