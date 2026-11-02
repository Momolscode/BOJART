import {WorkshopStore, calculateQuote, jobProgress} from './lib/workshop.js';
import {renderWall} from './lib/wall.js';
import {mountMotionStage} from './lib/motion-stage.js';
import {inspectMission, renderMission} from './lib/mission.js';
import {DOMAIN_CATALOG, buildOperations, buildMasterMission, buildControlDecision, answerMissionQuestion} from './lib/control-plane.js';
import {renderControlStage, renderControlHub, renderMasterMission} from './lib/control-view.js';
import {createProjectEvidence, preparationReportContext} from './lib/project-evidence.js';
import {renderDecisionDesk, mountDecisionDesk} from './lib/decision-view.js';
import {getDecisionProviderStatus, requestProjectDecision} from './lib/decision-client.js';
import {createDisplayBus} from './lib/display-bus.js';
import {VISUAL_VIEWS,visualContext,contextIsCurrent,availableVisuals,chooseLocalVisual,requestVisualDecision,getVisualProviderStatus} from './lib/visual-router.js';
import {renderVisualDock,renderVisualDesk} from './lib/visual-view.js';
import {renderSignatureView} from './lib/signature-view.js';
import {renderStudioView,mountStudio} from './lib/studio-view.js';
import {renderProjectStudio,mountProjectStudio} from './lib/project-studio-view.js';
import {projectEditPlans,latestEditVersion,exportEditPlan} from './lib/edit-plan.js';
import {inspectDeclaredPreparation,exportDeclaredPreparation} from './lib/preparation.js';
import {renderPreparationView,mountPreparationView} from './lib/preparation-view.js';
import {renderFleetRegistry,renderFleetForm} from './lib/fleet-view.js';
import {fleetRecordFromForm,exportFleetRegistry} from './lib/fleet-registry.js';
import {createWorkshopBackup,inspectWorkshopBackup} from './lib/workshop-backup.js';
import {createWorkshopSync} from './lib/workshop-sync.js';
import {continuityLabel,renderContinuityView,renderContinuityStatus,renderBackupPreview,renderAssetVault} from './lib/continuity-view.js';
import {createWorkshopAssetClient,assetSHA256} from './lib/workshop-assets.js';
import {createBrowserAssetsBackup,referencedWorkshopAssets} from './lib/browser-assets-backup.js';
import {INQUIRY_MAX_BYTES,inspectInquiryExport,importInquiryProject,inquiryQuestionsText,exportInquiryTechnical} from './lib/inquiry-import.js';
import {renderInquiryDesk,renderInquiryPreview,renderInquiryDetail} from './lib/inquiry-view.js';
import {renderIntegrityView,renderIntegrityBanner} from './lib/integrity-view.js';
import {validateSTLFiles,readSTLImportChoices,renderSTLImportSetup} from './lib/stl-import-view.js';

