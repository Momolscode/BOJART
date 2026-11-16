import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createDisplayBus} from '../dist/lib/display-bus.js';

const realNow = Date.now.bind(Date);
const microtasks = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
const valid = {kind: 'show', view: 'model', projectId: 'project-a', pieceId: 'piece-a', projectRevision: 2, pieceRevision: 3, exploded: false, section: 0};

class Clock {
  now = 100000;
  nextId = 0;
  timers = new Map();
  constructor() {
    this.saved = {now: Date.now, setTimeout, clearTimeout, setInterval, clearInterval};
    Date.now = () => this.now;
    globalThis.setTimeout = (fn, delay) => this.add(fn, delay, false);
    globalThis.setInterval = (fn, delay) => this.add(fn, delay, true);
    globalThis.clearTimeout = globalThis.clearInterval = id => this.timers.delete(id);
  }
  add(fn, delay, repeat) {
    const id = ++this.nextId;
    this.timers.set(id, {fn, at: this.now + delay, delay, repeat});
    return id;
  }
  async advance(ms, flush) {
    const until = this.now + ms;
    for (;;) {
      const next = [...this.timers.entries()].filter(([, timer]) => timer.at <= until).sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!next) break;
      const [id, timer] = next;
      this.now = timer.at;
      if (timer.repeat) timer.at += timer.delay;
      else this.timers.delete(id);
      timer.fn();
      await flush();
    }
    this.now = until;
    await flush();
  }
  restore() {
    Date.now = this.saved.now;
    for (const key of ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval']) globalThis[key] = this.saved[key];
  }
}

class ChannelHub {
  channels = [];
  queue = [];
  held = [];
  posts = [];
  filter = () => 'deliver';
  duplicateRequests = false;
  factory = name => {
    const hub = this;
    const channel = {
      name, closed: false, fail: false, listeners: new Set(), onmessage: null,
      addEventListener(type, fn) { assert.equal(type, 'message'); this.listeners.add(fn); },
      removeEventListener(type, fn) { assert.equal(type, 'message'); this.listeners.delete(fn); },
      postMessage(frame) {
        if (this.closed || this.fail) throw new Error('Channel unavailable');
        hub.posts.push({channel: this, frame: structuredClone(frame)});
        for (const target of hub.channels) {
          if (target === this || target.closed || target.name !== name) continue;
          const count = hub.duplicateRequests && frame.type === 'request' ? 2 : 1;
          for (let i = 0; i < count; i++) hub.queue.push({target, frame: structuredClone(frame)});
        }
      },
      close() { this.closed = true; }
    };
    this.channels.push(channel);
    return channel;
  };
  inject(frame, target) { this.queue.push({target, frame: structuredClone(frame)}); }
  async flush() {
    for (let round = 0; round < 50; round++) {
      const batch = this.queue.splice(0);
      for (const item of batch) {
        if (item.target.closed) continue;
        const decision = this.filter(item);
        if (decision === 'hold') { this.held.push(item); continue; }
        if (decision === 'drop') continue;
        for (const listener of [...item.target.listeners]) listener({data: structuredClone(item.frame)});
        item.target.onmessage?.({data: structuredClone(item.frame)});
      }
      await microtasks();
      if (!this.queue.length) return;
    }
    throw new Error('Broadcast loop exceeded the test bound');
  }
  requests() { return this.posts.filter(item => item.frame.type === 'request'); }
  acks() { return this.posts.filter(item => item.frame.type === 'ack'); }
}

function fixture() {
  const clock = new Clock();
  const hub = new ChannelHub();
  const stations = [];
  const station = (initialRole, handler = async () => ({ok: true, message: 'Vue affichée.'}), extra = {}) => {
    const state = {role: initialRole, changes: 0};
    const bus = createDisplayBus({getRole: () => state.role, onRequest: handler, onChange: () => state.changes++, channelFactory: hub.factory, ...extra});
    const record = {bus, state, channel: hub.channels.at(-1)};
    stations.push(record);
    return record;
  };
  return {
    clock, hub, station,
    advance: ms => clock.advance(ms, () => hub.flush()),
    async close() {
      try {
        for (const record of stations) record.bus.dispose();
        await microtasks();
        assert.equal(clock.timers.size, 0, 'Every heartbeat and pending timeout must be removed');
        for (const channel of hub.channels) {
          assert.equal(channel.closed, true);
          assert.equal(channel.listeners.size, 0);
          assert.equal(channel.onmessage, null);
        }
      } finally { clock.restore(); }
    }
  };
}

