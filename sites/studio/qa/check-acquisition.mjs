import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createAcquisitionService, authorizedAdmin } from '../lib/acquisition-service.mjs';
import { normalizeInquiry, canonicalJSON, verifyInquiryExport, sha256 } from '../lib/acquisition-core.mjs';

const root = resolve(import.meta.dirname, '..');
const migrationNames = (await readdir(resolve(root, 'drizzle'))).filter(name => name.endsWith('.sql')).sort();
const migrations = await Promise.all(migrationNames.map(name => readFile(resolve(root, 'drizzle', name), 'utf8')));
const origin = 'https://bojart-studio.yellowghost64.chatgpt.site';
const admin = { 'oai-authenticated-user-id': 'owner-test', 'oai-authenticated-user-email': 'owner@bojart.test' };
const secret = 'qa-only-' + 'x'.repeat(48);
let clock = Date.parse('2026-10-19T12:00:00.000Z');

function fixture() {
  const sql = new DatabaseSync(':memory:');
  for (const migration of migrations) sql.exec(migration);
  const hooks = { failAfterInsert: false, failNextRead: false, failBatchAt: -1 };
  const db = {
    prepare(query) {
      let values = [];
      const statement = {
        bind(...next) { values = next; return statement; },
        execute() {
          if (hooks.failNextRead && query.startsWith('SELECT * FROM inquiries')) { hooks.failNextRead = false; throw new Error('injected read failure'); }
          const prepared = sql.prepare(query);
          const result = /(^\s*SELECT\b|\bRETURNING\b)/i.test(query) ? prepared.all(...values) : (prepared.run(...values), []);
          const changes = sql.prepare('SELECT changes() AS n').get().n;
          if (hooks.failAfterInsert && query.startsWith('INSERT INTO inquiries')) { hooks.failAfterInsert = false; hooks.failNextRead = true; }
          return { success: true, results: result.map(row => ({ ...row })), meta: { changes } };
        },
        async first() { return statement.execute().results[0] || null; },
        async all() { return statement.execute(); },
        async run() { return statement.execute(); },
      };
      return statement;
    },
    async batch(statements) {
      sql.exec('BEGIN IMMEDIATE');
      try {
        const output = statements.map((statement, index) => {
          if (hooks.failBatchAt === index) { hooks.failBatchAt = -1; throw new Error('injected batch failure'); }
          return statement.execute();
        });
        sql.exec('COMMIT');
        return output;
      } catch (error) { sql.exec('ROLLBACK'); throw error; }
    },
  };
  return { db, sql, hooks, service: createAcquisitionService({ db, secret, adminEmails: 'owner@bojart.test', now: () => clock }), close() { sql.close(); } };
}
function brief(overrides = {}) {
  return { format: 'bojart.inquiry.v1', requestId: crypto.randomUUID(), offer: 'custom', name: 'Client Test', email: 'client@example.org', description: 'Une création originale pour un espace de présentation.', intendedUse: 'Décoration intérieure', quantity: 1, budgetRange: 'undecided', modelStatus: 'idea', referenceURLs: ['https://www.tiktok.com/@boj.art'], source: { entryPath: '/', utmSource: 'tiktok', utmCampaign: 'atelier' }, privacyAcknowledged: true, website: '', ...overrides };
}
function request(path = '/api/briefs', { method = 'GET', payload, token, headers = {} } = {}) {
  return new Request(origin + path, { method, headers: { ...(method !== 'GET' ? { origin, 'content-type': 'application/json', 'cf-connecting-ip': '198.51.100.7' } : {}), ...(token ? { 'x-bojart-form-token': token } : {}), ...headers }, ...(payload !== undefined ? { body: typeof payload === 'string' ? payload : JSON.stringify(payload) } : {}) });
}
async function token(service) { const response = await service.token(request('/api/briefs/token')); assert.equal(response.status, 200); return (await response.json()).token; }
async function submit(service, payload, overrides = {}) { const t = overrides.token ?? await token(service); return service.submit(request('/api/briefs', { method: 'POST', payload, token: t, ...overrides })); }
const results = [];
async function test(name, run) { try { await run(); results.push({ name, status: 'passed' }); console.log('PASS ' + name); } catch (error) { results.push({ name, status: 'failed', error: error.message }); console.error('FAIL ' + name + '\n' + error.stack); } }

