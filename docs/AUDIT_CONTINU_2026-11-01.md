# Audit et amélioration continue BOJ.ART — 1 novembre 2026

## Périmètre vérifié

Dépôt `Momolscode/BOJART`, branche `main`, public et accessible en écriture. Lecture initiale des 34 fichiers au commit `1ca60c3571c78f9303b8b4d54e82e34ae3e439f7`, puis rapprochement des deux documents historiques ajoutés jusqu'à `409c223ef5bf69211b1ecbe20fe7836d7612f744`. Au rapprochement avant publication, les ajouts jusqu’à `0c72455bec644dafffc142b5d72fcf81b8d9b1ac` ont aussi été lus : archives V23, V25, tour de contrôle, anciens bilans, requêtes et reçus Painted Reality/The Awakening. Le README concurrent a été conservé et complété. Les fichiers publiés après ces références sont couverts par les futurs rapports d'Actions, pas rétroactivement par cette lecture.

Les copies de consolidation locales observées contenaient déjà du travail Jarvis et une mémoire documentaire en préparation. Elles n'ont pas été modifiées ou présentées comme publiées. Le patch utilise la dernière tête distante au moment de l'écriture et préserve les ajouts des autres sessions.

Le point de reprise Jarvis actuel a été lu sur sa section prioritaire : M07 décrit des interfaces, un moteur local et des tests avec doubles ASR/Jev. Ces preuves rapportées ne qualifient ni un microphone réel, ni les imprimantes, ni une connexion Jev active. Le code M07 n'était pas encore dans les 36 fichiers de ce périmètre publié. La récupération intégrale de toutes les sessions n'est pas certifiée.

## Constats et corrections

| Constat | Preuve | Correction ou prochaine preuve |
|---|---|---|
| La CI existante ne se déclenchait sur push que pour quatre chemins | `.github/workflows/quality.yml` ; seul run lu : `41346049384`, succès sur ancien commit `6bc5645` | Ajout de `audit.yml` pour tous les pushes et PR, rapport par révision |
| Le vérificateur acceptait `reviewer: null` converti en texte | Lecture de `tools/quality_gate.py`, cas de régression reproduit | Relecteur et plan doivent être des chaînes non vides ; contrôles booléens stricts et critères connus |
| Un gabarit neuf portait `render_status: completed` | `runs/higgsfield/experiment-template.json` | `is_template: true`, `not_submitted`, aucun ID de job inventé |
| G1 était terminé sans ID dans son fichier de paramètres | `G1_PARAMETRES.json`, continuité de production actuelle, reçu Higgsfield relu | ID réel ajouté ; statut distant confirmé le 1 novembre |
| Les états distants et les rendus n'étaient pas reliés par un journal transactionnel dans ce périmètre | Absence de journal opérationnel dans l'arbre publié | `bojart_ops` livré : réservation, requête unique, réconciliation, reçus, empreinte du média et sauvegarde |
| Les cinq sources de R03 ne sont pas présentes dans le checkout initial | `productions/le-dernier-geste/ASSETS.json` | Cinq avertissements explicites ; aucune suppression de manifeste ou prétention de rendu reproduit |
| G2 reste manquant | `STATUT_G2.json` et `REVUE_R03.json` | Qualifier un plan fidèle ; TEST19 reste provisoire |

## Générations revérifiées

| Plan / essai | ID | Statut fournisseur relu | Interprétation |
|---|---|---|---|
| TEST18 | `721cf6a8-310b-40c9-b4c0-3b864e2bd53d` | `ip_detected` | Refus terminal ; aucune relance automatique |
| TEST19 | `b51304bb-e84a-435e-a21d-3ac0eaab12e6` | `completed` | Résultat disponible ; ne remplace pas un G2 fidèle |
| Essai figurine | `e41cf631-e33a-45f4-8a1a-b71e9310f2a0` | `nsfw` | Refus terminal conservé |
| Insert matière REPRISE01 | `0a942e6f-541c-4f00-ba65-f9f921671f3f` | `completed` | Résultat disponible |
| G1 R02/R03 | `e81c8ed0-5535-4216-ad7e-e88c2a4d8da3` | `completed` | Résultat disponible, paramètres rattachés |

Aucune génération soumise et aucun crédit média dépensé dans cet audit. Les cinq vidéos/sorties n'ont pas fait l'objet d'une nouvelle lecture perceptuelle complète ici. Le projet média BOJ.ART V35 retrouvé retourne zéro placement ordinaire ; cela ne décrit pas le contenu interne de sa scène 3D ni tout l'historique du compte.

## Vérification exécutée

34 tests Python réussis dans un environnement local : JSON invalides, traversée de chemins, empreintes, sources absentes, continuité d'EDL, critères de revue, double soumission, écritures concurrentes, dépassement de plafond, refus fournisseur, état inconnu, événement périmé et restauration SQLite. Les doubles n'appellent aucun fournisseur.

L'audit de la version de travail avant ajout de ce rapport a parcouru 47 fichiers : zéro erreur structurelle, cinq avertissements de médias absents, zéro groupe identique. Ce nombre est un instantané ; le rapport du run GitHub porte l'inventaire final de sa propre révision. Les vérifications ne garantissent ni absence de tout secret, ni récupération exhaustive, ni qualité artistique.

## Cap pratique

Un échange doit transporter le domaine, la source, sa version, l'action proposée et la preuve attendue. La mémoire documentaire répond avec des références ; le journal opérationnel enregistre les effets ; le média final et sa revue permettent de juger la création. Ne pas faire de la réussite d'un test de structure une validation générale de Jarvis.

Les [instructions d'exploitation](OPERATIONS.md) donnent les commandes et le suivi. La [recherche ciblée](OUTILS_ET_ESSAIS.md) retient cinq briques en fonction de ces besoins et définit leur prochain essai.
