# Passation — consolidation du 1 novembre 2026

Demande : orchestrer les poussées vers `Momolscode/BOJART`, classer la direction artistique et Jarvis, améliorer la continuité et préparer la gestion future des données sur la tour.

Sources examinées : M07, archive créative préparée pour GitHub, sources R01–R03, notes actuelles, sources Sites V11/V3 et BOJART à `6bc5645c23eeec5e2b7f707b46fde8a0c64a1b5f` avant consolidation. Provenance : `data/catalog/` et `data/knowledge/sources.json`.

Décisions : conserver les chemins relatifs du runtime dans `jarvis/`; séparer sites, création et mémoire ; conserver les variantes/rejets ; garder les médias personnels hors du dépôt public. Le contexte courant corrige l’audit arrêté à R02. Aucun nouveau rendu payant ni publication de site/réseau n’a été lancé.

Chaque prochaine passation contient : objectif, sources datées, faits nouveaux, décisions, fichiers modifiés, tests réellement exécutés, limites et prochaine preuve. Citer la décision remplacée. Un conflit non résolu reste visible ; le fichier le plus récent n’est pas automatiquement le plus vrai.

Le runtime local n’accède pas automatiquement aux anciens chats ni à leurs pièces jointes. Importer les exports autorisés ou intégrer un connecteur documenté dont on teste la couverture.

## Reprise du transfert interrompu — 1 novembre 2026

Les observations historiques ci-dessous sur des octets « externes » sont remplacées, pour la collecte de récupération, par `docs/ETAT_ARCHIVES_2026-11-01.md`. Les trois branches d'archive ont été téléchargées par Git à leurs commits épinglés, puis 3 340 contenus uniques et les fichiers du catalogue ont été restaurés. Comparaison octet par octet avec les trois ZIP d'origine : aucune divergence. Les 87 fichiers du paquet créatif et les 22 textes en attente sont tous déjà dans cette collection ; aucun nouveau doublon de leurs contenus n'a été ajouté.

Ajouts : restaurateur commun `tools/restore_recovery_2026_11_01.py`, état des archives, preuve `docs/evidence/recovery-resumption-2026-11-01.json`, entrée dans la mémoire et affirmation sourcée. Correction du validateur : la sélection binaire déjà fusionnée par la PR #3 est contrôlée contre son manifeste épinglé et ses empreintes, sans autorisation générale de nouveaux médias. Le manifeste général est régénéré dans le même changement.

Vérifications locales : restauration des 3 parties depuis GitHub, comparaison des 3 348 entrées des ZIP, 37 tests mémoire/restauration, 25 tests agents, 36 tests opérations, 11 tests JavaScript et 10 cas de recherche citée réussis. Les nouveaux tests refusent les chemins dangereux, les destinations existantes, la corruption et les modifications de la liste d'exceptions. La restauration de la sélection binaire de 5 fichiers est également vérifiée. Ces contrôles ne qualifient ni la voix réelle, ni les machines, ni la qualité artistique.

Concurrence détectée : la branche a avancé vers `1ca60c3571c78f9303b8b4d54e82e34ae3e439f7`. Les 23 nouveaux chemins distants et les évolutions README/PRODUCTION ont été récupérés et rapprochés. `productions/` reste la racine des recettes exécutables ; `creative/` conserve la direction.

Deux avances supplémentaires ont été rapprochées : `b68878fc5040a15dcee9a89ca415a94cbc946880` et `0c72455bec644dafffc142b5d72fcf81b8d9b1ac`. Leurs neuf nouveaux fichiers historiques et de génération sont conservés, ainsi que la clarification de couverture du README dans `docs/CREATIVE_PIPELINE_HISTORIQUE.md`. Les liens directs vers des médias personnels ont été retirés de la version publique courante ; cela ne modifie pas les anciens commits.

Dernière réconciliation : `cd71c6ba640f304248702d8a3e64c60f900f9d0b`, avec le module `bojart_ops`, ses tests et son workflow, les corrections du contrôle artistique et les observations de génération. Leur publication concurrente est conservée comme parent de la consolidation.

## Préparation mémoire — 1 novembre 2026

Extension intégrée sur la consolidation `30b3fb9858d81e5499d0a51ed8df6c317b771d7c`, sans second magasin documentaire. Voir `INSTALLER_DEMAIN.md`, `docs/memory/MCP.md` et `docs/memory/VALIDATION.json`. Installation prévue le 2 novembre ; OS non décidé. Les modèles sont facultatifs et non téléchargés. Les faits de référence viennent du registre sourcé ; les notes locales sont des propositions. La sauvegarde documentaire existante inclut les tables supplémentaires. Les sauvegardes opérationnelles M07 restent distinctes.

