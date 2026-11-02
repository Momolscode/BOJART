# M08 — Demande → figurine → visualisation → tranchage (2 novembre 2026)

## Niveau atteint

**N2 sur le personnage original de contrôle**, dans un conteneur Linux (4 vCPU, 15 Go de RAM, sans GPU) :
vrai maillage fermé, contrôles calculés, rendus, visionneuse pilotée dans Chromium et tranchage réel
par PrusaSlicer hors ligne. **Pas N3** : rien n'a été imprimé. **Pas la tour** : ni Windows, ni RTX 4060 Ti,
ni micro, ni les trois écrans n'étaient accessibles.

Le cas **Végéta** est compris (spécification complète) puis **BLOQUÉ avant toute géométrie** : Jarvis ne
sculpte ni ne rend un personnage protégé, et aucune licence n'est inventée. Le contrôle de bout en bout
utilise « La Sentinelle de l'atelier », personnage original BOJ.ART créé pour ce test.

Le résultat 3D est un **prototype procédural**, pas une figurine premium (voir la grille artistique).

## Inventaire court de l'existant (vérifié dans ce dépôt le 2026-11-02)

| Élément | État constaté |
|---|---|
| Point d'entrée texte `dialogue.interpret` | vérifié (tests M02) ; ne comprenait que le socle → étendu à `create_figurine` |
| Voix `voice.LocalVoice` (faster-whisper local) | code présent ; poids et micro absents → **NON TESTÉ** |
| CAO socle M01 (CadQuery) | présent ; CadQuery absent du conteneur → non réexécuté (échecs préexistants identiques avant/après) |
| LangGraph M06, Jev, régie trois vues M04/M07 | présents, non modifiés ; non nécessaires à ce parcours |
| Visionneuse 3D de l'Atelier (`sites/atelier/dist`) | **défaut** : `three.core.js` absent, l'import three.js échoue dans Chromium (`preuves/atelier_three_core_absent_2026-11-02.json`) |
| Connecteurs imprimantes, inventaire du parc | absents ; parc inconnu |

## Ce qui a été exécuté

Point d'entrée : `python jarvis/tools/figurine_pipeline.py "<demande>"`. Code : `jarvis/apps/jarvis/app/figurine/`.

| Étape | Exécution de preuve `d70b23ab2e4e3376` (commit `3cdeb3e`) | Durée | Pic mémoire |
|---|---|---|---|
| Réception + spécification | même point d'entrée que Jarvis, sans LLM | 0,02 s | 35 Mo |
| Transcription | **NON TESTÉE** : texte injecté, aucun score fabriqué | — | — |
| Étude de pose | 3 intentions à 2 mm de voxel, règle écrite d'avance | 3,2 s | 85 Mo |
| Géométrie | SDF + marching cubes (0,6 mm) + lissage Taubin | 42,9 s | 345 Mo |
| Assemblage | mise à l'échelle 200 mm, socle évidé, tenons Ø 4/5 mm | 0,6 s | — |
| Contrôles | volumes, normales, arêtes, flottants, épaisseurs, surplombs, stabilité, ajustement | 10,7 s | 620 Mo |
| Rendus | Blender 4.0.2 Cycles CPU : 4 vues argile + maillage + `.blend` | 39,3 s | 1 283 Mo (Blender) |
| Exports | STL par pièce, 3MF multi-objets relu | 1,7 s | — |
| Tranchage | PrusaSlicer 2.7.2, profil d'hypothèse, sans commande de chauffe | 32,1 s | 1 283 Mo (enfants) |
| Manifeste | empreintes SHA-256 de tous les fichiers | 0,4 s | — |

Durée totale : **2 min 12 s** à froid, un seul essai (pas de moyenne). Commande en doublon : **0,16 s**,
résultats existants renvoyés, aucune étape relancée. Visionneuse : chargement local 288 ms dans
Chromium 153 + SwiftShader (rendu logiciel).

## Résultats calculés (seuils FDM 0,4 mm fixés avant évaluation)

- Figurine : 181 810 triangles, volume fermé, normales cohérentes, 0 arête non-manifold, 1 seul corps,
  206,2 cm³, 125,8 × 99,0 × 188,0 mm. Hauteur totale avec socle : **200,0 mm** (cible 200).
- Épaisseurs (1 500 rayons) : min 3,99 mm, p1 6,67 mm ; aucun point sous 0,8 ou 1,2 mm.
- Surplombs > 45° : 10,8 % de la surface de la figurine ; socle 0,08 % (imprimé retourné).
- Socle : Ø 146,3 × 18 mm, évidement 9,2 mm, parois 3 mm, plancher 2 mm sous les logements.
- Stabilité statique (densité uniforme) : centre de masse à 4,0 mm du centre, marge 69,1 mm.
- Ajustement : interférence tenons/logements 0 mm³ avec un jeu d'hypothèse de 0,20 mm par côté ;
  tenons de diamètres différents = montage impossible à l'envers.
- **Non contrôlé** : auto-intersections explicites, résistance mécanique, jeu réel.

## Tranchage (estimations, pas des durées d'impression)

| Pièce | Temps estimé | Matière | Couches |
|---|---|---|---|
| Figurine debout, supports organiques | 12 h 16 min | 113,0 g (91,1 cm³) | 1 253 |
| Socle retourné | 8 h 10 min | 73,8 g | 120 |

Profil : buse 0,4, PLA, couches 0,15 mm, gyroïde 15 %, volume d'hypothèse 250 × 210 × 220 mm
(pas une machine du parc). Le G-code porte « NE PAS ENVOYER À UNE MACHINE », ne contient aucune
commande M104/M109/M140/M190 (vérifié par test) et reste hors Git. Aucune machine n'a reçu d'ordre.

