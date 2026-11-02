#!/usr/bin/env node
// Contrôle de la visionneuse figurine dans Chromium sans écran (SwiftShader).
// Usage : node figurine_viewer_check.cjs RUN_DIR [OUT_DIR]
// Prouve les interactions dans ce navigateur logiciel, PAS l'affichage sur la tour réelle.
'use strict';
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('playwright');
const runDir = path.resolve(process.argv[2]);
const outDir = path.resolve(process.argv[3] || path.join(runDir, 'visionneuse'));
const repo = path.resolve(__dirname, '..', '..');
const viewerDir = path.join(repo, 'jarvis/apps/jarvis/app/figurine/viewer');
const vendorDir = path.join(viewerDir, 'vendor');  // three 0.180.0 complet (voir VENDOR.json)
// Personnage sous droits de tiers : aucune capture de sa ressemblance, même depuis un fichier sous
// licence (fiche D14). Le fichier s'ouvre dans la visionneuse, mais ce contrôle n'en produit pas d'image.
const specPath = path.join(runDir, 'spec.json');
const rights = fs.existsSync(specPath) ? ((JSON.parse(fs.readFileSync(specPath, 'utf8')).character || {}).rights) : null;
if (rights !== 'bojart_original') {
  console.error(`Contrôle non lancé : personnage ${rights ? 'sous droits de tiers' : 'inconnu (spec.json absent)'}, aucune capture produite.`);
  process.exit(3);
}
fs.mkdirSync(outDir, { recursive: true });
const routes = {
  '/index.html': path.join(viewerDir, 'index.html'),
  '/vendor/three.module.min.js': path.join(vendorDir, 'three.module.min.js'),
  '/vendor/three.core.min.js': path.join(vendorDir, 'three.core.min.js'),
  '/vendor/OrbitControls.js': path.join(vendorDir, 'OrbitControls.js'),
  '/vendor/STLLoader.js': path.join(vendorDir, 'STLLoader.js'),
  '/parts/figurine.stl': path.join(runDir, 'figurine.stl'),
  '/parts/socle.stl': path.join(runDir, 'socle.stl'),
};
const types = { '.html': 'text/html', '.js': 'text/javascript', '.stl': 'model/stl' };
function stlTriangles(p) { const b = fs.readFileSync(p); return b.readUInt32LE(80); }