## Complément de transfert — 1 novembre 2026

Demande : pousser sur GitHub BOJ.ART. Base distante relue : `1d76c6876de54c7bc37b777ae66bf031207a140d`. Les 694 blobs du dépôt ont été restaurés avec vérification de leur empreinte Git avant préparation. Le paquet créatif actuel est déjà représenté par le catalogue initial et ses documents publics ; aucune ancienne variante ne remplace la version courante.

Trois archives de récupération ont passé CRC et SHA-256, puis les 3 340 contenus uniques ont été relus et contrôlés par taille et SHA-256. Les 6 445 emplacements se rattachent à 219 sources connues. Ajouts : catalogue public de provenance, note originale Jarvis 5, guide de restauration et entrée dans la mémoire documentaire. Le mode d’emploi de récupération, ajouté simultanément par une autre session, est réutilisé sans doublon. Les contenus multimédias et archives restent externes, explicitement signalés. Les tests logiciels hérités ne sont pas une conséquence de cette vérification de données.

Réconciliation avant envoi : les évolutions distantes jusqu’à `9a78aab6987905030e96112d0229ae0ba8ae53a5` sont préservées, y compris l’extension mémoire, les lanceurs et la correction des tests Windows.

## Document de reprise Jarvis 5 — 1 novembre 2026

Demande explicite : pousser le fichier joint `JARVIS5_REPRISE_VERIFIEE_2026-10-31.txt` dans `Momolscode/BOJART`. Base distante examinée : `4873567fad40d2033005ec0fd7af05a11b0bc2fe`. Le registre connaissait déjà son empreinte, mais aucun blob identique ne figurait dans l'arbre de `main`. Le document complet est ajouté sous `docs/historical/recovery-2026-11-01/`, sans modifier ses 117 992 octets. L'entrée `jarvis-recovery` existante pointe désormais vers cette copie ; aucune nouvelle source ni décision n'est créée. Les affirmations anciennes restent historiques et ne remplacent pas `context/CURRENT.md`. Contrôles : empreinte SHA-256 de la pièce jointe, absence de copie identique dans l'arbre de départ, manifeste du dépôt et provenance. Les médias et archives cités ne sont pas transférés par cet ajout documentaire.

## Suite : démarrage et reprise

