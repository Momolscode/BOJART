import type { Metadata } from "next";
import "../legal.css";
export const metadata: Metadata = { title: "Mentions du site" };
export default function Mentions(){return <main className="legal-shell">
  <nav className="legal-nav" aria-label="Navigation"><a href="/" aria-label="BOJ.ART, accueil"><img src="/assets/logo.webp" alt="BOJ.ART" width="72" height="72"/></a><a href="/#projet">Parlons de votre projet ↗</a></nav>
  <p className="legal-kicker">Informations du site</p><h1>Mentions légales.</h1>
  <div className="legal-note"><strong>Vitrine en préparation.</strong> L’identité juridique et les coordonnées de l’éditeur doivent être renseignées avant l’ouverture au public. Cette page ne présente pas ces informations comme vérifiées.</div>
  <h2>Éditeur et publication</h2><dl>
    <div><dt>Marque présentée</dt><dd>BOJ.ART</dd></div>
    <div><dt>Identité de l’éditeur</dt><dd>Nom ou dénomination, forme juridique et immatriculation à renseigner.</dd></div>
    <div><dt>Coordonnées</dt><dd>Adresse professionnelle, adresse électronique et téléphone de BOJ.ART à renseigner.</dd></div>
    <div><dt>Publication</dt><dd>Responsable de publication à renseigner.</dd></div>
    <div><dt>Hébergement</dt><dd>Vitrine publiée avec Sites. Identité juridique et coordonnées contractuelles de l’hébergeur à compléter avec les informations du contrat.</dd></div>
  </dl>
  <h2>Œuvres et images</h2><p>Les images et films du portfolio proviennent des publications BOJ.ART documentées. Les personnages et univers représentés peuvent relever des droits de leurs titulaires respectifs. Leur présentation comme référence ne constitue pas une annonce de disponibilité à la vente ni une autorisation de reproduction.</p>
  <p>Les liens vers les publications originales sont accessibles depuis les références du portfolio. Pour un projet sur mesure, la provenance des modèles, images et fichiers sera examinée avec le brief.</p>
  <h2>Demandes et devis</h2><p>Le formulaire permet de soumettre un projet à étudier. Son enregistrement n’est ni un devis accepté, ni une commande, ni une réservation de créneau. Un devis précis dépend notamment des dimensions, de la géométrie, de la matière, de la finition, des quantités et des conditions de livraison.</p>
  <p>Le site ne propose pas de paiement en ligne à ce stade. Les conditions de vente, les modalités d’accord et les informations applicables au service retenu devront accompagner la proposition commerciale.</p>
  <h2>Données personnelles</h2><p>Les informations sur le formulaire, les destinataires, la conservation et les droits figurent dans la <a href="/confidentialite">notice de confidentialité</a>.</p>
  <a className="legal-back" href="/">Retour à BOJ.ART</a><footer className="legal-footer"><span>BOJ.ART</span><a href="/confidentialite">Confidentialité</a><a href="https://www.tiktok.com/@boj.art" target="_blank" rel="noreferrer">TikTok officiel</a></footer>
</main>}
