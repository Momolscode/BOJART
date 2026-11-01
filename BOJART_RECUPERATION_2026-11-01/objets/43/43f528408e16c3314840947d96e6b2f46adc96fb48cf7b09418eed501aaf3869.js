/** BOJ.ART — a bounded presentation router. It cannot execute workshop operations. */
export const VISUAL_VIEWS=Object.freeze([
  Object.freeze({id:'model',label:'La pièce en 3D',short:'Inspecter',target:'creation',screen:'03',icon:'cube',image:'baki-detail.webp',description:'Tourner le modèle, examiner le maillage et la coupe.'}),
  Object.freeze({id:'art',label:'Les œuvres',short:'Révéler',target:'creation',screen:'03',icon:'spark',image:'atelier-motion-poster.webp',description:'Mettre les références BOJ.ART en mouvement.'}),
  Object.freeze({id:'film',label:'Le film d’atelier',short:'Revoir',target:'creation',screen:'03',icon:'film',image:'brand-film-frame-02-geste.webp',description:'Ouvrir le nouvel édit BOJ.ART de 22,7 secondes et ses contrôles de lecture.'}),
  Object.freeze({id:'production',label:'Le parc',short:'Superviser',target:'atelier',screen:'01',icon:'printer',image:'throne.webp',description:'Voir les machines et leur file de simulation.'})
]);
const ids=new Set(VISUAL_VIEWS.map(v=>v.id));
const plain=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&(Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null);
const positive=n=>Number.isSafeInteger(n)&&n>0;
const identifier=v=>typeof v==='string'&&v.length>0&&v.length<=128;
const normalized=v=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/œ/g,'oe');

export function visualContext(project,piece){
  if(!project||!identifier(project.id)||!positive(project.revision??1))throw new TypeError('Dossier indisponible pour l’affichage.');
  const context={projectId:project.id,projectRevision:project.revision??1};
  if(piece){if(!project.pieces.some(p=>p.id===piece.id)||!identifier(piece.id)||!positive(piece.revision??1))throw new TypeError('La pièce ne correspond pas au dossier.');Object.assign(context,{pieceId:piece.id,pieceRevision:piece.revision??1});}
  return context;
}
export function contextIsCurrent(context,project){
  if(!project||project.id!==context.projectId||(project.revision??1)!==context.projectRevision)return false;
  if(!context.pieceId)return true;
  const piece=project.pieces.find(p=>p.id===context.pieceId);
  return !!piece&&(piece.revision??1)===context.pieceRevision;
}
export function availableVisuals(project){return VISUAL_VIEWS.filter(v=>v.id!=='model'||project?.pieces?.length>0).map(v=>v.id);}

/** These explicit vocabulary rules are local, not an AI model or confidence estimate. */
export function chooseLocalVisual(command,availableViews=[...ids]){
  const text=normalized(command);
  if(!text.trim())return{view:'none',provider:'local',reason:'empty',message:'Décrivez le visuel à afficher.'};
  if(/\b(ne|pas|jamais|annule|annuler|stop)\b/.test(text))return{view:'none',provider:'local',reason:'negated',message:'La demande n’a pas modifié l’affichage.'};
  if(/\b(lance|demarre|imprime|supprime|publie|achete|envoie|pause|reprends)\b/.test(text)&&!/\b(visuel|vue|ecran|film|video)\b/.test(text))return{view:'none',provider:'local',reason:'outside_scope',message:'Cette régie choisit un visuel. Les opérations de l’atelier restent dans la commande principale.'};
  const productionText=text.replace(/\b(film|video)\s+(?:d[’']|de\s+l[’'])\s*atelier\b/g,'$1');
  const choices=[
    ['model',/\b(3d|stl|modele|socle|maillage|geometrie|coupe|volume|formes?|assemblage|eclate)\b/],
    ['film',/\b(film|video|sequence|montage|geste|peinture)\b/],
    ['art',/\b(oeuvres?|portfolio|signature|identite|inspiration|ambiance|revelation)\b/],
    ['production',/\b(parc|atelier|production|imprimantes?|machines?|charge|file|fabrication)\b/]
  ].filter(([id,re])=>re.test(id==='production'?productionText:text)).map(([id])=>id);
  // Only the atelier occurrence inside a film title is removed.
  const matches=choices;
  if(matches.length!==1)return{view:'none',provider:'local',reason:matches.length?'ambiguous':'unknown',message:matches.length?'Plusieurs vues correspondent. Choisissez une des quatre scènes.':'Choisissez une scène ou précisez : modèle 3D, œuvres, film ou parc.'};
  const view=matches[0];
  if(!availableViews.includes(view))return{view:'none',provider:'local',reason:'unavailable',message:'Cette vue a besoin d’une pièce dans le dossier.'};
  if(view==='production'&&/\b(droite?|ecran 0?3)\b/.test(text)||view!=='production'&&/\b(gauche|ecran 0?1)\b/.test(text))return{view:'none',provider:'local',reason:'target_mismatch',message:'Le parc est associé à l’écran 01 ; les œuvres, films et modèles à l’écran 03.'};
  return{view,provider:'local',reason:'matched',message:'Vue choisie par le vocabulaire local.'};
}

