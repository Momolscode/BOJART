import { InquiryError, UUID_RE, INQUIRY_STATUSES, PRIVACY_VERSION, normalizeInquiry, normalizeInquiryRecord, canonicalJSON, sha256, createInquiryExport } from './acquisition-core.mjs';

const TOKEN_TTL = 15 * 60 * 1000;
const BODY_LIMIT = 24 * 1024;
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', { fatal: true });
const cacheHeaders = { 'Cache-Control': 'no-store, private', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', Vary: 'Cookie, oai-authenticated-user-id' };
const json = (body, status = 200, headers = {}) => Response.json(body, { status, headers: { ...cacheHeaders, ...headers } });
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const b64encode = bytes => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
function b64decode(value) {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw new Error('invalid_base64');
  return Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4)), x => x.charCodeAt(0));
}

export function authorizedAdmin(identity, rawAllowlist) {
  if (!identity?.userId || !identity?.email || typeof rawAllowlist !== 'string') return false;
  const emails = rawAllowlist.split(/[\n,;]/).map(value => value.trim().toLowerCase()).filter(Boolean);
  return emails.length > 0 && emails.includes(identity.email.trim().toLowerCase());
}

function identityFrom(request) {
  const userId = request.headers.get('oai-authenticated-user-id');
  const email = request.headers.get('oai-authenticated-user-email');
  return userId && email ? { userId, email } : null;
}

export function requireSameOrigin(request) {
  const origin = request.headers.get('origin');
  if (!origin || origin !== new URL(request.url).origin || request.headers.get('sec-fetch-site') === 'cross-site') throw new InquiryError('origin_rejected', 'Cette opération doit être effectuée depuis le site BOJ.ART.', 403);
}

