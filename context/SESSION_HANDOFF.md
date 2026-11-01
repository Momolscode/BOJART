# Passation — consolidation du 1 novembre 2026

## Reprise : diagnostic des outils et du poste — 2 novembre 2026

Demande : poursuivre la préparation des outils et du lancement BOJ.ART. La PR #7 est fusionnée ; base actuelle examinée `a0500b39ddf5a6154c701c225c5b2ad80767cc70`, puis rapprochement des lanceurs publiés à `d5855c1e8c10f6ab57d7b362eb1d954c722b340b`. Leurs corrections sont préservées. La tour signalée par le connecteur est hors ligne ; aucun matériel cible n'est déduit de cet environnement de travail.

Ajouts : diagnostic local exécutable, raccourcis Windows/Linux, observation NVIDIA par carte et métadonnées de dix paquets Python, présence de neuf binaires dont quatre sondés pour leur version. Les sondes restent fixes et bornées ; les slicers, Ollama et le moteur Adobe ne sont pas démarrés. Les rapports datés restent hors du dépôt et distinguent présence, version et qualification. Le lanceur expose ce contrôle avec `--check-only --check-tools` ; son ouverture habituelle reste inchangée.

Le guide `docs/DIAGNOSTIC_OUTILS.md` est relié aux documents d'installation déjà indexés et à la tâche `target-inventory`, toujours bloquée sur l'accès au poste. Le corpus de référence sélectionné n'est pas élargi par une seconde copie détaillée des mêmes prérequis. Les 14 cas lexicaux existants sont conservés. Aucun modèle, outil tiers, connexion de compte ou imprimante activé.

Le contrôle GitHub a relevé les deux nouveaux raccourcis non classés après régénération du manifeste ; leur règle de classement est ajoutée, sans assouplir le test existant. Le passage Windows a également révélé une comparaison entre chemin long et alias 8.3 dans le test du rapport ; la comparaison porte désormais sur les deux chemins résolus, avec les mêmes contrôles de contenu et de non-écrasement. Tests et portée exécutée : `docs/evidence/environment-diagnostic-2026-11-02.json`. Les cas GPU sont synthétiques ; seul le diagnostic des outils présents dans cet environnement a été exécuté. Prochaine preuve : ouvrir `Diagnostic_BOJART` sur la tour, relever les champs restants, puis essayer un profil IA et les parcours créatifs sur ce matériel.

## Recherche des outils et qualification — 1 novembre 2026

Demande : enrichir BOJ.ART/Jarvis pour la 3D, la voix, le studio VFX, l'identité et le marketing. Revue de 18 dépôts à références épinglées et de documentations officielles ; 26 fiches, 14 besoins de données et 12 portes de recette dans `docs/research/launch-toolchain-2026-11-01/`. Aucun outil tiers installé ni génération payante ou publication lancée. La tour n'est pas accessible pour une qualification. Metricool n'est pas retenu dans cette demande ; repli proposé par données natives/exportées, sans prétendre les avoir collectées.

L'indexation de recherche a révélé une régression : l'état courant disparaissait des cinq premiers résultats d'un cas existant. Ajout d'une collection `research` dans la même mémoire, classification partagée entre CLI et agent, priorité aux sources de référence dans le lexical et la fusion sémantique, libellé explicite des propositions et retrait non destructif. Sept tests dédiés et quatre cas de recherche métier ajoutés. La destination historique du contexte marketing est corrigée vers `Momolscode/BOJART`. Les dépendances et portes physiques du runtime ne sont pas activées. Résultats exécutés : voir `docs/research/launch-toolchain-2026-11-01/VALIDATION.json`.

Base examinée `5268e7e7b70fa25efee7d186f27cd3716a49c4c1`, puis évolution distante `461d46ff39caaf142ce37a3e0b78f22dfcc2e842` rapprochée avant modification ; les corrections concurrentes de diversité de sources sont conservées. La nouvelle orchestration à `9f58fa29f0051cc8a7098855359a8a6dd0eef7e6` est également rapprochée, y compris ses entrées de mémoire. Prochaine preuve : qualification sur la tour et une machine, puis un plan sur la vraie œuvre et des statistiques de compte sourcées.


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

