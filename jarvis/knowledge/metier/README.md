# BOJ.ART / Jarvis — Bibliothèque métier V1

Date de constitution : 30 octobre 2026. Projet distinct d’UNUM et de M-Tek.

## Livrable réel
- 54 fiches : conception, matière, FDM, résine, qualité, prévention, pilotage, économie, Studio et données.
- 38 références primaires (fabricants, logiciels, INRS, CNIL, INPI, 3MF), consultées via pages ou extraits officiels.
- 10 procédures proposées pour l’atelier et 8 structures de registre à renseigner.
- Une interface HTML autonome consultable sans compte, modèle ou serveur.
- Une bibliothèque Python standard avec recherche textuelle SQLite FTS5 et vérification de complétude déclarative d’une recette.
- Un skill de reprise pour l’agent local, sans installation automatique ni réseau.

## Lire maintenant
Ouvrir `BASE_METIER.html`, rechercher un sujet puis lire le fait, son application BOJ.ART, sa portée et les informations manquantes. Les liens externes ne sont ouverts que sur action de l’utilisateur.

## Reprise par Claude / intégrateur (pas une tâche manuelle exigée de l’utilisateur)
Python 3.10+ avec SQLite FTS5 est nécessaire au module ; aucune dépendance tierce pour son exécution.

```sh
python app/base_metier.py "résine creuse drainage" --limit 4
python app/base_metier.py "socle assemblage" --domain conception
python app/base_metier.py "maintenance" --export-index index_local.sqlite
python -m unittest discover -s tests -v
```
L’index est une recherche lexicale avec synonymes limités, pas une recherche sémantique. Il ne comprend pas librement une question et ne génère pas une réponse par LLM.

## Limites importantes
Aucune pièce fabriquée, aucun profil d’impression qualifié, aucune voix ni IA installée. Les capacités du parc restent inconnues. La vérification d’une recette ne valide que la présence/concordance de champs déclarés : elle ne prouve pas l’authenticité d’un rapport, n’ouvre pas les pièces jointes, ne signe pas une qualification et n’autorise jamais une machine.

Les empreintes du manifeste permettent de comparer les fichiers de ce pack ; elles ne sont ni une signature d’éditeur ni une garantie de sécurité d’un logiciel tiers. Pas de snapshot intégral des pages : les URL et dates de consultation servent à la relecture. Les pages peuvent évoluer.

Mission 03 a été lue pour préparer une intégration cohérente. Ses sources, ses données et les sites publiés n’ont pas été modifiés. Voir `docs/INTEGRATION_M03.md`.
