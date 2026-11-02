'use strict';
// Banc vocal : exécute le VRAI code navigateur de la console Jarvis sur des flux
// micro simulés, sans navigateur ni micro.
//   - jarvis/apps/jarvis/app/voice_endpoint.js : fin de prise par énergie ;
//   - jarvis/apps/jarvis/app/capture.js : encodeur WAV 16 kHz (encodeForTest).
// Non simulés : getUserMedia, AudioWorklet, annulation d'écho, réduction de bruit
// et gain automatique du navigateur.
//
// Entrée : node banc_voix_navigateur.cjs PLAN.json
//   PLAN = {"clips":[{"id":..., "micro":"flux.f32", "taux":48000, "envoi":"sortie.wav"}]}
//   "micro" : échantillons float32 little-endian, mono, au taux indiqué.
// Sortie (stdout) : JSON, une entrée par clip.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const nodeCrypto = require('crypto');

const APP = path.resolve(__dirname, '../jarvis/apps/jarvis/app');
const QUANTUM = 128; // taille d'un bloc AudioWorklet
const MAX_SECONDS = 15; // même limite que capture.js

function loadEndpoint() {
  return require(path.join(APP, 'voice_endpoint.js'));
}

function loadCapture() {
  const window = { addEventListener() {} };
  const sandbox = { window, crypto: globalThis.crypto, console };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(APP, 'capture.js'), 'utf8'), sandbox, { filename: 'capture.js' });
  if (!window.BojCapture || typeof window.BojCapture.encodeForTest !== 'function') {
    throw Error('Encodeur de capture.js introuvable.');
  }
  return window.BojCapture;
}

function sha256(buffer) {
  return nodeCrypto.createHash('sha256').update(buffer).digest('hex');
}

function simulate(clip, endpointApi, capture) {
  const raw = fs.readFileSync(clip.micro);
  const samples = new Float32Array(raw.buffer, raw.byteOffset, Math.floor(raw.length / 4));
  const rate = clip.taux;
  const gate = endpointApi.create();
  const limit = Math.floor(rate * MAX_SECONDS);
  let kept = 0;
  let reason = null;
  // Même découpage que capture.js : blocs successifs, limite à 15 s, arrêt au bloc
  // qui déclenche la fin de prise.
  for (let offset = 0; offset < samples.length && !reason; offset += QUANTUM) {
    const remain = limit - kept;
    if (remain <= 0) { reason = 'limit'; break; }
    const chunk = samples.subarray(offset, Math.min(offset + QUANTUM, samples.length)).subarray(0, remain);
    kept += chunk.length;
    reason = gate.push(chunk, rate);
  }
  // Dans capture.js, un minuteur de 15 s termine la prise si la porte ne l'a pas fait.
  if (!reason && kept >= limit) reason = 'limit';
  const flat = samples.subarray(0, kept);
  const started = process.hrtime.bigint();
  const wav = Buffer.from(new Uint8Array(capture.encodeForTest(flat, rate)));
  const encodeMs = Number(process.hrtime.bigint() - started) / 1e6;
  fs.writeFileSync(clip.envoi, wav);
  return {
    id: clip.id,
    raison: reason, // 'pause' | 'limit' | 'no_speech' | null (flux terminé avant décision)
    fin_de_prise_s: kept / rate,
    envoi_octets: wav.length,
    envoi_sha256: sha256(wav),
    encodage_ms: Math.round(encodeMs * 1000) / 1000,
  };
}

function main() {
  const planPath = process.argv[2];
  if (!planPath) throw Error('Usage : node banc_voix_navigateur.cjs PLAN.json');
  const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
  const endpointApi = loadEndpoint();
  const capture = loadCapture();
  const sources = {};
  for (const name of ['voice_endpoint.js', 'capture.js']) {
    sources[name] = sha256(fs.readFileSync(path.join(APP, name)));
  }
  const results = plan.clips.map((clip) => simulate(clip, endpointApi, capture));
  process.stdout.write(JSON.stringify({ node: process.version, sources, resultats: results }));
}

main();
