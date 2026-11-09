/* Actual React + JSDOM interactions. No browser, server, credentials or network. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const Module = require('node:module');
const { webcrypto } = require('node:crypto');
const { JSDOM } = require('../../bojart-workshop/node_modules/jsdom');
const cssTree = require('../../bojart-workshop/node_modules/css-tree');
const esbuild = require('esbuild');
const rootPath = path.resolve(__dirname, '..');
const dom = new JSDOM('<!doctype html><html><body><button id="outside">Extérieur</button><div id="test-root"></div></body></html>', { url: 'https://bojart.example.org/' });
for (const key of ['window', 'document', 'HTMLElement', 'HTMLInputElement', 'HTMLTextAreaElement', 'HTMLSelectElement', 'Node', 'MutationObserver', 'Event', 'MouseEvent', 'KeyboardEvent']) global[key] = dom.window[key];
global.sessionStorage = dom.window.sessionStorage;
global.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true });
Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });
global.IS_REACT_ACT_ENVIRONMENT = true;
let reduced = false;
window.matchMedia = () => ({ matches: reduced, addEventListener() {}, removeEventListener() {} });
window.HTMLElement.prototype.scrollTo = function() {};
const downloads = [];
URL.createObjectURL = (blob) => { downloads.push(blob); return 'blob:bojart-test'; };
URL.revokeObjectURL = () => {};
window.HTMLAnchorElement.prototype.click = function() {};
const React = require('react');
const { act } = React;
const { createRoot } = require('react-dom/client');
let root;
let Storefront, BriefForm, validateBriefStep, inquiryFromDraft;
let fetchImpl = async () => { throw new Error('Unexpected fetch'); };
global.fetch = (...args) => fetchImpl(...args);
const results = [];

function compile(entry) {
  const output = esbuild.buildSync({ entryPoints: [path.join(rootPath, entry)], bundle: true, write: false, format: 'cjs', platform: 'node', packages: 'external', jsx: 'automatic', logLevel: 'silent' }).outputFiles[0].text;
  const filename = path.join(rootPath, 'qa', 'in-memory.cjs');
  const loaded = new Module(filename, module); loaded.filename = filename; loaded.paths = Module._nodeModulePaths(path.join(rootPath, 'qa')); loaded._compile(output, filename); return loaded.exports;
}
async function test(name, run) { try { await run(); results.push({ name, pass: true }); console.log('PASS', name); } catch (error) { results.push({ name, pass: false, error: error.message }); console.error('FAIL', name, error); throw error; } }
async function mount(Component, props = {}, url = '/') {
  if (root) await act(async () => root.unmount());
  window.history.replaceState({}, '', url); document.body.style.overflow = '';
  root = createRoot(document.getElementById('test-root'));
  await act(async () => { root.render(React.createElement(Component, props)); });
}
async function click(node) { assert.ok(node, 'click target exists'); await act(async () => node.dispatchEvent(new MouseEvent('click', { bubbles: true }))); }
function button(text) { return [...document.querySelectorAll('button')].find((node) => node.textContent.includes(text)); }
async function input(id, value) {
  const node = document.getElementById(id); assert.ok(node, id);
  await act(async () => {
    const proto = node.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : node.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(node, value);
    node.dispatchEvent(new Event(node.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
  });
}
async function next() { await click(button('Continuer')); }
async function fillUntilRecap() {
  await input('brief-description', 'Une figurine personnelle avec socle, à étudier pour une finition peinte.');
  await next();
  await input('brief-heightMm', '300');
  await input('brief-quantity', '2');
  await input('brief-budgetRange', '750_1500');
  await next();
  await input('brief-name', 'Camille Atelier');
  await input('brief-email', 'camille@example.org');
  await click(document.getElementById('brief-privacyAcknowledged'));
  await next();
  assert.match(document.getElementById('brief-title').textContent, /TOUT COMMENCE/);
}
function response(status, body) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }); }
function receipt(payload) { return { format: 'bojart.inquiry.receipt.v1', requestId: payload.requestId, reference: 'BOJ-20261019-AABBCCDDEEFF', createdAt: '2026-10-19T12:00:00.000Z', status: 'new' }; }
function plainDraft() { return { offer: 'custom', description: 'Un socle personnalisé pour exposer une figurine de collection.', intendedUse: '', widthMm: '', heightMm: '', depthMm: '', quantity: '1', budgetRange: 'undecided', deadline: '', modelStatus: 'idea', references: '', name: 'Camille Atelier', email: 'camille@example.org', phone: '', privacyAcknowledged: true, website: '' }; }

(async () => {
  Storefront = compile('app/components/Storefront.tsx').default;
  const briefModule = compile('app/components/BriefForm.tsx');
  ({ default: BriefForm, validateBriefStep, inquiryFromDraft } = briefModule);
  await test('Styles parsed; every rendered local image and font exists; no implicit social embeds', async () => {
    const css = fs.readFileSync(path.join(rootPath, 'app/vitrine.css'), 'utf8');
    const errors = []; cssTree.parse(css, { onParseError: (error) => errors.push(error.message) }); assert.deepEqual(errors, []);
    assert.match(css, /@media\(prefers-reduced-motion:reduce\)/); assert.match(css, /@media\(max-width:700px\)/);
    await mount(Storefront);
    assert.equal(document.querySelectorAll('main h1').length, 1);
    for (const element of document.querySelectorAll('img[src^="/assets/"]')) assert.ok(fs.existsSync(path.join(rootPath, 'public', element.getAttribute('src'))));
    for (const file of ['body.ttf', 'display.ttf', 'brand-film-master.mp4', 'brand-film-poster.webp']) assert.ok(fs.existsSync(path.join(rootPath, 'public/assets', file)));
    for (const id of ['realisations', 'possibles', 'atelier', 'questions', 'projet']) assert.ok(document.getElementById(id));
    assert.equal(document.querySelectorAll('iframe,video[autoplay]').length, 0);
    assert.equal(document.querySelectorAll('a[href="/mentions"]').length, 1); assert.equal(document.querySelectorAll('a[href="/confidentialite"]').length, 1);
  });
  await test('Hero selector changes real artwork and its detail; close restores focus', async () => {
    const selectors = [...document.querySelectorAll('.boj-art-selector button')]; await click(selectors[1]);
    assert.match(document.querySelector('.boj-art-caption h2').textContent, /Dragon Ball/);
    const trigger = document.querySelector('.boj-hero-image-button'); trigger.focus(); await click(trigger);
    assert.match(document.getElementById('work-title').textContent, /Dragon Ball/); assert.equal(document.body.style.overflow, 'hidden');
    await click(document.querySelector('.boj-dialog-close'));
    assert.equal(document.querySelector('[role="dialog"]'), null); assert.equal(document.activeElement, trigger); assert.equal(document.body.style.overflow, '');
  });
  await test('Offer keyboard navigation updates content and prepares the correct brief', async () => {
    const active = document.querySelector('[role="tab"][aria-selected="true"]');
    await act(async () => active.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true })));
    assert.equal(document.querySelector('[role="tab"][aria-selected="true"]').id, 'offer-tab-prototype');
    assert.match(document.querySelector('[role="tabpanel"]').textContent, /FAISABILITÉ À ÉTUDIER/);
    await click(button('Présenter mon besoin'));
    assert.equal(document.querySelector('input[name="offer"][value="prototype"]').checked, true);
    await click(document.querySelector('.boj-dialog-close'));
  });
  await test('Deep link chooses artwork; privacy-preserving UTM filtering does not block inquiry', async () => {
    await mount(Storefront, {}, '/?brief=artwork&piece=trone&utm_source=TikTok&utm_campaign=private%40example.com');
    assert.equal(document.querySelector('input[name="offer"][value="artwork"]').checked, true);
    assert.match(document.querySelector('.boj-selected-work').textContent, /Pièce sur trône/);
    const data = inquiryFromDraft(plainDraft(), webcrypto.randomUUID(), { pathname: '/pi%C3%A8ce', search: '?utm_source=TikTok&utm_medium=organic&utm_campaign=private%40example.com' });
    assert.equal(data.source.entryPath, '/'); assert.equal(data.source.utmSource, 'TikTok'); assert.equal(data.source.utmMedium, 'organic'); assert.equal(data.source.utmCampaign, undefined);
    await click(document.querySelector('.boj-dialog-close'));
  });
  await test('The four steps enforce useful description, dimensions, contact and privacy; no premature send', async () => {
    let calls = 0; fetchImpl = async () => { calls++; throw new Error('No request expected'); };
    await mount(BriefForm, { onClose() {} }); await next(); assert.ok(document.getElementById('error-description')); assert.equal(calls, 0);
    await input('brief-description', 'Une pièce originale à étudier à partir de références personnelles.');
    await input('brief-references', 'https://192.168.1.1/model'); await next(); assert.ok(document.getElementById('error-references'));
    await input('brief-references', ''); await next(); await input('brief-heightMm', '-2'); await next(); assert.ok(document.getElementById('error-heightMm'));
    await input('brief-heightMm', '300'); await next(); await next(); assert.ok(document.getElementById('error-name')); assert.ok(document.getElementById('error-privacyAcknowledged')); assert.equal(calls, 0);
    assert.ok(validateBriefStep({ ...plainDraft(), phone: 'abc' }, 2).phone); assert.ok(validateBriefStep({ ...plainDraft(), deadline: '2026-02-30' }, 1).deadline);
  });
  await test('An ambiguous submission is frozen, restored and replayed byte-for-byte; one server record', async () => {
    sessionStorage.clear(); const received = []; const saved = new Map(); let first = true;
    fetchImpl = async (url, options = {}) => {
      if (url === '/api/briefs/token') return response(200, { ok: true, token: 'test-token', expiresAt: '2026-10-19T14:00:00.000Z' });
      assert.equal(url, '/api/briefs'); assert.equal(options.headers['X-BOJART-Form-Token'], 'test-token');
      received.push(options.body); const payload = JSON.parse(options.body); saved.set(payload.requestId, payload);
      if (first) { first = false; throw new TypeError('La connexion a été interrompue.'); }
      return response(200, { ok: true, receipt: receipt(payload), replayed: true });
    };
    await mount(Storefront); await click(button('Décrire mon projet')); await fillUntilRecap(); await click(button('Envoyer à l’atelier'));
    assert.equal(document.querySelector('.boj-receipt'), null); assert.match(document.querySelector('.boj-submit-message').textContent, /Confirmation en attente/); assert.ok(sessionStorage.getItem('bojart.pending-inquiry.v1'));
    await click(document.querySelector('.boj-dialog-close')); await click(button('Décrire mon projet'));
    assert.match(document.getElementById('brief-title').textContent, /TOUT COMMENCE/); assert.equal(button('← Retour').disabled, true);
    await click(button('Renvoyer la même demande'));
    assert.equal(received.length, 2); assert.equal(received[0], received[1]); assert.equal(saved.size, 1); assert.match(document.querySelector('.boj-receipt').textContent, /BOJ-20261019-AABBCCDDEEFF/); assert.equal(sessionStorage.getItem('bojart.pending-inquiry.v1'), null);
    await click(button('Télécharger mon récapitulatif')); const text = await downloads.at(-1).text(); assert.match(text, /BOJ-20261019-AABBCCDDEEFF/); assert.match(text, /camille@example.org/);
    await click(document.querySelector('.boj-dialog-close'));
  });
  await test('Personal download before acknowledgment says it is not proof of transmission', async () => {
    await mount(BriefForm, { onClose() {} }); await input('brief-description', 'Une création personnelle à préparer avec le futur atelier.');
    await click(button('Télécharger une copie'));
    const text = await downloads.at(-1).text(); assert.match(text, /ne confirme pas un envoi/); assert.doesNotMatch(text, /Demande enregistrée :/); assert.equal(document.querySelector('.boj-receipt'), null);
  });
  await test('Server field rejection returns to the relevant editable step and clears unaccepted attempt', async () => {
    sessionStorage.clear(); fetchImpl = async (url) => url === '/api/briefs/token' ? response(200, { ok: true, token: 'test' }) : response(422, { ok: false, error: { code: 'validation_failed', message: 'Vérifiez votre téléphone.', fields: { phone: 'Le numéro est invalide.' } } });
    await mount(BriefForm, { onClose() {} }); await fillUntilRecap(); await click(button('Envoyer à l’atelier'));
    assert.match(document.getElementById('brief-title').textContent, /GARDONS LE CONTACT/); assert.ok(document.getElementById('error-phone')); assert.equal(document.getElementById('brief-phone').disabled, false); assert.equal(sessionStorage.getItem('bojart.pending-inquiry.v1'), null); assert.equal(document.querySelector('.boj-receipt'), null);
  });
  await test('A mismatched acknowledgment never becomes a success message', async () => {
    sessionStorage.clear(); fetchImpl = async (url, options = {}) => url === '/api/briefs/token' ? response(200, { ok: true, token: 'test' }) : response(200, { ok: true, receipt: receipt({ requestId: 'wrong-request' }), replayed: false });
    await mount(BriefForm, { onClose() {} }); await fillUntilRecap(); await click(button('Envoyer à l’atelier'));
    assert.equal(document.querySelector('.boj-receipt'), null); assert.ok(sessionStorage.getItem('bojart.pending-inquiry.v1')); assert.match(document.querySelector('.boj-submit-message').textContent, /Confirmation en attente/);
  });
  await test('Deleted server request is not replaced automatically; original identifier survives', async () => {
    const before = JSON.parse(sessionStorage.getItem('bojart.pending-inquiry.v1')).payload.requestId;
    let received; fetchImpl = async (url, options = {}) => { if (url === '/api/briefs/token') return response(200, { ok: true, token: 'test' }); received = JSON.parse(options.body); return response(410, { ok: false, error: { code: 'request_deleted', message: 'Cette demande a été supprimée.' } }); };
    await mount(BriefForm, { onClose() {} }); await click(button('Renvoyer la même demande'));
    assert.equal(received.requestId, before); assert.equal(JSON.parse(sessionStorage.getItem('bojart.pending-inquiry.v1')).payload.requestId, before); assert.equal(document.querySelector('.boj-receipt'), null);
  });
  await test('Reduced-motion preference and manual motion switch preserve visible content', async () => {
    sessionStorage.clear(); reduced = true; await mount(Storefront); assert.equal(document.querySelector('.boj-site').dataset.motion, 'reduced');
    assert.ok(document.getElementById('hero-title').textContent.includes('L’IMAGINAIRE')); await click(button('Mouvement : réduit')); assert.equal(document.querySelector('.boj-site').dataset.motion, 'full');
    const trigger = button('Décrire mon projet'); trigger.focus(); await click(trigger);
    const last = button('Télécharger une copie'); last.focus(); await act(async () => last.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))); assert.equal(document.activeElement, document.querySelector('.boj-dialog-close'));
    await act(async () => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))); assert.equal(document.querySelector('[role="dialog"]'), null); assert.equal(document.activeElement, trigger);
  });
  await test('Film is deliberate, controlled and sourced; selecting a work does not assert stock', async () => {
    await click(button('REGARDER LE FILM')); const video = document.querySelector('video'); assert.ok(video); assert.equal(video.autoplay, false); assert.equal(video.controls, true); assert.equal(video.getAttribute('preload'), 'metadata');
    assert.equal(document.querySelectorAll('.boj-film-description a').length, 2); await click(document.querySelector('.boj-dialog-close'));
    await click(document.querySelector('.boj-work-image')); assert.match(document.querySelector('.boj-portfolio-note').textContent, /ne confirme pas une disponibilité/); await click(button('Cette pièce m’intéresse')); assert.equal(document.querySelector('input[name="offer"][value="artwork"]').checked, true); assert.match(document.querySelector('.boj-selected-work').textContent, /Baki/);
  });
})().then(async () => {
  if (root) await act(async () => root.unmount()); dom.window.close();
  const report = { format: 'bojart.storefront.qa.v1', checkedAt: new Date().toISOString(), passed: results.length, failed: 0, scope: 'React 19 interactions in JSDOM, CSS syntax and local asset presence; injected network only. No browser render, physical devices or actual D1 deployment verified.', groups: results };
  fs.writeFileSync(path.join(__dirname, 'storefront-results.json'), JSON.stringify(report, null, 2) + '\n'); console.log(`${results.length} groups passed`);
}).catch(async (error) => { if (root) await act(async () => root.unmount()); dom.window.close(); fs.writeFileSync(path.join(__dirname, 'storefront-results.json'), JSON.stringify({ format: 'bojart.storefront.qa.v1', checkedAt: new Date().toISOString(), passed: results.filter((entry) => entry.pass).length, failed: results.filter((entry) => !entry.pass).length, groups: results }, null, 2) + '\n'); process.exitCode = 1; });