await test('Strict portable contract, field bounds, real dates and public-reference URLs', async () => {
  const input = brief({ dimensions: { heightMm: 1000, widthMm: 400 }, deadline: '2027-02-28' });
  const normalized = normalizeInquiry(input);
  assert.equal(normalized.website, undefined);
  assert.equal(normalized.dimensions.heightMm, 1000);
  for (const patch of [{ unknown: true }, { name: 'x' }, { email: 'bad' }, { description: 'short' }, { quantity: 1.5 }, { dimensions: { heightMm: -1 } }, { dimensions: {} }, { deadline: '2027-02-30' }, { referenceURLs: ['http://example.org/a'] }, { referenceURLs: ['https://localhost/a'] }, { referenceURLs: ['https://user:password@example.org/a'] }, { referenceURLs: ['https://127.0.0.1/a'] }, { source: { entryPath: '/?email=person@example.org' } }, { privacyAcknowledged: false }, { website: 'spam' }, { offer: 'admin' }]) assert.throws(() => normalizeInquiry({ ...input, ...patch }), error => error.code === 'validation_failed');
  assert.equal(canonicalJSON({ b: 2, a: { d: 4, c: 3 } }), '{"a":{"c":3,"d":4},"b":2}');
});

await test('Every administrator operation checks SIWC identity and explicit allowlist', async () => {
  const f = fixture();
  try {
    const id = crypto.randomUUID();
    for (const name of ['list', 'detail', 'export', 'update', 'remove']) {
      const response = await f.service[name](request('/api/admin/briefs/' + id), id);
      assert.equal(response.status, 401, name);
      const denied = await f.service[name](request('/api/admin/briefs/' + id, { headers: { ...admin, 'oai-authenticated-user-email': 'intruder@example.org' } }), id);
      assert.equal(denied.status, 403, name);
    }
    assert.equal(authorizedAdmin({ userId: 'x', email: 'OWNER@BOJART.TEST' }, ' other@example.org; owner@bojart.test '), true);
    assert.equal(authorizedAdmin({ userId: 'x', email: 'owner@bojart.test' }, ''), false);
    const allowed = await f.service.list(request('/api/admin/briefs', { headers: admin }));
    assert.equal(allowed.status, 200);
    assert.match(allowed.headers.get('cache-control'), /no-store/);
  } finally { f.close(); }
});

await test('HMAC form token, origin, expiry and absent configuration fail closed', async () => {
  const f = fixture(); const initial = clock;
  try {
    const t = await token(f.service);
    const unsigned = await f.service.submit(request('/api/briefs', { method: 'POST', payload: brief() }));
    assert.equal(unsigned.status, 403);
    const bad = await submit(f.service, brief(), { token: t.slice(0, -3) + 'aaa' }); assert.equal(bad.status, 403);
    const cross = await submit(f.service, brief(), { token: t, headers: { origin: 'https://attacker.invalid' } }); assert.equal(cross.status, 403);
    clock += 16 * 60000;
    const expired = await submit(f.service, brief(), { token: t }); assert.equal(expired.status, 403);
    const absent = createAcquisitionService({ db: f.db, now: () => clock });
    assert.equal((await absent.token(request('/api/briefs/token'))).status, 503);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 0);
  } finally { clock = initial; f.close(); }
});

await test('Receipt follows persisted SQLite row; identical retry returns the same receipt', async () => {
  const f = fixture();
  try {
    const input = brief();
    const response = await submit(f.service, input); assert.equal(response.status, 201);
    const first = await response.json(); assert.equal(first.replayed, false);
    const row = f.sql.prepare('SELECT * FROM inquiries').get();
    assert.equal(row.request_id, input.requestId);
    assert.equal(row.privacy_version, '2026-10-19');
    assert.equal(row.payload_hash, await sha256(canonicalJSON(normalizeInquiry(input))));
    const secondResponse = await submit(f.service, input); assert.equal(secondResponse.status, 200);
    const second = await secondResponse.json(); assert.equal(second.replayed, true);
    assert.deepEqual(second.receipt, first.receipt);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 1);
    assert.equal(first.receipt.email, undefined);
  } finally { f.close(); }
});

await test('Changed body under the same request ID is rejected without overwriting', async () => {
  const f = fixture();
  try {
    const input = brief(); await submit(f.service, input);
    const response = await submit(f.service, { ...input, quantity: 2 });
    assert.equal(response.status, 409); assert.equal((await response.json()).error.code, 'idempotency_conflict');
    assert.equal(JSON.parse(f.sql.prepare('SELECT payload_json FROM inquiries').get().payload_json).quantity, 1);
  } finally { f.close(); }
});

