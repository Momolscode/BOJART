# Réception par périmètre

Depuis le clone, en environnement isolé Python 3.12 :

- Mémoire source : `python -m unittest discover -s tests -v`.
- Adaptateur agent et conversations : `python -m unittest discover -s tests_agent -v`.
- Orchestration et préparation : `python -m unittest discover -s tests_ops -v`.
- Recherche historique : `python tools/evaluate_memory.py`.
- Préparation hors ligne : `python tools/prepare_jarvis.py status`, puis `build --destination DOSSIER_NEUF_HORS_CLONE`.
- Contrôle du dépôt : `python tools/validate_repository.py`. L’option `--write-manifest` modifie le manifeste ; l’utiliser après les modifications autorisées, puis relancer la validation.
- Reprise logicielle : lire `tools/check_startup.py`, puis utiliser `--abrupt --output CHEMIN_PREUVE` dans une recette isolée. Le navigateur est optionnel et doit être fourni sans reprendre un profil utilisateur.

Le runtime exige ses dépendances natives et des médias authentiques vérifiés. Lire les scripts de recette M05/M07 et leurs chemins avant exécution ; conserver versions de moteurs, fixtures et SHA de fichiers. Ne pas lancer une installation de modèle ou une machine pour satisfaire artificiellement un test local.

Format de preuve minimal : révision de base, SHA de fichiers modifiés, commande exacte, environnement, date UTC, exit code, nombre de cas, succès/échecs/skips, log et portée. Pour un défaut : stimulus et résultat observé dans un état isolé. Pour un reçu navigateur : distinguer accusé logique et écran physique.

Une couverture globale conserve les résultats antérieurs seulement si les octets et le contexte du scénario sont comparables. Le client Claude, les comptes fournisseurs, le microphone, la carte GPU et les imprimantes sont des recettes distinctes.
