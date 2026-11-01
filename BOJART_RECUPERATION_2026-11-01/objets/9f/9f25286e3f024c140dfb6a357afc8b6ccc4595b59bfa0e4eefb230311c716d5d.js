'use strict';
const $=id=>document.getElementById(id);const role=new URLSearchParams(location.search).get('role');const roles={atelier:'ATELIER / GAUCHE',pilotage:'JARVIS / CENTRE',creation:'CRÉATION / DROITE'};let screenId=null,busy=false;
const projectId=new URLSearchParams(location.search).get('project_id')||'BOJ-PILOTE-001';
for(const a of document.querySelectorAll('a[href="/tower"]'))a.href='/tower?project_id='+encodeURIComponent(projectId);
async function api(path,data){const r=await fetch(path,data===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),cache:'no-store'});const x=await r.json();if(!r.ok)throw Error(x.error||'Erreur du serveur local');return x;}
function say(t){$('receipt').textContent=t;}
function showText(t){$('canvas').classList.remove('active');$('visualBody').hidden=false;$('visualBody').textContent=t;}
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
   showText('Studio sources BOJ.ART · '+(data.segments?.length??data.total_segments??'catalogue')+' passages répertoriés. Ouvrir /studio pour la sélection complète.');
   $('visualLabel').textContent='BIBLIOTHÈQUE LOCALE';
 }else if(cmd.action==='show_planning_demo'){
   showText('PLANNING DÉMONSTRATIF — machines et temps fictifs. Aucune disponibilité d’imprimante réelle connue.');
   $('visualLabel').textContent='PLANNING / SIMULATION';
 }else if(cmd.action==='interrupt_speech'){
   showText('Interruption vocale demandée. Aucun moteur de synthèse vocale n’est connecté dans cette régie.');
   $('visualLabel').textContent='VOIX / NON RACCORDÉE';
 }else throw Error('Action inconnue.');
 await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
}
async function tick(){if(busy||!screenId)return;busy=true;try{const p=await api('/api/tower/poll',{screen_id:screenId});$('connection').textContent='VUE LOCALE CONNECTÉE';if(p.command){let outcome='rendered',message='Vue traitée par le navigateur.';try{await render(p.command);}catch(e){outcome='failed';message=String(e.message).slice(0,180);showText('Affichage refusé : '+message);}const a=await api('/api/tower/ack',{screen_id:screenId,request_id:p.command.request_id,outcome,message});say(a.state+' · '+message+' (accusé logiciel, non matériel)');}}
 catch(e){$('connection').textContent='CONNEXION À VÉRIFIER';say(e.message);}finally{busy=false;}}
(async()=>{if(!Object.hasOwn(roles,role)){say('Rôle invalide.');return;}$('screenRole').textContent=roles[role];const key='bojart_m05_screen_'+projectId+'_'+role;screenId=sessionStorage.getItem(key);try{if(screenId){try{await api('/api/tower/poll',{screen_id:screenId});}catch(e){screenId=null;sessionStorage.removeItem(key);}}
 if(!screenId){const p=await api('/api/tower/pair',{role,label:'Vue '+roles[role],project_id:projectId});screenId=p.screen_id;sessionStorage.setItem(key,screenId);}say('Vue appairée. En attente des commandes de la régie.');$('connection').textContent='VUE LOCALE CONNECTÉE';await tick();setInterval(tick,1200);}catch(e){sessionStorage.removeItem(key);say('Appairage impossible : '+e.message);}})();
