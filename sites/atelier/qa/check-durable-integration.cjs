const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const os = require('node:os');
const {pathToFileURL} = require('node:url');
const {webcrypto} = require('node:crypto');
const {JSDOM} = require('jsdom');

// Independent integration coverage. Only disposable SQLite databases are used.
// No socket, preview server, browser engine, hardware or external service starts.
const root = path.resolve(__dirname, '..');
const dist = path.join(root, 'dist');
const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
const seed = {version: 1, at: 1760000000000};
const seedKey = 'bojart.workshop.v1.seed';
const channels = new Map();
const fixtures = new Set();
const checks = [];
const databases = new Set(), temporaryDirectories = new Set();
let sqliteRoundtripVerified = false;
const copy = value => JSON.parse(JSON.stringify(value));
const tick = () => new Promise(resolve => setImmediate(resolve));
async function settle() { for (let i = 0; i < 4; i++) await tick(); }

class Storage {
  constructor(initial = new Map([[seedKey, JSON.stringify(seed)]])) {
    this.entries = new Map(initial);
    this.failReads = false;
    this.failWrites = false;
    this.writes = 0;
  }
  get length() { return this.entries.size; }
  key(index) { return [...this.entries.keys()][index] ?? null; }
  getItem(key) {
    if (this.failReads) throw new Error('Read unavailable in fixture');
    return this.entries.get(key) ?? null;
  }
  setItem(key, value) {
    if (this.failWrites) throw new Error('Quota exceeded in fixture');
    this.writes++;
    this.entries.set(key, String(value));
  }
  removeItem(key) { this.entries.delete(key); }
  snapshot() { return JSON.stringify([...this.entries].sort(([a], [b]) => a.localeCompare(b))); }
}

async function surface(name, {storage = new Storage(), role = 'pilotage', app = false, group = name} = {}) {
  const dom = new JSDOM(html, {
    url: `https://bojart.test/?screen=${role}&station=${role}&immersive=1`,
    runScripts: 'outside-only', pretendToBeVisual: true
  });
  const w = dom.window, context = dom.getInternalVMContext();
  const f = {name, dom, w, storage, modules: new Map(), errors: [], fetchCalls: [], response: null, stores: [], syncs: []};
  fixtures.add(f);
  Object.defineProperty(w, 'localStorage', {value: storage});
  w.matchMedia = () => ({matches: false, addEventListener() {}});
  w.scrollTo = () => {};
  w.TextEncoder = TextEncoder;
  w.TextDecoder = TextDecoder;
  Object.defineProperty(w.crypto, 'subtle', {value: webcrypto.subtle});
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  w.HTMLCanvasElement.prototype.getContext = () => null;
  w.HTMLMediaElement.prototype.pause = function () {};
  w.HTMLMediaElement.prototype.play = async function () {};
  w.addEventListener('error', event => f.errors.push(event.error?.message || event.message));
  f.realm = value => w.JSON.parse(JSON.stringify(value));
  f.json = (value, status = 200) => ({ok: status >= 200 && status < 300, status, json: async () => f.realm(value)});
  w.fetch = async (input, options = {}) => {
    const url = new w.URL(String(input), w.location.href);
    const call = {pathname: url.pathname, search: url.search, after: Number(url.searchParams.get('after') || 0), method: options.method || 'GET', body: options.body ? JSON.parse(options.body) : null, credentials: options.credentials};
    f.fetchCalls.push(call);
    if (url.pathname === '/assets/archive-index.json') return f.json(JSON.parse(fs.readFileSync(path.join(dist, 'assets/archive-index.json'), 'utf8')));
    return f.response ? f.response(call, options) : f.json({ok: false, code: 'not_found'}, 404);
  };
  w.BroadcastChannel = class {
    constructor(name) {
      this.name = group + ':' + name;
      this.closed = false;
      this.listeners = new Set();
      const peers = channels.get(this.name) || new Set();
      peers.add(this); channels.set(this.name, peers);
    }
    addEventListener(type, listener) { if (type === 'message') this.listeners.add(listener); }
    removeEventListener(type, listener) { if (type === 'message') this.listeners.delete(listener); }
    deliver(serialized) {
      if (this.closed) return;
      const event = {data: f.realm(JSON.parse(serialized))};
      this.onmessage?.(event);
      for (const listener of this.listeners) listener(event);
    }
    postMessage(data) {
      if (this.closed) throw new Error('Closed channel in fixture');
      const serialized = JSON.stringify(data);
      for (const peer of channels.get(this.name) || []) if (peer !== this && !peer.closed) queueMicrotask(() => peer.deliver(serialized));
    }
    close() { this.closed = true; channels.get(this.name)?.delete(this); }
  };
  const viewer = new vm.SyntheticModule(['createViewer', 'inspectSTL'], function () {
    this.setExport('createViewer', async () => ({loadSTL: () => ({dims: [20, 20, 20], triangles: 12}), showDemo() {}, reset() {}, explode: () => true, setWireframe() {}, setAutoRotate() {}, setMotion() {}, setSection() {}, dispose() {}}));
    this.setExport('inspectSTL', () => ({dims: [20, 20, 20], triangles: 12}));
  }, {context});
  await viewer.link(() => {}); await viewer.evaluate();
  function moduleFor(filename) {
    filename = path.resolve(filename);
    if (f.modules.has(filename)) return f.modules.get(filename);
    const mod = new vm.SourceTextModule(fs.readFileSync(filename, 'utf8'), {
      context, identifier: filename,
      importModuleDynamically: async (spec, parent) => spec.endsWith('/viewer.js') || spec === './viewer.js' ? viewer : f.load(path.resolve(path.dirname(parent.identifier), spec))
    });
    f.modules.set(filename, mod); return mod;
  }
  f.load = async filename => {
    const mod = moduleFor(filename);
    if (mod.status === 'unlinked') await mod.link((spec, parent) => moduleFor(path.resolve(path.dirname(parent.identifier), spec)));
    if (mod.status !== 'evaluated') await mod.evaluate();
    return mod;
  };
  f.$ = selector => w.document.querySelector(selector);
  f.click = async selector => { const node = f.$(selector); assert(node, name + ' missing ' + selector); node.click(); await settle(); };
  f.submit = async selector => { const form = f.$(selector); assert(form, name + ' missing ' + selector); form.dispatchEvent(new w.Event('submit', {bubbles: true, cancelable: true})); await settle(); };
  f.values = (form, values) => { for (const [key, value] of Object.entries(values)) { const field = form.elements.namedItem(key); assert(field, name + ' missing field ' + key); field.value = String(value); } };
  if (app) { f.app = await f.load(path.join(dist, 'app.js')); await settle(); }
  const storeModule = await f.load(path.join(dist, 'lib/workshop.js'));
  f.store = new storeModule.namespace.WorkshopStore(); f.stores.push(f.store);
  f.act = (type, payload) => {
    const result = f.store.dispatch(type, f.realm(payload));
    assert.equal(result.ok, true, result.message);
    return copy(result);
  };
  f.journal = () => copy(f.store.exportJournal());
  f.merge = (journal, options) => f.store.mergeJournal(f.realm(journal), options ? f.realm(options) : undefined);
  return f;
}

