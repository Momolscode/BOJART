import assert from 'node:assert/strict';
import {Readable, Writable} from 'node:stream';
import {mkdtemp, rm, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';
import {createGatewayHandler} from '../local/jev-gateway.mjs';
import {createWorkshopAssetRepository} from '../local/workshop-assets.mjs';
import {createJevProvider, DEFAULT_JEV_MODEL} from '../local/jev-provider.mjs';
import {createDecisionService, normalizeTypeSafeDecisionResponse} from '../local/jev-decisions.mjs';
import {createWorkshopGenesis} from '../dist/lib/workshop.js';
import {inspectDeclaredPreparation} from '../dist/lib/preparation.js';
import {buildAttentionDecisionRequest} from '../dist/lib/decision-context.js';
import {decisionCandidates, DECISION_POLICY_VERSION} from '../dist/lib/decision-contract.js';
import {requestProjectDecision, getDecisionProviderStatus} from '../dist/lib/decision-client.js';
import {createWorkshopAssetClient} from '../dist/lib/workshop-assets.js';

class Capture extends Writable {
  headersSent=false;headers={};chunks=[];
  writeHead(status,headers){this.statusCode=status;this.headers=headers;this.headersSent=true;return this;}
  _write(chunk,_encoding,done){this.chunks.push(Buffer.from(chunk));done();}
  bytes(){return Buffer.concat(this.chunks);}
  json(){return JSON.parse(this.bytes().toString());}
}
async function invoke(handler,url,{method='GET',headers={},body}={}){
  const bytes=body===undefined?null:typeof body==='string'?Buffer.from(body):Buffer.isBuffer(body)?body:body instanceof ArrayBuffer?Buffer.from(body):Buffer.from(await body.arrayBuffer());
  const request=Readable.from(bytes?[bytes]:[]);request.method=method;request.url=url;
  request.headers={host:'127.0.0.1:3137',...(method==='POST'?{origin:'http://127.0.0.1:3137'}:{}),...Object.fromEntries(Object.entries(headers).map(([key,value])=>[key.toLowerCase(),value]))};
  const response=new Capture(),finished=new Promise(resolve=>response.once('finish',resolve));
  await handler(request,response);await finished;return response;
}

const checks=[],root=await mkdtemp(join(tmpdir(),'boj-v9-gateway-'));
const assets=createWorkshopAssetRepository({directory:join(root,'vault')});
let decisionCalls=0;
const visual=createJevProvider({apiKey:'',fetchImpl:()=>{throw new Error('No upstream allowed');}});
const provider={status:()=>({ok:true,provider:'typesafe',configured:true,connected:false,model:DEFAULT_JEV_MODEL,policyVersion:DECISION_POLICY_VERSION,advisoryOnly:true}),async decide(request){
  decisionCalls++;const candidates=decisionCandidates(request),probabilities=Object.fromEntries(candidates.map((_,index)=>['c'+String(index+1).padStart(2,'0'),index===0?.9:0]));probabilities.none=.1;
  return normalizeTypeSafeDecisionResponse({model:DEFAULT_JEV_MODEL,answers:{decision:{type:'choice',choice:'c01',confidence:.9,probabilities}},usage:{input_tokens:1,output_tokens:1}},request);
}};
const handler=createGatewayHandler({provider:visual,assets,decisions:createDecisionService({provider})});
const transport=async(url,options={})=>{const response=await invoke(handler,url,options);return new Response(response.bytes(),{status:response.statusCode,headers:response.headers});};
try{
  const state=createWorkshopGenesis({version:1,at:1780000000000}).state,project=state.projects[0];
  const report=inspectDeclaredPreparation(state,project.id),{request}=buildAttentionDecisionRequest(report,project,{requestId:'gateway-integration'});
  const status=await getDecisionProviderStatus({fetchImpl:transport});assert(status.configured);assert(!status.connected);assert.equal(decisionCalls,0);
  const result=await requestProjectDecision(request,{fetchImpl:transport,getCurrentRequest:()=>request});assert.equal(result.context.projectId,project.id);assert.equal(result.decision.candidateId,decisionCandidates(request)[0].id);assert.equal(decisionCalls,1);
  checks.push('Real decision client → gateway → service → normalizer → client validator, with one injected provider result and no upstream request.');
  for(const headers of [{origin:'https://foreign.invalid'},{host:'foreign.invalid'},{'sec-fetch-site':'cross-site'}]){const rejected=await invoke(handler,'/api/decisions',{method:'POST',headers:{'content-type':'application/json',...headers},body:JSON.stringify(request)});assert.equal(rejected.statusCode,403);}assert.equal(decisionCalls,1);
  const oversized=await invoke(handler,'/api/decisions',{method:'POST',headers:{'content-type':'application/json'},body:'x'.repeat(65537)});assert.equal(oversized.statusCode,413);assert.equal(decisionCalls,1);
  const unknown=await invoke(handler,'/api/decisions',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({...request,tool:'start_print'})});assert.equal(unknown.statusCode,400);assert.equal(decisionCalls,1);
  checks.push('Origin, Host, fetch-site, body size and unknown action rejected before a decision provider is called.');
  const bytes=Buffer.from('solid example\nendsolid example'),buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.length),sha256=createHash('sha256').update(bytes).digest('hex');
  const client=createWorkshopAssetClient({fetchImpl:transport});assert((await client.status()).available);
  const metadata=await client.putAsset({id:'gateway-file',name:'example.stl',buffer,createdAt:1780000000000});assert.equal(metadata.sha256,sha256);
  const recovered=await client.readAsset('gateway-file',{expectedSha256:sha256});assert(Buffer.from(recovered.buffer).equals(bytes));
  assert.equal(await client.readAsset('missing'),null);await assert.rejects(()=>client.readAsset('gateway-file',{expectedSha256:'a'.repeat(64)}));
  checks.push('Real asset client → guarded gateway → immutable vault; bytes and expected SHA verified on recovery, missing and mismatched files distinguished.');
  const denied=await invoke(handler,'/api/workshop/assets/foreign',{method:'POST',headers:{origin:'https://foreign.invalid','content-type':'application/octet-stream'},body:bytes});assert.equal(denied.statusCode,403);assert.equal(assets.status().fileCount,1);
  const head=await invoke(handler,'/api/decisions/status',{method:'HEAD'});assert.equal(head.statusCode,200);assert.equal(head.bytes().length,0);
  const noServices=createGatewayHandler({provider:visual});const absent=await invoke(noServices,'/api/decisions/status');assert.equal(absent.statusCode,503);
  checks.push('Asset write denied before storage for a foreign origin; decision HEAD and absent-service status are truthful.');
  const output={ok:true,checks,scope:'Real modules and in-process streams; no listener, browser engine, credentials, TypeSafe request or machine command.'};
  await writeFile(new URL('./v9-gateway-results.json',import.meta.url),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));
}finally{assets.close();await rm(root,{recursive:true,force:true});}
