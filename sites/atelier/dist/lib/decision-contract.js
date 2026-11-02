/** BOJ.ART — closed, advisory decisions. This module has no execution adapter. */
import {PREPARATION_ORIENTATIONS} from './preparation.js';
import {EDIT_SERIES} from './edit-plan.js';
import {CONTENT_CATALOG_VERSION} from './content-catalog.js';

export const DECISION_POLICY_VERSION = 'bojart.jev-advisory.2026-10-19.v1';
export const DECISION_REQUEST_FORMAT = 'bojart.decision-request.v1';
export const DECISION_RESPONSE_FORMAT = 'bojart.decision-response.v1';
export const DECISION_LIMITS = Object.freeze({requestBytes:65536,responseBytes:65536,candidates:64,ageMs:60000,minProbability:.8,minMargin:.15});
const freeze = value => {if(value && typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
export const DECISION_DOMAINS = freeze([
  {id:'visual',label:'Trois écrans',status:'existing_visual_router',question:'Quelle vue disponible répond à la demande ?',evidence:['Projet et révision','Catalogue de vues','Accusé de l’écran'],output:'Présentation ciblée',limits:['Aucun lancement de fabrication','Aucun média généré']},
  {id:'preparation',label:'Préparation 3D',status:'implemented_advisory',question:'Quelle orientation brute examiner parmi celles qui tiennent dans le volume déclaré ?',evidence:['STL mesuré','Pièce et fichier identifiés','Fiche machine versionnée'],output:'Orientation à examiner',limits:['Boîte brute uniquement','Supports, solidité et imprimabilité non évalués','Aucun slicing ni changement de fichier']},
  {id:'attention',label:'Prochaine vérification',status:'implemented_advisory',question:'Quel élément existant du dossier examiner ensuite ?',evidence:['États des fichiers','Fiches du parc','Versions des intentions de montage'],output:'Élément à ouvrir',limits:['Aucune télémétrie machine','Aucune résolution automatique d’incident','Les travaux de simulation sont exclus']},
  {id:'editorial',label:'Direction éditoriale',status:'implemented_advisory',question:'Quelle série BOJ.ART choisir comme intention de départ ?',evidence:['Cinq séries écrites','Type de projet déclaré','Plan enregistré éventuel'],output:'Série à préparer',limits:['Aucune analyse visuelle des rushes','Aucun rendu, coupe ou publication','La relation média-projet reste une déclaration']},
  {id:'slicing',label:'Slicing',status:'future_contract',question:'Quelle recette déjà qualifiée répond aux priorités ?',evidence:['Profils conservés et empreintes','Matière et configuration qualifiées','Sortie du slicer'],output:'Recette candidate',limits:['Moteur de slicing à raccorder','Jev ne calcule pas les couches']},
  {id:'scheduling',label:'Répartition des plateaux',status:'future_contract',question:'Quel planning valide convient au délai et aux ressources ?',evidence:['Plateaux réalisables','Disponibilités fraîches','Opérations humaines'],output:'Planning proposé',limits:['Planificateur et connecteurs à qualifier','Pas d’ordre physique depuis Jev']},
  {id:'quality',label:'Qualité et incidents',status:'future_contract',question:'Quelle preuve ou procédure examiner ?',evidence:['Travail machine identifié','État et fraîcheur de télémétrie','Contrôles documentés'],output:'Priorité d’examen',limits:['Une réponse inconnue ne vaut pas un échec','Aucune relance d’impression automatique']},
  {id:'commercial',label:'Demandes et offres',status:'future_contract',question:'Quelle offre qualifiée correspond au brief ?',evidence:['Capacités vérifiées','Coût calculé','Droits et contraintes du dossier'],output:'Offre à préparer',limits:['Jev ne calcule pas le prix final','Aucun message client ni engagement envoyé']},
  {id:'publication',label:'Diffusion des contenus',status:'future_contract',question:'Quelle variante approuvée préparer pour quel canal ?',evidence:['Rendu et droits identifiés','Compte et parcours admissibles','Aperçu de publication'],output:'Paquet de publication',limits:['Connecteur non raccordé','Aucune publication depuis ce service']},
  {id:'robotics',label:'Prototypes et robotique',status:'future_contract',question:'Quel essai documenté prépare la prochaine étape ?',evidence:['Exigences','Pièces et actionneurs identifiés','Résultats d’essai'],output:'Protocole à examiner',limits:['Commandes d’actionneurs séparées','Aucune qualification déduite du modèle']}
]);
const GOALS = Object.freeze({preparation:['clearance','low_height','balanced'],attention:['blockers','next_step'],editorial:['showcase','technique','custom_order','prototype','offer']});
const FILE_STATES=['unreferenced','unchecked','missing','invalid','measured'];
const QUALIFICATION=['not_started','in_progress','documented','needs_review'];
const SERIES=EDIT_SERIES.map(value=>value.id);
const EXECUTION=freeze({advisoryOnly:true,canSlice:false,canStartPhysicalPrint:false,canRender:false,canPublish:false,canModifyProject:false});
export class DecisionError extends Error {
  constructor(code,message,status=400){super(message);this.name='DecisionError';this.code=code;this.status=status;}
}
const fail=(message='La demande de décision est invalide.',code='invalid_request',status=400)=>{throw new DecisionError(code,message,status);};
const plain=value=>!!value && typeof value==='object' && !Array.isArray(value) && [Object.prototype,null].includes(Object.getPrototypeOf(value));
function keys(value,allowed,label,required=allowed){
  if(!plain(value))fail(label+' doit être un objet simple.');
  for(const key of Reflect.ownKeys(value)){
    const descriptor=Object.getOwnPropertyDescriptor(value,key);
    if(typeof key!=='string'||!allowed.includes(key)||!descriptor?.enumerable||!Object.hasOwn(descriptor,'value'))fail(label+' contient un champ non autorisé.');
  }
  if(required.some(key=>!Object.hasOwn(value,key)))fail(label+' est incomplet.');
}
function identifier(value,label='Identifiant'){
  if(typeof value!=='string'||!value.trim()||value.trim()!==value||value.length>200||/[\u0000-\u001f\u007f]/.test(value))fail(label+' invalide.');
  return value;
}
function integer(value,min=0,max=Number.MAX_SAFE_INTEGER){if(!Number.isSafeInteger(value)||value<min||value>max)fail('Une valeur entière est invalide.');return value;}
function boolean(value){if(typeof value!=='boolean')fail('Une déclaration doit être booléenne.');return value;}
function enumeration(value,values){if(!values.includes(value))fail('Une valeur ne fait pas partie du catalogue autorisé.');return value;}
function list(value,max){if(!Array.isArray(value)||value.length>max||Reflect.ownKeys(value).length!==value.length+1||Object.keys(value).some((key,index)=>key!==String(index)))fail('La liste est invalide ou trop longue.');return value;}
function unique(values){if(new Set(values).size!==values.length)fail('Des éléments partagent le même identifiant.');}
function dims(value,max=1000000){list(value,3);if(value.length!==3||value.some(n=>typeof n!=='number'||!Number.isFinite(n)||n<=0||n>max))fail('Trois dimensions positives sont requises.');return [...value];}
function sha(value){if(value===null)return null;if(typeof value!=='string'||!/^([a-f0-9]{64})$/i.test(value))fail('Empreinte de fichier invalide.');return value.toLowerCase();}
function context(raw){keys(raw,['projectId','projectRevision'],'Contexte');return{projectId:identifier(raw.projectId),projectRevision:integer(raw.projectRevision,1)};}
function machine(raw){
  keys(raw,['id','revision','declared','technology','usableVolumeMm','profilesDeclared','qualificationStatus'],'Fiche machine');
  const item={id:identifier(raw.id),revision:integer(raw.revision),declared:boolean(raw.declared),technology:enumeration(raw.technology,['unknown','fdm','resin']),usableVolumeMm:raw.usableVolumeMm===null?null:dims(raw.usableVolumeMm,10000),profilesDeclared:boolean(raw.profilesDeclared),qualificationStatus:enumeration(raw.qualificationStatus,QUALIFICATION)};
  if(item.declared&&item.revision<1)fail('La fiche déclarée doit avoir une révision.');
  return item;
}
function attentionPiece(raw){
  keys(raw,['id','revision','assetId','unit','fileStatus','sha256','technology','hasEnvelopeFit'],'État de pièce');
  const item={id:identifier(raw.id),revision:integer(raw.revision,1),assetId:raw.assetId===null?null:identifier(raw.assetId),unit:enumeration(raw.unit,['mm','inch','unknown']),fileStatus:enumeration(raw.fileStatus,FILE_STATES),sha256:sha(raw.sha256),technology:enumeration(raw.technology,['fdm','resin','unknown']),hasEnvelopeFit:boolean(raw.hasEnvelopeFit)};
  if(item.fileStatus==='unreferenced'&&item.assetId!==null||item.fileStatus!=='unreferenced'&&item.assetId===null||item.fileStatus!=='measured'&&item.hasEnvelopeFit)fail('Les preuves de la pièce sont incohérentes.');
  return item;
}
function edit(raw){
  keys(raw,['id','revision','series','sourceCount','availableSourceCount','assignedBeats','rangedVideoBeats','videoBeats'],'Intention de montage');
  const item={id:identifier(raw.id),revision:integer(raw.revision,1,50),series:enumeration(raw.series,SERIES),sourceCount:integer(raw.sourceCount,0,31),availableSourceCount:integer(raw.availableSourceCount,0,31),assignedBeats:integer(raw.assignedBeats,0,4),rangedVideoBeats:integer(raw.rangedVideoBeats,0,4),videoBeats:integer(raw.videoBeats,0,4)};
  if(item.availableSourceCount>item.sourceCount||item.videoBeats>item.assignedBeats||item.rangedVideoBeats>item.videoBeats||item.sourceCount===0&&item.assignedBeats>0)fail('Les preuves du montage sont incohérentes.');
  return item;
}
function evidence(domain,raw){
  if(domain==='preparation'){
    keys(raw,['source','piece','machine'],'Preuves de préparation');
    if(raw.source!=='declared_preparation_v1')fail('Source de préparation inconnue.');
    keys(raw.piece,['id','revision','assetId','unit','sha256','technology','dimensionsMm'],'Mesure de pièce');
    const piece={id:identifier(raw.piece.id),revision:integer(raw.piece.revision,1),assetId:identifier(raw.piece.assetId),unit:enumeration(raw.piece.unit,['mm','inch']),sha256:sha(raw.piece.sha256),technology:enumeration(raw.piece.technology,['fdm','resin']),dimensionsMm:dims(raw.piece.dimensionsMm)};
    return{source:raw.source,piece,machine:machine(raw.machine)};
  }
  if(domain==='attention'){
    keys(raw,['source','catalogueVersion','pieces','machines','edits'],'Preuves du dossier');
    if(raw.source!=='preparation_and_saved_edits_v1'||raw.catalogueVersion!==CONTENT_CATALOG_VERSION)fail('La version du catalogue ne correspond pas à ce service.');
    const pieces=list(raw.pieces,64).map(attentionPiece),machines=list(raw.machines,32).map(machine),edits=list(raw.edits,20).map(edit);
    [pieces,machines,edits].forEach(items=>unique(items.map(item=>item.id)));
    return{source:raw.source,catalogueVersion:raw.catalogueVersion,pieces,machines,edits};
  }
  keys(raw,['source','catalogueVersion','projectKind','plan'],'Preuves éditoriales');
  if(raw.source!=='editorial_series_v1'||raw.catalogueVersion!==CONTENT_CATALOG_VERSION)fail('La version du catalogue éditorial ne correspond pas à ce service.');
  return{source:raw.source,catalogueVersion:raw.catalogueVersion,projectKind:enumeration(raw.projectKind,['sculpture','art','prototype','other']),plan:raw.plan===null?null:edit(raw.plan)};
}

/** Closed schema. The server regenerates choices; no prompts, tools, URLs or labels are accepted. */
export function normalizeDecisionRequest(raw){
  keys(raw,['format','policyVersion','requestId','domain','goal','context','evidence'],'Demande');
  if(raw.format!==DECISION_REQUEST_FORMAT||raw.policyVersion!==DECISION_POLICY_VERSION)fail('La version du contrat Jev ne correspond pas à ce service.','policy_mismatch',409);
  if(!Object.hasOwn(GOALS,raw.domain))fail('Ce domaine n’est pas encore raccordé aux décisions Jev.','domain_unavailable',409);
  const request={format:DECISION_REQUEST_FORMAT,policyVersion:DECISION_POLICY_VERSION,requestId:identifier(raw.requestId),domain:raw.domain,goal:enumeration(raw.goal,GOALS[raw.domain]),context:context(raw.context),evidence:evidence(raw.domain,raw.evidence)};
  if(new TextEncoder().encode(JSON.stringify(request)).byteLength>DECISION_LIMITS.requestBytes)fail('Le paquet de preuves dépasse 64 Kio.','body_too_large',413);
  const candidates=candidatesOf(request);
  if(candidates.length>DECISION_LIMITS.candidates)fail('Sélectionnez un périmètre plus petit : plus de 64 éléments demandent un examen.','too_many_candidates',409);
  return request;
}

const formatNumber=value=>value.toLocaleString('fr-FR',{maximumFractionDigits:2});
const dimensionText=value=>value.map(formatNumber).join(' × ')+' mm';
const candidate=(id,label,summary,target,facts)=>({id,label,summary,target,facts});
function candidatesOf(request){
  const e=request.evidence,p=request.context.projectId;
  if(request.domain==='preparation'){
    if(!e.machine.declared||e.machine.technology!==e.piece.technology||!e.machine.usableVolumeMm)return[];
    return PREPARATION_ORIENTATIONS.flatMap(orientation=>{
      const dimensions=orientation.axes.map(axis=>e.piece.dimensionsMm[axis]);
      const clearance=dimensions.map((value,index)=>e.machine.usableVolumeMm[index]-value);
      if(clearance.some(value=>value<0))return[];
      return[candidate('orientation:'+orientation.id,orientation.label,dimensionText(dimensions)+' · marge minimale '+formatNumber(Math.min(...clearance))+' mm',{action:'inspect_orientation',projectId:p,pieceId:e.piece.id,machineId:e.machine.id,orientationId:orientation.id},{kind:'raw_envelope_orientation',orientation:orientation.id,dimensionsMm:dimensions,clearanceMm:clearance})];
    });
  }
  if(request.domain==='editorial')return EDIT_SERIES.map(series=>candidate('series:'+series.id,series.label,series.description,{action:'prepare_series',projectId:p,series:series.id,planId:e.plan?.id??null},{kind:'editorial_intention',series:series.id}));
  const result=[];
  for(const piece of e.pieces){
    const problem=piece.fileStatus==='unreferenced'?'file_unreferenced':piece.fileStatus==='missing'?'file_missing':piece.fileStatus==='invalid'?'file_invalid':piece.fileStatus==='unchecked'?'file_unchecked':piece.technology==='unknown'?'technology_unknown':!piece.hasEnvelopeFit?'envelope_unresolved':'requirements_unqualified';
    const copy={file_unreferenced:['Associer un STL','Aucun fichier n’est associé à cette pièce.'],file_missing:['Retrouver le STL','Le binaire référencé est absent de ce poste.'],file_invalid:['Vérifier le STL','Le contrôle de ce fichier a échoué.'],file_unchecked:['Relire le STL','Le binaire n’a pas encore été mesuré dans ce contexte.'],technology_unknown:['Préciser le procédé','Le procédé de cette pièce reste à déclarer.'],envelope_unresolved:['Examiner le volume','Aucune paire pièce-machine mesurée ne présente de boîte compatible.'],requirements_unqualified:['Définir les exigences','La boîte est mesurée ; matière, supports et qualification de fabrication restent à établir.']}[problem];
    result.push(candidate('piece:'+piece.id,copy[0]+' · '+piece.id,copy[1],{action:'inspect_piece',projectId:p,pieceId:piece.id},{kind:'piece_review',problem,fileStatus:piece.fileStatus,technology:piece.technology}));
  }
  for(const item of e.machines){
    const problem=!item.declared?'machine_undeclared':item.technology==='unknown'||!item.usableVolumeMm?'machine_geometry_missing':!item.profilesDeclared?'profiles_missing':item.qualificationStatus!=='documented'?'qualification_undocumented':null;
    if(!problem)continue;
    const copy={machine_undeclared:['Déclarer la machine','Cette place du parc ne possède pas de fiche réelle déclarée.'],machine_geometry_missing:['Compléter le volume','Procédé ou dimensions utiles manquants dans la fiche.'],profiles_missing:['Compléter les profils','Slicer, version ou références de profils incomplets.'],qualification_undocumented:['Documenter l’essai','L’essai de la configuration reste à documenter ou à reprendre.']}[problem];
    result.push(candidate('machine:'+item.id,copy[0]+' · '+item.id,copy[1],{action:'inspect_machine',projectId:p,machineId:item.id},{kind:'machine_record_review',problem,technology:item.technology,qualificationStatus:item.qualificationStatus}));
  }
  for(const item of e.edits){
    const problem=item.availableSourceCount<item.sourceCount?'edit_media_unavailable':item.assignedBeats<4?'edit_sources_missing':item.rangedVideoBeats<item.videoBeats?'edit_ranges_missing':'edit_render_unconnected';
    const copy={edit_media_unavailable:['Vérifier les médias','Une source est déclarée indisponible dans le catalogue.'],edit_sources_missing:['Choisir les plans','Les quatre moments ne possèdent pas encore tous une source.'],edit_ranges_missing:['Définir les passages','Des plans vidéo n’ont pas de repères dans l’original.'],edit_render_unconnected:['Examiner l’intention','Le plan enregistré existe ; le rendu vidéo reste à raccorder.']}[problem];
    result.push(candidate('edit:'+item.id,copy[0]+' · '+item.id,copy[1],{action:'inspect_edit',projectId:p,planId:item.id,planRevision:item.revision},{kind:'saved_edit_review',problem,series:item.series,assignedBeats:item.assignedBeats}));
  }
  if(!e.edits.length)result.push(candidate('edit:new','Préparer une intention de montage','Aucun plan de montage enregistré dans ce dossier.',{action:'create_edit',projectId:p},{kind:'new_edit_intention',problem:'no_saved_edit'}));
  return result;
}
export function decisionCandidates(raw){return candidatesOf(normalizeDecisionRequest(raw));}

/** The complete local packet is hashed; identifiers and hashes are never sent to TypeSafe. */
export async function decisionFingerprint(raw){
  const request=normalizeDecisionRequest(raw);
  if(!globalThis.crypto?.subtle)fail('Le contrôle d’intégrité des décisions est indisponible dans ce navigateur.','integrity_unavailable',503);
  const encoded=new TextEncoder().encode(JSON.stringify(request));
  const digest=await globalThis.crypto.subtle.digest('SHA-256',encoded);
  return'sha256:'+Array.from(new Uint8Array(digest),value=>value.toString(16).padStart(2,'0')).join('');
}

function localChoice(request,candidates){
  if(!candidates.length)return null;
  if(request.domain==='editorial')return candidates.find(item=>item.facts.series===({showcase:'oeuvres',technique:'geste',custom_order:'sur_mesure',prototype:'prototype',offer:'disponible'})[request.goal]);
  if(request.domain==='preparation'){
    const volume=request.evidence.machine.usableVolumeMm;
    const score=item=>request.goal==='low_height'?-item.facts.dimensionsMm[2]:request.goal==='clearance'?Math.min(...item.facts.clearanceMm):Math.min(...item.facts.clearanceMm.map((value,index)=>value/volume[index]));
    return candidates.map((item,index)=>({item,index,score:score(item)})).sort((a,b)=>b.score-a.score||a.item.facts.dimensionsMm[2]-b.item.facts.dimensionsMm[2]||a.index-b.index)[0].item;
  }
  const priority={file_invalid:0,file_missing:0,file_unreferenced:1,file_unchecked:2,technology_unknown:3,machine_undeclared:3,machine_geometry_missing:3,envelope_unresolved:4,profiles_missing:5,qualification_undocumented:6,requirements_unqualified:7,edit_media_unavailable:8,edit_sources_missing:9,edit_ranges_missing:10,edit_render_unconnected:11,no_saved_edit:12};
  return candidates.map((item,index)=>({item,index,score:priority[item.facts.problem]??99})).sort((a,b)=>a.score-b.score||a.index-b.index)[0].item;
}
export function decisionRuleExplanation(raw){
  const request=normalizeDecisionRequest(raw);
  if(request.domain==='preparation')return{clearance:'Règle locale : marge minimale de boîte brute la plus grande, puis hauteur la plus faible.',low_height:'Règle locale : hauteur brute la plus faible parmi les orientations compatibles.',balanced:'Règle locale : marge minimale relative au volume utile la plus grande, puis hauteur la plus faible.'}[request.goal];
  if(request.domain==='editorial')return'Règle locale : série correspondant à l’objectif choisi. Aucun rush n’a été analysé par une IA.';
  return'Règle locale : fichiers absents ou invalides, données de fabrication, puis intentions de montage. Cette priorité est explicite et modifiable manuellement.';
}
export async function recommendLocalDecision(raw,{now=Date.now}={}){
  const request=normalizeDecisionRequest(raw),candidates=candidatesOf(request),choice=localChoice(request,candidates);
  const at=integer(now(),0,8.64e15);
  return{format:DECISION_RESPONSE_FORMAT,policyVersion:DECISION_POLICY_VERSION,ok:true,requestId:request.requestId,domain:request.domain,context:request.context,packetHash:await decisionFingerprint(request),provider:'local_rules',model:null,at,provenance:'client_snapshot_advisory',decision:{candidateId:choice?.id??null,selectedCandidateId:choice?.id??null,reason:choice?'local_rule':'no_candidates',probability:null,margin:null,confidence:null,probabilities:null},thresholds:null,execution:{...EXECUTION}};
}
export function decisionExecutionLimits(){return{...EXECUTION};}

/** Checks origin, full packet, schema, expiry and all scores before a UI may use a result. */
export async function validateProjectDecision(raw,input,{now=Date.now}={}){
  const request=normalizeDecisionRequest(input);
  const invalid=message=>fail(message,'invalid_response',502);
  try{keys(raw,['format','policyVersion','ok','requestId','domain','context','packetHash','provider','model','at','provenance','decision','thresholds','execution'],'Résultat');}catch{invalid('Le résultat ne respecte pas le contrat de décision.');}
  if(raw.format!==DECISION_RESPONSE_FORMAT||raw.policyVersion!==DECISION_POLICY_VERSION||raw.ok!==true||raw.requestId!==request.requestId||raw.domain!==request.domain||JSON.stringify(raw.context)!==JSON.stringify(request.context)||raw.provenance!=='client_snapshot_advisory')invalid('Le résultat Jev ne correspond pas à cette demande.');
  if(!Number.isSafeInteger(raw.at)||raw.at<0||raw.at>8.64e15)invalid('La date de décision est invalide.');
  const current=now();
  if(!Number.isSafeInteger(current)||raw.at>current+5000||current-raw.at>DECISION_LIMITS.ageMs)fail('Ce conseil a expiré ; demandez une nouvelle comparaison.','decision_expired',409);
  if(raw.packetHash!==await decisionFingerprint(request))fail('Le dossier ou ses preuves ont changé ; ce conseil est périmé.','context_changed',409);
  try{keys(raw.execution,Object.keys(EXECUTION),'Limites');if(Object.keys(EXECUTION).some(key=>raw.execution[key]!==EXECUTION[key]))invalid('Une décision ne peut pas ajouter de capacité d’exécution.');keys(raw.decision,['candidateId','selectedCandidateId','reason','probability','margin','confidence','probabilities'],'Choix');}catch{invalid('Les limites ou le choix de décision sont invalides.');}
  const d=raw.decision,options=candidatesOf(request),ids=options.map(value=>value.id);
  if(raw.provider==='local_rules'){
    const selected=localChoice(request,options)?.id??null;
    if(raw.model!==null||raw.thresholds!==null||d.candidateId!==selected||d.selectedCandidateId!==selected||d.reason!==(selected?'local_rule':'no_candidates')||[d.probability,d.margin,d.confidence,d.probabilities].some(value=>value!==null))invalid('Le conseil local contient un choix ou un score inattendu.');
  }else if(raw.provider==='typesafe'){
    if(typeof raw.model!=='string'||!/^jev-\d+\.\d+\.\d+$/.test(raw.model))invalid('Le modèle Jev effectif n’est pas identifié.');
    const values=[...ids,'none'];
    try{keys(d.probabilities,values,'Probabilités');keys(raw.thresholds,['minProbability','minMargin','experimental'],'Seuils');}catch{invalid('Les scores ne couvrent pas exactement les candidats disponibles.');}
    const t=raw.thresholds,probability=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0&&value<=1;
    if(!values.every(id=>probability(d.probabilities[id]))||!probability(d.confidence)||!probability(t.minProbability)||!probability(t.minMargin)||t.minProbability<DECISION_LIMITS.minProbability||t.minMargin<DECISION_LIMITS.minMargin||t.experimental!==true)invalid('Les probabilités ou seuils sont invalides.');
    if(!values.includes(d.selectedCandidateId))invalid('Le modèle a choisi un candidat inconnu.');
    const top=d.probabilities[d.selectedCandidateId],others=values.filter(id=>id!==d.selectedCandidateId).map(id=>d.probabilities[id]),margin=top-Math.max(0,...others);
    if(values.some(id=>d.probabilities[id]>top+1e-8)||Math.abs(values.reduce((sum,id)=>sum+d.probabilities[id],0)-1)>.001||!probability(d.probability)||!probability(d.margin)||Math.abs(d.probability-top)>1e-8||Math.abs(d.margin-margin)>1e-8)invalid('Le choix et la distribution de Jev sont incohérents.');
    const accepted=d.selectedCandidateId!=='none'&&top+1e-10>=t.minProbability&&margin+1e-10>=t.minMargin;
    if(d.candidateId!==(accepted?d.selectedCandidateId:null)||d.reason!==(d.selectedCandidateId==='none'?'no_match':accepted?'selected':'uncertain'))invalid('Le choix ne respecte pas le seuil d’abstention.');
  }else invalid('Le fournisseur de décision est inconnu.');
  return JSON.parse(JSON.stringify(raw));
}
