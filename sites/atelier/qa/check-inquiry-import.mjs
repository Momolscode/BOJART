import assert from 'node:assert/strict';
import {mkdtemp,rm,writeFile,readFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createInquiryExport,canonicalJSON} from '../dist/lib/inquiry-contract.js';
import {inspectInquiryExport,importInquiryProject,inquiryProjectId,inquiryProjectPayload,normalizeInquiryLink,locateInquiry,exportInquiryTechnical} from '../dist/lib/inquiry-import.js';
import {WorkshopStore,replayWorkshopAuthority,validateWorkshopOperation} from '../dist/lib/workshop.js';
import {createWorkshopBackup,inspectWorkshopBackup} from '../dist/lib/workshop-backup.js';
import {createWorkshopRepository} from '../local/workshop-repository.mjs';
import {buildMasterMission,buildControlDecision} from '../dist/lib/control-plane.js';
import {inspectMission} from '../dist/lib/mission.js';

const seed={version:1,at:1792324800000},checks=[],opened=[];
class Storage{data=new Map();get length(){return this.data.size;}key(i){return [...this.data.keys()][i]??null;}getItem(k){return this.data.get(k)??null;}setItem(k,v){this.data.set(k,String(v));}}
function createStore(){globalThis.localStorage=new Storage();const store=new WorkshopStore();store.mergeJournal({version:1,seed,operations:[]},{allowEmptyAdoption:true});opened.push(store);return store;}
const raw={format:'bojart.inquiry.v1',requestId:'c4bf323a-5620-43d8-8240-3b9e9e2f67c2',reference:'BOJ-20261019-C4BF323A5620',createdAt:'2026-10-19T12:10:00.000Z',updatedAt:'2026-10-19T12:10:00.000Z',status:'new',revision:1,offer:'custom',name:'Camille Exemple',email:'camille-private@example.com',phone:'+33 6 00 00 00 00',description:'DESCRIPTION PRIVEE A NE PAS COPIER : une création peinte pour un événement.',intendedUse:'Usage privé du demandeur',quantity:2,budgetRange:'750_1500',modelStatus:'idea',referenceURLs:[],source:{entryPath:'/sur-mesure',utmSource:'campagne-exemple'},privacyAcknowledged:true,privacyVersion:'2026-10-19'};
const check=async(name,fn)=>{await fn();checks.push(name);};
const exportOf=(record=raw,exportedAt='2026-10-19T12:15:00.000Z')=>createInquiryExport(record,{exportedAt});
const directory=await mkdtemp(join(tmpdir(),'boj-inquiry-qa-'));
try{
  const store=createStore(),envelope=await exportOf();let prepared,project;
  await check('Portable export is verified before any state mutation; original contacts are available only in the preview',async()=>{
    const before=canonicalJSON(store.state);prepared=await inspectInquiryExport(JSON.stringify(envelope),store.state);
    assert.equal(prepared.envelope.inquiry.email,raw.email);assert.equal(canonicalJSON(store.state),before);assert.equal(prepared.existing,null);assert.equal(prepared.conflict,false);
  });
  await check('Technical project is created atomically with stable reference and no invented height, geometry, price or accepted status',()=>{
    const before=store.state.projects.map(item=>canonicalJSON(item)),result=importInquiryProject(store,prepared,'Finition mate à étudier.');assert.equal(result.ok,true,result.message);
    project=store.getProject();assert.equal(project.id,inquiryProjectId(prepared.link));assert.equal(project.name,'DEMANDE '+raw.reference);assert.equal(project.height,null);assert.equal(project.quantity,2);assert.equal(project.status,'Étude');assert.equal(project.quote,null);assert.equal(project.pieces.length,0);assert.equal(project.notes,'Finition mate à étudier.');
    assert.deepEqual(store.state.projects.slice(0,-1).map(item=>canonicalJSON(item)),before);assert.equal(store.exportJournal().operations.length,1);assert.equal(store.exportJournal().operations[0].type,'ADD_PROJECT');
  });
  await check('Contacts, source prose, free campaign values and reference URLs are absent from project, journal and technical export',async()=>{
    const backup=await createWorkshopBackup(store.exportJournal());
    for(const value of [store.state,store.exportJournal(),backup,exportInquiryTechnical(project)]){
      const serialized=JSON.stringify(value);for(const privateText of [raw.name,raw.email,raw.phone,raw.description,raw.intendedUse,raw.source.utmSource])assert.equal(serialized.includes(privateText),false,privateText);
    }
    assert.equal('description' in project.inquiry,false);assert.equal('name' in project.inquiry,false);assert.equal('email' in project.inquiry,false);
  });
  await check('Reimport opens the existing project without erasing its changed notes, revisions or saved quotation',()=>{
    store.dispatch('UPDATE_PROJECT',{id:project.id,patch:{notes:'Travail conservé',height:420}});
    store.dispatch('SAVE_QUOTE',{projectId:project.id,inputs:{material:40,hours:5,rate:30,other:20,margin:30,fee:0,quantity:2}});
    const before=canonicalJSON(store.getProject()),count=store.state.projects.length,result=importInquiryProject(store,prepared,'Texte qui ne doit pas écraser');
    assert.equal(result.ok,true);assert.equal(result.duplicate,true);assert.equal(store.state.projects.length,count);assert.equal(canonicalJSON(store.getProject()),before);
  });
  await check('Changing only the export date preserves request identity and remains a duplicate',async()=>{
    const newer=await inspectInquiryExport(await exportOf(raw,'2026-10-19T14:00:00.000Z'),store.state);
    assert.notEqual(newer.envelope.sha256,envelope.sha256);assert.equal(newer.link.contentSha256,prepared.link.contentSha256);assert.equal(newer.conflict,false);assert.equal(importInquiryProject(store,newer).duplicate,true);
  });
  await check('A changed request or a reused reference is refused without overwriting the workshop project',async()=>{
    const before=canonicalJSON(store.getProject()),changed=await inspectInquiryExport(await exportOf({...raw,quantity:3,revision:2,updatedAt:'2026-10-19T13:00:00.000Z'}),store.state);
    assert.equal(changed.conflict,true);assert.equal(importInquiryProject(store,changed).ok,false);assert.equal(canonicalJSON(store.getProject()),before);
    const changedId=await inspectInquiryExport(await exportOf({...raw,requestId:'b4bf323a-5620-43d8-8240-3b9e9e2f67c2'}),store.state);assert.equal(changedId.conflict,true);assert.equal(importInquiryProject(store,changedId).ok,false);
    assert.equal(locateInquiry({projects:[{id:inquiryProjectId(prepared.link),name:'Un dossier préexistant'}]},prepared.link).conflict,true);
  });
  await check('Corruption, oversized JSON and non-normalized or unknown fields fail before project creation',async()=>{
    const bad=structuredClone(envelope);bad.inquiry.quantity=5;await assert.rejects(inspectInquiryExport(bad,store.state),/empreinte/);
    await assert.rejects(inspectInquiryExport(' '.repeat(65537),store.state),/64 Kio/);await assert.rejects(inspectInquiryExport('{invalid',store.state),/JSON/);
    assert.throws(()=>normalizeInquiryLink({...prepared.link,email:raw.email}),/technique invalide/);
    const op=store.exportJournal().operations.find(item=>item.type==='ADD_PROJECT');assert.throws(()=>validateWorkshopOperation({...op,payload:{...op.payload,inquiry:{...op.payload.inquiry,description:raw.description}}}),/technique invalide/);
  });
  await check('Mandatory project projection cannot turn an imported accepted status into production or substitute a geometry height',async()=>{
    const isolated=createStore(),accepted=await inspectInquiryExport(await exportOf({...raw,status:'accepted',dimensions:{heightMm:610,widthMm:200}}),isolated.state);
    const result=importInquiryProject(isolated,accepted);assert.equal(result.ok,true);assert.equal(isolated.getProject().status,'Étude');assert.equal(isolated.getProject().height,610);assert.equal(isolated.getProject().pieces.length,0);
    const payload=inquiryProjectPayload(accepted.link);payload.status='Production';const rejected=createStore().dispatch('ADD_PROJECT',payload);assert.equal(rejected.ok,false);assert.match(rejected.message,/paramètres de la demande/);
  });
  await check('Unknown height remains null in legacy and current preparation and drives a qualification decision',()=>{
    const isolated=createStore();importInquiryProject(isolated,prepared);const id=isolated.getProject().id;
    assert.equal(buildMasterMission(isolated.state,id).targetHeightMm,null);assert.equal(buildMasterMission(isolated.state,id).steps.find(item=>item.id==='brief').status,'needs_input');
    assert.equal(inspectMission(isolated.state,id).targetHeightMm,null);assert.equal(buildControlDecision(isolated.state,id).primary.action,'inquiry-current');
  });
  await check('Portable workshop backup retains only the technical projection and restores into a fresh browser store',async()=>{
    const backup=await createWorkshopBackup(store.exportJournal()),parsed=await inspectWorkshopBackup(backup),restored=createStore();
    restored.mergeJournal(parsed.journal,{allowEmptyAdoption:true});assert.deepEqual(restored.state.projects.find(item=>item.id===project.id),store.getProject());
  });
  await check('Two independent screens create one authoritative project, keep a stable collision receipt and restore through SQLite v2',async()=>{
    const a=createStore(),b=createStore();importInquiryProject(a,prepared);importInquiryProject(b,prepared);
    const repository=createWorkshopRepository({directory:join(directory,'source')}),recovered=createWorkshopRepository({directory:join(directory,'restored')});
    try{
      const batch=operations=>({version:2,workspaceId:repository.status().workspaceId,seed,operations});
      repository.append(batch(a.exportJournal().operations));repository.append(batch(b.exportJournal().operations));
      const backup=repository.backup(),state=replayWorkshopAuthority(backup.seed,backup.operations,backup.authority);
      assert.equal(state.state.projects.filter(item=>item.inquiry).length,1);assert.equal(backup.authority.receipts.filter(receipt=>receipt.outcome.ok).length,1);assert.equal(backup.authority.receipts.filter(receipt=>!receipt.outcome.ok).length,1);
      const before=canonicalJSON(backup.authority.receipts);repository.append(batch(b.exportJournal().operations));assert.equal(canonicalJSON(repository.backup().authority.receipts),before);
      recovered.restore(backup);const rebuilt=recovered.backup();assert.equal(canonicalJSON(rebuilt.authority.receipts),before);assert.deepEqual(replayWorkshopAuthority(rebuilt.seed,rebuilt.operations,rebuilt.authority).state.projects,state.state.projects);
      assert.equal(JSON.stringify(backup).includes(raw.email),false);
    }finally{repository.close();recovered.close();}
  });
  await check('Actual acquisition POST, SQLite persistence and admin-export fixture imports through the production workshop contract',async()=>{
    const fixture=await readFile(new URL('./inquiry-export-fixture.json',import.meta.url),'utf8'),isolated=createStore();
    const received=await inspectInquiryExport(fixture,isolated.state),result=importInquiryProject(isolated,received,'Interopérabilité vérifiée sur une demande de test.');
    assert.equal(result.ok,true,result.message);assert.equal(isolated.getProject().inquiry.requestId,received.envelope.inquiry.requestId);assert.equal(isolated.getProject().quantity,received.envelope.inquiry.quantity);
    const journal=JSON.stringify(isolated.exportJournal());assert(!journal.includes(received.envelope.inquiry.email));assert(!journal.includes(received.envelope.inquiry.name));assert(!journal.includes(received.envelope.inquiry.description));
    assert.equal(importInquiryProject(isolated,received).duplicate,true);
  });
  const result={status:'passed',checks,scope:'Actual workshop reducer, export hash, local journal, SQLite authority and restore. No network, messages, printer, quote acceptance or payment.'};
  await writeFile(new URL('./inquiry-import-results.json',import.meta.url),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{for(const store of opened)store.dispose();await rm(directory,{recursive:true,force:true});}
