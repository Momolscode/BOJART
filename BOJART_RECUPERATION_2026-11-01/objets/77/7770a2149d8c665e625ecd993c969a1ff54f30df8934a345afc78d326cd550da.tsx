"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDownToLine, ArrowUpRight, Check, ClipboardList, Clock3, RefreshCw, Search, ShieldCheck, Trash2, X } from "lucide-react";

type Status = "new" | "reviewing" | "awaiting_details" | "quoted" | "accepted" | "declined" | "archived";
type Source = { entryPath: string; utmSource?: string; utmMedium?: string; utmCampaign?: string };
type Summary = { requestId: string; reference: string; name: string; offer: string; status: Status; createdAt: string; updatedAt: string; revision: number; quantity: number; budgetRange: string; source: Source | null };
type Inquiry = Summary & { email: string; phone?: string; description: string; intendedUse?: string; dimensions?: { widthMm?: number; heightMm?: number; depthMm?: number }; deadline?: string; modelStatus: string; referenceURLs: string[]; artworkId?: string };
const statuses: Record<Status, string> = { new: "Nouvelle", reviewing: "À l’étude", awaiting_details: "Précisions attendues", quoted: "Devis communiqué", accepted: "Acceptée", declined: "Sans suite", archived: "Archivée" };
const offers: Record<string, string> = { artwork: "Œuvre & édition", custom: "Création sur mesure", prototype: "Prototype & objet" };
const budgets: Record<string, string> = { undecided: "À définir ensemble", under_250: "Moins de 250 €", "250_750": "250 à 750 €", "750_1500": "750 à 1 500 €", "1500_3000": "1 500 à 3 000 €", over_3000: "Plus de 3 000 €" };
const models: Record<string, string> = { idea: "Une idée", reference: "Des références", file_ready: "Un fichier déclaré prêt, non transmis" };
const date = (value: string) => new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "Europe/Paris" }).format(new Date(value));

async function api<T extends Record<string, unknown> = Record<string, unknown>>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal, credentials: "same-origin", cache: "no-store", headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers } });
    const body = await response.json().catch(() => null) as { ok?: boolean; error?: { message?: string; code?: string } } | null;
    if (!response.ok || !body || body.ok !== true) {
      const error = new Error(body?.error?.message || "L’opération n’a pas pu être confirmée. Actualisez pour vérifier son résultat.") as Error & { status?: number; code?: string };
      error.status = response.status;
      error.code = body?.error?.code;
      throw error;
    }
    return body as T;
  } catch (error) {
    if (error instanceof Error && ["AbortError", "TypeError"].includes(error.name)) throw new Error("La réponse du serveur n’a pas été reçue. Relisez le dossier avant de renouveler une modification.");
    throw error;
  } finally { clearTimeout(timer); }
}

