# Mémoire : mise à jour et reprise après interruption

Une actualisation du contexte doit publier un ensemble complet de documents. Si un fichier est invalide, inaccessible ou si le processus est interrompu avant validation, la version précédemment enregistrée doit rester exploitable.

## Import atomique

L’indexation au lancement, l’actualisation du panneau, l’initialisation MCP et la commande mémoire `index-repo` utilisent une seule transaction SQLite pour le lot. La commande `ingest` applique la même règle à son dossier sélectionné. Versions, index de recherche, événements et retraits deviennent visibles ensemble après validation. Une erreur annule les changements de ce lot.

Les imports individuels conservent leur fonctionnement. Les opérations imbriquées utilisent des points de sauvegarde : annuler une opération interne ne valide pas prématurément le reste du lot.

Les octets sources sont conservés séparément, de manière immuable. Un import interrompu peut laisser un objet préparé mais non référencé. Cet objet reste hors des résultats et hors des sauvegardes fondées sur les références validées. Aucune suppression automatique n’est ajoutée.

Les écritures sont sérialisées par SQLite ; les lectures continuent avec le journal WAL. Ce mécanisme ne fige pas les fichiers source sur disque pendant qu’un autre logiciel les modifie. Il faut toujours indexer un ensemble de fichiers stabilisé.

## Contexte cohérent

Les faits de référence et les passages d’une réponse sont lus dans un même instantané SQLite. Une mise à jour validée entre ces deux lectures ne mélange ainsi pas l’ancien registre avec les nouveaux passages. Le JSON de reprise indique `consistency: single_committed_sqlite_snapshot`, en complément des versions et empreintes déjà présentes.

Cette cohérence porte sur les données enregistrées. Elle ne transforme pas une proposition en fait, ne vérifie pas automatiquement une réponse générée et ne donne aucune autorité sur une machine.

## Vérification reproductible

Depuis le Python de l’environnement BOJ.ART :

```bash
python -m unittest discover -s tests_agent -p test_atomic_memory.py -v
python tools/check_startup.py --abrupt --output .bojart-audit/forced-restart.json
```

Les douze cas ciblés couvrent un fichier invalide au milieu d’un lot, la reprise idempotente, les lecteurs concurrents, les retraits, les transactions imbriquées, le contexte pendant une actualisation, les deux commandes d’import, l’arrêt forcé avant/après validation et la restauration après un import annulé.

La seconde commande utilise des données temporaires, arrête de force le premier processus du vrai lanceur, redémarre Jarvis puis vérifie le contexte et la restauration. Elle ne touche pas aux dossiers de travail du propriétaire et n’appelle aucun modèle.

Le workflow [Jarvis agent memory](https://github.com/Momolscode/BOJART/actions/workflows/agent-memory.yml) exécute cette recette sous Windows et Linux. Le rapport JSON est conservé comme artefact `memory-restart-<système>` pendant 14 jours. Lire le résultat du commit concerné avant d’annoncer une validation.

Un arrêt forcé de processus n’est pas une coupure électrique du PC. Le disque, les pilotes, le GPU, le micro et les imprimantes nécessitent leurs essais réels sur le poste BOJ.ART.