## Raccordement des recherches au pilotage

Réconciliation de la récupération approfondie (`7ac120994cdcf6102b6b2a353bf7805e2ac1fbc2`) avec la contribution outils/mémoire (`5e8a14415b816ac7aa840cb3409a1752943929da`). Les deux index documentaires sont réunis par projet et chemin ; les sources de récupération, la résilience et la collection research sont conservées. Le double paragraphe de mission est retiré de cette passation, sans suppression d'original historique.

Le plan relie les fiches d'outils, les besoins de données et les critères réels déclarés dans le runtime. Les calculs de dépendances restent descriptifs, sans installation ni qualification automatique. Seize scénarios dédiés couvrent les références, empreintes, exclusions, ordres stables et refus des validations fabriquées. Résultats exécutés : `docs/evidence/orchestration-integration-2026-11-01.json`. Aucun modèle, périphérique ou service payant lancé par cette intégration.

La première évaluation du corpus réuni réussissait 13 cas lexicaux sur 14 : ce journal repoussait le guide de gouvernance hors des cinq premiers résultats pour « restauration sauvegarde ». Classement dans `session_log`, étiquette historique et conservation des anciennes versions ajoutés ; cinq nouveaux scénarios vérifient migration, recherche et restauration. Les 14 cas passent après correction. La recette locale du vrai lanceur réussit également après arrêt forcé, redémarrage et restauration dans un nouveau dossier ; elle ne qualifie pas une coupure électrique, les modèles ou le matériel.

## Continuité des réponses et fraîcheur de l’historique

Demande : poursuivre la préparation de la mémoire Jarvis avant l’installation. Base examinée : `7ac120994cdcf6102b6b2a353bf7805e2ac1fbc2`, contrôles GitHub réussis. Les 62 originaux de récupération récemment ajoutés et leurs preuves sont conservés.

Constat : le client Ollama transmettait les 6 000 derniers caractères du JSON des épisodes, avec un risque de couper une question et de réutiliser une ancienne réponse après modification de ses sources. Le nouveau paquet conserve des champs complets, contrôle versions et originaux, écarte les réponses aux preuves périmées ou contradictoires et partage l’instantané du contexte courant. Les journaux originaux restent disponibles, ainsi que le paquet exact de chaque nouvelle inférence. Guide indexé : `docs/memory/CONVERSATIONS.md`.

Vérifications locales : 17 scénarios ciblés réussis avec client Ollama simulé, plus les tests sélectionnés de mémoire, contexte, transactions, diversité et MCP. Le workflow mémoire exécute les suites complètes et la reprise du lanceur sous Windows et Linux sur la révision publiée. La qualité d’un modèle réel et la tour BOJ.ART restent à qualifier.

Réconciliation supplémentaire avant publication : `0a7a08dd0a0bed445ef0dc5734be7c841b30467a` est conservé. Le contexte conversationnel borné, ses contrôles de fraîcheur et ses dix-sept scénarios restent intégrés à la mémoire commune. Les résultats consolidés figurent dans la preuve d’orchestration.

## Suite de l’audit : propositions après restauration

Base initialement examinée : `7ac120994cdcf6102b6b2a353bf7805e2ac1fbc2`, rapprochée de `0a7a08dd0a0bed445ef0dc5734be7c841b30467a` avant publication. Les modifications concurrentes de continuité des conversations sont conservées.

Deux défauts reproduits : une proposition visuelle préparée mais non distribuée restait courante après restauration ; une proposition CAO non exécutée pouvait encore atteindre le constructeur avec son ancienne confirmation. La restauration révoque désormais ces propositions. Les octets des propositions visuelles et des reçus restent conservés ; les résultats CAO déjà enregistrés se rejouent sans recalcul. Aucune réexécution automatique n’est ajoutée.

