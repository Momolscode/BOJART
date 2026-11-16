import {DatabaseSync} from 'node:sqlite';
import {createHash, randomUUID} from 'node:crypto';
import {chmodSync, lstatSync, mkdirSync, realpathSync} from 'node:fs';
import {open, readFile, rename, rm, stat} from 'node:fs/promises';
import {isAbsolute, join, resolve} from 'node:path';
import {canonicalWorkshopJSON} from '../dist/lib/workshop.js';

export const ASSET_LIMITS = Object.freeze({maxFileBytes: 52428800, maxArchiveBytes: 1073741824, maxManifestBytes: 16777216, maxAssets: 10000, pageSize: 100, maxConcurrentTransfers: 2});
const MAGIC = Buffer.from('BOJAST01');
const ARCHIVE_FORMAT = 'bojart.assets.backup.v1';
const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const SHA = /^[a-f0-9]{64}$/;
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const plain = value => value && typeof value === 'object' && !Array.isArray(value) && [Object.prototype, null].includes(Object.getPrototypeOf(value));
const canonical = canonicalWorkshopJSON;
const activeTransfers = new WeakMap();

export class WorkshopAssetError extends Error {
  constructor(code, message, status = 400) { super(message); this.name = 'WorkshopAssetError'; this.code = code; this.status = status; }
}
function fail(code, message, status = 400) { throw new WorkshopAssetError(code, message, status); }
function validId(id) { if (typeof id !== 'string' || !ID.test(id)) fail('invalid_asset_id', 'L’identifiant du fichier est invalide.'); return id; }
function validName(name) {
  if (typeof name !== 'string' || !name.trim() || name.length > 255 || /[\u0000-\u001f\u007f/\\]/.test(name) || !/\.stl$/i.test(name)) fail('invalid_asset_name', 'Un nom de fichier STL simple est requis.');
  return name;
}
function validTime(at) { if (!Number.isSafeInteger(at) || at < 0 || at > 8640000000000000) fail('invalid_asset', 'La date du fichier est invalide.'); return at; }
function metadata(raw) {
  if (!plain(raw) || Object.keys(raw).sort().join(',') !== 'byteLength,createdAt,format,id,name,sha256' || raw.format !== 'stl' || typeof raw.sha256 !== 'string' || !SHA.test(raw.sha256) || !Number.isSafeInteger(raw.byteLength) || raw.byteLength < 1 || raw.byteLength > ASSET_LIMITS.maxFileBytes) fail('invalid_asset', 'Le manifeste du fichier est invalide.');
  return {id: validId(raw.id), name: validName(raw.name), sha256: raw.sha256, byteLength: raw.byteLength, createdAt: validTime(raw.createdAt), format: 'stl'};
}
function rowMetadata(row) { return metadata({id: row.id, name: row.name, sha256: row.sha256, byteLength: row.byte_length, createdAt: row.created_at, format: 'stl'}); }
async function syncWrite(path, bytes) {
  const file = await open(path, 'wx', 0o600);
  try { await file.writeFile(bytes); await file.sync(); } finally { await file.close(); }
}
async function syncDirectory(path) {
  let directory;
  try { directory=await open(path,'r');await directory.sync(); }
  catch(error) { if(process.platform!=='win32'||!['EPERM','EACCES','EINVAL','ENOTSUP','EISDIR'].includes(error.code))throw error; }
  finally { await directory?.close(); }
}

