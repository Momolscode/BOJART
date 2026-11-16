/**
 * BOJ.ART — a visual editing desk built around the inspected local film.
 * Reference timings and crops come from assets/brand-film-sources.json.
 * Preparing a plan never starts a render, a skill, an upload or a publication.
 */
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const FILM_DURATION = 22.7;
const sourceURL = id => `https://www.tiktok.com/@boj.art/video/${id}`;
const sources = [
  {id:'7467517355535404310',label:'Baki fini · UV et lumière d’atelier',url:sourceURL('7467517355535404310'),recordedSha256:'27f922de227cd93c79ba5ca11f3adf9c08d883436ed27590d0abae2936ac44e8'},
  {id:'7464268707989114134',label:'Baki · partie 2, mise en peinture',url:sourceURL('7464268707989114134'),recordedSha256:'9ca3bd55f02e5841a1f8fba53adef40b4bd5c13954c6f8ff615dfe6ab3d56bf4'}
];
const chapters = [
  {id:'detail',number:'01',title:'DÉTAIL',filmLabel:'LE DÉTAIL.',start:0,end:5.2,still:1.3,image:'brand-film-frame-01-detail.webp',alt:'Image du film : visage et matière de Baki sous lumière UV violette.',intent:'Accrocher par la matière.',description:'Le regard sous UV, puis le détail peint en lumière d’atelier.',source:0,ranges:'00:08,9–00:11,9 · 00:24–00:26,2',framing:'Cadre portrait entier conservé. La lumière UV appartient à la prise d’origine.',shots:[{id:'detail-uv',source:0,in:8.9,out:11.9,referenceOutput:[0,3],crop:null},{id:'detail-colour',source:0,in:24,out:26.2,referenceOutput:[3,5.2],crop:null}]},
  {id:'geste',number:'02',title:'GESTE',filmLabel:'LE GESTE.',start:5.2,end:10.6,still:9.1,image:'brand-film-frame-02-geste.webp',alt:'Image du film : les mains de l’artiste et son pinceau dans un bandeau horizontal.',intent:'Montrer la main.',description:'Trois touches de peinture. Le geste relie la surface au travail de l’artiste.',source:1,ranges:'00:03,8–00:05,4 · 00:11,6–00:13,2 · 00:20,5–00:22,9',framing:'Bandeau vidéo extrait : 576 × 324 px, x = 0, y = 662. Il est présenté en 640 × 360 dans le master, soit +11,1 %, avec ses proportions conservées.',shots:[{id:'gesture-01',source:1,in:3.8,out:5.4,referenceOutput:[5.2,6.8],crop:{x:0,y:662,width:576,height:324}},{id:'gesture-02',source:1,in:11.6,out:13.2,referenceOutput:[6.8,8.4],crop:{x:0,y:662,width:576,height:324}},{id:'gesture-03',source:1,in:20.5,out:22.9,referenceOutput:[8.4,10.8],crop:{x:0,y:662,width:576,height:324}}]},
  {id:'oeuvre',number:'03',title:'ŒUVRE',filmLabel:'L’ŒUVRE.',start:10.6,end:19.1,still:12.3,image:'brand-film-frame-03-oeuvre.webp',alt:'Image du film : la figurine Baki entière et son socle dans l’atelier.',intent:'Laisser le volume exister.',description:'La pièce et son socle, puis une présentation mobile de l’œuvre finie.',source:0,ranges:'00:16,5–00:20,3 · 00:29,2–00:34,2',framing:'Portrait entier : 576 × 1 024 vers 630 × 1 120 px dans le master. Proportions et couleurs des œuvres conservées.',shots:[{id:'reveal-full',source:0,in:16.5,out:20.3,referenceOutput:[10.6,14.4],crop:null},{id:'reveal-moving',source:0,in:29.2,out:34.2,referenceOutput:[14.4,19.4],crop:null}]},
  {id:'embleme',number:'04',title:'EMBLÈME',filmLabel:'LA SIGNATURE.',start:19.1,end:22.7,still:20.6,image:'brand-film-frame-04-signature.webp',alt:'Image du film : l’emblème original BOJ.ART, personnage manga et lettrage blanc et rouge.',intent:'Signer avec l’original.',description:'L’emblème de la publication Baki termine le film, dans son cadre noir.',source:0,ranges:'00:35,2–00:36,7 · maintien final 2,1 s',framing:'Emblème d’origine conservé. La dernière image est maintenue 2,1 secondes ; aucune nouvelle variante du logo n’est créée.',shots:[{id:'signature',source:0,in:35.2,out:36.7,referenceOutput:[19.1,22.7],crop:null,holdLastFrameSeconds:2.1}]}
];
const formats = [
  {id:'9:16',label:'Vertical',width:1080,height:1920},
  {id:'1:1',label:'Carré',width:1080,height:1080},
  {id:'16:9',label:'Panoramique',width:1920,height:1080}
];
const skills = [
  {name:'claude-real-video',role:'Lire les plans',status:'Audité · à intégrer',tone:'reviewed',owner:'Communautaire · MIT',url:'https://github.com/HUANGCHIHHUNGLeo/claude-real-video/blob/master/skills/claude-real-video/SKILL.md',description:'Extractions, transcription et repères temporels pour préparer une lecture documentée des vidéos. L’échantillonnage ne garantit pas l’examen de chaque image.',conditions:'Préparation locale ; l’analyse par modèle dépendra du moteur choisi.'},
  {name:'Remotion',role:'Composer le mouvement',status:'Audité · à intégrer',tone:'reviewed',owner:'Skill officiel',url:'https://github.com/remotion-dev/skills/blob/main/skills/remotion-best-practices/SKILL.md',description:'Compositions reproductibles : titrage, chapitres, sous-titres et déclinaisons de formats. Les règles de mouvement devront être adaptées aux références BOJ.ART.',conditions:'Rendu local possible ; conditions du moteur Remotion à vérifier selon l’usage professionnel.'},
  {name:'ElevenLabs',role:'Dessiner le son',status:'Audité · option cloud',tone:'cloud',owner:'Skill officiel · dépôt MIT',url:'https://github.com/elevenlabs/skills/blob/main/sound-effects/SKILL.md',description:'Le skill sound-effects peut produire des accents sonores à partir d’une description. La direction sonore reste à écouter et à choisir.',conditions:'Texte envoyé au fournisseur, compte et API payante. Aucune génération dans ce Studio.'},
  {name:'video-evidence',role:'Relier le choix à sa preuve',status:'Laboratoire',tone:'lab',owner:'Communautaire · AGPL-3.0',url:'https://github.com/kenchikuliu/video-evidence/blob/main/SKILL.md',description:'Scènes, images et observations horodatées pour comparer les choix de plans. Candidat à tester sur le corpus BOJ.ART, sans score de signature présumé.',conditions:'Analyse locale avec dépendances et modèles ; la branche de génération distante reste distincte.'},
  {name:'color-grading-skill',role:'Exécuter une couleur choisie',status:'À corriger',tone:'hold',owner:'Communautaire · MIT',url:'https://github.com/kajisho5/color-grading-skill/blob/main/SKILL.md',description:'LUT et corrections explicites via FFmpeg. Le YAML du SKILL.md consulté comporte une erreur : correction et essai sur copies nécessaires.',conditions:'Traitement local. Préserver les originaux et vérifier chaque résultat avant d’adopter un traitement.'}
];
const timecode = value => {
  const tenths = Math.max(0,Math.round((Number(value)||0)*10));
  return `${String(Math.floor(tenths/600)).padStart(2,'0')}:${String(Math.floor(tenths/10)%60).padStart(2,'0')},${tenths%10}`;
};