await test('Ambiguous response after commit is recovered by an identical retry', async () => {
  const f = fixture();
  try {
    const input = brief(); f.hooks.failAfterInsert = true;
    const ambiguous = await submit(f.service, input); assert.equal(ambiguous.status, 503);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 1);
    const replay = await submit(f.service, input); assert.equal(replay.status, 200);
    assert.equal((await replay.json()).replayed, true);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 1);
  } finally { f.close(); }
});

await test('An actual SQL insert failure never returns a successful receipt', async () => {
  const f = fixture();
  try {
    f.sql.exec("CREATE TEMP TRIGGER fail_test_insert BEFORE INSERT ON inquiries BEGIN SELECT RAISE(FAIL, 'injected storage failure'); END");
    const response = await submit(f.service, brief());
    assert.equal(response.status, 503);
    const body = await response.json();
    assert.equal(body.ok, false);
    assert.equal(body.receipt, undefined);
    assert.equal(JSON.stringify(body).includes('injected storage failure'), false);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 0);
  } finally { f.close(); }
});

await test('Concurrent duplicate submissions produce one row and one winning receipt', async () => {
  const f = fixture();
  try {
    const input = brief(); const t = await token(f.service);
    const responses = await Promise.all([submit(f.service, input, { token: t }), submit(f.service, input, { token: t })]);
    assert.deepEqual(responses.map(response => response.status).sort(), [200, 201]);
    const bodies = await Promise.all(responses.map(response => response.json()));
    assert.deepEqual(bodies[0].receipt, bodies[1].receipt);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 1);
  } finally { f.close(); }
});

await test('Concurrent rate limiting is atomic, bounded and stores no raw network address', async () => {
  const f = fixture();
  try {
    const t = await token(f.service);
    const responses = await Promise.all(Array.from({ length: 12 }, () => submit(f.service, brief(), { token: t })));
    assert.equal(responses.filter(response => response.status === 201).length, 6);
    assert.equal(responses.filter(response => response.status === 429).length, 6);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 6);
    const rates = f.sql.prepare('SELECT * FROM inquiry_rate_limits').all();
    assert.equal(JSON.stringify(rates).includes('198.51.100.7'), false);
    assert.equal(rates.find(row => row.key.startsWith('minute:')).count, 6);
    assert.equal(responses.find(response => response.status === 429).headers.get('retry-after'), '120');
    f.sql.prepare('UPDATE inquiry_rate_limits SET count = 300 WHERE key LIKE ?').run('global-hour:%');
    const keysBefore = f.sql.prepare('SELECT COUNT(*) AS n FROM inquiry_rate_limits').get().n;
    const blockedNewClient = await submit(f.service, brief(), { token: t, headers: { 'cf-connecting-ip': '203.0.113.99' } });
    assert.equal(blockedNewClient.status, 429);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiry_rate_limits').get().n, keysBefore);
  } finally { f.close(); }
});

await test('Malformed JSON, non-JSON media and oversized streaming bodies are rejected', async () => {
  const f = fixture();
  try {
    const t = await token(f.service);
    assert.equal((await submit(f.service, '{broken', { token: t })).status, 400);
    assert.equal((await submit(f.service, brief(), { token: t, headers: { 'content-type': 'text/plain' } })).status, 415);
    assert.equal((await submit(f.service, 'x'.repeat(25000), { token: t })).status, 413);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 0);
  } finally { f.close(); }
});

await test('Contact correction preserves creation hash, notice version and initial retry receipt', async () => {
  const f = fixture();
  try {
    const input = brief({ phone: '+33 6 00 00 00 00' });
    const receipt = await (await submit(f.service, input)).json();
    const before = f.sql.prepare('SELECT * FROM inquiries').get();
    const update = await f.service.update(request('/api/admin/briefs/' + input.requestId, { method: 'PATCH', headers: admin, payload: { revision: 1, status: 'reviewing', contact: { name: 'Nom corrigé', email: 'corrected@example.org', phone: '' } } }), input.requestId);
    assert.equal(update.status, 200);
    const updated = (await update.json()).inquiry;
    assert.equal(updated.revision, 2); assert.equal(updated.name, 'Nom corrigé'); assert.equal(updated.phone, undefined);
    const after = f.sql.prepare('SELECT * FROM inquiries').get();
    assert.equal(after.payload_hash, before.payload_hash);
    assert.equal(after.privacy_version, before.privacy_version);
    assert.equal(after.payload_json.includes('client@example.org'), false);
    const retried = await submit(f.service, input);
    assert.deepEqual((await retried.json()).receipt, receipt.receipt);
    const stale = await f.service.update(request('/api/admin/briefs/' + input.requestId, { method: 'PATCH', headers: admin, payload: { revision: 1, status: 'accepted' } }), input.requestId);
    assert.equal(stale.status, 409);
  } finally { f.close(); }
});

