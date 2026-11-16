import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {DECISION_DOMAINS,DECISION_POLICY_VERSION,DecisionError,normalizeDecisionRequest,decisionCandidates,decisionFingerprint,recommendLocalDecision,validateProjectDecision} from '../dist/lib/decision-contract.js';
import {buildPreparationDecisionRequest,buildAttentionDecisionRequest,buildEditorialDecisionRequest} from '../dist/lib/decision-context.js';
import {requestProjectDecision,getDecisionProviderStatus} from '../dist/lib/decision-client.js';
import {buildTypeSafeDecisionRequest,normalizeTypeSafeDecisionResponse,createJevDecisionProvider,createDecisionService} from '../local/jev-decisions.mjs';
import {JevError,TYPESAFE_ENDPOINT,DEFAULT_JEV_MODEL} from '../local/jev-provider.mjs';
import {normalizeFleetRecord} from '../dist/lib/fleet-registry.js';
import {inspectDeclaredPreparation} from '../dist/lib/preparation.js';
import {createEditDraft} from '../dist/lib/edit-plan.js';
import {CONTENT_CATALOG} from '../dist/lib/content-catalog.js';

// Synthetic measurements and mocked transport only: no browser, server, real credential or physical device.
const checks=[];
async function check(name,run){await run();checks.push(name);}
const clone=value=>structuredClone(value),at=Date.UTC(2026,9,19,3),now=()=>at;
const secret='qa-credential-never-log',privateName='PRIVATE_CLIENT_NAME',privateNote='PRIVATE_OPERATOR_NOTE';
const registry=normalizeFleetRecord({origin:'declared',manufacturer:'QA',model:privateName,serial:'serial-private',technology:'fdm',usableVolumeMm:[120,90,130],material:'QA material',slicer:{name:'QA slicer',version:'1',machineProfile:'private/profile/path',materialProfile:'private/material'},notes:privateNote},null,at);
const project={id:'project-private',revision:4,name:privateName,kind:'sculpture',quantity:1,height:100,notes:privateNote,pieces:[{id:'piece-private',revision:2,name:privateName,assetId:'asset-private',unit:'mm',tech:'fdm',dims:[80,40,60]}]};
const state={projects:[project],machines:[{id:'machine-private',registry}],jobs:[{id:'fake-running',simulated:true,status:'running',duration:123}]};
const assetEvidence=[{projectId:project.id,pieceId:project.pieces[0].id,pieceRevision:2,assetId:'asset-private',unit:'mm',status:'measured',checkedAt:at,sha256:'a'.repeat(64),dimsMm:[80,40,60],triangles:12,byteLength:684}];
const report=inspectDeclaredPreparation(state,project.id,{assetEvidence});
const preparation=()=>buildPreparationDecisionRequest(report,{requestId:'request-preparation',pieceId:'piece-private',machineId:'machine-private',goal:'clearance'});
const attention=()=>buildAttentionDecisionRequest(report,project,{requestId:'request-attention'});
const editorial=()=>buildEditorialDecisionRequest(project,{requestId:'request-editorial',goal:'showcase'});
const json=body=>new Response(JSON.stringify(body),{headers:{'Content-Type':'application/json'}});
const code=value=>error=>(error instanceof DecisionError||error instanceof JevError)&&error.code===value&&!error.message.includes(secret);
function fixture(request,{choice='c01',top=.9,model=DEFAULT_JEV_MODEL}={}){
  const aliases=Object.keys(buildTypeSafeDecisionRequest(request).questions.decision.criteria);
  const probability=(1-top)/(aliases.length-1);
  return{model,answers:{decision:{type:'choice',choice,confidence:.82,probabilities:Object.fromEntries(aliases.map(alias=>[alias,alias===choice?top:probability]))}},usage:{input_tokens:250,output_tokens:20}};
}

