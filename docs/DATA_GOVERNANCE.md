# Données et continuité

| Niveau | Rôle | Règle |
|---|---|---|
| Sources | Exports, médias et archives originaux | Préserver octets et empreinte |
| Données structurées | Versions, passages, provenance et décisions | Conserver dates, domaine et contradictions |
| Contexte courant | Sélection utile à la tâche | Citer les sources ; ne pas prétendre à l’exhaustivité |

Même chemin/collection/projet et mêmes octets : aucun doublon de version. Contenu modifié : nouvelle version, ancienne conservée. Deux copies identiques partagent l’objet mais gardent leur provenance. « Version courante » ne signifie pas « chaque phrase est vraie ».

Domaines : `bojart.jarvis`, `bojart.creative`, `bojart.sites`. UNUM, M-Tek et conversations personnelles restent hors corpus. Import UTF-8 borné ; PDF/images/audio/vidéo demandent une extraction distincte et sourcée. Aucune transcription ou vision automatique.

## Importer

```bash
python3 -m bojart_memory ingest /chemin/exports-bojart --project bojart.jarvis --collection sessions-atelier --provenance "Export autorisé de sessions BOJART"
python3 -m bojart_memory search "restauration voix" --project bojart.jarvis
python3 -m bojart_memory search "G2" --project bojart.creative --history
```

Les exports JSON peuvent être indexés comme texte. Aucun accès automatique au compte ou aux pièces jointes. Un futur adaptateur devra extraire messages/dates, documenter les omissions et tester les pièces jointes.

Une affirmation garde sujet, propriété, valeur, validité, observation, statut, sources et éventuelle affirmation remplacée. `user_decision`, `source_reported`, `observed`, `proposal` sont distincts. Une répétition de résumé n’est pas une confirmation indépendante. Les conflits sont dans `data/knowledge/conflicts.json`.

L’import ne promeut pas automatiquement une phrase dans le contexte courant : revue explicite nécessaire. Préserver aussi refus et limites artistiques.

## Sauvegarder

```bash
python3 -m bojart_memory verify
python3 -m bojart_memory backup /chemin/sauvegardes/memoire-2026-11-01
python3 -m bojart_memory restore /chemin/sauvegardes/memoire-2026-11-01 /chemin/restauration-test
python3 -m bojart_memory --state /chemin/restauration-test search "Jev" --project bojart.jarvis
```

Copie SQLite cohérente, objets vérifiés, destination de restauration neuve. Sauvegarder séparément l’état opérationnel M07 et les médias : le ZIP des cinq bases M07 ne couvre pas cette mémoire et réciproquement.

Politique proposée : copie après travail, autre support chaque jour travaillé, copie hors site chiffrée et essai mensuel de restauration. Ces cadences ne sont pas activées. Mesurer volume, durée et perte acceptable avant automatisation.

Le journal `bojart_ops` reçu d’une autre session conserve budgets et reçus de génération dans une base distincte. Voir [OPERATIONS.md](OPERATIONS.md) pour sa sauvegarde. L’import documentaire ne remplace ni ce journal ni les cinq bases opérationnelles M07.
