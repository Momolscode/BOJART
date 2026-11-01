# Une mémoire vérifiable pour Jarvis

Choix du 1 novembre 2026, fondés sur la documentation officielle consultée et le code M07 retrouvé. L’objectif est un contexte utile et traçable dès le lancement. Aucun classement universel de « meilleur modèle » n’est affirmé : le GPU, la RAM et les requêtes réelles ne sont pas encore connus.

## Ce qui est réellement intégré

La mémoire documentaire existante conserve des originaux immuables par SHA-256, leurs versions et leur provenance. `bojart_memory.agent` ajoute des notes, épisodes et vecteurs **dans le même `memory.sqlite`**. Les sauvegardes existantes emportent ces tables. Les journaux et checkpoints opérationnels M07 restent distincts.

| Niveau | Support et règle |
|---|---|
| Référence | Registre `claims.jsonl`, source obligatoire, date, statut, liens de correction ; les faits remplacés sortent du contexte courant |
| Documents | Originaux conservés, recherche par projet, version courante par défaut, citations chemin/lignes/empreinte |
| Propositions | Notes locales, jamais promues automatiquement ; valeurs divergentes d’un même sujet signalées |
| Épisodes | Conversations du panneau mémoire, question, réponse et contexte exact ; isolement par session et projet |
| Tâche | Contexte limité à 14 000 caractères par défaut, références et empreinte ; estimation de tokens explicitement approximative |
| Procédures | `AGENTS.md`, passation et documentation versionnés ; documents récupérés traités comme données |

Le registre de faits est conservé pour chaque périmètre, puis ses lignes sont filtrées par projet. Le constructeur de contexte exclut le registre brut des passages récupérés : il transmet uniquement les faits du périmètre choisi. Les imports de conversations doivent être explicitement choisis et étiquetés par projet.

## Outils retenus et statut

| Outil | Utilité | Décision pour ce lancement |
|---|---|---|
| SQLite FTS5 / BM25 | Sources, versions, recherche exacte, sauvegarde sans serveur | Actif dès l’installation ; une base documentaire unique |
| Ollama + EmbeddingGemma | Recherche par sens en local, multilingue | Adaptateur livré ; téléchargement et activation explicites. EmbeddingGemma est un point de départ léger, à évaluer en français |
| Fusion RRF | Combiner les rangs lexicaux et vectoriels | Implémentée, constante 60 ; repli lexical si Ollama échoue. Scan vectoriel exact pour ce petit corpus |
| MCP stdio | Fournir le même contexte aux clients compatibles | Serveur livré : recherche, contexte, statut et proposition sourcée |
| LangGraph + checkpoints SQLite | Reprendre les tâches et décisions interrompues | Déjà prévu dans M07, conservé ; dépendances installées avec `--engines`. Ce n’est pas la mémoire documentaire |
| Qwen3 Embedding / Reranker | Candidats pour mieux rechercher et reclasser les passages | À comparer sur le GPU réel ; aucun reranker livré ni gain de précision présumé |
| Qdrant | Index vectoriel et fusion hybride à plus grande échelle | Évolution possible si le scan exact ou la concurrence deviennent limitants ; pas de service installé |
| Graphiti | Relations et faits temporels entre projets, pièces et machines | Étape ultérieure avec serveur graphe et modèle d’extraction qualifié ; pas de graphe généré ici |
| Letta | Agent disposant de blocs mémoire modifiables | Comparatif uniquement ; pas de second agent persistant ajouté au lancement |

L’API Ollama `/api/embed` est appelée avec `truncate:false` : un dépassement de contexte produit une erreur visible au lieu de tronquer silencieusement. Les vecteurs sont isolés par nom **et digest** de modèle. Les appels restent sur `127.0.0.1` ; les modèles distants déclarés par Ollama et les redirections sont refusés. Aucun modèle ni poids n’est téléchargé automatiquement.

La conversation du panneau utilise un modèle Ollama local choisi après l’inventaire du PC. Elle conserve le contexte exact, avertit si les références entre crochets ne correspondent pas au contexte, et marque toute réponse comme générée, non vérifiée automatiquement. Ce contrôle de références ne prouve pas la vérité d’une réponse. Aucun outil d’action n’est fourni au modèle.

## Faire progresser la qualité

Commencer par les dix cas de recherche existants dans `tools/evaluate_memory.py`, puis ajouter des questions réelles : synonymes français, corrections R02/R03, modèle d’imprimante inconnu, conflit de sources, question sans réponse et séparation des projets. Comparer BM25 seul et hybride sur les mêmes documents. Mesurer rappel des sources, précision des citations, abstention, latence et consommation RAM/VRAM. Les tests avec vecteurs simulés prouvent la mécanique de fusion, pas la qualité d’un modèle réel.

Le contextual retrieval d’Anthropic propose d’enrichir chaque morceau de document avant indexation et d’ajouter un reclassement. Notre code joint déjà chemin, lignes et provenance au contexte final, mais **n’implémente pas cette génération d’enrichissements ni un reranker**. Les expérimenter comme données dérivées, en conservant l’original et en comparant les résultats avant activation.

Le graphe temporel devient utile si les questions nécessitent plusieurs relations et dates, par exemple quelle pièce, quelle machine et quel profil étaient valides lors d’un essai. Les corrections explicites et les versions suffisent au démarrage ; une extraction automatique de relations doit rester révisable.

## Sources officielles

- [LangGraph : persistence](https://docs.langchain.com/oss/python/langgraph/persistence) — distingue état d’un fil et informations durables entre fils.
- [Ollama : API embeddings](https://docs.ollama.com/api/embed) et [EmbeddingGemma](https://ollama.com/library/embeddinggemma) — modèle de départ et endpoint local.
- [Qwen3 Embedding et Reranker](https://qwenlm.github.io/blog/qwen3-embedding/) — candidats multilingues à évaluer, pas une qualification du matériel BOJ.ART.
- [Qdrant : hybrid queries](https://qdrant.tech/documentation/concepts/hybrid-queries/) — fusion et requêtes hybrides.
- [Anthropic : contextual retrieval](https://www.anthropic.com/research/contextual-retrieval) — principes d’enrichissement et reclassement ; les chiffres de leur étude ne sont pas des résultats BOJ.ART.
- [Graphiti](https://github.com/getzep/graphiti) — graphe temporel et dépendances de stockage.
- [Letta : memory blocks](https://docs.letta.com/guides/agents/memory-blocks/) — comparaison d’architecture, sans intégration.
- [MCP : outils](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) — contrat d’accès local.
