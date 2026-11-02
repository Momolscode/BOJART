# Surveillance contextuelle des évolutions BOJART

L'audit technique GitHub Actions et la lecture contextuelle ChatGPT sont deux contrôles distincts. Le second met en relation les changements avec les décisions, les sources et les preuves de production.

## Déclenchement

L'automatisation `Auditer les évolutions BOJART` reçoit les événements des pull requests de `Momolscode/BOJART`, y compris leurs nouvelles révisions. Elle est activée, sans calendrier de scrutation. Le connecteur disponible expose les événements de PR ; il n'expose pas directement `push`.

La [PR de surveillance n°1](https://github.com/Momolscode/BOJART/pull/1) conserve `main` comme branche **source** et `audit/context-baseline` comme **base fixe** au commit `cd71c6ba640f304248702d8a3e64c60f900f9d0b`. Ainsi, un push direct sur `main` actualise la tête de cette PR. GitHub publie alors un événement de mise à jour de PR auquel la tâche est abonnée. Les PR ordinaires du dépôt restent également couvertes.

Cette PR est en brouillon et doit rester ouverte. **Ne pas la fusionner, supprimer sa base ni avancer sa base.** La fermer interrompt le relais de `main`. Aucun secret supplémentaire, service à héberger ni crédit Higgsfield n'est nécessaire à ce relais. Les délais de traitement dépendent des files GitHub et ChatGPT.

Référence du comportement GitHub : [événements `pull_request`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request). Configuration du dépôt : [context-monitor.json](../ops/context-monitor.json).

## Résultat vérifiable

Les résultats sont écrits sur la branche séparée [audit/context-results](https://github.com/Momolscode/BOJART/tree/audit/context-results/ops/context-monitor). Cette séparation évite qu'un reçu d'analyse déclenche lui-même une nouvelle analyse de `main`.

| Preuve | Emplacement | Interprétation |
|---|---|---|
| Dernière révision traitée par PR | `ops/context-monitor/checkpoint.json` | Point de reprise, avec état et reste à lire |
| Rapport JSON et Markdown | `ops/context-monitor/receipts/pr-<n>/<sha>.*` | Sources lues, écarts, contrôles observés, correctifs, limites et actions |
| Recette du déclenchement | `ops/context-monitor/probes/activation-2026-11-01.json` | Lancement sur ouverture puis lancement après push, IDs et résultats observés |
| Contrôles techniques | Onglet GitHub Actions, révision concernée | Résultats des tests et audit de structure, séparés du jugement contextuel |

Pour contrôler la surveillance, comparer le SHA courant de la PR avec celui du dernier reçu, puis lire son état : `complete`, `partial` ou `blocked`. Un reçu partiel doit énumérer les fichiers restant à examiner. Il ne valide pas les éléments en attente. Une analyse reprend ces éléments lors d'un déclenchement ultérieur ; elle ne constitue pas un service permanent exécuté dans la conversation ouverte.

La recette doit associer chaque événement à un lancement enregistré et à son résultat. Une tâche activée, un lancement en cours ou un succès technique seul ne prouve pas l'achèvement de l'analyse contextuelle. L'absence d'alerte ne signifie pas que tout est validé.

## Travail attendu

1. Figer le SHA de la PR et calculer le delta depuis le dernier reçu, sans confondre la comparaison cumulative et les changements nouveaux.
2. Lire les consignes applicables et le contexte courant, conserver les originaux et citer les sources exactes.
3. Vérifier les contradictions entre décisions, modèles, jobs, médias, versions et états ; distinguer simulation, matériel connecté et validation réelle.
4. Proposer ou appliquer un petit correctif réversible démontré, avec les tests utiles et sans écraser une écriture concurrente.
5. Enregistrer le reçu et les éléments restant à traiter avant de terminer. Dans le même commit, actualiser `data/catalog/repository_manifest.json` avec les tailles et SHA-256, y compris sur la branche des reçus. Une recherche d'outil doit répondre à un manque concret et citer des sources primaires actuelles.

Les générations payantes, les relances aveugles, les commandes de machines et les fusions automatiques ne sont pas autorisées par cette routine. Les bases privées, conversations non exportées et médias hors dépôt ne sont pas présumés accessibles. Les branches sans PR restent couvertes par l'audit technique ; elles ne sont pas couvertes par ce relais contextuel.
