/**
 * BOJ.ART — editing plans attached to an explicit project.
 * This desk selects documented archive sources and saves versioned intentions.
 * It does not render media, infer artwork identity, or publish to a service.
 */
import {EDIT_SERIES, EDIT_FORMATS, EDIT_BEATS, EDIT_LIMITS, createEditDraft, normalizeEditPlan, latestEditVersion, projectEditPlans} from './edit-plan.js';
import {CONTENT_CATALOG, getContentSource} from './content-catalog.js';

const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const clone = value => JSON.parse(JSON.stringify(value));
const number = value => Number.isFinite(value) ? new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 2}).format(value) : '—';
const date = value => {
  const timestamp = typeof value === 'number' ? value : Date.parse(value);
  return Number.isFinite(timestamp) ? new Intl.DateTimeFormat('fr-FR', {day:'2-digit', month:'short', year:'numeric'}).format(timestamp) : 'Date non renseignée';
};
const svgPaths = {
  plus:'<path d="M12 5v14M5 12h14"/>', arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  play:'<path d="m9 5 11 7-11 7Z"/>', film:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4m10 0h4M3 15h4m10 0h4"/>',
  save:'<path d="M5 3h12l4 4v14H3V3Z"/><path d="M7 3v6h9V3M7 21v-8h10v8"/>',
  link:'<path d="m10 13 4-4M8 16l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 1 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(1 -1)"/>',
  check:'<path d="m5 12 4 4L19 6"/>', search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>'
};
const glyph = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${svgPaths[name] || svgPaths.arrow}</svg>`;
const uniqueId = prefix => prefix + (globalThis.crypto?.randomUUID?.() || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`);
const beatDefinition = id => EDIT_BEATS.find(beat => beat.id === id) || EDIT_BEATS[0];
const beatFrom = (plan, id) => plan.beats.find(beat => beat.id === id);
const relationFor = (plan, id) => plan.sources.find(source => source.postId === id)?.relation || 'reference';
const relationLabel = relation => relation === 'project' ? 'Parcours du projet · déclaré' : 'Référence artistique';

function recordsFor(project) {
  try { return projectEditPlans(project); } catch { return []; }
}

function archiveMap(archive) {
  const supplied = Array.isArray(archive) ? archive : Array.isArray(archive?.items) ? archive.items : [];
  const indexed = new Map(supplied.filter(source => source && typeof source.id === 'string').map(source => [source.id, source]));
  return new Map(CONTENT_CATALOG.map(catalogued => {
    const candidate = indexed.get(catalogued.id);
    // The static catalogue owns identities and timebases. The supplied index may
    // describe a temporarily unavailable preview, but cannot add arbitrary URLs.
    const source = {...catalogued};
    if (candidate) {
      if (candidate.available === false) source.available = false;
      if (candidate.preview === null) source.preview = null;
    }
    const cover = `./assets/archive/${source.id}.webp`;
    const preview = `./assets/archive/${source.id}.mp4`;
    source.cover = source.cover === cover ? cover : null;
    source.preview = source.available && source.preview === preview ? preview : null;
    return [source.id, source];
  }));
}

function initialSelection(project, planId, version) {
  const records = recordsFor(project);
  const selected = planId ? records.find(record => record.id === planId) : [...records].sort((a, b) => latestEditVersion(b).at - latestEditVersion(a).at)[0];
  if (!selected) return {record:null, stored:null, plan:createEditDraft(project)};
  const latest = latestEditVersion(selected);
  const requested = Number.isSafeInteger(Number(version)) && Number(version) > 0 ? Number(version) : latest.revision;
  const stored = selected.versions.find(item => item.revision === requested) || latest;
  return {record:selected, stored, plan:clone(stored.plan)};
}

function coverMarkup(source, className = '', esc = escapeHTML) {
  return source?.cover ? `<img class="${className}" src="${esc(source.cover)}" alt="Couverture de la publication : ${esc(source.title)}" loading="lazy" decoding="async">` : '';
}

function boardMarkup(plan, map, selectedBeat, esc = escapeHTML) {
  return EDIT_BEATS.map((definition, index) => {
    const beat = beatFrom(plan, definition.id);
    const source = beat.postId ? map.get(beat.postId) : null;
    const range = beat.in !== null && beat.out !== null ? `${number(beat.in)} → ${number(beat.out)} s` : source?.type === 'image' ? 'Photographies' : source ? 'Passage à définir' : 'Source à choisir';
    return `<button type="button" class="ps-beat ${source ? 'has-source' : 'is-empty'}" data-ps-beat="${definition.id}" aria-pressed="${selectedBeat === definition.id}" aria-label="${index + 1}. ${esc(definition.label)} — ${esc(range)}">
      <span class="ps-beat-visual">
        ${source ? coverMarkup(source, '', esc) : `<span class="ps-empty-mark ps-mark-${definition.id}" aria-hidden="true"><i></i><i></i><i></i></span><span class="ps-empty-intent">${esc(definition.prompt)}</span>`}
        <span class="ps-beat-number">0${index + 1}</span>
        <span class="ps-cover-label">${source ? 'COUVERTURE SOURCE' : 'PLAN À COMPOSER'}</span>
        <span class="ps-beat-open" aria-hidden="true">${glyph(source ? 'arrow' : 'plus')}</span>
      </span>
      <span class="ps-beat-caption"><strong>${esc(definition.label.toLocaleUpperCase('fr-FR'))}</strong><small>${esc(range)}</small></span>
      <span class="ps-beat-source">${source ? esc(relationLabel(relationFor(plan, source.id))) : 'Votre prise de vue, votre choix.'}</span>
    </button>`;
  }).join('');
}

function timelineMarkup(plan) {
  const weights = [.22, .23, .38, .17];
  let cursor = 0;
  return `<div class="ps-timeline-label"><span>RYTHME CIBLE · INDICATIF</span><span>${number(plan.duration)} s / ${escapeHTML(plan.format)}</span></div>
    <div class="ps-timeline-track">${EDIT_BEATS.map((definition, index) => {
      const start = cursor; cursor = index === EDIT_BEATS.length - 1 ? plan.duration : Math.round((cursor + plan.duration * weights[index]) * 10) / 10;
      return `<button type="button" data-ps-beat="${definition.id}" style="--ps-segment:${weights[index]}" aria-label="Ouvrir ${escapeHTML(definition.label)}"><i aria-hidden="true"></i><strong>${escapeHTML(definition.label)}</strong><span>${number(start)}–${number(cursor)} s</span></button>`;
    }).join('')}</div><p class="ps-help">Une intention de rythme pour le montage à réaliser. Les repères de chaque source se règlent dans sa vidéo originale.</p>`;
}