function closeFixtures() {
  for (const f of fixtures) {
    for (const sync of f.syncs) { try { sync.stop(); } catch {} }
    for (const store of f.stores) { try { store.dispose(); } catch {} }
    try { f.w.dispatchEvent(new f.w.Event('pagehide')); f.w.close(); } catch {}
  }
  fixtures.clear();
  for (const peers of channels.values()) for (const peer of peers) peer.close();
  channels.clear();
  for (const database of databases) { try { database.close(); } catch {} }
  databases.clear();
  for (const directory of temporaryDirectories) fs.rmSync(directory, {recursive: true, force: true});
  temporaryDirectories.clear();
}

async function repository() {
  const {createWorkshopRepository} = await import(pathToFileURL(path.join(root, 'local/workshop-repository.mjs')).href);
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'bojart-durable-qa-'));
  temporaryDirectories.add(directory);
  const database = createWorkshopRepository({directory}); databases.add(database);
  return {database, directory, createWorkshopRepository};
}

async function transport(f) {
  const {database} = await repository();
  // These cases isolate mutation ACKs; empty-service bootstrap is covered in check-workshop-authority.mjs.
  database.append({version: 2, workspaceId: database.status().workspaceId, seed, operations: []});
  const service = {database, override: null};
  service.reply = async call => {
    try {
      if (call.pathname === '/api/workshop/status' && call.method === 'GET') return f.json(database.status());
      if (call.pathname === '/api/workshop/operations' && call.method === 'GET') return f.json(database.operations(call.after));
      if (call.pathname === '/api/workshop/operations' && call.method === 'POST') return f.json(database.append(call.body));
      if (call.pathname === '/api/workshop/backup') return f.json(call.method === 'POST' ? database.restore(call.body) : database.backup());
      return f.json({ok: false, code: 'not_found'}, 404);
    } catch (error) { return f.json({ok: false, code: error.code, message: error.message}, error.status || 500); }
  };
  f.response = (call, options) => service.override ? service.override(call, options) : service.reply(call);
  return service;
}

