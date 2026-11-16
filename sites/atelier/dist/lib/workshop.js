// BOJ.ART workshop state and append-only operations. No physical machine commands.
// Dimensions are millimetres. Durations and machine profiles below are fictitious.
import {normalizeFleetRecord} from './fleet-registry.js';
import {EDIT_LIMITS,normalizeEditPlan,latestEditVersion} from './edit-plan.js';
import {normalizeInquiryLink,inquiryProjectId,validateInquiryProjectPayload} from './inquiry-import.js';
const PREFIX = 'bojart.workshop.v1.';
const SEED_KEY = PREFIX + 'seed';
const OP_PREFIX = PREFIX + 'op.';
const AUTHORITY_KEY = PREFIX + 'authority.v2';
export const WORKSHOP_REDUCER_VERSION = 'bojart.reducer.v2';
const HOUR = 3600000;
const TYPES = new Set(['SELECT_PROJECT', 'SELECT_PIECE', 'UPDATE_PROJECT', 'ADD_PROJECT', 'UPDATE_PIECE', 'PLAN_PROJECT', 'TOGGLE_MACHINE', 'UPDATE_MACHINE', 'SAVE_QUOTE', 'SAVE_STORY', 'SAVE_EDIT_PLAN', 'LOG']);
const memory = new Map();
const memoryStorage = {
  get length() { return memory.size; },
  key(index) { return [...memory.keys()][index] ?? null; },
  getItem(key) { return memory.get(key) ?? null; },
  setItem(key, value) { memory.set(key, String(value)); }
};
const clone = value => JSON.parse(JSON.stringify(value));
const uid = prefix => prefix + '-' + (globalThis.crypto?.randomUUID?.() || Date.now().toString(36) + '-' + Math.random().toString(36).slice(2));
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const error = message => { throw new Error(message); };

function object(value, label = 'Données') {
  if (!value || typeof value !== 'object' || Array.isArray(value)) error(label + ' invalides.');
  return value;
}
function text(value, label, max = 160, empty = false) {
  if (typeof value !== 'string') error(label + ' doit être du texte.');
  const result = value.trim();
  if ((!empty && !result) || result.length > max) error(label + ' invalide.');
  return result;
}
function number(value, label, min = 0, max = Number.MAX_SAFE_INTEGER) {
  if ((typeof value !== 'number' && typeof value !== 'string') || (typeof value === 'string' && !value.trim())) error(label + ' doit être renseigné.');
  const result = Number(value);
  if (!Number.isFinite(result) || result < min || result > max) error(label + ' invalide.');
  return result;
}
function integer(value, label, min = 1) {
  const result = number(value, label, min);
  if (!Number.isSafeInteger(result)) error(label + ' doit être un entier.');
  return result;
}
function dimensions(value, label, allowFlat = false) {
  if (!Array.isArray(value) || value.length !== 3) error(label + ' : trois dimensions requises.');
  const result = value.map(v => number(v, label));
  if (result.every(v => v === 0) || (!allowFlat && result.some(v => v === 0))) error(label + ' invalides.');
  return result;
}
function technology(value) {
  if (value !== 'resin' && value !== 'fdm') error('Procédé attendu : resin ou fdm.');
  return value;
}
function optionalId(value) { return value === null || value === '' ? null : text(value, 'Identifiant'); }
function patchKeys(patch, allowed) {
  object(patch, 'Modifications');
  for (const key of Object.keys(patch)) if (!allowed.includes(key)) error('Champ non modifiable : ' + key + '.');
}

/** Material, hours and other costs cover the complete lot; rate is hourly. */
export function calculateQuote({ material, hours, rate, other, margin, fee = 0, quantity = 1 } = {}) {
  const m = number(material, 'Coût matière');
  const h = number(hours, 'Temps de travail');
  const r = number(rate, 'Taux horaire');
  const o = number(other, 'Autres coûts');
  const marginPct = number(margin, 'Marge', 0, 100);
  const feePct = number(fee, 'Commission', 0, 100);
  const q = integer(quantity, 'Quantité');
  if (marginPct + feePct >= 100) error('La somme marge + commission doit être inférieure à 100 %.');
  const cost = m + h * r + o;
  const price = cost / (1 - (marginPct + feePct) / 100);
  if (![cost, price, price / q].every(Number.isFinite)) error('Montants hors limites.');
  // Keep full precision; round only when formatting money in the interface.
  return { cost, price, unitPrice: price / q };
}

/** Read-only progress: reaching 100 does not issue a completion operation. */
export function jobProgress(job, now = Date.now()) {
  if (!job || !Number.isFinite(job.duration) || job.duration <= 0) return 0;
  if (job.status === 'done') return 100;
  let elapsed = Number.isFinite(job.elapsed) ? Math.max(0, job.elapsed) : 0;
  if (job.status === 'running' && Number.isFinite(job.startedAt) && Number.isFinite(now)) elapsed += Math.max(0, now - job.startedAt);
  return Math.min(100, Math.max(0, elapsed / job.duration * 100));
}

