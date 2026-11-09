# BOJ.ART — acquisition, demandes et continuité du projet · V10

Réaudit du 19 octobre 2026. Ce document complète le [registre des 30 exigences](PROJECT_REQUIREMENTS.md) et le [réaudit V9](RE_AUDIT_V9.md). Périmètre examiné : concept initial, application V9, calcul de coût, mission, référentiel, archive, conservation et nouvelle articulation vitrine → demande → atelier. La vitrine est développée dans un dépôt distinct ; son état de publication et ses contrôles de réception sont rapportés dans sa propre livraison.

## Décision générale

L’unité du projet reste le dossier. L’acquisition doit lui apporter une demande identifiable, utile à qualifier, dont l’origine se retrouve. Le site présente les créations et les offres ; la boîte de réception conserve les contacts ; Jarvis conserve les paramètres nécessaires au travail de l’atelier. Une demande reçue ne constitue ni un devis accepté, ni une autorisation de fabriquer, ni une preuve de fichier reçu.

Le développement commercial est cohérent avec les trois familles déjà retenues : œuvres et éditions, création sur mesure, prototypes et petites séries. Une offre doit décrire son résultat attendu, son périmètre, ses données nécessaires et ce qui détermine son prix. Les capacités futures de robotique doivent rester liées à un cahier des charges et à des essais appropriés.

## 1. Livré dans l’atelier V10

| Fonction | Comportement livré | Vérification |
|---|---|---|
| Entrée « Demandes client & vitrine » | Accessible depuis Commerce, le centre, l’onglet Demandes et `?panel=inquiries`. Lien explicite vers la vitrine distincte. | Parcours réel de l’application dans JSDOM. |
| Lecture d’un export de demande | Format `bojart.inquiry.export.v1`, structure normalisée et SHA-256 vérifiés avant l’aperçu. Limite 64 Kio. | Fichier valide, données changées, champs inconnus et dépassement de taille. |
| Aperçu avant création | Le contact et le texte source sont lisibles en mémoire. Aucun dossier n’est créé avant l’action de confirmation. La fermeture abandonne la lecture et retire l’aperçu. | Contrôle des opérations avant/après et lecture interrompue. |
| Projection technique | Identité de demande, référence, révision, empreintes et paramètres structurés conservés. Le nom, l’e-mail, le téléphone, la description originale, les campagnes et les liens libres ne sont pas copiés dans le journal. | Vérification du dossier, du journal et des sauvegardes. |
| Synthèse de travail | Zone distincte, vide au départ, pour saisir les contraintes utiles à l’atelier. Le titre initial est fondé sur la référence. | Import de texte technique et exclusion du texte source automatique. |
| Création atomique | Une action `ADD_PROJECT` crée un dossier vide de STL et son lien de provenance. Hauteur inconnue = `null`, affichée « À préciser ». | Réducteur métier et journal réels. |
| Réimport et concurrence | Même demande : ouverture du dossier existant. Contenu différent ou référence réutilisée : conflit sans écrasement. Deux écrans concurrents créent un seul dossier confirmé. | Réimport, modification des notes/devis, SQLite et restauration des reçus. |
| Qualification | Points à examiner selon données disponibles : dimensions, géométrie, usage prototype, budget, date, finition, droits et remise. Export de questions pour relecture. | Ouverture depuis la décision centrale ; aucun message envoyé. |
| Travail et calcul de coût | Accès au dossier et au formulaire de chiffrage existant, avec ses coûts à renseigner. | Absence de montant inventé à l’import. |
| Retour à la source | Lien vers l’administration de la vitrine, ciblé par l’UUID de la demande. Export d’une fiche technique distincte de l’export source. | Identifiant conservé ; aucune clé privée dans le lien. |

L’empreinte confirme que le fichier lu correspond à son contenu déclaré. Elle ne constitue pas une signature de l’émetteur. Le SHA de la demande elle-même sert à reconnaître un réexport identique, même si sa date d’export et son SHA d’enveloppe ont changé.

