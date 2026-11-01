# Reçus de surveillance contextuelle BOJART

Cette branche `audit/context-results` conserve les preuves d'analyse produites par l'automatisation ChatGPT « Auditer les évolutions BOJART ». Elle ne sert pas au déploiement et ne doit pas être fusionnée dans `main`.

La PR permanente dont la branche source est `main` et la base `audit/context-baseline` relaie les nouvelles révisions de `main` vers le webhook de PR. Les autres PR du dépôt sont également couvertes. La base reste fixe ; cette PR reste ouverte et ne doit pas être fusionnée.

## Registre

- `ops/context-monitor/checkpoint.json` : dernier reçu enregistré par numéro de PR ; un état partiel ou bloqué ne constitue pas une validation.
- `ops/context-monitor/receipts/pr-<numéro>/<sha>.json` et `.md` : révision figée, comparaison, portée, sources lues, contrôles observés, constats, correctifs et éléments restant à examiner.
- `ops/context-monitor/probes/` : preuves de recette du déclenchement, séparées des analyses.

Un reçu initial « pending » ne prouve aucune analyse. Seul un reçu terminé avec sources vérifiables et un lancement enregistré de l'automatisation prouve que ce déclenchement a été traité. L'absence d'alerte ne vaut pas validation. Aucun délai instantané ni exhaustivité sémantique n'est garanti.

Les écritures se font après relecture de la tête distante, sans force-push. Ne pas faire régresser le point de reprise si un lancement plus récent a déjà terminé. Conserver les reçus existants. Une analyse de grande ampleur doit expliciter les chemins non lus et poursuivre ce travail au lancement suivant, même si la révision n'a pas changé.

Chaque commit de reçus actualise aussi `data/catalog/repository_manifest.json` : tailles UTF-8 et SHA-256 des fichiers ajoutés ou modifiés, entrées inchangées préservées, manifeste exclu de lui-même. Cela conserve la CI de continuité sur cette branche.
