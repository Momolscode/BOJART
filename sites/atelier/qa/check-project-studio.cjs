// Focused QA of project-bound editing plans, journal replay and application wiring.
// Real business/app modules, isolated DOM windows and disposable SQLite only.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const os = require('node:os');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const {webcrypto} = require('node:crypto');
const {JSDOM} = require('jsdom');

const root = path.resolve(__dirname, '..');
const dist = path.join(root, 'dist');
const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
const index = JSON.parse(fs.readFileSync(path.join(dist, 'assets/archive-index.json'), 'utf8'));
const reportPath = path.join(__dirname, 'project-studio-results.json');
const businessOnly = process.argv.includes('--business-only');
const seed = {version: 1, at: 1760000000000};
const seedKey = 'bojart.workshop.v1.seed';
const fixtures = [], channels = new Map(), checks = [], databases = new Set(), directories = new Set();
const clone = value => JSON.parse(JSON.stringify(value));
const tick = () => new Promise(resolve => setImmediate(resolve));
async function settle() { for (let i = 0; i < 4; i++) await tick(); }

class Storage {
  constructor(initial) { this.entries = new Map(initial || [[seedKey, JSON.stringify(seed)]]); }
  get length() { return this.entries.size; }
  key(index) { return [...this.entries.keys()][index] ?? null; }
  getItem(key) { return this.entries.get(key) ?? null; }
  setItem(key, value) { this.entries.set(key, String(value)); }
  removeItem(key) { this.entries.delete(key); }
  snapshot() { return JSON.stringify([...this.entries].sort(([a], [b]) => a.localeCompare(b))); }
}

