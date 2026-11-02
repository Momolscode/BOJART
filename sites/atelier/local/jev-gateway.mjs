import {createServer} from 'node:http';
import {createReadStream} from 'node:fs';
import {realpath, stat} from 'node:fs/promises';
import {dirname, extname, resolve, sep, join} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createJevProvider, DEFAULT_JEV_MODEL, JevError, normalizeVisualRequest} from './jev-provider.mjs';
import {createWorkshopRepository, defaultWorkshopDirectory, WORKSHOP_LIMITS, WorkshopError} from './workshop-repository.mjs';
import {createJevDecisionProvider, createDecisionService} from './jev-decisions.mjs';
import {createWorkshopAssetRepository, handleWorkshopAssetRequest} from './workshop-assets.mjs';

const DEFAULT_PORT = 3137;
const BODY_LIMIT = 16384;
const DIST_DIRECTORY = resolve(dirname(fileURLToPath(import.meta.url)), '../dist');
const MIME = Object.freeze({
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.mp4': 'video/mp4', '.webm': 'video/webm',
  '.ttf': 'font/ttf', '.woff': 'font/woff', '.woff2': 'font/woff2', '.vtt': 'text/vtt; charset=utf-8'
});

function sendJson(response, status, body, head = false) {
  if (response.headersSent || response.writableEnded || response.destroyed) return;
  const bytes = Buffer.from(JSON.stringify(body));
  response.writeHead(status, {'Content-Type': 'application/json; charset=utf-8', 'Content-Length': bytes.length, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'});
  response.end(head ? undefined : bytes);
}

function errorBody(error) {
  if (error instanceof JevError || error instanceof WorkshopError) return {status: error.status, body: {ok: false, code: error.code, message: error.message}};
  return {status: 500, body: {ok: false, code: 'internal_error', message: 'La passerelle locale n’a pas pu traiter la demande.'}};
}

function requestOrigin(request, port) {
  const host = request.headers.host;
  if (![`127.0.0.1:${port}`, `localhost:${port}`].includes(host)) throw new JevError('origin_rejected', 'Cette origine n’est pas autorisée sur la passerelle locale.', 403);
  const origin = `http://${host}`;
  if (request.headers.origin !== undefined && request.headers.origin !== origin) throw new JevError('origin_rejected', 'Cette origine n’est pas autorisée sur la passerelle locale.', 403);
  if (request.headers['sec-fetch-site'] !== undefined && !['same-origin', 'none'].includes(request.headers['sec-fetch-site'])) throw new JevError('origin_rejected', 'Cette origine n’est pas autorisée sur la passerelle locale.', 403);
  if (request.method === 'POST' && request.headers.origin !== origin) throw new JevError('origin_rejected', 'La demande doit provenir du dashboard de cette tour.', 403);
  return origin;
}

function readJson(request, limit = BODY_LIMIT) {
  if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(request.headers['content-type'] || '')) throw new JevError('invalid_content_type', 'La demande doit être du JSON UTF-8.', 415);
  const declared = request.headers['content-length'];
  if (declared !== undefined && (!/^\d+$/.test(declared) || Number(declared) > limit)) throw new JevError('body_too_large', 'La demande locale dépasse la taille autorisée.', 413);
  return new Promise((resolveBody, reject) => {
    const chunks = [];
    let size = 0;
    let settled = false;
    const timer = setTimeout(() => finish(new JevError('request_timeout', 'La demande locale n’a pas été reçue à temps.', 408)), 8000);
    const cleanup = () => {
      clearTimeout(timer);
      request.off('data', onData);
      request.off('end', onEnd);
      request.off('error', onError);
      request.off('aborted', onError);
    };
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      cleanup();
      if (error) { request.resume(); reject(error); }
      else resolveBody(value);
    };
    const onData = chunk => {
      const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      size += bytes.length;
      if (size > limit) finish(new JevError('body_too_large', 'La demande locale dépasse la taille autorisée.', 413));
      else chunks.push(bytes);
    };
    const onError = () => finish(new JevError('invalid_request', 'La demande locale est incomplète.', 400));
    const onEnd = () => {
      try {
        const text = new TextDecoder('utf-8', {fatal: true}).decode(Buffer.concat(chunks));
        finish(null, JSON.parse(text));
      } catch { finish(new JevError('invalid_json', 'La demande ne contient pas du JSON valide.', 400)); }
    };
    request.on('data', onData);
    request.on('end', onEnd);
    request.on('error', onError);
    request.on('aborted', onError);
  });
}

