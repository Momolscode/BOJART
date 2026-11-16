/** Portable binary export. A metadata journal remains a separate, explicit backup. */
import {canonicalWorkshopJSON} from './workshop.js';
import {assetSHA256} from './workshop-assets.js';

export const BROWSER_ASSET_BACKUP_LIMIT = 268435456;
const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const SHA = /^[a-f0-9]{64}$/;

export function referencedWorkshopAssets(state, journal = null) {
  const found = new Map();
  function add(id, sha256 = null) {
    if (!id) return;
    if (typeof id !== 'string' || !ID.test(id) || sha256 !== null && !SHA.test(sha256)) throw new Error('Une référence de STL est invalide.');
    const previous = found.get(id);
    if (previous?.sha256 && sha256 && previous.sha256 !== sha256) throw new Error('Un même fichier possède deux empreintes dans le journal.');
    found.set(id, {id, sha256: sha256 || previous?.sha256 || null});
  }
  for (const project of state?.projects || []) for (const piece of project.pieces || []) add(piece.assetId, piece.assetSha256 || null);
  for (const project of journal?.authority?.genesis?.state?.projects || []) for (const piece of project.pieces || []) add(piece.assetId, piece.assetSha256 || null);
  for (const operation of journal?.operations || []) if (operation.type === 'UPDATE_PIECE') add(operation.payload?.patch?.assetId, operation.payload?.patch?.assetSha256 || null);
  return [...found.values()].sort((a, b) => a.id.localeCompare(b.id, 'en'));
}

export async function createBrowserAssetsBackup(state, {journal = null, readAsset, exportedAt = Date.now(), onProgress = () => {}} = {}) {
  if (typeof readAsset !== 'function' || !Number.isSafeInteger(exportedAt) || exportedAt < 0) throw new Error('Le lecteur de fichiers et la date de sauvegarde sont requis.');
  const references = referencedWorkshopAssets(state, journal);
  if (references.length > 10000) throw new Error('Cette sauvegarde dépasse 10 000 références de fichiers.');
  const assets = [], buffers = [];
  let byteLength = 12;
  for (const reference of references) {
    const stored = await readAsset(reference.id, {expectedSha256: reference.sha256});
    if (!stored?.buffer) throw new Error('Le fichier ' + reference.id + ' est absent. Retrouvez cet original avant de créer la sauvegarde des STL.');
    const name = stored.name;
    if (typeof name !== 'string' || !name.trim() || name.length > 255 || /[\u0000-\u001f\u007f/\\]/.test(name) || !/\.stl$/i.test(name)) throw new Error('Le nom de ce fichier STL est invalide.');
    const size = stored.buffer.byteLength;
    if (!Number.isSafeInteger(size) || size < 1 || size > 52428800) throw new Error('Chaque STL doit être non vide et limité à 50 Mio.');
    byteLength += size;
    if (byteLength > BROWSER_ASSET_BACKUP_LIMIT) throw new Error('Les fichiers dépassent 256 Mio. Utilisez le coffre de la tour pour sauvegarder ce volume.');
    const sha256 = await assetSHA256(stored.buffer);
    if (reference.sha256 && sha256 !== reference.sha256 || stored.sha256 && sha256 !== stored.sha256) throw new Error('Le contenu de ' + name + ' ne correspond pas à son empreinte conservée.');
    if (!Number.isSafeInteger(stored.createdAt) || stored.createdAt < 0) throw new Error('La date du fichier ' + name + ' est invalide.');
    assets.push({id: reference.id, name, sha256, byteLength: size, createdAt: stored.createdAt, format: 'stl'});
    buffers.push(stored.buffer);
    onProgress({completed: assets.length, total: references.length});
  }
  const body = {format: 'bojart.assets.backup.v1', exportedAt, assets};
  const manifest = {...body, sha256: await assetSHA256(new TextEncoder().encode(canonicalWorkshopJSON(body)))};
  const encoded = new TextEncoder().encode(JSON.stringify(manifest));
  if (encoded.byteLength > 16777216 || byteLength + encoded.byteLength > BROWSER_ASSET_BACKUP_LIMIT) throw new Error('La sauvegarde dépasse la limite de 256 Mio du navigateur.');
  const header = new Uint8Array(12);
  header.set(new TextEncoder().encode('BOJAST01'));
  new DataView(header.buffer).setUint32(8, encoded.byteLength, false);
  return {blob: new Blob([header, encoded, ...buffers], {type: 'application/octet-stream'}), manifest,
    summary: {files: assets.length, bytes: byteLength + encoded.byteLength, includes: ['stl_binaries', 'asset_manifests'], excludes: ['workshop_journal', 'credentials', 'printer_state']}};
}