async function surface(name, {storage = new Storage(), group = name, role = 'pilotage', panel = '', app = false} = {}) {
  const dom = new JSDOM(html, {
    url: `https://bojart.test/?screen=${role}&station=${role}&immersive=1${panel ? '&panel=' + panel : ''}`,
    runScripts: 'outside-only', pretendToBeVisual: true
  });
  const w = dom.window, context = dom.getInternalVMContext();
  const f = {name, dom, w, storage, modules: new Map(), fetchCalls: [], errors: [], downloads: [], objectURLs: new Map(), revokedURLs: [], stores: []};
  fixtures.push(f);
  Object.defineProperty(w, 'localStorage', {value: storage});
  Object.defineProperty(w.crypto, 'subtle', {value: webcrypto.subtle});
  w.matchMedia = () => ({matches: false, addEventListener() {}, removeEventListener() {}});
  w.scrollTo = () => {};
  w.TextEncoder = TextEncoder;
  w.TextDecoder = TextDecoder;
  w.HTMLCanvasElement.prototype.getContext = () => null;
  w.HTMLDialogElement.prototype.showModal = function() { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function() {
    if (!this.open) return;
    this.removeAttribute('open');
    setImmediate(() => { if (!f.closed) this.dispatchEvent(new w.Event('close')); });
  };
  const listenerRecords = new WeakMap();
  const add = w.EventTarget.prototype.addEventListener, remove = w.EventTarget.prototype.removeEventListener;
  const listenerKey = (type, options) => type + ':' + !!(typeof options === 'boolean' ? options : options?.capture);
  w.EventTarget.prototype.addEventListener = function(type, listener, options) {
    if (listener) {
      let record = listenerRecords.get(this);
      if (!record) listenerRecords.set(this, record = new Map());
      const key = listenerKey(type, options);
      if (!record.has(key)) record.set(key, new Set());
      record.get(key).add(listener);
    }
    return add.call(this, type, listener, options);
  };
  w.EventTarget.prototype.removeEventListener = function(type, listener, options) {
    listenerRecords.get(this)?.get(listenerKey(type, options))?.delete(listener);
    return remove.call(this, type, listener, options);
  };
  f.listenerCount = (target, type) => (listenerRecords.get(target)?.get(type + ':false')?.size || 0) + (listenerRecords.get(target)?.get(type + ':true')?.size || 0);
  const media = new WeakMap();
  f.mediaState = element => {
    if (!media.has(element)) media.set(element, {paused: true, playCalls: 0, pauseCalls: 0});
    return media.get(element);
  };
  Object.defineProperties(w.HTMLMediaElement.prototype, {
    paused: {get() { return f.mediaState(this).paused; }},
    ended: {get() { return false; }},
    duration: {get() { return this.src.includes('brand-film') ? 22.7 : 6; }},
    readyState: {get() { return 4; }}
  });
  w.HTMLMediaElement.prototype.play = async function() { const state = f.mediaState(this); state.playCalls++; state.paused = false; this.dispatchEvent(new w.Event('play')); };
  w.HTMLMediaElement.prototype.pause = function() { const state = f.mediaState(this); state.pauseCalls++; if (!state.paused) { state.paused = true; this.dispatchEvent(new w.Event('pause')); } };
  let objectId = 0;
  w.URL.createObjectURL = blob => { const url = `blob:https://bojart.test/${name}-${++objectId}`; f.objectURLs.set(url, blob); return url; };
  w.URL.revokeObjectURL = url => { f.revokedURLs.push(url); f.objectURLs.delete(url); };
  const clickAnchor = w.HTMLAnchorElement.prototype.click;
  w.HTMLAnchorElement.prototype.click = function() {
    if (this.download) f.downloads.push({filename: this.download, href: this.href, blob: f.objectURLs.get(this.href)});
    else clickAnchor.call(this);
  };
  w.addEventListener('error', event => f.errors.push(event.error?.stack || event.message));
  f.realm = value => w.JSON.parse(JSON.stringify(value));
  f.response = (body, status = 200) => ({ok: status >= 200 && status < 300, status, json: async () => f.realm(body)});
  w.fetch = async (input, options = {}) => {
    const url = new w.URL(String(input), w.location.href);
    f.fetchCalls.push({pathname: url.pathname, method: options.method || 'GET', body: options.body ? JSON.parse(options.body) : null});
    if (url.pathname === '/assets/archive-index.json') return f.response(index);
    return f.response({ok: false}, 404);
  };
  w.BroadcastChannel = class {
    constructor(name) {
      this.name = group + ':' + name; this.closed = false; this.listeners = new Set();
      if (!channels.has(this.name)) channels.set(this.name, new Set());
      channels.get(this.name).add(this);
    }
    addEventListener(type, listener) { if (type === 'message') this.listeners.add(listener); }
    removeEventListener(type, listener) { if (type === 'message') this.listeners.delete(listener); }
    deliver(serialized) {
      if (this.closed) return;
      const event = {data: f.realm(JSON.parse(serialized))};
      this.onmessage?.(event);
      for (const listener of this.listeners) listener(event);
    }
    postMessage(frame) {
      if (this.closed) throw Error('Closed channel');
      const serialized = JSON.stringify(frame);
      for (const peer of channels.get(this.name) || []) if (peer !== this && !peer.closed) queueMicrotask(() => peer.deliver(serialized));
    }
    close() { this.closed = true; channels.get(this.name)?.delete(this); }
  };
  const viewer = new vm.SyntheticModule(['createViewer', 'inspectSTL'], function() {
    this.setExport('createViewer', async () => ({loadSTL: () => ({dims: [20,20,20], triangles: 12}), showDemo() {}, reset() {}, explode: () => true, setWireframe() {}, setAutoRotate() {}, setMotion() {}, setSection() {}, dispose() {}}));
    this.setExport('inspectSTL', () => ({dims: [20,20,20], triangles: 12}));
  }, {context});
  await viewer.link(() => {}); await viewer.evaluate();
  function moduleFor(filename) {
    filename = path.resolve(filename);
    if (f.modules.has(filename)) return f.modules.get(filename);
    const mod = new vm.SourceTextModule(fs.readFileSync(filename, 'utf8'), {
      context, identifier: filename,
      importModuleDynamically: async (specifier, parent) => {
        const target = path.resolve(path.dirname(parent.identifier), specifier);
        return target === path.join(dist, 'lib/viewer.js') ? viewer : f.load(target);
      }
    });
    f.modules.set(filename, mod);
    return mod;
  }
  f.load = async filename => {
    const mod = moduleFor(filename);
    if (mod.status === 'unlinked') await mod.link((specifier, parent) => moduleFor(path.resolve(path.dirname(parent.identifier), specifier)));
    if (mod.status !== 'evaluated') await mod.evaluate();
    return mod;
  };
  f.$ = selector => w.document.querySelector(selector);
  f.$$ = selector => [...w.document.querySelectorAll(selector)];
  f.click = async selector => { const element = f.$(selector); assert(element, name + ': missing ' + selector); element.click(); await settle(); };
  f.submit = async selector => { const form = f.$(selector); assert(form, name + ': missing ' + selector); form.dispatchEvent(new w.Event('submit', {bubbles: true, cancelable: true})); await settle(); };
  f.input = async (selector, value) => { const element = f.$(selector); assert(element, name + ': missing ' + selector); element.value = String(value); element.dispatchEvent(new w.Event('input', {bubbles: true})); await settle(); };
  f.selectProject = async id => { const picker = f.$('#project-picker'); assert(picker); picker.value = id; assert.equal(picker.value, id); picker.dispatchEvent(new w.Event('change', {bubbles: true})); await settle(); };
  if (app) { f.app = await f.load(path.join(dist, 'app.js')); await settle(); }
  const storeModule = await f.load(path.join(dist, 'lib/workshop.js'));
  f.store = new storeModule.namespace.WorkshopStore(); f.stores.push(f.store);
  f.business = (await f.load(path.join(dist, 'lib/edit-plan.js'))).namespace;
  f.catalog = (await f.load(path.join(dist, 'lib/content-catalog.js'))).namespace;
  f.project = id => { f.store.refresh(); return f.store.state.projects.find(project => project.id === id); };
  f.act = (type, payload) => {
    if (type === 'SAVE_EDIT_PLAN' && !Object.hasOwn(payload, 'expectedVersionId')) {
      const record = f.project(payload.projectId)?.contentPlans?.find(record => record.id === payload.planId);
      payload = {...payload, expectedVersionId: payload.expectedRevision === 0 ? null : record?.versions.find(version => version.revision === payload.expectedRevision)?.operationId};
    }
    const result = f.store.dispatch(type, f.realm(payload));
    assert.equal(result.ok, true, result.message);
    return clone(result);
  };
  f.journal = () => clone(f.store.exportJournal());
  f.merge = journal => f.store.mergeJournal(f.realm(journal));
  f.draft = (id, series = 'oeuvres') => clone(f.business.createEditDraft(f.project(id), series));
  return f;
}

async function readDownload(f, download = f.downloads.at(-1)) {
  assert(download?.blob, 'An actual JSON Blob is downloaded');
  const text = await new Promise((resolve, reject) => {
    const reader = new f.w.FileReader();
    reader.onload = () => resolve(reader.result); reader.onerror = () => reject(reader.error);
    reader.readAsText(download.blob);
  });
  return JSON.parse(text);
}

async function check(id, description, task) {
  try { await task(); checks.push({id, status: 'passed', description}); }
  catch (error) { checks.push({id, status: 'failed', description, error: error.stack}); }
}

async function runBusinessChecks() {
  await check('catalogue-source-identities', 'The static catalogue preserves all 31 original IDs, publication URLs, availability and the separation of full-media duration from local preview intervals.', async () => {
    const f = await surface('catalogue');
    assert.equal(f.catalog.CONTENT_CATALOG.length, index.length);
    assert.equal(index.length, 31);
    assert.equal(new Set(f.catalog.CONTENT_CATALOG.map(source => source.id)).size, index.length);
    for (const item of index) {
      const source = f.catalog.getContentSource(item.id);
      assert(source, 'Missing source ' + item.id);
      for (const key of ['id', 'url', 'title', 'type', 'available']) assert.equal(source[key], item[key], item.id + ': ' + key);
      assert.equal(source.duration, item.type === 'video' && Number.isFinite(item.duration) && item.duration > 0 ? item.duration : null);
      assert.equal(source.preview, item.preview || null);
      assert.equal(source.previewStart, item.preview ? item.previewStart : null);
      assert.equal(source.previewSeconds, item.preview ? item.previewSeconds : null);
      if (source.preview) {
        assert(source.previewStart + source.previewSeconds <= source.duration + 0.001);
        assert(fs.existsSync(path.resolve(dist, source.preview)), 'Preview file exists for ' + item.id);
      }
    }
    const baki = f.catalog.getContentSource('7464268707989114134');
    assert.match(baki.title, /60 cm/);
    assert.equal(baki.previewStart, 4);
    assert.equal(baki.previewSeconds, 6);
    assert.equal(f.catalog.getContentSource('invented-source'), null);
    assert.equal(f.fetchCalls.length, 0);
  });

  await check('explicit-reference-no-proof', 'Every editorial series starts without media; choosing the Baki 60 cm publication remains an explicit visual reference in the Sculpture XL 1 m dossier.', async () => {
    const f = await surface('references');
    const project = f.project('sculpture-xl');
    assert.equal(project.height, 1000);
    for (const series of f.business.EDIT_SERIES) {
      const draft = clone(f.business.createEditDraft(project, series.id));
      assert.equal(draft.sources.length, 0);
      assert(draft.beats.every(beat => beat.postId === null && beat.in === null && beat.out === null));
      assert(!index.some(source => JSON.stringify(draft).includes(source.id)));
    }
    const plan = f.draft('sculpture-xl');
    plan.sources.push({postId: '7464268707989114134', relation: 'reference'});
    Object.assign(plan.beats[0], {postId: '7464268707989114134', in: 4, out: 10});
    f.act('SAVE_EDIT_PLAN', {projectId: 'sculpture-xl', planId: 'explicit-reference', expectedRevision: 0, plan});
    const current = f.project('sculpture-xl');
    const exported = clone(f.business.exportEditPlan(current, current.contentPlans[0]));
    assert.equal(exported.sourceMetadata[0].relation, 'reference');
    assert.equal(exported.sourceMetadata[0].relationBasis, 'visual_reference');
    assert.match(exported.sourceMetadata[0].title, /60 cm/);
    assert.equal(exported.plan.beats[0].in, 4);
    assert.equal(exported.plan.beats[0].out, 10);
    assert.equal(exported.sourceMetadata[0].previewSeconds, 6);
    assert.equal(exported.sourceMetadata[0].duration, 36.433333);
    assert.match(exported.declarations.sourceRelation, /sans preuve automatique/);
    assert.deepEqual(exported.execution, {renderRequested: false, publicationRequested: false, renderedFile: null});
    const before = f.storage.snapshot();
    const invented = clone(plan);
    invented.sources[0].postId = 'unknown-post'; invented.beats[0].postId = 'unknown-post';
    const failed = f.store.dispatch('SAVE_EDIT_PLAN', f.realm({projectId: 'sculpture-xl', planId: 'invented', expectedRevision: 0, expectedVersionId: null, plan: invented}));
    assert.equal(failed.ok, false);
    assert.equal(f.storage.snapshot(), before, 'An invalid source cannot enter the persisted journal');
    assert.equal(f.fetchCalls.length, 0);
  });

  await check('versions-and-export-target', 'Saved versions are append-only, keep historical dossier names and export their explicit target after another dossier becomes active; quote, story and project revision remain intact.', async () => {
    const f = await surface('versions');
    f.act('SAVE_STORY', {projectId: 'sculpture-xl', text: 'Scénario indépendant du plan d’édit.'});
    f.act('SAVE_QUOTE', {projectId: 'sculpture-xl', inputs: {material: 100, hours: 2, rate: 50, other: 40, margin: 30, fee: 0, quantity: 1}});
    const before = clone(f.project('sculpture-xl'));
    const plan = f.draft('sculpture-xl'); plan.title = 'Le geste — première version';
    f.act('SAVE_EDIT_PLAN', {projectId: 'sculpture-xl', planId: 'versioned-plan', expectedRevision: 0, plan});
    const originalVersion = clone(f.project('sculpture-xl').contentPlans[0].versions[0]);
    f.act('UPDATE_PROJECT', {id: 'sculpture-xl', patch: {name: 'Dossier Sculpture XL renommé'}});
    f.act('SELECT_PROJECT', {id: 'prototype'});
    const second = clone(plan); second.title = 'Le geste — seconde version'; second.caption = 'Texte de légende conservé en version 2.';
    f.act('SAVE_EDIT_PLAN', {projectId: 'sculpture-xl', planId: 'versioned-plan', expectedRevision: 1, plan: second});
    const current = f.project('sculpture-xl'), record = current.contentPlans[0];
    assert.equal(f.store.state.projectId, 'prototype', 'Saving a plan does not switch the active dossier');
    assert.deepEqual(clone(record.versions[0]), originalVersion);
    assert.equal(record.versions.length, 2);
    assert.equal(record.versions[1].revision, 2);
    assert.equal(current.revision, before.revision);
    assert.deepEqual(clone(current.quote), before.quote);
    assert.equal(current.story, before.story);
    assert.deepEqual(clone(current.pieces), before.pieces);
    const v1 = clone(f.business.exportEditPlan(current, record, 1));
    assert.equal(v1.project.id, 'sculpture-xl');
    assert.equal(v1.project.name, before.name);
    assert.equal(v1.project.currentName, 'Dossier Sculpture XL renommé');
    assert.equal(v1.version.revision, 1);
    assert.equal(v1.version.operationId, originalVersion.operationId);
    assert.equal(v1.plan.title, plan.title);
    const v2 = clone(f.business.exportEditPlan(current, record, 2));
    assert.equal(v2.project.name, 'Dossier Sculpture XL renommé');
    assert.equal(v2.plan.caption, second.caption);
    assert.throws(() => f.business.exportEditPlan(f.project('prototype'), record, 1), /dossier/i);
    const foreign = clone(record.versions[0]); foreign.plan.title = 'Une autre version, non conservée.';
    assert.throws(() => f.business.exportEditPlan(current, record, f.realm(foreign)), /version|état/i);
    const saveOperation = f.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').at(-1);
    assert.equal(saveOperation.payload.projectId, 'sculpture-xl');
    assert.equal(saveOperation.context.projectId, 'sculpture-xl');
    assert.equal(saveOperation.context.originProjectId, 'prototype');
    const beforeInvalid = f.storage.snapshot();
    const stale = f.store.dispatch('SAVE_EDIT_PLAN', f.realm({projectId: 'sculpture-xl', planId: 'versioned-plan', expectedRevision: 1, expectedVersionId: originalVersion.operationId, plan}));
    assert.equal(stale.ok, false);
    assert.equal(f.storage.snapshot(), beforeInvalid, 'A stale edit does not append a new operation');
    const malformedJournal = f.journal();
    const wrongTarget = malformedJournal.operations.find(operation => operation.type === 'SAVE_EDIT_PLAN');
    wrongTarget.id = 'wrong-target-import';
    wrongTarget.clock = Math.max(...malformedJournal.operations.map(operation => operation.clock)) + 1;
    wrongTarget.context.projectId = 'prototype';
    assert.throws(() => f.merge(malformedJournal));
    assert.equal(f.storage.snapshot(), beforeInvalid, 'Target disagreement cannot alter the journal');
  });

  await check('concurrent-plan-conflict', 'Two windows editing the same first revision converge to one saved version; the conflicting operation remains auditable and no existing plan is erased.', async () => {
    const a = await surface('conflict-a'), b = await surface('conflict-b');
    const first = a.draft('sculpture-xl'), second = b.draft('sculpture-xl');
    first.title = 'Proposition depuis la fenêtre A'; second.title = 'Proposition depuis la fenêtre B';
    a.act('SAVE_EDIT_PLAN', {projectId: 'sculpture-xl', planId: 'same-plan', expectedRevision: 0, plan: first});
    b.act('SAVE_EDIT_PLAN', {projectId: 'sculpture-xl', planId: 'same-plan', expectedRevision: 0, plan: second});
    const merged = a.merge(b.journal());
    assert.equal(merged.rejected.length, 1);
    b.merge(a.journal());
    const stateA = clone(a.project('sculpture-xl').contentPlans), stateB = clone(b.project('sculpture-xl').contentPlans);
    assert.deepEqual(stateA, stateB);
    assert.equal(stateA.length, 1); assert.equal(stateA[0].versions.length, 1);
    const operations = a.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').sort((left, right) => left.clock - right.clock || left.id.localeCompare(right.id));
    assert.equal(operations.length, 2);
    assert.equal(stateA[0].versions[0].plan.title, operations[0].payload.plan.title);
    assert.equal(a.store.state.journal.filter(entry => entry.type === 'SAVE_EDIT_PLAN' && entry.ok === false).length, 1);
    assert.equal(a.merge(b.journal()).added, 0, 'Repeated synchronization remains idempotent');
  });

  await check('plan-sqlite-roundtrip', 'Two complete plan versions and their source identities survive browser backup, reopened SQLite and additive restoration alongside an unrelated local story.', async () => {
    const f = await surface('backup-source');
    const plan = f.draft('sculpture-xl');
    plan.title = 'Plan conservé hors de la fenêtre';
    plan.sources = [{postId: '7464268707989114134', relation: 'reference'}];
    Object.assign(plan.beats[1], {postId: '7464268707989114134', in: 4, out: 10, note: 'Geste de peinture pris comme référence.'});
    f.act('SAVE_EDIT_PLAN', {projectId: 'sculpture-xl', planId: 'backup-plan', expectedRevision: 0, plan});
    plan.caption = 'Nouvelle légende, même provenance explicite.';
    f.act('SAVE_EDIT_PLAN', {projectId: 'sculpture-xl', planId: 'backup-plan', expectedRevision: 1, plan});
    const expected = clone(f.project('sculpture-xl').contentPlans);
    const backupModule = (await f.load(path.join(dist, 'lib/workshop-backup.js'))).namespace;
    const backup = clone(await backupModule.createWorkshopBackup(f.realm(f.journal())));
    const {createWorkshopRepository} = await import(pathToFileURL(path.join(root, 'local/workshop-repository.mjs')).href);
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'bojart-project-studio-qa-')); directories.add(directory);
    const database = createWorkshopRepository({directory}); databases.add(database);
    const restored = database.restore(backup);
    assert.equal(restored.ok, true); assert.equal(restored.operationCount, 2);
    const instanceId = database.status().instanceId;
    database.close(); databases.delete(database);
    const reopened = createWorkshopRepository({directory}); databases.add(reopened);
    assert.equal(reopened.status().instanceId, instanceId);
    assert.equal(reopened.status().operationCount, 2);
    const destination = await surface('backup-destination');
    destination.act('SAVE_STORY', {projectId: 'prototype', text: 'Brouillon local indépendant à préserver.'});
    const inspected = await (await destination.load(path.join(dist, 'lib/workshop-backup.js'))).namespace.inspectWorkshopBackup(JSON.stringify(reopened.backup()));
    const merge = destination.merge(clone(inspected.journal));
    assert.equal(merge.added, 2); assert.equal(merge.rejected.length, 0);
    assert.deepEqual(clone(destination.project('sculpture-xl').contentPlans), expected);
    assert.equal(destination.project('prototype').story, 'Brouillon local indépendant à préserver.');
    assert.equal(destination.journal().operations.length, 3);
    assert.equal(destination.merge(clone(inspected.journal)).added, 0);
  });
}

