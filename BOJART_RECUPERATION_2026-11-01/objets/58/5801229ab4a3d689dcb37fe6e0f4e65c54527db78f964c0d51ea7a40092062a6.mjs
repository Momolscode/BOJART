import { mkdir, writeFile, readFile, open, rename, chmod } from 'node:fs/promises';
import { createReadStream, createWriteStream } from 'node:fs';
import { createBrotliDecompress, brotliDecompressSync } from 'node:zlib';
import { pipeline } from 'node:stream/promises';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
const folder = resolve('../browser');
await mkdir(folder, { recursive: true });
const archiveRoot = resolve('node_modules/@sparticuz/chromium/bin');
const path = resolve(folder, 'chromium');
const binary = brotliDecompressSync(await readFile(archiveRoot + '/chromium.br'));
const staged = path + '.stage';
const handle = await open(staged, 'w', 0o755);
try { await handle.writeFile(binary); await handle.sync(); } finally { await handle.close(); }
await rename(staged, path);
for (const name of ['fonts', 'swiftshader', 'al2023']) {
  const tar = resolve(folder, name + '.tar');
  await pipeline(createReadStream(archiveRoot + '/' + name + '.tar.br'), createBrotliDecompress(), createWriteStream(tar));
  const extracted = spawnSync('tar', ['--no-same-owner', '--no-same-permissions', '-xf', tar, '-C', folder], { encoding: 'utf8' });
  if (extracted.status !== 0) throw new Error(extracted.stderr);
}
await chmod(path, 0o755);
const actual = await readFile(path);
if (!actual.equals(binary)) throw new Error('Chromium extraction checksum mismatch');
const env = { ...process.env, LD_LIBRARY_PATH: folder + '/lib:' + folder, FONTCONFIG_PATH: folder + '/fonts' };
const result = spawnSync(path, ['--version'], { encoding: 'utf8', env });
if (result.status !== 0) throw new Error(result.stderr || 'Browser probe failed');
const wrapper = resolve(folder, 'chrome-local');
const quote = v => "'" + v.replaceAll("'", "'\\''") + "'";
await writeFile(wrapper, '#!/bin/sh\nexport LD_LIBRARY_PATH=' + quote(env.LD_LIBRARY_PATH) + '\nexport FONTCONFIG_PATH=' + quote(env.FONTCONFIG_PATH) + '\nexec ' + quote(path) + ' "$@"\n');
await chmod(wrapper, 0o755);
const profile = JSON.parse(await readFile('hypit.runtime.json', 'utf8'));
profile.endpoints['html.local'].config.chromePath = wrapper;
await writeFile('hypit.runtime.json', JSON.stringify(profile, null, 2) + '\n');
await writeFile('../evidence/browser.json', JSON.stringify({ path: wrapper, binary: path, version: result.stdout.trim(), sha256: createHash('sha256').update(actual).digest('hex'), size: actual.length, source: '@sparticuz/chromium@153.0.0', extraction: 'Node Brotli, fsync, checksum and tar without archive ownership restoration' }, null, 2));
console.log(JSON.stringify({ path: wrapper, version: result.stdout.trim() }));