function sameContext(a,b){return plain(a)&&Object.keys(a).length===Object.keys(b).length&&Object.keys(b).every(k=>a[k]===b[k]);}
function checkedRequest(request){
  if(!plain(request)||Object.keys(request).some(k=>!['requestId','command','context','availableViews'].includes(k))||!identifier(request.requestId)||typeof request.command!=='string'||!request.command.trim()||request.command.length>2000||!plain(request.context))throw new TypeError('Demande visuelle invalide.');
  const c=request.context;
  if(!identifier(c.projectId)||!positive(c.projectRevision)||Object.keys(c).some(k=>!['projectId','projectRevision','pieceId','pieceRevision'].includes(k))||('pieceId'in c)!==('pieceRevision'in c)||('pieceId'in c)&&(!identifier(c.pieceId)||!positive(c.pieceRevision)))throw new TypeError('Contexte visuel invalide.');
  if(!Array.isArray(request.availableViews)||!request.availableViews.length||new Set(request.availableViews).size!==request.availableViews.length||request.availableViews.some(v=>!ids.has(v)))throw new TypeError('Liste des vues invalide.');
}
// Confidence is recorded separately. Selection thresholds apply to p and margin.
export function validateVisualDecision(data,request){
  checkedRequest(request);
  if(!plain(data)||data.ok!==true||data.requestId!==request.requestId||!sameContext(data.context,request.context)||data.provider!=='typesafe'||typeof data.model!=='string'||!data.model||data.model.length>128||!plain(data.decision))throw new Error('Le résultat Jev ne correspond pas à cette demande.');
  const d=data.decision,options=[...request.availableViews,'none'];
  if(!options.includes(d.view)||!plain(d.probabilities)||Object.keys(d.probabilities).length!==options.length||options.some(id=>typeof d.probabilities[id]!=='number'||!Number.isFinite(d.probabilities[id])||d.probabilities[id]<0||d.probabilities[id]>1))throw new Error('La réponse Jev contient une vue ou un score invalide.');
  const ranked=options.map(id=>[id,d.probabilities[id]]).sort((a,b)=>b[1]-a[1]);
  const sum=ranked.reduce((n,[,p])=>n+p,0),probability=ranked[0][1],margin=probability-(ranked[1]?.[1]||0);
  if(Math.abs(sum-1)>.001||typeof d.confidence!=='number'||!Number.isFinite(d.confidence)||d.confidence<0||d.confidence>1||typeof d.probability!=='number'||!Number.isFinite(d.probability)||Math.abs(d.probability-probability)>.001||typeof d.margin!=='number'||!Number.isFinite(d.margin)||Math.abs(d.margin-margin)>.001)throw new Error('La distribution Jev n’a pas pu être vérifiée.');
  if(d.selectedView!==undefined&&d.selectedView!==ranked[0][0])throw new Error('Le choix Jev et ses scores ne correspondent pas.');
  if(d.view!=='none'&&(d.view!==ranked[0][0]||probability+1e-10<.8||margin+1e-10<.15))throw new Error('Le choix Jev est trop incertain pour changer la vue.');
  return{view:d.view,provider:'typesafe',model:data.model,reason:d.reason||'selected',probability,margin,confidence:d.confidence,message:d.view==='none'?'Jev conserve l’affichage. Choisissez une scène ou précisez votre demande.':'Vue choisie par Jev ; l’écran doit encore confirmer son affichage.'};
}
export async function requestVisualDecision(request,{fetchImpl=globalThis.fetch,timeoutMs=10000}={}){
  checkedRequest(request);
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const response=await fetchImpl('/api/visual-decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),signal:controller.signal,credentials:'same-origin'});
    if(!response.ok)throw new Error(response.status===503?'Jev n’est pas configuré sur ce poste.':response.status===504?'Jev n’a pas répondu à temps. La vue est conservée.':'Le service Jev n’a pas pu choisir de vue.');
    return validateVisualDecision(await response.json(),request);
  }catch(error){if(error?.name==='AbortError')throw new Error('Jev n’a pas répondu à temps. La vue est conservée.');if(error instanceof SyntaxError)throw new Error('Le service Jev n’a pas renvoyé une décision valide.');throw error;}
  finally{clearTimeout(timer);}
}
export async function getVisualProviderStatus({fetchImpl=globalThis.fetch,timeoutMs=2500}={}){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const r=await fetchImpl('/api/visual-decision/status',{signal:controller.signal,credentials:'same-origin',cache:'no-store'});
    if(!r.ok)return{checked:true,configured:false,connected:false};
    const data=await r.json();
    return{checked:true,configured:data?.configured===true,connected:data?.configured===true&&data?.connected===true,model:typeof data?.model==='string'?data.model:null};
  }catch{return{checked:true,configured:false,connected:false};}finally{clearTimeout(timer);}
}
