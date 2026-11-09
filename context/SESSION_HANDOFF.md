# Passation — consolidation du 1 novembre 2026

## Installation prête — 9 novembre 2026

Demande d'Olsen : « Audit l'ensemble du projet. Je veux qu'il soit fonctionnel à son installation ce Jarvis. » Base `main` `3436f53`. Intégration sur `claude/project-thread-m5t36k` : #20 (avec #17), #18, #11, #15, #21, conflits du manifeste régénérés, `SESSION_HANDOFF` réuni, `index.json` fusionné champ par champ. Laissées à part : #14 (bras peintre, conflits nombreux, sans effet sur l'installation), #16 (recettes Veille), #19 (fiche STRATES), #1 (surveillance de `main`).

Décisions : installer depuis une copie sans Git doit marcher comme depuis un clone (raison : « Download ZIP » est le chemin documenté) ; la voix est préparée par l'installateur avec l'accord unique déjà demandé (raison : sans poids ni réglage, le micro ne servait à rien après installation) ; la fin de prise garde sa règle d'origine et n'ajoute qu'une seconde façon de conclure, relative au fond sonore (raison : ne rien changer au calme, mesuré bon). Remplace le constat `voix-fin-de-prise-bruit-20261102` par `voix-fin-de-prise-bruit-20261109`.

Fichiers : `bojart_ops/banc_statique.py` (repli manifeste et `.gitignore`), `bojart_ops/banc_simulation.py` (révision d'une copie sans Git), `tools/validate_repository.py`, `bojart_ops/voix_installation.py`, `tools/preparer_voix.py`, `bojart_ops/installation_tout.py`, `tools/installer_tout.py` (`--sans-figurine`), `tools/prepare_installation.py` (`--figurine`, sonde des imports), `jarvis/requirements-figurine.txt`, `figurine/pipeline.py` et `slicing.py` (UTF-8), `jarvis/apps/jarvis/app/voice_endpoint.js`, `Installer_Tout_BOJART.cmd`, `Diagnostic_BOJART.cmd` (CRLF), `data/preinstallation/actions-jarvis.json`, `INSTALLER_DEMAIN.md` (trois gestes en tête), `docs/BANC_VOIX.md`, workflow du banc ; tests `tests_ops/test_installation_prete.py` (11), `test_installation_tout.py` (17), 4 tests de fin de prise.

Tests exécutés : réinstallation complète depuis une copie sans Git de `3917f7a` (journal et banc dans `docs/evidence/installation-2026-11-09/`) : 1 148 tests sans régression, 16/16 HTTP, 2 actions en échec pour le seul verrou figurine ; voix avec les poids installés 37/40, 0 erreur critique, 15/15 cas d'erreur ; fin de prise avant/après sur 114 prises ; bruit seul 0 commande ; parcours navigateur des 8 pages. Limites : conteneur Linux, synthèse vocale, aucun matériel réel, Ollama non installé. Verrou figurine ajouté depuis l'artefact de la CI Windows de `db89f3a` (versions communes identiques aux verrous moteurs et voix). Prochaine preuve : installation et recette sur la tour (`Installer_Tout_BOJART.cmd`, `Banc_BOJART.cmd`, `Mesurer_Voix_BOJART.cmd`, vrai micro avec imprimante en marche).

## Débrief de la tour vers GitHub — 9 novembre 2026

Demande d'Olsen : Jarvis doit pouvoir pousser sur GitHub. Lecture retenue par l'assistant, à confirmer : Jarvis pousse son débrief, pas du code. Décisions : branche neuve `tour/debrief-AAAAMMJJ-HHMMSS`, jamais `main` (raison : le dépôt est public et un rapport de la tour ne vaut ni réception ni décision) ; seuls les rapports écrits par Jarvis partent (raison : aucun média, base ni donnée client hors de la tour) ; accord à l'écran, pas de déclenchement vocal (raison : une transcription n'est pas une instruction) ; la connexion reste celle de Git, aucun jeton lu ni gardé.

