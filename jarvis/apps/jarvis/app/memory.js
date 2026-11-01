'use strict';
let generation=0;
document.querySelector('#search').addEventListener('submit',async event=>{
  event.preventDefault();const request=++generation;
  const status=document.querySelector('#status'), results=document.querySelector('#results');
  results.replaceChildren();status.textContent='Recherche…';
  const params=new URLSearchParams({q:document.querySelector('#query').value,project:document.querySelector('#project').value});
  try{
    const response=await fetch('/api/memory/search?'+params,{credentials:'same-origin'});
    const data=await response.json();if(request!==generation)return;
    if(!response.ok)throw new Error(data.error||'Recherche indisponible.');
    status.textContent=data.available ? `${data.results.length} passage(s) retrouvé(s).` : data.message;
    for(const row of data.results){
      const article=document.createElement('article');article.className='panel';
      const title=document.createElement('h2');title.textContent=row.source_path;
      const text=document.createElement('p');text.style.whiteSpace='pre-wrap';text.textContent=row.text;
      const source=document.createElement('p');source.className='help';source.textContent=`${row.provenance} · lignes ${row.start_line}–${row.end_line} · SHA-256 ${row.sha256}`;
      article.append(title,text,source);results.append(article);
    }
  }catch(error){if(request===generation)status.textContent=error.message;}
});
