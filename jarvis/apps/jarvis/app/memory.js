"use strict";
const $=id=>document.getElementById(id);
let generation=0,refreshGeneration=0;
const labels={observed:"observé",source_reported:"rapporté",proposal:"proposition",user_decision:"décision"};
let session=localStorage.getItem("boj-memory-session");
if(!session){session=crypto.randomUUID();localStorage.setItem("boj-memory-session",session)}
async function api(path,body){const opts=body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)};const r=await fetch(path,opts);const v=await r.json();if(!r.ok)throw new Error(v.error||"Erreur locale");return v}
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
async function task(id,fn){const run=++generation,domain=$("domain").value;const active=()=>run===generation&&domain===$("domain").value;$(id).disabled=true;$("notice").textContent="En cours…";try{await fn(active);if(active())$("notice").textContent="Terminé."}catch(e){if(active())$("notice").textContent=e.message}finally{$(id).disabled=false}}
async function refresh(){
  const refreshRun=++refreshGeneration;
  const project=$("domain").value;
  const [s,fs]=await Promise.all([api("/api/memory/status"),api("/api/memory/facts?project="+project)]);
  if(refreshRun!==refreshGeneration||project!==$("domain").value)return;
  $("docs").textContent=s.sources;$("episodes").textContent=s.agent_episodes;
  $("integrity").textContent=s.database_integrity==="ok"?"Vérifiée":"À contrôler";
  $("model-state").textContent=s.chat_configured?"Conversation locale configurée. Les réponses générées restent à vérifier.":"Recherche disponible. Conversation IA à activer avec un modèle Ollama local.";
  $("fact-list").replaceChildren();$("facts").textContent=fs.facts.length;
  for(const f of fs.facts){const d=el("details",undefined,"fact");d.append(el("summary",f.key+" · "+(labels[f.status]||f.status)+(f.conflict?" · CONFLIT":"")),el("p",typeof f.value==="string"?f.value:JSON.stringify(f.value)),el("small",f.observed_at+" — "+f.source));$("fact-list").append(d)}
}
function query(){const q=$("question").value.trim();if(!q)throw new Error("Écris une question pour commencer.");return "?project="+$("domain").value+"&q="+encodeURIComponent(q)}
$("search").onclick=()=>task("search",async active=>{const r=await api("/api/memory/recall"+query());if(!active())return;$("results").replaceChildren(el("h2",r.results.length+" passages retrouvés"));if(!r.results.length)$("results").append(el("p","Aucune source pertinente retrouvée. Ne pas inventer une réponse."));for(const h of r.results){const e=el("article",undefined,"hit");e.append(el("small",h.source_path+" — lignes "+h.start_line+"–"+h.end_line),el("p",h.text),el("small",h.citation));$("results").append(e)}$("results").append(el("p","Recherche sémantique : "+r.semantic_status,"hint"))});
$("context").onclick=()=>task("context",async active=>{const r=await api("/api/memory/context"+query());if(!active())return;const copy=el("button","Copier le contexte","secondary");copy.onclick=async()=>{try{await navigator.clipboard.writeText(r.text);copy.textContent="Copié"}catch{$("notice").textContent="Sélectionne le texte du contexte pour le copier."}};const download=el("button","Télécharger la reprise","secondary");download.onclick=()=>{
const url=URL.createObjectURL(new Blob([JSON.stringify(r)+"\n"],{type:"application/json;charset=utf-8"}));
const link=el("a");link.href=url;link.download="BOJART_REPRISE_"+r.project.replaceAll(".","_")+"_"+r.sha256.slice(0,12)+".json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$("results").replaceChildren(el("h2","Contexte prêt à transmettre"),el("p",r.characters+" caractères · "+r.citations.length+" références · "+r.omitted+" éléments hors budget","hint"),copy,download,el("p","La reprise contient les informations du domaine choisi. Vérifie son contenu avant de la partager.","hint"),el("pre",r.text))});
$("ask").onclick=()=>task("ask",async active=>{query();const r=await api("/api/memory/ask",{text:$("question").value.trim(),project:$("domain").value,session,request_id:crypto.randomUUID()});if(!active())return;$("results").replaceChildren(el("h2","Jarvis"),el("p",r.answer,"answer"),el("p","Réponse générée localement, à vérifier. Contexte : "+r.context_sha256,"hint"));if(r.citation_warnings?.length)$("results").append(el("p","Références non reconnues dans cette réponse : "+r.citation_warnings.join(", "),"hint"));await refresh()});
$("remember").onclick=()=>task("remember",async active=>{await api("/api/memory/note",{key:$("note-key").value.trim(),value:$("note-value").value.trim(),source:$("note-source").value.trim(),project:$("domain").value});if(!active())return;$("note-value").value="";await refresh()});
$("reindex").onclick=()=>task("reindex",async active=>{const r=await api("/api/memory/reindex",{});if(!active())return;await refresh();if(!active())return;$("results").replaceChildren(el("h2","Sources actualisées"),el("p",r.indexed_paths+" chemins indexés, "+r.new_versions+" nouvelles versions."))});
$("backup").onclick=()=>task("backup",async active=>{const r=await api("/api/memory/backup",{});if(!active())return;$("results").replaceChildren(el("h2","Sauvegarde mémoire créée"),el("p",r.path,"answer"),el("p","Les dossiers CAO et médias se sauvegardent depuis Dossiers dans Jarvis.","hint"))});
function invalidate(){generation++;$("results").replaceChildren();$("notice").textContent="Contexte modifié. Relance la recherche pour ce domaine et ce sujet."}
$("question").oninput=invalidate;
$("domain").onchange=()=>{invalidate();$("fact-list").replaceChildren();$("facts").textContent="—";const expected=refreshGeneration+1;return refresh().catch(e=>{if(expected===refreshGeneration)$("notice").textContent=e.message})};
refresh().catch(e=>$("notice").textContent=e.message);
