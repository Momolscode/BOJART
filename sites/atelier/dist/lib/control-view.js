/** Rendering only. Decisions and action authority belong to the control plane. */
const GLYPHS={creation:'cube',preparation:'layers',production:'printer',contenus:'film',commerce:'chart',ressources:'settings',systeme:'screens',robotique:'spark'};
const DECISION_STATES={ready:'ACTION DISPONIBLE',needs_input:'À COMPLÉTER',blocked:'DÉCISION REQUISE',pending:'VÉRIFICATION EN COURS',checking:'LECTURE EN COURS',complete:'PREUVE DISPONIBLE',not_connected:'À RACCORDER'};

function operationAttributes(operation,contextProjectId,esc){
  return `data-operation="${esc(operation.id)}" data-operation-project="${esc(operation.projectId||'')}" data-mode="${esc(operation.mode)}" data-operation-context="${esc(contextProjectId)}" data-operation-job="${esc(operation.jobId||'')}" data-operation-status="${esc(operation.expectedStatus||'')}"`;
}

function decisionAction(action,{operations,projectId,esc,icon,primary=false}){
  if(!action)return '';
  const operation=action.operationId?operations.find(item=>item.id===action.operationId):null;
  const label=action.label||operation?.label||'Voir les opérations';
  const className=`control-decision-action${primary?' is-primary':''}`;
  if(action.operationId&&!operation)return `<button type="button" class="${className}" disabled title="Cette opération doit être actualisée depuis le projet actif.">${esc(label)} ${icon('info')}</button>`;
  const attributes=operation?operationAttributes(operation,projectId,esc):action.action?`data-action="${esc(action.action)}" data-mission-project="${esc(projectId)}" data-project-id="${esc(projectId)}"${action.pieceId?` data-piece-id="${esc(action.pieceId)}"`:''}`:'';
  return `<button type="button" class="${className}" ${attributes}${attributes?'':' disabled'}>${esc(label)} ${icon(primary?'arrow':'arrowUp')}</button>`;
}

/**
 * decision is an optional evidence snapshot supplied by the caller:
 * {title,reason,targetLabel,evidenceLabel,state,modeLabel,facts,primary,secondary}.
 * Actions use {label,operationId} or {label,action}; facts use {label,value,detail,state}.
 * Referenced asset IDs are shown as metadata and never promoted to measured proof.
 */
