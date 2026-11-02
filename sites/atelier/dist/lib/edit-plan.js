/**
 * BOJ.ART project editing plans. Pure validation and snapshots; no render,
 * publication, printer command, storage access or inferred media ownership.
 */
import {CONTENT_CATALOG,CONTENT_CATALOG_SOURCE,CONTENT_CATALOG_VERSION,getContentSource} from './content-catalog.js';

const freezeRows = rows => Object.freeze(rows.map(row=>Object.freeze(row)));
export const EDIT_SERIES = freezeRows([
  {id:'oeuvres',label:'Les œuvres',description:'Présenter la matière, le travail et l’œuvre entière.'},
  {id:'geste',label:'Le geste',description:'Raconter une technique et la main qui la réalise.'},
  {id:'sur_mesure',label:'Sur mesure',description:'Relier une intention singulière à sa réalisation.'},
  {id:'prototype',label:'Prototype',description:'Montrer le besoin, les essais et les observations utiles.'},
  {id:'disponible',label:'Disponible',description:'Préparer la présentation d’une pièce et de son offre.'}
]);
export const EDIT_FORMATS = Object.freeze(['9:16','1:1','16:9']);
export const EDIT_BEATS = freezeRows([
  {id:'detail',label:'Le détail',prompt:'Choisir un détail caractéristique du dossier.'},
  {id:'geste',label:'Le geste',prompt:'Montrer une étape, une main ou une technique.'},
  {id:'oeuvre',label:'L’œuvre',prompt:'Présenter la pièce entière ou le résultat observé.'},
  {id:'signature',label:'La signature',prompt:'Choisir la conclusion et l’emblème à utiliser.'}
]);
export const EDIT_LIMITS = Object.freeze({plans:20,versions:50,sources:31,title:120,brief:4000,caption:2200,beatNote:1000,audioNotes:2000,planBytes:32768});
const PLAN_KEYS = ['title','series','format','duration','brief','caption','status','sources','beats','audioNotes'];
const VERSION_KEYS = ['revision','operationId','at','projectRevision','projectName','plan'];
const seriesIds = new Set(EDIT_SERIES.map(series=>series.id));
const beatIds = new Set(EDIT_BEATS.map(beat=>beat.id));
const fail = message => {throw new Error(message);};
const has = (value,key) => Object.prototype.hasOwnProperty.call(value,key);

function object(value,label) {
  if(!value||typeof value!=='object'||Array.isArray(value))fail(label+' invalide.');
  const prototype=Object.getPrototypeOf(value);
  if(prototype!==null&&Object.getPrototypeOf(prototype)!==null)fail(label+' doit contenir des données simples.');
  return value;
}
function keys(value,allowed,label) {
  object(value,label);
  for(const key of Reflect.ownKeys(value)) {
    if(typeof key!=='string'||!allowed.includes(key))fail(label+' : champ inconnu.');
    const descriptor=Object.getOwnPropertyDescriptor(value,key);
    if(!descriptor?.enumerable||!has(descriptor,'value'))fail(label+' : valeur non sérialisable.');
  }
  for(const key of allowed)if(!has(value,key))fail(label+' : champ « '+key+' » manquant.');
}
function text(value,label,max,allowEmpty=false) {
  if(typeof value!=='string')fail(label+' doit être du texte.');
  const clean=value.trim();
  if((!allowEmpty&&!clean)||clean.length>max)fail(label+' : '+(allowEmpty?'au maximum ':'de 1 à ')+max+' caractères.');
  return clean;
}
function integer(value,label,min,max=Number.MAX_SAFE_INTEGER) {
  if(typeof value!=='number'||!Number.isSafeInteger(value)||value<min||value>max)fail(label+' : entier attendu entre '+min+' et '+max+'.');
  return value;
}
function planId(value) {
  if(typeof value!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$/.test(value))fail('Identifiant de plan invalide.');
  return value;
}
function sourceId(value) {
  if(typeof value!=='string'||!getContentSource(value))fail('Publication absente du catalogue BOJ.ART.');
  return value;
}
function list(value,label,max) {
  if(!Array.isArray(value)||value.length>max)fail(label+' : '+max+' éléments au maximum.');
  const own=Object.keys(value);
  if(own.length!==value.length||own.some((key,index)=>key!==String(index)))fail(label+' doit être une liste complète.');
  return value;
}
function freezeSnapshot(value) {
  if(value&&typeof value==='object') {Object.values(value).forEach(freezeSnapshot);Object.freeze(value);}
  return value;
}

