// BOJ.ART — ephemeral coordination of same-origin display windows only.
// This channel carries view requests; it never commands machines or external services.
const PROTOCOL = 'bojart.display-bus.v1';
const HEARTBEAT_MS = 1500;
const PEER_TTL_MS = 6000;
const REQUEST_TIMEOUT_MS = 6000;
const ROLES = new Set(['atelier', 'pilotage', 'creation']);
const VIEWS = new Set(['model', 'art', 'film', 'production']);
const PAYLOAD_KEYS = new Set(['kind', 'view', 'projectId', 'pieceId', 'exploded', 'section', 'projectRevision', 'pieceRevision']);
let sequence = 0;

function identifier(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 128 && value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
}

function copyPayload(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Demande de vue invalide.');
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) throw new Error('La demande doit être un objet simple.');
  const keys = Reflect.ownKeys(value);
  if (keys.some(key => !PAYLOAD_KEYS.has(key))) throw new Error('Cette demande contient un champ non autorisé.');
  const owns = key => Object.prototype.hasOwnProperty.call(value, key);
  if (!owns('kind') || value.kind !== 'show' || !owns('view') || !VIEWS.has(value.view) || !owns('projectId') || !identifier(value.projectId)) throw new Error('Une vue et un projet précis sont nécessaires.');
  const result = {kind: 'show', view: value.view, projectId: value.projectId};
  if (owns('pieceId')) {
    if (!identifier(value.pieceId)) throw new Error('La pièce demandée est invalide.');
    result.pieceId = value.pieceId;
  }
  if (owns('exploded')) {
    if (typeof value.exploded !== 'boolean') throw new Error('Le mode éclaté doit être booléen.');
    result.exploded = value.exploded;
  }
  if (owns('section')) {
    if (value.section !== null && (typeof value.section !== 'number' || !Number.isFinite(value.section) || value.section < 0 || value.section > 1)) throw new Error('La coupe doit être nulle ou comprise entre 0 et 1.');
    result.section = value.section;
  }
  for (const key of ['projectRevision', 'pieceRevision']) {
    if (!owns(key)) continue;
    if (!Number.isSafeInteger(value[key]) || value[key] < 1) throw new Error('La révision demandée est invalide.');
    result[key] = value[key];
  }
  if (owns('pieceRevision') && !owns('pieceId')) throw new Error('Une révision de pièce nécessite sa pièce.');
  return result;
}

function instanceId() {
  try { if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID(); } catch {}
  return 'display-' + Date.now().toString(36) + '-' + (++sequence).toString(36) + '-' + Math.random().toString(36).slice(2);
}

function messageText(value, fallback) {
  return typeof value === 'string' && value.trim() ? value.slice(0, 600) : fallback;
}

/**
 * channelFactory(name) may provide a BroadcastChannel-compatible test double.
 * peers() excludes this instance and unassigned roles. No state survives reload.
 * A timeout means the view was not confirmed; it does not authorize a local retry.
 * onRequest must validate project/piece existence and revisions before confirming.
 */