await test('Two administrators editing one revision cannot overwrite the winner', async () => {
  const f = fixture();
  try {
    const input = brief(); await submit(f.service, input);
    const update = status => f.service.update(request('/api/admin/briefs/' + input.requestId, { method: 'PATCH', headers: admin, payload: { revision: 1, status } }), input.requestId);
    const responses = await Promise.all([update('reviewing'), update('declined')]);
    assert.deepEqual(responses.map(response => response.status).sort(), [200, 409]);
    assert.equal(f.sql.prepare('SELECT revision FROM inquiries').get().revision, 2);
  } finally { f.close(); }
});

await test('Export is portable and checksum-verified; changed contents are rejected', async () => {
  const f = fixture();
  try {
    const input = brief({ dimensions: { heightMm: 1000 } }); await submit(f.service, input);
    const response = await f.service.export(request('/api/admin/briefs/' + input.requestId + '/export', { headers: admin }), input.requestId);
    assert.equal(response.status, 200); assert.match(response.headers.get('content-disposition'), /attachment/);
    const exported = await response.json();
    const verified = await verifyInquiryExport(exported); assert.equal(verified.inquiry.requestId, input.requestId);
    assert.equal(verified.inquiry.privacyVersion, '2026-10-19');
    assert.equal(verified.inquiry.website, undefined);
    await assert.rejects(() => verifyInquiryExport({ ...exported, inquiry: { ...exported.inquiry, quantity: 999 } }), error => error.code === 'checksum_mismatch');
    await writeFile(resolve(root, 'qa/inquiry-export-fixture.json'), JSON.stringify(exported, null, 2));
  } finally { f.close(); }
});

await test('Deletion removes all customer payload and blocks stale public retries', async () => {
  const f = fixture();
  try {
    const input = brief(); await submit(f.service, input);
    const make = () => request('/api/admin/briefs/' + input.requestId, { method: 'DELETE', headers: admin, payload: { revision: 1, confirmation: input.requestId } });
    const removed = await f.service.remove(make(), input.requestId); assert.equal(removed.status, 200);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 0);
    const tombstone = f.sql.prepare('SELECT * FROM inquiry_tombstones').get();
    assert.deepEqual(Object.keys(tombstone).sort(), ['deleted_at', 'request_id']);
    const retried = await submit(f.service, input); assert.equal(retried.status, 410);
    const removedAgain = await f.service.remove(make(), input.requestId); assert.equal(removedAgain.status, 200);
    assert.equal((await removedAgain.json()).replayed, true);
  } finally { f.close(); }
});

await test('Failed deletion transaction leaves original row and no false tombstone', async () => {
  const f = fixture();
  try {
    const input = brief(); await submit(f.service, input); f.hooks.failBatchAt = 1;
    const response = await f.service.remove(request('/api/admin/briefs/' + input.requestId, { method: 'DELETE', headers: admin, payload: { revision: 1, confirmation: input.requestId } }), input.requestId);
    assert.equal(response.status, 503);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiries').get().n, 1);
    assert.equal(f.sql.prepare('SELECT COUNT(*) AS n FROM inquiry_tombstones').get().n, 0);
  } finally { f.close(); }
});

await test('Deleted or stale records cannot be exported or silently updated', async () => {
  const f = fixture();
  try {
    const id = crypto.randomUUID();
    assert.equal((await f.service.detail(request('/api/admin/briefs/' + id, { headers: admin }), id)).status, 404);
    assert.equal((await f.service.export(request('/api/admin/briefs/' + id + '/export', { headers: admin }), id)).status, 404);
    assert.equal((await f.service.update(request('/api/admin/briefs/' + id, { method: 'PATCH', headers: admin, payload: { revision: 1, status: 'accepted' } }), id)).status, 404);
    assert.equal((await f.service.update(request('/api/admin/briefs/' + id, { method: 'PATCH', headers: { ...admin, origin: 'https://attacker.invalid' }, payload: { revision: 1, status: 'accepted' } }), id)).status, 403);
  } finally { f.close(); }
});

