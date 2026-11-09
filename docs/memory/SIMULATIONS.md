# Simuler et mesurer Jarvis

Le banc exécute le vrai code de mémoire dans des dossiers temporaires. Il mesure le corpus public sélectionné, puis des documents synthétiques, des lectures/écritures concurrentes, une sauvegarde/restauration et des arrêts forcés de processus. Aucun état privé existant n'est importé ou modifié. La première recette chiffrée est dans [les résultats du 2 novembre](../evidence/simulations-2026-11-02/README.md).

## Sur le poste BOJ.ART

Après l'installation Python/Ollama et du profil `speed`, double-cliquer **`Mesurer_BOJART.cmd`** à la racine. Il lance les mesures de mémoire puis celles des modèles déjà présents. Aucun téléchargement, activation de profil ou changement de pilote n'est effectué. Les rapports JSON uniques sont conservés par défaut dans `%USERPROFILE%\BOJART\benchmarks`. Si `BOJART_MEMORY_STATE` est défini, ils vont dans le dossier `benchmarks` voisin de cette mémoire.

Depuis un terminal, les deux parcours peuvent être lancés séparément :

```powershell
.venv\Scripts\python.exe tools/benchmark_jarvis.py --mode memory
.venv\Scripts\python.exe tools/benchmark_jarvis.py --mode models --profile speed --repeats 30
```

Sous Linux, remplacer `.venv\Scripts\python.exe` par `.venv/bin/python`. Le mode mémoire fonctionne sans Ollama. Le mode modèles exige un serveur local et les deux modèles du profil ; `--url http://127.0.0.1:PORT` accepte un autre port local. Une destination distante est refusée. `--output NOUVEAU_FICHIER.json` choisit un rapport ; un fichier existant n'est jamais remplacé.

Fermer les autres tâches lourdes pour un premier relevé, puis refaire le parcours avec la charge habituelle. Conserver les deux rapports : ce sont des conditions différentes. Le banc ne ferme aucune application et n'envoie aucune commande d'atelier.

## Ce que les chiffres signifient

- **Médiane** : durée centrale observée. **p95** : durée au-dessous de laquelle se trouvent au moins 95 % des observations, calculée au rang supérieur. Les valeurs sont en millisecondes sauf indication contraire.
- **Mémoire** : 14 questions de référence répétées 30 fois, contextes de 8 000 et 13 000 octets UTF-8, paliers de 100/1 000/5 000 documents synthétiques, 320 opérations avec huit workers et 20 % d'écritures. Les corpus synthétiques ont une taille et des identifiants simples ; leur succès ne mesure pas la compréhension de documents difficiles.
- **Concurrence** : durée de service et durée incluant l'attente sont séparées. Un lot de 320 tâches n'est pas constitué de 320 utilisateurs actifs simultanément. Le débit de ce lot n'est pas une capacité de service soutenue.
- **Modèles** : un premier appel conservé séparément, puis 30 appels répartis sur quatre cas synthétiques. Temps complet du client, durées fournies par Ollama, tokens/s, présence des termes attendus et troncatures. Les temps excluent la recherche documentaire, le navigateur et la voix. Les répétitions peuvent profiter du cache ; le premier appel n'est pas présenté comme un démarrage à froid.
- **Matériel** : informations non sensibles de l'hôte, relevé ponctuel NVIDIA si disponible et modèles chargés signalés par `/api/ps`. Ces instantanés ne sont pas un pic de VRAM. Une absence de donnée reste inconnue.
- **Pannes** : un arrêt de processus avant/après commit SQLite ne simule pas une panne électrique ou une corruption de disque. Les scénarios supplémentaires altèrent un original temporaire, invalident les réglages de modèle et rendent une ancienne réponse périmée.

Les quatre cas du modèle vérifient projet, donnée manquante, instruction importée trompeuse et référence dans un texte long. Ils ne constituent pas une mesure générale d'intelligence, de français ou de résistance aux injections. Un échec de transport interrompt cette série ; les appels restants ne sont pas comptés comme réussis. Les percentiles décrivent uniquement les réponses terminées et le rapport distingue série complète et partielle.

Le code de retour du mode mémoire signale les contrôles d'intégrité et les références retrouvées. Celui du mode modèles signale les critères littéraux et embeddings ; les dépassements de l'objectif de latence sont rapportés séparément. Aucun résultat ne promeut automatiquement `production_ready` ou les portes de qualification de l'atelier.

## Améliorations guidées par les mesures

La première expérience retrouve la référence attendue dans les cinq premiers résultats pour les 14 questions, mais le paquet de contexte de 8 000 octets ne conserve cette source précise que pour dix questions. À 13 000 octets, treize la conservent. Plusieurs sources fournissent parfois la même réponse ; l'absence d'une référence attendue n'est pas, seule, une réponse fausse. Le banc conserve cette limite au lieu de changer les questions ou de compter les sources trouvées comme des réponses correctes.

Priorité suivante : comparer une sélection de passages tenant compte de la question et de leur taille, avec des questions françaises nouvelles et une revue des réponses. Vérifier à la fois la présence des preuves, les contradictions et la latence. Ne pas augmenter aveuglément le contexte sur une carte de 8 Go : le budget documentaire en octets n'est pas la fenêtre du modèle en tokens. Le profil déjà installé garde son adaptation de l'historique et son contrôle d'enveloppe.

Pour la première réponse visible et les intervalles entre tokens, **AIPerf** est la piste retenue. NVIDIA indique que GenAI-Perf est en retrait et renvoie vers AIPerf ; son exemple officiel utilise Ollama. Révision consultée : `ai-dynamo/aiperf@6b565f4e4872755087c13285ba43dd0695c12b8a`. Installation et compatibilité avec ce poste restent à essayer, dans un environnement séparé ; cet outil n'est pas installé par le banc léger. La diffusion progressive de la réponse dans l'interface Jarvis reste un travail distinct.

Références primaires consultées le 2 novembre 2026 : [horloge monotone Python](https://docs.python.org/3.12/library/time.html#time.perf_counter_ns), [concurrence SQLite WAL](https://sqlite.org/wal.html), [mesures Ollama](https://docs.ollama.com/api/usage), [modèles chargés](https://docs.ollama.com/api/ps), [transition NVIDIA](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/perf_analyzer/genai-perf/README.html), [AIPerf](https://github.com/ai-dynamo/aiperf/tree/6b565f4e4872755087c13285ba43dd0695c12b8a).

Le workflow **Jarvis measured simulations** reproduit le mode mémoire sous Ubuntu et Windows lors des changements de mémoire ou de corpus, et sur déclenchement manuel. Il conserve les résultats comme artefacts pendant 30 jours. Les trois rapports de la recette initiale sont aussi versionnés dans le dépôt ; les chiffres d'un autre hôte ne deviennent pas ceux de la RTX 4060 Ti.