function byteRange(header, size) {
  if (header === undefined) return null;
  const match = /^bytes=(\d*)-(\d*)$/.exec(header);
  if (!match || !match[1] && !match[2] || size < 1) return false;
  const first = match[1] ? Number(match[1]) : null;
  const second = match[2] ? Number(match[2]) : null;
  if (first !== null && !Number.isSafeInteger(first) || second !== null && !Number.isSafeInteger(second)) return false;
  const start = first === null ? Math.max(0, size - second) : first;
  const end = first === null || second === null ? size - 1 : Math.min(second, size - 1);
  if (start < 0 || start > end || start >= size || first === null && second === 0) return false;
  return {start, end};
}

/** Request handler can be exercised with streams and an injected provider, no server or API call. */
export function createGatewayHandler({provider, workshop = null, assets = null, decisions = null, port = DEFAULT_PORT, distDirectory = DIST_DIRECTORY} = {}) {
  if (!provider || typeof provider.status !== 'function' || typeof provider.decide !== 'function') throw new Error('A visual decision provider is required.');
  if (!Number.isSafeInteger(port) || port < 1 || port > 65535) throw new Error('A valid local port is required.');
  const root = resolve(distDirectory);
  return async function handle(request, response) {
    try {
      const origin = requestOrigin(request, port);
      if (typeof request.url !== 'string' || request.url.length > 4096 || !request.url.startsWith('/') || request.url.startsWith('//')) throw new JevError('invalid_request', 'Le chemin demandé est invalide.', 400);
      const rawPath = request.url.split('?')[0];
      let pathname;
      try { pathname = decodeURIComponent(rawPath); } catch { throw new JevError('invalid_request', 'Le chemin demandé est invalide.', 400); }
      if (/[\u0000-\u001f\u007f\\]/.test(pathname) || pathname.split('/').some(part => part.startsWith('.'))) throw new JevError('not_found', 'Cette ressource n’existe pas.', 404);
      const url = new URL(request.url, origin);
      if (url.origin !== origin) throw new JevError('invalid_request', 'Le chemin demandé est invalide.', 400);
      if (pathname === '/api/visual-decision/status') {
        if (request.method !== 'GET' && request.method !== 'HEAD') throw new JevError('method_not_allowed', 'Cette méthode n’est pas disponible.', 405);
        sendJson(response, 200, provider.status(), request.method === 'HEAD');
        return;
      }
      if (pathname === '/api/visual-decision') {
        if (request.method !== 'POST') throw new JevError('method_not_allowed', 'Cette méthode n’est pas disponible.', 405);
        const input = normalizeVisualRequest(await readJson(request));
        sendJson(response, 200, await provider.decide(input));
        return;
      }
      if (pathname === '/api/decisions/status') {
        if (!['GET', 'HEAD'].includes(request.method)) throw new JevError('method_not_allowed', 'Cette méthode n’est pas disponible.', 405);
        if (!decisions) throw new JevError('unconfigured', 'Le service de conseils n’est pas configuré sur cette passerelle.', 503);
        sendJson(response, 200, decisions.status(), request.method === 'HEAD');
        return;
      }
      if (pathname === '/api/decisions') {
        if (request.method !== 'POST') throw new JevError('method_not_allowed', 'Cette méthode n’est pas disponible.', 405);
        if (!decisions) throw new JevError('unconfigured', 'Le service de conseils n’est pas configuré sur cette passerelle.', 503);
        sendJson(response, 200, await decisions.decide(await readJson(request, 65536)));
        return;
      }
      if (await handleWorkshopAssetRequest({request, response, pathname, assets})) return;
      if (['/api/workshop/status', '/api/workshop/operations', '/api/workshop/backup'].includes(pathname)) {
        if (!workshop) throw new WorkshopError('unconfigured', 'Le journal durable n’est pas configuré sur cette passerelle.', 503);
        if (pathname === '/api/workshop/status') {
          if (!['GET', 'HEAD'].includes(request.method)) throw new WorkshopError('method_not_allowed', 'Cette méthode n’est pas disponible.', 405);
          sendJson(response, 200, workshop.status(), request.method === 'HEAD');
        } else if (pathname === '/api/workshop/operations') {
          if (['GET', 'HEAD'].includes(request.method)) {
            if ([...url.searchParams.keys()].some(key => key !== 'after') || url.searchParams.getAll('after').length > 1) throw new WorkshopError('invalid_cursor', 'La demande doit contenir un seul curseur de journal.');
            const rawAfter = url.searchParams.get('after') ?? '0';
            if (!/^\d+$/.test(rawAfter)) throw new WorkshopError('invalid_cursor', 'Le curseur du journal est invalide.');
            sendJson(response, 200, workshop.operations(Number(rawAfter)), request.method === 'HEAD');
          } else if (request.method === 'POST') {
            sendJson(response, 200, workshop.append(await readJson(request, WORKSHOP_LIMITS.maxRequestBytes)));
          } else throw new WorkshopError('method_not_allowed', 'Cette méthode n’est pas disponible.', 405);
        } else {
          if (['GET', 'HEAD'].includes(request.method)) sendJson(response, 200, workshop.backup(), request.method === 'HEAD');
          else if (request.method === 'POST') sendJson(response, 200, workshop.restore(await readJson(request, WORKSHOP_LIMITS.maxBackupBytes)));
          else throw new WorkshopError('method_not_allowed', 'Cette méthode n’est pas disponible.', 405);
        }
        return;
      }
      if (pathname.startsWith('/api/')) throw new JevError('not_found', 'Cette route n’existe pas.', 404);
      if (request.method !== 'GET' && request.method !== 'HEAD') throw new JevError('method_not_allowed', 'Cette méthode n’est pas disponible.', 405);
      const target = resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
      if (!target.startsWith(root + sep) || !MIME[extname(target).toLowerCase()]) throw new JevError('not_found', 'Cette ressource n’existe pas.', 404);
      let actualRoot, actualTarget, info;
      try {
        [actualRoot, actualTarget] = await Promise.all([realpath(root), realpath(target)]);
        if (!actualTarget.startsWith(actualRoot + sep)) throw new Error('outside');
        info = await stat(actualTarget);
        if (!info.isFile()) throw new Error('not-file');
      } catch { throw new JevError('not_found', 'Cette ressource n’existe pas.', 404); }
      const range = byteRange(request.headers.range, info.size);
      if (range === false) {
        response.writeHead(416, {'Content-Range': `bytes */${info.size}`, 'Content-Length': 0, 'X-Content-Type-Options': 'nosniff'});
        response.end();
        return;
      }
      response.writeHead(range ? 206 : 200, {
        'Content-Type': MIME[extname(target).toLowerCase()],
        'Content-Length': range ? range.end - range.start + 1 : info.size,
        'Accept-Ranges': 'bytes',
        ...(range ? {'Content-Range': `bytes ${range.start}-${range.end}/${info.size}`} : {}),
        'Cache-Control': 'no-cache',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer'
      });
      if (request.method === 'HEAD') { response.end(); return; }
      await new Promise(done => {
        const stream = createReadStream(actualTarget, range || undefined);
        const finish = () => { stream.destroy(); done(); };
        response.once('close', finish);
        response.once('finish', done);
        stream.once('error', () => { response.destroy(); done(); });
        stream.pipe(response);
      });
    } catch (error) {
      const failure = errorBody(error);
      sendJson(response, failure.status, failure.body, request.method === 'HEAD');
      request.resume?.();
    }
  };
}