async function runApplicationChecks() {
  const storage = new Storage();
  const center = await surface('ui-center', {storage, group: 'ui-workshop', role: 'pilotage', panel: 'contenus', app: true});
  const left = await surface('ui-left', {storage, group: 'ui-workshop', role: 'atelier', app: true});
  const right = await surface('ui-right', {storage, group: 'ui-workshop', role: 'creation', app: true});
  await settle();
  const formSelector = '[data-project-studio-form]';
  const field = name => `${formSelector} [name="${name}"]`;
  let firstPlanId = null, firstVersion = null, remoteVersion = null;

  await check('ui-route-and-empty-draft', 'The project Studio route opens on the explicit XL dossier without associating a publication or announcing a rendered project film.', async () => {
    assert(center.$('#drawer').open);
    assert(center.$('[data-project-studio]'));
    const form = center.$(formSelector);
    assert(form);
    assert.equal(form.dataset.projectId, 'sculpture-xl');
    assert.equal(center.$('#main').dataset.screen, 'pilotage');
    assert.equal(center.$('[data-ps-preview-video]'), null);
    assert.equal(center.$('[data-ps-export]').disabled, true, 'An unsaved plan cannot be exported as a recorded version');
    assert.equal(center.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').length, 0);
    assert(center.$('link[href="./project-studio.css"]'));
  });

  await check('ui-source-preview-preserves-text', 'Choosing a real archive preview and editing its original interval keeps the creative brief and caption untouched; source relation remains an explicit reference.', async () => {
    const form = center.$(formSelector);
    await center.input(field('title'), 'Peinture en référence — dossier XL');
    await center.input(field('brief'), 'Conserver ma saisie <atelier> même pendant la consultation d’une publication.');
    await center.input(field('caption'), 'Légende de travail, ni vidéo rendue ni annonce de fabrication.');
    await center.click('[data-ps-beat="geste"]');
    await center.click('[data-ps-library-open]');
    await center.input('[data-ps-search]', '7464268707989114134');
    await center.click('[data-ps-choose-source="7464268707989114134"]');
    assert.equal(center.$(formSelector), form, 'Browsing a source must not replace the editing form');
    assert.equal(center.$(field('brief')).value, 'Conserver ma saisie <atelier> même pendant la consultation d’une publication.');
    assert.equal(center.$(field('caption')).value, 'Légende de travail, ni vidéo rendue ni annonce de fabrication.');
    const video = center.$('[data-ps-preview-video]');
    assert(video);
    assert(video.src.endsWith('/assets/archive/7464268707989114134.mp4'));
    assert.equal(video.hasAttribute('autoplay'), false);
    assert.equal(center.mediaState(video).playCalls, 0);
    const timebase = center.$('[data-ps-preview-timebase]').textContent;
    assert(timebase.includes('Aperçu local :') && timebase.includes('0–6 s'), timebase);
    assert(timebase.includes('Dans l’original :') && timebase.includes('4–10 s'), timebase);
    assert.equal(center.$('[name="sourceRelation"]').value, 'reference');
    await center.input('[name="beatIn"]', '4');
    await center.input('[name="beatOut"]', '10');
    video.currentTime = 2;
    video.dispatchEvent(new center.w.Event('timeupdate'));
    assert.equal(center.$('[name="beatIn"]').value, '4');
    assert.equal(center.$('[name="beatOut"]').value, '10', 'Reading the preview must not rewrite original-media cut points');
    assert.match(center.$('[data-project-studio]').textContent, /60 cm/);
  });

  await check('ui-save-captured-target', 'After another screen selects Prototype, the unchanged form saves to its original XL dossier and all three screens keep their display roles.', async () => {
    const form = center.$(formSelector);
    const brief = center.$(field('brief')).value;
    await right.selectProject('prototype');
    assert.equal(center.$('#project-picker').value, 'prototype');
    assert.equal(center.$(formSelector), form);
    assert.equal(center.$(field('brief')).value, brief);
    assert.equal(form.dataset.projectId, 'sculpture-xl');
    const context = center.$('[data-ps-context]');
    assert(context && context.textContent.trim().length > 0, 'The original target is visible after a remote selection');
    await center.click('[data-ps-save]');
    const source = center.project('sculpture-xl');
    assert.equal(source.contentPlans.length, 1);
    firstPlanId = source.contentPlans[0].id;
    firstVersion = clone(source.contentPlans[0].versions[0]);
    assert.equal(firstVersion.plan.title, 'Peinture en référence — dossier XL');
    assert.equal(firstVersion.plan.brief, brief);
    assert.equal(firstVersion.plan.sources.length, 1);
    assert.deepEqual(clone(firstVersion.plan.sources[0]), {postId: '7464268707989114134', relation: 'reference'});
    const beat = firstVersion.plan.beats.find(beat => beat.id === 'geste');
    assert.equal(beat.postId, '7464268707989114134'); assert.equal(beat.in, 4); assert.equal(beat.out, 10);
    assert.equal(center.business.projectEditPlans(center.project('prototype')).length, 0);
    assert.equal(center.$(formSelector).dataset.planId, firstPlanId);
    assert.equal(center.$(formSelector).dataset.revision, '1');
    assert.equal(center.$('[data-ps-export]').disabled, false, 'Own save acknowledgement must clear draft/stale state');
    assert.equal(center.$('#project-picker').value, 'prototype');
    assert.equal(left.$('#main').dataset.screen, 'atelier');
    assert.equal(center.$('#main').dataset.screen, 'pilotage');
    assert.equal(right.$('#main').dataset.screen, 'creation');
    const downloadCount = center.downloads.length;
    await center.click('[data-ps-export]');
    assert.equal(center.downloads.length, downloadCount + 1);
    const exported = await readDownload(center);
    assert.equal(exported.format, 'bojart.project-edit-plan.v1');
    assert.equal(exported.project.id, 'sculpture-xl');
    assert.equal(exported.recordId, firstPlanId);
    assert.equal(exported.version.revision, 1);
    assert.equal(exported.version.operationId, firstVersion.operationId);
    assert.equal(exported.plan.brief, brief);
    assert.equal(exported.execution.renderRequested, false);
    assert.equal(exported.execution.publicationRequested, false);
  });

  await check('ui-stale-edit-keeps-draft', 'A competing saved revision preserves the local unsaved text, blocks exporting that draft and refuses an obsolete save without overwriting the retained history.', async () => {
    assert(firstPlanId);
    await center.input(field('brief'), 'Mon texte encore non enregistré reste visible après la version distante.');
    const form = center.$(formSelector);
    const other = clone(firstVersion.plan);
    other.title = 'Version concurrente conservée depuis l’écran droit';
    other.caption = 'Légende enregistrée par l’autre fenêtre.';
    right.act('SAVE_EDIT_PLAN', {projectId: 'sculpture-xl', planId: firstPlanId, expectedRevision: 1, plan: other});
    await settle();
    remoteVersion = clone(center.project('sculpture-xl').contentPlans[0].versions[1]);
    assert.equal(center.$(formSelector), form);
    assert.equal(center.$(field('brief')).value, 'Mon texte encore non enregistré reste visible après la version distante.');
    assert(center.$('[data-ps-context]').textContent.trim().length > 0);
    assert.equal(center.$('[data-ps-export]').disabled, true);
    const count = center.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').length;
    await center.submit(formSelector);
    assert.equal(center.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').length, count);
    assert.equal(center.project('sculpture-xl').contentPlans[0].versions.length, 2);
    assert.equal(center.$(field('brief')).value, 'Mon texte encore non enregistré reste visible après la version distante.');
    const history = center.$('[data-ps-history]'), draftKey = history.value;
    assert(draftKey.startsWith('draft:'));
    history.value = '1';
    history.dispatchEvent(new center.w.Event('change', {bubbles: true}));
    await settle();
    assert.equal(center.$(field('brief')).value, firstVersion.plan.brief);
    history.value = draftKey;
    history.dispatchEvent(new center.w.Event('change', {bubbles: true}));
    await settle();
    assert.equal(center.$(field('brief')).value, 'Mon texte encore non enregistré reste visible après la version distante.', 'Consulting history keeps the local draft available');
    assert.equal(center.$(formSelector).dataset.revision, '1', 'Returning to a draft does not silently rebase it');
  });

  await check('ui-recorded-history-and-resume', 'An old saved version is read-only and exports unchanged; explicit resume creates revision 3 from it while preserving both preceding versions.', async () => {
    assert(firstPlanId && remoteVersion);
    await center.click('#drawer [data-action="close-dialog"]');
    await right.selectProject('sculpture-xl');
    await center.click('[data-action="project-studio"]');
    const history = center.$('[data-ps-history]');
    assert(history);
    history.value = '1';
    history.dispatchEvent(new center.w.Event('change', {bubbles: true}));
    await settle();
    assert.equal(center.$(field('title')).value, firstVersion.plan.title);
    assert(center.$(field('title')).readOnly || center.$(field('title')).disabled);
    assert.equal(center.$('[data-ps-save]').disabled, true);
    const before = center.downloads.length;
    await center.click('[data-ps-export]');
    assert.equal(center.downloads.length, before + 1);
    const exported = await readDownload(center);
    assert.equal(exported.project.id, 'sculpture-xl');
    assert.equal(exported.version.revision, 1);
    assert.deepEqual(exported.plan, firstVersion.plan);
    await center.click('[data-ps-resume]');
    assert.equal(center.$(formSelector).dataset.revision, '2');
    assert.equal(center.$(field('brief')).value, firstVersion.plan.brief);
    assert.equal(center.$(field('brief')).disabled, false);
    assert.equal(center.$(field('brief')).readOnly, false);
    await center.input(field('brief'), 'Reprise explicite de la première version, conservée en version 3.');
    await center.click('[data-ps-save]');
    const versions = center.project('sculpture-xl').contentPlans[0].versions;
    assert.equal(versions.length, 3);
    assert.deepEqual(clone(versions[0]), firstVersion);
    assert.deepEqual(clone(versions[1]), remoteVersion);
    assert.equal(versions[2].revision, 3);
    assert.equal(versions[2].plan.brief, 'Reprise explicite de la première version, conservée en version 3.');
  });

  await check('ui-dispose-and-no-external-action', 'Opening another panel disposes the project Studio so retained DOM cannot save/export again; plan work invokes no API write, render, cloud or social publication.', async () => {
    const view = center.$('[data-project-studio]'), form = center.$(formSelector);
    assert(view && form);
    await center.click('[data-ps-beat="geste"]');
    await center.click('[data-ps-editor] [data-ps-preview-source="7464268707989114134"]');
    const video = center.$('[data-ps-preview-video]');
    assert(video);
    await video.play();
    const operationCount = center.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').length;
    const downloadCount = center.downloads.length;
    await center.click('[data-action="studio"]');
    assert(center.$('.studio-view'));
    assert.equal(center.$('[data-project-studio]'), null);
    assert.equal(video.paused, true);
    for (const event of ['click', 'input', 'change', 'submit']) assert.equal(center.listenerCount(view, event), 0, 'Disposed root listener: ' + event);
    form.dispatchEvent(new center.w.Event('submit', {bubbles: true, cancelable: true}));
    view.querySelector('[data-ps-export]')?.click();
    await settle();
    assert.equal(center.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').length, operationCount);
    assert.equal(center.downloads.length, downloadCount);
    assert.equal([center, left, right].flatMap(f => f.fetchCalls).filter(call => call.method !== 'GET').length, 0);
    for (const f of [center, left, right]) assert.equal(f.errors.length, 0, f.errors.join('\n'));
    assert.equal(center.$('#main').dataset.screen, 'pilotage');
  });

  await check('ui-same-revision-divergence', 'An offline journal merge that changes the winning content of revision 1 cannot silently export or save the formerly displayed revision; explicit rebase preserves the draft and produces revision 2.', async () => {
    const f = await surface('ui-same-revision', {panel: 'contenus', app: true});
    await f.input(`${formSelector} [name="title"]`, 'Version locale affichée avant fusion');
    await f.input(`${formSelector} [name="brief"]`, 'Ma proposition locale reste visible si une autre branche gagne.');
    await f.click('[data-ps-save]');
    const source = f.project('sculpture-xl'), record = source.contentPlans[0];
    assert.equal(record.versions.length, 1);
    assert.equal(f.$('[data-ps-export]').disabled, false);
    const initialForm = f.$(formSelector), initialTitle = f.$(`${formSelector} [name="title"]`).value;
    const localOperation = f.journal().operations.find(operation => operation.type === 'SAVE_EDIT_PLAN');
    const competing = clone(localOperation);
    competing.id = '000-offline-creation-branch';
    competing.payload.plan.title = 'Contenu gagnant arrivé depuis le journal hors ligne';
    competing.payload.plan.brief = 'Autre proposition à la même révision numérique.';
    assert(competing.id < localOperation.id, 'The replay tie-break deterministically places the offline branch first');
    const merged = f.merge({version: 1, seed: f.journal().seed, operations: [competing]});
    assert.equal(merged.rejected.length, 1);
    await settle();
    const winning = clone(f.project('sculpture-xl').contentPlans[0].versions[0]);
    assert.equal(winning.revision, 1);
    assert.equal(winning.plan.title, competing.payload.plan.title);
    assert.equal(f.$(formSelector), initialForm);
    assert.equal(f.$(`${formSelector} [name="title"]`).value, initialTitle);
    assert.equal(f.$('[data-ps-context]').hidden, false, 'Same revision with different content must surface a conflict');
    assert.equal(f.$('[data-ps-export]').disabled, true, 'The displayed old content must not export the newly winning V1');
    const savesBefore = f.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').length;
    await f.submit(formSelector);
    assert.equal(f.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').length, savesBefore, 'Identical revision numbers do not authorize an implicit rebase');
    await f.click('[data-ps-rebase]');
    assert.equal(f.$(`${formSelector} [name="title"]`).value, initialTitle);
    await f.click('[data-ps-save]');
    const versions = f.project('sculpture-xl').contentPlans[0].versions;
    assert.equal(versions.length, 2);
    assert.deepEqual(clone(versions[0]), winning);
    assert.equal(versions[1].revision, 2);
    assert.equal(versions[1].plan.title, initialTitle);
    assert.equal(f.$('[data-ps-export]').disabled, false);
    assert.equal(f.fetchCalls.filter(call => call.method !== 'GET').length, 0);
    assert.equal(f.errors.length, 0, f.errors.join('\n'));
  });

  await check('ui-unnotified-base-change', 'Save and export reject a changed base operation even before its storage notification reaches the form, preserving its text and exposing the updated conflict for explicit rebase.', async () => {
    for (const action of ['save', 'export']) {
      const f = await surface('ui-unnotified-' + action, {panel: 'contenus', app: true});
      await f.input(`${formSelector} [name="title"]`, 'V1 locale — course ' + action);
      await f.click('[data-ps-save]');
      const originalForm = f.$(formSelector), originalTitle = f.$(`${formSelector} [name="title"]`).value;
      const original = f.journal().operations.find(operation => operation.type === 'SAVE_EDIT_PLAN');
      assert(original);
      assert.equal(originalForm.dataset.expectedVersionId, original.id);
      if (action === 'save') await f.input(`${formSelector} [name="brief"]`, 'Texte saisi avant la notification différée, à conserver.');
      const brief = f.$(`${formSelector} [name="brief"]`).value;
      const competing = clone(original);
      competing.id = '000-unnotified-branch-' + action;
      competing.payload.plan.title = 'Autre V1 déjà présente dans le stockage';
      assert(competing.id < original.id);
      // Simulate the interval between another window's storage write and the
      // asynchronous storage/BroadcastChannel notification. Do not refresh here.
      f.storage.setItem('bojart.workshop.v1.op.' + competing.id, JSON.stringify(competing));
      assert.equal(f.$('[data-ps-context]').hidden, true, 'The form has not observed the other operation yet');
      const downloadCount = f.downloads.length;
      if (action === 'save') await f.submit(formSelector);
      else await f.click('[data-ps-export]');
      assert.equal(f.$(formSelector), originalForm);
      assert.equal(f.$(`${formSelector} [name="title"]`).value, originalTitle);
      assert.equal(f.$(`${formSelector} [name="brief"]`).value, brief);
      assert.equal(f.downloads.length, downloadCount, 'A stale recorded identity is not downloaded');
      assert.equal(f.journal().operations.filter(operation => operation.type === 'SAVE_EDIT_PLAN').length, 2, 'No implicit save follows a changed base operation');
      const versions = f.project('sculpture-xl').contentPlans[0].versions;
      assert.equal(versions.length, 1);
      assert.equal(versions[0].operationId, competing.id);
      assert.equal(versions[0].plan.title, competing.payload.plan.title);
      assert.equal(f.$('[data-ps-message]').dataset.tone, 'error');
      assert.equal(f.$('[data-ps-context]').hidden, false, 'The failed action refreshes its target context so recovery is available');
      assert(f.$('[data-ps-rebase]'));
      assert.equal(f.fetchCalls.filter(call => call.method !== 'GET').length, 0);
      assert.equal(f.errors.length, 0, f.errors.join('\n'));
    }
  });
}

(async () => {
  try {
    await runBusinessChecks();
    if (!businessOnly) await runApplicationChecks();
  } finally {
    for (const f of fixtures) {
      for (const store of f.stores) store.dispose();
      f.w.dispatchEvent(new f.w.Event('pagehide'));
      f.closed = true; f.w.close();
    }
    for (const database of databases) database.close();
    for (const directory of directories) fs.rmSync(directory, {recursive: true, force: true});
  }
  const failed = checks.filter(check => check.status === 'failed');
  const report = {
    status: failed.length || checks.length === 0 ? 'failed' : 'passed', checkedAt: new Date().toISOString(), mode: businessOnly ? 'business-only' : 'complete-integration', checks,
    browserRenderingVerified: false, mediaDecodingVerified: false, networkUsed: false,
    scope: 'Real app, project Studio, business model, backup validator and SQLite repository in isolated fixtures; no browser engine, preview server, renderer or external service.'
  };
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  if (report.status !== 'passed') process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
