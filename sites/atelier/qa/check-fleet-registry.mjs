import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import {WorkshopStore} from '../dist/lib/workshop.js';
import {FLEET_FORMAT,createEmptyFleetRecord,normalizeFleetRecord,fleetRecordOf,fleetRecordFromForm,fleetCompleteness,summarizeFleet,exportFleetRegistry} from '../dist/lib/fleet-registry.js';
import {renderFleetRegistry,renderFleetForm} from '../dist/lib/fleet-view.js';

const checks=[];
const test=(name,fn)=>{fn();checks.push(name);};
const copy=value=>JSON.parse(JSON.stringify(value));
const at=Date.parse('2026-10-18T20:30:00Z');
const raw=()=>({origin:'declared',manufacturer:'Fabricant fourni',model:'Modèle fourni',serial:'atelier-01',location:'Poste gauche',firmware:'Version relevée',technology:'fdm',usableVolumeMm:[220,220,250],volumeSource:'Mesures déclarées pour le test',material:'Matière fournie',slicer:{name:'Slicer fourni',version:'Version fournie',machineProfile:'Profil machine fourni',materialProfile:'Profil matière fourni'},fileFormats:['gcode'],connection:{kind:'manual',endpoint:''},qualification:{status:'not_started',testedOn:'',operator:'',report:''},notes:''});
const store=new WorkshopStore();
const machine=store.state.machines[0];

test('Existing eight demo slots remain empty declarations without copied dimensions or fictitious identities.',()=>{
  const before=copy(store.state),summary=summarizeFleet(store.state.machines);
  assert.equal(summary.slots,8);assert.equal(summary.declared,0);assert.equal(summary.complete,0);assert.equal(summary.examples,8);
  const entry=fleetRecordOf(machine);assert.equal(entry.origin,'example');assert.equal(entry.usableVolumeMm,null);assert.equal(entry.technology,'unknown');assert.equal(entry.model,'');assert.equal(entry.revision,0);
  entry.slicer.name='Isolated edit';assert.equal(fleetRecordOf(machine).slicer.name,'');assert.deepEqual(store.state,before);
});

test('Started and complete refer to declared fields, never connected or physically qualified hardware.',()=>{
  const partial=normalizeFleetRecord({origin:'declared',model:'Première information'},null,at),full=normalizeFleetRecord(raw(),null,at);
  const started=fleetCompleteness(partial),complete=fleetCompleteness(full);
  assert.equal(started.status,'started');assert.equal(complete.status,'complete');assert.equal(complete.completed,6);assert.equal(complete.percent,100);
  for(const result of [started,complete]){assert.equal(result.connected,false);assert.equal(result.qualificationVerified,false);assert.equal(result.canStartPhysicalPrint,false);}
  assert.equal(fleetCompleteness(createEmptyFleetRecord()).status,'example');
});

test('Operation time and previous revision produce an immutable deterministic record.',()=>{
  const input=raw(),saved=copy(input),first=normalizeFleetRecord(input,null,at),before=copy(first);
  const second=normalizeFleetRecord({...input,notes:'Note suivante'},first,at+1);
  assert.equal(first.format,FLEET_FORMAT);assert.equal(first.revision,1);assert.equal(second.revision,2);assert.equal(second.updatedAt,at+1);assert.deepEqual(first,before);assert.deepEqual(input,saved);
  assert.deepEqual(normalizeFleetRecord(input,null,at),first);
  assert.throws(()=>normalizeFleetRecord(input,null),/date/);
  assert.throws(()=>normalizeFleetRecord(input,{...first,revision:Number.MAX_SAFE_INTEGER},at+2),/révision/);
});

test('Invented connection, qualification, schema and revision fields are rejected instead of persisted.',()=>{
  for(const patch of [{connected:true},{qualified:true},{revision:999},{updatedAt:0},{format:FLEET_FORMAT},{manufacturer:7},{origin:'detected'}])assert.throws(()=>normalizeFleetRecord({...raw(),...patch},null,at));
  for(const patch of [{connection:{kind:'manual',connected:true}},{qualification:{status:'verified'}},{slicer:{name:'A',command:'shell'}}])assert.throws(()=>normalizeFleetRecord({...raw(),...patch},null,at));
  assert.throws(()=>normalizeFleetRecord({origin:'declared'},null,at),/fabricant/);
});

test('Physical dimensions require three positive finite numbers; strings and incomplete axes cannot imply a build volume.',()=>{
  for(const volume of [[100,100],[100,0,100],[100,-1,100],[Infinity,100,100],[NaN,100,100],['100',100,100],[10001,100,100],[]])assert.throws(()=>normalizeFleetRecord({...raw(),usableVolumeMm:volume},null,at));
  assert.equal(normalizeFleetRecord({...raw(),usableVolumeMm:null},null,at).usableVolumeMm,null);
  assert.throws(()=>fleetRecordFromForm({origin:'declared',model:'M',volumeX:'200',volumeY:'',volumeZ:'300'}),/trois/);
  assert.deepEqual(fleetRecordFromForm({origin:'declared',model:'M',volumeX:'220,5',volumeY:'130',volumeZ:'250'}).usableVolumeMm,[220.5,130,250]);
});

