# Installation réelle depuis une copie sans Git — 9 novembre 2026

Demande d'Olsen : auditer tout le projet et rendre Jarvis fonctionnel dès son installation. Méthode : intégrer les PR qui touchent l'installation (#17, #20, #18, #11, #15, #21) sur `claude/project-thread-m5t36k`, puis installer comme sur la tour, depuis les seuls fichiers publiés (ce que donne « Code → Download ZIP », sans dossier `.git`), avec `tools/installer_tout.py --oui --sans-modeles`, un `HOME` neuf et un environnement Python neuf. Conteneur Linux (Xeon 2,1 GHz, 4 cœurs, 15,7 Go, sans GPU, Python 3.12.3) : ce n'est pas la tour Windows.

## Ce qui empêchait Jarvis d'être prêt (premier essai, intégration `e224529`)

| Défaut | Effet | Correction (commit) |
|---|---|---|
| Banc et validateur appelaient `git ls-files` | Installation finie en échec sur une copie ZIP | Repli sur le manifeste et sur les règles `.gitignore` (mêmes réponses que `git check-ignore` sur 1 153 chemins) — `6ddfdaa` |
| Voix installée mais éteinte, sans poids | Micro inutilisable après installation | Étape `voix` : `tools/preparer_voix.py` télécharge `small` à sa révision épinglée, contrôle l'empreinte de `model.bin`, met de côté sans effacer un dossier altéré ou interrompu, active la voix dans `jarvis/apps/jarvis/config.json` (section voix seule) — `6ddfdaa` |
| Rapport d'installation : CAO absente | Faux blocage | `doctor.py --probe-imports` après installation des moteurs — `6ddfdaa` |
| Chaîne figurine M08 sans chemin d'installation | Figurine et tranchage inutilisables | Profil `--figurine`, numpy 2.5.4 aligné sur les verrous — `6ddfdaa` |
| Sous-processus figurine lus sans UTF-8 | Accents corrompus sous cp1252 | `encoding='utf-8', errors='replace'` — `6ddfdaa` |
| `Diagnostic_BOJART.cmd` en LF | Lanceur fragile sous `cmd.exe` | CRLF — `6ddfdaa` |
| Fin de prise jamais automatique dans le bruit | ≈ 12 s d'attente après chaque phrase | Fond sonore mesuré, pause reconnue au-dessus du bruit — `3917f7a` |
| Banc d'une copie sans Git : « Révision None » | Rapport non rattachable à une version | Révision nommée par l'empreinte du manifeste, comme le journal d'installation — commit suivant |

## Réinstallation depuis zéro (`3917f7a`, manifeste `a8aa17c9…`)

`journal-installation.json` : FFmpeg présent ; Jarvis complet (mémoire, CAO, orchestration, voix, figurine) 69,8 s ; voix 7,0 s (poids téléchargés, empreinte vérifiée, configuration créée) ; banc 259,8 s ; « Tout est installé ». Modèles Ollama non installés (`--sans-modeles` : pas d'Ollama dans ce conteneur).

`banc-apres-installation.md` : 1 148 tests, 16/16 scénarios HTTP (1 réserve de charge), aucune régression. Tests non exécutés, tous pour une précondition nommée : médias M07 non hydratés, Playwright Python absent, pytest absent. Actions : 12 simulées OK, 22 partielles, 2 non codées (découpe d'une sculpture d'un mètre, pilotage réel des imprimantes), 2 en échec pour une seule raison : `jarvis/locks/windows-cp312-figurine.txt` manque, il se génère sous Windows (CI du banc). Avant les corrections (`e224529`) : 3 échecs, 6 non codées, 15 constats majeurs ; après : 2, 2 et 13 (4 actions passent de « non codé » à « partiel » parce que le catalogue reconnaît désormais le code fusionné des PR #15 et #18 : figurine, tranchage, inventaire, devis).

Parcours navigateur sur l'installation (premier essai, Playwright Chromium) : les 8 pages de la console s'ouvrent ; « Affiche le dashboard atelier » tapé dans la console s'affiche sur la vue ATELIER en ≈ 80 ms. Captures gardées hors du dépôt.

## Voix

- `voix-poids-installes.md` : poids téléchargés par l'installateur, 40 prises cibles du corpus : 37 correctes, 0 erreur critique, 15/15 cas d'erreur conformes.
- `voix-avant-fin-adaptee.md`, `voix-apres-fin-adaptee.md`, `fin-de-prise-bruit.json` : même protocole sur 114 prises (voix Piper gilles, upmc-jessica, upmc-pierre), avant et après `3917f7a`. Attente médiane après la phrase : imprimante 12,43 → 3,83 s, atelier fort 12,34 → 2,89 s, calme et ventilation ≈ 1,0 s inchangés, voix de fond inchangée (limite). 0 erreur critique avant et après ; 87 → 90 prises correctes ; aucune prise coupée avant la fin de la phrase.
- `bruit-seul-apres.md` : 112 flux sans parole, 0 commande déclenchée.

## Limites

Synthèse vocale et bruit synthétiques ; ni micro, ni voix humaine, ni traitements audio du navigateur. Aucun écran physique, imprimante, modèle Ollama ni service distant. Linux, pas Windows : `cmd.exe`, winget, les roues Windows et la page de code réelle restent couverts par la CI Windows du banc et par la recette sur la tour.

Prochaine preuve : sur la tour, `Installer_Tout_BOJART.cmd`, puis `Lancer_BOJART.cmd`, « Parler à Jarvis » au vrai micro dans l'atelier, imprimante en marche ; comparer `Banc_BOJART.cmd` à `banc-apres-installation.md` et `Mesurer_Voix_BOJART.cmd` à `voix-apres-fin-adaptee.md`.
