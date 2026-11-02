# Banc de simulation pré-installation

État du 2 novembre 2026. Le banc rejoue **chaque action que Jarvis devra faire** sur la tour, avec des doubles d'essai à la place du micro, des moniteurs, des imprimantes et des services distants. Il sert à trouver avant l'installation les erreurs, corruptions et manques, puis à garder la même preuve à chaque modification.

Il ne qualifie ni la tour, ni la voix française réelle, ni les trois moniteurs, ni une imprimante, ni la qualité artistique. Ces recettes restent des portes distinctes (`jarvis/apps/jarvis/app/launch_readiness.py`).

## Lancer le banc

Sur Windows : double-cliquer `Banc_BOJART.cmd`. Les rapports JSON et Markdown sont écrits dans `%USERPROFILE%\BOJART\banc\` avec un nom neuf.

Depuis la racine du dépôt :

```sh
python tools/banc_preinstallation.py --output banc.json --markdown banc.md
python tools/banc_preinstallation.py --quick                 # suites courtes + HTTP + statique
python tools/banc_preinstallation.py --reseau --output b.json # ajoute les roues Windows cp312 (lecture PyPI)
```

Un rapport existant n'est jamais écrasé. Code de sortie 1 si un constat est **bloquant**. Le workflow `.github/workflows/preinstall-bench.yml` exécute le banc sous Linux et Windows avec LangGraph et CadQuery, et conserve les deux rapports 30 jours.

## Ce que le banc exécute

| Bloc | Contenu | Ce que cela prouve |
|---|---|---|
| Suites | `tests`, `tests_agent`, `tests_ops`, `tests_workflows`, **`jarvis/tests`, `jarvis/apps/jarvis/tests`, `tests_m03`, base métier**, tests Node | Les suites Jarvis M02–M07 (plus de 400 tests) n’étaient lancées par aucun workflow CI ; le banc les reprend. |
| Outils | `simulate_jarvis_workflows.py`, `validate_repository.py`, `evaluate_memory.py`, `check_startup.py --abrupt` | Tours vocaux synthétiques et flotte fictive, manifeste SHA-256, recherche citée, arrêt forcé du lanceur. |
| Statique | chemins Windows, scripts `.cmd`, syntaxe Python/JS, JSON stricts, imports ES et références HTML/CSS, encodage des E/S texte, provenance Three.js | Corruption de fichiers, références cassées, pièges Windows (MAX_PATH, noms réservés, CRLF, cp1252). |
| HTTP bout en bout | 16 scénarios contre le **vrai serveur** `consolidated_workbench.py`, avec trois écrans simulés | Session et refus d'accès, dashboards, scène à trois accusés, clarification, refus physique et négation, rejeu, annulation, voix sans moteur, charge, **arrêt brutal et reprise**, mémoire vide, Growth sans publication, socle CAO réel, **base corrompue**. |
| Encodage Windows | Suites et scénarios HTTP avec l'encodage par défaut de Windows (cp1252 émulé sous Linux, natif sous Windows) | Accents et apostrophes non corrompus sans `PYTHONUTF8=1`. |
| Roues Windows (`--reseau`) | Résolution `pip --dry-run` pour `win_amd64` / CPython 3.12 de `jarvis/requirements.txt` et `requirements-voice.txt` | Chaque dépendance s'installe sans compilation sur la tour. Pas une installation réelle. |

Le catalogue `data/preinstallation/actions-jarvis.json` relie chaque action (36) à ses vérifications et à sa porte de recette réelle. Statuts : **Simulé OK**, **Partiel** (une vérification non exécutée ou une précondition absente), **ÉCHEC**, **Non codé**. Une précondition absente (médias M07, Playwright) n'est jamais comptée comme réussite ; si elle devient disponible, l'échec redevient une régression.

## Résultats du 2 novembre 2026

Voir [le rapport daté](evidence/banc-preinstallation-2026-11-02/README.md) pour le SHA mesuré, les chiffres et les fichiers bruts.

Défauts trouvés et **corrigés dans ce lot** :

1. **Lanceurs Windows en fins de ligne LF** (9 fichiers `.cmd`). `cmd.exe` cherche les étiquettes `goto`/`call :x` par blocs de 512 octets ; avec des LF seuls, une étiquette peut devenir introuvable selon sa position. Quatre lanceurs à étiquettes étaient concernés. Le dépôt garde les octets exacts (`* -text`) : les scripts sont maintenant enregistrés en CRLF.
2. **`Simuler_BOJART.cmd` sans `PYTHONUTF8=1`**, contrairement aux autres lanceurs.
3. **Lectures/écritures de texte sans encodage explicite** dans le code exécuté par l'application et les outils (serveur, médiathèque FFprobe, mesures, préinstallation, `doctor`, `start_jarvis`, `validate_repository`, etc.). Sous Windows sans mode UTF-8, Python utilise cp1252 : accents corrompus en silence, ou `UnicodeDecodeError`. Le manifeste écrit par `validate_repository.py --write-manifest` aurait aussi pris des fins de ligne CRLF sous Windows. Un test mémoire échouait réellement en cp1252.
4. **Base de travail corrompue** : le refus de démarrer était correct (aucune réinitialisation silencieuse), mais l'utilisateur recevait une trace Python. Le message nomme maintenant la cause et la restauration dans un nouveau dossier.
5. **Chemins Windows non canoniques** (trouvé par la CI Windows du banc) : un dossier temporaire Windows peut porter un nom court 8.3 (`RUNNER~1`) que `resolve()` développe. L'outil de restauration de l'archive refusait alors une restauration légitime comme « chemin dangereux », et un test de la médiathèque comparait deux formes du même chemin. Les deux comparent maintenant des chemins canoniques.

Le rapport garde la ligne d'exception de chaque test en échec, et un test qui échoue déjà en UTF-8 n'est pas imputé à l'encodage cp1252.

Constats **conservés pour décision ou recette** :

- Les suites Jarvis M02–M07 n'étaient dans aucune CI : le nouveau workflow du banc les exécute sous Linux et Windows.
- Quatre tests Studio/Growth/M05 exigent les médias M07 d'exemple, absents du dépôt public (`tools/hydrate_m07_media.py` avec l'archive vérifiée).
- Les scripts de recette navigateur hérités (`test_browser*.py`, `test_ui.py`, `test_preview*.py`) ne sont pas des tests `unittest` : ils visent `/usr/bin/chromium` et réécrivent leurs preuves dans `preuves/`. À ne pas lancer sur la tour sans adaptation.
- Site Atelier : `three.core.js` est bien présent sur `main` (défaut signalé par la PR #15 déjà corrigé), mais le logo et les polices (`logo.webp`, `body.ttf`, `display.ttf`) sont exclus du dépôt : à hydrater avant tout rendu.
- Sous charge (24 demandes simultanées), les tours arrivés pendant un traitement restent « EN ATTENTE » ; la console demande un clic « Reprendre ». Aucun tour n'est perdu ni dupliqué à la reprise. Une nouvelle tentative automatique de la même référence serait plus fluide en voix.
- 95 paquets résolus en roues Windows cp312, aucun à compiler ; 83 dépendances transitives ne sont pas épinglées. Un fichier de contraintes Windows avec empreintes rendrait l'installation de la tour identique à celle testée.
- Non codé dans `main` : figurine M08, découpe d'un mètre et tranchage (PR #15 en revue), inventaire et pilotage des imprimantes (volontairement absent), devis réel.

## Limites

Les temps du banc mesurent des appels HTTP locaux sur l'hôte de test, sans navigateur qui dessine, sans micro ni GPU. Ils ne sont ni une latence vocale ni un délai d'affichage physique. L'émulation cp1252 sous Linux reproduit l'encodage des fichiers et des sous-processus, pas la console ni le système de fichiers Windows ; le passage sous Windows dans la CI complète ce point. Un « Simulé OK » se réexamine après toute installation réelle.
