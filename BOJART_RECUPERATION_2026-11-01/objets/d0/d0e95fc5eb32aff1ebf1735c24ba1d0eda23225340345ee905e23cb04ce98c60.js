/**
 * BOJ.ART — declared machine inventory.
 * This module never contacts a printer, edits simulation geometry or qualifies hardware.
 * Record timestamps and revisions are supplied by the WorkshopStore operation reducer.
 */
export const FLEET_FORMAT = 'bojart.fleet-record.v1';
export const FLEET_CONNECTIONS = Object.freeze([
  ['unknown','À préciser'],['manual','Carte mémoire / USB'],['moonraker','Moonraker / Klipper'],
  ['octoprint','OctoPrint'],['vendor','Interface constructeur'],['other','Autre interface']
].map(([id,label])=>Object.freeze({id,label})));
export const FLEET_QUALIFICATION = Object.freeze([
  ['not_started','Essai à préparer'],['in_progress','Essai en cours'],
  ['documented','Essai documenté'],['needs_review','Essai à reprendre']
].map(([id,label])=>Object.freeze({id,label})));

const RECORD_KEYS = ['origin','manufacturer','model','serial','location','firmware','technology','usableVolumeMm','volumeSource','material','slicer','fileFormats','connection','qualification','notes'];
const META_KEYS = ['format','revision','updatedAt'];
const copy = value => JSON.parse(JSON.stringify(value));
const fail = message => {throw new TypeError(message);};
const own = (value,key) => Object.prototype.hasOwnProperty.call(value,key);
function object(value,label,allowed){
  if(!value||typeof value!=='object'||Array.isArray(value)||![Object.prototype,null].includes(Object.getPrototypeOf(value)))fail(label+' doit être un objet.');
  if(allowed)for(const key of Object.keys(value))if(!allowed.includes(key))fail(label+' : champ inconnu « '+key+' ».');
  return value;
}
function text(value,label,max=240){
  if(value===undefined)return '';
  if(typeof value!=='string')fail(label+' doit être du texte.');
  const clean=value.trim();
  if(clean.length>max||/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(clean))fail(label+' invalide.');
  return clean;
}
function enumValue(value,allowed,fallback,label){
  const clean=value===undefined?fallback:value;
  if(!allowed.includes(clean))fail(label+' invalide.');
  return clean;
}
function volume(value){
  if(value===undefined||value===null)return null;
  if(!Array.isArray(value)||value.length!==3||value.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<=0||v>10000))fail('Le volume utile attend trois mesures positives en mm, au plus 10 000 mm par axe.');
  return [...value];
}
function date(value){
  const result=text(value,'Date de l’essai',10);
  if(!result)return '';
  if(!/^\d{4}-\d{2}-\d{2}$/.test(result))fail('La date de l’essai est invalide.');
  const parsed=new Date(result+'T12:00:00Z');
  if(!Number.isFinite(parsed.getTime())||parsed.toISOString().slice(0,10)!==result)fail('La date de l’essai est invalide.');
  return result;
}
function endpoint(value){
  const clean=text(value,'Adresse de l’interface',500);
  if(!clean)return '';
  let parsed;
  try{parsed=new URL(clean);}catch{fail('L’adresse de l’interface doit être une URL HTTP ou HTTPS complète.');}
  if(!['http:','https:'].includes(parsed.protocol)||!parsed.hostname||parsed.username||parsed.password||parsed.search||parsed.hash)fail('L’adresse attend HTTP ou HTTPS, sans identifiant, mot de passe, paramètre ni fragment.');
  return parsed.href;
}
function formats(value){
  if(value===undefined)return [];
  if(!Array.isArray(value)||value.length>16)fail('Renseignez au plus 16 extensions de fichier.');
  return [...new Set(value.map(item=>{
    const clean=text(item,'Format de fichier',24).toLowerCase().replace(/^\./,'');
    if(!/^[a-z0-9][a-z0-9_+-]{0,23}$/.test(clean))fail('Utilisez des extensions de fichier, séparées par des virgules.');
    return clean;
  }))];
}

