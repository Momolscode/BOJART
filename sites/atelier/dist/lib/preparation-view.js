import {PREPARATION_ORIENTATIONS} from './preparation.js';

/** A visual workbench for measured STL envelopes and declared machine volumes.
 * Files are checked in sequence. No mesh, printer profile or assignment is invented.
 * The application owns file import, export and navigation to the machine record.
 */
const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=value=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('fr-FR',{maximumFractionDigits:2}):'—';
const dimensions=value=>Array.isArray(value)&&value.length===3?value.map(number).join(' × ')+' mm':'À mesurer';
const copy=value=>JSON.parse(JSON.stringify(value));
const technology=value=>value==='resin'?'Résine UV':value==='fdm'?'FDM':'Procédé à renseigner';
const fileLabels={unreferenced:'Sans STL',unchecked:'À vérifier',missing:'Fichier absent',invalid:'Fichier invalide',measured:'STL mesuré'};
const shortStatus={not_declared:'Fiche à déclarer',technology_unknown:'Procédé à préciser',technology_mismatch:'Autre procédé',volume_missing:'Volume absent',file_unchecked:'STL à vérifier',file_missing:'STL absent',file_invalid:'STL invalide',non_volumetric:'Pièce sans volume',fits:'Volume compatible',exceeds:'Hors volume'};
const issueActions={fleet:'Compléter la fiche de la machine sélectionnée.',import:'Associer ou remplacer le STL de cette pièce.',inspect:'Examiner la pièce et ses exigences de fabrication.'};
const glyph=name=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${({cube:'<path d="m12 2 9 5v10l-9 5-9-5V7l9-5Z"/><path d="m3 7 9 5 9-5M12 12v10"/>',upload:'<path d="M12 16V3m-5 5 5-5 5 5M3 15v5a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-5"/>',arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',save:'<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',rotate:'<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>',printer:'<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/>'})[name]||''}</svg>`;

function firstSelection(project,machines,report){
  const piece=(project?.pieces||[]).find(item=>item.assetId)||(project?.pieces||[])[0]||null;
  const declared=report?.machines?.find(machine=>machine.declared&&machine.record?.technology===piece?.tech)||report?.machines?.find(machine=>machine.declared);
  const machine=declared||machines?.find(item=>item.id===piece?.machine)||machines?.[0]||null;
  const assessment=report?.pieces?.find(item=>item.id===piece?.id)?.assessments?.find(item=>item.machineId===machine?.id);
  return{pieceId:piece?.id||null,machineId:machine?.id||null,orientationId:assessment?.bestOrientationId||'xyz'};
}
function pieceRows(report,selected,esc=escapeHtml){
  return(report?.pieces||[]).map((piece,index)=>`<button type="button" class="pw-piece${piece.id===selected?' is-selected':''}" data-prep-piece="${esc(piece.id)}" aria-pressed="${piece.id===selected}"><span class="pw-piece-index">${String(index+1).padStart(2,'0')}</span><span class="pw-piece-text"><strong>${esc(piece.name)}</strong><small>${technology(piece.tech)}</small><span class="pw-file-state" data-status="${esc(piece.file.status)}"><i></i>${esc(fileLabels[piece.file.status]||'À vérifier')}</span></span></button>`).join('')||'<div class="pw-rail-empty"><strong>Aucune pièce.</strong><p>Ajoutez un STL au dossier pour commencer sa préparation.</p></div>';
}
function matrix(report,selection,esc=escapeHtml){
  const machines=report?.machines||[];
  if(!report?.pieces?.length)return'<div class="pw-matrix-empty">Le rapport apparaîtra ici lorsque le dossier contiendra une pièce.</div>';
  return`<div class="pw-matrix-scroll" tabindex="0" role="region" aria-label="Comparaison des pièces et des machines"><table class="pw-matrix"><caption class="pw-sr-only">Compatibilité du volume brut, sans supports ni qualification de fabrication.</caption><thead><tr><th scope="col">Pièce / machine</th>${machines.map(machine=>`<th scope="col"><span>${esc(machine.id)}</span><small>${machine.declared?esc(technology(machine.record?.technology)):'À déclarer'}</small></th>`).join('')}</tr></thead><tbody>${report.pieces.map(piece=>`<tr><th scope="row"><strong>${esc(piece.name)}</strong><small>${esc(fileLabels[piece.file.status]||'À vérifier')}</small></th>${machines.map(machine=>{const assessment=piece.assessments.find(item=>item.machineId===machine.id);const selected=piece.id===selection.pieceId&&machine.id===selection.machineId;return`<td><button type="button" data-prep-cell-piece="${esc(piece.id)}" data-prep-cell-machine="${esc(machine.id)}" class="pw-matrix-cell${selected?' is-selected':''}" data-status="${esc(assessment?.status||'not_declared')}" aria-pressed="${selected}" aria-label="${esc(piece.name)}, ${esc(machine.id)} : ${esc(assessment?.label||'À renseigner')}"><i></i><span>${esc(shortStatus[assessment?.status]||assessment?.label||'À renseigner')}</span>${assessment?.fitOrientationIds?.length?`<small>${assessment.fitOrientationIds.length} orientation${assessment.fitOrientationIds.length>1?'s':''}</small>`:''}</button></td>`;}).join('')}</tr>`).join('')}</tbody></table></div>`;
}

export function renderPreparationView({project,machines,report,esc=escapeHtml,icon=glyph}){
  const selection=firstSelection(project,machines,report);
  return`<section class="preparation-workbench" data-preparation-workbench data-project-id="${esc(project.id)}" data-prep-state="checking">
    <div class="pw-masthead"><div class="pw-brand">BOJ<span>.</span>ART <small>JARVIS / PRÉPARATION</small></div><span class="pw-scope"><i></i> ÉTUDE DU VOLUME BRUT</span></div>
    <header class="pw-hero"><div><p class="pw-kicker">DE LA GÉOMÉTRIE AU PLATEAU</p><h2>CHAQUE PIÈCE.<br><em>À SA PLACE.</em></h2></div><div class="pw-project"><span>LE DOSSIER CIBLE</span><strong data-prep-project-name>${esc(project.name)}</strong><p>Inspecter le fichier. Comparer les machines. Comprendre ce qui tient, avant de préparer les supports et le tranchage.</p><div class="pw-hero-metrics"><span><b data-prep-metric="measured">${report?.summary?.measuredFiles||0}</b><small>STL<br>MESURÉS</small></span><span><b data-prep-metric="declared">${report?.summary?.declaredMachines||0}</b><small>MACHINES<br>DÉCLARÉES</small></span><span><b data-prep-metric="fit">${report?.summary?.piecesWithEnvelopeFit||0}</b><small>PIÈCES DANS<br>UN VOLUME</small></span></div></div></header>
    <div class="pw-context" data-prep-context role="status" hidden></div>
    <div class="pw-inspection-bar"><div><span class="pw-kicker">LE FICHIER FAIT FOI</span><p data-prep-audit role="status">Vérification des STL accessibles sur ce poste…</p></div><button type="button" class="pw-text-button" data-prep-action="decisions">${icon('spark')} Conseils & Jev</button><button type="button" class="pw-text-button" data-prep-action="recheck">${icon('rotate')} Relire les fichiers</button></div>
    <div class="pw-layout">
      <aside class="pw-piece-rail"><div class="pw-rail-heading"><span class="pw-kicker">LES PIÈCES</span><b data-prep-piece-count>${project.pieces?.length||0}</b></div><div class="pw-pieces" data-prep-pieces aria-label="Choisir une pièce">${pieceRows(report,selection.pieceId,esc)}</div></aside>
      <section class="pw-stage" aria-label="Inspection 3D de la pièce sélectionnée"><div class="pw-stage-heading"><div><span class="pw-kicker">LA PIÈCE SÉLECTIONNÉE</span><h3 data-prep-piece-name>Chargement du dossier</h3></div><span class="pw-stage-tag" data-prep-model-tag>STL À VÉRIFIER</span></div><div class="pw-viewport" data-prep-viewport><div class="pw-viewport-host" data-prep-canvas></div><div class="pw-stage-corners" aria-hidden="true"><i></i><i></i><i></i><i></i></div><div class="pw-empty" data-prep-empty><span class="pw-empty-symbol">${icon('cube')}</span><h4 data-prep-empty-title>Le fichier, à l’échelle.</h4><p data-prep-empty-copy>Le modèle 3D apparaîtra ici après la lecture de son STL.</p></div><div class="pw-axis-key" aria-label="Axes de la machine"><span><i>X</i> LARGEUR</span><span><i>Y</i> PROFONDEUR</span><span><i>Z</i> HAUTEUR</span></div><div class="pw-view-controls"><button type="button" data-prep-action="reset" aria-label="Recentrer la pièce et le volume">${icon('rotate')}</button><button type="button" data-prep-action="wire" aria-pressed="false">Maillage</button></div></div><div class="pw-stage-caption"><span data-prep-view-status role="status">Aucun modèle de remplacement.</span><span class="pw-scale-tag">MM <small>MESURES</small></span></div><div class="pw-source-details" data-prep-source-details></div><div class="pw-import-row"><label for="prep-import-unit">Unité du prochain STL<select id="prep-import-unit" data-prep-import-unit><option value="mm">Millimètre</option><option value="inch">Pouce</option></select></label><button type="button" class="button button-red" data-prep-action="import">${icon('upload')} <span data-prep-import-label>Associer un STL</span></button></div><p class="pw-unit-note">Le format STL ne définit pas d’unité. Ce choix s’applique au prochain fichier associé à cette pièce.</p></section>
      <aside class="pw-placement"><div class="pw-placement-heading"><span class="pw-kicker">LE VOLUME CIBLE</span><h3>LA MACHINE.</h3></div><label class="pw-field" for="prep-machine-id">Comparer avec<select id="prep-machine-id" data-prep-machine>${(report?.machines||machines||[]).map(machine=>`<option value="${esc(machine.id)}" ${machine.id===selection.machineId?'selected':''}>${esc(machine.id)}${machine.declared&&machine.record?.model?' · '+esc(machine.record.model):''}</option>`).join('')}</select></label><p class="pw-machine-note" data-prep-machine-note></p><button type="button" class="pw-text-button" data-prep-action="fleet">${icon('printer')} <span data-prep-fleet-label>Fiche de la machine</span> ${icon('arrow')}</button><div class="pw-placement-result" data-prep-result></div><div class="pw-orientation-heading"><span>ORIENTATION ORTHOGONALE</span><small data-prep-orientation-count></small></div><div class="pw-orientations" data-prep-orientations role="group" aria-label="Choisir une orientation orthogonale"></div><div class="pw-axis-report" data-prep-axes></div><p class="pw-placement-note">Pièce centrée et posée à Z = 0. La marge brute ne prévoit ni supports, ni bordure, ni drainage.</p></aside>
    </div>
    <section class="pw-checks"><div><span class="pw-kicker">LE POINT DE PRÉPARATION</span><h3>CE QU’IL RESTE<br><em>À PRÉPARER.</em></h3></div><div class="pw-issues" data-prep-issues></div></section>
    <section class="pw-matrix-section"><header><div><span class="pw-kicker">LE DOSSIER, D’UN REGARD</span><h3>PIÈCES × MACHINES.</h3></div><p>Sélectionnez une case pour inspecter ce couple.<br>Le rapport compare les six orientations à 90°.</p></header><div data-prep-matrix>${matrix(report,selection,esc)}</div><div class="pw-matrix-legend"><span><i data-tone="fit"></i>Volume brut compatible</span><span><i data-tone="exceeds"></i>Dépassement</span><span><i data-tone="unknown"></i>Information à compléter</span></div></section>
    <footer class="pw-footer"><div><strong>Un rapport de préparation, lié à ses mesures.</strong><p>Les choix ci-dessus restent un essai de placement. Aucun fichier n’est redimensionné, tranché ou envoyé à une machine.</p><span data-prep-export-status role="status"></span></div><button type="button" class="button button-red" data-prep-action="export" disabled>${icon('save')} Exporter le rapport</button></footer>
  </section>`;
}

function geometryKey(project){return JSON.stringify([project?.id,(project?.pieces||[]).map(piece=>[piece.id,piece.revision,piece.assetId,piece.assetSha256,piece.unit,piece.tech,piece.dims])]);}
function contextKey(project,machines){return JSON.stringify([project?.id,project?.name,project?.revision,project?.quantity,project?.height,(project?.pieces||[]).map(piece=>[piece.id,piece.name,piece.revision,piece.assetId,piece.assetSha256,piece.unit,piece.tech,piece.dims]),(machines||[]).map(machine=>[machine.id,machine.registry])]);}

export function mountPreparationView(root,{project,machines,report,createViewport,readAsset,inspectSTL,analyze,onExport=()=>({ok:false}),onImport=()=>{},onOpenFleet=()=>{},onReport=()=>{},onDecision=()=>{},motion=true}){
  const host=root.matches?.('[data-preparation-workbench]')?root:root.querySelector('[data-preparation-workbench]');
  if(!host)throw new Error('L’établi de préparation est absent.');
  const $=query=>host.querySelector(query),$$=query=>[...host.querySelectorAll(query)];
  const projectId=project.id;
  let currentProject=copy(project),currentMachines=copy(machines),currentReport=report;
  let selection=firstSelection(currentProject,currentMachines,currentReport),activeProjectId=projectId;
  let disposed=false,removed=false,checking=false,exporting=false,wire=false,viewport=null,viewportPromise=null;
  let auditEpoch=0,previewEpoch=0,version=0,auditQueue=Promise.resolve(),previewQueue=Promise.resolve();
  let evidence=[],auditMessage='',renderError='',lastContext=contextKey(currentProject,currentMachines),lastGeometry=geometryKey(currentProject),pendingSelection=null;
  const importUnits=new Map();
  const text=(selector,value)=>{const node=$(selector);if(node)node.textContent=value;};
  const selectedPiece=()=>currentReport?.pieces?.find(piece=>piece.id===selection.pieceId)||null;
  const selectedMachine=()=>currentReport?.machines?.find(machine=>machine.id===selection.machineId)||null;
  const selectedAssessment=()=>selectedPiece()?.assessments?.find(item=>item.machineId===selection.machineId)||null;

  function normalizeSelection(preferBest=false){
    if(!currentReport?.pieces?.some(piece=>piece.id===selection.pieceId))selection.pieceId=currentReport?.pieces?.[0]?.id||null;
    if(!currentReport?.machines?.some(machine=>machine.id===selection.machineId))selection.machineId=currentReport?.machines?.[0]?.id||null;
    const assessment=selectedAssessment();
    if(preferBest||!assessment?.orientations?.some(orientation=>orientation.id===selection.orientationId))selection.orientationId=assessment?.bestOrientationId||'xyz';
  }
  function recompute(){
    if(removed)return;
    try{currentReport=analyze(currentProject,currentMachines,evidence);renderError='';normalizeSelection();}
    catch(error){renderError=String(error?.message||'Le rapport n’a pas pu être calculé.');}
  }
  function paintContext(){
    const node=$('[data-prep-context]');
    const messages=[];
    if(removed)messages.push('Ce dossier n’est plus disponible. Rouvrez la préparation depuis un dossier existant.');
    else if(activeProjectId&&activeProjectId!==projectId)messages.push(`Un autre écran consulte un autre dossier. Cet établi reste lié à « ${currentProject.name} ».`);
    if(renderError)messages.push(renderError);
    node.hidden=!messages.length;node.textContent=messages.join(' ');
  }
  function paint(){
    if(disposed)return;
    if(pendingSelection&&currentReport?.pieces?.some(piece=>piece.id===pendingSelection.pieceId)){
      selection.pieceId=pendingSelection.pieceId;
      if(currentReport.machines.some(machine=>machine.id===pendingSelection.machineId))selection.machineId=pendingSelection.machineId;
      const assessment=selectedAssessment();
      if(assessment?.orientations?.some(item=>item.id===pendingSelection.orientationId)){selection.orientationId=pendingSelection.orientationId;pendingSelection=null;}
      else if(!pendingSelection.orientationId){normalizeSelection(true);pendingSelection=null;}
    }
    const focused=host.ownerDocument.activeElement;
    const focusKey=host.contains(focused)?focused.dataset:null;
    const focusRestore=focusKey?.prepPiece?{kind:'piece',piece:focusKey.prepPiece}:focusKey?.prepOrientation?{kind:'orientation',orientation:focusKey.prepOrientation}:focusKey?.prepCellPiece?{kind:'cell',piece:focusKey.prepCellPiece,machine:focusKey.prepCellMachine}:null;
    const matrixScroll=$('.pw-matrix-scroll')?.scrollLeft||0;
    const evidenceOpen=$('.pw-file-evidence')?.open||false;
    paintContext();
    text('[data-prep-project-name]',currentProject.name);
    const summary=currentReport?.summary||{};
    text('[data-prep-metric="measured"]',summary.measuredFiles||0);text('[data-prep-metric="declared"]',summary.declaredMachines||0);text('[data-prep-metric="fit"]',summary.piecesWithEnvelopeFit||0);
    text('[data-prep-piece-count]',currentReport?.pieces?.length||0);
    $('[data-prep-pieces]').innerHTML=pieceRows(currentReport,selection.pieceId);
    text('[data-prep-audit]',auditMessage||'Les fichiers sont vérifiés dans ce navigateur.');
    host.dataset.prepState=removed?'unavailable':checking?'checking':renderError?'error':'ready';
    const piece=selectedPiece(),machine=selectedMachine(),assessment=selectedAssessment();
    const orientation=assessment?.orientations?.find(item=>item.id===selection.orientationId)||null;
    const canonicalPiece=currentProject.pieces?.find(item=>item.id===selection.pieceId)||null;
    text('[data-prep-piece-name]',piece?.name||'Aucune pièce');
    text('[data-prep-model-tag]',piece?.file?.status==='measured'?'FICHIER STL RÉEL':fileLabels[piece?.file?.status]?.toUpperCase()||'AUCUN FICHIER');
    $('[data-prep-model-tag]').dataset.status=piece?.file?.status||'unreferenced';
    const source=piece?.file;
    const measuredTime=typeof source?.checkedAt==='number'&&Number.isFinite(source.checkedAt)?'fichier relu à '+new Date(source.checkedAt).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'heure de lecture non renseignée';
    $('[data-prep-source-details]').innerHTML=piece?`<div><span>${source?.status==='measured'?'MESURE DU STL':'DIMENSIONS DU DOSSIER'}</span><strong>${dimensions(source?.status==='measured'?piece.dimensionsMm:piece.storedDimensionsMm)}</strong></div><div><span>${source?.status==='measured'?'MAILLAGE':'LE FICHIER'}</span><strong>${source?.status==='measured'?number(source.triangles)+' triangles':escapeHtml(fileLabels[source?.status]||'À vérifier')}</strong></div><p>${source?.status==='measured'?`Unité interprétée : ${piece.unit==='inch'?'pouce → mm':'millimètre'} · ${measuredTime}.`:'Les dimensions du dossier ne constituent pas une mesure du STL.'}${piece.measurementsMatchRecord===false?' La mesure relue diffère des dimensions conservées dans le dossier.':''}</p>${source?.status==='measured'?`<details class="pw-file-evidence"><summary>Empreinte du fichier et origine des mesures</summary><p>${source.sha256?`SHA-256 : <code>${escapeHtml(source.sha256)}</code>`:'SHA-256 indisponible dans cet environnement : aucune empreinte calculée.'}</p><p>${number(source.byteLength)} octets · révision de la pièce ${piece.revision} · les sommets du fichier définissent les mesures affichées.</p></details>`:''}`:'<p>Aucune pièce dans ce dossier.</p>';
    if(evidenceOpen&&$('.pw-file-evidence'))$('.pw-file-evidence').open=true;
    const unit=importUnits.get(selection.pieceId)||(canonicalPiece?.unit==='inch'?'inch':'mm');
    $('[data-prep-import-unit]').value=unit;
    $('[data-prep-import-unit]').disabled=removed||!canonicalPiece;
    $('[data-prep-action="import"]').disabled=removed||!canonicalPiece;
    text('[data-prep-import-label]',canonicalPiece?.assetId?'Remplacer le STL':'Associer un STL');
    const machineSelect=$('[data-prep-machine]');
    machineSelect.innerHTML=(currentReport?.machines||[]).map(item=>`<option value="${escapeHtml(item.id)}">${escapeHtml(item.id)}${item.declared&&item.record?.model?' · '+escapeHtml(item.record.model):''}</option>`).join('');
    machineSelect.value=selection.machineId||'';machineSelect.disabled=removed||!currentReport?.machines?.length;
    const volume=machine?.declared?machine.record?.usableVolumeMm:null;
    text('[data-prep-machine-note]',!machine?'Aucune machine dans le parc.':!machine.declared?'Ce slot possède une fiche à déclarer. Aucun volume de simulation ne sera utilisé.':volume?`${technology(machine.record.technology)} · volume utile déclaré : ${dimensions(volume)}.${machine.record.volumeSource?' Source : '+machine.record.volumeSource:''}`:`${technology(machine.record.technology)} · dimensions utiles à renseigner dans la fiche.`);
    $('[data-prep-action="fleet"]').disabled=removed||!machine;
    text('[data-prep-fleet-label]',machine?.declared?'Consulter la fiche':'Déclarer cette machine');
    const currentPlacement=orientation&&assessment?.technologyStatus==='match'?(orientation.fits?'fits':'exceeds'):assessment?.status||'not_declared';
    const placementLabel=orientation&&assessment?.technologyStatus==='match'?(orientation.fits?'Dans le volume.':'Cette orientation dépasse.'):assessment?.label||'À renseigner';
    $('[data-prep-result]').dataset.status=currentPlacement;
    $('[data-prep-result]').innerHTML=`<span>CE COUPLE PIÈCE / MACHINE</span><strong>${escapeHtml(placementLabel)}</strong><p>${orientation?orientation.fits?'L’enveloppe de cette orientation tient dans les dimensions déclarées.':'Cette orientation dépasse au moins une dimension déclarée.':'Associez un STL et complétez la fiche machine pour comparer les volumes.'}${assessment?.technologyStatus==='mismatch'?' Le procédé de la pièce diffère de celui de la machine.':''}</p>`;
    text('[data-prep-orientation-count]',assessment?.orientations?.length?`${assessment.orientations.filter(item=>item.fits).length} / 6 dans le volume`:'À calculer');
    $('[data-prep-orientations]').innerHTML=PREPARATION_ORIENTATIONS.map(item=>{const candidate=assessment?.orientations?.find(value=>value.id===item.id);return`<button type="button" data-prep-orientation="${escapeHtml(item.id)}" aria-pressed="${selection.orientationId===item.id}" ${!candidate||removed?'disabled':''} title="${escapeHtml(item.label)}${candidate?' · '+dimensions(candidate.dimensionsMm):''}" data-fits="${candidate?candidate.fits?'yes':'no':'unknown'}"><span class="pw-orientation-axes">${item.id.toUpperCase().split('').map(axis=>`<i>${axis}</i>`).join('')}</span><small>${candidate?candidate.fits?'Dans le volume':'Dépasse':'À calculer'}</small></button>`;}).join('');
    $('[data-prep-axes]').innerHTML=`<table><caption>DIMENSIONS COMPARÉES · MM</caption><thead><tr><th scope="col">Axe</th><th scope="col">Pièce</th><th scope="col">Volume</th><th scope="col">Marge</th></tr></thead><tbody>${['X','Y','Z'].map((axis,index)=>`<tr><th scope="row">${axis}</th><td>${number(orientation?.dimensionsMm?.[index]??piece?.dimensionsMm?.[index])}</td><td>${number(volume?.[index])}</td><td class="${orientation?.clearanceMm?.[index]<0?'is-negative':''}">${number(orientation?.clearanceMm?.[index])}</td></tr>`).join('')}</tbody></table>${orientation?`<div class="pw-volume-bars" aria-label="Occupation de chaque axe du volume utile">${['X','Y','Z'].map((axis,index)=>`<div data-overflow="${orientation.clearanceMm[index]<0}"><span>${axis}</span><i><b style="--pw-fill:${Math.min(100,Math.max(0,orientation.dimensionsMm[index]/volume[index]*100))}%"></b></i><small>${number(orientation.dimensionsMm[index]/volume[index]*100)} %</small></div>`).join('')}</div>`:''}`;
    const issues=assessment?.issues||[];
    $('[data-prep-issues]').innerHTML=issues.length?issues.map((issue,index)=>`<div class="pw-issue"><span>${String(index+1).padStart(2,'0')}</span><div><strong>${escapeHtml(issue.label)}</strong><p>${escapeHtml(issueActions[issue.action]||'À préparer dans le dossier.')}</p></div></div>`).join(''):'<div class="pw-issue"><span>01</span><div><strong>Supports et procédé à préparer.</strong><p>Le volume brut est une première vérification. Les supports, les réglages du matériau et le fichier tranché demandent leur propre préparation.</p></div></div>';
    $('[data-prep-matrix]').innerHTML=matrix(currentReport,selection);
    if($('.pw-matrix-scroll'))$('.pw-matrix-scroll').scrollLeft=matrixScroll;
    $('[data-prep-action="export"]').disabled=removed||checking||exporting||!!renderError||!currentReport;
    $('[data-prep-action="recheck"]').disabled=removed||checking;
    $('[data-prep-action="wire"]').setAttribute('aria-pressed',String(wire));
    if(viewport){viewport.setBuildVolume(volume||null);viewport.setOrientation(selection.orientationId);}
    if(focusRestore){
      const target=focusRestore.kind==='piece'?$$('[data-prep-piece]').find(node=>node.dataset.prepPiece===focusRestore.piece):focusRestore.kind==='orientation'?$$('[data-prep-orientation]').find(node=>node.dataset.prepOrientation===focusRestore.orientation):$$('[data-prep-cell-piece]').find(node=>node.dataset.prepCellPiece===focusRestore.piece&&node.dataset.prepCellMachine===focusRestore.machine);
      target?.focus({preventScroll:true});
    }
    onReport({report:copy(currentReport),selection:copy(selection),checking,unavailable:removed||!!renderError});
  }

  async function checkFile(piece,epoch,isPreview=false){
    const isCurrent=()=>!disposed&&!removed&&(isPreview?epoch===previewEpoch:epoch===auditEpoch);
    const unit=piece.unit??'mm';
    const base={projectId,pieceId:piece.id,pieceRevision:piece.revision||1,assetId:piece.assetId,unit,checkedAt:Date.now()};
    let stored;
    try{stored=await readAsset(piece.assetId,{expectedSha256:piece.assetSha256||null});}catch(error){if(!isCurrent())return null;return{proof:{...base,status:error?.code==='checksum_mismatch'?'invalid':'missing',message:String(error?.message||'Le fichier n’a pas pu être relu.').slice(0,240)},buffer:null};}
    if(!isCurrent())return null;
    if(!stored?.buffer)return{proof:{...base,status:'missing',message:'Le binaire STL n’est pas présent dans ce navigateur.'},buffer:null};
    try{
      const measured=await inspectSTL(stored.buffer,unit);
      if(!isCurrent())return null;
      let sha256=null;
      if(globalThis.crypto?.subtle){try{const hash=await globalThis.crypto.subtle.digest('SHA-256',stored.buffer);if(!isCurrent())return null;sha256=Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,'0')).join('');}catch{sha256=null;}}
      if(!isCurrent())return null;
      return{proof:{...base,status:'measured',dimsMm:[...measured.dims],triangles:measured.triangles,byteLength:stored.buffer.byteLength,sha256},buffer:stored.buffer};
    }catch(error){return isCurrent()?{proof:{...base,status:'invalid',message:String(error?.message||'Le STL ne peut pas être mesuré.').slice(0,240)},buffer:null}:null;}
  }
  function remember(proof){evidence=evidence.filter(item=>item.pieceId!==proof.pieceId);evidence.push(proof);}
  function beginAudit(){
    const epoch=++auditEpoch;
    checking=true;evidence=[];recompute();
    const pieces=copy(currentProject.pieces||[]).filter(piece=>piece.assetId);
    auditMessage=pieces.length?`Lecture des STL · 0 / ${pieces.length}`:'Ce dossier ne possède pas encore de STL associé.';
    paint();
    auditQueue=auditQueue.catch(()=>{}).then(async()=>{
      if(disposed||removed||epoch!==auditEpoch)return;
      let checked=0;
      for(const piece of pieces){
        const result=await checkFile(piece,epoch);
        if(!result||disposed||removed||epoch!==auditEpoch)return;
        remember(result.proof);checked++;recompute();
        auditMessage=`Lecture des STL · ${checked} / ${pieces.length}`;paint();
      }
      if(disposed||removed||epoch!==auditEpoch)return;
      checking=false;recompute();
      const summary=currentReport?.summary||{};
      auditMessage=pieces.length?`${summary.measuredFiles||0} STL mesuré${summary.measuredFiles>1?'s':''} sur ${pieces.length} associé${pieces.length>1?'s':''}.${summary.missingFiles?' '+summary.missingFiles+' fichier'+(summary.missingFiles>1?'s absents.':' absent.'):''}${summary.invalidFiles?' '+summary.invalidFiles+' fichier'+(summary.invalidFiles>1?'s invalides.':' invalide.'):''} La vérification porte sur les fichiers de ce navigateur.`:'Aucun STL associé. Les dimensions du dossier ne sont pas utilisées comme mesure du fichier.';
      paint();schedulePreview();
    }).catch(error=>{if(disposed||epoch!==auditEpoch)return;checking=false;renderError=String(error?.message||'La vérification des fichiers a échoué.');auditMessage='Vérification interrompue. Vous pouvez relire les fichiers.';paint();});
  }
  async function ensureViewport(){
    if(viewport)return viewport;
    if(viewportPromise)return viewportPromise;
    viewportPromise=Promise.resolve().then(()=>createViewport($('[data-prep-canvas]'),{motion,onStatus:message=>{if(!disposed)text('[data-prep-view-status]',message);}})).then(candidate=>{
      if(disposed){candidate?.dispose();return null;}
      viewport=candidate;viewport.setMotion(motion);viewport.setWireframe(wire);return viewport;
    }).catch(error=>{if(!disposed){text('[data-prep-view-status]','Le rendu 3D n’est pas disponible : '+String(error?.message||'WebGL indisponible.'));}return null;});
    return viewportPromise;
  }
  function showEmpty(title,description){
    $('[data-prep-empty]').hidden=false;text('[data-prep-empty-title]',title);text('[data-prep-empty-copy]',description);
  }
  function schedulePreview(){
    const epoch=++previewEpoch;
    const piece=copy(currentProject.pieces?.find(item=>item.id===selection.pieceId)||null);
    const selectedId=selection.pieceId;
    viewport?.clearModel();
    showEmpty(piece?.assetId?'Lecture du STL…':'Le fichier manque encore.',piece?.assetId?'Le maillage est relu à son unité déclarée.':piece?'Associez le STL de cette pièce pour la voir dans le volume de la machine.':'Le dossier ne contient aucune pièce.');
    text('[data-prep-view-status]','Inspection locale · aucune géométrie de remplacement.');
    previewQueue=previewQueue.catch(()=>{}).then(async()=>{
      if(disposed||removed||epoch!==previewEpoch)return;
      const candidate=await ensureViewport();
      if(disposed||removed||epoch!==previewEpoch||selectedId!==selection.pieceId)return;
      candidate?.clearModel();
      const volume=selectedMachine()?.declared?selectedMachine().record?.usableVolumeMm:null;
      candidate?.setBuildVolume(volume||null);candidate?.setOrientation(selection.orientationId);
      if(!piece?.assetId){showEmpty('Le fichier manque encore.','Associez le STL de cette pièce pour la voir à l’échelle. Aucun modèle de démonstration ne remplace son fichier.');return;}
      const result=await checkFile(piece,epoch,true);
      if(!result||disposed||removed||epoch!==previewEpoch||selectedId!==selection.pieceId)return;
      remember(result.proof);recompute();paint();
      if(!result.buffer){candidate?.clearModel();showEmpty(result.proof.status==='missing'?'STL à réimporter.':'STL à vérifier.',result.proof.message);text('[data-prep-view-status]',result.proof.message);return;}
      if(!candidate){showEmpty('Les mesures restent disponibles.','Le fichier a été relu. Le rendu 3D demande WebGL dans ce navigateur ; le rapport chiffré reste consultable.');return;}
      const currentVolume=selectedMachine()?.declared?selectedMachine().record?.usableVolumeMm:null;
      try{candidate.loadSTL(result.buffer,piece.unit??'mm');candidate.setBuildVolume(currentVolume||null);candidate.setOrientation(selection.orientationId);candidate.setWireframe(wire);$('[data-prep-empty]').hidden=true;text('[data-prep-view-status]',currentVolume?'STL à l’échelle dans le volume déclaré · hors supports.':'STL à l’échelle · renseignez le volume utile de la machine.');}
      catch(error){candidate.clearModel();showEmpty('Rendu 3D indisponible.',String(error?.message||'Le modèle n’a pas pu être affiché.'));text('[data-prep-view-status]','Le rapport conserve les mesures du fichier ; aucun modèle de remplacement.');}
    });
  }
  function selectPair(pieceId,machineId){
    const changedPiece=selection.pieceId!==pieceId;
    selection.pieceId=pieceId;selection.machineId=machineId;normalizeSelection(true);paint();
    if(changedPiece)schedulePreview();
    else if(viewport){viewport.setBuildVolume(selectedMachine()?.declared?selectedMachine().record?.usableVolumeMm||null:null);viewport.setOrientation(selection.orientationId);viewport.reset();}
    text('[data-prep-export-status]','');
  }
  async function onClick(event){
    const button=event.target.closest('button');if(!button||!host.contains(button)||button.disabled||disposed)return;
    if(button.dataset.prepPiece){selectPair(button.dataset.prepPiece,selection.machineId);return;}
    if(button.dataset.prepCellPiece){selectPair(button.dataset.prepCellPiece,button.dataset.prepCellMachine);return;}
    if(button.dataset.prepOrientation){selection.orientationId=button.dataset.prepOrientation;paint();text('[data-prep-export-status]','');return;}
    const action=button.dataset.prepAction;if(!action)return;
    if(action==='decisions'){onDecision(getSnapshot());return;}
    if(action==='wire'){wire=!wire;viewport?.setWireframe(wire);button.setAttribute('aria-pressed',String(wire));return;}
    if(action==='reset'){viewport?.reset();return;}
    if(action==='recheck'){beginAudit();return;}
    if(action==='fleet'){if(selection.machineId)onOpenFleet({machineId:selection.machineId});return;}
    if(action==='import'){if(selection.pieceId)onImport({projectId,pieceId:selection.pieceId,unit:$('[data-prep-import-unit]').value});return;}
    if(action==='export'){
      if(checking||exporting||removed||renderError||!currentReport)return;
      const atVersion=version;
      const assessment=selectedAssessment();
      const exportSelection={...selection,orientationId:assessment?.orientations?.some(item=>item.id===selection.orientationId)?selection.orientationId:null};
      exporting=true;paint();
      try{const result=await onExport({report:copy(currentReport),selection:exportSelection});if(!disposed&&atVersion===version)text('[data-prep-export-status]',result?.message||(result?.ok?'Rapport exporté. Les fichiers STL restent séparés.':'Le rapport n’a pas pu être exporté.'));}
      catch(error){if(!disposed&&atVersion===version)text('[data-prep-export-status]',String(error?.message||'L’export a échoué.'));}
      finally{exporting=false;if(!disposed)paint();}
    }
  }
  function onChange(event){
    if(disposed||removed)return;
    if(event.target.matches('[data-prep-machine]'))selectPair(selection.pieceId,event.target.value);
    if(event.target.matches('[data-prep-import-unit]'))importUnits.set(selection.pieceId,event.target.value);
  }
  host.addEventListener('click',onClick);host.addEventListener('change',onChange);
  function setMotion(enabled){motion=!!enabled;host.classList.toggle('pw-motion-off',!motion);viewport?.setMotion(motion);}
  function refreshContext({project:nextProject,machines:nextMachines,activeProjectId:activeId,report:nextReport}={}){
    if(disposed)return;
    if(activeId!==undefined)activeProjectId=activeId;
    if(!nextProject||nextProject.id!==projectId){removed=true;version++;auditEpoch++;previewEpoch++;checking=false;viewport?.clearModel();paint();showEmpty('Dossier indisponible.','Rouvrez la préparation depuis un dossier existant.');return;}
    const machinesToUse=nextMachines||currentMachines;
    const nextKey=contextKey(nextProject,machinesToUse),nextGeometry=geometryKey(nextProject);
    const geometryChanged=nextGeometry!==lastGeometry,changed=nextKey!==lastContext;
    currentProject=copy(nextProject);currentMachines=copy(machinesToUse);removed=false;
    lastContext=nextKey;lastGeometry=nextGeometry;
    if(!changed){paintContext();return;}
    version++;text('[data-prep-export-status]','Le dossier ou une fiche machine a changé. Le rapport a été recalculé.');
    if(nextReport)currentReport=nextReport;
    if(geometryChanged){previewEpoch++;viewport?.clearModel();beginAudit();}
    else{recompute();paint();if(viewport){viewport.setBuildVolume(selectedMachine()?.declared?selectedMachine().record?.usableVolumeMm||null:null);viewport.setOrientation(selection.orientationId);} }
  }
  function dispose(){if(disposed)return;disposed=true;version++;auditEpoch++;previewEpoch++;host.removeEventListener('click',onClick);host.removeEventListener('change',onChange);viewport?.dispose();viewport=null;evidence=[];}
  function getSnapshot(){return{report:copy(currentReport),selection:copy(selection),checking,unavailable:disposed||removed||!!renderError};}
  function select(next){
    if(disposed||removed||!next||!currentReport?.pieces?.some(piece=>piece.id===next.pieceId))return false;
    if(next.machineId&&!currentReport.machines.some(machine=>machine.id===next.machineId))return false;
    pendingSelection={pieceId:next.pieceId,machineId:next.machineId||selection.machineId,orientationId:next.orientationId||null};
    paint();schedulePreview();return true;
  }
  setMotion(motion);recompute();paint();beginAudit();schedulePreview();
  return{dispose,setMotion,refreshContext,getSnapshot,select};
}