export async function readBoundedJSON(request, limit = BODY_LIMIT) {
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get('content-type') || '')) throw new InquiryError('unsupported_media', 'Utilisez le format JSON.', 415);
  const length = request.headers.get('content-length');
  if (length && (!/^\d+$/.test(length) || Number(length) > limit)) throw new InquiryError('body_too_large', 'La demande dépasse la taille autorisée.', 413);
  if (!request.body) throw new InquiryError('invalid_json', 'La demande est vide.', 400);
  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  let timer;
  try {
    const timeout = new Promise((_, reject) => { timer = setTimeout(() => reject(new InquiryError('request_timeout', 'La réception de la demande a expiré. Réessayez avec la même demande.', 408)), 8000); });
    while (true) {
      const { done, value } = await Promise.race([reader.read(), timeout]);
      if (done) break;
      total += value.byteLength;
      if (total > limit) throw new InquiryError('body_too_large', 'La demande dépasse la taille autorisée.', 413);
      chunks.push(value);
    }
    const bytes = new Uint8Array(total);
    let at = 0;
    for (const chunk of chunks) { bytes.set(chunk, at); at += chunk.length; }
    try { return JSON.parse(decoder.decode(bytes)); }
    catch { throw new InquiryError('invalid_json', 'Le JSON de la demande est invalide.', 400); }
  } finally {
    clearTimeout(timer);
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

function requestId(value) {
  if (typeof value !== 'string' || !UUID_RE.test(value)) throw new InquiryError('invalid_id', 'Identifiant de demande invalide.', 400);
  return value.toLowerCase();
}

function recordFrom(row) {
  return normalizeInquiryRecord({
    ...JSON.parse(row.payload_json), reference: row.reference,
    createdAt: new Date(row.created_at).toISOString(), updatedAt: new Date(row.updated_at).toISOString(),
    status: row.status, revision: row.revision, privacyVersion: row.privacy_version,
  });
}
function receiptFrom(row) {
  // A receipt acknowledges the original deposit; public retries reveal no current
  // contact data, quotation state, or internal workflow updates.
  return { format: 'bojart.inquiry.receipt.v1', requestId: row.request_id, reference: row.reference, createdAt: new Date(row.created_at).toISOString(), status: 'new' };
}

export function createAcquisitionService({ db, secret, adminEmails, now = () => Date.now(), cryptoImpl = globalThis.crypto } = {}) {
  function requireDB() {
    if (!db?.prepare || !db?.batch) throw new InquiryError('storage_unavailable', 'La réception est momentanément indisponible. Conservez votre récapitulatif et réessayez avec la même demande.', 503);
    return db;
  }
  function requireAdmin(request) {
    const identity = identityFrom(request);
    if (!identity) throw new InquiryError('authentication_required', 'Connectez-vous pour accéder à l’administration.', 401);
    if (!authorizedAdmin(identity, adminEmails)) throw new InquiryError('access_denied', 'Cette session n’est pas autorisée à administrer BOJ.ART.', 403);
    return identity;
  }
  async function hmac(bytes, usage = 'sign', signature) {
    if (typeof secret !== 'string' || secret.length < 32 || !cryptoImpl?.subtle) throw new InquiryError('intake_unavailable', 'La réception est momentanément indisponible. Votre brouillon peut être conservé.', 503);
    const key = await cryptoImpl.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, [usage]);
    return usage === 'verify' ? cryptoImpl.subtle.verify('HMAC', key, signature, bytes) : new Uint8Array(await cryptoImpl.subtle.sign('HMAC', key, bytes));
  }
  async function verifyToken(request) {
    const token = request.headers.get('x-bojart-form-token');
    if (!token || token.length > 1500) throw new InquiryError('token_expired', 'Actualisez la protection du formulaire puis réessayez la même demande.', 403);
    try {
      const parts = token.split('.');
      if (parts.length !== 2) throw new Error('parts');
      const bytes = b64decode(parts[0]);
      const signature = b64decode(parts[1]);
      if (!await hmac(bytes, 'verify', signature)) throw new Error('signature');
      const data = JSON.parse(decoder.decode(bytes));
      const timestamp = now();
      if (!plain(data) || data.v !== 1 || data.origin !== new URL(request.url).origin || !Number.isSafeInteger(data.issuedAt) || !Number.isSafeInteger(data.expiresAt) || data.issuedAt > timestamp + 30000 || data.expiresAt <= timestamp || data.expiresAt - data.issuedAt !== TOKEN_TTL || !UUID_RE.test(data.nonce)) throw new Error('claims');
      return data;
    } catch (error) {
      if (error instanceof InquiryError) throw error;
      throw new InquiryError('token_expired', 'Actualisez la protection du formulaire puis réessayez la même demande.', 403);
    }
  }
  async function find(id) { return requireDB().prepare('SELECT * FROM inquiries WHERE request_id = ?').bind(id).first(); }
  async function assertNotDeleted(id) {
    if (await requireDB().prepare('SELECT request_id FROM inquiry_tombstones WHERE request_id = ?').bind(id).first()) throw new InquiryError('request_deleted', 'Cette demande a été supprimée. Elle ne sera pas recréée par cet envoi.', 410);
  }
  async function consumeRate(request) {
    const timestamp = now();
    const day = Math.floor(timestamp / 86400000);
    const hour = Math.floor(timestamp / 3600000);
    const minute = Math.floor(timestamp / 60000);
    const client = request.headers.get('cf-connecting-ip') || identityFrom(request)?.userId || 'unavailable';
    const clientKey = b64encode(await hmac(encoder.encode(`bojart-rate:${day}:${client}`)));
    const globalKey = `global-hour:${hour}`;
    const rules = [
      { key: `minute:${minute}:${clientKey}`, limit: 6, expiry: (minute + 2) * 60000 },
      { key: `day:${day}:${clientKey}`, limit: 30, expiry: (day + 2) * 86400000 },
    ];
    // D1 executes a batch sequentially in one transaction. Reserve all three
    // allowances together: a rejected client must not consume the shared quota.
    // SQLite changes() gates each subsequent INSERT on the preceding reservation.
    // No per-client key is added after the global ceiling has been reached.
    const results = await requireDB().batch([
      requireDB().prepare('INSERT INTO inquiry_rate_limits (key, count, expires_at) SELECT ?, 1, ? WHERE NOT EXISTS (SELECT 1 FROM inquiry_rate_limits WHERE (key = ? AND count >= ?) OR (key = ? AND count >= ?)) ON CONFLICT(key) DO UPDATE SET count = count + 1 WHERE count < ? RETURNING count').bind(globalKey, (hour + 2) * 3600000, rules[0].key, rules[0].limit, rules[1].key, rules[1].limit, 300),
      ...rules.map(rule => requireDB().prepare('INSERT INTO inquiry_rate_limits (key, count, expires_at) SELECT ?, 1, ? WHERE changes() = 1 ON CONFLICT(key) DO UPDATE SET count = count + 1 RETURNING count').bind(rule.key, rule.expiry)),
    ]);
    // Bounded expiry cleanup is operational, not customer-retention purging.
    await requireDB().prepare('DELETE FROM inquiry_rate_limits WHERE key IN (SELECT key FROM inquiry_rate_limits WHERE expires_at < ? LIMIT 200)').bind(timestamp).run();
    if (results.some(result => !result.results?.length)) throw new InquiryError('rate_limited', 'Trop de demandes ont été reçues. Attendez quelques minutes avant de réessayer.', 429);
  }
  async function guarded(action) {
    try { return await action(); }
    catch (error) {
      if (error instanceof InquiryError) return json({ ok: false, error: { code: error.code, message: error.message, ...(error.fields ? { fields: error.fields } : {}) } }, error.status, error.status === 429 ? { 'Retry-After': '120' } : {});
      // Never include SQL, customer fields, headers, secrets or runtime stack.
      return json({ ok: false, error: { code: 'storage_unavailable', message: 'L’opération n’a pas pu être confirmée. Actualisez avant de réessayer ; conservez le même identifiant de demande.' } }, 503);
    }
  }

  return {
    token: request => guarded(async () => {
      requireDB();
      const issuedAt = now();
      const expiresAt = issuedAt + TOKEN_TTL;
      const body = { v: 1, origin: new URL(request.url).origin, issuedAt, expiresAt, nonce: cryptoImpl.randomUUID() };
      const bytes = encoder.encode(canonicalJSON(body));
      const token = b64encode(bytes) + '.' + b64encode(await hmac(bytes));
      return json({ ok: true, token, expiresAt: new Date(expiresAt).toISOString() });
    }),
    submit: request => guarded(async () => {
      requireSameOrigin(request);
      await verifyToken(request);
      const payload = normalizeInquiry(await readBoundedJSON(request));
      const payloadJSON = canonicalJSON(payload);
      const payloadHash = await sha256(payloadJSON, cryptoImpl);
      await assertNotDeleted(payload.requestId);
      const previous = await find(payload.requestId);
      if (previous) {
        if (previous.payload_hash !== payloadHash) throw new InquiryError('idempotency_conflict', 'Cet identifiant appartient à une demande différente. Vérifiez le reçu de la première demande avant d’en créer une autre.', 409);
        return json({ ok: true, receipt: receiptFrom(previous), replayed: true });
      }
      await consumeRate(request);
      const timestamp = now();
      const reference = `BOJ-${new Date(timestamp).toISOString().slice(0, 10).replaceAll('-', '')}-${cryptoImpl.randomUUID().replaceAll('-', '').slice(0, 12).toUpperCase()}`;
      // The unique ID is the final concurrency boundary. A concurrent winner is
      // read back and compared; a tombstone also blocks a racing late retry.
      const inserted = await requireDB().prepare('INSERT INTO inquiries (request_id, reference, payload_hash, payload_json, privacy_version, status, revision, created_at, updated_at) SELECT ?, ?, ?, ?, ?, ?, 1, ?, ? WHERE NOT EXISTS (SELECT 1 FROM inquiry_tombstones WHERE request_id = ?) ON CONFLICT(request_id) DO NOTHING').bind(payload.requestId, reference, payloadHash, payloadJSON, PRIVACY_VERSION, 'new', timestamp, timestamp, payload.requestId).run();
      const saved = await find(payload.requestId);
      if (!saved) { await assertNotDeleted(payload.requestId); throw new InquiryError('storage_unavailable', 'La réception n’a pas pu être confirmée. Réessayez avec la même demande.', 503); }
      if (saved.payload_hash !== payloadHash) throw new InquiryError('idempotency_conflict', 'Une autre demande a déjà été reçue avec cet identifiant.', 409);
      const created = inserted.meta?.changes === 1;
      return json({ ok: true, receipt: receiptFrom(saved), replayed: !created }, created ? 201 : 200);
    }),
    list: request => guarded(async () => {
      requireAdmin(request);
      const url = new URL(request.url);
      const status = url.searchParams.get('status') || 'all';
      if (status !== 'all' && !INQUIRY_STATUSES.includes(status)) throw new InquiryError('invalid_status', 'Filtre de statut invalide.', 400);
      const cursor = url.searchParams.get('cursor');
      let before = null;
      if (cursor) {
        try {
          before = JSON.parse(decoder.decode(b64decode(cursor)));
          if (!plain(before) || !Number.isSafeInteger(before.at) || before.at < 0 || !UUID_RE.test(before.id)) throw new Error('cursor');
        } catch { throw new InquiryError('invalid_cursor', 'La page demandée est invalide.', 400); }
      }
      const clauses = [];
      const values = [];
      if (status !== 'all') { clauses.push('status = ?'); values.push(status); }
      if (before) { clauses.push('(created_at < ? OR (created_at = ? AND request_id < ?))'); values.push(before.at, before.at, before.id); }
      const rows = await requireDB().prepare(`SELECT * FROM inquiries ${clauses.length ? 'WHERE ' + clauses.join(' AND ') : ''} ORDER BY created_at DESC, request_id DESC LIMIT 51`).bind(...values).all();
      const visible = rows.results.slice(0, 50);
      const summaries = visible.map(row => { const item = recordFrom(row); return { requestId: item.requestId, reference: item.reference, name: item.name, offer: item.offer, status: item.status, createdAt: item.createdAt, updatedAt: item.updatedAt, revision: item.revision, quantity: item.quantity, budgetRange: item.budgetRange, source: item.source || null }; });
      const last = visible.at(-1);
      const nextCursor = rows.results.length > 50 && last ? b64encode(encoder.encode(JSON.stringify({ at: last.created_at, id: last.request_id }))) : null;
      const counts = await requireDB().prepare('SELECT status, COUNT(*) AS count FROM inquiries GROUP BY status').all();
      return json({ ok: true, inquiries: summaries, nextCursor, counts: Object.fromEntries(counts.results.map(row => [row.status, row.count])) });
    }),
    detail: (request, id) => guarded(async () => {
      requireAdmin(request);
      const row = await find(requestId(id));
      if (!row) throw new InquiryError('not_found', 'Cette demande est introuvable ou a été supprimée.', 404);
      return json({ ok: true, inquiry: recordFrom(row) });
    }),
    update: (request, id) => guarded(async () => {
      requireAdmin(request);
      requireSameOrigin(request);
      id = requestId(id);
      const body = await readBoundedJSON(request, 4096);
      if (!plain(body) || Object.keys(body).some(key => !['revision', 'status', 'contact'].includes(key)) || !Number.isInteger(body.revision) || body.revision < 1 || (!('status' in body) && !('contact' in body))) throw new InquiryError('invalid_update', 'Modification de demande invalide.', 422);
      const row = await find(id);
      if (!row) throw new InquiryError('not_found', 'Cette demande est introuvable ou a été supprimée.', 404);
      if (row.revision !== body.revision) throw new InquiryError('revision_conflict', 'La demande a changé dans une autre fenêtre. Actualisez avant de modifier.', 409);
      if (body.status !== undefined && !INQUIRY_STATUSES.includes(body.status)) throw new InquiryError('invalid_status', 'Statut de demande invalide.', 422);
      let payload = JSON.parse(row.payload_json);
      if (body.contact !== undefined) {
        if (!plain(body.contact) || !Object.keys(body.contact).length || Object.keys(body.contact).some(key => !['name', 'email', 'phone'].includes(key))) throw new InquiryError('invalid_contact', 'Seuls le nom, l’e-mail et le téléphone peuvent être corrigés.', 422);
        payload = normalizeInquiry({ ...payload, ...body.contact });
      }
      const updated = await requireDB().prepare('UPDATE inquiries SET payload_json = ?, status = ?, revision = revision + 1, updated_at = ? WHERE request_id = ? AND revision = ? RETURNING *').bind(canonicalJSON(payload), body.status ?? row.status, Math.max(now(), row.created_at, row.updated_at), id, body.revision).all();
      if (!updated.results.length) throw new InquiryError('revision_conflict', 'La demande a changé. Actualisez avant de modifier.', 409);
      return json({ ok: true, inquiry: recordFrom(updated.results[0]) });
    }),
    remove: (request, id) => guarded(async () => {
      requireAdmin(request);
      requireSameOrigin(request);
      id = requestId(id);
      const body = await readBoundedJSON(request, 1024);
      if (!plain(body) || Object.keys(body).some(key => !['revision', 'confirmation'].includes(key)) || !Number.isInteger(body.revision) || body.revision < 1 || body.confirmation !== id) throw new InquiryError('invalid_deletion', 'Confirmez la suppression de cette demande.', 422);
      const row = await find(id);
      if (!row) {
        const deleted = await requireDB().prepare('SELECT request_id FROM inquiry_tombstones WHERE request_id = ?').bind(id).first();
        if (deleted) return json({ ok: true, deleted: true, requestId: id, replayed: true });
        throw new InquiryError('not_found', 'Cette demande est introuvable.', 404);
      }
      if (row.revision !== body.revision) throw new InquiryError('revision_conflict', 'La demande a changé. Actualisez avant de la supprimer.', 409);
      const result = await requireDB().batch([
        requireDB().prepare('INSERT INTO inquiry_tombstones (request_id, deleted_at) SELECT request_id, ? FROM inquiries WHERE request_id = ? AND revision = ? ON CONFLICT(request_id) DO NOTHING').bind(now(), id, body.revision),
        requireDB().prepare('DELETE FROM inquiries WHERE request_id = ? AND revision = ? AND EXISTS (SELECT 1 FROM inquiry_tombstones WHERE request_id = ?) RETURNING request_id').bind(id, body.revision, id),
      ]);
      if (!result[1].results.length) throw new InquiryError('revision_conflict', 'La demande a changé. Actualisez avant de la supprimer.', 409);
      return json({ ok: true, deleted: true, requestId: id, replayed: false });
    }),
    export: (request, id) => guarded(async () => {
      requireAdmin(request);
      const row = await find(requestId(id));
      if (!row) throw new InquiryError('not_found', 'Cette demande est introuvable ou a été supprimée.', 404);
      const exported = await createInquiryExport(recordFrom(row), { exportedAt: new Date(now()).toISOString(), cryptoImpl });
      return json(exported, 200, { 'Content-Disposition': `attachment; filename="${row.reference}.json"` });
    }),
  };
}