/** Return a complete editable draft. No publication is associated automatically. */
export function createEditDraft(project,series='oeuvres') {
  object(project,'Dossier');
  if(!seriesIds.has(series))fail('Série éditoriale inconnue.');
  const name=text(project.name,'Nom du dossier',300);
  const label=EDIT_SERIES.find(item=>item.id===series).label;
  const inheritedBrief=typeof project.story==='string'&&project.story.trim()?project.story.trim():typeof project.notes==='string'?project.notes.trim():'';
  return normalizeEditPlan({
    title:(name+' · '+label).slice(0,EDIT_LIMITS.title),series,format:'9:16',duration:23,
    brief:inheritedBrief.slice(0,EDIT_LIMITS.brief),
    caption:'',status:'draft',sources:[],
    beats:EDIT_BEATS.map(beat=>({id:beat.id,note:beat.prompt,postId:null,in:null,out:null})),
    audioNotes:''
  });
}

/** Strong, state-independent validation, shared by UI, replay and SQLite. */
export function normalizeEditPlan(raw) {
  keys(raw,PLAN_KEYS,'Plan d’édit');
  if(!seriesIds.has(raw.series))fail('Série éditoriale inconnue.');
  if(!EDIT_FORMATS.includes(raw.format))fail('Format attendu : 9:16, 1:1 ou 16:9.');
  if(!['draft','ready_to_edit'].includes(raw.status))fail('État attendu : brouillon ou prêt à monter.');
  const sourceSet=new Set();
  const sources=list(raw.sources,'Sources du plan',EDIT_LIMITS.sources).map(source=>{
    keys(source,['postId','relation'],'Source');
    const postId=sourceId(source.postId);
    if(sourceSet.has(postId))fail('Une publication ne peut être déclarée qu’une fois dans les sources.');
    if(!['reference','project'].includes(source.relation))fail('Relation attendue : référence ou média déclaré du dossier.');
    sourceSet.add(postId);
    return {postId,relation:source.relation};
  });
  const rawBeats=list(raw.beats,'Moments du montage',EDIT_BEATS.length);
  if(rawBeats.length!==EDIT_BEATS.length)fail('Les quatre moments détail, geste, œuvre et signature sont requis.');
  const beats=new Map();
  for(const beat of rawBeats) {
    keys(beat,['id','note','postId','in','out'],'Moment du montage');
    if(!beatIds.has(beat.id)||beats.has(beat.id))fail('Chaque moment détail, geste, œuvre et signature doit apparaître une seule fois.');
    const postId=beat.postId===null?null:sourceId(beat.postId);
    if(postId!==null&&!sourceSet.has(postId))fail('La publication du moment doit être déclarée dans les sources du plan.');
    const emptyIn=beat.in===null,emptyOut=beat.out===null;
    if(emptyIn!==emptyOut)fail('Le début et la fin du passage doivent être renseignés ensemble.');
    let start=null,end=null;
    if(!emptyIn) {
      if(postId===null)fail('Choisissez une publication avant de définir un passage.');
      const source=getContentSource(postId);
      if(source.type!=='video')fail('Une photographie ne possède pas de plage vidéo source.');
      if(!Number.isFinite(source.duration)||source.duration<=0)fail('La durée originale est inconnue : laissez le passage à définir.');
      if(typeof beat.in!=='number'||typeof beat.out!=='number'||!Number.isFinite(beat.in)||!Number.isFinite(beat.out)||beat.in<0||beat.out<=beat.in||beat.out>source.duration)fail('Le passage doit respecter 0 ≤ début < fin ≤ durée originale ('+String(source.duration).replace('.',',')+' s).');
      start=beat.in;end=beat.out;
    }
    beats.set(beat.id,{id:beat.id,note:text(beat.note,'Note du moment',EDIT_LIMITS.beatNote,true),postId,in:start,out:end});
  }
  const clean={
    title:text(raw.title,'Titre de l’édit',EDIT_LIMITS.title),series:raw.series,format:raw.format,
    duration:integer(raw.duration,'Durée cible',10,60),brief:text(raw.brief,'Brief créatif',EDIT_LIMITS.brief,true),
    caption:text(raw.caption,'Légende proposée',EDIT_LIMITS.caption,true),status:raw.status,sources,
    beats:EDIT_BEATS.map(beat=>beats.get(beat.id)),audioNotes:text(raw.audioNotes,'Notes sonores',EDIT_LIMITS.audioNotes,true)
  };
  if(new TextEncoder().encode(JSON.stringify(clean)).byteLength>EDIT_LIMITS.planBytes)fail('Le plan dépasse 32 Kio. Réduisez les textes avant de l’enregistrer.');
  return clean;
}

function normalizeVersion(raw,expectedRevision=null) {
  keys(raw,VERSION_KEYS,'Version du plan');
  const revision=integer(raw.revision,'Révision du plan',1,EDIT_LIMITS.versions);
  if(expectedRevision!==null&&revision!==expectedRevision)fail('Historique du plan non continu.');
  if(typeof raw.operationId!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/.test(raw.operationId))fail('Identité de la version enregistrée invalide.');
  return {revision,operationId:raw.operationId,at:integer(raw.at,'Date de version',0),projectRevision:integer(raw.projectRevision,'Révision du dossier',1),projectName:text(raw.projectName,'Nom historique du dossier',300),plan:normalizeEditPlan(raw.plan)};
}
function recordVersions(record) {
  keys(record,['id','versions'],'Historique du plan');
  planId(record.id);
  return list(record.versions,'Versions du plan',EDIT_LIMITS.versions);
}

