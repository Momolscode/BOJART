/**
 * BOJ.ART visual reference desk.
 * Sources are existing local assets; timing comes from atelier-motion-sources.json.
 * The palette and interface gestures are proposals, not sampled brand standards.
 * All display actions are resolved by the host's typed visual catalogue.
 */
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));

const sequences = [
  {name:'Baki',gesture:'L’œuvre entière',image:'baki-detail.webp',alt:'La figurine de Baki et son socle, photographiés dans l’atelier.',id:'7467517355535404310',source:'00:16 – 00:21',output:'00:00',start:0,span:25,position:'50% 50%'},
  {name:'Vegeta',gesture:'Tourner autour de la pièce',image:'archive/7331788287171988768.webp',alt:'Vegeta sur son socle, dans le décor manga de l’atelier.',id:'7331788287171988768',source:'00:01 – 00:06',output:'00:04,4',start:23.404,span:26.596,position:'50% 50%'},
  {name:'Sukuna',gesture:'La matière et le volume',image:'archive/7376602431603346721.webp',alt:'Sukuna sur son trône : référence du plan de rotation manuelle.',id:'7376602431603346721',source:'00:01 – 00:06',output:'00:09,1',start:48.404,span:26.596,position:'50% 50%'},
  {name:'Le geste',gesture:'Le travail au pinceau',image:'atelier.webp',alt:'Vue plongeante des mains de l’artiste pendant la mise en peinture.',id:'7464268707989114134',source:'00:20 – 00:25',output:'00:13,8',start:73.404,span:26.596,position:'50% 50%'}
];

const palette = [
  {name:'Charbon',hex:'#09090D',tone:'dark'},
  {name:'Ivoire',hex:'#F4F0ED',tone:'light'},
  {name:'Cramoisi',hex:'#F13A54',tone:'red'},
  {name:'Braise',hex:'#A91639',tone:'ember'}
];

