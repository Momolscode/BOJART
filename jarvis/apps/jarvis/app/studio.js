'use strict';
const $ = id => document.getElementById(id);
let catalogue, selected, filter = 'all', plan = null, preparedRequest = null;
let draftGeneration = 0, preparing = false, verifying = false;
const offline = Boolean(window.DEMO_STUDIO);
const kindLabels = {authentic_capture:'FIGURINE RÉELLE', ai_generation:'GÉNÉRATION IA', concept:'CONCEPT / ESSAI', mixed:'CONTENU MÉLANGÉ', unknown:'NON CLASSÉ'};
const demoIds = ['profil', 'troisquarts', 'visage'];
const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const tm = n => Number(n).toFixed(1).replace('.', ',') + ' s';
const usable = s => s && s.availability === 'verified' && s.review !== 'rejected' && ['authentic_capture','ai_generation'].includes(s.kind);
const anchorEligible = s => usable(s) && s.identity_anchor && s.kind === 'authentic_capture' && s.review === 'approved_internal';
async function api(route, body) {
  const r = await fetch(route, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const d = await r.json();
  if (!r.ok) throw Error(d.error || 'Erreur de lecture.');
  return d;
}
function feedback(message, ok = false) {
  $('feedback').textContent = message;
  $('feedback').className = 'feedback ' + (ok ? 'ok' : 'error');
}
function thumb(s) {
  // Static demo thumbnails are not bound to the live asset's hash.
  return offline ? window.DEMO_STUDIO.thumbs[s.id] : null;
}
function addThumbnail(parent, s, alt = '') {
  const url = thumb(s);
  if (!url) return;
  const im = document.createElement('img'); im.src = url; im.alt = alt;
  parent.append(im);
}
function renderList() {
  const q = norm($('search').value).trim().split(/\s+/).filter(Boolean);
  const rows = catalogue.segments.filter(s => (filter === 'all' || s.kind === 'authentic_capture') && q.every(w => norm(s.label + ' ' + s.tags.join(' ')).includes(w)));
  $('segments').replaceChildren(); $('empty').hidden = rows.length > 0;
  for (const s of rows) {
    const b = document.createElement('button'); b.type = 'button';
    b.className = 'segment' + (selected?.id === s.id ? ' selected' : ''); b.dataset.segment = s.id;
    addThumbnail(b, s);
    const words = document.createElement('span'), title = document.createElement('strong'), time = document.createElement('small'), kind = document.createElement('span');
    title.textContent = s.label; time.textContent = tm(s.start) + ' → ' + tm(s.end);
    kind.className = 'kind'; kind.textContent = kindLabels[s.kind];
    if (s.review === 'rejected') kind.textContent = 'PASSAGE REFUSÉ';
    if (s.availability !== 'verified') kind.textContent += ' · SOURCE INDISPONIBLE';
    words.append(title, time, kind); b.append(words); b.onclick = () => select(s); $('segments').append(b);
  }
}
function select(s) {
  if (!s) return;
  selected = s;
  $('selectedTitle').textContent = s.label; $('sourceKind').textContent = kindLabels[s.kind];
  $('times').textContent = tm(s.start) + ' → ' + tm(s.end); $('assetLabel').textContent = s.asset_label;
  $('mediaSpec').textContent = s.metadata.width + ' × ' + s.metadata.height + ' · ' + tm(s.metadata.duration) + ' · audio ' + (s.metadata.audio ? 'présent, non validé' : 'absent');
  $('integrity').textContent = s.availability === 'verified' ? 'Empreinte vérifiée · passage R' + s.revision : 'Source absente ou modifiée';
  $('evidence').textContent = s.evidence; $('provenance').textContent = s.provenance; $('hash').textContent = 'SHA-256 · ' + s.asset_id;
  const v = $('video'); v.pause();
  $('play').disabled = s.availability !== 'verified';
  $('posterFallback').style.display = 'block';
  $('posterFallback').textContent = s.availability === 'verified' ? 'Chargement du passage…' : 'Source absente ou modifiée : lecture désactivée.';
  const poster = thumb(s);
  if (poster) v.poster = poster; else v.removeAttribute('poster');
  if (s.availability !== 'verified') { v.removeAttribute('src'); v.load(); renderList(); return; }
  const url = offline ? window.DEMO_STUDIO.proxies[s.asset_id] : '/api/studio/media/' + s.asset_id;
  v.onloadedmetadata = () => { if (selected !== s) return; v.currentTime = Math.min(s.start, v.duration || s.start); $('posterFallback').style.display = 'none'; };
  v.oncanplay = () => { if (selected === s) $('posterFallback').style.display = 'none'; };
  v.onerror = () => { if (selected === s) $('posterFallback').textContent = 'Lecture indisponible : vérifier la source et son format.'; };
  if (v.getAttribute('src') !== url) v.src = url; else { v.currentTime = s.start; $('posterFallback').style.display = 'none'; }
  $('proxyNote').textContent = offline ? 'Aperçu autonome : copie allégée. Les empreintes concernent les originaux.' : 'Lecture du fichier original vérifié avant transmission au lecteur.';
  renderList();
}
function selectedIds() {
  return Array.from(document.querySelectorAll('input[name="studio-segment"]:checked')).map(x => x.value);
}
function refreshDraftControls() {
  const ids = selectedIds(), anchor = catalogue?.segments.find(s => s.id === $('anchor').value);
  const eligible = anchorEligible(anchor) && ids.length > 0 && ids.length <= 12 && ids.every(id => usable(catalogue.segments.find(s => s.id === id)));
  $('prepare').disabled = preparing || !eligible;
  $('verify').disabled = !plan || verifying; $('export').disabled = !plan;
  $('selectionSummary').textContent = ids.length ? ids.length + ' passage(s) choisi(s), dans l’ordre affiché.' : 'Choisis de 1 à 12 passages pour le montage.';
  $('anchorEvidence').textContent = anchorEligible(anchor) ? anchor.label + ' — ' + anchor.evidence : 'Choisis une captation authentique relue. La prévisualisation seule ne sélectionne aucune référence.';
}
function invalidateDraft() {
  draftGeneration++; plan = null; preparedRequest = null;
  refreshDraftControls();
  feedback('Sélection modifiée. Prépare un nouveau brief pour ces sources.', true);
}
function setupSelection() {
  $('anchor').replaceChildren(); $('briefSources').replaceChildren();
  const placeholder = document.createElement('option');
  placeholder.value = ''; placeholder.textContent = 'Choisir la référence authentique'; $('anchor').append(placeholder);
  for (const s of catalogue.segments.filter(anchorEligible)) {
    const o = document.createElement('option'); o.value = s.id; o.textContent = s.label + ' · R' + s.revision; $('anchor').append(o);
  }
  const legacy = demoIds.map(id => catalogue.segments.find(s => s.id === id));
  const knownDemo = legacy.every(s => usable(s) && s.kind === 'authentic_capture') && anchorEligible(legacy[2]) && legacy.every(s => s.asset_id === legacy[2].asset_id);
  $('anchor').value = knownDemo ? 'visage' : '';
  for (const s of catalogue.segments) {
    const row = document.createElement('label'), checkbox = document.createElement('input'), caption = document.createElement('span');
    checkbox.type = 'checkbox'; checkbox.name = 'studio-segment'; checkbox.value = s.id;
    checkbox.disabled = !usable(s); checkbox.checked = knownDemo && demoIds.includes(s.id);
    checkbox.onchange = invalidateDraft; row.className = 'source-choice';
    caption.textContent = s.label + ' · R' + s.revision + (checkbox.disabled ? ' · indisponible pour ce brief' : '');
    row.append(checkbox, caption); $('briefSources').append(row);
  }
  $('anchor').onchange = invalidateDraft;
  refreshDraftControls();
}
function selectionRequest() {
  const ids = selectedIds(), anchor = catalogue.segments.find(s => s.id === $('anchor').value);
  if (!anchorEligible(anchor)) throw Error('Choisis une référence authentique, relue et disponible.');
  if (!ids.length || ids.length > 12) throw Error('Choisis de 1 à 12 passages.');
  const revisions = {};
  for (const id of new Set([anchor.id, ...ids])) {
    const s = catalogue.segments.find(row => row.id === id);
    if (!usable(s)) throw Error('Un passage choisi est absent, modifié ou refusé.');
    revisions[id] = s.revision;
  }
  return {request_id:'brief-' + (crypto.randomUUID ? crypto.randomUUID() : Date.now()), anchor_id:anchor.id, segment_ids:ids, expected_revisions:revisions};
}
$('search').oninput = () => { if (catalogue) renderList(); };
$('all').onclick = () => { filter = 'all'; $('all').classList.add('active'); $('authentic').classList.remove('active'); if (catalogue) renderList(); };
$('authentic').onclick = () => { filter = 'authentic'; $('authentic').classList.add('active'); $('all').classList.remove('active'); if (catalogue) renderList(); };
$('play').onclick = async () => { try { if (!selected || $('play').disabled) return; $('video').currentTime = selected.start; await $('video').play(); } catch { feedback('Lecture à relancer depuis les commandes du lecteur.'); } };
$('video').ontimeupdate = () => { if (selected && $('video').currentTime >= selected.end && !$('video').paused) $('video').pause(); };
$('prepare').onclick = async () => {
  if (preparing || !catalogue) return;
  const generation = draftGeneration;
  preparing = true; refreshDraftControls();
  try {
    preparedRequest = preparedRequest || selectionRequest();
    const request = preparedRequest;
    let result;
    if (offline) {
      const example = window.DEMO_STUDIO.plan;
      if (request.anchor_id !== example.anchor_id || JSON.stringify(request.segment_ids) !== JSON.stringify(example.segment_order)) throw Error('Cet aperçu contient un seul brief précalculé. Le service local prépare les autres sélections.');
      result = structuredClone(example);
    } else result = await api('/api/studio/prepare', request);
    if (generation !== draftGeneration) return;
    plan = result;
    feedback((offline ? 'Exemple précalculé : ' : 'Brief conservé : ') + plan.segment_order.length + ' passages liés à leurs révisions. Aucune vidéo rendue ni publiée.', true);
  } catch (e) { if (generation === draftGeneration) feedback(e.message); }
  finally { preparing = false; refreshDraftControls(); }
};
$('verify').onclick = async () => {
  if (!plan || verifying) return;
  const generation = draftGeneration, checkedPlan = plan;
  verifying = true; refreshDraftControls();
  try {
    const r = offline ? window.DEMO_STUDIO.verification : await api('/api/studio/verify', {plan_id:checkedPlan.id});
    if (generation !== draftGeneration || plan !== checkedPlan) return;
    feedback(r.valid ? 'Références cohérentes' + (offline ? ' lors de la création de cet aperçu.' : ' à cette vérification.') + ' Publication toujours désactivée.' : 'Contrôle à reprendre.', r.valid);
  } catch (e) { if (generation === draftGeneration && plan === checkedPlan) feedback(e.message); }
  finally { verifying = false; refreshDraftControls(); }
};
$('export').onclick = () => {
  if (!plan) return;
  const b = new Blob([JSON.stringify(plan, null, 2)], {type:'application/json'}), a = document.createElement('a');
  a.href = URL.createObjectURL(b); a.download = 'BOJART_BRIEF_STUDIO.json'; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
};
(async () => {
  try {
    catalogue = offline ? window.DEMO_STUDIO.catalogue : await api('/api/studio/catalogue');
    if (offline) {
      $('mode').textContent = 'APERÇU HORS LIGNE · CONTRÔLES PRÉCALCULÉS';
      document.querySelectorAll('a[href="/"]').forEach(a => { a.href = '#'; a.onclick = e => { e.preventDefault(); feedback('Dans le pack complet, le dialogue et le Studio partagent le même serveur local.', true); }; });
    }
    $('assetCount').textContent = catalogue.asset_count; $('segmentCount').textContent = catalogue.segments.length;
    $('anchorCount').textContent = catalogue.segments.filter(anchorEligible).length;
    setupSelection(); renderList();
    for (const s of catalogue.segments.filter(s => s.kind === 'authentic_capture')) {
      const b = document.createElement('button'); b.type = 'button'; b.title = s.label;
      addThumbnail(b, s, s.label);
      const cap = document.createElement('span'); cap.textContent = tm(s.start); b.append(cap); b.onclick = () => select(s); $('filmstrip').append(b);
    }
    if (!catalogue.segments.length) {
      $('selectedTitle').textContent = 'Aucun passage disponible';
      $('posterFallback').textContent = 'La bibliothèque est vide.';
      feedback('Bibliothèque vide : aucun passage importé et annoté. Ajoute des sources au catalogue avant de préparer un brief.', true);
    } else {
      select(catalogue.segments.find(s => s.id === 'visage') || catalogue.segments[0]);
      if (!catalogue.segments.some(anchorEligible)) feedback('Aucune référence authentique relue et disponible. Les sources restent consultables.');
    }
  } catch (e) { feedback('Bibliothèque indisponible : ' + e.message); }
})();