export function renderStudioView({esc=escapeHTML,icon=()=>''}={}) {
  return `<section class="studio-view" data-studio-motion="off" aria-labelledby="studio-title">
    <header class="studio-masthead"><p class="studio-overline"><span></span> BOJ.ART / DIRECTION VISUELLE</p><span class="studio-edition">ÉDIT D’ÉTUDE <b>V.01</b></span></header>

    <section class="studio-hero" aria-label="Film de démonstration et direction proposée">
      <div class="studio-direction">
        <p class="studio-overline studio-red">UNE PIÈCE. QUATRE MOMENTS.</p>
        <h2 id="studio-title">DU DÉTAIL.<br>À <em>L’ŒUVRE.</em></h2>
        <p class="studio-lead">La matière attire.<br>La main raconte.<br>L’œuvre prend sa place.</p>
        <div class="studio-manifesto"><p>MANIFESTE PROPOSÉ <span>À VALIDER</span></p><ol>${chapters.map(chapter=>`<li><button type="button" class="studio-chapter-link" data-studio-seek="${chapter.start}" data-studio-chapter="${chapter.id}" ${chapter.start===0?'aria-current="true"':''}><span>${chapter.number}</span><strong>${esc(chapter.title)}</strong><small>${esc(chapter.intent)}</small></button></li>`).join('')}</ol></div>
        <div class="studio-hero-actions"><button type="button" class="button button-red studio-send" data-action="visual-present" data-visual-id="film">${icon('screens')} Envoyer le film <span>ÉCRAN 03 ${icon('arrow')}</span></button><button type="button" class="button" data-action="project-studio">${icon('folder')} Les contenus du projet</button><button type="button" class="studio-text-button" data-action="identity">La référence historique ${icon('arrowUp')}</button></div>
        <p class="studio-direction-note">Une direction construite à partir des publications de Baki. Elle reste une proposition de montage à valider avec l’artiste.</p>
      </div>

      <figure class="studio-player">
        <div class="studio-player-top"><span><i></i> BAKI HANMA / 60 CM</span><span>9:16 <b>22,7 S</b></span></div>
        <div class="studio-player-screen"><span class="studio-frame-corner top-left" aria-hidden="true"></span><span class="studio-frame-corner bottom-right" aria-hidden="true"></span><video data-studio-video src="./assets/brand-film-master.mp4" poster="./assets/brand-film-poster.webp" controls playsinline muted preload="metadata" aria-label="Film silencieux BOJ.ART de 22,7 secondes : détail de Baki, peinture, œuvre entière et emblème. Lire à votre demande."></video></div>
        <figcaption class="studio-player-bottom"><div><strong>Du détail à l’œuvre.</strong><span>Nouvel édit · deux publications d’origine</span></div><span class="studio-silent">SANS PISTE AUDIO</span></figcaption>
        <p class="studio-film-error" data-studio-video-error role="status" hidden>Le film ne peut pas être lu ici. Les quatre images ci-dessous restent disponibles.</p>
      </figure>
    </section>

    <section class="studio-sequence" aria-labelledby="studio-sequence-title">
      <div class="studio-section-head"><div><p class="studio-overline">01 / LE FIL DU MONTAGE</p><h3 id="studio-sequence-title">CHAQUE PLAN A UN RÔLE.</h3></div><div class="studio-transport"><button type="button" data-studio-command="toggle" class="studio-play-button" aria-label="Lire le film"><span data-studio-play-symbol aria-hidden="true">▶</span><span data-studio-play-label>Lire</span></button><output data-studio-current-time>00:00,0</output><span>/</span><span data-studio-total-time>00:22,7</span></div></div>
      <div class="studio-time-rail" data-studio-rail style="--studio-progress:0%"><div class="studio-time-segments" aria-hidden="true">${chapters.map(chapter=>`<i style="width:${(chapter.end-chapter.start)/FILM_DURATION*100}%"></i>`).join('')}</div><span class="studio-playhead" data-studio-playhead aria-hidden="true"></span><label class="studio-sr-only" for="studio-scrub">Position dans le film de référence</label><input id="studio-scrub" data-studio-scrub type="range" min="0" max="22.7" step="0.1" value="0" aria-valuetext="00:00,0 sur 00:22,7"></div>
      <div class="studio-time-labels" aria-hidden="true"><span>00:00</span><span>00:05,2</span><span>00:10,6</span><span>00:19,1</span><span>00:22,7</span></div>
      <ol class="studio-filmstrip">${chapters.map(chapter=>`<li><button type="button" class="studio-shot" data-studio-seek="${chapter.start}" data-studio-chapter="${chapter.id}" ${chapter.start===0?'aria-current="true"':''} aria-label="Voir ${esc(chapter.title.toLowerCase())} à ${esc(timecode(chapter.start))}"><span class="studio-shot-image"><img src="./assets/${esc(chapter.image)}" alt="${esc(chapter.alt)}" loading="lazy" width="720" height="1280"><span class="studio-shot-pointer" aria-hidden="true">↗</span></span><span class="studio-shot-caption"><span>${chapter.number}</span><strong>${esc(chapter.title)}</strong><small>${esc(timecode(chapter.start))}</small></span><span class="studio-shot-intent">${esc(chapter.intent)}</span></button></li>`).join('')}</ol>
      <div class="studio-source-cue" aria-live="polite" aria-atomic="true"><span class="studio-source-index" data-studio-source-index>01</span><div><span class="studio-overline">LE PLAN À L’ÉCRAN</span><h4 data-studio-source-title>${esc(chapters[0].description)}</h4><p data-studio-source-framing>${esc(chapters[0].framing)}</p><div class="studio-source-reference"><a data-studio-source-link href="${sources[0].url}" target="_blank" rel="noopener noreferrer">Publication d’origine ${icon('arrowUp')}</a><span data-studio-source-ranges>${esc(chapters[0].ranges)}</span></div></div></div>
      <p class="studio-sequence-note">Cliquez un moment pour vous y placer. Le curseur suit la lecture réelle. Les images du film sont affichées entières ; les timecodes source renvoient aux publications.</p>
    </section>

    <section class="studio-language" aria-labelledby="studio-language-title"><div><p class="studio-overline">02 / LE LANGAGE PROPOSÉ</p><h3 id="studio-language-title">DU CARACTÈRE.<br><em>DE L’ESPACE POUR L’ART.</em></h3></div><div class="studio-language-copy"><p>Charbon pour le fond, ivoire pour la lecture, carmin pour l’action. Des entrées courtes, un repère qui suit le temps, des détails qui répondent au geste.</p><div class="studio-palette" aria-label="Palette proposée pour l’interface"><span><i style="--swatch:#09090D"></i><b>CHARBON</b><small>#09090D</small></span><span><i style="--swatch:#F4F0ED"></i><b>IVOIRE</b><small>#F4F0ED</small></span><span><i style="--swatch:#F13A54"></i><b>CARMIN</b><small>#F13A54</small></span></div><p class="studio-language-note">Cette palette concerne l’interface et l’habillage du film. Les plans gardent leurs couleurs d’origine.</p></div></section>

    <section class="studio-workbench" aria-labelledby="studio-plan-title">
      <div class="studio-section-head"><div><p class="studio-overline">03 / PRÉPARER LA SUITE</p><h3 id="studio-plan-title">LE PROCHAIN ÉDIT.</h3></div><span class="studio-plan-state">PLAN / À MONTER</span></div>
      <p class="studio-plan-context">À partir du film de référence Baki · 60 cm.</p>
      <div class="studio-plan-layout">
        <form class="studio-plan-form" data-studio-plan-form>
          <fieldset><legend>Choisir le cadre <span>01</span></legend><div class="studio-format-options">${formats.map((format,index)=>`<label><input type="radio" name="studio-format" value="${format.id}" ${index===0?'checked':''}><span class="studio-format-choice"><i class="studio-format-glyph" style="--format-ratio:${format.width}/${format.height}" aria-hidden="true"></i><strong>${format.id}</strong><small>${format.label}</small></span></label>`).join('')}</div></fieldset>
          <fieldset class="studio-duration-field"><legend>Donner le rythme <span>02</span></legend><div class="studio-duration-heading"><label for="studio-duration">Durée cible</label><output for="studio-duration" data-studio-duration-output>23 <small>SEC</small></output></div><input type="range" id="studio-duration" name="studio-duration" min="10" max="60" step="1" value="23" aria-describedby="studio-duration-hint"><div class="studio-duration-presets"><span>10 s</span><button type="button" data-studio-duration="15">15 s</button><button type="button" data-studio-duration="23" aria-pressed="true">23 s</button><button type="button" data-studio-duration="30">30 s</button><span>60 s</span></div><p id="studio-duration-hint" data-studio-plan-hint>23 secondes visées. Les points de coupe seront à choisir au montage.</p></fieldset>
          <div class="studio-plan-actions"><button type="submit" class="button button-red">${icon('save')} Exporter le plan JSON ${icon('arrowUp')}</button><span>Paramètres et sources.<br>Préparation de cette session.</span></div><p class="studio-plan-message" data-studio-plan-message role="status"></p>
        </form>
        <div class="studio-plan-preview"><div class="studio-plan-preview-head"><span>ÉTUDE DE CADRE</span><span data-studio-format-dimensions>1 080 × 1 920</span></div><div class="studio-format-stage"><div class="studio-format-window" data-studio-format-window style="--preview-width:56.25%;--preview-ratio:9/16;--preview-scale:.5625"><img data-studio-plan-image src="./assets/brand-film-frame-03-oeuvre.webp" alt="Image du film de référence placée entière dans le cadre choisi ; ceci n’est pas un rendu vidéo." loading="lazy" width="720" height="1280"><i aria-hidden="true"></i><span data-studio-format-label>9:16</span></div></div><div class="studio-proposed-beats" data-studio-proposed-beats aria-label="Répartition indicative des quatre moments"></div><p>Image fixe de référence, adaptée au cadre sans couper l’œuvre. Le plan exporté décrit une intention ; le nouveau film reste à monter et à valider.</p></div>
      </div>
      <details class="studio-plan-json"><summary>Lire le contenu du plan <span aria-hidden="true">+</span></summary><pre data-studio-plan-json tabindex="0" aria-label="Plan d’édit JSON"></pre></details>
    </section>

    <section class="studio-tools" aria-labelledby="studio-tools-title"><div class="studio-section-head"><div><p class="studio-overline">04 / LES COMPÉTENCES À RELIER</p><h3 id="studio-tools-title">UNE CHAÎNE CRÉATIVE.</h3></div><span class="studio-tool-count">05 <small>CANDIDATS</small></span></div><p class="studio-tools-intro">Des skills identifiés pour lire, composer, sonoriser et vérifier. La sélection a été auditée ; aucun de ces cinq outils n’est activé dans ce Studio.</p><div class="studio-skill-index">${skills.map((skill,index)=>`<details class="studio-skill"><summary><span class="studio-skill-number">0${index+1}</span><span class="studio-skill-name"><strong>${esc(skill.name)}</strong><small>${esc(skill.role)}</small></span><span class="studio-skill-status ${skill.tone}">${esc(skill.status)}</span><span class="studio-skill-expand" aria-hidden="true">+</span></summary><div class="studio-skill-detail"><p>${esc(skill.description)}</p><p>${esc(skill.conditions)}</p><div><span>${esc(skill.owner)}</span><a href="${esc(skill.url)}" target="_blank" rel="noopener noreferrer">Consulter le SKILL.md ${icon('arrowUp')}</a></div></div></details>`).join('')}</div></section>

    <details class="studio-provenance"><summary><span>LES SOURCES & LES CHOIX DE MONTAGE</span><span aria-hidden="true">+</span></summary><div><p>Ce film de 22,7 s est issu de deux publications de la même figurine Baki annoncée à 60 cm. Il ne représente pas une nouvelle fabrication dans l’atelier.</p><ol>${sources.map(source=>`<li><a href="${source.url}" target="_blank" rel="noopener noreferrer">${esc(source.label)} ${icon('arrowUp')}</a><span>${source.id}</span></li>`).join('')}</ol><p>La peinture provient du bandeau horizontal de la seconde vidéo. La grande carte logo et l’ancienne incitation à s’abonner restent dans l’original archivé. Les autres plans conservent leur cadre portrait entier. Fondus à 10,6–10,8 s et 19,1–19,4 s ; vitesse d’origine, cadence 30 i/s et maintien final de l’emblème de 2,1 s.</p><p>Aucune piste audio n’a été ajoutée. Les sons des originaux restent dans l’archive. Le lecteur affiche le master de ce montage en 720 × 1 280 px.</p><a class="studio-manifest-link" href="./assets/brand-film-sources.json" target="_blank" rel="noopener">Lire le manifeste des sources ${icon('arrowUp')}</a></div></details>

    <footer class="studio-footer"><div><img src="./assets/logo.webp" alt="" loading="lazy"><p>LA SIGNATURE RESTE<br><strong>ENTRE VOS MAINS.</strong></p></div><nav aria-label="Continuer le travail créatif"><button type="button" class="studio-text-button" data-action="open-archive">Ouvrir l’archive ${icon('arrowUp')}</button><button type="button" class="button" data-action="story">${icon('film')} Préparer un scénario</button></nav></footer>
  </section>`;
}

