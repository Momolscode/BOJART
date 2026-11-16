/** BOJ.ART — a project-bound desk for advisory comparisons, never a machine controller. */
import {DECISION_DOMAINS,DECISION_LIMITS,recommendLocalDecision,validateProjectDecision,decisionRuleExplanation} from './decision-contract.js';
import {buildPreparationDecisionRequest,buildAttentionDecisionRequest,buildEditorialDecisionRequest} from './decision-context.js';
import {requestProjectDecision,getDecisionProviderStatus} from './decision-client.js';
import {projectEditPlans,latestEditVersion} from './edit-plan.js';

const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,character=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const paths={
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  layers:'<path d="m3 8 9-5 9 5-9 5-9-5Zm0 5 9 5 9-5M3 18l9 5 9-5"/>',
  cube:'<path d="m12 3 9 5v9l-9 5-9-5V8l9-5Zm0 10 9-5m-9 5L3 8m9 5v9"/>',
  film:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4m10 0h4M3 15h4m10 0h4"/>',
  spark:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>',
  rotate:'<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/>',
  check:'<path d="m5 12 4 4L19 6"/>'
};
const glyph=name=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.arrow}</svg>`;
const uid=()=>`decision-${globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,12)}`;
const number=value=>Number.isFinite(value)?new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2}).format(value):'—';
const time=value=>Number.isFinite(value)?new Intl.DateTimeFormat('fr-FR',{hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(value):'—';
const GOALS={
  attention:[['blockers','Traiter les points bloquants'],['next_step','Choisir la prochaine vérification']],
  preparation:[['balanced','Équilibrer la marge brute'],['clearance','Maximiser la marge minimale'],['low_height','Réduire la hauteur brute']],
  editorial:[['showcase','Mettre l’œuvre en valeur'],['technique','Montrer le geste'],['custom_order','Présenter le sur-mesure'],['prototype','Documenter un prototype'],['offer','Préparer une offre']]
};
const MODES=[
  {id:'attention',label:'Priorités',detail:'Pièces, parc, contenus',icon:'layers'},
  {id:'preparation',label:'Orientations',detail:'Boîte brute mesurée',icon:'cube'},
  {id:'editorial',label:'Édit vidéo',detail:'Séries BOJ.ART',icon:'film'}
];
const FILE_LABELS={unreferenced:'sans STL',unchecked:'à relire',missing:'fichier absent',invalid:'à vérifier',measured:'STL mesuré'};
const EMPTY_PROVIDER={checked:false,configured:false,connected:false,availability:'unchecked',model:null,advisoryOnly:true};
const empty=message=>({request:null,options:[],unavailableReason:message});
const samePacket=(left,right)=>JSON.stringify(left?.request||null)===JSON.stringify(right?.request||null);
function recordsFor(project){try{return projectEditPlans(project);}catch{return[];}}
function defaultContext(project,report){return{project,report,activeProjectId:project?.id,evidenceStatus:report?'ready':'unchecked'};}
function alignSelection(state,context){
  const pieces=context.report?.pieces||context.project?.pieces||[];
  if(!state.pieceId)state.pieceId=(pieces.find(piece=>piece.file?.status==='measured')||pieces[0])?.id||null;
  const machines=context.report?.machines||[];
  if(!state.machineId){
    const piece=pieces.find(item=>item.id===state.pieceId);
    state.machineId=(machines.find(machine=>machine.declared&&machine.record?.technology===piece?.tech)||machines.find(machine=>machine.declared)||machines[0])?.id||null;
  }
}
function packetFor(context,state,requestId=state.requestId){
  if(!context?.project||context.project.id!==state.projectId)return empty('Le dossier lié à ce bureau n’est plus disponible. Rouvrez le bureau depuis le projet souhaité.');
  if(context.activeProjectId&&context.activeProjectId!==state.projectId)return empty('Le dossier actif a changé. Ce bureau reste lié au dossier affiché ; rouvrez-le pour comparer le projet souhaité.');
  try{
    if(state.domain==='editorial')return buildEditorialDecisionRequest(context.project,{requestId,goal:state.goals.editorial,planId:state.planId});
    if(!context.report)return empty(context.evidenceStatus==='checking'?'La lecture des pièces est en cours. Les candidats apparaîtront avec le rapport.':'Relisez les fichiers dans la préparation pour disposer de preuves actuelles.');
    if(context.report.project?.id!==context.project.id||context.report.project?.revision!==context.project.revision)return empty('Le rapport de préparation ne correspond plus à la révision de ce dossier. Relisez ses fichiers.');
    if(state.domain==='preparation')return buildPreparationDecisionRequest(context.report,{requestId,pieceId:state.pieceId,machineId:state.machineId,goal:state.goals.preparation});
    return buildAttentionDecisionRequest(context.report,context.project,{requestId,goal:state.goals.attention});
  }catch(error){return empty(error?.message||'Les preuves du dossier ne permettent pas encore cette comparaison.');}
}
function initialState({project,report,provider,initial={}}){
  const domain=MODES.some(mode=>mode.id===initial.domain)?initial.domain:'attention';
  const state={projectId:project?.id||'',context:defaultContext(project,report),provider:{...EMPTY_PROVIDER,...(provider||{})},domain,goals:{attention:'blockers',preparation:'balanced',editorial:'showcase'},pieceId:typeof initial.pieceId==='string'?initial.pieceId:null,machineId:typeof initial.machineId==='string'?initial.machineId:null,planId:typeof initial.planId==='string'?initial.planId:null,initialOrientationId:typeof initial.orientationId==='string'?initial.orientationId:null,requestId:uid(),bundle:null,result:null,expired:false,busy:false,busyProvider:null,statusBusy:false,message:'',messageKind:'info',canInspect:false,motion:true};
  if(GOALS[domain].some(([id])=>id===initial.goal))state.goals[domain]=initial.goal;
  alignSelection(state,state.context);state.bundle=packetFor(state.context,state);return state;
}
function providerMarkup(state,esc,icon){
  const provider=state.provider;
  const label=state.statusBusy?'Vérification du service…':provider.connected?'Jev · échange vérifié':provider.configured?'Jev configuré · échange à vérifier':!provider.checked?'Jev non vérifié':provider.availability==='unavailable'?'Jev indisponible ici':'Jev non configuré';
  return `<div class="dd-provider" data-provider-connected="${provider.connected===true}"><div><strong>Règles locales disponibles</strong><span data-dd-provider-label>${esc(label)}${provider.model?` · ${esc(provider.model)}`:''}</span></div><button type="button" data-dd-status-refresh aria-label="Vérifier la disponibilité du service Jev"${state.statusBusy?' disabled':''}>${icon('rotate')}</button></div>`;
}
function selectMarkup(state,esc){
  const project=state.context.project,report=state.context.report;
  const goals=GOALS[state.domain];
  let extra='';
  if(state.domain==='preparation'){
    const pieces=report?.pieces||project?.pieces||[],machines=report?.machines||[];
    const missingPiece=state.pieceId&&!pieces.some(piece=>piece.id===state.pieceId)?`<option value="${esc(state.pieceId)}" selected>Pièce introuvable · ${esc(state.pieceId)}</option>`:'';
    const missingMachine=state.machineId&&!machines.some(machine=>machine.id===state.machineId)?`<option value="${esc(state.machineId)}" selected>Machine à relire · ${esc(state.machineId)}</option>`:'';
    extra=`<label class="dd-field" for="dd-piece">Pièce<select id="dd-piece" name="dd-piece">${missingPiece}${pieces.length?pieces.map(piece=>`<option value="${esc(piece.id)}"${piece.id===state.pieceId?' selected':''}>${esc(piece.name||piece.id)} · ${esc(FILE_LABELS[piece.file?.status]||'mesure à relire')}</option>`).join(''):missingPiece?'':'<option value="">Aucune pièce dans le dossier</option>'}</select></label><label class="dd-field" for="dd-machine">Machine à comparer<select id="dd-machine" name="dd-machine">${missingMachine}${machines.length?machines.map(machine=>`<option value="${esc(machine.id)}"${machine.id===state.machineId?' selected':''}>${esc(machine.name||machine.id)} · ${machine.declared?'fiche déclarée':'à déclarer'}</option>`).join(''):missingMachine?'':'<option value="">Rapport de parc nécessaire</option>'}</select></label>`;
  }
  if(state.domain==='editorial'){
    const records=recordsFor(project);
    const missingPlan=state.planId!==null&&!records.some(record=>record.id===state.planId)?`<option value="${esc(state.planId)}" selected>Plan introuvable · ${esc(state.planId)}</option>`:'';
    extra=`<label class="dd-field dd-field-wide" for="dd-plan">Plan de référence<select id="dd-plan" name="dd-plan"><option value=""${state.planId===null?' selected':''}>Aucun plan sélectionné · nouvelle intention</option>${missingPlan}${records.map(record=>{const latest=latestEditVersion(record);return `<option value="${esc(record.id)}"${record.id===state.planId?' selected':''}>${esc(latest.plan.title)} · version ${latest.revision}</option>`;}).join('')}</select></label>`;
  }
  return `<div class="dd-selectors"><label class="dd-field dd-field-wide" for="dd-goal">Votre objectif<select id="dd-goal" name="dd-goal">${goals.map(([id,label])=>`<option value="${id}"${id===state.goals[state.domain]?' selected':''}>${esc(label)}</option>`).join('')}</select></label>${extra}</div>`;
}
function envelopeMarkup(option,esc){
  const dimensions=option.facts?.dimensionsMm,clearance=option.facts?.clearanceMm;
  if(!Array.isArray(dimensions)||!Array.isArray(clearance))return '';
  return `<span class="dd-envelope" aria-label="Boîte brute rapportée au volume utile déclaré">${dimensions.map((dimension,index)=>{const volume=dimension+clearance[index],fill=volume>0?Math.max(0,Math.min(100,dimension/volume*100)):0;return `<span><span>${['X','Y','Z'][index]}</span><i aria-hidden="true"><b style="--dd-fill:${fill.toFixed(3)}%"></b></i><em>${esc(number(dimension))} / ${esc(number(volume))} mm</em></span>`;}).join('')}</span>`;
}
function candidateMarkup(option,index,state,esc,icon){
  const selected=state.result?.decision?.candidateId===option.id&&!state.expired;
  const current=!selected&&state.domain==='preparation'&&state.initialOrientationId&&option.id==='orientation:'+state.initialOrientationId;
  const kind=option.facts?.kind;
  const badge=kind==='raw_envelope_orientation'?'VOLUME BRUT':kind==='editorial_intention'?'INTENTION DE SÉRIE':kind==='machine_record_review'?'FICHE MACHINE':kind==='piece_review'?'PIÈCE DU DOSSIER':kind==='saved_edit_review'?'PLAN ENREGISTRÉ':'MONTAGE À PRÉPARER';
  return `<button type="button" class="dd-candidate${selected?' is-recommended':current?' is-current':''}" data-dd-inspect="${esc(option.id)}"${!state.canInspect||state.busy?' disabled':''}><span class="dd-candidate-index">${String(index+1).padStart(2,'0')}</span><span class="dd-candidate-main"><small>${badge}${selected?' · CONSEILLÉ':current?' · OUVERT DANS L’ÉTABLI':''}</small><strong>${esc(option.label)}</strong><span>${esc(option.summary)}</span>${envelopeMarkup(option,esc)}</span><span class="dd-candidate-arrow" aria-hidden="true">${icon('arrow')}</span></button>`;
}
function resultMarkup(state,esc,icon){
  const result=state.result,bundle=state.bundle;
  if(!result)return `<div class="dd-result-empty"><span class="dd-result-symbol" aria-hidden="true">${icon('spark')}</span><p class="dd-kicker">LE CONSEIL</p><h3 id="dd-result-title">Un choix.<br>Des raisons.</h3><p>Les candidats viennent du dossier. Choisissez votre objectif, puis demandez une comparaison.</p><div class="dd-result-context"><span>Dossier lié</span><strong>${esc(state.context.project?.name||'Indisponible')}</strong><small>Révision ${esc(state.context.project?.revision||'—')}</small></div></div>`;
  const candidate=bundle.options.find(option=>option.id===result.decision.candidateId);
  const local=result.provider==='local_rules',abstained=!result.decision.candidateId;
  const title=state.expired?'Conseil à actualiser':abstained?'Gardez le choix manuel.':candidate?.label||'Candidat à actualiser';
  const source=state.expired?'À ACTUALISER':local?'RÈGLE LOCALE':abstained?'JEV S’ABSTIENT':'CONSEIL DE JEV';
  const why=state.expired?'Cette comparaison a plus de 60 secondes. Demandez un nouveau conseil avant d’ouvrir sa recommandation.':abstained?(result.decision.reason==='no_match'?'Jev n’a retenu aucun candidat. Les options du dossier restent accessibles.':'Les scores de Jev ne permettent pas de retenir un candidat. Examinez les options du dossier.'):candidate?.summary||'Les données ont changé. Reprenez la comparaison.';
  const rule=local?decisionRuleExplanation(bundle.request):'Jev choisit parmi les candidats présentés ; les faits ci-dessous restent ceux du dossier.';
  return `<div class="dd-result-card" data-dd-result-provider="${esc(result.provider)}" data-dd-result-state="${state.expired?'expired':abstained?'abstained':'recommended'}"><p class="dd-result-badge">${source}</p><h3 id="dd-result-title">${esc(title)}</h3><p class="dd-result-why">${esc(why)}</p>${!state.expired?`<p class="dd-rule">${esc(rule)}</p>`:''}${candidate&&!state.expired?envelopeMarkup(candidate,esc):''}${!local&&!state.expired?`<dl class="dd-scores"><div><dt>Score de sélection</dt><dd>${number(result.decision.probability*100)} %</dd></div><div><dt>Écart au suivant</dt><dd>${number(result.decision.margin*100)} pts</dd></div></dl><p class="dd-score-note">Seuils expérimentaux · aucun score de qualité d’impression.</p>`:''}<div class="dd-result-context"><span>${local?'Règle exécutée sur ce poste':esc(result.model||'Jev')}</span><strong>Révision ${esc(result.context.projectRevision)} · ${time(result.at)}</strong><small>À actualiser après 60 s ou modification des preuves.</small></div>${candidate&&!abstained?`<button type="button" class="dd-primary dd-result-open" data-dd-open-result${state.expired||state.busy||!state.canInspect?' disabled':''}>Examiner ce candidat ${icon('arrow')}</button>`:''}</div>`;
}
function deskMarkup(state,esc=escapeHTML,icon=glyph){
  const project=state.context.project,definition=DECISION_DOMAINS.find(domain=>domain.id===state.domain);
  const noRequest=!state.bundle?.request;
  const changed=state.context.activeProjectId&&state.context.activeProjectId!==state.projectId;
  return `<header class="dd-head"><img src="./assets/logo.webp" alt="Emblème original BOJ.ART" width="43" height="50"><div><p class="dd-kicker">JARVIS / LE BUREAU DES DÉCISIONS</p><h3>EXAMINER. <em>PUIS CHOISIR.</em></h3></div></header><div class="dd-project-line"><span>${escapeHTML(project?.name||'Dossier indisponible')}</span><strong>Révision ${esc(project?.revision||'—')}</strong><small>Conseils · aucune commande machine</small></div>${providerMarkup(state,esc,icon)}<div class="dd-modes" role="group" aria-label="Domaine de la comparaison">${MODES.map(mode=>`<button type="button" data-dd-domain="${mode.id}" aria-pressed="${state.domain===mode.id}"><span>${icon(mode.icon)}</span><strong>${mode.label}</strong><small>${mode.detail}</small></button>`).join('')}</div><div class="dd-status ${state.messageKind==='error'?'is-error':''}" role="status" aria-live="polite" data-dd-status${state.message?'':' hidden'}>${esc(state.message)}</div>${changed?`<p class="dd-context-changed">Le dossier actif a changé. Ce bureau reste lié à ${esc(project?.name||state.projectId)}. Rouvrez-le depuis le projet souhaité.</p>`:''}<div class="dd-layout"><section class="dd-comparison" aria-label="Objectif et candidats">${selectMarkup(state,esc)}<p class="dd-question">${esc(definition?.question||'')}</p><div class="dd-compare-actions"><button type="button" class="dd-primary" data-dd-run="local"${noRequest||state.busy?' disabled':''}>${icon('layers')}${state.busy&&state.busyProvider==='local'?'Comparaison locale…':'Comparer localement'}</button><button type="button" class="dd-secondary" data-dd-run="jev"${noRequest||state.busy||!state.provider.configured?' disabled':''}>${icon('spark')}${state.busy&&state.busyProvider==='jev'?'Jev compare…':'Demander à Jev'}</button></div><p class="dd-provider-note">Jev utilise le service TypeSafe lorsqu’il est configuré. Le choix local reste disponible.</p><div class="dd-candidates-heading"><h4>Les candidats <span>${state.bundle.options.length}</span></h4><button type="button" data-dd-refresh>${icon('rotate')}Relire le dossier</button></div>${noRequest?`<div class="dd-unavailable">${icon('info')}<p>${esc(state.bundle.unavailableReason||'Aucun candidat disponible.')}</p>${state.domain!=='editorial'&&!changed?`<button type="button" data-action="preparation" data-project-id="${esc(state.projectId)}">Ouvrir la préparation ${icon('arrow')}</button>`:''}</div>`:`<div class="dd-candidates" aria-label="Candidats issus des preuves du dossier">${state.bundle.options.map((option,index)=>candidateMarkup(option,index,state,esc,icon)).join('')}</div>`}<details class="dd-scope"><summary>Ce que cette comparaison examine</summary><p>${esc((definition?.evidence||[]).join(' · '))}</p><ul>${(definition?.limits||[]).map(limit=>`<li>${esc(limit)}</li>`).join('')}</ul></details></section><aside class="dd-result" aria-labelledby="dd-result-title" aria-busy="${state.busy}">${resultMarkup(state,esc,icon)}</aside></div>`;
}

export function renderDecisionDesk({project,report=null,provider=EMPTY_PROVIDER,initial={},esc=escapeHTML,icon=glyph}){
  const state=initialState({project,report,provider,initial});
  return `<section class="decision-desk" data-decision-project="${esc(state.projectId)}" data-decision-project-revision="${esc(project?.revision||'')}" data-decision-motion="true">${deskMarkup(state,esc,icon)}</section>`;
}

/** The only effect allowed here is opening a currently rebuilt, closed candidate target. */
export function mountDecisionDesk(root,{projectId,initial={},getContext,getProviderStatus=getDecisionProviderStatus,requestDecision=requestProjectDecision,onInspect,motion=true,esc=escapeHTML,icon=glyph}={}){
  const desk=root?.matches?.('.decision-desk')?root:root?.querySelector?.('.decision-desk');
  if(!desk||typeof getContext!=='function')throw new TypeError('Le bureau et sa relecture de contexte sont requis.');
  const boundId=projectId||desk.dataset.decisionProject;
  let state=initialState({project:{id:boundId,name:desk.querySelector('.dd-project-line>span')?.textContent||'Dossier lié',revision:Number(desk.dataset.decisionProjectRevision)||null},report:null,initial});
  state.projectId=boundId;state.canInspect=typeof onInspect==='function';state.motion=motion!==false;
  let disposed=false,epoch=0,refreshEpoch=0,providerEpoch=0,expiryTimer=null;
  const doc=desk.ownerDocument,win=doc.defaultView;
  function clearExpiry(){if(expiryTimer!==null){win.clearTimeout(expiryTimer);expiryTimer=null;}}
  function clearResult(){clearExpiry();state.result=null;state.expired=false;}
  function announce(message,kind='info'){state.message=message;state.messageKind=kind;}
  function rememberFocus(){
    const focused=doc.activeElement;
    if(!focused||!desk.contains(focused))return null;
    for(const attribute of ['data-dd-domain','data-dd-run','data-dd-inspect','data-dd-open-result','data-dd-status-refresh','data-dd-refresh','name'])if(focused.hasAttribute(attribute))return{attribute,value:focused.getAttribute(attribute)};
    return null;
  }
  function render(){
    if(disposed)return;
    const focus=rememberFocus();
    desk.innerHTML=deskMarkup(state,esc,icon);desk.dataset.decisionMotion=String(state.motion);desk.dataset.decisionDomain=state.domain;
    if(focus){const target=[...desk.querySelectorAll(`[${focus.attribute}]`)].find(node=>node.getAttribute(focus.attribute)===focus.value);if(target&&!target.disabled)target.focus({preventScroll:true});}
  }
  async function readContext(){
    const context=await getContext();
    return context&&typeof context==='object'?context:{project:null,report:null,activeProjectId:null,evidenceStatus:'unavailable'};
  }
  async function refreshContext(){
    const revision=++refreshEpoch;
    try{
      const context=await readContext();if(disposed||revision!==refreshEpoch)return false;
      alignSelection(state,context);
      const bundle=packetFor(context,state);
      const changed=!samePacket(state.bundle,bundle)||state.context.project?.revision!==context.project?.revision||state.context.activeProjectId!==context.activeProjectId;
      if(changed){epoch++;if(state.result)announce('Les preuves ont changé. Demandez une nouvelle comparaison.');clearResult();}
      state.context=context;state.bundle=bundle;render();return !!bundle.request;
    }catch(error){if(disposed||revision!==refreshEpoch)return false;epoch++;clearResult();state.bundle=empty(error?.message||'Le dossier n’a pas pu être relu.');announce(state.bundle.unavailableReason,'error');render();return false;}
  }
  async function refreshProvider(){
    if(typeof getProviderStatus!=='function')return;
    const revision=++providerEpoch;state.statusBusy=true;render();
    try{const provider=await getProviderStatus();if(disposed||revision!==providerEpoch)return;state.provider={...EMPTY_PROVIDER,...(provider||{})};}
    catch{if(disposed||revision!==providerEpoch)return;state.provider={...EMPTY_PROVIDER,checked:true,availability:'unavailable'};}
    finally{if(!disposed&&revision===providerEpoch){state.statusBusy=false;render();}}
  }
  function armExpiry(result){
    clearExpiry();
    const delay=Math.max(0,result.at+DECISION_LIMITS.ageMs-Date.now()+1);
    expiryTimer=win.setTimeout(()=>{if(disposed||state.result!==result)return;state.expired=true;announce('Ce conseil a expiré. Les candidats restent consultables ; relancez la comparaison pour une recommandation actuelle.');render();},delay);
  }
  async function compare(provider){
    if(disposed||state.busy||!state.bundle.request||provider==='jev'&&!state.provider.configured)return;
    const actionEpoch=++epoch;
    state.requestId=uid();clearResult();state.bundle=packetFor(state.context,state);state.busy=true;state.busyProvider=provider;
    announce(provider==='jev'?'Jev compare les candidats du dossier…':'La règle locale compare les preuves du dossier…');render();
    const requestId=state.requestId;
    const currentPacket=async()=>{
      if(disposed||actionEpoch!==epoch)return null;
      const context=await readContext();if(disposed||actionEpoch!==epoch)return null;
      return packetFor(context,state,requestId).request;
    };
    try{
      const context=await readContext();if(disposed||actionEpoch!==epoch)return;
      const bundle=packetFor(context,state,requestId);
      if(!bundle.request)throw new Error(bundle.unavailableReason);
      const result=provider==='jev'?await requestDecision(bundle.request,{getCurrentRequest:currentPacket}):await recommendLocalDecision(bundle.request);
      if(disposed||actionEpoch!==epoch)return;
      const currentContext=await readContext();if(disposed||actionEpoch!==epoch)return;
      const currentBundle=packetFor(currentContext,state,requestId);
      if(!currentBundle.request)throw new Error(currentBundle.unavailableReason);
      const checked=await validateProjectDecision(result,currentBundle.request);
      if(disposed||actionEpoch!==epoch)return;
      state.context=currentContext;state.bundle=currentBundle;state.result=checked;state.expired=false;
      if(checked.provider==='typesafe')state.provider={...state.provider,checked:true,configured:true,connected:true,availability:'connected',model:checked.model,lastVerifiedAt:checked.at};
      const chosen=currentBundle.options.find(option=>option.id===checked.decision.candidateId);
      announce(chosen?`${checked.provider==='local_rules'?'Règle locale':'Jev'} : ${chosen.label}. Ouvrez le candidat pour l’examiner.`:'Jev ne retient aucun candidat. Le choix manuel reste disponible.');
      armExpiry(checked);
    }catch(error){if(!disposed&&actionEpoch===epoch){clearResult();announce(error?.message||'La comparaison n’a pas abouti. Les candidats restent accessibles.','error');}}
    finally{if(!disposed){state.busy=false;state.busyProvider=null;render();}}
  }
  async function inspect(candidateId,{fromResult=false}={}){
    if(disposed||state.busy||!state.canInspect||!state.bundle.request)return;
    const actionEpoch=epoch,renderedBundle=state.bundle,requestId=state.bundle.request.requestId;
    try{
      const context=await readContext();if(disposed||actionEpoch!==epoch)return;
      const bundle=packetFor(context,state,requestId);
      if(!bundle.request||!samePacket(renderedBundle,bundle))throw new Error('Le dossier ou ses preuves ont changé. Relisez les candidats avant de les ouvrir.');
      let id=candidateId;
      if(fromResult){
        if(!state.result||state.expired)throw new Error('Ce conseil doit être actualisé.');
        const checked=await validateProjectDecision(state.result,bundle.request);
        if(disposed||actionEpoch!==epoch)return;
        id=checked.decision.candidateId;
      }
      const confirmedContext=await readContext();
      if(disposed||actionEpoch!==epoch)return;
      const confirmedBundle=packetFor(confirmedContext,state,requestId);
      if(!confirmedBundle.request||!samePacket(bundle,confirmedBundle))throw new Error('Les preuves ont changé pendant la vérification. Relisez les candidats.');
      if(fromResult&&Date.now()-state.result.at>DECISION_LIMITS.ageMs)throw new Error('Ce conseil a expiré. Demandez une nouvelle comparaison.');
      const candidate=confirmedBundle.options.find(option=>option.id===id);
      if(!candidate)throw new Error('Aucun candidat actuel ne correspond à ce choix.');
      const answer=await onInspect({...candidate.target});
      if(disposed)return;
      if(answer===false||answer?.ok===false)throw new Error(answer?.message||'Le candidat n’a pas pu être ouvert. Relisez le contexte.');
      announce('Ouverture demandée pour : '+candidate.label+'.');render();
    }catch(error){if(!disposed&&actionEpoch===epoch){clearResult();announce(error?.message||'Cette cible doit être relue avant ouverture.','error');render();}}
  }
  function onChange(event){
    const control=event.target;
    if(!control?.matches?.('select[name^="dd-"]'))return;
    const name=control.name;
    if(name==='dd-goal'&&GOALS[state.domain].some(([id])=>id===control.value))state.goals[state.domain]=control.value;
    else if(name==='dd-piece')state.pieceId=control.value||null;
    else if(name==='dd-machine')state.machineId=control.value||null;
    else if(name==='dd-plan')state.planId=control.value||null;
    else return;
    epoch++;state.requestId=uid();state.initialOrientationId=null;clearResult();state.bundle=packetFor(state.context,state);announce('Objectif ou cible modifié. Les candidats ont été actualisés.');render();
  }
  function onClick(event){
    const button=event.target?.closest?.('button');if(!button||!desk.contains(button)||button.disabled)return;
    if(button.hasAttribute('data-dd-domain')){
      const domain=button.dataset.ddDomain;if(!MODES.some(mode=>mode.id===domain)||domain===state.domain)return;
      epoch++;state.domain=domain;state.requestId=uid();clearResult();alignSelection(state,state.context);state.bundle=packetFor(state.context,state);announce('');render();
    }else if(button.hasAttribute('data-dd-run'))void compare(button.dataset.ddRun);
    else if(button.hasAttribute('data-dd-inspect'))void inspect(button.dataset.ddInspect);
    else if(button.hasAttribute('data-dd-open-result'))void inspect(null,{fromResult:true});
    else if(button.hasAttribute('data-dd-status-refresh'))void refreshProvider();
    else if(button.hasAttribute('data-dd-refresh'))void refreshContext();
  }
  desk.addEventListener('click',onClick);desk.addEventListener('change',onChange);
  const ready=refreshContext().then(()=>{if(!disposed)return refreshProvider();});
  return{
    ready,
    refreshContext,
    setMotion(value){state.motion=value!==false;if(!disposed)desk.dataset.decisionMotion=String(state.motion);},
    dispose(){if(disposed)return;disposed=true;epoch++;refreshEpoch++;providerEpoch++;clearExpiry();desk.removeEventListener('click',onClick);desk.removeEventListener('change',onChange);}
  };
}
