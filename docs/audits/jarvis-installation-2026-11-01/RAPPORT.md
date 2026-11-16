# Installation et orchestration Jarvis — évaluation datée
Évaluation du 1 novembre 2026. Références exactes et sources : README.md, PREUVES.json et SOURCES.json.

## Conclusion
Le socle local est assez avancé pour une **installation de validation** : la mémoire s’installe, l’application démarre et les pages répondent dans l’environnement Linux testé. Le Jarvis complet de l’atelier, avec voix continue, création, imprimantes et publication autonome, n’est pas démontré par cette recette.

La qualification du PC cible reste ouverte : OS, GPU, moniteurs, micro, poids ASR et parc d’imprimantes n’ont pas été testés ici. Aucun pourcentage global de préparation n’est calculé.

## Ce qui a été observé
Sur e5cd9f3, Python 3.12.14 et SQLite 3.53.1 avec FTS5 ont permis l’installation minimale dans un environnement isolé. Les six routes /workspace, /memory, /tower, /studio, /growth et /knowledge ont répondu HTTP 200. Une recherche documentaire sur Jev a rendu des citations.

La restauration documentaire dans un dossier neuf a renvoyé ok=true, sans anomalie, avec 21 objets, 23 sources, 23 versions, 43 fragments et 23 événements. Cette observation concerne la mémoire documentaire. Les cinq bases opérationnelles M07 ont leur propre circuit de sauvegarde ; leur restauration réelle complète n’est pas démontrée par ce résultat documentaire.

L’état HTTP annonçait production_ready=false et physical_commands=false. Le runtime annonçait langgraph=missing_dependency : **ce lancement a utilisé le repli local**, et non le moteur LangGraph installé. La conversation continue et la publication étaient désactivées. FFmpeg/ffprobe étaient détectés sur l’hôte ; cela ne prouve pas une chaîne de production artistique autonome.

## Tests sélectionnés
| Suite | Référence | Résultat |
|---|---|---:|
| tests/ | e5cd9f3 | 37 réussis |
| tests_agent/ | e5cd9f3 | 25 réussis |
| jarvis/tests/test_jarvis_m06.py | e5cd9f3 | 42 réussis |
| jarvis/tests/test_jarvis_m07.py | e5cd9f3 | 22 réussis |
| tests_ops/ | 3c28821 | 46 réussis |
| voice_endpoint.test.cjs + memory_context.test.cjs | e5cd9f3 | 11 réussis |
| Évaluation documentaire lexicale | e5cd9f3 | 10 cas sur 10 avec résultat attendu dans les cinq premiers et citations vérifiées |

Total des suites Python sélectionnées : 172, sur deux références explicites. Les 10 cas documentaires sont un petit jeu rédigé à la main ; ils ne mesurent ni la qualité d’un LLM ni une compréhension générale. Les doubles des services voix/Jev ne qualifient pas les services réels. La recette historique de 578 tests citée ailleurs dans le dépôt n’a pas été réexécutée dans cette évaluation.

Les résumés observés sont transcrits dans preuves/. Les journaux bruts locaux complets n’ont pas pu être joints après la déconnexion de l’environnement. L’auditeur devra enregistrer de nouveaux journaux avec sa version, ses dépendances et son environnement.

## Comment les actions sont orchestrées
Le fichier jarvis/apps/jarvis/app/jarvis_runtime.py construit réellement un graphe à quatre nœuds :
route → guard → dispatch → receipt. Un refus ou une confirmation encore attendue passe de guard à receipt sans distribution. Lorsque les dépendances sont disponibles, LangGraph utilise des checkpoints SQLite et une durabilité synchrone. En leur absence, le repli déterministe local conserve un fonctionnement borné.

Les dix intentions du routeur sont model, sources, studio, planning, workspace, growth, knowledge, cad, silence et tower. Jev peut proposer une décision sur du texte et du contexte structurés ; les contrôles applicatifs restent obligatoires. Jev n’effectue ni la transcription, ni la synthèse vocale, ni une commande machine.

