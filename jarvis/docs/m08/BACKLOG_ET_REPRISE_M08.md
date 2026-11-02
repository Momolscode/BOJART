# M08 — Backlog priorisé et note de reprise (2 novembre 2026)

## Reprendre en 5 minutes

1. Lire `RELEASE_M08.md` (niveaux de preuve) puis `REGISTRE_DECISIONS_M08.md` (choix sourcés). Avant de
   sculpter : `GRILLE_CONCEPTION_FIGURINE.md` (proportions, taille minimale d'un détail, lisibilité).
2. Dépendances : `pip install -r jarvis/requirements-figurine.txt` (compatible avec `requirements.txt` dans
   le même environnement, trimesh 4.11.1 commun), PrusaSlicer et Blender (facultatif).
3. Parcours nominal (personnage original, ~5 min sur 4 vCPU sans GPU, grille de 0,4 mm) :
   `python jarvis/tools/figurine_pipeline.py "Jarvis, crée-moi Ardoise 3D imprimable dans une position stylée, iconique et remarquable."`
   (Ardoise, guerrier choisi par Olsen ; « la Sentinelle » reste le personnage de contrôle).
   Résultats dans `runs/figurine/<id>/` (hors Git) : `manifest.json`, `checks.json`, `rendus/`, `tranchage/`.
4. Visionneuse : `node jarvis/tools/figurine_viewer_check.cjs runs/figurine/<id>`.
5. Tests : `cd jarvis && python -m unittest tests.test_figurine_m08 -v` (30 tests, ~100 s).

Règles à garder : un personnage tiers reste BLOQUÉ sans maillage fourni et fiche de provenance ;
aucun G-code n'est envoyé ; une dépendance absente donne BLOQUÉ, jamais une réussite ; un doublon de
commande renvoie la tâche existante sans recalcul.

## Backlog (chaque tâche : résultat attendu → dépendance → test d'acceptation → preuve)

### P1 — bloque la qualification réelle du parcours

1. **Exécuter la chaîne sur la tour Windows.**
   Résultat : même parcours N2 sur la RTX 4060 Ti, temps et mémoire relevés.
   Dépendance : installation Python 3.12 + requirements-figurine + PrusaSlicer (version actuelle) + Blender.
   Test : `figurine_pipeline.py` DONE, `figurine_viewer_check.cjs` 13/13, tests M08 verts.
   Preuve : manifeste de la tour (environnement, versions, durées par étape, pic mémoire). La mesure
   mémoire Windows (`GetProcessMemoryInfo`) n'a jamais été exécutée : vérifier qu'elle donne un chiffre ;
   le pic de Blender et de PrusaSlicer n'y est pas mesuré.
2. **Qualité artistique : comparer une génération image→3D locale au prototype procédural.**
   Résultat : un maillage original plus riche (anatomie, plis, visage) passé par les mêmes contrôles.
   Dépendance : tâche 1 ; TripoSG (8 Go VRAM annoncés, code MIT, licence des poids à relire) ; dessin
   de concept original d'Ardoise (personnage choisi par Olsen, fiche D11) aux droits clairs, en gardant
   ses garde-fous de distinction.
   Test : grille artistique fixée d'avance + critères éliminatoires identiques ; revue par Olsen ou un
   sculpteur (évaluation indépendante), cas de contrôle tenus à l'écart des réglages.
   Preuve : vues argile avant/après, `checks.json` des deux maillages, fiche D1 mise à jour.
   Référence procédurale à battre : Ardoise v6 (fiche D13), jugée sur la vue rapprochée du buste.
3. **Inventorier le parc et calibrer l'ajustement réel.**
   Résultat : modèles d'imprimantes, volumes, profils matière ; jeu tenon/logement mesuré.
   Dépendance : accès aux machines avec opérateur (impression N3 autorisée explicitement).
   Test : coupon tenons Ø 4/5 mm avec jeux 0,10–0,30 mm ; jeu retenu = premier montage sans forcer.
   Le tenon de Ø 4 mm est sous les 5 mm conseillés pour le FDM (grille, section 3) : le coupon dira
   s'il faut l'épaissir.
   Preuve : photos du coupon, profil exporté, `ASSEMBLY_HYPOTHESES` remplacées par des valeurs mesurées.

### P2 — robustesse, voix, affichage

4. **Voix réelle de la commande de référence.** Enregistrer Olsen (WAV 16 kHz, micro de la tour),
   poids faster-whisper locaux, mesurer la transcription sur la commande et sur « Végéta / végétal ».
   Test : transcription relue, confusion détectée → CLARIFY. Preuve : journaux, sans conserver l'audio
   au dépôt.
5. **Raccorder la chaîne au tableau de bord Jarvis.** La proposition `create_figurine` existe au point
   d'entrée texte ; il manque la tâche de fond (progression, annulation, reprise) et la vue création
   sur l'écran droit avec la visionneuse. Test : parcours confirmé depuis l'interface, doublon refusé.
6. **Une seule copie de three.js.** L'Atelier (réparé sur `main` par `02be63c`, revérifié dans
   Chromium) et la visionneuse figurine portent chacun three 0.180.0 (complet et minifié). Choisir une
   copie commune lors de la prochaine publication du site. Test : les deux visionneuses chargent dans
   Chromium, `tools/validate_repository.py` valide.