(async () => {
  const server = http.createServer((req, res) => {
    const file = routes[req.url.split('?')[0]];
    if (!file || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  }).listen(0, '127.0.0.1');
  await new Promise(r => server.once('listening', r));
  const url = `http://127.0.0.1:${server.address().port}/index.html`;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push(String(e)));
  const results = { url_kind: 'serveur local 127.0.0.1', checks: [], started: new Date().toISOString() };
  const check = (name, ok, detail) => results.checks.push({ name, ok: !!ok, detail });
  const t0 = Date.now();
  await page.goto(url);
  await page.waitForFunction(() => window.__viewer && window.__viewer.state.ready, null, { timeout: 120000 });
  results.load_ms = Date.now() - t0;
  const st = await page.evaluate(() => window.__viewer.state);
  for (const p of ['figurine', 'socle']) {
    const expected = stlTriangles(routes[`/parts/${p}.stl`]);
    check(`chargement ${p}`, st.loaded[p] && st.triangles[p] === expected, { shown: st.triangles[p], file: expected });
  }
  const cam = () => page.evaluate(() => { const c = window.__viewer.camera, t = window.__viewer.controls.target;
    return { pos: c.position.toArray(), dist: c.position.distanceTo(t) }; });
  await page.screenshot({ path: path.join(outDir, 'viewer_trois_quarts.png') });
  // Rotation : glisser la souris au centre.
  const before = await cam();
  await page.mouse.move(640, 480); await page.mouse.down(); await page.mouse.move(820, 430, { steps: 12 }); await page.mouse.up();
  const afterRot = await cam();
  const moved = Math.hypot(...before.pos.map((v, i) => v - afterRot.pos[i]));
  check('rotation à la souris', moved > 1 && Math.abs(afterRot.dist - before.dist) < 1e-3 * before.dist, { camera_moved_mm: +moved.toFixed(1) });
  await page.screenshot({ path: path.join(outDir, 'viewer_apres_rotation.png') });
  // Zoom : molette.
  await page.mouse.move(640, 480); await page.mouse.wheel(0, -600); await page.waitForTimeout(200);
  const afterZoom = await cam();
  check('zoom molette', afterZoom.dist < afterRot.dist * 0.98, { distance_before: +afterRot.dist.toFixed(1), distance_after: +afterZoom.dist.toFixed(1) });
  // Vues normalisées.
  for (const [view, axis, sign] of [['face', 1, -1], ['profil', 0, -1], ['dos', 1, 1], ['trois_quarts', 1, -1]]) {
    await page.click(`[data-view="${view}"]`);
    const v = await page.evaluate(() => { const c = window.__viewer.camera, t = window.__viewer.controls.target;
      return { d: c.position.clone().sub(t).normalize().toArray(), view: window.__viewer.state.view }; });
    check(`vue ${view}`, v.view === view && Math.sign(v.d[axis]) === sign && Math.abs(v.d[axis]) > 0.5, { direction: v.d.map(x => +x.toFixed(3)) });
    await page.screenshot({ path: path.join(outDir, `viewer_${view}.png`) });
  }
  // Pièces séparées.
  await page.click('[data-part="socle"]');
  const vis = await page.evaluate(() => ({ socle: window.__viewer.meshes.socle.visible, figurine: window.__viewer.meshes.figurine.visible }));
  check('masquer le socle', vis.socle === false && vis.figurine === true, vis);
  await page.screenshot({ path: path.join(outDir, 'viewer_figurine_seule.png') });
  await page.click('[data-part="socle"]');
  await page.click('#explode');
  const z = await page.evaluate(() => window.__viewer.meshes.figurine.position.z);
  check('vue éclatée (tenons visibles)', z > 1, { lift_mm: +z.toFixed(1) });
  await page.screenshot({ path: path.join(outDir, 'viewer_eclate.png') });
  await page.click('#wire');
  check('affichage maillage', await page.evaluate(() => window.__viewer.meshes.figurine.material.wireframe === true), null);
  await page.screenshot({ path: path.join(outDir, 'viewer_maillage.png') });
  // Le canevas n'est pas vide : pixels non uniformes.
  const nonEmpty = await page.evaluate(() => { const c = document.querySelector('canvas'); const g = document.createElement('canvas');
    g.width = 64; g.height = 64; const x = g.getContext('2d'); x.drawImage(c, 0, 0, 64, 64);
    const d = x.getImageData(0, 0, 64, 64).data; const s = new Set(); for (let i = 0; i < d.length; i += 4) s.add(d[i] >> 3);
    return s.size; });
  check('canevas non vide', nonEmpty > 4, { distinct_levels: nonEmpty });
  results.console_errors = consoleErrors;
  check('aucune erreur console', consoleErrors.length === 0, consoleErrors.slice(0, 5));
  results.browser = `${browser.browserType().name()} ${browser.version()}`;
  results.gl = await page.evaluate(() => { const g = document.querySelector('canvas').getContext('webgl2');
    const e = g && g.getExtension('WEBGL_debug_renderer_info'); return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'inconnu'; });
  results.passed = results.checks.every(c => c.ok);
  results.scope = 'Chromium sans écran + rendu logiciel ; ne qualifie ni la tour, ni ses trois écrans, ni le tableau de bord Jarvis réel.';
  fs.writeFileSync(path.join(outDir, 'viewer_check.json'), JSON.stringify(results, null, 1));
  console.log(JSON.stringify({ passed: results.passed, checks: results.checks.map(c => `${c.ok ? 'OK ' : 'ÉCHEC '}${c.name}`) }, null, 1));
  await browser.close(); server.close();
  process.exit(results.passed ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