## Grille artistique (auto-évaluation, pas une validation indépendante)

| Critère | Observation | Niveau |
|---|---|---|
| Identité du personnage | gardienne casquée au maillet, lisible mais générique | insuffisant pour vitrine |
| Cohérence multivue | un seul champ de distance : volumes cohérents par construction | correct |
| Anatomie | capsules et ellipsoïdes ; poings sphériques, pas de visage | schématique |
| Pose | garde basse lisible, peu de dynamique | moyen |
| Surfaces | terrasses de voxelisation visibles sur la vue maillage ; écart à la surface voulue p95 0,13 mm, p99 0,22 mm (approximation) | à corriger avant résine |
| Lisibilité après FDM | volumes ≥ 4 mm, peu de détails à perdre | correcte, mais peu de détails |

Conclusion : la chaîne est qualifiée numériquement ; la figurine ne l'est pas artistiquement.

## Matrice de défaillances

| Scénario | Résultat | Preuve |
|---|---|---|
| Demande Végéta nominale | spécification complète, géométrie BLOQUÉE, aucun maillage ni rendu | test + exécution `5aafd044cf97f6d3` |
| Maillage tiers sans fiche de provenance | BLOQUÉ, fichier non traité | test |
| Modification taille / pose (30 cm, combat) | spécification correcte | test N0 |
| Commande ambiguë | CLARIFY, aucune tâche créée | test |
| Transcription erronée (« végétal ») | CLARIFY avec suggestion ; **texte simulé, audio non testé** | test N0 |
| Ordre physique (« imprime ») | REFUSED, aucune tâche | test |
| Détails fragiles (plaque 0,4 mm), trou, élément flottant, mauvaise hauteur | éliminatoires détectés | tests N0 |
| Réparation destructrice | refusée (fidélité) ; réparation légère acceptée avec écart ≤ 0,3 mm | test N0 |
| Mémoire insuffisante | BLOQUÉ, pas de baisse silencieuse de qualité | test N1 |
| Blender absent | rendus BLOQUÉS, aucune image substituée | test N1 |
| Trancheur absent / en échec | BLOQUÉ / FAILED, aucun chiffre inventé | tests N1 |
| Interruption puis reprise | géométrie réutilisée (1 tentative), reprise jusqu'au blocage suivant | test N1 |
| Doublon de commande | même tâche, aucune étape relancée | test + exécution |
| Trois tentatives par étape | quatrième refusée | test N0 |
| Variante 1 m | 18 pièces étudiées pour le volume d'hypothèse, tranchage BLOQUÉ (clés et parc non définis) | test + exécution `f65591bfc2cc1f0a` |
| Réseau ou identifiant absent | non applicable : la chaîne n'appelle aucun service distant ; non testé réseau coupé | — |
| Pose difficile (maillet levé) | évaluée à basse résolution seulement | `pose_study.json` |

Tests : `python -m unittest tests.test_figurine_m08` → 19 réussis (~54 s). Suites existantes relancées
avant/après sur le même conteneur : mêmes échecs préexistants (dépendances absentes), aucune régression ;
`tools/validate_repository.py` valide.

## Boucles d'amélioration exécutées

Détail chiffré : `preuves/boucles_2026-11-02.json`.

1. **Performance** : pic mémoire des contrôles 4 253 → 620 Mo, durée 25,3 → 10,6 s, mêmes valeurs mesurées.
2. **Coût du socle** : 9 h 30 / 93,2 g → 8 h 10 / 73,8 g estimés, critères calculés conservés.
3. **Surface** : voxel 0,45 mm réduit l'écart à la surface voulue (p95 0,13 → 0,07 mm) mais double la durée
   de géométrie (47 → 108 s) : non adopté par défaut en FDM, recommandé pour la résine (`--voxel 0.45`).
   Plus de lissage (Taubin 12) dégrade la fidélité : rejeté.

## Synthèse par capacité

| Capacité | Niveau vérifié | Référence visée | Écart principal | Prochain test |
|---|---|---|---|---|
| Comprendre la commande | texte borné, N0/N1 | voix française robuste en atelier | aucune voix réelle ; grammaire étroite | enregistrement d'Olsen sur la tour |
| Créer la figurine | N2 procédural | sculpture de vitrine | anatomie, détails, surfaces | TripoSG local vs SDF, revue indépendante |
| Contrôler la géométrie | N2 calculé | analyse de fabrication professionnelle | auto-intersections, résistance | ajout du test d'intersections |
| Préparer l'assemblage | jeux d'hypothèse | jeux calibrés par machine | aucune pièce test | coupon tenons 0,10–0,30 mm |
| Visualiser | Chromium sans écran, 13/13 | vue création Jarvis sur l'écran réel | pas raccordé au tableau de bord | essai sur la tour |
| Trancher | PrusaSlicer 2.7.2 réel | profils vérifiés du parc | profil d'hypothèse, version à actualiser | profil de la première FDM inventoriée |

## Fichiers

- Preuves versionnées (JSON) : `preuves/execution-d70b23ab2e4e3376/`, `preuves/execution-5aafd044cf97f6d3-vegeta-bloque/`,
  `preuves/execution-f65591bfc2cc1f0a-1m-decoupe/`.
- Fichiers lourds hors Git (dossier du projet, `figurine-m08/`) : `figurine.stl`, `socle.stl`, `projet.3mf`,
  `rendus/` (vues + `figurine.blend`), `visionneuse/` (captures), `tranchage/apercu_couches_figurine.png`.
- Choix sourcés : `REGISTRE_DECISIONS_M08.md`. Suite : `BACKLOG_ET_REPRISE_M08.md`.
