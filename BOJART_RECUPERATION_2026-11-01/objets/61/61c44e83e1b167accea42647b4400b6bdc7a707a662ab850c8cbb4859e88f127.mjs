import assert from 'node:assert/strict';
import {mkdtemp, writeFile, mkdir, symlink, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {Readable, Writable} from 'node:stream';
import {createGatewayHandler} from '../local/jev-gateway.mjs';
import {
  buildTypeSafeRequest, createJevProvider, DEFAULT_JEV_MODEL, JevError,
  normalizeTypeSafeResponse, normalizeVisualRequest, TYPESAFE_ENDPOINT
} from '../local/jev-provider.mjs';

// No listening socket, real credentials, upstream API, or browser is used.
const checks = [];
async function check(name, run) { await run(); checks.push(name); }
const secret = 'test-secret-never-print';
const request = {
  requestId: 'visual-17', command: 'Montre le modèle de cette pièce',
  context: {projectId: 'project-a', projectRevision: 4, pieceId: 'piece-b', pieceRevision: 2},
  availableViews: ['model', 'art', 'film', 'production']
};
const fixture = (choice = 'model', probabilities = {model: .88, art: .04, film: .03, production: .02, none: .03}) => ({
  model: DEFAULT_JEV_MODEL,
  answers: {visual: {type: 'choice', choice, confidence: .85, probabilities}},
  usage: {input_tokens: 342, output_tokens: 22}
});
const jsonResponse = (body, {status = 200, headers = {}} = {}) => new Response(JSON.stringify(body), {status, headers: {'Content-Type': 'application/json', ...headers}});
const clone = value => structuredClone(value);
const assertCode = code => error => error instanceof JevError && error.code === code && !error.message.includes(secret);

class MockResponse extends Writable {
  statusCode = null;
  headers = {};
  headersSent = false;
  chunks = [];
  writeHead(statusCode, headers) { this.statusCode = statusCode; this.headers = headers; this.headersSent = true; return this; }
  _write(chunk, encoding, callback) { this.chunks.push(Buffer.from(chunk)); callback(); }
  bytes() { return Buffer.concat(this.chunks); }
  json() { return JSON.parse(this.bytes().toString('utf8')); }
}

async function invoke(handler, {method = 'GET', url = '/', body, headers = {}} = {}) {
  const bytes = body === undefined ? null : Buffer.isBuffer(body) ? body : Buffer.from(typeof body === 'string' ? body : JSON.stringify(body));
  const stream = Readable.from(bytes ? [bytes] : []);
  stream.method = method;
  stream.url = url;
  stream.headers = {
    host: '127.0.0.1:3137',
    ...(method === 'POST' ? {origin: 'http://127.0.0.1:3137', 'content-type': 'application/json'} : {}),
    ...headers
  };
  for (const [name, value] of Object.entries(stream.headers)) if (value === undefined) delete stream.headers[name];
  const response = new MockResponse();
  const finished = new Promise(resolveFinish => { response.once('finish', resolveFinish); response.once('close', resolveFinish); });
  await handler(stream, response);
  await finished;
  assert.equal(Object.keys(response.headers).some(key => /^access-control-allow-origin$/i.test(key)), false, 'No CORS access is granted');
  return response;
}

await check('Contrat borné, copie de contexte et paire pièce/révision', () => {
  const normalized = normalizeVisualRequest(request);
  assert.deepEqual(normalized, request);
  normalized.context.projectRevision = 99;
  assert.equal(request.context.projectRevision, 4);
  const projectOnly = clone(request);
  delete projectOnly.context.pieceId;
  delete projectOnly.context.pieceRevision;
  assert.deepEqual(normalizeVisualRequest(projectOnly).context, {projectId: 'project-a', projectRevision: 4});
  const mutations = [
    value => { value.url = 'https://example.invalid'; },
    value => { value.apiKey = secret; },
    value => { value.model = 'another-model'; },
    value => { value.context.action = 'start_print'; },
    value => { delete value.context.pieceRevision; },
    value => { delete value.context.pieceId; },
    value => { value.context.projectRevision = 0; },
    value => { value.context.pieceRevision = 1.2; },
    value => { value.availableViews = ['start_print']; },
    value => { value.availableViews = ['model', 'model']; },
    value => { value.availableViews = []; },
    value => { value.availableViews = ['none']; },
    value => { value.command = 'x'.repeat(2001); },
    value => { value.requestId = ' '; }
  ];
  for (const mutate of mutations) { const bad = clone(request); mutate(bad); assert.throws(() => normalizeVisualRequest(bad), assertCode('invalid_request')); }
  const polluted = JSON.parse(JSON.stringify(request).replace('"requestId"', '"__proto__":{},"requestId"'));
  assert.throws(() => normalizeVisualRequest(polluted), assertCode('invalid_request'));
});

await check('Requête officielle : endpoint fixe, critères disponibles et none, modèle figé', () => {
  const built = buildTypeSafeRequest({...request, availableViews: ['film', 'model']});
  assert.equal(built.model, 'jev-1.13.0');
  assert.deepEqual(Object.keys(built.questions.visual.criteria), ['model', 'film', 'none']);
  assert.deepEqual(built.state.context, request.context);
  assert.equal(built.questions.visual.type, 'choice');
  assert.equal(Object.hasOwn(built, 'tools'), false);
  assert.equal(buildTypeSafeRequest(request, {model: 'jev-preview'}).model, 'jev-preview');
  assert.throws(() => buildTypeSafeRequest(request, {model: 'https://elsewhere.invalid'}), assertCode('invalid_configuration'));
});

await check('Décision réelle validée et scores conservés sans écriture de projet', () => {
  const result = normalizeTypeSafeResponse(fixture(), request);
  assert.equal(result.decision.view, 'model');
  assert.equal(result.decision.selectedView, 'model');
  assert.equal(result.decision.reason, 'selected');
  assert.equal(result.decision.probability, .88);
  assert.equal(result.model, 'jev-1.13.0');
  assert.deepEqual(result.context, request.context);
  assert.equal(result.requestId, request.requestId);
  assert.deepEqual(Object.keys(result).sort(), ['context', 'decision', 'model', 'ok', 'provider', 'requestId', 'usage']);
});

await check('Abstention sur incertitude, égalité et choix none', () => {
  const uncertain = normalizeTypeSafeResponse(fixture('model', {model: .6, art: .2, film: .1, production: .05, none: .05}), request);
  assert.equal(uncertain.decision.view, 'none');
  assert.equal(uncertain.decision.selectedView, 'model');
  assert.equal(uncertain.decision.reason, 'uncertain');
  const tie = normalizeTypeSafeResponse(fixture('model', {model: .5, art: .5, film: 0, production: 0, none: 0}), request, {minProbability: .5});
  assert.equal(tie.decision.view, 'none');
  const none = normalizeTypeSafeResponse(fixture('none', {model: .05, art: .02, film: .01, production: .02, none: .9}), request);
  assert.equal(none.decision.view, 'none');
  assert.equal(none.decision.reason, 'no_match');
  const boundary = normalizeTypeSafeResponse(fixture('model', {model: .8, art: .1, film: .05, production: .03, none: .02}), request);
  assert.equal(boundary.decision.view, 'model');
});

await check('Réponses invalides : schéma, modèle effectif, distribution et choix refusés', () => {
  const mutations = [
    value => { delete value.model; },
    value => { value.model = 'jev-latest'; },
    value => { value.model = 'jev-1.14.0'; },
    value => { value.answers.visual.choice = 'delete'; },
    value => { value.answers.visual.choice = 'art'; },
    value => { value.answers.visual.type = 'noul'; },
    value => { value.answers.visual.probabilities.extra = .1; },
    value => { delete value.answers.visual.probabilities.none; },
    value => { value.answers.visual.probabilities.model = .4; },
    value => { value.answers.visual.probabilities.model = NaN; },
    value => { value.answers.visual.confidence = 2; },
    value => { delete value.usage; },
    value => { value.usage.input_tokens = -1; },
    value => { value.answers.other_question = {}; }
  ];
  for (const mutate of mutations) { const bad = fixture(); mutate(bad); assert.throws(() => normalizeTypeSafeResponse(bad, request), assertCode('invalid_response')); }
  const subset = {...request, availableViews: ['film']};
  assert.throws(() => normalizeTypeSafeResponse(fixture(), subset), assertCode('invalid_response'));
  const acceptedAlias = fixture();
  acceptedAlias.model = 'jev-1.14.0';
  assert.equal(normalizeTypeSafeResponse(acceptedAlias, request, {model: 'jev-preview'}).model, 'jev-1.14.0');
});

await check('Sans clé : aucun appel, statut non configuré', async () => {
  let called = 0;
  const provider = createJevProvider({fetchImpl: () => { called++; throw new Error('must not run'); }});
  assert.equal(provider.status().configured, false);
  assert.equal(provider.status().connected, false);
  assert.equal(provider.status().availability, 'unconfigured');
  await assert.rejects(provider.decide(request), assertCode('unconfigured'));
  assert.equal(called, 0);
});

await check('Clé serveur, zéro appel au statut, connexion uniquement après réponse vérifiée', async () => {
  const calls = [];
  const provider = createJevProvider({apiKey: secret, now: () => Date.UTC(2026, 9, 18), fetchImpl: async (url, options) => {
    calls.push({url, options});
    return jsonResponse(fixture());
  }});
  assert.equal(provider.status().configured, true);
  assert.equal(provider.status().connected, false);
  assert.equal(provider.status().availability, 'configured');
  assert.equal(calls.length, 0);
  const result = await provider.decide(request);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, TYPESAFE_ENDPOINT);
  assert.equal(calls[0].options.headers.Authorization, `Bearer ${secret}`);
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.signal instanceof AbortSignal, true);
  assert.equal(JSON.parse(calls[0].options.body).model, DEFAULT_JEV_MODEL);
  assert.equal(JSON.stringify(result).includes(secret), false);
  assert.equal(JSON.stringify(provider.status()).includes(secret), false);
  assert.equal(provider.status().connected, true);
  assert.equal(provider.status().lastVerifiedAt, '2026-10-18T00:00:00.000Z');
});

