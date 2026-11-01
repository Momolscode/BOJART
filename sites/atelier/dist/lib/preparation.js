/**
 * BOJ.ART — inspection of raw STL envelopes against the declared workshop.
 * No printer, slicer, journal, storage or network operation is performed here.
 */
import {fleetRecordOf} from './fleet-registry.js';

const copy = value => JSON.parse(JSON.stringify(value));
const fail = message => { throw new TypeError(message); };
const TECHNOLOGIES = ['fdm','resin'];
const FILE_STATES = ['unreferenced','unchecked','missing','invalid','measured'];
const MAX_STL_BYTES = 50 * 1024 * 1024;
const MAX_TRIANGLES = 2000000;

/** Output axis i = input[axes[i]] * signs[i]. Every transform has determinant +1. */
export const PREPARATION_ORIENTATIONS = Object.freeze([
  ['xyz','X · Y · Z',[0,1,2],[1,1,1]],
  ['yxz','Y · −X · Z',[1,0,2],[1,-1,1]],
  ['xzy','X · −Z · Y',[0,2,1],[1,-1,1]],
  ['zxy','Z · X · Y',[2,0,1],[1,1,1]],
  ['yzx','Y · Z · X',[1,2,0],[1,1,1]],
  ['zyx','Z · −Y · X',[2,1,0],[1,-1,1]]
].map(([id,label,axes,signs]) => Object.freeze({id,label,axes:Object.freeze(axes),signs:Object.freeze(signs)})));

const LIMITATIONS = Object.freeze([
  'Les volumes et procédés viennent exclusivement des fiches de machines déclarées ; les profils de démonstration ne participent pas à ce rapport.',
  'Le calcul compare la boîte englobante du STL à un volume utile déclaré. Il ne vérifie ni fermeture du maillage, ni solidité, ni imprimabilité.',
  'La fiche décrit une enveloppe rectangulaire XYZ ; les plateaux non rectangulaires et les zones interdites demandent un contrôle de contour distinct.',
  'Les six orientations représentent des permutations de dimensions par rotations à angles droits, sans réflexion. Elles ne recherchent pas une orientation optimale pour imprimer.',
  'Les écarts par axe concernent la pièce brute seule. Supports, brim, raft, évidement, drainage, espacements, tolérances et retrait matière ne sont pas calculés.',
  'Chaque pièce est examinée seule. Aucun placement de lot, nesting, contrôle de collision ou calendrier de fabrication n’est produit.',
  'Matières, profils et dossiers d’essai sont des déclarations. La compatibilité matière de la pièce et la qualification physique de la configuration restent à établir.',
  'La hauteur demandée dans le dossier ne redimensionne pas le STL. Les coordonnées sont interprétées dans l’unité sélectionnée puis exprimées en millimètres.',
  'Les fichiers STL restent séparés du journal et de cet export. Aucun fichier de slicing ni ordre d’impression n’est produit.'
]);

function plain(value,label) {
  if(!value || typeof value !== 'object' || Array.isArray(value) || ![Object.prototype,null].includes(Object.getPrototypeOf(value))) fail(label+' invalide.');
  return value;
}
function id(value,label) {
  if(typeof value !== 'string' || !value.trim() || value.length>300) fail(label+' invalide.');
  return value;
}
function finiteDimensions(value,allowFlat=false) {
  return Array.isArray(value) && value.length===3 && Array.from(value).every(n=>typeof n==='number' && Number.isFinite(n) && (allowFlat?n>=0:n>0) && n<=1000000) && value.some(n=>n>0);
}
function safeNumber(value,fallback=1) {
  return Number.isSafeInteger(value) && value>0 ? value : fallback;
}
function cleanMessage(value,fallback) {
  return typeof value==='string' && value.trim() ? value.replace(/[\u0000-\u001f\u007f]/g,' ').trim().slice(0,1000) : fallback;
}
function exactState(state,projectId) {
  plain(state,'État de l’atelier');
  if(!Array.isArray(state.projects) || !Array.isArray(state.machines)) fail('Les dossiers et machines de l’atelier sont requis.');
  id(projectId,'Identifiant du dossier');
  const matches=state.projects.filter(project=>project?.id===projectId);
  if(matches.length!==1) throw new RangeError(matches.length?'Identifiant de dossier ambigu.':'Le dossier ciblé est introuvable.');
  const project=plain(matches[0],'Dossier');
  if(!Array.isArray(project.pieces)) fail('Les pièces du dossier sont invalides.');
  const machineIds=new Set(),pieceIds=new Set();
  for(const machine of state.machines) {
    plain(machine,'Machine');id(machine.id,'Identifiant de machine');
    if(machineIds.has(machine.id)) fail('Identifiant de machine ambigu.');
    machineIds.add(machine.id);
  }
  for(const piece of project.pieces) {
    plain(piece,'Pièce');id(piece.id,'Identifiant de pièce');
    if(pieceIds.has(piece.id)) fail('Identifiant de pièce ambigu.');
    pieceIds.add(piece.id);
  }
  return project;
}