function cleanRecord(raw){
  object(raw,'Fiche du parc',RECORD_KEYS);
  const s=object(raw.slicer??{},'Slicer',['name','version','machineProfile','materialProfile']);
  const c=object(raw.connection??{},'Interface',['kind','endpoint']);
  const q=object(raw.qualification??{},'Dossier d’essai',['status','testedOn','operator','report']);
  const record={
    origin:enumValue(raw.origin,['example','declared'],'example','Origine de la fiche'),
    manufacturer:text(raw.manufacturer,'Fabricant',120),model:text(raw.model,'Modèle',160),
    serial:text(raw.serial,'Identifiant de la machine',160),location:text(raw.location,'Position dans l’atelier',160),
    firmware:text(raw.firmware,'Firmware',160),
    technology:enumValue(raw.technology,['unknown','fdm','resin'],'unknown','Procédé'),
    usableVolumeMm:volume(raw.usableVolumeMm),volumeSource:text(raw.volumeSource,'Source des dimensions',500),
    material:text(raw.material,'Matière',240),
    slicer:{name:text(s.name,'Slicer',120),version:text(s.version,'Version du slicer',100),machineProfile:text(s.machineProfile,'Profil machine',240),materialProfile:text(s.materialProfile,'Profil matière',240)},
    fileFormats:formats(raw.fileFormats),
    connection:{kind:enumValue(c.kind,FLEET_CONNECTIONS.map(x=>x.id),'unknown','Type d’interface'),endpoint:endpoint(c.endpoint)},
    qualification:{status:enumValue(q.status,FLEET_QUALIFICATION.map(x=>x.id),'not_started','État de l’essai'),testedOn:date(q.testedOn),operator:text(q.operator,'Responsable de l’essai',160),report:text(q.report,'Référence et résultat de l’essai',2000)},
    notes:text(raw.notes,'Notes',4000)
  };
  if(record.origin==='declared'&&![record.manufacturer,record.model,record.serial].some(Boolean))fail('Pour commencer une fiche d’atelier, renseignez un fabricant, un modèle ou un identifiant.');
  if(['unknown','manual'].includes(record.connection.kind)&&record.connection.endpoint)fail('Choisissez une interface réseau pour conserver une adresse.');
  if(record.origin==='example'&&record.qualification.status!=='not_started')fail('Un exemple ne peut pas porter un essai de machine réelle.');
  if(record.qualification.status==='documented'&&(!record.qualification.testedOn||!record.qualification.operator||!record.qualification.report))fail('Un essai documenté demande une date, un responsable et une référence de résultat.');
  return record;
}

function storedRecord(value){
  object(value,'Fiche enregistrée',[...RECORD_KEYS,...META_KEYS]);
  if(value.format!==FLEET_FORMAT||!Number.isSafeInteger(value.revision)||value.revision<1||!Number.isFinite(value.updatedAt)||value.updatedAt<0||value.updatedAt>8.64e15)fail('Métadonnées de la fiche du parc invalides.');
  const raw=Object.fromEntries(RECORD_KEYS.filter(key=>own(value,key)).map(key=>[key,value[key]]));
  return {...cleanRecord(raw),format:FLEET_FORMAT,revision:value.revision,updatedAt:value.updatedAt};
}

export function createEmptyFleetRecord(){
  return {...cleanRecord({}),format:FLEET_FORMAT,revision:0,updatedAt:null};
}

/** A missing registry stays empty; example dimensions are never copied into a real record. */
export function fleetRecordOf(machine){
  object(machine,'Machine');
  if(machine.registry===undefined||machine.registry===null)return createEmptyFleetRecord();
  return storedRecord(machine.registry);
}

/** Validates a complete replacement; the caller must compare expectedRegistryRevision first. */
export function normalizeFleetRecord(raw,previous=null,at){
  if(typeof at!=='number'||!Number.isFinite(at)||at<0||at>8.64e15)fail('Une date d’opération explicite est requise.');
  const before=previous===null?null:storedRecord(previous),record=cleanRecord(raw);
  if(before?.revision===Number.MAX_SAFE_INTEGER)fail('La révision de la fiche est hors limites.');
  if(before?.qualification.status==='documented'&&record.qualification.status==='documented'){
    const critical=['manufacturer','model','serial','firmware','technology','usableVolumeMm','material','slicer','fileFormats','connection'];
    const changed=critical.some(key=>JSON.stringify(before[key])!==JSON.stringify(record[key]));
    const sameEvidence=['testedOn','operator','report'].every(key=>before.qualification[key]===record.qualification[key]);
    if(changed&&sameEvidence)record.qualification.status='needs_review';
  }
  return {...record,format:FLEET_FORMAT,revision:(before?.revision??0)+1,updatedAt:at};
}