function createPlan(formatId,duration) {
  const format = formats.find(item=>item.id===formatId)||formats[0];
  const target = Math.min(60,Math.max(10,Math.round(Number(duration)||23)));
  let start = 0;
  const timeline = chapters.map((chapter,index)=>{
    const end = index===chapters.length-1?target:Math.round(chapter.end/FILM_DURATION*target*10)/10;
    const beat = {role:chapter.title,intention:chapter.intent,proposedStartSeconds:start,proposedEndSeconds:end,referenceChapterSeconds:[chapter.start,chapter.end],timingStatus:'indicative_requires_editing',referenceShots:chapter.shots.map(shot=>({id:shot.id,sourceId:sources[shot.source].id,sourceInSeconds:shot.in,sourceOutSeconds:shot.out,referenceOutputSeconds:shot.referenceOutput,crop:shot.crop,holdLastFrameSeconds:shot.holdLastFrameSeconds||0}))};
    start = end;
    return beat;
  });
  return {
    format:'bojart.edit-plan.v1',brand:'BOJ.ART',status:'plan_only',renderRequested:false,outputVideo:null,
    reference:{title:'Baki — Du détail à l’œuvre',version:1,durationSeconds:FILM_DURATION,manifest:'assets/brand-film-sources.json',master:'assets/brand-film-master.mp4',preview:'assets/brand-film-preview.mp4',subject:'Figurine Baki publiée comme 60 cm',audioTracks:0},
    direction:{status:'proposed_requires_artist_review',sequence:chapters.map(chapter=>chapter.title),sourceColours:'preserve_original',emblem:'use_original_from_cited_publication',interfacePalette:{charcoal:'#09090D',ivory:'#F4F0ED',crimson:'#F13A54'}},
    target:{aspectRatio:format.id,width:format.width,height:format.height,framesPerSecond:30,durationSeconds:target,framing:'contain_sources_at_original_aspect_ratio; review_each_shot',speed:'retain_source_speed; choose_cuts_before_rendering'},
    sources:sources.map(source=>({id:source.id,url:source.url,label:source.label,sha256RecordedInSourceManifest:source.recordedSha256})),
    timeline,
    audio:{status:'to_choose',referenceIsSilent:true,originalAudioPreservedInArchive:true,cloudGenerationRequested:false},
    nextSteps:[target>FILM_DURATION?'Choisir des plans supplémentaires, prolongements ou maintiens pour atteindre la durée cible.':'Choisir les points de coupe pour atteindre la durée cible.','Vérifier chaque cadre et le raccord entre les quatre moments.','Décider du son et vérifier les droits des pistes retenues.','Rendre un nouveau fichier, inspecter le résultat puis valider avec l’artiste.'],
    publication:{requested:false,status:'not_requested'}
  };
}

