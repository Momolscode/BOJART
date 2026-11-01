/** BOJ.ART — pure orchestration descriptions. This module executes no action. */
import {summarizeFleet} from './fleet-registry.js';
import {projectEditPlans, latestEditVersion} from './edit-plan.js';
import {inspectDeclaredPreparation} from './preparation.js';
import {preparationReportContext} from './project-evidence.js';
export const DOMAIN_CATALOG = Object.freeze([
  ['creation','Création','Brief, fichiers et inspection des modèles.'],
  ['preparation','Préparation','Affectation, profils et préparation de fabrication.'],
  ['production','Production','File et commandes de simulation du parc.'],
  ['contenus','Contenus','Archives, scénarios et futures publications.'],
  ['commerce','Commerce','Dossiers, devis et futures commandes.'],
  ['ressources','Ressources','Machines, matières et moyens de l’atelier.'],
  ['systeme','Système','Poste, sauvegardes, journal et connexions.'],
  ['robotique','Robotique','Prototypes, validation et futurs équipements.']
].map(([id,label,description])=>Object.freeze({id,label,description})));

const DOMAIN_IDS=new Set(DOMAIN_CATALOG.map(d=>d.id));
const copy=value=>JSON.parse(JSON.stringify(value));
const positiveDimensions=d=>Array.isArray(d)&&d.length===3&&d.every(n=>typeof n==='number'&&Number.isFinite(n)&&n>0);
const permutations=([x,y,z])=>[[x,y,z],[x,z,y],[y,x,z],[y,z,x],[z,x,y],[z,y,x]];
function stateArrays(state){
  if(!state||!Array.isArray(state.projects)||!Array.isArray(state.machines)||!Array.isArray(state.jobs))throw new TypeError('État de l’atelier invalide.');
  return state;
}
function exactProject(state,id){
  stateArrays(state);
  if(typeof id!=='string'||!id)throw new TypeError('Un identifiant de projet explicite est requis.');
  const project=state.projects.find(p=>p.id===id);
  if(!project)throw new RangeError('Projet introuvable : '+id+'.');
  if(!Array.isArray(project.pieces))throw new TypeError('Les pièces du projet sont invalides.');
  return project;
}
function fits(piece,machine){
  return ['resin','fdm'].includes(piece.tech)&&piece.tech===machine.tech&&positiveDimensions(piece.dims)&&positiveDimensions(machine.volume)&&permutations(piece.dims).some(d=>d.every((n,i)=>n<=machine.volume[i]));
}
function projectEvidence(state,project){
  const pieces=project.pieces.map(piece=>{
    const revision=piece.revision??1;
    const job=state.jobs.find(j=>j.projectId===project.id&&j.pieceId===piece.id&&j.revision===revision);
    const compatible=state.machines.filter(m=>fits(piece,m)).map(m=>m.id);
    return {id:piece.id,name:piece.name,tech:piece.tech,dims:copy(piece.dims),revision,
      assetId:piece.assetId||null,unit:piece.unit??null,triangles:piece.triangles??null,
      fileState:piece.assetId?'referenced_unverified':'missing',compatibleMachines:compatible,
      assignedMachine:job?.machine||piece.machine||null,jobId:job?.id||null,
      jobQuantity:job?.quantity??null,quantity:project.quantity};
  });
  return {pieces,hasBrief:typeof project.name==='string'&&!!project.name.trim()&&Number.isInteger(project.quantity)&&project.quantity>0&&Number.isFinite(project.height)&&project.height>0,
    referencedFiles:pieces.filter(p=>p.assetId).length,
    compatiblePieces:pieces.filter(p=>p.compatibleMachines.length).length,
    assignments:pieces.filter(p=>p.jobId).length,
    differentLots:pieces.filter(p=>p.jobQuantity!==null&&p.jobQuantity!==project.quantity).map(p=>p.id)};
}
const future=(adapter,operation)=>({adapter,operation,implemented:false});

