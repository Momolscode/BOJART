# Preuve — banc de simulation pré-installation de Jarvis

2 novembre 2026. Révision mesurée : `860aaaf9bf401ea041b619897033456d681566b4` (branche `claude/project-thread-0y7gbd`, sans modification locale). Base `main` : `3436f5352659554e4bac5af492b94af6c522ed2d`.

Rapports bruts : [banc-linux.json](banc-linux.json) et [banc-linux.md](banc-linux.md), produits par `tools/banc_preinstallation.py --reseau`. Seule modification après exécution : le chemin de l'interpréteur du conteneur est remplacé par `<venv Python 3.12 du conteneur>`. Les rapports ne contiennent ni jeton de session, ni base active, ni média, ni donnée client.

## Ce qui a été exécuté

Hôte : conteneur Linux x86_64, Python 3.12.3, LangGraph et CadQuery épinglés installés, Node présent. Ce n'est pas la tour Windows 11 / RTX 4060 Ti. Durée totale : 2 min 48 s.

| Bloc | Résultat |
|---|---|
| Suites | **947 tests exécutés** : `tests` 102, `tests_agent` 236, `tests_ops` 112, `tests_workflows` 20, `jarvis/tests` 280, `jarvis/apps/jarvis/tests` 63, `tests_m03` 52, base métier 41, Node 41. Aucune régression. 6 tests non exécutés faute de précondition (ci-dessous). |
| Scénarios HTTP | **16/16 réussis** contre le vrai `consolidated_workbench.py`, dont 1 avec réserve (charge). |
| Encodage Windows | cp1252 émulé (`LC_ALL=fr_FR.CP1252`, `PYTHONUTF8=0`) : 5 suites (462 tests) et 7 scénarios HTTP réussis ; seuls les 3 tests M07 manquent. |
| Roues Windows | 95 paquets résolus pour `win_amd64` / CPython 3.12, **aucun à compiler**. Résolution PyPI du jour, pas une installation. |
| Statique | 0 bloquant. Chemins Windows, scripts `.cmd`, syntaxe Python/JS, JSON, versions épinglées, provenance Three.js : OK. |
| Outils existants | `simulate_jarvis_workflows.py` (moteur `sqlite_ready`, 27 essais, 16 gardes et pannes), `validate_repository.py` (941 fichiers, 0 anomalie), `evaluate_memory.py`, `check_startup.py --abrupt` : OK. |

## Actions de Jarvis (36)

- **Simulé OK : 13** — installation des dépendances, lanceurs, démarrage sécurisé, orchestration LangGraph, charge (avec réserve), dashboards atelier et nommés, clarification et refus, recherche mémoire citée, MCP, socle CAO STL/STEP/GLB, répartition fictive du parc, intégrité du dépôt.
- **Partiel : 17** — 12 le sont uniquement parce que la suite `jarvis/tests` (ou sa reprise cp1252) contient 3 tests qui exigent les médias M07 d'exemple : le statut est calculé par suite et n'est jamais promu. Hydrater ces médias sur la tour est donc la précondition qui débloque le plus d'actions. Les autres : Studio (médias + navigateur), site Atelier (logo et polices hors dépôt), synthèse vocale, modèle local et montage vidéo (code volontairement incomplet : poids, service ou FFmpeg absents).
- **Non codé : 6** — figurine M08, découpe d'un mètre, tranchage (PR #15 en revue), inventaire et pilotage des imprimantes, devis.

## Mesures HTTP

Appels locaux sur l'hôte de test, sans rendu ni micro. Ce ne sont ni des latences vocales ni des délais d'affichage.

| Scénario | Mesure |
|---|---|
| Dashboard atelier | dépôt 42,2 ms, accusé 16,9 ms |
| Trois dashboards | dépôt 40,1 ms, 3 vues accusées |
| Socle CAO | construction 2 435 ms, STL étanche, plus grande dimension 180 mm |
| Arrêt brutal (SIGKILL) puis relance | tour `QUEUED`, commande unique, aucune double distribution |
| Annulation puis accusé tardif | `CANCELLED_AFTER_DISPATCH`, accusé refusé (409) |
| Base corrompue | refus de démarrer, aucune base recréée, message de restauration |
| 24 demandes simultanées | 2 acceptées d'emblée, 5 refus 429, 17 « EN ATTENTE » ; 22 reprises manuelles réussies, aucune perte ni doublon |

## Défauts trouvés puis corrigés

1. 9 lanceurs `.cmd` en fins de ligne LF seules, dont 4 avec étiquettes `goto`/`call`.
2. `Simuler_BOJART.cmd` sans `PYTHONUTF8=1`.
3. E/S texte sans encodage explicite dans le code exécuté (serveur, médiathèque, mesures, préinstallation, outils de lancement et de validation) ; un test mémoire échouait réellement en cp1252.
4. Base de travail corrompue : trace Python brute au lieu d'un message.
5. Le premier passage complet (`41c3f48`) a signalé deux appels du banc lui-même sans encodage : corrigés dans `860aaaf`, mesuré ici.

## Préconditions et constats ouverts

- Médias M07 d'exemple non hydratés : 4 tests (`HTTPTests` M03, deux tests M05, un test Growth).
- Navigateur : `test_preview_m03` et `test_studio_browser` visent `/usr/bin/chromium`, introuvable sous Windows.
- Site Atelier et vitrine Studio : `logo.webp`, `body.ttf`, `display.ttf` exclus du dépôt.
- 37 fichiers de tests et d'outils hérités lisent ou écrivent du texte sans encodage : mineur tant que les lanceurs gardent `PYTHONUTF8=1`.
- 83 dépendances transitives non épinglées pour Windows.
- La PR #15 épingle `trimesh==5.2.0`, `main` épingle `trimesh==4.11.1` : installation conjointe impossible en l'état.

## CI

Le workflow `Jarvis pre-installation bench` exécute le même banc sur `ubuntu-latest` et `windows-latest` et conserve ses rapports 30 jours. Résultats rattachés à leur SHA dans la PR #17.

## Limites

Simulation logicielle uniquement : aucun micro, moniteur physique, imprimante, modèle local, service distant ou publication. L'émulation cp1252 reproduit l'encodage des fichiers et sous-processus, pas la console ni le système de fichiers Windows. Prochaine preuve : `Banc_BOJART.cmd` sur la tour après installation, comparé au rapport CI Windows.
