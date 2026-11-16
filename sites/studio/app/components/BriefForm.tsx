"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Dialog from "./Dialog";
import { isPublicReference, normalizeInquiry, UUID_RE } from "../../lib/acquisition-core.mjs";

export type Offer = "artwork" | "custom" | "prototype";
type ModelStatus = "idea" | "reference" | "file_ready";
type Budget = "undecided" | "under_250" | "250_750" | "750_1500" | "1500_3000" | "over_3000";
type Draft = { offer: Offer; description: string; intendedUse: string; widthMm: string; heightMm: string; depthMm: string; quantity: string; budgetRange: Budget; deadline: string; modelStatus: ModelStatus; references: string; name: string; email: string; phone: string; privacyAcknowledged: boolean; website: string; artworkId?: string };
type Inquiry = { format: "bojart.inquiry.v1"; requestId: string; offer: Offer; name: string; email: string; phone?: string; description: string; intendedUse?: string; dimensions?: { widthMm?: number; heightMm?: number; depthMm?: number }; quantity: number; budgetRange: Budget; deadline?: string; modelStatus: ModelStatus; referenceURLs: string[]; artworkId?: string; source: { entryPath: string; utmSource?: string; utmMedium?: string; utmCampaign?: string }; privacyAcknowledged: true; website: string };
type Receipt = { format: "bojart.inquiry.receipt.v1"; requestId: string; reference: string; createdAt: string; status: "new" };
type Pending = { payload: Inquiry; savedAt: number; uncertain?: boolean; resolution?: "deleted" };
type Recovery = { requestId: string | null; reason: "expired" | "unreadable"; recordedAt: number };
type Errors = Record<string, string>;
type Reply = { ok: boolean | null; token?: string; receipt: Record<string, unknown>; error: { message?: string; code?: string; fields: Record<string, unknown> } };