const checks = [];
async function check(name, test) {
  const env = fixture();
  let failure;
  try { await test(env); } catch (error) { failure = error; }
  try { await env.close(); } catch (error) { failure ||= error; }
  checks.push({name, ok: !failure, ...(failure ? {error: failure.stack || String(failure)} : {})});
  console.log((failure ? 'FAIL ' : 'PASS ') + name);
  if (failure) console.error(failure.stack || failure);
}

await check('Canal absent ou refusé : aucune présence revendiquée', async ({station, clock}) => {
  for (const factory of [() => null, () => { throw new Error('Denied'); }]) {
    const {bus} = station('pilotage', undefined, {channelFactory: factory});
    assert.equal(bus.available, false);
    assert.deepEqual(bus.peers(), []);
    assert.equal((await bus.request('creation', valid)).code, 'unavailable');
    assert.equal(bus.announce(), false);
    bus.dispose(); bus.dispose();
  }
  assert.equal(clock.timers.size, 0);
});

await check('Trois stations : découverte réciproque et copies des pairs', async ({station, hub, clock}) => {
  const central = station('pilotage');
  const left = station('atelier');
  const right = station('creation');
  await hub.flush();
  assert.deepEqual(central.bus.peers().map(peer => peer.role).sort(), ['atelier', 'creation']);
  for (const target of [central, left, right]) {
    assert.equal(target.bus.peers().length, 2);
    assert.ok(target.state.changes > 0);
    assert.ok(target.bus.peers().every(peer => peer.lastSeen === clock.now));
  }
  const copy = central.bus.peers();
  copy[0].role = 'mutated';
  assert.ok(central.bus.peers().every(peer => peer.role !== 'mutated'));
  right.state.role = null;
  right.bus.announce();
  await hub.flush();
  assert.deepEqual(central.bus.peers().map(peer => peer.role), ['atelier']);
});

await check('ACK après rendu asynchrone ; contexte, révisions et coupe conservés', async ({station, hub}) => {
  let confirm;
  const received = [];
  const central = station('pilotage');
  station('creation', payload => { received.push(payload); return new Promise(resolve => { confirm = resolve; }); });
  await hub.flush();
  const original = {...valid};
  const completion = central.bus.request('creation', original);
  let settled = false;
  completion.then(() => { settled = true; });
  original.projectId = 'project-b'; original.pieceRevision = 99; original.section = 1;
  await hub.flush();
  assert.equal(settled, false);
  assert.deepEqual(received, [valid]);
  confirm({ok: true, message: 'Géométrie de la révision demandée affichée.'});
  await hub.flush();
  const result = await completion;
  assert.equal(result.ok, true);
  assert.equal(result.code, 'ack');
  assert.equal(result.peerId, central.bus.peers()[0].id);
});

await check('Refus métier, révision périmée et exception restent des refus', async ({station, hub}) => {
  const central = station('pilotage');
  let mode = 'context';
  station('creation', payload => {
    if (mode === 'throw') throw new Error('WebGL unavailable');
    if (mode === 'invalid') return undefined;
    return {ok: payload.projectId === 'project-b' && payload.pieceRevision === 4, message: 'Projet, pièce ou révision indisponible.'};
  });
  await hub.flush();
  for (const nextMode of ['context', 'throw', 'invalid']) {
    mode = nextMode;
    const completion = central.bus.request('creation', valid);
    await hub.flush();
    const result = await completion;
    assert.equal(result.ok, false);
    assert.equal(result.code, 'rejected');
  }
});

