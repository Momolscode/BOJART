// Targeted preparation QA: real STL parsing and Three mathematics, isolated DOMs,
// declared fleet records and controlled asynchronous asset reads. No WebGL run.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {createHash, webcrypto} = require('node:crypto');
const {JSDOM} = require('jsdom');
const csstree = require('css-tree');

const root = path.resolve(__dirname, '..');
const dist = path.join(root, 'dist');
const reportPath = path.join(__dirname, 'preparation-integration-results.json');
const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
const archive = JSON.parse(fs.readFileSync(path.join(dist, 'assets/archive-index.json'), 'utf8'));
const at = Date.parse('2026-10-18T23:50:00Z');
const seedKey = 'bojart.workshop.v1.seed';
const checks = [], fixtures = [], channels = new Map();
const clone = value => JSON.parse(JSON.stringify(value));
const tick = () => new Promise(resolve => setImmediate(resolve));
const settle = async () => { for (let i = 0; i < 5; i++) await tick(); };
const closeTo = (actual, expected, epsilon = 1e-8) => assert(Math.abs(actual - expected) <= epsilon, `${actual} != ${expected}`);
function gate() { let resolve; const promise = new Promise(done => { resolve = done; }); return {promise, resolve}; }

class Storage {
  constructor(initial = [[seedKey, JSON.stringify({version: 1, at})]]) { this.entries = new Map(initial); }
  get length() { return this.entries.size; }
  key(index) { return [...this.entries.keys()][index] ?? null; }
  getItem(key) { return this.entries.get(key) ?? null; }
  setItem(key, value) { this.entries.set(key, String(value)); }
  removeItem(key) { this.entries.delete(key); }
}

function boxSTL(dims = [10,20,30], offset = [0,0,0], {open = false} = {}) {
  const vertices = [[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]].map(point => point.map((v, i) => offset[i] + v * dims[i]));
  const faces = [[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]];
  const text = ['solid asymmetric', ...(open ? faces.slice(0,-2) : faces).map(face => 'facet normal 0 0 0\nouter loop\n' + face.map(index => 'vertex ' + vertices[index].join(' ')).join('\n') + '\nendloop\nendfacet'), 'endsolid asymmetric'].join('\n');
  return Buffer.from(text);
}
function binaryBoxSTL(dims = [10,20,30]) {
  const ascii = boxSTL(dims).toString();
  const vertices = [...ascii.matchAll(/vertex (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)/g)].map(match => match.slice(1).map(Number));
  const output = Buffer.alloc(84 + vertices.length / 3 * 50);
  output.write('BOJ.ART isolated QA fixture', 0, 'ascii');
  output.writeUInt32LE(vertices.length / 3, 80);
  for (let facet = 0; facet < vertices.length / 3; facet++) {
    for (let vertex = 0; vertex < 3; vertex++) for (let axis = 0; axis < 3; axis++) output.writeFloatLE(vertices[facet * 3 + vertex][axis], 84 + facet * 50 + 12 + vertex * 12 + axis * 4);
  }
  return output;
}