function inspectFile(projectId,piece,assetEvidence) {
  const base={status:'unchecked',message:'Le binaire STL n’a pas encore été relu sur ce poste.',checkedAt:null,byteLength:null,triangles:null,sha256:null};
  if(!piece.assetId) return {...base,status:'unreferenced',message:'Aucun fichier STL n’est associé à cette pièce.'};
  const candidates=assetEvidence.filter(e=>e && e.projectId===projectId && e.pieceId===piece.id && e.pieceRevision===(piece.revision??1) && e.assetId===piece.assetId && e.unit===(piece.unit??'mm'));
  if(candidates.length!==1) return {...base,message:candidates.length?'Plusieurs contrôles concurrents correspondent à cette pièce ; relire le fichier.':base.message};
  const evidence=candidates[0];
  if(!['measured','missing','invalid'].includes(evidence.status)) return {...base,status:'invalid',message:'Le résultat du contrôle de fichier est invalide.'};
  const checkedAt=evidence.checkedAt===undefined || evidence.checkedAt===null ? null : evidence.checkedAt;
  if(checkedAt!==null && (typeof checkedAt!=='number' || !Number.isFinite(checkedAt) || checkedAt<0 || checkedAt>8.64e15)) return {...base,status:'invalid',message:'La date du contrôle de fichier est invalide.'};
  const sha256=evidence.sha256===undefined || evidence.sha256===null ? null : evidence.sha256;
  if(sha256!==null && (typeof sha256!=='string' || !/^[0-9a-f]{64}$/i.test(sha256))) return {...base,status:'invalid',message:'L’empreinte du fichier est invalide.'};
  const file={...base,checkedAt,sha256:sha256?.toLowerCase()??null};
  if(evidence.status==='missing') return {...file,status:'missing',message:cleanMessage(evidence.message,'Le binaire référencé est absent de ce poste.')};
  if(evidence.status==='invalid') return {...file,status:'invalid',message:cleanMessage(evidence.message,'Le fichier ne peut pas être inspecté comme un STL.')};
  if(piece.assetSha256&&file.sha256!==piece.assetSha256)return {...file,status:'invalid',message:'L’empreinte relue ne confirme pas le fichier associé à cette révision.'};
  if(!['mm','inch'].includes(piece.unit??'mm')) return {...file,status:'invalid',message:'L’unité du fichier doit être renseignée explicitement en mm ou en pouces avant ce contrôle.'};
  if(!finiteDimensions(evidence.dimsMm,true) || !Number.isSafeInteger(evidence.triangles) || evidence.triangles<1 || evidence.triangles>MAX_TRIANGLES || !Number.isSafeInteger(evidence.byteLength) || evidence.byteLength<15 || evidence.byteLength>MAX_STL_BYTES) {
    return {...file,status:'invalid',message:'Les mesures, le nombre de triangles ou la taille du fichier sont invalides.'};
  }
  return {...file,status:'measured',message:'Le binaire STL a été relu et sa boîte englobante mesurée.',byteLength:evidence.byteLength,triangles:evidence.triangles,dimensionsMm:[...evidence.dimsMm]};
}

