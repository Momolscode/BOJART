"use client";

import { useEffect, useRef, useState } from "react";
import Dialog from "./Dialog";
import BriefForm, { type Offer } from "./BriefForm";

type Work = { id: string; title: string; short: string; image: string; alt: string; category: string; description: string; details: string[]; source: string };

export const WORKS: Work[] = [
  {
    id: "baki", title: "Baki", short: "Le caractère, en volume.", image: "baki-hero.webp",
    alt: "Figurine peinte de Baki, posture de combat et socle sculpté aux nuances mauves, photographiée sur fond clair.",
    category: "FIGURINE · PEINTURE",
    description: "La tension d’une posture. Les nuances de la peau. Un socle qui prolonge le mouvement. Cette pièce donne à voir le travail de peinture et la présence d’un personnage dans l’espace.",
    details: ["Vue de la pièce finie et de son socle", "Geste de mise en peinture documenté dans les publications de l’atelier", "Photographie extraite d’une publication BOJ.ART"],
    source: "https://www.tiktok.com/@boj.art/video/7480904142689635607",
  },
  {
    id: "dragon-ball", title: "Composition Dragon Ball", short: "Un univers. Une scène.", image: "dragon.webp",
    alt: "Composition peinte Dragon Ball : personnages superposés et rochers sur un socle circulaire noir.",
    category: "COMPOSITION · PEINTURE",
    description: "Plusieurs silhouettes, une scène commune. Le regard circule entre les visages, les reliefs et le socle pour retrouver l’énergie de cet univers.",
    details: ["Composition présentée sur son socle", "Contraste entre personnages peints et texture des rochers", "Photographie extraite d’une publication BOJ.ART"],
    source: "https://www.tiktok.com/@boj.art/video/7480904142689635607",
  },
  {
    id: "trone", title: "Pièce sur trône", short: "Le détail impose le ton.", image: "throne.webp",
    alt: "Personnage peint assis sur un trône entouré de textures osseuses et de têtes sculptées, sur un socle noir.",
    category: "FIGURINE · DÉCOR",
    description: "Une silhouette calme au milieu d’un décor dense. Les surfaces sombres, les touches de rouge et les textures osseuses installent toute l’atmosphère de la pièce.",
    details: ["Vue frontale de la figurine et du décor", "Matières peintes et reliefs contrastés", "Photographie extraite d’une publication BOJ.ART"],
    source: "https://www.tiktok.com/@boj.art/video/7480904142689635607",
  },
];

const OFFERS: { id: Offer; number: string; title: string; subtitle: string; copy: string; points: string[]; cta: string }[] = [
  { id: "artwork", number: "01", title: "Œuvres & éditions", subtitle: "Pour les pièces qui vous parlent.", copy: "Une réalisation vous a marqué ? Demandez sa disponibilité ou parlez-nous d’une pièce à venir. Les dimensions, la finition et les conditions sont confirmées dans la proposition de l’atelier.", points: ["Disponibilité à confirmer", "Finition et présentation", "Projet de collection"], cta: "Parler d’une pièce" },
  { id: "custom", number: "02", title: "Votre pièce, sur mesure", subtitle: "Un objet qui commence avec vous.", copy: "Une idée, une référence ou un modèle 3D : partagez votre point de départ. Nous préparons l’étude de la forme, de l’échelle et de la finition pour construire une proposition adaptée.", points: ["Figurine, objet ou socle", "À partir d’une idée ou d’un fichier", "Faisabilité étudiée avant devis"], cta: "Décrire mon idée" },
  { id: "prototype", number: "03", title: "Prototypes & usages", subtitle: "Explorer ce qu’une pièce peut faire.", copy: "Un boîtier, un assemblage, un support ou un projet robotique : exposez le besoin réel et les contraintes. Les procédés, les essais et les limites seront étudiés avant engagement.", points: ["Besoin et contraintes d’usage", "Dimensions et assemblages", "Projet soumis à étude"], cta: "Présenter mon besoin" },
];