7. **Socle : hauteur de couche 0,25–0,3 mm** (pièce sans détail) puis règle de rayon plus serrée.
   Test : même figure, même profil hors cette variable ; garder si gain sans perte des critères.

8. **Surfaces et intersections** : maillage adaptatif ou dual contouring pour supprimer les terrasses
   sans doubler la durée (référence mesurée : voxel 0,45 → p95 0,07 mm en 108 s) ; ajouter un contrôle
   explicite d'auto-intersections. Test : écart p95 ≤ 0,05 mm en ≤ 60 s sur le conteneur de référence.

### P3 — extensions

9. **Variante d'un mètre** : clés d'assemblage sur les plans de coupe, répartition sur le parc réel
   (après tâche 3). L'étude actuelle donne seulement le nombre de pièces pour le volume d'hypothèse.
10. **Personnage sous droits de tiers** (Végéta, fiches D14 et D15) : pièce de collection, pas de vente
   (précision d'Olsen du 2 novembre). Olsen a choisi un fichier de fan imprimé pour la maison, sous sa
   responsabilité (14:01 UTC) : en attente du fichier et de sa source. Le socle d'exposition pour une
   figurine officielle (`tools/socle_vitrine.py`) reste disponible. Gérer un kit en plusieurs pièces. Reste à
   faire : schéma de fiche de provenance (source, concédant, usage déclaré, territoire, durée) et contrôle
   automatique avant toute importation. La chaîne ne produit déjà aucune image d'un personnage tiers
   (rendus, aperçu des couches, captures de la visionneuse).
11. **CI** : workflow GitHub qui installe PrusaSlicer et exécute les tests M08 (Blender facultatif).
12. **Stries du socle en strates au-delà de 22 cm** : pour une figurine plus haute, les stries de clivage
   du socle retourné se creusent avec l'échelle mais gardent 1 mm de haut, donc des flancs de plus de 45°.
   Corriger dans une version 2 du style (identifiant de tâche nouveau) ; la variante à l'endroit du socle
   d'exposition est déjà corrigée.

## Ce qu'il ne faut pas refaire

- Chercher pourquoi la 3D de l'Atelier ne chargeait pas : `three.core.js` manquait sur l'ancienne base,
  déjà réparé sur `main` (`02be63c`). Les 404 restants (logo, polices, visuel, API) sont attendus en
  service statique du dépôt.
- Installer trimesh 5.x à côté de la CAO M01 : versions alignées sur 4.11.1 (fiche D10).
- Sculpter des doigts en anneaux autour d'un manche, des bords roulés en capsules, ou une paire de
  petits reliefs sur une plaque frontale : lus comme des bagues, des « bouées » ou un visage (grille,
  section 5).
- Comparer Hunyuan3D 2.1 : licence non applicable dans l'UE (vérifié le 2026-11-02).
- Tester TRELLIS.2 sur la tour actuelle : 24 Go de VRAM exigés par la fiche officielle.