Six nouveaux tests couvrent le refus des anciennes demandes, les nouvelles demandes, les reçus terminés, la compatibilité des anciennes sauvegardes, le redémarrage et une seconde sauvegarde/restauration. Ils sont intégrés à la suite `tests` exécutée par le workflow mémoire sous Windows et Linux. Vérifications locales complémentaires : 64 tests d’orchestration M06/M07, 44 tests de régie M04, 31 tests M05 sans médias privés et 7 tests de fermeture SQLite réussis. Trois cas M05 restent non validés ici faute des médias d’exemple ; aucune qualification CAO réelle, voix, écran ou imprimante n’est revendiquée. Les résultats CI et les empreintes du commit sont consignés dans le reçu de continuation de `audit/context-results`.

Rapprochement du pilotage : le correctif de restauration `9c2a0fb47baf1b610e31d2deb800a5323bb9495e` est conservé avec ses six scénarios. La preuve d’orchestration est actualisée sur le corpus et le code réunis.

## Modèles facultatifs et premier lancement

Base examinée : `0a7a08dd0a0bed445ef0dc5734be7c841b30467a`, contrôles GitHub réussis. Demande : continuer la préparation de Jarvis.

Défaut reproduit : un `models.json` invalide interrompait la recherche et le statut avant le repli lexical. La configuration est désormais validée séparément ; la recherche reste exploitable, avec un état de modèle explicite. Les contrôles d’intégrité des sources restent bloquants pour les faits altérés.

Ajouts : diagnostic local sans inférence ni création de base, contrôle des capacités déclarées avant configuration, préservation d’un port local existant, écriture atomique des réglages et intégration au diagnostic de lancement. Guide indexé : `docs/memory/MODELES_LOCAUX.md`. L’API Ollama officielle a été relue ; aucun modèle n’a été téléchargé ou qualifié.

Vérification locale : 20 nouveaux cas avec un serveur de métadonnées simulé, erreurs de configuration, modèles absents, capacités incompatibles, référence distante, panne et échec d’écriture. Un cas HTTP du panneau est ajouté à la recette complète Windows/Linux. Les résultats par commit distinguent ces contrôles logiciels de l’essai réel sur la tour.

Réconciliation : le classement des recherches et journaux, l’indexation commune, la priorité aux références et les corrections de restauration du commit `54f245ba852a8d1c611d96d818ee36d1aa5adba9` sont conservés.

## Suite de l’audit : sources et réponses de l’interface — 2 novembre 2026

Base examinée : `4be8480b653d98b4744b5a59ca89d2ee1d732d6e`. Les corrections de restauration, l’indexation des recherches et journaux et la configuration des modèles facultatifs sont conservées.

Défauts reproduits : le Studio supposait la présence de `visage`, `profil` et `troisquarts`, y compris sur un catalogue vide ; Growth pouvait afficher un ancien brouillon après changement de compte ou de passages. Le Studio propose maintenant les références et passages admissibles du catalogue, transmet leurs révisions exactes et invalide le brief lors d’une modification. Les réponses tardives de préparation et de vérification sont ignorées dans les deux interfaces. Les miniatures statiques ne sont utilisées que dans l’aperçu hors ligne ; un identifiant de passage ne prouve pas qu’une image appartient au fichier actuel. L’exemple hors ligne reste lié à sa sélection précalculée.

Validation locale : treize nouveaux tests JavaScript, intégrés au workflow de continuité ; 52 tests mémoire/HTTP, 99 tests agents, 50 tests du catalogue média et 53 tests Growth réussis. Six contrôles supplémentaires utilisent le vrai serveur HTTP et SQLite avec médias de test explicitement fictifs : catalogue vide, ressources de l’interface, identifiants personnalisés, référence hors montage, brief vérifié et brouillon non publié. Les tests de miroir des skills et de média privé de la suite Growth ne sont pas inclus dans ce passage local. Chromium n’étant pas installé dans cet environnement, aucune nouvelle recette visuelle ou de lecture vidéo n’est revendiquée. Les contrôles distants et le reste de la revue sont consignés dans le reçu sur `audit/context-results`.