Fichiers : `bojart_ops/debrief_tour.py`, `tools/publier_debrief.py`, `Publier_Debrief_BOJART.cmd`, `bojart_ops/installation_tout.py` (Git par winget), `bojart_ops/banc_simulation.py` (`outil:debrief_simulation`), `data/preinstallation/actions-jarvis.json` (39 actions), `Mesurer_Voix_BOJART.cmd` (réutilise les poids posés par l'installateur), `docs/DEBRIEF_TOUR.md` ; tests `tests_ops/test_debrief_tour.py` (22), `test_installation_tout.py` (19).

Tests exécutés : `publier_debrief.py essai` 12/12 sur un faux dépôt distant ; `--simulation` face au vrai dépôt, rien poussé (`docs/evidence/debrief-tour-2026-11-09/`). Limites : aucune poussée réelle, ni connexion GitHub de la tour, ni `cmd.exe`. Prochaine étape : sur la tour, `Publier_Debrief_BOJART.cmd` après l'installation, puis lecture de la branche par un fil de travail.

## Chaîne vocale simulée — 2 novembre 2026

Demande d'Olsen (option « chaîne vocale simulée ») : tester « Affiche le dashboard atelier » de bout en bout sans la tour, mesurer chaque étape (médiane, p95, max, erreurs, froid/chaud) pour comparer ensuite avec la tour, y compris bruit, commande inconnue, coupure et réponse tardive. Branche reposée sur la PR #17 (correctif PyAV 18.1.0, verrou voix, `tools/verifier_voix.py`) pour ne pas dupliquer son banc.

Décision : ajouter au décodage de `voice.py` un vocabulaire (`initial_prompt`) avec les mots du catalogue. Raison : sans lui, `small` ne reconnaissait la commande cible que 12 fois sur 80 (« dash beau d'atelier », « Jarvi ») ; avec, 65/80, sans erreur critique, négations toujours refusées, aucune commande inventée sur du bruit seul. Le routeur reste exact. Proposé, non codé : accepter le singulier de « dossiers », « contenus », « trois dashboards » (+7 commandes par mesure, aucun affichage dangereux) ; fin de prise adaptée au bruit ; filtre des phrases fantômes de Whisper.

Fichiers : `bojart_ops/banc_voix.py`, `bojart_ops/voix_corpus.py`, `tools/banc_voix.py`, `tools/banc_voix_navigateur.cjs`, `tests_ops/test_banc_voix.py` (17 tests), `Mesurer_Voix_BOJART.cmd`, `.github/workflows/voice-bench.yml`, `docs/BANC_VOIX.md`, `docs/evidence/voix-2026-11-02/`, `jarvis/apps/jarvis/app/voice.py`, `jarvis/apps/jarvis/tests/test_m02.py`. Corpus (WAV hors Git) déposé dans le dossier partagé du projet : `banc-voix/corpus-voix-2026-11-02.zip`.

Résultat sur conteneur Linux (Xeon 2,1 GHz, 4 cœurs, sans GPU) : 830 prises, 0 erreur critique, 15/15 cas d'erreur à chaque mesure ; référence `small` au commit `dad184c` : transcription 1 001 ms, de la fin de prise au reçu 1 090 ms, bout en bout 2,2 s au calme, 13,9 s avec imprimante (prise arrêtée par la limite de 15 s). `base` : 0/80 ; `large-v3-turbo` sans vocabulaire : 43/80 en 3,9 s. Limites : voix de synthèse, bruit synthétique, traitements audio du navigateur non simulés, vues sans rendu. Prochaine preuve : `Mesurer_Voix_BOJART.cmd` sur la tour avec le même corpus, comparaison avec `small-reference.json`, puis prises au vrai micro dans l'atelier.

## Banc de simulation pré-installation — 2 novembre 2026

Demande d'Olsen : simuler chaque action que Jarvis devra passer et trouver erreurs, corruptions et améliorations avant l'installation sur la tour. Base `3436f5352659554e4bac5af492b94af6c522ed2d` ; PR #15 (M08) et #16 (contenu) examinées, non modifiées. Le défaut `three.core.js` signalé par la PR #15 est déjà corrigé sur `main` (empreinte conforme à la provenance r180).

Ajouts : catalogue de 38 actions (dont l'installation complète en une fois et la collecte guidée), banc `bojart_ops/banc_*.py` et `tools/banc_preinstallation.py`, lanceur `Banc_BOJART.cmd`, workflow Linux/Windows `preinstall-bench.yml`, 16 tests du banc. Corrections : 9 `.cmd` en CRLF (4 avec étiquettes), `PYTHONUTF8` dans `Simuler_BOJART.cmd`, encodage UTF-8 explicite dans le serveur, la médiathèque, les mesures, la préinstallation et les outils de lancement/validation (manifeste en LF), fixture de test mémoire, message clair quand une base de travail est illisible ; chemins canoniques dans l'outil de restauration d'archive et un test de médiathèque (noms courts 8.3 sous Windows, trouvés par la CI Windows du banc). Les suites Jarvis passent avec les mêmes exclusions explicites qu'avant (médias M07). Verrou d'installation Windows : `bojart_ops/verrou_dependances.py`, `tools/verrouiller_dependances.py`, verrous `jarvis/locks/windows-cp312-{moteurs,voice}.txt` générés par la CI Windows (82 + 24 paquets avec empreintes), installés par `prepare_installation.py` sous Windows (`--require-hashes --no-deps`, puis `pip check`) et contrôlés par le banc (`statique:verrou_installation`). Pas encore installés sur la tour. Installation complète en une fois : `Installer_Tout_BOJART.cmd` → `tools/installer_tout.py` (`bojart_ops/installation_tout.py`) : plan, un seul accord, winget pour Ollama/FFmpeg, Jarvis complet, modèles `speed`, banc, journal dans `~/BOJART/installation/` ; simulé par le banc (`outil:installation_tout_simulation`) et 15 tests, pas encore lancé sur la tour. Collecte guidée : `Collecter_BOJART.cmd` → `tools/collecte_guidee.py` (`bojart_ops/collecte.py`) : dossiers désignés une fois, copie vérifiée par SHA-256 dans `~/BOJART/collecte/originaux`, sans écrasement ni modification des sources, textes et `conversations.json` des exports ChatGPT en mémoire comme données non vérifiées ; simulation de bout en bout (13 contrôles, `outil:collecte_simulation`) et 14 tests. Emplacement réel des vidéos d'Olsen encore inconnu. Voix : `av==18.1.0` épinglé (PyAV 19 retire `metadata_errors`, appelé par faster-whisper 1.2.1 : chaque transcription échouait) ; contrôle `tools/verifier_voix.py` (`outil:voix_decodage`) ; la CI installe moteurs et voix par `prepare_installation.install_commands` avant le banc. Verrou voix Windows régénéré par la CI (seul `av` change) ; CI Windows verte au commit `46a9df9` avec ce verrou et le décodage réussi (preuve `docs/evidence/banc-preinstallation-2026-11-02/ci-windows-46a9df9.json`).

Mesuré à `860aaaf` : 947 tests, 16/16 scénarios HTTP (1 réserve de charge), cp1252 et 95 roues Windows sans compilation ; actions 13 simulées OK, 17 partielles (12 à cause des seuls médias M07), 6 non codées. Vérifications et limites : voir `docs/evidence/banc-preinstallation-2026-11-02/`. Aucun micro, moniteur physique, imprimante, modèle local, service distant ou publication. Prochaine preuve : exécuter `Banc_BOJART.cmd` sur la tour après installation et comparer au rapport CI Windows.
## Reprise : diagnostic des outils et du poste — 2 novembre 2026

Demande : poursuivre la préparation des outils et du lancement BOJ.ART. La PR #7 est fusionnée ; base actuelle examinée `a0500b39ddf5a6154c701c225c5b2ad80767cc70`, puis rapprochement des lanceurs publiés à `d5855c1e8c10f6ab57d7b362eb1d954c722b340b`. Leurs corrections sont préservées. La tour signalée par le connecteur est hors ligne ; aucun matériel cible n'est déduit de cet environnement de travail.

Ajouts : diagnostic local exécutable, raccourcis Windows/Linux, observation NVIDIA par carte et métadonnées de dix paquets Python, présence de neuf binaires dont quatre sondés pour leur version. Les sondes restent fixes et bornées ; les slicers, Ollama et le moteur Adobe ne sont pas démarrés. Les rapports datés restent hors du dépôt et distinguent présence, version et qualification. Le lanceur expose ce contrôle avec `--check-only --check-tools` ; son ouverture habituelle reste inchangée.

Le guide `docs/DIAGNOSTIC_OUTILS.md` est relié aux documents d'installation déjà indexés et à la tâche `target-inventory`, toujours bloquée sur l'accès au poste. Le corpus de référence sélectionné n'est pas élargi par une seconde copie détaillée des mêmes prérequis. Les 14 cas lexicaux existants sont conservés. Aucun modèle, outil tiers, connexion de compte ou imprimante activé.

Le contrôle GitHub a relevé les deux nouveaux raccourcis non classés après régénération du manifeste ; leur règle de classement est ajoutée, sans assouplir le test existant. Le passage Windows a également révélé une comparaison entre chemin long et alias 8.3 dans le test du rapport ; la comparaison porte désormais sur les deux chemins résolus, avec les mêmes contrôles de contenu et de non-écrasement. Tests et portée exécutée : `docs/evidence/environment-diagnostic-2026-11-02.json`. Les cas GPU sont synthétiques ; seul le diagnostic des outils présents dans cet environnement a été exécuté. Prochaine preuve : ouvrir `Diagnostic_BOJART` sur la tour, relever les champs restants, puis essayer un profil IA et les parcours créatifs sur ce matériel. Rapprochement final avec `2025ac1c8f376341532fbd2df8a176b0b8fc3de4` : le GPU déclaré RTX 4060 Ti, les 8 Go visibles sur la photo et le parcours compact sont conservés. La photo ne remplace pas le relevé du pilote, de la mémoire disponible et des performances. Les 295 tests Python, 14 recherches et la recette du lanceur passent sur le corpus réuni.

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

## Sources de production reliées aux archives — 2 novembre 2026

Base rapprochée : `20283c3136c66fbfca78a9e733b5c74bd5dfcf03`, après les correctifs de modèles locaux et de sélection Studio/Growth. Le rapprochement par empreinte identifie les cinq médias R03 dans la collecte initiale ; leurs noms de stockage différaient des chemins attendus par le montage. Le plan expose ce lien, et `tools/prepare_production.py` prépare une copie de travail externe vérifiée avec les recettes courantes.

Les originaux et les anciennes versions sont préservés. Aucune génération, publication ou validation artistique n'est ajoutée ; TEST19 reste provisoire et G2 manque toujours. Guide : `docs/creative/RECUPERATION_PRODUCTION.md`. Recette, empreintes et limites : `docs/evidence/production-recovery-2026-11-02.json`.

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

Réconciliation du raccordement des médias : la préparation des profils locaux et le contrôle des identités de modèles publiés à `a0500b39ddf5a6154c701c225c5b2ad80767cc70` sont préservés. Les sélections documentaires des deux contributions sont réunies par projet et chemin.

## Suite de l’audit : lanceurs historiques — 2 novembre 2026

Base examinée : `20283c3136c66fbfca78a9e733b5c74bd5dfcf03`. Les contrôles GitHub de cette base et le reçu Studio/Growth `870896c1f1f313ce64479894a1d174fc34073808` sont réussis.

Défauts reproduits : les lanceurs de `jarvis/` et `jarvis/apps/jarvis/` démarraient directement le serveur sans les contrôles et l'indexation du lanceur BOJART, et ignoraient le Python installé dans `.venv` à la racine. Le raccourci shell d'ouverture d'un dossier essayait d'exécuter un script suivi sans permission d'exécution. Les raccourcis de restauration choisissaient également un autre environnement. Les lanceurs rejoignent maintenant le point d'entrée canonique ; la restauration choisit son environnement installé, les appels shell passent explicitement par Bash et les scripts Windows conservent le code d'erreur après leur pause. Le repli des paquets historiques séparés est conservé.

Validation locale : dix tests exécutent les vrais scripts contre des programmes Python de contrôle et des environnements isolés, sans installation de dépendances ni accès réseau. Ils vérifient les arguments, les espaces/accents, la sélection Python, le choix de dossier et les erreurs. Quatre contrôles HTTP supplémentaires vérifient le téléchargement exact d'une sauvegarde, sa restauration dans un nouveau dossier, les accès authentifiés et les longueurs de réponse ; cette voie existante fonctionne sans correction du serveur. Deux appels réels `--check-only` par les anciens lanceurs atteignent le diagnostic complet sans créer d'état ni appeler de fournisseur. La suite racine compte maintenant 66 tests, exécutés automatiquement sous Ubuntu et Windows ; ses résultats distants et la portée exacte sont consignés dans le reçu d'audit. Ces essais ne qualifient ni le poste cible ni ses moteurs optionnels.

Réconciliation avant publication : les profils de modèles et le contrôle d’identité pendant l’inférence du commit `a0500b39ddf5a6154c701c225c5b2ad80767cc70` sont conservés. Les documents communs ont été fusionnés ; le manifeste repart de cette nouvelle tête.

Raccordement des médias : les lanceurs unifiés et les contrôles de téléchargement de sauvegarde, rapprochés jusqu’à `d5855c1e8c10f6ab57d7b362eb1d954c722b340b`, sont conservés. Les essais des deux contributions sont relancés ensemble.

## Adaptation au poste RTX 4060 Ti — 2 novembre 2026

L'utilisateur nomme une RTX 4060 Ti ; la photo fournie affiche 8 Go de mémoire graphique, 16 Go de RAM, un Ryzen 5 5600G et Windows 11 Professionnel Insider Preview 25H2. Le registre conserve les statuts `source_reported`, remplace l'ancienne inconnue de système par une affirmation sourcée et ne conserve ni photo ni identifiants Windows dans Git. Les 932 GB affichés ne sont pas l'espace libre. Cette information ne constitue pas un diagnostic exécuté sur le poste.

Base examinée : `a0500b39ddf5a6154c701c225c5b2ad80767cc70`. Profil d'essai retenu : `speed`, Qwen3.5 4B Q4_K_M + Qwen3 Embedding 0.6B ; contexte demandé 16384, sortie 512, think faux, keep_alive 300 secondes. L'installeur Windows dédié lance la préparation et les mesures existantes après installation de Python 3.12 et Ollama. Les autres profils restent disponibles pour d'autres matériels.

Le contexte de conversation réserve la place de la question, des instructions et de l'historique selon l'enveloppe UTF-8. Il sélectionne ensuite des faits et passages entiers, en une seule recherche, et conserve les originaux historiques. Les cinq nouvelles régressions couvrent les caractères multioctets, les longues conversations, le nombre d'appels, le plus petit contexte accepté et le refus avant réseau d'une question trop grande. Les tests de serveur simulé ne prouvent pas la qualité ou la vitesse d'un modèle réel. Les résultats exacts Windows/Linux sont à consulter dans les workflows du commit publié ; la tour reste à qualifier.

Le cas de recherche « GPU imprimantes » attend désormais le guide canonique `POSTE_RTX4060TI.md`, qui rassemble le GPU rapporté et les inconnues du parc. Son ancienne source attendue, le résumé `CURRENT.md`, a reculé au classement après l'ajout de ce guide ; la question et le seuil de cinq résultats restent inchangés. Le journal historique conserve les anciennes inconnues à leur date ; seul l'état courant est actualisé.

Réconciliation avant publication : les corrections des lanceurs historiques et leurs quatorze tests, publiés sur `d5855c1e8c10f6ab57d7b362eb1d954c722b340b`, sont conservés. Le guide d'installation et le journal ont été réunis ; le manifeste repart de cette tête.

## Reprise mémoire locale V4 du 2 novembre 2026

Base distante intégrée : `2025ac1c8f376341532fbd2df8a176b0b8fc3de4`. La copie locale ajoute les corrections des quatre défauts mémoire relevés en V3, avec nouvelles contre-épreuves. Lire `docs/memory/HARDENING_2026-11-02.txt` et la matrice de réception V4 livrée avant les audits historiques. Ne pas relancer automatiquement les demandes UNKNOWN et arrêter les anciens processus avant migration. Cette entrée ne prouve ni push GitHub ni recette du matériel.

Réconciliation du dossier de production : les informations matérielles sourcées, l’installeur RTX 4060 Ti et les contrôles de contexte compact du commit `2025ac1c8f376341532fbd2df8a176b0b8fc3de4` sont conservés avec la reconstruction des cinq médias R03. Le correctif de simulation de collision de dossiers est passé sous Windows et Linux au commit `0d853787285142292a70850a1e38c49ce45b385e`. Les contrôles de l’ensemble réuni sont consignés dans la preuve de récupération.

## Simulations mesurées — 2 novembre 2026

Demande : confirmer le push, trouver des simulations utiles et fournir des statistiques. Le push RTX 4060 Ti est vérifié sur `2025ac1c8f376341532fbd2df8a176b0b8fc3de4`. Les sources runtime/corpus de cette révision ont été comparées à leurs empreintes avant trois répétitions indépendantes en états temporaires sur un hôte Linux sans GPU NVIDIA détecté. Le code du banc et les corpus gardent leurs empreintes dans les rapports.

Résultats : 1 260 recherches, soit 14 questions répétées 90 fois, retrouvent la référence dans les cinq premiers résultats. Médiane 0,706 ms, p95 1,053 ms. Les paquets de 8 000 octets conservent cette référence précise dans 900/1260 cas, contre 1170/1260 à 13 000 octets ; plusieurs sources peuvent contenir la même réponse, ce n'est pas un score d'exactitude du modèle. Trois corpus de 5 000 documents synthétiques, 960 opérations mixtes avec huit workers sans erreur, 60 arrêts forcés et neuf autres scénarios de panne vérifiés. Sauvegarde/restauration : les documents et les 64 notes de chaque lot sont préservés. Les durées de file et de service restent séparées.

Ajouts : banc sans dépendance supplémentaire, rapports bruts, guide de lecture des limites, essai facultatif des modèles déjà installés avec 30 appels et télémétrie Ollama, raccourci Windows `Mesurer_BOJART.cmd` et workflow Ubuntu/Windows. AIPerf est documenté comme piste pour mesurer la première réponse et les intervalles entre tokens ; aucune installation n'est revendiquée. Aucune inférence de modèle réel, latence de commande physique ou qualité artistique n'a été mesurée ici.

Les corrections concurrentes de récupération des sources R03 publiées jusqu'à `70848b97dd59de037801628f6ec67c34b63e56d7` sont conservées. Leurs nouveaux documents restent distincts du corpus figé utilisé pour ces statistiques. Résultats et limites : `docs/evidence/simulations-2026-11-02/README.md`.


## 2 novembre 2026 — simulations de demandes et de parc

Les alias exacts « affiche le dashboard atelier/dossiers/Studio/contenus/conception/base métier » et « affiche les trois dashboards » rejoignent le routeur local M07 ; une demande de dashboard sans nom demande une précision sans appel Jev. Les autres contrôles et le circuit de confirmation sont conservés.

Recette : docs/SIMULATIONS_ATELIER.md et docs/evidence/workflows-2026-11-02. Trois campagnes sur hôte Linux : 810 commandes (9 formulations répétées 90 fois), p95 dépôt 19,95 ms, p95 jusqu'au reçu synthétique 32,06 ms ; 16 scénarios de garde/reprise par campagne, tous passés. Ces mesures utilisent les vraies classes et SQLite avec un serveur minimal et des reçus factices, en repli sans LangGraph. Aucun son, navigateur, Jev, LLM ou GPU testé par cette recette. 20 tests dédiés passent localement.

Le simulateur de parc est séparé du runtime vocal : 24 volumes et 8 imprimantes fictifs, 25 h 15 à tour de rôle contre 21 h 24 par heuristique sur ces seules durées supposées ; 23 h 33 sur 7 machines avant démarrage. Pièce trop grande, procédé incompatible, résultat inconnu et changement d'échelle bloquent correctement. Aucune géométrie Végéta, découpe, durée réelle de slicer ou impression produite. La demande vocale de figurine reste CLARIFY. Nouveau lanceur Simuler_BOJART.cmd et tests/CI reproductibles, sans installation automatique ni accès aux machines.

Intégration mémoire : le long guide de simulation initialement indexé en référence courante faisait reculer CURRENT hors du top 5 pour LangGraph (13/14 cas). Correction : docs/COMMANDES_DASHBOARD.md est le catalogue canonique concis ; le rapport d'essais est un journal daté, et le guide complet reste lié. Les 14/14 cas repassent, sans modifier le moteur de recherche, les seuils ou les attentes. Voir les preuves retrieval-regression.json et retrieval-after.json dans le dossier d'essais.

Complément CI au SHA 13005fe924e0c092e87a99a82089c8ad15cf9b4c : 20 tests dédiés et 270 commandes dans chaque mode (règles puis LangGraph), sur Linux et Windows ; tous passent fonctionnellement. Attention à la latence Windows : LangGraph p95 740,895 ms, maximum 17 964,718 ms, sept essais > 1 s dont deux > 5 s. Règles seules : p95 375,076 ms, max 419,910 ms. Cause non isolée, aucune qualification de fluidité constante ni mesure du PC cible. Les quatre rapports CI et leurs empreintes sont conservés dans docs/evidence/workflows-2026-11-02 ; ne pas citer uniquement les chiffres Linux. Aucun changement du runtime de production n'est justifié par une attribution causale non démontrée.


## 2 novembre 2026 — réception HTTP et cohérence des sauvegardes

Une requête JSON authentifiée mais incomplète retenait le verrou global avant même d'être reçue : une seconde fenêtre ne pouvait plus créer de dossier. Le défaut a été reproduit sur les routes atelier, Studio et CAO. La réception est désormais bornée à 16 Kio et à douze lecteurs, hors du verrou de mutation, avec le délai de socket existant ; les opérations acceptées gardent leur verrou jusqu'à leur fin. Les limites plus petites de chaque route et les contrôles de session, origine, révision et confirmation restent appliqués. Les routes mémoire et voix conservent leur circuit distinct.

Un jeton de démarrage non ASCII provoquait aussi une coupure de connexion : il reçoit désormais un refus JSON 401. Les longueurs absentes, malformées ou dupliquées, les corps tronqués, les délais dépassés et la saturation sont refusés avant mutation. Treize nouveaux tests utilisent de vraies connexions HTTP et SQLite dans des dossiers temporaires, sans moteur vocal, modèle ni calcul géométrique. Le test de refus des liens symboliques dans les sauvegardes utilise maintenant une base toujours présente, sans dépendre des médias privés.

Vérifications locales : 98 tests racine, 64 tests M06/M07, 38 tests de console consolidée, 31 tests M05 et 20 tests de parcours réussis. Les trois autres cas M05 exigent les médias privés absents et ne sont pas déclarés validés. Les tests de sauvegarde pendant une mutation acceptée et de fermeture pendant une mutation passent. La branche distante c71628cf20426dd8b4bdedbab2dcf403f5135667, dont ses mesures Windows, est préservée. Les contrôles CI et la liste restante de l'audit sont consignés séparément sur audit/context-results. Aucun navigateur ni poste cible n'est qualifié par cette recette.

## Passation transversale locale V5 — 2 novembre 2026

Le lot distant c71628cf20426dd8b4bdedbab2dcf403f5135667 est intégré avec les correctifs mémoire V4. Lire docs/AUDIT_TRANSVERSAL_V5.txt et docs/research/audit-transversal-2026-11-02/ pour les corrections, les données et les propositions. La réception détaillée, la couverture des chats et les sources sélectionnées restent dans le paquet JARVIS_V5. Une copie locale corrigée ne signifie ni push, ni installation sur la tour.

## Publication du paquet V5 et session bras robotique — 2 novembre 2026

Objectif : pousser ce qui n'avait pas été publié, dont la session « bras robotique ». Sources reçues le 2 novembre : les deux ZIP du paquet V5, le PDF `STRATES_Audit_Robotique_IA_2026-11-02.pdf`, deux vidéos générées et le lien de la conversation ChatGPT `6ae7c762-6630-83eb-afde-680aa0c54b2e`.

Faits nouveaux. Le paquet est complet : 1 316 fichiers conformes à leur manifeste. La révision locale `754620639eef04835ec3be5fda71c8017a5958fe` n'existait pas sur GitHub. Ses 926 fichiers sont rejoués sur `c71628cf20426dd8b4bdedbab2dcf403f5135667` au commit `02be63cf7f7c8430cd09cb60adf7ef5122492b92`, sans écart d'empreinte. Ils sont ensuite fusionnés avec `b49101e3acad6257e2d1a610dac5fb95ec0a8bfb` : les deux sections de passation sont conservées, le manifeste est régénéré et le bit exécutable de l'installeur shell est restauré. L'utilisateur rattache la conversation « Bras robotique précis » à BOJ.ART ; l'audit des chats V5 la laissait ambiguë. Elle renvoie 403 sans compte et n'a pas été lue.

Décisions. Le dépôt est public : le PDF STRATES, son texte, ses montants, le nom du partenaire et les vidéos restent hors Git. Il en va de même des 282 fichiers du paquet que V5 gardait déjà hors du dépôt. Une synthèse publique, l'identité des originaux et les calculs recalculés sont ajoutés. Cinq affirmations sont inscrites au registre :

- publication observée ;
- rattachement décidé par l'utilisateur ;
- recommandation STRATES au statut de proposition ;
- calculs vérifiés ;
- portée limitée des vidéos.

Fichiers : `docs/evidence/handoff-v5-2026-11-02/`, `docs/research/strates-robotique-2026-11-02/`, `context/CURRENT.md`, `data/knowledge/` et le manifeste du dépôt.

Tests exécutés sur conteneur Linux, sans GPU. Réussis : `tests` 102, `tests_agent` 234, `tests_ops` 98, `tests_workflows` 20, Node 41, base métier 41, validateur. `jarvis/tests` et `jarvis/apps/jarvis/tests` ont les mêmes échecs que `main` non fusionné, faute de médias privés, de `cadquery`, de `playwright` et de `pytest`. Après ajout des deux documents indexés, ces suites repassent. L'évaluation de recherche garde ses 14 références sur 14 dans les cinq premiers résultats. Dans une mémoire temporaire indexée depuis le dépôt, la fiche STRATES sort au troisième rang pour « bras robotique STRATES peinture relief », après `CURRENT.md` et le registre. `verify` est OK.

Limites. Le corps de la conversation n'est pas lu. Les documents internes I1–I3 et les sources R1–R9 ne sont pas rouverts. Aucun essai physique, devis ou achat. Les binaires reçus ne sont pas archivés sur GitHub sans accord.

Prochaine preuve : fiche d'acceptation STRATES (G0) signée, puis coupons mesurés avec incertitude. Le choix d'un stockage privé pour le PDF, les vidéos, le texte de la conversation et les rapports V5 revient à l'utilisateur.

Correctif CI Windows : `OwnerLock` comparait le chemin résolu du dossier `.ask-locks` à son chemin absolu non résolu. Sous Windows, un nom court 8.3 du dossier temporaire suffisait à signaler une redirection : trois tests `test_ask_requests` échouaient. Un parent lié produit le même faux positif sous Linux ou macOS. L'état est désormais résolu avant comparaison ; seul un `.ask-locks` lien ou jonction reste refusé. Deux tests sont ajoutés : un parent lié est accepté, un dossier de verrous redirigé est refusé sans réservation. Le premier échoue sans la correction.

## Atelier : devis, suivi des demandes et parc simulé — 2 novembre 2026

Objectif : étape 3 du plan Jarvis, pendant que la figurine (PR #15), le contenu (PR #16) et le banc (PR #17) avancent. Demande : devis automatiques, suivi des demandes clients, vue et pilotage des imprimantes en mode simulé, sans commande machine réelle. Défaut signalé : Atelier 3D sans `three.core.js`.

Faits nouveaux. `three.core.js` est présent sur `main` : la visionneuse importe three r180 et crée un contexte WebGL dans Chromium. La copie publiée renvoie 401 et n'est pas vérifiable d'ici ; un redéploiement éventuel demande l'accord d'Olsen. Le calcul géométrique STL en Python pur donne les mêmes triangles, volume, surface et boîte que trimesh 4.11.1 sur les deux STL M08. Les sources consultées (Moonraker, OctoPrint, PrusaLink, Bambu, Elegoo, mentions du devis) et leur statut de lecture sont listés dans `docs/ATELIER_DEVIS_PARC.md`.

Décisions. Les tables atelier sont dans la base des missions, donc dans la sauvegarde globale existante. Aucune machine réelle ne reçoit d'ordre ; seule la lecture d'état peut y être autorisée, et elle est refusée tant qu'aucun connecteur n'est qualifié. Le téléversement Moonraker avec `print=true` ne doit jamais servir. La grille d'exemple ne peut pas émettre de devis.

Fichiers : `jarvis/apps/jarvis/app/atelier_*.py`, `atelier.html|js|css`, `jarvis/config/atelier/`, `jarvis/tests/test_atelier.py` et sa fixture PrusaSlicer, raccordements dans `consolidated_workbench.py`, `workspace_state.py`, `jarvis_runtime.py`, `tower_screen.js`, `workspace.html`, `jarvis/tools/m07_browser.cjs`.

Tests exécutés (conteneur Linux) : `test_atelier` 35/35 ; `tests` 102, `tests_agent` 236, Node 30 ; `jarvis/tests` 315 dont les 3 mêmes échecs que `main` faute de médias M07. Banc PR #17 sur l'arbre fusionné : +35 tests réussis, aucun autre écart. Détail : `docs/evidence/atelier-devis-parc-2026-11-02/VALIDATION.json`.

Limites : aucun prix, régime de TVA ni émetteur réels ; mentions du devis non relues sur source officielle ; aucun connecteur ; parc réel inconnu ; captures d'écran hors dépôt.

Prochaine preuve : grille et TVA déclarées puis devis à blanc relu ; inventaire du parc sur la tour ; une machine en lecture d'état avec opérateur.

## Atelier : relecture et améliorations — 2 novembre 2026 (soir)

Demande d'Olsen : « Prête, continue d'améliorer tout ça ». La PR #18 est passée en « prête ». Une relecture a trouvé quatre défauts, chacun couvert par un test qui échouait avant la correction :
- l'entonnoir ne comptait que les 200 demandes affichées ;
- les dates d'envoi et d'accord prenaient le jour de saisie ;
- un devis expiré restait déclarable envoyé ;
- la comparaison prévu / réel n'était pas chiffrée.

Ajouts :
- devis imprimable A4, avec lignes client au prorata exact du total HT et filigranes ;
- bloc commandes avec mesures opérateur nominatives, écarts par pièce et dérive par procédé ;
- délais de réponse en jours.

Tests : `test_atelier` 42/42 ; `jarvis/tests` 322 avec les 3 mêmes échecs que `main` ; `tests` 102, `tests_agent` 236, `tests_ops` 98, `tests_workflows` 20, Node 30. Parcours Chromium sans erreur console, PDF A4 d'une page. Détail : `docs/evidence/atelier-devis-parc-2026-11-02/VALIDATION.json` (section `ameliorations_soir`).

Limites inchangées : aucun prix, régime de TVA ni émetteur réels ; mentions légales non relues ; aucun connecteur d'imprimante.

Suite du soir : la grille tarifaire se déclare par un formulaire (plus de JSON à la main) :
- chaque déclaration est versionnée par empreinte, avec historique ; une déclaration concurrente est refusée ;
- le chiffrage désigne la grille courante par son empreinte ;
- un brouillon calculé avec une grille remplacée est signalé et son émission refusée ;
- le SIRET de l'émetteur est contrôlé par sa clé (règle de python-stdnum 2.1, La Poste comprise).

Tests : `test_atelier` 47/47, dont 5 nouveaux qui échouaient avant ; `jarvis/tests` 327 avec les 3 mêmes échecs que `main`. Parcours Chromium : SIRET faux refusé, deux versions de grille, brouillon périmé bloqué, révision, émission, PDF A4 d'une page. Banc #17 sur la fusion, trois passages : seul l'effectif des tests atelier change ; la répartition 429 / « EN ATTENTE » du scénario concurrent varie déjà de 2 à 9 refus sur le banc seul (preuves CI du banc et passages locaux). Détail : `VALIDATION.json`, section `grille_declaree`.

Point de vigilance trouvé par le banc : pour la question « LangGraph », `tools/evaluate_memory.py` attend `context/CURRENT.md`, classé 5e sur 5. Une phrase de plus dans la section Atelier de `CURRENT.md` l'a fait sortir sur l'arbre fusionné avec #17 (13/14 et un échec `tests_agent`). La phrase a été raccourcie : 14/14 sur les deux arbres. Tout ajout à `CURRENT.md` doit relancer cette évaluation.

## 2 novembre 2026 — preuve locale d'export vidéo/audio

Suite demandée : continuer puis pousser sur GitHub. La branche de diagnostic PR #11 est rapprochée du commit `b49101e3acad6257e2d1a610dac5fb95ec0a8bfb` ; récupération des sources R03, simulations et correction de réception HTTP sont conservées. Le diagnostic de matériel et de versions reste sans génération par défaut.

L'option `python tools/diagnose_environment.py --check-media --save --summary` encode une mire temporaire de deux secondes en H.264/AAC, contrôle 48 images à 24 i/s, les dimensions et durées, décode toutes les pistes et mesure le signal PCM. Une panne ou un outil absent renvoie 2 et conserve un reçu d'échec ; le fichier de test est nettoyé. Les commandes sont fixes, sans shell ni entrée média utilisateur. Le résultat ne qualifie aucune production, aucun GPU, Blender ou After Effects.

Preuve exécutée sur l'environnement Linux de développement : `docs/evidence/synthetic-media-check-2026-11-02.json`, export réussi, 96 256 échantillons PCM décodés, signal non silencieux, empreinte inchangée puis suppression du clip. Treize nouveaux tests de panne passent. Validation réunie : 129 tests racine, 135 tests agents et 83 tests opérations, plus 14/14 cas de recherche lexicale. Le manifeste public est régénéré et validé. Le job CI `media-export` réalise l'export avec FFmpeg sur Linux ; les tests Windows de ce module simulent les processus et ne prouvent pas un export sur la tour. Voir `docs/DIAGNOSTIC_OUTILS.md` pour les limites et les motifs d'échec.
## Veille des outils de conception 3D — 4 novembre 2026

Objectif : demande d'Olsen du 4 novembre (« chercher les données nécessaires pour la conception 3D, tous les outils dont on pourrait avoir besoin »). Base : `main` à `3436f5352659554e4bac5af492b94af6c522ed2d`, plus la branche de la PR #15 (chaîne M08) relue pour ne pas dupliquer.

Faits nouveaux. 161 fiches sourcées en cinq domaines : IA 3D locale, IA 3D en ligne et rig, modélisation et numérisation, préparation à l'impression, pilotage et données. Coûts 3D Higgsfield relevés par préflight sans job soumis : Tripo H3.1 de 6 à 12 crédits, Hunyuan3D v3 de 7 à 11, Meshy 7 de 25 à 38. Contradictions avec le dépôt : PrusaSlicer 2.7.2 contre 2.9.7 en amont ; Blender 4.0.2 contre 5.2.3 LTS (API Python changée en 5.2) ; TRELLIS.2 désormais natif dans ComfyUI sous Windows (int8 de 5,25 Go, 8 Go non mesurés) ; chemin par défaut de TripoSG non commercial (RMBG-1.4 et diso, vérifiés) ; exclusion UE de Hunyuan3D étendue à toute la famille ouverte. Les archives du site citent des Ender 5 Pro/Plus et Elegoo Saturn/Mars : indice, pas inventaire.

Décisions. Aucune adoption : les fiches sont des candidats, et l'ordre des essais est une proposition. Huit bancs sont décrits dans `BANCS.json`, tous non exécutés. B1 (88 crédits) attend l'accord de l'utilisateur.

Fichiers : `docs/research/conception-3d-2026-11-04/`, `data/knowledge/index.json`, `ops/orchestration.json` (tâche `conception-3d-bancs`), `context/CURRENT.md` et le manifeste du dépôt.

Limites. Lecture web seulement, recoupement partiel (`VERIFICATIONS.json`). Plusieurs prix restent marqués non vérifiés. Rien d'installé, d'acheté, de généré ni de mesuré sur la tour. Pas un avis juridique.

Prochaine preuve : B3, B4 et B5, qui tournent sans tour ni dépense ; puis l'inventaire réel des imprimantes, dont dépendent le trancheur, les profils et le pilotage.

Suite du 4 novembre, bancs gratuits (conteneur Linux, sans GPU, pas la tour). B1 a été approuvé par l'utilisateur à 13:21 UTC, mais le compte Higgsfield n'a que 0,65 crédit : rien n'est lancé ni débité. B3 : les contrôles M08 laissent passer une pièce de 400 mm (arrêtée ensuite par le trancheur), refusent les erreurs d'unités pour une fausse raison et plantent sur un STL tronqué ; la porte d'import proposée classe les 12 pièges, mais elle a été écrite en les connaissant. B4 : PrusaSlicer 2.7.2 reproduit au chiffre près le tranchage d'Ardoise v6 du 2 novembre ; 2.9.7 donne +0,2 % de temps ; OrcaSlicer 2.4.2 avec profil traduit +17,6 % de temps et +12,5 % de filament, dus à ses supports ; Orca chauffe sans M109. B5 : Ardoise à 1 m en 18 pièces avec 34 goujons, écart de remontage 0,00003 mm après correction des trous débouchants de la première exécution. Scripts et résultats : `docs/research/conception-3d-2026-11-04/bancs/`. Prochaine preuve : B1 après recharge ; intégrer la porte d'import et la découpe à la chaîne M08 avec tests.
