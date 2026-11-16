import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {mkdtemp,mkdir,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createWorkshopRepository} from '../local/workshop-repository.mjs';
import {canonicalWorkshopJSON,WorkshopStore,replayWorkshopOperations,replayWorkshopAuthority} from '../dist/lib/workshop.js';
import {createWorkshopBackup,inspectWorkshopBackup} from '../dist/lib/workshop-backup.js';
import {createWorkshopSync} from '../dist/lib/workshop-sync.js';
const root=await mkdtemp(join(tmpdir(),'boj-authority-qa-')),open=new Set(),checks=[],proof={};
const seed={version:1,at:1700000000000},now=seed.at+10000;
const hash=value=>createHash('sha256').update(canonicalWorkshopJSON(value)).digest('hex');
const check=async(name,run)=>{await run();checks.push(name);};
const repo=name=>{const value=createWorkshopRepository({directory:join(root,name),now:()=>now});open.add(value);return value;};
const op=(id,patch={notes:id},version=0)=>({version:1,id,clock:1,at:now,type:'UPDATE_PROJECT',payload:{id:'sculpture-xl',patch},expected:{entityVersion:version},context:{projectId:'sculpture-xl',projectName:'SCULPTURE XL',pieceId:null,machineId:null,originProjectId:'sculpture-xl'}});
const imported=(id,asset,version=0)=>({...op(id,{},version),type:'UPDATE_PIECE',payload:{projectId:'sculpture-xl',id:'buste',expectedPieceRevision:1,expectedAssetId:null,patch:{assetId:asset,dims:[170,110,230]}}});
const batch=(r,operations)=>({version:2,workspaceId:r.status().workspaceId,seed,operations});
const replay=r=>{const b=r.backup();return replayWorkshopAuthority(b.seed,b.operations,b.authority);};
const project=r=>replay(r).state.projects.find(p=>p.id==='sculpture-xl');
const code=expected=>failure=>failure.code===expected;
class Storage{data=new Map();get length(){return this.data.size;}key(i){return [...this.data.keys()][i]??null;}getItem(k){return this.data.get(k)??null;}setItem(k,v){this.data.set(k,String(v));}}
function store(){globalThis.localStorage=new Storage();const s=new WorkshopStore();s.mergeJournal({version:1,seed,operations:[]},{allowEmptyAdoption:true});return s;}
function transport(r){return async(url,options={})=>{let body,status=200;try{const path=new URL(url,'http://localhost').pathname;if(path.endsWith('/status'))body=r.status();else if(path.endsWith('/backup'))body=options.method==='POST'?r.restore(JSON.parse(options.body)):r.backup();else body=options.method==='POST'?r.append(JSON.parse(options.body)):r.operations(Number(new URL(url,'http://localhost').searchParams.get('after')||0));}catch(error){status=error.status||500;body={ok:false,code:error.code,message:error.message};}return new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json'}});};}
try{
  await check('Concurrent guards: first receipt survives lower-clock/ID arrival, retry and restart',()=>{
    let first=repo('concurrent');const second=repo('concurrent');
    const z=imported('z-fenetre','asset-z'),a=imported('a-fenetre','asset-a');
    const accepted=first.append(batch(first,[z]));assert.equal(accepted.receipts[0].outcome.ok,true);assert.equal(accepted.receipts[0].seq,1);
    const rejected=second.append(batch(second,[a]));assert.equal(rejected.receipts[0].outcome.ok,false);assert.equal(rejected.receipts[0].seq,2);
    assert.equal(project(first).pieces[0].assetId,'asset-z');assert.deepEqual(first.append(batch(first,[z])).receipts,accepted.receipts);
    assert.deepEqual(first.operations().receipts[0],accepted.receipts[0]);first.close();first=repo('concurrent');
    assert.deepEqual(first.operations().receipts[0],accepted.receipts[0]);assert.equal(project(first).pieces[0].assetId,'asset-z');
    Object.assign(proof,{synthetic:true,seed,commands:[z,a].map(operation=>({id:operation.id,clock:operation.clock,expectedPieceRevision:operation.payload.expectedPieceRevision,expectedAssetId:operation.payload.expectedAssetId,expectedEntityVersion:operation.expected.entityVersion})),firstReceipt:accepted.receipts[0],secondReceipt:rejected.receipts[0],afterRestart:{assetId:project(first).pieces[0].assetId,pieceRevision:project(first).pieces[0].revision,receiptUnchanged:true}});
    assert.throws(()=>first.append({version:1,seed,operations:[op('obsolete')]}),code('upgrade_required'));
    const missing=op('missing');delete missing.expected.entityVersion;assert.throws(()=>first.append(batch(first,[missing])),code('expected_version_required'));
    assert.equal(first.status().operationCount,2);
  });
  await check('Expected aggregate version protects notes too; immutable-ID conflict rolls back the complete batch',()=>{
    const r=repo('aggregate');r.append(batch(r,[op('first')]));
    assert.equal(r.append(batch(r,[op('stale')])).receipts[0].outcome.ok,false);assert.equal(project(r).notes,'first');
    const before=r.status().cursor;assert.throws(()=>r.append(batch(r,[op('valid-new',{},1),op('first',{notes:'changed'})])),code('operation_id_conflict'));assert.equal(r.status().cursor,before);
    const accepted=r.append(batch(r,[op('valid-now',{notes:'current'},1)])).receipts[0];assert.equal(accepted.entityVersionBefore,1);assert.equal(accepted.entityVersionAfter,2);assert.equal(project(r).notes,'current');
  });
  await check('Legacy SQLite migration freezes prior logical winner and keeps every original row byte-for-byte',async()=>{
    const directory=join(root,'legacy');await mkdir(directory);
    const db=new DatabaseSync(join(directory,'workshop.sqlite3'));db.exec('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL) STRICT;CREATE TABLE operations(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,canonical TEXT NOT NULL,digest TEXT NOT NULL,received_at INTEGER NOT NULL) STRICT;');
    for(const [key,value] of [['schema_version','1'],['instance_id','workshop-12345678-1234-1234-1234-123456789abc'],['seed',canonicalWorkshopJSON(seed)]])db.prepare('INSERT INTO metadata VALUES(?,?)').run(key,value);
    const operations=[imported('z-legacy','asset-z'),imported('a-legacy','asset-a')];for(const operation of operations){delete operation.expected.entityVersion;const canonical=canonicalWorkshopJSON(operation);db.prepare('INSERT INTO operations(id,canonical,digest,received_at) VALUES(?,?,?,?)').run(operation.id,canonical,hash(operation),now);}
    const before=db.prepare('SELECT * FROM operations ORDER BY seq').all();db.close();
    const r=repo('legacy');assert.equal(project(r).pieces[0].assetId,'asset-a');assert.deepEqual(r.operations().operations.map(x=>x.id),['a-legacy','z-legacy']);
    const inspect=new DatabaseSync(join(directory,'workshop.sqlite3'),{readOnly:true});assert.deepEqual(inspect.prepare('SELECT * FROM operations ORDER BY seq').all(),before);assert.equal(inspect.prepare('SELECT value FROM metadata WHERE key=?').get('schema_version').value,'2');assert.ok(inspect.prepare('SELECT value FROM metadata WHERE key=?').get('genesis').value.includes('"state"'));inspect.close();
    assert.equal(replayWorkshopOperations(seed,operations).state.projects[0].pieces[0].assetId,project(r).pieces[0].assetId);
  });
  await check('V2 backup restores exact receipts, genesis and identity into a new DB; older backup cannot roll back or branch',async()=>{
    const source=repo('backup-source'),destination=repo('backup-destination');source.append(batch(source,[op('backup-first')]));const backup=source.backup(),inspected=await inspectWorkshopBackup(backup);
    assert.equal(inspected.journal.version,2);assert.equal(inspected.summary.confirmed,1);assert.ok(inspected.summary.excludes.includes('stl_binaries'));
    destination.restore(backup);assert.notEqual(destination.status().instanceId,source.status().instanceId);assert.equal(destination.status().workspaceId,source.status().workspaceId);assert.deepEqual(destination.backup().authority,backup.authority);
    destination.append(batch(destination,[op('newer',{notes:'keep newer'},1)]));destination.restore(backup);assert.equal(project(destination).notes,'keep newer');assert.equal(destination.status().cursor,2);
    const branch=structuredClone(backup);branch.authority.receipts[0].receivedAt++;const {sha256,...body}=branch;branch.sha256=hash(body);assert.throws(()=>destination.restore(branch),code('authority_conflict'));assert.equal(destination.status().cursor,2);
    const corrupt=structuredClone(backup);corrupt.operations[0].payload.patch.notes='corrupt';assert.throws(()=>destination.restore(corrupt),code('checksum_mismatch'));
  });
  await check('Legacy portable backup is accepted atomically only before authoritative history or as exact duplicates',async()=>{
    const r=repo('legacy-backup'),z=imported('z-old','asset-z'),a=imported('a-old','asset-a');delete z.expected.entityVersion;delete a.expected.entityVersion;
    const backup=await createWorkshopBackup({version:1,seed,operations:[z,a]},{now});r.restore(backup);assert.equal(project(r).pieces[0].assetId,'asset-a');assert.equal(r.restore(backup).accepted.length,0);
    const newLegacy=await createWorkshopBackup({version:1,seed,operations:[op('other-old')]},{now});assert.throws(()=>r.restore(newLegacy),code('legacy_merge_requires_review'));assert.equal(r.status().cursor,2);
  });
  await check('Browser follows server sequence, shows provisional work, survives reload and retains refused payloads',()=>{
    const r=repo('browser'),s=store();r.append(batch(r,[imported('z-browser','asset-z')]));r.append(batch(r,[imported('a-browser','asset-a')]));
    const b=r.backup();s.mergeJournal({version:2,seed,operations:b.operations,authority:b.authority});assert.equal(s.getProject().pieces[0].assetId,'asset-z');assert.equal(s._results.get('z-browser').confirmed,true);assert.equal(s._results.get('a-browser').ok,false);
    const local=s.dispatch('UPDATE_PROJECT',{id:'sculpture-xl',patch:{notes:'provisional'}});assert.equal(local.ok,true);assert.equal(local.confirmed,false);
    r.append(batch(r,[op('other-screen',{notes:'confirmed remote'},1)]));const pending=s.exportJournal().operations.find(x=>x.id===local.operationId);r.append(batch(r,[pending]));
    const latest=r.backup();s.mergeJournal({version:2,seed,operations:latest.operations,authority:latest.authority});assert.equal(s.getProject().notes,'confirmed remote');assert.equal(s._results.get(local.operationId).ok,false);
    const next=new WorkshopStore();assert.equal(next.getProject().notes,'confirmed remote');assert.equal(next.exportJournal().authority.receipts.length,4);next.dispose();s.dispose();
  });
  await check('Actual sync v2 bootstraps legacy history, reconnects and confirms new work through complete receipts',async()=>{
    const r=repo('sync'),s=store();s.dispatch('UPDATE_PROJECT',{id:'sculpture-xl',patch:{notes:'before connection'}});
    const sync=createWorkshopSync({store:s,fetchImpl:transport(r)});const first=await sync.connect();assert.equal(first.durable,true,first.message);assert.equal(s.exportJournal().version,2);assert.equal(r.status().cursor,1);
    s.dispatch('UPDATE_PROJECT',{id:'sculpture-xl',patch:{notes:'after connection'}});const second=await sync.sync();assert.equal(second.durable,true,second.message);assert.equal(second.pending,0);assert.equal(project(r).notes,'after connection');assert.equal(s._results.get(s.exportJournal().authority.receipts.at(-1).operationId).confirmed,true);
    sync.stop();s.dispose();
  });
  await check('Two screens connecting an empty authority together receive one stable winner and one auditable refusal',async()=>{
    const r=repo('sync-race'),a=store(),b=store();
    a.dispatch('UPDATE_PROJECT',{id:'sculpture-xl',patch:{notes:'Screen A'}});b.dispatch('UPDATE_PROJECT',{id:'sculpture-xl',patch:{notes:'Screen B'}});
    const sa=createWorkshopSync({store:a,fetchImpl:transport(r)}),sb=createWorkshopSync({store:b,fetchImpl:transport(r)});
    try {
      await Promise.all([sa.connect(),sb.connect()]);await sa.sync();await sb.sync();
      assert.equal(sa.status.durable,true,sa.status.message);assert.equal(sb.status.durable,true,sb.status.message);
      assert.equal(sa.status.pending,0);assert.equal(sb.status.pending,0);assert.equal(r.status().cursor,2);
      const receipts=r.operations().receipts;assert.equal(receipts.filter(row=>row.outcome.ok).length,1);assert.equal(receipts.filter(row=>!row.outcome.ok).length,1);
      assert.equal(a.getProject().notes,project(r).notes);assert.equal(b.getProject().notes,project(r).notes);
    } finally {sa.stop();sb.stop();a.dispose();b.dispose();}
  });
  await check('Rebinding to a restored clone verifies the old prefix and refuses a divergent branch with the same workspace ID',async()=>{
    const a=repo('clone-a'),b=repo('clone-b');a.append(batch(a,[]));b.restore(a.backup());a.append(batch(a,[op('branch-a',{notes:'A'})]));b.append(batch(b,[op('branch-b',{notes:'B'})]));
    const s=store(),backup=a.backup();s.mergeJournal({version:2,seed,operations:backup.operations,authority:backup.authority});
    const sync=createWorkshopSync({store:s,fetchImpl:transport(b)});
    try {const state=await sync.connect();assert.equal(state.mode,'conflict');assert.equal(state.durable,false);assert.equal(s.getProject().notes,'A');assert.equal(s.exportJournal().authority.receipts[0].operationId,'branch-a');assert.equal(project(b).notes,'B');}
    finally {sync.stop();s.dispose();}
  });
  await check('Asset identity replacement clears the old SHA and invalidates preparation through piece revision',()=>{
    const s=store();const first=s.dispatch('UPDATE_PIECE',{projectId:'sculpture-xl',id:'buste',patch:{assetId:'original',assetSha256:'a'.repeat(64)}});assert.equal(first.ok,true);
    const revision=s.getProject().pieces[0].revision;assert.equal(s.dispatch('UPDATE_PIECE',{projectId:'sculpture-xl',id:'buste',patch:{assetId:'replacement'}}).ok,true);
    assert.equal(s.getProject().pieces[0].assetSha256,null);assert.ok(s.getProject().pieces[0].revision>revision);s.dispose();
  });
  await check('Logical corruption refuses reopen without deleting original SQLite rows',()=>{
    const r=repo('corrupt');r.append(batch(r,[op('preserve')]));r.close();const db=new DatabaseSync(join(root,'corrupt','workshop.sqlite3'));db.prepare('UPDATE decisions SET digest=? WHERE seq=1').run('0'.repeat(64));db.close();assert.throws(()=>repo('corrupt'),code('storage_unavailable'));const read=new DatabaseSync(join(root,'corrupt','workshop.sqlite3'),{readOnly:true});assert.equal(read.prepare('SELECT COUNT(*) AS count FROM operations').get().count,1);read.close();
  });
  const report={ok:true,protocolVersion:2,node:process.version,checks,concurrencyProof:proof,physicalCommands:0,listenersStarted:0};
  await writeFile(new URL('./workshop-authority-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({ok:true,checks,physicalCommands:0,listenersStarted:0},null,2));
}finally{for(const r of open)r.close();await rm(root,{recursive:true,force:true});delete globalThis.localStorage;}