## Sélection et préparation des modèles locaux — 2 novembre 2026

Demande : trouver les meilleurs candidats locaux et avancer vers un Jarvis opérationnel, cohérent et réactif. Base examinée : `4be8480b653d98b4744b5a59ca89d2ee1d732d6e`. Matériel BOJ.ART toujours inconnu ; aucune inférence à partir des machines UNUM/M-Tek.

Recherche dans les fiches Qwen, Google, Ollama, Mistral, Black Forest Labs et Wan-AI. Choix d'essai : Qwen3.5 4B pour la charge réduite, Gemma 4 12B pour le compromis, Qwen3.8 27B pour la capacité, Qwen3 Embedding 0.6B pour l'index. FLUX.2 Klein 4B est proposé pour une étape créative distincte ; aucun générateur n'est raccordé par ces profils.

Ajouts : plan hors ligne, téléchargement explicite des seuls modèles manquants, contrôles synthétiques avec mesures, indexation de la base existante puis activation atomique. Identités des modèles contrôlées avant/après inférence et entre lots d'embeddings. Le programme rapporte les limites de mesure ; les réglages explicites n'impliquent pas une latence garantie. Les commandes connues M07 utilisent déjà leur résolution locale ; aucun pouvoir machine n'est ajouté au panneau Mémoire.

Les contrôles avec serveur local simulé vérifient erreurs, changements de tag, refus d'activation, conservation des réglages, index unique et paramètres transmis. Les tests de CI portent sur le logiciel exact sous Windows/Linux ; seuls des essais sur la tour pourront prouver les modèles et temps réels. Aucun poids téléchargé ici et aucun résultat artistique nouveau.

Réconciliation : les améliorations concurrentes du Studio/Growth et leurs treize tests d’interface, publiées au commit `20283c3136c66fbfca78a9e733b5c74bd5dfcf03`, sont conservées.

## Suite de l’audit : lanceurs historiques — 2 novembre 2026

Base examinée : `20283c3136c66fbfca78a9e733b5c74bd5dfcf03`. Les contrôles GitHub de cette base et le reçu Studio/Growth `870896c1f1f313ce64479894a1d174fc34073808` sont réussis.

Défauts reproduits : les lanceurs de `jarvis/` et `jarvis/apps/jarvis/` démarraient directement le serveur sans les contrôles et l'indexation du lanceur BOJART, et ignoraient le Python installé dans `.venv` à la racine. Le raccourci shell d'ouverture d'un dossier essayait d'exécuter un script suivi sans permission d'exécution. Les raccourcis de restauration choisissaient également un autre environnement. Les lanceurs rejoignent maintenant le point d'entrée canonique ; la restauration choisit son environnement installé, les appels shell passent explicitement par Bash et les scripts Windows conservent le code d'erreur après leur pause. Le repli des paquets historiques séparés est conservé.

Validation locale : dix tests exécutent les vrais scripts contre des programmes Python de contrôle et des environnements isolés, sans installation de dépendances ni accès réseau. Ils vérifient les arguments, les espaces/accents, la sélection Python, le choix de dossier et les erreurs. Quatre contrôles HTTP supplémentaires vérifient le téléchargement exact d'une sauvegarde, sa restauration dans un nouveau dossier, les accès authentifiés et les longueurs de réponse ; cette voie existante fonctionne sans correction du serveur. Deux appels réels `--check-only` par les anciens lanceurs atteignent le diagnostic complet sans créer d'état ni appeler de fournisseur. La suite racine compte maintenant 66 tests, exécutés automatiquement sous Ubuntu et Windows ; ses résultats distants et la portée exacte sont consignés dans le reçu d'audit. Ces essais ne qualifient ni le poste cible ni ses moteurs optionnels.

Réconciliation avant publication : les profils de modèles et le contrôle d’identité pendant l’inférence du commit `a0500b39ddf5a6154c701c225c5b2ad80767cc70` sont conservés. Les documents communs ont été fusionnés ; le manifeste repart de cette nouvelle tête.