async function syncClient(f) {
  const module = await f.load(path.join(dist, 'lib/workshop-sync.js'));
  const statuses = [];
  const client = module.namespace.createWorkshopSync({store: f.store, fetchImpl: (...args) => f.w.fetch(...args), onStatus: status => statuses.push(copy(status))});
  f.syncs.push(client);
  return {client, statuses};
}

async function check(id, label, run) {
  try {
    await run();
    for (const f of fixtures) assert.deepEqual(f.errors, [], f.errors.join('\n'));
    checks.push({id, label, status: 'passed'});
    console.log('PASS ' + label);
  } catch (error) {
    checks.push({id, label, status: 'failed', error: {name: error.name, message: error.message}});
    console.error('FAIL ' + label + ': ' + error.message);
  } finally { closeFixtures(); }
}

function reordered(value) {
  if (Array.isArray(value)) return value.map(reordered);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).reverse().map(([key, child]) => [key, reordered(child)]));
}

async function journalChecks() {
  await check('additive-restore', 'Same-seed restoration adds work on independent aggregates without replacing local work; repeated import is idempotent.', async () => {
    const local = await surface('additive-local'), remote = await surface('additive-remote');
    local.act('UPDATE_PROJECT', {id: 'sculpture-xl', patch: {name: 'Projet préparé dans la tour'}});
    remote.act('SAVE_STORY', {projectId: 'prototype', text: 'Brouillon écrit dans l’autre navigateur.'});
    const imported = local.merge(remote.journal());
    assert.equal(imported.ok, true); assert.equal(imported.added, 1); assert.equal(imported.persisted, true);
    assert.equal(local.store.getProject().name, 'Projet préparé dans la tour');
    assert.equal(local.store.state.projects.find(project => project.id === 'prototype').story, 'Brouillon écrit dans l’autre navigateur.');
    assert.equal(local.journal().operations.length, 2);
    const before = local.storage.snapshot(), state = copy(local.store.state);
    const repeated = local.merge(local.journal());
    assert.equal(repeated.added, 0); assert.equal(repeated.duplicates, 2);
    assert.equal(local.storage.snapshot(), before); assert.deepEqual(copy(local.store.state), state);
  });

  await check('canonical-duplicate', 'Equivalent operation objects with different property order remain one immutable journal entry.', async () => {
    const f = await surface('canonical');
    f.act('SAVE_STORY', {projectId: 'prototype', text: 'Ordre des propriétés sans effet.'});
    const before = f.storage.snapshot();
    const result = f.merge(reordered(f.journal()));
    assert.equal(result.added, 0); assert.equal(result.duplicates, 1); assert.equal(f.storage.snapshot(), before);
  });

  await check('seed-conflict-atomic', 'A divergent seed is rejected before any write or state change, even when adoption is requested on a nonempty journal.', async () => {
    const f = await surface('seed-conflict');
    f.act('UPDATE_PROJECT', {id: 'prototype', patch: {notes: 'Donnée locale à conserver.'}});
    const incoming = f.journal(); incoming.seed.at += 1;
    const before = f.storage.snapshot(), state = copy(f.store.state);
    assert.throws(() => f.merge(incoming));
    assert.throws(() => f.merge(incoming, {allowEmptyAdoption: true}));
    assert.equal(f.storage.snapshot(), before); assert.deepEqual(copy(f.store.state), state);
  });

  await check('empty-adoption-explicit', 'Only an explicitly requested adoption can attach a browser with no local operations to a different seed.', async () => {
    const f = await surface('empty-adoption');
    const remoteStorage = new Storage(new Map([[seedKey, JSON.stringify({...seed, at: seed.at + 1000})]]));
    const remote = await surface('empty-remote', {storage: remoteStorage});
    remote.act('SAVE_STORY', {projectId: 'prototype', text: 'Journal restauré dans un navigateur neuf.'});
    const incoming = remote.journal(), before = f.storage.snapshot();
    assert.throws(() => f.merge(incoming)); assert.equal(f.storage.snapshot(), before);
    const adopted = f.merge(incoming, {allowEmptyAdoption: true});
    assert.equal(adopted.ok, true); assert.deepEqual(f.journal().seed, incoming.seed);
    assert.equal(f.store.state.projects.find(project => project.id === 'prototype').story, 'Journal restauré dans un navigateur neuf.');
  });

  await check('collision-preflight', 'An existing ID with changed content rejects the entire incoming batch before its otherwise-valid new operation is written.', async () => {
    const f = await surface('collision-local'), remote = await surface('collision-remote');
    f.act('SAVE_STORY', {projectId: 'prototype', text: 'Texte original immuable.'});
    remote.act('UPDATE_PROJECT', {id: 'commande-art', patch: {notes: 'Nouvelle opération dans le même paquet.'}});
    const collision = copy(f.journal().operations[0]); collision.payload.text = 'Collision qui tente de modifier l’histoire.';
    const incoming = remote.journal(); incoming.operations.push(collision);
    const before = f.storage.snapshot(), state = copy(f.store.state);
    assert.throws(() => f.merge(incoming));
    assert.equal(f.storage.snapshot(), before); assert.deepEqual(copy(f.store.state), state);
  });

  await check('internal-collision-preflight', 'Two different operations with the same ID inside one packet are rejected without partial restoration.', async () => {
    const f = await surface('internal-collision'), remote = await surface('internal-remote');
    remote.act('SAVE_STORY', {projectId: 'prototype', text: 'Première version.'});
    const incoming = remote.journal(), collision = copy(incoming.operations[0]);
    collision.payload.text = 'Deuxième version utilisant le même ID.'; incoming.operations.push(collision);
    const before = f.storage.snapshot(), state = copy(f.store.state);
    assert.throws(() => f.merge(incoming));
    assert.equal(f.storage.snapshot(), before); assert.deepEqual(copy(f.store.state), state);
  });
}

