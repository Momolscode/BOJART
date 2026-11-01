import {canonicalWorkshopJSON,validateWorkshopSeed,validateWorkshopOperation,replayWorkshopOperations,replayWorkshopAuthority} from './workshop.js';

export const WORKSHOP_BACKUP_FORMAT='bojart.workshop.backup.v2';
export const LEGACY_WORKSHOP_BACKUP_FORMAT='bojart.workshop.backup.v1';
export const MAX_BACKUP_BYTES=16777216;
const EXCLUDES=['stl_binaries','credentials','printer_state'];
const bytes=value=>new TextEncoder().encode(value);
async function checksum(value) {
  if(!globalThis.crypto?.subtle) throw new Error('La vérification du fichier nécessite un contexte HTTPS ou le poste local.');
  const digest=await crypto.subtle.digest('SHA-256',bytes(canonicalWorkshopJSON(value)));
  return [...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join('');
}

/** Pure contract shared with SQLite; checksum verification belongs to the caller. */
export function workshopBackupBody(raw) {
  if(!raw||typeof raw!=='object'||Array.isArray(raw))throw new Error('Sauvegarde invalide.');
  const version=raw.format===WORKSHOP_BACKUP_FORMAT?2:raw.format===LEGACY_WORKSHOP_BACKUP_FORMAT?1:null;
  const keys=['format','exportedAt','sourceInstanceId','seed','operations','excludes','sha256',...(version===2?['authority']:[])];
  if(!version||Object.keys(raw).some(k=>!keys.includes(k)))throw new Error('Format de sauvegarde inconnu. L’ancien export descriptif ne contient pas le journal restaurable.');
  if(typeof raw.exportedAt!=='string'||!Number.isFinite(Date.parse(raw.exportedAt))||typeof raw.sourceInstanceId!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/.test(raw.sourceInstanceId))throw new Error('Provenance de la sauvegarde invalide.');
  if(!Array.isArray(raw.excludes)||canonicalWorkshopJSON(raw.excludes)!==canonicalWorkshopJSON(EXCLUDES))throw new Error('Le périmètre de sauvegarde est invalide.');
  const seed=validateWorkshopSeed(raw.seed);
  if(!Array.isArray(raw.operations)||raw.operations.length>50000)throw new Error('Journal de sauvegarde invalide.');
  const operations=raw.operations.map(validateWorkshopOperation),body={format:raw.format,exportedAt:raw.exportedAt,sourceInstanceId:raw.sourceInstanceId,seed,operations,excludes:[...EXCLUDES]};
  if(version===2) {
    replayWorkshopAuthority(seed,operations,raw.authority);
    body.authority=JSON.parse(canonicalWorkshopJSON(raw.authority));
  } else replayWorkshopOperations(seed,operations);
  return body;
}
export async function createWorkshopBackup(journal,{sourceInstanceId='browser',now=Date.now()}={}) {
  const body=workshopBackupBody({format:journal.authority?WORKSHOP_BACKUP_FORMAT:LEGACY_WORKSHOP_BACKUP_FORMAT,exportedAt:new Date(now).toISOString(),sourceInstanceId,seed:journal.seed,operations:journal.operations,excludes:[...EXCLUDES],...(journal.authority?{authority:journal.authority}:{})});
  const backup={...body,sha256:await checksum(body)};
  if(bytes(JSON.stringify(backup)).byteLength>MAX_BACKUP_BYTES)throw new Error('Le journal dépasse 16 Mio. Utilisez la sauvegarde de la base locale.');
  return backup;
}
export async function inspectWorkshopBackup(input) {
  const text=typeof input==='string'?input:JSON.stringify(input);
  if(bytes(text).byteLength>MAX_BACKUP_BYTES)throw new Error('La sauvegarde dépasse 16 Mio.');
  let raw;try{raw=JSON.parse(text);}catch{throw new Error('Le fichier ne contient pas de JSON valide.');}
  if(typeof raw?.sha256!=='string'||!/^[a-f0-9]{64}$/.test(raw.sha256))throw new Error('Empreinte SHA-256 manquante ou invalide.');
  const {sha256,...rawBody}=raw;
  if(await checksum(rawBody)!==sha256)throw new Error('L’empreinte du fichier ne correspond pas à son contenu. Aucun dossier n’a été modifié.');
  const body=workshopBackupBody(raw),version=body.authority?2:1;
  const {state,results}=version===2?replayWorkshopAuthority(body.seed,body.operations,body.authority):replayWorkshopOperations(body.seed,body.operations);
  return {backup:{...body,sha256},journal:{version,seed:body.seed,operations:body.operations,...(body.authority?{authority:body.authority}:{})},summary:{projects:state.projects.length,machines:state.machines.length,operations:body.operations.length,confirmed:body.authority?.receipts.length||0,conflicts:[...results.values()].filter(x=>!x.ok).length,exportedAt:body.exportedAt,includes:['workshop_metadata','operation_journal',...(version===2?['genesis','server_receipts']:[])],excludes:[...EXCLUDES]}};
}
