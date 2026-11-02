import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {VISUAL_VIEWS,visualContext,contextIsCurrent,chooseLocalVisual,availableVisuals,validateVisualDecision,requestVisualDecision,getVisualProviderStatus} from '../dist/lib/visual-router.js';
import {normalizeTypeSafeResponse} from '../local/jev-provider.mjs';

const checks=[];
const test=(name,fn)=>{fn();checks.push(name);};
const project={id:'project-a',revision:4,pieces:[{id:'piece-b',revision:2,name:'Socle'}]};
const request={requestId:'visual-17',command:'Montre les formes de la pièce',context:visualContext(project,project.pieces[0]),availableViews:availableVisuals(project)};
const copy=v=>JSON.parse(JSON.stringify(v));
const raw={model:'jev-1.13.0',answers:{visual:{type:'choice',choice:'model',confidence:.85,probabilities:{model:.88,art:.04,film:.03,production:.02,none:.03}}},usage:{input_tokens:342,output_tokens:22}};
const valid=()=>normalizeTypeSafeResponse(copy(raw),request);

test('French scene vocabulary handles accents and the œuvres ligature without claiming model inference.',()=>{
  for(const [command,view] of [['Montre les œuvres','art'],['Voir la géométrie','model'],['Regarde le film d’atelier','film'],["Regarde la vidéo de l’atelier",'film'],['Le parc','production']]){const d=chooseLocalVisual(command);assert.equal(d.view,view,command);assert.equal(d.provider,'local');assert.equal(d.confidence,undefined);}
});
test('Negation, conflicting scenes and a mismatched destination preserve the display.',()=>{
  for(const command of ['Ne montre pas les œuvres','Montre le parc et la vidéo','Montre le film d’atelier et le parc','Montre la 3D à gauche','Montre le parc à droite','Publie ce contenu','Inconnu'])assert.equal(chooseLocalVisual(command).view,'none',command);
});
test('An empty project has no model option; invalid explicit revisions are rejected.',()=>{
  assert.deepEqual(availableVisuals({pieces:[]}),['art','film','production']);
  assert.equal(chooseLocalVisual('Montre la 3D',['art','film']).view,'none');
  for(const revision of [0,NaN,'',-1])assert.throws(()=>visualContext({...project,revision}));
  assert.throws(()=>visualContext(project,{...project.pieces[0],revision:0}));
  assert.throws(()=>visualContext(project,{id:'other',revision:2}));
});
test('A decision context requires the exact existing project and piece revisions.',()=>{
  assert(contextIsCurrent(request.context,project));
  assert(!contextIsCurrent(request.context,{...project,revision:5}));
  assert(!contextIsCurrent(request.context,{...project,pieces:[]}));
  assert(!contextIsCurrent(request.context,{...project,pieces:[{...project.pieces[0],revision:3}]}));
  assert(!contextIsCurrent(request.context,{...project,id:'other'}));
});
test('The real gateway adapter and browser validator agree on an accepted official response.',()=>{
  const decision=validateVisualDecision(valid(),request);assert.equal(decision.view,'model');assert.equal(decision.model,'jev-1.13.0');assert.equal(decision.probability,.88);assert.equal(decision.margin,.84);
});
test('Uncertain or no-match Jev decisions abstain even when a selectedView is present for audit.',()=>{
  const uncertain=copy(raw);uncertain.answers.visual={...uncertain.answers.visual,confidence:0,probabilities:{model:.4,art:.2,film:.2,production:.1,none:.1}};
  assert.equal(validateVisualDecision(normalizeTypeSafeResponse(uncertain,request),request).view,'none');
  const none=copy(raw);none.answers.visual.choice='none';none.answers.visual.probabilities={model:.01,art:.01,film:.01,production:.02,none:.95};
  assert.equal(validateVisualDecision(normalizeTypeSafeResponse(none,request),request).view,'none');
});
test('Forged scopes, injected view names and incomplete probability distributions never reach a renderer.',()=>{
  for(const mutate of [x=>x.requestId='another',x=>x.context.projectRevision++,x=>x.context.pieceId='other',x=>x.decision.view='start_print',x=>x.decision.selectedView='film',x=>delete x.decision.probabilities.none,x=>x.decision.probabilities.shell=0,x=>x.decision.probabilities.model=.3,x=>x.model='',x=>x.provider='fake']){const d=valid();mutate(d);assert.throws(()=>validateVisualDecision(d,request));}
});
test('Non-finite fields and invented certainty are rejected by the browser contract.',()=>{
  for(const key of ['probability','margin','confidence'])for(const n of [NaN,Infinity]){const d=valid();d.decision[key]=n;assert.throws(()=>validateVisualDecision(d,request));}
  const weak=valid();weak.decision.probabilities={model:.4,art:.2,film:.2,production:.1,none:.1};weak.decision.probability=.4;weak.decision.margin=.2;weak.decision.confidence=1;assert.throws(()=>validateVisualDecision(weak,request));
});
test('Presentation catalog contains only four renderer IDs and no machine operation.',()=>{
  assert.deepEqual(VISUAL_VIEWS.map(v=>v.id),['model','art','film','production']);
  assert.throws(()=>validateVisualDecision(valid(),{...request,endpoint:'https://untrusted.invalid'}));
});

let calls=0;
const result=await requestVisualDecision(request,{fetchImpl:async(url,options)=>{calls++;assert.equal(url,'/api/visual-decision');assert.equal(options.method,'POST');assert.deepEqual(JSON.parse(options.body),request);assert(!options.headers.Authorization);return new Response(JSON.stringify(valid()),{headers:{'content-type':'application/json'}});}});
assert.equal(result.view,'model');assert.equal(calls,1);checks.push('The client sends one bounded same-origin request with no API credential.');
const noService=await getVisualProviderStatus({fetchImpl:async()=>new Response('',{status:404})});assert.equal(noService.configured,false);assert.equal(noService.connected,false);
const configured=await getVisualProviderStatus({fetchImpl:async()=>new Response(JSON.stringify({configured:true,connected:false,model:'jev-1.13.0'}))});assert.equal(configured.configured,true);assert.equal(configured.connected,false);checks.push('Configured and connected states stay distinct; a static host remains local-only.');
let timedCalls=0;
await assert.rejects(requestVisualDecision(request,{timeoutMs:10,fetchImpl:async(_,options)=>{timedCalls++;return new Promise((_,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError'))));}}),/temps/);
assert.equal(timedCalls,1);checks.push('A provider deadline reports failure without an automatic retry.');

const report={status:'passed',checks,liveProviderVerified:false,browserRenderingVerified:false};
await writeFile(new URL('./visual-router-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