export function renderControlStage({project,domains,operations,receipt,picker='',displaySummary='',visualDock='',decision=null,esc,icon}){
  const pieces=Array.isArray(project.pieces)?project.pieces:[];
  const files=pieces.filter(piece=>piece.assetId).length;
  const fallback={
    title:'Examiner la préparation',
    reason:'Relire les fichiers du dossier et comparer leurs volumes au parc déclaré depuis l’établi.',
    targetLabel:project.name,
    evidenceLabel:'Les références de fichiers ne confirment pas encore leurs mesures ni leur disponibilité.',
    state:'needs_input',
    modeLabel:'Préparation locale · parc simulé',
    primary:{label:'Ouvrir la préparation',operationId:'preparation.declared_volume'},
    secondary:[{label:'Voir le plan de mission',action:'master-mission'}],
    facts:[]
  };
  const current={...fallback,...(decision||{})};
  const state=Object.hasOwn(DECISION_STATES,current.state)?current.state:'needs_input';
  const facts=Array.isArray(current.facts)?current.facts.slice(0,3):[];
  const secondary=Array.isArray(current.secondary)?current.secondary.slice(0,2):[];
  const actionContext={operations,projectId:project.id,esc,icon};
  const reference=project.media?`<figure class="control-project-image"><img src="./assets/${esc(project.media)}" alt="Référence artistique du dossier ${esc(project.name)}, distincte du modèle 3D"><figcaption>Référence visuelle · hors STL</figcaption></figure>`:`<div class="control-project-empty">${icon('cube')}<p>Aucune référence visuelle dans ce dossier.</p></div>`;
  return `<section class="control-stage control-workstation" aria-label="Jarvis, poste de décision du projet actif">
    <header class="control-stage-top">
      <div class="control-brand"><img src="./assets/logo.webp" alt="Emblème original BOJ.ART" width="38" height="44"><div><strong>BOJ.ART</strong><span>LA TOUR DE CONTRÔLE</span></div></div>
      ${displaySummary}
      <div class="control-project-picker">${picker}</div>
      <button type="button" class="control-screen-settings" data-action="screens" aria-label="Configurer les trois moniteurs">${icon('screens')}<span>Les écrans</span></button>
    </header>

    <aside class="control-project" aria-label="Dossier actif">
      <p class="eyebrow">LE DOSSIER ACTIF</p>
      <h2>${esc(project.name)}</h2>
      <p class="control-project-kind">${esc(project.kind||'Création sur mesure')} · ${esc(project.quantity)} exemplaire${project.quantity>1?'s':''}</p>
      ${project.status?`<p class="control-project-status">${esc(project.status)}</p>`:''}
      ${reference}
      <div class="control-project-metrics"><div><strong>${String(pieces.length).padStart(2,'0')}</strong><span>pièces du dossier</span></div><div><strong>${files}<small> / ${pieces.length}</small></strong><span>fichiers référencés</span></div></div>
      <button type="button" class="control-record-link" data-action="project-edit" data-project-id="${esc(project.id)}">Voir le brief ${icon('arrowUp')}</button>
    </aside>

    <section class="control-decision" data-decision-state="${state}" aria-labelledby="control-decision-title">
      <div class="control-decision-heading"><p class="eyebrow">LA PROCHAINE DÉCISION</p><span class="control-decision-state">${DECISION_STATES[state]}</span></div>
      <div class="control-decision-main">
        <p class="control-decision-target">${icon('layers')}<span>${esc(current.targetLabel||project.name)}</span></p>
        <h2 id="control-decision-title">${esc(current.title||fallback.title)}</h2>
        <p class="control-decision-reason">${esc(current.reason||fallback.reason)}</p>
      </div>
      ${facts.length?`<dl class="control-decision-facts">${facts.map(fact=>`<div${fact.state?` data-fact-state="${esc(fact.state)}"`:''}><dt>${esc(fact.label||'État')}</dt><dd>${esc(fact.value??'—')}${fact.detail?`<small>${esc(fact.detail)}</small>`:''}</dd></div>`).join('')}</dl>`:''}
      ${current.evidenceLabel?`<p class="control-decision-evidence">${icon('info')}<span>${esc(current.evidenceLabel)}</span></p>`:''}
      <div class="control-decision-actions">${decisionAction(current.primary,{...actionContext,primary:true})}${secondary.map(action=>decisionAction(action,actionContext)).join('')}</div>
      <p class="control-mode-label">${esc(current.modeLabel||fallback.modeLabel)}</p>
    </section>

    <aside class="control-tools" aria-label="Jarvis et régie des trois écrans">
      <div class="control-orbit">
        <div class="motion-canvas" data-motion-stage="jarvis" aria-hidden="true"></div>
        <div class="control-orbit-label"><span>LE POSTE CENTRAL</span><h2>JARVIS<span>.</span></h2></div>
      </div>
      <p class="control-orbit-note">Visuel d’interface · aucune télémétrie</p>
      ${visualDock}
      <button type="button" class="control-decisions-entry" data-action="decisions" data-project-id="${esc(project.id)}">${icon('spark')}<span>Le bureau des décisions</span>${icon('arrowUp')}</button>
      <details class="control-domains"><summary><span>Les domaines de l’atelier</span><strong>${String(domains.length).padStart(2,'0')}</strong>${icon('grid')}</summary><div class="control-domain-list">${domains.map(domain=>{
        const available=operations.filter(operation=>operation.domain===domain.id&&operation.available).length;
        return `<button type="button" data-control-domain="${esc(domain.id)}"><span>${icon(GLYPHS[domain.id]||'grid')}</span><strong>${esc(domain.label)}</strong><small>${available} accès</small>${icon('arrowUp')}</button>`;
      }).join('')}</div><button type="button" class="control-all" data-action="control">Toutes les opérations ${icon('arrow')}</button></details>
    </aside>

    <div class="control-intention">
      <form id="wall-command-form"><label for="wall-command-input">DONNER UNE INTENTION À JARVIS</label><div class="wall-command-field"><span class="control-input-mark" aria-hidden="true">${icon('spark')}</span><input id="wall-command-input" placeholder="Jarvis, prépare les pièces de ce projet…" autocomplete="off" maxlength="250" aria-describedby="control-command-hint"><button type="submit" aria-label="Traiter l’intention dans le projet actif">${icon('arrow')}</button></div><p id="control-command-hint" class="control-command-hint">Commande écrite locale · voix à raccorder.</p><div class="quick-intents"><button type="button" data-quick-command="Orchestre mon projet">Examiner la mission ${icon('arrowUp')}</button><button type="button" data-action="preparation">Préparer les pièces</button><button type="button" data-action="visual-desk">Piloter les visuels</button><button type="button" data-action="project-studio">Contenus du projet</button></div></form>
      <div class="control-feedback"><span class="eyebrow">LE DERNIER RETOUR</span><div id="wall-command-receipt" role="status" aria-live="polite">${esc(receipt||'Prêt pour une intention écrite. Parc simulé ; voix locale et équipements à raccorder.')}</div><button type="button" data-action="journal">Ouvrir le journal ${icon('arrow')}</button></div>
    </div>
  </section>`;
}