/** Copies protect the journal-backed state from changes in editing forms. */
export function latestEditVersion(record) {
  if(record===undefined||record===null)return null;
  const versions=recordVersions(record);
  return versions.length?normalizeVersion(versions.at(-1),versions.length):null;
}
export function projectEditPlans(project) {
  if(project===undefined||project===null||project.contentPlans===undefined)return [];
  const records=list(project.contentPlans,'Plans du dossier',EDIT_LIMITS.plans),ids=new Set();
  return records.map(record=>{
    const versions=recordVersions(record);
    if(ids.has(record.id))fail('Deux historiques partagent le même identifiant de plan.');
    if(!versions.length)fail('Un historique enregistré doit contenir une version.');
    ids.add(record.id);
    return {id:record.id,versions:versions.map((version,index)=>normalizeVersion(version,index+1))};
  });
}

/** Only recorded versions of the explicit target project can be exported. */
export function exportEditPlan(project,record,version=undefined) {
  object(project,'Dossier d’export');
  const projectId=text(project.id,'Identifiant du dossier',300),currentName=text(project.name,'Nom du dossier',300);
  const currentRevision=integer(project.revision,'Révision du dossier',1);
  const requestedVersions=recordVersions(record);
  const saved=projectEditPlans(project).find(item=>item.id===record.id);
  if(!saved)fail('Ce plan n’appartient pas au dossier d’export.');
  const selectedRevision=version===undefined?latestEditVersion(record)?.revision:typeof version==='number'?integer(version,'Révision à exporter',1,EDIT_LIMITS.versions):normalizeVersion(version).revision;
  const candidate=requestedVersions.find(item=>item.revision===selectedRevision),stored=saved.versions.find(item=>item.revision===selectedRevision);
  if(!candidate||!stored)fail('La version demandée est absente de l’historique enregistré.');
  if(JSON.stringify(normalizeVersion(candidate))!==JSON.stringify(stored))fail('La version du plan ne correspond pas à celle conservée dans ce dossier.');
  if(version!==undefined&&typeof version!=='number'&&JSON.stringify(normalizeVersion(version))!==JSON.stringify(stored))fail('La version fournie appartient à un autre état du plan.');
  const plan=normalizeEditPlan(stored.plan);
  const sourceMetadata=plan.sources.map(reference=>{
    const source=getContentSource(reference.postId);
    return {postId:source.id,url:source.url,title:source.title,type:source.type,available:source.available,duration:source.duration,
      preview:source.preview,previewStart:source.previewStart,previewSeconds:source.previewSeconds,relation:reference.relation,
      relationBasis:reference.relation==='project'?'user_declaration':'visual_reference',
      availabilityNote:source.available?'Publication répertoriée comme conservée dans l’archive.':'Publication répertoriée, média indisponible dans l’archive.',
      durationNote:source.type==='image'?'Photographie : aucune plage vidéo source.':source.duration===null?'Durée originale inconnue.':'Plages exprimées dans la vidéo originale ; l’aperçu est un extrait distinct.'};
  });
  const unresolved=[];
  if(!plan.sources.length)unresolved.push('Aucune publication source choisie.');
  for(const source of sourceMetadata)if(!source.available)unresolved.push('Média source indisponible : '+source.postId+'.');
  for(const beat of plan.beats) {
    if(beat.postId===null)unresolved.push(EDIT_BEATS.find(item=>item.id===beat.id).label+' : source à choisir.');
    else if(getContentSource(beat.postId).type==='video'&&beat.in===null)unresolved.push(EDIT_BEATS.find(item=>item.id===beat.id).label+' : passage original à définir.');
  }
  return freezeSnapshot({
    format:'bojart.project-edit-plan.v1',exportedAt:new Date().toISOString(),
    project:{id:projectId,name:stored.projectName,currentName,revision:stored.projectRevision,currentRevision},recordId:record.id,
    version:{revision:stored.revision,operationId:stored.operationId,at:stored.at,projectRevision:stored.projectRevision,projectName:stored.projectName},plan,
    catalogue:{source:CONTENT_CATALOG_SOURCE,version:CONTENT_CATALOG_VERSION,publications:CONTENT_CATALOG.length},sourceMetadata,unresolved,
    declarations:{sourceRelation:'Le lien « média du dossier » est une déclaration de l’utilisateur, sans preuve automatique d’identité de la pièce.',status:'Le statut du plan est déclaré par l’utilisateur ; il ne constate ni rendu ni publication.'},
    execution:{renderRequested:false,publicationRequested:false,renderedFile:null}
  });
}