function assess(piece,machine) {
  const r=machine.record;
  const knownTechnology=machine.declared && TECHNOLOGIES.includes(r.technology) && TECHNOLOGIES.includes(piece.tech);
  const technologyStatus=knownTechnology?(piece.tech===r.technology?'match':'mismatch'):'unknown';
  const measured=piece.file.status==='measured';
  const volumetric=measured && finiteDimensions(piece.dimensionsMm);
  const volumeKnown=machine.declared && finiteDimensions(r.usableVolumeMm);
  const orientations=volumetric && volumeKnown ? PREPARATION_ORIENTATIONS.map(orientation=>{
    const dimensionsMm=orientation.axes.map(axis=>piece.dimensionsMm[axis]);
    const clearanceMm=dimensionsMm.map((n,axis)=>r.usableVolumeMm[axis]-n);
    return {id:orientation.id,dimensionsMm,clearanceMm,fits:clearanceMm.every(n=>n>=0)};
  }) : [];
  const envelopeStatus=orientations.length?(orientations.some(o=>o.fits)?'fits':'exceeds'):'unknown';
  const fitOrientationIds=technologyStatus==='match'?orientations.filter(o=>o.fits).map(o=>o.id):[];
  let status,label;
  if(!machine.declared) [status,label]=['not_declared','Machine à renseigner'];
  else if(technologyStatus==='unknown') [status,label]=['technology_unknown','Procédé à renseigner'];
  else if(technologyStatus==='mismatch') [status,label]=['technology_mismatch','Procédé différent'];
  else if(!volumeKnown) [status,label]=['volume_missing','Volume utile à renseigner'];
  else if(piece.file.status==='unreferenced') [status,label]=['file_missing','Aucun STL associé'];
  else if(piece.file.status==='unchecked') [status,label]=['file_unchecked','STL à relire'];
  else if(piece.file.status==='missing') [status,label]=['file_missing','STL absent de ce poste'];
  else if(piece.file.status==='invalid') [status,label]=['file_invalid','STL à vérifier'];
  else if(!volumetric) [status,label]=['non_volumetric','Boîte sans volume'];
  else if(envelopeStatus==='fits') [status,label]=['fits','Boîte brute dans le volume'];
  else [status,label]=['exceeds','Dépasse aux angles testés'];
  const missingProfiles=[!r.slicer.name&&'Slicer',!r.slicer.version&&'Version du slicer',!r.slicer.machineProfile&&'Profil machine',!r.slicer.materialProfile&&'Profil matière'].filter(Boolean);
  const issues=[];
  if(status!=='fits') issues.push({code:status,label,action:['not_declared','technology_unknown','volume_missing'].includes(status)?'fleet':['file_missing','file_unchecked','file_invalid'].includes(status)?'import':'inspect'});
  if(machine.declared && !r.volumeSource) issues.push({code:'volume_source_missing',label:'Source du volume utile à documenter.',action:'fleet'});
  if(machine.declared && missingProfiles.length) issues.push({code:'profiles_missing',label:'Slicer et profils à compléter : '+missingProfiles.join(', ')+'.',action:'fleet'});
  issues.push({code:'material_unspecified',label:'La matière requise par cette pièce n’est pas spécifiée ; sa compatibilité reste à établir.',action:'inspect'});
  if(machine.declared && r.qualification.status!=='documented') issues.push({code:'test_not_documented',label:r.qualification.status==='needs_review'?'La configuration a changé ; l’essai est à reprendre.':'Essai de la configuration à documenter.',action:'fleet'});
  if(piece.measurementsMatchRecord===false) issues.push({code:'stored_measurements_differ',label:'Les dimensions mesurées diffèrent de celles du dossier ; ce contrôle utilise le fichier relu.',action:'inspect'});
  return {machineId:machine.id,status,label,technologyStatus,envelopeStatus,orientations,fitOrientationIds,bestOrientationId:fitOrientationIds[0]??null,
    material:{declared:r.material,status:'unspecified'},profiles:{declared:machine.declared && missingProfiles.length===0,missing:missingProfiles},
    qualification:{...copy(r.qualification),verified:false},issues};
}

