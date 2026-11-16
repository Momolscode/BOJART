// V11 explicit STL import QA: full application, real STL parser and controlled
// browser storage/async boundaries. Isolated DOM only; no server, browser or hardware.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {createHash, webcrypto} = require('node:crypto');
const {JSDOM} = require('jsdom');
const csstree = require('css-tree');

const root = path.resolve(__dirname, '..');
const dist = path.join(root, 'dist');
const reportPath = path.join(__dirname, 'v11-stl-import-results.json');
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
            if (f.failAssetWrite || (f.failAssetWriteOnceFor && record.name === f.failAssetWriteOnceFor)) { f.failAssetWriteOnceFor = null; transaction.error = new Error('Quota de test'); transaction.onerror?.(); return; }
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
  f.inspectCalls = [];
  f.inspectSTL = (buffer, unit) => { f.inspectCalls.push({unit, byteLength: buffer.byteLength}); return actualViewer.namespace.inspectSTL(buffer, unit); };
  f.fileGates = [];
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

async function check(id, description, task) {
  try { await task(); checks.push({id, status: 'passed', description}); }
  catch (error) { checks.push({id, status: 'failed', description, error: error.stack}); }
}
async function eventually(predicate, message = 'Asynchronous work did not settle') {
  const deadline = Date.now() + 3000;
  while (Date.now() < deadline) { if (predicate()) return; await new Promise(resolve => setTimeout(resolve, 5)); }
  throw new Error(message);
}
function file(f, name, dims = [10,20,30], {pending, bytes = boxSTL(dims)} = {}) {
  if (pending) f.fileGates.push(pending);
  const item = {name, size: bytes.length, reads: 0, bytes, async arrayBuffer() { item.reads++; if (pending) await pending.promise; return f.buffer(bytes); }};
  return item;
}
async function selectFiles(f, files) {
  const input = f.$('#stl-input');
  Object.defineProperty(input, 'files', {configurable: true, value: files});
  input.dispatchEvent(new f.w.Event('change', {bubbles: true}));
  await settle();
  return f.$('#stl-import-form');
}
function choices(form, index, unit, tech) {
  form.elements.namedItem(`unit-${index}`).value = unit;
  form.elements.namedItem(`tech-${index}`).value = tech;
}
function submit(f, form = f.$('#stl-import-form')) { form.dispatchEvent(new f.w.Event('submit', {bubbles: true, cancelable: true})); }
async function drop(f, files) {
  const event = new f.w.Event('drop', {bubbles: true, cancelable: true});
  Object.defineProperty(event, 'dataTransfer', {value: {files}});
  f.w.document.dispatchEvent(event);
  await settle();
}
const row = (f, index) => f.$(`[data-stl-row="${index}"]`);
const status = (f, index) => f.$(`[data-stl-status="${index}"]`)?.textContent || '';
const baseIds = (f, id = 'sculpture-xl') => new Set(f.project(id).pieces.map(piece => piece.id));
const addedPieces = (f, before, id = 'sculpture-xl') => f.project(id).pieces.filter(piece => !before.has(piece.id));
function unchangedProject(f, id, before) { assert.deepEqual(clone(f.project(id)), before); }