Le statut commercial de l’export est seulement visible dans l’aperçu. Il ne place pas le dossier en production. Une demande mise à jour conserve la même identité côté source ; le rapprochement de nouvelles versions avec le travail existant reste manuel dans cette version.

## 2. Parcours métier complet à construire

| Étape | Résultat qui doit exister | État actuel / prochaine réalisation |
|---|---|---|
| Contenu ou découverte | Œuvre, offre, page d’arrivée, lien de campagne explicite. | Vitrine distincte et fonds BOJ.ART disponibles dans le projet. Attribution à mesurer côté acquisition. |
| Demande | Référence, besoin, contact, paramètres et accusé de réception réel. | Contrat de demande et raccordement par export/import. Réception distante sous responsabilité de la vitrine. |
| Qualification | Questions résolues, usage, dimensions, fichier ou besoin de conception, finition, date et livraison. | Liste de travail livrée. Décision de faisabilité à documenter avec l’opérateur. |
| Chiffrage | Coûts complets, hypothèses et quantité associés à une version. | Calcul local existant ; détail des opérations et comparaison prévu/réel à ajouter. |
| Devis commercial | Offre versionnée, conditions, validité, prix/fiscalité, délai et périmètre transmis. | Le calcul actuel reste un brouillon. Document commercial et conservation de ses versions à réaliser. |
| Accord | Acceptation portant sur une version précise du devis et, si nécessaire, un aperçu ou prototype précis. | À raccorder ; un champ de statut ne remplace pas cette preuve. |
| Paiement initial | Référence du paiement et rapprochement avec la commande. | À raccorder via un prestataire ; aucune donnée de carte à stocker dans l’atelier. |
| Fabrication | Lot, plateaux, profils, fichiers machine, reçus et consommation réels. | Lecture STL et comparaison de volumes disponibles ; slicing et connecteurs physiques à qualifier. |
| Finition et contrôle | Opérations humaines terminées, contrôle, photos et traitement des reprises. | À formaliser et mesurer sur une réalisation mixte. |
| Livraison | Colis ou retrait, conditionnement, suivi, remise et facture. | À raccorder. Prévoir les créations fragiles et volumineuses dès le chiffrage. |
| SAV | Réclamation liée à la version, diagnostic, réponse, réparation ou reprise. | À construire ; conserver les causes pour améliorer les futures recettes. |
| Contenu et fidélisation | Autorisation de diffusion, montage rendu, contenu publié et origine des nouvelles demandes. | Studio d’intention disponible ; rendu exact, diffusion et suivi commercial encore à raccorder. |

## 3. Ce qui risquait d’être oublié

Les priorités ci-dessous sont des décisions de conception fondées sur le code et les ambitions du projet. Elles ne prétendent pas décrire des incidents déjà observés dans l’atelier physique.