await check('Validation stricte aux deux extrémités : aucune commande physique', async ({station, hub, clock}) => {
  let calls = 0;
  const central = station('pilotage');
  const right = station('creation', () => { calls++; return {ok: true}; });
  await hub.flush();
  const invalid = [null, [], new Date(), {...valid, kind: 'print'}, {...valid, view: 'slice'}, {...valid, machineId: 'P01'}, {...valid, projectId: ' '}, {...valid, pieceId: undefined}, {...valid, exploded: 1}, {...valid, section: NaN}, {...valid, section: 1.1}, {...valid, section: '0.5'}, {...valid, projectRevision: 0}, {...valid, pieceRevision: 1.5}, {...valid, projectRevision: Number.MAX_SAFE_INTEGER + 1}, {kind: 'show', view: 'model', projectId: 'project-a', pieceRevision: 1}];
  for (const payload of invalid) assert.equal((await central.bus.request('creation', payload)).code, 'rejected');
  assert.equal((await central.bus.request('robot', valid)).code, 'rejected');
  assert.equal(hub.requests().length, 0);
  hub.inject({protocol: 'bojart.display-bus.v1', type: 'request', from: right.bus.peers()[0].id, to: central.bus.peers()[0].id, role: 'creation', requestId: 'remote-invalid', expiresAt: clock.now + 6000, payload: {...valid, action: 'start-printer'}}, right.channel);
  await hub.flush();
  assert.equal(calls, 0);
  assert.equal(hub.acks().at(-1).frame.ok, false);
  const completion = central.bus.request('creation', {...valid, section: null, exploded: true});
  await hub.flush();
  assert.equal((await completion).code, 'ack');
  assert.equal(calls, 1);
});

await check('Stations en double : cible unique déterministe et requête dédupliquée', async ({station, hub}) => {
  const central = station('pilotage');
  const calls = [0, 0];
  const resolvers = [];
  const rights = [0, 1].map(index => station('creation', () => { calls[index]++; return new Promise(resolve => { resolvers[index] = resolve; }); }));
  await hub.flush();
  hub.duplicateRequests = true;
  const selected = central.bus.peers().filter(peer => peer.role === 'creation').map(peer => peer.id).sort()[0];
  const completion = central.bus.request('creation', {...valid, view: 'film'});
  await hub.flush();
  assert.equal(calls[0] + calls[1], 1);
  assert.equal(hub.requests()[0].frame.to, selected);
  const selectedIndex = calls.findIndex(count => count === 1);
  resolvers[selectedIndex]({ok: true, message: 'Film affiché.'});
  await hub.flush();
  assert.equal((await completion).peerId, selected);
  const original = hub.requests()[0].frame;
  hub.inject(original, rights[selectedIndex].channel);
  await hub.flush();
  assert.equal(calls[0] + calls[1], 1);
  assert.equal(hub.acks().at(-1).frame.ok, true);
  hub.inject({...original, payload: {...valid, view: 'art'}}, rights[selectedIndex].channel);
  await hub.flush();
  assert.equal(calls[0] + calls[1], 1);
  assert.equal(hub.acks().at(-1).frame.ok, false);
});

await check('Rôle changé : refus définitif conservé lors de la livraison en double', async ({station, hub}) => {
  let calls = 0;
  const central = station('pilotage');
  const right = station('creation', () => { calls++; return {ok: true}; });
  await hub.flush();
  const completion = central.bus.request('creation', valid);
  const original = hub.requests()[0].frame;
  right.state.role = 'atelier';
  await hub.flush();
  assert.equal((await completion).code, 'rejected');
  const firstAck = hub.acks().at(-1).frame;
  right.state.role = 'creation';
  hub.inject(original, right.channel);
  await hub.flush();
  assert.equal(calls, 0);
  assert.deepEqual(hub.acks().at(-1).frame, firstAck);
});

await check('ACK étranger et tardif ignorés ; aucun renvoi après délai dépassé', async ({station, hub, advance}) => {
  let confirm;
  let calls = 0;
  const central = station('pilotage');
  station('creation', () => { calls++; return new Promise(resolve => { confirm = resolve; }); });
  station('atelier');
  await hub.flush();
  const completion = central.bus.request('creation', valid);
  let settled = false;
  completion.then(() => { settled = true; });
  await hub.flush();
  const original = hub.requests()[0].frame;
  const other = central.bus.peers().find(peer => peer.role === 'atelier').id;
  const fake = {protocol: original.protocol, type: 'ack', from: other, to: original.from, requestId: original.requestId, ok: true, message: 'Faux ACK'};
  hub.inject(fake, central.channel);
  await hub.flush();
  assert.equal(settled, false);
  await advance(6000);
  const result = await completion;
  assert.equal(result.code, 'timeout');
  confirm({ok: true, message: 'Trop tard.'});
  hub.inject({...fake, from: original.to}, central.channel);
  await hub.flush();
  assert.equal((await completion).code, 'timeout');
  assert.equal(hub.requests().length, 1);
  assert.equal(calls, 1);
});