const $ = (q, scope=document) => scope.querySelector(q);
const $$ = (q, scope=document) => [...scope.querySelectorAll(q)];
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const euro = n => Number(n).toLocaleString('fr-FR',{style:'currency',currency:'EUR',maximumFractionDigits:2});
const fmt = n => Number(n).toLocaleString('fr-FR',{maximumFractionDigits:1});
const paths={printer:'<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6zM18 12h.01"/>',cube:'<path d="m12 2 9 5v10l-9 5-9-5V7l9-5Z"/><path d="m3 7 9 5 9-5M12 12v10M7.5 4.5l9 5"/>',grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',spark:'<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6L12 3ZM20 2v4M18 4h4"/>',settings:'<path d="m9.5 3-.6 2.2-2 1.1L4.7 6 3 9l1.6 1.5v3L3 15l1.7 3 2.2-.3 2 1.1.6 2.2h5l.6-2.2 2-1.1 2.2.3 1.7-3-1.6-1.5v-3L21 9l-1.7-3-2.2.3-2-1.1L14.5 3Z"/><circle cx="12" cy="12" r="3"/>',screens:'<rect x="2" y="4" width="14" height="11" rx="2"/><path d="M6 20h7M9 15v5M19 7h3v12h-6v-1"/>',arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',arrowUp:'<path d="M6 18 18 6M6 6h12v12"/>',close:'<path d="m6 6 12 12M6 18 18 6"/>',motion:'<path d="M3 8h4M1 12h5M3 16h4"/><circle cx="15" cy="12" r="6"/>',plus:'<path d="M12 5v14M5 12h14"/>',upload:'<path d="M12 16V3m-5 5 5-5 5 5M3 15v5a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-5"/>',play:'<path d="m8 4 12 8-12 8V4Z"/>',pause:'<path d="M8 4v16M16 4v16"/>',rotate:'<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>',expand:'<path d="M8 3H3v5M16 3h5v5M21 16v5h-5M8 21H3v-5M8 8l-5-5M16 8l5-5M16 16l5 5M8 16l-5 5"/>',layers:'<path d="m12 3 10 5-10 5L2 8l10-5Zm-10 9 10 5 10-5M2 16l10 5 10-5"/>',film:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 7h4M3 12h4M3 17h4M17 7h4M17 12h4M17 17h4"/>',info:'<circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7h.01"/>',check:'<path d="m5 12 4 4L20 5"/>',folder:'<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>',edit:'<path d="m16 3 5 5-12 12-6 1 1-6L16 3ZM13 6l5 5"/>',chart:'<path d="M3 3v18h18M7 16v-5M12 16V7M17 16V4"/>',down:'<path d="m6 9 6 6 6-6"/>',trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',link:'<path d="m10 13 4-4M8 16l-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0M16 8l2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>',save:'<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12l4 4v12a2 2 0 0 1-2 2Z"/><path d="M7 3v6h10V3M7 21v-8h10v8"/>'};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.cube}</svg>`;
function icons(scope=document){$$('[data-icon]',scope).forEach(n=>{n.innerHTML=icon(n.dataset.icon);n.removeAttribute('data-icon');});}
const store = new WorkshopStore();
let workshopSync=null,pendingRestore=null,backupReadSequence=0,studioController=null,projectStudioController=null,projectStudioId=null;
let preparationController=null,preparationProjectId=null,preparationImportTarget=null,preparationImportSequence=0;
let decisionController=null,decisionProjectId=null,masterMissionProjectId=null;
let inquiryReadSequence=0,pendingInquiry=null,inquiryViewProjectId=null;
let pendingSTLImport=null,stlImportSequence=0;
const assetVault=createWorkshopAssetClient();
let assetVaultStatus={available:false,checked:false,busy:false,fileCount:0,message:''};
let continuityStatus={mode:store.persistent?'browser':'memory',message:store.persistent?'Dossiers conservés dans ce navigateur.':'Conservation limitée à cette fenêtre.',pending:0,lastSavedAt:null,available:false,durable:false,conflicts:0};
const screenNames={panorama:'Tour de contrôle',atelier:'Atelier',pilotage:'Jarvis',creation:'Création'};
const params=new URLSearchParams(location.search);
let savedMotion=null;try{savedMotion=localStorage.getItem('bojart.motion');}catch{}
const osMotion=matchMedia('(prefers-reduced-motion: reduce)');
const ui={screen:screenNames[params.get('screen')]?params.get('screen'):'pilotage',creationTab:['oeuvre','modele','video'].includes(params.get('tab'))?params.get('tab'):'oeuvre',pilotTab:'controle',controlDomain:'all',filter:'all',machine:'P01',motion:savedMotion==='off'?false:!osMotion.matches,wire:false,auto:false,exploded:false,archiveQuery:'',wallFocus:'all',immersive:params.get('immersive')==='1',ambient:true,section:null};
let viewer=null,viewerGeneration=0,archive=[],lastReceipt=null,toastTimer,dbPromise;
let motionStages=[],ambientObserver=null,lastProjectId=store.state.projectId;
const stationRoles=['atelier','pilotage','creation'];
ui.station=stationRoles.includes(params.get('station'))?params.get('station'):params.get('immersive')==='1'&&stationRoles.includes(params.get('screen'))?params.get('screen'):null;
let displayBus=null,displayPending=false,intentSequence=0;
let visualProvider={checked:false,configured:false,connected:false},visualBusy=false,visualSequence=0,visualReceipt='',transferTimer;
const artSource={baki:'https://www.tiktok.com/@boj.art/video/7480904142689635607',atelier:'https://www.tiktok.com/@boj.art/video/7464268707989114134',film:'https://www.tiktok.com/@boj.art/video/7467517355535404310'};
const projectEvidence=createProjectEvidence({getState:()=>store.state,readAsset,
  inspectSTL:async(buffer,unit)=>(await import('./lib/viewer.js')).inspectSTL(buffer,unit),
  onChange:({projectId})=>{if(store.integrityError||!getProject())return;decisionController?.refreshContext?.();if(masterMissionProjectId===projectId&&$('#drawer').open){$('#drawer-content').innerHTML=renderMasterMission({mission:currentMasterMission(projectId),domains:DOMAIN_CATALOG,esc,icon});icons($('#drawer'));}if(projectId===store.state.projectId&&(ui.screen==='panorama'||ui.screen==='pilotage'&&ui.pilotTab==='controle'))render(false);}
});
function currentMasterMission(projectId=getProject().id){const evidence=projectEvidence.snapshot(projectId);return buildMasterMission(store.state,projectId,{preparationReport:evidence.report,evidenceStatus:evidence.status});}
function getProject(){return store.getProject()||store.state.projects[0];}
function getPiece(){const p=getProject();return p?.pieces.find(x=>x.id===store.state.selectedPieceId)||p?.pieces[0];}
function dispatch(type,payload){const result=store.dispatch(type,payload);if(result?.ok===false){toast(result.message||'Cette action n’est pas disponible.');if(store.integrityError)render(false);}return result;}
function paintIntegrityGuard(){
  const reason=store.integrityError;
  document.documentElement.classList.toggle('integrity-blocked',!!reason);
  const mode=$('.mode-pill');if(mode)mode.innerHTML=reason?'<i></i> Journal à vérifier':'<i></i> Poste de préparation';
  for(const dialog of [$('#drawer'),$('#command-dialog')]){
    let banner=$('[data-integrity-banner]',dialog);
    if(!reason){banner?.remove();continue;}
    if(!dialog.open)continue;
    const markup=renderIntegrityBanner({reason,esc,icon});
    if(banner)banner.outerHTML=markup;else(dialog.id==='drawer'?$('#drawer-content'):dialog).insertAdjacentHTML('afterbegin',markup);
  }
}
function integrityFailure(){return {ok:false,message:store.integrityError||'Le journal doit être relu avant de poursuivre.'};}
function exportIntegrityCopy(){try{downloadJson(store.recoverRawStorage(),'BOJ_ART_Recuperation_'+new Date().toISOString().replace(/[:.]/g,'-')+'.json');toast('Copie de récupération préparée. Elle conserve les entrées disponibles sans les réparer.');}catch(error){toast(error.message);}}
function recheckIntegrity(){const result=store.recheckIntegrity();paintIntegrityGuard();paintContinuity();render(false);if(result.ok){startWorkshopSync();if(getProject())void projectEvidence.inspect(getProject().id,{force:true});}toast(result.message);}
function techName(tech){return tech==='resin'?'Résine UV':'FDM';}
function techTag(tech){return `<span class="tag ${tech==='resin'?'tag-red':'tag-blue'}">${techName(tech)}</span>`;}
function projectPicker(){return `<div class="project-switch"><label for="project-picker">Projet actif</label><select id="project-picker" aria-label="Projet actif">${store.state.projects.map(p=>`<option value="${esc(p.id)}" ${p.id===getProject().id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></div>`;}
function header(kicker,title,actions=''){return `<section class="page-head reveal"><div><p class="eyebrow">${kicker}</p><h1>${title}</h1></div><div class="page-actions">${actions}</div></section>`;}
function currentJob(machineId){return store.state.jobs.find(j=>j.machine===machineId&&j.status==='running'&&jobProgress(j)<100)||store.state.jobs.find(j=>j.machine===machineId&&j.status==='paused')||store.state.jobs.find(j=>j.machine===machineId&&j.status==='queued')||store.state.jobs.find(j=>j.machine===machineId);}
function jobPiece(job){if(!job)return null;return store.state.projects.find(p=>p.id===job.projectId)?.pieces.find(p=>p.id===job.pieceId);}
function jobStatus(job){if(!job)return 'Disponible';if(jobProgress(job)>=100)return 'Simulation terminée';return {running:'Simulation en cours',paused:'Simulation en pause',queued:'En attente',done:'Simulation terminée'}[job.status]||'En attente';}
function remaining(job){if(!job)return 'À affecter';const minutes=Math.max(0,Math.ceil((job.duration||0)*(1-jobProgress(job)/100)/60000));return minutes>59?`${Math.floor(minutes/60)} h ${String(minutes%60).padStart(2,'0')}`:`${minutes} min`;}
function renderCreation(){const p=getProject(),piece=getPiece();
  let stage;
  const tabs=`<div class="tab-bar stage-tabs" role="tablist" aria-label="Espace de création">${[['oeuvre','L’œuvre'],['modele','Inspecteur 3D'],['video','Édit vidéo']].map(([key,label])=>`<button class="tab-button ${ui.creationTab===key?'active':''}" data-creation-tab="${key}" role="tab" aria-selected="${ui.creationTab===key}">${label}</button>`).join('')}</div>`;
  if(ui.creationTab==='modele')stage=`<div class="viewer" id="model-viewer" aria-label="Inspecteur 3D : tourner avec le doigt ou la souris, zoomer avec deux doigts ou la molette"><div class="viewer-note"><strong id="model-name">${esc(piece?.assetId?piece.name:'Socle technique — modèle de démonstration')}</strong><span id="model-info">${piece?.assetId?`${piece.dims.map(fmt).join(' × ')} mm · hors supports`:'Géométrie de démonstration · import STL disponible'}</span></div><div class="section-control"><label for="section-slider">Coupe 3D <output id="section-value">${ui.section===null?'désactivée':Math.round(ui.section*100)+' %'}</output></label><input id="section-slider" type="range" min="0" max="100" step="1" value="${ui.section===null?100:Math.round(ui.section*100)}"><button data-action="section-reset">Modèle entier</button></div><div class="viewer-tools"><div><button class="button button-dark button-small" data-action="viewer-reset" aria-label="Recentrer le modèle">${icon('rotate')}</button><button class="button button-dark button-small" data-action="viewer-wire" aria-pressed="${ui.wire}">Maillage</button><button class="button button-dark button-small" data-action="viewer-explode" aria-pressed="${ui.exploded}">Éclaté démo</button><button class="button button-dark button-small" data-action="viewer-auto" aria-pressed="${ui.auto}">${icon('motion')}</button></div><button class="button button-red button-small" data-action="import">${icon('upload')} STL</button></div></div><div class="stage-top">${tabs}<span class="tag">ESPACE 3D RÉEL</span></div>`;
  else if(ui.creationTab==='video')stage=`<div class="studio-film brand-film-stage"><video id="studio-video" src="./assets/brand-film-master.mp4" poster="./assets/brand-film-poster.webp" playsinline muted preload="metadata" aria-label="Baki — Du détail à l’œuvre, nouvel édit BOJ.ART silencieux de 22,7 secondes"></video><div class="stage-top">${tabs}<span class="tag">NOUVEL ÉDIT BOJ.ART</span></div><div class="stage-caption"><div><span class="tag tag-red">BAKI / 60 CM · 22,7 S</span><h3>LE DÉTAIL.<br>LE GESTE.<br><em>L’ŒUVRE.</em></h3><p>Huit plans, une même création.<br>Proposition de signature · sans audio.</p></div><div class="stage-controls"><button class="button button-dark" data-action="play-video" id="film-play">${icon('play')} Lire</button><button class="button button-red" data-action="studio">Le Studio ${icon('arrow')}</button></div></div></div>`;
  else stage=ui.creationTab==='oeuvre'&&p.media?`<div class="cinematic-stage"><video class="ambient-film" data-ambient-video src="./assets/atelier-motion.mp4" poster="./assets/atelier-motion-poster.webp" muted loop playsinline preload="metadata" aria-label="Œuvres et gestes originaux BOJ.ART"></video><div class="cinema-shade"></div><div class="cinema-frame"></div><div class="stage-top">${tabs}<span class="tag stage-live-label">LES ŒUVRES EN MOUVEMENT</span></div><div class="cinema-word"><small>LE GESTE DE L’ARTISTE. L’INTELLIGENCE DE L’ATELIER.</small>L’ART<br><em>PREND VIE.</em></div><button class="ambient-toggle" data-action="ambient" aria-pressed="${ui.ambient&&ui.motion}" aria-label="Mettre le montage en pause">${icon('pause')}</button><div class="stage-caption"><div><span class="tag tag-red">BOJ.ART / LES RÉFÉRENCES</span><h3>L’empreinte du geste.</h3><p>Trois œuvres et un geste de peinture · montage silencieux de 18,8 s</p></div><div class="cinema-controls"><button class="button button-dark" data-action="wall-model">${icon('cube')} Inspecter en 3D</button><button class="button button-red" data-action="mission">${icon('layers')} Préparer</button></div></div><div class="film-progress"><i></i></div></div>`:`<img class="hero-photo" src="./assets/${esc(p.media||'logo.webp')}" alt="Référence du dossier BOJ.ART"><div class="hero-gradient"></div><div class="stage-top">${tabs}<span class="tag">LE DOSSIER</span></div><div class="hero-word"><small>UN NOUVEAU TERRAIN DE CRÉATION</small>DE L’IDÉE<br><span>À LA PIÈCE.</span></div><div class="stage-caption"><div><h3>${esc(p.name)}</h3><p>Importez vos fichiers pour préparer cette création.</p></div><button class="button button-red" data-action="import">${icon('upload')} STL</button></div>`;
  return `${header('ÉCRAN 03 / CRÉATION','DU GESTE À <em>L’ŒUVRE.</em>',`${projectPicker()}<button class="button button-red" data-action="import">${icon('upload')} Importer un STL</button>`)}
  <div class="creation-layout"><section class="panel creation-stage reveal" style="--order:1">${stage}</section><aside class="panel project-panel reveal" style="--order:2"><div class="project-summary"><p class="eyebrow">LE DOSSIER</p><h2>${esc(p.name)}</h2><p class="small muted">${esc(p.subtitle||p.kind||'Création sur mesure')}</p><div class="project-meta"><div><strong>${p.height===null?'À préciser':fmt(p.height||0)+'<small class="small"> mm</small>'}</strong><span>Hauteur souhaitée</span></div><div><strong>${p.pieces.length.toString().padStart(2,'0')}</strong><span>Pièces du dossier</span></div><div><strong>${p.quantity||1}</strong><span>Exemplaire${p.quantity>1?'s':''}</span></div></div></div><div class="piece-list" aria-label="Pièces du projet">${p.pieces.map((item,i)=>`<button class="piece-row ${item.id===piece?.id?'active':''}" data-piece="${esc(item.id)}" aria-pressed="${item.id===piece?.id}"><span class="piece-index">${String(i+1).padStart(2,'0')}</span><span><strong>${esc(item.name)}</strong><small>${techName(item.tech)}${item.assetId?' · STL importé':' · exemple'}</small></span><span class="piece-machine">${esc(item.machine||'—')}</span></button>`).join('')}</div><div class="project-bottom"><button class="button button-block" data-action="piece">${icon('layers')} Détail de la pièce ${icon('arrow')}</button></div></aside></div>
  <div class="creation-lower"><section class="panel reveal" style="--order:3"><div class="work-strip">${[['atelier.webp','Le savoir-faire','Le geste de peinture','atelier'],['dragon.webp','La collection','Composition Dragon Ball','dragon'],['throne.webp','La signature','Matières & contrastes','throne']].map(([image,title,sub,id])=>`<button class="work-thumb" data-art="${id}"><img src="./assets/${image}" alt="${esc(title)} — référence BOJ.ART"><span class="work-label">${title}<small>${sub}</small></span></button>`).join('')}</div></section><section class="panel quick-jarvis reveal" style="--order:4"><div class="orb" aria-hidden="true"></div><div><h3>PARLONS CRÉATION.</h3><p>Le dossier et ses vues, au même endroit.</p><button class="button button-small" data-action="command">Ouvrir Jarvis ${icon('arrow')}</button></div></section></div>`;
}
function renderAtelier(){const p=getProject(),m=store.getMachine(ui.machine)||store.state.machines[0],job=currentJob(m.id),piece=jobPiece(job);const machines=store.state.machines.filter(m=>ui.filter==='all'||m.tech===ui.filter);
  return `${header('ÉCRAN 01 / PRODUCTION','LA MATIÈRE <em>EN ACTION.</em>',`${projectPicker()}<button class="button" data-action="fleet">${icon('printer')} Le parc</button><button class="button button-red" data-action="plan">${icon('layers')} Répartir les pièces</button>`)}${renderProductionOverview()}<div class="section-line reveal"><div class="stats-inline"><span><strong>${store.state.machines.length}</strong> emplacements de démonstration</span><span><strong>${store.state.jobs.filter(j=>j.status==='running'&&jobProgress(j)<100).length}</strong> simulations actives</span></div><div class="filter-tabs" role="group" aria-label="Filtrer les procédés">${[['all','Tout le parc'],['resin','Résine'],['fdm','FDM']].map(([k,l])=>`<button data-filter="${k}" class="${ui.filter===k?'active':''}" aria-pressed="${ui.filter===k}">${l}</button>`).join('')}</div></div>
  <div class="production-layout"><section class="machine-grid">${machines.map((m,i)=>{const job=currentJob(m.id),piece=jobPiece(job),progress=job?jobProgress(job):0;return `<button class="panel machine-card reveal ${m.tech} ${job?.status==='running'&&progress<100?'running':''} ${m.id===ui.machine?'selected':''}" style="--order:${Math.min(i,5)}" data-machine="${m.id}" aria-pressed="${m.id===ui.machine}"><div class="machine-head"><span class="machine-number">${m.id}</span><span class="machine-tech">${m.tech==='resin'?'RÉSINE':'FDM'}</span></div><div class="machine-viz">${icon('printer')}</div><span class="machine-job">${esc(piece?.name||'Prête pour une simulation')}</span><div class="progress-track" role="progressbar" aria-label="Progression simulée de ${m.id}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(progress)}" data-progress-machine="${m.id}"><div class="progress-bar" style="--progress:${progress}%"></div></div><div class="machine-meta"><span class="${job?.status==='running'?'running-label':''}" data-machine-status="${m.id}">${job?.status==='paused'?'En pause':job?.status==='running'?'Simulation':job?.status==='queued'?'En attente':'Disponible'}</span><span data-machine-time="${m.id}">${job?`${Math.round(progress)} %`:'—'}</span></div></button>`;}).join('')}</section>
  <aside class="panel production-detail reveal" style="--order:3"><img class="detail-photo" src="./assets/baki-detail.webp" alt="Détail d’une œuvre dans l’atelier BOJ.ART"><div class="detail-main"><p class="eyebrow">RESSOURCE SÉLECTIONNÉE</p><h2>${m.id} <span class="muted">/ ${m.tech==='resin'?'RÉSINE':'FDM'}</span></h2><p class="small muted">${esc(piece?.name||'Aucun travail affecté')} · ${jobStatus(job)}</p><div class="detail-grid"><div><span>Volume d’exemple</span><strong>${m.volume.map(fmt).join(' × ')} mm</strong></div><div><span>Matière prévue</span><strong>${esc(m.material||'À renseigner')}</strong></div><div><span>Temps simulé restant</span><strong>${remaining(job)}</strong></div><div><span>Profil réel</span><strong>À qualifier</strong></div></div><div class="detail-actions"><button class="button button-red" data-action="toggle-machine" data-id="${m.id}">${icon(job?.status==='running'?'pause':'play')} ${job?.status==='running'?'Pause':job?.status==='paused'?'Reprendre':'Simuler'}</button><button class="button" data-fleet-machine="${m.id}">${icon('settings')} Fiche réelle</button></div><button class="button button-small" data-action="machine-edit" data-id="${m.id}">Profil de simulation</button><p class="note-line">${icon('info')} Aucune imprimante connectée. Les états affichés proviennent de la simulation.</p></div></aside></div>
  <section class="panel queue-panel reveal" style="--order:5"><div class="panel-header"><h3>La file du projet <span class="muted">/ ${esc(p.name)}</span></h3><span class="tag">DOSSIER DE DÉMONSTRATION</span></div><table class="queue-table"><thead><tr><th>Pièce</th><th>Procédé</th><th>Enveloppe brute</th><th>Avancement</th><th>Machine</th><th></th></tr></thead><tbody>${p.pieces.map((piece,i)=>{const j=store.state.jobs.find(x=>x.projectId===p.id&&x.pieceId===piece.id&&x.revision===(piece.revision||1));return `<tr><td><span class="queue-index">${String(i+1).padStart(2,'0')}</span>${esc(piece.name)}</td><td>${techTag(piece.tech)}</td><td class="muted">${piece.dims.map(fmt).join(' × ')} mm</td><td><span class="timeline">${Array.from({length:8},(_,k)=>`<span class="${j&&jobProgress(j)>k*12.5?'done':''}"></span>`).join('')}</span></td><td>${esc(j?.machine||piece.machine||'À affecter')}</td><td><button class="table-action" data-piece-detail="${esc(piece.id)}">Détail ${icon('arrowUp')}</button></td></tr>`;}).join('')}</tbody></table></section>`;
}
function renderPilotage(){const p=getProject();if(ui.pilotTab==='controle')return renderControlScreen();if(ui.pilotTab==='demandes')return `${header('ÉCRAN 02 / ACQUISITION','DU CONTACT À <em>LA CRÉATION.</em>',projectPicker())}${controlTabs()}<section class="panel inquiry-page">${renderInquiryDesk({projects:store.state.projects,esc,icon})}</section>`;let content;
  if(ui.pilotTab==='archive'){const filtered=archive.filter(a=>(a.title+' '+a.id).toLocaleLowerCase('fr').includes(ui.archiveQuery.toLocaleLowerCase('fr')));content=`<section class="panel"><div class="archive-summary"><span><strong>${archive.length}</strong> publications indexées · références originales</span><input class="archive-search" id="archive-search" aria-label="Rechercher une publication" placeholder="Rechercher dans l’archive…" value="${esc(ui.archiveQuery)}"></div><div class="archive-grid" id="archive-grid">${archiveCards(filtered)}</div>${!archive.length?'<div class="empty-state"><h3>Le catalogue se prépare.</h3>Les références de l’atelier restent disponibles dans l’onglet Création.</div>':''}</section>`;}
  else if(ui.pilotTab==='journal'){content=`<section class="panel"><div class="panel-header"><h3>Le journal du poste</h3><span class="tag">SIMULATIONS ET DOSSIERS</span></div><div class="log-list">${store.state.journal.slice(0,18).map(j=>`<div class="log-item"><time>${new Date(j.at||j.timestamp||Date.now()).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})}</time><span>${esc(j.message||j.text||j.type)}</span></div>`).join('')||'<div class="empty-state">Les modifications et actions apparaîtront ici.</div>'}</div></section>`;}
  else content=`<section class="panel"><div class="panel-header"><h3>Les projets de l’atelier</h3><button class="button button-small" data-action="new-project">${icon('plus')} Nouveau dossier</button></div><div class="project-list">${store.state.projects.map(p=>`<div class="project-record"><img class="record-thumb" src="./assets/${esc(p.media||'logo.webp')}" alt="Référence visuelle du dossier"><div class="record-text"><strong>${esc(p.name)}</strong><span>${esc(p.kind||'Sur mesure')} · ${p.pieces.length} pièces · ${p.quantity||1} exemplaire${p.quantity>1?'s':''}</span></div><div class="record-amount">${p.quote?.result?euro(p.quote.result.price):'À chiffrer'}<small>${p.quote?.result?'Brouillon du lot':'Aucune vente réelle'}</small></div><button class="icon-button" data-project-edit="${esc(p.id)}" aria-label="Modifier ${esc(p.name)}">${icon('arrowUp')}</button></div>`).join('')}</div><div class="pipeline-strip">${[['Étude','À qualifier'],['Chiffré','Chiffrés'],['Production','À produire'],['Terminé','Terminés']].map(([s,label])=>`<div class="pipeline-step"><strong>${store.state.projects.filter(p=>(p.status||'Étude').startsWith(s)).length.toString().padStart(2,'0')}</strong><span>${label}</span></div>`).join('')}</div></section><section class="panel"><div class="panel-header"><h3>Le projet actif <span class="muted">/ ${esc(p.name)}</span></h3><span class="tag tag-red">BROUILLON</span></div><div class="panel-body"><div class="section-line"><p class="small muted">${esc(p.notes||'Préparer la fabrication, son coût et sa mise en scène.')}</p></div><div class="page-actions"><button class="button" data-action="project-edit">${icon('edit')} Le brief</button><button class="button button-red" data-action="quote">${icon('chart')} Chiffrer le projet</button><button class="button" data-action="story">${icon('film')} Préparer le contenu</button></div></div></section>`;
  return `${header('ÉCRAN 02 / JARVIS','UNE INTENTION. <em>TOUT L’ATELIER.</em>',`${projectPicker()}<button class="button" data-action="screens">${icon('screens')} Poste 3 écrans</button>`)}${renderCommandDeck()}<div class="pilot-grid"><aside class="panel jarvis-panel reveal" style="--order:1"><p class="eyebrow">JARVIS / POSTE CENTRAL</p><div class="single-jarvis-canvas"><div class="motion-canvas" data-motion-stage="jarvis" aria-hidden="true"></div><div class="jarvis-display-word"><small>LA TOUR DE CONTRÔLE</small><strong>JARVIS</strong></div></div><div class="waveform" aria-hidden="true">${Array.from({length:26},(_,i)=>`<i style="--height:${5+Math.sin(i*1.8)**2*20}px;--delay:${i*.075}s"></i>`).join('')}</div><h2>UNE INTENTION.<br>UNE ACTION.</h2><p>Un dossier, ses pièces, ses ressources. Préparer chaque étape depuis le poste central.</p><button class="button button-red button-block" data-action="command">Donner une intention ${icon('arrow')}</button><button class="button button-block mission-quick" data-action="mission">${icon('layers')} Préparer la fabrication</button><p class="micro-copy">Voix locale et Jev à raccorder.</p></aside><div class="pilot-content reveal" style="--order:2"><div class="tab-bar" role="tablist" aria-label="Administration">${[['controle','Le poste'],['dossiers','Les dossiers'],['demandes','Les demandes'],['archive','La vidéothèque'],['journal','Le journal']].map(([id,label])=>`<button class="tab-button ${ui.pilotTab===id?'active':''}" data-pilot-tab="${id}" role="tab" aria-selected="${ui.pilotTab===id}">${label}</button>`).join('')}</div>${content}<section class="panel identity-band"><div><p class="eyebrow">L’ADN DE BOJ.ART</p><h2>LA SIGNATURE, PARTOUT.</h2><p>Les œuvres, le geste et les références d’origine.</p><button class="button button-ghost button-small" data-action="identity">Voir la direction artistique ${icon('arrow')}</button></div><img src="./assets/logo.webp" alt="Emblème original de BOJ.ART"></section></div></div>`;
}
function archiveCards(items){return items.map(a=>`<button class="archive-card" data-media="${esc(a.id)}"><div class="archive-picture"><img src="${esc(a.cover||'./assets/baki-detail.webp')}" alt="${esc(a.title||'Publication BOJ.ART')}" loading="lazy"><span class="play-chip">${icon(a.type==='image'?'layers':'play')}</span></div><strong>${esc(a.title||'Publication BOJ.ART')}</strong><small>${esc(a.date||'')} · ${a.type==='image'?'Carrousel':a.duration?`${fmt(a.duration)} s`:'Vidéo'}${a.available===false?' · source indexée':''}</small></button>`).join('')||'<div class="empty-state">Aucune publication correspondante.</div>';}
async function render(animate=false){
  const commandDraft=!animate&&$('#wall-command-input')?{value:$('#wall-command-input').value,focused:document.activeElement===$('#wall-command-input'),start:$('#wall-command-input').selectionStart,end:$('#wall-command-input').selectionEnd}:null;
  $('#main').dataset.screen=ui.screen;
  const generation=++viewerGeneration;
  viewer?.dispose();viewer=null;disposeAtmosphere();
  if(store.integrityError||!getProject()){
    workshopSync?.stop();workshopSync=null;
    $('#main').innerHTML=renderIntegrityView({state:store.state,reason:store.integrityError||'Aucun dossier lisible dans le journal.',esc,icon});
    paintIntegrityGuard();paintContinuity();applyMotion();
    return integrityFailure();
  }
  paintIntegrityGuard();
  const evidence=ui.screen==='panorama'?projectEvidence.snapshot(getProject().id):null;
  $('#main').innerHTML=ui.screen==='panorama'?renderWall({store,archive,icon,esc,fmt,jobProgress,focus:ui.wallFocus,immersive:ui.immersive,receipt:lastReceipt,decision:buildControlDecision(store.state,getProject().id,{preparationReport:evidence.report,evidenceStatus:evidence.status})}):ui.screen==='atelier'?renderAtelier():ui.screen==='pilotage'?renderPilotage():renderCreation();
  if(ui.screen!=='panorama')$('#main').insertAdjacentHTML('beforeend',immersiveDock());
  document.documentElement.classList.toggle('is-immersive',ui.immersive);
  $$('[data-screen]').forEach(n=>{n.classList.toggle('active',n.dataset.screen===ui.screen);n.setAttribute('aria-current',n.dataset.screen===ui.screen?'page':'false');});
  icons();$('#main').classList.toggle('view-enter',animate&&ui.motion);mountAtmosphere();applyMotion();updateDisplayPresence();
  if(commandDraft&&$('#wall-command-input')){const input=$('#wall-command-input');input.value=commandDraft.value;if(commandDraft.focused){input.focus({preventScroll:true});input.setSelectionRange(commandDraft.start,commandDraft.end);}}
  if(ui.screen==='creation'&&ui.creationTab==='modele'){
    const piece=getPiece();
    try{
      const {createViewer}=await import('./lib/viewer.js');
      if(generation!==viewerGeneration)return{ok:false,message:'La vue a changé pendant son ouverture.'};
      const candidate=await createViewer($('#model-viewer'),{motion:ui.motion,onStatus:text=>{if(generation!==viewerGeneration)return;const n=$('#model-info');if(n)n.textContent=text;}});
      if(generation!==viewerGeneration){candidate.dispose();return{ok:false,message:'La vue a changé pendant son ouverture.'};}
      viewer=candidate;candidate.setWireframe(ui.wire);candidate.setAutoRotate(ui.auto);
      if(piece?.assetId){
        const stored=await readAsset(piece.assetId);
        if(generation!==viewerGeneration)return{ok:false,message:'Le contexte a changé pendant le chargement du STL.'};
        if(!stored){candidate.showDemo();$('#model-name').textContent='Fichier à réimporter';$('#model-info').textContent='Le binaire STL est absent. Le socle de démonstration reste visible.';return{ok:false,message:'Le binaire STL n’est pas disponible dans ce navigateur.'};}
        const result=candidate.loadSTL(stored.buffer,piece.unit||'mm');
        $('#model-info').textContent=`${result.dims.map(fmt).join(' × ')} mm · ${result.triangles.toLocaleString('fr-FR')} triangles · préparation non validée`;
      }else if(ui.exploded)candidate.explode(true);
      if(ui.section!==null)candidate.setSection?.(ui.section);
      return{ok:true,message:piece?.assetId?'STL chargé dans l’inspecteur 3D.':'Socle de démonstration affiché ; aucun STL importé pour cette pièce.'};
    }catch(error){
      if(generation!==viewerGeneration)return{ok:false,message:'La vue a changé pendant son ouverture.'};
      const container=$('#model-viewer');
      if(container)container.insertAdjacentHTML('beforeend',`<div class="viewer-error">${icon('cube')}<strong>Le rendu 3D n’est pas disponible ici.</strong><span>${esc(error.message||'WebGL indisponible dans ce navigateur.')}</span><button class="button" data-action="import">Importer un STL pour ses dimensions</button></div>`);
      return{ok:false,message:'L’inspecteur 3D n’a pas pu afficher le modèle : '+error.message};
    }
  }
  return{ok:true,message:ui.screen==='atelier'?'Parc et travaux simulés affichés.':ui.screen==='creation'?(ui.creationTab==='video'?'Studio vidéo ouvert ; lecture manuelle disponible.':'Scène des œuvres ouverte.'):'Vue ouverte.'};
}
function navigate(screen){if(!screenNames[screen])return Promise.resolve({ok:false,message:'Vue inconnue.'});ui.screen=screen;const q=new URL(location.href);q.searchParams.set('screen',screen);if(ui.station)q.searchParams.set('station',ui.station);history.replaceState(null,'',q);const drawing=render(true);if(ui.motion){const slash=$('.view-slash');slash.classList.remove('play');void slash.offsetWidth;slash.classList.add('play');}window.scrollTo({top:0,behavior:'instant'});return drawing;}

function toast(text){clearTimeout(toastTimer);const n=$('#toast');n.textContent=text;n.classList.add('visible');toastTimer=setTimeout(()=>n.classList.remove('visible'),4500);}
function disposeStudio(){studioController?.dispose();studioController=null;projectStudioController?.dispose();projectStudioController=null;projectStudioId=null;preparationController?.dispose();preparationController=null;preparationProjectId=null;decisionController?.dispose();decisionController=null;decisionProjectId=null;masterMissionProjectId=null;inquiryReadSequence++;pendingInquiry=null;inquiryViewProjectId=null;stlImportSequence++;pendingSTLImport=null;}
function openDrawer(title,html,kicker='BOJ.ART / LE DOSSIER'){const d=$('#drawer');disposeStudio();$$('video',d).forEach(v=>v.pause());backupReadSequence++;pendingRestore=null;d.classList.remove('signature-drawer','fleet-drawer','continuity-drawer','studio-drawer','project-studio-drawer','preparation-drawer','decision-drawer','inquiry-drawer');$('#drawer-title').textContent=title;$('#drawer-kicker').textContent=kicker;$('#drawer-content').innerHTML=html;icons(d);freezeDrawerForm();if(!d.open)d.showModal();}
function closeDrawer(){disposeStudio();backupReadSequence++;pendingRestore=null;$('#drawer').close();$$('video',$('#drawer')).forEach(v=>v.pause());if($('#drawer').classList.contains('inquiry-drawer'))$('#drawer-content').replaceChildren();}
$('#drawer').addEventListener('close',()=>{if(!$('#drawer').open){disposeStudio();if($('#drawer').classList.contains('inquiry-drawer'))$('#drawer-content').replaceChildren();}});

function formSnapshot(form){
  const project=store.state.projects.find(p=>p.id===(form.dataset.project||form.dataset.id));
  if(form.id==='project-form')return form.dataset.id?JSON.stringify(project&&Object.fromEntries(['name','kind','quantity','height','notes','status'].map(k=>[k,project[k]]))):null;
  if(form.id==='piece-form')return JSON.stringify(project?.pieces.find(p=>p.id===form.dataset.id)||null);
  if(form.id==='quote-form')return JSON.stringify(project?{revision:project.revision,quantity:project.quantity,quote:project.quote}:null);
  if(form.id==='story-form')return JSON.stringify(project?.story??null);
  if(form.id==='fleet-form')return String(store.getMachine(form.dataset.id)?.registry?.revision||0);
  if(form.id==='machine-form'){const m=store.getMachine(form.dataset.id);return JSON.stringify(m&&{name:m.name,material:m.material,volume:m.volume,tech:m.tech});}
  return null;
}
function freezeDrawerForm(){const form=$('#drawer form');if(!form)return;const snapshot=formSnapshot(form);if(snapshot!==null)form.dataset.baseSnapshot=snapshot;}
function keepDraftVisible(){
  if(projectStudioController||preparationController)return;
  const form=$('#drawer form');if(!form)return;
  const target=form.dataset.project||(form.id==='project-form'?form.dataset.id:null);
  const changed=form.dataset.baseSnapshot!==undefined&&form.dataset.baseSnapshot!==formSnapshot(form);
  const switched=target&&target!==getProject().id;
  let note=$('.form-context-note',form);
  if(!changed&&!switched){note?.remove();return;}
  if(!note){note=document.createElement('div');note.className='form-context-note';note.setAttribute('role','status');form.prepend(note);}
  const name=store.state.projects.find(p=>p.id===target)?.name||form.dataset.id||'cette fiche';
  note.innerHTML=(changed?'Cette fiche a changé depuis son ouverture. Votre saisie reste visible. Rechargez la version conservée avant d’enregistrer.':`Le projet actif a changé. Ce formulaire reste lié à « ${esc(name)} ».`)+(changed?'<div><button type="button" class="button button-small" data-action="reload-form">Recharger la fiche conservée</button></div>':'');
}
function reloadDrawerForm(){const form=$('#drawer form');if(!form)return;const id=form.dataset.id,projectId=form.dataset.project;
  if(form.id==='fleet-form')return openFleetMachine(id);
  if(form.id==='machine-form')return openMachine(id);
  if(form.id==='project-form')return openProject(id);
  if(projectId!==getProject().id){toast('Rouvrez le dossier cible pour retrouver cette fiche. Votre saisie reste visible.');return;}
  if(form.id==='piece-form')return openPiece(id);
  if(form.id==='quote-form')return openQuote();
  if(form.id==='story-form')return openStory();
}
function openFleet(){closeCommand();openDrawer('LE PARC.',renderFleetRegistry({machines:store.state.machines,esc,icon}),'BOJ.ART / RÉFÉRENTIEL DES MACHINES');$('#drawer').classList.add('fleet-drawer');}
function openFleetMachine(id){const machine=store.getMachine(id);if(!machine)return;closeCommand();openDrawer(id+' / LA FICHE.',renderFleetForm({machine,esc,icon}),'BOJ.ART / LE PARC');$('#drawer').classList.add('fleet-drawer');}
function openContinuity(){closeCommand();openDrawer('LE TRAVAIL CONTINUE.',renderContinuityView({store,status:continuityStatus,assetStatus:assetVaultStatus,esc,icon}),'BOJ.ART / SAUVEGARDES & REPRISE');$('#drawer').classList.add('continuity-drawer');void inspectAssetVault();}
function openInquiries(){closeCommand();openDrawer('LES DEMANDES.',renderInquiryDesk({projects:store.state.projects,esc,icon}),'BOJ.ART / ACQUISITION & QUALIFICATION');$('#drawer').classList.add('inquiry-drawer');}
function openInquiryDetail(projectId){
  const project=store.state.projects.find(item=>item.id===projectId);
  if(!project?.inquiry){toast('Cette demande n’est plus liée à un dossier accessible.');return;}
  if(getProject().id!==projectId){const selected=dispatch('SELECT_PROJECT',{id:projectId});if(!selected.ok)return;}
  closeCommand();openDrawer('DE LA DEMANDE À L’ÉTUDE.',renderInquiryDetail({project,esc,icon}),'BOJ.ART / LE DOSSIER TECHNIQUE');$('#drawer').classList.add('inquiry-drawer');inquiryViewProjectId=projectId;
}
async function previewInquiryFile(file){
  if(!file)return;
  const input=$('#inquiry-input');
  if(file.size>INQUIRY_MAX_BYTES){toast('L’export de demande dépasse 64 Kio.');input.value='';return;}
  closeCommand();openDrawer('LIRE LA DEMANDE.',`<p class="inquiry-loading" role="status">Lecture du document et vérification de son empreinte…</p>`,'BOJ.ART / APERÇU AVANT IMPORT');$('#drawer').classList.add('inquiry-drawer');
  const sequence=++inquiryReadSequence;
  try{
    const prepared=await inspectInquiryExport(await file.text(),store.state);
    if(sequence!==inquiryReadSequence||!$('#drawer').open)return;
    pendingInquiry=prepared;
    $('#drawer-content').innerHTML=renderInquiryPreview({prepared,esc,icon});icons($('#drawer'));
  }catch(error){if(sequence===inquiryReadSequence&&$('#drawer').open){$('#drawer-content').innerHTML=`<div class="inquiry-preview-result" role="alert">${esc(error.message)}</div><button type="button" class="button" data-action="inquiries">Revenir aux demandes</button>`;}}
  finally{input.value='';}
}
function confirmInquiryImport(form){
  if(!pendingInquiry)throw new Error('Relisez l’export avant de créer son dossier.');
  const prepared=pendingInquiry;
  const result=importInquiryProject(store,prepared,String(new FormData(form).get('technicalSummary')||''));
  if(!result.ok)throw new Error(result.message);
  openInquiryDetail(result.projectId);toast(result.message+(result.persisted?'':' Vérifiez la continuité avant de fermer ce poste.'));
}
function paintAssetVault(patch={}){assetVaultStatus={...assetVaultStatus,...patch};const panel=$('#asset-vault-panel');if(panel){panel.innerHTML=renderAssetVault({status:assetVaultStatus,esc,icon});icons(panel);}}
async function inspectAssetVault(){if(assetVaultStatus.busy)return;const status=await assetVault.status();paintAssetVault({...status,checked:true,message:status.available?`${status.fileCount} fichier(s) inscrits dans le coffre local. Les imports suivants peuvent y être conservés.`:'Le coffre local n’est pas disponible depuis cette adresse. Les exports des fichiers du navigateur restent utilisables.'});if(status.available)void projectEvidence.inspect(getProject().id,{force:true});}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
async function exportBrowserAssets(){
  if(assetVaultStatus.busy)return;
  paintAssetVault({busy:true,message:'Je rassemble les fichiers référencés et vérifie leurs empreintes…'});
  try{const state=JSON.parse(JSON.stringify(store.state)),journal=store.exportJournal();const result=await createBrowserAssetsBackup(state,{journal,readAsset,onProgress:({completed,total})=>paintAssetVault({message:`${completed} / ${total} STL vérifié(s) pour l’export.`})});downloadBlob(result.blob,'BOJ_ART_STL_'+new Date().toISOString().slice(0,10)+'.bojassets');paintAssetVault({message:`Archive STL préparée : ${result.summary.files} fichier(s), empreintes vérifiées. Conservez également la sauvegarde JSON du journal.`});}
  catch(error){paintAssetVault({message:error.message});toast(error.message);}
  finally{paintAssetVault({busy:false});}
}
async function syncAssetVault(){
  if(assetVaultStatus.busy||!assetVaultStatus.available)return;
  const references=referencedWorkshopAssets(store.state,store.exportJournal());let completed=0;
  paintAssetVault({busy:true,message:`Conservation des STL sur la tour · 0 / ${references.length}`});
  try{for(const reference of references){const record=await readAsset(reference.id,{expectedSha256:reference.sha256});if(!record)throw new Error('Le fichier '+reference.id+' est absent de ce poste.');await assetVault.putAsset(record);completed++;paintAssetVault({message:`${completed} / ${references.length} STL confirmé(s) par le coffre local.`});}const status=await assetVault.status();paintAssetVault({...status,message:`${completed} fichier(s) de cet historique ont été confirmés par le coffre. La sauvegarde du coffre contient leurs originaux.`});}
  catch(error){paintAssetVault({message:`${completed} / ${references.length} STL confirmé(s). ${error.message}`});toast('La conservation des STL demande une vérification.');}
  finally{paintAssetVault({busy:false});}
}
async function restoreAssetVault(file){
  if(!file||assetVaultStatus.busy||!assetVaultStatus.available)return;
  paintAssetVault({busy:true,message:'Vérification et restauration de l’archive STL…'});
  try{const result=await assetVault.restoreBackup(file);const status=await assetVault.status();paintAssetVault({...status,message:`${result.verifiedFiles} fichier(s) vérifié(s), ${result.added.length} ajouté(s), ${result.duplicates.length} déjà présent(s). Le journal JSON se restaure séparément.`});await projectEvidence.inspect(getProject().id,{force:true});refreshPreparation();}
  catch(error){paintAssetVault({message:error.message});toast(error.message);}
  finally{paintAssetVault({busy:false});$('#asset-backup-input').value='';}
}
function paintContinuity(status=continuityStatus){
  continuityStatus=status;
  if(store.integrityError){const footer=$('#save-status');if(footer){footer.dataset.syncMode='integrity';footer.innerHTML='<i class="status-dot"></i> Journal à vérifier · actions suspendues';footer.title=store.integrityError;}paintIntegrityGuard();return;}
  const footer=$('#save-status');if(footer){footer.dataset.syncMode=status.mode;footer.innerHTML='<i class="status-dot"></i> '+esc(continuityLabel(status)+(status.pending?' · '+status.pending+' en attente':''));footer.title=status.message;}
  const panel=$('#continuity-status');if(panel)panel.innerHTML=renderContinuityStatus({status,esc,icon});
  const count=$('[data-journal-count]');if(count)try{count.textContent=store.exportJournal().operations.length.toLocaleString('fr-FR');}catch{count.textContent='À vérifier';if(store.integrityError)render(false);}
}
function startWorkshopSync(){if(workshopSync||store.integrityError||!getProject())return;workshopSync=createWorkshopSync({store,onStatus:paintContinuity});paintContinuity(workshopSync.status);void workshopSync.inspect();}
async function exportBackup(){
  try{const backup=await createWorkshopBackup(store.exportJournal(),{sourceInstanceId:'browser'});downloadJson(backup,'BOJ_ART_Sauvegarde_'+new Date().toISOString().slice(0,10)+'.json');toast('Sauvegarde du journal préparée. Conservez aussi vos fichiers STL.');}
  catch(error){const node=$('#continuity-error');if(node)node.textContent=error.message;toast(error.message);}
}
async function previewBackup(file){
  if(!file)return;const seq=++backupReadSequence;pendingRestore=null;
  try{
    if(file.size>16777216)throw new Error('La sauvegarde dépasse 16 Mio.');
    const inspection=await inspectWorkshopBackup(await file.text());
    if(seq!==backupReadSequence||!$('#backup-preview'))return;
    pendingRestore=inspection;$('#continuity-error').textContent='';$('#backup-preview').innerHTML=renderBackupPreview({inspection,store,filename:file.name,esc,icon});$('#backup-preview').scrollIntoView?.({behavior:ui.motion?'smooth':'instant',block:'nearest'});
  }catch(error){if(seq===backupReadSequence&&$('#continuity-error'))$('#continuity-error').textContent=error.message;}
  finally{$('#backup-input').value='';}
}
function restoreBackup(){
  if(!pendingRestore)return;
  try{const outcome=store.mergeJournal(pendingRestore.journal,{allowEmptyAdoption:store.exportJournal().operations.length===0});pendingRestore=null;openContinuity();toast(`${outcome.added} opération(s) ajoutée(s), ${outcome.duplicates} doublon(s) reconnus.${outcome.rejected.length?' Des conflits restent à examiner.':''}`);}
  catch(error){const node=$('#continuity-error');if(node)node.textContent=error.message;}
}

function field(label,name,value,type='text',extra=''){return `<label class="field">${label}<input name="${name}" type="${type}" value="${esc(value??'')}" ${extra}></label>`;}
function openProject(id=getProject().id,isNew=false){const p=store.state.projects.find(p=>p.id===id)||getProject();openDrawer(isNew?'NOUVEAU DOSSIER.':'LE BRIEF.',`<form id="project-form" data-id="${isNew?'':esc(p.id)}"><div class="form-grid">${field('Nom du projet','name',isNew?'':p.name,'text','required maxlength="80"')}${field('Type de projet','kind',isNew?'Sur mesure':p.kind,'text','required maxlength="40"')}${field('Quantité du lot','quantity',isNew?1:p.quantity,'number','required min="1" max="10000" step="1"')}${field('Hauteur souhaitée (mm)','height',isNew?'':p.height,'number','min="1" max="100000" step="0.1" placeholder="À préciser"')}<label class="field full">Notes du brief<textarea name="notes" maxlength="8000">${esc(isNew?'':p.notes)}</textarea></label><label class="field full">Étape du dossier<select name="status">${['Étude','Chiffré','Production','Terminé'].map(s=>`<option ${!isNew&&p.status===s?'selected':''}>${s}</option>`).join('')}</select></label></div><p class="badge-box">La hauteur du brief ne redimensionne pas les fichiers STL. La quantité modifiée rend le chiffrage précédent à recalculer.</p><div class="form-actions"><button class="button button-red" type="submit">${icon('save')} ${isNew?'Créer le dossier':'Enregistrer'}</button><button class="button" type="button" data-action="close-dialog">Fermer</button></div><div class="inline-error" role="alert" id="form-error"></div></form>`);}
function openPiece(id=getPiece()?.id){const p=getProject(),piece=p.pieces.find(x=>x.id===id);if(!piece)return;dispatch('SELECT_PIECE',{id:piece.id});openDrawer(piece.name.toUpperCase(),`<form id="piece-form" data-project="${esc(p.id)}" data-id="${esc(piece.id)}"><div class="form-grid">${field('Nom de la pièce','name',piece.name,'text','required maxlength="80"')}<label class="field">Procédé<select name="tech"><option value="resin" ${piece.tech==='resin'?'selected':''}>Résine UV</option><option value="fdm" ${piece.tech==='fdm'?'selected':''}>FDM</option></select></label><label class="field full">Machine prévue<select name="machine"><option value="">À affecter</option>${store.state.machines.map(m=>`<option value="${m.id}" ${m.id===piece.machine?'selected':''}>${m.id} — ${techName(m.tech)}</option>`).join('')}</select></label>${piece.assetId?`<label class="field full">Unité interprétée du fichier<select name="unit"><option value="mm" ${piece.unit!=='inch'?'selected':''}>Millimètre (mm)</option><option value="inch" ${piece.unit==='inch'?'selected':''}>Pouce (25,4 mm)</option></select></label>`:''}</div><div class="form-section"><h3>${piece.assetId?'Fichier STL importé':'Géométrie du dossier de démonstration'}</h3><div class="data-row"><span>Dimensions hors supports</span><strong>${piece.dims.map(fmt).join(' × ')} mm</strong></div>${piece.triangles?`<div class="data-row"><span>Triangles</span><strong>${piece.triangles.toLocaleString('fr-FR')}</strong></div>`:''}<div class="data-row"><span>Révision</span><strong>${piece.revision||1}</strong></div><div class="data-row"><span>Préparation</span><span class="tag tag-amber">À valider</span></div></div><p class="badge-box">La vérification du volume brut ne valide ni les supports, ni le drainage, ni la solidité. Une affectation reste un brouillon de préparation.</p><div class="form-actions"><button class="button button-red" type="submit">Enregistrer</button><button class="button" data-action="open-piece-3d" type="button">${icon('cube')} Voir en 3D</button></div><div id="form-error" class="inline-error" role="alert"></div></form>`);}
function openQuote(){const p=getProject(),q=p.quote?.inputs||{};openDrawer('LE JUSTE CHIFFRAGE.',`<p class="small muted">${esc(p.name)} · tous les coûts ci-dessous portent sur le lot complet de ${p.quantity||1} exemplaire${p.quantity>1?'s':''}.</p><form id="quote-form" data-project="${esc(p.id)}"><div class="form-grid form-section">${field('Matières du lot (€)','material',q.material??'','number','required min="0" step="0.01"')}${field('Travail humain du lot (h)','hours',q.hours??'','number','required min="0" step="0.1"')}${field('Coût horaire (€ / h)','rate',q.rate??'','number','required min="0" step="0.01"')}${field('Autres coûts du lot (€)','other',q.other??'','number','required min="0" step="0.01"')}${field('Marge visée (% du prix)','margin',q.margin??30,'number','required min="0" max="99" step="0.1"')}${field('Commission (% du prix)','fee',q.fee??0,'number','required min="0" max="99" step="0.1"')}</div><div class="form-actions"><button class="button button-red" type="submit">${icon('chart')} Calculer & enregistrer</button></div><div id="quote-result">${p.quote?.result?quoteResult(p.quote.result):''}</div><div id="form-error" class="inline-error" role="alert"></div><p class="micro-copy form-section">Prix = coût du lot ÷ (1 − marge − commission). Brouillon de calcul, fiscalité et TVA à préciser selon l’activité.</p></form>`);}
function quoteResult(result){return `<div class="metric-row"><div class="metric"><span>Coût du lot</span><strong>${euro(result.cost)}</strong></div><div class="metric highlight"><span>Prix cible du lot</span><strong>${euro(result.price)}</strong></div></div><p class="small muted" style="margin-top:12px">Soit ${euro(result.unitPrice)} par exemplaire · brouillon enregistré.</p>`;}
function openStory(){const p=getProject();openDrawer('LE GESTE. LE RÉCIT.',`<video class="media-player" src="./assets/studio-loop.mp4" poster="./assets/baki-detail.webp" controls playsinline muted preload="metadata"></video><form id="story-form" data-project="${esc(p.id)}" class="form-section"><label class="field">Scénario du prochain montage<textarea name="text" rows="7" maxlength="4000">${esc(p.story||'01 — Accroche : l’œuvre finie, un détail fort.\n02 — Le geste : préparation, impression ou peinture.\n03 — La transformation : du brut à la finition.\n04 — La révélation : œuvre entière et signature BOJ.ART.')}</textarea></label><div class="form-actions"><button class="button button-red" type="submit">${icon('save')} Enregistrer le scénario</button></div><p class="micro-copy form-section">Extrait d’origine conservé. Ce formulaire prépare le montage ; il n’exporte pas de nouvelle vidéo et ne publie pas sur les réseaux.</p></form>`);}
function openMachine(id=ui.machine){const m=store.getMachine(id);if(!m)return;openDrawer(`${m.id} / LA RESSOURCE.`,`<form id="machine-form" data-id="${m.id}"><div class="form-grid">${field('Dénomination','name',m.name||m.id,'text','required maxlength="80"')}${field('Matière prévue','material',m.material,'text','required maxlength="80"')}${field('Volume X (mm)','x',m.volume[0],'number','required min="1" max="10000" step="0.1"')}${field('Volume Y (mm)','y',m.volume[1],'number','required min="1" max="10000" step="0.1"')}${field('Volume Z (mm)','z',m.volume[2],'number','required min="1" max="10000" step="0.1"')}<label class="field">Procédé<select name="tech"><option value="resin" ${m.tech==='resin'?'selected':''}>Résine UV</option><option value="fdm" ${m.tech==='fdm'?'selected':''}>FDM</option></select></label></div><p class="badge-box">Cette fiche décrit une ressource de démonstration. Enregistrer ses caractéristiques ne connecte pas de machine et ne qualifie pas un profil d’impression.</p><div class="form-actions"><button class="button button-red" type="submit">Enregistrer la fiche</button></div><div class="inline-error" id="form-error" role="alert"></div></form>`,'BOJ.ART / PARC DE DÉMONSTRATION');}
function openPlan(){const p=getProject();openDrawer('RÉPARTIR LE PROJET.',`<p class="small muted">${esc(p.name)} · ${p.pieces.length} pièces à répartir dans le parc de démonstration.</p><div class="form-section">${p.pieces.map(piece=>`<div class="data-row"><span>${esc(piece.name)}</span><span>${techTag(piece.tech)} · ${piece.dims.map(fmt).join(' × ')} mm</span></div>`).join('')}</div><p class="badge-box">La simulation respecte le procédé et l’enveloppe brute, puis répartit la charge. Les profils, orientations, supports et matières doivent être qualifiés avant une fabrication réelle.</p><div class="form-actions"><button class="button button-red" data-action="confirm-plan">${icon('layers')} Simuler la répartition</button></div><div id="plan-result" role="status"></div>`);}
function openScreens(){
  const peers=displayBus?.peers()||[];
  openDrawer('TROIS ÉCRANS. UNE TOUR.',`<p class="small muted">Ouvrez une fenêtre par moniteur. Depuis Jarvis, un aperçu peut être envoyé vers la fenêtre Création ; le parc s’ouvre sur Atelier. Les vues confirment leur affichage au poste central.</p><div class="screens-presence" data-screens-status role="status"></div><div class="screens-list">${[['atelier','01','À gauche · Atelier','Machines, pièces et préparation'],['pilotage','02','Au centre · Jarvis','Intention, mission et administration'],['creation','03','À droite · Création','Œuvres, coupes 3D et modèles']].map(([role,number,title,description])=>{const here=ui.station===role,online=here||peers.some(p=>p.role===role);return `<a class="screen-link" href="?screen=${role}&station=${role}&immersive=1" target="_blank" rel="noopener"><span>${number}</span><span><strong>${title}</strong><small>${description}</small><b class="screen-presence-label ${online?'online':''}">${here?'CETTE FENÊTRE':online?'FENÊTRE DÉTECTÉE':'OUVRIR CETTE VUE'}</b></span>${icon('arrowUp')}</a>`;}).join('')}</div><div class="form-actions"><button class="button button-red" data-action="display-test">${icon('cube')} Envoyer l’aperçu à droite</button><button class="button" data-action="display-local">Afficher le modèle ici</button><button class="button" data-action="open-panorama">${icon('screens')} Vue d’ensemble</button></div><p class="micro-copy form-section">Déplacez les fenêtres sur les moniteurs choisis, puis activez le plein écran du navigateur. La liaison fonctionne entre les fenêtres de ce même navigateur. La présence détectée indique une fenêtre ouverte ; elle ne détecte pas le branchement physique d’un moniteur.</p>`,'BOJ.ART / COORDINATION DES ÉCRANS');
  updateDisplayPresence();
}

function openSettings(){
  openDrawer('LE POSTE CENTRAL.',`<div class="form-actions"><button class="button button-red" data-action="continuity">${icon('save')} Sauvegardes & reprise</button><button class="button" data-action="fleet">${icon('printer')} Référentiel des machines</button><button class="button" data-action="decisions">${icon('spark')} Bureau de décisions</button></div>
  <div class="setting-row"><div><strong>Fichiers & dossiers</strong><p>Conservation dans ce navigateur ; journal et coffre disponibles avec le service de la tour.</p></div><span class="tag tag-green">NAVIGATEUR ACTIF</span></div>
  <div class="setting-row"><div><strong>Inspection des STL</strong><p>Lecture du fichier, empreinte, dimensions et comparaison au parc déclaré.</p></div><span class="tag tag-green">DISPONIBLE</span></div>
  <div class="setting-row"><div><strong>Jev : décisions et visuels</strong><p>Bureau de comparaison et régie prêts. Le service TypeSafe se configure sur la tour.</p></div><span class="tag tag-amber">FOURNISSEUR À RACCORDER</span></div>
  <div class="setting-row"><div><strong>Voix et compréhension locales</strong><p>Microphone, transcription et modèle à installer et évaluer sur le PC dédié.</p></div><span class="tag tag-amber">À RACCORDER</span></div>
  <div class="setting-row"><div><strong>Parc d’imprimantes</strong><p>Profils, slicing, transfert et qualification par machine.</p></div><span class="tag tag-amber">À RACCORDER</span></div>
  <div class="setting-row"><div><strong>Réseaux sociaux & ventes</strong><p>Publication et commandes externes.</p></div><span class="tag tag-amber">À RACCORDER</span></div>
  <div class="form-section"><h3>Affichage & mouvement</h3><button class="button" data-action="motion">${icon('motion')} ${ui.motion?'Réduire les animations':'Activer les animations'}</button></div>
  <div class="form-section"><h3>Conserver l’ensemble du travail</h3><p class="small muted">« Sauvegardes & reprise » fournit le journal JSON et une archive des originaux STL. Conservez les deux exports ensemble. L’export descriptif ci-dessous résume les dossiers et leurs affectations.</p><div class="form-actions"><button class="button" data-action="export-state">${icon('save')} Export descriptif des dossiers</button></div></div>`);
}
function openStudio(){closeCommand();openDrawer('LE STUDIO.',renderStudioView({esc,icon}),'BOJ.ART / SIGNATURE & CONTENUS');$('#drawer').classList.add('studio-drawer');studioController=mountStudio($('#drawer'),{motion:ui.motion});}
function refreshProjectStudio(){
  if(!projectStudioController||!projectStudioId)return;
  const project=store.state.projects.find(item=>item.id===projectStudioId);
  projectStudioController.refreshContext?.({project:project||null,activeProjectId:store.state.projectId,archive});
}
function openProjectStudio(projectId=getProject().id,planId=null,version=null){
  const project=store.state.projects.find(item=>item.id===projectId);
  if(!project){toast('Le dossier cible est introuvable.');return;}
  closeCommand();openDrawer('LES CONTENUS.',renderProjectStudio({project,archive,esc,icon,planId,version}),'BOJ.ART / STUDIO DU PROJET');$('#drawer').classList.add('project-studio-drawer');projectStudioId=project.id;
  projectStudioController=mountProjectStudio($('#drawer'),{project,archive,motion:ui.motion,activeProjectId:store.state.projectId,
    onSave:payload=>{
      if(payload?.projectId!==project.id)return{ok:false,message:'Le plan ne correspond pas au dossier ouvert.'};
      const result=dispatch('SAVE_EDIT_PLAN',payload);
      if(result?.ok===false){refreshProjectStudio();return result;}
      const target=store.state.projects.find(item=>item.id===project.id);
      const record=projectEditPlans(target).find(item=>item.id===payload.planId);
      const saved=latestEditVersion(record);
      if(!record||!saved)return{ok:false,message:'La version n’a pas pu être retrouvée dans le dossier.'};
      return{...result,project:target,record,planId:record.id,revision:saved.revision};
    },
    onExport:request=>{
      try{
        if(request?.projectId!==project.id||!Number.isSafeInteger(request.version)||request.version<1||typeof request.expectedVersionId!=='string')throw new Error('Choisissez une version conservée dans ce dossier.');
        store.refresh();
        const target=store.state.projects.find(item=>item.id===project.id);
        const record=projectEditPlans(target).find(item=>item.id===request.planId);
        if(!target||!record)throw new Error('Ce plan n’est pas présent dans le dossier cible.');
        const selected=record.versions.find(item=>item.revision===request.version);
        if(!selected||selected.operationId!==request.expectedVersionId)throw new Error('Cette version a changé depuis son affichage. Consultez-la dans l’historique avant de l’exporter.');
        const content=exportEditPlan(target,record,request.version);
        const fileId=record.id.replace(/[^A-Za-z0-9_-]/g,'_');
        downloadJson(content,`BOJ_ART_Edit_${fileId}_v${request.version}.json`);
        return{ok:true,message:`Version ${request.version} exportée avec ses sources. Le film reste à monter.`};
      }catch(error){return{ok:false,message:error.message};}
    }
  });
}
function refreshPreparation(){
  if(!preparationController||!preparationProjectId)return;
  const project=store.state.projects.find(item=>item.id===preparationProjectId);
  preparationController.refreshContext({project:project||null,machines:store.state.machines,activeProjectId:store.state.projectId});
}
function preparationContext(report){return preparationReportContext(report);}
function openPreparation(projectId=getProject().id,selection=null){
  const project=store.state.projects.find(item=>item.id===projectId);
  if(!project){toast('Le dossier cible est introuvable.');return;}
  const report=projectEvidence.report(project.id);
  closeCommand();openDrawer('LA PRÉPARATION.',renderPreparationView({project,machines:store.state.machines,report,esc,icon}),'BOJ.ART / LA PIÈCE & LA MACHINE');
  $('#drawer').classList.add('preparation-drawer');preparationProjectId=project.id;
  preparationController=mountPreparationView($('#drawer'),{
    project,machines:store.state.machines,report,activeProjectId:store.state.projectId,motion:ui.motion,readAsset,
    inspectSTL:async(buffer,unit)=>(await import('./lib/viewer.js')).inspectSTL(buffer,unit),
    createViewport:async(container,options)=>(await import('./lib/preparation-viewport.js')).createPreparationViewport(container,options),
    analyze:(target,machines,assetEvidence)=>inspectDeclaredPreparation({projects:[target],machines},target.id,{assetEvidence}),
    onImport:request=>{
      if(request?.projectId!==project.id)return{ok:false,message:'Le fichier ne correspond pas au dossier ouvert.'};
      const target=store.state.projects.find(item=>item.id===project.id),piece=target?.pieces.find(item=>item.id===request.pieceId);
      if(!piece)return{ok:false,message:'La pièce cible est introuvable.'};
      const unit=request.unit??piece.unit??'mm';
      if(!['mm','inch'].includes(unit))return{ok:false,message:'Choisissez explicitement millimètres ou pouces pour ce fichier.'};
      preparationImportTarget={projectId:project.id,pieceId:piece.id,pieceRevision:piece.revision,assetId:piece.assetId??null,unit};
      const input=$('#preparation-stl-input');input.value='';input.click();
      return{ok:true,message:'Sélectionnez le STL à associer à cette pièce.'};
    },
    onOpenFleet:({machineId}={})=>machineId?openFleetMachine(machineId):openFleet(),
    onReport:({report:inspected,checking,unavailable})=>{if(!checking&&!unavailable&&projectEvidence.absorb(inspected)&&ui.screen==='pilotage'&&ui.pilotTab==='controle')render(false);},
    onDecision:snapshot=>openDecisionDesk(project.id,{domain:'preparation',...snapshot.selection}),
    onExport:({report:inspected,selection}={})=>{
      try{
        if(inspected?.project?.id!==project.id)throw new Error('Le rapport ne correspond pas au dossier ouvert.');
        store.refresh();
        const current=inspectDeclaredPreparation(store.state,project.id);
        if(preparationContext(inspected)!==preparationContext(current))throw new Error('Les pièces ou les fiches machines ont changé. Attendez la mise à jour du rapport avant de l’exporter.');
        const content=exportDeclaredPreparation(inspected,selection,Date.now());
        downloadJson(content,`BOJ_ART_Preparation_${project.id.replace(/[^A-Za-z0-9_-]/g,'_')}.json`);
        return{ok:true,message:'Rapport dimensionnel exporté avec ses mesures et sa sélection. Les STL restent à conserver séparément.'};
      }catch(error){refreshPreparation();return{ok:false,message:error.message};}
    }
  });
  if(selection)preparationController.select(selection);
}
function openIdentity(){closeCommand();openDrawer('LA SIGNATURE.',renderSignatureView({esc,icon}),'BOJ.ART / IDENTITÉ & MOUVEMENT');$('#drawer').classList.add('signature-drawer');}
function openDecisionDesk(projectId=getProject().id,initial={}){
  const project=store.state.projects.find(item=>item.id===projectId);
  if(!project){toast('Le dossier cible est introuvable.');return;}
  const report=projectEvidence.report(projectId);
  closeCommand();openDrawer('CONSEILS & JEV.',renderDecisionDesk({project,report,provider:{checked:false,configured:false,connected:false},initial,esc,icon}),'BOJ.ART / LE BUREAU DES DÉCISIONS');
  $('#drawer').classList.add('decision-drawer');decisionProjectId=projectId;
  decisionController=mountDecisionDesk($('#drawer'),{projectId,initial,motion:ui.motion,
    getContext:()=>{const current=store.state.projects.find(item=>item.id===projectId);if(!current)return{project:null,report:null,activeProjectId:store.state.projectId,evidenceStatus:'unavailable'};const evidence=projectEvidence.snapshot(projectId);return{project:current,report:evidence.report,activeProjectId:store.state.projectId,evidenceStatus:evidence.status};},
    getProviderStatus:getDecisionProviderStatus,requestDecision:requestProjectDecision,
    onInspect:target=>{
      const current=store.state.projects.find(item=>item.id===projectId);
      if(!target||target.projectId!==projectId||!current)return{ok:false,message:'Le conseil ne correspond plus au dossier ouvert.'};
      if(['inspect_orientation','inspect_piece'].includes(target.action)){
        if(!current.pieces.some(piece=>piece.id===target.pieceId))return{ok:false,message:'La pièce cible est introuvable.'};
        openPreparation(projectId,{pieceId:target.pieceId,machineId:target.machineId,orientationId:target.orientationId});
      }else if(target.action==='inspect_machine'){
        if(!store.state.machines.some(machine=>machine.id===target.machineId))return{ok:false,message:'La machine cible est introuvable.'};
        openFleetMachine(target.machineId);
      }else if(target.action==='inspect_edit'){
        const record=projectEditPlans(current).find(item=>item.id===target.planId);
        if(!record||latestEditVersion(record).revision!==target.planRevision)return{ok:false,message:'La version du plan a changé. Relisez le conseil.'};
        openProjectStudio(projectId,target.planId,target.planRevision);
      }else if(target.action==='create_edit'||target.action==='prepare_series'){
        openProjectStudio(projectId);
        if(!projectStudioController?.prepareSeries(target.series||'oeuvres'))return{ok:false,message:'Le brouillon n’a pas pu être ouvert dans ce dossier.'};
      }else return{ok:false,message:'Cette action n’est pas disponible dans le bureau des décisions.'};
      return{ok:true,message:'L’élément du dossier est ouvert pour examen.'};
    }
  });
  void projectEvidence.inspect(projectId);
}
function openArt(id){const map={atelier:['LE GESTE.','atelier.webp',artSource.atelier,'22 s · peinture dans l’atelier'],dragon:['LA COMPOSITION.','dragon.webp',artSource.baki,'42 s · extrait du portfolio'],throne:['LE DÉTAIL.','throne.webp',artSource.baki,'46,5 s · extrait du portfolio']};const a=map[id];if(!a)return;openDrawer(a[0],`<img class="media-image" src="./assets/${a[1]}" alt="Œuvre ou geste original de BOJ.ART"><div class="media-detail"><p>${a[3]}</p><p>Image extraite d’une vidéo publique de BOJ.ART, conservée comme référence de l’identité de l’atelier.</p><a class="source-link" href="${a[2]}" target="_blank" rel="noopener">Voir la publication d’origine</a></div>`,'BOJ.ART / RÉFÉRENCE ORIGINALE');}
function openMedia(id){const a=archive.find(a=>a.id===id);if(!a)return;const visual=a.preview?`<video class="media-player" src="${esc(a.preview)}" poster="${esc(a.cover||'./assets/baki-detail.webp')}" playsinline controls preload="metadata"></video>`:`<img class="media-image" src="${esc(a.cover||'./assets/baki-detail.webp')}" alt="Couverture de la publication">`;openDrawer('LA VIDÉOTHÈQUE.',`${visual}<div class="media-detail"><h3>${esc(a.title)}</h3><p>${esc(a.date||'')} · ${a.type==='image'?'Carrousel photo':a.duration?`${fmt(a.duration)} secondes`:'Vidéo'}</p><p>${a.preview?'Extrait de consultation. Le fichier original et ses métadonnées sont conservés dans l’archive livrée.':a.available?'Publication référencée dans l’archive livrée.':'Publication indexée ; média original non récupéré à ce stade.'}</p><p>${esc(a.description||'').slice(0,800)}</p><a class="source-link" href="${esc(a.url)}" target="_blank" rel="noopener">Ouvrir la publication TikTok</a></div>`,'BOJ.ART / PUBLICATION ORIGINALE');}
function openCommand(){if(store.integrityError){toast(store.integrityError);return;}$('#command-dialog').showModal();setTimeout(()=>$('#command-input').focus(),70);}
async function executeCommand(raw){store.refresh();if(store.integrityError||!getProject()){const result=integrityFailure();toast(result.message);return result;}const text=raw.trim(),normalized=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/œ/g,'oe');if(!text)return;
  if(/^repete[.!?]*$/.test(normalized)){if(lastReceipt)$('#command-receipt').textContent=lastReceipt;else $('#command-receipt').textContent='Aucune commande à relire.';return;}
  const p=getProject(),sequence=++intentSequence,answer=answerMissionQuestion(text,currentMasterMission(p.id));let receipt;
  if(answer){receipt=answer;}
  else if(/\b(ne|pas|jamais|si|peut|pourrait|hypothese)\b/.test(normalized)){receipt='Aucune action de modification n’a été effectuée. La demande reste à préciser.';}
  else if(/pause|reprends|reprendre|reprise/.test(normalized)){const targets=[...normalized.matchAll(/\bp\s*0?([1-8])\b/g)].map(m=>'P0'+m[1]);const unique=[...new Set(targets)];if(unique.length!==1||/\b(et|toutes|tous|imprimantes)\b/.test(normalized)){receipt='Indiquez une seule machine, par exemple : « Mets en pause P03 ». Aucune action effectuée.';}else{const id=unique[0],j=currentJob(id),wantsPause=/pause/.test(normalized);if(!j||j.status==='queued'||jobProgress(j)>=100){receipt=`${id} : aucune simulation active à ${wantsPause?'suspendre':'reprendre'}.`;}else if(wantsPause&&j.status==='paused'||!wantsPause&&j.status==='running'){receipt=`${id} : simulation déjà ${wantsPause?'en pause':'en cours'}. Aucune nouvelle action.`;}else{const result=dispatch('TOGGLE_MACHINE',{id});receipt=result?.ok===false?result.message:`${id} : simulation ${wantsPause?'mise en pause':'reprise'}. Projet d’origine : ${store.state.projects.find(project=>project.id===j.projectId)?.name||j.projectId}.`;}}}
  else if(/\bjev\b/.test(normalized)){closeCommand();if(/affiche|montre|ecran|visuel|scene/.test(normalized))receipt=await performVisualRequest(text.replace(/\bjev\b[ ,:]*/i,''),{provider:'typesafe',log:false});else{openDecisionDesk(p.id,{domain:/orientation|volume/.test(normalized)?'preparation':/edit|montage|contenu/.test(normalized)?'editorial':'attention'});receipt='Conseils & Jev affichés : priorités, orientations et intentions de montage du dossier.';}}
  else if(/parc|referentiel|fiche machine/.test(normalized)){closeCommand();openFleet();receipt='Référentiel des machines affiché : identité, profils et essais.';}
  else if(/sauvegard|continuite|restaur/.test(normalized)){closeCommand();openContinuity();receipt='Sauvegardes et reprise affichées.';}
  else if(/prepare les pieces|preparer les pieces|preparation des pieces|etabli|encombrement|compatibilite dimensionnelle/.test(normalized)){closeCommand();openPreparation();receipt='Établi affiché : STL relus et volumes déclarés des machines, pièce par pièce.';}
  else if(/contenus du projet|mes contenus|studio du projet|montage du projet|plans? de montage|prochain edit/.test(normalized)){closeCommand();openProjectStudio();receipt='Studio du projet affiché avec ses plans et versions.';}
  else if(/studio|signature|identite|edit/.test(normalized)){closeCommand();openStudio();receipt='Studio de signature BOJ.ART affiché.';}
  else if(/regie|visuels?/.test(normalized)){openVisualDesk();receipt='Régie visuelle affichée : scènes, écran de destination et choix avec Jev.';}
  else if(/orchestre|orchestr|coordonne|de a a z/.test(normalized)){receipt=await runOrchestration(p.id);}
  else if(/tout|controle|capacites|domaines/.test(normalized)){openControl();receipt='Les huit domaines et leurs opérations sont affichés.';}
  else if(/devis|chiffr|cout|marge/.test(normalized)){closeCommand();openQuote();receipt='Chiffrage du lot affiché : renseignez les coûts du projet.';}
  else if(/scenario|montage|contenu/.test(normalized)){closeCommand();openStory();receipt='Scénario lié au projet affiché.';}
  else if(/demande|prospect|acquisition|vitrine/.test(normalized)){openInquiries();receipt='Demandes client affichées : import, qualification et accès à la vitrine.';}
  else if(/client|vente|catalogue|boutique|commerce/.test(normalized)){openControl('commerce');receipt='Commerce affiché : dossiers, chiffrage et raccordements pour la vente.';}
  else if(/stock|matiere|maintenance|ressource/.test(normalized)){openControl('ressources');receipt='Ressources affichées : machines et raccordement des stocks.';}
  else if(/systeme|sauvegarde|connexion|services|voix/.test(normalized)){openControl('systeme');receipt='Système affiché : export, journal, écrans et connexions.';}
  else if(/robot|prototype/.test(normalized)){openControl('robotique');receipt='Robotique affichée : dossier de prototype et futures interfaces matérielles.';}
  else if(/reseaux|tiktok|publie|publication/.test(normalized)){openControl('contenus');receipt='Contenus affichés : vidéothèque, scénario et état des connexions sociales.';}
  else if(/mission complete|mission globale/.test(normalized)){openMasterMission();receipt='Mission complète affichée : création, fabrication, contenus et commerce.';}
  else if(/mission|prepar|slic|imprime|impression|repart/.test(normalized)){openMission();receipt='Préparation affichée : fichiers, compatibilités et raccordements à compléter. Aucun slicing ni démarrage physique effectué.';}
  else if(/tour|panorama|ensemble|trois ecrans|3 ecrans/.test(normalized)){navigate('panorama');receipt='Tour de contrôle affichée : Atelier, Jarvis et Création.';}
  else if(/socle/.test(normalized)){const piece=p.pieces.find(x=>/socle/i.test(x.name));receipt=piece?await presentView('model',{pieceId:piece.id,remoteOnly:/\b(droite?|ecran 0?3)\b/.test(normalized)}):`Aucun socle dans ${p.name}.`;}
  else if(/atelier|production|imprimante/.test(normalized)){receipt=await presentView('production',{remoteOnly:/gauche|ecran 0?1/.test(normalized)});}
  else if(/film|oeuvre/.test(normalized)&&/\b(droite?|ecran 0?3)\b/.test(normalized)){receipt=await presentView(/film/.test(normalized)?'film':'art',{remoteOnly:true});}
  else if(/video|archive|videotheque/.test(normalized)){ui.pilotTab='archive';navigate('pilotage');receipt=`Vidéothèque affichée : ${archive.length} publications indexées.`;}
  else if(/signature|identite/.test(normalized)){$('#command-dialog').close();openIdentity();receipt='Direction artistique BOJ.ART affichée.';}
  else if(/creation|modele|3d|eclate/.test(normalized)){receipt=await presentView('model',{exploded:/eclate/.test(normalized),remoteOnly:/\b(droite?|ecran 0?3)\b/.test(normalized)});}
  else if(/dossier/.test(normalized)){closeCommand();ui.pilotTab='dossiers';navigate('pilotage');receipt='Pilotage des dossiers affiché.';}
  else if(/jarvis|pilotage|commandes|administration/.test(normalized)){closeCommand();ui.pilotTab='controle';navigate('pilotage');receipt='Jarvis au centre de l’atelier : huit domaines accessibles.';}
  else receipt='Commande non reconnue. Essayez « Affiche l’atelier », « Montre le socle » ou « Ouvre les vidéos ».';
  if(sequence!==intentSequence){dispatch('LOG',{projectId:p.id,message:`Jarvis — retour d’une demande précédente : ${receipt}`});return;}
  setDisplayReceipt(receipt);dispatch('LOG',{projectId:p.id,message:`Jarvis — ${text} → ${receipt}`});
}
function applyMotion(){document.documentElement.classList.toggle('reduced-motion',!ui.motion);document.documentElement.classList.toggle('motion-running',ui.motion);$('#motion-button').innerHTML=icon('motion')+`<span>Motion ${ui.motion?'activée':'réduite'}</span>`;viewer?.setMotion(ui.motion);motionStages.forEach(s=>s.setMotion(ui.motion));studioController?.setMotion(ui.motion);projectStudioController?.setMotion(ui.motion);preparationController?.setMotion(ui.motion);decisionController?.setMotion?.(ui.motion);if(!ui.motion)$$('video').forEach(v=>v.pause());syncAmbient();$$('[data-action="immersive"]').forEach(n=>n.setAttribute('aria-pressed',ui.immersive));}
async function openAssetDB(){if(!dbPromise)dbPromise=new Promise((resolve,reject)=>{const req=indexedDB.open('bojart-files',1);req.onupgradeneeded=()=>req.result.createObjectStore('assets',{keyPath:'id'});req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});return dbPromise;}
async function writeBrowserAsset(record){const db=await openAssetDB();return new Promise((resolve,reject)=>{const tx=db.transaction('assets','readwrite');tx.objectStore('assets').put(record);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}
async function readBrowserAsset(id){try{const db=await openAssetDB();return await new Promise((resolve,reject)=>{const req=db.transaction('assets').objectStore('assets').get(id);req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});}catch{return null;}}
async function saveAsset(record){
  const sha256=await assetSHA256(record.buffer),saved={...record,sha256};
  const existing=await readBrowserAsset(record.id);
  if(existing?.buffer&&(await assetSHA256(existing.buffer)!==sha256||existing.name!==record.name||existing.createdAt!==record.createdAt))throw new Error('Cet identifiant appartient déjà à un autre fichier.');
  await writeBrowserAsset(saved);
  let durable=false;
  if(assetVaultStatus.available){try{await assetVault.putAsset(saved);durable=true;paintAssetVault({message:`${record.name} : original confirmé par le coffre local.`});}catch(error){paintAssetVault({message:`${record.name} est conservé dans ce navigateur. Le coffre demande une nouvelle tentative : ${error.message}`});}}
  return{...saved,durable};
}
async function readAsset(id,{expectedSha256=null}={}){
  const associated=[...new Set(store.state.projects.flatMap(project=>project.pieces.filter(piece=>piece.assetId===id&&piece.assetSha256).map(piece=>piece.assetSha256)))];
  if(associated.length>1||expectedSha256&&associated.length&&associated[0]!==expectedSha256){const error=new Error('Les associations de ce fichier ne partagent pas la même empreinte.');error.code='checksum_mismatch';throw error;}
  const expected=expectedSha256||associated[0]||null;
  const local=await readBrowserAsset(id);
  if(local?.buffer){
    if(expected||local.sha256){const actual=await assetSHA256(local.buffer);if(expected&&actual!==expected||local.sha256&&actual!==local.sha256){const error=new Error('Le STL du navigateur ne correspond pas à son empreinte. Retrouvez son original ou restaurez le coffre.');error.code='checksum_mismatch';throw error;}}
    return local;
  }
  if(!assetVaultStatus.available)return null;
  const recovered=await assetVault.readAsset(id,{expectedSha256:expected});
  if(recovered){try{await writeBrowserAsset(recovered);}catch{/* The verified vault remains available when the browser cache is full. */}}
  return recovered;
}
function prepareSTLImport(files){
  $('#stl-input').value='';
  if(!files.length)return;
  try{
    store.refresh();if(store.integrityError)throw new Error(store.integrityError);
    validateSTLFiles(files);
    if($('#drawer').open||$('#command-dialog').open)throw new Error('Fermez le panneau actuel avant d’importer les STL. Votre saisie reste visible.');
    const project=getProject();if(!project)throw new Error('Ouvrez le dossier de destination.');
    openDrawer('DE FICHIER À PIÈCE.',renderSTLImportSetup({files,project,esc,icon}),'BOJ.ART / L’IMPORT STL');
    pendingSTLImport={sequence:++stlImportSequence,projectId:project.id,projectName:project.name,projectRevision:project.revision||1,entries:files.map(file=>({file,added:false})),busy:false,stale:false,lastImportedId:null};
  }catch(error){toast(error.message);}
}

async function confirmSTLImport(form){
  const pending=pendingSTLImport;
  if(!pending||pending.busy||pending.stale||form!==$('#stl-import-form'))return;
  const output=$('#form-error',form);output.textContent='';
  try{pending.entries=readSTLImportChoices(form,pending.entries);}catch(error){output.textContent=error.message;return;}
  pending.busy=true;
  const current=()=>pending===pendingSTLImport&&pending.sequence===stlImportSequence&&form.isConnected;
  const validateTarget=()=>{
    if(!current())throw new Error('Import interrompu : le panneau a été fermé ou remplacé.');
    store.refresh();
    if(store.integrityError){pending.stale=true;throw new Error(store.integrityError);}
    const target=store.state.projects.find(p=>p.id===pending.projectId);
    if(!target||(target.revision||1)!==pending.projectRevision){pending.stale=true;throw new Error('Le dossier de destination a changé. Les pièces déjà ajoutées restent conservées ; rouvrez l’import pour les fichiers restants.');}
    return target;
  };
  $$('select,button[type="submit"]',form).forEach(node=>node.disabled=true);
  try{
    for(const [index,entry] of pending.entries.entries()){
      if(entry.added)continue;
      const row=$(`[data-stl-row="${index}"]`,form),status=$(`[data-stl-status="${index}"]`,form);
      try{
        validateTarget();status.textContent='Analyse du fichier et vérification de sa conservation…';
        const buffer=await entry.file.arrayBuffer();validateTarget();
        const {inspectSTL}=await import('./lib/viewer.js');validateTarget();
        const result=inspectSTL(buffer,entry.unit);
        const id='asset-'+crypto.randomUUID();
        const saved=await saveAsset({id,name:entry.file.name,buffer,createdAt:Date.now()});
        validateTarget();
        const pieceId='stl-'+crypto.randomUUID(),piece={name:entry.file.name.replace(/\.stl$/i,''),dims:result.dims,triangles:result.triangles,unit:entry.unit,revision:1,assetId:id,assetSha256:saved.sha256,tech:entry.tech,machine:''};
        const update=dispatch('UPDATE_PIECE',{projectId:pending.projectId,id:pieceId,patch:piece});
        if(update?.ok===false)throw new Error(update.message);
        entry.added=true;pending.lastImportedId=pieceId;
        pending.projectRevision=store.state.projects.find(p=>p.id===pending.projectId).revision||1;
        row.dataset.state='added';status.textContent=`Ajoutée · ${result.dims.map(fmt).join(' × ')} mm · ${techName(entry.tech)} · préparation à valider.`;
      }catch(error){
        if(!current())return;
        row.dataset.state='error';status.textContent=error.message;
        if(pending.stale){output.textContent=error.message;break;}
      }
    }
  }finally{
    pending.busy=false;
    if(current()){
      const added=pending.entries.filter(entry=>entry.added).length,remaining=pending.entries.length-added;
      $('[data-stl-import-summary]',form).textContent=`${added} pièce(s) ajoutée(s) dans « ${pending.projectName} ».${remaining?' '+remaining+' fichier(s) restent à reprendre.':' Toutes les pièces de cet import sont dans le dossier.'}`;
      const submit=$('button[type="submit"]',form);submit.disabled=!remaining||pending.stale;submit.textContent=remaining?'Reprendre les fichiers restants':'Pièces ajoutées';
      $('[data-action="stl-import-inspect"]',form).hidden=!added;
      for(const [index,entry] of pending.entries.entries())for(const name of ['unit','tech'])form.elements.namedItem(`${name}-${index}`).disabled=entry.added||pending.stale;
    }
  }
}

async function inspectImportedSTL(){
  const pending=pendingSTLImport;if(!pending||pending.busy||!pending.lastImportedId)return;
  const project=store.state.projects.find(p=>p.id===pending.projectId);if(!project?.pieces.some(p=>p.id===pending.lastImportedId))return;
  const pieceId=pending.lastImportedId;
  if(store.state.projectId!==project.id&&!dispatch('SELECT_PROJECT',{id:project.id}).ok)return;
  if(!dispatch('SELECT_PIECE',{id:pieceId}).ok)return;
  closeDrawer();setDisplayReceipt(await presentView('model',{pieceId,localOnly:true}));
}

async function importPreparationFile(file,target){
  if(!file||!target||store.integrityError)return;
  const sequence=++preparationImportSequence;
  const currentPiece=()=>{
    if(store.integrityError)throw new Error(store.integrityError);
    const project=store.state.projects.find(item=>item.id===target.projectId),piece=project?.pieces.find(item=>item.id===target.pieceId);
    if(!piece||piece.revision!==target.pieceRevision||(piece.assetId??null)!==target.assetId)throw new Error('La pièce a changé pendant la sélection du fichier. Son association actuelle est conservée ; sélectionnez à nouveau le STL.');
    return {project,piece};
  };
  try{
    if(!/\.stl$/i.test(file.name)||file.size>50*1024*1024)throw new Error('Fichier STL requis, 50 Mo maximum.');
    if(!['mm','inch'].includes(target.unit))throw new Error('Unité du fichier à préciser : mm ou pouces.');
    const buffer=await file.arrayBuffer();if(sequence!==preparationImportSequence)return;
    const {inspectSTL}=await import('./lib/viewer.js');if(sequence!==preparationImportSequence)return;
    const measured=inspectSTL(buffer,target.unit);store.refresh();currentPiece();
    const id='asset-'+crypto.randomUUID();const saved=await saveAsset({id,name:file.name,buffer,createdAt:Date.now()});
    if(sequence!==preparationImportSequence)return;
    store.refresh();const {project,piece}=currentPiece();
    const result=dispatch('UPDATE_PIECE',{projectId:target.projectId,id:target.pieceId,expectedPieceRevision:target.pieceRevision,expectedAssetId:target.assetId,patch:{assetId:id,assetSha256:saved.sha256,dims:measured.dims,triangles:measured.triangles,unit:target.unit}});
    if(result?.ok===false)throw new Error(result.message);
    toast(`STL associé à « ${piece.name} » dans « ${project.name} ». Le procédé et le nom de la pièce sont conservés.`);
  }catch(error){toast(error.message);refreshPreparation();}
  finally{if(sequence===preparationImportSequence)$('#preparation-stl-input').value='';}
}

function guardJournalInteraction(event){
  const button=event.target.closest?.('button,a[data-action]');
  if(event.type==='click'&&!button)return;
  if(button&&['integrity-export','integrity-recheck','close-dialog','close-command','motion'].includes(button.dataset.action))return;
  store.refresh();if(!store.integrityError)return;
  event.preventDefault();event.stopImmediatePropagation();paintIntegrityGuard();toast(store.integrityError);
}
document.addEventListener('click',guardJournalInteraction,true);
document.addEventListener('change',guardJournalInteraction,true);
document.addEventListener('submit',guardJournalInteraction,true);
document.addEventListener('click',async event=>{const button=event.target.closest('button,a[data-action]');if(!button)return;
  if(button.dataset.action==='integrity-export'){exportIntegrityCopy();return;}
  if(button.dataset.action==='integrity-recheck'){recheckIntegrity();return;}
  if(button.dataset.action==='stl-import-inspect'){await inspectImportedSTL();return;}
  if(button.dataset.screen)return navigate(button.dataset.screen);
  if(button.dataset.wallFocus){ui.wallFocus=button.dataset.wallFocus;const wall=$('.wall-monitors');wall.dataset.focus=ui.wallFocus;$$('[data-wall-focus]').forEach(n=>n.setAttribute('aria-pressed',n.dataset.wallFocus===ui.wallFocus));if(innerWidth<921&&ui.wallFocus!=='all')$(`[data-monitor="${ui.wallFocus}"]`)?.scrollIntoView({behavior:ui.motion?'smooth':'instant',block:'nearest',inline:'center'});return;}
  if(button.dataset.wallMachine){ui.machine=button.dataset.wallMachine;navigate('atelier');return;}
  if(button.dataset.controlDomain)return openControl(button.dataset.controlDomain);
  if(button.dataset.operation)return runOperation(button);
  if(button.dataset.quickCommand){executeCommand(button.dataset.quickCommand);return;}
  if(button.dataset.creationTab){ui.creationTab=button.dataset.creationTab;render(true);return;}
  if(button.dataset.pilotTab){ui.pilotTab=button.dataset.pilotTab;render(true);return;}
  if(button.dataset.filter){ui.filter=button.dataset.filter;render(false);return;}
  if(button.dataset.fleetMachine)return openFleetMachine(button.dataset.fleetMachine);
  if(button.dataset.machine){ui.machine=button.dataset.machine;render(false);return;}
  if(button.dataset.piece){dispatch('SELECT_PIECE',{id:button.dataset.piece});return;}
  if(button.dataset.pieceDetail)return openPiece(button.dataset.pieceDetail);
  if(button.dataset.projectEdit)return openProject(button.dataset.projectEdit);
  if(button.dataset.art)return openArt(button.dataset.art);
  if(button.dataset.media)return openMedia(button.dataset.media);
  if(button.dataset.command){$('#command-input').value=button.dataset.command;executeCommand(button.dataset.command);return;}
  const action=button.dataset.action;if(!action)return;
  if(button.dataset.missionProject&&button.dataset.missionProject!==getProject().id){toast('Le dossier actif a changé. Ouvrez sa mission avant de poursuivre.');return;}
  switch(action){
    case'inquiries':openInquiries();break;
    case'inquiry-current':openInquiryDetail(button.dataset.projectId||getProject().id);break;
    case'inquiry-import':$('#inquiry-input').click();break;
    case'inquiry-open':openInquiryDetail(button.dataset.inquiryProject);break;
    case'inquiry-project':{const project=store.state.projects.find(item=>item.id===button.dataset.inquiryProject);if(!project?.inquiry){toast('Dossier de demande introuvable.');break;}openProject(project.id);break;}
    case'inquiry-quote':{const project=store.state.projects.find(item=>item.id===button.dataset.inquiryProject);if(!project?.inquiry){toast('Dossier de demande introuvable.');break;}const selected=project.id===getProject().id?{ok:true}:dispatch('SELECT_PROJECT',{id:project.id});if(selected.ok)openQuote();break;}
    case'inquiry-export':{const project=store.state.projects.find(item=>item.id===button.dataset.inquiryProject);if(!project?.inquiry){toast('Dossier de demande introuvable.');break;}downloadJson(exportInquiryTechnical(project),'BOJ_ART_'+project.inquiry.reference+'_technique.json');toast('Fiche technique exportée. Les coordonnées restent dans la demande source.');break;}
    case'inquiry-questions':{const project=store.state.projects.find(item=>item.id===button.dataset.inquiryProject);if(!project?.inquiry){toast('Dossier de demande introuvable.');break;}downloadBlob(new Blob([inquiryQuestionsText(project)],{type:'text/plain;charset=utf-8'}),'BOJ_ART_'+project.inquiry.reference+'_questions.txt');toast('Questions préparées pour relecture. Aucun message envoyé.');break;}
    case'fleet':openFleet();break;
    case'continuity':openContinuity();break;
    case'asset-browser-export':await exportBrowserAssets();break;
    case'asset-vault-sync':await syncAssetVault();break;
    case'asset-vault-refresh':await inspectAssetVault();break;
    case'asset-vault-export':{if(assetVaultStatus.available){const link=document.createElement('a');link.href=assetVault.backupURL;link.download='BOJ_ART_Coffre_STL.bojassets';link.click();}break;}
    case'asset-vault-restore':$('#asset-backup-input').click();break;
    case'reload-form':reloadDrawerForm();break;
    case'export-fleet':downloadJson(exportFleetRegistry(store.state.machines,Date.now()),'BOJ_ART_Referentiel_Machines.json');toast('Référentiel des machines exporté.');break;
    case'backup-export':await exportBackup();break;
    case'backup-import':$('#backup-input').click();break;
    case'backup-restore':restoreBackup();break;
    case'backup-cancel':pendingRestore=null;backupReadSequence++;if($('#backup-preview'))$('#backup-preview').innerHTML='';break;
    case'sync-connect':button.disabled=true;await workshopSync?.connect();break;
    case'sync-inspect':button.disabled=true;await workshopSync?.inspect();break;
    case'studio':openStudio();break;
    case'project-studio':openProjectStudio(button.dataset.projectId||getProject().id);break;
    case'preparation':openPreparation(button.dataset.projectId||getProject().id,button.dataset.pieceId?{pieceId:button.dataset.pieceId}:null);break;
    case'decisions':openDecisionDesk(button.dataset.projectId||getProject().id);break;
    case'audit-project':await runOrchestration(button.dataset.projectId||getProject().id);break;
    case'visual-desk':openVisualDesk();break;case'visual-provider-refresh':await refreshVisualProvider();break;case'visual-present':{const scene=VISUAL_VIEWS.find(v=>v.id===button.dataset.visualId);if(scene)await performVisualRequest(scene.label,{view:scene.id});break;}case'signature':openIdentity();break;case'display-test':closeDrawer();setDisplayReceipt(await presentView('model',{remoteOnly:true}));break;case'display-local':closeDrawer();setDisplayReceipt(await presentView('model',{localOnly:true}));break;case'control':openControl();break;case'master-mission':openMasterMission();break;case'orchestrate':runOrchestration(button.dataset.missionProject||getProject().id);break;case'export-master':exportMasterMission();break;case'journal':closeDrawer();ui.pilotTab='journal';navigate('pilotage');break;case'open-panorama':closeDrawer();navigate('panorama');break;case'mission':closeDrawer();openMission();break;case'connections':openConnections();break;case'capabilities':openCapabilities();break;case'export-mission':exportMission();break;case'wall-model':closeDrawer();setDisplayReceipt(await presentView('model'));break;case'immersive':ui.immersive=!ui.immersive;document.documentElement.classList.toggle('is-immersive',ui.immersive);{const url=new URL(location.href);ui.immersive?url.searchParams.set('immersive','1'):url.searchParams.delete('immersive');history.replaceState(null,'',url);}applyMotion();if(ui.screen!=='panorama')render(false);break;case'ambient':ui.ambient=!ui.ambient;if(ui.ambient&&!ui.motion){ui.motion=true;}applyMotion();break;case'section-reset':ui.section=null;viewer?.setSection(null);if($('#section-slider'))$('#section-slider').value='100';if($('#section-value'))$('#section-value').textContent='désactivée';break;case'command':openCommand();break;case'close-command':$('#command-dialog').close();break;case'close-dialog':closeDrawer();break;case'screens':openScreens();break;case'settings':openSettings();break;case'project-edit':openProject();break;case'new-project':openProject(undefined,true);break;case'piece':openPiece();break;case'quote':openQuote();break;case'story':openStory();break;case'identity':openIdentity();break;case'plan':openPlan();break;case'open-archive':closeDrawer();ui.pilotTab='archive';navigate('pilotage');break;
    case'import':$('#stl-input').click();break;
    case'open-piece-3d':closeDrawer();setDisplayReceipt(await presentView('model'));break;
    case'machine-edit':openMachine(button.dataset.id);break;
    case'confirm-plan':{const result=dispatch('PLAN_PROJECT',{projectId:getProject().id});$('#plan-result').innerHTML=`<div class="badge-box">${esc(result?.message||'Répartition de démonstration mise à jour. Les profils restent à qualifier.')}</div>`;toast(result?.message||'Répartition simulée.');break;}
    case'toggle-machine':{const result=dispatch('TOGGLE_MACHINE',{id:button.dataset.id});toast(result?.message||'Simulation mise à jour.');break;}
    case'viewer-reset':viewer?.reset();break;
    case'viewer-wire':ui.wire=!ui.wire;viewer?.setWireframe(ui.wire);button.setAttribute('aria-pressed',ui.wire);button.classList.toggle('button-red',ui.wire);break;
    case'viewer-explode':ui.exploded=!ui.exploded;if(viewer?.explode(ui.exploded)===false){ui.exploded=false;toast('L’éclaté nécessite des pièces séparées. Le STL importé reste un seul maillage.');}button.setAttribute('aria-pressed',ui.exploded);break;
    case'viewer-auto':ui.auto=!ui.auto;viewer?.setAutoRotate(ui.auto);button.setAttribute('aria-pressed',ui.auto);break;
    case'play-video':{const v=$('#studio-video');if(!v)break;if(v.paused){try{await v.play();button.innerHTML=icon('pause')+' Pause';v.onended=()=>button.innerHTML=icon('play')+' Revoir';}catch{toast('Utilisez les contrôles de lecture de votre navigateur.');v.controls=true;}}else{v.pause();button.innerHTML=icon('play')+' Lire';}break;}
    case'motion':ui.motion=!ui.motion;try{localStorage.setItem('bojart.motion',ui.motion?'on':'off');}catch{}applyMotion();toast(ui.motion?'Mouvement activé.':'Animations réduites.');break;
    case'export-state':{const blob=new Blob([JSON.stringify({format:'bojart-workshop',exportedAt:new Date().toISOString(),data:store.state},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='bojart-dossiers.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);toast('Export des dossiers préparé.');break;}
  }
});
document.addEventListener('change',event=>{const target=event.target;if(target.id==='project-picker'){dispatch('SELECT_PROJECT',{id:target.value});ui.exploded=false;if(!getProject()?.media){ui.creationTab='modele';render(false);}}if(target.id==='stl-input')prepareSTLImport([...target.files]);if(target.id==='backup-input')previewBackup(target.files[0]);});
$('#preparation-stl-input').addEventListener('change',event=>{const target=preparationImportTarget;preparationImportTarget=null;importPreparationFile(event.target.files[0],target);});
$('#preparation-stl-input').addEventListener('cancel',()=>{preparationImportTarget=null;});
$('#asset-backup-input').addEventListener('change',event=>{void restoreAssetVault(event.target.files[0]);});
$('#inquiry-input').addEventListener('change',event=>{void previewInquiryFile(event.target.files[0]);});
document.addEventListener('input',event=>{if(store.integrityError)return;if(event.target.closest('#quote-form')){$('#quote-result').innerHTML='';$('#form-error').textContent='Chiffrage modifié : recalcul nécessaire.';}if(event.target.id==='section-slider'){ui.section=Number(event.target.value)/100;viewer?.setSection(ui.section);$('#section-value').textContent=Math.round(ui.section*100)+' %';}if(event.target.id==='archive-search'){ui.archiveQuery=event.target.value;const needle=ui.archiveQuery.toLocaleLowerCase('fr');$('#archive-grid').innerHTML=archiveCards(archive.filter(a=>(a.title+' '+a.id).toLocaleLowerCase('fr').includes(needle)));}});
document.addEventListener('submit',async event=>{if(event.target.id!=='stl-import-form')return;event.preventDefault();if(event.target.reportValidity())await confirmSTLImport(event.target);});
document.addEventListener('submit',async event=>{const form=event.target;if(form.id==='inquiry-confirm-form'){event.preventDefault();if(!form.reportValidity())return;try{confirmInquiryImport(form);}catch(error){const output=$('#form-error',form);if(output)output.textContent=error.message;}return;}if(form.id==='visual-command-form'){event.preventDefault();if(!form.reportValidity())return;await performVisualRequest($('#visual-command-input').value.trim(),{provider:new FormData(form).get('provider')||'local'});return;}if(form.id==='wall-command-form'){event.preventDefault();executeCommand($('#wall-command-input').value);return;}if(!['command-form','project-form','piece-form','quote-form','story-form','machine-form','fleet-form'].includes(form.id))return;event.preventDefault();if(!form.reportValidity())return;const values=Object.fromEntries(new FormData(form));const error=$('#form-error',form);if(error)error.textContent='';try{
  if(form.id==='command-form'){executeCommand($('#command-input').value);return;}
  if(form.id!=='fleet-form'&&form.dataset.baseSnapshot!==undefined&&form.dataset.baseSnapshot!==formSnapshot(form))throw new Error('La fiche source a changé. Votre saisie reste visible ; rechargez la version conservée avant d’enregistrer.');
  if(form.id==='fleet-form'){const result=dispatch('UPDATE_MACHINE',{id:form.dataset.id,expectedRegistryRevision:Number(form.dataset.revision),patch:{registry:fleetRecordFromForm(values)}});if(result?.ok===false)throw new Error(result.message);openFleetMachine(form.dataset.id);toast('Fiche machine enregistrée. Le raccordement reste à réaliser.');}
  if(form.id==='project-form'){const patch={name:values.name.trim(),kind:values.kind.trim(),quantity:Number(values.quantity),height:values.height.trim()===''?null:Number(values.height),notes:values.notes.trim(),status:values.status};if(!patch.name||!patch.kind)throw new Error('Renseignez un nom et un type de projet.');const result=form.dataset.id?dispatch('UPDATE_PROJECT',{id:form.dataset.id,patch}):dispatch('ADD_PROJECT',patch);if(result?.ok===false)throw new Error(result.message);closeDrawer();toast(result.persisted?'Dossier enregistré.':'Dossier modifié. Conservation limitée à cette fenêtre.');}
  if(form.id==='piece-form'){const project=store.state.projects.find(p=>p.id===form.dataset.project),old=project.pieces.find(p=>p.id===form.dataset.id);const machine=values.machine?store.getMachine(values.machine):null;if(machine&&machine.tech!==values.tech)throw new Error('Le procédé de la pièce et celui de la machine doivent correspondre.');const patch={name:values.name.trim(),tech:values.tech,machine:values.machine};if(!patch.name)throw new Error('Renseignez le nom de la pièce.');if(old.assetId&&values.unit&&values.unit!==old.unit){const factor=values.unit==='inch'?25.4:1/25.4;patch.unit=values.unit;patch.dims=old.dims.map(d=>d*factor);patch.revision=(old.revision||1)+1;}const result=dispatch('UPDATE_PIECE',{projectId:project.id,id:old.id,patch});if(result?.ok===false)throw new Error(result.message);closeDrawer();toast('Pièce enregistrée. La préparation reste à valider.');}
  if(form.id==='quote-form'){if(Object.values(values).some(v=>v===''))throw new Error('Tous les coûts doivent être renseignés, y compris les valeurs nulles.');const p=store.state.projects.find(p=>p.id===form.dataset.project),inputs={...Object.fromEntries(Object.entries(values).map(([k,v])=>[k,Number(v)])),quantity:p.quantity};const result=calculateQuote(inputs);const saved=dispatch('SAVE_QUOTE',{projectId:p.id,inputs,result});if(saved?.ok===false)throw new Error(saved.message);form.dataset.baseSnapshot=formSnapshot(form);keepDraftVisible();$('#quote-result').innerHTML=quoteResult(result);toast('Chiffrage du lot calculé et enregistré.');}
  if(form.id==='story-form'){const saved=dispatch('SAVE_STORY',{projectId:form.dataset.project,text:values.text.trim()});if(saved?.ok===false)throw new Error(saved.message);form.dataset.baseSnapshot=formSnapshot(form);keepDraftVisible();toast('Scénario enregistré.');}
  if(form.id==='machine-form'){const patch={name:values.name.trim(),material:values.material.trim(),tech:values.tech,volume:[Number(values.x),Number(values.y),Number(values.z)],qualified:false};const hasWork=store.state.jobs.some(j=>j.machine===form.dataset.id&&['running','paused','queued'].includes(j.status));if(hasWork&&patch.tech!==store.getMachine(form.dataset.id).tech)throw new Error('Une ressource avec des travaux affectés conserve son procédé.');const result=dispatch('UPDATE_MACHINE',{id:form.dataset.id,patch});if(result?.ok===false)throw new Error(result.message);closeDrawer();toast('Fiche de démonstration enregistrée.');}
}catch(e){if(error)error.textContent=e.message;else toast(e.message);}});
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommand();}if(e.key==='Escape'){$$('video',$('#drawer')).forEach(v=>v.pause());if(ui.immersive&&!$('#drawer').open&&!$('#command-dialog').open){ui.immersive=false;document.documentElement.classList.remove('is-immersive');const url=new URL(location.href);url.searchParams.delete('immersive');history.replaceState(null,'',url);applyMotion();}}});
document.addEventListener('dragover',e=>{if([...e.dataTransfer.types].includes('Files'))e.preventDefault();});
document.addEventListener('drop',e=>{if(e.dataTransfer.files.length){e.preventDefault();prepareSTLImport([...e.dataTransfer.files]);}});
store.addEventListener('change',()=>{if(store.integrityError||!getProject()){intentSequence++;visualSequence++;preparationImportSequence++;if(pendingSTLImport)pendingSTLImport.stale=true;render(false);paintContinuity();return;}if(store.state.projectId!==lastProjectId){lastProjectId=store.state.projectId;if($('#drawer').open&&!$('#drawer form')&&!$('#continuity-status')&&!projectStudioController&&!preparationController&&!decisionController)closeDrawer();if($('#command-dialog').open)$('#command-dialog').close();}keepDraftVisible();refreshProjectStudio();refreshPreparation();decisionController?.refreshContext?.();render(false);paintContinuity();void projectEvidence.inspect(getProject().id);});
osMotion.addEventListener('change',e=>{if(e.matches){ui.motion=false;applyMotion();}});
document.addEventListener('visibilitychange',()=>{if(document.hidden)$$('video').forEach(v=>v.pause());else syncAmbient();});
setInterval(()=>{if(document.hidden||ui.screen!=='atelier')return;$$('[data-progress-machine]').forEach(n=>{const j=currentJob(n.dataset.progressMachine),progress=j?jobProgress(j):0;n.setAttribute('aria-valuenow',Math.round(progress));$('.progress-bar',n).style.setProperty('--progress',`${progress}%`);const t=$(`[data-machine-time="${n.dataset.progressMachine}"]`);if(t)t.textContent=j?`${Math.round(progress)} %`:'—';});},1000);
function immersiveDock(){return `<div class="immersive-dock"><span>BOJ.ART <i>/</i> LE POSTE</span><button data-screen="panorama" aria-label="Vue des trois écrans">${icon('screens')}</button><button data-action="command" aria-label="Ouvrir Jarvis">${icon('spark')}</button><button data-action="immersive" aria-label="Quitter le mode immersif">${icon('close')}</button></div>`;}
function renderProductionOverview(){const active=store.state.jobs.filter(j=>j.status==='running'&&jobProgress(j)<100).length;return `<section class="production-overview reveal"><div class="production-overview-copy"><p class="eyebrow">LE PARC, EN PERSPECTIVE</p><h2>CHAQUE PIÈCE.<br><em>AU BON ENDROIT.</em></h2><p>Visualiser les ressources, préparer leur charge et suivre la répartition du projet.</p><div class="ambient-count"><div><strong>${String(store.state.machines.length).padStart(2,'0')}</strong><span>Ressources démo</span></div><div><strong>${String(active).padStart(2,'0')}</strong><span>Simulations actives</span></div><div><strong>02</strong><span>Procédés</span></div></div></div><div class="motion-canvas" data-motion-stage="production" aria-hidden="true"></div><div class="scene-caption">RÉSINE UV <span>×</span> FDM / VUE D’INTENTION</div></section>`;}
function disposeAtmosphere(){motionStages.forEach(s=>s.dispose());motionStages=[];ambientObserver?.disconnect();ambientObserver=null;$$('[data-ambient-video]').forEach(v=>v.pause());}
function syncAmbient(){const play=ui.motion&&ui.ambient&&!document.hidden;$$('[data-ambient-video]').forEach(v=>{if(play&&v.dataset.inView!=='false'){const promise=v.play();promise?.catch(()=>{v.dataset.playBlocked='true';syncAmbientButtons();});}else v.pause();});syncAmbientButtons();}
function syncAmbientButtons(){$$('[data-action="ambient"]').forEach(b=>{const v=b.closest('.art-display,.cinematic-stage')?.querySelector('video');const playing=ui.motion&&ui.ambient&&v?.dataset.playBlocked!=='true';b.innerHTML=icon(playing?'pause':'play');b.setAttribute('aria-label',playing?'Mettre le montage en pause':'Lire le montage');b.setAttribute('aria-pressed',String(playing));});}
function mountAtmosphere(){for(const node of $$('[data-motion-stage]')){try{motionStages.push(mountMotionStage(node,{kind:node.dataset.motionStage,motion:ui.motion}));}catch{node.classList.add('motion-fallback');}}
  if(typeof IntersectionObserver==='function')ambientObserver=new IntersectionObserver(entries=>{entries.forEach(entry=>{const v=entry.target;v.dataset.inView=String(entry.isIntersecting);if(!entry.isIntersecting)v.pause();});syncAmbient();},{threshold:.1});
  $$('[data-ambient-video]').forEach(v=>{v.muted=true;ambientObserver?.observe(v);v.addEventListener('timeupdate',()=>{const track=v.parentElement.querySelector('.film-progress');if(track&&v.duration)track.style.setProperty('--film-progress',String(v.currentTime/v.duration));});v.addEventListener('playing',()=>{delete v.dataset.playBlocked;syncAmbientButtons();});});
}
function mission(){return inspectMission(store.state,getProject().id);}
function openMission(){openMasterMission();}
function renderCommandDeck(){const m=mission(),c=m.checks;return `<section class="command-deck panel reveal"><div class="command-deck-intention"><p class="eyebrow">JARVIS / UNE INTENTION, UN PARCOURS</p><form id="wall-command-form"><label for="wall-command-input">Qu’est-ce qu’on crée aujourd’hui ?</label><div class="wall-command-field"><input id="wall-command-input" placeholder="Prépare la fabrication du projet…" autocomplete="off" maxlength="250"><button type="submit" aria-label="Préparer cette intention">${icon('arrow')}</button></div></form><div class="quick-intents"><button data-quick-command="Prépare la mission">Préparer</button><button data-quick-command="Montre le socle">Voir la 3D</button><button data-quick-command="Affiche les trois écrans">Vue d’ensemble</button></div><div class="wall-receipt" id="wall-command-receipt" role="status">${esc(lastReceipt||'Console de démonstration. La voix locale sera raccordée à la tour.')}</div></div><div class="command-deck-mission"><span class="eyebrow">${esc(m.projectName)}</span><div class="readiness-counts"><span><strong>${c.importedFiles}<small> / ${c.totalPieces}</small></strong>STL importés</span><span><strong>${c.compatibleEnvelopes}<small> / ${c.totalPieces}</small></strong>Enveloppes compatibles</span></div><button class="button button-red button-block" data-action="mission">${icon('layers')} Ouvrir la préparation ${icon('arrow')}</button><button class="button button-ghost button-small" data-action="capabilities">Toutes les capacités du poste ${icon('arrowUp')}</button></div></section>`;}
function openConnections(){openDrawer('RACCORDER LA TOUR.',`<p class="small muted">Jarvis prépare une mission visible. Les moteurs locaux et les imprimantes devront ensuite renvoyer leur état et leurs fichiers de fabrication.</p><div class="connection-flow"><div><span>01</span><strong>La voix & l’intention</strong><p>Reconnaissance vocale locale, raccourci d’écoute et commandes structurées.</p><span class="tag tag-amber">À RACCORDER</span></div><div><span>02</span><strong>La préparation & le slicing</strong><p>Moteur installé sur la tour, profils machine/matière validés, fichier de sortie et aperçu des couches.</p><span class="tag tag-amber">À RACCORDER</span></div><div><span>03</span><strong>Le parc & ses états</strong><p>Connecteur par protocole, affectation explicite du fichier à la machine, progression, pause et reprise.</p><span class="tag tag-amber">À RACCORDER</span></div><div><span>04</span><strong>La traçabilité</strong><p>Relier modèle, révision, matière, profil, fichier slicé et travail d’impression.</p><button class="button button-small" data-action="continuity">Journal & sauvegardes</button></div></div><p class="badge-box">Le dashboard n’a encore accès à aucune imprimante ni au PC local. Les modèles exacts, volumes, formats de fichiers et protocoles détermineront les connecteurs.</p><div class="form-actions"><button class="button button-red" data-action="mission">Revenir à la mission</button><button class="button" data-action="export-mission">Exporter la préparation</button></div>`,'BOJ.ART / LES CONNEXIONS DU POSTE');}
function openCapabilities(){openControl();}
function exportMission(){exportMasterMission();}

function controlTabs(){return `<div class="tab-bar control-tabs" role="tablist" aria-label="Pilotage de l’atelier">${[['controle','Le poste'],['dossiers','Les dossiers'],['demandes','Les demandes'],['archive','La vidéothèque'],['journal','Le journal']].map(([id,label])=>`<button class="tab-button ${ui.pilotTab===id?'active':''}" data-pilot-tab="${id}" role="tab" aria-selected="${ui.pilotTab===id}">${label}</button>`).join('')}</div>`;}
function renderControlScreen(){const evidence=projectEvidence.snapshot(getProject().id),decision=buildControlDecision(store.state,getProject().id,{preparationReport:evidence.report,evidenceStatus:evidence.status});return `<section class="page-head control-page-head"><div><p class="eyebrow">ÉCRAN 02 / LE CŒUR DE L’ATELIER</p><h1>JARVIS. <em>AUX COMMANDES.</em></h1></div><div class="page-actions"><button class="button" data-action="inquiries">${icon('folder')} Demandes client</button><button class="button" data-action="fleet">${icon('printer')} Le parc</button><button class="button" data-action="continuity">${icon('save')} Continuité</button><button class="button" data-action="master-mission">${icon('layers')} Mission complète</button><button class="button" data-action="screens">${icon('screens')} Les trois écrans</button></div></section>${controlTabs()}${renderControlStage({project:getProject(),domains:DOMAIN_CATALOG,operations:buildOperations(store.state,archive.length),decision,receipt:lastReceipt,picker:projectPicker(),displaySummary:displaySummary(),visualDock:renderVisualDock({esc,icon}),esc,icon})}`;}
function closeCommand(){if($('#command-dialog').open)$('#command-dialog').close();}
function openControl(domain='all'){
  closeCommand();ui.controlDomain=DOMAIN_CATALOG.some(d=>d.id===domain)?domain:'all';
  openDrawer('LE CHAMP D’ACTION.',renderControlHub({domains:DOMAIN_CATALOG,operations:buildOperations(store.state,archive.length),selected:ui.controlDomain,contextProjectId:getProject().id,esc,icon}),'BOJ.ART / JARVIS — TOUT L’ATELIER');
}
function openMasterMission(projectId=getProject().id){if(!store.state.projects.some(project=>project.id===projectId)){toast('Le dossier est introuvable.');return;}closeCommand();openDrawer('UNE MISSION. TOUT LE PROJET.',renderMasterMission({mission:currentMasterMission(projectId),domains:DOMAIN_CATALOG,esc,icon}),'BOJ.ART / JARVIS — MISSION GLOBALE');masterMissionProjectId=projectId;void projectEvidence.inspect(projectId);}
function downloadJson(data,name){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function exportMasterMission(){downloadJson({...currentMasterMission(masterMissionProjectId||getProject().id),exportedAt:new Date().toISOString()},'bojart-mission-complete.json');toast('Mission et preuves exportées. Les binaires STL restent séparés.');}
async function runOrchestration(projectId){
  if(projectId!==getProject().id){const message='Le projet actif a changé. Rouvrez sa mission avant de la préparer.';toast(message);return message;}
  closeCommand();
  try{
    const checked=await projectEvidence.inspect(projectId,{force:true});
    if(projectId!==getProject().id||!checked){const message='Le dossier a évolué pendant la lecture. Les preuves actuelles restent consultables dans sa mission.';toast(message);return message;}
    const mission=currentMasterMission(projectId),s=mission.preparation.report.summary;
    const receipt=`${mission.projectName} : ${s.measuredFiles} STL relu(s), ${s.piecesWithEnvelopeFit} pièce(s) dans un volume déclaré, ${mission.editPlans.length} plan(s) de montage conservé(s). Les prochaines étapes sont affichées.`;
    setDisplayReceipt(receipt);render(false);openMasterMission(projectId);
    return receipt;
  }catch(error){toast(error.message);return 'La préparation n’a pas abouti : '+error.message;}
}
async function runOperation(button){
  const op=buildOperations(store.state,archive.length).find(o=>o.id===button.dataset.operation);
  if(!op||button.dataset.operationContext!==getProject().id||op.projectId!==button.dataset.operationProject||op.machineId&&(op.jobId!==button.dataset.operationJob||op.expectedStatus!==button.dataset.operationStatus)){
    toast('La cible ou son état a changé. Rouvrez les opérations avant de continuer.');return;
  }
  if(op.mode==='unconnected'||!op.available){
    openDrawer(op.label.toUpperCase(),`<span class="tag tag-amber">${op.mode==='unconnected'?'À RACCORDER':'À PRÉPARER'}</span><p class="small muted form-section">${esc(op.requirement)}</p><div class="form-actions"><button class="button button-red" data-action="connections">${icon('link')} Les raccordements</button><button class="button" data-action="control">${icon('grid')} Toutes les opérations</button></div><p class="micro-copy form-section">Cette opération n’a pas été exécutée.</p>`,'BOJ.ART / JARVIS — ÉTAT DE L’OPÉRATION');
    lastReceipt=op.label+' : '+(op.mode==='unconnected'?'service à raccorder.':'préparation requise.');dispatch('LOG',{projectId:op.projectId,message:'Jarvis — '+lastReceipt});return;
  }
  let message=op.label+' : accès ouvert.';closeDrawer();
  switch(op.targetAction){
    case'import':$('#stl-input').click();message='Sélecteur de STL ouvert.';break;
    case'wall-model':message=await presentView('model');break;
    case'project-edit':openProject(op.projectId);break;
    case'new-project':openProject(undefined,true);if(op.projectKind==='robotique')$('#project-form').elements.namedItem('kind').value='Prototype robotique';break;
    case'control':openMasterMission();break;
    case'plan':openPlan();break;
    case'production-view':message=await presentView('production');break;
    case'fleet':openFleet();break;
    case'continuity':openContinuity();break;
    case'studio':openStudio();break;
    case'project-studio':openProjectStudio();break;
    case'preparation':openPreparation();break;
    case'decisions':openDecisionDesk(op.projectId);break;
    case'toggle-machine':{const r=dispatch('TOGGLE_MACHINE',{id:op.machineId});message=r.message;openControl('production');break;}
    case'open-archive':ui.pilotTab='archive';navigate('pilotage');break;
    case'story':openStory();break;
    case'quote':openQuote();break;
    case'inquiries':openInquiries();break;
    case'export-mission':exportMasterMission();message='Mission complète exportée en JSON.';break;
    case'export-state':downloadJson({format:'bojart-workshop',exportedAt:new Date().toISOString(),data:store.state},'bojart-dossiers.json');message='État de tous les dossiers exporté en JSON.';break;
    case'journal':ui.pilotTab='journal';navigate('pilotage');break;
    case'screens':openScreens();break;
    case'connections':openConnections();break;
    default:message='Cette opération ne possède pas encore de commande disponible.';
  }
  lastReceipt=message;$('#command-receipt').textContent=message;dispatch('LOG',{projectId:op.projectId,message:'Jarvis — '+message});
}


function setDisplayReceipt(message){lastReceipt=message;if($('#command-receipt'))$('#command-receipt').textContent=message;if($('#wall-command-receipt'))$('#wall-command-receipt').textContent=message;}
function displaySummary(){
  const peers=displayBus?.peers()||[];
  return `<div class="display-constellation ${displayPending?'pending':''}" data-display-summary role="group" aria-label="Présence des fenêtres du poste">${[['atelier','01','Atelier'],['pilotage','02','Jarvis'],['creation','03','Création']].map(([role,number,label])=>{const own=ui.station===role,online=own||peers.some(p=>p.role===role);return `<button data-action="screens" class="${online?'online':'offline'}" title="${esc(label)} : ${own?'cette fenêtre':online?'fenêtre détectée':'à ouvrir'}"><i></i><span>${number}</span><strong>${label}</strong></button>`;}).join('')}</div>`;
}
function updateDisplayPresence(){
  const current=$('[data-display-summary]');if(current)current.outerHTML=displaySummary();
  const status=$('[data-screens-status]');if(status){const peers=displayBus?.peers()||[];status.textContent=displayBus?.available?`${new Set(peers.map(p=>p.role).concat(ui.station?[ui.station]:[])).size} rôle(s) détecté(s) dans les fenêtres du navigateur.`:'La liaison entre fenêtres n’est pas disponible dans ce navigateur. Les vues restent accessibles séparément.';}
}
async function receiveDisplayRequest(payload,{remote=true}={}){
  const target=payload.view==='production'?'atelier':'creation';
  if(remote&&ui.station!==target)return{ok:false,message:'Cette fenêtre n’est plus associée à l’écran demandé.'};
  if(remote&&($('#drawer').open||$('#command-dialog').open))return{ok:false,message:'Un panneau est ouvert sur l’écran cible. Fermez-le avant de remplacer la vue.'};
  store.refresh();
  if(store.integrityError)return integrityFailure();
  const p=store.state.projects.find(p=>p.id===payload.projectId);
  if(!p||p.id!==store.state.projectId)return{ok:false,message:'Le projet actif a changé ; aucune vue demandée n’a été ouverte.'};
  if(payload.projectRevision!==undefined&&payload.projectRevision!==(p.revision||1))return{ok:false,message:'Le dossier a changé de révision.'};
  const piece=payload.pieceId?p.pieces.find(x=>x.id===payload.pieceId):null;
  if(payload.pieceId&&!piece)return{ok:false,message:'La pièce demandée n’appartient pas à ce dossier.'};
  if(payload.pieceRevision!==undefined&&payload.pieceRevision!==(piece?.revision||1))return{ok:false,message:'La pièce a changé de révision.'};
  if(payload.view==='model'&&!piece)return{ok:false,message:'Le dossier ne contient pas de pièce à inspecter.'};
  if(payload.exploded&&piece?.assetId)return{ok:false,message:'L’éclaté est disponible sur le démonstrateur ; le STL importé n’est pas un assemblage de pièces séparées.'};
  if(piece&&store.state.selectedPieceId!==piece.id){const selected=dispatch('SELECT_PIECE',{id:piece.id});if(!selected.ok)return{ok:false,message:selected.message};}
  if(!remote){closeDrawer();closeCommand();}
  if(target==='creation'){ui.creationTab={model:'modele',art:'oeuvre',film:'video'}[payload.view];ui.exploded=payload.exploded===true;ui.section=payload.section??null;}
  const result=await navigate(target);
  if(store.integrityError||store.state.projectId!==p.id||getProject()?.revision!==p.revision)return{ok:false,message:'Le projet a changé ou son journal doit être vérifié pendant l’affichage.'};
  if(result?.ok)announceVisualArrival(payload.view);
  return result||{ok:false,message:'Le résultat de l’affichage n’a pas été confirmé.'};
}
async function presentView(view,{pieceId,exploded=false,section=null,remoteOnly=false,localOnly=false}={}){
  store.refresh();if(store.integrityError||!getProject())return integrityFailure().message;
  if(displayPending)return 'Une demande d’affichage attend déjà le retour de son écran.';
  const project=getProject(),target=view==='production'?'atelier':'creation';
  const piece=pieceId?project.pieces.find(p=>p.id===pieceId):getPiece();
  const payload={kind:'show',view,projectId:project.id,projectRevision:project.revision||1};
  if(view==='model'){if(!piece)return 'Ajoutez une pièce au dossier pour l’inspecter.';Object.assign(payload,{pieceId:piece.id,pieceRevision:piece.revision||1,exploded,section});}
  const remote=displayBus?.peers().some(p=>p.role===target);
  const targetIsHere=ui.station===target||!ui.station&&ui.screen===target&&!remoteOnly;
  const useRemote=!localOnly&&!targetIsHere&&(remoteOnly||Boolean(ui.station)||remote);
  if(useRemote){
    if(!remote){openScreens();return `Écran ${target==='creation'?'03 · Création':'01 · Atelier'} à ouvrir dans ce navigateur. Jarvis conserve sa vue.`;}
    displayPending=true;setDisplayReceipt(`Demande envoyée à l’écran ${target==='creation'?'03 · Création':'01 · Atelier'}…`);updateDisplayPresence();
    try{const result=await displayBus.request(target,payload);return result.ok?`Écran ${target==='creation'?'03 · Création':'01 · Atelier'} : ${result.message}`:result.code==='timeout'?'L’écran cible n’a pas confirmé son affichage. Vérifiez son état ; aucune nouvelle demande n’a été envoyée automatiquement.':`Affichage non confirmé : ${result.message}`;}
    finally{displayPending=false;updateDisplayPresence();}
  }
  const result=await receiveDisplayRequest(payload,{remote:false});
  return result.ok?'Dans cette fenêtre : '+result.message:'Affichage non confirmé : '+result.message;
}

function setVisualReceipt(message,{busy=false}={}){
  visualReceipt=message;setDisplayReceipt(message);
  const output=$('[data-visual-status]');if(output){output.textContent=message;output.dataset.busy=String(busy);}
  const submit=$('#visual-command-form button[type="submit"]');if(submit)submit.disabled=busy;
}
function openVisualDesk(){
  closeCommand();openDrawer('LA RÉGIE VISUELLE.',renderVisualDesk({project:getProject(),provider:visualProvider,receipt:visualReceipt,esc,icon}),'BOJ.ART / JARVIS — LES VISUELS');
  if(!visualProvider.checked)refreshVisualProvider();
}
async function refreshVisualProvider(){
  const label=$('[data-visual-provider-state]');if(label)label.textContent='Vérification de la passerelle Jev…';
  visualProvider=await getVisualProviderStatus();
  const current=$('[data-visual-provider-state]');if(current)current.textContent=visualProvider.connected?'Jev a répondu sur ce poste.':visualProvider.configured?'Jev configuré · premier appel à tester.':'Jev à raccorder · les raccourcis locaux sont disponibles.';
  const input=$('#visual-command-form input[value="typesafe"]');if(input){input.disabled=!visualProvider.configured;if(input.disabled&&input.checked){input.checked=false;$('#visual-command-form input[value="local"]').checked=true;}}
}
function visualPiece(command,project){
  const normalized=command.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/œ/g,'oe');
  const candidates=project.pieces.filter(p=>{const name=p.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/œ/g,'oe');return name.length>2&&normalized.includes(name)||/\bsocle\b/.test(normalized)&&/socle/.test(name);});
  if(candidates.length>1)throw new Error('Plusieurs pièces correspondent. Sélectionnez la pièce à inspecter dans le dossier.');
  if(/\bsocle\b/.test(normalized)&&!candidates.length)throw new Error('Ce dossier ne contient pas de socle.');
  return candidates[0]||getPiece();
}
async function performVisualRequest(command,{view=null,provider='local',log=true,localOnly=false}={}){
  store.refresh();if(store.integrityError||!getProject())return integrityFailure().message;
  if(visualBusy)return 'Une demande visuelle attend déjà son résultat.';
  const project=getProject(),selectionAtStart=store.state.selectedPieceId,sequence=++visualSequence;let message;
  try{
    const piece=visualPiece(command,project),context=visualContext(project,piece),availableViews=availableVisuals(project);
    let decision;
    if(view){if(!availableViews.includes(view))throw new Error('Ajoutez une pièce au dossier avant de l’inspecter.');decision={view,provider:'direct',message:'Scène choisie directement.'};}
    else if(provider==='typesafe'){
      if(!visualProvider.configured){openVisualDesk();throw new Error('Jev est à raccorder sur la tour. Les quatre scènes restent accessibles directement.');}
      visualBusy=true;setVisualReceipt('Jev choisit parmi les vues du poste…',{busy:true});
      decision=await requestVisualDecision({requestId:crypto.randomUUID(),command,context,availableViews});
      visualProvider={...visualProvider,connected:true,model:decision.model};
    }else decision=chooseLocalVisual(command,availableViews);
    if(sequence!==visualSequence)return 'Demande visuelle interrompue.';
    store.refresh();if(store.integrityError)throw new Error(store.integrityError);
    if(!contextIsCurrent(context,getProject())||store.state.selectedPieceId!==selectionAtStart)throw new Error('Le dossier ou sa pièce a changé. Redemandez le visuel pour la nouvelle révision.');
    if(decision.view==='none')message=decision.message;
    else{
      if(visualBusy&&$('#drawer').open&&!$('[data-visual-desk]'))throw new Error('Un autre panneau est ouvert. Le choix Jev n’a pas remplacé votre travail.');
      const draft=$('#visual-command-input');if(visualBusy&&draft&&draft.value.trim()!==command.trim())throw new Error('Votre demande a changé pendant la réponse. Le nouvel affichage attend votre envoi.');
      closeDrawer();closeCommand();
      message=await presentView(decision.view,{pieceId:piece?.id,remoteOnly:!localOnly,localOnly});
      if(decision.provider==='typesafe')message=`Jev (${decision.model}) · ${message}`;
    }
  }catch(error){message=error.message||'La demande visuelle n’a pas abouti.';}
  finally{visualBusy=false;}
  setVisualReceipt(message);
  if(log)dispatch('LOG',{projectId:project.id,message:'Régie visuelle — '+command+' → '+message});
  return message;
}
function announceVisualArrival(view){
  const scene=VISUAL_VIEWS.find(v=>v.id===view);if(!scene)return;
  clearTimeout(transferTimer);$('.visual-transfer-note')?.remove();
  const note=document.createElement('div');note.className='visual-transfer-note';note.setAttribute('role','status');
  note.innerHTML=`<b>${scene.screen}</b><div><strong>${esc(scene.label)}</strong><small>Vue ouverte · BOJ.ART / Jarvis</small></div>`;document.body.append(note);
  transferTimer=setTimeout(()=>{note.classList.add('leaving');setTimeout(()=>note.remove(),240);},3100);
}
function startDisplayBus(){if(displayBus)return;displayBus=createDisplayBus({getRole:()=>ui.station,onRequest:receiveDisplayRequest,onChange:updateDisplayPresence});updateDisplayPresence();}
startDisplayBus();
window.addEventListener('pagehide',()=>{visualSequence++;displayBus?.dispose();displayBus=null;workshopSync?.stop();workshopSync=null;});
window.addEventListener('pageshow',()=>{startDisplayBus();startWorkshopSync();});

icons();render(true);startWorkshopSync();if(!store.integrityError&&getProject()){void projectEvidence.inspect(getProject().id);void inspectAssetVault();
if(params.get('panel')==='regie')openVisualDesk();
else if(params.get('panel')==='signature')openIdentity();
else if(params.get('panel')==='fleet')openFleet();
else if(params.get('panel')==='continuite')openContinuity();
else if(params.get('panel')==='studio')openStudio();
else if(params.get('panel')==='contenus')openProjectStudio();
else if(params.get('panel')==='preparation')openPreparation();
else if(params.get('panel')==='decisions')openDecisionDesk();
else if(params.get('panel')==='inquiries')openInquiries();
}
fetch('./assets/archive-index.json').then(r=>r.ok?r.json():[]).then(data=>{archive=Array.isArray(data)?data:data.items||[];refreshProjectStudio();if(ui.screen==='panorama'||ui.screen==='pilotage'&&['archive','controle'].includes(ui.pilotTab))render(false);}).catch(()=>{});

// Exposed read-only inspection helpers support semantic QA without a browser engine.
export {esc,techName,executeCommand};
