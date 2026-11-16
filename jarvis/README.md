# BOJ.ART / Jarvis — Mission 07, scène et commande vocale

**M07 : une commande compose les trois vues ; confirmation vocale des propositions visuelles, arrêt de prise sur pause et contexte figé avant écoute.**
Le lanceur ouvre `/workspace` ; la régie et ses trois vues sont dans `/tower`. Lire [la version M07](docs/m07/RELEASE_M07.md), [la configuration](docs/m07/INSTALLATION_ET_REPRISE.txt), [le schéma cliquable](docs/m07/SCHEMA_M07.html) et [la recherche actualisée](docs/m07/RECHERCHE_2026-11-01.md).

La reconnaissance réelle et Jev restent à configurer puis qualifier sur la tour. Les tests synthétiques ne constituent pas une preuve de précision vocale en atelier. Les versions M05/M06 sont conservées dans l'historique.

M05 reste la base des dossiers distincts, sauvegardes globales et reprises d'interruption. Les données existantes restent dans leur dossier `mission05` ; ce nom conservé ne signifie pas que l'ancien code est utilisé.

Le code courant est publié dans [Momolscode/BOJART](https://github.com/Momolscode/BOJART). Le point d'entrée d'installation est [INSTALLER_DEMAIN.md](../INSTALLER_DEMAIN.md) à la racine du dépôt. Les sources des sites sont dans `../sites/` ; lancer Jarvis ne les déploie pas. Les paragraphes de livraison et de préservation ci-dessous décrivent les paquets historiques ; [l'état courant](../context/CURRENT.md) et [l'état des archives](../docs/ETAT_ARCHIVES_2026-11-01.md) précisent les récupérations vérifiées. L'intégralité des anciens chats et des données du PC réel n'est pas certifiée.

Après l'installation à la racine, `Lancer_Jarvis.cmd` ou `bash Lancer_Jarvis.sh` rejoint le même lanceur BOJART : environnement Python installé, diagnostic et actualisation de la mémoire. Le lanceur dans `apps/jarvis/` suit également ce parcours. Pour reprendre un espace existant/restauré : `Ouvrir_un_dossier_Jarvis.cmd` ou `bash Ouvrir_un_dossier_Jarvis.sh`. Pour une restauration non destructive : `Restaurer_Jarvis.cmd` ou `bash Restaurer_Jarvis.sh`, avec le Python installé à la racine. Un paquet historique extrait séparément conserve son repli local. Rien n'est installé par ces lanceurs.

La CAO, le catalogue, les brouillons et les vues fonctionnent dans la recette locale. La voix, les modèles IA, les imprimantes et les moniteurs physiques restent à qualifier sur la tour. **Lancement physique non qualifié.**

## Commencer sans perdre le fil
1. Lire `context/START_HERE.md`, puis `context/DECISIONS.json`.
2. Examiner `preservation/COVERAGE.md` : disponible, manquant et contenu seulement référencé.
3. Vérifier les fichiers : `python tools/verify_repository.py`.
4. Pour l'intégrateur : `python tools/run_checks.py` puis `python apps/jarvis/app/consolidated_workbench.py --no-browser`.

Python 3.12 utilisé pour la recette M06 ; CadQuery/Trimesh requis pour la CAO, FFprobe pour les médias. `requirements.txt` inclut LangGraph ; `requirements-voice.txt` ajoute le moteur de transcription. Les poids restent à configurer. Aucune installation ni mise à jour automatique. Les variantes 3D livrées ne sont pas une validation mécanique. Les modèles voix/LLM et Jev demeurent désactivés par défaut.

## Arborescence
- `apps/jarvis/` : base Mission 03 (incluant 01/02) et extension de consolidation.
- `knowledge/metier/` : 54 fiches, sources, règles et recherche SQLite locale.
- `labs/planning/` : laboratoire de planning à données fictives, pas le parc réel.
- `creative/character-lock-v6/` : identité de la sculpture et sources authentiques.
- `marketing/` : calendrier et maquettes, sans publication ni métriques connectées.
- `research/voice-jev/` : recherche et architecture, pas un moteur installé.
- `docs/guides/` : PDF conservés, non remplacés par une synthèse.
- `history/` : démonstrateur initial, plans antérieurs et preuves historiques.
- `context/` : mémoire courte, décisions sourcées, contradictions résolues et état réel.
- `preservation/` : inventaires, empreintes, provenance et limites de récupération.
- `tools/` : vérification, restauration, tests et publication GitHub à autoriser.

## Consolidation historique
La base métier peut maintenant être interrogée via le même serveur local que le Studio. Les contrats de commandes d'affichage sont validés sans appel à Jev pour un ordre connu. Une proposition d'affichage ne prétend pas qu'un écran physique l'a exécutée. Voir `docs/CONSOLIDATION.md` et les tests.

## Préservation
Les 81 chemins montés lors de cette session sont conservés octet pour octet dans le coffre de livraison ; 75 objets SHA-256, avec alias pour les doublons. Les ZIP historiques sont conservés intacts. Le dépôt exploitable n'écrase pas les fichiers d'origine. Le bundle inclut l'historique de consolidation créé ici, PAS l'historique Git des sites.

Le coffre et le bundle sont complémentaires : un `git clone` seul ne contient pas tous les originaux. La publication préparée ajoute le coffre comme pièce jointe de Release dans un dépôt PRIVÉ, puis retélécharge pour contrôler les empreintes. Elle n'effectue jamais de force-push, de mirror-push ou de suppression.

Ne pas fusionner avec UNUM, M-Tek ou les autres dépôts.


## SEO & publications — 31 octobre 2026
La route locale `/growth` reprend les passages du Studio, prépare titre/légende/hashtags avec règles explicites et conserve le brouillon. Six skills `.claude/skills` et `.agents/skills`, corpus `knowledge/growth`. Pas de connexion sociale ni Ads. Lire `docs/SEO_PUBLICATION_2026-10-31.md` et le contrat de publication avant tout raccordement.

## Historique Mission 04 — régie locale et recette de lancement

**Nouveau :** `/tower` offre trois rôles de vues navigateur, des commandes d'affichage contrôlées et des accusés logiciels persistants. `/api/launch/readiness` expose les douze portes de recette, volontairement non validées sans essais sur la tour. Les lanceurs `apps/jarvis/Lancer_Jarvis.cmd` et `.sh` ouvrent désormais `consolidated_workbench.py` (M04 utilisait un espace séparé ; M05 emploie désormais mission05).

Pour un diagnostic sans installation ni commande machine : `python tools/m04_pc_audit.py --output rapport_pc.json`. Pour une recette locale CAO + API + trois rôles avec accusés simulés : `python tools/m04_smoke.py`.

Lire `docs/m04/RELEASE_GATE_M04.md` et `docs/m04/REPRISE_CLAUDE_M04.txt`. Les trois vues sont des onglets locaux, **pas encore trois moniteurs physiques appairés**. Pas de publication, d'impression, de modèle local/Jev ou de dépense.
