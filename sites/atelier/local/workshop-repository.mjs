import {DatabaseSync} from 'node:sqlite';
import {createHash,randomUUID} from 'node:crypto';
import {chmodSync,lstatSync,mkdirSync,realpathSync} from 'node:fs';
import {homedir} from 'node:os';
import {isAbsolute,join,resolve} from 'node:path';
import {canonicalWorkshopJSON,validateWorkshopOperation,validateWorkshopSeed,createWorkshopGenesis,validateWorkshopGenesis,applyWorkshopOperation,replayWorkshopAuthority,validateWorkshopReceipt,workshopEntityKey,WORKSHOP_REDUCER_VERSION} from '../dist/lib/workshop.js';
import {workshopBackupBody,WORKSHOP_BACKUP_FORMAT,LEGACY_WORKSHOP_BACKUP_FORMAT} from '../dist/lib/workshop-backup.js';

export const WORKSHOP_LIMITS=Object.freeze({maxBatchOperations:100,maxOperationBytes:65536,maxRequestBytes:2097152,pageSize:200,maxBackupBytes:16777216,maxJournalOperations:50000});
const EXCLUDES=['stl_binaries','credentials','printer_state'];
const hash=value=>createHash('sha256').update(value,'utf8').digest('hex');
export const canonicalJson=canonicalWorkshopJSON;
export class WorkshopError extends Error {
  constructor(code,message,status=400){super(message);this.name='WorkshopError';this.code=code;this.status=status;}
}
const fail=(code,message,status=400)=>{throw new WorkshopError(code,message,status);};
const clone=value=>JSON.parse(JSON.stringify(value));
function record(raw,keys){if(!raw||typeof raw!=='object'||Array.isArray(raw)||Object.keys(raw).some(key=>!keys.includes(key))||keys.some(key=>!Object.prototype.hasOwnProperty.call(raw,key)))fail('invalid_operation','L’enveloppe du journal est invalide.');}
function normalizedSeed(raw,nullable=false){if(nullable&&raw===null)return null;try{const value=validateWorkshopSeed(raw);if(value.at>8640000000000000)throw new Error();return value;}catch{fail('invalid_operation','L’origine du journal est invalide.');}}
function normalizeOperations(raw,maxCount){
  if(!Array.isArray(raw)||raw.length>maxCount)fail('batch_too_large','Le lot contient trop d’opérations.',413);
  const entries=new Map();
  for(const value of raw){
    let operation,canonical;
    try{operation=validateWorkshopOperation(value);canonical=canonicalJson(operation);}catch{fail('invalid_operation','Une opération ne respecte pas le contrat BOJ.ART.');}
    if(Buffer.byteLength(canonical)>WORKSHOP_LIMITS.maxOperationBytes)fail('operation_too_large','Une opération dépasse 64 Kio.',413);
    const old=entries.get(operation.id);
    if(old&&old.canonical!==canonical)fail('operation_id_conflict','Un identifiant correspond à deux contenus différents. Aucun ajout effectué.',409);
    entries.set(operation.id,{operation,canonical,digest:hash(canonical)});
  }
  return [...entries.values()];
}
function clock(now){const value=Number(now());if(!Number.isSafeInteger(value)||value<0||value>8640000000000000)fail('invalid_configuration','L’horloge locale est invalide.',503);return value;}
export function defaultWorkshopDirectory(env=process.env){
  if(env.BOJ_WORKSHOP_DATA_DIR!==undefined){if(!env.BOJ_WORKSHOP_DATA_DIR||!isAbsolute(env.BOJ_WORKSHOP_DATA_DIR))fail('invalid_configuration','BOJ_WORKSHOP_DATA_DIR doit être un chemin absolu.',503);return resolve(env.BOJ_WORKSHOP_DATA_DIR);}
  if(process.platform==='win32')return join(env.LOCALAPPDATA||join(homedir(),'AppData','Local'),'BOJ.ART','workshop');
  if(process.platform==='darwin')return join(homedir(),'Library','Application Support','BOJ.ART','workshop');
  return join(env.XDG_STATE_HOME&&isAbsolute(env.XDG_STATE_HOME)?env.XDG_STATE_HOME:join(homedir(),'.local','state'),'bojart','workshop');
}