const FAQ = [
  ["Je n’ai pas de fichier 3D. Peut-on commencer ?", "Oui, vous pouvez commencer par une idée, une description et des liens de référence. Indiquez ce que la pièce doit représenter ou accomplir. La modélisation nécessaire et sa faisabilité seront précisées dans l’étude."],
  ["Les œuvres présentées sont-elles à vendre ?", "Les images de cette page constituent un portfolio. Elles ne sont pas un inventaire de vente. Utilisez le bouton d’intérêt d’une pièce pour demander sa disponibilité ou discuter d’un projet ; une proposition écrite précisera ce qui peut être réalisé."],
  ["Comment le prix et le délai sont-ils définis ?", "Ils dépendent notamment du modèle, de l’échelle, de la quantité, du procédé, de la matière et du niveau de finition. Le brief recueille votre enveloppe et votre échéance souhaitées. Seule la proposition de l’atelier fixe le prix, le périmètre et le calendrier retenus."],
  ["Peut-on reproduire un personnage ou un modèle existant ?", "Chaque demande est étudiée en fonction des modèles et des droits disponibles. Présenter une référence aide à comprendre votre intention ; cela ne garantit pas qu’une reproduction pourra être proposée."],
  ["Comment transmettre un STL ou des références ?", "Le brief accepte des liens HTTPS vers vos références et permet d’indiquer qu’un fichier 3D est prêt. Il ne téléverse pas encore de STL. Conservez votre fichier : le mode de transmission sera défini lors de l’échange avec l’atelier."],
  ["Comment se passe la remise de la pièce ?", "Précisez votre besoin dans le brief. Le conditionnement, une éventuelle expédition, ses frais et les modalités de remise sont à définir dans la proposition, selon la pièce et sa destination."],
];

