const assert = require('node:assert/strict');
const test = require('node:test');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const app = path.join(__dirname, '../apps/jarvis/app');
const tick = () => new Promise(resolve => setImmediate(resolve));

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.children = []; this.value = '';
    this.disabled = false; this.checked = false; this.hidden = false;
    this.style = {}; this.dataset = {}; this.listeners = {}; this.attributes = {};
    this._text = ''; this.paused = true;
    this.classList = {add() {}, remove() {}};
  }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text + this.children.map(x => x.textContent).join(''); }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this._text = ''; this.children = items; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  getAttribute(name) { return this.attributes[name] ?? this[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; delete this[name]; }
  pause() { this.paused = true; }
  async play() { this.paused = false; }
  load() {}
  click() { return this.onclick?.(); }
}

function segment(id, extra = {}) {
  return {id, asset_id: 'a'.repeat(64), label: id, asset_label: 'TEST VIDEO',
    start: 0, end: 1, revision: 1, kind: 'authentic_capture', review: 'approved_internal',
    identity_anchor: true, availability: 'verified', tags: ['sculpture'],
    metadata: {width: 64, height: 64, duration: 2, audio: false},
    evidence: 'Explicit test annotation', provenance: 'Test fixture', ...extra};
}
const catalogue = segments => ({asset_count: segments.length ? 1 : 0, segments});
const growthState = {accounts: {one: {platform: 'tiktok', handle: '@one'}, two: {platform: 'tiktok', handle: '@two'}},
  topics: {sculpture: {label: 'Sculpture'}}};
const packet = (id = 'old-packet') => ({id, title: id, caption: 'Draft', search_query: 'sculpture',
  account: {handle: '@one'}, platform: 'tiktok', tag_basis: 'Fixture', hashtags: [], tag_rationale: [], blockers: []});

async function harness(name, cat, studioDemo = null) {
  const nodes = new Map(), all = [], requests = [], downloads = [];
  const get = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  const html = fs.readFileSync(path.join(app, name + '.html'), 'utf8');
  for (const match of html.matchAll(/<([\w-]+)\b([^>]*\bid="([^"]+)"[^>]*)>/g)) {
    const el = new Element(match[1]); el.disabled = /\bdisabled\b/.test(match[2]);
    el.hidden = /\bhidden\b/.test(match[2]); nodes.set(match[3], el);
  }
  function query(selector) {
    const match = selector.match(/^input\[name="([^"]+)"\](:checked)?$/);
    return match ? all.filter(x => x.tagName === 'INPUT' && x.name === match[1] && (!match[2] || x.checked)) : [];
  }
  vm.runInNewContext(fs.readFileSync(path.join(app, name + '.js'), 'utf8'), {
    window: studioDemo ? {DEMO_STUDIO: studioDemo} : {}, document: {getElementById: get, querySelectorAll: query,
      createElement: tag => { const el = new Element(tag); all.push(el); return el; }},
    crypto: {randomUUID: (() => { let n = 0; return () => 'request-' + ++n; })()},
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({url, options, reject,
      respond: (body, ok = true) => resolve({ok, json: async () => body})})),
    Blob, URL: {createObjectURL: blob => { downloads.push(blob); return 'blob:test'; }, revokeObjectURL() {}},
    structuredClone, setTimeout: fn => fn()
  });
  function reply(url, data, ok = true) {
    const i = requests.findIndex(r => r.url === url); assert.notEqual(i, -1, 'Pending request: ' + url);
    requests.splice(i, 1)[0].respond(data, ok);
  }
  if (name === 'growth') { reply('/api/growth/state', growthState); await tick(); }
  if (!studioDemo) reply('/api/studio/catalogue', cat);
  await tick();
  if (name === 'growth') { get('account').value = 'one'; get('topic').value = 'sculpture'; get('objective').value = 'portfolio'; }
  function change() { return get('form').listeners.change?.(); }
  return {get, reply, requests, all, downloads, query, change};
}