Base rapprochée : `e5cd9f3f18f744b800aa8bb655a70fa643c634a1` (PR #4). La reprise commune des archives et les contrôles du manifeste binaire sont réutilisés. Diagnostic de lancement, chemin mémoire partagé, export sourcé, invalidation des réponses périmées et diversification des sources sont ajoutés. Voir `docs/DEMARRAGE_ET_REPRISE.md` et les preuves de démarrage/restauration dans `docs/evidence/startup-2026-11-01.json`. Les modèles et périphériques réels restent à qualifier.

## Suite : orchestration des domaines et des revues

Base observée : `5268e7e7b70fa25efee7d186f27cd3716a49c4c1`, 776 fichiers. Reçu de surveillance relu sur `audit/context-results` à `cfdca9fc47d71dd8b2bce6ff324994f089d88d34` : 633 chemins en attente à cette observation. La PR de surveillance n°1 reste ouverte ; les branches de récupération restent séparées.

Ajouts : registre des domaines et de dix tâches sourcées, planificateur en lecture seule, lots de 20 contenus maximum et tests de non-régression. Le workflow d’audit existant publie le classement et ses dépendances avec ses artefacts. Les doublons conservent tous leurs chemins ; un checkpoint périmé ou bloqué ne réduit pas la revue de la révision courante. Guide : `docs/ORCHESTRATION.md`, indexé pour les trois domaines mémoire.

L’environnement local était indisponible pendant cette préparation ; la validation de ce changement passe par les contrôles GitHub de sa révision. Aucun nouveau test de modèle, navigateur, micro, écran ou imprimante n’est revendiqué. Les prochaines preuves restent l’inventaire de la tour, l’installation réelle et la source fidèle G2.

Réconciliation avant publication : le correctif concurrent `461d46ff39caaf142ce37a3e0b78f22dfcc2e842` est conservé, notamment la diversification avant limite, les avertissements de sources absentes et ses tests de mémoire/interface. Il devient le parent du changement d’orchestration.

## Dossier d’audit Jarvis — 1 novembre 2026

Publication demandée par l’utilisateur : [rapport, visuel et mission indépendante](../docs/audits/jarvis-installation-2026-11-01/README.md). Base rapprochée : `9f58fa29f0051cc8a7098855359a8a6dd0eef7e6`. Les versions, observations, sorties transcrites, limites et commandes sont consignées dans ce dossier. Le moteur et le matériel facultatifs restent à qualifier. Les journaux locaux complets sont indisponibles après déconnexion ; les contrôles distants sont attribués à leur propre SHA. Le workflow du dossier régénère le manifeste du dépôt, valide les empreintes et fournit un ZIP. Prochaine preuve : retour de l’auditeur sur la version choisie et le PC cible.

## Résilience mémoire avant installation

Base examinée : `5268e7e7b70fa25efee7d186f27cd3716a49c4c1`, dont les contrôles GitHub sont réussis. Le blocage des archives observé précédemment est résolu dans cette base.

Renforcement : transaction unique pour chaque lot documentaire, points de sauvegarde pour les opérations imbriquées, lecture cohérente des faits et passages, recette du vrai lanceur après arrêt forcé. Aucun second magasin, changement de modèle ou raccordement machine. Voir `docs/memory/RESILIENCE.md`.

L’environnement local a été interrompu pendant la préparation. Les nouveaux contrôles sont donc exécutés sur une branche isolée par GitHub Actions, sous Windows et Linux ; leurs résultats par commit servent de preuve. Ne pas assimiler ces essais de processus à une coupure électrique du poste.

Réconciliation : les améliorations de diversité des sources et de signalement des preuves manquantes du commit `461d46ff39caaf142ce37a3e0b78f22dfcc2e842` sont conservées. Le premier passage des douze scénarios atomiques réussit sous Windows et Linux ; la recette du lanceur a exposé un serveur détaché sous Windows. Exécution dans le même processus ajoutée avant un nouveau passage complet.

Validation : les contrôles du commit `d57330052b32cb5f638e841bdc086804cd65ede1` réussissent, y compris la recette réelle du lanceur sous Windows et Linux, l’arrêt forcé, le redémarrage et les douze scénarios atomiques. Preuve : https://github.com/Momolscode/BOJART/actions/runs/41357380816. Les ajouts d’orchestration sont préservés ; les contrôles de leur consolidation avec la mémoire réussissent également au commit `f15e323da95d7a9a81a5de6ae3e3fe66a97eb4b7` (recette Windows/Linux : https://github.com/Momolscode/BOJART/actions/runs/41357688600). Le dossier d’audit publié entre-temps à `241db66fcaf4ed602782d0fce1f6fb019c2e88b5` est conservé sans modification de ses preuves datées.

## Recherche approfondie après la première reprise

Demande : retrouver tous les éléments BOJ.ART/Jarvis encore accessibles. Inventaire de 722 fichiers, contexte des anciens échanges, historique Higgsfield, Pages et recherches Drive/Notion/Gmail. Résultat : 62 originaux supplémentaires dédoublonnés, conservés sur `archive/deep-recovery-2026-11-01` au commit `81d43e7910f17ebb85fdccab244b3f53bf360f9d`. Les 76 fiches fournisseur sont conservées avec leurs paramètres ; aucun rendu nouveau lancé. Une notice déjà présente dans main est référencée sans copie.

Validation : 62 fichiers, 390 425 092 octets restaurés depuis GitHub, comparaison octet par octet et SHA-256, aucun recouvrement avec les 3 340 objets initiaux ; contrôles de format et 11 gardes du restaurateur réussis. L’environnement initial est tombé en panne pendant la collecte ; tous les médias du complément ont été récupérés à nouveau avant la vérification distante. Les synthèses de recherche restent explicitement distinctes des transcriptions originales. État et limites : `docs/RECUPERATION_APPROFONDIE_2026-11-01.md` ; preuve : `docs/evidence/deep-recovery-2026-11-01.json`.

## Continuité des réponses et fraîcheur de l’historique

Demande : poursuivre la préparation de la mémoire Jarvis avant l’installation. Base examinée : `7ac120994cdcf6102b6b2a353bf7805e2ac1fbc2`, contrôles GitHub réussis. Les 62 originaux de récupération récemment ajoutés et leurs preuves sont conservés.

Constat : le client Ollama transmettait les 6 000 derniers caractères du JSON des épisodes, avec un risque de couper une question et de réutiliser une ancienne réponse après modification de ses sources. Le nouveau paquet conserve des champs complets, contrôle versions et originaux, écarte les réponses aux preuves périmées ou contradictoires et partage l’instantané du contexte courant. Les journaux originaux restent disponibles, ainsi que le paquet exact de chaque nouvelle inférence. Guide indexé : `docs/memory/CONVERSATIONS.md`.

Vérifications locales : 17 scénarios ciblés réussis avec client Ollama simulé, plus les tests sélectionnés de mémoire, contexte, transactions, diversité et MCP. Le workflow mémoire exécute les suites complètes et la reprise du lanceur sous Windows et Linux sur la révision publiée. La qualité d’un modèle réel et la tour BOJ.ART restent à qualifier.
