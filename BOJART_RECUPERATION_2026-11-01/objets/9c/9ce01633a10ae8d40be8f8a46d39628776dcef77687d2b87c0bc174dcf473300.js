export function validateSTLFiles(files) {
  if(!Array.isArray(files)||!files.length)throw new Error('Sélectionnez au moins un fichier STL.');
  if(files.length>12)throw new Error('Importez jusqu’à 12 fichiers STL à la fois.');
  for(const file of files)if(!/\.stl$/i.test(file.name)||!Number.isFinite(file.size)||file.size<=0||file.size>50*1024*1024)throw new Error(`${file.name||'Fichier'} : fichier STL non vide requis, 50 Mo maximum.`);
  return files;
}

export function readSTLImportChoices(form,entries) {
  return entries.map((entry,index)=>{
    if(entry.added)return {...entry};
    const unit=form.elements.namedItem(`unit-${index}`)?.value,tech=form.elements.namedItem(`tech-${index}`)?.value;
    if(!['mm','inch'].includes(unit))throw new Error(`${entry.file.name} : précisez l’unité d’origine.`);
    if(!['fdm','resin'].includes(tech))throw new Error(`${entry.file.name} : choisissez le procédé prévu.`);
    return {...entry,unit,tech};
  });
}

export function renderSTLImportSetup({files,project,esc,icon}) {
  return `<form id="stl-import-form" class="stl-import-form" data-project="${esc(project.id)}"><div class="stl-import-intro"><span class="tag tag-red">AVANT L’ANALYSE</span><h3>LA BONNE ÉCHELLE.<br>LE BON PROCÉDÉ.</h3><p>Destination : <strong>${esc(project.name)}</strong>. Un STL ne déclare pas son unité. Indiquez l’unité d’origine et le procédé souhaité pour chaque fichier.</p></div><div class="stl-import-list">${files.map((file,i)=>`<section class="stl-import-row" data-stl-row="${i}" aria-label="${esc(file.name)}"><div class="stl-import-file"><b>${String(i+1).padStart(2,'0')}</b><div><strong>${esc(file.name)}</strong><small>${(file.size/1024/1024).toLocaleString('fr-FR',{maximumFractionDigits:2})} Mo</small></div></div><label>Unité d’origine<select name="unit-${i}" required><option value="">À préciser</option><option value="mm">Millimètres (mm)</option><option value="inch">Pouces (inch)</option></select></label><label>Procédé prévu<select name="tech-${i}" required><option value="">À choisir</option><option value="fdm">FDM</option><option value="resin">Résine UV</option></select></label><p class="stl-import-status" data-stl-status="${i}" role="status">En attente de vos choix.</p></section>`).join('')}</div><p class="note-line">${icon('info')} Le procédé pourra être révisé après l’étude de la pièce. Cet import n’affecte aucune imprimante et ne lance aucune fabrication.</p><div id="form-error" class="form-error" role="alert"></div><p data-stl-import-summary role="status"></p><div class="form-actions"><button type="button" class="button" data-action="close-dialog">Fermer</button><button type="button" class="button" data-action="stl-import-inspect" hidden>Inspecter la dernière pièce ${icon('arrow')}</button><button type="submit" class="button button-red">Analyser et ajouter ${files.length>1?'les pièces':'la pièce'} ${icon('upload')}</button></div></form>`;
}