/** New operation objects are returned on every call; targets are captured now. */
export function buildOperations(state,archiveCount=0){
  const project=exactProject(state,state?.projectId),e=projectEvidence(state,project);
  if(!Number.isSafeInteger(archiveCount)||archiveCount<0)throw new TypeError('Le nombre de références doit être un entier positif ou nul.');
  const operations=[];
  function add(id,label,domain,mode,targetAction,requirement,available=true,extra={}){
    if(!DOMAIN_IDS.has(domain))throw new Error('Domaine inconnu.');
    operations.push({id,label,domain,mode,requirement,targetAction,projectId:project.id,available:mode!=='unconnected'&&!!available,...extra});
  }
  add('creation.import_stl','Importer des STL','creation','local','import','Sélectionner des fichiers locaux ; leurs unités et leur préparation restent à vérifier.');
  add('creation.inspect_3d','Inspecter les modèles','creation','local','wall-model','Un binaire accessible est nécessaire pour voir une pièce importée ; sinon le viewer indique le démonstrateur.',project.pieces.length>0,{pieceId:state.selectedPieceId||null});
  add('creation.edit_brief','Modifier le brief','creation','local','project-edit','La hauteur du brief ne redimensionne pas les fichiers.');
  add('creation.generate_model','Créer un modèle par intention','creation','unconnected','connections','Moteur de génération ou de CAO à intégrer.',false,{futureEndpoint:future('modeling','create_model')});
  add('preparation.control','Ouvrir la mission complète','preparation','local','control','Lire les étapes, les dépendances et les actions disponibles pour ce projet.');
  add('preparation.section_3d','Inspecter une coupe 3D','preparation','local','wall-model','Coupe visuelle : ne produit ni couches ni fichier machine.',project.pieces.length>0,{pieceId:state.selectedPieceId||null});
  add('preparation.assign_jobs','Répartir les pièces en simulation','preparation','simulation','plan','Procédé et enveloppe brute uniquement ; profils, supports et orientation non qualifiés.',project.pieces.length>0);
  add('preparation.slice','Slicer avec un profil validé','preparation','unconnected','connections','Moteur local, préparation géométrique et profils machine/matière validés requis.',false,{futureEndpoint:future('slicer','slice')});
  add('production.view','Ouvrir la file de production','production','local','production-view','Afficher les travaux et leurs instantanés de démonstration.');
  add('production.start_physical','Envoyer une fabrication réelle','production','unconnected','connections','Fichier machine vérifié, machine identifiée et passerelle authentifiée requis.',false,{futureEndpoint:future('printer_gateway','start_job')});
  for(const machine of state.machines){
    const jobs=state.jobs.filter(j=>j.machine===machine.id);
    const job=jobs.find(j=>j.status==='running')||jobs.find(j=>j.status==='paused')||jobs.find(j=>j.status==='queued');
    if(!job)continue;
    add('production.machine.'+machine.id,(job.status==='running'?'Mettre en pause ':job.status==='paused'?'Reprendre ':'Démarrer la simulation ')+machine.id,'production','simulation','toggle-machine',
      'Commande de simulation ciblée ; une pause conserve la réservation de la ressource.',true,
      {projectId:job.projectId,machineId:machine.id,pieceId:job.pieceId,jobId:job.id,expectedStatus:job.status});
  }
  add('contenus.archive','Explorer la vidéothèque','contenus','local','open-archive',archiveCount+' référence(s) indexée(s) ; disponibilité de chaque média à vérifier.');
  add('contenus.draft','Préparer le scénario du projet','contenus','local','story','Brouillon lié au projet ; aucune publication externe.');
  add('contenus.publish','Publier sur les réseaux','contenus','unconnected','connections','Comptes, droits de publication et approbation éditoriale à raccorder.',false,{futureEndpoint:future('social','publish')});
  add('commerce.quote','Chiffrer le lot','commerce','local','quote','Coûts du lot, marge, commission et quantité à renseigner avant calcul.');
  add('commerce.inquiries','Demandes client & vitrine','commerce','local','inquiries','Importer l’export d’une demande, conserver ses paramètres techniques et préparer sa qualification ; contacts accessibles dans la demande source privée.');
  add('commerce.project','Ouvrir le dossier commercial','commerce','local','project-edit','Brief, quantité et notes du projet.');
  add('commerce.sell','Mettre une pièce en vente','commerce','unconnected','connections','Catalogue, paiement, conditions de vente et stock réel à raccorder.',false,{futureEndpoint:future('commerce','publish_listing')});
  add('ressources.machines','Renseigner les machines','ressources','local','fleet','Fiches des machines : identité, volume déclaré, profils et dossier d’essai ; connexion à réaliser.',state.machines.length>0);
  add('ressources.inventory','Gérer les stocks réels','ressources','unconnected','connections','Inventaire et suivi des consommations à mettre en place.',false,{futureEndpoint:future('inventory','manage_stock')});
  add('systeme.export_mission','Exporter la mission du projet','systeme','local','export-mission','Export descriptif JSON ; les binaires STL restent séparés.');
  add('systeme.continuity','Sauvegardes et reprise','systeme','local','continuity','Journal restaurable, rapprochement des opérations et conservation locale sur la tour.');
  add('contenus.studio','Studio de signature BOJ.ART','contenus','local','studio','Édit de référence, plans d’origine et langage visuel.');
  add('preparation.declared_volume','Préparer les pièces avec le parc déclaré','preparation','local','preparation','Relire les STL, comparer les enveloppes et exporter le rapport des machines renseignées.');
  add('systeme.decisions','Examiner les conseils de Jev','systeme','local','decisions','Priorités, orientations et intentions éditoriales à partir du dossier courant ; règles locales disponibles et Jev à configurer.');
  add('contenus.plans','Plans et versions du projet','contenus','local','project-studio','Scénario, sources déclarées et historique des édits de ce dossier.');
  add('systeme.export_workspace','Exporter tous les dossiers','systeme','local','export-state','Export de l’état du navigateur ; aucun binaire STL inclus.',true,{scope:'workspace'});
  add('systeme.journal','Lire le journal','systeme','local','journal','Historique local des dossiers et simulations.');
  add('systeme.screens','Installer les trois vues','systeme','local','screens','Fenêtres du même navigateur et de la même origine.');
  add('systeme.connections','Préparer les connexions','systeme','local','connections','Voir les interfaces à développer ; cette action ne connecte aucun équipement.');
  add('systeme.voice','Commander avec la voix locale','systeme','unconnected','connections','Reconnaissance vocale et moteur de commandes à installer sur le poste.',false,{futureEndpoint:future('voice','interpret_intent')});
  add('robotique.project','Créer un dossier de prototype','robotique','local','new-project','Créer le dossier et ses fichiers ; aucun comportement robotique n’est exécuté.',true,{projectKind:'robotique'});
  add('robotique.validate','Valider un prototype robotique','robotique','unconnected','connections','Modèle mécanique, électronique et protocole d’essai à définir.',false,{futureEndpoint:future('robotics','validate_prototype')});
  add('robotique.execute','Piloter un équipement robotique','robotique','unconnected','connections','Équipement identifié, contrôleur, limites et validation matérielle nécessaires.',false,{futureEndpoint:future('robotics','execute')});
  return operations;
}