/** Maps a native FormData object converted with Object.fromEntries, never reads the DOM. */
export function fleetRecordFromForm(values){
  object(values,'Formulaire du parc');
  const axes=['volumeX','volumeY','volumeZ'].map(key=>text(values[key]??'','Dimension',60));
  if(axes.some(Boolean)&&!axes.every(Boolean))fail('Renseignez les trois dimensions utiles, ou laissez les trois vides.');
  const raw={origin:values.origin,manufacturer:values.manufacturer,model:values.model,serial:values.serial,location:values.location,firmware:values.firmware,technology:values.tech,
    usableVolumeMm:axes.every(Boolean)?axes.map(value=>Number(value.replace(',','.'))):null,
    volumeSource:values.volumeSource,material:values.material,
    slicer:{name:values.slicerName,version:values.slicerVersion,machineProfile:values.machineProfile,materialProfile:values.materialProfile},
    fileFormats:text(values.formats??'','Formats',400).split(/[,;\s]+/).filter(Boolean),
    connection:{kind:values.connectionKind,endpoint:values.endpoint},
    qualification:{status:values.qualificationStatus,testedOn:values.testedOn,operator:values.operator,report:values.report},notes:values.notes};
  return cleanRecord(raw);
}

/** Completeness concerns declared fields only. It is not a printer readiness score. */
export function fleetCompleteness(machineOrRecord){
  const r=machineOrRecord?.format===FLEET_FORMAT?machineOrRecord:fleetRecordOf(machineOrRecord);
  const groups=[
    {id:'identity',label:'Identité',complete:Boolean(r.manufacturer&&r.model&&r.serial),missing:[!r.manufacturer&&'fabricant',!r.model&&'modèle',!r.serial&&'identifiant'].filter(Boolean)},
    {id:'geometry',label:'Procédé & volume',complete:r.technology!=='unknown'&&!!r.usableVolumeMm,missing:[r.technology==='unknown'&&'procédé',!r.usableVolumeMm&&'volume utile'].filter(Boolean)},
    {id:'firmware',label:'Firmware',complete:!!r.firmware,missing:!r.firmware?['firmware']:[]},
    {id:'slicing',label:'Slicer & profils',complete:!!(r.slicer.name&&r.slicer.version&&r.slicer.machineProfile&&r.slicer.materialProfile),missing:[!r.slicer.name&&'slicer',!r.slicer.version&&'version du slicer',!r.slicer.machineProfile&&'profil machine',!r.slicer.materialProfile&&'profil matière'].filter(Boolean)},
    {id:'material',label:'Matière',complete:!!r.material,missing:!r.material?['matière']:[]},
    {id:'transfer',label:'Format & interface',complete:!!r.fileFormats.length&&r.connection.kind!=='unknown'&&(r.connection.kind==='manual'||!!r.connection.endpoint),missing:[!r.fileFormats.length&&'format de sortie',r.connection.kind==='unknown'&&'interface',!['manual','unknown'].includes(r.connection.kind)&&!r.connection.endpoint&&'adresse de l’interface'].filter(Boolean)}
  ];
  const completed=groups.filter(g=>g.complete).length;
  const status=r.origin==='example'?'example':completed===groups.length?'complete':'started';
  return {status,label:{example:'Exemple',started:'Fiche commencée',complete:'Fiche complète'}[status],completed,total:groups.length,percent:Math.round(completed/groups.length*100),groups,missing:groups.flatMap(g=>g.missing),connected:false,qualificationVerified:false,canStartPhysicalPrint:false};
}

export function summarizeFleet(machines){
  if(!Array.isArray(machines))fail('Le parc attend une liste de machines.');
  const records=machines.map(machine=>({id:machine.id,record:fleetRecordOf(machine),completeness:fleetCompleteness(machine)}));
  return {slots:records.length,declared:records.filter(x=>x.record.origin==='declared').length,
    examples:records.filter(x=>x.completeness.status==='example').length,
    started:records.filter(x=>x.completeness.status==='started').length,
    complete:records.filter(x=>x.completeness.status==='complete').length,
    documentedTests:records.filter(x=>x.record.qualification.status==='documented').length,
    connected:0,qualificationVerified:false,canStartPhysicalPrint:false,records};
}

export function exportFleetRegistry(machines,at){
  if(typeof at!=='number'||!Number.isFinite(at)||at<0)fail('Une date d’export explicite est requise.');
  const summary=summarizeFleet(machines);
  return {format:'bojart.fleet-export.v1',brand:'BOJ.ART',exportedAt:at,
    scope:'declared_inventory_not_machine_configuration',
    summary:{slots:summary.slots,declared:summary.declared,complete:summary.complete,connected:0,qualificationVerified:false},
    machines:summary.records.map(({id,record,completeness})=>({slotId:id,record:copy(record),completeness:{status:completeness.status,completed:completeness.completed,total:completeness.total}})),
    limitations:['Les fiches sont des déclarations conservées dans le navigateur.','Une fiche complète ne prouve ni connexion ni qualification de la machine.','Les profils et fichiers machine ne sont pas inclus dans cet export.','Les dimensions de simulation sont conservées séparément.']};
}