await check('Requête livrée après son échéance : aucun changement de vue différé', async ({station, hub, advance}) => {
  let calls = 0;
  const central = station('pilotage');
  station('creation', () => { calls++; return {ok: true}; });
  await hub.flush();
  hub.filter = ({frame}) => frame.type === 'request' ? 'hold' : 'deliver';
  const completion = central.bus.request('creation', valid);
  await hub.flush();
  await advance(6001);
  assert.equal((await completion).code, 'timeout');
  hub.filter = () => 'deliver';
  hub.queue.push(...hub.held.splice(0));
  await hub.flush();
  assert.equal(calls, 0);
  assert.equal(hub.requests().length, 1);
});

await check('Présence expirée ou rôle retiré : station manquante, pas de cible implicite', async ({station, hub, advance}) => {
  const central = station('pilotage');
  const right = station('creation');
  await hub.flush();
  const rightId = central.bus.peers()[0].id;
  hub.filter = ({frame}) => frame.type === 'presence' && frame.from === rightId ? 'drop' : 'deliver';
  await advance(6000);
  assert.deepEqual(central.bus.peers(), []);
  assert.equal((await central.bus.request('creation', valid)).code, 'missing');
  assert.equal(hub.requests().length, 0);
  hub.filter = () => 'deliver';
  right.bus.announce();
  await hub.flush();
  assert.equal(central.bus.peers().length, 1);
  right.bus.dispose();
  await hub.flush();
  assert.deepEqual(central.bus.peers(), []);
});

await check('Dispose, rechargement et canal en erreur : délais nettoyés, aucun rejeu', async ({station, hub, advance}) => {
  let calls = 0;
  const central = station('pilotage');
  const oldRight = station('creation', () => { calls++; return {ok: true}; });
  await hub.flush();
  hub.filter = ({frame}) => frame.type === 'request' ? 'hold' : 'deliver';
  const completion = central.bus.request('creation', valid);
  await hub.flush();
  const original = hub.requests()[0].frame;
  oldRight.bus.dispose(); oldRight.bus.dispose();
  const newRight = station('creation', () => { calls++; return {ok: true}; });
  await hub.flush();
  hub.filter = () => 'deliver';
  hub.inject(original, newRight.channel);
  hub.queue.push(...hub.held.splice(0));
  await hub.flush();
  assert.equal(calls, 0);
  await advance(6000);
  assert.equal((await completion).code, 'timeout');
  const pending = central.bus.request('creation', valid);
  central.bus.dispose(); central.bus.dispose();
  assert.equal((await pending).code, 'unavailable');
  assert.equal(central.bus.available, false);
  assert.deepEqual(central.bus.peers(), []);
  assert.equal(central.bus.announce(), false);
  const replacement = station('pilotage');
  await hub.flush();
  replacement.channel.fail = true;
  const failed = await replacement.bus.request('creation', valid);
  assert.equal(failed.code, 'unavailable');
  assert.equal(replacement.bus.available, false);
  assert.deepEqual(replacement.bus.peers(), []);
  assert.equal(replacement.channel.listeners.size, 0);
});

const moduleUrl = new URL('../dist/lib/display-bus.js', import.meta.url);
const summary = {total: checks.length, passed: checks.filter(item => item.ok).length, failed: checks.filter(item => !item.ok).length};
const report = {
  format: 'bojart.display-bus-qa.v1', checkedAt: new Date(realNow()).toISOString(), runtime: process.version,
  scope: 'Module réel ; doublures BroadcastChannel et horloge virtuelle. Aucun navigateur, réseau, stockage persistant ni matériel.',
  timings: {heartbeatMs: 1500, peerExpiryMs: 6000, requestTimeoutMs: 6000},
  sources: {'dist/lib/display-bus.js': createHash('sha256').update(await readFile(moduleUrl)).digest('hex')},
  summary, checks
};
await writeFile(new URL('./display-bus-results.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(summary));
if (summary.failed) process.exitCode = 1;
