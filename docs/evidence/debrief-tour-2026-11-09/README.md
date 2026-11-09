# Débrief de la tour vers GitHub — essais du 9 novembre 2026

Demande d'Olsen : Jarvis doit pouvoir pousser sur GitHub. Réponse codée : `Publier_Debrief_BOJART.cmd` → `tools/publier_debrief.py` (`bojart_ops/debrief_tour.py`), décrit dans `docs/DEBRIEF_TOUR.md`. Conteneur Linux (Git 2.43.0, Python 3.12.3) : ce n'est pas la tour.

- `essai.json` : `python tools/publier_debrief.py essai`. Faux dépôt distant local construit depuis les fichiers publiés, faux dossier personnel « Camille Exemple » sur un poste « TOUR-ESSAI », une image et un jeton plantés. 12 contrôles sur 12 : seule la branche neuve `tour/debrief-…` est poussée, `main` ne bouge pas, seuls le dossier du débrief et le manifeste changent, les données personnelles sont retirées, l'image reste sur la tour, la copie de travail est intacte, l'identité du commit est neutre, le jeton est refusé par le contrôle du dépôt sans rien créer à distance, une branche existante et un autre dépôt sont refusés, la simulation ne pousse rien, l'arbre temporaire est retiré.
- `simulation-depot-reel.json` : `python tools/publier_debrief.py --simulation` sur le journal et le banc de la réinstallation du jour, face au vrai dépôt : `main` relu sur GitHub (`3436f53`), arbre préparé, contrôle du dépôt passé, commit fait dans un arbre temporaire, **rien poussé**.

## Limites

Aucune poussée réelle n'a été faite : ni la fenêtre de connexion GitHub de Git pour Windows, ni les droits du compte de la tour, ni `cmd.exe` ne sont essayés ici. La CI Windows du banc rejoue `essai` et les 22 tests. Prochaine preuve : sur la tour, `Publier_Debrief_BOJART.cmd` après l'installation, puis lecture de la branche `tour/debrief-…` par un fil de travail.