export default function AdminConsole() {
  const [items, setItems] = useState<Summary[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Inquiry | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState<Status>("new");
  const [contact, setContact] = useState({ name: "", email: "", phone: "" });
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const listGeneration = useRef(0);
  const detailGeneration = useRef(0);
  // Refs lock immediately, before React renders a disabled button. They cover
  // successive events in one frame as well as delayed reads of another dossier.
  const readLock = useRef(false);
  const writeLock = useRef(false);
  const statusRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async (next: string | null = null) => {
    const generation = ++listGeneration.current;
    setLoading(true);
    setError("");
    try {
      const query = new URLSearchParams({ status: filter });
      if (next) query.set("cursor", next);
      const result = await api<{ inquiries: Summary[]; counts: Record<string, number>; nextCursor: string | null }>(`/api/admin/briefs?${query}`);
      if (generation !== listGeneration.current) return;
      setItems(previous => next ? [...previous, ...result.inquiries.filter((item: Summary) => !previous.some(old => old.requestId === item.requestId))] : result.inquiries);
      setCounts(result.counts);
      setCursor(result.nextCursor);
    } catch (caught) {
      if (generation === listGeneration.current) setError(caught instanceof Error ? caught.message : "Les demandes sont indisponibles.");
    } finally { if (generation === listGeneration.current) setLoading(false); }
  }, [filter]);

  const inspect = useCallback(async (id: string) => {
    if (writeLock.current) return;
    readLock.current = true;
    const generation = ++detailGeneration.current;
    setDetailLoading(true);
    setDeleteOpen(false);
    setDeleteConfirmation("");
    setError("");
    setNotice("");
    try {
      const result = await api<{ inquiry: Inquiry }>(`/api/admin/briefs/${encodeURIComponent(id)}`);
      if (generation !== detailGeneration.current) return;
      setSelected(result.inquiry);
      setStatus(result.inquiry.status);
      setContact({ name: result.inquiry.name, email: result.inquiry.email, phone: result.inquiry.phone || "" });
      window.history.replaceState(null, "", `/administration?demande=${encodeURIComponent(id)}`);
    } catch (caught) {
      if (generation === detailGeneration.current) { setSelected(null); setError(caught instanceof Error ? caught.message : "La demande est indisponible."); }
    } finally { if (generation === detailGeneration.current) { readLock.current = false; setDetailLoading(false); } }
  }, []);

  useEffect(() => { void load(); return () => { listGeneration.current++; }; }, [load]);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("demande");
    if (id && /^[a-f0-9-]{36}$/i.test(id)) void inspect(id);
    return () => { detailGeneration.current++; readLock.current = false; };
  }, [inspect]);

  async function save() {
    if (!selected || writeLock.current || readLock.current) return;
    writeLock.current = true;
    const generation = ++detailGeneration.current;
    listGeneration.current++;
    setLoading(false);
    setSaving(true); setError(""); setNotice("");
    const id = selected.requestId;
    try {
      const result = await api<{ inquiry: Inquiry }>(`/api/admin/briefs/${id}`, { method: "PATCH", body: JSON.stringify({ revision: selected.revision, status, contact }) });
      if (generation !== detailGeneration.current) return;
      setSelected(result.inquiry);
      setStatus(result.inquiry.status);
      setContact({ name: result.inquiry.name, email: result.inquiry.email, phone: result.inquiry.phone || "" });
      setNotice(`Demande enregistrée · version ${result.inquiry.revision}.`);
      await load();
    } catch (caught) {
      if (generation === detailGeneration.current) setError(caught instanceof Error ? caught.message : "La modification n’a pas pu être confirmée.");
    } finally { writeLock.current = false; if (generation === detailGeneration.current) setSaving(false); }
  }

  async function remove() {
    if (!selected || writeLock.current || readLock.current || deleteConfirmation !== selected.reference) return;
    writeLock.current = true;
    const generation = ++detailGeneration.current;
    listGeneration.current++;
    setLoading(false);
    setSaving(true); setError(""); setNotice("");
    try {
      await api(`/api/admin/briefs/${selected.requestId}`, { method: "DELETE", body: JSON.stringify({ revision: selected.revision, confirmation: selected.requestId }) });
      if (generation !== detailGeneration.current) return;
      const reference = selected.reference;
      setSelected(null); setDeleteOpen(false); setDeleteConfirmation("");
      window.history.replaceState(null, "", "/administration");
      setNotice(`${reference} supprimée de la boîte de demandes. Les exports déjà téléchargés restent à supprimer séparément.`);
      await load();
    } catch (caught) { if (generation === detailGeneration.current) setError(caught instanceof Error ? caught.message : "La suppression n’a pas pu être confirmée."); }
    finally { writeLock.current = false; if (generation === detailGeneration.current) setSaving(false); }
  }

  const visible = items.filter(item => `${item.name} ${item.reference} ${offers[item.offer]}`.toLocaleLowerCase("fr").includes(search.toLocaleLowerCase("fr")));
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
  const sourceCounts = items.reduce<Record<string, number>>((sum, item) => { const source = item.source?.utmSource || "Accès direct / non renseigné"; sum[source] = (sum[source] || 0) + 1; return sum; }, {});

  return <>
    <section className="boj-admin-intro">
      <div><p className="boj-admin-eyebrow">Acquisition / Dossiers réels</p><h1>De l’intention<br /><em>au projet.</em></h1></div>
      <p>Une boîte de réception pour qualifier, suivre et préparer le passage à l’atelier. Chaque demande conserve sa référence et sa version.</p>
    </section>
    <section className="boj-admin-metrics" aria-label="État des demandes">
      <article><ClipboardList aria-hidden="true" /><span>{total}</span><p>Demandes conservées</p></article>
      <article><Clock3 aria-hidden="true" /><span>{counts.new || 0}</span><p>À découvrir</p></article>
      <article><Check aria-hidden="true" /><span>{counts.accepted || 0}</span><p>Acceptées · statut déclaré</p></article>
      <article className="boj-admin-metric-note"><ShieldCheck aria-hidden="true" /><p>Accès autorisé côté serveur.<br />Aucun envoi d’e-mail automatique.</p></article>
    </section>
    <div className="boj-admin-status" ref={statusRef} aria-live="polite" aria-atomic="true">{error && <p className="boj-admin-error" role="alert">{error}</p>}{notice && <p className="boj-admin-success">{notice}</p>}</div>
    <section className="boj-admin-workspace">
      <aside className="boj-admin-inbox" aria-label="Liste des demandes">
        <div className="boj-admin-section-title"><h2>La boîte de demandes</h2><button className="boj-admin-icon" type="button" aria-label="Actualiser les demandes" disabled={loading || saving} onClick={() => void load()}><RefreshCw size={18} className={loading ? "boj-admin-spin" : ""} /></button></div>
        <label className="boj-admin-filter"><span>État du dossier</span><select value={filter} disabled={saving} onChange={event => setFilter(event.target.value)}><option value="all">Toutes les demandes</option>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="boj-admin-search"><Search size={18} aria-hidden="true" /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Nom ou référence affichée" aria-label="Rechercher parmi les demandes affichées" /></label>
        <div className="boj-admin-list" aria-busy={loading}>
          {!loading && !visible.length && <p className="boj-admin-empty">{items.length ? "Aucune demande affichée ne correspond à cette recherche." : "Les demandes reçues apparaîtront ici avec leur référence."}</p>}
          {visible.map(item => <button type="button" className={`boj-admin-inquiry ${selected?.requestId === item.requestId ? "is-selected" : ""}`} key={item.requestId} disabled={saving} onClick={() => void inspect(item.requestId)} aria-pressed={selected?.requestId === item.requestId}>
            <span className="boj-admin-inquiry-top"><span>{offers[item.offer]}</span><span className={`boj-admin-chip is-${item.status}`}>{statuses[item.status]}</span></span>
            <strong>{item.name}</strong><span>{item.reference}</span><span className="boj-admin-inquiry-bottom"><span>{date(item.createdAt)}</span><ArrowUpRight size={18} aria-hidden="true" /></span>
          </button>)}
          {loading && <p className="boj-admin-empty">Lecture des demandes…</p>}
        </div>
        {cursor && <button className="boj-admin-secondary" type="button" disabled={loading || saving} onClick={() => void load(cursor)}>Afficher les suivantes</button>}
      </aside>
      <div className="boj-admin-detail" aria-busy={detailLoading}>
        {detailLoading ? <div className="boj-admin-placeholder"><Clock3 size={32} /><h2>Ouverture du dossier…</h2></div> : !selected ? <div className="boj-admin-placeholder"><ClipboardList size={38} /><p className="boj-admin-eyebrow">Sélectionnez une demande</p><h2>Un brief. Une référence.<br />Un prochain geste.</h2><p>Consultez l’intention, vérifiez les précisions nécessaires et exportez une demande pour préparer son passage dans Jarvis.</p></div> : <>
          <div className="boj-admin-detail-heading"><div><p className="boj-admin-eyebrow">{selected.reference} · v{selected.revision}</p><h2>{offers[selected.offer]}</h2><p>Reçue le {date(selected.createdAt)} · actualisée le {date(selected.updatedAt)}</p></div><button className="boj-admin-icon" type="button" aria-label="Relire cette demande depuis le serveur" disabled={saving} onClick={() => void inspect(selected.requestId)}><RefreshCw size={18} /></button></div>
          <section className="boj-admin-brief"><h3>L’intention</h3><p className="boj-admin-verbatim">{selected.description}</p>{selected.intendedUse && <><h3>L’usage envisagé</h3><p className="boj-admin-verbatim">{selected.intendedUse}</p></>}</section>
          <dl className="boj-admin-specs"><div><dt>Quantité souhaitée</dt><dd>{selected.quantity}</dd></div><div><dt>Préférence de budget</dt><dd>{budgets[selected.budgetRange]}</dd></div><div><dt>Point de départ</dt><dd>{models[selected.modelStatus]}</dd></div><div><dt>Échéance souhaitée</dt><dd>{selected.deadline ? date(selected.deadline + "T12:00:00.000Z") : "À définir"}</dd></div><div><dt>Dimensions souhaitées</dt><dd>{selected.dimensions ? Object.entries(selected.dimensions).map(([key, value]) => `${({ widthMm: "L", heightMm: "H", depthMm: "P" } as Record<string, string>)[key]} ${value} mm`).join(" · ") : "À préciser"}</dd></div><div><dt>Création de référence</dt><dd>{selected.artworkId || "Non renseignée"}</dd></div></dl>
          {selected.referenceURLs.length > 0 && <section className="boj-admin-references"><h3>Références fournies</h3><p>Liens fournis par le demandeur ; leur contenu n’a pas été vérifié ni importé.</p>{selected.referenceURLs.map((url, index) => <a key={url} href={url} target="_blank" rel="noopener noreferrer nofollow">Référence {index + 1} · {new URL(url).hostname}<ArrowUpRight size={16} /></a>)}</section>}
          <section className="boj-admin-edit"><h3>Contact & suivi</h3><p>Les corrections remplacent les coordonnées enregistrées. Le budget est une préférence ; aucun tarif n’est calculé ici. Le statut est déclaré par l’atelier : il ne constitue ni un devis ni une preuve d’accord.</p><div className="boj-admin-contact-grid"><label>Nom<input value={contact.name} minLength={2} maxLength={100} disabled={saving} autoComplete="off" onChange={event => setContact(value => ({ ...value, name: event.target.value }))} /></label><label>E-mail<input type="email" value={contact.email} maxLength={254} disabled={saving} autoComplete="off" onChange={event => setContact(value => ({ ...value, email: event.target.value }))} /></label><label>Téléphone facultatif<input type="tel" value={contact.phone} maxLength={40} disabled={saving} autoComplete="off" onChange={event => setContact(value => ({ ...value, phone: event.target.value }))} /></label><label>Statut<select value={status} disabled={saving} onChange={event => setStatus(event.target.value as Status)}>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div><div className="boj-admin-edit-actions"><button className="boj-admin-primary" type="button" disabled={saving} onClick={() => void save()}>{saving ? "Enregistrement…" : "Enregistrer le suivi"}<Check size={17} /></button><a className="boj-admin-secondary" href={`mailto:${encodeURIComponent(contact.email)}`}>Rédiger un e-mail<ArrowUpRight size={16} /></a></div></section>
          <section className="boj-admin-transfer"><div><p className="boj-admin-eyebrow">Passage vers l’atelier</p><h3>Préparer avec Jarvis.</h3><p>L’export contient la demande et son empreinte. Dans Jarvis, examinez-le et rédigez une synthèse technique avant de créer un dossier.</p></div><a className="boj-admin-primary" href={`/api/admin/briefs/${selected.requestId}/export`} download={`${selected.reference}.json`}><ArrowDownToLine size={18} />Exporter la demande</a><p className="boj-admin-fineprint">Ce fichier contient des coordonnées. Conservez-le dans un espace autorisé ; son export ne lance aucune fabrication.</p></section>
          <div className="boj-admin-attribution"><span>Origine déclarée</span><p>{selected.source?.utmSource || "Non renseignée"}{selected.source?.utmCampaign ? ` · ${selected.source.utmCampaign}` : ""}{selected.source?.utmMedium ? ` · ${selected.source.utmMedium}` : ""}</p></div>
          <section className="boj-admin-delete"><button type="button" className="boj-admin-text-danger" disabled={saving} onClick={() => { setDeleteOpen(value => !value); setDeleteConfirmation(""); }}><Trash2 size={16} />Supprimer cette demande</button>{deleteOpen && <div className="boj-admin-delete-confirm"><button className="boj-admin-icon" type="button" aria-label="Annuler la suppression" disabled={saving} onClick={() => setDeleteOpen(false)}><X size={16} /></button><h3>Effacer la demande et ses coordonnées</h3><p>Cette suppression est définitive dans la boîte. Un identifiant technique sans coordonnées empêche un ancien envoi de recréer la demande. Les fichiers exportés restent à supprimer séparément.</p><label>Recopiez {selected.reference}<input value={deleteConfirmation} onChange={event => setDeleteConfirmation(event.target.value)} disabled={saving} autoComplete="off" /></label><button type="button" className="boj-admin-danger" disabled={saving || deleteConfirmation !== selected.reference} onClick={() => void remove()}>Confirmer la suppression</button></div>}</section>
        </>}
      </div>
    </section>
    <section className="boj-admin-bottom"><article><p className="boj-admin-eyebrow">Lecture de l’acquisition</p><h2>D’où viennent les demandes affichées ?</h2><div className="boj-admin-sources">{Object.entries(sourceCounts).map(([source, count]) => <div key={source}><span>{source}</span><strong>{count}</strong></div>)}</div><p>Comptage des demandes chargées, selon les libellés de campagne fournis au dépôt. Aucun suivi publicitaire ni mesure des visiteurs.</p></article><article><p className="boj-admin-eyebrow">Continuité du dossier</p><h2>Le contact reste à sa source.</h2><p>Corrigez ou supprimez les coordonnées dans cette boîte. Après examen, Jarvis conserve la référence et les paramètres utiles au projet. Vérifiez séparément les copies exportées lors d’une demande d’effacement.</p><a href="/confidentialite">Information sur les données<ArrowUpRight size={16} /></a></article></section>
  </>;
}
