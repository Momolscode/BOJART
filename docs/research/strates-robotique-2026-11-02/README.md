# STRATES — session « bras robotique » du 2 novembre 2026

Statut : **audit documentaire et propositions**. Aucune performance physique, aucun robot, aucune cellule, aucun devis et aucun essai de peinture n'ont été acquis ou exécutés. Rien ici n'autorise un achat, une commande machine ou un message à un tiers.

## Ce qui a été reçu

| Élément | Identité | Disposition |
|---|---|---|
| PDF `STRATES_Audit_Robotique_IA_2026-11-02.pdf`, 12 pages A4, « BOJ.ART / MARWIN TECH — Revue de conception » | SHA-256 `2a9830490b0ea15742678f74e305c8747fc79650153c0952c6c7938302a47e94`, 109 437 octets | Original **hors Git public** : il reprend des montants du dossier investisseur et du budget, et nomme le partenaire de la proposition artistique. Lu intégralement le 2 novembre ; ce résumé ne le remplace pas. |
| Vidéo générée « Photorealistic-cinematic-documentary-of… » | SHA-256 `335303cc8dcdc65d36f78cf798fec9026661e0bd83051e91854104a8eab281ed`, 22 295 616 octets | Hors Git (média). Voir `PROVENANCE.json`. |
| Vidéo générée « Photorealistic-10-second-practical-works… » | SHA-256 `68ebcc909aa4772e824aabaec89ad0f65872f716dbcd7778ae027a183fb14c4f`, 8 697 367 octets | Hors Git (média, droits du personnage non vérifiés). |
| Conversation ChatGPT « Bras robotique précis », `6ae7c762-6630-83eb-afde-680aa0c54b2e` | Lien privé : HTTP 403 sans compte le 2 novembre | **Non lue**. Aucun message n'est reconstruit ici. |

L'utilisateur désigne cette conversation comme « la session bras robotique » de BOJ.ART. L'audit des chats V5 la classait encore comme candidat ambigu, corps non lu ; ce rattachement vient désormais de la déclaration de l'utilisateur, pas d'une lecture. L'en-tête mentionne Marwin Tech : ce dépôt n'absorbe pas les projets personnels Marwin ; seul le lien avec l'atelier BOJ.ART et Jarvis est consigné.

## Résumé de l'audit (synthèse, pas l'original)

**Périmètre.** Peindre au pinceau un relief mural stratifié pour une proposition artistique, avec un lien possible vers l'atelier BOJ.ART et Jarvis. L'audit s'appuie sur trois documents internes non transmis ici [I1–I3 : proposition STRATES v1.1, dossier investisseur v1.0, budget] et neuf sources publiques [R1–R9].

**Verdict.** Avis favorable à un **banc d'essai ciblé**. L'achat d'une cellule complète et le programme R&D chiffré dans le dossier demandent des preuves supplémentaires. Trois décisions recommandées :

1. Figer la recette STRATES et ses critères, distincts de ceux des figurines.
2. Mesurer matière, contact et erreur totale avant de choisir capteur ou bras.
3. Financer une preuve physique avec décision explicite de poursuite, puis une œuvre pilote.

**Séparer ambitions et preuves.** Les exigences de figurines (trait de 0,50 mm ± 0,15 ; contour P95 ≤ 0,20 mm) restent une ambition de recherche distincte, non validée. STRATES vise un segment de 10–15 cm, trait nominal 7 mm, largeur 6–8 mm sur 90 % de la longueur, débordement ≤ 1 mm ; l'œuvre finale envisagée mesure environ 90 × 65 cm. Une réussite à 7 mm ne prouve pas le 0,5 mm. Il manque une fiche d'acceptation STRATES versionnée unique.

**Cinématique après le procédé.** Comparer : bras existant en laboratoire, banc XYZ avec outil compliant, bras six axes dédié. Vérifier géométrie (porte-outil, câbles, brides), accès sur tout le trajet et recalage. La répétabilité annoncée d'un bras du commerce ne garantit ni l'accès à une œuvre de 90 × 65 cm, ni la précision du contour peint. Recommandation pour BOJ.ART : utiliser le parc d'impression pour coupons, gabarits et porte-outils, et obtenir d'abord un essai sur une machine disponible.