/**
 * ready = a local action can be attempted, never proof that an output is approved.
 * This pure snapshot cannot check IndexedDB binaries, profiles or external services.
 */
export function buildMasterMission(state,projectId,{preparationReport=null,evidenceStatus='unchecked'}={}){
  const project=exactProject(state,projectId),e=projectEvidence(state,project),fleet=summarizeFleet(state.machines),steps=[];
  const baseline=inspectDeclaredPreparation(state,projectId);
  const acceptedReport=preparationReport?.format==='bojart.declared-preparation.v1'&&preparationReport.brand==='BOJ.ART'&&preparationReport.canSlice===false&&preparationReport.canStartPhysicalPrint===false&&preparationReportContext(preparationReport)===preparationReportContext(baseline);
  const report=acceptedReport?inspectDeclaredPreparation(state,projectId,{assetEvidence:preparationReport.pieces.filter(piece=>['measured','missing','invalid'].includes(piece.file?.status)).map(piece=>({...copy(piece.file||{}),projectId,pieceId:piece.id,pieceRevision:piece.revision,assetId:piece.assetId,unit:piece.unit,dimsMm:piece.dimensionsMm}))}):baseline;
  const summary=report.summary;
  const binariesVerified=e.pieces.length>0&&summary.measuredFiles===e.pieces.length;
  const editPlans=projectEditPlans(project).map(record=>{const version=latestEditVersion(record);return{id:record.id,revision:version.revision,operationId:version.operationId,projectRevision:version.projectRevision,title:version.plan.title,series:version.plan.series,status:version.plan.status,sourceCount:version.plan.sources.length,renderVerified:false};});
  function step(id,label,domain,dependencies,mode,status,operationIds,requirement,targetAction,extra={}){
    steps.push({id,label,domain,dependencies,status,mode,operationIds,requirement,targetAction,action:targetAction,projectId:project.id,...extra});
  }
  step('brief','Définir le projet','creation',[],'local',e.hasBrief?'ready':'needs_input',['creation.edit_brief'],'Renseigner l’intention, le lot et la hauteur demandée ; cela ne modifie aucun STL.','project-edit',{evidence:{briefPresent:e.hasBrief}});
  step('files','Retrouver et relire les fichiers','creation',['brief'],'local',binariesVerified?'ready':'needs_input',['creation.import_stl','preparation.declared_volume'],summary.measuredFiles+' STL relu(s), '+summary.missingFiles+' absent(s), '+summary.invalidFiles+' invalide(s), '+summary.unreferencedFiles+' pièce(s) sans STL.','preparation',{evidence:{referencedFiles:e.referencedFiles,measuredFiles:summary.measuredFiles,missingFiles:summary.missingFiles,invalidFiles:summary.invalidFiles,binariesVerified},actionLabel:'Ouvrir les fichiers du dossier'});
  step('inspect','Comparer les pièces au parc déclaré','creation',['files','resources'],'local',summary.measuredFiles?'ready':'needs_input',['preparation.declared_volume'],summary.piecesWithEnvelopeFit+' pièce(s) mesurée(s) possèdent au moins une orientation dans un volume déclaré. Supports, solidité et assemblage restent à préparer.','preparation',{evidence:{measuredFiles:summary.measuredFiles,declaredEnvelopeFits:summary.piecesWithEnvelopeFit,geometryQualified:false},actionLabel:'Inspecter les six orientations'});
  step('resources','Définir les ressources','ressources',['brief'],'local',fleet.complete?'ready':'needs_input',['ressources.machines'],'Renseigner les fiches des machines et matières ; la qualification physique et le raccordement restent à vérifier.','fleet',{evidence:{slots:fleet.slots,declaredMachines:fleet.declared,completeRecords:fleet.complete,qualificationVerified:false}});
  step('simulation','Simuler la répartition','preparation',['brief','resources'],'simulation',e.pieces.length&&e.compatiblePieces?'ready':'needs_input',['preparation.assign_jobs'],'Simulation à partir des métadonnées ; ne dépend pas d’un fichier slicé et ne fabrique rien.','plan',{evidence:{compatibleEnvelopes:e.compatiblePieces,totalPieces:e.pieces.length,simulatedAssignments:e.assignments,differentLots:e.differentLots}});
  step('prepare','Préparer les pièces et supports','preparation',['inspect','resources'],'unconnected','not_connected',[],'Orientation, supports, drainage, assemblage et profils à préparer dans les outils adaptés.','connections',{futureEndpoint:future('preparation','prepare_geometry')});
  step('slice','Produire et examiner les couches','preparation',['prepare'],'unconnected','not_connected',['preparation.slice'],'Exécuter un slicer identifié avec des profils validés et conserver le fichier généré.','connections',{futureEndpoint:future('slicer','slice')});
  step('approve','Valider le dossier de fabrication','preparation',['slice'],'unconnected','not_connected',[],'Contrôler le fichier machine, la révision, la matière, le plateau et la disponibilité physique.','connections',{futureEndpoint:future('build_review','approve_build')});
  step('fabricate','Lancer et suivre la fabrication','production',['approve'],'unconnected','not_connected',['production.start_physical'],'Envoi explicite, accusé de la bonne machine et retour d’état réel requis.','connections',{futureEndpoint:future('printer_gateway','start_job')});
  step('finish','Finir, assembler et contrôler','production',['fabricate'],'unconnected','not_connected',[],'Retrait, lavage/séchage/polymérisation selon procédé, assemblage et contrôle physique restent à organiser.','connections',{futureEndpoint:future('workshop_tasks','record_finishing')});
  step('story','Préparer et conserver les édits','contenus',['brief'],'local',e.hasBrief?'ready':'needs_input',['contenus.plans','contenus.archive'],editPlans.length+' plan(s) de montage conservé(s) avec version, sources et timecodes. Le film exact reste à rendre et examiner.','project-studio',{evidence:{draftPresent:typeof project.story==='string'&&!!project.story.trim(),savedPlans:editPlans,renderVerified:false},actionLabel:'Ouvrir les plans et leurs versions'});
  step('publish','Publier le contenu','contenus',['story'],'unconnected','not_connected',['contenus.publish'],'Validation éditoriale et compte autorisé requis ; aucune publication par ce module.','connections',{futureEndpoint:future('social','publish')});
  step('quote','Préparer le devis','commerce',['brief'],'local',e.hasBrief?'ready':'needs_input',['commerce.quote'],'Renseigner les coûts réels du lot avant tout calcul ; fiscalité à préciser.','quote',{evidence:{savedQuotePresent:!!project.quote}});
  step('sale','Proposer la vente','commerce',['quote'],'unconnected','not_connected',['commerce.sell'],'Offre, disponibilité, délais, conditions et paiement à raccorder avant vente.','connections',{futureEndpoint:future('commerce','publish_listing')});
  step('robotics','Préparer les essais du prototype','robotique',['inspect','resources'],'unconnected','not_connected',['robotique.validate'],'Branche optionnelle : exigences, électronique, essais et limites spécifiques au prototype.','connections',{optional:true,futureEndpoint:future('robotics','validate_prototype')});
  return {format:'bojart.master-mission.v2',brand:'BOJ.ART',projectId:project.id,projectName:project.name,
    project:{id:project.id,name:project.name,revision:project.revision??1},
    projectRevision:project.revision??1,scope:{kind:'project',projectId:project.id,revision:project.revision??1},
    quantity:project.quantity,targetHeightMm:project.height,steps,
    edges:steps.flatMap(s=>s.dependencies.map(from=>({from,to:s.id}))),
    pieces:report.pieces.map(piece=>({...copy(piece),simulation:e.pieces.find(item=>item.id===piece.id)})),
    preparation:{report:copy(report),evidenceStatus:acceptedReport?evidenceStatus:'unchecked'},
    editPlans,
    jobs:copy(state.jobs.filter(j=>j.projectId===project.id)),
    readiness:{readyMeaning:'local_action_available_not_completed',referencedFiles:e.referencedFiles,binariesVerified,
      measuredFiles:summary.measuredFiles,declaredMachines:summary.declaredMachines,compatibleEnvelopes:summary.piecesWithEnvelopeFit,
      simulatedCompatibleEnvelopes:e.compatiblePieces,simulatedAssignments:e.assignments,canSlice:false,canStartPhysicalPrint:false,canPublish:false,canExecuteRobot:false},
    limitations:['La mission décrit des actions et leurs dépendances ; elle ne les exécute pas.',
      'Les preuves de fichier indiquent une relecture sur ce poste et cette révision ; elles ne certifient pas la fabrication.',
      'Les compatibilités du dossier utilisent uniquement les STL mesurés et les volumes déclarés. La simulation reste séparée.',
      'Les travaux de simulation conservent leur projet, révision et quantité d’origine.',
      'Les capacités futures sont des noms de contrats à développer, pas des services connectés.',
      'L’export JSON ne contient aucun binaire STL, secret, commande machine ni publication.']};
}