async function registryChecks() {
  await check('registry-offline-conflict', 'Concurrent registry edits converge deterministically while preserving the rejected operation in both journals.', async () => {
    const a = await surface('registry-a'), b = await surface('registry-b');
    const physicalBefore = copy({machines: a.store.state.machines.map(({registry, ...machine}) => machine), jobs: a.store.state.jobs, projects: a.store.state.projects});
    const rawA = {origin: 'declared', model: 'Machine de test A', technology: 'fdm', notes: 'Saisie hors ligne A.'};
    const rawB = {origin: 'declared', model: 'Machine de test B', technology: 'fdm', notes: 'Saisie hors ligne B.'};
    a.act('UPDATE_MACHINE', {id: 'P08', patch: {registry: rawA}, expectedRegistryRevision: 0});
    b.act('UPDATE_MACHINE', {id: 'P08', patch: {registry: rawB}, expectedRegistryRevision: 0});
    const journalA = a.journal(), journalB = b.journal();
    const [winner, loser] = [journalA.operations[0], journalB.operations[0]].sort((left, right) => left.clock - right.clock || left.id.localeCompare(right.id));
    const mergedA = a.merge(journalB), mergedB = b.merge(journalA);
    assert.equal(mergedA.rejected.length, 1); assert.equal(mergedB.rejected.length, 1);
    assert.equal(mergedA.rejected[0].id, loser.id); assert.equal(mergedB.rejected[0].id, loser.id);
    assert.equal(a.store.getMachine('P08').registry.notes, winner.payload.patch.registry.notes);
    assert.equal(b.store.getMachine('P08').registry.notes, winner.payload.patch.registry.notes);
    assert.equal(a.store.getMachine('P08').registry.revision, 1);
    assert.deepEqual(a.journal(), b.journal());
    assert.equal(a.journal().operations.length, 2);
    assert.equal(a.store.state.journal.find(entry => entry.id === loser.id).ok, false);
    assert.deepEqual(copy({machines: a.store.state.machines.map(({registry, ...machine}) => machine), jobs: a.store.state.jobs, projects: a.store.state.projects}), physicalBefore);
    const before = a.storage.snapshot();
    const stale = a.store.dispatch('UPDATE_MACHINE', a.realm({id: 'P08', patch: {registry: rawA}, expectedRegistryRevision: 0}));
    assert.equal(stale.ok, false); assert.equal(a.storage.snapshot(), before);
    a.act('UPDATE_MACHINE', {id: 'P08', patch: {registry: {...rawA, notes: 'Saisie revue après lecture du conflit.'}}, expectedRegistryRevision: 1});
    assert.equal(a.store.getMachine('P08').registry.revision, 2);
  });
}

