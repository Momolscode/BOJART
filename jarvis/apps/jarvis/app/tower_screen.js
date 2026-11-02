'use strict';
const $=id=>document.getElementById(id);const role=new URLSearchParams(location.search).get('role');const roles={atelier:'ATELIER / GAUCHE',pilotage:'JARVIS / CENTRE',creation:'CRÉATION / DROITE'};let screenId=null,busy=false;
const projectId=new URLSearchParams(location.search).get('project_id')||'BOJ-PILOTE-001';
for(const a of document.querySelectorAll('a[href="/tower"]'))a.href='/tower?project_id='+encodeURIComponent(projectId);
async function api(path,data){const r=await fetch(path,data===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),cache:'no-store'});const x=await r.json();if(!r.ok)throw Error(x.error||'Erreur du serveur local');return x;}
function say(t){$('receipt').textContent=t;}
function showText(t){$('canvas').classList.remove('active');$('visualBody').hidden=false;$('visualBody').textContent=t;}
function card(title,text,href,label='Ouvrir'){
 const c=document.createElement('article');c.className='viewCard';const h=document.createElement('h3');h.textContent=title;c.append(h);
 const p=document.createElement('p');p.textContent=text;c.append(p);
 if(href){const a=document.createElement('a');a.href=href;a.textContent=label;c.append(a);}$('visualBody').append(c);
}
async function render(cmd){if(cmd.project_id!==projectId)throw Error('Dossier de la commande incompatible avec cette vue.');$('screenTitle').textContent='Commande reçue';$('screenInfo').textContent='Projet '+cmd.project_id+' · Révision '+cmd.revision+' · Action '+cmd.action;
 if(cmd.action==='show_model'){
   if(!cmd.asset)throw Error('Fichier 3D absent.');
   const response=await fetch(cmd.asset.path,{cache:'no-store'});if(!response.ok)throw Error('Fichier GLB inaccessible.');
   const bytes=await response.arrayBuffer();const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');
   if(digest!==cmd.asset.sha256)throw Error('Empreinte du GLB différente : affichage refusé.');
   const mesh=await api('/artifacts/'+encodeURIComponent(cmd.asset.operation_id)+'/modele.json');
   if(!mesh||!Array.isArray(mesh.positions)||!Array.isArray(mesh.normals)||!mesh.positions.length)throw Error('Maillage absent ou illisible.');
   $('visualBody').hidden=true;$('canvas').classList.add('active');window.BojViewer.setModel(mesh);
   if(!Number($('canvas').dataset.renderedTriangles||0))throw Error('Aucun triangle affiché.');
   $('visualLabel').textContent='MODÈLE 3D / SOURCE VÉRIFIÉE';
 }else if(cmd.action==='show_sources'){
   const data=await api('/api/studio/catalogue');
   showText('');card('Studio sources BOJ.ART',(data.segments?.length??data.total_segments??'Catalogue')+' passages répertoriés. Catalogue partagé entre les dossiers.','/studio','Choisir les sources et préparer un brief');
   for(const s of (data.segments||[]).slice(0,5))card(s.title||s.label||s.id, s.description||s.kind||s.media_kind||'Passage du catalogue local');
   $('visualLabel').textContent='BIBLIOTHÈQUE LOCALE';
 }else if(cmd.action==='show_planning_demo'){
   showText('PLANNING DÉMONSTRATIF — machines et temps fictifs. Aucune disponibilité d’imprimante réelle connue.');
   $('visualLabel').textContent='PLANNING / SIMULATION';
 }else if(cmd.action==='interrupt_speech'){
   window.speechSynthesis?.cancel();
   showText('Réponse vocale interrompue dans cette vue. Aucun ordre d’arrêt machine envoyé.');
   $('visualLabel').textContent='RÉPONSE / INTERROMPUE';
 }else if(cmd.action==='show_workspace'){
   const data=await api('/api/workspace/state');showText('');
   card('Dossiers et continuité',data.projects.length+' dossiers · '+data.media+' médias · '+data.studio_briefs+' briefs · '+data.growth_drafts+' brouillons.','/workspace','Gérer les dossiers et sauvegardes');
   for(const p of data.projects.slice(0,6))card(p.name||p.id,'Révision '+(p.revision??0), '/?project_id='+encodeURIComponent(p.id),'Ouvrir le dossier');
   $('visualLabel').textContent='ÉTAT LOCAL / DOSSIERS';
 }else if(cmd.action==='show_growth'){
   const data=await api('/api/growth/state'),workspace=await api('/api/workspace/state');showText('');
   card('Contenus BOJ.ART',workspace.growth_drafts+' préparations conservées. '+data.notice,'/growth','Préparer un contenu');
   card('Publication','Comptes externes non connectés. Aucun contenu envoyé.');
   $('visualLabel').textContent='CONTENUS / PRÉPARATION';
 }else if(cmd.action==='show_knowledge'){
   const data=await api('/api/knowledge/search?q=resine');showText('');
   card('Base métier','Recherche locale disponible. Exemple résine : '+data.total_returned+' fiches. Les sources documentaires ne commandent pas les machines.','/knowledge','Rechercher dans la base métier');
   $('visualLabel').textContent='CONNAISSANCES / SOURCES';
 }else if(cmd.action==='show_cad'){
   const data=await api('/api/state?project_id='+encodeURIComponent(projectId));showText('');
   card('Conception du dossier',projectId+' · Révision '+data.revision+' · '+data.jobs.filter(j=>j.state==='READY').length+' calculs conservés.','/?project_id='+encodeURIComponent(projectId),'Ouvrir le poste de conception');
   card('Créer une pièce','La création exige une proposition paramétrique relue et confirmée. Aucun calcul lancé par cet affichage.');
   $('visualLabel').textContent='CONCEPTION / DOSSIER';
 }else throw Error('Action inconnue.');
 await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
}
let tickAgain=false;
async function tick(){if(busy){tickAgain=true;return;}if(!screenId)return;busy=true;try{const p=await api('/api/tower/poll',{screen_id:screenId});$('connection').textContent='VUE LOCALE CONNECTÉE';if(p.command){let outcome='rendered',message='Vue traitée par le navigateur.';try{await render(p.command);}catch(e){outcome='failed';message=String(e.message).slice(0,180);showText('Affichage refusé : '+message);}const a=await api('/api/tower/ack',{screen_id:screenId,request_id:p.command.request_id,outcome,message});say(a.state+' · '+message+' (accusé logiciel, non matériel)');tickAgain=true;}}
 catch(e){$('connection').textContent='CONNEXION À VÉRIFIER';say(e.message);}finally{busy=false;if(tickAgain){tickAgain=false;setTimeout(tick,50);}}}
(async()=>{if(!Object.hasOwn(roles,role)){say('Rôle invalide.');return;}$('screenRole').textContent=roles[role];const key='bojart_m05_screen_'+projectId+'_'+role;screenId=sessionStorage.getItem(key);try{if(screenId){try{await api('/api/tower/poll',{screen_id:screenId});}catch(e){screenId=null;sessionStorage.removeItem(key);}}
 if(!screenId){const p=await api('/api/tower/pair',{role,label:'Vue '+roles[role],project_id:projectId});screenId=p.screen_id;sessionStorage.setItem(key,screenId);}say('Vue appairée. En attente des commandes de la régie.');$('connection').textContent='VUE LOCALE CONNECTÉE';await tick();const events=new EventSource('/api/tower/events');events.onmessage=()=>tick();window.addEventListener('pagehide',()=>events.close());setInterval(tick,5000);}catch(e){sessionStorage.removeItem(key);say('Appairage impossible : '+e.message);}})();
