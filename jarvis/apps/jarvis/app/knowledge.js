'use strict';
let turn=0;
function el(tag,text){const n=document.createElement(tag);n.textContent=text;return n;}
document.getElementById('search').addEventListener('submit',async e=>{
 e.preventDefault();const own=++turn;const status=document.getElementById('status');status.textContent='Recherche locale…';
 try{const r=await fetch('/api/knowledge/search?q='+encodeURIComponent(document.getElementById('q').value));const d=await r.json();if(own!==turn)return;if(!r.ok)throw new Error(d.error||'Recherche indisponible');
 const box=document.getElementById('results');box.replaceChildren();
 for(const item of d.items){const a=el('article','');a.append(el('h2',item.card.title),el('p',item.card.statement),el('p',item.card.bojart_application));for(const s of item.sources){const link=el('a',s.title||s.id);const u=new URL(s.url);if(u.protocol==='https:'){link.href=u.href;link.target='_blank';link.rel='noopener noreferrer';a.append(link,el('br',''));}}a.append(el('p',item.warnings.join(' ')));box.append(a);}
 status.textContent=d.total_returned+' fiches · recherche textuelle · aucune action machine.';
 }catch(err){if(own===turn)status.textContent=err.message;}
});