async function surface(name, {app = false, panel = '', storage = new Storage(), group = name} = {}) {
  const dom = new JSDOM(html, {url: `https://bojart.test/?screen=pilotage&station=pilotage${panel ? '&panel=' + panel : ''}`, runScripts: 'outside-only', pretendToBeVisual: true});
  const w = dom.window, context = dom.getInternalVMContext();
  const f = {name, dom, w, storage, assets: new Map(), assetGates: new Map(), assetReads: [], assetWrites: [], assetWriteAttempts: [], fetchCalls: [], errors: [], downloads: [], objectURLs: new Map(), viewports: [], viewers: [], stores: [], closed: false, failViewport: false};
  fixtures.push(f);
  Object.defineProperty(w, 'localStorage', {value: storage});
  Object.defineProperty(w.crypto, 'subtle', {value: webcrypto.subtle});
  w.TextEncoder = TextEncoder; w.TextDecoder = TextDecoder;
  w.matchMedia = () => ({matches: false, addEventListener() {}, removeEventListener() {}});
  w.scrollTo = () => {}; w.setInterval = () => 0;
  w.HTMLCanvasElement.prototype.getContext = () => null;
  w.HTMLMediaElement.prototype.play = async function() {};
  w.HTMLMediaElement.prototype.pause = function() {};
  w.HTMLDialogElement.prototype.showModal = function() { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function() { if (!this.open) return; this.removeAttribute('open'); setImmediate(() => { if (!f.closed) this.dispatchEvent(new w.Event('close')); }); };
  w.ResizeObserver = class {observe() {} unobserve() {} disconnect() {}};
  w.IntersectionObserver = class {observe() {} unobserve() {} disconnect() {}};
  w.addEventListener('error', event => f.errors.push(event.error?.stack || event.message));
  f.realm = value => w.JSON.parse(JSON.stringify(value));
  f.buffer = bytes => new w.Uint8Array(Buffer.from(bytes)).buffer;
  f.addAsset = (id, bytes, filename = id + '.stl') => { const buffer = f.buffer(bytes); const record = {id, name: filename, buffer, createdAt: at}; f.assets.set(id, record); return record; };
  f.readAsset = async id => { f.assetReads.push(id); const pending = f.assetGates.get(id); if (pending) await pending.promise; return f.assets.get(id) || null; };
  const database = {
    createObjectStore() {},
    transaction(_storeName, mode = 'readonly') {
      const transaction = {error: null, objectStore() { return {
        get(id) {
          const request = {};
          f.readAsset(id).then(result => { request.result = result || undefined; request.onsuccess?.({target: request}); }, error => { request.error = error; request.onerror?.({target: request}); });
          return request;
        },
        put(record) {
          const request = {};
          f.assetWriteAttempts.push(record.id);
          setImmediate(async () => {
            if(f.assetWriteGate)await f.assetWriteGate.promise;
            if (f.failAssetWrite) { transaction.error = new Error('Quota de test'); transaction.onerror?.(); return; }
            f.assets.set(record.id, record); f.assetWrites.push(record.id);
            request.result = record.id; request.onsuccess?.(); transaction.oncomplete?.();
          });
          return request;
        }
      }; }};
      return transaction;
    }
  };
  w.indexedDB = {open() { const request = {}; setImmediate(() => { request.result = database; request.onupgradeneeded?.(); request.onsuccess?.(); }); return request; }};
  let objectId = 0;
  w.URL.createObjectURL = blob => { const url = `blob:https://bojart.test/${name}-${++objectId}`; f.objectURLs.set(url, blob); return url; };
  w.URL.revokeObjectURL = url => f.objectURLs.delete(url);
  w.HTMLAnchorElement.prototype.click = function() { if (this.download) f.downloads.push({filename: this.download, blob: f.objectURLs.get(this.href)}); };
  w.fetch = async (input, options = {}) => {
    const url = new w.URL(String(input), w.location.href);
    f.fetchCalls.push({pathname: url.pathname, method: options.method || 'GET', body: options.body || null});
    return {ok: url.pathname === '/assets/archive-index.json', status: url.pathname === '/assets/archive-index.json' ? 200 : 404, json: async () => f.realm(url.pathname === '/assets/archive-index.json' ? archive : {ok: false})};
  };
  w.BroadcastChannel = class {
    constructor(channel) { this.key = group + ':' + channel; this.listeners = new Set(); if (!channels.has(this.key)) channels.set(this.key, new Set()); channels.get(this.key).add(this); }
    addEventListener(type, listener) { if (type === 'message') this.listeners.add(listener); }
    removeEventListener(type, listener) { if (type === 'message') this.listeners.delete(listener); }
    postMessage(frame) { const serialized = JSON.stringify(frame); for (const peer of channels.get(this.key) || []) if (peer !== this) queueMicrotask(() => { const event = {data: f.realm(JSON.parse(serialized))}; peer.onmessage?.(event); for (const listener of peer.listeners) listener(event); }); }
    close() { channels.get(this.key)?.delete(this); }
  };
  function loader(overrides = new Map()) {
    const modules = new Map();
    const resolve = (specifier, parent) => specifier === 'three' ? path.join(dist, 'vendor/three.module.js') : path.resolve(path.dirname(parent.identifier), specifier);
    function moduleFor(filename) {
      filename = path.resolve(filename);
      if (overrides.has(filename)) return overrides.get(filename);
      if (modules.has(filename)) return modules.get(filename);
      const mod = new vm.SourceTextModule(fs.readFileSync(filename, 'utf8'), {context, identifier: filename, importModuleDynamically: async (specifier, parent) => load(resolve(specifier, parent))});
      modules.set(filename, mod); return mod;
    }
    async function load(filename) {
      const mod = moduleFor(filename);
      if (mod.status === 'unlinked') await mod.link((specifier, parent) => moduleFor(resolve(specifier, parent)));
      if (mod.status !== 'evaluated') await mod.evaluate();
      return mod;
    }
    return load;
  }
  f.loadReal = loader();
  const actualViewer = await f.loadReal(path.join(dist, 'lib/viewer.js'));
  f.inspectSTL = actualViewer.namespace.inspectSTL;
  const makeViewport = async () => {
    if (f.viewportGate) await f.viewportGate.promise;
    if (f.failViewport) throw new Error('WebGL indisponible pour cette vérification DOM.');
    const viewport = {disposed: false, loads: [], volumes: [], orientations: [], clearCalls: 0, motion: [], setBuildVolume(value) { this.volumes.push(clone(value)); }, setOrientation(value) { this.orientations.push(value); }, loadSTL(buffer, unit) { const result = f.inspectSTL(buffer, unit); this.loads.push({buffer, unit, result: clone(result)}); return result; }, clearModel() { this.clearCalls++; }, reset() {}, setWireframe() {}, setAutoRotate() {}, setSection() {}, setMotion(value) { this.motion.push(value); }, dispose() { this.disposed = true; }};
    f.viewports.push(viewport); return viewport;
  };
  f.createViewport = makeViewport;
  const viewerStub = new vm.SyntheticModule(['createViewer','inspectSTL'], function() {
    this.setExport('inspectSTL', f.inspectSTL);
    this.setExport('createViewer', async () => { const viewer = {loads: [], demoCalls: 0, disposed: false, loadSTL(buffer, unit) { const result = f.inspectSTL(buffer, unit); this.loads.push({buffer,unit,result:clone(result)}); return result; }, showDemo() { this.demoCalls++; }, reset() {}, explode: () => true, setWireframe() {}, setAutoRotate() {}, setMotion() {}, setSection() {}, dispose() { this.disposed = true; }}; f.viewers.push(viewer); return viewer; });
  }, {context});
  await viewerStub.link(() => {}); await viewerStub.evaluate();
  const viewportStub = new vm.SyntheticModule(['createPreparationViewport','createViewport'], function() { this.setExport('createPreparationViewport', makeViewport); this.setExport('createViewport', makeViewport); }, {context});
  await viewportStub.link(() => {}); await viewportStub.evaluate();
  f.load = loader(new Map([[path.join(dist,'lib/viewer.js'),viewerStub],[path.join(dist,'lib/preparation-viewport.js'),viewportStub]]));
  f.$ = selector => w.document.querySelector(selector);
  f.$$ = selector => [...w.document.querySelectorAll(selector)];
  f.click = async selector => { const element = f.$(selector); assert(element, name + ': missing ' + selector); element.click(); await settle(); };
  f.change = async (selector, value) => { const element = f.$(selector); assert(element, name + ': missing ' + selector); element.value = String(value); element.dispatchEvent(new w.Event('change', {bubbles: true})); await settle(); };
  f.input = async (selector, value) => { const element = f.$(selector); assert(element, name + ': missing ' + selector); element.value = String(value); element.dispatchEvent(new w.Event('input', {bubbles: true})); await settle(); };
  f.selectProject = async id => f.change('#project-picker', id);
  const storeModule = await f.load(path.join(dist, 'lib/workshop.js'));
  f.store = new storeModule.namespace.WorkshopStore(); f.stores.push(f.store);
  f.act = (type, payload) => { const result = f.store.dispatch(type, f.realm(payload)); assert.equal(result.ok, true, result.message); return clone(result); };
  f.project = id => { f.store.refresh(); return f.store.state.projects.find(project => project.id === id); };
  f.math = (await f.load(path.join(dist,'lib/preparation.js'))).namespace;
  f.fleet = (await f.load(path.join(dist,'lib/fleet-registry.js'))).namespace;
  if (app) { f.app = await f.load(path.join(dist,'app.js')); await settle(); }
  return f;
}

function declaredRecord(f, overrides = {}) {
  return f.fleet.normalizeFleetRecord(f.realm({origin:'declared',model:'Machine déclarée pour QA',technology:'fdm',usableVolumeMm:[100,100,100],volumeSource:'Dimensions de test',...overrides}), null, at);
}
function sampleState(f, {dims=[10,20,30], unit='mm', tech='fdm'} = {}) {
  const piece = {id:'qa-piece',name:'Pièce asymétrique',assetId:'qa-asset',revision:3,dims,unit,tech,machine:null};
  return f.realm({projectId:'qa-project',selectedPieceId:piece.id,projects:[{id:'qa-project',name:'Dossier QA',revision:4,quantity:2,height:1000,pieces:[piece]}],machines:[{id:'P01',name:'Résine de démonstration',tech:'resin',volume:[10000,10000,10000],registry:declaredRecord(f)}],jobs:[]});
}
function proof(f, state, changes = {}) {
  const project = state.projects[0], piece = project.pieces[0];
  return f.realm({projectId:project.id,pieceId:piece.id,pieceRevision:piece.revision,assetId:piece.assetId,unit:piece.unit,status:'measured',dimsMm:[...piece.dims],triangles:12,byteLength:684,checkedAt:at,message:'STL mesuré pour le test',sha256:'a'.repeat(64),...changes});
}
const inspect = (f, state, evidence=[]) => f.math.inspectDeclaredPreparation(state,'qa-project',f.realm({assetEvidence:evidence}));
async function readDownload(f, download=f.downloads.at(-1)) {
  assert(download?.blob, 'The UI produces a downloadable Blob');
  const text = await new Promise((resolve,reject) => { const reader = new f.w.FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(reader.error); reader.readAsText(download.blob); });
  return JSON.parse(text);
}
async function check(id, description, task) {
  try { await task(); checks.push({id,status:'passed',description}); }
  catch (error) { checks.push({id,status:'failed',description,error:error.stack}); }
}
async function eventually(predicate,message='Asynchronous work did not settle') {
  const deadline=Date.now()+2500;
  while(Date.now()<deadline){if(predicate())return;await new Promise(resolve=>setTimeout(resolve,5));}
  assert(predicate(),message);
}
async function mountWorkbench(f,state,{inspectSTL=f.inspectSTL,onExport=null}={}){
  const module=(await f.load(path.join(dist,'lib/preparation-view.js'))).namespace;
  const project=state.projects[0],report=inspect(f,state),container=f.$('#drawer-content');
  f.targetProjectId=project.id;f.workshopState=state;f.exports=[];f.imports=[];f.fleetRequests=[];f.report=report;
  container.innerHTML=module.renderPreparationView({project,machines:state.machines,report});f.$('#drawer').showModal();
  f.controller=module.mountPreparationView(container,{project,machines:state.machines,report,motion:true,createViewport:f.createViewport,readAsset:f.readAsset,inspectSTL,
    analyze:(current,machines,assetEvidence)=>{f.report=f.math.inspectDeclaredPreparation(f.realm({projects:[current],machines}),current.id,{assetEvidence});return f.report;},
    onExport:async request=>{f.exports.push(clone(request));return onExport?onExport(request):{ok:true,message:'Rapport de test exporté.'};},
    onImport:request=>{f.imports.push(clone(request));return{ok:true};},onOpenFleet:request=>f.fleetRequests.push(clone(request))});
  f.refresh=(nextState=f.workshopState,activeProjectId=project.id)=>{f.workshopState=nextState;f.controller.refreshContext({project:nextState.projects.find(item=>item.id===project.id)||null,machines:nextState.machines,activeProjectId});};
  f.ready=()=>eventually(()=>f.$('[data-preparation-workbench]')?.dataset.prepState==='ready','The preparation file audit must finish.');
  await settle();return f.controller;
}
function twoPieceState(f){
  const state=sampleState(f);
  state.projects[0].pieces.push(f.realm({id:'second-piece',name:'Deuxième pièce',assetId:'second-asset',revision:1,dims:[40,15,25],unit:'mm',tech:'fdm',machine:null}));
  state.machines.push(f.realm({id:'P02',name:'Deuxième slot',tech:'resin',volume:[999,999,999],registry:declaredRecord(f,{model:'Machine B déclarée',usableVolumeMm:[80,85,90]})}));
  f.addAsset('qa-asset',boxSTL());f.addAsset('second-asset',boxSTL([40,15,25]));
  return state;
}
async function appPreparation(name){
  const f=await surface(name,{panel:'preparation'});
  const record={origin:'declared',model:'Machine résine pour QA',technology:'resin',usableVolumeMm:[900,900,900],volumeSource:'Volume de vérification'};
  f.act('UPDATE_MACHINE',{id:'P01',expectedRegistryRevision:0,patch:{registry:record}});
  f.act('UPDATE_PIECE',{projectId:'sculpture-xl',id:'buste',patch:{assetId:'qa-asset',dims:[10,20,30],unit:'mm',triangles:12}});
  f.addAsset('qa-asset',boxSTL());f.app=await f.load(path.join(dist,'app.js'));await settle();
  await eventually(()=>f.$('[data-preparation-workbench]')?.dataset.prepState==='ready');
  return f;
}
async function chooseFile(f,selector,{name='QA_import.stl',bytes=boxSTL(),pending=null}={}){
  const input=f.$(selector);assert(input,'The import file input must exist.');
  let started=false;
  const file={name,size:bytes.length,arrayBuffer:async()=>{started=true;if(pending)await pending.promise;return f.buffer(bytes);}};
  Object.defineProperty(input,'files',{configurable:true,value:[file]});input.dispatchEvent(new f.w.Event('change',{bubbles:true}));
  await eventually(()=>started,'The selected file must be read.');return file;
}

async function run() {
  await check('real-stl-units-and-original-bytes','Actual ASCII and binary STL parsing measures an asymmetric box; inches are converted exactly once and original bytes stay unchanged.',async()=>{
    const f=await surface('geometry');
    for(const bytes of [boxSTL([10,20,30],[-31,7,-42]),binaryBoxSTL()]){
      const buffer=f.buffer(bytes),before=Buffer.from(buffer).toString('hex');
      const mm=f.inspectSTL(buffer,'mm'),inch=f.inspectSTL(buffer,'inch');
      assert.deepEqual(clone(mm.dims),[10,20,30]);assert.equal(mm.triangles,12);
      inch.dims.forEach((value,index)=>closeTo(value,[254,508,762][index]));
      assert.equal(Buffer.from(buffer).toString('hex'),before);
      assert.deepEqual(clone(f.inspectSTL(buffer,'mm').dims),[10,20,30]);
    }
    for(const unit of ['cm','m','in','inches','unknown'])assert.throws(()=>f.inspectSTL(f.buffer(boxSTL()),unit),/Unité/);
    assert.throws(()=>f.inspectSTL(f.buffer('This is not an STL file.'),'mm'));
    const invalid=binaryBoxSTL();invalid.writeFloatLE(NaN,96);assert.throws(()=>f.inspectSTL(f.buffer(invalid),'mm'),/coordonnées/);
  });

  await check('declared-registry-only','The real preparation reads declared technology and useful dimensions; demo slot values cannot establish compatibility.',async()=>{
    const f=await surface('registry'),state=sampleState(f),before=clone(state);
    let report=inspect(f,state,[proof(f,state)]),assessment=report.pieces[0].assessments[0];
    assert.equal(assessment.technologyStatus,'match');assert.equal(assessment.status,'fits');assert.equal(report.summary.piecesWithEnvelopeFit,1);
    assert.equal(state.machines[0].tech,'resin');assert.equal(report.machines[0].record.technology,'fdm');
    assert.deepEqual(clone(state),before);
    delete state.machines[0].registry;report=inspect(f,state,[proof(f,state)]);
    assert.equal(report.summary.declaredMachines,0);assert.equal(report.pieces[0].assessments[0].status,'not_declared');assert.equal(report.summary.piecesWithEnvelopeFit,0);
    assert.equal(report.machines[0].record.usableVolumeMm,null);
    state.machines[0].registry=declaredRecord(f,{usableVolumeMm:null});report=inspect(f,state,[proof(f,state)]);
    assert.equal(report.pieces[0].assessments[0].status,'volume_missing');assert.equal(report.summary.piecesWithEnvelopeFit,0);
    state.machines[0].registry=declaredRecord(f,{technology:'unknown'});report=inspect(f,state,[proof(f,state)]);
    assert.equal(report.pieces[0].assessments[0].technologyStatus,'unknown');assert.equal(report.summary.piecesWithEnvelopeFit,0);
    state.machines[0].registry=declaredRecord(f,{technology:'resin'});report=inspect(f,state,[proof(f,state)]);
    assert.equal(report.pieces[0].assessments[0].status,'technology_mismatch');assert.equal(report.pieces[0].assessments[0].fitOrientationIds.length,0);assert.equal(report.summary.piecesWithEnvelopeFit,0);
  });

  await check('file-proof-identity-and-absence','A stored asset ID alone is not a measured file; source evidence must match project, piece, revision, asset and unit exactly.',async()=>{
    const f=await surface('evidence'),state=sampleState(f);
    let report=inspect(f,state);assert.equal(report.pieces[0].file.status,'unchecked');assert.equal(report.summary.measuredFiles,0);assert.equal(report.summary.piecesWithEnvelopeFit,0);
    for(const patch of [{projectId:'another-project'},{pieceId:'another-piece'},{pieceRevision:2},{assetId:'another-asset'},{unit:'inch'}]){
      report=inspect(f,state,[proof(f,state,patch)]);assert.equal(report.pieces[0].file.status,'unchecked');assert.equal(report.summary.piecesWithEnvelopeFit,0);
    }
    for(const status of ['missing','invalid']){
      report=inspect(f,state,[proof(f,state,{status,message:'Source indisponible pour la QA'})]);assert.equal(report.pieces[0].file.status,status);assert.equal(report.pieces[0].dimensionsMm,null);assert.equal(report.summary.piecesWithEnvelopeFit,0);
    }
    report=inspect(f,state,[proof(f,state),proof(f,state,{checkedAt:at+1})]);assert.equal(report.pieces[0].file.status,'unchecked');assert.equal(report.summary.measuredFiles,0);
    state.projects[0].pieces[0].assetId=null;report=inspect(f,state,[proof(f,state)]);assert.equal(report.pieces[0].file.status,'unreferenced');assert.equal(report.summary.measuredFiles,0);
  });

  await check('measurement-validation-and-reconciliation','Nonfinite or malformed measurements cannot generate candidates; valid measured dimensions are compared without silently rewriting stored dimensions.',async()=>{
    const f=await surface('measurements'),state=sampleState(f);
    for(const patch of [{dimsMm:[0,0,0]},{dimsMm:[10,-20,30]},{dimsMm:[10,20]},{triangles:0},{triangles:1.5},{byteLength:14},{sha256:'not-a-checksum'}]){
      const report=inspect(f,state,[proof(f,state,patch)]);assert.equal(report.pieces[0].file.status,'invalid');assert.equal(report.summary.piecesWithEnvelopeFit,0);
    }
    for(const value of [NaN,Infinity]){
      const invalid=proof(f,state);invalid.dimsMm[0]=value;
      const report=f.math.inspectDeclaredPreparation(state,'qa-project',{assetEvidence:[invalid]});assert.equal(report.pieces[0].file.status,'invalid');assert.equal(report.summary.piecesWithEnvelopeFit,0);
    }
    const recordBefore=clone(state),report=inspect(f,state,[proof(f,state,{dimsMm:[11,22,33],sha256:null})]);
    assert.deepEqual(clone(report.pieces[0].storedDimensionsMm),[10,20,30]);assert.deepEqual(clone(report.pieces[0].dimensionsMm),[11,22,33]);assert.equal(report.pieces[0].measurementsMatchRecord,false);assert.equal(report.pieces[0].file.sha256,null);assert.deepEqual(clone(state),recordBefore);
    state.projects[0].pieces[0].unit='cm';const unsupported=inspect(f,state,[proof(f,state)]);assert.notEqual(unsupported.pieces[0].file.status,'measured');assert.equal(unsupported.summary.piecesWithEnvelopeFit,0);
  });

  await check('six-orthogonal-envelope-comparisons','Six orthogonal placements compare the measured box to the useful volume; exact contact is a raw fit and dimensional overflow stays visible.',async()=>{
    const f=await surface('orientations'),state=sampleState(f);state.machines[0].registry=declaredRecord(f,{usableVolumeMm:[20,10,30]});
    const report=inspect(f,state,[proof(f,state)]),assessment=report.pieces[0].assessments[0];
    assert.equal(assessment.orientations.length,6);assert.equal(new Set(assessment.orientations.map(item=>item.id)).size,6);
    assert.deepEqual([...assessment.fitOrientationIds],['yxz']);
    const placed=assessment.orientations.find(item=>item.id==='yxz');assert.deepEqual(clone(placed.dimensionsMm),[20,10,30]);assert.deepEqual(clone(placed.clearanceMm),[0,0,0]);assert.equal(placed.fits,true);
    const initial=assessment.orientations.find(item=>item.id==='xyz');assert.equal(initial.fits,false);assert.equal(initial.clearanceMm[1],-10);
    const oversized=inspect(f,state,[proof(f,state,{dimsMm:[31,32,33]})]);assert.equal(oversized.pieces[0].assessments[0].status,'exceeds');assert.equal(oversized.summary.piecesWithEnvelopeFit,0);
    for(const item of report.pieces[0].assessments){assert.equal(item.qualification.verified,false);assert.equal(item.material.status,'unspecified');}
    assert.equal(report.canSlice,false);assert.equal(report.canStartPhysicalPrint,false);
  });

  await check('real-three-placement-matches-report','The viewport uses actual Three matrices with determinant +1; all six placements of off-origin STL vertices agree with machine-axis dimensions in millimetres and inches.',async()=>{
    const f=await surface('placement'),viewport=(await f.loadReal(path.join(dist,'lib/preparation-viewport.js'))).namespace;
    const three=(await f.loadReal(path.join(dist,'vendor/three.module.js'))).namespace;
    const STLLoader=(await f.loadReal(path.join(dist,'vendor/STLLoader.js'))).namespace.STLLoader;
    const bytes=boxSTL([10,20,30],[-31,7,-42]),buffer=f.buffer(bytes),sourceBefore=Buffer.from(buffer).toString('hex');
    const geometry=new STLLoader().parse(buffer);geometry.computeBoundingBox();
    const positions=geometry.getAttribute('position'),positionsBefore=Array.from(positions.array);
    for(const unit of ['mm','inch']){
      const factor=unit==='inch'?25.4:1,state=sampleState(f,{dims:[10,20,30].map(n=>n*factor),unit});
      state.machines[0].registry=declaredRecord(f,{usableVolumeMm:[1000,1000,1000]});
      const report=inspect(f,state,[proof(f,state)]);
      for(const definition of f.math.PREPARATION_ORIENTATIONS){
        const rotation=viewport.buildOrientationMatrix(definition.id);closeTo(rotation.determinant(),1);
        const sample=new three.Vector3(2,3,5).applyMatrix4(rotation);
        sample.toArray().forEach((value,axis)=>closeTo(value,[2,3,5][definition.axes[axis]]*definition.signs[axis]));
        const placement=viewport.placementForBounds(geometry.boundingBox.min.toArray(),geometry.boundingBox.max.toArray(),unit,definition.id);
        const points=[];for(let i=0;i<positions.count;i++)points.push(new three.Vector3().fromBufferAttribute(positions,i).applyMatrix4(placement.matrix));
        const actualBounds=new three.Box3().setFromPoints(points),size=actualBounds.getSize(new three.Vector3());
        const assessment=report.pieces[0].assessments[0].orientations.find(item=>item.id===definition.id);
        placement.dimensionsMm.forEach((value,axis)=>closeTo(value,assessment.dimensionsMm[axis],1e-7));
        size.toArray().forEach((value,axis)=>closeTo(value,assessment.dimensionsMm[[0,2,1][axis]],1e-7));
        closeTo(actualBounds.min.y,0,1e-7);closeTo(actualBounds.getCenter(new three.Vector3()).x,0,1e-7);closeTo(actualBounds.getCenter(new three.Vector3()).z,0,1e-7);
        actualBounds.min.toArray().forEach((value,axis)=>closeTo(value,placement.worldBounds.min.toArray()[axis],1e-7));
        actualBounds.max.toArray().forEach((value,axis)=>closeTo(value,placement.worldBounds.max.toArray()[axis],1e-7));
        closeTo(placement.matrix.determinant(),factor**3,1e-6);
      }
    }
    assert.deepEqual(Array.from(positions.array),positionsBefore);assert.equal(Buffer.from(buffer).toString('hex'),sourceBefore);
    assert.throws(()=>viewport.buildOrientationMatrix('mirrored'));
    assert.throws(()=>viewport.placementForBounds(f.realm([0,0,0]),f.realm([1,2,3]),'cm'));
    assert.throws(()=>viewport.placementForBounds(f.realm([4,0,0]),f.realm([1,2,3]),'mm'));
    geometry.dispose();
  });

  await check('flat-and-open-meshes','Flat STL geometry is inspectable without a volumetric fit; an open 3D mesh never becomes physically qualified through its bounding box.',async()=>{
    const f=await surface('mesh-limits'),state=sampleState(f);
    const flat=f.inspectSTL(f.buffer(boxSTL([10,20,0])),'mm');assert.deepEqual(clone(flat.dims),[10,20,0]);
    let report=inspect(f,state,[proof(f,state,{dimsMm:flat.dims,triangles:flat.triangles})]);
    assert.equal(report.pieces[0].file.status,'measured');assert.equal(report.summary.nonVolumetricPieces,1);assert.equal(report.pieces[0].assessments[0].status,'non_volumetric');assert.equal(report.summary.piecesWithEnvelopeFit,0);
    const open=f.inspectSTL(f.buffer(boxSTL([10,20,30],[0,0,0],{open:true})),'mm');assert.equal(open.triangles,10);
    report=inspect(f,state,[proof(f,state,{dimsMm:open.dims,triangles:open.triangles})]);
    assert.equal(report.summary.measuredFiles,1);assert.equal(report.canStartPhysicalPrint,false);assert.equal(report.canSlice,false);assert.equal(report.pieces[0].assessments[0].qualification.verified,false);
    assert.match(report.limitations.join(' '),/fermeture|fermé|maillage|étanchéité/);
  });

  await check('immutable-explicit-report-export','A report export retains its exact project and selection, rejects foreign identifiers, and cannot mutate state or claim a machine command.',async()=>{
    const f=await surface('export'),state=sampleState(f),report=inspect(f,state,[proof(f,state)]),before=clone(report);
    const out=f.math.exportDeclaredPreparation(report,f.realm({pieceId:'qa-piece',machineId:'P01',orientationId:'xyz'}),at+1);
    assert.equal(out.canStartPhysicalPrint??out.report?.canStartPhysicalPrint,false);assert.equal(out.canSlice??out.report?.canSlice,false);
    assert.match(JSON.stringify(out),/qa-project/);assert.match(JSON.stringify(out),/qa-piece/);assert.match(JSON.stringify(out),/xyz/);assert.deepEqual(clone(report),before);
    for(const selection of [{pieceId:'foreign'},{pieceId:'qa-piece',machineId:'foreign'},{pieceId:'qa-piece',machineId:'P01',orientationId:'unlisted'}])assert.throws(()=>f.math.exportDeclaredPreparation(report,f.realm(selection),at+1));
    assert.throws(()=>f.math.exportDeclaredPreparation(report,{},NaN));
    assert.throws(()=>f.math.inspectDeclaredPreparation(state,'foreign-project',{}));
    assert.deepEqual(clone(out.execution),{slicingRequested:false,physicalPrintRequested:false,geometryModified:false,stlIncluded:false});
    out.report.pieces[0].dimensionsMm[0]=999;out.project.name='Changed export only';assert.deepEqual(clone(report),before);
  });

  await check('workbench-real-files-and-controls','The workbench reads authentic local STL bytes through an asynchronous inspector, shows their hash and unit, and routes orientation, machine, import and export controls.',async()=>{
    const f=await surface('workbench'),state=twoPieceState(f);state.machines[0].registry=declaredRecord(f,{usableVolumeMm:[20,10,30]});const before=clone(state);
    await mountWorkbench(f,state,{inspectSTL:async(buffer,unit)=>f.inspectSTL(buffer,unit)});await f.ready();
    await eventually(()=>f.viewports.some(viewport=>viewport.loads.length),'The selected STL must reach the viewport.');
    assert.equal(f.report.summary.measuredFiles,2);assert.equal(f.report.summary.piecesWithEnvelopeFit,2);
    assert.equal(f.$('[data-prep-metric="measured"]').textContent,'2');
    const sha=createHash('sha256').update(boxSTL()).digest('hex');assert.equal(f.report.pieces[0].file.sha256,sha);assert(f.$('[data-prep-source-details]').textContent.includes(sha));
    assert.equal(f.$$('[data-prep-orientation]').length,6);assert.equal(f.$('[data-prep-result]').dataset.status,'exceeds');await f.click('[data-prep-orientation="yxz"]');
    assert.equal(f.$('[data-prep-orientation="yxz"]').getAttribute('aria-pressed'),'true');assert.equal(f.viewports.at(-1).orientations.at(-1),'yxz');
    assert.equal(f.$('[data-prep-result]').dataset.status,'fits');
    await f.change('[data-prep-machine]','P02');assert.deepEqual(f.viewports.at(-1).volumes.at(-1),[80,85,90]);
    await f.change('[data-prep-import-unit]','inch');await f.click('[data-prep-action="import"]');assert.deepEqual(f.imports.at(-1),{projectId:'qa-project',pieceId:'qa-piece',unit:'inch'});
    await f.click('[data-prep-action="fleet"]');assert.deepEqual(f.fleetRequests.at(-1),{machineId:'P02'});
    await f.click('[data-prep-action="export"]');assert.equal(f.exports.at(-1).report.project.id,'qa-project');assert.equal(f.exports.at(-1).selection.machineId,'P02');assert.equal(f.exports.at(-1).report.canSlice,false);assert.equal(f.exports.at(-1).report.canStartPhysicalPrint,false);
    f.controller.setMotion(false);assert(f.$('[data-preparation-workbench]').classList.contains('pw-motion-off'));assert.equal(f.viewports.at(-1).motion.at(-1),false);
    const ids=f.$$('[id]').map(node=>node.id);assert.equal(ids.length,new Set(ids).size);assert.deepEqual(clone(state),before);assert.equal(f.fetchCalls.length,0);assert.equal(f.errors.length,0);
  });

  await check('missing-invalid-and-webgl-unavailable','Missing or invalid binaries show no substitute model; valid measurements and export remain available when WebGL cannot start.',async()=>{
    const f=await surface('unavailable'),state=twoPieceState(f);f.assets.delete('qa-asset');f.assets.set('second-asset',{id:'second-asset',buffer:f.buffer('Not an STL model at all.')});
    await mountWorkbench(f,state);await f.ready();await settle();
    assert.equal(f.report.summary.measuredFiles,0);assert.equal(f.report.summary.missingFiles,1);assert.equal(f.report.summary.invalidFiles,1);assert.equal(f.report.summary.piecesWithEnvelopeFit,0);
    assert.equal(f.viewports.reduce((total,viewport)=>total+viewport.loads.length,0),0);assert.equal(f.$('[data-prep-empty]').hidden,false);assert.match(f.$('[data-prep-empty-title]').textContent,/STL|fichier/i);
    assert.equal(f.$$('[data-prep-orientation]:not([disabled])').length,0);
    await f.click('[data-prep-piece="second-piece"]');await settle();assert.match(f.$('[data-prep-source-details]').textContent,/invalide/i);assert.equal(f.viewports.reduce((total,viewport)=>total+viewport.loads.length,0),0);
    const noGL=await surface('without-webgl'),known=sampleState(noGL);noGL.addAsset('qa-asset',boxSTL());noGL.failViewport=true;
    await mountWorkbench(noGL,known);await noGL.ready();await eventually(()=>/mesures restent/i.test(noGL.$('[data-prep-empty-title]').textContent));
    assert.equal(noGL.report.summary.measuredFiles,1);assert.equal(noGL.report.summary.piecesWithEnvelopeFit,1);assert.equal(noGL.$('[data-prep-action="export"]').disabled,false);assert.equal(noGL.viewports.length,0);assert.equal(noGL.errors.length,0);
  });

  await check('machine-change-during-stl-read','A delayed STL preview always receives the currently selected machine volume, including a registry change during the read.',async()=>{
    const f=await surface('machine-race'),state=twoPieceState(f);await mountWorkbench(f,state);await f.ready();await eventually(()=>f.viewports.at(-1)?.loads.length>0);
    const pending=gate();f.assetGates.set('second-asset',pending);const readsBefore=f.assetReads.length;
    await f.click('[data-prep-piece="second-piece"]');await eventually(()=>f.assetReads.length>readsBefore);
    await f.change('[data-prep-machine]','P02');
    const next=f.realm(clone(state));next.machines[1].registry=f.fleet.normalizeFleetRecord(f.realm({origin:'declared',model:'Machine B ajustée',technology:'fdm',usableVolumeMm:[44,55,66],volumeSource:'Mesure suivante'}),next.machines[1].registry,at+1);
    f.refresh(next);pending.resolve();await eventually(()=>f.viewports.at(-1)?.loads.some(load=>load.result.dims[0]===40));
    assert.equal(f.$('[data-prep-machine]').value,'P02');assert.deepEqual(f.viewports.at(-1).volumes.at(-1),[44,55,66]);assert.deepEqual(clone(f.report.machines[1].record.usableVolumeMm),[44,55,66]);
    assert.match(f.$('[data-prep-machine-note]').textContent,/44 × 55 × 66/);assert.equal(f.errors.length,0);
  });

  await check('obsolete-piece-read-and-disposal','Changing the selected piece ignores an old asynchronous read; closing the workbench prevents a late viewport or STL from reappearing.',async()=>{
    const f=await surface('piece-race'),state=twoPieceState(f);await mountWorkbench(f,state);await f.ready();await eventually(()=>f.viewports.at(-1)?.loads.length>0);
    const initialLoads=f.viewports.at(-1).loads.length,pending=gate();f.assetGates.set('second-asset',pending);const readsBefore=f.assetReads.length;
    await f.click('[data-prep-piece="second-piece"]');await eventually(()=>f.assetReads.length>readsBefore);await f.click('[data-prep-piece="qa-piece"]');pending.resolve();
    await eventually(()=>f.viewports.at(-1).loads.length>initialLoads);assert(f.viewports.at(-1).loads.slice(initialLoads).every(load=>load.result.dims[0]===10));assert.equal(f.$('[data-prep-piece="qa-piece"]').getAttribute('aria-pressed'),'true');
    const closed=await surface('closed-preview'),closedState=sampleState(closed);closed.addAsset('qa-asset',boxSTL());closed.viewportGate=gate();
    await mountWorkbench(closed,closedState);closed.controller.dispose();closed.viewportGate.resolve();await settle();
    assert(closed.viewports.every(viewport=>viewport.disposed));assert(closed.viewports.every(viewport=>viewport.loads.length===0));assert.equal(closed.errors.length,0);
  });

  await check('captured-project-during-export','The open preparation retains its target after another screen selects a project; an asynchronous export receives an immutable snapshot of that target.',async()=>{
    const f=await surface('project-race'),state=twoPieceState(f),pending=gate();
    state.projects.push(f.realm({id:'other-project',name:'Autre dossier',revision:1,height:200,quantity:1,pieces:[]}));
    await mountWorkbench(f,state,{onExport:async()=>{await pending.promise;return{ok:true,message:'Export du dossier initial.'};}});await f.ready();
    f.refresh(state,'other-project');assert.equal(f.$('[data-prep-context]').hidden,false);assert.match(f.$('[data-prep-context]').textContent,/Dossier QA/);
    await f.click('[data-prep-action="export"]');assert.equal(f.exports.length,1);assert.equal(f.exports[0].report.project.id,'qa-project');assert.equal(f.$('[data-prep-action="export"]').disabled,true);
    const changed=f.realm(clone(state));changed.projects[0].name='Dossier QA renommé';changed.projects[0].revision++;
    f.refresh(changed,'other-project');pending.resolve();await settle();
    assert.equal(f.exports[0].report.project.name,'Dossier QA');assert.equal(f.$('[data-prep-project-name]').textContent,'Dossier QA renommé');assert(!f.$('[data-prep-export-status]').textContent.includes('Export du dossier initial.'));
    await f.click('[data-prep-action="import"]');assert.equal(f.imports.at(-1).projectId,'qa-project');assert.equal(f.errors.length,0);
  });

  await check('application-targeted-import-and-export','The live application associates a real STL with its captured piece in inches after the active project changes, preserves its name and technology, and exports the inspected target.',async()=>{
    const f=await appPreparation('app-import'),before=clone(f.project('sculpture-xl').pieces.find(piece=>piece.id==='buste')),otherBefore=clone(f.project('prototype'));
    const pending=gate(),bytes=boxSTL([1,2,3]);await f.change('[data-prep-import-unit]','inch');await f.click('[data-prep-action="import"]');
    await chooseFile(f,'#preparation-stl-input',{bytes,pending});await f.selectProject('prototype');
    assert.equal(f.$('#drawer').open,true);assert.equal(f.$('[data-preparation-workbench]').dataset.projectId,'sculpture-xl');pending.resolve();
    await eventually(()=>f.project('sculpture-xl').pieces.find(piece=>piece.id==='buste').assetId!=='qa-asset','The import must attach to the original piece.');
    const piece=f.project('sculpture-xl').pieces.find(piece=>piece.id==='buste');assert.equal(piece.name,before.name);assert.equal(piece.tech,before.tech);assert.equal(piece.unit,'inch');assert.equal(piece.revision,before.revision+1);piece.dims.forEach((value,axis)=>closeTo(value,[25.4,50.8,76.2][axis]));
    assert.deepEqual(clone(f.project('prototype')),otherBefore);assert.equal(f.store.state.projectId,'prototype');assert.equal(f.store.state.selectedPieceId,'boitier');
    assert.equal(Buffer.from(f.assets.get(piece.assetId).buffer).toString('hex'),bytes.toString('hex'));
    await eventually(()=>!f.$('[data-prep-action="export"]').disabled);await f.click('[data-prep-action="export"]');
    const exported=await readDownload(f);assert.equal(exported.project.id,'sculpture-xl');assert.equal(exported.selection.pieceId,'buste');assert.equal(exported.report.pieces.find(item=>item.id==='buste').file.sha256,createHash('sha256').update(bytes).digest('hex'));
    assert.deepEqual(exported.execution,{slicingRequested:false,physicalPrintRequested:false,geometryModified:false,stlIncluded:false});
    await f.click('#motion-button');assert(f.$('[data-preparation-workbench]').classList.contains('pw-motion-off'));
    assert(f.fetchCalls.every(call=>call.method==='GET'&&['/assets/archive-index.json','/api/workshop/status','/api/workshop/assets/status'].includes(call.pathname)),JSON.stringify(f.fetchCalls));assert.equal(f.errors.length,0);
  });

  await check('targeted-import-stale-piece-guard','Changing a piece while its replacement STL is being read or stored preserves the current file and geometry instead of overwriting them with the late import.',async()=>{
    for(const stage of ['read','storage']){
      const f=await appPreparation('stale-import-'+stage),before=clone(f.project('sculpture-xl').pieces.find(piece=>piece.id==='buste'));
      const pending=gate();if(stage==='storage')f.assetWriteGate=pending;
      await f.click('[data-prep-action="import"]');await chooseFile(f,'#preparation-stl-input',{bytes:boxSTL([31,32,33]),pending:stage==='read'?pending:null});
      if(stage==='storage')await eventually(()=>f.assetWriteAttempts.length>0);
      f.act('UPDATE_PIECE',{projectId:'sculpture-xl',id:'buste',patch:{dims:[12,23,34]}});await settle();pending.resolve();
      await eventually(()=>/changé/.test(f.$('#toast').textContent),'The stale replacement must report that the piece changed.');
      const piece=f.project('sculpture-xl').pieces.find(piece=>piece.id==='buste');assert.equal(piece.assetId,before.assetId);assert.deepEqual(clone(piece.dims),[12,23,34]);assert.equal(piece.revision,before.revision+1);
      assert.equal(f.store.exportJournal().operations.filter(operation=>operation.type==='UPDATE_PIECE'&&operation.payload.expectedPieceRevision!==undefined).length,0);
      assert.equal(f.errors.length,0);
    }
  });

  await check('general-import-preserves-other-screen-selection','A general multi-file import keeps its original project without selecting or showing a foreign piece after another screen switches projects.',async()=>{
    const f=await appPreparation('general-import'),originalCount=f.project('sculpture-xl').pieces.length,otherBefore=clone(f.project('prototype')),pending=gate();
    await f.click('[data-action="close-dialog"]');await chooseFile(f,'#stl-input',{name:'late_general.stl',bytes:boxSTL([21,22,23]),pending});await f.selectProject('prototype');pending.resolve();
    await eventually(()=>f.project('sculpture-xl').pieces.length===originalCount+1);await settle();
    assert.deepEqual(clone(f.project('prototype')),otherBefore);assert.equal(f.store.state.projectId,'prototype');assert.equal(f.store.state.selectedPieceId,'boitier');assert.equal(f.$('#main').dataset.screen,'pilotage');
    assert.match(f.$('#toast').textContent,/SCULPTURE XL/);assert(!f.store.state.journal.some(entry=>entry.ok===false&&/Pièce absente/.test(entry.message)));assert.equal(f.errors.length,0);
  });

  await check('workbench-css-and-escaped-identity','The workbench stylesheet parses, honors reduced motion, and renders user-supplied project, piece and machine names without executable markup.',async()=>{
    const css=fs.readFileSync(path.join(dist,'preparation.css'),'utf8');csstree.parse(css,{parseValue:false,parseCustomProperty:false});assert.match(css,/prefers-reduced-motion/);assert.match(css,/pw-motion-off/);
    const f=await surface('escaped-workbench'),state=sampleState(f);state.projects[0].name='</strong><img src=x onerror=bad()>';state.projects[0].pieces[0].name='</span><script>bad()</script>';
    state.machines[0].registry=declaredRecord(f,{model:'</option><img src=x onerror=bad()>'});f.addAsset('qa-asset',boxSTL());
    await mountWorkbench(f,state);await f.ready();assert.equal(f.$$('[data-preparation-workbench] script,[data-preparation-workbench] [onerror]').length,0);
    assert(f.$('[data-prep-project-name]').textContent.includes('<img'));assert(f.$('[data-prep-piece-name]').textContent.includes('<script>'));assert.equal(f.errors.length,0);
  });
}

(async () => {
  try { await run(); }
  catch(error) { checks.push({id:'harness',status:'failed',description:'Preparation QA harness',error:error.stack}); }
  finally {
    for (const f of fixtures) { f.closed=true; for(const pending of f.assetGates.values()) pending.resolve(); f.assetWriteGate?.resolve();f.viewportGate?.resolve(); f.controller?.dispose?.(); for(const store of f.stores) store.dispose?.(); f.w.close(); }
  }
  const report = {status:checks.some(check=>check.status==='failed')?'failed':'passed',checks,browserRenderingVerified:false,webglRenderingVerified:false,hardwareVerified:false,livePrinterConnections:0,reason:'Real STL parsing, pure Three geometry and isolated JSDOM only. No browser preview server or physical command.'};
  fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
  if(report.status!=='passed')process.exitCode=1;
})();
