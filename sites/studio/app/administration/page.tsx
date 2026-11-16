import type { Metadata } from "next";
import { getChatGPTUser, chatGPTSignInPath, chatGPTSignOutPath } from "../chatgpt-auth";
import { isAcquisitionAdmin } from "../../lib/acquisition-runtime";
import AdminConsole from "./AdminConsole";
import "./admin.css";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Demandes — BOJ.ART", robots: { index: false, follow: false } };

export default async function Administration() {
  const user = await getChatGPTUser();
  if (!user || !isAcquisitionAdmin(user)) return <main className="boj-admin boj-admin-access">
    <a href="/" className="boj-admin-brand">BOJ.ART<span>Studio</span></a>
    <p className="boj-admin-eyebrow">Espace atelier</p>
    <h1>Les demandes,<br />au même endroit.</h1>
    <p>{user ? "Cette session n’est pas autorisée à consulter les demandes de BOJ.ART." : "Connectez-vous avec le compte autorisé pour consulter les demandes, préparer leur suivi et les transmettre à Jarvis."}</p>
    <a className="boj-admin-primary" href={user ? chatGPTSignOutPath("/administration") : chatGPTSignInPath("/administration")} target="_top">{user ? "Changer de session" : "Se connecter avec ChatGPT"}</a>
    <a href="/">Revenir au studio</a>
  </main>;

  return <main className="boj-admin">
    <header className="boj-admin-header">
      <a href="/" className="boj-admin-brand">BOJ.ART<span>Studio / Administration</span></a>
      <nav aria-label="Navigation administration"><a href="/">Voir le site ↗</a><a href={chatGPTSignOutPath("/")} target="_top">Déconnexion</a></nav>
    </header>
    <AdminConsole />
  </main>;
}
