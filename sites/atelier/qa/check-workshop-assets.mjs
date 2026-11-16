import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp,readFile,writeFile,rm,readdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {Readable,Writable} from 'node:stream';
import {createWorkshopAssetRepository,handleWorkshopAssetRequest,ASSET_LIMITS} from '../local/workshop-assets.mjs';
import {createWorkshopAssetClient} from '../dist/lib/workshop-assets.js';
import {createBrowserAssetsBackup} from '../dist/lib/browser-assets-backup.js';
const root=await mkdtemp(join(tmpdir(),'boj-vault-qa-')),opened=new Set(),checks=[];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const code=expected=>failure=>failure.code===expected;
const check=async(name,run)=>{await run();checks.push(name);};
const repo=name=>{const r=createWorkshopAssetRepository({directory:join(root,name),now:()=>1700000000000});opened.add(r);return r;};
const first=Buffer.from('solid BOJ_A\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid BOJ_A\n');
const second=Buffer.from(first.toString().replaceAll('BOJ_A','BOJ_B'));
const record=(id,buffer=first)=>({id,name:id.replaceAll(':','_')+'.stl',buffer,sha256:sha(buffer),createdAt:1700000000000});
class ResponseSink extends Writable{statusCode=0;headers={};headersSent=false;chunks=[];writeHead(status,headers){this.statusCode=status;this.headers=headers;this.headersSent=true;return this;}_write(chunk,encoding,done){this.chunks.push(Buffer.from(chunk));done();}bytes(){return Buffer.concat(this.chunks);}}
async function invoke(assets,{url='/api/workshop/assets/status',method='GET',body,headers={}}={}){
  const bytes=body===undefined?null:Buffer.isBuffer(body)?body:body instanceof Blob?Buffer.from(await body.arrayBuffer()):Buffer.from(body);
  const request=Readable.from(bytes?[bytes]:[]);request.url=url;request.method=method;request.headers={'content-type':'application/octet-stream',...headers};
  const response=new ResponseSink(),finished=new Promise(resolve=>{response.once('finish',resolve);response.once('close',resolve);});
  await handleWorkshopAssetRequest({request,response,pathname:decodeURIComponent(new URL(url,'http://localhost').pathname),assets});await finished;return response;
}
function transport(assets){return async(url,options={})=>{const response=await invoke(assets,{url,method:options.method||'GET',body:options.body,headers:Object.fromEntries(Object.entries(options.headers||{}).map(([key,value])=>[key.toLowerCase(),value]))});return new Response(response.bytes(),{status:response.statusCode,headers:response.headers});};}
try{
  await check('Original STL bytes preserved with SHA, stable idempotent receipt, immutable ID and reopen',async()=>{
    let r=repo('immutable');const a=record('asset-a'),saved=await r.put(a);assert.deepEqual(saved.added,['asset-a']);assert.equal((await r.get(a.id)).sha256,a.sha256);assert.deepEqual((await r.get(a.id)).buffer,a.buffer);
    assert.deepEqual((await r.put(a)).duplicates,['asset-a']);await assert.rejects(()=>r.put({...a,buffer:second,sha256:sha(second)}),code('asset_id_conflict'));await assert.rejects(()=>r.put({...a,sha256:'0'.repeat(64)}),code('checksum_mismatch'));await assert.rejects(()=>r.put({...a,name:'../escape.stl'}),code('invalid_asset_name'));
    const defaults={id:'default-date',name:'default.stl',buffer:first,sha256:sha(first)};await r.put(defaults);assert.deepEqual((await r.put(defaults)).duplicates,['default-date']);
    r.close();r=repo('immutable');assert.deepEqual((await r.get(a.id)).buffer,first);assert.equal(r.status().fileCount,2);assert.equal(r.status().capabilities.printerCommands,false);
  });
  await check('Real vault export/restoration verifies every original byte and is idempotent',async()=>{
    const source=repo('archive-source'),target=repo('archive-target');await source.put(record('a'));await source.put(record('b',second));const archive=await source.exportArchive();
    const bytes=await readFile(archive.path);assert.equal(bytes.length,archive.byteLength);assert.equal(bytes.subarray(0,8).toString(),'BOJAST01');
    const receipt=await target.restoreArchive(archive.path);assert.equal(receipt.verifiedFiles,2);assert.equal(receipt.restoredFiles,2);assert.deepEqual((await target.get('a')).buffer,first);assert.deepEqual((await target.get('b')).buffer,second);
    assert.equal((await target.restoreArchive(archive.path)).duplicates.length,2);await archive.cleanup();
  });
  await check('Corrupt last STL, truncated archive or identity conflict never exposes a partial restoration',async()=>{
    const source=repo('bad-source');await source.put(record('a'));await source.put(record('b',second));const archive=await source.exportArchive(),bytes=await readFile(archive.path),bad=Buffer.from(bytes);bad[bad.length-1]^=1;const path=join(root,'bad.bojassets');await writeFile(path,bad);const target=repo('bad-target');
    await assert.rejects(()=>target.restoreArchive(path),code('checksum_mismatch'));assert.equal(target.status().fileCount,0);assert.deepEqual(await readdir(join(target.directory,'staging')),[]);
    await writeFile(path,bytes.subarray(0,bytes.length-1));await assert.rejects(()=>target.restoreArchive(path),code('invalid_archive'));assert.equal(target.status().fileCount,0);
    const conflict=repo('archive-conflict');await conflict.put(record('b',first));await assert.rejects(()=>conflict.restoreArchive(archive.path),code('asset_id_conflict'));assert.equal(conflict.status().fileCount,1);assert.equal(await conflict.get('a'),null);assert.deepEqual((await conflict.get('b')).buffer,first);await archive.cleanup();
  });
  await check('Missing binaries can be restored from verified archive; corrupt existing bytes are reported without overwrite',async()=>{
    const r=repo('recovery'),a=record('recover');await r.put(a);const archive=await r.exportArchive(),path=join(r.directory,'blobs',a.sha256+'.stl');await rm(path);await assert.rejects(()=>r.get(a.id),code('asset_integrity'));await r.restoreArchive(archive.path);assert.deepEqual((await r.get(a.id)).buffer,first);
    await writeFile(path,Buffer.alloc(first.length));await assert.rejects(()=>r.get(a.id),code('asset_integrity'));await assert.rejects(()=>r.restoreArchive(archive.path),code('asset_integrity'));assert.deepEqual(await readFile(path),Buffer.alloc(first.length));await archive.cleanup();
  });
  await check('Browser export includes current and replaced originals and restores directly into tower vault',async()=>{
    const records=new Map([['old',record('old')],['current',record('current',second)]]),state={projects:[{pieces:[{assetId:'current',assetSha256:sha(second)}]}]},journal={operations:[{type:'UPDATE_PIECE',payload:{patch:{assetId:'old',assetSha256:sha(first)}}}]};
    const archive=await createBrowserAssetsBackup(state,{journal,readAsset:async id=>records.get(id),exportedAt:1700000000000});assert.equal(archive.summary.files,2);assert.ok(archive.summary.excludes.includes('workshop_journal'));const path=join(root,'browser.bojassets');await writeFile(path,Buffer.from(await archive.blob.arrayBuffer()));
    const target=repo('browser-target');assert.equal((await target.restoreArchive(path)).verifiedFiles,2);assert.deepEqual((await target.get('old')).buffer,first);assert.deepEqual((await target.get('current')).buffer,second);
    await assert.rejects(()=>createBrowserAssetsBackup(state,{journal,readAsset:async id=>id==='current'?record('current',first):records.get(id)}),/empreinte/);
    await assert.rejects(()=>createBrowserAssetsBackup(state,{journal,readAsset:async id=>id==='old'?null:records.get(id)}),/absent/);
  });
  await check('Same-origin HTTP/browser client uploads, downloads, lists and restores complete archive without listener',async()=>{
    const r=repo('http'),client=createWorkshopAssetClient({fetchImpl:transport(r)}),a=record('asset:encoded');assert.equal((await client.status()).available,true);assert.equal((await client.putAsset(a)).sha256,a.sha256);assert.deepEqual(Buffer.from((await client.readAsset(a.id,{expectedSha256:a.sha256})).buffer),first);assert.equal(await client.readAsset('absent'),null);assert.equal((await client.listAssets()).assets.length,1);
    const archive=await r.exportArchive(),bytes=await readFile(archive.path),target=repo('http-restore'),other=createWorkshopAssetClient({fetchImpl:transport(target)});assert.equal((await other.restoreBackup(new Blob([bytes]))).verifiedFiles,1);assert.deepEqual(Buffer.from((await other.readAsset(a.id)).buffer),first);
    const downloaded=await invoke(r,{url:'/api/workshop/assets/backup'});assert.equal(downloaded.statusCode,200);assert.equal(downloaded.bytes().subarray(0,8).toString(),'BOJAST01');await archive.cleanup();
    const oversize=await invoke(r,{url:'/api/workshop/assets/too-large',method:'POST',body:first,headers:{'content-length':String(ASSET_LIMITS.maxFileBytes+1)}});assert.equal(oversize.statusCode,413);assert.equal(r.status().fileCount,1);
  });
  await check('Client refuses wrong receipt, unexpected SHA and lying Content-Length before oversized allocation',async()=>{
    const r=repo('client-invalid'),a=record('valid');await r.put(a);const base=transport(r);
    const wrong=createWorkshopAssetClient({fetchImpl:async(url,options)=>{const response=await base(url,options);if(options.method==='POST'){const value=await response.json();value.asset.sha256='0'.repeat(64);return new Response(JSON.stringify(value));}return response;}});await assert.rejects(()=>wrong.putAsset(a),code('invalid_receipt'));
    const client=createWorkshopAssetClient({fetchImpl:base});await assert.rejects(()=>client.readAsset(a.id,{expectedSha256:'0'.repeat(64)}),code('checksum_mismatch'));
    const lying=createWorkshopAssetClient({fetchImpl:async()=>new Response(new Uint8Array(first.length+1),{headers:{'content-length':String(first.length),'x-boj-asset-id':a.id,'x-boj-sha256':a.sha256,'x-boj-file-name':a.name,'x-boj-created-at':String(a.createdAt)}})});await assert.rejects(()=>lying.readAsset(a.id),code('response_too_large'));
  });
  await check('Offline status is bounded and returns a usable unavailable state',async()=>{
    let aborted=false;const client=createWorkshopAssetClient({fetchImpl:async(url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>{aborted=true;reject(new DOMException('Aborted','AbortError'));},{once:true}))});const status=await client.status();assert.equal(aborted,true);assert.equal(status.available,false);assert.equal(status.code,'transfer_timeout');
  });
  const report={ok:true,node:process.version,checks,originalSHA256:[sha(first),sha(second)],serverArchiveRoundtrip:true,browserArchiveToServerRoundtrip:true,listenersStarted:0,physicalCommands:0};
  await writeFile(new URL('./workshop-assets-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}finally{for(const r of opened)r.close();await rm(root,{recursive:true,force:true});}
