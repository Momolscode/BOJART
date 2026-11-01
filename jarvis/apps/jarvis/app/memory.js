"use strict";
const $=id=>document.getElementById(id);
let renderGeneration=0, factsGeneration=0;
const labels={observed:"observé",source_reported:"rapporté",proposal:"proposition",user_decision:"décision"};
let session=localStorage.getItem("boj-memory-session");
if(!session){session=crypto.randomUUID();localStorage.setItem("boj-memory-session",session)}
async function api(path,body){const opts=body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)};const r=await fetch(path,opts);const v=await r.json();if(!r.ok)throw new Error(v.error||"Erreur locale");return v}
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
async function task(id,fn){
  const generation=++renderGeneration, domain=$("domain").value;
  const current=()=>generation===renderGeneration && domain===$("domain").value;
  $(id).disabled=true;$("notice").textContent="En cours…";
  try{await fn(current);if(current())$("notice").textContent="Terminé."}
  catch(e){if(current())$("notice").textContent=e.message}
  finally{$(id).disabled=false}
}
async function refresh(){
  const generation=++factsGeneration, domain=$("domain").value;
  const current=()=>generation===factsGeneration && domain===$("domain").value;
  try{
    const s=await api("/api/memory/status");if(!current())return;
    $("docs").textContent=s.sources;$("episodes").textContent=s.agent_episodes;$("integrity").textContent=s.database_integrity==="ok"?"Vérifiée":"À contrôler";
    $("model-state").textContent=s.chat_configured?"Conversation locale configurée. Les réponses générées restent à vérifier.":"Recherche disponible. Conversation IA à activer avec un modèle Ollama local.";
    const fs=await api("/api/memory/facts?project="+domain);if(!current())return;
    $("fact-list").replaceChildren();$("facts").textContent=fs.facts.length;
    for(const f of fs.facts){const d=el("details",undefined,"fact");d.append(el("summary",f.key+" · "+(labels[f.status]||f.status)+(f.conflict?" · CONFLIT":"")),el("p",typeof f.value==="string"?f.value:JSON.stringify(f.value)),el("small",f.observed_at+" — "+f.source));$("fact-list").append(d)}
  }catch(e){if(current())throw e}
}
function query(){const q=$("question").value.trim();if(!q)throw new Error("Écris une question pour commencer.");return "?project="+$("domain").value+"&q="+encodeURIComponent(q)}
$("search").onclick=()=>task("search",async(current)=>{const r=await api("/api/memory/recall"+query());if(!current())return;$("results").replaceChildren(el("h2",r.results.length+" passages retrouvés"));if(!r.results.length)$("results").append(el("p","Aucune source pertinente retrouvée. Ne pas inventer une réponse."));for(const h of r.results){const e=el("article",undefined,"hit");e.append(el("small",h.source_path+" — lignes "+h.start_line+"–"+h.end_line),el("p",h.text),el("small",h.citation));$("results").append(e)}$("results").append(el("p","Recherche sémantique : "+r.semantic_status,"hint"))});
$("context").onclick=()=>task("context",async(current)=>{const r=await api("/api/memory/context"+query());if(!current())return;const copy=el("button","Copier le contexte","secondary");copy.onclick=async()=>{try{await navigator.clipboard.writeText(r.text);copy.textContent="Copié"}catch{$("notice").textContent="Sélectionne le texte du contexte pour le copier."}};$("results").replaceChildren(el("h2","Contexte prêt à transmettre"),el("p",r.characters+" caractères · "+r.citations.length+" références · "+r.omitted+" éléments hors budget","hint"),copy,el("pre",r.text))});
$("ask").onclick=()=>task("ask",async(current)=>{query();const r=await api("/api/memory/ask",{text:$("question").value.trim(),project:$("domain").value,session,request_id:crypto.randomUUID()});if(!current())return;$("results").replaceChildren(el("h2","Jarvis"),el("p",r.answer,"answer"),el("p","Réponse générée localement, à vérifier. Contexte : "+r.context_sha256,"hint"));if(r.citation_warnings?.length)$("results").append(el("p","Références non reconnues dans cette réponse : "+r.citation_warnings.join(", "),"hint"));await refresh()});
$("remember").onclick=()=>task("remember",async(current)=>{await api("/api/memory/note",{key:$("note-key").value.trim(),value:$("note-value").value.trim(),source:$("note-source").value.trim(),project:$("domain").value});if(!current())return;$("note-value").value="";await refresh()});
$("reindex").onclick=()=>task("reindex",async(current)=>{const r=await api("/api/memory/reindex",{});if(!current())return;await refresh();if(!current())return;$("results").replaceChildren(el("h2","Sources actualisées"),el("p",r.indexed_paths+" chemins indexés, "+r.new_versions+" nouvelles versions."))});
$("backup").onclick=()=>task("backup",async(current)=>{const r=await api("/api/memory/backup",{});if(!current())return;$("results").replaceChildren(el("h2","Sauvegarde mémoire créée"),el("p",r.path,"answer"),el("p","Les dossiers CAO et médias se sauvegardent depuis Dossiers dans Jarvis.","hint"))});
$("domain").onchange=()=>{
  ++renderGeneration;
  $("results").replaceChildren(el("p","Contexte changé. Lance une recherche dans le domaine sélectionné."));
  $("fact-list").replaceChildren();$("facts").textContent="—";$("notice").textContent="";
  return refresh().catch(e=>$("notice").textContent=e.message);
};
refresh().catch(e=>$("notice").textContent=e.message);