function fits(piece, machine) {
  if (piece.tech !== machine.tech || piece.dims.some(v => v <= 0)) return false;
  const [x, y, z] = piece.dims;
  return [[x,y,z],[x,z,y],[y,x,z],[y,z,x],[z,x,y],[z,y,x]].some(d => d.every((v, i) => v <= machine.volume[i]));
}
const active = job => job.status === 'running' || job.status === 'paused';
const jobId = (project, piece) => 'job-' + project.id + '-' + piece.id + '-r' + (piece.revision || 1);
function piece(id, name, tech, dims, machine = null) {
  return { id, name, tech, dims, machine, assetId: null, triangles: 0, unit: 'mm', revision: 1 };
}
function seed(at) {
  const machines = Array.from({ length: 8 }, (_, i) => {
    const id = 'P' + String(i + 1).padStart(2, '0');
    const resin = i < 5;
    return { id, name: (resin ? 'Résine ' : 'FDM ') + id + ' · démo', tech: resin ? 'resin' : 'fdm', volume: resin ? (i === 4 ? [300,165,300] : [220,130,250]) : (i === 5 ? [350,350,400] : i === 6 ? [256,256,256] : [300,300,300]), material: resin ? 'Résine UV · exemple' : 'PLA · exemple', qualified: false };
  });
  const projects = [
    { id: 'sculpture-xl', name: 'SCULPTURE XL', subtitle: 'Baki · étude de fabrication', kind: 'sculpture', quantity: 1, height: 1000, notes: 'Scénario de démonstration. Figurine en résine segmentée, socle FDM. Dimensions et durées fictives ; préparation et fabrication non qualifiées.', status: 'Étude · démonstration', media: 'baki-hero.webp', revision: 1,
      pieces: [piece('buste','Buste','resin',[170,110,230],'P01'),piece('tete','Tête','resin',[125,115,155],'P02'),piece('bras-gauche','Bras gauche','resin',[72,88,230],'P03'),piece('bras-droit','Bras droit','resin',[75,86,220],'P04'),piece('jambes','Jambes','resin',[170,115,240],'P05'),piece('socle','Socle','fdm',[300,270,95],'P06')], quote: null, story: '' },
    { id: 'prototype', name: 'PROTOTYPE', subtitle: 'Boîtier · étude fonctionnelle', kind: 'prototype', quantity: 2, height: 85, notes: 'Boîtier de démonstration. Aucun essai de montage ni validation fonctionnelle réalisés.', status: 'Conception · démonstration', media: null, revision: 1,
      pieces: [piece('boitier','Corps du boîtier','fdm',[160,110,65],'P07'),piece('couvercle','Couvercle','fdm',[165,115,20],'P08')], quote: null, story: '' },
    { id: 'commande-art', name: 'COMMANDE ART', subtitle: 'Composition · sur mesure', kind: 'art', quantity: 1, height: 350, notes: 'Composition fictive sur mesure ; intention artistique et faisabilité à définir.', status: 'Brief · démonstration', media: null, revision: 1,
      pieces: [piece('forme','Forme principale','resin',[150,110,210],'P05'),piece('detail','Détail sculpté','resin',[80,55,95],'P04'),piece('socle','Socle de présentation','fdm',[220,180,45],'P08')], quote: null, story: '' }
  ];
  const jobs = [];
  function initial(projectIndex, pieceIndex, status, duration, progress) {
    const project = projects[projectIndex], item = project.pieces[pieceIndex];
    jobs.push({ id: jobId(project,item), projectId: project.id, pieceId: item.id, machine: item.machine, status, duration, elapsed: status === 'paused' ? duration * progress : 0, startedAt: status === 'running' ? at - duration * progress : null, revision: item.revision, quantity: project.quantity, assetId: null, dims: [...item.dims], tech: item.tech, pieceName: item.name, simulated: true });
  }
  initial(0,0,'running',5*HOUR,.62);
  initial(0,1,'running',3*HOUR,.37);
  initial(0,2,'paused',4*HOUR,.48);
  initial(0,5,'queued',7*HOUR,0);
  initial(1,0,'running',4*HOUR,.76);
  return { projectId: projects[0].id, selectedPieceId: projects[0].pieces[0].id, projects, machines, jobs, journal: [{ id: 'demo-seed', at, type: 'SEED', message: 'Démonstration initialisée. Aucune machine ni aucun compte connecté.', projectId: projects[0].id, projectName: projects[0].name, pieceId: null, machineId: null, ok: true }] };
}

function getProject(state, id) {
  const result = state.projects.find(p => p.id === id);
  if (!result) error('Projet introuvable.');
  return result;
}
function getMachine(state, id) {
  const result = state.machines.find(m => m.id === id);
  if (!result) error('Machine de démonstration introuvable.');
  return result;
}
function invalidate(project) { project.quote = null; project.revision = (project.revision || 1) + 1; }
function projectPatch(raw) {
  patchKeys(raw, ['name','subtitle','kind','quantity','height','notes','status','media']);
  const out = {};
  for (const [key,value] of Object.entries(raw)) {
    if (key === 'quantity') out[key] = integer(value,'Quantité');
    else if (key === 'height') out[key] = value===null?null:number(value,'Hauteur demandée',Number.EPSILON);
    else if (key === 'media') out[key] = value === null ? null : text(value,'Média',500,true);
    else out[key] = text(value,key,key === 'notes' ? 8000 : 300,['subtitle','notes'].includes(key));
  }
  return out;
}
function piecePatch(raw) {
  patchKeys(raw,['name','tech','dims','machine','assetId','assetSha256','triangles','unit','revision']);
  const out = {};
  for (const [key,value] of Object.entries(raw)) {
    if (key === 'name') out[key] = text(value,'Nom de pièce',300);
    else if (key === 'tech') out[key] = technology(value);
    else if (key === 'dims') out[key] = dimensions(value,'Dimensions du modèle',true);
    else if (key === 'machine' || key === 'assetId') out[key] = optionalId(value);
    else if (key === 'assetSha256') {
      if(value!==null && (typeof value!=='string'||!/^[a-f0-9]{64}$/.test(value))) error('Empreinte du fichier invalide.');
      out[key]=value;
    }
    else if (key === 'triangles') out[key] = integer(value,'Nombre de triangles',0);
    else if (key === 'revision') out[key] = integer(value,'Révision');
    else {
      if (!['mm','cm','m','in','inch','inches'].includes(value)) error('Unité d’import inconnue.');
      out[key] = value;
    }
  }
  return out;
}

/** Optional import guard; older UPDATE_PIECE operations retain their original semantics. */
function pieceImportGuard(raw) {
  const hasRevision=Object.prototype.hasOwnProperty.call(raw,'expectedPieceRevision');
  const hasAsset=Object.prototype.hasOwnProperty.call(raw,'expectedAssetId');
  if(hasRevision!==hasAsset) error('La révision attendue de la pièce et son fichier attendu doivent être fournis ensemble.');
  if(!hasRevision) return null;
  if(typeof raw.expectedPieceRevision!=='number'||!Number.isSafeInteger(raw.expectedPieceRevision)||raw.expectedPieceRevision<1) error('La révision attendue de la pièce doit être un entier positif.');
  const expectedAssetId=raw.expectedAssetId===null?null:text(raw.expectedAssetId,'Identifiant du fichier attendu');
  return {expectedPieceRevision:raw.expectedPieceRevision,expectedAssetId};
}

function editPlanPayload(raw) {
  patchKeys(raw,['projectId','planId','expectedRevision','expectedVersionId','plan']);
  const projectId=text(raw.projectId,'Identifiant du dossier',300);
  if(typeof raw.planId!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$/.test(raw.planId)) error('Identifiant de plan invalide.');
  if(typeof raw.expectedRevision!=='number'||!Number.isSafeInteger(raw.expectedRevision)||raw.expectedRevision<0||raw.expectedRevision>EDIT_LIMITS.versions) error('Révision attendue du plan invalide.');
  if(raw.expectedRevision===0) {
    if(raw.expectedVersionId!==null) error('Une création de plan doit attendre une identité de version nulle.');
  } else if(typeof raw.expectedVersionId!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/.test(raw.expectedVersionId)) error('Identité de la version attendue manquante ou invalide.');
  return {projectId,planId:raw.planId,expectedRevision:raw.expectedRevision,expectedVersionId:raw.expectedVersionId,plan:normalizeEditPlan(raw.plan)};
}

