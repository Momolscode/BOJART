import type { Metadata } from "next";
import "./globals.css";
import "./vitrine.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://bojart-studio.yellowghost64.chatgpt.site"),
  title: { default: "BOJ.ART — L’idée prend du volume", template: "%s — BOJ.ART" },
  description: "Découvrez les œuvres BOJ.ART et préparez votre projet de création sur mesure : figurine, pièce artistique, socle ou prototype. Un brief clair pour étudier sa réalisation.",
  robots: { index: false, follow: false },
  openGraph: {
    type: "website", locale: "fr_FR", siteName: "BOJ.ART",
    title: "BOJ.ART — L’idée prend du volume",
    description: "Œuvres, créations sur mesure et projets de prototypes. Du premier détail à la pièce entière.",
    url: "https://bojart-studio.yellowghost64.chatgpt.site",
    images: [{ url: "/assets/baki-hero.webp", alt: "Œuvre Baki, référence du portfolio BOJ.ART" }],
  },
  twitter: { card: "summary_large_image", title: "BOJ.ART — L’idée prend du volume", images: ["/assets/baki-hero.webp"] },
  icons: {
    icon: "/assets/logo.webp",
    shortcut: "/assets/logo.webp",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body><script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify({"@context":"https://schema.org","@graph":[{"@type":"WebSite","@id":"https://bojart-studio.yellowghost64.chatgpt.site/#website",url:"https://bojart-studio.yellowghost64.chatgpt.site",name:"BOJ.ART",inLanguage:"fr-FR"},{"@type":"Brand",name:"BOJ.ART",url:"https://bojart-studio.yellowghost64.chatgpt.site",logo:"https://bojart-studio.yellowghost64.chatgpt.site/assets/logo.webp",sameAs:["https://www.tiktok.com/@boj.art"]}]}).replace(/</g,"\\u003c")}}/>{children}</body>
    </html>
  );
}