async function backupChecks() {
  await check('browser-backup-integrity', 'Browser backup round trip preserves the journal and detects changed content before any restoration.', async () => {
    const f = await surface('backup-integrity');
    f.act('SAVE_STORY', {projectId: 'prototype', text: 'Brouillon inclus dans la sauvegarde.'});
    const module = await f.load(path.join(dist, 'lib/workshop-backup.js'));
    const backup = await module.namespace.createWorkshopBackup(f.realm(f.journal()));
    assert.equal(backup.sourceInstanceId, 'browser');
    assert.deepEqual(copy(backup.excludes), ['stl_binaries', 'credentials', 'printer_state']);
    const checked = await module.namespace.inspectWorkshopBackup(JSON.stringify(backup));
    assert.deepEqual(copy(checked.journal), f.journal());
    const changed = copy(backup); changed.operations[0].payload.text = 'Texte altéré sans nouvelle empreinte.';
    const before = f.storage.snapshot();
    await assert.rejects(() => module.namespace.inspectWorkshopBackup(JSON.stringify(changed)), /empreinte/i);
    assert.equal(f.storage.snapshot(), before);
  });

  await check('browser-sqlite-backup-roundtrip', 'A default browser backup restores into an isolated SQLite journal, survives reopening and restores additively into another browser.', async () => {
    const f = await surface('sqlite-export');
    f.act('UPDATE_PROJECT', {id: 'prototype', patch: {notes: 'Preuve de persistance indépendante du navigateur.'}});
    const browserModule = await f.load(path.join(dist, 'lib/workshop-backup.js'));
    const backup = copy(await browserModule.namespace.createWorkshopBackup(f.realm(f.journal())));
    const {createWorkshopRepository, directory, database} = await repository();
    const restored = database.restore(backup);
    assert.equal(restored.ok, true); assert.equal(restored.operationCount, 1);
    const instanceId = restored.instanceId;
    database.close(); databases.delete(database);
    const reopened = createWorkshopRepository({directory}); databases.add(reopened);
    assert.equal(reopened.status().instanceId, instanceId);
    assert.equal(reopened.status().operationCount, 1);
    const second = await surface('sqlite-import');
    second.act('SAVE_STORY', {projectId: 'commande-art', text: 'Brouillon local écrit avant restauration.'});
    const secondModule = await second.load(path.join(dist, 'lib/workshop-backup.js'));
    const checked = await secondModule.namespace.inspectWorkshopBackup(JSON.stringify(reopened.backup()));
    const result = second.merge(copy(checked.journal));
    assert.equal(result.added, 1); assert.equal(second.journal().operations.length, 2);
    const project = second.store.state.projects.find(project => project.id === 'prototype');
    assert.equal(project.notes, 'Preuve de persistance indépendante du navigateur.');
    assert.equal(second.store.state.projects.find(item => item.id === 'commande-art').story, 'Brouillon local écrit avant restauration.');
    sqliteRoundtripVerified = true;
  });
}

