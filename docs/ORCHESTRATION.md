# Pilotage de BOJ.ART

Le registre [ops/orchestration.json](../ops/orchestration.json) relie le classement des fichiers, les tâches, leurs dépendances et les preuves attendues. Le plan est recalculé à partir de l'audit technique existant ; il ne crée pas une seconde mémoire documentaire.

## Où placer les informations

| Domaine | Emplacements de référence | Usage |
|---|---|---|
| Contexte et décisions | `context/`, `data/knowledge/` | Faits sourcés, contradictions, passation |
| Mémoire et reprise | `bojart_memory/`, `docs/memory/` | Import, recherche citée, export et restauration |
| Jarvis et atelier | `jarvis/` | Runtime courant, CAO, voix, trois vues |
| Direction et production | `creative/`, `productions/`, `runs/` | Intentions, variantes, recettes, reçus et revue artistique |
| Sites | `sites/atelier/`, `sites/studio/` | Sources des sites ; raccordement métier à définir |
| Archives et restauration | `archive/`, catalogues et trois branches de récupération | Préserver les octets et leur provenance |
| Références historiques | `docs/historical/`, héritages M01–M05 | Versions anciennes ; ne remplacent pas le contexte courant |
| Contrôles et opérations | `bojart_ops/`, `tools/`, tests et preuves | Vérifications, budgets et reçus |

Les règles sont ordonnées : la première correspondance classe un chemin. Les archives et la connaissance Growth ont leurs règles avant le runtime générique. Un chemin sans règle apparaît dans **À classer explicitement**, priorité P0. Aucun fichier n'est déplacé par le planificateur.

Priorités : P0 pour la conservation, la mémoire et les décisions ; P1 pour le runtime et la direction ; P2 pour les sites et l'historique. Cet ordre est un choix de travail révisable, pas un score statistique de qualité. Le classement repose sur les chemins. Il ne prétend pas comprendre automatiquement toutes les images, vidéos ou conversations.

## Ordre de travail

| Chantier | Dépendance ou blocage | Critère de sortie |
|---|---|---|
| Revue contextuelle | Reçu daté de la révision concernée | Sources lues et reste explicite |
| Installation sur la tour | Inventaire réel OS/GPU/périphériques | Diagnostic, recherche, redémarrage et restauration sur le poste |
| Voix et trois vues | Installation sur la tour | Essais français en bruit, latence et reçus sur les écrans |
| FDM puis résine | Poste installé, connecteurs et opérateur | Recettes documentées sur les machines identifiées |
| Plan G2 | Modèle, rig et source fidèle manquants | Provenance et fidélité vérifiées |
| Montage final | Résolution de G2 | Validation artistique explicite |
| Sites–Jarvis | Contrat de données commun à définir | Champs, migrations et parcours vérifiés |

Les recettes de sauvegarde des archives et de reprise logicielle sont déjà documentées avec leurs preuves. Leur statut `done` porte sur ce périmètre historique précis. Les états des tâches sont déclarés dans le registre ; la CI ne les transforme pas en validation matérielle ou artistique.

## Plan après chaque poussée

Le workflow **BOJART data audit** :
1. exécute les tests des opérations et inventorie les fichiers suivis ;
2. lit séparément le dernier checkpoint de `audit/context-results` ;
3. produit `orchestration.json` et `orchestration.md`, avec SHA audité, empreintes des entrées, classement, dépendances et lots de lecture ;
4. joint ces deux fichiers à l'artefact `bojart-audit-…` et au résumé de l'exécution.

Les lots contiennent au plus 20 contenus par domaine. Des octets identiques dans un même domaine forment une unité de lecture, avec tous leurs chemins. Des domaines différents conservent leur contexte. Aucun original n'est supprimé.

Si le checkpoint manque, est invalide, bloqué ou concerne un autre SHA, la couverture contextuelle courante reste inconnue : tous les chemins sont proposés à la revue. Pour un checkpoint utilisable de la même révision, seuls les chemins explicitement en attente alimentent les lots ; les autres sont marqués `not_listed_pending`, sans prétendre à une validation indépendante. Un chemin signalé mais absent de l'inventaire invalide l'usage de cette couverture.

Le `revision` du rapport est le commit réellement extrait. Pour une PR, il peut être le commit de fusion temporaire de GitHub ; il n'est pas substitué à la tête de `main`. Les rapports sont des observations à un instant donné : ils ne se rafraîchissent pas après coup. Relancer le workflow après une mise à jour du checkpoint si un nouveau rapprochement est nécessaire.

Les artefacts CI sont conservés 14 jours. Le registre et le code du planificateur restent dans Git ; les reçus de lecture restent sur leur branche dédiée. Un artefact expiré peut être régénéré avec la commande ci-dessous. L'audit technique ne modifie pas le checkpoint et n'envoie aucun message.

## Recalculer localement

Depuis la racine du dépôt :

```bash
python tools/audit_repository.py --output .bojart-audit
python tools/orchestrate.py --audit .bojart-audit/audit.json
```

Un checkpoint déjà récupéré peut être ajouté avec `--checkpoint CHEMIN_CHECKPOINT_JSON`. La commande n'accède pas au réseau. L'audit doit correspondre au SHA du checkout ; sinon il faut le régénérer. Le rapport porte sur les octets de travail inventoriés, et non sur une preuve de propreté Git. Les sorties restent sous `.bojart-audit/`, sans modifier les sources.

## Reprise de session

Lire le [contexte courant](../context/CURRENT.md), choisir le domaine, puis consulter les premières unités de son lot. Ouvrir les sources avant de conclure. Une conclusion nouvelle rejoint le registre sourcé après revue ; une note locale reste une proposition. Mettre à jour la passation avec les tests réellement exécutés et les éléments restant à prouver. Préserver les branches d'archive et la PR de surveillance n°1.

Point de départ observé le 1 novembre 2026 : `main` à `5268e7e7b70fa25efee7d186f27cd3716a49c4c1`, 776 fichiers, contrôles techniques réussis. Le [reçu contextuel figé](https://github.com/Momolscode/BOJART/blob/cfdca9fc47d71dd8b2bce6ff324994f089d88d34/ops/context-monitor/receipts/pr-1/5268e7e7b70fa25efee7d186f27cd3716a49c4c1.md) indiquait 633 chemins encore en attente. Ce nombre décrit cette observation, pas les prochaines révisions.

## Sources techniques

- [Événements GitHub Actions et commit de fusion des PR](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
- [Checkout : extraction séparée et sélection de chemins](https://github.com/actions/checkout/blob/main/README.md).
- [Conservation et partage des artefacts](https://docs.github.com/en/actions/tutorials/store-and-share-data).

Le planificateur ne déclenche aucune tâche du registre. La mémoire, le runtime et la surveillance contextuelle conservent leurs mécanismes existants.