await test('Administrative pagination is bounded, stable and excludes full contact payloads', async () => {
  const f = fixture();
  try {
    for (let i = 0; i < 55; i++) {
      const input = normalizeInquiry(brief());
      f.sql.prepare('INSERT INTO inquiries (request_id,reference,payload_hash,payload_json,privacy_version,status,revision,created_at,updated_at) VALUES (?,?,?,?,?,?,1,?,?)').run(input.requestId, `BOJ-20261019-${i.toString(16).toUpperCase().padStart(12, '0')}`, await sha256(canonicalJSON(input)), canonicalJSON(input), '2026-10-19', i % 2 ? 'new' : 'reviewing', clock, clock);
    }
    const first = await (await f.service.list(request('/api/admin/briefs', { headers: admin }))).json();
    assert.equal(first.inquiries.length, 50); assert.ok(first.nextCursor);
    assert.equal(first.inquiries[0].email, undefined); assert.equal(first.inquiries[0].description, undefined);
    const second = await (await f.service.list(request('/api/admin/briefs?cursor=' + first.nextCursor, { headers: admin }))).json();
    assert.equal(second.inquiries.length, 5); assert.equal(second.nextCursor, null);
    assert.equal(new Set([...first.inquiries, ...second.inquiries].map(item => item.requestId)).size, 55);
    assert.equal(first.counts.new + first.counts.reviewing, 55);
    const filtered = await (await f.service.list(request('/api/admin/briefs?status=new', { headers: admin }))).json();
    assert.equal(filtered.inquiries.every(item => item.status === 'new'), true);
  } finally { f.close(); }
});

await test('A client already limited cannot exhaust the shared allowance for other visitors', async () => {
  const f = fixture();
  try {
    const t = await token(f.service);
    for (let i = 0; i < 305; i++) await submit(f.service, brief(), { token: t });
    assert.equal(f.sql.prepare('SELECT count FROM inquiry_rate_limits WHERE key LIKE ?').get('global-hour:%').count, 6);
    const other = await submit(f.service, brief(), { token: t, headers: { 'cf-connecting-ip': '203.0.113.91' } });
    assert.equal(other.status, 201);
  } finally { f.close(); }
});

await test('Concurrent over-limit attempts reserve only accepted quota and cannot poison other clients', async () => {
  const f = fixture();
  try {
    const t = await token(f.service);
    const replies = await Promise.all(Array.from({ length: 50 }, () => submit(f.service, brief(), { token: t })));
    assert.equal(replies.filter(item => item.status === 201).length, 6);
    const rates = f.sql.prepare('SELECT * FROM inquiry_rate_limits').all();
    assert.equal(rates.find(item => item.key.startsWith('global-hour:')).count, 6);
    assert.equal(rates.find(item => item.key.startsWith('day:')).count, 6);
    assert.equal((await submit(f.service, brief(), { token: t, headers: { 'cf-connecting-ip': '203.0.113.92' } })).status, 201);
  } finally { f.close(); }
});

await test('A clock correction cannot move the last modification before the preceding revision', async () => {
  const f = fixture(); const initial = clock;
  try {
    const input = brief(); await submit(f.service, input);
    const edit = revision => f.service.update(request('/api/admin/briefs/' + input.requestId, { method: 'PATCH', headers: admin, payload: { revision, status: 'reviewing' } }), input.requestId);
    clock += 60000;
    const first = (await (await edit(1)).json()).inquiry;
    clock -= 30000;
    const second = (await (await edit(2)).json()).inquiry;
    assert.ok(second.updatedAt >= first.updatedAt, `${second.updatedAt} precedes ${first.updatedAt}`);
  } finally { clock = initial; f.close(); }
});

const report = { version: 'bojart.acquisition.qa.v1', testedAt: new Date().toISOString(), engine: process.version, scope: 'Actual generated SQL in Node SQLite, real Request/Response/WebCrypto, D1 API adapter; no deployed database or live SIWC asserted.', groups: results.length, passed: results.filter(result => result.status === 'passed').length, failed: results.filter(result => result.status === 'failed').length, results };
await writeFile(resolve(root, 'qa/acquisition-results.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ groups: report.groups, passed: report.passed, failed: report.failed }));
if (report.failed) process.exitCode = 1;