export function renderSignatureView({esc=escapeHTML,icon=()=>''}={}) {
  return `<section class="signature-view" aria-labelledby="signature-title">
    <header class="signature-heading">
      <div><p class="signature-kicker"><span></span> BOJ.ART / LA SIGNATURE</p><h2 id="signature-title">LE GESTE.<br><em>L’ŒUVRE.</em></h2></div>
      <div class="signature-heading-note"><span class="signature-reference-count">04 <small>plans d’origine</small></span><p>Les références de l’artiste.<br>Un même langage sur les trois écrans.</p></div>
    </header>

    <div class="signature-hero">
      <section class="signature-brand-card" aria-label="Emblème BOJ.ART issu d’une publication originale">
        <div class="signature-brand-top"><span>LE SIGNE</span><span>01 / IDENTITÉ</span></div>
        <div class="signature-emblem"><img src="./assets/logo.webp" alt="Emblème BOJ.ART : personnage manga, éclats rouges et signature blanche au pinceau." loading="lazy"></div>
        <div class="signature-brand-caption"><strong>La signature d’origine.</strong><p>Emblème de la série Baki, conservé dans son cadre noir.</p><a class="signature-source-link" href="https://www.tiktok.com/@boj.art/video/7467517355535404310" target="_blank" rel="noopener noreferrer">Plan signature · 00:35 ${icon('arrowUp')}</a></div>
        <details class="signature-variants"><summary>Les variantes de l’archive <span aria-hidden="true">+</span></summary><div><img src="./assets/archive/7480904142689635607.webp" alt="Autre emblème publié dans le montage « Mon évolution en 5 années » : personnage aux cheveux orange et lettrage noir sur blanc." loading="lazy"><p>Le montage « Mon évolution en 5 années » présente un autre emblème. Chaque version garde sa source.<a class="signature-source-link" href="https://www.tiktok.com/@boj.art/video/7480904142689635607" target="_blank" rel="noopener noreferrer">Voir cette publication ${icon('arrowUp')}</a></p></div></details>
      </section>

      <section class="signature-film-card" aria-label="Montage de référence BOJ.ART">
        <div class="signature-film-head"><span>LE MOUVEMENT</span><span><i></i> ARCHIVES / 18,8 S</span></div>
        <div class="signature-film-screen"><video class="signature-film" src="./assets/atelier-motion.mp4" poster="./assets/atelier-motion-poster.webp" controls muted playsinline loop preload="metadata" aria-label="Lire le montage silencieux de Baki, Vegeta, Sukuna et du geste de peinture. La lecture démarre à votre demande."></video><span class="signature-film-mark" aria-hidden="true">BOJ.ART</span></div>
        <div class="signature-film-bottom"><div><h3>L’atelier en mouvement.</h3><p>Quatre plans authentiques. Couleurs des œuvres préservées.</p></div><button type="button" class="button button-red signature-present" data-action="visual-present" data-visual-id="film">${icon('screens')} Mettre en scène <span>03 ${icon('arrow')}</span></button></div>
      </section>
    </div>

    <section class="signature-sequence" aria-labelledby="signature-sequence-title">
      <div class="signature-section-heading"><div><p class="signature-kicker">LE FIL DU MONTAGE</p><h3 id="signature-sequence-title">De l’œuvre au geste.</h3></div><span>18,8 s <i>/</i> Fondus de 0,3 s</span></div>
      <div class="signature-timebar" aria-hidden="true">${sequences.map((sequence,index)=>`<i style="--sequence-start:${sequence.start}%;--sequence-span:${sequence.span}%;--sequence-tone:${1-index*.16}"></i>`).join('')}<span>00:00</span><span>00:18,8</span></div>
      <ol class="signature-sequence-grid">${sequences.map((sequence,index)=>`<li class="signature-sequence-card"><a href="https://www.tiktok.com/@boj.art/video/${esc(sequence.id)}" target="_blank" rel="noopener noreferrer" aria-label="Voir la publication source : ${esc(sequence.name)}."><div class="signature-sequence-image"><img src="./assets/${esc(sequence.image)}" alt="${esc(sequence.alt)}" loading="lazy" style="object-position:${sequence.position}"><span class="signature-sequence-number">0${index+1}</span><span class="signature-sequence-output">${esc(sequence.output)}</span><span class="signature-sequence-open" aria-hidden="true">${icon('arrowUp')}</span></div><div class="signature-sequence-caption"><h4>${esc(sequence.name)}</h4><p>${esc(sequence.gesture)}</p><span>Source <strong>${esc(sequence.source)}</strong></span></div></a></li>`).join('')}</ol>
      <p class="signature-sequence-note">Les vignettes identifient les publications ; les minutages « source » indiquent les passages du montage. Le dernier fondu rejoint le premier plan.</p>
    </section>

    <section class="signature-language" aria-labelledby="signature-language-title">
      <div class="signature-section-heading"><div><p class="signature-kicker">L’ADAPTATION POUR LE POSTE</p><h3 id="signature-language-title">Une identité, trois écrans.</h3></div><span>Proposition d’interface</span></div>
      <div class="signature-language-grid">
        <section class="signature-palette-card"><span class="signature-card-overline">01 / COULEURS</span><h4>Le noir porte l’œuvre.<br>Le rouge guide le geste.</h4><div class="signature-swatches">${palette.map(color=>`<div><span class="signature-swatch ${color.tone}" style="--swatch:${color.hex}"></span><strong>${color.name}</strong><small>${color.hex}</small></div>`).join('')}</div><p>Palette proposée pour l’interface. Les images conservent leurs couleurs d’origine.</p></section>
        <section class="signature-type-card"><span class="signature-card-overline">02 / HIÉRARCHIE</span><div class="signature-type-sample"><span>BOJ.ART</span><strong>UNE INTENTION.<br>TOUT L’ATELIER.</strong></div><div class="signature-type-detail"><span>Des titres francs.</span><span>Des commandes lisibles.</span><span>Le lettrage de l’artiste dans son emblème.</span></div></section>
        <section class="signature-motion-card"><span class="signature-card-overline">03 / MOUVEMENT</span><h4>Le mouvement suit l’action.</h4><div class="signature-motion-demos" aria-label="Études d’animation : survolez ou placez le focus sur un exemple pour le voir"><button type="button" class="signature-motion-demo signature-demo-reveal" aria-label="Prévisualiser la révélation diagonale"><span class="signature-demo-stage"><span class="signature-demo-art">BOJ.ART</span><i class="signature-demo-slash"></i></span><strong>Révéler</strong><small>Le visuel</small></button><button type="button" class="signature-motion-demo signature-demo-open" aria-label="Prévisualiser l’ouverture du panneau"><span class="signature-demo-stage"><i class="signature-demo-panel"><b></b><b></b><b></b></i></span><strong>Ouvrir</strong><small>L’opération</small></button><button type="button" class="signature-motion-demo signature-demo-confirm" aria-label="Prévisualiser la confirmation d’affichage"><span class="signature-demo-stage"><i class="signature-demo-screen">03</i><i class="signature-demo-check">✓</i></span><strong>Confirmer</strong><small>L’affichage</small></button></div><p>Des gestes courts à la demande. La réduction des animations est respectée.</p></section>
      </div>
    </section>

    <footer class="signature-footer"><div><img src="./assets/logo.webp" alt="" loading="lazy"><p><strong>L’œuvre reste au centre.</strong><span>Retrouver l’atelier sur l’écran de création.</span></p></div><button type="button" class="button signature-present" data-action="visual-present" data-visual-id="art">Voir l’œuvre <span>03 ${icon('arrowUp')}</span></button></footer>
  </section>`;
}
