import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {mkdtemp, mkdir, rm, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {Readable, Writable} from 'node:stream';
import {createGatewayHandler} from '../local/jev-gateway.mjs';
import {createWorkshopRepository, defaultWorkshopDirectory, WORKSHOP_LIMITS, WorkshopError} from '../local/workshop-repository.mjs';
import {createWorkshopBackup, inspectWorkshopBackup} from '../dist/lib/workshop-backup.js';
import {replayWorkshopAuthority} from '../dist/lib/workshop.js';

// Real temporary SQLite files and handler streams; no listening server or printer.
const checks = [], opened = new Set();
const directory = await mkdtemp(join(tmpdir(), 'boj-workshop-qa-'));
const seed = {version: 1, at: Date.UTC(2026, 9, 18, 12)};
const at = seed.at + 1000;
const clone = value => structuredClone(value);
const code = expected => error => error instanceof WorkshopError && error.code === expected;
async function check(name, run) { await run(); checks.push(name); }
function repository(name) {
  const repo = createWorkshopRepository({directory: join(directory, name), now: () => at});
  opened.add(repo);
  return repo;
}
function operation(id, patch = {notes: 'Essai du journal'}, clock = 1) {
  return {version: 1, id, clock, at, type: 'UPDATE_PROJECT', payload: {id: 'sculpture-xl', patch}, expected: {entityVersion: Math.max(0, clock - 1)},
    context: {projectId: 'sculpture-xl', projectName: 'SCULPTURE XL', pieceId: null, machineId: null, originProjectId: 'sculpture-xl'}};
}
const batch = (repo, operations) => ({version: 2, workspaceId: repo.status().workspaceId, seed, operations});
function replayOf(repo) { const backup = repo.backup(); return replayWorkshopAuthority(backup.seed, backup.operations, backup.authority); }
function projectOf(repo) { return replayOf(repo).state.projects.find(p => p.id === 'sculpture-xl'); }

class MockResponse extends Writable {
  statusCode = null; headers = {}; headersSent = false; chunks = [];
  writeHead(status, headers) { this.statusCode = status; this.headers = headers; this.headersSent = true; return this; }
  _write(chunk, encoding, callback) { this.chunks.push(Buffer.from(chunk)); callback(); }
  bytes() { return Buffer.concat(this.chunks); }
  json() { return JSON.parse(this.bytes().toString('utf8')); }
}
async function invoke(handler, {method = 'GET', url = '/api/workshop/status', body, headers = {}} = {}) {
  const bytes = body === undefined ? null : Buffer.isBuffer(body) ? body : Buffer.from(typeof body === 'string' ? body : JSON.stringify(body));
  const request = Readable.from(bytes ? [bytes] : []);
  request.method = method; request.url = url;
  request.headers = {host: '127.0.0.1:3137', ...(method === 'POST' ? {origin: 'http://127.0.0.1:3137', 'content-type': 'application/json'} : {}), ...headers};
  for (const [key, value] of Object.entries(request.headers)) if (value === undefined) delete request.headers[key];
  const response = new MockResponse();
  const finished = new Promise(resolve => { response.once('finish', resolve); response.once('close', resolve); });
  await handler(request, response); await finished;
  assert.equal(Object.keys(response.headers).some(key => /^access-control-allow-origin$/i.test(key)), false);
  return response;
}

try {
  await check('Base vierge : identité durable, graine absente, limites et capacités exactes', async () => {
    const repo = repository('identity'), status = repo.status();
    assert.equal(status.seed, null); assert.equal(status.cursor, 0); assert.equal(status.operationCount, 0);
    assert.equal(status.durable, true); assert.equal(status.storage, 'sqlite');
    assert.deepEqual(status.capabilities, {printerCommands: false, stlStorage: false, businessReceipts: true, persistedGenesis: true});
    assert.equal(status.version, 2);
    assert.equal(status.limits.maxBackupBytes, 16777216);
    assert.throws(() => repo.backup(), code('not_initialized'));
    repo.close();
    const reopened = repository('identity');
    assert.equal(reopened.status().instanceId, status.instanceId);
    assert.equal(reopened.status().seed, null);
    assert.throws(() => defaultWorkshopDirectory({BOJ_WORKSHOP_DATA_DIR: 'relative'}), code('invalid_configuration'));
  });

  await check('Fichier préexistant vide ou métadonnées manquantes : démarrage refusé sans nouvelle identité', async () => {
    const empty = join(directory, 'empty-existing'); await mkdir(empty);
    await writeFile(join(empty, 'workshop.sqlite3'), '');
    assert.throws(() => createWorkshopRepository({directory: empty}), code('storage_unavailable'));
    const repo = repository('incomplete-existing'); repo.append(batch(repo, [operation('keep-existing')])); repo.close();
    const db = new DatabaseSync(join(directory, 'incomplete-existing', 'workshop.sqlite3'));
    db.prepare('DELETE FROM metadata WHERE key = ?').run('instance_id');
    db.close();
    assert.throws(() => createWorkshopRepository({directory: join(directory, 'incomplete-existing')}), code('storage_unavailable'));
    const preserved = new DatabaseSync(join(directory, 'incomplete-existing', 'workshop.sqlite3'), {readOnly: true});
    assert.equal(preserved.prepare('SELECT COUNT(*) AS count FROM operations').get().count, 1);
    assert.equal(preserved.prepare('SELECT value FROM metadata WHERE key = ?').get('instance_id'), undefined);
    preserved.close();
  });

  await check('Deux clients concurrents : un reçu accepté, un refus métier stable sur une version périmée', () => {
    const first = repository('shared'), second = repository('shared');
    assert.equal(first.status().cursor, second.status().cursor);
    first.append(batch(first, [operation('concurrent-a', {notes: 'Notes de l’écran atelier'}, 1)]));
    second.append(batch(second, [operation('concurrent-b', {subtitle: 'Sous-titre du poste central'}, 1)]));
    const state = projectOf(first);
    assert.equal(state.notes, 'Notes de l’écran atelier');
    assert.equal(second.operations().receipts[1].outcome.ok, false);
    assert.notEqual(state.subtitle, 'Sous-titre du poste central');
    assert.equal(first.status().operationCount, 2);
    assert.deepEqual(first.operations(1).operations.map(op => op.id), ['concurrent-b']);
    assert.equal(first.operations(2).operations.length, 0);
  });

  await check('Identifiants immuables : nouvelle tentative dédupliquée, lot conflictuel sans écriture partielle', () => {
    const repo = repository('immutable'), original = operation('unique-a');
    assert.deepEqual(repo.append(batch(repo, [original, clone(original)])).accepted, ['unique-a']);
    const reordered = {...original, payload: {patch: {notes: 'Essai du journal'}, id: 'sculpture-xl'}};
    const retry = repo.append(batch(repo, [reordered]));
    assert.deepEqual(retry.accepted, []); assert.deepEqual(retry.duplicates, ['unique-a']);
    assert.throws(() => repo.append(batch(repo, [operation('new-before-conflict'), operation('unique-a', {notes: 'Autre valeur'})])), code('operation_id_conflict'));
    assert.equal(repo.status().operationCount, 1);
    assert.throws(() => repo.append(batch(repo, [operation('conflict-within'), operation('conflict-within', {notes: 'Différent'})])), code('operation_id_conflict'));
    assert.equal(repo.status().operationCount, 1);
  });

  await check('Graine divergente refusée et reprise des travaux simulés sans doublons après réouverture', () => {
    let repo = repository('jobs');
    const plan = {...operation('plan-a'), type: 'PLAN_PROJECT', payload: {projectId: 'sculpture-xl'}};
    repo.append(batch(repo, [plan]));
    const previous = replayOf(repo).state.jobs;
    assert.throws(() => repo.append({version: 2, workspaceId: repo.status().workspaceId, seed: {...seed, at: seed.at + 10}, operations: [operation('foreign')]}), code('seed_conflict'));
    repo.close(); repo = repository('jobs');
    repo.append(batch(repo, [plan, {...plan, id: 'plan-b', clock: 2}]));
    const current = replayOf(repo).state.jobs;
    assert.equal(current.length, previous.length);
    assert.equal(new Set(current.map(job => job.id)).size, current.length);
    assert.equal(current.every(job => job.simulated === true), true);
    assert.deepEqual(repo.status().seed, seed);
  });

  await check('Fiches du parc et conflits conservés dans le journal sans qualifier une machine', () => {
    const repo = repository('registry');
    const raw = {origin: 'declared', manufacturer: 'Fabricant de test', model: 'Modèle à qualifier', technology: 'fdm', notes: 'Version A'};
    const registry = {...operation('registry-a'), type: 'UPDATE_MACHINE', payload: {id: 'P01', expectedRegistryRevision: 0, patch: {registry: raw}}, context: {...operation('x').context, machineId: 'P01'}};
    const stale = {...registry, id: 'registry-b', payload: {...registry.payload, patch: {registry: {...raw, notes: 'Version concurrente B'}}}};
    repo.append(batch(repo, [registry])); repo.append(batch(repo, [stale]));
    const replay = replayOf(repo);
    const machine = replay.state.machines.find(item => item.id === 'P01');
    assert.equal(machine.registry.notes, 'Version A');
    assert.equal(machine.registry.revision, 1);
    assert.equal(machine.qualified, false);
    assert.equal(replay.results.get('registry-b').ok, false);
    assert.equal(repo.backup().operations.find(op => op.id === 'registry-b').payload.patch.registry.notes, 'Version concurrente B');
  });

  await check('Sauvegardes navigateur et serveur compatibles, empreinte SHA-256 vérifiée', async () => {
    const repo = repository('backup');
    const browser = await createWorkshopBackup({seed, operations: [operation('browser-a')]}, {sourceInstanceId: 'browser', now: at});
    repo.restore(browser);
    const server = repo.backup();
    assert.deepEqual(server.excludes, ['stl_binaries', 'credentials', 'printer_state']);
    const inspected = await inspectWorkshopBackup(server);
    assert.equal(inspected.summary.operations, 1);
    assert.equal(inspected.backup.sourceInstanceId, repo.status().instanceId);
    const changed = clone(server); changed.operations[0].payload.patch.notes = 'Fichier modifié';
    assert.throws(() => repo.restore(changed), code('checksum_mismatch'));
    assert.equal(repo.status().operationCount, 1);
    const otherBrowser = await createWorkshopBackup({seed, operations: [operation('window-a', {notes: 'Import fenêtre'}, 2)]}, {sourceInstanceId: 'window-01234567-89ab-cdef-0123-456789abcdef', now: at});
    assert.throws(() => repo.restore(otherBrowser), code('legacy_merge_requires_review'));
    assert.equal(repo.status().operationCount, 1);
  });

  await check('Restauration additive : les modifications récentes restent présentes', async () => {
    const source = repository('restore-source'), destination = repository('restore-destination');
    source.append(batch(source, [operation('old-a')]));
    const backup = source.backup();
    destination.restore(backup);
    destination.append(batch(destination, [operation('newer-a', {subtitle: 'À conserver'}, 2)]));
    assert.equal(destination.restore(backup).accepted.length, 0);
    assert.equal(projectOf(destination).subtitle, 'À conserver');
    assert.equal(destination.status().operationCount, 2);
    assert.notEqual(destination.status().instanceId, source.status().instanceId);
    const incompatible = await createWorkshopBackup({seed: {...seed, at: seed.at + 100}, operations: [operation('foreign-backup')]}, {now: at});
    assert.throws(() => destination.restore(incompatible), code('seed_conflict'));
    assert.equal(destination.status().operationCount, 2);
  });

  await check('Validation des enveloppes, tailles, types, données imbriquées et commandes inconnues', () => {
    const repo = repository('validation');
    const mutations = [
      op => { op.type = 'START_REAL_PRINT'; }, op => { op.clock = 1.2; }, op => { op.at = Infinity; },
      op => { op.payload.patch.startPrinter = true; }, op => { op.context.projectId = null; },
      op => { op.payload.patch.notes = 'x'.repeat(70000); }, op => { op.payload.patch.notes = {nested: {value: true}}; },
      op => { op.payload = JSON.parse('{"__proto__":{"polluted":true}}'); }
    ];
    for (const mutate of mutations) { const bad = operation('bad-operation'); mutate(bad); assert.throws(() => repo.append(batch(repo, [bad])), error => error instanceof WorkshopError); }
    assert.throws(() => repo.append({...batch(repo, []), url: 'http://printer.invalid'}), code('invalid_operation'));
    assert.throws(() => repo.append(batch(repo, Array.from({length: 101}, (_, i) => operation('many-' + i)))), code('batch_too_large'));
    assert.equal(repo.status().seed, null); assert.equal(repo.status().operationCount, 0);
    assert.equal({}.polluted, undefined);
  });

  await check('Pagination complète : aucune opération omise ou répétée entre deux pages', () => {
    const repo = repository('paging');
    for (const start of [0, 100, 200]) repo.append(batch(repo, Array.from({length: start === 200 ? 5 : 100}, (_, i) => operation('page-' + (start + i), {notes: 'Ligne ' + (start + i)}, start + i + 1))));
    const first = repo.operations(0), second = repo.operations(first.nextCursor);
    assert.equal(first.operations.length, 200); assert.equal(first.hasMore, true);
    assert.equal(second.operations.length, 5); assert.equal(second.hasMore, false);
    assert.equal(new Set([...first.operations, ...second.operations].map(op => op.id)).size, 205);
    assert.equal(second.nextCursor, second.cursor);
    assert.throws(() => repo.operations(second.cursor + 1), code('cursor_out_of_range'));
    assert.throws(() => repo.operations(-1), code('invalid_cursor'));
  });

  await check('Corruption logique détectée : aucune réinitialisation silencieuse du fichier SQLite', () => {
    const repo = repository('integrity'); repo.append(batch(repo, [operation('integrity-a')]));
    const db = new DatabaseSync(join(directory, 'integrity', 'workshop.sqlite3'));
    db.prepare('UPDATE operations SET digest = ? WHERE id = ?').run('0'.repeat(64), 'integrity-a'); db.close();
    assert.throws(() => repo.operations(), code('storage_unavailable'));
    assert.throws(() => repo.append(batch(repo, [operation('integrity-b')])), code('storage_unavailable'));
    assert.equal(repo.status().operationCount, 1);
  });

  const dist = join(directory, 'dist'); await mkdir(dist);
  await writeFile(join(dist, 'index.html'), '<!doctype html><title>BOJ.ART</title>');
  await writeFile(join(dist, 'clip.mp4'), '0123456789');
  const apiRepo = repository('api');
  let decisions = 0;
  const provider = {status: () => ({ok: true, configured: false, connected: false}), decide: async () => { decisions++; return {ok: true}; }};
  const handler = createGatewayHandler({provider, workshop: apiRepo, distDirectory: dist});

  await check('Routes HTTP de journal et sauvegarde, sans appel Jev ni équipement', async () => {
    assert.equal((await invoke(handler)).json().seed, null);
    const emptyBackup = await invoke(handler, {url: '/api/workshop/backup'});
    assert.equal(emptyBackup.statusCode, 409); assert.equal(emptyBackup.json().code, 'not_initialized');
    const largeStory = {...operation('http-story'), type: 'SAVE_STORY', payload: {projectId: 'sculpture-xl', text: 'x'.repeat(19000)}};
    const pushed = await invoke(handler, {method: 'POST', url: '/api/workshop/operations', body: batch(apiRepo, [largeStory])});
    assert.equal(pushed.statusCode, 200); assert.deepEqual(pushed.json().accepted, ['http-story']);
    assert.equal((await invoke(handler, {url: '/api/workshop/operations?after=0'})).json().operations.length, 1);
    const backup = await invoke(handler, {url: '/api/workshop/backup'});
    assert.equal(backup.statusCode, 200); assert.equal((await inspectWorkshopBackup(backup.json())).summary.operations, 1);
    const restored = await invoke(handler, {method: 'POST', url: '/api/workshop/backup', body: backup.json()});
    assert.equal(restored.statusCode, 200); assert.deepEqual(restored.json().duplicates, ['http-story']);
    assert.equal(decisions, 0);
  });

  await check('Protections Host, Origin, JSON, taille, curseur et méthodes maintenues', async () => {
    const forbidden = [
      {headers: {host: 'malicious.example:3137'}}, {headers: {origin: 'https://malicious.example'}},
      {headers: {'sec-fetch-site': 'cross-site'}},
      {method: 'POST', url: '/api/workshop/operations', body: batch(apiRepo, []), headers: {origin: undefined}},
      {method: 'POST', url: '/api/workshop/operations', body: batch(apiRepo, []), headers: {'content-type': 'text/plain'}},
      {method: 'POST', url: '/api/workshop/operations', body: '{'},
      {method: 'POST', url: '/api/workshop/operations', body: batch(apiRepo, []), headers: {'content-length': String(WORKSHOP_LIMITS.maxRequestBytes + 1)}},
      {url: '/api/workshop/operations?after=0&after=1'}, {url: '/api/workshop/operations?after=-1'},
      {method: 'DELETE', url: '/api/workshop/operations'}
    ];
    for (const input of forbidden) { const response = await invoke(handler, input); assert.equal(response.statusCode >= 400, true); }
    assert.equal(apiRepo.status().operationCount, 1);
    const head = await invoke(handler, {method: 'HEAD'}); assert.equal(head.statusCode, 200); assert.equal(head.bytes().length, 0);
    const unconfigured = await invoke(createGatewayHandler({provider, distDirectory: dist}));
    assert.equal(unconfigured.statusCode, 503); assert.equal(unconfigured.json().code, 'unconfigured');
  });

  await check('Fichiers publics et lecture vidéo Range préservés ; base locale non publiée', async () => {
    const range = await invoke(handler, {url: '/clip.mp4', headers: {range: 'bytes=2-5'}});
    assert.equal(range.statusCode, 206); assert.equal(range.bytes().toString(), '2345');
    assert.equal((await invoke(handler, {url: '/'})).statusCode, 200);
    assert.equal((await invoke(handler, {url: '/../api/workshop.sqlite3'})).statusCode, 404);
    assert.equal((await invoke(handler, {url: '/workshop.sqlite3'})).statusCode, 404);
    const visualStatus = await invoke(handler, {url: '/api/visual-decision/status'});
    assert.equal(visualStatus.statusCode, 200); assert.equal(visualStatus.json().configured, false);
    assert.equal(decisions, 0);
  });

  const report = {status: 'passed', checks: checks.length, tests: checks, environment: {node: process.version, sqlite: 'real temporary files', http: 'injected handler streams', listeningServer: false, browser: false, printers: false, jevApi: false}};
  await writeFile(new URL('./workshop-backend-results.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
  process.stdout.write(JSON.stringify(report, null, 2) + '\n');
} finally {
  for (const repo of opened) { try { repo.close(); } catch { /* continue fixture cleanup */ } }
  await rm(directory, {recursive: true, force: true});
}