// Reducer: all time and identity comes from the operation, never from replay time.
function reduce(state, op) {
  const p = object(op.payload || {}), ctx = op.context;
  const entityKey = workshopEntityKey(op);
  const entityVersion = entityKey ? (state.entityVersions?.[entityKey] || 0) : 0;
  let result;
  try {
    if(entityKey && op.expected?.entityVersion!==undefined && op.expected.entityVersion!==entityVersion) error('Cette ressource a changé sur un autre écran. L’opération est conservée sans remplacer la version confirmée ; rechargez-la avant de réappliquer votre modification.');
    if (op.type === 'SELECT_PROJECT') {
      const project = getProject(state,p.id);
      state.projectId = project.id;
      state.selectedPieceId = project.pieces[0]?.id || null;
      result = { ok: true, message: 'Projet sélectionné : ' + project.name + '.', projectId: project.id };
    } else if (op.type === 'SELECT_PIECE') {
      const project = getProject(state,ctx.projectId);
      if (!project.pieces.some(item => item.id === p.id)) error('Pièce absente du projet ciblé.');
      state.projectId = project.id;
      state.selectedPieceId = p.id;
      result = { ok: true, message: 'Pièce sélectionnée.', pieceId: p.id };
    } else if (op.type === 'ADD_PROJECT') {
      const id = text(p.id,'Identifiant de projet');
      if (state.projects.some(project => project.id === id)) error('Ce projet existe déjà.');
      const inquiry=p.inquiry===undefined?null:validateInquiryProjectPayload(p).inquiry;
      const clean = projectPatch({ name:p.name, kind:p.kind ?? 'art', quantity:p.quantity ?? 1, height:p.height===undefined?350:p.height, notes:p.notes ?? '' });
      const project = { id, ...clean, subtitle: inquiry?'Demande importée · étude à qualifier':'Nouveau dossier · démonstration', status: p.status===undefined?'Brief · démonstration':projectPatch({status:p.status}).status, media: null, pieces: [], quote: null, story: '', revision: 1, ...(inquiry?{inquiry}: {}) };
      state.projects.push(project);
      state.projectId = id;
      state.selectedPieceId = null;
      result = { ok: true, message: inquiry?'Dossier technique créé depuis la demande '+inquiry.reference+'.':'Dossier créé dans la démonstration.', id, projectId: id };
    } else if (op.type === 'UPDATE_PROJECT') {
      const project = getProject(state,p.id), patch = projectPatch(p.patch);
      const stale = ['quantity','height','kind'].some(key => key in patch && !same(project[key],patch[key]));
      Object.assign(project,patch);
      if (stale) invalidate(project);
      result = { ok: true, message: 'Dossier mis à jour.' + (stale ? ' Devis à recalculer.' : '') };
    } else if (op.type === 'UPDATE_PIECE') {
      const project = getProject(state,p.projectId), id = text(p.id,'Identifiant de pièce'), patch = piecePatch(p.patch);
      const previous = project.pieces.find(item => item.id === id);
      const importGuard=pieceImportGuard(p);
      if(importGuard) {
        if(ctx.projectId!==p.projectId) error('Le dossier ciblé par l’import ne correspond pas au contexte de l’opération.');
        if(!previous || previous.revision!==importGuard.expectedPieceRevision || (previous.assetId||null)!==importGuard.expectedAssetId) error('La pièce ou son fichier a changé pendant la lecture du STL. Aucun fichier existant n’a été remplacé ; reprenez l’import depuis la pièce actuelle.');
      }
      if (!previous && !patch.dims) error('Les dimensions sont requises pour ajouter une pièce.');
      const candidate = { ...(previous || piece(id,'Pièce importée',project.kind === 'prototype' ? 'fdm' : 'resin',patch.dims)), ...patch, id };
      if('assetId' in patch && patch.assetId!==(previous?.assetId||null) && !('assetSha256' in patch)) candidate.assetSha256=null;
      const changed = !previous || ['tech','dims','assetId','assetSha256','unit','machine'].some(key => key in patch && !same(previous[key],patch[key]));
      if (previous) {
        if (patch.revision && patch.revision < previous.revision) error('Une révision ne peut pas reculer.');
        candidate.revision = changed ? Math.max(previous.revision + 1,patch.revision || 1) : Math.max(previous.revision,patch.revision || 1);
      }
      if (candidate.machine && !fits(candidate,getMachine(state,candidate.machine))) {
        if ('machine' in patch && patch.machine) error('Affectation incompatible avec le procédé ou les dimensions brutes.');
        candidate.machine = null;
      }
      if (previous) Object.assign(previous,candidate); else project.pieces.push(candidate);
      if (changed || (previous && candidate.revision !== (op.expected?.pieceRevision ?? candidate.revision))) invalidate(project);
      result = { ok: true, message: previous ? 'Pièce mise à jour ; géométrie non qualifiée pour fabrication.' : 'Pièce ajoutée ; géométrie non qualifiée pour fabrication.', pieceId: id, revision: candidate.revision };
    } else if (op.type === 'PLAN_PROJECT') {
      const project = getProject(state,p.projectId), added = [], unassigned = [], differentLots = [];
      for (const item of project.pieces) {
        const id = jobId(project,item);
        const existing = state.jobs.find(job => job.id === id);
        if (existing) {
          if (existing.quantity !== project.quantity) differentLots.push(item.id);
          continue;
        }
        const candidates = state.machines.filter(machine => fits(item,machine));
        const load = machine => state.jobs.filter(job => job.machine === machine.id && job.status !== 'done').reduce((total,job) => total + job.duration * (1 - jobProgress(job,op.at)/100),0);
        candidates.sort((a,b) => load(a)-load(b) || Number(b.id === item.machine)-Number(a.id === item.machine) || a.id.localeCompare(b.id));
        if (!candidates.length) { unassigned.push(item.id); continue; }
        const machine = candidates[0];
        const job = { id, projectId: project.id, pieceId: item.id, machine: machine.id, status: 'queued', duration: (item.tech === 'resin' ? 4 : 6)*HOUR*project.quantity, elapsed: 0, startedAt: null, revision: item.revision || 1, quantity: project.quantity, assetId: item.assetId, dims:[...item.dims], tech:item.tech, pieceName:item.name, simulated:true };
        state.jobs.push(job);
        item.machine = machine.id;
        added.push(job);
      }
      result = { ok: true, message: added.length + ' travail(s) ajouté(s) à la file simulée.' + (unassigned.length ? ' ' + unassigned.length + ' pièce(s) sans affectation compatible.' : ' Aucun lancement réel.') + (differentLots.length ? ' ' + differentLots.length + ' pièce(s) ont déjà un lot planifié de quantité différente ; préparer une nouvelle révision avant de les replanifier.' : ''), planned:added.length, added:added.map(job => job.id), unassigned, differentLots };
    } else if (op.type === 'TOGGLE_MACHINE') {
      const machine = getMachine(state,p.id);
      const job = state.jobs.find(item => item.id === op.expected?.jobId && item.machine === machine.id);
      if (!job) error('Aucun travail ciblé sur cette machine de démonstration.');
      const desired = op.expected.status;
      if (job.status === desired) result = { ok: true, message: 'La simulation est déjà ' + (desired === 'paused' ? 'en pause.' : 'en cours.'), jobId:job.id, unchanged:true };
      else if (desired === 'paused' && job.status === 'running') {
        job.elapsed = job.duration * jobProgress(job,op.at) / 100;
        job.startedAt = null;
        job.status = 'paused';
        result = { ok: true, message: 'Simulation mise en pause sur ' + machine.id + '.', jobId:job.id };
      } else if (desired === 'running' && (job.status === 'paused' || job.status === 'queued')) {
        if (state.jobs.some(other => other.id !== job.id && other.machine === machine.id && active(other))) error('Machine réservée par une autre simulation, même en pause.');
        const model = { tech:job.tech, dims:job.dims };
        if (!fits(model,machine)) error('Le profil de démonstration ne convient plus à ce travail. Replanification nécessaire.');
        job.startedAt = op.at;
        job.status = 'running';
        result = { ok: true, message: 'Simulation démarrée ou reprise sur ' + machine.id + '.', jobId:job.id };
      } else error('L’état du travail a changé ; commande non rejouée.');
    } else if (op.type === 'UPDATE_MACHINE') {
      const machine = getMachine(state,p.id);
      patchKeys(p.patch,['name','tech','volume','material','qualified','registry']);
      if ('registry' in p.patch && p.expectedRegistryRevision !== (machine.registry?.revision || 0)) error('Cette fiche a changé sur un autre écran. Votre saisie est conservée ; rechargez la fiche avant de l’enregistrer.');
      const patch = {};
      for (const [key,value] of Object.entries(p.patch)) {
        if (key === 'registry') patch[key] = normalizeFleetRecord(value,machine.registry || null,op.at);
        else if (key === 'tech') patch[key] = technology(value);
        else if (key === 'volume') patch[key] = dimensions(value,'Volume utile de démonstration');
        else if (key === 'qualified') { if (value !== false) error('Cette démonstration ne peut pas qualifier une machine réelle.'); patch[key] = false; }
        else patch[key] = text(value,key,300);
      }
      const candidate = { ...machine,...patch,qualified:false };
      if (state.jobs.some(job => job.machine === machine.id && active(job) && !fits({ tech:job.tech,dims:job.dims },candidate))) error('La modification rendrait incompatible un travail actif ou en pause.');
      Object.assign(machine,candidate);
      result = { ok: true, message: patch.registry ? 'Fiche du parc enregistrée. Connexion et qualification physique restent distinctes.' : 'Ressource de démonstration modifiée ; qualification réelle non établie.' };
    } else if (op.type === 'SAVE_QUOTE') {
      const project = getProject(state,p.projectId);
      if (project.revision !== op.expected?.projectRevision) error('Le projet a changé : recalculer le devis.');
      const inputs = object(p.inputs,'Paramètres du devis');
      if (integer(inputs.quantity ?? 1,'Quantité') !== project.quantity) error('La quantité du devis ne correspond plus au projet.');
      const calculation = calculateQuote(inputs);
      project.quote = { inputs:clone(inputs), result:calculation, ...calculation, quantity:project.quantity, at:op.at, revision:project.revision, status:'Brouillon · démonstration' };
      result = { ok: true, message: 'Brouillon de devis calculé et conservé.', quote:clone(project.quote) };
    } else if (op.type === 'SAVE_STORY') {
      const project = getProject(state,p.projectId);
      project.story = text(p.text,'Texte du contenu',20000,true);
      result = { ok: true, message: 'Brouillon de contenu conservé. Aucune publication.' };
    } else if (op.type === 'SAVE_EDIT_PLAN') {
      // Validate again for the browser's stored-operation path, which also replays
      // older operation types. Build the new record fully before changing state.
      const data=validateWorkshopOperation(op).payload;
      const project=getProject(state,data.projectId);
      const records=project.contentPlans===undefined?[]:project.contentPlans;
      if(!Array.isArray(records)||records.length>EDIT_LIMITS.plans) error('Historique des plans du dossier invalide.');
      const previous=records.find(record=>record.id===data.planId),last=latestEditVersion(previous);
      if(data.expectedRevision!==(last?.revision||0)||data.expectedVersionId!==(last?.operationId??null)) error('Ce plan a changé sur un autre écran. Votre saisie est conservée ; rechargez sa dernière version ou créez un autre plan.');
      if(!previous&&records.length>=EDIT_LIMITS.plans) error('Ce dossier atteint la limite de '+EDIT_LIMITS.plans+' plans. Les historiques existants sont conservés.');
      if(previous&&(last?.revision||0)>=EDIT_LIMITS.versions) error('Ce plan atteint la limite de '+EDIT_LIMITS.versions+' versions. Créez un autre plan pour poursuivre ; son historique est conservé.');
      const revision=(last?.revision||0)+1;
      const version={revision,operationId:op.id,at:op.at,projectRevision:project.revision,projectName:project.name,plan:data.plan};
      const record={id:data.planId,versions:[...(previous?.versions||[]),version]};
      project.contentPlans=previous?records.map(item=>item.id===data.planId?record:item):[...records,record];
      result={ok:true,message:'Plan d’édit « '+data.plan.title+' » enregistré · version '+revision+'. Le montage reste à réaliser.',projectId:project.id,planId:data.planId,revision};
    } else if (op.type === 'LOG') {
      result = { ok: true, message:text(p.message,'Message',2000) };
    } else error('Opération inconnue.');
  } catch (failure) { result = { ok:false, message:failure.message || 'Opération invalide.' }; }
  if(entityKey && result.ok) {
    state.entityVersions ||= {};
    state.entityVersions[entityKey] = entityVersion + 1;
  }
  state.journal.unshift({ id:op.id, at:op.at, type:op.type, message:result.message, ...ctx, context:clone(ctx), ok:result.ok });
  state.journal = state.journal.slice(0,300);
  return result;
}

