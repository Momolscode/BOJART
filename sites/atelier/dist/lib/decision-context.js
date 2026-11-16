/** Project-bound projections. Names, notes, URLs, secrets and binaries stay out of the request. */
import {DECISION_REQUEST_FORMAT,DECISION_POLICY_VERSION,DecisionError,normalizeDecisionRequest,decisionCandidates} from './decision-contract.js';
import {projectEditPlans,latestEditVersion} from './edit-plan.js';
import {CONTENT_CATALOG_VERSION,getContentSource} from './content-catalog.js';

const fail=message=>{throw new DecisionError('invalid_context',message,409);};
const copy=value=>JSON.parse(JSON.stringify(value));
const empty=message=>({request:null,options:[],unavailableReason:message});
const unit=value=>['mm','inch'].includes(value)?value:'unknown';
const technology=value=>['fdm','resin'].includes(value)?value:'unknown';
function projectContext(project){
  if(!project||typeof project.id!=='string'||!project.id||!Number.isSafeInteger(project.revision)||project.revision<1)fail('Le dossier et sa révision sont requis.');
  return{projectId:project.id,projectRevision:project.revision};
}
function reportContext(report){
  if(report?.format!=='bojart.declared-preparation.v1'||report.brand!=='BOJ.ART'||!Array.isArray(report.pieces)||!Array.isArray(report.machines)||report.canSlice!==false||report.canStartPhysicalPrint!==false)fail('Un rapport de préparation actuel est requis.');
  return projectContext(report.project);
}
function only(items,id,label){
  const values=items.filter(item=>item?.id===id);
  if(values.length!==1)fail(label+' est introuvable ou ambigu.');
  return values[0];
}
function machineEvidence(item){
  if(!item?.record)fail('La fiche de machine du rapport est absente.');
  const record=item.record,s=record.slicer||{};
  return{id:item.id,revision:record.revision,declared:item.declared===true,technology:technology(record.technology),usableVolumeMm:record.usableVolumeMm?copy(record.usableVolumeMm):null,profilesDeclared:!!(s.name&&s.version&&s.machineProfile&&s.materialProfile),qualificationStatus:record.qualification?.status};
}
function editEvidence(record){
  const saved=latestEditVersion(record),plan=saved.plan;
  const videos=plan.beats.filter(beat=>beat.postId&&getContentSource(beat.postId)?.type==='video');
  return{id:record.id,revision:saved.revision,series:plan.series,sourceCount:plan.sources.length,availableSourceCount:plan.sources.filter(source=>getContentSource(source.postId)?.available===true).length,assignedBeats:plan.beats.filter(beat=>beat.postId!==null).length,rangedVideoBeats:videos.filter(beat=>beat.in!==null&&beat.out!==null).length,videoBeats:videos.length};
}
function finish(domain,goal,context,evidence,requestId,labels={}){
  const request=normalizeDecisionRequest({format:DECISION_REQUEST_FORMAT,policyVersion:DECISION_POLICY_VERSION,requestId,domain,goal,context,evidence});
  const options=decisionCandidates(request).map(option=>{
    const name=labels[option.id];
    return name?{...option,label:option.label.replace(/ · .*$/,'')+' · '+name}:option;
  });
  if(!options.length)return empty('Aucun candidat disponible dans ce périmètre. Choisissez une autre pièce ou complétez les données.');
  return{request,options,unavailableReason:null};
}

/** Six rotations are rebuilt from measured dimensions; they are never optimal print orientations. */
export function buildPreparationDecisionRequest(report,{requestId,pieceId,machineId,goal='balanced'}={}){
  const context=reportContext(report);
  if(!pieceId||!machineId)return empty('Sélectionnez une pièce et une machine dans l’établi.');
  const piece=only(report.pieces,pieceId,'La pièce'),machine=only(report.machines,machineId,'La machine');
  if(piece.file?.status!=='measured'||!piece.assetId)return empty('Relisez le STL de cette pièce avant de comparer ses orientations.');
  if(!Array.isArray(piece.dimensionsMm)||piece.dimensionsMm.length!==3||piece.dimensionsMm.some(value=>typeof value!=='number'||!Number.isFinite(value)||value<=0))return empty('Le STL doit présenter trois dimensions positives mesurées.');
  if(!['mm','inch'].includes(piece.unit))return empty('L’unité du STL doit être indiquée en millimètres ou en pouces.');
  if(!machine.declared||machine.record?.origin!=='declared')return empty('Choisissez une machine réellement déclarée dans le parc.');
  if(!['fdm','resin'].includes(piece.tech)||machine.record.technology!==piece.tech)return empty('Le procédé de la pièce doit correspondre au procédé déclaré de la machine.');
  if(!machine.record.usableVolumeMm)return empty('Complétez le volume utile déclaré de cette machine.');
  const evidence={source:'declared_preparation_v1',piece:{id:piece.id,revision:piece.revision,assetId:piece.assetId,unit:piece.unit,sha256:piece.file.sha256??null,technology:piece.tech,dimensionsMm:copy(piece.dimensionsMm)},machine:machineEvidence(machine)};
  return finish('preparation',goal,context,evidence,requestId);
}

/** Uses file, declared registry and saved-edit evidence only; no simulated job is read. */
export function buildAttentionDecisionRequest(report,project,{requestId,goal='blockers'}={}){
  const context=reportContext(report),current=projectContext(project);
  if(JSON.stringify(context)!==JSON.stringify(current)||!Array.isArray(project.pieces)||project.pieces.length!==report.pieces.length)fail('Le rapport appartient à un autre état du dossier.');
  const pieces=report.pieces.map(item=>{
    const stored=only(project.pieces,item.id,'La pièce du dossier');
    if((stored.revision??1)!==item.revision||(stored.assetId||null)!==(item.assetId||null)||unit(stored.unit??'mm')!==unit(item.unit)||technology(stored.tech)!==technology(item.tech))fail('Le fichier ou la révision d’une pièce a changé depuis le rapport.');
    return{id:item.id,revision:item.revision,assetId:item.assetId||null,unit:unit(item.unit),fileStatus:item.file?.status,sha256:item.file?.sha256??null,technology:technology(item.tech),hasEnvelopeFit:item.file?.status==='measured'&&item.assessments?.some(assessment=>assessment.status==='fits')===true};
  });
  const records=projectEditPlans(project);
  const evidence={source:'preparation_and_saved_edits_v1',catalogueVersion:CONTENT_CATALOG_VERSION,pieces,machines:report.machines.map(machineEvidence),edits:records.map(editEvidence)};
  const labels=Object.fromEntries([...project.pieces.map(item=>['piece:'+item.id,item.name||item.id]),...report.machines.map(item=>['machine:'+item.id,item.name||item.id]),...records.map(item=>['edit:'+item.id,latestEditVersion(item).plan.title])]);
  return finish('attention',goal,context,evidence,requestId,labels);
}

/** A proposed series is not a generated montage. Existing series remain the source of truth. */
export function buildEditorialDecisionRequest(project,{requestId,goal='showcase',planId=null}={}){
  const context=projectContext(project),records=projectEditPlans(project);
  let plan=null;
  if(planId!==null)plan=editEvidence(only(records,planId,'Le plan enregistré'));
  const evidence={source:'editorial_series_v1',catalogueVersion:CONTENT_CATALOG_VERSION,projectKind:['sculpture','art','prototype'].includes(project.kind)?project.kind:'other',plan};
  return finish('editorial',goal,context,evidence,requestId);
}