async function syncChecks() {
  await check('sync-confirmation-pending', 'Availability, in-flight writes, new edits and confirmed persistence have distinct truthful statuses.', async () => {
    const f = await surface('sync-confirmation'), service = await transport(f), {client} = await syncClient(f);
    f.act('SAVE_STORY', {projectId: 'prototype', text: 'Modification envoyée au journal local.'});
    assert.equal(client.status.mode, 'browser'); assert.equal(client.status.durable, false); assert.equal(client.status.lastSavedAt, null);
    await client.inspect();
    assert.equal(client.status.mode, 'available'); assert.equal(client.status.durable, false); assert.equal(client.status.lastSavedAt, null);
    assert.equal(f.fetchCalls.filter(call => call.method === 'POST').length, 0);
    let release = null;
    service.override = async call => {
      const response = await service.reply(call);
      if (call.method === 'POST' && call.body.operations.length) return new Promise(resolve => { release = () => resolve(response); });
      return response;
    };
    const pending = client.connect(); await settle();
    assert(release, 'The write acknowledgement should be deferred by the fixture');
    assert.equal(client.status.mode, 'syncing'); assert.equal(client.status.durable, false); assert.equal(client.status.lastSavedAt, null);
    assert.equal(client.status.pending, 1);
    f.act('UPDATE_PROJECT', {id: 'prototype', patch: {notes: 'Nouvelle saisie pendant la confirmation.'}});
    assert.equal(client.status.pending, 2);
    release(); await pending;
    assert.equal(client.status.mode, 'syncing'); assert.equal(client.status.pending, 1);
    service.override = null;
    await client.sync();
    assert.equal(client.status.mode, 'saved'); assert.equal(client.status.pending, 0); assert.equal(client.status.durable, true);
    assert(Number.isFinite(client.status.lastSavedAt)); assert.equal(service.database.status().operationCount, 2);
    assert(f.fetchCalls.every(call => call.credentials === 'same-origin'));
  });

  await check('sync-ack-loss-retry', 'A malformed success acknowledgement cannot claim persistence; rereading the committed journal recovers without duplicate entries.', async () => {
    const f = await surface('sync-ack-loss'), service = await transport(f), {client} = await syncClient(f);
    f.act('SAVE_STORY', {projectId: 'prototype', text: 'Opération dont la réponse a été perdue.'});
    service.override = async call => {
      const response = await service.reply(call);
      if (call.method === 'POST' && call.body.operations.length) {
        const body = copy(await response.json()); body.accepted = []; body.duplicates = [];
        return f.json(body);
      }
      return response;
    };
    await client.connect();
    assert(['offline', 'error'].includes(client.status.mode)); assert.equal(client.status.durable, false); assert.equal(client.status.lastSavedAt, null); assert.equal(client.status.pending, 1);
    assert.equal(service.database.status().operationCount, 1);
    service.override = null; await client.sync();
    assert.equal(client.status.mode, 'saved'); assert.equal(client.status.pending, 0);
    assert.equal(service.database.status().operationCount, 1);
  });

  await check('sync-truncated-page', 'A page claiming completion before the advertised cursor is rejected before merging a truncated journal.', async () => {
    const f = await surface('sync-truncated'), remote = await surface('sync-truncated-remote');
    remote.act('SAVE_STORY', {projectId: 'prototype', text: 'Première opération distante.'});
    remote.act('UPDATE_PROJECT', {id: 'prototype', patch: {notes: 'Seconde opération distante.'}});
    const service = await transport(f); service.database.append({...remote.journal(), version: 2, workspaceId: service.database.status().workspaceId});
    service.override = async call => {
      const response = await service.reply(call);
      if (call.pathname === '/api/workshop/operations' && call.method === 'GET') {
        const body = copy(await response.json()); body.operations = body.operations.slice(0, 1); body.nextCursor = 1; body.hasMore = false;
        return f.json(body);
      }
      return response;
    };
    const {client} = await syncClient(f); await client.connect();
    assert.notEqual(client.status.mode, 'saved'); assert.equal(client.status.durable, false); assert.equal(client.status.lastSavedAt, null);
    assert.equal(f.journal().operations.length, 0);
  });

  await check('sync-instance-change', 'A changed service identity blocks automatic continuation and preserves new local work.', async () => {
    const f = await surface('sync-instance'), service = await transport(f), {client} = await syncClient(f);
    f.act('SAVE_STORY', {projectId: 'prototype', text: 'Journal associé à une base précise.'});
    await client.connect(); assert.equal(client.status.mode, 'saved');
    f.act('UPDATE_PROJECT', {id: 'prototype', patch: {notes: 'Saisie à garder après remplacement de la base.'}});
    const before = f.journal();
    service.override = async call => {
      const response = await service.reply(call);
      if (call.pathname === '/api/workshop/status') { const body = copy(await response.json()); body.instanceId = 'workshop-00000000-0000-4000-8000-000000000000'; return f.json(body); }
      return response;
    };
    const writes = f.fetchCalls.filter(call => call.method === 'POST').length;
    await client.sync();
    assert.equal(client.status.mode, 'conflict'); assert.equal(client.status.durable, false); assert.equal(client.status.pending, 1);
    assert.equal(f.fetchCalls.filter(call => call.method === 'POST').length, writes);
    assert.deepEqual(f.journal(), before);
  });

  await check('sync-memory-truth', 'A storage failure remains labelled memory-only until a separately confirmed service write exists.', async () => {
    const storage = new Storage(); storage.failReads = true;
    const f = await surface('sync-memory', {storage}), {client} = await syncClient(f);
    const result = f.act('SAVE_STORY', {projectId: 'prototype', text: 'Saisie en mémoire volatile.'});
    assert.equal(result.persisted, false); assert.equal(f.store.persistent, false);
    assert.equal(client.status.mode, 'memory'); assert.equal(client.status.durable, false);
    await client.inspect();
    assert.equal(client.status.mode, 'memory'); assert.equal(client.status.lastSavedAt, null);
    assert.equal(f.journal().operations.length, 1);
  });

  await check('sync-business-conflict-status', 'Confirmed journal storage and a rejected business edit remain distinct when two registry revisions conflict.', async () => {
    const f = await surface('sync-business-local'), remote = await surface('sync-business-remote');
    f.act('UPDATE_MACHINE', {id: 'P08', patch: {registry: {origin: 'declared', model: 'Fiche saisie dans la tour', notes: 'Révision locale.'}}, expectedRegistryRevision: 0});
    remote.act('UPDATE_MACHINE', {id: 'P08', patch: {registry: {origin: 'declared', model: 'Fiche reçue du service', notes: 'Révision distante.'}}, expectedRegistryRevision: 0});
    const service = await transport(f); service.database.append({...remote.journal(), version: 2, workspaceId: service.database.status().workspaceId});
    const {client} = await syncClient(f); await client.connect();
    assert.equal(client.status.mode, 'conflict'); assert.equal(client.status.conflicts, 1);
    assert.equal(client.status.pending, 0); assert.equal(client.status.durable, true);
    assert(Number.isFinite(client.status.lastSavedAt)); assert.equal(service.database.status().operationCount, 2);
    assert.equal(f.journal().operations.length, 2);
    assert.equal(f.store.state.journal.filter(entry => entry.ok === false).length, 1);
    assert.equal(f.store.getMachine('P08').qualified, false);
  });
}