export function createDisplayBus({getRole = () => null, onRequest, onChange = () => {}, channelFactory} = {}) {
  const id = instanceId();
  const known = new Map();
  const pending = new Map();
  const received = new Map();
  let channel = null;
  let heartbeat = null;
  let disposed = false;
  let failed = false;
  let closed = false;
  let changeQueued = false;
  let requestSequence = 0;
  const isAvailable = () => !!channel && !disposed && !failed;
  const role = () => {
    try { const value = getRole(); return ROLES.has(value) ? value : null; } catch { return null; }
  };
  const notify = () => {
    if (changeQueued || disposed) return;
    changeQueued = true;
    queueMicrotask(() => {
      changeQueued = false;
      if (!disposed) { try { onChange(); } catch {} }
    });
  };
  const finish = (requestId, result) => {
    const entry = pending.get(requestId);
    if (!entry) return;
    pending.delete(requestId);
    clearTimeout(entry.timer);
    entry.resolve({...result, peerId: entry.peerId});
  };
  const closeChannel = () => {
    if (!channel || closed) return;
    closed = true;
    try {
      if (typeof channel.removeEventListener === 'function') channel.removeEventListener('message', receive);
      else if (channel.onmessage === receive) channel.onmessage = null;
    } catch {}
    try { channel.close?.(); } catch {}
  };
  const unavailable = () => {
    if (failed || disposed) return;
    failed = true;
    clearInterval(heartbeat);
    closeChannel();
    known.clear();
    for (const requestId of [...pending.keys()]) finish(requestId, {ok: false, code: 'unavailable', message: 'La coordination entre fenêtres est indisponible.'});
    notify();
  };
  const send = frame => {
    if (!isAvailable()) return false;
    try { channel.postMessage({protocol: PROTOCOL, from: id, ...frame}); return true; }
    catch { unavailable(); return false; }
  };
  const prune = () => {
    const now = Date.now();
    let changed = false;
    for (const [peerId, peer] of known) {
      if (now - peer.lastSeen >= PEER_TTL_MS) { known.delete(peerId); changed = true; }
    }
    for (const [key, entry] of received) if (now >= entry.expiresAt + REQUEST_TIMEOUT_MS) received.delete(key);
    if (changed) notify();
  };
  const presence = requestReply => send({type: 'presence', role: role(), requestReply});
  const answer = (frame, result) => send({type: 'ack', to: frame.from, requestId: frame.requestId, ok: result.ok === true, message: result.message});

  function receive(event) {
    if (!isAvailable()) return;
    const frame = event?.data;
    if (!frame || typeof frame !== 'object' || frame.protocol !== PROTOCOL || !identifier(frame.from) || frame.from === id) return;
    if (frame.type === 'presence') {
      if (frame.role !== null && !ROLES.has(frame.role)) return;
      if (typeof frame.requestReply !== 'boolean') return;
      const previous = known.get(frame.from);
      if (frame.role === null) {
        if (known.delete(frame.from)) notify();
      } else {
        known.set(frame.from, {id: frame.from, role: frame.role, lastSeen: Date.now()});
        if (!previous || previous.role !== frame.role) notify();
      }
      if (frame.requestReply) presence(false);
      return;
    }
    if (frame.type === 'leave') {
      if (known.delete(frame.from)) notify();
      return; // A previously sent request still needs an ACK or timeout.
    }
    if (frame.to !== id || !identifier(frame.requestId)) return;
    if (frame.type === 'ack') {
      const entry = pending.get(frame.requestId);
      if (!entry || entry.peerId !== frame.from || typeof frame.ok !== 'boolean' || typeof frame.message !== 'string') return;
      if (Date.now() >= entry.expiresAt) finish(frame.requestId, {ok: false, code: 'timeout', message: 'La station n’a pas confirmé l’aperçu dans le délai prévu.'});
      else finish(frame.requestId, {ok: frame.ok, code: frame.ok ? 'ack' : 'rejected', message: messageText(frame.message, frame.ok ? 'Aperçu confirmé par la station.' : 'Aperçu refusé par la station.')});
      return;
    }
    if (frame.type !== 'request') return;
    const reject = message => answer(frame, {ok: false, message});
    if (!ROLES.has(frame.role) || !Number.isSafeInteger(frame.expiresAt) || Date.now() >= frame.expiresAt || frame.expiresAt > Date.now() + REQUEST_TIMEOUT_MS) { reject('La demande est invalide ou a expiré.'); return; }
    let payload;
    try { payload = copyPayload(frame.payload); } catch (error) { reject(error.message); return; }
    const key = frame.from + ':' + frame.requestId;
    const signature = JSON.stringify({role: frame.role, payload});
    const previous = received.get(key);
    if (previous) {
      if (previous.signature !== signature) reject('Cet identifiant a déjà servi à une autre demande.');
      else if (previous.result) answer(frame, previous.result);
      return;
    }
    prune();
    if (received.size >= 256) { reject('La station traite déjà trop de demandes.'); return; }
    const entry = {signature, expiresAt: frame.expiresAt, result: null};
    received.set(key, entry);
    if (role() !== frame.role) {
      entry.result = {ok: false, message: 'Cette fenêtre n’occupe plus la station demandée.'};
      answer(frame, entry.result);
      return;
    }
    Promise.resolve().then(async () => {
      if (!isAvailable() || Date.now() >= frame.expiresAt) return;
      let result;
      try {
        if (role() !== frame.role) result = {ok: false, message: 'Cette fenêtre n’occupe plus la station demandée.'};
        else if (typeof onRequest !== 'function') result = {ok: false, message: 'Cette station ne traite pas les aperçus.'};
        else {
          const handled = await onRequest({...payload});
          result = {ok: handled?.ok === true, message: messageText(handled?.message, handled?.ok === true ? 'Aperçu confirmé par la station.' : 'Aperçu refusé par la station.')};
        }
      } catch { result = {ok: false, message: 'La station n’a pas pu afficher cet aperçu.'}; }
      if (role() !== frame.role) result = {ok: false, message: 'Cette fenêtre n’occupe plus la station demandée.'};
      entry.result = result;
      if (isAvailable() && Date.now() < frame.expiresAt) answer(frame, result);
    });
  }

  const api = {
    get available() { return isAvailable(); },
    peers() {
      prune();
      return [...known.values()].sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0).map(peer => ({...peer}));
    },
    async request(targetRole, value) {
      if (!ROLES.has(targetRole)) return {ok: false, code: 'rejected', message: 'La station demandée est invalide.'};
      let payload;
      try { payload = copyPayload(value); } catch (error) { return {ok: false, code: 'rejected', message: error.message}; }
      if (!isAvailable()) return {ok: false, code: 'unavailable', message: 'La coordination entre fenêtres est indisponible.'};
      const peer = api.peers().find(candidate => candidate.role === targetRole);
      if (!peer) return {ok: false, code: 'missing', message: 'Aucune fenêtre de la station demandée n’est présente.'};
      if (pending.size >= 64) return {ok: false, code: 'rejected', message: 'Trop de demandes attendent déjà une confirmation.'};
      const requestId = id + '-' + (++requestSequence).toString(36);
      const expiresAt = Date.now() + REQUEST_TIMEOUT_MS;
      return new Promise(resolve => {
        const timer = setTimeout(() => finish(requestId, {ok: false, code: 'timeout', message: 'La station n’a pas confirmé l’aperçu dans le délai prévu.'}), REQUEST_TIMEOUT_MS);
        timer?.unref?.();
        pending.set(requestId, {peerId: peer.id, expiresAt, timer, resolve});
        if (!send({type: 'request', to: peer.id, role: targetRole, requestId, expiresAt, payload})) finish(requestId, {ok: false, code: 'unavailable', message: 'La demande n’a pas pu être confirmée par la station.'});
      });
    },
    announce() { prune(); return presence(true); },
    dispose() {
      if (disposed) return;
      if (isAvailable()) send({type: 'leave'});
      disposed = true;
      clearInterval(heartbeat);
      closeChannel();
      known.clear();
      received.clear();
      for (const requestId of [...pending.keys()]) finish(requestId, {ok: false, code: 'unavailable', message: 'La coordination de cette fenêtre est arrêtée.'});
    }
  };
  try {
    channel = channelFactory ? channelFactory(PROTOCOL) : typeof globalThis.BroadcastChannel === 'function' ? new globalThis.BroadcastChannel(PROTOCOL) : null;
    if (!channel || typeof channel.postMessage !== 'function') { failed = true; closeChannel(); }
    else {
      if (typeof channel.addEventListener === 'function') channel.addEventListener('message', receive);
      else channel.onmessage = receive;
      heartbeat = setInterval(() => { prune(); presence(false); }, HEARTBEAT_MS);
      heartbeat?.unref?.();
      api.announce();
    }
  } catch { unavailable(); }
  return api;
}