/** One SQLite authority. SQL sequence, immutable business receipts, no hardware. */
export function createWorkshopRepository({directory=defaultWorkshopDirectory(),now=Date.now}={}){
  if(Number(process.versions.node.split('.')[0])<24||typeof directory!=='string'||!isAbsolute(directory))fail('invalid_configuration','Node.js 24 et un dossier local absolu sont requis.',503);
  const folder=resolve(directory),filename=join(folder,'workshop.sqlite3');
  let db,closed=false;
  function transaction(write,run){
    if(closed)fail('storage_unavailable','Le journal local est fermé.',503);
    let started=false;
    try{db.exec(write?'BEGIN IMMEDIATE':'BEGIN');started=true;const result=run();db.exec('COMMIT');return result;}
    catch(error){if(started)try{db.exec('ROLLBACK');}catch{}if(error instanceof WorkshopError)throw error;fail('storage_unavailable','Le journal local n’a pas confirmé cette opération. Les données existantes sont conservées.',503);}
  }
  const getMeta=key=>db.prepare('SELECT value FROM metadata WHERE key=?').get(key)?.value;
  const setMeta=(key,value)=>db.prepare('INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').run(key,value);
  function readOperation(row){
    try{if(hash(row.canonical)!==row.digest)throw new Error();const operation=validateWorkshopOperation(JSON.parse(row.canonical));if(operation.id!==row.id||canonicalJson(operation)!==row.canonical)throw new Error();return operation;}
    catch{fail('storage_unavailable','Une opération conservée ne passe plus le contrôle d’intégrité. Aucune réinitialisation automatique.',503);}
  }
  function readReceipt(row){
    try{if(hash(row.receipt)!==row.receipt_digest)throw new Error();const receipt=validateWorkshopReceipt(JSON.parse(row.receipt));if(receipt.seq!==row.decision_seq||receipt.operationId!==row.id||canonicalJson(receipt)!==row.receipt)throw new Error();return receipt;}
    catch{fail('storage_unavailable','Un reçu conservé ne passe plus le contrôle d’intégrité. Aucun résultat confirmé ne sera réinterprété.',503);}
  }
  const rowsSQL='SELECT o.id,o.canonical,o.digest,o.received_at,d.seq AS decision_seq,d.receipt,d.digest AS receipt_digest FROM operations o JOIN decisions d ON d.operation_id=o.id';
  function rows(){return db.prepare(rowsSQL+' ORDER BY d.seq').all();}
  function origin(){
    const seed=normalizedSeed(JSON.parse(getMeta('seed')),true);
    let genesis=null;
    if(seed){const encoded=getMeta('genesis');if(!encoded||hash(encoded)!==getMeta('genesis_digest'))fail('storage_unavailable','La genèse ne passe plus son contrôle d’intégrité.',503);try{genesis=validateWorkshopGenesis(JSON.parse(encoded),seed);}catch{fail('storage_unavailable','La genèse conservée est incompatible. Aucun état de remplacement n’est créé.',503);}}
    else if(getMeta('genesis')!=='null')fail('storage_unavailable','Le journal possède une origine incohérente.',503);
    if(getMeta('reducer_version')!==WORKSHOP_REDUCER_VERSION)fail('storage_unavailable','Le moteur nécessaire à ce journal n’est pas disponible.',503);
    return {seed,genesis,workspaceId:getMeta('workspace_id'),reducerVersion:getMeta('reducer_version')};
  }
  function metadata(){
    const base=origin(),total=db.prepare('SELECT COUNT(*) AS count,MAX(received_at) AS last_write FROM operations').get(),decisions=db.prepare('SELECT COUNT(*) AS count,COALESCE(MAX(seq),0) AS cursor FROM decisions').get();
    if(total.count!==decisions.count||decisions.count!==decisions.cursor||(!base.seed&&total.count))fail('storage_unavailable','La séquence du journal est incomplète ; aucune fusion automatique.',503);
    return {ok:true,version:2,instanceId:getMeta('instance_id'),...base,cursor:decisions.cursor,operationCount:total.count,lastWriteAt:total.last_write===null?null:new Date(total.last_write).toISOString()};
  }
  function authority(base,receipts){return {workspaceId:base.workspaceId,reducerVersion:base.reducerVersion,genesis:base.genesis,receipts};}
  function verifySeed(old,incoming){if(old&&canonicalJson(old)!==canonicalJson(incoming))fail('seed_conflict','Ce journal appartient à un autre atelier. Les historiques restent séparés.',409);}
  function initialize(seed,workspaceId=null,genesis=createWorkshopGenesis(seed)){
    setMeta('seed',canonicalJson(seed));setMeta('genesis',canonicalJson(genesis));setMeta('genesis_digest',hash(canonicalJson(genesis)));if(workspaceId)setMeta('workspace_id',workspaceId);
  }
  function existing(entries){
    const duplicates=new Set();
    for(const entry of entries){const old=db.prepare('SELECT canonical,digest FROM operations WHERE id=?').get(entry.operation.id);if(!old)continue;if(old.canonical!==entry.canonical||old.digest!==entry.digest)fail('operation_id_conflict','Un identifiant existe avec un autre contenu. Aucun lot n’a été ajouté.',409);duplicates.add(entry.operation.id);}
    return duplicates;
  }
  function persist(entry,receipt){
    db.prepare('INSERT INTO operations(id,canonical,digest,received_at) VALUES(?,?,?,?)').run(entry.operation.id,entry.canonical,entry.digest,receipt.receivedAt);
    const encoded=canonicalJson(receipt);db.prepare('INSERT INTO decisions(seq,operation_id,receipt,digest) VALUES(?,?,?,?)').run(receipt.seq,entry.operation.id,encoded,hash(encoded));
  }
  function replayConfirmed(base=metadata()){
    const all=rows(),operations=all.map(readOperation),receipts=all.map(readReceipt);
    if(!base.seed)return {state:null,operations,receipts};
    try{return {...replayWorkshopAuthority(base.seed,operations,authority(base,receipts)),operations,receipts};}
    catch{fail('storage_unavailable','Les reçus confirmés sont incompatibles avec le moteur versionné. Aucune réinterprétation automatique.',503);}
  }
  function appendEntries(seed,entries,{legacy=false}={}){
    const before=metadata();verifySeed(before.seed,seed);const duplicates=existing(entries),pending=entries.filter(entry=>!duplicates.has(entry.operation.id));
    if(before.operationCount+pending.length>WORKSHOP_LIMITS.maxJournalOperations)fail('journal_full','La limite de 50 000 opérations est atteinte. Aucune suppression automatique.',413);
    if(!legacy)for(const entry of pending)if(workshopEntityKey(entry.operation)&&entry.operation.expected?.entityVersion===undefined)fail('expected_version_required','La commande doit annoncer la version de la ressource qu’elle modifie. Actualisez le client.',409);
    if(!before.seed)initialize(seed);
    let base=metadata(),replay=replayConfirmed(base),state=replay.state,next=base.cursor;
    const added=[];
    for(const entry of pending){
      const decision=applyWorkshopOperation(state,entry.operation),receipt={version:1,seq:++next,operationId:entry.operation.id,receivedAt:clock(now),entityKey:decision.entityKey,entityVersionBefore:decision.entityVersionBefore,entityVersionAfter:decision.entityVersionAfter,outcome:decision.outcome};
      persist(entry,receipt);state=decision.state;added.push(receipt);
    }
    const receipts=entries.map(entry=>readReceipt(db.prepare(rowsSQL+' WHERE o.id=?').get(entry.operation.id)));
    return {...metadata(),accepted:pending.map(entry=>entry.operation.id),duplicates:[...duplicates],receipts};
  }

  try{
    mkdirSync(folder,{recursive:true,mode:0o700});if(!lstatSync(folder).isDirectory()||lstatSync(folder).isSymbolicLink())throw new Error();
    let existed=false;try{const file=lstatSync(filename);if(!file.isFile()||file.isSymbolicLink())throw new Error();existed=true;}catch(error){if(error.code!=='ENOENT')throw error;}
    db=new DatabaseSync(filename,{timeout:1500,enableForeignKeyConstraints:true,enableDoubleQuotedStringLiterals:false,allowExtension:false});
    let previous=null;
    if(existed){const tables=new Set(db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map(row=>row.name));if(!tables.has('metadata')||!tables.has('operations'))throw new Error();previous=getMeta('schema_version');if(!['1','2'].includes(previous)||!/^workshop-[0-9a-f-]{36}$/.test(getMeta('instance_id')||'')||getMeta('seed')===undefined)throw new Error();if(previous==='2'&&(!tables.has('decisions')||!/^workspace-[0-9a-f-]{36}$/.test(getMeta('workspace_id')||'')||getMeta('genesis')===undefined||getMeta('genesis_digest')===undefined))throw new Error();}
    chmodSync(filename,0o600);if(db.prepare('PRAGMA journal_mode=WAL').get().journal_mode!=='wal')throw new Error();
    db.exec('PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON; PRAGMA trusted_schema=OFF;');
    transaction(true,()=>{
      db.exec('CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL) STRICT; CREATE TABLE IF NOT EXISTS operations(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,canonical TEXT NOT NULL,digest TEXT NOT NULL,received_at INTEGER NOT NULL) STRICT; CREATE TABLE IF NOT EXISTS decisions(seq INTEGER PRIMARY KEY,operation_id TEXT NOT NULL UNIQUE REFERENCES operations(id),receipt TEXT NOT NULL,digest TEXT NOT NULL) STRICT;');
      if(!existed){setMeta('instance_id','workshop-'+randomUUID());setMeta('seed','null');}
      if(previous!=='2'){
        const legacySeed=normalizedSeed(JSON.parse(getMeta('seed')),true),legacyRows=db.prepare('SELECT id,canonical,digest,received_at FROM operations ORDER BY seq').all();
        if(!legacySeed&&legacyRows.length)throw new Error();
        setMeta('workspace_id','workspace-'+randomUUID());setMeta('reducer_version',WORKSHOP_REDUCER_VERSION);setMeta('genesis','null');setMeta('genesis_digest',hash('null'));
        if(legacySeed){
          initialize(legacySeed);let state=createWorkshopGenesis(legacySeed).state,sequence=0;
          // Preserve the old logical replay exactly once. Existing operation bytes
          // and their original SQLite arrival sequence are never rewritten.
          const legacy=legacyRows.map(row=>({row,operation:readOperation(row)})).sort((a,b)=>a.operation.clock-b.operation.clock||(a.operation.id<b.operation.id?-1:a.operation.id>b.operation.id?1:0));
          for(const {row,operation} of legacy){const decision=applyWorkshopOperation(state,operation),receipt={version:1,seq:++sequence,operationId:operation.id,receivedAt:row.received_at,entityKey:decision.entityKey,entityVersionBefore:decision.entityVersionBefore,entityVersionAfter:decision.entityVersionAfter,outcome:decision.outcome};const encoded=canonicalJson(receipt);db.prepare('INSERT INTO decisions(seq,operation_id,receipt,digest) VALUES(?,?,?,?)').run(receipt.seq,operation.id,encoded,hash(encoded));state=decision.state;}
        }
        setMeta('schema_version','2');setMeta('migration',canonicalJson({from:previous||'new',at:clock(now),order:previous==='1'?'legacy_clock_id_frozen':'server_sequence'}));
      }
      replayConfirmed(metadata());
    });
    const integrity=db.prepare('PRAGMA quick_check').all();if(integrity.length!==1||integrity[0].quick_check!=='ok')throw new Error();
  }catch{try{db?.close();}catch{}fail('storage_unavailable','Le journal local ne peut pas être ouvert. Aucune base de remplacement n’a été créée ; les données existantes sont conservées.',503);}

  return {
    directory:realpathSync(folder),
    status(){return transaction(false,()=>({...metadata(),storage:'sqlite',durable:true,limits:{...WORKSHOP_LIMITS},capabilities:{printerCommands:false,stlStorage:false,businessReceipts:true,persistedGenesis:true}}));},
    operations(after=0){
      if(!Number.isSafeInteger(after)||after<0)fail('invalid_cursor','Le curseur doit être un entier positif ou nul.');
      return transaction(false,()=>{
        const current=metadata();if(after>current.cursor)fail('cursor_out_of_range','Ce curseur ne correspond plus au journal. Vérifiez son identité.',409);
        const selected=[];let size=Buffer.byteLength(canonicalJson(current))+100;
        for(const row of db.prepare(rowsSQL+' WHERE d.seq>? ORDER BY d.seq LIMIT ?').all(after,WORKSHOP_LIMITS.pageSize)){const length=Buffer.byteLength(row.canonical)+Buffer.byteLength(row.receipt)+2;if(size+length>WORKSHOP_LIMITS.maxRequestBytes)break;selected.push(row);size+=length;}
        const nextCursor=selected.length?selected.at(-1).decision_seq:after;
        return {...current,operations:selected.map(readOperation),receipts:selected.map(readReceipt),nextCursor,hasMore:nextCursor<current.cursor};
      });
    },
    append(input){
      if(input?.version!==2)fail('upgrade_required','Le protocole v1 ne garantit pas un résultat métier stable. Actualisez les écrans vers le protocole v2.',426);
      record(input,['version','workspaceId','seed','operations']);
      const seed=normalizedSeed(input.seed),entries=normalizeOperations(input.operations,WORKSHOP_LIMITS.maxBatchOperations);
      if(Buffer.byteLength(canonicalJson(input))>WORKSHOP_LIMITS.maxRequestBytes)fail('body_too_large','Le lot dépasse 2 Mio.',413);
      return transaction(true,()=>{if(input.workspaceId!==metadata().workspaceId)fail('authority_conflict','La commande vise une autre autorité. Aucun ajout.',409);return appendEntries(seed,entries);});
    },
    backup(){
      return transaction(false,()=>{
        const current=metadata();if(!current.seed)fail('not_initialized','Le journal local n’est pas initialisé.',409);
        const bytes=db.prepare('SELECT COALESCE(SUM(length(CAST(o.canonical AS BLOB))+length(CAST(d.receipt AS BLOB))),0) AS total FROM operations o JOIN decisions d ON d.operation_id=o.id').get().total;
        if(bytes+current.operationCount*2+Buffer.byteLength(canonicalJson(current.genesis))+1024>WORKSHOP_LIMITS.maxBackupBytes)fail('backup_too_large','Le journal dépasse l’export JSON de 16 Mio. La base locale est conservée.',413);
        const replay=replayConfirmed(current),body={format:WORKSHOP_BACKUP_FORMAT,exportedAt:new Date(clock(now)).toISOString(),sourceInstanceId:current.instanceId,seed:current.seed,operations:replay.operations,authority:authority(current,replay.receipts),excludes:[...EXCLUDES]};
        const backup={...body,sha256:hash(canonicalJson(body))};
        if(Buffer.byteLength(JSON.stringify(backup))>WORKSHOP_LIMITS.maxBackupBytes)fail('backup_too_large','Le journal dépasse l’export JSON de 16 Mio. La base locale est conservée.',413);
        return backup;
      });
    },
    restore(input){
      if(!input||typeof input.sha256!=='string'||!/^[a-f0-9]{64}$/.test(input.sha256))fail('invalid_operation','Empreinte de sauvegarde manquante.');
      const {sha256,...rawBody}=input;let encoded;
      try{encoded=canonicalJson(rawBody);}catch{fail('invalid_operation','Sauvegarde invalide.');}
      if(Buffer.byteLength(encoded)+80>WORKSHOP_LIMITS.maxBackupBytes)fail('backup_too_large','La sauvegarde dépasse 16 Mio.',413);
      if(hash(encoded)!==sha256)fail('checksum_mismatch','L’empreinte ne correspond pas au contenu. Aucun ajout.');
      let body;try{body=workshopBackupBody(input);}catch{fail('invalid_operation','Le journal sauvegardé ne respecte pas son contrat ou ses reçus.');}
      const entries=normalizeOperations(body.operations,WORKSHOP_LIMITS.maxJournalOperations);
      return transaction(true,()=>{
        const before=metadata();verifySeed(before.seed,body.seed);const duplicates=existing(entries);
        if(body.format===LEGACY_WORKSHOP_BACKUP_FORMAT){
          if(before.operationCount&&entries.some(entry=>!duplicates.has(entry.operation.id)))fail('legacy_merge_requires_review','Un journal v1 contenant des opérations nouvelles ne peut pas réordonner une autorité déjà confirmée. Conservez ce fichier et importez-le dans un atelier local vide.',409);
          return appendEntries(body.seed,entries.sort((a,b)=>a.operation.clock-b.operation.clock||(a.operation.id<b.operation.id?-1:a.operation.id>b.operation.id?1:0)),{legacy:true});
        }
        const incoming=body.authority;
        if(before.seed&&before.workspaceId!==incoming.workspaceId)fail('authority_conflict','Cette sauvegarde appartient à une autre autorité. Les historiques restent séparés.',409);
        if(!before.seed)initialize(body.seed,incoming.workspaceId,incoming.genesis);
        const base=metadata(),existingReplay=replayConfirmed(base),incomingReceipts=incoming.receipts;
        for(let i=0;i<Math.min(existingReplay.receipts.length,incomingReceipts.length);i++)if(canonicalJson(existingReplay.receipts[i])!==canonicalJson(incomingReceipts[i]))fail('authority_conflict','La sauvegarde contient une branche différente de la séquence confirmée. Aucun ajout.',409);
        const byId=new Map(entries.map(entry=>[entry.operation.id,entry]));
        for(const receipt of incomingReceipts.slice(base.cursor)){
          const entry=byId.get(receipt.operationId);if(duplicates.has(receipt.operationId))fail('authority_conflict','Une opération confirmée occupe une autre séquence.',409);
          persist(entry,receipt);
        }
        // Offline browser backups may contain provisional commands. Those are
        // decided now, after the complete verified confirmed prefix, in one commit.
        const confirmed=new Set(incomingReceipts.map(receipt=>receipt.operationId));
        const pending=entries.filter(entry=>!confirmed.has(entry.operation.id)).sort((a,b)=>a.operation.clock-b.operation.clock||(a.operation.id<b.operation.id?-1:a.operation.id>b.operation.id?1:0));
        appendEntries(body.seed,pending);
        replayConfirmed(metadata());
        return {...metadata(),accepted:entries.filter(entry=>!duplicates.has(entry.operation.id)).map(entry=>entry.operation.id),duplicates:[...duplicates],receipts:entries.map(entry=>readReceipt(db.prepare(rowsSQL+' WHERE o.id=?').get(entry.operation.id)))};
      });
    },
    close(){if(closed)return;db.close();closed=true;}
  };
}