/** An explicit project and current file evidence are required; no active-project fallback. */
export function inspectDeclaredPreparation(state,projectId,{assetEvidence=[]}={}) {
  const project=exactState(state,projectId);
  if(!Array.isArray(assetEvidence)) fail('Les contrôles de fichiers doivent être une liste.');
  const machines=state.machines.map(machine=>{
    const record=fleetRecordOf(machine),declared=record.origin==='declared';
    const identity=declared?[record.manufacturer,record.model].filter(Boolean).join(' '):'';
    return {id:machine.id,name:identity || (declared?record.serial:'') || machine.id,declared,record:copy(record)};
  });
  const pieces=project.pieces.map(source=>{
    const file=inspectFile(projectId,source,assetEvidence);
    const dimensionsMm=file.status==='measured'?[...file.dimensionsMm]:null;
    delete file.dimensionsMm;
    const storedDimensionsMm=finiteDimensions(source.dims,true)?[...source.dims]:null;
    const measurementsMatchRecord=dimensionsMm && storedDimensionsMm ? dimensionsMm.every((n,i)=>Math.abs(n-storedDimensionsMm[i])<=Math.max(0.000001,Math.abs(n)*1e-9)) : null;
    const piece={id:source.id,name:typeof source.name==='string'?source.name:source.id,revision:safeNumber(source.revision),tech:TECHNOLOGIES.includes(source.tech)?source.tech:'unknown',unit:source.unit??'mm',assetId:source.assetId||null,assetSha256:source.assetSha256||null,storedDimensionsMm,dimensionsMm,file,measurementsMatchRecord};
    return {...piece,assessments:machines.map(machine=>assess(piece,machine))};
  });
  const countFile=status=>pieces.filter(piece=>piece.file.status===status).length;
  return {format:'bojart.declared-preparation.v1',brand:'BOJ.ART',
    project:{id:project.id,name:typeof project.name==='string'?project.name:project.id,revision:safeNumber(project.revision),quantity:safeNumber(project.quantity),targetHeightMm:typeof project.height==='number' && Number.isFinite(project.height) && project.height>0?project.height:null},
    machines,pieces,summary:{totalPieces:pieces.length,totalMachines:machines.length,declaredMachines:machines.filter(m=>m.declared).length,
      measuredFiles:countFile('measured'),unreferencedFiles:countFile('unreferenced'),uncheckedFiles:countFile('unchecked'),missingFiles:countFile('missing'),invalidFiles:countFile('invalid'),
      nonVolumetricPieces:pieces.filter(p=>p.file.status==='measured' && !finiteDimensions(p.dimensionsMm)).length,piecesWithEnvelopeFit:pieces.filter(p=>p.assessments.some(a=>a.status==='fits')).length},
    limitations:[...LIMITATIONS],canSlice:false,canStartPhysicalPrint:false};
}

/** Export the inspected snapshot and an optional inspected selection, never the current UI project. */
export function exportDeclaredPreparation(report,selection={},at) {
  plain(report,'Rapport de préparation');plain(selection,'Sélection de préparation');
  if(report.format!=='bojart.declared-preparation.v1' || report.brand!=='BOJ.ART' || !report.project || !Array.isArray(report.pieces) || !Array.isArray(report.machines) || report.canSlice!==false || report.canStartPhysicalPrint!==false) fail('Le rapport de préparation n’est pas reconnu.');
  id(report.project.id,'Identifiant du dossier du rapport');
  if(typeof at!=='number' || !Number.isFinite(at) || at<0 || at>8.64e15) fail('Une date d’export explicite est requise.');
  for(const key of Object.keys(selection)) if(!['pieceId','machineId','orientationId'].includes(key)) fail('Champ de sélection inconnu : '+key+'.');
  const chosen={pieceId:selection.pieceId??null,machineId:selection.machineId??null,orientationId:selection.orientationId??null};
  const piece=chosen.pieceId===null?null:report.pieces.find(p=>p.id===chosen.pieceId);
  const machine=chosen.machineId===null?null:report.machines.find(m=>m.id===chosen.machineId);
  if(chosen.pieceId!==null && !piece) throw new RangeError('La pièce sélectionnée ne figure pas dans ce rapport.');
  if(chosen.machineId!==null && !machine) throw new RangeError('La machine sélectionnée ne figure pas dans ce rapport.');
  const assessment=piece && machine?piece.assessments.find(a=>a.machineId===machine.id):null;
  const orientation=chosen.orientationId===null?null:assessment?.orientations.find(o=>o.id===chosen.orientationId);
  if(chosen.orientationId!==null && !orientation) throw new RangeError('L’orientation sélectionnée n’a pas été calculée pour cette paire.');
  if(report.pieces.some(p=>!FILE_STATES.includes(p.file?.status))) fail('Un état de fichier du rapport est invalide.');
  return {format:'bojart.declared-preparation-export.v1',brand:'BOJ.ART',exportedAt:at,scope:'declared_registry_and_current_local_stl_measurements',
    project:copy(report.project),selection:copy(chosen),selectedAssessment:assessment?copy(assessment):null,selectedOrientation:orientation?copy(orientation):null,
    report:copy(report),execution:{slicingRequested:false,physicalPrintRequested:false,geometryModified:false,stlIncluded:false}};
}
