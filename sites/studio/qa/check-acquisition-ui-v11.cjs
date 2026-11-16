/* Contradictory UI checks with real React and deferred replies; no browser or network. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const Module = require('node:module');
const { webcrypto } = require('node:crypto');
const { JSDOM } = require('../../bojart-workshop/node_modules/jsdom');
const esbuild = require('esbuild');
const base = path.resolve(__dirname, '..');
const dom = new JSDOM('<!doctype html><html><body><div id="test-root"></div></body></html>', { url: 'https://bojart.example.org/' });
for (const key of ['window', 'document', 'HTMLElement', 'HTMLInputElement', 'HTMLTextAreaElement', 'HTMLSelectElement', 'Node', 'MutationObserver', 'Event', 'MouseEvent', 'KeyboardEvent']) global[key] = dom.window[key];
global.sessionStorage = dom.window.sessionStorage;
Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true });
Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });
global.IS_REACT_ACT_ENVIRONMENT = true;
window.HTMLElement.prototype.scrollTo = function() {};
URL.createObjectURL = () => 'blob:bojart-test'; URL.revokeObjectURL = () => {};
window.HTMLAnchorElement.prototype.click = function() {};
const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
let root; let fetchImpl; global.fetch = (...args) => fetchImpl(...args);
const results = [];
function compile(entry) {
  const result = esbuild.buildSync({ entryPoints: [path.join(base, entry)], bundle: true, write: false, format: 'cjs', platform: 'node', packages: 'external', jsx: 'automatic', logLevel: 'silent' }).outputFiles[0].text;
  const filename = path.join(base, 'qa/in-memory-v11.cjs'); const loaded = new Module(filename, module); loaded.filename = filename; loaded.paths = Module._nodeModulePaths(path.join(base, 'qa')); loaded._compile(result, filename); return loaded.exports.default;
}
const BriefForm = compile('app/components/BriefForm.tsx'); const AdminConsole = compile('app/administration/AdminConsole.tsx');
async function test(name, fn) { try { await fn(); results.push({ name, pass: true }); console.log('PASS', name); } catch (error) { results.push({ name, pass: false, error: error.message }); console.error('FAIL', name, error.message); } }
async function mount(Component, url = '/') { if (root) await act(async () => root.unmount()); window.history.replaceState({}, '', url); root = createRoot(document.getElementById('test-root')); await act(async () => root.render(React.createElement(Component, { onClose() {} }))); }
const button = text => [...document.querySelectorAll('button')].find(node => node.textContent.includes(text));
async function click(node) { assert.ok(node, 'Expected actionable button'); await act(async () => node.dispatchEvent(new MouseEvent('click', { bubbles: true }))); }
async function input(id, value) { const node = document.getElementById(id); assert.ok(node, id); await act(async () => { const proto = node.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto, 'value').set.call(node, value); node.dispatchEvent(new Event('input', { bubbles: true })); }); }
const response = (status, data) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
const token = () => response(200, { ok: true, token: 'test-token' });
const receipt = payload => response(200, { ok: true, receipt: { format: 'bojart.inquiry.receipt.v1', requestId: payload.requestId, reference: 'BOJ-20261019-AABBCCDDEEFF', createdAt: '2026-10-19T12:00:00.000Z', status: 'new' } });
function deferred() { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; }
async function fill() { await input('brief-description', 'Une figurine originale à étudier pour notre salle de présentation.'); await click(button('Continuer')); await click(button('Continuer')); await input('brief-name', 'Camille Test'); await input('brief-email', 'camille@example.org'); await click(document.getElementById('brief-privacyAcknowledged')); await click(button('Continuer')); }
const pending = () => JSON.parse(sessionStorage.getItem('bojart.pending-inquiry.v1'));

(async () => {
  await test('An unrecognized JSON 400/413/422 never clears a possibly committed submission', async () => {
    for (const status of [400, 413, 422]) {
      sessionStorage.clear(); let sent; let retry = false;
      fetchImpl = async (url, opts = {}) => { if (url.endsWith('/token')) return token(); const value = JSON.parse(opts.body); sent ||= value; if (!retry) return response(status, { error: 'upstream response could not be relayed' }); assert.equal(value.requestId, sent.requestId); return receipt(value); };
      await mount(BriefForm); await fill(); await click(button('Envoyer à l’atelier'));
      assert.equal(pending()?.payload.requestId, sent.requestId, `Unknown ${status} lost request identity`);
      retry = true; await click(button('Renvoyer la même demande')); assert.ok(document.querySelector('.boj-receipt'));
    }
  });
  await test('A validation error after an ambiguous prior send preserves the original identifier', async () => {
    sessionStorage.clear(); let first = true; let sent;
    fetchImpl = async (url, opts = {}) => { if (url.endsWith('/token')) return token(); sent ||= JSON.parse(opts.body); if (first) { first = false; throw new TypeError('lost response after commit'); } return response(422, { ok: false, error: { code: 'validation_failed', message: 'Le service a refusé cette nouvelle tentative.', fields: { description: 'À vérifier avec l’atelier.' } } }); };
    await mount(BriefForm); await fill(); await click(button('Envoyer à l’atelier')); await click(button('Renvoyer la même demande'));
    assert.equal(pending()?.payload.requestId, sent.requestId); assert.equal(button('← Retour').disabled, true);
  });
  await test('A deleted request becomes terminal and can be cleared explicitly without being recreated', async () => {
    sessionStorage.clear(); let sends = 0;
    fetchImpl = async url => url.endsWith('/token') ? token() : (++sends, response(410, { ok: false, error: { code: 'request_deleted', message: 'Cette demande a été supprimée.' } }));
    await mount(BriefForm); await fill(); await click(button('Envoyer à l’atelier'));
    assert.ok(button('Commencer un nouveau brief')); assert.equal(button('Renvoyer la même demande'), undefined);
    await mount(BriefForm); assert.ok(button('Commencer un nouveau brief')); await click(button('Commencer un nouveau brief'));
    assert.equal(pending(), null); assert.equal(document.getElementById('brief-description').value, ''); assert.equal(sends, 1);
  });
  await test('A failure before POST leaves a new brief editable instead of freezing an unsent request', async () => {
    sessionStorage.clear(); let posts = 0; fetchImpl = async url => { if (url.endsWith('/token')) return response(503, { ok: false, error: { message: 'Protection indisponible.' } }); posts++; return receipt({}); };
    await mount(BriefForm); await fill(); await click(button('Envoyer à l’atelier'));
    assert.equal(posts, 0); assert.equal(pending(), null); assert.equal(button('← Retour').disabled, false);
  });
  await test('Rapid repeated submission enters one in-flight operation and creates one request identifier', async () => {
    sessionStorage.clear(); const gate = deferred(); const bodies = [];
    fetchImpl = async (url, opts = {}) => { if (url.endsWith('/token')) { await gate.promise; return token(); } bodies.push(JSON.parse(opts.body)); return receipt(bodies.at(-1)); };
    await mount(BriefForm); await fill(); const node = button('Envoyer à l’atelier');
    await act(async () => { node.dispatchEvent(new MouseEvent('click', { bubbles: true })); node.dispatchEvent(new MouseEvent('click', { bubbles: true })); });
    await act(async () => gate.resolve()); assert.equal(bodies.length, 1);
  });
  await test('An administrator cannot write dossier A while a selection of dossier B is pending', async () => {
    const a = { requestId: '00000000-0000-4000-8000-000000000001', reference: 'BOJ-20261019-AAAAAAAAAAAA', name: 'Test A', email: 'a@example.org', offer: 'custom', status: 'new', createdAt: '2026-10-19T12:00:00.000Z', updatedAt: '2026-10-19T12:00:00.000Z', revision: 1, quantity: 1, budgetRange: 'undecided', source: null, description: 'Pièce originale de test A.', modelStatus: 'idea', referenceURLs: [] };
    const b = { ...a, requestId: '00000000-0000-4000-8000-000000000002', reference: 'BOJ-20261019-BBBBBBBBBBBB', name: 'Test B' };
    const gate = deferred(); const writes = [];
    fetchImpl = async (url, opts = {}) => {
      if (opts.method === 'PATCH') { writes.push(url); return response(200, { ok: true, inquiry: { ...a, revision: 2 } }); }
      if (url.includes('?status=')) return response(200, { ok: true, inquiries: [a, b], nextCursor: null, counts: { new: 2 } });
      if (url.endsWith(b.requestId)) { await gate.promise; return response(200, { ok: true, inquiry: b }); }
      return response(200, { ok: true, inquiry: a });
    };
    await mount(AdminConsole, '/administration'); await click(button('Test A')); const save = button('Enregistrer le suivi'); const selectB = button('Test B');
    await act(async () => { selectB.dispatchEvent(new MouseEvent('click', { bubbles: true })); save.dispatchEvent(new MouseEvent('click', { bubbles: true })); });
    await act(async () => gate.resolve()); assert.equal(writes.length, 0); assert.match(document.querySelector('.boj-admin-detail-heading').textContent, /BBBBBBBBBBBB/);
  });
  await test('An expired uncertain attempt retains a minimal recovery notice before any fresh submission', async () => {
    sessionStorage.clear(); let sent; let posts = 0;
    fetchImpl = async (url, opts = {}) => { if (url.endsWith('/token')) return token(); posts++; sent = JSON.parse(opts.body); throw new TypeError('unknown response'); };
    await mount(BriefForm); await fill(); await click(button('Envoyer à l’atelier'));
    sessionStorage.setItem('bojart.pending-inquiry.v1', JSON.stringify({ ...pending(), savedAt: Date.now() - 2 * 86400000 }));
    await mount(BriefForm);
    assert.ok(button('J’ai vérifié : commencer un nouveau brief'));
    const recovery = JSON.parse(sessionStorage.getItem('bojart.pending-recovery.v1'));
    assert.equal(recovery.requestId, sent.requestId); assert.equal(pending(), null);
    assert.equal(JSON.stringify(recovery).includes('camille@example.org'), false);
    await mount(BriefForm); assert.ok(button('J’ai vérifié : commencer un nouveau brief'));
    await click(button('J’ai vérifié : commencer un nouveau brief'));
    assert.equal(document.getElementById('brief-description').value, ''); assert.equal(posts, 1);
    assert.equal(sessionStorage.getItem('bojart.pending-recovery.v1'), null);
  });
})().finally(async () => {
  if (root) await act(async () => root.unmount()); dom.window.close();
  const report = { version: 'bojart.acquisition.ui.qa.v11', testedAt: new Date().toISOString(), scope: 'React in JSDOM with deferred injected responses, no browser, live session or database.', passed: results.filter(result => result.pass).length, failed: results.filter(result => !result.pass).length, results };
  fs.writeFileSync(path.join(__dirname, 'acquisition-ui-v11-results.json'), JSON.stringify(report, null, 2) + '\n'); console.log(JSON.stringify({ passed: report.passed, failed: report.failed })); if (report.failed) process.exitCode = 1;
});
