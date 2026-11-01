import {calculateQuote} from './workshop.js';
import {buildMasterMission} from './control-plane.js';

/** Runs only supported browser preparation; external steps never become done. */
export function runProjectPreparation(store, projectId){
  const before=buildMasterMission(store.state,projectId);
  const results=[];
  const project=()=>{const p=store.state.projects.find(p=>p.id===projectId);if(!p)throw new RangeError('Le projet de la mission est introuvable.');return p;};
  const record=(id,label,status,detail,evidence={})=>results.push({id,label,status,detail,...evidence});
  if(project().pieces.length){
    const result=store.dispatch('PLAN_PROJECT',{projectId});
    const incomplete=Boolean(result.unassigned?.length||result.differentLots?.length);
    const status=!result.ok?'error':incomplete?'needs_input':result.planned?'performed':'preserved';
    record('simulation','Répartition des pièces',status,result.message,{planned:result.planned||0,unassigned:result.unassigned||[],differentLots:result.differentLots||[]});
  }else record('simulation','Répartition des pièces','needs_input','Le dossier ne contient encore aucune pièce.');

  const quote=project().quote;
  if(quote?.inputs){
    try{
      const inputs={...quote.inputs,quantity:project().quantity};
      calculateQuote(inputs);
      const result=store.dispatch('SAVE_QUOTE',{projectId,inputs});
      record('quote','Chiffrage du lot',result.ok?'performed':'error',result.message);
    }catch(error){record('quote','Chiffrage du lot','needs_input',error.message);}
  }else record('quote','Chiffrage du lot','needs_input','Renseignez les coûts du lot pour calculer son prix. Aucun coût n’a été inventé.');

  if(project().story?.trim()) record('story','Scénario BOJ.ART','preserved','Le scénario déjà enregistré est conservé.');
  else{
    const p=project();
    const text=[
      `BOJ.ART — ${p.name}`,
      `Projet : ${p.kind||'Création sur mesure'} · lot de ${p.quantity} exemplaire${p.quantity>1?'s':''}.`,
      '01 — Accroche : ouvrir sur un détail fort de l’œuvre ou du prototype terminé.',
      '02 — Le geste : filmer la préparation, la fabrication et le travail de la matière.',
      '03 — La transformation : relier la pièce brute à sa finition avec des raccords de mouvement.',
      '04 — La révélation : montrer la pièce entière, puis l’emblème original BOJ.ART.',
      'Direction proposée : fond sombre, œuvre lisible, accents rouges/magenta, signature blanche. Sélectionner des plans vérifiés dans la vidéothèque ou la captation du projet.',
      'Brouillon de scénario à monter ; aucune nouvelle vidéo exportée ni publication effectuée.'
    ].join('\n');
    const result=store.dispatch('SAVE_STORY',{projectId,text});
    record('story','Scénario BOJ.ART',result.ok?'performed':'error',result.message);
  }
  record('external','Fabrication et services externes','unconnected','Slicer, imprimantes, voix locale, publication et vente restent à raccorder. Aucune commande externe n’a été envoyée.');
  const outcome={format:'bojart.preparation-result.v1',projectId,projectName:before.projectName,projectRevision:before.projectRevision,results,mission:buildMasterMission(store.state,projectId)};
  store.dispatch('LOG',{projectId,message:`Jarvis — orchestration de ${before.projectName} : ${results.map(r=>r.label+' = '+r.status).join(' ; ')}.`});
  return outcome;
}