| Priorité | Point | Ce qui existe réellement | Ce qu’il faut compléter et comment l’évaluer |
|---|---|---|---|
| P0 | Coordonnées et demandes privées | Les projets sont conservés dans un journal append-only. | Conserver les contacts et le texte source dans la boîte de réception administrable ; projection minimale dans Jarvis. Vérifier accès, correction, suppression et cycle des exports avant exploitation CRM. |
| P0 | Réception effective | Un formulaire et un bouton ne prouvent pas une réception. | Retour serveur après conservation, référence, nouvelle tentative idempotente et rapprochement d’un résultat inconnu. Tester la réponse perdue sans second contact créé. |
| P0 | Version commerciale acceptée | `SAVE_QUOTE` conserve un calcul courant ; une modification peut l’invalider. | Créer des devis distincts et immuables après émission, puis une commande liée à la version acceptée. Ne jamais réécrire un devis émis avec le calcul courant du projet. |
| P0 | Bonne machine / bon fichier | Identité STL, SHA, unité et révision sont disponibles. | Ajouter profil, matière, version du slicer, plateau et travail physique ; rapprocher une réception perdue avant tout nouveau départ. |
| P0 | Reprise et sauvegarde | Journal v2, reçus et coffre STL disponibles. | Conserver aussi configurations, inventaire, recettes, contacts dans leur source et preuves commerciales. Exercices de restauration séparés ; disponibilité de la tour et alimentation à qualifier. |
| P1 | Coût complet | Le formulaire a déjà matières, heures humaines, taux horaire, autres coûts, marge et commission. | Ventiler conception, préparation, lavage, supports, assemblage, peinture, contrôle et emballage. Ajouter consommables, usure, rebuts et transport selon l’activité. Comparer chaque estimation au temps et coût observés. |
| P1 | Capacité de finition | La mission mentionne l’après-impression. | Définir opérateurs, postes, horaires, files et temps de séchage ; promettre un délai sur la chaîne complète. Mesurer le goulot sur une vraie commande. |
| P1 | Stock et disponibilité | Ressources encore déclarées/simulées ; catalogue à alimenter. | Identifier matières et lots, stock disponible/réservé/consommé, pièces disponibles et réassort. Une impression terminée ne rend pas automatiquement une œuvre vendable. |
| P1 | Droits et provenance | Des œuvres et vidéos sont référencées ; les plans d’édit gardent leurs sources. | Distinguer autorisation du modèle, de l’œuvre représentée, des images du client, des rushes et du son ; conserver les restrictions propres aux usages prévus. Ne pas traiter la présence en ligne comme preuve de droit commercial. |
| P1 | Délais et modifications | Quantité et hauteur peuvent évoluer dans le dossier. | Séparer demande client, exigence validée et ordre de changement. Chiffrer l’effet sur temps, coût, révisions et assemblage avant engagement. |
| P1 | Retouches et qualité | Les échecs de fichier sont identifiés ; qualification physique future. | Enregistrer cause, quantité reprise, temps perdu, résultat et recette corrigée. La qualité finale porte aussi sur aspect, assemblage et emballage. |
| P1 | Mesure de l’acquisition | Le contrat peut conserver une origine et des libellés de campagne côté vitrine. | Suivre demandes reçues → qualifiées → devis → commandes → marge observée. Séparer contacts en double, spam et demandes non réalisables. Aucun taux de conversion fictif. |
| P2 | Voix locale et Jev | Interfaces, contrats de conseil, règles locales et contrôle de fraîcheur disponibles. | Évaluer compréhension française, bruit d’atelier, latence et modes dégradés sur la tour ; réserver des ressources à l’interface pendant les rendus lourds. |
| P2 | Robotique et prototypes | Branche de mission et famille d’offre définies. | Ajouter exigences fonctionnelles, CAO, sous-ensembles, nomenclature, essais et limites d’usage par projet ; qualification distincte d’une figurine décorative. |

## 4. Les devis : garder ce qui fonctionne et compléter la preuve

Le calcul existant couvre le lot complet : matières + heures × taux + autres coûts. Il divise ensuite ce coût par `1 − marge − commission` pour obtenir le prix de calcul, puis le prix par exemplaire. Il conserve la précision interne jusqu’à l’affichage. Les champs ne sont donc pas manquants ; leurs données réelles et leur ventilation restent à recueillir.

La prochaine structure utile sépare : estimation de travail, devis commercial, version acceptée, commande et paiements. Prévoir un identifiant, une révision, une date, une durée de validité, une liste de postes, les hypothèses, les conditions, le résultat attendu et les exclusions convenues. La nature des paiements initiaux et les modalités d’annulation doivent être explicites dans le document applicable. Ne pas calculer une rentabilité réelle à partir des durées fictives du parc de démonstration.