export function Arrow({ diagonal = false }: { diagonal?: boolean }) {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d={diagonal ? "M6 18 18 6M6 6h12v12" : "M4 12h15m-6-6 6 6-6 6"} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

export default function Storefront() {
  const [hero, setHero] = useState(0);
  const [work, setWork] = useState<Work | null>(null);
  const [offer, setOffer] = useState<Offer>("custom");
  const [brief, setBrief] = useState<{ offer: Offer; artworkId?: string } | null>(null);
  const [film, setFilm] = useState(false);
  const [menu, setMenu] = useState(false);
  const [motion, setMotion] = useState(true);
  const [hasPending, setHasPending] = useState(false);
  const page = useRef<HTMLDivElement>(null);
  const chosen = WORKS[hero];
  const activeOffer = OFFERS.find((item) => item.id === offer)!;

  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (mq?.matches) setMotion(false);
    const changed = () => setMotion(!mq?.matches);
    mq?.addEventListener?.("change", changed);
    try { setHasPending(!!sessionStorage.getItem("bojart.pending-inquiry.v1")); } catch { /* Storage may be unavailable. */ }
    const entry = new URLSearchParams(window.location.search);
    const entryOffer = entry.get("brief");
    const entryPiece = entry.get("piece");
    if (entryOffer === "artwork" || entryOffer === "custom" || entryOffer === "prototype") {
      setBrief({ offer: entryOffer, ...(entryPiece && WORKS.some((item) => item.id === entryPiece) ? { artworkId: entryPiece } : {}) });
    }
    return () => mq?.removeEventListener?.("change", changed);
  }, []);

  useEffect(() => {
    if (!page.current || typeof IntersectionObserver === "undefined" || !motion) return;
    const nodes = [...page.current.querySelectorAll<HTMLElement>("[data-reveal]")];
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) if (entry.isIntersecting) { entry.target.classList.add("boj-is-visible"); observer.unobserve(entry.target); }
    }, { threshold: 0.08, rootMargin: "0px 0px 30px 0px" });
    for (const node of nodes) { node.classList.add("boj-reveal-ready"); observer.observe(node); }
    return () => { observer.disconnect(); nodes.forEach((node) => node.classList.remove("boj-reveal-ready")); };
  }, [motion]);

  function openBrief(next: Offer = "custom", artworkId?: string) { setMenu(false); setWork(null); setBrief({ offer: next, artworkId }); }
  function closeBrief() { setBrief(null); try { setHasPending(!!sessionStorage.getItem("bojart.pending-inquiry.v1")); } catch { setHasPending(false); } }

  return <div ref={page} className="boj-site" data-motion={motion ? "full" : "reduced"}>
    <a className="boj-skip" href="#contenu">Aller au contenu</a>
    <header className="boj-header">
      <a href="#accueil" className="boj-brand" aria-label="BOJ.ART — accueil">
        <img src="/assets/logo.webp" width="44" height="50" alt="" />
        <span>BOJ.ART<small>ATELIER DE CRÉATION</small></span>
      </a>
      <nav aria-label="Navigation principale" className={menu ? "boj-navigation is-open" : "boj-navigation"}>
        <a href="#realisations" onClick={() => setMenu(false)}>Réalisations</a>
        <a href="#possibles" onClick={() => setMenu(false)}>Votre projet</a>
        <a href="#atelier" onClick={() => setMenu(false)}>L’atelier</a>
      </nav>
      <div className="boj-header-actions">
        <button className="boj-nav-cta" onClick={() => openBrief()}>Parlons de votre idée <Arrow diagonal /></button>
        <button className="boj-menu-toggle" aria-label={menu ? "Fermer le menu" : "Ouvrir le menu"} aria-expanded={menu} onClick={() => setMenu(!menu)}><span /><span /></button>
      </div>
    </header>

    <main id="contenu">
      <section className="boj-hero" id="accueil" aria-labelledby="hero-title">
        <div className="boj-hero-copy">
          <p className="boj-eyebrow"><span className="boj-mark" /> LE VOLUME. LE GESTE. LA SIGNATURE.</p>
          <h1 id="hero-title">L’IMAGINAIRE.<br /><span>PREND FORME.</span></h1>
          <p className="boj-hero-description">Des univers à collectionner.<br />Des pièces à imaginer ensemble.<br />Votre prochaine idée commence ici.</p>
          <div className="boj-hero-actions">
            <button className="boj-button boj-button-primary" onClick={() => openBrief()}>Décrire mon projet <Arrow diagonal /></button>
            <a className="boj-text-link" href="#realisations">Explorer les réalisations <Arrow /></a>
          </div>
          {hasPending && <button className="boj-pending-link" onClick={() => openBrief()}>Reprendre ma demande en attente de confirmation <Arrow /></button>}
          <div className="boj-hero-index"><span>FIGURINES & ŒUVRES</span><span>SUR MESURE</span><span>PROTOTYPES SUR ÉTUDE</span></div>
        </div>
        <div className="boj-hero-art">
          <div className="boj-art-topline"><span>REGARD D’ATELIER</span><span>0{hero + 1} / 03</span></div>
          <button className="boj-hero-image-button" onClick={() => setWork(chosen)} aria-label={`Explorer ${chosen.title}`}>
            <img key={chosen.id} className="boj-hero-image" src={`/assets/${chosen.image}`} width="576" height="610" alt={chosen.alt} fetchPriority="high" />
            <span className="boj-image-open"><Arrow diagonal /></span>
          </button>
          <div className="boj-art-caption" aria-live="polite" aria-atomic="true"><div><p>{chosen.category}</p><h2>{chosen.title}</h2></div><span>PIÈCE DE PORTFOLIO</span></div>
          <div className="boj-art-selector" aria-label="Choisir une œuvre à découvrir">{WORKS.map((item, index) => <button key={item.id} onClick={() => setHero(index)} aria-pressed={hero === index}><span>0{index + 1}</span><span>{index === 1 ? "Dragon Ball" : item.title}</span><i aria-hidden="true" /></button>)}</div>
        </div>
        <a href="#realisations" className="boj-scroll-cue" aria-label="Descendre vers les réalisations"><span>POURSUIVRE LA VISITE</span><Arrow /></a>
      </section>

      <div className="boj-manifesto-line" aria-hidden="true"><span>UNE IDÉE.</span><i>✳</i><span>DU RELIEF.</span><i>✳</i><span>DU CARACTÈRE.</span><i>✳</i><span>BOJ.ART</span></div>

      <section className="boj-works boj-section" id="realisations" aria-labelledby="works-title">
        <div className="boj-section-heading" data-reveal><p className="boj-eyebrow"><span>01 /</span> RÉALISATIONS</p><div><h2 id="works-title">DES UNIVERS.<br /><em>UNE PRÉSENCE.</em></h2><p>Personnages, compositions, textures.<br />Un aperçu de l’univers visuel de BOJ.ART,<br />à travers ses pièces et ses publications.</p></div></div>
        <div className="boj-work-grid">{WORKS.map((item, index) => <article className={`boj-work boj-work-${index + 1}`} key={item.id} data-reveal>
          <button className="boj-work-image" onClick={() => setWork(item)} aria-label={`Voir la réalisation ${item.title}`}><img src={`/assets/${item.image}`} alt={item.alt} width="576" height="610" loading="lazy" /><span className="boj-work-explore">Explorer la pièce <Arrow diagonal /></span><span className="boj-work-number">0{index + 1}</span></button>
          <div className="boj-work-caption"><div><p>{item.category}</p><h3><button onClick={() => setWork(item)}>{item.title}</button></h3><span>{item.short}</span></div><button className="boj-circle-button" aria-label={`En savoir plus sur ${item.title}`} onClick={() => setWork(item)}><Arrow diagonal /></button></div>
        </article>)}</div>
        <div className="boj-gallery-footer"><p>Ces réalisations forment notre portfolio.<br />La disponibilité d’une pièce se confirme avec l’atelier.</p><a className="boj-text-link" href="https://www.tiktok.com/@boj.art" target="_blank" rel="noopener noreferrer">La suite sur TikTok <Arrow diagonal /></a></div>
      </section>

      <section className="boj-offers boj-section" id="possibles" aria-labelledby="offers-title">
        <div className="boj-section-heading" data-reveal><p className="boj-eyebrow"><span>02 /</span> LE CHAMP DES POSSIBLES</p><div><h2 id="offers-title">VOTRE IDÉE.<br /><em>SON POINT DE DÉPART.</em></h2><p>Vous venez avec une envie ou un besoin.<br />Nous commençons par les bonnes questions.</p></div></div>
        <div className="boj-offer-layout" data-reveal>
          <div className="boj-offer-tabs" role="tablist" aria-label="Explorer les types de projets">{OFFERS.map((item) => <button key={item.id} role="tab" id={`offer-tab-${item.id}`} aria-controls={`offer-panel-${item.id}`} aria-selected={offer === item.id} tabIndex={offer === item.id ? 0 : -1} onClick={() => setOffer(item.id)} onKeyDown={(event) => { const index = OFFERS.findIndex((entry) => entry.id === offer); let next = index; if (event.key === "ArrowDown" || event.key === "ArrowRight") next = (index + 1) % OFFERS.length; else if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = (index + OFFERS.length - 1) % OFFERS.length; else if (event.key === "Home") next = 0; else if (event.key === "End") next = OFFERS.length - 1; else return; event.preventDefault(); setOffer(OFFERS[next].id); document.getElementById(`offer-tab-${OFFERS[next].id}`)?.focus(); }}><span>{item.number}</span><strong>{item.title}</strong><Arrow diagonal /></button>)}</div>
          <div className="boj-offer-detail" role="tabpanel" id={`offer-panel-${offer}`} aria-labelledby={`offer-tab-${offer}`} tabIndex={0} key={offer}>
            <span className="boj-offer-watermark" aria-hidden="true">{activeOffer.number}</span><p className="boj-eyebrow">{offer === "prototype" ? "FAISABILITÉ À ÉTUDIER" : "COMMENÇONS PAR VOTRE BRIEF"}</p><h3>{activeOffer.subtitle}</h3><p>{activeOffer.copy}</p><ul>{activeOffer.points.map((point) => <li key={point}><span aria-hidden="true">+</span>{point}</li>)}</ul><button className="boj-button boj-button-dark" onClick={() => openBrief(activeOffer.id)}>{activeOffer.cta}<Arrow diagonal /></button>
          </div>
        </div>
      </section>

      <section className="boj-atelier boj-section" id="atelier" aria-labelledby="atelier-title">
        <div className="boj-atelier-visual" data-reveal><img src="/assets/atelier.webp" alt="Dans l’atelier BOJ.ART, une main au pinceau travaille la peinture d’une pièce tenue avec un gant bleu." width="576" height="324" loading="lazy" /><button className="boj-film-trigger" onClick={() => setFilm(true)}><span className="boj-play-icon" aria-hidden="true">▶</span><span>REGARDER LE FILM<small>Le détail. Le geste. L’œuvre. · 23 s · sans son</small></span><Arrow diagonal /></button><p className="boj-visual-credit">Geste réel de mise en peinture · images BOJ.ART</p></div>
        <div className="boj-atelier-copy" data-reveal><p className="boj-eyebrow"><span>03 /</span> DANS L’ATELIER</p><h2 id="atelier-title">LE GESTE<br /><em>FAIT LA<br />DIFFÉRENCE.</em></h2><p>Un relief prend la lumière. Une nuance donne du caractère. Une pièce se révèle dans les détails.</p><p>Les publications de BOJ.ART montrent cette rencontre entre le volume et le travail de peinture. C’est ce regard que nous voulons partager avec chaque projet.</p><a className="boj-text-link" href="https://www.tiktok.com/@boj.art/video/7464268707989114134" target="_blank" rel="noopener noreferrer">Voir le geste dans la publication originale <Arrow diagonal /></a></div>
      </section>

      <section className="boj-process boj-section" aria-labelledby="process-title">
        <div className="boj-section-heading" data-reveal><p className="boj-eyebrow"><span>04 /</span> DE L’IDÉE À L’ATELIER</p><div><h2 id="process-title">FAISONS LES CHOSES<br /><em>DANS LE BON ORDRE.</em></h2></div></div>
        <ol className="boj-process-grid">{[
          ["On pose l’idée.", "L’univers, l’usage, les dimensions et votre point de départ. Le brief nous aide à comprendre ce qui compte."],
          ["On étudie la pièce.", "Modèle, matière, assemblages, finition et contraintes : la faisabilité détermine la proposition."],
          ["On précise l’accord.", "Périmètre, prix, calendrier et modalités de remise sont définis avant tout lancement."],
          ["Le projet prend forme.", "Les étapes de réalisation et de contrôle suivent le périmètre accepté, jusqu’à la remise de la pièce."],
        ].map(([title, copy], index) => <li key={title} data-reveal><span className="boj-process-number">0{index + 1}</span><h3>{title}</h3><p>{copy}</p></li>)}</ol>
      </section>

      <section className="boj-faq boj-section" id="questions" aria-labelledby="faq-title"><div data-reveal><p className="boj-eyebrow"><span>05 /</span> AVANT DE SE LANCER</p><h2 id="faq-title">LES BONNES<br /><em>QUESTIONS.</em></h2><button className="boj-text-link" onClick={() => openBrief()}>Parler de mon cas <Arrow diagonal /></button></div><div className="boj-faq-list" data-reveal>{FAQ.map(([question, answer], index) => <details key={question}><summary><span className="boj-faq-number">0{index + 1}</span><span>{question}</span><span className="boj-faq-plus" aria-hidden="true">+</span></summary><p>{answer}</p></details>)}</div></section>

      <section className="boj-project-cta" id="projet" aria-labelledby="project-title"><div className="boj-cta-copy" data-reveal><p className="boj-eyebrow">LE PROCHAIN PROJET POURRAIT ÊTRE LE VÔTRE.</p><h2 id="project-title">VOUS L’AVEZ<br />EN TÊTE.<br /><span>ON EN PARLE ?</span></h2><p>Décrivez votre idée. Ajoutez vos contraintes.<br />Commencez une demande de devis sans paiement.</p><button className="boj-button boj-button-ivory" onClick={() => openBrief()}>Créer mon brief <Arrow diagonal /></button></div><div className="boj-cta-signature"><img src="/assets/logo.webp" alt="Emblème original BOJ.ART" width="464" height="524" loading="lazy" /><span>DU CARACTÈRE.<br />JUSQU’À LA SIGNATURE.</span></div></section>
    </main>

    <footer className="boj-footer"><div className="boj-footer-top"><a href="#accueil" className="boj-footer-wordmark">BOJ.ART<span>ATELIER DE CRÉATION</span></a><p>Des idées qui prennent forme.<br />Des pièces qui ont du caractère.</p><a className="boj-text-link" href="https://www.tiktok.com/@boj.art" target="_blank" rel="noopener noreferrer">@boj.art <Arrow diagonal /></a></div><div className="boj-footer-bottom"><span>BOJ.ART · Les œuvres et leurs univers gardent leurs auteurs.</span><nav aria-label="Informations"><a href="/confidentialite">Confidentialité</a><a href="/mentions">Mentions légales</a><button onClick={() => setMotion(!motion)} aria-pressed={!motion}>Mouvement : {motion ? "activé" : "réduit"}</button></nav></div></footer>

    {work && <Dialog labelledBy="work-title" onClose={() => setWork(null)} className="boj-work-dialog"><div className="boj-work-dialog-image"><img src={`/assets/${work.image}`} alt={work.alt} width="576" height="610" /></div><div className="boj-work-dialog-copy"><p className="boj-eyebrow">REGARD SUR UNE RÉALISATION</p><h2 id="work-title">{work.title}</h2><p>{work.description}</p><ul>{work.details.map((detail) => <li key={detail}>{detail}</li>)}</ul><div className="boj-portfolio-note"><strong>Une réalisation de portfolio.</strong><p>Sa présence ici ne confirme pas une disponibilité à la vente. Parlons de votre intérêt ou d’une idée personnelle.</p></div><button className="boj-button boj-button-primary" onClick={() => openBrief("artwork", work.id)}>Cette pièce m’intéresse <Arrow diagonal /></button><a className="boj-source-link" href={work.source} target="_blank" rel="noopener noreferrer">Voir la publication originale sur TikTok <Arrow diagonal /></a></div></Dialog>}
    {film && <Dialog labelledBy="film-title" onClose={() => setFilm(false)} className="boj-film-dialog"><div className="boj-film-heading"><p className="boj-eyebrow">UN FILM DE RÉFÉRENCE BOJ.ART</p><h2 id="film-title">DU DÉTAIL À L’ŒUVRE.</h2></div><video controls playsInline preload="metadata" poster="/assets/brand-film-poster.webp" src="/assets/brand-film-master.mp4" aria-label="Film silencieux de la pièce Baki : détails, mise en peinture, œuvre et emblème BOJ.ART" /><div className="boj-film-description"><p>Montage silencieux de 23 secondes, créé à partir de deux publications du projet Baki. Couleurs et geste d’origine conservés.</p><a href="https://www.tiktok.com/@boj.art/video/7467517355535404310" target="_blank" rel="noopener noreferrer">L’œuvre originale <Arrow diagonal /></a><a href="https://www.tiktok.com/@boj.art/video/7464268707989114134" target="_blank" rel="noopener noreferrer">Le travail de peinture <Arrow diagonal /></a></div></Dialog>}
    {brief && <BriefForm initialOffer={brief.offer} initialArtworkId={brief.artworkId} onClose={closeBrief} />}
  </div>;
}
