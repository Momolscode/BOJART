import {verifyInquiryExport,canonicalJSON,sha256,UUID_RE,OFFERS,BUDGET_RANGES,MODEL_STATUSES} from './inquiry-contract.js';

export const INQUIRY_LINK_FORMAT='bojart.inquiry.link.v1';
export const INQUIRY_MAX_BYTES=65536;
export const INQUIRY_SOURCE_ORIGIN='https://bojart-studio.yellowghost64.chatgpt.site';
export const inquiryLabels=Object.freeze({
  offers:{artwork:'Œuvre & édition',custom:'Création sur mesure',prototype:'Prototype & petite série'},
  budgets:{undecided:'À définir',under_250:'Moins de 250 €','250_750':'250 à 750 €','750_1500':'750 à 1 500 €','1500_3000':'1 500 à 3 000 €',over_3000:'Plus de 3 000 €'},
  models:{idea:'Une idée à développer',reference:'Des références',file_ready:'Fichier prêt selon le demandeur'},
  statuses:{new:'Nouvelle demande',reviewing:'En cours d’examen',awaiting_details:'Précisions attendues',quoted:'Devis indiqué dans la source',accepted:'Accord indiqué dans la source',declined:'Non retenue',archived:'Archivée'}
});
const fail=message=>{throw new Error(message);};
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const iso=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)&&Number.isFinite(Date.parse(value))&&new Date(value).toISOString()===value;
const clone=value=>JSON.parse(JSON.stringify(value));

/** A strict technical projection. Contacts, original free text, campaign values,
 * links, and commercial status never enter the append-only workshop journal. */
export function normalizeInquiryLink(input){
  const keys=['format','requestId','reference','contentSha256','exportSha256','createdAt','updatedAt','revision','offer','quantity','dimensions','budgetRange','deadline','modelStatus'];
  if(!object(input)||Object.keys(input).some(key=>!keys.includes(key))||input.format!==INQUIRY_LINK_FORMAT)fail('Lien de demande technique invalide.');
  if(typeof input.requestId!=='string'||!UUID_RE.test(input.requestId)||input.requestId!==input.requestId.toLowerCase())fail('Identifiant de demande invalide.');
  if(typeof input.reference!=='string'||!/^BOJ-\d{8}-[A-F0-9]{12}$/.test(input.reference))fail('Référence de demande invalide.');
  for(const key of ['contentSha256','exportSha256'])if(typeof input[key]!=='string'||!/^[a-f0-9]{64}$/.test(input[key]))fail('Empreinte de demande invalide.');
  if(!iso(input.createdAt)||!iso(input.updatedAt)||input.updatedAt<input.createdAt)fail('Dates de demande invalides.');
  if(!Number.isSafeInteger(input.revision)||input.revision<1||input.revision>1000000)fail('Révision de demande invalide.');
  if(!OFFERS.includes(input.offer)||!BUDGET_RANGES.includes(input.budgetRange)||!MODEL_STATUSES.includes(input.modelStatus))fail('Paramètres de demande inconnus.');
  if(!Number.isSafeInteger(input.quantity)||input.quantity<1||input.quantity>1000)fail('Quantité de demande invalide.');
  if(input.dimensions!==undefined){
    if(!object(input.dimensions)||!Object.keys(input.dimensions).length||Object.keys(input.dimensions).some(key=>!['widthMm','heightMm','depthMm'].includes(key)))fail('Dimensions de demande invalides.');
    for(const value of Object.values(input.dimensions))if(typeof value!=='number'||!Number.isFinite(value)||value<=0||value>100000)fail('Dimensions de demande invalides.');
  }
  if(input.deadline!==undefined){
    const value=input.deadline;
    if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(Date.parse(value+'T00:00:00.000Z'))||new Date(value+'T00:00:00.000Z').toISOString().slice(0,10)!==value||Number(value.slice(0,4))<1900||Number(value.slice(0,4))>2100)fail('Date souhaitée invalide.');
  }
  return clone(input);
}
export function inquiryProjectId(link){return 'inquiry-'+normalizeInquiryLink(link).requestId;}
export function inquirySourceURL(link){return INQUIRY_SOURCE_ORIGIN+'/administration?demande='+normalizeInquiryLink(link).requestId;}

export function locateInquiry(state,link){
  const clean=normalizeInquiryLink(link),id=inquiryProjectId(clean);
  const matches=(state?.projects||[]).filter(project=>project.id===id||project.inquiry?.requestId===clean.requestId||project.inquiry?.reference===clean.reference);
  const existing=matches[0]||null;
  const conflict=matches.length>1||!!existing&&(!existing.inquiry||existing.inquiry.requestId!==clean.requestId||existing.inquiry.reference!==clean.reference||existing.inquiry.contentSha256!==clean.contentSha256);
  return {existing,conflict,matchCount:matches.length};
}

/** Compare only the two imported technical projections. This never compares
 * current working notes, costs or geometry, changes an import decision, or
 * infers which personal/source field changed from a content hash. */
