# Débrief de la tour vers GitHub

Demande d'Olsen du 9 novembre 2026 : Jarvis doit pouvoir pousser sur GitHub, pour que le résultat d'une installation ou d'une séance d'essais arrive aux fils de travail sans que personne ne recopie un rapport à la main.

État : codé et testé sur un faux dépôt distant, sous Linux. Pas encore lancé depuis la tour : la connexion GitHub réelle et la première poussée restent à faire.

## Sur la tour

Double-cliquer **Publier_Debrief_BOJART.cmd**. Le programme montre la liste exacte des fichiers qui partent, propose d'ajouter une phrase, demande un accord, puis pousse. Il donne ensuite l'adresse de la branche à ouvrir dans le navigateur.

La première fois, Git ouvre une fenêtre de connexion GitHub : se connecter avec un compte qui a le droit d'écrire dans `Momolscode/BOJART`. Jarvis ne lit et ne garde aucun jeton ; la connexion reste celle de Git sur la tour. L'installateur complet installe Git avec winget s'il manque.

| Commande | Effet |
|---|---|
| `Publier_Debrief_BOJART.cmd` | Liste, phrase facultative, accord, poussée |
| `Publier_Debrief_BOJART.cmd --simulation` | Tout préparer et contrôler, sans rien pousser |
| `Publier_Debrief_BOJART.cmd --note "micro OK, écran 2 noir"` | Phrase donnée d'avance |
| `Publier_Debrief_BOJART.cmd --avec-diagnostic` | Joindre aussi le dernier diagnostic du poste |
| `python tools/publier_debrief.py essai` | Essai complet sur un faux dépôt local, sans réseau |

## Ce qui part

Seulement les rapports que Jarvis écrit lui-même dans `%USERPROFILE%\BOJART`, en `.json`, `.md` ou `.txt`, de moins de 1 Mo :

| Famille | Dossier | Retenu |
|---|---|---|
| installation | `installation` | le dernier journal de `Installer_Tout_BOJART.cmd` |
| banc | `banc` | le dernier rapport de `Banc_BOJART.cmd` (JSON et Markdown) |
| voix | `banc-voix\rapports` | les deux derniers de `Mesurer_Voix_BOJART.cmd` (mesure et bruit seul) |
| mesures | `benchmarks` | la dernière de `Mesurer_BOJART.cmd` |
| diagnostic | `diagnostics` | le dernier, sur demande seulement |

Ces rapports disent ce qui a été mesuré, les versions installées, le système, le processeur, la mémoire et la carte graphique. Ils arrivent dans `docs/evidence/tour-AAAA-MM-JJ-HHMMSS/`, avec un `README.md` qui donne pour chacun l'empreinte SHA-256 de l'original resté sur la tour, le nombre de retraits et une ligne de résultat.

Ne partent jamais : médias, bases SQLite, mémoire documentaire, collecte, configuration privée, modèles, ni aucun dossier choisi librement.

## Garde-fous

- Le dossier personnel, le dossier d'installation, le nom de session Windows, le nom du poste et les adresses de courriel sont retirés avant la copie.
- Le contrôle du dépôt (`tools/validate_repository.py` : secrets, binaires, tailles, manifeste) doit passer sur l'arbre préparé ; sinon rien n'est créé sur GitHub.
- La destination est `Momolscode/BOJART` et lui seul, sur une branche neuve `tour/debrief-AAAAMMJJ-HHMMSS`. Jamais `main`, jamais une branche existante, jamais de poussée forcée.
- La copie de travail de la tour n'est pas touchée : le commit se fait dans un arbre temporaire, sur la tête de `main` relue à l'instant. Une copie « Download ZIP » sans Git garde pour cela un clone minimal dans `%USERPROFILE%\BOJART\depot-github`.
- Le commit est signé « Jarvis BOJ.ART (tour) » : l'identité Git du poste n'est pas publiée.
- Une commande vocale ne déclenche pas cette poussée. Le dépôt est public et une transcription n'est pas une instruction : l'accord se donne à l'écran, après lecture de la liste.

## Ce que cela ne fait pas

Le débrief arrive sur une branche, pas dans `main` : il décrit ce que la tour a mesuré et ne vaut ni réception, ni décision. Un fil de travail le lit, le compare aux preuves du conteneur (`docs/evidence/installation-2026-11-09/`) et met à jour le contexte par une PR relue. Le programme ne pousse aucun code, n'ouvre aucune PR et ne télécharge aucune mise à jour.

## Vérifications

`python tools/publier_debrief.py essai` : faux dépôt distant local, faux dossier personnel, une image et un jeton plantés ; 12 contrôles, exécutés par le banc sous Linux et sous Windows (`outil:debrief_simulation`). `tests_ops/test_debrief_tour.py` : 22 tests (ce qui est retenu, ce qui est retiré, destinations refusées, accord, lanceur). Preuve du 9 novembre : `docs/evidence/debrief-tour-2026-11-09/`.
