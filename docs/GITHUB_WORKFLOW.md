# Orchestration GitHub

Destination actuelle : `Momolscode/BOJART`, publique. L’ancien `bojart-jarvis` est historique. Visibilité inchangée.

1. Lire le contexte et actualiser la branche distante ; utiliser une branche par session.
2. Importer les sources privées localement. Versionner seulement code, documents relus, références et empreintes utiles.
3. Garder les contradictions visibles jusqu’à réconciliation ; mettre à jour la passation.
4. Tester le composant, exécuter `tools/validate_repository.py` et relire `git diff --cached`.
5. Créer un commit cohérent et une PR si plusieurs sessions travaillent ensemble. Comparer à la nouvelle tête distante ; aucun force-push.
6. Vérifier SHA distant et fichiers publiés.

Le workflow de CI n’a que des droits de lecture et un groupe de concurrence par branche. Il ne pousse, n’imprime et ne déploie rien. Sa présence n’active pas une protection de branche.

L’import initial garde le commit distant comme parent. Un arbre complet est préparé puis la référence est avancée avec tête attendue. Si elle change, relire et réconcilier avant de retenter.

Les historiques M07/Sites restent dans le bundle et les dépôts d’origine. Les copies de sites ici ne se déploient pas automatiquement. Les archives et médias sont référencés, pas poussés en Git ordinaire. Un pointeur ne prouve pas le transfert des octets ; vérifier le téléchargement/restauration d’un futur remote média.