test('empty Studio loads as an empty catalogue without a fabricated demo selection', async () => {
  const h = await harness('studio', catalogue([]));
  assert.equal(h.get('segmentCount').textContent, '0');
  assert.equal(h.get('prepare').disabled, true);
  assert.equal(h.get('play').disabled, true);
  assert.match(h.get('feedback').textContent, /aucun passage|bibliothèque vide/i);
  assert.doesNotMatch(h.get('feedback').textContent, /undefined|indisponible|TypeError/);
});

test('Studio prepares arbitrary catalogue IDs with an explicit reference and exact revisions', async () => {
  const h = await harness('studio', catalogue([segment('piece-reference'), segment('detail', {identity_anchor: false, revision: 3})]));
  assert.equal(h.get('prepare').disabled, true, 'No identity reference is guessed');
  h.get('anchor').value = 'piece-reference'; h.get('anchor').onchange();
  const chosen = h.query('input[name="studio-segment"]').find(x => x.value === 'detail');
  assert.ok(chosen); chosen.checked = true; chosen.onchange();
  const pending = h.get('prepare').onclick();
  const request = JSON.parse(h.requests[0].options.body);
  assert.equal(request.anchor_id, 'piece-reference');
  assert.deepEqual(request.segment_ids, ['detail']);
  assert.deepEqual(request.expected_revisions, {'piece-reference': 1, detail: 3});
  h.reply('/api/studio/prepare', {id: 'brief', segment_order: ['detail']}); await pending;
  assert.equal(h.get('export').disabled, false);
});

test('missing or rejected Studio sources cannot become a reference or a selected source', async () => {
  const h = await harness('studio', catalogue([segment('missing', {availability: 'missing_or_changed'}), segment('rejected', {review: 'rejected'})]));
  assert.equal(h.get('anchor').children.filter(x => x.value).length, 0);
  assert.equal(h.get('prepare').disabled, true);
  assert.ok(h.query('input[name="studio-segment"]').every(x => x.disabled));
});

test('a live source named like a demo never borrows its unverified thumbnail', async () => {
  const h = await harness('studio', catalogue([segment('visage', {asset_id: 'b'.repeat(64)})]));
  assert.equal(h.all.filter(x => x.tagName === 'IMG').length, 0);
  assert.equal(h.get('video').src, '/api/studio/media/' + 'b'.repeat(64));
});

async function selectedStudio() {
  const h = await harness('studio', catalogue(['profil', 'troisquarts', 'visage'].map(id => segment(id))));
  return h;
}

test('changing a Studio selection ignores a late brief and leaves export disabled', async () => {
  const h = await selectedStudio();
  const pending = h.get('prepare').onclick();
  const chosen = h.query('input[name="studio-segment"]')[0];
  assert.ok(chosen); chosen.checked = false; chosen.onchange();
  h.reply('/api/studio/prepare', {id: 'old-brief', segment_order: ['profil']}); await pending;
  assert.equal(h.get('export').disabled, true);
  assert.equal(h.get('verify').disabled, true);
  h.get('export').onclick(); assert.equal(h.downloads.length, 0);
});

test('changing a Studio selection ignores a late verification result', async () => {
  const h = await selectedStudio();
  const first = h.get('prepare').onclick(); h.reply('/api/studio/prepare', {id: 'brief', segment_order: ['profil']}); await first;
  const pending = h.get('verify').onclick();
  const chosen = h.query('input[name="studio-segment"]')[0];
  assert.ok(chosen); chosen.checked = false; chosen.onchange();
  const feedback = h.get('feedback').textContent;
  h.reply('/api/studio/verify', {valid: true}); await pending;
  assert.equal(h.get('feedback').textContent, feedback);
  assert.equal(h.get('export').disabled, true);
});