/** The central next step has exactly the same evidence as the exported mission. */
export function buildControlDecision(state,projectId,options={}){
  const mission=buildMasterMission(state,projectId,options),report=mission.preparation.report,s=report.summary;
  const project=exactProject(state,projectId),pieces=report.pieces;
  const facts=[
    {label:'STL relus',value:s.measuredFiles+' / '+s.totalPieces,detail:'Mesures de cette révision',state:s.measuredFiles===s.totalPieces&&s.totalPieces?'ready':'pending'},
    {label:'Machines déclarées',value:s.declaredMachines+' / '+s.totalMachines,detail:'Fiches du parc réel',state:s.declaredMachines?'ready':'pending'},
    {label:'Plans de montage',value:String(mission.editPlans.length),detail:'Versions conservées',state:mission.editPlans.length?'ready':'pending'}
  ];
  const decision={state:'needs_input',modeLabel:'DOSSIER RÉEL · PRÉPARATION',title:'Examiner la préparation.',reason:'Les fichiers, le parc et les contenus partagent le même dossier.',targetLabel:project.name,evidenceLabel:'Aucune fabrication lancée',facts,
    primary:{label:'Ouvrir l’établi',action:'preparation'},secondary:[{label:'Conseils & Jev',action:'decisions'},{label:'Mission complète',action:'master-mission'}]};
  if(mission.preparation.evidenceStatus==='checking')return{...decision,state:'checking',title:'Je relis les STL du dossier.',reason:'Les dimensions et les empreintes sont calculées à partir des fichiers accessibles sur ce poste.',evidenceLabel:s.measuredFiles+' fichier(s) mesuré(s)'};
  if(project.inquiry&&!pieces.length)return{...decision,title:'Qualifier cette demande.',reason:'Les paramètres reçus et les informations à préciser sont reliés au dossier. Définissez l’étude et récupérez les fichiers avant la préparation.',evidenceLabel:project.inquiry.reference,primary:{label:'Examiner la demande',action:'inquiry-current'}};
  if(!pieces.length)return{...decision,title:'Rassembler la première pièce.',reason:'Le brief est créé. Importez un STL pour ouvrir la préparation dimensionnelle.',primary:{label:'Importer un STL',action:'import'}};
  const missing=pieces.find(piece=>['missing','invalid','unreferenced'].includes(piece.file.status));
  if(missing){const invalid=missing.file.status==='invalid',unreferenced=missing.file.status==='unreferenced';return{...decision,title:invalid?'Revoir ce fichier.':unreferenced?'Associer le STL de cette pièce.':'Retrouver le fichier original.',targetLabel:missing.name,reason:invalid?missing.file.message:unreferenced?'Cette pièce possède une fiche, mais aucun fichier associé. Son volume ne peut pas encore être vérifié.':'Le dossier référence ce STL, mais son binaire n’est pas accessible sur ce poste. Le coffre local peut permettre de le retrouver.',evidenceLabel:'Pièce '+missing.id+' · révision '+missing.revision,primary:{label:invalid?'Examiner la pièce':'Ouvrir la pièce',action:'preparation',pieceId:missing.id}};}
  if(s.uncheckedFiles)return{...decision,title:'Relire les fichiers associés.',reason:'Une référence de STL ne remplace pas la lecture de son binaire. La vérification est à effectuer sur ce poste.',primary:{label:'Relire les STL',action:'audit-project'}};
  if(!s.declaredMachines)return{...decision,title:'Déclarer le parc réel.',reason:'Les STL sont mesurés. Les emplacements de démonstration n’apportent aucune preuve sur les volumes de vos imprimantes.',primary:{label:'Renseigner les machines',action:'fleet'},evidenceLabel:s.measuredFiles+' STL relu(s)'};
  const noFit=pieces.find(piece=>piece.file.status==='measured'&&!piece.assessments.some(item=>item.technologyStatus==='match'&&item.fitOrientationIds.length));
  if(noFit)return{...decision,title:'Examiner son encombrement.',targetLabel:noFit.name,reason:'Aucune des six orientations testées ne tient actuellement dans un volume déclaré du bon procédé. Une autre préparation ou une autre ressource doit être examinée.',primary:{label:'Comparer la pièce au parc',action:'preparation',pieceId:noFit.id},evidenceLabel:'Comparaison du STL et des fiches déclarées'};
  return{...decision,state:'ready',title:'Préparer le procédé et l’assemblage.',reason:'Les enveloppes brutes trouvent une place dans le parc déclaré. La prochaine preuve à produire porte sur l’orientation finale, les supports, la matière et le fichier slicé.',evidenceLabel:s.piecesWithEnvelopeFit+' pièce(s) dans un volume brut déclaré'};
}