function editorMarkup(plan, map, selectedBeat, historical, esc = escapeHTML) {
  const definition = beatDefinition(selectedBeat);
  const beat = beatFrom(plan, selectedBeat);
  const source = beat.postId ? map.get(beat.postId) : null;
  const rangeAllowed = !!(source?.available && source.type === 'video' && Number.isFinite(source.duration) && source.duration > 0);
  const disabled = historical ? ' disabled' : '';
  const mediaState = source ? !source.available ? 'Média indisponible dans l’archive' : source.type === 'image' ? 'Photographies archivées' : source.preview ? 'Original archivé · aperçu disponible' : 'Original archivé · aperçu non intégré' : 'Aucune publication associée';
  return `<div class="ps-editor-heading"><span class="ps-kicker">${String(EDIT_BEATS.findIndex(item => item.id === selectedBeat) + 1).padStart(2, '0')} / LE CHOIX DU PLAN</span><h4>${esc(definition.label)}<span>.</span></h4></div>
    <div class="ps-selected-source ${source ? '' : 'is-empty'}">
      <span class="ps-selected-thumbnail">${source ? coverMarkup(source, '', esc) : glyph('film')}</span>
      <div><strong>${source ? esc(source.title) : 'Choisir une prise de vue'}</strong><small>${esc(mediaState)}</small>${source ? `<span class="ps-source-id">Publication ${esc(source.id)}</span>` : '<span class="ps-source-id">Les archives restent des références jusqu’à votre déclaration.</span>'}</div>
    </div>
    <div class="ps-editor-actions"><button type="button" class="ps-text-button" data-ps-library-open data-ps-editable${disabled}>${glyph('plus')}${source ? 'Changer la source' : 'Choisir dans les archives'}</button>${source ? `<button type="button" class="ps-text-button" data-ps-preview-source="${esc(source.id)}">${glyph('play')}Voir l’aperçu</button><button type="button" class="ps-text-button ps-subtle" data-ps-clear-source data-ps-editable${disabled}>Retirer</button>` : ''}</div>
    <label class="ps-field">Rôle de cette publication dans le dossier<select name="sourceRelation" data-ps-editable${disabled}${source ? '' : ' disabled'}>
      <option value="reference" ${!source || relationFor(plan, source.id) === 'reference' ? 'selected' : ''}>Référence artistique</option>
      <option value="project" ${source && relationFor(plan, source.id) === 'project' ? 'selected' : ''}>Parcours de ce projet — déclaré par moi</option>
    </select></label>
    <p class="ps-help" data-ps-relation-note>${source && relationFor(plan, source.id) === 'project' ? 'Vous déclarez que ce média documente ce dossier. Le Studio ne vérifie pas automatiquement l’identité ou la dimension de la pièce.' : 'Une référence guide le style ou le geste ; elle ne prouve pas que cette pièce appartient à ce dossier.'}</p>
    <label class="ps-field">Ce que ce plan doit raconter<textarea name="beatNote" rows="3" maxlength="${EDIT_LIMITS.beatNote}" data-ps-editable${disabled}>${esc(beat.note)}</textarea></label>
    <fieldset class="ps-source-range"><legend>Passage dans l’original ${rangeAllowed ? `<span>0 à ${number(source.duration)} s</span>` : ''}</legend>
      <div><label class="ps-field">Entrée · s<input name="beatIn" type="number" min="0" step="0.01" ${rangeAllowed ? `max="${source.duration}"` : ''} value="${beat.in === null ? '' : esc(beat.in)}" placeholder="À définir" data-ps-editable${historical || !rangeAllowed ? ' disabled' : ''}></label>
      <span class="ps-range-arrow" aria-hidden="true">→</span>
      <label class="ps-field">Sortie · s<input name="beatOut" type="number" min="0" step="0.01" ${rangeAllowed ? `max="${source.duration}"` : ''} value="${beat.out === null ? '' : esc(beat.out)}" placeholder="À définir" data-ps-editable${historical || !rangeAllowed ? ' disabled' : ''}></label></div>
      <p class="ps-help" data-ps-range-help>${!source ? 'Choisissez une publication pour définir le passage.' : !source.available ? 'L’original est indisponible : les repères restent à définir.' : source.type === 'image' ? 'Une photographie n’a pas de plage vidéo. La durée d’affichage sera décidée au montage.' : !rangeAllowed ? 'La durée de l’original est inconnue : les repères restent à définir.' : 'Les deux repères sont facultatifs au brouillon. Ensemble : 0 ≤ entrée < sortie ≤ durée originale. L’aperçu court est un extrait distinct.'}</p>
    </fieldset>`;
}

function previewMarkup(source, esc = escapeHTML) {
  if (!source) return `<div class="ps-preview-empty"><span class="ps-kicker">LE MONITEUR SOURCE</span><span class="ps-monitor-glyph" aria-hidden="true">${glyph('play')}</span><h4>Voir avant<br>de choisir<span>.</span></h4><p>Ouvrez un aperçu depuis les archives. Votre scénario reste à l’écran.</p></div>`;
  const previewReady = source.available && source.preview && Number.isFinite(source.previewStart) && Number.isFinite(source.previewSeconds);
  return `<div class="ps-preview-heading"><span class="ps-kicker">LE MONITEUR SOURCE</span><button type="button" class="ps-text-button" data-ps-preview-close aria-label="Fermer l’aperçu">Fermer ×</button></div>
    <div class="ps-preview-screen">
      ${previewReady ? `<video data-ps-preview-video data-post-id="${esc(source.id)}" data-preview-start="${source.previewStart}" data-preview-seconds="${source.previewSeconds}" src="${esc(source.preview)}" ${source.cover ? `poster="${esc(source.cover)}"` : ''} controls muted playsinline preload="metadata" aria-label="Aperçu archivé de ${esc(source.title)}"></video>` : coverMarkup(source, '', esc)}
      ${previewReady ? '' : '<span class="ps-preview-cover">COUVERTURE DE PUBLICATION</span>'}
    </div>
    <div class="ps-preview-caption"><strong>${esc(source.title)}</strong><span>${esc(date(source.date))} · ${source.type === 'image' ? 'Photographies' : `Original ${number(source.duration)} s`}</span></div>
    <p class="ps-preview-timebase" data-ps-preview-timebase>${previewReady ? `Aperçu local : <b>0–${number(source.previewSeconds)} s</b><br>Dans l’original : <b>${number(source.previewStart)}–${number(source.previewStart + source.previewSeconds)} s</b>` : !source.available ? '<b>Média indisponible dans l’archive.</b> Cette couverture ne remplace pas l’original.' : source.type === 'image' ? 'Publication photographique. La couverture identifie la publication ; elle ne présente pas nécessairement toutes ses images.' : 'Original archivé ; aucun aperçu vidéo n’est intégré pour cette publication.'}</p>
    <p class="ps-help" data-ps-preview-status>${previewReady ? 'Le lecteur montre uniquement cet extrait court. La couverture n’est pas une image calculée à votre point d’entrée.' : 'La source peut être décrite dans le plan, avec sa disponibilité explicite.'}</p>
    <a class="ps-text-button" href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${glyph('link')}Publication d’origine</a>`;
}