La publication d’un catalogue de vente et la conclusion de contrats imposent des informations adaptées à l’activité : professionnel, caractéristiques, prix, conditions, délai, garanties et modalités applicables. La fiche officielle [Service Public — règles du commerce en ligne](https://entreprendre.service-public.gouv.fr/vosdroits/F23455), vérifiée le 19 juin 2026, sert de base à cette préparation. L’identité juridique de BOJ.ART n’est pas connue dans ce dossier : aucune coordonnée de M-Tek ou d’UNUM ne doit lui être substituée.

## 5. Données personnelles et acquisition

Le chemin retenu réduit les duplications : l’administration de la vitrine conserve la demande complète ; l’atelier enregistre une référence et des paramètres techniques. Le nom de personne, le téléphone, l’e-mail et la description originale sont exclus de l’import métier. La synthèse technique est saisie séparément et n’est pas présentée comme une anonymisation automatique. Des informations personnelles peuvent toujours être saisies manuellement dans une note ou déduites d’un contexte ; la restriction d’accès et la politique de conservation restent nécessaires.

Le responsable du traitement doit définir les objectifs, la base de traitement, les destinataires, les durées et les modalités d’exercice des droits. Les [exemples de formulaires CNIL](https://www.cnil.fr/fr/exemples-de-formulaire-de-collecte-de-donnees-caractere-personnel) donnent une base d’information à adapter. La CNIL distingue conservation active, archivage intermédiaire et suppression selon la finalité ; une archive de demande ne doit pas être conservée indéfiniment sans justification. Voir [CNIL — durées de conservation](https://www.cnil.fr/fr/passer-laction/les-durees-de-conservation-des-donnees), 2 avril 2026.

Les demandes de devis et les abonnements publicitaires doivent suivre des finalités distinctes. Ajouter des pixels, lecteurs tiers ou mesures d’audience demande un examen de leurs traceurs et du consentement applicable. La première version peut fonctionner avec ses propres contenus, des liens sortants et les libellés de campagne explicites, sans ajouter systématiquement une pile publicitaire. Voir [Service Public — cookies et traceurs](https://entreprendre.service-public.gouv.fr/vosdroits/F31228), vérifié le 13 octobre 2026.

Le bouton d’export de la boîte de réception produit un document comportant des données personnelles : son stockage, son partage et son effacement relèvent du cycle de la demande. La projection technique importée et ses empreintes restent des références internes, pas une certification de données anonymes. Aucun contact n’est envoyé automatiquement à Jev dans cette version.

## 6. Jalons et critères de réussite

1. **Acquisition utilisable.** Parcours mobile, offre compréhensible, demande sauvegardée avec retour réel, administration privée, export/import relié à la bonne référence. Vérifier droits et coordonnées de l’activité avant lancement commercial.
2. **Commande suivie.** Une demande qualifiée donne une estimation puis un devis versionné et un accord explicite. Le paiement et les changements sont rapprochés de cette commande.
3. **Fabrication qualifiée.** Une FDM et une résine exécutent chacune une recette identifiée, depuis le fichier jusqu’à la pièce contrôlée. Tester aussi interruption, état inconnu et reprise.
4. **Projet mixte rentable.** Suivre heures humaines, matières, assemblage, finition et livraison d’une réalisation. Comparer prévision et observation ; corriger les offres et les recettes.
5. **Boucle de contenu.** Prévisualisation et rendu proviennent du même plan versionné, avec sources autorisées. Une publication et sa page d’arrivée produisent des demandes dont le devenir est mesuré.

## Vérifications de cette extension

`qa/check-inquiry-import.mjs` : 12 groupes, avec contrat d’export, réduction métier, sauvegarde, concurrence, bases SQLite temporaires et import de la fixture produite par le POST de la vitrine, sa conservation SQLite et son endpoint d’export administrateur. `qa/check-inquiry-interface.cjs` : 8 groupes sur l’application réelle dans JSDOM, avec import, aperçu, qualification, chiffrage, doublon, conflit et fermeture pendant lecture. Les résultats détaillés sont conservés dans `qa/inquiry-import-results.json` et `qa/inquiry-interface-results.json`.

Ces vérifications n’envoient aucun message, ne collectent aucun paiement et ne démarrent aucune impression. Elles n’exercent pas un compte client réel ni la boîte D1 déployée. Le rendu graphique du navigateur et les trois moniteurs physiques restent à vérifier avec la capacité de prévisualisation requise ou sur la tour.
