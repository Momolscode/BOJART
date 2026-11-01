/** Portable BOJ.ART inquiry contract. No network, server, or Node imports. */
export const INQUIRY_FORMAT = 'bojart.inquiry.v1';
export const EXPORT_FORMAT = 'bojart.inquiry.export.v1';
export const PRIVACY_VERSION = '2026-10-19';
export const PRIVACY_VERSIONS = Object.freeze(['2026-10-19']);
export const OFFERS = Object.freeze(['artwork', 'custom', 'prototype']);
export const BUDGET_RANGES = Object.freeze(['undecided', 'under_250', '250_750', '750_1500', '1500_3000', 'over_3000']);
export const MODEL_STATUSES = Object.freeze(['idea', 'reference', 'file_ready']);
export const INQUIRY_STATUSES = Object.freeze(['new', 'reviewing', 'awaiting_details', 'quoted', 'accepted', 'declined', 'archived']);
export const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TOP_KEYS = new Set(['format', 'requestId', 'offer', 'name', 'email', 'phone', 'description', 'intendedUse', 'dimensions', 'quantity', 'budgetRange', 'deadline', 'modelStatus', 'referenceURLs', 'artworkId', 'source', 'privacyAcknowledged', 'website']);
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value) && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);

export class InquiryError extends Error {
  constructor(code, message, status = 422, fields = undefined) {
    super(message);
    this.name = 'InquiryError';
    this.code = code;
    this.status = status;
    this.fields = fields;
  }
}
function cleaned(value, { multiline = false } = {}) {
  if (typeof value !== 'string') return null;
  const result = value.replace(/\r\n?/g, '\n').normalize('NFC').trim();
  if ((multiline ? /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/ : /[\u0000-\u001F\u007F]/).test(result)) return null;
  return result;
}
export function canonicalJSON(value) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonicalJSON).join(',') + ']';
  if (plain(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonicalJSON(value[key])).join(',') + '}';
  throw new InquiryError('invalid_data', 'Le document contient une valeur non portable.', 422);
}
export async function sha256(value, cryptoImpl = globalThis.crypto) {
  if (!cryptoImpl?.subtle) throw new InquiryError('crypto_unavailable', 'La vérification du document est indisponible.', 503);
  const bytes = typeof value === 'string' ? new TextEncoder().encode(value) : value;
  const digest = new Uint8Array(await cryptoImpl.subtle.digest('SHA-256', bytes));
  return Array.from(digest, b => b.toString(16).padStart(2, '0')).join('');
}
export function isPublicReference(value) {
  if (typeof value !== 'string' || value.length > 2000) return false;
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase().replace(/\.$/, '');
    if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443')) return false;
    if (!host.includes('.') || host.includes(':') || /^\d+(\.\d+){3}$/.test(host)) return false;
    return !/(^|\.)(localhost|local|internal|lan|test|invalid|example|onion)$/.test(host);
  } catch { return false; }
}
export function normalizeInquiry(input) {
  if (!plain(input)) throw new InquiryError('invalid_request', 'La demande doit être un objet JSON.', 422, { _form: 'Format de demande invalide.' });
  const errors = {};
  const out = {};
  if (Object.keys(input).some(key => !TOP_KEYS.has(key))) errors._form = 'La demande contient des champs inconnus.';
  if (input.format !== INQUIRY_FORMAT) errors.format = 'Version de demande non reconnue.';
  out.format = INQUIRY_FORMAT;
  if (typeof input.requestId !== 'string' || !UUID_RE.test(input.requestId)) errors.requestId = 'Identifiant de demande invalide.';
  else out.requestId = input.requestId.toLowerCase();
  if (!OFFERS.includes(input.offer)) errors.offer = 'Choisissez une famille de projet.';
  else out.offer = input.offer;
  function field(key, min, max, options = {}) {
    const value = input[key];
    if (options.optional && (value === undefined || value === null || value === '')) return;
    const text = cleaned(value, options);
    if (text === null || text.length < min || text.length > max) errors[key] = `Utilisez entre ${min} et ${max} caractères.`;
    else out[key] = text;
  }
  field('name', 2, 100);
  field('email', 3, 254);
  if (out.email && !/^[^\s@<>"(),:;\\\[\]]+@[^\s@<>"(),:;\\\[\]]+\.[^\s@<>"(),:;\\\[\]]+$/.test(out.email)) errors.email = 'Renseignez une adresse e-mail valide.';
  field('phone', 3, 40, { optional: true });
  if (out.phone && !/^[+\d().\s-]+$/.test(out.phone)) errors.phone = 'Utilisez uniquement chiffres, espaces et signes de téléphone.';
  field('description', 20, 6000, { multiline: true });
  field('intendedUse', 1, 1000, { optional: true, multiline: true });
  if (input.dimensions !== undefined && input.dimensions !== null) {
    const dimensions = input.dimensions;
    if (!plain(dimensions) || !Object.keys(dimensions).length || Object.keys(dimensions).some(key => !['widthMm', 'heightMm', 'depthMm'].includes(key))) errors.dimensions = 'Renseignez les dimensions en millimètres.';
    else {
      out.dimensions = {};
      for (const key of ['widthMm', 'heightMm', 'depthMm']) {
        if (dimensions[key] === undefined) continue;
        if (typeof dimensions[key] !== 'number' || !Number.isFinite(dimensions[key]) || dimensions[key] <= 0 || dimensions[key] > 100000) errors.dimensions = 'Chaque dimension doit être positive, au plus 100 000 mm.';
        else out.dimensions[key] = dimensions[key];
      }
      if (!Object.keys(out.dimensions).length) errors.dimensions = 'Renseignez au moins une dimension.';
    }
  }
  if (!Number.isInteger(input.quantity) || input.quantity < 1 || input.quantity > 1000) errors.quantity = 'La quantité doit être un entier de 1 à 1 000.';
  else out.quantity = input.quantity;
  if (!BUDGET_RANGES.includes(input.budgetRange)) errors.budgetRange = 'Choisissez une préférence de budget.';
  else out.budgetRange = input.budgetRange;
  if (input.deadline !== undefined && input.deadline !== null && input.deadline !== '') {
    const date = typeof input.deadline === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(input.deadline) ? new Date(input.deadline + 'T00:00:00.000Z') : null;
    if (!date || !Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== input.deadline || date.getUTCFullYear() < 1900 || date.getUTCFullYear() > 2100) errors.deadline = 'Renseignez une date valide.';
    else out.deadline = input.deadline;
  }
  if (!MODEL_STATUSES.includes(input.modelStatus)) errors.modelStatus = 'Précisez le point de départ du projet.';
  else out.modelStatus = input.modelStatus;
  if (!Array.isArray(input.referenceURLs) || input.referenceURLs.length > 5) errors.referenceURLs = 'Ajoutez au plus cinq liens de référence.';
  else {
    out.referenceURLs = [];
    for (const value of input.referenceURLs) {
      const text = cleaned(value);
      if (!text || !isPublicReference(text)) errors.referenceURLs = 'Utilisez des liens HTTPS publics, sans identifiants ni adresse réseau privée.';
      else if (!out.referenceURLs.includes(text)) out.referenceURLs.push(text);
    }
  }
  field('artworkId', 1, 80, { optional: true });
  if (out.artworkId && !/^[A-Za-z0-9_-]+$/.test(out.artworkId)) errors.artworkId = 'La référence de création est invalide.';
  if (input.source !== undefined && input.source !== null) {
    if (!plain(input.source) || Object.keys(input.source).some(key => !['entryPath', 'utmSource', 'utmMedium', 'utmCampaign'].includes(key))) errors.source = 'L’origine de la demande est invalide.';
    else {
      out.source = {};
      const entryPath = cleaned(input.source.entryPath);
      if (!entryPath || entryPath.length > 200 || !/^\/(?!\/)[A-Za-z0-9/_-]*$/.test(entryPath)) errors.source = 'Le chemin d’origine est invalide.';
      else out.source.entryPath = entryPath;
      for (const key of ['utmSource', 'utmMedium', 'utmCampaign']) {
        if (input.source[key] === undefined || input.source[key] === '') continue;
        const value = cleaned(input.source[key]);
        if (!value || value.length > 80 || !/^[A-Za-z0-9_. -]+$/.test(value)) errors.source = 'Les paramètres de campagne doivent être de courts libellés sans données personnelles.';
        else out.source[key] = value;
      }
    }
  }
  if (input.privacyAcknowledged !== true) errors.privacyAcknowledged = 'Veuillez prendre connaissance de l’information sur vos données.';
  else out.privacyAcknowledged = true;
  if (input.website !== undefined && (typeof input.website !== 'string' || input.website.trim() !== '')) errors._form = 'La demande n’a pas pu être validée.';
  if (Object.keys(errors).length) throw new InquiryError('validation_failed', 'Vérifiez les champs indiqués.', 422, errors);
  return out;
}
export function normalizeInquiryRecord(record) {
  if (!plain(record)) throw new InquiryError('invalid_record', 'Le dossier de demande est invalide.');
  const extras = new Set(['reference', 'createdAt', 'updatedAt', 'status', 'revision', 'privacyVersion']);
  const raw = {};
  for (const [key, value] of Object.entries(record)) if (!extras.has(key)) raw[key] = value;
  const inquiry = normalizeInquiry(raw);
  if (typeof record.reference !== 'string' || !/^BOJ-\d{8}-[A-F0-9]{12}$/.test(record.reference)) throw new InquiryError('invalid_record', 'Référence de demande invalide.');
  const validISO = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value) && Number.isFinite(new Date(value).getTime()) && new Date(value).toISOString() === value;
  if (!validISO(record.createdAt) || !validISO(record.updatedAt) || record.updatedAt < record.createdAt) throw new InquiryError('invalid_record', 'Dates de demande invalides.');
  if (!INQUIRY_STATUSES.includes(record.status) || !Number.isInteger(record.revision) || record.revision < 1 || record.revision > 1000000 || !PRIVACY_VERSIONS.includes(record.privacyVersion)) throw new InquiryError('invalid_record', 'Version ou statut de demande invalide.');
  return { ...inquiry, reference: record.reference, createdAt: record.createdAt, updatedAt: record.updatedAt, status: record.status, revision: record.revision, privacyVersion: record.privacyVersion };
}
export async function createInquiryExport(record, { exportedAt = new Date().toISOString(), cryptoImpl = globalThis.crypto } = {}) {
  const inquiry = normalizeInquiryRecord(record);
  const body = { format: EXPORT_FORMAT, exportedAt, source: 'BOJ.ART', inquiry };
  return { ...body, sha256: await sha256(canonicalJSON(body), cryptoImpl) };
}
export async function verifyInquiryExport(input, { cryptoImpl = globalThis.crypto } = {}) {
  if (!plain(input) || Object.keys(input).some(key => !['format', 'exportedAt', 'source', 'inquiry', 'sha256'].includes(key)) || input.format !== EXPORT_FORMAT || input.source !== 'BOJ.ART' || typeof input.exportedAt !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(input.exportedAt) || !Number.isFinite(new Date(input.exportedAt).getTime()) || new Date(input.exportedAt).toISOString() !== input.exportedAt || !/^[a-f0-9]{64}$/.test(input.sha256)) throw new InquiryError('invalid_export', 'Le fichier n’est pas un export BOJ.ART reconnu.');
  const body = { format: input.format, exportedAt: input.exportedAt, source: input.source, inquiry: input.inquiry };
  const expected = await sha256(canonicalJSON(body), cryptoImpl);
  if (expected !== input.sha256) throw new InquiryError('checksum_mismatch', 'L’empreinte de l’export ne correspond pas à son contenu.');
  const inquiry = normalizeInquiryRecord(input.inquiry);
  if (canonicalJSON(inquiry) !== canonicalJSON(input.inquiry)) throw new InquiryError('invalid_export', 'L’export contient une demande non normalisée.');
  return { ...body, inquiry, sha256: input.sha256 };
}
