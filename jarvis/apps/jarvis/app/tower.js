'use strict';
const $=id=>document.getElementById(id);let readiness=null,loading=false;
const projectId=new URLSearchParams(location.search).get('project_id')||'BOJ-PILOTE-001';
const query='?project_id='+encodeURIComponent(projectId);
const pendingKey='boj_m05_display_'+projectId;
for(const a of document.querySelectorAll('a[href="/"]'))a.href='/'+query;
$('send').textContent=sessionStorage.getItem(pendingKey)?'Reprendre la tentative conservée':'Préparer puis envoyer à la vue';
async function api(url,data){const r=await fetch(url,data===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),cache:'no-store'});const x=await r.json();if(!r.ok){const e=Error(x.error||'Erreur du serveur local');e.http=r.status;throw e;}return x;}
function node(tag,text,cls){const el=document.createElement(tag);el.textContent=text;if(cls)el.className=cls;return el;}
function feedback(text,bad=false){$('feedback').textContent=text;$('feedback').className='feedback '+(bad?'bad':'good');}
async function refresh(){if(loading)return;loading=true;try{
 const [s,r,project]=await Promise.all([api('/api/tower/state'+query),api('/api/launch/readiness'),api('/api/state'+query)]);readiness=r;
 $('launchState').textContent=r.production_ready?'QUALIFIÉ':'NON QUALIFIÉ';$('launchReason').textContent=r.production_ready?'Recette complète':r.why_not_ready;
 $('projectLabel').textContent=(project.projects.find(p=>p.id===projectId)?.name||projectId)+' · Révision '+project.revision;
 $('viewsCount').textContent=s.browser_views_connected;$('ackedCount').textContent=s.commands.filter(c=>c.state==='rendered').length;
 $('gateCount').textContent=r.gates.length+' GATES';const gates=$('gates');gates.replaceChildren();for(const g of r.gates){const row=node('div','', 'gate '+g.state);row.append(node('span','','dot'));const body=node('div','');body.append(node('b',g.label),node('small',g.evidence));row.append(body);gates.append(row);}
 const roles=$('roles');roles.replaceChildren();for(const [role,label,desc] of [['atelier','GAUCHE / ATELIER','Planning & machines'],['pilotage','CENTRE / JARVIS','Dialogue & missions'],['creation','DROITE / CRÉATION','Modèle & médias']]){const row=node('div','', 'role');const body=node('div','');body.append(node('b',label),node('small',desc+' · '+(s.roles[role]||0)+' vue(s)'));const b=node('button','Ouvrir la vue');b.onclick=()=>window.open('/tower/screen?role='+encodeURIComponent(role)+'&project_id='+encodeURIComponent(projectId),'_blank');row.append(body,b);roles.append(row);}
 const journal=$('journal');journal.replaceChildren();if(!s.commands.length)journal.textContent='Aucune commande.';else for(const c of s.commands){const row=node('div','', 'entry');row.append(node('span',c.target_role+' · '+c.request_id.slice(0,12)),node('b',c.state));journal.append(row);}
 const op=$('operation'),prev=op.value;op.replaceChildren();op.append(new Option('Aucun modèle conservé',''));for(const j of project.jobs||[]){if(j.state==='READY')op.append(new Option('Modèle '+(j.id||j.operation_id).slice(0,12),j.id||j.operation_id));}if([...op.options].some(x=>x.value===prev))op.value=prev;
 }catch(e){feedback('Diagnostic indisponible : '+e.message,true);}finally{loading=false;}}
$('send').onclick=async()=>{const btn=$('send');btn.disabled=true;try{
 let request=JSON.parse(sessionStorage.getItem(pendingKey)||'null');
 if(!request){const project=await api('/api/state'+query);const command=$('command').value;const operation=command==='Affiche le modèle à droite'?$('operation').value:null;
  if(command==='Affiche le modèle à droite'&&!operation)throw Error('Crée ou sélectionne d’abord un modèle dans ce dossier.');
  request={request_id:'m05_'+crypto.randomUUID().replaceAll('-',''),project_id:projectId,revision:project.revision,turn_id:'ui_'+crypto.randomUUID().replaceAll('-',''),command,operation_id:operation};
  sessionStorage.setItem(pendingKey,JSON.stringify(request));}
 const p=await api('/api/control/prepare',request);const d=await api('/api/tower/dispatch',{request_id:p.request_id});
 sessionStorage.removeItem(pendingKey);feedback('Dossier '+projectId+' → '+d.state+' vers '+d.target_role+'. Référence '+p.request_id.slice(-8));await refresh();
 }catch(e){if(e.http&&e.http>=400&&e.http<500&&![408,429].includes(e.http))sessionStorage.removeItem(pendingKey);feedback(e.message+(sessionStorage.getItem(pendingKey)?' — Tentative conservée. Le bouton reprendra la même référence.':''),true);}finally{btn.disabled=false;btn.textContent=sessionStorage.getItem(pendingKey)?'Reprendre la tentative conservée':'Préparer puis envoyer à la vue';}};
$('export').onclick=()=>{if(!readiness)return;const blob=new Blob([JSON.stringify(readiness,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='BOJART_M05_RECETTE_LANCEMENT.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
refresh();setInterval(refresh,3000);