/** Immutable, content-addressed original bytes. This repository never slices or prints. */
export function createWorkshopAssetRepository({directory, now = Date.now} = {}) {
  if (typeof directory !== 'string' || !isAbsolute(directory)) fail('invalid_configuration', 'Un dossier absolu est requis pour le coffre STL.', 503);
  if (typeof now !== 'function') fail('invalid_configuration', 'L’horloge du coffre est invalide.', 503);
  const folder = resolve(directory);
  let database;
  try {
    mkdirSync(folder, {recursive: true, mode: 0o700});
    if (!lstatSync(folder).isDirectory() || lstatSync(folder).isSymbolicLink()) throw new Error('directory');
    const blobs = join(folder, 'blobs'), staging = join(folder, 'staging');
    for (const child of [blobs, staging]) { mkdirSync(child, {recursive: true, mode: 0o700}); if (!lstatSync(child).isDirectory() || lstatSync(child).isSymbolicLink()) throw new Error('directory'); }
    const filename = join(folder, 'assets.sqlite3');
    let existed = false;
    try { const info = lstatSync(filename); if (!info.isFile() || info.isSymbolicLink()) throw new Error('database'); existed = true; } catch (error) { if (error.code !== 'ENOENT') throw error; }
    database = new DatabaseSync(filename, {timeout: 1500, enableDoubleQuotedStringLiterals: false, allowExtension: false});
    if (existed && !database.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='assets'").get()) throw new Error('unknown database');
    chmodSync(filename, 0o600);
    if (database.prepare('PRAGMA journal_mode = WAL').get().journal_mode !== 'wal') throw new Error('WAL');
    database.exec('PRAGMA synchronous = FULL; PRAGMA trusted_schema = OFF; CREATE TABLE IF NOT EXISTS assets (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, name TEXT NOT NULL, sha256 TEXT NOT NULL, byte_length INTEGER NOT NULL, created_at INTEGER NOT NULL) STRICT;');
    if (database.prepare('PRAGMA quick_check').get().quick_check !== 'ok') throw new Error('integrity');
  } catch {
    try { database?.close(); } catch {}
    fail('storage_unavailable', 'Le coffre STL ne peut pas être ouvert. Les fichiers existants sont conservés.', 503);
  }
  const blobs = join(folder, 'blobs'), staging = join(folder, 'staging');
  const statements = {
    byId: database.prepare('SELECT * FROM assets WHERE id = ?'),
    count: database.prepare('SELECT COUNT(*) AS count FROM assets'),
    all: database.prepare('SELECT * FROM assets ORDER BY seq'),
    page: database.prepare('SELECT * FROM assets WHERE seq > ? ORDER BY seq LIMIT ?'),
    insert: database.prepare('INSERT INTO assets (id,name,sha256,byte_length,created_at) VALUES (?,?,?,?,?)')
  };
  let closed = false;
  function ensureOpen() { if (closed) fail('storage_unavailable', 'Le coffre STL est fermé.', 503); }
  function blobPath(sha256) { if (!SHA.test(sha256)) fail('invalid_asset', 'Empreinte de fichier invalide.'); return join(blobs, sha256 + '.stl'); }
  async function verifiedBytes(meta) {
    ensureOpen();
    const path = blobPath(meta.sha256);
    let bytes;
    try {
      const info = await stat(path);
      if (!info.isFile() || info.size !== meta.byteLength || lstatSync(path).isSymbolicLink()) throw new Error('size');
      bytes = await readFile(path);
      if (digest(bytes) !== meta.sha256) throw new Error('digest');
    } catch { fail('asset_integrity', 'Le fichier conservé ne correspond pas à son empreinte, ou son binaire est absent. Aucun remplacement automatique.', 503); }
    return bytes;
  }
  async function preserveBlob(meta, bytes) {
    const target = blobPath(meta.sha256);
    try { await stat(target); await verifiedBytes(meta); await syncDirectory(blobs); return; } catch (error) { if (error.code !== 'ENOENT') throw error; }
    const temporary = join(staging, randomUUID() + '.upload');
    try { await syncWrite(temporary, bytes); await rename(temporary, target); await syncDirectory(blobs); }
    finally { await rm(temporary, {force: true}); }
  }
  function sameIdentity(left, right) { return left.sha256 === right.sha256 && left.byteLength === right.byteLength && left.name === right.name && left.createdAt === right.createdAt; }
  function preflight(metas) {
    let added = 0;
    for (const meta of metas) {
      const old = statements.byId.get(meta.id);
      if (old && !sameIdentity(rowMetadata(old), meta)) fail('asset_id_conflict', 'Cet identifiant désigne déjà un autre fichier ou un autre manifeste. L’original est conservé.', 409);
      if (!old) added++;
    }
    if (statements.count.get().count + added > ASSET_LIMITS.maxAssets) fail('asset_limit', 'Le coffre atteint sa limite de fichiers. Aucune suppression automatique.', 413);
  }
  function commit(metas) {
    ensureOpen(); let started = false;
    try {
      database.exec('BEGIN IMMEDIATE'); started = true; preflight(metas);
      const added = [], duplicates = [];
      for (const meta of metas) {
        if (statements.byId.get(meta.id)) duplicates.push(meta.id);
        else { statements.insert.run(meta.id, meta.name, meta.sha256, meta.byteLength, meta.createdAt); added.push(meta.id); }
      }
      database.exec('COMMIT'); return {ok: true, added, duplicates};
    } catch (error) {
      if (started) try { database.exec('ROLLBACK'); } catch {}
      if (error instanceof WorkshopAssetError) throw error;
      fail('storage_unavailable', 'Le coffre n’a pas confirmé la conservation du manifeste.', 503);
    }
  }
  const api = {
    directory: realpathSync(folder),
    status() { ensureOpen(); return {ok: true, version: 1, storage: 'local_content_addressed', immutable: true, fileCount: statements.count.get().count, limits: {...ASSET_LIMITS}, capabilities: {stlStorage: true, archiveExport: true, archiveRestore: true, printerCommands: false}}; },
    list({after = 0, limit = ASSET_LIMITS.pageSize} = {}) {
      ensureOpen();
      if (!Number.isSafeInteger(after) || after < 0 || !Number.isSafeInteger(limit) || limit < 1 || limit > ASSET_LIMITS.pageSize) fail('invalid_cursor', 'La page du coffre est invalide.');
      const rows = statements.page.all(after, limit + 1), selected = rows.slice(0, limit);
      return {ok: true, version: 1, assets: selected.map(rowMetadata), nextCursor: selected.at(-1)?.seq ?? after, hasMore: rows.length > limit};
    },
    async put({id, name, buffer, sha256, createdAt} = {}) {
      ensureOpen(); validId(id); validName(name); createdAt=createdAt??statements.byId.get(id)?.created_at??now(); validTime(createdAt);
      if (!(buffer instanceof ArrayBuffer) && !ArrayBuffer.isView(buffer)) fail('invalid_asset', 'Le fichier doit contenir des octets.');
      if (!buffer.byteLength || buffer.byteLength > ASSET_LIMITS.maxFileBytes) fail('asset_too_large', 'Le fichier STL dépasse 50 Mio ou est vide.', 413);
      // Own the bytes before the first await: a caller may reuse its input
      // buffer while fsync runs, but the confirmed SHA must describe the file.
      const source = buffer instanceof ArrayBuffer ? new Uint8Array(buffer) : new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength);
      const bytes = Buffer.from(source);
      if (typeof sha256 !== 'string' || !SHA.test(sha256) || digest(bytes) !== sha256) fail('checksum_mismatch', 'L’empreinte fournie ne correspond pas aux octets du STL.');
      const meta = metadata({id, name, sha256, byteLength: bytes.length, createdAt, format: 'stl'});
      preflight([meta]); await preserveBlob(meta, bytes); const receipt = commit([meta]);
      return {...receipt, asset: meta};
    },
    async get(id) {
      ensureOpen(); validId(id); const row = statements.byId.get(id);
      if (!row) return null;
      const meta = rowMetadata(row); return {...meta, buffer: await verifiedBytes(meta)};
    },
    async exportArchive() {
      ensureOpen();
      const assets = statements.all.all().map(rowMetadata);
      const body = {format: ARCHIVE_FORMAT, exportedAt: validTime(now()), assets};
      const manifest = {...body, sha256: digest(Buffer.from(canonical(body)))};
      const encoded = Buffer.from(JSON.stringify(manifest));
      const size = MAGIC.length + 4 + encoded.length + assets.reduce((sum, item) => sum + item.byteLength, 0);
      if (encoded.length > ASSET_LIMITS.maxManifestBytes || size > ASSET_LIMITS.maxArchiveBytes) fail('archive_too_large', 'Cette archive dépasse la capacité de sauvegarde du coffre (1 Gio).', 413);
      const path = join(staging, randomUUID() + '.bojassets');
      let file;
      try {
        file = await open(path, 'wx', 0o600);
        const length = Buffer.alloc(4); length.writeUInt32BE(encoded.length);
        await file.writeFile(Buffer.concat([MAGIC, length, encoded]));
        for (const meta of assets) await file.writeFile(await verifiedBytes(meta));
        await file.sync(); await file.close(); file = null;
        return {path, byteLength: size, filename: 'BOJ_ART_Coffre_STL.bojassets', assets: assets.length, cleanup: () => rm(path, {force: true})};
      } catch (error) { await file?.close(); await rm(path, {force: true}); throw error; }
    },
    async restoreArchive(path) {
      ensureOpen();
      const info = await stat(path);
      if (!info.isFile() || info.size < 12 || info.size > ASSET_LIMITS.maxArchiveBytes) fail('invalid_archive', 'La sauvegarde du coffre est invalide ou trop volumineuse.');
      const file = await open(path, 'r');
      const staged = [];
      async function exact(length, offset) {
        const bytes = Buffer.alloc(length); let total = 0;
        while (total < length) { const part = await file.read(bytes, total, length - total, offset + total); if (!part.bytesRead) fail('invalid_archive', 'La sauvegarde du coffre est tronquée.'); total += part.bytesRead; }
        return bytes;
      }
      try {
        const prefix = await exact(12, 0);
        if (!prefix.subarray(0,8).equals(MAGIC)) fail('invalid_archive', 'Ce fichier n’est pas une sauvegarde BOJ.ART du coffre STL.');
        const length = prefix.readUInt32BE(8);
        if (length < 2 || length > ASSET_LIMITS.maxManifestBytes || 12 + length > info.size) fail('invalid_archive', 'Le manifeste de sauvegarde est invalide.');
        let manifest;
        try { manifest = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(await exact(length, 12))); } catch { fail('invalid_archive', 'Le manifeste de sauvegarde n’est pas du JSON valide.'); }
        if (!plain(manifest) || Object.keys(manifest).sort().join(',') !== 'assets,exportedAt,format,sha256' || manifest.format !== ARCHIVE_FORMAT || typeof manifest.sha256!=='string' || !SHA.test(manifest.sha256) || !Array.isArray(manifest.assets) || manifest.assets.length > ASSET_LIMITS.maxAssets) fail('invalid_archive', 'Le contrat de sauvegarde du coffre est invalide.');
        validTime(manifest.exportedAt);
        const assets = manifest.assets.map(metadata), {sha256, ...body} = manifest;
        if (digest(Buffer.from(canonical(body))) !== sha256) fail('checksum_mismatch', 'Le manifeste du coffre ne correspond pas à son empreinte.');
        if (new Set(assets.map(meta => meta.id)).size !== assets.length) fail('invalid_archive', 'La sauvegarde contient plusieurs fois le même identifiant.');
        if (12 + length + assets.reduce((sum, meta) => sum + meta.byteLength, 0) !== info.size) fail('invalid_archive', 'La taille de l’archive ne correspond pas au manifeste.');
        preflight(assets);
        let offset = 12 + length;
        // Validate every byte before any alias becomes visible in the database.
        for (const meta of assets) {
          const bytes = await exact(meta.byteLength, offset); offset += meta.byteLength;
          if (digest(bytes) !== meta.sha256) fail('checksum_mismatch', 'Un STL de la sauvegarde ne correspond pas à son empreinte. Aucun manifeste n’a été restauré.');
          const temporary = join(staging, randomUUID() + '.restore'); await syncWrite(temporary, bytes); staged.push({meta, temporary});
        }
        for (const {meta, temporary} of staged) await preserveBlob(meta, await readFile(temporary));
        const result = commit(assets);
        return {...result, version: 1, restoredFiles: result.added.length, verifiedFiles: assets.length, includes: ['stl_binaries', 'asset_manifests'], excludes: ['workshop_journal', 'credentials', 'printer_state']};
      } finally { await file.close(); await Promise.allSettled(staged.map(item => rm(item.temporary, {force: true}))); }
    },
    close() { if (!closed) { database.close(); closed = true; } }
  };
  return api;
}

