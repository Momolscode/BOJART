# Banc de simulation pré-installation — 2026-11-02

Révision `860aaaf9bf401ea041b619897033456d681566b4` (claude/project-thread-0y7gbd), modifications locales : non.
Hôte : Linux-6.18.44-fc-v185-x86_64-with-glibc2.39 ; Python testé : `<venv Python 3.12 du conteneur>` ; LangGraph : True ; CadQuery : True.

Simulation logicielle uniquement : aucun micro, moniteur physique, imprimante, modèle local, service distant ou publication.

## Synthèse

- 947 tests exécutés ; scénarios HTTP : {'ok': 15, 'ok_reserve': 1, 'echec': 0, 'non_execute': 0}.
- Actions : 36 — Non codé 6, Partiel 17, Simulé OK 13
- Constats : majeur 10, mineur 39

## Actions de Jarvis

| Domaine | Action | Banc | Hors simulation |
|---|---|---|---|
| Installation | Installer les dépendances épinglées sur Windows 11 / Python 3.12 | Simulé OK | Installation réelle sur la tour; Pilote NVIDIA et VRAM libre |
| Installation | Lancer, mesurer, simuler et restaurer par double-clic | Simulé OK | Exécution cmd.exe réelle sur la tour (la CI Windows couvre trois lanceurs) |
| Installation | Lire et écrire les textes français sans corruption sous Windows | Partiel | Console et page de code réelles de la tour |
| Démarrage | Démarrer le serveur local, ouvrir la session et refuser les accès étrangers | Simulé OK | Pare-feu Windows et antivirus de la tour |
| Voix | Réserver le micro pour une seule fenêtre et refuser l'audio non réservé | Partiel | Micro réel, bruit d'atelier, permission navigateur |
| Voix | Transcrire la parole en français, hors ligne | Partiel | Poids faster-whisper non livrés; Précision française et latence non mesurées |
| Voix | Répondre à voix haute | Partiel | Voix françaises installées sous Windows; Haut-parleurs |
| Voix | Confirmer à voix haute une proposition visuelle précise | Partiel | Phrase réellement prononcée et transcrite |
| Orchestration | Interpréter un tour, le garder, le distribuer et produire un reçu (LangGraph + checkpoint SQLite) | Simulé OK | Latence sur la tour (la CI Windows a montré un p95 de 740 ms) |
| Orchestration | Rejouer une même référence sans dupliquer, refuser une référence réutilisée | Partiel | — |
| Orchestration | Annuler un tour et ignorer un accusé tardif | Partiel | Écran physique qui a déjà commencé l'affichage |
| Orchestration | Reprendre après arrêt brutal sans perdre ni répéter une commande | Partiel | Coupure électrique réelle et cache disque Windows |
| Orchestration | Recevoir plusieurs demandes simultanées sans perte ni doublon | Simulé OK (réserve) | Charge réelle de la tour avec CAO et modèle local actifs |
| Orchestration | Refuser de démarrer sur une base de travail corrompue, sans la réinitialiser | Partiel | Disque réel défaillant |
| Écrans | Afficher le dashboard atelier sur l'écran gauche | Simulé OK | Rendu visible sur le moniteur physique; Le planning reste démonstratif |
| Écrans | Afficher les dashboards dossiers, Studio, contenus, conception, base métier | Simulé OK | Rendu visible sur les moniteurs physiques |
| Écrans | Composer les trois écrans et n'annoncer le succès qu'avec trois accusés | Partiel | Appairage des trois moniteurs réels; Déconnexion d'un écran |
| Écrans | Demander une précision ou refuser une phrase ambiguë, niée ou physique | Simulé OK | Transcriptions réelles imparfaites |
| Mémoire | Retrouver une information avec sa source et sa ligne | Simulé OK | Exports réels des conversations et documents de l'atelier |
| Mémoire | Exposer la mémoire aux assistants compatibles MCP | Simulé OK | Client MCP réel configuré sur la tour |
| Mémoire | Sauvegarder puis restaurer la mémoire et les cinq bases dans un dossier neuf | Partiel | Restauration complète sur la tour; Médias réels de l'atelier |
| Mémoire | Répondre avec le modèle local (Ollama, profil speed) | Partiel | Ollama et Qwen3.5 4B non installés ici; VRAM réelle de la RTX 4060 Ti |
| Jev | Proposer une intention visuelle quand la phrase n'est pas un ordre connu, avec confirmation | Partiel | Service Jev réel, clé, panne réseau et réponse lente |
| Studio | Choisir une référence authentique et des passages du brief | Partiel | Médias M07 d'exemple non hydratés dans le dépôt public; Vrais rushes de l'atelier |
| Contenus | Préparer un brouillon de publication relié aux médias, sans publier | Partiel | Comptes réels, droits, statistiques |
| Contenus | Monter et exporter une vidéo vérifiée (son, durée, format) | Partiel | FFmpeg sur la tour; Médias sources hors dépôt |
| Conception 3D | Créer un socle paramétrique confirmé et exporter STL/STEP/GLB | Simulé OK | CadQuery sur la tour (roues Windows à installer); Charge CAO pendant la voix |
| Conception 3D | Préparer une figurine originale : maillage, contrôles, socle, rendus, visionneuse | Non codé | Modèle génératif local (TripoSG à essayer); Droits des personnages tiers |
| Fabrication | Découper une sculpture d'un mètre en pièces imprimables avec assemblages | Non codé | Géométrie réelle; Profils machines |
| Imprimantes | Répartir des pièces sur le parc (procédé, matière, volume, disponibilité) | Simulé OK | Inventaire réel des imprimantes; Durées issues d'un trancheur |
| Imprimantes | Trancher une pièce avec le profil réel de la machine | Non codé | Profils réels du parc |
| Imprimantes | Inventorier modèle, procédé, volume, matière, état et interface de chaque machine | Non codé | Toutes les machines réelles |
| Imprimantes | Lire l'état puis, avec autorisation propre, chauffer, téléverser, démarrer | Non codé | Connecteur, arrêt d'urgence, supervision humaine |
| Devis | Préparer un devis (matière, temps machine, finition, marge, TVA) | Non codé | Tarifs réels, temps trancheur, règles HT/TTC |
| Sites | Charger la visionneuse 3D et l'identité visuelle du site Atelier | Partiel | Polices et logo exclus du dépôt; Rendu navigateur réel |
| Données | Garantir que les fichiers du dépôt ne sont ni corrompus ni altérés | Simulé OK | Bases actives et médias hors dépôt |

