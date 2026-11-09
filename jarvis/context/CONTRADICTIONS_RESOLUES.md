# Contradictions résolues, sans supprimer l'historique

| Historique | Référence actuelle |
|---|---|
| « Jev est l'agent vocal / réponse vocale » | ASR et TTS sont des moteurs séparés. Jev classe des options structurées. |
| « Tout est prêt / plug-and-play » | Sources et démonstrateurs disponibles ; qualification matérielle, voix et déploiement incomplets. |
| « À droite = moniteur » | Dans M02/M03, c'est un panneau. L'appairage des trois moniteurs n'est pas établi. |
| « LangGraph intégré » dans les premières sources M03 | Depuis M06/M07, `apps/jarvis/app/jarvis_runtime.py` construit réellement le graphe route → guard → dispatch → receipt avec checkpoints SQLite si les dépendances sont présentes ; sinon le statut reste `missing_dependency` et les règles locales prennent le relais. Cette intégration logicielle ne qualifie pas la tour ni les effets physiques. Voir `docs/m07/RELEASE_M07.md`. |
| « 14 017 abonnés uniques » | Chiffres arrondis par compte, recouvrement inconnu ; aucun total exact ni unique. |
| « Grandes figurines = résine obligatoire » | Préférence utilisateur à confronter à la pièce, la matière, la finition et aux essais. |
| « Fichier generated = artistiquement validé » | Validations technique, identité, mouvement, montage et droits distinctes. |
| « Le dernier modèle est le meilleur » | Version et licence vérifiées, benchmark français et charge réelle, retour arrière. |
| « Un clone Git suffit à tout sauvegarder » | Dépôt + coffre des originaux + données runtime + médias externes, avec tests de restauration. |
| « Toute la conversation récupérée » | Mémoire distillée et sources disponibles, pas une transcription intégrale. |
