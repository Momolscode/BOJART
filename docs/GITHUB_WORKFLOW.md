# Orchestration GitHub

Destination actuelle : `Momolscode/BOJART`, publique. L’ancien `bojart-jarvis` est historique. Visibilité inchangée.

1. Lire le contexte et actualiser la branche distante ; utiliser une branche par session.
2. Importer les sources privées localement. Versionner seulement code, documents relus, références et empreintes utiles.
3. Garder les contradictions visibles jusqu’à réconciliation ; mettre à jour la passation.
4. Tester le composant. Après les derniers changements de fichiers, actualiser le manifeste avec `python3 tools/validate_repository.py --write-manifest`, puis vérifier avec `python3 tools/validate_repository.py`. Inclure le manifeste dans le même commit et relire `git diff --cached`.
5. Créer un commit cohérent et une PR si plusieurs sessions travaillent ensemble. Comparer à la nouvelle tête distante ; aucun force-push.
6. Vérifier SHA distant et fichiers publiés.

Le workflow de CI n’a que des droits de lecture et un groupe de concurrence par branche. Il ne pousse, n’imprime et ne déploie rien. Sa présence n’active pas une protection de branche.

L’import initial garde le commit distant comme parent. Un arbre complet est préparé puis la référence est avancée avec tête attendue. Si elle change, relire et réconcilier avant de retenter.

Les historiques M07/Sites restent dans le bundle et les dépôts d’origine. Les copies de sites ici ne se déploient pas automatiquement. Les trois branches de récupération et la sélection binaire déjà publiée restent distinctes du runtime ; leur périmètre est décrit dans `docs/ETAT_ARCHIVES_2026-11-01.md`. Pour tout autre média, un pointeur ne prouve pas le transfert des octets ; vérifier son téléchargement et sa restauration.

Le [plan d’orchestration](ORCHESTRATION.md) complète l’audit technique : classement, lots de revue et tâches avec dépendances. Il consulte le checkpoint contextuel sans le modifier. Une révision différente, un checkpoint bloqué ou absent laisse la couverture courante inconnue. Les fichiers `orchestration.json` et `orchestration.md` sont joints au même artefact d’audit, avec les empreintes de leurs entrées.
