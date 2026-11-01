# BOJ.ART — Studio & acquisition

Vitrine préparée le 19 octobre 2026 pour transformer la découverte des œuvres BOJ.ART en demandes qualifiées, puis en dossiers techniques dans Jarvis.

## Les trois espaces

| Espace | Adresse | Usage |
| --- | --- | --- |
| Studio | https://bojart-studio.yellowghost64.chatgpt.site | Portfolio, film, offres et brief guidé |
| Administration | https://bojart-studio.yellowghost64.chatgpt.site/administration | Réception et suivi des demandes ; compte autorisé requis |
| Tour Jarvis | https://bojart-atelier.yellowghost64.chatgpt.site/?panel=inquiries | Examen de l’export et préparation technique du dossier |

La publication initiale était privée. Lors de l’audit du **19 octobre 2026**, l’accès de la vitrine est **public** ; celui de la tour de contrôle reste réservé au propriétaire. Cette révision préserve ces audiences. Les mentions commerciales et la notice restent incomplètes, faute d’identité juridique, de contact professionnel et de conditions confirmés. Ces informations doivent être complétées avant d’engager l’acquisition commerciale. Les robots sont exclus à ce stade.

L’[audit V11 de l’acquisition](docs/audit-v11-acquisition.md) décrit les défauts reproduits et corrigés : double soumission, résultat incertain, ancienne tentative, sélection administrative et admission transactionnelle. Le reçu, le devis, l’accord et l’impression demeurent des étapes distinctes.

## Ce qui est implémenté

- Portfolio de photographies authentiques BOJ.ART, avec provenance ; changement de pièce principale et vues détaillées.
- Identité charbon, ivoire et carmin, emblème existant, polices locales et animations avec réduction du mouvement.
- Film BOJ.ART déclenché par le visiteur, sans lecteur social tiers.
- Trois parcours : œuvre ou édition, création sur mesure, prototype ou objet à étudier.
- Brief en quatre étapes : intention, détails, coordonnées, récapitulatif. Disponibilité, prix, faisabilité et délai restent à confirmer.
- Enregistrement serveur dans D1 et reçu avec référence. Une tentative dont la confirmation a été perdue conserve son identifiant et son contenu pour être reprise sans duplication.
- Administration contrôlée côté serveur : liste paginée, recherche dans les demandes chargées, filtres, compteurs, détail, correction des coordonnées et du statut, export JSON et suppression.
- Version de la notice conservée au dépôt, protection contre les corrections concurrentes, empreinte du contenu initial conservée pour retrouver le reçu après correction du contact.
- Export vérifiable vers Jarvis. Après examen, Jarvis retient une projection technique et une référence source ; les coordonnées et le brief libre ne sont pas automatiquement ajoutés à son journal.

Les comptes correspondent aux demandes conservées. L’attribution par source porte sur les demandes affichées et les libellés de campagne transmis ; elle ne mesure ni les visiteurs ni un taux de conversion.

## Parcours opérationnel

1. Choisir une offre ou une réalisation et compléter le brief.
2. Le serveur valide la demande puis confirme sa conservation. Le reçu ne signifie pas qu’un membre de l’atelier l’a déjà lue.
3. L’atelier consulte `/administration`, vérifie le contact, qualifie le besoin et tient le statut à jour.
4. Télécharger l’export JSON de la demande. Ce fichier contient des coordonnées et reste dans un espace autorisé.
5. Dans Jarvis, ouvrir « Demandes vitrine », examiner l’export et rédiger la synthèse technique à conserver.
6. Créer ou retrouver le dossier lié. Les fichiers 3D, la faisabilité, les coûts, l’accord et la fabrication sont traités dans leurs étapes respectives.

## Liens d’acquisition préparés

- `/?brief=custom`
- `/?brief=prototype`
- `/?brief=artwork&piece=baki`
- `/?brief=artwork&piece=dragon-ball`
- `/?brief=artwork&piece=trone`

Les paramètres de campagne sont `utm_source`, `utm_medium` et `utm_campaign`. Utiliser des noms courts sans données personnelles, par exemple `tiktok`, `organic` et `atelier_baki`. Aucun compte social, campagne ou envoi n’est automatiquement activé par ces liens.

## Architecture et exploitation

Starter Sites Vinext, Worker et D1 sous le binding `DB`. Schéma Drizzle et migrations versionnés ; aucune création de table pendant une requête. Les secrets d’exécution `BOJART_FORM_SECRET` et `BOJART_ADMIN_EMAILS` ne figurent ni dans le dépôt ni dans le navigateur. L’identité de connexion vient de la plateforme ; elle ne suffit pas à autoriser l’administration sans présence dans la liste admise.

L’API n’envoie aucun e-mail, ne prend aucun paiement, ne télécharge aucun lien de référence et ne commande aucune imprimante. Les statuts « devis communiqué » et « acceptée » sont déclarés par l’atelier ; ils ne créent pas de document ou de preuve d’accord.

- [Plan d’acquisition et priorités de mise en service](docs/ACQUISITION_STRATEGY.md)
- [API et exploitation de la réception](docs/ACQUISITION.md)
- [Environnement et workflow Sites](docs/SITES_RUNTIME.md)
- [Provenance des médias](public/assets/sources.json)
- [Sources et transformations du film](public/assets/brand-film-sources.json)

## Vérification

Les scripts et résultats applicatifs sont dans `qa/`. Le service est testé avec les migrations SQL réelles dans SQLite, les objets Request/Response et WebCrypto, derrière un adaptateur de l’API D1. Sont couverts le reçu après écriture, les réessais et collisions, les droits d’administration, les corrections concurrentes et l’effacement transactionnel.

Ces vérifications ne prouvent pas une soumission client effectuée sur le déploiement, une connexion SIWC interactive ni le rendu graphique sur appareil réel. Le contrôle de navigateur géré n’était pas disponible. La compilation et les contrôles DOM/CSS sont les vérifications réalisées ; la revue visuelle doit se poursuivre sur le site publié.

Pour modifier ce site, conserver son identité dans `.openai/hosting.json` et suivre le workflow Sites officiel : ouverture du source, vérifications, build, synchronisation de l’état exact et publication avec audience préservée.