Le nœud receipt consigne le résultat du tour, par exemple une commande en attente ou refusée. Un reçu de rendu navigateur arrive ensuite de façon asynchrone : terminer le graphe ne prouve pas que chaque écran a affiché le résultat. La tour complète attend trois reçus.

La mémoire apporte du contexte sourcé. La CAO suit un circuit séparé et borné de proposition, confirmation et calcul. Les catalogues Studio, brouillons Growth et scripts de production existent, mais leur présence ne constitue pas une chaîne autonome Jarvis → génération vidéo → montage → publication.

## Capacités et limites
| Domaine | État dans le périmètre examiné | Preuve encore nécessaire |
|---|---|---|
| Mémoire et interface | Installation minimale et recherche/restauration observées | Recette sur le PC cible et contrôle des changements ultérieurs |
| Graphe LangGraph | Implémenté dans le code ; tests sélectionnés réussis | Démarrage avec moteur réel, interruption et reprise sans effets répétés |
| CAO | Circuit borné et dépendances prévues | Installation des moteurs, exports STL/STEP/GLB réels, contrôle géométrique |
| Voix | Capture ponctuelle, ASR local optionnel, TTS navigateur | Micro réel, modèle français, bruit, latence et interruptions |
| Jev | Adaptateur distant optionnel avec garde applicative | Appel réel, erreurs réseau, confirmations et coût maîtrisé |
| Planning et fabrication | Démonstration ; connecteurs incomplets | Découpe, tranchage, télémétrie et qualification FDM/résine |
| Studio/Growth | Catalogue et brouillons | Chaîne complète avec validation artistique et publication explicite |
| Conversation permanente | Non activée | Intégration et recette d’une couche temps réel |

## Changements postérieurs et prochaines vérifications
La publication se prépare sur 9f58fa2, quatre commits après 3c28821. Le démarrage, la mémoire, le pilotage des revues et des tests ont changé. Le fichier DELTA_A_REEXAMINER.json donne la comparaison exacte. Les preuves déjà présentes sous docs/evidence/startup-* proviennent d’une autre session ; elles sont utiles, mais ne doivent pas être confondues avec les sorties transcrites ici. Les nouveaux contrôles CI de cette publication sont consultables dans GitHub Actions et doivent être attribués à leur propre commit.

Priorités pour l’auditeur :
1. Rejouer installation, redémarrage et restauration sur la tête choisie et sur la tour cible ; vérifier les cinq bases opérationnelles séparément.
2. Installer les moteurs réels puis éprouver confirmations, annulation, crash/reprise, appels répétés et perte de reçu navigateur. Revoir aussi provenance, notes non fiables et isolation des états.
3. Qualifier une FDM et une résine avec opérateur, après inventaire matériel. Séparer les fonctions absentes des défauts de code.

## Choix d’outils proposés
Conserver LangGraph est cohérent avec le graphe déjà implémenté. Pour une conversation audio continue, Pipecat est une piste complémentaire, pas une intégration actuelle. Temporal devient pertinent si des tâches longues et distribuées doivent survivre à des redémarrages et à des reprises interservices ; son ajout n’est pas justifié par le seul besoin de dessiner le graphe.

Ce sont des propositions d’architecture, pas des fonctionnalités annoncées. Le SVG décrit l’état examiné et distingue les circuits présents des éléments à raccorder. Les documentations officielles consultées figurent dans SOURCES.json.

## Contrôle pendant la publication
La première version documentaire ae3b0fe a passé le contrôle du manifeste et les 46 tests mémoire/HTTP de sa CI, mais son évaluation documentaire a obtenu 9/10 : la source attendue pour « LangGraph » n’apparaissait plus dans les cinq premiers résultats. Le document de passation nouvellement enrichi apparaissait à sa place. La passation de publication a été condensée en renvoyant au dossier détaillé ; aucun seuil de test ni code de recherche n’a été modifié pour faire passer ce contrôle. Les faits et le lien du journal initial sont conservés dans preuves/CI_PUBLICATION.json ; consulter les exécutions ultérieures de la PR nº 6 pour vérifier le résultat final. Cet incident montre que le classement lexical dépend du corpus documentaire.