await check('Un échec suivant retire le statut connecté et conserve la dernière vérification datée', async () => {
  let succeed = true;
  const provider = createJevProvider({apiKey: secret, fetchImpl: async () => succeed ? jsonResponse(fixture()) : new Response(secret, {status: 401})});
  await provider.decide(request);
  const date = provider.status().lastVerifiedAt;
  succeed = false;
  await assert.rejects(provider.decide(request), assertCode('authentication'));
  assert.equal(provider.status().connected, false);
  assert.equal(provider.status().availability, 'configured');
  assert.equal(provider.status().lastVerifiedAt, date);
});

await check('Erreurs réseau et fournisseur normalisées sans exception ou corps amont', async () => {
  for (const [status, code] of [[403, 'authentication'], [429, 'rate_limited'], [529, 'rate_limited'], [500, 'upstream_error']]) {
    const provider = createJevProvider({apiKey: secret, fetchImpl: async () => new Response(secret, {status})});
    await assert.rejects(provider.decide(request), assertCode(code));
  }
  const provider = createJevProvider({apiKey: secret, fetchImpl: async () => { throw new Error(secret); }});
  await assert.rejects(provider.decide(request), assertCode('unavailable'));
});

await check('Délai borné et appel concurrent refusé sans second envoi', async () => {
  let calls = 0;
  let signal;
  const provider = createJevProvider({apiKey: secret, timeoutMs: 20, fetchImpl: async (url, options) => {
    calls++;
    signal = options.signal;
    return new Promise(() => {});
  }});
  const first = provider.decide(request);
  const firstRejected = assert.rejects(first, assertCode('timeout'));
  await assert.rejects(provider.decide({...request, requestId: 'other'}), assertCode('busy'));
  await firstRejected;
  assert.equal(signal.aborted, true);
  assert.equal(calls, 1);
  assert.equal(provider.status().connected, false);
});