test('Interface addresses carry no credentials or command schemes and make no network request.',()=>{
  for(const address of ['javascript:alert(1)','file:///tmp/config','https://name:pass@printer.invalid','http://printer.invalid?apiKey=x','http://printer.invalid/#secret','printer.invalid'])assert.throws(()=>normalizeFleetRecord({...raw(),connection:{kind:'moonraker',endpoint:address}},null,at));
  const record=normalizeFleetRecord({...raw(),connection:{kind:'moonraker',endpoint:'http://printer.invalid:7125'}},null,at);
  assert.equal(record.connection.endpoint,'http://printer.invalid:7125/');assert.equal(fleetCompleteness(record).connected,false);
  assert.throws(()=>normalizeFleetRecord({...raw(),connection:{kind:'manual',endpoint:'http://printer.invalid'}},null,at));
});

test('Documented tests require a real calendar date, a named operator and a report reference.',()=>{
  for(const q of [{status:'documented'},{status:'documented',testedOn:'2026-02-30',operator:'Atelier',report:'Rapport'},{status:'documented',testedOn:'2026-02-28',operator:'',report:'Rapport'}])assert.throws(()=>normalizeFleetRecord({...raw(),qualification:q},null,at));
  assert.throws(()=>normalizeFleetRecord({...raw(),origin:'example',qualification:{status:'in_progress'}},null,at),/exemple/);
  const record=normalizeFleetRecord({...raw(),qualification:{status:'documented',testedOn:'2026-10-18',operator:'Atelier',report:'Rapport fictif utilisé uniquement dans ce test'}},null,at);
  assert.equal(record.qualification.status,'documented');assert.equal(fleetCompleteness(record).qualificationVerified,false);
});

test('A changed preparation configuration cannot silently reuse a documented test as current evidence.',()=>{
  const input={...raw(),qualification:{status:'documented',testedOn:'2026-10-18',operator:'Atelier',report:'Essai A'}},first=normalizeFleetRecord(input,null,at);
  const changed=normalizeFleetRecord({...input,material:'Autre matière'},first,at+1);
  assert.equal(changed.qualification.status,'needs_review');assert.equal(changed.qualification.report,'Essai A');assert.equal(first.qualification.status,'documented');
  const note=normalizeFleetRecord({...input,notes:'Précision sans changement de configuration'},first,at+1);assert.equal(note.qualification.status,'documented');
  const retested=normalizeFleetRecord({...input,material:'Autre matière',qualification:{...input.qualification,report:'Essai B'}},first,at+2);assert.equal(retested.qualification.status,'documented');assert.equal(fleetCompleteness(retested).qualificationVerified,false);
});

test('File formats are deduplicated extensions and cannot carry a path or executable command.',()=>{
  const record=normalizeFleetRecord({...raw(),fileFormats:['.GCODE','gcode','3mf']},null,at);assert.deepEqual(record.fileFormats,['gcode','3mf']);
  for(const format of ['https://host/file','../../secret','stl;rm','', 'x'.repeat(25)])assert.throws(()=>normalizeFleetRecord({...raw(),fileFormats:[format]},null,at));
});

test('The rendered form starts blank, keeps a captured revision and round-trips through native FormData.',()=>{
  const emptyDOM=new JSDOM(renderFleetForm({machine}));
  assert.equal(emptyDOM.window.document.querySelector('input[name="model"]').value,'');assert.equal(emptyDOM.window.document.querySelector('input[name="volumeX"]').value,'');assert.equal(emptyDOM.window.document.querySelector('#fleet-form').dataset.revision,'0');
  const record=normalizeFleetRecord(raw(),null,at),dom=new JSDOM(renderFleetForm({machine:{...machine,registry:record}}));
  const form=dom.window.document.querySelector('#fleet-form'),values=Object.fromEntries(new dom.window.FormData(form));
  assert.equal(form.dataset.id,machine.id);assert.equal(form.dataset.revision,'1');assert.deepEqual(fleetRecordFromForm(values),raw());
  assert.equal(dom.window.document.querySelectorAll('details.fleet-form-section').length,5);
  assert.equal(dom.window.document.querySelectorAll('#form-error[role="alert"]').length,1);
});

test('User-supplied names and notes cannot insert executable markup in cards or form values.',()=>{
  const record=normalizeFleetRecord({...raw(),model:'</h3><script>bad()</script>',manufacturer:'"><img src=x onerror=bad()>',notes:'</textarea><script>bad()</script>'},null,at);
  for(const html of [renderFleetRegistry({machines:[{...machine,registry:record}]}),renderFleetForm({machine:{...machine,registry:record}})]){
    const dom=new JSDOM(html);assert.equal(dom.window.document.querySelectorAll('script,[onerror]').length,0);
  }
});

test('The inventory grid and export retain slots without relabeling a demo profile as detected hardware.',()=>{
  const dom=new JSDOM(renderFleetRegistry({machines:store.state.machines}));assert.equal(dom.window.document.querySelectorAll('[data-fleet-machine]').length,8);assert.equal(dom.window.document.querySelectorAll('.fleet-slot.example').length,8);
  const full=normalizeFleetRecord(raw(),null,at),machines=store.state.machines.map((m,i)=>i?m:{...m,registry:full}),exported=exportFleetRegistry(machines,at+1);
  assert.equal(exported.brand,'BOJ.ART');assert.equal(exported.machines.length,8);assert.equal(exported.summary.declared,1);assert.equal(exported.summary.complete,1);assert.equal(exported.summary.connected,0);
  assert.equal(exported.machines[1].record.usableVolumeMm,null);assert.equal(exported.machines[0].record.usableVolumeMm[0],220);
  exported.machines[0].record.slicer.name='Mutation';assert.equal(full.slicer.name,'Slicer fourni');
});

const report={status:'passed',checks,browserRenderingVerified:false,hardwareVerified:false,livePrinterConnections:0};
await writeFile(new URL('./fleet-registry-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