export function compareInquiryRevisions(previousLink,receivedLink,{matchCount=1}={}){
  const unavailable=(code,message)=>({format:'bojart.inquiry.comparison.v1',available:false,code,message,rows:[],impacts:[],canApply:false});
  if(matchCount!==1)return unavailable('ambiguous_identity','Plusieurs dossiers correspondent à cette référence. Examinez leurs identités avant de rapprocher les paramètres.');
  let previous,received;
  try{previous=normalizeInquiryLink(previousLink);received=normalizeInquiryLink(receivedLink);}
  catch{return unavailable('projection_unavailable','La projection technique d’origine ne peut pas être relue. Retrouvez la demande source avant de comparer ses versions.');}
  if(previous.requestId!==received.requestId||previous.reference!==received.reference||previous.createdAt!==received.createdAt)return unavailable('identity_mismatch','L’identité ou la date d’origine de la demande diffère. Ces documents ne sont pas présentés comme deux versions de la même demande.');
  const definitions=[
    ['offer','Famille de projet',value=>inquiryLabels.offers[value],'Revoir le périmètre de l’étude et le procédé envisagé.'],
    ['quantity','Quantité demandée',value=>`${value} exemplaire${value>1?'s':''}`,'Réexaminer le coût du lot, les matières et la capacité de finition.'],
    ['widthMm','Largeur demandée',value=>value===null?'À préciser':`${value.toLocaleString('fr-FR')} mm`,'Réexaminer l’échelle, l’assemblage et l’encombrement des fichiers à préparer.'],
    ['heightMm','Hauteur demandée',value=>value===null?'À préciser':`${value.toLocaleString('fr-FR')} mm`,'Réexaminer l’échelle, l’assemblage et l’encombrement des fichiers à préparer.'],
    ['depthMm','Profondeur demandée',value=>value===null?'À préciser':`${value.toLocaleString('fr-FR')} mm`,'Réexaminer l’échelle, l’assemblage et l’encombrement des fichiers à préparer.'],
    ['budgetRange','Budget souhaité',value=>inquiryLabels.budgets[value],'Confronter la nouvelle préférence au chiffrage ; le budget indiqué ne fixe pas le prix.'],
    ['deadline','Date souhaitée',value=>value===null?'À préciser':value,'Réexaminer le calendrier complet, avec finition et remise de la pièce.'],
    ['modelStatus','Point de départ du modèle',value=>inquiryLabels.models[value],'Confirmer les fichiers à recevoir et le travail de conception nécessaire.']
  ];
  const valueOf=(link,id)=>['widthMm','heightMm','depthMm'].includes(id)?link.dimensions?.[id]??null:link[id]??null;
  const rows=definitions.map(([id,label,display,impact])=>{
    const before=valueOf(previous,id),after=valueOf(received,id),changed=before!==after;
    return{id,label,before,after,beforeLabel:display(before),afterLabel:display(after),changed,...(changed?{impact}:{})};
  });
  const changedCount=rows.filter(row=>row.changed).length,sourceChanged=previous.contentSha256!==received.contentSha256;
  const revisionRelation=received.revision>previous.revision?'newer':received.revision<previous.revision?'older':'same';
  return{format:'bojart.inquiry.comparison.v1',available:true,canApply:false,previousRevision:previous.revision,receivedRevision:received.revision,revisionRelation,sourceChanged,technicalChanged:changedCount>0,changedCount,rows,impacts:[...new Set(rows.filter(row=>row.changed).map(row=>row.impact))],
    message:changedCount?`${changedCount} paramètre${changedCount>1?'s':''} technique${changedCount>1?'s':''} diffère${changedCount>1?'nt':''} de la demande importée.`:sourceChanged?'Paramètres techniques inchangés ; le contenu ou le suivi de la demande source a changé.':'Les paramètres techniques et le contenu de la demande sont identiques.'};
}

export async function inspectInquiryExport(input,state,{cryptoImpl=globalThis.crypto}={}){
  let raw=input;
  if(typeof input==='string'){
    if(new TextEncoder().encode(input).byteLength>INQUIRY_MAX_BYTES)fail('L’export dépasse la limite de 64 Kio.');
    try{raw=JSON.parse(input);}catch{fail('Ce fichier ne contient pas un document JSON valide.');}
  }else if(new TextEncoder().encode(canonicalJSON(raw)).byteLength>INQUIRY_MAX_BYTES)fail('L’export dépasse la limite de 64 Kio.');
  const envelope=await verifyInquiryExport(raw,{cryptoImpl}),q=envelope.inquiry;
  const link=normalizeInquiryLink({format:INQUIRY_LINK_FORMAT,requestId:q.requestId,reference:q.reference,contentSha256:await sha256(canonicalJSON(q),cryptoImpl),exportSha256:envelope.sha256,createdAt:q.createdAt,updatedAt:q.updatedAt,revision:q.revision,offer:q.offer,quantity:q.quantity,...(q.dimensions?{dimensions:q.dimensions}:{}),budgetRange:q.budgetRange,...(q.deadline?{deadline:q.deadline}:{}),modelStatus:q.modelStatus});
  return {envelope,link,...locateInquiry(state,link)};
}