## Suites de tests

| Suite | Domaine | Tests | Résultat | Non exécutés (cause) |
|---|---|---|---|---|
| tests | Mémoire, lanceurs, installation | 102 | OK | — |
| tests_agent | Mémoire agent, MCP, modèles simulés | 236 | OK | — |
| tests_ops | Orchestration, préinstallation | 112 | OK | — |
| tests_workflows | Tours vocaux synthétiques, flotte fictive | 20 | OK | — |
| jarvis_tests | Runtime Jarvis M04–M07 (régie, voix, Jev, Studio, Growth) | 280 | Partiel | 3 |
| jarvis_app_tests | CAO M01–M02, interface et navigateur | 63 | OK | — |
| jarvis_app_tests_m03 | Bibliothèque Studio M03 | 52 | Partiel | 3 |
| metier | Base métier | 41 | OK | — |
| node_jarvis | Interface voix, mémoire, Studio/Growth (JS) | 41 | OK | — |

## Scénarios HTTP bout en bout

| Scénario | Résultat | Détail |
|---|---|---|
| http_demarrage_securite | OK | {"moteur_orchestration": "sqlite_ready", "jev": {"status": "disabled", "model": "jev-1.14.0", "role": "optional_text_decider", "live_verified": false, "audio_supported": false, "retries": 0, "timeout_seconds": 5, "automa |
| http_ecrans_appairage | OK | {"ecrans": ["atelier", "creation", "pilotage"]} |
| http_dashboard_atelier | OK | {"depot_ms": 42.2, "accuse_ms": 16.9} |
| http_dashboards_nommes | OK | {"Affiche le dashboard dossiers": {"depot_ms": 29.13, "accuse_ms": 18.3}, "Affiche le dashboard Studio": {"depot_ms": 26.07, "accuse_ms": 15.11}, "Montre le tableau de bord contenus": {"depot_ms": 26.12, "accuse_ms": 15. |
| http_trois_dashboards | OK | {"depot_ms": 40.05, "vues": 3} |
| http_clarification | OK | {"Affiche un des dashboards": "CLARIFY", "Affiche le dashboard": "CLARIFY"} |
| http_refus_physique_negation | OK | {"Lance l’impression de la figurine sur toutes les imprimantes": "CLARIFY", "Chauffe la buse à 220 degrés": "CLARIFY", "N’affiche pas le dashboard atelier": "CLARIFY", "Affiche le dashboard atelier et lance l’impression" |
| http_rejeu_idempotent | OK | {"rejeu": "QUEUED", "reference_reutilisee": 409} |
| http_annulation_recu_tardif | OK | {"statut_final": "CANCELLED_AFTER_DISPATCH", "accuse_tardif_http": 409, "accuse_tardif": "Ce navigateur ne possède pas cette commande."} |
| http_voix_sans_moteur | OK | {"sans_reservation": 409, "moteur_absent": 409, "message": "Micro désactivé ; aucun enregistrement.", "type_faux": 415} |
| http_concurrence | OK avec réserve | {"requetes": 24, "acceptees": 2, "refus_429": 5, "commandes": 2, "p50_ms": 46.0, "max_ms": 1076.1, "motifs_non_acceptes": {"429  Trop de requêtes.": 5, "200 NEW": 17}, "reprises_manuelles_reussies": 22, "reserve": "17 to |
| http_coupure_reprise | OK | {"statut_apres_coupure": "QUEUED", "commande_unique": true} |
| http_memoire_non_initialisee | OK | {"message": "La mémoire locale doit être initialisée avec le lanceur BOJART."} |
| http_growth_sans_publication | OK | {"cles": ["accounts", "capabilities", "notice", "rules", "skills", "topics", "version"]} |
| http_cao_socle | OK | {"construction_ms": 2435, "exports": ["socle.step", "socle.stl", "socle_metres.glb"], "stl_etanche": true, "plus_grande_dimension_mm": "180.0"} |
| http_base_corrompue | OK | {"base": "missions.sqlite3", "refus_au_demarrage": true, "message": " dossier de travail est illisible (file is not a database). Aucune base n’a été recréée. Restaurer une sauvegarde vérifiée dans un nouveau dossier (Res |

## Émulation de l’encodage Windows (cp1252)

Résultat : Partiel. Émulation sous Linux : encodage des fichiers et sous-processus comme Windows, pas la console ni le système de fichiers Windows.
- enc_tests_memoire : OK, 31 tests
- enc_tests_production : OK, 19 tests
- enc_tests_workflows : OK, 20 tests
- enc_jarvis_tests : Partiel, 280 tests
- enc_tests_ops : OK, 112 tests

## Roues Windows cp312

Résultat : OK — 95 paquets, 0 à compiler, 83 dépendances transitives non épinglées. Résolution PyPI du jour pour win_amd64/cp312 ; pas une installation ni un essai d’import sous Windows.

## Constats

| Sévérité | Contrôle | Fichier | Détail | Correction |
|---|---|---|---|---|
| majeur | suite:jarvis_app_tests_m03 | 1 test(s) | Médias d’exemple M07 non hydratés (tools/hydrate_m07_media.py avec l’archive M07 vérifiée). Non exécutés : HTTPTests | Fournir la précondition sur la tour avant la recette. |
| majeur | suite:jarvis_app_tests_m03 | 2 test(s) | Playwright Python ou Chromium absent ; ces tests visent aussi /usr/bin/chromium, introuvable sous Windows. Non exécutés : test_preview_m03, test_studio_browser | Fournir la précondition sur la tour avant la recette. |
| majeur | suite:jarvis_tests | 3 test(s) | Médias d’exemple M07 non hydratés (tools/hydrate_m07_media.py avec l’archive M07 vérifiée). Non exécutés : test_full_snapshot_reopens_with_all_work_and_relative_media, test_missing_media_makes_check_and_backup_fail, test_prepare_from_actual_studio | Fournir la précondition sur la tour avant la recette. |
| majeur | web_references | sites/atelier/dist/index.html | « ./assets/logo.webp » absent du dépôt (exclu par .gitignore : média à hydrater sur la tour). | Fournir le média ou un repli explicite ; vérifier le rendu après hydratation. |
| majeur | web_references | sites/atelier/dist/index.html | « ./assets/logo.webp » absent du dépôt (exclu par .gitignore : média à hydrater sur la tour). | Fournir le média ou un repli explicite ; vérifier le rendu après hydratation. |
| majeur | web_references | sites/atelier/dist/signature.css | « ./assets/logo.webp » absent du dépôt (exclu par .gitignore : média à hydrater sur la tour). | Fournir le média ou un repli explicite ; vérifier le rendu après hydratation. |
| majeur | web_references | sites/atelier/dist/style.css | « ./assets/body.ttf » absent du dépôt (exclu par .gitignore : média à hydrater sur la tour). | Fournir le média ou un repli explicite ; vérifier le rendu après hydratation. |
| majeur | web_references | sites/atelier/dist/style.css | « ./assets/display.ttf » absent du dépôt (exclu par .gitignore : média à hydrater sur la tour). | Fournir le média ou un repli explicite ; vérifier le rendu après hydratation. |
| majeur | web_references | sites/studio/app/vitrine.css | « /assets/display.ttf » absent du dépôt (exclu par .gitignore : média à hydrater sur la tour). | Fournir le média ou un repli explicite ; vérifier le rendu après hydratation. |
| majeur | web_references | sites/studio/app/vitrine.css | « /assets/body.ttf » absent du dépôt (exclu par .gitignore : média à hydrater sur la tour). | Fournir le média ou un repli explicite ; vérifier le rendu après hydratation. |
| mineur | http:http_concurrence | serveur Jarvis | 17 tour(s) restés « EN ATTENTE » pendant un traitement concurrent : la console exige un clic « Reprendre », sans nouvelle tentative automatique. |  |
| mineur | python_encodage | jarvis/apps/jarvis/tests/test_browser_m02.py | 6 lecture(s)/écriture(s) texte sans encodage explicite (lignes 18 read_text(), 19 read_text(), 21 read_text(), 88 write_text(), 101 write_text(), 106 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/apps/jarvis/tests/test_m02.py | 6 lecture(s)/écriture(s) texte sans encodage explicite (lignes 61 write_text(), 99 read_text(), 99 write_text(), 112 read_text(), 112 write_text(), 163 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/apps/jarvis/tests/test_mission01.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 108 write_text(), 154 read_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/apps/jarvis/tests/test_preview.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 11 read_text(), 22 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/apps/jarvis/tests/test_ui.py | 4 lecture(s)/écriture(s) texte sans encodage explicite (lignes 22 read_text(), 23 read_text(), 45 read_text(), 82 read_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/apps/jarvis/tests_m03/test_preview_m03.py | 3 lecture(s)/écriture(s) texte sans encodage explicite (lignes 15 read_text(), 31 read_text(), 43 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/apps/jarvis/tests_m03/test_studio_browser.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 40 read_text(), 52 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/knowledge/metier/tests/check_interface.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 16 read_text(), 57 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/knowledge/metier/tests/test_base_metier.py | 7 lecture(s)/écriture(s) texte sans encodage explicite (lignes 21 read_text(), 73 read_text(), 73 write_text(), 77 read_text(), 77 write_text(), 81 read_text(), 81 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tests/test_consolidated.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 50 read_text(), 50 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tests/test_growth.py | 4 lecture(s)/écriture(s) texte sans encodage explicite (lignes 60 read_text(), 60 write_text(), 107 read_text(), 111 read_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tests/test_preservation.py | 6 lecture(s)/écriture(s) texte sans encodage explicite (lignes 51 write_text(), 61 write_text(), 65 write_text(), 69 write_text(), 74 write_text(), 77 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tests/test_readiness_research.py | 4 lecture(s)/écriture(s) texte sans encodage explicite (lignes 26 read_text(), 26 read_text(), 28 read_text(), 31 read_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tests/test_tower_m04.py | 6 lecture(s)/écriture(s) texte sans encodage explicite (lignes 43 read_text(), 43 write_text(), 85 read_text(), 85 write_text(), 89 read_text(), 89 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tests/test_workspace_m05.py | 9 lecture(s)/écriture(s) texte sans encodage explicite (lignes 80 write_text(), 90 read_text(), 90 write_text(), 163 write_text(), 165 read_text(), 219 read_text(), 223 read_text(), 225 write_text() …). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompu | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tools/export_m07_graph.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 18 write_text(), 26 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tools/legacy_publish_github.py | 5 lecture(s)/écriture(s) texte sans encodage explicite (lignes 13 subprocess.run(text=True), 32 read_text(), 62 subprocess.run(text=True), 79 subprocess.run(text=True), 96 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDeco | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tools/m05_smoke.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 32 subprocess.run(text=True)). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tools/m06_smoke.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 30 subprocess.run(text=True), 34 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tools/m07_smoke.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 41 subprocess.run(text=True), 46 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tools/pc-audit-v1/audit_pc.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 7 subprocess.run(text=True)). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | jarvis/tools/render_m07_pipeline.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 62 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | productions/le-dernier-geste/R03_LE_DERNIER_GESTE/build_dernier_geste_r03.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 68 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | productions/le-dernier-geste/verify_assets.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 8 read_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests/test_archive_recovery.py | 5 lecture(s)/écriture(s) texte sans encodage explicite (lignes 21 write_text(), 25 read_text(), 47 write_text(), 67 read_text(), 67 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests/test_installation.py | 3 lecture(s)/écriture(s) texte sans encodage explicite (lignes 53 write_text(), 56 write_text(), 83 subprocess.run(text=True)). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests/test_memory.py | 6 lecture(s)/écriture(s) texte sans encodage explicite (lignes 90 write_text(), 127 write_text(), 133 read_text(), 133 write_text(), 137 write_text(), 142 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests/test_production_recovery.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 82 read_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_agent/test_agent.py | 3 lecture(s)/écriture(s) texte sans encodage explicite (lignes 112 write_text(), 139 write_text(), 176 subprocess.run(text=True)). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_agent/test_atomic_memory.py | 3 lecture(s)/écriture(s) texte sans encodage explicite (lignes 146 subprocess.run(text=True), 159 subprocess.run(text=True), 187 subprocess.Popen(text=True)). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_agent/test_benchmarks.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 38 read_text(), 92 read_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_agent/test_context_export.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 73 subprocess.run(text=True)). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_agent/test_model_setup.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 267 subprocess.run(text=True), 277 subprocess.run(text=True)). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_agent/test_research_indexing.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 95 subprocess.run(text=True)). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_agent/test_retrieval_diversity.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 52 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_ops/test_orchestration.py | 1 lecture(s)/écriture(s) texte sans encodage explicite (lignes 224 write_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | python_encodage | tests_ops/test_preinstallation.py | 2 lecture(s)/écriture(s) texte sans encodage explicite (lignes 87 write_text(), 90 read_text()). Sous Windows sans PYTHONUTF8=1 : cp1252, accents corrompus ou UnicodeDecodeError. | Passer encoding="utf-8" ; garder PYTHONUTF8=1 dans les lanceurs. |
| mineur | reseau:roues_windows | jarvis/requirements*.txt | 83 dépendances transitives non épinglées : l’installation de la tour peut résoudre d’autres versions que celles testées. | Générer un fichier de contraintes Windows cp312 avec empreintes. |

Un statut « Simulé OK » signifie que le logiciel se comporte comme prévu avec des doubles d’essai. Il ne qualifie ni la tour, ni le micro, ni les moniteurs, ni les imprimantes, ni la qualité artistique.