await check('Corps fournisseur borné, type JSON et UTF-8 vérifiés', async () => {
  const responses = [
    new Response(JSON.stringify(fixture()), {headers: {'Content-Type': 'text/html'}}),
    jsonResponse(fixture(), {headers: {'Content-Length': '70000'}}),
    jsonResponse({payload: 'x'.repeat(70000)}),
    new Response(new Uint8Array([0xc3, 0x28]), {headers: {'Content-Type': 'application/json'}})
  ];
  for (const response of responses) {
    const provider = createJevProvider({apiKey: secret, fetchImpl: async () => response});
    await assert.rejects(provider.decide(request), assertCode('invalid_response'));
  }
});

const directory = await mkdtemp(join(tmpdir(), 'boj-jev-qa-'));
try {
  const dist = join(directory, 'dist');
  await mkdir(dist);
  await writeFile(join(dist, 'index.html'), '<!doctype html><title>BOJ.ART</title>');
  await writeFile(join(dist, 'clip.mp4'), Buffer.from('0123456789'));
  await writeFile(join(directory, 'private.json'), JSON.stringify({secret}));
  await symlink(join(directory, 'private.json'), join(dist, 'outside.json'));
  let calls = 0;
  const provider = {
    status: () => ({ok: true, configured: false, connected: false, availability: 'unconfigured', model: DEFAULT_JEV_MODEL}),
    decide: async input => { calls++; return normalizeTypeSafeResponse(fixture(), input); }
  };
  const handler = createGatewayHandler({provider, distDirectory: dist});

  await check('Statut et dashboard servis sans appel au modèle, HEAD sans corps', async () => {
    const status = await invoke(handler, {url: '/api/visual-decision/status'});
    assert.equal(status.statusCode, 200);
    assert.equal(status.json().connected, false);
    const page = await invoke(handler);
    assert.equal(page.statusCode, 200);
    assert.match(page.bytes().toString(), /BOJ\.ART/);
    const head = await invoke(handler, {method: 'HEAD'});
    assert.equal(head.bytes().length, 0);
    assert.equal(head.headers['Content-Length'], page.bytes().length);
    assert.equal(calls, 0);
  });

  await check('POST valide transmis une seule fois avec contexte précis et retour normalisé', async () => {
    const result = await invoke(handler, {method: 'POST', url: '/api/visual-decision', body: request});
    assert.equal(result.statusCode, 200);
    assert.equal(result.json().requestId, request.requestId);
    assert.deepEqual(result.json().context, request.context);
    assert.equal(result.json().decision.view, 'model');
    assert.equal(calls, 1);
  });

  await check('Host, Origin et origine navigateur extérieurs refusés avant fournisseur', async () => {
    const attempts = [
      {host: 'attacker.example:3137'},
      {origin: 'https://attacker.example'},
      {origin: 'null'},
      {origin: undefined},
      {'sec-fetch-site': 'cross-site'},
      {origin: 'http://127.0.0.1:3138'},
      {host: '127.0.0.1:3137@attacker.example'}
    ];
    for (const headers of attempts) {
      const result = await invoke(handler, {method: 'POST', url: '/api/visual-decision', body: request, headers});
      assert.equal(result.statusCode, 403);
      assert.equal(result.json().code, 'origin_rejected');
    }
    assert.equal(calls, 1);
  });

  await check('JSON, taille, schéma et méthode invalides refusés sans appel', async () => {
    for (const [options, status] of [
      [{method: 'POST', body: '{bad'}, 400],
      [{method: 'POST', body: request, headers: {'content-type': 'text/plain'}}, 415],
      [{method: 'POST', body: 'x'.repeat(17000)}, 413],
      [{method: 'POST', body: request, headers: {'content-length': '20000'}}, 413],
      [{method: 'POST', body: {...request, endpoint: 'https://elsewhere.invalid'}}, 400],
      [{method: 'POST', body: Buffer.from([0xc3, 0x28])}, 400],
      [{method: 'GET'}, 405],
      [{method: 'OPTIONS'}, 405]
    ]) {
      const result = await invoke(handler, {url: '/api/visual-decision', ...options});
      assert.equal(result.statusCode, status);
    }
    assert.equal(calls, 1);
  });

  await check('Dossier dist seul : traversée, lien externe, fichiers cachés et API inconnue exclus', async () => {
    for (const url of ['/../private.json', '/%2e%2e/private.json', '/%2e%2e%2fprivate.json', '/outside.json', '/local/jev-provider.mjs', '/.env', '/api/start-print', '/%5c..%5cprivate.json']) {
      const result = await invoke(handler, {url});
      assert.equal(result.statusCode, 404, url);
      assert.equal(result.bytes().toString().includes(secret), false);
    }
  });

  await check('Lecture vidéo : octets complets, Range, suffixe, HEAD et borne invalide', async () => {
    const full = await invoke(handler, {url: '/clip.mp4'});
    assert.equal(full.bytes().toString(), '0123456789');
    const range = await invoke(handler, {url: '/clip.mp4', headers: {range: 'bytes=2-5'}});
    assert.equal(range.statusCode, 206);
    assert.equal(range.bytes().toString(), '2345');
    assert.equal(range.headers['Content-Range'], 'bytes 2-5/10');
    const suffix = await invoke(handler, {url: '/clip.mp4', headers: {range: 'bytes=-3'}});
    assert.equal(suffix.bytes().toString(), '789');
    const head = await invoke(handler, {method: 'HEAD', url: '/clip.mp4', headers: {range: 'bytes=2-'}});
    assert.equal(head.headers['Content-Length'], 8);
    assert.equal(head.bytes().length, 0);
    for (const range of ['bytes=50-', 'bytes=0-1,5-6', 'bytes=-0', 'bad']) {
      const invalid = await invoke(handler, {url: '/clip.mp4', headers: {range}});
      assert.equal(invalid.statusCode, 416);
      assert.equal(invalid.bytes().length, 0);
    }
  });

  await check('Exceptions inattendues masquées dans les réponses HTTP', async () => {
    const broken = createGatewayHandler({distDirectory: dist, provider: {status: () => { throw new Error(secret); }, decide: async () => { throw new Error(secret); }}});
    const status = await invoke(broken, {url: '/api/visual-decision/status'});
    assert.equal(status.statusCode, 500);
    assert.equal(status.bytes().toString().includes(secret), false);
    const decision = await invoke(broken, {method: 'POST', url: '/api/visual-decision', body: request});
    assert.equal(decision.statusCode, 500);
    assert.equal(decision.bytes().toString().includes(secret), false);
  });
} finally {
  await rm(directory, {recursive: true, force: true});
}

console.log(JSON.stringify({ok: true,groups: checks.length,checks,realApiCalled: false,listeningSocketOpened: false,browserRenderingVerified: false}, null, 2));