export async function startGateway({env = process.env} = {}) {
  const port = env.BOJ_JEV_PORT === undefined ? DEFAULT_PORT : Number(env.BOJ_JEV_PORT);
  if (!Number.isSafeInteger(port) || port < 1024 || port > 65535) throw new JevError('invalid_configuration', 'BOJ_JEV_PORT doit être compris entre 1024 et 65535.', 503);
  const provider = createJevProvider({
    apiKey: env.TYPESAFE_API_KEY || '',
    model: env.JEV_MODEL || DEFAULT_JEV_MODEL,
    minProbability: env.BOJ_JEV_MIN_PROBABILITY === undefined ? 0.8 : Number(env.BOJ_JEV_MIN_PROBABILITY),
    minMargin: env.BOJ_JEV_MIN_MARGIN === undefined ? 0.15 : Number(env.BOJ_JEV_MIN_MARGIN)
  });
  const directory = defaultWorkshopDirectory(env);
  if (directory === DIST_DIRECTORY || directory.startsWith(DIST_DIRECTORY + sep)) throw new WorkshopError('invalid_configuration', 'Le journal local doit être stocké hors du dossier public dist.', 503);
  const workshop = createWorkshopRepository({directory});
  if (workshop.directory === DIST_DIRECTORY || workshop.directory.startsWith(DIST_DIRECTORY + sep)) {
    workshop.close();
    throw new WorkshopError('invalid_configuration', 'Le journal local doit être stocké hors du dossier public dist.', 503);
  }
  let assets;
  try { assets = createWorkshopAssetRepository({directory: join(directory, 'assets')}); }
  catch (error) { workshop.close(); throw error; }
  let decisionProvider, decisions;
  try {
    decisionProvider = createJevDecisionProvider({apiKey: env.TYPESAFE_API_KEY || '', model: env.JEV_MODEL || DEFAULT_JEV_MODEL});
    decisions = createDecisionService({provider: decisionProvider});
  } catch (error) { workshop.close(); assets.close(); throw error; }
  const server = createServer(createGatewayHandler({provider, workshop, assets, decisions, port}));
  server.once('close', () => { workshop.close(); assets.close(); });
  server.requestTimeout = 180000;
  server.headersTimeout = 10000;
  server.keepAliveTimeout = 5000;
  try {
    await new Promise((resolveServer, reject) => {
      server.once('error', reject);
      server.listen(port, '127.0.0.1', resolveServer);
    });
  } catch (error) { workshop.close(); assets.close(); throw error; }
  return {server, provider, decisionProvider, decisions, workshop, assets, url: `http://127.0.0.1:${port}`};
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const {server, provider, workshop, url} = await startGateway();
    const status = provider.status();
    console.log(`BOJ.ART — dashboard local : ${url}`);
    console.log(status.configured ? `Jev configuré (${status.model}). Aucun appel effectué au démarrage.` : 'Jev non configuré. Le dashboard fonctionne ; la sélection Jev reste indisponible.');
    console.log(`Journal SQLite disponible (${workshop.status().operationCount} opération(s)). Coffre STL prêt. Conservation et conseils accessibles depuis le dashboard. Aucun équipement connecté.`);
    const close = () => server.close(() => process.exit(0));
    process.once('SIGINT', close);
    process.once('SIGTERM', close);
  } catch (error) {
    console.error(error instanceof JevError || error instanceof WorkshopError ? error.message : 'Impossible de démarrer la passerelle locale. Vérifiez le port et la configuration.');
    process.exitCode = 1;
  }
}