export function renderControlHub({domains,operations,selected='all',contextProjectId='',esc,icon}){
  const labels={local:'DISPONIBLE',simulation:'SIMULATION',unconnected:'À RACCORDER'};
  const local=operations.filter(operation=>operation.mode==='local'&&operation.available).length;
  const simulation=operations.filter(operation=>operation.mode==='simulation'&&operation.available).length;
  const disconnected=operations.filter(operation=>operation.mode==='unconnected').length;
  const shown=selected==='all'?operations:operations.filter(operation=>operation.domain===selected);
  return `<section class="control-hub panel"><div class="control-hub-head"><div><p class="eyebrow">LE CHAMP D’ACTION DE JARVIS</p><h2>TOUT L’ATELIER.<br><em>UNE MÊME INTENTION.</em></h2></div><button type="button" class="button button-red" data-action="master-mission">${icon('layers')} Mission complète</button></div><div class="control-summary"><span><strong>${local}</strong> actions locales</span><span><strong>${simulation}</strong> actions simulées</span><span><strong>${disconnected}</strong> raccordements prévus</span></div><div class="domain-grid" role="group" aria-label="Domaines contrôlés par Jarvis">${domains.map(domain=>{const ops=operations.filter(operation=>operation.domain===domain.id),n=ops.filter(operation=>operation.available&&operation.mode!=='unconnected').length;return `<button type="button" class="domain-card ${selected===domain.id?'active':''}" data-control-domain="${esc(domain.id)}" aria-pressed="${selected===domain.id}"><span class="domain-symbol">${icon(GLYPHS[domain.id]||'grid')}</span><strong>${esc(domain.label)}</strong><span>${n?`${n} accès disponible${n>1?'s':''}`:'Raccordement à préparer'}</span><i></i></button>`;}).join('')}</div><div class="operations-heading"><h3>${selected==='all'?'Toutes les opérations':esc(domains.find(domain=>domain.id===selected)?.label||selected)}</h3><button type="button" data-control-domain="all" aria-pressed="${selected==='all'}">Tout afficher ${icon('grid')}</button></div><div class="operations-list">${shown.map(operation=>`<button type="button" class="operation-row" ${operationAttributes(operation,contextProjectId,esc)}><span class="operation-icon">${icon(GLYPHS[operation.domain]||'grid')}</span><div><strong>${esc(operation.label)}</strong><small>${esc(operation.requirement||'Accès direct depuis Jarvis.')}</small></div><span class="operation-mode ${esc(operation.mode)}">${labels[operation.mode]||'À PRÉPARER'}</span>${icon('arrowUp')}</button>`).join('')}</div></section>`;
}

export function renderMasterMission({mission,domains,esc,icon}){
  const steps=mission.steps||mission.nodes||[];
  const projectId=mission.project?.id||mission.projectId||'';
  const labels={ready:'ACTION DISPONIBLE',needs_input:'À COMPLÉTER',not_connected:'À RACCORDER',complete:'PREUVE PRÉSENTE',blocked:'À EXAMINER',pending:'VÉRIFICATION EN COURS'};
  return `<div class="master-intro"><span class="tag tag-red">JARVIS / MISSION TRANSVERSALE</span><h3>${esc(mission.projectName||mission.project?.name||'Le projet')}</h3><p>Création, fabrication, contenu et commerce dans un même parcours.</p></div><div class="master-top-actions"><button type="button" class="button button-red button-block" data-action="orchestrate" data-mission-project="${esc(projectId)}" data-project-id="${esc(projectId)}">${icon('spark')} Examiner le plan de mission</button><p>Relire les preuves du dossier et repérer la prochaine étape. Les raccordements physiques et externes gardent leur état déclaré.</p></div><div class="master-path">${steps.map((step,index)=>{
    const action=typeof step.action==='string'?step.action:step.action?.action;
    const actionLabel=step.actionLabel||step.action?.label||'Ouvrir cette étape';
    return `<div class="master-step ${esc(step.status)}"><span class="master-number">${String(index+1).padStart(2,'0')}</span><div><small>${esc(domains.find(domain=>domain.id===step.domain)?.label||step.domain||'Le projet')}</small><strong>${esc(step.label||step.title||step.id)}</strong><p>${esc(step.reason||step.requirement||step.description||'')}</p><span class="operation-mode ${step.status==='not_connected'?'unconnected':'local'}">${labels[step.status]||esc(step.status)}</span>${action?`<button type="button" class="button master-step-action" data-action="${esc(action)}" data-mission-project="${esc(projectId)}" data-project-id="${esc(projectId)}">${esc(actionLabel)} ${icon('arrowUp')}</button>`:''}</div></div>`;
  }).join('')}</div><div class="form-actions"><button type="button" class="button" data-action="export-master">${icon('save')} Exporter la mission complète</button><button type="button" class="button" data-action="control">${icon('grid')} Toutes les opérations</button></div><p class="micro-copy form-section">Un plan central décrit les étapes et leurs dépendances. Une fonction à raccorder ne peut pas être déclarée exécutée par l’interface.</p>`;
}