function record(value: unknown): Record<string, unknown> { return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
function reply(value: unknown): Reply {
  const outer = record(value); const error = record(outer.error);
  return { ok: outer.ok === true ? true : outer.ok === false ? false : null, ...(typeof outer.token === "string" ? { token: outer.token } : {}), receipt: record(outer.receipt), error: { ...(typeof error.message === "string" ? { message: error.message.slice(0, 1200) } : {}), ...(typeof error.code === "string" ? { code: error.code } : {}), fields: record(error.fields) } };
}

const PENDING_KEY = "bojart.pending-inquiry.v1";
const RECOVERY_KEY = "bojart.pending-recovery.v1";
const OFFER_LABELS: Record<Offer, string> = { artwork: "Œuvre & édition", custom: "Pièce sur mesure", prototype: "Prototype & usage" };
const ARTWORK_LABELS: Record<string, string> = { baki: "Baki", "dragon-ball": "Composition Dragon Ball", trone: "Pièce sur trône" };
const BUDGETS: { value: Budget; label: string }[] = [
  { value: "undecided", label: "À définir ensemble" }, { value: "under_250", label: "Moins de 250 €" }, { value: "250_750", label: "250 à 750 €" }, { value: "750_1500", label: "750 à 1 500 €" }, { value: "1500_3000", label: "1 500 à 3 000 €" }, { value: "over_3000", label: "Plus de 3 000 €" },
];
const MODEL_LABELS: Record<ModelStatus, string> = { idea: "Une idée à développer", reference: "Des références visuelles", file_ready: "Un fichier 3D déjà prêt" };

function blankDraft(offer: Offer, artworkId?: string): Draft {
  return { offer, artworkId, description: "", intendedUse: "", widthMm: "", heightMm: "", depthMm: "", quantity: "1", budgetRange: "undecided", deadline: "", modelStatus: "idea", references: "", name: "", email: "", phone: "", privacyAcknowledged: false, website: "" };
}

export function validateBriefStep(draft: Draft, step: number): Errors {
  const errors: Errors = {};
  if (step === 0) {
    if (!Object.hasOwn(OFFER_LABELS, draft.offer)) errors.offer = "Choisissez un type de projet.";
    if (draft.description.trim().length < 20 || draft.description.trim().length > 6000) errors.description = "Décrivez votre idée en 20 à 6 000 caractères.";
    if (!Object.hasOwn(MODEL_LABELS, draft.modelStatus)) errors.modelStatus = "Précisez votre point de départ.";
    if (draft.references.trim()) {
      const links = draft.references.split(/\n/).map((url) => url.trim()).filter(Boolean);
      if (links.length > 5) errors.references = "Ajoutez au maximum cinq liens, un par ligne.";
      else if (links.some((link) => !isPublicReference(link))) errors.references = "Utilisez des liens HTTPS publics, sans identifiants ni adresse réseau privée, un par ligne.";
    }
  }
  if (step === 1) {
    for (const field of ["widthMm", "heightMm", "depthMm"] as const) if (draft[field].trim() && (!Number.isFinite(Number(draft[field])) || Number(draft[field]) <= 0 || Number(draft[field]) > 100000)) errors[field] = "Indiquez une dimension positive en millimètres (100 000 maximum).";
    const quantity = Number(draft.quantity);
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 1000) errors.quantity = "Indiquez une quantité entière entre 1 et 1 000.";
    if (draft.intendedUse.length > 1000) errors.intendedUse = "Limitez les contraintes d’usage à 1 000 caractères.";
    if (draft.deadline) { const date = new Date(`${draft.deadline}T12:00:00Z`); if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.deadline) || !Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== draft.deadline || date.getUTCFullYear() < 1900 || date.getUTCFullYear() > 2100) errors.deadline = "Choisissez une date valide entre 1900 et 2100."; }
  }
  if (step === 2) {
    if (draft.name.trim().length < 2 || draft.name.trim().length > 100) errors.name = "Indiquez votre nom (2 à 100 caractères).";
    if (draft.email.trim().length > 254 || !/^[^\s@<>"(),:;\\\[\]]+@[^\s@<>"(),:;\\\[\]]+\.[^\s@<>"(),:;\\\[\]]+$/.test(draft.email.trim())) errors.email = "Vérifiez votre adresse e-mail.";
    if (draft.phone.trim() && (draft.phone.trim().length < 3 || draft.phone.trim().length > 40 || !/^[+\d().\s-]+$/.test(draft.phone.trim()))) errors.phone = "Utilisez 3 à 40 caractères : chiffres, espaces et signes de téléphone.";
    if (!draft.privacyAcknowledged) errors.privacyAcknowledged = "Veuillez lire et reconnaître les informations de confidentialité.";
  }
  return errors;
}

export function inquiryFromDraft(draft: Draft, requestId: string, location: { pathname: string; search: string }): Inquiry {
  const params = new URLSearchParams(location.search);
  const path = location.pathname.slice(0, 200);
  const source: Inquiry["source"] = { entryPath: /^\/(?!\/)[A-Za-z0-9/_-]*$/.test(path) ? path : "/" };
  for (const [query, field] of [["utm_source", "utmSource"], ["utm_medium", "utmMedium"], ["utm_campaign", "utmCampaign"]] as const) { const value = params.get(query)?.trim().slice(0, 80); if (value && /^[A-Za-z0-9_. -]+$/.test(value)) source[field] = value; }
  const dimensions: NonNullable<Inquiry["dimensions"]> = {};
  for (const field of ["widthMm", "heightMm", "depthMm"] as const) if (draft[field].trim()) dimensions[field] = Number(draft[field]);
  return {
    format: "bojart.inquiry.v1", requestId, offer: draft.offer, name: draft.name.trim(), email: draft.email.trim(),
    ...(draft.phone.trim() ? { phone: draft.phone.trim() } : {}), description: draft.description.trim(),
    ...(draft.intendedUse.trim() ? { intendedUse: draft.intendedUse.trim() } : {}), ...(Object.keys(dimensions).length ? { dimensions } : {}),
    quantity: Number(draft.quantity), budgetRange: draft.budgetRange, ...(draft.deadline ? { deadline: draft.deadline } : {}), modelStatus: draft.modelStatus,
    referenceURLs: draft.references.split(/\n/).map((url) => url.trim()).filter(Boolean), ...(draft.artworkId ? { artworkId: draft.artworkId } : {}),
    source, privacyAcknowledged: true, website: draft.website,
  };
}

function draftFromInquiry(payload: Inquiry): Draft {
  return { ...blankDraft(payload.offer, payload.artworkId), description: payload.description, intendedUse: payload.intendedUse || "", quantity: String(payload.quantity), widthMm: payload.dimensions?.widthMm == null ? "" : String(payload.dimensions.widthMm), heightMm: payload.dimensions?.heightMm == null ? "" : String(payload.dimensions.heightMm), depthMm: payload.dimensions?.depthMm == null ? "" : String(payload.dimensions.depthMm), budgetRange: payload.budgetRange, deadline: payload.deadline || "", modelStatus: payload.modelStatus, references: payload.referenceURLs.join("\n"), name: payload.name, email: payload.email, phone: payload.phone || "", privacyAcknowledged: payload.privacyAcknowledged, website: payload.website || "" };
}

function readPending(): { pending: Pending | null; recovery: Recovery | null } {
  const empty = { pending: null, recovery: null };
  function recover(reason: Recovery["reason"], id?: unknown) {
    const recovery: Recovery = { requestId: typeof id === "string" && UUID_RE.test(id) ? id : null, reason, recordedAt: Date.now() };
    try { sessionStorage.setItem(RECOVERY_KEY, JSON.stringify(recovery)); sessionStorage.removeItem(PENDING_KEY); } catch { /* The visible recovery state remains available in this tab. */ }
    return { pending: null, recovery };
  }
  try {
    const raw = sessionStorage.getItem(PENDING_KEY);
    if (!raw) {
      const previous = sessionStorage.getItem(RECOVERY_KEY);
      if (!previous || previous.length > 1000) return empty;
      let value: Recovery;
      try { value = JSON.parse(previous) as Recovery; } catch { return recover("unreadable"); }
      if (value && (value.requestId === null || (typeof value.requestId === "string" && UUID_RE.test(value.requestId))) && ["expired", "unreadable"].includes(value.reason) && Number.isFinite(value.recordedAt)) return { pending: null, recovery: { requestId: value.requestId, reason: value.reason, recordedAt: value.recordedAt } };
      return recover("unreadable");
    }
    if (raw.length > 28000) return recover("unreadable");
    let value: Pending;
    try { value = JSON.parse(raw) as Pending; } catch { return recover("unreadable"); }
    const data = value?.payload;
    if (!value || !Number.isFinite(value.savedAt) || value.savedAt > Date.now() + 60000) return recover("unreadable", data?.requestId);
    if (Date.now() - value.savedAt > 86400000) {
      if (value.uncertain === false) { sessionStorage.removeItem(PENDING_KEY); return empty; }
      return recover("expired", data?.requestId);
    }
    if (data?.format !== "bojart.inquiry.v1" || typeof data.requestId !== "string" || !UUID_RE.test(data.requestId) || !Object.hasOwn(OFFER_LABELS, data.offer) || typeof data.name !== "string" || typeof data.email !== "string" || typeof data.description !== "string" || !Object.hasOwn(MODEL_LABELS, data.modelStatus) || !BUDGETS.some((budget) => budget.value === data.budgetRange) || !Array.isArray(data.referenceURLs) || !data.referenceURLs.every((url) => typeof url === "string") || data.privacyAcknowledged !== true || (value.uncertain !== undefined && typeof value.uncertain !== "boolean") || (value.resolution !== undefined && value.resolution !== "deleted")) return recover("unreadable", data?.requestId);
    try {
      normalizeInquiry(data);
      const draft = draftFromInquiry(data);
      if ([0, 1, 2].some((step) => Object.keys(validateBriefStep(draft, step)).length)) return recover("unreadable", data.requestId);
    } catch { return recover("unreadable", data.requestId); }
    return { pending: value, recovery: null };
  } catch { return empty; }
}

function downloadText(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = name; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function recapText(draft: Draft, receipt: Receipt | null, pending: Pending | null) {
  return ["BOJ.ART — COPIE DE VOTRE BRIEF", receipt ? `Demande enregistrée : ${receipt.reference}\nReçu le : ${receipt.createdAt}` : "Copie personnelle — ce fichier ne confirme pas un envoi à l’atelier.", pending ? `Identifiant de tentative : ${pending.payload.requestId}\n${pending.resolution === "deleted" ? "Cette demande a été supprimée de la boîte de l’atelier. Cette copie personnelle reste distincte." : "Réception à vérifier : conservez cet identifiant si vous contactez l’atelier."}` : "", "", `Projet : ${OFFER_LABELS[draft.offer]}`, draft.artworkId ? `Référence portfolio : ${ARTWORK_LABELS[draft.artworkId] || draft.artworkId}` : "", `Idée : ${draft.description}`, `Point de départ : ${MODEL_LABELS[draft.modelStatus]}`, `Quantité : ${draft.quantity}`, `Dimensions souhaitées (L × H × P, mm) : ${draft.widthMm || "?"} × ${draft.heightMm || "?"} × ${draft.depthMm || "?"}`, `Usage / contraintes : ${draft.intendedUse || "À préciser"}`, `Enveloppe souhaitée : ${BUDGETS.find((entry) => entry.value === draft.budgetRange)?.label}`, `Échéance souhaitée : ${draft.deadline || "À définir"}`, `Références :\n${draft.references || "Aucune"}`, "", `Nom : ${draft.name}`, `E-mail : ${draft.email}`, `Téléphone : ${draft.phone || "Non renseigné"}`, "", "Ce brief ne constitue ni un devis, ni un paiement, ni une validation de faisabilité. Le prix, le calendrier et les conditions seront précisés dans la proposition de l’atelier."].filter((line) => line !== "").join("\n\n");
}

function Arrow() { return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>; }

export default function BriefForm({ initialOffer = "custom", initialArtworkId, onClose }: { initialOffer?: Offer; initialArtworkId?: string; onClose: () => void }) {
  const [draft, setDraft] = useState<Draft>(() => blankDraft(initialOffer, initialArtworkId));
  const [step, setStep] = useState(0);
  const [errors, setErrors] = useState<Errors>({});
  const [pending, setPending] = useState<Pending | null>(null);
  const [recovery, setRecovery] = useState<Recovery | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [downloaded, setDownloaded] = useState(false);
  const [storageWarning, setStorageWarning] = useState(false);
  const sendLock = useRef(false);
  const mounted = useRef(true);
  const heading = useRef<HTMLHeadingElement>(null);
  const content = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mounted.current = true;
    const restored = readPending();
    const previous = restored.pending;
    if (restored.recovery) { setRecovery(restored.recovery); setStep(3); }
    if (previous) { setPending(previous); setDraft(draftFromInquiry(previous.payload)); setStep(3); setMessage(previous.resolution === "deleted" ? "Cette demande a été supprimée. Elle ne sera pas recréée. Vous pouvez conserver votre copie ou commencer un nouveau brief." : "Une tentative attend une confirmation. Renvoyez cette même demande pour obtenir son reçu, sans la dupliquer."); }
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => { content.current?.scrollTo?.({ top: 0 }); heading.current?.focus(); }, [step, receipt, recovery]);

  function update<K extends keyof Draft>(key: K, value: Draft[K]) { if (pending) return; setDraft((current) => ({ ...current, [key]: value })); setErrors((current) => { const copy = { ...current }; delete copy[key]; return copy; }); setDownloaded(false); }
  function fieldError(name: string) { return errors[name] ? <span className="boj-field-error" id={`error-${name}`} role="status">{errors[name]}</span> : null; }
  function invalid(name: string) { return { "aria-invalid": !!errors[name], "aria-describedby": errors[name] ? `error-${name}` : undefined }; }
  function checkStep(next: number) { const found = validateBriefStep(draft, next); setErrors(found); if (Object.keys(found).length) { setTimeout(() => document.getElementById(`brief-${Object.keys(found)[0]}`)?.focus(), 0); return false; } return true; }
  function clearPending() { setPending(null); setStorageWarning(false); try { sessionStorage.removeItem(PENDING_KEY); } catch { /* The in-memory request is still cleared. */ } }
  function rememberPending(value: Pending) { setPending(value); try { sessionStorage.setItem(PENDING_KEY, JSON.stringify(value)); } catch { setStorageWarning(true); } }
  function copyBrief() { downloadText(`BOJ_ART_${receipt?.reference || "mon_brief"}.txt`, recovery ? `BOJ.ART — ANCIENNE TENTATIVE À VÉRIFIER\n\nIdentifiant : ${recovery.requestId || "Non récupérable"}\n\nCet avis ne confirme pas l’enregistrement. Le contenu du brief n’est plus disponible dans cet onglet. Vérifiez sa réception avec l’atelier avant d’envoyer une nouvelle demande.` : recapText(draft, receipt, pending)); setDownloaded(true); }
  function startNewBrief() { if (sendLock.current || (!recovery && pending?.resolution !== "deleted")) return; clearPending(); setRecovery(null); try { sessionStorage.removeItem(RECOVERY_KEY); } catch { /* The in-memory recovery state is cleared. */ } setDraft(blankDraft(initialOffer, initialArtworkId)); setStep(0); setErrors({}); setMessage(""); setDownloaded(false); }

  async function send() {
    if (sendLock.current || recovery || pending?.resolution === "deleted") return;
    for (let index = 0; index < 3; index++) if (Object.keys(validateBriefStep(draft, index)).length) { setStep(index); checkStep(index); return; }
    sendLock.current = true;
    setBusy(true); setMessage(""); setErrors({});
    let request = pending;
    const wasUncertain = !!request && request.uncertain !== false;
    let postStarted = false;
    try {
      if (!request) {
        if (!globalThis.crypto?.randomUUID) throw new Error("La connexion sécurisée requise pour envoyer le brief est indisponible. Conservez une copie de votre demande.");
        request = { payload: inquiryFromDraft(draft, crypto.randomUUID(), window.location), savedAt: Date.now(), uncertain: false };
        if (new TextEncoder().encode(JSON.stringify(request.payload)).byteLength > 24 * 1024) { setStep(0); throw new Error("Le brief complet est trop volumineux. Raccourcissez la description ou les liens, puis réessayez. Aucun envoi n’a été effectué."); }
        rememberPending(request);
      }
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 20000);
      try {
        const tokenResponse = await fetch("/api/briefs/token", { cache: "no-store", credentials: "same-origin", signal: controller.signal });
        const tokenData = reply(await tokenResponse.json());
        if (!tokenResponse.ok || tokenData.ok !== true || typeof tokenData.token !== "string") throw new Error(tokenData?.error?.message || "Le service de demande est momentanément indisponible. Vous pouvez conserver une copie de votre brief.");
        // Persist the uncertainty before POST can reach storage. Any subsequent
        // retry must retain this exact payload, even if that retry is rejected.
        request = { ...request, uncertain: true };
        rememberPending(request);
        postStarted = true;
        const response = await fetch("/api/briefs", { method: "POST", headers: { "Content-Type": "application/json", "X-BOJART-Form-Token": tokenData.token }, body: JSON.stringify(request.payload), credentials: "same-origin", signal: controller.signal });
        const result = reply(await response.json());
        const ack = result?.receipt;
        if (response.ok && result.ok === true && ack?.format === "bojart.inquiry.receipt.v1" && ack.requestId === request.payload.requestId && typeof ack.reference === "string" && /^BOJ-\d{8}-[A-F0-9]{12}$/.test(ack.reference) && typeof ack.createdAt === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(ack.createdAt) && Number.isFinite(Date.parse(ack.createdAt)) && new Date(ack.createdAt).toISOString() === ack.createdAt && ack.status === "new") {
          if (mounted.current) { setReceipt({ format: "bojart.inquiry.receipt.v1", requestId: request.payload.requestId, reference: ack.reference, createdAt: ack.createdAt, status: "new" }); clearPending(); setMessage(""); }
          return;
        }
        if (response.status === 410 && result.ok === false && result.error.code === "request_deleted") {
          if (mounted.current) rememberPending({ ...request, resolution: "deleted", uncertain: false });
          throw new Error("Cette demande a été supprimée. Elle ne sera pas recréée. Vous pouvez conserver votre copie ou commencer un nouveau brief.");
        }
        const rejectedBeforeWrite = result.ok === false && ((response.status === 400 && result.error.code === "invalid_json") || (response.status === 413 && result.error.code === "body_too_large") || (response.status === 422 && result.error.code === "validation_failed"));
        if (rejectedBeforeWrite && !wasUncertain) {
          if (mounted.current) {
            clearPending();
            if (Object.keys(result.error.fields).length) {
              const clean: Errors = {};
              for (const [key, value] of Object.entries(result.error.fields)) if (typeof value === "string") clean[key === "referenceURLs" ? "references" : key.replace(/^dimensions\./, "")] = value;
              setErrors(clean);
              const firstField = Object.keys(clean)[0];
              const fieldStep = ["offer", "description", "modelStatus", "references", "artworkId"].includes(firstField) ? 0 : ["dimensions", "widthMm", "heightMm", "depthMm", "quantity", "intendedUse", "deadline", "budgetRange"].includes(firstField) ? 1 : ["name", "email", "phone", "privacyAcknowledged"].includes(firstField) ? 2 : 3;
              setStep(fieldStep);
            }
          }
        }
        if (rejectedBeforeWrite && wasUncertain) throw new Error("Cette nouvelle tentative a été refusée, mais le résultat du premier envoi reste à vérifier. L’identifiant et le contenu sont conservés. Téléchargez la copie pour vérifier la réception avec l’atelier.");
        if (response.status === 409 && result?.error?.code === "idempotency_conflict") throw new Error("Cette référence d’envoi correspond déjà à un contenu différent. La tentative est conservée ; téléchargez votre récapitulatif pour vérifier la demande avec l’atelier.");
        throw new Error(result?.error?.message || "L’enregistrement n’a pas été confirmé. Réessayez avec cette même demande.");
      } finally { clearTimeout(timeout); }
    } catch (error) {
      if (mounted.current) {
        if (!postStarted && !wasUncertain) clearPending();
        setMessage(error instanceof Error && !["AbortError", "TypeError", "SyntaxError"].includes(error.name) ? error.message : "Nous n’avons pas reçu de confirmation. Vous pouvez renvoyer exactement cette demande : un envoi déjà enregistré renverra son reçu.");
      }
    } finally { sendLock.current = false; if (mounted.current) setBusy(false); }
  }

  function submit(event: FormEvent) { event.preventDefault(); if (step < 3) { if (checkStep(step)) setStep(step + 1); } else void send(); }
  const steps = ["Votre idée", "Les détails", "Vos coordonnées", "Le récapitulatif"];

  return <Dialog labelledBy="brief-title" onClose={onClose} className="boj-brief-dialog" busy={busy}>
    <aside className="boj-brief-aside"><a href="#accueil" onClick={(event) => { event.preventDefault(); if (!busy) onClose(); }} className="boj-brief-brand">BOJ.ART</a><p className="boj-eyebrow">UN PROJET COMMENCE PAR UN ÉCHANGE.</p><h2>{receipt ? <>L’IDÉE<br />EST<br /><em>POSÉE.</em></> : <>DONNONS<br />FORME À<br /><em>VOTRE IDÉE.</em></>}</h2><p>Une figurine. Une pièce personnelle. Un objet à inventer. Racontez-nous ce qui compte.</p><div className="boj-brief-aside-bottom"><img src="/assets/atelier.webp" width="576" height="324" alt="Le travail du pinceau dans l’atelier BOJ.ART" /><span>LE VOLUME. LE GESTE. LA SIGNATURE.</span></div></aside>
    <div className="boj-brief-main" ref={content}>
      {receipt ? <section className="boj-brief-success"><p className="boj-eyebrow">DEMANDE ENREGISTRÉE</p><div className="boj-success-symbol" aria-hidden="true">✓</div><h2 id="brief-title" ref={heading} tabIndex={-1}>VOTRE BRIEF<br />A SON NUMÉRO.</h2><p>Votre demande est enregistrée pour étude. Conservez cette référence avec votre récapitulatif.</p><div className="boj-receipt"><span>VOTRE RÉFÉRENCE</span><strong>{receipt.reference}</strong><small>{new Date(receipt.createdAt).toLocaleString("fr-FR", { timeZone: "Europe/Paris" })} · heure de Paris</small></div><p className="boj-fine-print">Le prix, la faisabilité, le calendrier et les modalités de remise restent à préciser dans la proposition de l’atelier. Aucun paiement n’a été demandé.</p><button type="button" className="boj-button boj-button-primary" onClick={copyBrief}>Télécharger mon récapitulatif <Arrow /></button>{downloaded && <p className="boj-download-note" role="status">Votre copie contient le brief et sa référence d’enregistrement.</p>}<button type="button" className="boj-text-link" onClick={onClose}>Retour aux réalisations <Arrow /></button></section> : recovery ? <section className="boj-brief-success"><p className="boj-eyebrow">UNE ANCIENNE TENTATIVE À VÉRIFIER</p><h2 id="brief-title" ref={heading} tabIndex={-1}>REPRENONS<br />SANS DOUBLON.</h2><p>{recovery.reason === "expired" ? "Une tentative d’envoi de plus de 24 heures n’a pas de confirmation conservée dans cet onglet." : "Une ancienne tentative ne peut plus être relue correctement dans cet onglet."} Le brief n’est plus conservé ici ; cela ne dit pas s’il a été reçu par l’atelier.</p>{recovery.requestId && <div className="boj-receipt"><span>IDENTIFIANT À CONSERVER POUR LA VÉRIFICATION</span><code style={{ display: "block", overflowWrap: "anywhere" }}>{recovery.requestId}</code></div>}<p className="boj-fine-print">Vérifiez la réception de cette demande avec l’atelier avant d’en saisir une autre. Commencer un nouveau brief ne supprime aucune demande déjà reçue.</p><button type="button" className="boj-text-link" onClick={copyBrief}>Conserver l’identifiant de tentative <Arrow /></button>{downloaded && <p className="boj-download-note" role="status">Avis de reprise préparé, sans coordonnées ni contenu du brief.</p>}<button type="button" className="boj-button boj-button-primary" onClick={startNewBrief}>J’ai vérifié : commencer un nouveau brief <Arrow /></button></section> : <>
        <div className="boj-brief-topline"><span>DEMANDE DE DEVIS · SANS PAIEMENT</span><span>0{step + 1} / 04</span></div>
        <ol className="boj-brief-progress" aria-label="Étapes du brief">{steps.map((title, index) => <li key={title} className={index < step ? "is-done" : index === step ? "is-current" : ""} aria-current={index === step ? "step" : undefined}><span>{index < step ? "✓" : index + 1}</span><small>{title}</small></li>)}</ol>
        <h2 id="brief-title" ref={heading} tabIndex={-1}>{["PARLEZ-NOUS DE L’IDÉE.", "PRÉCISONS LA PIÈCE.", "GARDONS LE CONTACT.", "TOUT COMMENCE ICI."][step]}</h2>
        <p className="boj-brief-intro">{["Quelques mots suffisent pour poser le point de départ.", "Ces repères aident l’étude. Ce qui n’est pas encore défini peut attendre.", "Les champs marqués * sont nécessaires pour traiter votre demande.", "Relisez votre demande avant de l’enregistrer auprès de l’atelier."][step]}</p>
        <form onSubmit={submit} noValidate>
          {step === 0 && <div className="boj-brief-step">
            <fieldset className="boj-choice-field"><legend>Quel type de projet ? *</legend><div className="boj-offer-choices">{(Object.keys(OFFER_LABELS) as Offer[]).map((value) => <label key={value} className={draft.offer === value ? "is-selected" : ""}><input type="radio" name="offer" value={value} checked={draft.offer === value} onChange={() => update("offer", value)} /><span>{OFFER_LABELS[value]}</span><i aria-hidden="true">↗</i></label>)}</div>{fieldError("offer")}</fieldset>
            {draft.artworkId && <div className="boj-selected-work"><span>Votre référence : <strong>{ARTWORK_LABELS[draft.artworkId] || draft.artworkId}</strong></span><button type="button" onClick={() => update("artworkId", undefined)} aria-label="Retirer cette référence de portfolio">×</button></div>}
            <label className="boj-field" htmlFor="brief-description"><span>Votre idée, avec vos mots *</span><textarea id="brief-description" value={draft.description} onChange={(event) => update("description", event.target.value)} minLength={20} maxLength={6000} rows={5} placeholder={draft.offer === "prototype" ? "À quoi doit servir la pièce ? Que souhaitez-vous essayer ou améliorer ?" : "L’univers, l’objet, la personne à qui il est destiné, ce qui vous tient à cœur…"} required {...invalid("description")} /><small>Au moins 20 caractères. Les dimensions viennent à l’étape suivante.</small>{fieldError("description")}</label>
            <fieldset className="boj-choice-field"><legend>Votre point de départ *</legend><div className="boj-model-choices">{(Object.keys(MODEL_LABELS) as ModelStatus[]).map((value) => <label key={value}><input type="radio" name="modelStatus" checked={draft.modelStatus === value} onChange={() => update("modelStatus", value)} /><span>{MODEL_LABELS[value]}</span></label>)}</div></fieldset>
            {draft.modelStatus === "file_ready" && <p className="boj-context-note">Conservez votre fichier 3D. Ce formulaire ne le téléverse pas ; son mode de transmission sera défini avec l’atelier.</p>}
            <label className="boj-field" htmlFor="brief-references"><span>Liens de référence <small>facultatif</small></span><textarea id="brief-references" value={draft.references} onChange={(event) => update("references", event.target.value)} maxLength={10000} rows={2} placeholder="https://…" {...invalid("references")} /><small>Jusqu’à 5 liens HTTPS publics, un par ligne. Évitez les documents confidentiels.</small>{fieldError("references")}</label>
          </div>}
          {step === 1 && <div className="boj-brief-step">
            <fieldset className="boj-choice-field"><legend>Dimensions souhaitées <small>facultatif · en millimètres</small></legend><div className="boj-dimensions">{([ ["widthMm", "Largeur"], ["heightMm", "Hauteur"], ["depthMm", "Profondeur"] ] as const).map(([field, label]) => <label className="boj-field" key={field} htmlFor={`brief-${field}`}><span>{label}</span><div className="boj-input-unit"><input id={`brief-${field}`} type="number" min="0.001" max="100000" step="any" inputMode="decimal" value={draft[field]} onChange={(event) => update(field, event.target.value)} placeholder="—" {...invalid(field)} /><span>mm</span></div>{fieldError(field)}</label>)}</div><p className="boj-field-help">100 mm = 10 cm · 1 000 mm = 1 m. Une dimension souhaitée ne confirme pas la faisabilité.</p></fieldset>
            <div className="boj-field-row"><label className="boj-field" htmlFor="brief-quantity"><span>Nombre de pièces *</span><input id="brief-quantity" type="number" min="1" max="1000" step="1" inputMode="numeric" value={draft.quantity} onChange={(event) => update("quantity", event.target.value)} required {...invalid("quantity")} />{fieldError("quantity")}</label><label className="boj-field" htmlFor="brief-deadline"><span>Date souhaitée <small>facultatif</small></span><input id="brief-deadline" type="date" value={draft.deadline} onChange={(event) => update("deadline", event.target.value)} {...invalid("deadline")} />{fieldError("deadline")}</label></div>
            <label className="boj-field" htmlFor="brief-budgetRange"><span>Votre enveloppe pour ce projet</span><select id="brief-budgetRange" value={draft.budgetRange} onChange={(event) => update("budgetRange", event.target.value as Budget)}>{BUDGETS.map((budget) => <option key={budget.value} value={budget.value}>{budget.label}</option>)}</select><small>Un repère pour comprendre votre projet, pas un tarif ni une estimation de l’atelier.</small></label>
            <label className="boj-field" htmlFor="brief-intendedUse"><span>Usage, finition ou contraintes <small>facultatif</small></span><textarea id="brief-intendedUse" value={draft.intendedUse} onChange={(event) => update("intendedUse", event.target.value)} maxLength={1000} rows={3} placeholder="Pièce d’exposition ou d’usage ? Finition peinte ? Assemblage, effort, extérieur, destination de livraison…" {...invalid("intendedUse")} />{fieldError("intendedUse")}</label>
          </div>}
          {step === 2 && <div className="boj-brief-step">
            <label className="boj-field" htmlFor="brief-name"><span>Votre nom *</span><input id="brief-name" name="name" autoComplete="name" value={draft.name} onChange={(event) => update("name", event.target.value)} maxLength={100} required {...invalid("name")} />{fieldError("name")}</label>
            <label className="boj-field" htmlFor="brief-email"><span>Votre e-mail *</span><input id="brief-email" name="email" type="email" autoComplete="email" value={draft.email} onChange={(event) => update("email", event.target.value)} maxLength={254} required {...invalid("email")} />{fieldError("email")}</label>
            <label className="boj-field" htmlFor="brief-phone"><span>Votre téléphone <small>facultatif</small></span><input id="brief-phone" name="tel" type="tel" autoComplete="tel" value={draft.phone} onChange={(event) => update("phone", event.target.value)} maxLength={40} {...invalid("phone")} />{fieldError("phone")}</label>
            <div className="boj-form-trap" aria-hidden="true"><label htmlFor="brief-website">Votre site<input id="brief-website" name="website" tabIndex={-1} autoComplete="off" value={draft.website} onChange={(event) => update("website", event.target.value)} /></label></div>
            <div className="boj-privacy-box"><p>Ces informations servent à examiner votre demande et préparer les échanges avant une éventuelle commande. Elles ne vous inscrivent à aucune newsletter.</p><label className="boj-check-label"><input id="brief-privacyAcknowledged" type="checkbox" checked={draft.privacyAcknowledged} onChange={(event) => update("privacyAcknowledged", event.target.checked)} required {...invalid("privacyAcknowledged")} /><span>J’ai lu les <a href="/confidentialite" target="_blank" rel="noopener noreferrer">informations de confidentialité</a> et compris l’usage de mes données pour cette demande. *</span></label>{fieldError("privacyAcknowledged")}</div>
          </div>}
          {step === 3 && <div className="boj-brief-step">
            <div className="boj-recap"><div className="boj-recap-label">VOTRE PROJET</div><h3>{OFFER_LABELS[draft.offer]}</h3>{draft.artworkId && <span className="boj-recap-artwork">Référence : {ARTWORK_LABELS[draft.artworkId] || draft.artworkId}</span>}<p className="boj-recap-description">{draft.description}</p><dl><div><dt>Point de départ</dt><dd>{MODEL_LABELS[draft.modelStatus]}</dd></div><div><dt>Quantité souhaitée</dt><dd>{draft.quantity}</dd></div><div><dt>Dimensions · L × H × P</dt><dd>{draft.widthMm || "?"} × {draft.heightMm || "?"} × {draft.depthMm || "?"} mm</dd></div><div><dt>Enveloppe souhaitée</dt><dd>{BUDGETS.find((entry) => entry.value === draft.budgetRange)?.label}</dd></div><div><dt>Échéance souhaitée</dt><dd>{draft.deadline || "À définir"}</dd></div>{draft.intendedUse && <div><dt>Usage / contraintes</dt><dd>{draft.intendedUse}</dd></div>}<div><dt>Références visuelles</dt><dd>{draft.references.trim() ? draft.references.split(/\n/).filter((value) => value.trim()).join("\n") : "Aucun lien ajouté"}</dd></div><div><dt>Contact</dt><dd>{draft.name}<br />{draft.email}{draft.phone && <><br />{draft.phone}</>}</dd></div></dl></div>
            <p className="boj-fine-print">L’envoi ne vaut pas commande. L’atelier devra confirmer la faisabilité, le prix, les droits nécessaires, le calendrier et les modalités de remise dans une proposition.</p>
            {pending && pending.resolution !== "deleted" && <p className="boj-context-note">Cette tentative garde son contenu et son identifiant jusqu’à confirmation. Une répétition de l’envoi ne crée pas une seconde demande.</p>}
          </div>}
          {message && <div className="boj-submit-message" role="alert"><strong>{pending?.resolution === "deleted" ? "Demande supprimée" : pending ? "Confirmation en attente" : "À vérifier avant l’envoi"}</strong><p>{message}</p>{Object.keys(errors).length > 0 && <ul>{Object.entries(errors).map(([field, error]) => <li key={field}>{error}</li>)}</ul>}</div>}
          {storageWarning && <p className="boj-context-note" role="status">Le navigateur ne permet pas de conserver la tentative après fermeture. Gardez cet onglet ouvert jusqu’au reçu, ou téléchargez votre copie.</p>}
          <div className="boj-brief-actions">{pending?.resolution === "deleted" ? <button type="button" className="boj-button boj-button-primary" onClick={startNewBrief}>Commencer un nouveau brief<Arrow /></button> : <><button type="button" className="boj-brief-back" disabled={busy || step === 0 || !!pending} onClick={() => { setStep(step - 1); setErrors({}); setMessage(""); }}>← Retour</button><button type="submit" className="boj-button boj-button-primary" disabled={busy}>{busy ? <><span className="boj-loading-dot" /> Enregistrement…</> : step === 3 ? <>{pending ? "Renvoyer la même demande" : "Envoyer à l’atelier"}<Arrow /></> : <>Continuer<Arrow /></>}</button></>}</div>
          <div className="boj-brief-save"><button type="button" onClick={copyBrief}>Télécharger une copie de mon brief</button>{downloaded && <span role="status">Copie personnelle préparée. Elle ne confirme pas un envoi.</span>}<p>Une tentative d’envoi peut être conservée temporairement dans cet onglet pour éviter les doublons. Aucun fichier 3D n’est transmis ici.</p></div>
        </form>
      </>}
    </div>
  </Dialog>;
}