**Métrologie.** Grandeur mesurée : débordement du pigment sec hors zone autorisée. Allocation proposée pour ≤ 1 mm : recalage 0,10 ; calibration de pointe 0,15 ; suivi de trajectoire 0,10 ; déformation du pinceau 0,20 ; étalement 0,25 ; incertitude de mesure 0,20 mm. C'est une proposition d'allocation, pas une performance. Règle de recette proposée : valeur mesurée + incertitude ≤ 1 mm. Utiliser un étalon indépendant du système qui pilote le robot.

**Contact et matière.** Résolution, justesse, répétabilité, bruit, dérive et hystérésis d'un capteur d'effort sont distinctes ; demander la référence exacte avant achat. Essais proposés : geste de référence, bruit/dérive à faible charge, variation contact/vitesse, trois préparations de surface. Figer pinceau, support, peinture/dilution, charge, essuyage, délais et ambiance avant de collecter.

**Architecture logique proposée.** Jarvis/interface → superviseur local (identifiants, état, préconditions, journal) → contrôleur du procédé (contact, exécution, défauts, horodatage) → robot et outil ; vision/planificateur et mesures physiques en boucle ; **chaîne de sécurité indépendante**. La commande conversationnelle ne ferme pas la boucle de contact. Un identifiant de mission évite un doublon informatique mais ne dit pas quelle peinture a déjà été déposée : après interruption, journaliser l'exécuté et inspecter la surface. Aucune de ces liaisons n'est vérifiée sur matériel.

**IA.** Niveaux : recette programmée → modèle du dépôt → correction bornée → généralisation, chacun avec sa condition de validation sur des sessions tenues à l'écart. Retenir un modèle seulement s'il améliore la qualité ou réduit le travail total à qualité égale face à la recette programmée. Les vidéos générées communiquent la direction artistique ; elles ne remplacent pas les couples action/force/dépôt mesurés.

**Protocole et statistiques.** Étapes : référence manuelle, calibration (exclue de la validation finale), validation initiale de 20 essais sur coupons neufs, qualification étendue planifiée, œuvre pilote. 19/20 réussites donnent une borne inférieure unilatérale à 95 % d'environ 78,4 % ; il faut 59 réussites sur 59 essais indépendants pour dépasser 95 %. Rapporter séparément qualité du dépôt, durée complète avec interventions et réception artistique.

**Risques P1.** Dépôt instable ; mesure inadaptée ; contact mal maîtrisé ; achat mal dimensionné ; valeur artistique insuffisante. **P2.** Reprise qui double un trait ; dérive ou mauvaise généralisation. Sécurité : ISO 10218-2:2025 pour l'intégration des cellules ; règlement machines (UE) 2023/1230 applicable à partir du 20 janvier 2027, selon l'audit. Aucune conformité n'est attestée.

**Économie.** L'audit déclare l'arithmétique du budget cohérente et recommande de rechiffrer banc et œuvre pilote par livrables. L'économie de séries ne justifie pas à elle seule une œuvre unique. Montants non reproduits dans ce dépôt public.

**Jalons proposés.** G0 définition (critères signés) ; G1 matière et mesure ; G2 mouvement (accès, arrêt) ; G3 répétition (recette figée, validation séparée) ; G4 valeur (pièce physique, réception artistique et commerciale). Cinq premiers jours de travail proposés : un motif et ses limites acceptables, coupons, mesure de largeur/débordement, même cas d'essai soumis à un laboratoire et à un intégrateur, tenue de G0/G1.

## Vérifications faites dans cette session

Les calculs du document ont été recalculés : `verification-calculs.json`. Les bornes binomiales, la résolution caméra, la synchronisation, le budget d'erreur, les sommes et parts du budget et les coûts par série concordent. Ces recalculs ne vérifient ni les tarifs, ni les fiches constructeur, ni les sources R1–R9, qui n'ont pas été rouvertes ici.

## Lien avec Jarvis

Ce dossier reste une recherche (`bojart.jarvis`, collection `research`). Il ne crée ni route, ni connecteur, ni commande machine. Il rejoint les invariants existants : route → garde → dispatch → reçu, résultat inconnu rapproché avant relance, et aucun pouvoir physique conféré par un document ou une conversation.

## Prochaine preuve

G0 : fiche d'acceptation STRATES signée (motif, pinceau, support, rendus acceptable/inacceptable). Ensuite des coupons mesurés avec incertitude déclarée. Si l'utilisateur l'autorise, verser le PDF, les deux vidéos et le texte de la conversation dans un stockage privé avec leurs empreintes.