async function applicationChecks() {
  await check('ui-stale-fleet-form', 'Two real application windows preserve an unsaved fleet form and reject its stale revision without overwriting the first edit.', async () => {
    const storage = new Storage();
    const left = await surface('ui-fleet-left', {storage, app: true, role: 'atelier', group: 'ui-fleet'});
    const center = await surface('ui-fleet-center', {storage, app: true, role: 'pilotage', group: 'ui-fleet'});
    await left.click('[data-action="fleet"]'); await left.click('[data-fleet-machine="P08"]');
    await center.click('[data-action="fleet"]'); await center.click('[data-fleet-machine="P08"]');
    const editing = center.$('#fleet-form'); assert(editing);
    center.values(editing, {origin: 'declared', model: 'Mon brouillon non enregistré', notes: 'Texte à conserver exactement, malgré une fiche reçue.'});
    left.values(left.$('#fleet-form'), {origin: 'declared', model: 'Machine renseignée sur le premier écran', notes: 'Référence validée par le premier opérateur.'});
    await left.submit('#fleet-form'); await settle();
    assert(center.$('#drawer').open); assert.equal(center.$('#fleet-form'), editing);
    assert.equal(editing.dataset.id, 'P08'); assert.equal(editing.dataset.revision, '0');
    assert.equal(editing.elements.namedItem('notes').value, 'Texte à conserver exactement, malgré une fiche reçue.');
    assert.equal(center.$('#main').dataset.screen, 'pilotage'); assert.equal(left.$('#main').dataset.screen, 'atelier');
    assert.equal(center.store.getMachine('P08').registry.model, 'Machine renseignée sur le premier écran');
    const before = center.journal();
    await center.submit('#fleet-form');
    assert(center.$('#drawer').open); assert.equal(center.$('#fleet-form'), editing);
    assert.match(center.$('#form-error').textContent, /fiche a changé|autre écran|révision/i);
    assert.equal(editing.elements.namedItem('model').value, 'Mon brouillon non enregistré');
    assert.deepEqual(center.journal(), before);
    assert.equal(center.store.getMachine('P08').registry.revision, 1);
  });

  await check('ui-project-change-preserves-form', 'A project selection from another window preserves the current screen, tab and editor target, and saving still updates the original dossier.', async () => {
    const storage = new Storage();
    const left = await surface('ui-dossier-left', {storage, app: true, role: 'atelier', group: 'ui-dossier'});
    const center = await surface('ui-dossier-center', {storage, app: true, role: 'pilotage', group: 'ui-dossier'});
    await center.click('[data-pilot-tab="dossiers"]'); await center.click('[data-action="project-edit"]');
    const editing = center.$('#project-form'), original = editing.dataset.id;
    assert.equal(original, 'sculpture-xl');
    center.values(editing, {notes: 'Brouillon rattaché au premier dossier, à garder pendant la sync.'});
    const nextNotes = left.store.state.projects.find(project => project.id === 'prototype').notes;
    left.act('SELECT_PROJECT', {id: 'prototype'}); await settle();
    assert.equal(center.$('#project-picker').value, 'prototype');
    assert.equal(center.$('#main').dataset.screen, 'pilotage');
    assert.equal(center.$('[data-pilot-tab="dossiers"]').getAttribute('aria-selected'), 'true');
    assert(center.$('#drawer').open); assert.equal(center.$('#project-form'), editing);
    assert.equal(editing.dataset.id, original);
    assert.equal(editing.elements.namedItem('notes').value, 'Brouillon rattaché au premier dossier, à garder pendant la sync.');
    await center.submit('#project-form'); await settle();
    assert.equal(center.store.state.projects.find(project => project.id === original).notes, 'Brouillon rattaché au premier dossier, à garder pendant la sync.');
    assert.equal(center.store.state.projects.find(project => project.id === 'prototype').notes, nextNotes);
    assert.equal(center.$('#main').dataset.screen, 'pilotage');
  });

  await check('ui-memory-status', 'The visible save indicator reports memory-only retention when browser storage is unavailable.', async () => {
    const storage = new Storage(); storage.failReads = true;
    const f = await surface('ui-memory', {storage, app: true});
    await f.click('[data-pilot-tab="dossiers"]'); await f.click('[data-action="project-edit"]');
    f.values(f.$('#project-form'), {notes: 'Saisie non durable à ne pas annoncer sauvegardée.'});
    await f.submit('#project-form');
    assert.match(f.$('#save-status').textContent, /fenêtre|mémoire/i);
    assert.doesNotMatch(f.$('#save-status').textContent, /sauvegarde navigateur|conservé sur la tour/i);
    assert.equal(f.store.persistent, false);
  });

  await check('ui-continuity-confirmation', 'The continuity drawer and footer display saved-on-tower only after the actual repository acknowledgement returns.', async () => {
    const f = await surface('ui-continuity', {app: true});
    const service = await transport(f);
    f.act('SAVE_STORY', {projectId: 'prototype', text: 'Saisie suivie dans le panneau Continuité.'}); await settle();
    await f.click('[data-action="continuity"]');
    assert(f.$('#continuity-status'));
    await f.click('[data-action="sync-inspect"]');
    assert.equal(f.$('[data-sync-mode]').dataset.syncMode, 'available');
    assert.doesNotMatch(f.$('#save-status').textContent, /Conservé sur la tour/i);
    let release = null;
    service.override = async call => {
      const response = await service.reply(call);
      if (call.method === 'POST' && call.body.operations.length) return new Promise(resolve => { release = () => resolve(response); });
      return response;
    };
    await f.click('[data-action="sync-connect"]');
    assert(release, 'The UI should await the write acknowledgement');
    assert.equal(f.$('[data-sync-mode]').dataset.syncMode, 'syncing');
    assert.doesNotMatch(f.$('#save-status').textContent, /Conservé sur la tour/i);
    assert.equal(f.$('#main').dataset.screen, 'pilotage');
    release(); await settle();
    assert.equal(f.$('[data-sync-mode]').dataset.syncMode, 'saved');
    assert.match(f.$('#save-status').textContent, /Conservé sur la tour/i);
    assert.equal(service.database.status().operationCount, 1);
    assert(f.$('#drawer').open); assert.equal(f.$('#main').dataset.screen, 'pilotage');
  });

  await check('ui-created-project-sqlite', 'A project created through the actual form survives browser backup, SQLite restoration and replay with its stage and empty geometry intact.', async () => {
    const f = await surface('ui-new-project', {app: true});
    await f.click('[data-pilot-tab="dossiers"]'); await f.click('[data-action="new-project"]');
    f.values(f.$('#project-form'), {name: 'Nouveau prototype de la tour', kind: 'prototype', quantity: 2, height: 85, notes: 'Brief créé dans le formulaire puis restauré.', status: 'Étude'});
    await f.submit('#project-form'); await settle();
    const id = f.store.state.projectId, project = f.store.getProject();
    assert.equal(project.name, 'Nouveau prototype de la tour'); assert.equal(project.status, 'Étude');
    assert.equal(project.quantity, 2); assert.equal(project.pieces.length, 0);
    const module = await f.load(path.join(dist, 'lib/workshop-backup.js'));
    const backup = copy(await module.namespace.createWorkshopBackup(f.realm(f.journal())));
    const {database} = await repository(); const result = database.restore(backup);
    assert.equal(result.ok, true); assert.equal(result.operationCount, 1);
    const second = await surface('ui-new-project-restored');
    const backupModule = await second.load(path.join(dist, 'lib/workshop-backup.js'));
    const checked = await backupModule.namespace.inspectWorkshopBackup(JSON.stringify(database.backup()));
    second.merge(copy(checked.journal));
    const restored = second.store.state.projects.find(project => project.id === id);
    assert(restored); assert.equal(restored.name, 'Nouveau prototype de la tour'); assert.equal(restored.status, 'Étude');
    assert.equal(restored.notes, 'Brief créé dans le formulaire puis restauré.'); assert.equal(restored.pieces.length, 0);
  });
}

(async () => {
  await journalChecks();
  await registryChecks();
  await backupChecks();
  await syncChecks();
  await applicationChecks();
  const failed = checks.filter(check => check.status === 'failed');
  const report = {status: failed.length ? 'failed' : 'passed', checks, browserRenderingVerified: false, webglRenderingVerified: false, sqliteRoundtripVerified, liveServicesVerified: false, scope: 'Isolated JSDOM contexts, actual WorkshopStore, browser backup validator and SQLite repository. Temporary SQLite database only; no browser engine, socket or physical operation.'};
  fs.writeFileSync(path.join(__dirname, 'durable-integration-results.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (failed.length) process.exitCode = 1;
})().catch(error => { closeFixtures(); console.error(error); process.exitCode = 1; });
