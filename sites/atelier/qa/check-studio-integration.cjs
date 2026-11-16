// Targeted integration of the real application with the real Studio module.
// No browser, media decoder, renderer, network socket or external service is used.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {JSDOM} = require('jsdom');

const dist = path.resolve(__dirname, '../dist');
const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
const reportPath = path.join(__dirname, 'studio-integration-results.json');
const surfaces = [], checks = [], errors = [], channels = new Map();
const storageData = new Map();
const storage = {
  get length() { return storageData.size; },
  key: i => [...storageData.keys()][i] ?? null,
  getItem: key => storageData.get(key) ?? null,
  setItem: (key, value) => storageData.set(key, String(value)),
  removeItem: key => storageData.delete(key)
};
const tick = () => new Promise(resolve => setImmediate(resolve));
async function settle() { await tick(); await tick(); await tick(); }

async function createSurface(role, panel = '') {
  const dom = new JSDOM(html, {
    url: `https://bojart.test/?screen=${role}&station=${role}&immersive=1${panel ? '&panel=' + panel : ''}`,
    runScripts: 'outside-only', pretendToBeVisual: true
  });
  const w = dom.window, context = dom.getInternalVMContext();
  const surface = {role, dom, w, modules: new Map(), fetchCalls: [], frames: [], downloads: [], objectURLs: new Map(), revokedURLs: [], reducedMotion: false};
  surfaces.push(surface);
  Object.defineProperty(w, 'localStorage', {value: storage});
  w.scrollTo = () => {};
  w.TextDecoder = TextDecoder;
  w.TextEncoder = TextEncoder;
  w.HTMLCanvasElement.prototype.getContext = () => null;

  // Keep native EventTarget delivery while observing media listener disposal.
  const listenerRecords = new WeakMap();
  const add = w.EventTarget.prototype.addEventListener;
  const remove = w.EventTarget.prototype.removeEventListener;
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
  surface.listenerCount = (target, type) => (listenerRecords.get(target)?.get(type + ':false')?.size || 0) + (listenerRecords.get(target)?.get(type + ':true')?.size || 0);

  const preferences = [];
  w.matchMedia = query => {
    const preference = new w.EventTarget();
    Object.defineProperties(preference, {matches: {get: () => surface.reducedMotion}, media: {value: query}});
    preferences.push(preference);
    return preference;
  };
  surface.setReducedMotion = async value => {
    surface.reducedMotion = value;
    for (const preference of preferences) {
      const event = new w.Event('change');
      Object.defineProperty(event, 'matches', {value});
      preference.dispatchEvent(event);
    }
    await settle();
  };
  let frameId = 0;
  const animationFrames = new Map();
  w.requestAnimationFrame = callback => { const id = ++frameId; animationFrames.set(id, callback); return id; };
  w.cancelAnimationFrame = id => animationFrames.delete(id);
  surface.pendingAnimationFrames = () => animationFrames.size;

  // Media behavior is deterministic; decoding and visual quality are not asserted.
  const mediaStates = new WeakMap();
  surface.mediaState = element => {
    if (!mediaStates.has(element)) mediaStates.set(element, {paused: true, playCalls: 0, pauseCalls: 0});
    return mediaStates.get(element);
  };
  Object.defineProperties(w.HTMLMediaElement.prototype, {
    paused: {get() { return surface.mediaState(this).paused; }},
    ended: {get() { return false; }},
    duration: {get() { return this.src.includes('brand-film-') ? 22.7 : 18.8; }},
    readyState: {get() { return 4; }}
  });
  w.HTMLMediaElement.prototype.play = async function() {
    const state = surface.mediaState(this);
    state.playCalls++;
    state.paused = false;
    this.dispatchEvent(new w.Event('play'));
  };
  w.HTMLMediaElement.prototype.pause = function() {
    const state = surface.mediaState(this);
    state.pauseCalls++;
    if (!state.paused) { state.paused = true; this.dispatchEvent(new w.Event('pause')); }
  };
  w.HTMLDialogElement.prototype.showModal = function() { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function() {
    if (!this.open) return;
    this.removeAttribute('open');
    // Native close dispatch is queued; this exposes the rapid-reopen race.
    setImmediate(() => { if (!surface.closed) this.dispatchEvent(new w.Event('close')); });
  };
  let urlId = 0;
  w.URL.createObjectURL = blob => {
    const url = `blob:https://bojart.test/${role}-${++urlId}`;
    surface.objectURLs.set(url, blob);
    return url;
  };
  w.URL.revokeObjectURL = url => { surface.revokedURLs.push(url); surface.objectURLs.delete(url); };
  const anchorClick = w.HTMLAnchorElement.prototype.click;
  w.HTMLAnchorElement.prototype.click = function() {
    if (this.download) surface.downloads.push({filename: this.download, href: this.href, blob: surface.objectURLs.get(this.href)});
    else anchorClick.call(this);
  };
  const response = (body, status = 200) => ({ok: status >= 200 && status < 300, status, json: async () => w.JSON.parse(JSON.stringify(body))});
  w.fetch = async (input, options = {}) => {
    const url = new w.URL(String(input), w.location.href);
    surface.fetchCalls.push({pathname: url.pathname, method: options.method || 'GET'});
    if (url.pathname === '/assets/archive-index.json') return response(JSON.parse(fs.readFileSync(path.join(dist, 'assets/archive-index.json'), 'utf8')));
    return response({ok: false}, 404);
  };
  w.BroadcastChannel = class {
    constructor(name) {
      this.name = name; this.closed = false; this.listeners = new Set();
      if (!channels.has(name)) channels.set(name, new Set());
      channels.get(name).add(this);
    }
    addEventListener(type, listener) { if (type === 'message') this.listeners.add(listener); }
    removeEventListener(type, listener) { if (type === 'message') this.listeners.delete(listener); }
    deliver(serialized) {
      if (this.closed) return;
      const event = {data: w.JSON.parse(serialized)};
      this.onmessage?.(event);
      for (const listener of this.listeners) listener(event);
    }
    postMessage(frame) {
      if (this.closed) throw Error('Closed channel');
      const serialized = JSON.stringify(frame);
      surface.frames.push(JSON.parse(serialized));
      for (const peer of channels.get(this.name) || []) if (peer !== this && !peer.closed) queueMicrotask(() => peer.deliver(serialized));
    }
    close() { this.closed = true; channels.get(this.name)?.delete(this); }
  };
  w.addEventListener('error', event => errors.push(`${role}: ${event.error?.stack || event.message}`));
  const viewerStub = new vm.SyntheticModule(['createViewer', 'inspectSTL'], function() {
    this.setExport('createViewer', async () => ({loadSTL: () => ({dims: [20,20,20], triangles: 12}), showDemo() {}, reset() {}, explode: () => true, setWireframe() {}, setAutoRotate() {}, setMotion() {}, setSection() {}, dispose() {}}));
    this.setExport('inspectSTL', () => ({dims: [20,20,20], triangles: 12}));
  }, {context});
  await viewerStub.link(() => {});
  await viewerStub.evaluate();
  function moduleFor(filename) {
    filename = path.resolve(filename);
    if (surface.modules.has(filename)) return surface.modules.get(filename);
    const mod = new vm.SourceTextModule(fs.readFileSync(filename, 'utf8'), {
      context, identifier: filename,
      importModuleDynamically: async (specifier, parent) => {
        const target = path.resolve(path.dirname(parent.identifier), specifier);
        if (target === path.join(dist, 'lib/viewer.js')) return viewerStub;
        const imported = await load(target);
        if (imported.status !== 'evaluated') await imported.evaluate();
        return imported;
      }
    });
    surface.modules.set(filename, mod);
    return mod;
  }
  async function load(filename) {
    const mod = moduleFor(filename);
    if (mod.status === 'unlinked') await mod.link((specifier, parent) => moduleFor(path.resolve(path.dirname(parent.identifier), specifier)));
    return mod;
  }
  surface.$ = selector => w.document.querySelector(selector);
  surface.click = async selector => {
    const element = surface.$(selector);
    assert(element, `${role}: missing ${selector}`);
    element.click();
    await settle();
  };
  surface.app = await load(path.join(dist, 'app.js'));
  await surface.app.evaluate();
  await settle();
  return surface;
}

function snapshotStudio(surface) {
  const view = surface.$('.studio-view');
  assert(view, 'Studio is mounted');
  return {view, video: view.querySelector('[data-studio-video]'), form: view.querySelector('[data-studio-plan-form]'), time: view.querySelector('[data-studio-current-time]')};
}

function assertDisposed(surface, studio) {
  assert.equal(studio.video.paused, true, 'Disposed Studio pauses its player');
  assert.equal(studio.view.dataset.studioMotion, 'off', 'Disposed Studio disables its motion');
  assert.equal(surface.listenerCount(studio.video, 'timeupdate'), 0, 'Detached media handlers are removed');
  assert.equal(surface.listenerCount(studio.form, 'submit'), 0, 'Detached plan export cannot remain active');
  const time = studio.time.textContent, count = surface.downloads.length;
  studio.video.currentTime = 18;
  studio.video.dispatchEvent(new surface.w.Event('timeupdate'));
  studio.form.dispatchEvent(new surface.w.Event('submit', {bubbles: true, cancelable: true}));
  assert.equal(studio.time.textContent, time);
  assert.equal(surface.downloads.length, count, 'An obsolete form does not export');
}

async function readBlob(surface, blob) {
  return new Promise((resolve, reject) => {
    const reader = new surface.w.FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

(async () => {
  let failure = null;
  try {
    const center = await createSurface('pilotage', 'studio');
    const left = await createSurface('atelier');
    const right = await createSurface('creation');
    await settle();
    let studio = snapshotStudio(center);
    assert(center.$('#drawer').open);
    assert(center.$('#drawer').classList.contains('studio-drawer'));
    assert.equal(center.$('#drawer-title').textContent, 'LE STUDIO.');
    assert.equal(center.$('#main').dataset.screen, 'pilotage');
    assert(studio.video.src.endsWith('/assets/brand-film-master.mp4'));
    assert.equal(center.mediaState(studio.video).playCalls, 0, 'Opening Studio does not play the film');
    assert.equal(studio.video.hasAttribute('autoplay'), false);
    assert.equal(center.listenerCount(studio.form, 'submit'), 1);
    assert(center.$('link[href="./studio.css"]'));
    for (const asset of ['studio.css', 'assets/brand-film-master.mp4', 'assets/brand-film-poster.webp']) assert(fs.existsSync(path.join(dist, asset)), `Missing ${asset}`);
    checks.push('URL panel=studio mounts the real editing desk at the Jarvis station, uses the new 22.7 s film and loads its stylesheet without automatic playback.');

    await center.click('[data-studio-command="toggle"]');
    assert.equal(studio.video.paused, false);
    await center.click('#drawer [data-action="close-dialog"]');
    assert.equal(center.$('#drawer').open, false);
    assertDisposed(center, studio);
    await center.click('[data-action="studio"]');
    const reopened = snapshotStudio(center);
    assert.notEqual(reopened.view, studio.view);
    assert.equal(center.listenerCount(reopened.video, 'timeupdate'), 1);
    assert.equal(center.listenerCount(reopened.form, 'submit'), 1);
    assert.equal(center.mediaState(reopened.video).playCalls, 0);
    checks.push('The global Studio action reopens a fresh controller; closing pauses the previous player and removes its media and export listeners.');

    studio = reopened;
    await center.click('[data-studio-command="toggle"]');
    await center.click('#drawer [data-action="identity"]');
    assert(center.$('#drawer').classList.contains('signature-drawer'));
    assert.equal(center.$('.studio-view'), null);
    assertDisposed(center, studio);
    await center.click('[data-action="studio"]');
    studio = snapshotStudio(center);
    await center.click('[data-studio-command="toggle"]');
    await center.click('#drawer [data-action="story"]');
    assert(center.$('#story-form'));
    assert.equal(center.$('.studio-view'), null);
    assertDisposed(center, studio);
    checks.push('Switching from Studio to the historical identity or project scenario releases the previous Studio instead of keeping a hidden active player.');

    await center.click('[data-action="studio"]');
    studio = snapshotStudio(center);
    await center.click('[data-studio-command="toggle"]');
    center.$('#drawer').close();
    await settle();
    assertDisposed(center, studio);
    await center.click('[data-action="studio"]');
    studio = snapshotStudio(center);
    center.$('#drawer').close();
    center.$('[data-action="studio"]').click();
    const immediate = snapshotStudio(center);
    await settle();
    assertDisposed(center, studio);
    assert(center.$('#drawer').open);
    assert.equal(center.listenerCount(immediate.video, 'timeupdate'), 1);
    assert.equal(center.listenerCount(immediate.form, 'submit'), 1);
    immediate.video.currentTime = 9.1;
    immediate.video.dispatchEvent(new center.w.Event('timeupdate'));
    assert.equal(immediate.time.textContent, '00:09,1', 'Queued close does not dispose a newly opened Studio');
    checks.push('Native dialog close disposes Studio; a queued close from the preceding dialog does not destroy an immediate reopening.');

    studio = immediate;
    await center.click('[data-studio-command="toggle"]');
    assert.equal(studio.video.paused, false);
    const playCount = center.mediaState(studio.video).playCalls;
    await center.click('#motion-button');
    assert(center.w.document.documentElement.classList.contains('reduced-motion'));
    assert.equal(studio.view.dataset.studioMotion, 'off');
    assert.equal(studio.video.paused, true);
    await center.click('#motion-button');
    assert.equal(studio.view.dataset.studioMotion, 'on');
    assert.equal(center.mediaState(studio.video).playCalls, playCount, 'Re-enabling motion does not start the film');
    await center.setReducedMotion(true);
    assert.equal(studio.view.dataset.studioMotion, 'off');
    assert(center.w.document.documentElement.classList.contains('reduced-motion'));
    assert.equal(studio.video.paused, true);
    await center.setReducedMotion(false);
    assert.equal(studio.view.dataset.studioMotion, 'off', 'An OS preference change does not silently resume motion');
    await center.click('#motion-button');
    assert.equal(studio.view.dataset.studioMotion, 'on');
    checks.push('Global and operating-system reduced motion reach the mounted Studio, pause the film and never restart playback when motion is re-enabled.');

    const selected = studio.form.querySelector('input[name="studio-format"][value="16:9"]');
    selected.checked = true;
    selected.dispatchEvent(new center.w.Event('change', {bubbles: true}));
    const duration = studio.form.querySelector('#studio-duration');
    duration.value = '30';
    duration.dispatchEvent(new center.w.Event('input', {bubbles: true}));
    const requestsBefore = surfaces.reduce((sum, surface) => sum + surface.fetchCalls.length, 0);
    const downloadsBefore = center.downloads.length;
    studio.form.dispatchEvent(new center.w.Event('submit', {bubbles: true, cancelable: true}));
    await settle();
    assert.equal(center.downloads.length, downloadsBefore + 1);
    const downloaded = center.downloads.at(-1);
    const plan = JSON.parse(await readBlob(center, downloaded.blob));
    assert.equal(plan.format, 'bojart.edit-plan.v1');
    assert.equal(plan.brand, 'BOJ.ART');
    assert.equal(plan.target.aspectRatio, '16:9');
    assert.equal(plan.target.width, 1920);
    assert.equal(plan.target.height, 1080);
    assert.equal(plan.target.durationSeconds, 30);
    assert.equal(plan.status, 'plan_only');
    assert.equal(plan.renderRequested, false);
    assert.equal(plan.outputVideo, null);
    assert.equal(plan.publication.requested, false);
    assert.equal(plan.reference.master, 'assets/brand-film-master.mp4');
    assert(Number.isFinite(Date.parse(plan.preparedAt)));
    assert.match(downloaded.filename, /^BOJ_ART_plan_edit_16x9_30s_\d{4}-\d{2}-\d{2}\.json$/);
    assert(center.$('[data-studio-plan-message]').textContent.includes('le nouveau film reste à monter'));
    assert.equal(surfaces.reduce((sum, surface) => sum + surface.fetchCalls.length, 0), requestsBefore, 'Export remains local');
    assert(center.objectURLs.has(downloaded.href), 'Download URL is available while the desk is open');
    checks.push('The real Studio form exports one parseable local JSON plan with the selected 16:9 / 30 s target and truthful plan-only, unrendered and unpublished status.');

    const projectId = center.$('#project-picker').value;
    await center.click('[data-studio-command="toggle"]');
    await center.click('#drawer [data-action="visual-present"][data-visual-id="film"]');
    await settle();
    assert.equal(center.$('#drawer').open, false);
    assertDisposed(center, studio);
    assert(center.revokedURLs.includes(downloaded.href), 'Closing after sending revokes the pending download URL');
    assert.equal(center.objectURLs.size, 0);
    assert.equal(center.$('#main').dataset.screen, 'pilotage');
    assert.equal(center.$('#project-picker').value, projectId);
    assert.equal(left.$('#main').dataset.screen, 'atelier');
    const displayed = right.$('#studio-video');
    assert(displayed, 'The right window receives the film');
    assert(displayed.src.endsWith('/assets/brand-film-master.mp4'));
    assert.equal(displayed.hasAttribute('autoplay'), false);
    assert.equal(right.mediaState(displayed).playCalls, 0, 'The receiving screen waits for explicit playback');
    assert.equal(center.$('#studio-video'), null);
    const receipt = center.$('#command-receipt').textContent;
    assert(receipt.includes('Écran 03'), receipt);
    assert(receipt.includes('lecture manuelle'), receipt);
    const displayRequest = center.frames.find(frame => frame.protocol === 'bojart.display-bus.v1' && frame.type === 'request' && frame.payload?.view === 'film');
    assert(displayRequest, 'Film is sent through the actual display bus');
    assert.equal(surfaces.flatMap(surface => surface.fetchCalls).filter(call => call.method !== 'GET').length, 0);
    checks.push('Sending the reference film from Studio closes/disposes the desk, revokes its export URL and receives a right-screen acknowledgement while Jarvis and the left screen keep their roles; no render, publication or automatic playback is triggered.');

    const ids = [...center.w.document.querySelectorAll('[id]')].map(element => element.id);
    assert.equal(new Set(ids).size, ids.length);
    assert.equal(errors.length, 0, errors.join('\n'));
    checks.push('The integration completes with unique central-page IDs and no JavaScript error.');
  } catch (error) {
    failure = error;
  } finally {
    for (const surface of surfaces) {
      surface.w.dispatchEvent(new surface.w.Event('pagehide'));
      surface.closed = true;
      surface.w.close();
    }
  }
  const report = {
    status: failure ? 'failed' : 'passed', checkedAt: new Date().toISOString(), checks,
    applicationAndStudioModules: 'real',
    displayTransport: 'real protocol over isolated BroadcastChannel fixture',
    mediaLifecycle: 'deterministic HTMLMediaElement fixture',
    browserRenderingVerified: false, mediaDecodingVerified: false, networkUsed: false,
    scope: 'Targeted application/Studio integration; chapter timing, crop math and visual rendering belong to separate module/media verification.',
    ...(failure ? {failure: failure.stack} : {})
  };
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  if (failure) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
