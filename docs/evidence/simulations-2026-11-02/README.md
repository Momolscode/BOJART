# Jarvis : simulations mesurées du 2 novembre 2026

Trois répétitions complètes sur un hôte Linux x86-64, Python 3.12.14, limite cgroup de huit cœurs CPU et 8 Gio de mémoire. Aucun GPU NVIDIA détecté. Le runtime et le corpus de référence sont ceux du commit `2025ac1c8f376341532fbd2df8a176b0b8fc3de4`, figés avant les ajouts concurrents de récupération R03. Les empreintes des sources, du corpus et du nouveau banc sont conservées dans chaque rapport.

**Ces résultats mesurent le logiciel de mémoire sur cet hôte. Ils ne mesurent pas les réponses du LLM, la 4060 Ti, l'affichage, la voix, la création ou les imprimantes.** Les données synthétiques et les mémoires sont temporaires ; aucun contenu privé de l'utilisateur n'est utilisé.

## Résultats agrégés

| Mesure | Échantillons | Médiane | p95 |
| --- | ---: | ---: | ---: |
| Recherche dans le corpus de référence | 1260 | 0.706 ms | 1.053 ms |
| Construction du contexte, plafond 8 000 octets | 1260 | 1.426 ms | 2.524 ms |
| Construction du contexte, plafond 13 000 octets | 1260 | 1.425 ms | 2.470 ms |
| Requête large sur 5 000 documents synthétiques | 90 | 13.206 ms | 16.014 ms |
| Opération mixte : service seul | 960 | 8.238 ms | 13.050 ms |
| Opération mixte : attente comprise | 960 | 174.041 ms | 331.955 ms |

- Référence attendue dans les cinq premiers résultats : **1 260/1 260**. Il s'agit de **14 questions distinctes répétées 90 fois**, pas de 1 260 questions différentes.
- Contexte de 8 000 octets : référence précise présente **900/1 260**, soit **71,4 %** ; à 13 000 octets : **1 170/1 260**, soit **92,9 %**. Les sources sont sélectionnées entières. Ce critère mesure la présence d'un document désigné, pas la vérité d'une réponse ; d'autres documents peuvent donner la même information.
- Charge mixte : **960 opérations, 0 erreur**, trois lots de 320 avec huit workers et 20 % d'écritures. Les 64 notes de chaque lot sont retrouvées après restauration.
- Pannes : **60 arrêts forcés de processus**, moitié avant commit et moitié après, plus neuf scénarios d'original altéré, de configuration invalide et d'historique périmé : **69/69 contrôles attendus réussis**.
- Chaque sauvegarde/restauration couvre **5 000 documents synthétiques** ; les octets et les références de base sont vérifiés. Les trois restaurations durent de **0,962 à 1,083 seconde**, hors création de la sauvegarde ; les sauvegardes durent de **1,267 à 1,469 seconde**.

## Lecture et décisions

Le temps de recherche seul est faible sur ce corpus. Une rafale de tâches ajoute une attente visible : le p95 passe à environ 332 ms quand on inclut la file. Ces appels restent des opérations documentaires, pas des réponses complètes de Jarvis. Le débit d'un lot court n'est pas une capacité continue garantie.

Le point à travailler est la sélection du contexte : retrouver une source et la conserver dans le paquet sont deux critères différents. À 8 000 octets, les références désignées pour Jev, LangGraph, la destination GitHub et la recherche de hashtags sont omises. À 13 000 octets, celle désignée pour LangGraph reste omise, alors que d'autres documents sur LangGraph sont inclus. Aucun score de réponse générée n'est déduit de ces résultats.

Les paramètres de production n'ont pas été élargis à la suite de ce test. La prochaine comparaison utile porte sur une sélection de passages selon la question et leur coût en octets, sur un jeu nouveau de questions françaises avec revue humaine des réponses. La place disponible dépend aussi des instructions et de l'historique ; 13 000 octets documentaires ne tiennent pas nécessairement dans chaque échange du profil 16K.

## Reproduction et limites

Les p50 sont les médianes et les p95 les rangs supérieurs des mesures brutes regroupées. Les trois répétitions utilisent le même petit jeu de questions ; elles ne constituent ni trois populations d'utilisateurs ni un intervalle de confiance. Le premier passage survient après lecture du corpus pour indexation : il n'est pas un test de cache disque froid. Les contextes sont mesurés dans l'ordre 8 000 puis 13 000 octets ; l'écart de vitesse entre ces variantes ne doit pas être interprété comme un avantage causal.

Les corpus de charge contiennent des identifiants exacts et du texte répétitif de petite taille. Ils exercent les fichiers, les transactions et les requêtes ; ils ne représentent pas la difficulté sémantique de toutes les archives. Arrêter un processus n'équivaut pas à couper l'alimentation du PC. Zéro erreur dans ces essais n'est pas une preuve de fiabilité absolue.

Le [guide exécutable](../../memory/SIMULATIONS.md) permet de refaire le banc sur la tour et de mesurer séparément trente réponses des modèles locaux déjà installés. Aucune statistique de GPU ou de premier token n'est inventée ici. Le workflow GitHub ajoute des mesures propres à ses hôtes Windows/Ubuntu ; elles doivent rester séparées de ces trois relevés.

Rapports complets : [synthèse JSON](summary.json), [répétition 1](run-1.json), [répétition 2](run-2.json), [répétition 3](run-3.json). Les nouvelles versions du corpus produiront d'autres résultats ; leurs empreintes doivent être comparées avant de conclure à une amélioration.