test('an unchanged Studio selection retries a failed request under the same ID', async () => {
  const h = await selectedStudio();
  const first = h.get('prepare').onclick(); const body = h.requests[0].options.body;
  h.reply('/api/studio/prepare', {error: 'Response lost'}, false); await first;
  const second = h.get('prepare').onclick(); assert.equal(h.requests[0].options.body, body);
  h.reply('/api/studio/prepare', {id: 'replayed', segment_order: ['profil']}); await second;
  assert.equal(h.get('export').disabled, false);
});

test('the offline Studio example stays bound to its precalculated selection', async () => {
  const cat = catalogue(['profil', 'troisquarts', 'visage'].map(id => segment(id)));
  const example = {id: 'demo-brief', anchor_id: 'visage', segment_order: ['profil', 'troisquarts', 'visage']};
  const h = await harness('studio', cat, {catalogue: cat, plan: example, verification: {valid: true}, thumbs: {}, proxies: {}});
  await h.get('prepare').onclick();
  assert.equal(h.get('export').disabled, false);
  const chosen = h.query('input[name="studio-segment"]')[0]; chosen.checked = false; chosen.onchange();
  await h.get('prepare').onclick();
  assert.equal(h.get('export').disabled, true);
  assert.match(h.get('feedback').textContent, /précalculé/);
  assert.equal(h.requests.length, 0);
});

async function growth() { return harness('growth', catalogue([segment('ensemble'), segment('visage')])); }

test('a late Growth draft cannot reappear after changing the account', async () => {
  const h = await growth(); const pending = h.get('form').onsubmit({preventDefault() {}});
  h.get('account').value = 'two'; h.change();
  h.reply('/api/growth/prepare', packet()); await pending;
  assert.equal(h.get('packet').hidden, true);
  h.get('export').onclick(); assert.equal(h.downloads.length, 0);
  const fresh = h.get('form').onsubmit({preventDefault() {}});
  assert.equal(JSON.parse(h.requests[0].options.body).account_key, 'two');
  h.reply('/api/growth/prepare', packet('new-packet')); await fresh;
  assert.equal(h.get('packet').hidden, false);
});

test('late Growth verification success cannot validate a changed selection', async () => {
  const h = await growth(); const first = h.get('form').onsubmit({preventDefault() {}});
  h.reply('/api/growth/prepare', packet()); await first;
  const pending = h.get('check').onclick(); h.change(); const feedback = h.get('feedback').textContent;
  h.reply('/api/growth/validate', {sources_intact: true}); await pending;
  assert.equal(h.get('feedback').textContent, feedback);
  assert.equal(h.get('packet').hidden, true);
});

test('late Growth errors cannot replace feedback for the current selection', async () => {
  const h = await growth(); const pending = h.get('form').onsubmit({preventDefault() {}});
  h.change(); const feedback = h.get('feedback').textContent;
  h.reply('/api/growth/prepare', {error: 'OLD REQUEST ERROR'}, false); await pending;
  assert.equal(h.get('feedback').textContent, feedback);
});

test('an older Growth check cannot replace the result of a newer check', async () => {
  const h = await growth(); const prepared = h.get('form').onsubmit({preventDefault() {}});
  h.reply('/api/growth/prepare', packet()); await prepared;
  const first = h.get('check').onclick(), second = h.get('check').onclick();
  h.requests[1].respond({error: 'CURRENT SOURCE CHANGED'}, false); await second;
  h.requests[0].respond({sources_intact: true}); await first;
  assert.equal(h.get('feedback').textContent, 'CURRENT SOURCE CHANGED');
});

test('an unchanged Growth selection can display and export its draft', async () => {
  const h = await growth(); const pending = h.get('form').onsubmit({preventDefault() {}});
  h.reply('/api/growth/prepare', packet('current')); await pending;
  assert.equal(h.get('postTitle').textContent, 'current');
  h.get('export').onclick(); assert.equal(h.downloads.length, 1);
  assert.equal(JSON.parse(await h.downloads[0].text()).id, 'current');
});