(async () => {
  await check('choices-required', 'No default unit or process; empty, partial and invalid choices perform no parsing, file read or asset write.', async () => {
    const f = await surface('choices-required', {app: true});
    const before = clone(f.project('sculpture-xl')), selected = file(f, 'sans-hypothese.stl');
    const form = await selectFiles(f, [selected]);
    assert(form); assert.equal(form.dataset.project, before.id);
    assert.equal(form.elements.namedItem('unit-0').value, '');
    assert.equal(form.elements.namedItem('tech-0').value, '');
    assert.equal(form.checkValidity(), false);
    submit(f); await settle();
    assert.equal(selected.reads, 0); assert.equal(f.inspectCalls.length, 0); assert.equal(f.assetWrites.length, 0);
    // Exercise the application validator as well as the browser constraint gate.
    form.reportValidity = () => true;
    submit(f); await settle(); assert.match(f.$('#form-error').textContent, /unité/);
    choices(form, 0, 'mm', ''); submit(f); await settle(); assert.match(f.$('#form-error').textContent, /procédé/);
    choices(form, 0, '', 'resin'); submit(f); await settle(); assert.match(f.$('#form-error').textContent, /unité/);
    assert.equal(selected.reads, 0); assert.equal(f.inspectCalls.length, 0); assert.equal(f.assetWrites.length, 0);
    unchangedProject(f, before.id, before);
  });

  await check('mixed-unit-process-destination', 'Mixed mm/FDM and inch/resin files retain their explicit choices and original destination when the active dossier changes during reading.', async () => {
    const f = await surface('mixed-unit-process-destination', {app: true}), pending = gate();
    const before = baseIds(f), otherBefore = clone(f.project('prototype'));
    const first = file(f, 'Socle millimetres.stl', [10,20,30], {pending});
    const second = file(f, 'Figurine pouces.stl', [1,2,3]);
    const form = await selectFiles(f, [first, second]);
    choices(form, 0, 'mm', 'fdm'); choices(form, 1, 'inch', 'resin'); submit(f);
    await eventually(() => first.reads === 1, 'The first source is being read');
    await f.selectProject('prototype');
    assert.equal(f.$('#stl-import-form'), form); assert.match(form.textContent, /reste lié/);
    pending.resolve(); await eventually(() => row(f, 1)?.dataset.state === 'added', 'Both mixed entries complete');
    const added = addedPieces(f, before); assert.equal(added.length, 2);
    const a = added.find(piece => piece.name === 'Socle millimetres'), b = added.find(piece => piece.name === 'Figurine pouces');
    assert(a && b); assert.equal(a.tech, 'fdm'); assert.equal(a.unit, 'mm'); assert.equal(b.tech, 'resin'); assert.equal(b.unit, 'inch');
    [10,20,30].forEach((value, i) => closeTo(a.dims[i], value));
    [25.4,50.8,76.2].forEach((value, i) => closeTo(b.dims[i], value, 1e-5));
    for (const [piece, source] of [[a,first],[b,second]]) {
      assert.equal(piece.machine, null); assert.equal(piece.triangles, 12);
      assert.equal(piece.assetSha256, createHash('sha256').update(source.bytes).digest('hex'));
      assert.deepEqual(Buffer.from(f.assets.get(piece.assetId).buffer), source.bytes);
    }
    unchangedProject(f, 'prototype', otherBefore); f.store.refresh(); assert.equal(f.store.state.projectId, 'prototype');
    assert.equal(first.reads, 1); assert.equal(second.reads, 1); assert.equal(f.assetWrites.length, 2);
    assert.match(f.$('[data-stl-import-summary]').textContent, /2 pièce.*SCULPTURE XL/);
    assert.equal(form.querySelector('button[type="submit"]').disabled, true);
  });

  await check('double-submit', 'Two submissions in one interval read and append the source only once.', async () => {
    const f = await surface('double-submit', {app: true}), pending = gate(), before = baseIds(f);
    const selected = file(f, 'unique.stl', [10,20,30], {pending});
    const form = await selectFiles(f, [selected]); choices(form, 0, 'mm', 'fdm');
    submit(f); submit(f); await eventually(() => selected.reads > 0);
    assert.equal(selected.reads, 1); assert.equal(form.querySelector('button[type="submit"]').disabled, true);
    pending.resolve(); await eventually(() => row(f, 0)?.dataset.state === 'added'); await settle();
    assert.equal(selected.reads, 1); assert.equal(addedPieces(f, before).length, 1); assert.equal(f.assetWrites.length, 1);
    submit(f); await settle(); assert.equal(addedPieces(f, before).length, 1); assert.equal(f.assetWrites.length, 1);
  });

  await check('close-during-file-read', 'Closing the import while arrayBuffer is pending produces no parsing, asset write or piece addition after reading returns.', async () => {
    const f = await surface('close-during-file-read', {app: true}), pending = gate(), before = clone(f.project('sculpture-xl'));
    const selected = file(f, 'fermeture.stl', [10,20,30], {pending});
    const form = await selectFiles(f, [selected]); choices(form, 0, 'mm', 'resin'); submit(f);
    await eventually(() => selected.reads === 1); await f.click('#stl-import-form [data-action="close-dialog"]');
    pending.resolve(); await settle(); await settle();
    assert.equal(f.$('#drawer').open, false); assert.equal(f.inspectCalls.length, 0); assert.equal(f.assetWrites.length, 0);
    unchangedProject(f, before.id, before);
  });

  await check('revision-during-file-read', 'A concurrent destination revision interrupts the lot without overwriting the revised dossier or attaching a stale part.', async () => {
    const f = await surface('revision-during-file-read', {app: true}), pending = gate();
    const selected = file(f, 'revision.stl', [10,20,30], {pending}), form = await selectFiles(f, [selected]);
    choices(form, 0, 'mm', 'fdm'); submit(f); await eventually(() => selected.reads === 1);
    f.act('UPDATE_PROJECT', {id: 'sculpture-xl', patch: {quantity: 2, notes: 'Une autre saisie a été enregistrée pendant la lecture.'}}); await settle();
    const updated = clone(f.project('sculpture-xl')); pending.resolve();
    await eventually(() => row(f, 0)?.dataset.state === 'error');
    assert.match(status(f, 0), /dossier de destination a changé/);
    assert.equal(form.querySelector('button[type="submit"]').disabled, true);
    assert.equal(f.inspectCalls.length, 0); assert.equal(f.assetWrites.length, 0); unchangedProject(f, updated.id, updated);
    submit(f); await settle(); assert.equal(selected.reads, 1); unchangedProject(f, updated.id, updated);
  });

  await check('partial-success-retry', 'After one asset storage failure, retry only reads and adds the remaining source; the already-added part and its bytes remain unchanged.', async () => {
    const f = await surface('partial-success-retry', {app: true}), before = baseIds(f);
    const first = file(f, 'conservee.stl'), second = file(f, 'a-reprendre.stl', [1,2,3]);
    f.failAssetWriteOnceFor = second.name;
    const form = await selectFiles(f, [first,second]); choices(form, 0, 'mm', 'fdm'); choices(form, 1, 'inch', 'resin'); submit(f);
    await eventually(() => row(f, 1)?.dataset.state === 'error');
    assert.equal(row(f, 0).dataset.state, 'added'); assert.match(status(f, 1), /Quota/);
    const kept = clone(addedPieces(f, before)[0]); assert(kept); assert.equal(addedPieces(f, before).length, 1);
    assert.equal(form.elements.namedItem('unit-0').disabled, true); assert.equal(form.elements.namedItem('tech-0').disabled, true);
    assert.equal(form.elements.namedItem('unit-1').disabled, false); assert.equal(form.elements.namedItem('tech-1').disabled, false);
    assert.match(form.querySelector('button[type="submit"]').textContent, /Reprendre/);
    submit(f); await eventually(() => row(f, 1)?.dataset.state === 'added');
    const completed = addedPieces(f, before); assert.equal(completed.length, 2);
    assert.deepEqual(clone(completed.find(piece => piece.id === kept.id)), kept);
    assert.equal(new Set(completed.map(piece => piece.assetId)).size, 2);
    assert.equal(first.reads, 1); assert.equal(second.reads, 2); assert.equal(f.assetWrites.length, 2); assert.equal(f.assetWriteAttempts.length, 3);
    assert.equal(completed.find(piece => piece.name === 'a-reprendre').tech, 'resin');
    assert.equal(completed.find(piece => piece.name === 'a-reprendre').unit, 'inch');
    assert.match(f.$('[data-stl-import-summary]').textContent, /2 pièce.*Toutes les pièces/);
  });

  await check('preserve-open-drafts-on-drop', 'Dropping an STL preserves a draft brief, Jarvis command and existing STL setup instead of replacing the open panel.', async () => {
    const f = await surface('preserve-open-drafts-on-drop', {app: true}), before = clone(f.project('sculpture-xl'));
    const incoming = file(f, 'nouveau.stl');
    await f.click('[data-action="project-edit"]');
    const draft = f.$('#project-form'); assert(draft);
    await f.input('#project-form [name="notes"]', 'Brouillon non enregistré, à conserver exactement.');
    await drop(f, [incoming]);
    assert.equal(f.$('#project-form'), draft); assert.equal(draft.elements.namedItem('notes').value, 'Brouillon non enregistré, à conserver exactement.');
    assert.equal(f.$('#stl-import-form'), null); assert.match(f.$('#toast').textContent, /Fermez le panneau actuel/);
    await f.click('#project-form [data-action="close-dialog"]');
    await f.click('[data-action="command"]'); await f.input('#command-input', 'Jarvis, voici une intention non soumise');
    const command = f.$('#command-form'); await drop(f, [incoming]);
    assert.equal(f.$('#command-dialog').open, true); assert.equal(f.$('#command-form'), command);
    assert.equal(f.$('#command-input').value, 'Jarvis, voici une intention non soumise'); assert.equal(f.$('#stl-import-form'), null);
    await f.click('[data-action="close-command"]');
    const original = file(f, 'deja-selectionnee.stl'), setup = await selectFiles(f, [original]); choices(setup, 0, 'inch', 'fdm');
    await drop(f, [incoming]);
    assert.equal(f.$('#stl-import-form'), setup); assert.equal(setup.elements.namedItem('unit-0').value, 'inch');
    assert.equal(setup.elements.namedItem('tech-0').value, 'fdm'); assert.match(setup.textContent, /deja-selectionnee/);
    assert.doesNotMatch(setup.textContent, /nouveau.stl/); assert.equal(incoming.reads, 0); assert.equal(original.reads, 0);
    assert.equal(f.inspectCalls.length, 0); assert.equal(f.assetWrites.length, 0); unchangedProject(f, before.id, before);
  });

  await check('close-during-storage', 'Closing after parsing while storage is in flight attaches no piece; an already-started byte write may remain as an unassociated asset.', async () => {
    const f = await surface('close-during-storage', {app: true}), before = clone(f.project('sculpture-xl'));
    const pending = gate(); f.assetWriteGate = pending;
    const selected = file(f, 'ecriture-en-cours.stl'), form = await selectFiles(f, [selected]); choices(form, 0, 'mm', 'fdm'); submit(f);
    await eventually(() => f.assetWriteAttempts.length === 1);
    await f.click('#stl-import-form [data-action="close-dialog"]'); pending.resolve();
    await eventually(() => f.assetWrites.length === 1); await settle();
    unchangedProject(f, before.id, before); assert.equal(f.$('#drawer').open, false);
    assert.equal(f.assets.size, 1); assert.equal(selected.reads, 1);
  });

  await check('motion-focus-responsive-contract', 'The explicit import keeps labelled required controls and status text; reduced-motion CSS covers the drawer and the UI toggle preserves input.', async () => {
    const css = fs.readFileSync(path.join(dist, 'style.css'), 'utf8');
    const extra = fs.readFileSync(path.join(dist, 'integrity.css'), 'utf8');
    const parseErrors = []; csstree.parse(css, {onParseError: error => parseErrors.push(error.message)}); csstree.parse(extra, {onParseError: error => parseErrors.push(error.message)});
    assert.deepEqual(parseErrors, []);
    assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    assert.match(css, /\.reduced-motion[^{}]*\{[^}]*animation:\s*none!important[^}]*transition:\s*none!important/);
    assert.match(css, /@media\(prefers-reduced-motion:reduce\)\{html\{scroll-behavior:auto\}\*,\*:before,\*:after\{animation:none!important;transition:none!important\}/);
    assert.match(extra, /\.stl-import-row select:focus-visible\{[^}]*outline:/);
    assert.match(extra, /@media\(max-width:430px\)\{\.stl-import-row\{grid-template-columns:1fr\}/);
    const f = await surface('motion-focus-responsive-contract', {app: true});
    const form = await selectFiles(f, [file(f, 'interface.stl')]); choices(form, 0, 'inch', 'resin');
    for (const select of form.querySelectorAll('select')) { assert.equal(select.required, true); assert(select.closest('label')); }
    assert.equal(form.querySelector('[data-stl-status]').getAttribute('role'), 'status');
    assert.equal(form.querySelector('#form-error').getAttribute('role'), 'alert');
    await f.click('#motion-button');
    assert.equal(f.w.document.documentElement.classList.contains('reduced-motion'), true);
    assert.equal(f.$('#stl-import-form'), form); assert.equal(form.elements.namedItem('unit-0').value, 'inch'); assert.equal(form.elements.namedItem('tech-0').value, 'resin');
  });

  await settle();
  const unexpectedErrors = fixtures.flatMap(f => f.errors.map(error => ({surface: f.name, error})));
  const networkWrites = fixtures.flatMap(f => f.fetchCalls.filter(call => call.method !== 'GET').map(call => ({surface: f.name, ...call})));
  if (unexpectedErrors.length) checks.push({id: 'no-unhandled-ui-errors', status: 'failed', description: 'No unexpected DOM error', errors: unexpectedErrors});
  if (networkWrites.length) checks.push({id: 'no-network-mutations', status: 'failed', description: 'No external request, connector or machine mutation', requests: networkWrites});
  const passed = checks.filter(item => item.status === 'passed').length, failed = checks.filter(item => item.status === 'failed').length;
  const report = {
    generatedAt: new Date().toISOString(), suite: 'BOJ.ART V11 explicit STL import', passed, failed,
    environment: {runtime: process.version, fullApplication: true, realSTLParser: true, browser: false, webGL: false, server: false, realIndexedDB: false, realMachine: false},
    scope: 'App.js integration with actual import helper, WorkshopStore reducer and real STL/Three geometry; controlled JSDOM and IndexedDB contract.',
    limitations: ['Does not certify visual rendering, actual browser IndexedDB persistence or hardware behavior.', 'A write already in flight when the drawer is closed may leave unassociated STL bytes; the dossier remains unchanged.', 'New parts remain unassigned and unqualified. No slicing or printing is triggered.'],
    checks, unexpectedErrors, networkWrites
  };
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  for (const f of fixtures) { f.closed = true; f.assetWriteGate?.resolve(); f.viewportGate?.resolve(); for (const pending of f.fileGates) pending.resolve(); for (const pending of f.assetGates.values()) pending.resolve(); for (const store of f.stores) store.destroy?.(); f.w.close(); }
  console.log(JSON.stringify({passed, failed, report: path.relative(root, reportPath), failures: checks.filter(item => item.status === 'failed')}, null, 2));
  process.exitCode = failed ? 1 : 0;
})().catch(error => { console.error(error); process.exitCode = 1; for (const f of fixtures) { f.closed = true; f.w.close(); } });