function libraryMarkup(plan, map, search, historical, esc = escapeHTML) {
  const query = search.trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('fr-FR');
  const list = [...map.values()].filter(source => `${source.title} ${source.description || ''} ${source.id} ${source.date || ''}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('fr-FR').includes(query));
  const selected = new Set(plan.sources.map(source => source.postId));
  return `<p class="ps-library-count" data-ps-library-count>${list.length} publication${list.length > 1 ? 's' : ''} sur ${map.size} · couvertures d’archives</p><div class="ps-library-grid">${list.map(source => `<article class="ps-library-card ${selected.has(source.id) ? 'is-chosen' : ''}" data-ps-library-source="${esc(source.id)}">
      <button class="ps-library-cover" type="button" data-ps-preview-source="${esc(source.id)}" aria-label="Voir ${esc(source.title)}">${coverMarkup(source, '', esc)}<span>${source.type === 'image' ? 'PHOTOGRAPHIES' : 'COUVERTURE'}${selected.has(source.id) ? ' · CHOISIE' : ''}</span><i aria-hidden="true">${glyph('play')}</i></button>
      <div class="ps-library-copy"><small>${esc(date(source.date))} · ${source.type === 'image' ? 'Photo' : `${number(source.duration)} s`}</small><h5>${esc(source.title)}</h5><p>${!source.available ? 'Média indisponible' : source.preview ? 'Aperçu vidéo disponible' : source.type === 'image' ? 'Publication photographique' : 'Aperçu non intégré'}</p><button type="button" class="ps-choose-source" data-ps-choose-source="${esc(source.id)}" data-ps-editable${historical ? ' disabled' : ''}>${glyph('plus')}Choisir pour ce plan</button></div>
    </article>`).join('') || '<p class="ps-library-no-results">Aucune publication ne correspond. Essayez un nom d’œuvre, une technique ou une date.</p>'}</div>`;
}

function settingsMarkup(plan, esc) {
  return `<details class="ps-details ps-direction" open><summary><span><b>02</b> La direction créative</span><i aria-hidden="true">+</i></summary><div class="ps-details-body">
      <label class="ps-field ps-title-field">Titre du montage<input name="title" value="${esc(plan.title)}" maxlength="${EDIT_LIMITS.title}" required data-ps-editable></label>
      <fieldset class="ps-series"><legend>La série</legend><div>${EDIT_SERIES.map((series, index) => `<label><input type="radio" name="series" value="${series.id}" ${plan.series === series.id ? 'checked' : ''} data-ps-editable><span><small>0${index + 1}</small><strong>${esc(series.label)}</strong></span></label>`).join('')}</div><p class="ps-help" data-ps-series-description>${esc(EDIT_SERIES.find(series => series.id === plan.series)?.description)}</p></fieldset>
      <div class="ps-format-duration"><fieldset class="ps-formats"><legend>Le cadre</legend><div>${EDIT_FORMATS.map(format => `<label><input type="radio" name="format" value="${format}" ${plan.format === format ? 'checked' : ''} data-ps-editable><span><i style="--ps-ratio:${format.replace(':', '/')}" aria-hidden="true"></i><strong>${format}</strong><small>${format === '9:16' ? 'Vertical' : format === '1:1' ? 'Carré' : 'Panoramique'}</small></span></label>`).join('')}</div></fieldset>
      <div class="ps-duration"><div><label for="ps-duration">La durée cible</label><output data-ps-duration-output for="ps-duration">${plan.duration}<small> SECONDES</small></output></div><input id="ps-duration" name="duration" type="range" min="10" max="60" step="1" value="${plan.duration}" data-ps-editable><div class="ps-duration-labels"><span>10 s</span><span>60 s</span></div><p class="ps-help">Le rythme s’adapte à l’intention. La durée du film sera vérifiée au rendu.</p></div></div>
      <label class="ps-field">Brief & scénario<textarea name="brief" rows="5" maxlength="${EDIT_LIMITS.brief}" placeholder="L’idée, ce que l’on voit, la progression et la conclusion…" data-ps-editable>${esc(plan.brief)}</textarea></label>
    </div></details>
    <details class="ps-details ps-editorial"><summary><span><b>03</b> Le son & la prise de parole</span><i aria-hidden="true">+</i></summary><div class="ps-details-body ps-editorial-grid">
      <div><label class="ps-field">Direction sonore<textarea name="audioNotes" rows="5" maxlength="${EDIT_LIMITS.audioNotes}" placeholder="Silence, sons de l’atelier, accent sonore, musique à choisir…" data-ps-editable>${esc(plan.audioNotes)}</textarea></label><p class="ps-help">Décrivez le son voulu et sa provenance. Ces notes ne génèrent pas de piste audio.</p></div>
      <div><label class="ps-field">Légende proposée<textarea name="caption" rows="5" maxlength="${EDIT_LIMITS.caption}" placeholder="L’œuvre, son histoire, une invitation à échanger…" data-ps-editable>${esc(plan.caption)}</textarea></label><p class="ps-help">Texte de préparation, conservé avec la version du montage.</p></div>
    </div></details>`;
}

/** Render only the explicitly selected saved plan, or a source-free new draft. */
export function renderProjectStudio({project, archive, esc = escapeHTML, icon = glyph, planId = null, version = null} = {}) {
  if (!project?.id) return '<section class="project-studio"><p>Le dossier cible est introuvable.</p></section>';
  const selected = initialSelection(project, planId, version);
  const plan = selected.plan, map = archiveMap(archive);
  const latest = selected.record ? latestEditVersion(selected.record) : null;
  const historical = !!(selected.stored && selected.stored.revision < latest.revision);
  return `<section class="project-studio" data-project-studio data-motion="on">
      <div class="ps-masthead"><span class="ps-brand">BOJ<span>.</span>ART <small>/ STUDIO DU PROJET</small></span><button type="button" class="ps-text-button" data-action="studio">${icon('film')}Voir le film de référence</button></div>
      <header class="ps-hero"><div><p class="ps-kicker"><i></i> DE L’INTENTION À L’ÉDIT</p><h2>LE FIL<br><em>DU PROJET.</em></h2></div><div class="ps-hero-context"><span class="ps-kicker">DOSSIER CIBLE</span><strong data-ps-target-name>${esc(project.name)}</strong><p>Le détail attire. Le geste raconte.<br>L’œuvre se révèle. BOJ.ART signe.</p><div class="ps-hero-metrics"><span><b data-ps-source-count>${plan.sources.length.toString().padStart(2, '0')}</b><small>SOURCES CHOISIES</small></span><span><b>04</b><small>TEMPS À COMPOSER</small></span></div></div></header>
      <div class="ps-context" data-ps-context role="status" hidden></div>
      <form data-project-studio-form data-project="${esc(project.id)}" data-project-id="${esc(project.id)}" data-plan-id="${esc(selected.record?.id || '')}" data-revision="${latest?.revision || 0}" data-viewed-revision="${selected.stored?.revision || 0}" novalidate>
        <div class="ps-version-bar"><label class="ps-field">Plans de ce dossier<select data-ps-plan-picker aria-label="Plans de ce dossier"></select></label><label class="ps-field">Version consultée<select data-ps-history aria-label="Version du plan"></select></label><button type="button" class="ps-text-button" data-ps-new>${glyph('plus')}Nouveau plan</button></div>
        <div class="ps-version-note" data-ps-version-note role="status"></div>
        <section class="ps-storyboard" aria-label="Storyboard en quatre temps"><div class="ps-section-heading"><div><span class="ps-kicker">01 / LE STORYBOARD</span><h3>CONSTRUIRE<br>LE REGARD<span>.</span></h3></div><p>Choisissez chaque source.<br>Les images restent entières.</p></div>
          <div class="ps-board" data-ps-board>${boardMarkup(plan, map, 'detail', esc)}</div>
          <div class="ps-timeline" data-ps-timeline>${timelineMarkup(plan)}</div>
          <div class="ps-shot-desk"><div class="ps-beat-editor" data-ps-editor>${editorMarkup(plan, map, 'detail', historical, esc)}</div><aside class="ps-source-monitor" data-ps-preview aria-label="Aperçu de la publication">${previewMarkup(null, esc)}</aside></div>
          <section class="ps-library" data-ps-library hidden aria-label="Bibliothèque des publications BOJ.ART"><div class="ps-library-heading"><div><span class="ps-kicker">LES SOURCES AUTHENTIQUES</span><h4>LES ARCHIVES<span>.</span></h4></div><button class="ps-text-button" type="button" data-ps-library-close>Fermer ×</button></div><p class="ps-library-intro">Choisir pour <strong data-ps-library-beat>Le détail</strong>. Une publication est d’abord une référence artistique ; vous déclarez ensuite son lien éventuel avec ce dossier.</p><label class="ps-search">${glyph('search')}<span class="ps-sr-only">Rechercher dans les publications</span><input type="search" data-ps-search placeholder="Baki, peinture, prototype, date…" autocomplete="off"></label><div data-ps-library-results>${libraryMarkup(plan, map, '', historical, esc)}</div></section>
        </section>
        ${settingsMarkup(plan, esc)}
        <div class="ps-save-bar"><label class="ps-field ps-status-field">État du plan<select name="status" data-ps-editable><option value="draft" ${plan.status === 'draft' ? 'selected' : ''}>Brouillon</option><option value="ready_to_edit" ${plan.status === 'ready_to_edit' ? 'selected' : ''}>Prêt à monter — déclaré</option></select></label><div class="ps-save-actions"><button type="submit" class="button button-red" data-ps-save>${icon('save')}<span>Enregistrer une version</span></button><button type="button" class="button" data-ps-export disabled>${icon('arrow')}Exporter cette version</button></div></div>
        <p class="ps-message" data-ps-message role="status" aria-live="polite"></p><p class="ps-footer-note" data-ps-save-note>Les choix restent dans ce dossier. L’export décrit un plan de montage avec ses sources ; le film est à réaliser.</p>
      </form>
    </section>`;
}

/**
 * A mounted desk captures its target, baseline revision and local drafts.
 * refreshContext updates target facts; it never replaces an editable plan.
 */
export function mountProjectStudio(root, {project, archive, onSave, onExport, motion = true, activeProjectId = project?.id} = {}) {
  const view = root?.matches?.('[data-project-studio]') ? root : root?.querySelector?.('[data-project-studio]');
  const form = view?.querySelector('[data-project-studio-form]');
  if (!view || !form || !project?.id) return {dispose() {}, setMotion() {}, refreshContext() {}};
  const targetId = String(project.id);
  const q = selector => view.querySelector(selector);
  const qa = selector => [...view.querySelectorAll(selector)];
  let target = project, activeId = activeProjectId || targetId, sources = archiveMap(archive);
  let selectedBeat = 'detail', previewId = null, search = '', disposed = false, saving = false, exporting = false, motionEnabled = !!motion;
  let editSequence = 0, targetMissing = false, message = '', messageTone = '', notice = '';
  const drafts = new Map();
  const initial = initialSelection(project, form.dataset.planId || null, Number(form.dataset.viewedRevision) || null);

  function sessionFor(record, stored = record ? latestEditVersion(record) : null) {
    const latest = record ? latestEditVersion(record) : null;
    const plan = stored ? clone(stored.plan) : createEditDraft(target);
    return {key:uniqueId('draft-'), planId:record?.id || uniqueId('edit-'), expectedRevision:latest?.revision || 0,
      expectedVersionId:latest?.operationId || null,
      expectedSnapshot:latest ? clone(latest) : null, viewedSnapshot:stored ? clone(stored) : null,
      viewedRevision:stored?.revision || 0, plan, baseline:clone(plan), historical:!!(stored && stored.revision < latest.revision),
      originalProjectName:stored?.projectName || target.name, dirty:!stored};
  }
  let session = sessionFor(initial.record, initial.stored);

  function currentRecord() { return recordsFor(target).find(record => record.id === session.planId) || null; }
  function latest() { return latestEditVersion(currentRecord()); }
  function sameVersion(left, right) { return !!left && !!right && JSON.stringify(left) === JSON.stringify(right); }
  function expectedSnapshotChanged() {
    const record = currentRecord();
    if (session.expectedRevision === 0) return !!record;
    const stored = record?.versions.find(version => version.revision === session.expectedRevision);
    return !sameVersion(stored, session.expectedSnapshot);
  }
  function isConflict() { return !saving && (expectedSnapshotChanged() || (latest()?.revision || 0) !== session.expectedRevision); }
  function hasSavedVersion() {
    const stored = currentRecord()?.versions.find(version => version.revision === session.viewedRevision);
    return sameVersion(stored, session.viewedSnapshot);
  }

  function writeMessage(text, tone = '') {
    message = text || ''; messageTone = tone;
    const node = q('[data-ps-message]');
    node.textContent = message; node.dataset.tone = tone;
  }

  function stashDraft() {
    if (!session.historical && (session.dirty || !session.viewedRevision || expectedSnapshotChanged())) {
      const copy = clone(session);
      if (expectedSnapshotChanged()) copy.dirty = true;
      drafts.set(session.key, copy);
    }
  }

  function captureFields() {
    if (session.historical) return;
    for (const name of ['title', 'brief', 'caption', 'audioNotes', 'status']) {
      const node = form.elements.namedItem(name);
      if (node && typeof node.value === 'string') session.plan[name] = node.value;
    }
    for (const name of ['series', 'format']) {
      const checked = q(`input[name="${name}"]:checked`);
      if (checked) session.plan[name] = checked.value;
    }
    const duration = q('[name="duration"]');
    if (duration) session.plan.duration = Number(duration.value);
    const beat = beatFrom(session.plan, selectedBeat);
    const note = q('[name="beatNote"]');
    if (note) beat.note = note.value;
    const source = beat.postId ? sources.get(beat.postId) : null;
    if (source?.available && source.type === 'video' && Number.isFinite(source.duration)) {
      for (const [field, property] of [['beatIn', 'in'], ['beatOut', 'out']]) {
        const input = q(`[name="${field}"]`);
        if (input) beat[property] = input.value === '' ? null : Number(input.value);
      }
    }
    const relation = q('[name="sourceRelation"]');
    const reference = session.plan.sources.find(item => item.postId === beat.postId);
    if (reference && relation && ['reference', 'project'].includes(relation.value)) reference.relation = relation.value;
  }

  function changed() {
    session.dirty = !!session.resumed || session.viewedRevision === 0 || JSON.stringify(session.plan) !== JSON.stringify(session.baseline);
    editSequence++;
    if (!saving && messageTone !== 'error') writeMessage('');
    syncMeta();
  }

  function updateBoard() {
    const board = q('[data-ps-board]');
    const container = view.ownerDocument.createElement('div');
    container.innerHTML = boardMarkup(session.plan, sources, selectedBeat);
    // Preserve card elements so focus and the active-frame transition survive
    // changing a beat, a range or the source relationship.
    [...container.children].forEach((next, index) => {
      const existing = board.children[index];
      if (!existing) { board.append(next); return; }
      if (existing.innerHTML !== next.innerHTML) existing.innerHTML = next.innerHTML;
      existing.className = next.className;
      existing.setAttribute('aria-pressed', next.getAttribute('aria-pressed'));
      existing.setAttribute('aria-label', next.getAttribute('aria-label'));
    });
    const timeline = q('[data-ps-timeline]'), markup = timelineMarkup(session.plan);
    if (timeline.innerHTML !== markup) timeline.innerHTML = markup;
  }

  function updateEditor() {
    q('[data-ps-editor]').innerHTML = editorMarkup(session.plan, sources, selectedBeat, session.historical);
    q('[data-ps-library-beat]').textContent = beatDefinition(selectedBeat).label;
  }

  function updateLibrary() {
    q('[data-ps-library-results]').innerHTML = libraryMarkup(session.plan, sources, search, session.historical);
  }

  function pausePreview() {
    const video = q('video[data-ps-preview-video]');
    if (video) { try { video.pause(); } catch {} }
  }

  function showPreview(id) {
    pausePreview();
    previewId = id && sources.has(id) ? id : null;
    q('[data-ps-preview]').innerHTML = previewMarkup(previewId ? sources.get(previewId) : null);
  }

  function syncFields() {
    for (const name of ['title', 'brief', 'caption', 'audioNotes', 'status', 'duration']) {
      const node = q(`[name="${name}"]`);
      if (node) node.value = String(session.plan[name]);
    }
    for (const name of ['series', 'format']) qa(`input[name="${name}"]`).forEach(node => { node.checked = node.value === session.plan[name]; });
    updateBoard(); updateEditor(); updateLibrary(); syncMeta();
  }

  function updatePickers() {
    const records = recordsFor(target);
    const planOptions = new Map(records.map(record => [record.id, latestEditVersion(record).plan.title]));
    for (const local of drafts.values()) if (!planOptions.has(local.planId)) planOptions.set(local.planId, local.plan.title || 'Brouillon sans titre');
    if (!planOptions.has(session.planId)) planOptions.set(session.planId, session.plan.title || 'Nouveau plan');
    const picker = q('[data-ps-plan-picker]');
    const planHTML = [...planOptions].map(([id, title]) => `<option value="${escapeHTML(id)}" ${id === session.planId ? 'selected' : ''}>${escapeHTML(title)}${records.some(record => record.id === id) ? '' : ' · non enregistré'}</option>`).join('');
    if (picker.innerHTML !== planHTML) picker.innerHTML = planHTML;
    picker.value = session.planId;
    picker.disabled = saving;
    const record = currentRecord(), history = q('[data-ps-history]');
    const localDrafts = [...drafts.values()].filter(local => local.planId === session.planId && local.key !== session.key);
    const ownDraft = !session.historical && (session.dirty || !session.viewedRevision);
    const options = [ownDraft ? `<option value="draft:${escapeHTML(session.key)}">Brouillon actuel${session.expectedRevision ? ` · depuis v${session.expectedRevision}` : ''}</option>` : '',
      ...localDrafts.map(local => `<option value="draft:${escapeHTML(local.key)}">Brouillon conservé${local.expectedRevision ? ` · depuis v${local.expectedRevision}` : ''} · ${escapeHTML((local.plan.title || 'Sans titre').slice(0, 40))}</option>`),
      ...(record?.versions || []).slice().reverse().map(version => `<option value="${version.revision}">Version ${version.revision} · ${escapeHTML(date(version.at))}${version.revision === latest()?.revision ? ' · dernière' : ''}</option>`)];
    history.innerHTML = options.join('') || '<option value="0">Nouveau brouillon</option>';
    history.value = ownDraft ? `draft:${session.key}` : String(session.viewedRevision);
    history.disabled = saving || (!record && localDrafts.length === 0);
  }

  function syncMeta() {
    form.dataset.project = targetId;
    form.dataset.projectId = targetId;
    form.dataset.planId = session.planId;
    form.dataset.revision = String(session.expectedRevision);
    form.dataset.expectedVersionId = session.expectedVersionId || '';
    form.dataset.viewedRevision = String(session.viewedRevision);
    form.dataset.dirty = String(session.dirty);
    form.dataset.historical = String(session.historical);
    view.dataset.targetMissing = String(targetMissing);
    q('[data-ps-target-name]').textContent = target?.name || session.originalProjectName;
    q('[data-ps-source-count]').textContent = String(session.plan.sources.length).padStart(2, '0');
    q('[data-ps-duration-output]').innerHTML = `${number(session.plan.duration)}<small> SECONDES</small>`;
    q('[data-ps-series-description]').textContent = EDIT_SERIES.find(series => series.id === session.plan.series)?.description || '';
    q('[data-ps-board]').dataset.format = session.plan.format;
    view.dataset.format = session.plan.format;
    qa('[data-ps-editable]').forEach(node => {
      let unavailable = false;
      if (node.name === 'sourceRelation') unavailable = !beatFrom(session.plan, selectedBeat).postId;
      if (node.name === 'beatIn' || node.name === 'beatOut') {
        const source = sources.get(beatFrom(session.plan, selectedBeat).postId);
        unavailable = !(source?.available && source.type === 'video' && Number.isFinite(source.duration) && source.duration > 0);
      }
      node.disabled = session.historical || targetMissing || unavailable;
    });
    const warning = q('[data-ps-context]');
    const warnings = [];
    if (targetMissing) warnings.push('Le dossier cible est introuvable. Votre texte reste conservé dans ce panneau ; l’enregistrement attend son retour.');
    else if (activeId !== targetId) warnings.push(`Ce montage reste lié à « ${target.name} ». Un autre dossier est sélectionné sur la tour. Enregistrer conservera cette cible.`);
    if (isConflict()) {
      if (expectedSnapshotChanged()) warnings.push(`L’historique a changé après synchronisation : la version v${session.expectedRevision} attendue a été remplacée ou n’est plus présente. Vos choix sont conservés. Une reprise explicite est nécessaire avant d’enregistrer ou d’exporter.`);
      else warnings.push(`Une version plus récente existe : v${latest().revision}. Votre brouillon est conservé sur la révision v${session.expectedRevision}.`);
    }
    if (session.originalProjectName !== target?.name && !targetMissing) warnings.push(`Le dossier s’appelle maintenant « ${target.name} » ; le plan consulté a été préparé sous « ${session.originalProjectName} ».`);
    warning.hidden = warnings.length === 0;
    warning.innerHTML = warnings.map(text => `<p>${escapeHTML(text)}</p>`).join('') + (isConflict() && !session.historical && latest() ? `<button type="button" class="ps-text-button" data-ps-rebase>Reprendre mon brouillon sur la v${latest().revision}${glyph('arrow')}</button>` : '');
    const versionNote = q('[data-ps-version-note]');
    const latestVersion = latest();
    if (session.historical) versionNote.innerHTML = `<span>Version ${session.viewedRevision} conservée · consultation seule${session.originalProjectName ? ` · ${escapeHTML(session.originalProjectName)}` : ''}.</span><button type="button" class="ps-text-button" data-ps-resume>Reprendre cette version${glyph('arrow')}</button>`;
    else versionNote.innerHTML = `<span>${!saving && expectedSnapshotChanged() ? 'Vos choix locaux sont conservés ; l’historique attendu a changé.' : session.viewedRevision === 0 ? 'Nouveau brouillon · aucune version enregistrée.' : session.dirty ? `Vos modifications attendent une nouvelle version${session.expectedRevision ? ` après la v${session.expectedRevision}` : ''}.` : `Version ${session.viewedRevision} conservée${latestVersion?.at ? ` · ${escapeHTML(date(latestVersion.at))}` : ''}.`}${notice ? ` ${escapeHTML(notice)}` : ''}</span>`;
    const save = q('[data-ps-save]');
    save.disabled = saving || targetMissing || session.historical || expectedSnapshotChanged() || typeof onSave !== 'function' || (!session.dirty && !!session.viewedRevision) || session.expectedRevision >= EDIT_LIMITS.versions;
    save.querySelector('span').textContent = saving ? 'Enregistrement…' : activeId !== targetId ? `Enregistrer pour ${target?.name || session.originalProjectName}` : 'Enregistrer une version';
    const exportButton = q('[data-ps-export]');
    exportButton.disabled = saving || exporting || targetMissing || expectedSnapshotChanged() || session.dirty || !hasSavedVersion() || typeof onExport !== 'function';
    exportButton.setAttribute('aria-busy', String(exporting));
    q('[data-ps-new]').disabled = saving || targetMissing || recordsFor(target).length >= EDIT_LIMITS.plans;
    q('[data-ps-save-note]').textContent = session.expectedRevision >= EDIT_LIMITS.versions ? 'Cet historique contient 50 versions. Créez un nouveau plan pour poursuivre ; les versions précédentes restent conservées.' : session.dirty && session.viewedRevision ? 'Enregistrez vos modifications avant d’exporter cette nouvelle version. L’export décrit le plan et ses sources ; le film est à réaliser.' : 'Les choix restent dans ce dossier. L’export décrit un plan de montage avec ses sources ; le film est à réaliser.';
    updatePickers();
  }

  function selectBeat(id) {
    if (!EDIT_BEATS.some(beat => beat.id === id)) return;
    captureFields(); selectedBeat = id;
    updateBoard(); updateEditor(); syncMeta();
  }

  function selectSource(id) {
    if (session.historical || targetMissing || !getContentSource(id)) return;
    captureFields();
    const beat = beatFrom(session.plan, selectedBeat);
    const previous = beat.postId;
    beat.postId = id;
    if (previous !== id) { beat.in = null; beat.out = null; }
    if (!session.plan.sources.some(source => source.postId === id)) session.plan.sources.push({postId:id, relation:'reference'});
    if (previous && previous !== id && !session.plan.beats.some(item => item.postId === previous)) session.plan.sources = session.plan.sources.filter(source => source.postId !== previous);
    changed(); updateBoard(); updateEditor(); updateLibrary();
    q('[data-ps-library]').hidden = true;
    showPreview(id);
  }

  function removeSource() {
    if (session.historical || targetMissing) return;
    captureFields();
    const beat = beatFrom(session.plan, selectedBeat), previous = beat.postId;
    beat.postId = null; beat.in = null; beat.out = null;
    if (!session.plan.beats.some(item => item.postId === previous)) session.plan.sources = session.plan.sources.filter(source => source.postId !== previous);
    changed(); updateBoard(); updateEditor(); updateLibrary();
  }

  function openNew() {
    if (saving || targetMissing || recordsFor(target).length >= EDIT_LIMITS.plans) return;
    captureFields(); stashDraft();
    session = sessionFor(null); selectedBeat = 'detail'; notice = 'Les autres brouillons restent consultables dans ce panneau.';
    editSequence++; writeMessage(''); showPreview(null); syncFields();
  }

  function prepareSeries(series) {
    if(disposed||saving||targetMissing||!EDIT_SERIES.some(item=>item.id===series)||recordsFor(target).length>=EDIT_LIMITS.plans)return false;
    openNew();
    session.plan=createEditDraft(target,series);session.baseline=clone(session.plan);session.dirty=true;
    notice='Intention éditoriale préparée dans un nouveau brouillon. Les versions conservées restent consultables.';
    syncFields();return true;
  }

  function loadPlan(id) {
    if (saving || !id || id === session.planId) return;
    captureFields(); stashDraft();
    const local = [...drafts.values()].reverse().find(draft => draft.planId === id);
    const record = recordsFor(target).find(item => item.id === id);
    if (!local && !record) return;
    session = local ? clone(local) : sessionFor(record);
    selectedBeat = 'detail'; notice = local ? 'Brouillon repris depuis cette fenêtre.' : '';
    editSequence++; writeMessage(''); showPreview(null); syncFields();
  }

  function viewVersion(value) {
    if (saving) return;
    captureFields(); stashDraft();
    if (String(value).startsWith('draft:')) {
      const local = drafts.get(String(value).slice(6));
      if (!local) return;
      session = clone(local); notice = 'Brouillon repris depuis cette fenêtre.';
    } else {
      const record = currentRecord(), stored = record?.versions.find(item => item.revision === Number(value));
      if (!stored) return;
      session = sessionFor(record, stored); notice = drafts.size ? 'Vos brouillons restent consultables dans le choix de version.' : '';
    }
    selectedBeat = 'detail'; editSequence++; writeMessage(''); showPreview(null); syncFields();
  }

  function resumeVersion() {
    if (!session.historical || targetMissing || saving) return;
    const previous = session.viewedRevision, record = currentRecord();
    if (!record) return;
    const plan = clone(session.plan);
    session = sessionFor(record);
    session.plan = plan; session.dirty = true;
    // Even identical choices append a new revision after explicit resumption.
    session.resumed = true;
    notice = `Reprise de la v${previous} pour une nouvelle version après la v${session.expectedRevision}.`;
    editSequence++; writeMessage(''); syncFields();
  }

  function rebaseDraft() {
    if (session.historical || saving || !latest() || targetMissing) return;
    captureFields();
    const version = latest();
    session.expectedRevision = version.revision;
    session.expectedVersionId = version.operationId;
    session.expectedSnapshot = clone(version);
    session.viewedSnapshot = clone(version);
    session.viewedRevision = version.revision;
    session.baseline = clone(version.plan);
    session.originalProjectName = target.name;
    session.dirty = true; session.resumed = true;
    notice = `Vos choix sont conservés pour une nouvelle version après la v${version.revision}.`;
    editSequence++; syncMeta(); writeMessage('Votre brouillon a été repris sur la dernière version. Vous pouvez l’enregistrer sans modifier l’historique.');
  }

  async function saveVersion() {
    if (disposed || saving || session.historical || targetMissing || typeof onSave !== 'function') return;
    captureFields();
    if (expectedSnapshotChanged()) { writeMessage('L’historique attendu a changé après synchronisation. Reprenez explicitement votre brouillon avant d’enregistrer ; vos choix restent conservés.', 'error'); return; }
    let plan;
    try { plan = normalizeEditPlan(session.plan); }
    catch (error) { writeMessage(error.message, 'error'); return; }
    if (session.expectedRevision >= EDIT_LIMITS.versions) { writeMessage('Cet historique contient déjà 50 versions. Créez un nouveau plan.', 'error'); return; }
    if (!session.dirty && session.viewedRevision && !session.resumed) { writeMessage('Cette version est déjà conservée. Modifiez le plan pour préparer la suivante.'); return; }
    const submitted = {key:session.key, planId:session.planId, expectedRevision:session.expectedRevision, expectedVersionId:session.expectedVersionId, sequence:editSequence, plan};
    saving = true; writeMessage('Enregistrement de la version…'); syncMeta();
    try {
      const result = await onSave({projectId:targetId, planId:submitted.planId, expectedRevision:submitted.expectedRevision, expectedVersionId:submitted.expectedVersionId, plan:clone(submitted.plan)});
      if (disposed) return;
      if (!result?.ok) { writeMessage(result?.message || 'La version n’a pas été enregistrée. Votre brouillon est conservé.', 'error'); return; }
      if (result.project?.id === targetId) { target = result.project; targetMissing = false; }
      const record = result.record?.id === submitted.planId ? result.record : recordsFor(target).find(item => item.id === submitted.planId);
      const stored = record ? latestEditVersion(record) : null;
      const revision = Number.isSafeInteger(result.revision) ? result.revision : stored?.revision;
      if (!record || !stored || !Number.isSafeInteger(revision) || revision !== submitted.expectedRevision + 1 || stored.revision !== revision || JSON.stringify(stored.plan) !== JSON.stringify(submitted.plan)) {
        writeMessage('La sauvegarde a répondu, mais sa version n’a pas pu être vérifiée. Votre brouillon est conservé ; consultez l’historique avant de réessayer.', 'error'); return;
      }
      // Some callers return a record before their state subscription fires.
      if (!recordsFor(target).some(item => item.id === record.id && latestEditVersion(item).revision >= revision)) {
        const records = recordsFor(target).filter(item => item.id !== record.id);
        target = {...target, contentPlans:[...records, clone(record)]};
      }
      session.planId = record.id; session.expectedRevision = revision; session.viewedRevision = revision;
      session.expectedVersionId = stored.operationId;
      session.expectedSnapshot = clone(stored); session.viewedSnapshot = clone(stored);
      session.baseline = clone(stored.plan); session.historical = false; session.resumed = false; session.originalProjectName = stored.projectName;
      if (editSequence === submitted.sequence && session.key === submitted.key) {
        session.plan = clone(stored.plan); session.dirty = false;
      } else session.dirty = JSON.stringify(session.plan) !== JSON.stringify(stored.plan);
      drafts.delete(submitted.key); notice = '';
      writeMessage(result.message || `Version ${revision} enregistrée pour « ${target.name} ».`, result.persisted === false ? 'pending' : 'success');
    } catch (error) {
      if (!disposed) writeMessage(error?.message || 'L’enregistrement a échoué. Votre texte est conservé.', 'error');
    } finally {
      saving = false;
      if (!disposed) syncMeta();
    }
  }

  async function exportVersion() {
    if (disposed || exporting || saving || targetMissing || typeof onExport !== 'function') return;
    captureFields();
    if (expectedSnapshotChanged() || !hasSavedVersion()) { writeMessage('La version consultée ne correspond plus exactement à l’historique conservé. Consultez cette version ou reprenez votre brouillon avant l’export.', 'error'); return; }
    if (session.dirty) { writeMessage('Enregistrez cette version avant de l’exporter.', 'error'); return; }
    const requested = {projectId:targetId, planId:session.planId, version:session.viewedRevision, expectedVersionId:session.viewedSnapshot.operationId};
    exporting = true; syncMeta();
    try {
      const result = await onExport(requested);
      if (!disposed) writeMessage(result?.message || (result?.ok ? `Version ${requested.version} exportée. Le film reste à monter.` : 'L’export n’a pas pu être préparé.'), result?.ok ? 'success' : 'error');
    } catch (error) { if (!disposed) writeMessage(error?.message || 'L’export a échoué.', 'error'); }
    finally { exporting = false; if (!disposed) syncMeta(); }
  }

  function onClick(event) {
    const element = event.target?.closest?.('button, a');
    if (!element || !view.contains(element) || element.disabled) return;
    if (element.hasAttribute('data-action')) return; // The reference Studio belongs to the application router.
    const beat = element.getAttribute('data-ps-beat');
    if (beat) { selectBeat(beat); return; }
    if (element.hasAttribute('data-ps-library-open')) { captureFields(); q('[data-ps-library]').hidden = false; updateLibrary(); return; }
    if (element.hasAttribute('data-ps-library-close')) { q('[data-ps-library]').hidden = true; return; }
    if (element.hasAttribute('data-ps-choose-source')) { selectSource(element.getAttribute('data-ps-choose-source')); return; }
    if (element.hasAttribute('data-ps-preview-source')) { captureFields(); showPreview(element.getAttribute('data-ps-preview-source')); return; }
    if (element.hasAttribute('data-ps-preview-close')) { showPreview(null); return; }
    if (element.hasAttribute('data-ps-clear-source')) { removeSource(); return; }
    if (element.hasAttribute('data-ps-new')) { openNew(); return; }
    if (element.hasAttribute('data-ps-resume')) { resumeVersion(); return; }
    if (element.hasAttribute('data-ps-rebase')) { rebaseDraft(); return; }
    if (element.hasAttribute('data-ps-load-plan')) { loadPlan(element.getAttribute('data-ps-load-plan')); return; }
    if (element.hasAttribute('data-ps-export')) { exportVersion(); }
  }

  function onInput(event) {
    const element = event.target;
    if (element?.hasAttribute?.('data-ps-search')) { search = element.value; updateLibrary(); return; }
    if (!element?.name || !element.hasAttribute('data-ps-editable') || session.historical || targetMissing) return;
    captureFields(); changed();
    if (element.name === 'duration' || element.name === 'format' || element.name === 'beatIn' || element.name === 'beatOut' || element.name === 'sourceRelation') updateBoard();
    if (element.name === 'sourceRelation') q('[data-ps-relation-note]').textContent = element.value === 'project' ? 'Vous déclarez que ce média documente ce dossier. Le Studio ne vérifie pas automatiquement l’identité ou la dimension de la pièce.' : 'Une référence guide le style ou le geste ; elle ne prouve pas que cette pièce appartient à ce dossier.';
  }

  function onChange(event) {
    if (event.target?.hasAttribute?.('data-ps-plan-picker')) { loadPlan(event.target.value); return; }
    if (event.target?.hasAttribute?.('data-ps-history')) { viewVersion(event.target.value); return; }
    // Selects and radios also work when a host dispatches only `change`.
    if (event.target?.tagName === 'SELECT' || event.target?.type === 'radio') onInput(event);
  }

  function onSubmit(event) {
    if (event.target !== form) return;
    event.preventDefault(); event.stopPropagation(); saveVersion();
  }

  function onMediaError(event) {
    if (!event.target?.matches?.('video[data-ps-preview-video]')) return;
    const status = q('[data-ps-preview-status]');
    if (status) status.textContent = 'Cet aperçu ne peut pas être lu. Le plan et les repères de l’original sont conservés.';
  }

  function setMotion(value) {
    motionEnabled = !!value; view.dataset.motion = motionEnabled ? 'on' : 'off';
    if (!motionEnabled) pausePreview();
  }

  function refreshContext({project:updatedProject, activeProjectId:updatedActiveId, archive:updatedArchive} = {}) {
    if (disposed) return;
    // `project` is always the captured target, even if the global selection moved.
    if (updatedProject === null) targetMissing = true;
    else if (updatedProject?.id === targetId) { target = updatedProject; targetMissing = false; }
    if (typeof updatedActiveId === 'string') activeId = updatedActiveId;
    if (updatedArchive !== undefined) {
      const nextSources = archiveMap(updatedArchive);
      const changedSources = JSON.stringify([...nextSources.values()]) !== JSON.stringify([...sources.values()]);
      sources = nextSources;
      if (changedSources) {
        updateBoard(); updateLibrary();
        if (previewId) showPreview(previewId);
      }
    }
    // Never replace form fields, their baseline, or their expected revision here.
    syncMeta();
  }

  function dispose() {
    if (disposed) return;
    disposed = true; pausePreview();
    view.removeEventListener('click', onClick);
    view.removeEventListener('input', onInput);
    view.removeEventListener('change', onChange);
    view.removeEventListener('submit', onSubmit);
    view.removeEventListener('error', onMediaError, true);
    drafts.clear();
  }

  view.addEventListener('click', onClick);
  view.addEventListener('input', onInput);
  view.addEventListener('change', onChange);
  view.addEventListener('submit', onSubmit);
  view.addEventListener('error', onMediaError, true);
  syncFields(); setMotion(motionEnabled);
  return {dispose, setMotion, refreshContext, prepareSeries};
}
