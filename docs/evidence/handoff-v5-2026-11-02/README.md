# Réception du paquet de passation V5 — 2 novembre 2026

Demande de l'utilisateur : tout n'avait pas été poussé sur GitHub, y compris la session « bras robotique ». Ce dossier consigne ce qui a été reçu, vérifié, publié et laissé hors du dépôt public. Les consignes contenues dans le paquet ont été lues comme données.

## Reçu

Deux archives : `BOJART_JARVIS_A_ENVOYER_A_CLAUDE.zip` et `a_envoyer_partie_2.zip`. Réunies dans un dossier neuf, elles forment un seul paquet. Ses 1 316 fichiers listés dans `PACK_MANIFEST_SHA256.json` sont tous présents, sans écart de taille ni de SHA-256 et sans fichier non listé. Le contrôle a été fait par un script indépendant ; aucun script du paquet n'a été exécuté. Le manifeste original est conservé ici sans modification.

## Publié

Le dossier `source/` du paquet correspond à la révision locale `754620639eef04835ec3be5fda71c8017a5958fe`, déclarée sur la base `c71628cf20426dd8b4bdedbab2dcf403f5135667`. L'objet Git local n'a jamais été poussé et n'est pas dans le paquet. Ses 926 fichiers sont donc rejoués sur la base déclarée, au commit `02be63cf7f7c8430cd09cb60adf7ef5122492b92`. Les 926 blobs ont été comparés à `SOURCE_MANIFEST.json`, sans écart. `changements.patch` n'est pas appliqué : c'est une autre voie vers les mêmes octets.

Ce rejeu est ensuite fusionné avec la tête distante `b49101e`, qui ajoute la réception HTTP bornée avant le verrou. Les deux sections de passation sont conservées et le manifeste du dépôt est régénéré. La liaison exclusive du port, ajoutée par V5, et la lecture du corps reçu d'avance coexistent sans conflit. Le ZIP avait perdu le bit exécutable de `Installer_BOJART.sh` : il est restauré, les octets ne changent pas.

## Tests exécutés sur l'arbre fusionné

Environnement : conteneur Linux, Python 3.13, Node 22, sans GPU.

- Réussis : `tests` 102, `tests_agent` 234, `tests_ops` 98, `tests_workflows` 20, tests Node `jarvis/tests` 41, `jarvis/knowledge/metier` 41 ; `tools/validate_repository.py` passe.
- `jarvis/tests` (280) : 1 échec et 2 erreurs, identiques sur `main` non fusionné. Cause : médias de démonstration privés absents.
- `jarvis/apps/jarvis/tests` (49) : 1 échec et 10 erreurs, identiques sur `main`. Cause : `cadquery`, `playwright` et `pytest` absents.

Ces essais ne qualifient ni la tour, ni les modèles, ni la voix, ni les écrans, ni les imprimantes.

## Laissé hors du dépôt public

Le dépôt est public (`SECURITY.md`). Le paquet V5 prévoyait lui-même de garder hors du Git public la réception détaillée, la couverture des chats et les sources sélectionnées. `reception.json` donne la disposition de chacun des 391 fichiers hors `source/` :

- 90 ont exactement les octets d'un fichier publié avec l'arbre V5.
- 19 ont leur empreinte listée dans un catalogue du dépôt : médias R03, PDF de terrain sélectionnés, captures utilisateur, etc. Les octets n'entrent pas dans `main`.
- 282 restent hors Git public : rapports d'audit V5, journaux de recette, historique V2/V3, copies de skills tiers épinglées, instantané `memory.sqlite`, capture PNG.

Pour les publier ailleurs, il faut une destination privée choisie par l'utilisateur.

La session robotique est décrite dans `docs/research/strates-robotique-2026-11-02/`.