export function inquiryProjectPayload(link,technicalSummary=''){
  const inquiry=normalizeInquiryLink(link);
  if(typeof technicalSummary!=='string'||technicalSummary.trim().length>3000||/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/.test(technicalSummary))fail('La synthèse technique doit rester un texte de 3 000 caractères maximum.');
  return {id:inquiryProjectId(inquiry),name:'DEMANDE '+inquiry.reference,kind:inquiryLabels.offers[inquiry.offer],quantity:inquiry.quantity,height:inquiry.dimensions?.heightMm??null,notes:technicalSummary.trim(),status:'Étude',inquiry};
}
export function validateInquiryProjectPayload(payload){
  const expected=inquiryProjectPayload(payload.inquiry,payload.notes??'');
  for(const key of ['id','name','kind','quantity','height','status'])if(payload[key]!==expected[key])fail('Le dossier technique ne correspond pas aux paramètres de la demande.');
  return expected;
}

export function importInquiryProject(store,prepared,technicalSummary=''){
  if(!prepared?.link)fail('Relisez l’export avant de créer son dossier.');
  store.refresh?.();
  const current=locateInquiry(store.state,prepared.link);
  if(current.conflict)return{ok:false,message:'Cette référence existe avec un contenu différent. Aucun dossier n’a été remplacé.'};
  if(current.existing){
    const selected=store.dispatch('SELECT_PROJECT',{id:current.existing.id});
    return {...selected,duplicate:true,projectId:current.existing.id,message:selected.ok?'Demande déjà importée : dossier existant ouvert sans modification.':selected.message};
  }
  return store.dispatch('ADD_PROJECT',inquiryProjectPayload(prepared.link,technicalSummary));
}

export function inquiryQualification(project){
  const q=project?.inquiry;if(!q)return{items:[]};
  const items=[];
  if(!Number.isFinite(project.height)||!project.height||!q.dimensions?.widthMm||!q.dimensions?.depthMm)items.push({id:'dimensions',title:'Dimensions & échelle',question:'Quelles dimensions finales et quelles contraintes d’encombrement faut-il respecter ?'});
  if(!(project.pieces||[]).some(piece=>piece.assetId))items.push({id:'geometry',title:'Fichier & géométrie',question:q.modelStatus==='file_ready'?'Récupérer le fichier original annoncé, puis vérifier ses unités, sa géométrie et ses droits d’utilisation.':'Définir si le modèle doit être créé, adapté ou fourni ; préciser la validation attendue avant fabrication.'});
  if(q.offer==='prototype')items.push({id:'usage',title:'Usage & essais du prototype',question:'Préciser les efforts, températures, assemblages, jeux et essais qui permettront d’accepter la pièce.'});
  if(q.budgetRange==='undecided')items.push({id:'budget',title:'Budget de l’étude',question:'Quelle enveloppe peut être envisagée pour la conception, la fabrication et la finition du lot ?'});
  if(!q.deadline)items.push({id:'deadline',title:'Date souhaitée',question:'Existe-t-il une date d’événement ou une contrainte de livraison à prendre en compte ?'});
  items.push({id:'finish',title:'Finition & résultat attendu',question:'Définir le rendu, les couleurs, l’assemblage et les critères visuels ; prévoir le temps de finition et de contrôle.'});
  items.push({id:'rights',title:'Droits & confidentialité',question:'Vérifier l’autorisation d’utiliser le modèle et les références ; convenir séparément de la diffusion des images du projet.'});
  items.push({id:'delivery',title:'Remise & transport',question:'Préciser retrait ou expédition, destination et protection nécessaire pour la pièce assemblée.'});
  return{items};
}
export function inquiryProjectSummary(project){const q=project.inquiry;return `${inquiryLabels.offers[q.offer]} · ${project.quantity} exemplaire${project.quantity>1?'s':''}. Les paramètres reçus servent à préparer l’étude ; le coût complet et la capacité réelle restent à vérifier.`;}
export function inquiryQuestionsText(project){return `BOJ.ART — ${project.inquiry.reference}\nQuestions préparées pour qualification\n\n${inquiryQualification(project).items.map((item,index)=>`${index+1}. ${item.title}\n${item.question}`).join('\n\n')}\n\nBrouillon de travail à relire. Aucun message envoyé.\n`;}
export function exportInquiryTechnical(project){return{format:'bojart.inquiry.technical.v1',projectId:project.id,source:inquirySourceURL(project.inquiry),inquiry:normalizeInquiryLink(project.inquiry),technicalSummary:project.notes||'',project:{name:project.name,kind:project.kind,quantity:project.quantity,height:project.height,status:project.status},limitations:['Fiche technique sans copie automatique des coordonnées ou de la description source.','Paramètres demandés : fichiers, faisabilité, coûts, accord et livraison restent à vérifier.']};}
