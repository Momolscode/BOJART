# Simuler une demande à Jarvis : dashboards et figurine de 1 m

État du 2 novembre 2026. Les commandes d'affichage passent par le runtime réel et ses bases SQLite temporaires. La fabrication reste un **simulateur séparé**, sans branchement à la voix, sans modèle de Végéta et sans connecteur machine.

## Ce que tu peux dire pour l'affichage

| Transcription | Résultat logiciel |
|---|---|
| « Jarvis, affiche le dashboard atelier ! » | Planning **démonstratif** à gauche |
| « Affiche le dashboard dossiers » | Dossiers au centre |
| « Affiche le dashboard Studio » | Catalogue Studio à droite |
| « Affiche le dashboard contenus » | Préparations éditoriales à droite |
| « Affiche le dashboard conception » | Poste CAO du dossier au centre ; ne crée pas de personnage |
| « Affiche le dashboard base métier » | Base documentaire au centre |
| « Affiche les trois dashboards » | Planning, dossiers et modèle sélectionné ou Studio ; trois reçus requis |
| « Affiche un des dashboards » | Demande quel tableau afficher ; aucun choix au hasard |

« Montre » et « Ouvre », ainsi que « tableau de bord », sont acceptés pour les sept noms déclarés (atelier, planning, dossiers, Studio, contenus, conception, base métier). Ce sont des phrases exactes normalisées, pas une reconnaissance générale du langage. Une négation ou une instruction ajoutée n'est pas supprimée pour rendre la phrase acceptable. Les anciennes commandes restent disponibles.

Ces alias n'appellent pas Jev. Le LLM local du panneau mémoire n'est pas devenu un pilote de machines. Dans le vrai parcours, le micro doit encore être transcrit correctement et les vues doivent être ouvertes/appairées ; les essais de ce dossier commencent après cette transcription.

## Scénario « prépare un Végéta 3D d'un mètre »

**État actuel du runtime vocal :** cette demande retourne `CLARIFY`, sans créer de géométrie ni lancer une impression. Le script de simulation appelle séparément un prototype de préparation avec les paramètres explicitement fournis par l'auteur du test : sujet Végéta, hauteur 1 000 mm. Ce n'est pas une interprétation réalisée par un modèle de langage.

Le prototype produit un dossier `NEEDS_INPUT`, avec quatre éléments à compléter :

1. Le fichier 3D source, ses unités et sa hauteur mesurée.
2. L'inventaire réel des imprimantes, matières, volumes utiles, profils et disponibilités.
3. Une découpe avec orientations, supports, assemblages et cotes vérifiés à la hauteur cible.
4. Des durées et quantités issues du slicer pour chaque combinaison pièce / profil.

Réponse textuelle préparée par le prototype, **non prononcée par Jarvis** : « Je prépare le dossier Végéta, hauteur 1000 mm. Il me manque le modèle 3D et les profils réels des imprimantes pour découper et chiffrer le travail. »

Le second volet utilise **24 boîtes orientées et huit imprimantes entièrement fictives**. Il n'y a ni STL, ni sculpture, ni découpe géométrique ; ces boîtes ne prouvent pas qu'un assemblage fera exactement 1 m. Les durées sont des hypothèses renseignées par couple pièce / machine. Elles ne proviennent pas d'un slicer ou d'une mesure réelle.

Le planificateur filtre le procédé, la matière, le volume utile, les marges et la disponibilité. Pour un plateau circulaire, il contrôle la diagonale de la boîte, pas seulement ses côtés. Il conserve l'orientation fournie ; aucun retournement automatique n'est déclaré imprimable. Il tient compte des charges initiales et d'un temps entre deux travaux.

Il compare une distribution à tour de rôle à une heuristique : pièces longues d'abord, affectation à la machine compatible qui termine le plus tôt. Il calcule aussi une borne inférieure optimiste et signale que l'optimum n'est pas démontré. Aucun qualificatif « meilleur solveur » ou « optimal » n'est justifié par cette expérience.

| Cas synthétique | Résultat calculé |
|---|---|
| 24 pièces, huit machines, tour de rôle | 25 h 15 jusqu'à la dernière fin d'impression supposée |
| Mêmes données, répartition par fin la plus proche | 21 h 24 ; réduction de 15,25 % sur ce jeu précis |
| Une machine indisponible **avant tout démarrage** | 24 pièces réparties sur sept machines ; 23 h 33 |
| Une pièce dépasse tous les volumes | `INFEASIBLE` ; aucun plan présenté comme exécutable |
| Une pièce résine, parc exclusivement FDM | `INFEASIBLE` |
| Résultat d'impression perdu ou impression en cours | `NEEDS_RECONCILIATION` ; pas de réimpression automatique |
| Hauteur changée à 1,20 m sans nouvelles pièces/estimations | Refus ; nouvelles données de découpe/slicing nécessaires |

Les huit machines du test ne représentent pas ton parc. Les temps n'incluent pas assemblage, finition, post-traitement, horaires opérateur, renouvellement matière ou pannes. Une boîte qui tient sur un plateau ne prouve pas l'imprimabilité ni la tenue de la pièce. Le simulateur refuse les données non marquées fictives et ne génère aucun G-code.

## Rejouer les essais

Sur Windows : double-cliquer `Simuler_BOJART.cmd`. Il utilise le Python du dépôt s'il existe, sinon Python 3.12, et affiche le chemin d'un rapport JSON unique. Aucune installation, ouverture du microphone ni commande physique.

Depuis la racine :

```sh
python -m unittest discover -s tests_workflows -v
python tools/simulate_jarvis_workflows.py --repeats 30 --output rapport-workflows.json
```

Choisir un chemin neuf : les rapports existants ne sont pas écrasés. Les bases de travail sont créées puis supprimées dans un répertoire temporaire. Aucune donnée de l'atelier n'est consultée.

Le moteur utilisé est inscrit dans le rapport : `missing_dependency` signifie le repli en règles locales, `sqlite_ready` signifie LangGraph avec checkpoint SQLite. La CI exécute les deux modes sur Linux et Windows. Ses mesures restent séparées des mesures locales et de celles à réaliser sur le PC RTX 4060 Ti.

## Preuve et limites de la mesure

Voir [les trois campagnes et le rapport](evidence/workflows-2026-11-02/README.md). Sur l'hôte Linux de test : **810 essais**, neuf formulations répétées 90 fois chacune. P95 du dépôt de commande : **19,95 ms** ; p95 jusqu'au reçu synthétique : **32,06 ms**. Les 16 scénarios de refus/panne/reprise passent dans chacune des trois campagnes.

Ces temps mesurent des appels Python et SQLite. Pas de HTTP, navigateur, SSE, microphone, reconnaissance, synthèse vocale, Jev, LLM ou GPU dans cette mesure. Le reçu est injecté par un client d'essai, sans rendu visuel. Il ne faut pas appeler ces chiffres « latence vocale » ou « délai d'affichage physique ».

Pour le vrai Végéta : le prochain raccordement est modèle 3D vérifié → découpe/assemblage → profils slicer du parc → planning révisable → validation opérateur → connecteur qualifié. Aucune de ces étapes physiques n'est déclarée terminée par ce simulateur.
