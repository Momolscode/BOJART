# Continuité des conversations et sources actualisées

Le panneau « Parler à Jarvis » conserve les échanges dans la mémoire locale. Pour une nouvelle réponse, il prépare désormais un historique structuré au lieu de couper les derniers caractères d’un journal JSON.

## Ce qui est transmis au modèle

Les six derniers épisodes de la même session et du même projet sont examinés. Chaque échange retenu contient une question complète, sa date, son identifiant et le statut de son ancienne réponse.

Une réponse antérieure peut être reprise uniquement si son contexte possède des preuves vérifiables : versions documentaires encore courantes, originaux présents et intacts, faits de référence et éventuelles contradictions inchangés. Elle reste explicitement **non vérifiée** : la présence de sources ne prouve pas que le modèle les avait interprétées correctement.

Si un document a changé ou a été retiré, si un original manque, si un fait est remplacé ou devient contradictoire, l’ancienne réponse est écartée du contexte envoyé au modèle. Sa question et la raison de cette exclusion restent disponibles. Un ancien épisode sans contexte vérifiable, ou une réponse sans preuve, suit la même règle.

Exemple : une ancienne réponse s’appuyait sur « version alpha ». Après indexation de « version bêta », une nouvelle question reçoit les documents actuels ; la réponse alpha reste dans le journal, mais son texte n’est pas réinjecté comme historique exploitable.

## Budget et cohérence

L’historique sérialisé occupe au maximum 6 000 caractères Unicode, métadonnées comprises. Les échanges les plus récents sont prioritaires. Une réponse trop longue est écartée en entier ; le texte n’est pas coupé au milieu d’un champ JSON. Les échanges qui ne tiennent pas sont comptabilisés.

Le contexte documentaire et le contrôle de fraîcheur des échanges partagent le même instantané SQLite. Une indexation concurrente ne peut donc pas faire comparer un ancien contexte documentaire à un nouvel état de ses sources.

Chaque nouvel épisode conserve le paquet conversationnel exact transmis au modèle, ainsi que son empreinte, sa taille et les nombres d’échanges ou de réponses écartés dans `response.history_usage`. Les sauvegardes documentaires existantes incluent ces épisodes ; aucune autre base n’est créée.

## Relecture et limites

La commande `history` conserve l’historique original. Réessayer une requête avec le même identifiant renvoie la réponse déjà enregistrée : c’est une reprise de requête, pas une nouvelle analyse. Une nouvelle question utilise un nouvel identifiant et réévalue les sources.

Ces contrôles détectent les évolutions enregistrées dans la mémoire. Ils ne découvrent pas seuls une modification sur le PC, une nouvelle décision dans un ancien chat ou un fait extérieur. Il faut importer ou indexer les documents concernés. Aucune ancienne réponse générée n’est promue automatiquement en fait de référence.

## Vérification

```bash
python -m unittest discover -s tests_agent -p test_conversation_context.py -v
```

Les 17 cas couvrent les changements de documents et de faits, les sources retirées ou absentes, les conflits, les références invalides, la séparation des projets et sessions, la mise à jour concurrente, la restauration, la reprise de requête et le budget exact du JSON. Le client Ollama est simulé : ces essais vérifient la préparation du contexte et sa transmission, pas la qualité d’un modèle réel.

Ils font partie du workflow [Jarvis agent memory](https://github.com/Momolscode/BOJART/actions/workflows/agent-memory.yml), exécuté sous Windows et Linux.