function sendJson(response, status, body) {
  const bytes = Buffer.from(JSON.stringify(body));
  response.writeHead(status, {'Content-Type': 'application/json; charset=utf-8', 'Content-Length': bytes.length, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}); response.end(bytes);
}
async function bodyBuffer(request, limit) {
  if ((request.headers['content-type'] || '').split(';')[0].trim().toLowerCase() !== 'application/octet-stream') fail('invalid_content_type', 'Le coffre attend un fichier binaire.', 415);
  const declared = request.headers['content-length'];
  if (declared !== undefined && (!/^\d+$/.test(declared) || Number(declared) > limit)) fail('asset_too_large', 'Le fichier dépasse la taille autorisée.', 413);
  const chunks = []; let length = 0;
  for await (const chunk of request) { length += chunk.length; if (length > limit) fail('asset_too_large', 'Le fichier dépasse la taille autorisée.', 413); chunks.push(chunk); }
  if(declared!==undefined&&Number(declared)!==length) fail('invalid_asset','Le transfert du fichier est incomplet.');
  return Buffer.concat(chunks);
}

/** Parent MUST run Host/Origin validation first. No listener is started by this module. */
export async function handleWorkshopAssetRequest({request, response, pathname, assets} = {}) {
  if (!pathname?.startsWith('/api/workshop/assets')) return false;
  let temporary, archive, reserved=false;
  try {
    if (!assets) fail('unconfigured', 'Le coffre STL n’est pas configuré sur cette tour.', 503);
    if(!['/api/workshop/assets/status','/api/workshop/assets'].includes(pathname)) {
      const active=activeTransfers.get(assets)||0;
      if(active>=ASSET_LIMITS.maxConcurrentTransfers) fail('transfer_busy','Deux transferts du coffre sont en cours. Réessayez avec les mêmes fichiers.',503);
      activeTransfers.set(assets,active+1);reserved=true;
    }
    if (pathname === '/api/workshop/assets/status') {
      if (request.method !== 'GET') fail('method_not_allowed', 'Méthode indisponible.', 405);
      sendJson(response, 200, assets.status());
    } else if (pathname === '/api/workshop/assets') {
      if (request.method !== 'GET') fail('method_not_allowed', 'Méthode indisponible.', 405);
      const url = new URL(request.url, 'http://localhost');
      if ([...url.searchParams.keys()].some(key => key !== 'after') || url.searchParams.getAll('after').length > 1 || !/^\d+$/.test(url.searchParams.get('after') || '0')) fail('invalid_cursor', 'Le curseur du coffre est invalide.');
      sendJson(response, 200, assets.list({after: Number(url.searchParams.get('after') || 0)}));
    } else if (pathname === '/api/workshop/assets/backup') {
      if (request.method !== 'GET') fail('method_not_allowed', 'Méthode indisponible.', 405);
      archive = await assets.exportArchive();
      response.writeHead(200, {'Content-Type': 'application/octet-stream', 'Content-Length': archive.byteLength, 'Content-Disposition': 'attachment; filename="' + archive.filename + '"', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'});
      const file = await open(archive.path, 'r');
      try { for await (const chunk of file.createReadStream()) { if (response.destroyed) break; if (!response.write(chunk)) await new Promise(resolve => {const done=()=>{for(const event of ['drain','close','error'])response.removeListener(event,done);resolve();};for(const event of ['drain','close','error'])response.once(event,done);if(response.destroyed)done();}); } if (!response.destroyed) response.end(); }
      finally { await file.close().catch(() => {}); }
    } else if (pathname === '/api/workshop/assets/restore') {
      if (request.method !== 'POST') fail('method_not_allowed', 'Méthode indisponible.', 405);
      // Upload is staged on disk; the archive is never unpacked using user paths.
      if ((request.headers['content-type'] || '').split(';')[0].trim().toLowerCase() !== 'application/octet-stream') fail('invalid_content_type', 'Une archive binaire du coffre est requise.', 415);
      const declared = request.headers['content-length'];
      if (declared !== undefined && (!/^\d+$/.test(declared) || Number(declared) > ASSET_LIMITS.maxArchiveBytes)) fail('archive_too_large', 'La sauvegarde du coffre dépasse 1 Gio.', 413);
      temporary = join(assets.directory, 'staging', randomUUID() + '.incoming');
      const file = await open(temporary, 'wx', 0o600); let length = 0;
      try { for await (const chunk of request) { length += chunk.length; if (length > ASSET_LIMITS.maxArchiveBytes) fail('archive_too_large', 'La sauvegarde du coffre dépasse 1 Gio.', 413); await file.writeFile(chunk); } await file.sync(); }
      finally { await file.close(); }
      if(declared!==undefined&&Number(declared)!==length) fail('invalid_archive','Le transfert de la sauvegarde est incomplet.');
      sendJson(response, 200, await assets.restoreArchive(temporary));
    } else {
      const match = /^\/api\/workshop\/assets\/([A-Za-z0-9][A-Za-z0-9._:-]{0,199})$/.exec(pathname);
      if (!match) fail('not_found', 'Cette route du coffre n’existe pas.', 404);
      const id = match[1];
      if (request.method === 'GET') {
        const asset = await assets.get(id); if (!asset) fail('asset_missing', 'Ce fichier n’est pas présent dans le coffre de la tour.', 404);
        response.writeHead(200, {'Content-Type': 'application/octet-stream', 'Content-Length': asset.byteLength, 'X-BOJ-Asset-ID': asset.id, 'X-BOJ-SHA256': asset.sha256, 'X-BOJ-File-Name': encodeURIComponent(asset.name), 'X-BOJ-Created-At': String(asset.createdAt), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}); response.end(asset.buffer);
      } else if (request.method === 'POST') {
        let name; try { name = decodeURIComponent(request.headers['x-boj-file-name'] || ''); } catch { fail('invalid_asset_name', 'Le nom du fichier est invalide.'); }
        const rawTime = request.headers['x-boj-created-at'];
        if (rawTime !== undefined && !/^\d+$/.test(rawTime)) fail('invalid_asset', 'La date du fichier est invalide.');
        const result = await assets.put({id, name, sha256: request.headers['x-boj-sha256'], ...(rawTime === undefined ? {} : {createdAt: Number(rawTime)}), buffer: await bodyBuffer(request, ASSET_LIMITS.maxFileBytes)});
        sendJson(response, 200, result);
      } else fail('method_not_allowed', 'Méthode indisponible.', 405);
    }
  } catch (error) {
    if (!response.headersSent) sendJson(response, error instanceof WorkshopAssetError ? error.status : 503, {ok: false, code: error instanceof WorkshopAssetError ? error.code : 'storage_unavailable', message: error instanceof WorkshopAssetError ? error.message : 'Le coffre STL n’a pas confirmé cette opération.'});
    else response.destroy?.();
    request.resume?.();
  } finally { if(reserved)activeTransfers.set(assets,Math.max(0,(activeTransfers.get(assets)||1)-1));await archive?.cleanup(); if (temporary) await rm(temporary, {force: true}); }
  return true;
}