export function mountStudio(root,{motion=true}={}) {
  const view = root?.matches?.('.studio-view')?root:root?.querySelector?.('.studio-view');
  if(!view)return {dispose(){},setMotion(){}};
  const win = view.ownerDocument.defaultView;
  const doc = view.ownerDocument;
  const video = view.querySelector('[data-studio-video]');
  const scrub = view.querySelector('[data-studio-scrub]');
  const durationInput = view.querySelector('#studio-duration');
  const form = view.querySelector('[data-studio-plan-form]');
  const listeners = [];
  const objectURLs = new Set();
  const cleanupTimers = new Set();
  let disposed = false;
  let motionEnabled = !!motion;
  let animationFrame = null;
  let currentChapter = -1;
  let pendingSeek = null;
  let plan = createPlan('9:16',23);
  const mediaPreference = win?.matchMedia?.('(prefers-reduced-motion: reduce)');
  const listen = (target,event,handler,options) => {target?.addEventListener(event,handler,options);listeners.push(()=>target?.removeEventListener(event,handler,options));};
  const node = selector => view.querySelector(selector);
  const setText = (selector,value) => {const element=node(selector);if(element)element.textContent=value;};
  const filmDuration = () => Number.isFinite(video?.duration)&&video.duration>0?video.duration:FILM_DURATION;
  const cancelFrame = () => {if(animationFrame!==null){win?.cancelAnimationFrame?.(animationFrame);animationFrame=null;}};
  const updatePosition = () => {
    if(disposed||!video)return;
    const duration = filmDuration();
    const time = Math.min(duration,Math.max(0,Number(video.currentTime)||0));
    const progress = Math.min(100,time/duration*100);
    node('[data-studio-rail]')?.style.setProperty('--studio-progress',`${progress}%`);
    if(scrub){scrub.max=String(duration);scrub.value=String(time);scrub.setAttribute('aria-valuetext',`${timecode(time)} sur ${timecode(duration)}`);}
    setText('[data-studio-current-time]',timecode(time));
    setText('[data-studio-total-time]',timecode(duration));
    let index = chapters.length-1;
    for(let i=0;i<chapters.length;i++){if(time<chapters[i].end){index=i;break;}}
    if(currentChapter!==index){
      currentChapter=index;
      const chapter=chapters[index];
      view.querySelectorAll('[data-studio-chapter]').forEach(button=>{if(button.dataset.studioChapter===chapter.id)button.setAttribute('aria-current','true');else button.removeAttribute('aria-current');});
      setText('[data-studio-source-index]',chapter.number);
      setText('[data-studio-source-title]',chapter.description);
      setText('[data-studio-source-framing]',chapter.framing);
      setText('[data-studio-source-ranges]',chapter.ranges);
      const link=node('[data-studio-source-link]');if(link)link.href=sources[chapter.source].url;
    }
  };
  const updateTransport = () => {
    const playing=video&&!video.paused&&!video.ended;
    view.classList.toggle('studio-is-playing',!!playing);
    const toggle=node('[data-studio-command="toggle"]');
    toggle?.setAttribute('aria-label',playing?'Mettre le film en pause':'Lire le film');
    setText('[data-studio-play-label]',playing?'Pause':'Lire');
    setText('[data-studio-play-symbol]',playing?'Ⅱ':'▶');
  };
  const frame = () => {
    animationFrame=null;
    if(disposed||!video||video.paused||video.ended||doc.hidden)return;
    updatePosition();
    if(motionEnabled&&!mediaPreference?.matches)animationFrame=win?.requestAnimationFrame?.(frame)??null;
  };
  const startFrame = () => {cancelFrame();if(motionEnabled&&!mediaPreference?.matches&&!doc.hidden&&!video.paused&&!video.ended)animationFrame=win?.requestAnimationFrame?.(frame)??null;};
  const setMotion = enabled => {
    if(disposed)return;
    motionEnabled=!!enabled;
    view.dataset.studioMotion=motionEnabled&&!mediaPreference?.matches?'on':'off';
    startFrame();
  };
  const seek = value => {
    const target=Math.min(filmDuration(),Math.max(0,Number(value)||0));
    try{video.currentTime=target;pendingSeek=null;updatePosition();}
    catch{pendingSeek=target;setText('[data-studio-video-error]','Le repère sera affiché dès que les métadonnées du film seront chargées.');node('[data-studio-video-error]')?.removeAttribute('hidden');}
  };
  const updatePlan = () => {
    const selected=node('input[name="studio-format"]:checked')?.value||'9:16';
    const duration=Number(durationInput?.value)||23;
    plan=createPlan(selected,duration);
    const format=formats.find(item=>item.id===selected)||formats[0];
    const output=node('[data-studio-duration-output]');
    if(output){output.replaceChildren(doc.createTextNode(`${plan.target.durationSeconds} `));const small=doc.createElement('small');small.textContent='SEC';output.append(small);}
    setText('[data-studio-format-dimensions]',`${format.width.toLocaleString('fr-FR')} × ${format.height.toLocaleString('fr-FR')}`);
    setText('[data-studio-format-label]',format.id);
    const preview=node('[data-studio-format-window]');
    preview?.style.setProperty('--preview-width',`${format.width<format.height?56.25:100}%`);
    preview?.style.setProperty('--preview-ratio',`${format.width}/${format.height}`);
    preview?.style.setProperty('--preview-scale',String(format.width/format.height));
    const hint=plan.target.durationSeconds>FILM_DURATION+1?`${plan.target.durationSeconds} secondes visées : prévoir des plans supplémentaires ou des maintiens. La référence dure 22,7 s.`:`${plan.target.durationSeconds} secondes visées. Les points de coupe seront à choisir au montage.`;
    setText('[data-studio-plan-hint]',hint);
    view.querySelectorAll('[data-studio-duration]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.studioDuration)===plan.target.durationSeconds)));
    const beats=node('[data-studio-proposed-beats]');
    if(beats){beats.replaceChildren();plan.timeline.forEach(beat=>{const item=doc.createElement('div');item.style.flex=String(beat.proposedEndSeconds-beat.proposedStartSeconds);const title=doc.createElement('strong');title.textContent=beat.role;const time=doc.createElement('span');time.textContent=`${(beat.proposedEndSeconds-beat.proposedStartSeconds).toFixed(1).replace('.',',')} s`;item.append(title,time);beats.append(item);});}
    setText('[data-studio-plan-json]',JSON.stringify(plan,null,2));
    setText('[data-studio-plan-message]','');
  };
  const exportPlan = event => {
    event.preventDefault();
    updatePlan();
    const exported={...plan,preparedAt:new Date().toISOString()};
    const urlAPI=win?.URL;
    if(!urlAPI?.createObjectURL){setText('[data-studio-plan-json]',JSON.stringify(exported,null,2));const details=node('.studio-plan-json');if(details)details.open=true;setText('[data-studio-plan-message]','Le téléchargement n’est pas disponible ici. Le plan JSON est ouvert ci-dessous pour copie.');return;}
    try{
      const blob=new win.Blob([JSON.stringify(exported,null,2)+'\n'],{type:'application/json;charset=utf-8'});
      const url=urlAPI.createObjectURL(blob);objectURLs.add(url);
      const link=doc.createElement('a');link.href=url;link.download=`BOJ_ART_plan_edit_${plan.target.aspectRatio.replace(':','x')}_${plan.target.durationSeconds}s_${exported.preparedAt.slice(0,10)}.json`;link.hidden=true;doc.body.append(link);link.click();link.remove();
      const timer=win.setTimeout(()=>{urlAPI.revokeObjectURL(url);objectURLs.delete(url);cleanupTimers.delete(timer);},30000);cleanupTimers.add(timer);
      setText('[data-studio-plan-message]','Plan préparé. Le téléchargement du JSON a été demandé au navigateur ; le nouveau film reste à monter.');
    }catch{setText('[data-studio-plan-message]','Le plan est prêt, mais le téléchargement a échoué. Vous pouvez le copier dans « Lire le contenu du plan ».');const details=node('.studio-plan-json');if(details)details.open=true;}
  };
  listen(view,'click',event=>{
    const target=event.target?.closest?.('[data-studio-seek],[data-studio-command],[data-studio-duration]');
    if(!target||!view.contains(target))return;
    if(target.hasAttribute('data-studio-seek'))seek(target.dataset.studioSeek);
    else if(target.hasAttribute('data-studio-duration')){durationInput.value=target.dataset.studioDuration;updatePlan();}
    else if(target.dataset.studioCommand==='toggle'){
      if(video.paused||video.ended){if(video.ended)seek(0);try{const promise=video.play();promise?.catch(()=>{if(disposed)return;setText('[data-studio-video-error]','La lecture n’a pas démarré. Essayez les commandes du lecteur vidéo.');node('[data-studio-video-error]')?.removeAttribute('hidden');});}catch{setText('[data-studio-video-error]','La lecture n’a pas démarré. Essayez les commandes du lecteur vidéo.');node('[data-studio-video-error]')?.removeAttribute('hidden');}}
      else video.pause();
    }
  });
  listen(scrub,'input',()=>seek(scrub.value));
  listen(video,'timeupdate',updatePosition);
  listen(video,'seeked',updatePosition);
  listen(video,'durationchange',updatePosition);
  listen(video,'loadedmetadata',()=>{if(pendingSeek!==null)seek(pendingSeek);node('[data-studio-video-error]')?.setAttribute('hidden','');updatePosition();});
  listen(video,'play',()=>{node('[data-studio-video-error]')?.setAttribute('hidden','');updateTransport();startFrame();});
  listen(video,'pause',()=>{cancelFrame();updateTransport();updatePosition();});
  listen(video,'ended',()=>{cancelFrame();updateTransport();updatePosition();});
  listen(video,'error',()=>{cancelFrame();setText('[data-studio-video-error]','Le film ne peut pas être lu ici. Les quatre images et les repères documentés restent disponibles.');node('[data-studio-video-error]')?.removeAttribute('hidden');});
  listen(doc,'visibilitychange',()=>{if(doc.hidden)cancelFrame();else startFrame();});
  listen(mediaPreference,'change',()=>setMotion(motionEnabled));
  listen(form,'input',updatePlan);
  listen(form,'change',updatePlan);
  listen(form,'submit',exportPlan);
  updatePlan();updatePosition();updateTransport();setMotion(motion);
  return {
    setMotion,
    dispose(){if(disposed)return;disposed=true;cancelFrame();listeners.forEach(remove=>remove());cleanupTimers.forEach(timer=>win.clearTimeout(timer));objectURLs.forEach(url=>win.URL.revokeObjectURL(url));objectURLs.clear();cleanupTimers.clear();try{video.pause();}catch{}view.dataset.studioMotion='off';}
  };
}
