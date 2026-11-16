/** File evidence is measured locally, scoped to a piece revision, and never a print approval. */
import {inspectDeclaredPreparation} from './preparation.js';

const copy = value => JSON.parse(JSON.stringify(value));
export function preparationReportContext(report) {
  if (!report?.project || !Array.isArray(report.pieces) || report.pieces.some(piece=>!piece||typeof piece!=='object') || !Array.isArray(report.machines)) return null;
  return JSON.stringify({project: report.project, machines: report.machines, pieces: report.pieces.map(piece => ({
    id: piece.id, name: piece.name, revision: piece.revision, tech: piece.tech, unit: piece.unit,
    assetId: piece.assetId, assetSha256: piece.assetSha256 || null, storedDimensionsMm: piece.storedDimensionsMm
  }))});
}
const pieceKey = (projectId, piece) => JSON.stringify([projectId, piece.id, piece.revision || 1, piece.assetId || null, piece.assetSha256 || null, piece.unit || 'mm', piece.tech, piece.dims]);
const geometryKey = project => JSON.stringify([project.id, project.pieces.map(piece => pieceKey(project.id, piece))]);

export function createProjectEvidence({getState, readAsset, inspectSTL, now = Date.now, onChange = () => {}, cryptoImpl = globalThis.crypto} = {}) {
  if (![getState, readAsset, inspectSTL].every(fn => typeof fn === 'function')) throw new TypeError('Les lecteurs du dossier et des STL sont requis.');
  const proofs = new Map(), audits = new Map();
  let serial = Promise.resolve(), disposed = false;
  const projectOf = id => getState().projects.find(project => project.id === id);
  function report(projectId) {
    const project = projectOf(projectId);
    if (!project) throw new Error('Le dossier n’existe plus.');
    return inspectDeclaredPreparation(getState(), projectId, {assetEvidence: project.pieces.map(piece => proofs.get(pieceKey(projectId, piece))).filter(Boolean)});
  }
  function snapshot(projectId) {
    const current = report(projectId), audit = audits.get(projectId);
    const status = audit?.key === geometryKey(projectOf(projectId)) ? audit.status : 'unchecked';
    return {report: current, status, checkedAt: status === 'checked' ? audit.checkedAt : null};
  }
  function changed(projectId) { if (!disposed && projectOf(projectId)) onChange({projectId, ...snapshot(projectId)}); }
  function absorb(inspected) {
    if(inspected?.format!=='bojart.declared-preparation.v1'||inspected.brand!=='BOJ.ART'||inspected.canSlice!==false||inspected.canStartPhysicalPrint!==false)return false;
    const project = projectOf(inspected?.project?.id);
    if (!project || preparationReportContext(inspected) !== preparationReportContext(inspectDeclaredPreparation(getState(), project.id))) return false;
    let updated=false;
    for (const item of inspected.pieces) {
      const piece = project.pieces.find(candidate => candidate.id === item.id);
      if (!piece || !['measured', 'missing', 'invalid'].includes(item.file?.status)) continue;
      const key=pieceKey(project.id,piece),proof={...copy(item.file),projectId: project.id, pieceId: piece.id, pieceRevision: piece.revision || 1,
        assetId: piece.assetId, unit: piece.unit || 'mm', dimsMm: item.dimensionsMm ? [...item.dimensionsMm] : null};
      if(JSON.stringify(proofs.get(key))!==JSON.stringify(proof)){proofs.set(key,proof);updated=true;}
    }
    return updated;
  }
  function inspect(projectId, {force = false} = {}) {
    if (disposed) return Promise.resolve(null);
    const project = projectOf(projectId);
    if (!project) return Promise.resolve(null);
    const key = geometryKey(project), previous = audits.get(projectId);
    if (!force && previous?.key === key && ['checking', 'checked'].includes(previous.status)) return previous.promise || Promise.resolve(snapshot(projectId));
    const audit = {key, status: 'checking', checkedAt: null, token: Symbol(projectId), promise: null};
    const pieces = copy(project.pieces.filter(piece => piece.assetId));
    audits.set(projectId, audit);
    if (force) for (const piece of pieces) proofs.delete(pieceKey(projectId, piece));
    const isCurrent = () => !disposed && audits.get(projectId) === audit && projectOf(projectId) && geometryKey(projectOf(projectId)) === key;
    audit.promise = serial.catch(() => {}).then(async () => {
      if (!isCurrent()) return null;
      for (const piece of pieces) {
        const proofKey = pieceKey(projectId, piece);
        if (!force && proofs.has(proofKey)) continue;
        const base = {projectId, pieceId: piece.id, pieceRevision: piece.revision || 1, assetId: piece.assetId, unit: piece.unit || 'mm', checkedAt: now()};
        let proof;
        try {
          const stored = await readAsset(piece.assetId,{expectedSha256:piece.assetSha256||null});
          if (!isCurrent()) return null;
          if (!stored?.buffer) proof = {...base, status: 'missing', message: 'Le STL n’est pas accessible depuis ce poste.'};
          else {
            try {
              const measured = await inspectSTL(stored.buffer, base.unit);
              if (!isCurrent()) return null;
              let sha256 = null;
              if (cryptoImpl?.subtle) {
                let bytes=null;try{bytes = await cryptoImpl.subtle.digest('SHA-256', stored.buffer);}catch{}
                if (!isCurrent()) return null;
                if(bytes)sha256 = Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
              }
              proof = {...base, status: 'measured', dimsMm: [...measured.dims], triangles: measured.triangles, byteLength: stored.buffer.byteLength, sha256};
            } catch (error) { proof = {...base, status: 'invalid', message: String(error?.message || 'Le STL ne peut pas être mesuré.').slice(0, 240)}; }
          }
        } catch (error) { proof = {...base, status: error?.code==='checksum_mismatch'?'invalid':'missing', message: String(error?.message || 'Le fichier est inaccessible.').slice(0, 240)}; }
        if (!isCurrent()) return null;
        proofs.set(proofKey, proof);
        changed(projectId);
      }
      if (!isCurrent()) return null;
      audit.status = 'checked'; audit.checkedAt = now();
      changed(projectId);
      return snapshot(projectId);
    }).catch(error => {
      if (isCurrent()) { audit.status = 'error'; audit.message = String(error?.message || 'Lecture interrompue.'); changed(projectId); }
      return null;
    });
    serial = audit.promise;
    changed(projectId);
    return audit.promise;
  }
  return {report, snapshot, inspect, absorb, dispose() { disposed = true; proofs.clear(); audits.clear(); }};
}