await check('Trois domaines actifs et domaines futurs explicitement non raccordés',()=>{
  assert.deepEqual(DECISION_DOMAINS.filter(domain=>domain.status==='implemented_advisory').map(domain=>domain.id),['preparation','attention','editorial']);
  for(const domain of ['slicing','scheduling','quality','commercial','publication','robotics']){
    assert.equal(DECISION_DOMAINS.find(value=>value.id===domain).status,'future_contract');
    assert.throws(()=>normalizeDecisionRequest({...editorial().request,domain}),code('domain_unavailable'));
  }
});
await check('Candidats de préparation régénérés depuis les mesures, sans dimensions de démonstration',()=>{
  const value=preparation();assert.equal(value.unavailableReason,null);assert.equal(value.options.length,6);
  assert.equal(value.request.evidence.piece.sha256,'a'.repeat(64));
  assert.equal(value.request.evidence.machine.revision,1);
  for(const option of value.options){assert.equal(option.target.action,'inspect_orientation');assert.ok(option.facts.clearanceMm.every(value=>value>=0));assert.equal(option.target.pieceId,'piece-private');}
  const changed=clone(report);changed.pieces[0].storedDimensionsMm=[999,999,999];
  assert.deepEqual(buildPreparationDecisionRequest(changed,{requestId:'request-preparation',pieceId:'piece-private',machineId:'machine-private',goal:'clearance'}).request,value.request);
});
await check('Sans STL mesuré, fiche réelle, bon procédé ou volume : aucun candidat inventé',()=>{
  for(const change of [r=>{r.pieces[0].file.status='unchecked';},r=>{r.pieces[0].assetId=null;},r=>{r.machines[0].declared=false;},r=>{r.machines[0].record.technology='resin';},r=>{r.machines[0].record.usableVolumeMm=null;},r=>{r.pieces[0].dimensionsMm=[999,999,999];},r=>{r.pieces[0].dimensionsMm=[0,1,2];}]){
    const r=clone(report);change(r);const result=buildPreparationDecisionRequest(r,{requestId:'q',pieceId:'piece-private',machineId:'machine-private'});assert.equal(result.request,null);assert.equal(result.options.length,0);assert.ok(result.unavailableReason);
  }
});
await check('Contrat fermé : prompts, outils, endpoints, candidats et politique étrangère refusés',()=>{
  const request=preparation().request;
  for(const change of [r=>{r.prompt='execute';},r=>{r.url='https://other.invalid';},r=>{r.apiKey=secret;},r=>{r.candidates=[{id:'print'}];},r=>{r.evidence.action='start_print';},r=>{r.context.projectRevision=0;},r=>{r.evidence.piece.dimensionsMm=[80,40,NaN];},r=>{r.evidence.piece.sha256='invalid';},r=>{r.evidence.machine.revision=0;},r=>{r.goal='print';}]){const bad=clone(request);change(bad);assert.throws(()=>normalizeDecisionRequest(bad),code('invalid_request'));}
  assert.throws(()=>normalizeDecisionRequest({...request,policyVersion:'other'}),code('policy_mismatch'));
  const polluted=JSON.parse(JSON.stringify(request).replace('"format"','"__proto__":{},"format"'));assert.throws(()=>normalizeDecisionRequest(polluted),code('invalid_request'));
});
await check('Empreinte liée aux preuves : fichier, unité, machine, objectif et révision',async()=>{
  const request=preparation().request,hash=await decisionFingerprint(request);
  for(const change of [r=>{r.evidence.piece.assetId='another';},r=>{r.evidence.piece.sha256='b'.repeat(64);},r=>{r.evidence.piece.unit='inch';},r=>{r.evidence.machine.revision++;},r=>{r.context.projectRevision++;},r=>{r.goal='low_height';}]){const changed=clone(request);change(changed);assert.notEqual(await decisionFingerprint(changed),hash);}
  const reordered=Object.fromEntries(Object.entries(request).reverse());assert.equal(await decisionFingerprint(reordered),hash);
});
await check('Attention : uniquement fichiers, fiches et intentions existants ; jobs simulés exclus',()=>{
  const value=attention();assert.ok(value.options.some(option=>option.id==='piece:piece-private'));assert.ok(value.options.some(option=>option.id==='machine:machine-private'));assert.ok(value.options.some(option=>option.id==='edit:new'));assert.equal(JSON.stringify(value.request).includes('fake-running'),false);
  const changed=clone(project);changed.pieces[0].assetId='changed';assert.throws(()=>buildAttentionDecisionRequest(report,changed,{requestId:'q'}),code('invalid_context'));
  const altered=clone(project);altered.revision++;assert.throws(()=>buildAttentionDecisionRequest(report,altered,{requestId:'q'}),code('invalid_context'));
});
const source=CONTENT_CATALOG.find(source=>source.available&&source.type==='video');
const plan=createEditDraft(project);plan.sources=[{postId:source.id,relation:'reference'}];plan.beats[0]={...plan.beats[0],postId:source.id,in:1,out:2};
const edited=clone(project);edited.contentPlans=[{id:'edit-private',versions:[{revision:1,operationId:'edit-op-1',at,projectRevision:project.revision,projectName:project.name,plan}]}];
await check('Éditorial : catalogue réel et dernière version enregistrée, sans supposer des médias de projet',async()=>{
  const value=buildEditorialDecisionRequest(edited,{requestId:'edit-q',goal:'technique',planId:'edit-private'});assert.equal(value.options.length,5);assert.equal(value.request.evidence.plan.revision,1);assert.equal(value.request.evidence.plan.assignedBeats,1);assert.equal(value.request.evidence.plan.availableSourceCount,1);assert.ok(value.options.every(option=>option.target.action==='prepare_series'));
  const changed=clone(edited);changed.contentPlans[0].versions.push({...clone(changed.contentPlans[0].versions[0]),revision:2,operationId:'edit-op-2'});
  const later=buildEditorialDecisionRequest(changed,{requestId:'edit-q',goal:'technique',planId:'edit-private'});assert.notEqual(await decisionFingerprint(value.request),await decisionFingerprint(later.request));
  assert.throws(()=>buildEditorialDecisionRequest(edited,{requestId:'q',planId:'nonexistent'}),code('invalid_context'));
});
await check('Minimisation serveur : ni identifiants, noms, notes, chemins, empreintes ni clé au modèle',()=>{
  for(const request of [preparation().request,attention().request,buildEditorialDecisionRequest(edited,{requestId:'q',planId:'edit-private'}).request]){
    const value=buildTypeSafeDecisionRequest(request),text=JSON.stringify(value);
    for(const term of [privateName,privateNote,'project-private','piece-private','machine-private','asset-private','edit-private','a'.repeat(64),'private/profile/path',secret])assert.equal(text.includes(term),false);
    assert.deepEqual(Object.keys(value),['model','state','questions']);assert.equal(value.questions.decision.type,'choice');assert.ok(Object.hasOwn(value.questions.decision.criteria,'none'));assert.equal(Object.hasOwn(value,'tools'),false);
  }
});
await check('Conseil local explicite, déterministe, sans probabilité ni connexion prétendue',async()=>{
  for(const request of [preparation().request,attention().request,editorial().request]){const value=await recommendLocalDecision(request,{now});assert.equal(value.provider,'local_rules');assert.equal(value.model,null);assert.equal(value.decision.probability,null);assert.equal(value.decision.probabilities,null);assert.equal(value.execution.canStartPhysicalPrint,false);assert.equal((await validateProjectDecision(value,request,{now})).decision.reason,'local_rule');}
});
await check('Sans clé : statut non configuré et zéro appel au fournisseur',async()=>{
  let calls=0;const provider=createJevDecisionProvider({fetchImpl:async()=>{calls++;throw new Error('unexpected');}});
  assert.equal(provider.status().configured,false);assert.equal(provider.status().connected,false);assert.equal(calls,0);await assert.rejects(provider.decide(editorial().request),code('unconfigured'));assert.equal(calls,0);
});
await check('Réponse réelle normalisée : alias fermé, modèle figé, paquet original et limites invariables',async()=>{
  const request=preparation().request,value=await normalizeTypeSafeDecisionResponse(fixture(request),request,{now});
  assert.equal(value.decision.candidateId,decisionCandidates(request)[0].id);assert.equal(value.model,DEFAULT_JEV_MODEL);assert.equal(value.provenance,'client_snapshot_advisory');assert.equal(value.execution.canModifyProject,false);assert.equal(value.packetHash,await decisionFingerprint(request));assert.ok(!JSON.stringify(value).includes(secret));
});
await check('Abstention conservée pour incertitude et choix none',async()=>{
  const request=editorial().request;
  for(const options of [{top:.5},{choice:'none',top:.95}]){const value=await normalizeTypeSafeDecisionResponse(fixture(request,options),request,{now});assert.equal(value.decision.candidateId,null);assert.ok(['uncertain','no_match'].includes(value.decision.reason));}
});
await check('Choix amont inconnu, modèle inattendu, scores corrompus et capacité additionnelle refusés',async()=>{
  const request=editorial().request;
  for(const change of [r=>{r.answers.decision.choice='print';},r=>{r.model='jev-99.0.0';},r=>{r.answers.decision.probabilities.extra=.1;},r=>{r.answers.decision.probabilities.c01=NaN;},r=>{r.answers.decision.confidence=2;},r=>{r.answers.decision.probabilities.c01=.2;},r=>{r.answers.decision.action='publish';},r=>{delete r.usage;}]){const raw=fixture(request);change(raw);await assert.rejects(normalizeTypeSafeDecisionResponse(raw,request,{now}),code('invalid_response'));}
  const good=await normalizeTypeSafeDecisionResponse(fixture(request),request,{now});
  for(const change of [r=>{r.execution.canSlice=true;},r=>{r.target={action:'print'};},r=>{r.thresholds.minProbability=.5;},r=>{r.decision.candidateId='unknown';},r=>{r.provenance='machine_qualified';}]){const raw=clone(good);change(raw);await assert.rejects(validateProjectDecision(raw,request,{now}),code('invalid_response'));}
});
await check('Ancienne réponse refusée après changement de preuves ou expiration',async()=>{
  const request=preparation().request,value=await normalizeTypeSafeDecisionResponse(fixture(request),request,{now});
  const changed=clone(request);changed.evidence.machine.revision++;await assert.rejects(validateProjectDecision(value,changed,{now}),code('context_changed'));
  await assert.rejects(validateProjectDecision(value,request,{now:()=>at+60001}),code('decision_expired'));
  await assert.rejects(validateProjectDecision({...value,requestId:'foreign'},request,{now}),code('invalid_response'));
});
await check('Connexion annoncée uniquement après réponse vérifiée ; secret dans en-tête serveur seulement',async()=>{
  const request=editorial().request;let calls=0,succeed=true;
  const provider=createJevDecisionProvider({apiKey:secret,now,fetchImpl:async(url,options)=>{calls++;assert.equal(url,TYPESAFE_ENDPOINT);assert.equal(options.headers.Authorization,'Bearer '+secret);assert.equal(options.redirect,'error');assert.equal(JSON.stringify(JSON.parse(options.body)).includes(secret),false);return succeed?json(fixture(request)):new Response(secret,{status:401});}});
  assert.equal(provider.status().configured,true);assert.equal(provider.status().connected,false);assert.equal(calls,0);await provider.decide(request);assert.equal(provider.status().connected,true);assert.equal(provider.status().lastVerifiedAt,new Date(at).toISOString());succeed=false;await assert.rejects(provider.decide(request),code('authentication'));assert.equal(provider.status().connected,false);assert.equal(JSON.stringify(provider.status()).includes(secret),false);
});
await check('Réseau, surcharge et erreurs JSON sans fuite de corps amont',async()=>{
  const request=editorial().request;
  for(const[status,expected]of[[403,'authentication'],[429,'rate_limited'],[529,'rate_limited'],[500,'upstream_error']]){const provider=createJevDecisionProvider({apiKey:secret,fetchImpl:async()=>new Response(secret,{status})});await assert.rejects(provider.decide(request),code(expected));}
  const bad=[new Response('secret',{headers:{'Content-Type':'text/html'}}),json({huge:'x'.repeat(70000)}),new Response(new Uint8Array([0xc3,0x28]),{headers:{'Content-Type':'application/json'}})];
  for(const response of bad){const provider=createJevDecisionProvider({apiKey:secret,fetchImpl:async()=>response});await assert.rejects(provider.decide(request),code('invalid_response'));}
  const provider=createJevDecisionProvider({apiKey:secret,fetchImpl:async()=>{throw new Error(secret);}});await assert.rejects(provider.decide(request),code('unavailable'));
});
await check('Délai et concurrence bornés, sans réémission automatique',async()=>{
  let calls=0,signal;const provider=createJevDecisionProvider({apiKey:secret,timeoutMs:20,fetchImpl:async(url,options)=>{calls++;signal=options.signal;return new Promise(()=>{});}});
  const first=provider.decide(editorial().request),rejected=assert.rejects(first,code('timeout'));await assert.rejects(provider.decide(editorial().request),code('busy'));await rejected;assert.equal(calls,1);assert.equal(signal.aborted,true);
});
await check('Client : contrôle du contexte obligatoire avant tout envoi',async()=>{
  const request=editorial().request;let calls=0;const fetchImpl=async()=>{calls++;throw new Error('unused');};
  await assert.rejects(requestProjectDecision(request,{fetchImpl}),code('invalid_configuration'));
  await assert.rejects(requestProjectDecision(request,{fetchImpl,getCurrentRequest:()=>null}),code('context_changed'));assert.equal(calls,0);
});
await check('Client : le contexte est relu après réponse, même si la révision du projet ne change pas',async()=>{
  const request=preparation().request;let current=clone(request);
  const result=await normalizeTypeSafeDecisionResponse(fixture(request),request,{now});
  await assert.rejects(requestProjectDecision(request,{now,getCurrentRequest:()=>current,fetchImpl:async()=>{current.evidence.machine.revision++;return json(result);}}),code('context_changed'));
  current=clone(request);const accepted=await requestProjectDecision(request,{now,getCurrentRequest:()=>current,fetchImpl:async(url,options)=>{assert.equal(url,'/api/decisions');assert.equal(options.credentials,'same-origin');assert.equal(Object.hasOwn(options.headers,'Authorization'),false);return json(result);}});assert.equal(accepted.decision.reason,'selected');
});
await check('Client : les erreurs HTTP et délais laissent les options locales disponibles',async()=>{
  const request=editorial().request;
  await assert.rejects(requestProjectDecision(request,{getCurrentRequest:()=>request,fetchImpl:async()=>new Response(secret,{status:503})}),code('service_unavailable'));
  await assert.rejects(requestProjectDecision(request,{timeoutMs:20,getCurrentRequest:()=>request,fetchImpl:async()=>new Promise(()=>{})}),code('timeout'));
  assert.equal((await recommendLocalDecision(request)).provider,'local_rules');
});
await check('Statut client : un site sans service ou une politique étrangère ne devient jamais connecté',async()=>{
  const missing=await getDecisionProviderStatus({fetchImpl:async()=>new Response('',{status:404})});assert.equal(missing.connected,false);
  const provider=createJevDecisionProvider();const configured=await getDecisionProviderStatus({fetchImpl:async()=>json(provider.status())});assert.equal(configured.availability,'unconfigured');
  const foreign=await getDecisionProviderStatus({fetchImpl:async()=>json({...provider.status(),configured:true,connected:true,policyVersion:'other'})});assert.equal(foreign.connected,false);
});
await check('Service exportable : résolveur autoritatif vérifié avant et après le conseil',async()=>{
  const request=editorial().request;let calls=0,current=clone(request);
  const provider={status:()=>({configured:true,connected:false}),decide:async input=>{calls++;return recommendLocalDecision(input,{now});}};
  const service=createDecisionService({provider,getCurrentRequest:()=>current});assert.equal(service.status().serverContextRechecked,true);await service.decide(request);assert.equal(calls,1);
  current.context.projectRevision++;await assert.rejects(service.decide(request),code('context_changed'));assert.equal(calls,1);
  current=clone(request);const post=createDecisionService({provider:{...provider,decide:async input=>{const result=await recommendLocalDecision(input,{now});current.context.projectRevision++;return result;}},getCurrentRequest:()=>current});await assert.rejects(post.decide(request),code('context_changed'));
});

const result={ok:true,checks:checks.length,names:checks,scope:'Synthetic measured/declared fixtures and mocked fetch. No browser, server, TypeSafe account, slicer, printer, video render or social action.'};
await writeFile(new URL('./project-decisions-results.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