/** Stable JSON used for duplicate detection and backup integrity, not authentication. */
export function canonicalWorkshopJSON(value) {
  function walk(item,depth=0) {
    if(depth>24) error('Données trop imbriquées.');
    if(item===null || typeof item==='string' || typeof item==='boolean') return item;
    if(typeof item==='number') { if(!Number.isFinite(item)) error('Nombre non fini dans le journal.'); return item; }
    if(Array.isArray(item)) return item.map(v=>walk(v,depth+1));
    if(typeof item!=='object') error('Type de données invalide dans le journal.');
    const result={};
    for(const key of Object.keys(item).sort()) {
      if(['__proto__','prototype','constructor'].includes(key)) error('Clé interdite dans le journal.');
      result[key]=walk(item[key],depth+1);
    }
    return result;
  }
  return JSON.stringify(walk(value));
}

export function validateWorkshopSeed(raw) {
  patchKeys(raw,['version','at']);
  if(raw.version!==1 || !Number.isSafeInteger(raw.at) || raw.at<0) error('Origine du journal invalide.');
  return {version:1,at:raw.at};
}

/** Validation is independent of the current business state: conflicts remain auditable. */
export function validateWorkshopOperation(raw) {
  object(raw,'Opération');
  const encoded=canonicalWorkshopJSON(raw);
  if(new TextEncoder().encode(encoded).byteLength>65536) error('Opération trop volumineuse.');
  const op=JSON.parse(encoded);
  patchKeys(op,['version','id','clock','at','type','payload','expected','context']);
  if(op.version!==1 || typeof op.id!=='string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/.test(op.id) || !Number.isSafeInteger(op.clock) || op.clock<1 || !Number.isSafeInteger(op.at) || op.at<0 || !TYPES.has(op.type)) error('Enveloppe d’opération invalide.');
  const ctx=object(op.context,'Contexte');
  patchKeys(ctx,['projectId','projectName','pieceId','machineId','originProjectId']);
  for(const [key,value] of Object.entries(ctx)) if(value!==null) text(value,'Contexte '+key,300,key==='projectName');
  if(typeof ctx.projectId!=='string' || !ctx.projectId) error('Projet explicite requis dans le journal.');
  const expected=op.expected===undefined?{}:object(op.expected,'État attendu');
  patchKeys(expected,['projectRevision','pieceRevision','jobId','status','entityVersion']);
  if('entityVersion' in expected) integer(expected.entityVersion,'Version de ressource attendue',0);
  for(const key of ['projectRevision','pieceRevision']) if(key in expected) integer(expected[key],'Révision attendue');
  if('jobId' in expected) text(expected.jobId,'Travail attendu',300);
  if('status' in expected && !['running','paused'].includes(expected.status)) error('État de travail attendu invalide.');
  const data=object(op.payload,'Contenu');
  const allowed={SELECT_PROJECT:['id'],SELECT_PIECE:['id'],ADD_PROJECT:['id','name','kind','quantity','height','notes','status','inquiry'],UPDATE_PROJECT:['id','patch'],UPDATE_PIECE:['projectId','id','patch','expectedPieceRevision','expectedAssetId'],PLAN_PROJECT:['projectId'],TOGGLE_MACHINE:['id'],UPDATE_MACHINE:['id','patch','expectedRegistryRevision'],SAVE_QUOTE:['projectId','inputs'],SAVE_STORY:['projectId','text'],SAVE_EDIT_PLAN:['projectId','planId','expectedRevision','expectedVersionId','plan'],LOG:['projectId','message']}[op.type];
  patchKeys(data,allowed);
  if('id' in data) text(data.id,'Identifiant',300);
  if('projectId' in data) text(data.projectId,'Identifiant de projet',300);
  if(['SELECT_PROJECT','SELECT_PIECE','UPDATE_PROJECT','UPDATE_PIECE','UPDATE_MACHINE','TOGGLE_MACHINE','ADD_PROJECT'].includes(op.type)&&!data.id) error('Cible d’opération manquante.');
  if(['UPDATE_PIECE','PLAN_PROJECT','SAVE_QUOTE','SAVE_STORY','SAVE_EDIT_PLAN'].includes(op.type)&&!data.projectId) error('Projet cible manquant.');
  if(op.type==='UPDATE_PROJECT') projectPatch(data.patch);
  if(op.type==='ADD_PROJECT') projectPatch({name:data.name,kind:data.kind??'art',quantity:data.quantity??1,height:data.height===undefined?350:data.height,notes:data.notes??''});
  if(op.type==='ADD_PROJECT'&&data.inquiry!==undefined) validateInquiryProjectPayload(data);
  if(op.type==='ADD_PROJECT'&&'status' in data) projectPatch({status:data.status});
  if(op.type==='UPDATE_PIECE') {
    piecePatch(data.patch);
    const importGuard=pieceImportGuard(data);
    if(importGuard && ctx.projectId!==data.projectId) error('Le dossier ciblé par l’import ne correspond pas au contexte de l’opération.');
  }
  if(op.type==='UPDATE_MACHINE') {
    patchKeys(data.patch,['name','tech','volume','material','qualified','registry']);
    for(const [key,value] of Object.entries(data.patch)) {
      if(key==='registry') { integer(data.expectedRegistryRevision,'Révision de fiche',0); normalizeFleetRecord(value,null,op.at); }
      else if(key==='tech') technology(value);
      else if(key==='volume') dimensions(value,'Volume');
      else if(key==='qualified') { if(value!==false) error('La qualification physique ne peut pas être déclarée par cette opération.'); }
      else text(value,key,300);
    }
  }
  if(op.type==='TOGGLE_MACHINE' && (!expected.jobId || !expected.status)) error('Travail et état explicites requis.');
  if(op.type==='SAVE_QUOTE') {
    patchKeys(data.inputs,['material','hours','rate','other','margin','fee','quantity']);
    calculateQuote(data.inputs); integer(expected.projectRevision,'Révision du devis');
  }
  if(op.type==='SAVE_STORY') text(data.text,'Contenu',20000,true);
  if(op.type==='SAVE_EDIT_PLAN') {
    op.payload=editPlanPayload(data);
    if(op.payload.projectId!==ctx.projectId) error('Le dossier ciblé par le plan ne correspond pas au contexte de l’opération.');
  }
  if(op.type==='LOG') text(data.message,'Message',2000);
  return op;
}

export function replayWorkshopOperations(rawSeed,rawOperations) {
  const meta=validateWorkshopSeed(rawSeed);
  if(!Array.isArray(rawOperations) || rawOperations.length>50000) error('Journal invalide ou trop volumineux.');
  const unique=new Map();
  for(const raw of rawOperations) {
    const op=validateWorkshopOperation(raw),old=unique.get(op.id);
    if(old && canonicalWorkshopJSON(old)!==canonicalWorkshopJSON(op)) error('Un identifiant d’opération contient deux versions différentes.');
    unique.set(op.id,op);
  }
  const ordered=[...unique.values()].sort((a,b)=>a.clock-b.clock||(a.id<b.id?-1:a.id>b.id?1:0));
  const state=seed(meta.at),results=new Map();
  for(const op of ordered) results.set(op.id,reduce(state,op));
  return {state,results};
}

/** Conflict versions are business aggregate versions, never geometry revisions. */
export function workshopEntityKey(op) {
  if(['SELECT_PROJECT','SELECT_PIECE','LOG'].includes(op.type)) return null;
  if(['UPDATE_MACHINE','TOGGLE_MACHINE'].includes(op.type)) return JSON.stringify(['machine',op.payload.id]);
  const id=['ADD_PROJECT','UPDATE_PROJECT'].includes(op.type)?op.payload.id:op.payload.projectId;
  return JSON.stringify(['project',id]);
}

/** Keep seed() as the immutable v1 fixture. New fixtures require a new format. */
export function createWorkshopGenesis(rawSeed) {
  const meta=validateWorkshopSeed(rawSeed);
  return {format:'bojart.workshop.genesis.v1',seed:meta,state:seed(meta.at)};
}
export function validateWorkshopGenesis(raw,rawSeed=raw?.seed) {
  patchKeys(raw,['format','seed','state']);
  const expected=createWorkshopGenesis(rawSeed);
  if(canonicalWorkshopJSON(raw)!==canonicalWorkshopJSON(expected)) error('La genèse conservée ne correspond pas au format pris en charge. Aucun état de remplacement n’est généré.');
  return clone(raw);
}

/** A rejected operation cannot leave half a business mutation in the state. */
export function applyWorkshopOperation(rawState,rawOperation) {
  const operation=validateWorkshopOperation(rawOperation),state=clone(rawState),entityKey=workshopEntityKey(operation);
  const entityVersionBefore=entityKey?(state.entityVersions?.[entityKey]||0):0;
  const outcome=reduce(state,operation);
  if(!outcome.ok) {
    const unchanged=clone(rawState);unchanged.journal=state.journal;
    return {state:unchanged,outcome,entityKey,entityVersionBefore,entityVersionAfter:entityVersionBefore};
  }
  return {state,outcome,entityKey,entityVersionBefore,entityVersionAfter:entityKey?(state.entityVersions?.[entityKey]||0):0};
}

export function validateWorkshopReceipt(raw) {
  patchKeys(raw,['version','seq','operationId','receivedAt','entityKey','entityVersionBefore','entityVersionAfter','outcome']);
  if(raw.version!==1||!Number.isSafeInteger(raw.seq)||raw.seq<1||typeof raw.operationId!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/.test(raw.operationId)||!Number.isSafeInteger(raw.receivedAt)||raw.receivedAt<0) error('Reçu du journal invalide.');
  if(raw.entityKey!==null&&(typeof raw.entityKey!=='string'||raw.entityKey.length>660)) error('Ressource du reçu invalide.');
  for(const key of ['entityVersionBefore','entityVersionAfter']) if(!Number.isSafeInteger(raw[key])||raw[key]<0) error('Version du reçu invalide.');
  object(raw.outcome,'Résultat du reçu');
  if(typeof raw.outcome.ok!=='boolean'||typeof raw.outcome.message!=='string'||raw.outcome.message.length>22000) error('Résultat métier du reçu invalide.');
  canonicalWorkshopJSON(raw);
  return clone(raw);
}

/** Confirmed receipts are replayed in server order; local pending work follows. */
export function replayWorkshopAuthority(rawSeed,rawOperations,rawAuthority) {
  const meta=validateWorkshopSeed(rawSeed),authority=object(rawAuthority,'Autorité');
  patchKeys(authority,['workspaceId','reducerVersion','genesis','receipts']);
  if(typeof authority.workspaceId!=='string'||!/^workspace-[0-9a-f-]{36}$/.test(authority.workspaceId)||authority.reducerVersion!==WORKSHOP_REDUCER_VERSION) error('Identité ou version de l’autorité non prise en charge.');
  const genesis=validateWorkshopGenesis(authority.genesis,meta);
  if(!Array.isArray(rawOperations)||rawOperations.length>50000||!Array.isArray(authority.receipts)||authority.receipts.length>50000) error('Journal trop volumineux.');
  const operations=new Map();
  for(const raw of rawOperations) {
    const operation=validateWorkshopOperation(raw),previous=operations.get(operation.id);
    if(previous&&canonicalWorkshopJSON(previous)!==canonicalWorkshopJSON(operation)) error('Conflit d’identifiant dans le journal.');
    operations.set(operation.id,operation);
  }
  let state=clone(genesis.state);const results=new Map(),confirmed=new Set();
  for(let i=0;i<authority.receipts.length;i++) {
    const receipt=validateWorkshopReceipt(authority.receipts[i]),operation=operations.get(receipt.operationId);
    if(receipt.seq!==i+1||confirmed.has(receipt.operationId)||!operation) error('La séquence confirmée est incomplète ou contradictoire.');
    const decision=applyWorkshopOperation(state,operation);
    if(receipt.entityKey!==decision.entityKey||receipt.entityVersionBefore!==decision.entityVersionBefore||receipt.entityVersionAfter!==decision.entityVersionAfter||canonicalWorkshopJSON(receipt.outcome)!==canonicalWorkshopJSON(decision.outcome)) error('Un reçu métier ne correspond plus au moteur versionné. Le journal confirmé ne sera pas réinterprété.');
    state=decision.state;confirmed.add(operation.id);
    results.set(operation.id,{...receipt.outcome,confirmed:true,serverSeq:receipt.seq,entityVersion:receipt.entityVersionAfter});
  }
  const authoritativeState=clone(state);
  const pending=[...operations.values()].filter(op=>!confirmed.has(op.id)).sort((a,b)=>a.clock-b.clock||(a.id<b.id?-1:a.id>b.id?1:0));
  for(const op of pending) {const decision=applyWorkshopOperation(state,op);state=decision.state;results.set(op.id,{...decision.outcome,confirmed:false});}
  return {state,authoritativeState,results,confirmed};
}

export class WorkshopStore extends EventTarget {
  constructor() {
    super();
    this.clientId = uid('window');
    this.persistent = true;
    this._volatile = new Map();
    this._clock = 0;
    this._signature = '';
    this.integrityError = null;
    this._persistedOperationIds = new Set();
    this._seedPersisted = false;
    this._authorityPersisted = false;
    this._persistedAuthorityCursor = 0;
    try {
      this._storage = globalThis.localStorage || globalThis.window?.localStorage;
      if (!this._storage) throw new Error('Storage unavailable');
      this._storage.getItem(SEED_KEY);
    } catch { this._storage = memoryStorage; this.persistent = false; }
    this._sync(false);
    this._onStorage = event => { if (event.key === null || event.key?.startsWith(PREFIX)) this._sync(true); };
    globalThis.window?.addEventListener?.('storage',this._onStorage);
    if (typeof globalThis.window !== 'undefined' && typeof globalThis.BroadcastChannel === 'function') {
      try {
        this._channel = new BroadcastChannel(PREFIX + 'changes');
        this._channel.onmessage = () => this._sync(true);
      } catch { /* storage events remain the cross-window fallback */ }
    }
  }

  getProject() { return this.state.projects.find(project => project.id === this.state.projectId) || null; }
  getMachine(id) { return this.state.machines.find(machine => machine.id === id) || null; }

  _seedTime() {
    const raw=this._storage.getItem(SEED_KEY);
    if(raw!==null) {
      let meta;
      try {meta=validateWorkshopSeed(JSON.parse(raw));}
      catch {error('L’origine du journal est illisible. Elle est conservée sans remplacement ; exportez la copie de récupération avant toute réparation.');}
      if(this._baseAt!==undefined && meta.at!==this._baseAt && (this._operations?.length||this._authority)) error('L’origine du journal a changé alors que des dossiers existent. Aucun historique n’a été réinterprété.');
      this._baseAt=meta.at;this._seedPersisted=true;return meta.at;
    }
    if(this._seedPersisted || this._storage.getItem(AUTHORITY_KEY)!==null) error('L’origine du journal a disparu. Les données restantes sont conservées ; aucune nouvelle origine n’est créée.');
    for(let i=0;i<this._storage.length;i++) if(this._storage.key(i)?.startsWith(OP_PREFIX)) error('Des opérations sont présentes sans leur origine. Aucun nouveau journal n’est créé.');
    const at=this._baseAt??Date.now();this._baseAt=at;
    // A genuinely empty, writable store may create its first origin. An
    // unreadable or missing origin with existing history never takes this path.
    if(!this.persistent && this._volatile.size)return at;
    try {this._storage.setItem(SEED_KEY,JSON.stringify({version:1,at}));}
    catch {this.persistent=false;return at;}
    let winner;
    try {winner=validateWorkshopSeed(JSON.parse(this._storage.getItem(SEED_KEY)));}
    catch {error('L’origine initiale du journal n’a pas pu être relue. Aucune opération n’est ajoutée.');}
    this._baseAt=winner.at;this._seedPersisted=true;return winner.at;
  }

  _sync(emit = true) {
    const hadError=!!this.integrityError;
    try {
      const baseAt=this._seedTime(),operations=new Map(),persistedIds=new Set();
      for(const raw of this._volatile.values()) {
        const op=validateWorkshopOperation(raw);operations.set(op.id,op);
      }
      for (let i=0;i<this._storage.length;i++) {
        const key = this._storage.key(i);
        if (!key?.startsWith(OP_PREFIX)) continue;
        let op;
        try {op=validateWorkshopOperation(JSON.parse(this._storage.getItem(key)));if(key!==OP_PREFIX+op.id)throw new Error();}
        catch {error('Une opération conservée est illisible ou ne correspond pas à son identifiant. Le journal reste inchangé ; exportez la copie de récupération.');}
        const previous=operations.get(op.id);
        if(previous&&canonicalWorkshopJSON(previous)!==canonicalWorkshopJSON(op)) error('Deux contenus occupent le même identifiant d’opération. Les données sont conservées sans choisir un remplacement.');
        operations.set(op.id,op);persistedIds.add(op.id);
      }
      for(const id of this._persistedOperationIds)if(!persistedIds.has(id)) error('Une opération précédemment conservée a disparu du navigateur. Le dernier état lisible reste affiché ; aucune réécriture automatique.');
      for(const previous of this._operations||[]) {
        const current=operations.get(previous.id);
        if(current&&canonicalWorkshopJSON(previous)!==canonicalWorkshopJSON(current))error('Le contenu d’une opération déjà lue a changé sous le même identifiant. Le dernier état lisible est conservé ; aucun remplacement automatique.');
      }
      if(operations.size>50000)error('Le journal dépasse la capacité de cette version. Les données existantes sont conservées.');
      let authority=this._authority||null;
      const rawAuthority=this._storage.getItem(AUTHORITY_KEY);
      let savedAuthorityCursor=null;
      if(rawAuthority!==null) {
        let saved;
        try {saved=JSON.parse(rawAuthority);object(saved,'Autorité');if(!Array.isArray(saved.receipts))throw new Error();}
        catch {error('Les reçus de l’autorité sont illisibles. Aucun journal de remplacement n’est créé.');}
        if(authority && authority.workspaceId!==saved.workspaceId) error('L’identité de l’autorité locale a changé. Les historiques restent séparés.');
        if(authority)for(let i=0;i<Math.min(authority.receipts.length,saved.receipts.length);i++)if(canonicalWorkshopJSON(authority.receipts[i])!==canonicalWorkshopJSON(saved.receipts[i]))error('Deux reçus incompatibles occupent la même séquence.');
        if(this._authorityPersisted&&saved.receipts.length<this._persistedAuthorityCursor)error('Des reçus précédemment conservés ont disparu. Aucun retour en arrière automatique.');
        if(!authority || saved.receipts.length>=authority.receipts.length)authority=saved;
        savedAuthorityCursor=saved.receipts.length;
      } else if(this._authorityPersisted)error('Les reçus confirmés ont disparu du navigateur. Le dernier état lisible est conservé.');
      const ordered=[...operations.values()].sort((a,b)=>a.clock-b.clock||(a.id<b.id?-1:a.id>b.id?1:0));
      const signature=String(baseAt)+'|'+ordered.map(op=>canonicalWorkshopJSON(op)).join('|')+'|'+(authority?canonicalWorkshopJSON(authority):'');
      if(this.state&&signature===this._signature){this.integrityError=null;this.authorityError=null;if(emit&&hadError)this._emit();return;}
      let replay;
      if(authority)replay=replayWorkshopAuthority({version:1,at:baseAt},ordered,authority);
      else {
        const local=replayWorkshopOperations({version:1,at:baseAt},ordered);
        replay={state:local.state,results:new Map([...local.results].map(([id,result])=>[id,{...result,confirmed:false}]))};
      }
      this._operations=ordered;this._persistedOperationIds=persistedIds;this._clock=ordered.reduce((max,op)=>Math.max(max,op.clock),0);
      this.state=replay.state;this._results=replay.results;if(authority)this._authority=clone(authority);
      if(savedAuthorityCursor!==null){this._authorityPersisted=true;this._persistedAuthorityCursor=savedAuthorityCursor;}
      this._signature=signature;this.integrityError=null;this.authorityError=null;
    } catch(failure) {
      this.integrityError=String(failure?.message||'Le journal du navigateur ne peut pas être relu. Aucune modification effectuée.');
      this.authorityError=this.integrityError;
      if(!this.state) {
        this.state={projectId:null,selectedPieceId:null,projects:[],machines:[],jobs:[],journal:[]};
        this._results=new Map();this._operations=[];
      }
    }
    if(emit)this._emit();
  }

  _emit(result = null) {
    const event = new Event('change');
    Object.defineProperty(event,'detail',{ value:{ state:this.state,result,persistent:this.persistent } });
    this.dispatchEvent(event);
  }

  dispatch(type, payload = {}) {
    this._sync(false);
    if(this.authorityError) return {ok:false,message:this.authorityError,persisted:false};
    let op;
    try {
      if (!TYPES.has(type)) error('Opération inconnue : ' + type + '.');
      // A new edit plan is validated before JSON cloning can turn NaN into null
      // or discard unknown fields. The form owns only its explicit target ID.
      const importGuard=type==='UPDATE_PIECE'?pieceImportGuard(object(payload)):null;
      const data = type==='SAVE_EDIT_PLAN'?editPlanPayload(payload):clone(object(payload));
      if(importGuard) Object.assign(data,importGuard);
      let projectId = data.projectId || (['UPDATE_PROJECT','SELECT_PROJECT'].includes(type) ? data.id : this.state.projectId);
      let pieceId = type === 'UPDATE_PIECE' || type === 'SELECT_PIECE' ? data.id : type === 'LOG' && projectId === this.state.projectId ? this.state.selectedPieceId : null;
      let machineId = ['UPDATE_MACHINE','TOGGLE_MACHINE'].includes(type) ? data.id : null;
      const expected = {};
      if (type === 'ADD_PROJECT') { data.id = data.inquiry?inquiryProjectId(normalizeInquiryLink(data.inquiry)):uid('project'); projectId = data.id; pieceId = null; }
      if (type === 'SELECT_PIECE') projectId = this.state.projectId;
      if (type === 'TOGGLE_MACHINE') {
        getMachine(this.state,data.id);
        const list = this.state.jobs.filter(job => job.machine === data.id);
        const job = list.find(item => item.status === 'running') || list.find(item => item.status === 'paused') || list.find(item => item.status === 'queued');
        if (!job) error('Aucun travail simulé à démarrer ou reprendre sur ' + data.id + '.');
        expected.jobId = job.id;
        expected.status = job.status === 'running' ? 'paused' : 'running';
        projectId = job.projectId;
        pieceId = job.pieceId;
      }
      const project = this.state.projects.find(item => item.id === projectId);
      if (type === 'SELECT_PROJECT') pieceId = project?.pieces[0]?.id || null;
      if (type === 'SAVE_QUOTE') {
        if (!project) error('Projet introuvable.');
        data.inputs = { ...object(data.inputs,'Paramètres du devis'), quantity:data.inputs.quantity ?? project.quantity, fee:data.inputs.fee ?? 0 };
        // Caller-supplied result is deliberately recomputed from the inputs.
        delete data.result;
        expected.projectRevision = project.revision;
      }
      if (type === 'UPDATE_PIECE') expected.pieceRevision = project?.pieces.find(item => item.id === data.id)?.revision;
      op = { version:1,id:uid(this.clientId),clock:this._clock+1,at:Date.now(),type,payload:data,expected,context:{ projectId,projectName:project?.name || data.name || '',pieceId:pieceId || null,machineId:machineId || null,originProjectId:this.state.projectId } };
      const entityKey=workshopEntityKey(op);
      if(entityKey) op.expected.entityVersion=this.state.entityVersions?.[entityKey]||0;
      op = validateWorkshopOperation(JSON.parse(JSON.stringify(op)));
      // Validate the complete operation before committing a durable record.
      const trial = reduce(clone(this.state),op);
      if (!trial.ok) return { ...trial,persisted:false };
    } catch (failure) { return { ok:false,message:failure.message || 'Données invalides.',persisted:false }; }
    let persisted = this.persistent;
    try { this._storage.setItem(OP_PREFIX + op.id,JSON.stringify(op)); }
    catch { this._volatile.set(op.id,op); this.persistent = false; persisted = false; }
    this._sync(false);
    const result = { ...(this._results.get(op.id) || { ok:false,message:'Opération non retrouvée.' }),operationId:op.id,persisted };
    if (!persisted && result.ok) result.message += ' Conservation limitée à cette fenêtre.';
    this._emit(result);
    if (persisted) { try { this._channel?.postMessage({ id:op.id }); } catch { /* persisted storage event is sufficient */ } }
    return result;
  }

  refresh() { this._sync(true); return this.state; }

  recheckIntegrity() {
    this._sync(true);
    return {ok:!this.integrityError,message:this.integrityError||'Le journal a été relu ; sa structure et ses reçus sont cohérents.',retainedState:!!this.state.projects.length};
  }

  /** A forensic copy only: raw text is not interpreted, repaired, or merged. */
  recoverRawStorage() {
    const entries=[];
    for(let i=0;i<this._storage.length;i++) {
      const key=this._storage.key(i);
      if(key===SEED_KEY||key===AUTHORITY_KEY||key?.startsWith(OP_PREFIX))entries.push({key,value:this._storage.getItem(key)});
    }
    entries.sort((a,b)=>a.key.localeCompare(b.key));
    const lastValidatedJournal=this._signature?{version:this._authority?2:1,seed:{version:1,at:this._baseAt},operations:clone(this._operations),...(this._authority?{authority:clone(this._authority)}:{})}:null;
    const recovery={format:'bojart.workshop.recovery.v1',exportedAt:new Date().toISOString(),reason:this.integrityError||null,entries,volatileOperations:clone([...this._volatile.values()]),lastValidatedJournal};
    if(new TextEncoder().encode(JSON.stringify(recovery)).byteLength>16777216)error('La copie dépasse 16 Mio. Conservez les données du navigateur avec les outils du poste ; aucun contenu n’a été effacé.');
    return recovery;
  }

  exportJournal() {
    this._sync(false);
    if(this.authorityError) error(this.authorityError);
    return {version:this._authority?2:1,seed:{version:1,at:this._baseAt},operations:clone(this._operations),...(this._authority?{authority:clone(this._authority)}:{})};
  }

  /** Additive import: validate all identities before the first storage write. */
  mergeJournal(journal,{allowEmptyAdoption=false}={}) {
    patchKeys(journal,['version','seed','operations','authority']);
    if(![1,2].includes(journal.version) || !Array.isArray(journal.operations) || (journal.version===2)!==!!journal.authority) error('Format de journal inconnu.');
    const meta=validateWorkshopSeed(journal.seed);
    this._sync(false);
    if(this.integrityError)error(this.integrityError);
    const adopted=meta.at!==this._baseAt;
    const local=new Map(this._operations.map(op=>[op.id,op])),incoming=new Map(),added=[],duplicates=[];
    if(meta.at!==this._baseAt && !(allowEmptyAdoption && local.size===0)) error('Ce fichier appartient à un autre atelier. Aucun dossier n’a été remplacé.');
    for(const raw of journal.operations) {
      const op=validateWorkshopOperation(raw),old=local.get(op.id)||incoming.get(op.id);
      if(old && canonicalWorkshopJSON(old)!==canonicalWorkshopJSON(op)) error('Conflit d’identifiant : une opération possède un contenu différent. Aucun ajout effectué.');
      if(old) duplicates.push(op.id); else {incoming.set(op.id,op);added.push(op.id);}
    }
    if(local.size+incoming.size>50000) error('Le journal dépasse la capacité de cette version.');
    let authority=this._authority||null;
    if(journal.version===2) {
      if(authority && (authority.workspaceId!==journal.authority.workspaceId||canonicalWorkshopJSON(authority.genesis)!==canonicalWorkshopJSON(journal.authority.genesis))) error('Ce journal confirmé appartient à une autre autorité. Les données ne sont pas fusionnées.');
      if(authority) for(let i=0;i<Math.min(authority.receipts.length,journal.authority.receipts.length);i++) if(canonicalWorkshopJSON(authority.receipts[i])!==canonicalWorkshopJSON(journal.authority.receipts[i])) error('Conflit de séquence : un reçu confirmé possède un autre contenu.');
      if(!authority||journal.authority.receipts.length>=authority.receipts.length) authority=clone(journal.authority);
    }
    // Validate the complete immutable prefix before any storage write.
    if(authority) replayWorkshopAuthority(meta,[...local.values(),...incoming.values()],authority);
    else replayWorkshopOperations(meta,[...local.values(),...incoming.values()]);
    if(meta.at!==this._baseAt) {
      try {
        this._storage.setItem(SEED_KEY,JSON.stringify(meta));
        if(this._storage.getItem(SEED_KEY)!==JSON.stringify(meta)) throw new Error('Origine non conservée.');
      } catch { error('L’origine du journal ne peut pas être enregistrée. Aucun ajout effectué.'); }
      this._baseAt=meta.at;
    }
    for(const op of incoming.values()) {
      try { this._storage.setItem(OP_PREFIX+op.id,JSON.stringify(op)); }
      catch { this._volatile.set(op.id,op);this.persistent=false; }
    }
    const previousCursor=this._authority?.receipts.length||0;
    if(authority) {
      this._authority=authority;
      // Raw operations precede the single authority snapshot. Quota failure is
      // explicit memory mode; the server copy and receipt stay authoritative.
      try {if(this._volatile.size)throw new Error('Volatile operations');this._storage.setItem(AUTHORITY_KEY,JSON.stringify(authority));this._authorityPersisted=true;this._persistedAuthorityCursor=authority.receipts.length;}
      catch {this.persistent=false;}
    }
    this._sync(false);
    const rejected=[...this._results].filter(([,result])=>!result.ok).map(([id,result])=>({id,message:result.message}));
    const result={ok:true,added:added.length,duplicates:duplicates.length,rejected,persisted:this.persistent};
    if(added.length || adopted || (authority?.receipts.length||0)!==previousCursor) {
      this._emit();
      try {this._channel?.postMessage({imported:true});}catch{}
    }
    return result;
  }
  dispose() {
    globalThis.window?.removeEventListener?.('storage',this._onStorage);
    this._channel?.close();
  }
}
