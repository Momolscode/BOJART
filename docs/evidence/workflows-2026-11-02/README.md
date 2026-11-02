# Preuve — demandes d'affichage et préparation fictive d'une figurine de 1 m

2 novembre 2026. Base inspectée : `6cda578030b619c7b459515e77a34b80b2b5f396`.
Les empreintes des fichiers réellement exécutés figurent dans chaque rapport. Les trois rapports partagent les mêmes empreintes. Les sorties ne contiennent ni bases actives, ni inventaire privé, ni médias de l'utilisateur.

## Ce qui a été exécuté

Les vraies classes `Store`, `DisplayProposals`, `ControlTower` et `JarvisRuntime`, avec SQLite sur disque temporaire. Le serveur périphérique est une fixture minimale, le contexte est fictif et les reçus sont injectés directement par le script. Aucun navigateur n'a affiché les tableaux pendant cette expérience. La source `voice` indique uniquement l'entrée attendue après ASR, elle ne démontre aucune captation.

Les trois campagnes locales utilisent le repli `missing_dependency` : LangGraph n'est pas installé sur cet hôte. Elles ne valident donc pas ses performances. Le workflow GitHub `Jarvis transcript and fleet simulations` vérifie séparément le repli puis les dépendances LangGraph épinglées, sur Linux et Windows ; il exige `sqlite_ready` dans son second rapport. Les résultats de CI sont des preuves supplémentaires attachées à leur SHA, sans les mélanger aux statistiques ci-dessous.

Hôte local : Linux x86_64, Python 3.12.14 ; limites du conteneur : quota de huit cœurs, 8 Gio de mémoire. Il ne s'agit pas de la tour Ryzen / RTX 4060 Ti. Aucun GPU, ASR, Jev, LLM, service HTTP, flux SSE, slicer ou imprimante testé ici.

## Résultats mesurés

Neuf formulations, 30 répétitions par campagne, trois campagnes séquentielles : **810 essais**. Chaque essai emploie un identifiant neuf, sans appel distant. Les vues d'essai sont déjà appairées. La création initiale de la base et du runtime est hors chronomètre ; le premier ordre est inclus. Les valeurs utilisent `perf_counter_ns`. P50 et p95 sont les rangs empiriques, pas des intervalles de confiance.

| Mesure sur 810 essais | P50 | P95 | Maximum |
|---|---:|---:|---:|
| Soumission → commande persistée | 11,781 ms | 19,950 ms | 45,304 ms |
| Soumission → reçu synthétique relu | 15,749 ms | 32,062 ms | 76,551 ms |

810/810 résultats attendus dans cet ensemble fermé. **Ce n'est pas un taux de compréhension vocale ou de compréhension de phrases nouvelles.** Un reçu `rendered` est ici une valeur fournie par le client de test, pas une capture d'écran ni une preuve de rendu.

Le fichier [before.json](before.json) conserve l'observation avant correction : les trois ordres historiques passent ; six formulations avec « dashboard » demandent une clarification. Après ajout des alias exacts, les neuf passent. Les demandes ambiguës, de création de Végéta et de lancement d'impression restent sans commande physique. Les tests unitaires parcourent aussi l'ensemble des alias locaux et vérifient l'absence d'appel au décideur externe.

## Pannes et cohérence

**16 scénarios par campagne, 48/48 réussis :** dashboard non précisé ; modèle non sélectionné ; préparation de personnage non raccordée ; ordre physique non pris en charge ; négation ; action supplémentaire ; révision périmée ; contexte changé depuis l'écoute ; réponse perdue puis redémarrage sous le même identifiant ; identifiant réutilisé pour un autre contenu ; scène partiellement distribuée ; vue absente puis revenue ; vue en échec ; annulation ; vue d'un autre projet ; contexte changé avant le reçu.

La scène reste à 2/3 jusqu'au troisième reçu. La reprise partielle réutilise les références des enfants. Trois soumissions séparées par un redémarrage du runtime produisent une seule commande. Ces essais ne sont pas des crashs brutaux du processus : ceux de la mémoire sont documentés séparément dans `../simulations-2026-11-02/`.

## Répartition fictive de fabrication

Le fichier [fleet_1000mm_synthetic.json](../../../jarvis/fixtures/fleet_1000mm_synthetic.json) contient huit profils fictifs et 24 boîtes orientées, pas une sculpture. La hauteur de scénario est 1 000 mm, sans preuve d'assemblage. Les durées sont des hypothèses explicites. Une machine a un plateau cylindrique, les autres un plateau rectangulaire. Les marges et les temps de changement sont pris en compte.

| Scénario | Fin calculée de la dernière impression supposée |
|---|---:|
| Tour de rôle, huit machines | 1 515 min — 25 h 15 |
| Pièces longues puis machine terminant le plus tôt | 1 284 min — 21 h 24 |
| Une machine hors ligne avant démarrage | 1 413 min — 23 h 33 |

Gain sur cette seule fixture : **231 min, soit 15,25 %**, à entrées identiques. Ce gain n'est pas généralisable. La borne inférieure optimiste du cas huit machines est 957,844 min ; le planning calculé est 34,05 % au-dessus de cette borne. L'optimum n'est pas prouvé ; il reste de la place pour un solveur plus complet et des données réelles.

Les cas pièce trop grande et procédé incompatible retournent `INFEASIBLE`. Une pièce en cours ou de résultat inconnu interdit la replanification automatique. Une hauteur modifiée exige de nouvelles pièces et estimations. Aucun plan de ce prototype ne peut autoriser une impression.

Les [20 tests dédiés](tests.log) couvrent aussi les marges, les coins d'un plateau circulaire, les unités, les valeurs non finies, les doublons, l'exclusion des pièces déjà terminées, les estimations manquantes, la stabilité des entrées et l'absence de chevauchement. Quarante jeux à durées variables, générés avec une graine fixe, vérifient les invariants des deux heuristiques. Un petit cas énuméré exhaustivement contrôle la validité de la borne inférieure.

## Fichiers et reproduction

La première intégration du long guide expérimental dans les références courantes a fait reculer `context/CURRENT.md` hors des cinq premiers résultats pour « LangGraph » : 13/14 cas de recherche passaient. La correction conserve un [catalogue d'usage actuel](../../COMMANDES_DASHBOARD.md) en référence canonique et ce compte rendu daté en journal de session. Le guide complet reste consultable. Aucun cas attendu ni seuil de test n'a changé ; aucune source n'est effacée. Les 14/14 cas passent à nouveau, avec citations vérifiées. Voir [la régression conservée](retrieval-regression.json) et [le nouveau contrôle](retrieval-after.json).

- [summary.json](summary.json) : agrégats, portée et empreintes des trois rapports.
- [run-1.json](run-1.json), [run-2.json](run-2.json), [run-3.json](run-3.json) : mesures individuelles, dialogues d'essai, résultats des gardes et plannings complets.
- [Guide d'utilisation et limites](../../SIMULATIONS_ATELIER.md).

```sh
python -m unittest discover -s tests_workflows -v
python tools/simulate_jarvis_workflows.py --repeats 30 --output nouveau-rapport.json
```

Sur le PC, `Simuler_BOJART.cmd` rejoue la même expérience sans activer de périphérique. La qualification réelle nécessite une autre campagne : voix française dans le bruit, rendu visible sur les moniteurs, modèle 3D de référence, slicing, profils et reçus d'une machine qualifiée. Aucun résultat de cette page ne remplace ces mesures.