export function answerMissionQuestion(raw,mission){
  const text=String(raw||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  if(!/^(?:jarvis[, :]*|jev[, :]*)?(?:pourquoi|comment|quel(?:le)?s?|ou\b|est-ce|peux-tu expliquer|explique|que reste|qu.est-ce qui)/.test(text)&&!text.trim().endsWith('?'))return null;
  const s=mission.preparation.report.summary;
  if(/jev/.test(text))return'Jev peut conseiller une priorité, une orientation admissible ou une intention éditoriale à partir des preuves du dossier. Le bureau « Conseils & Jev » indique si son service répond. Ces conseils n’envoient aucune commande machine.';
  if(/fichier|stl|mesur/.test(text))return s.measuredFiles+' STL relu(s) sur '+s.totalPieces+' pièce(s) : '+s.unreferencedFiles+' sans fichier, '+s.missingFiles+' absent(s), '+s.invalidFiles+' invalide(s), '+s.uncheckedFiles+' à relire. L’établi montre les mesures, unités et empreintes.';
  if(/contenu|edit|montage|video/.test(text))return mission.editPlans.length+' plan(s) de montage sont conservés avec leurs versions et leurs sources. Leur présence ne signifie pas qu’un film final a été rendu.';
  if(/imprim|slic|fabric|bloqu|pret|prepare/.test(text))return s.piecesWithEnvelopeFit+' pièce(s) mesurée(s) trouvent une enveloppe brute dans le parc déclaré. Le slicing et les imprimantes ne sont pas raccordés. Il faut ensuite préparer le procédé, examiner le fichier machine et obtenir l’état de la ressource cible.';
  return mission.projectName+' : '+s.measuredFiles+' STL relu(s), '+s.declaredMachines+' machine(s) déclarée(s), '+mission.editPlans.length+' plan(s) de montage conservé(s). La mission complète expose les prochaines étapes et leurs dépendances.';
}
