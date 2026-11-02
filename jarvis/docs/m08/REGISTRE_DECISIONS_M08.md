# M08 — Registre des choix (2 novembre 2026)

Chaque fiche : besoin, options, sources datées, décision, test, résultat, limites, condition de réexamen.
« Vérifié le 2026-11-02 » = page officielle consultée pendant la session. Une fiche n'est pas une
qualification sur la tour.

## D1. Origine du maillage : sculpture procédurale locale (SDF) pour le cas de contrôle

- **Besoin** : un vrai maillage fermé, reproductible, sans dépense ni GPU, pour qualifier la chaîne.
- **Options examinées** (sources officielles vérifiées le 2026-11-02) :

| Option | Licence | Mémoire GPU annoncée | Verdict pour BOJ.ART (France, RTX 4060 Ti 8 Go rapportée) |
|---|---|---|---|
| Sculpture SDF procédurale (ce dépôt) | code BOJ.ART | aucune | **retenue** pour le contrôle : déterministe, mais niveau artistique de prototype |
| TRELLIS.2-4B (Microsoft) — [fiche](https://huggingface.co/microsoft/TRELLIS.2-4B), [dépôt](https://github.com/microsoft/TRELLIS.2) | MIT | « at least 24GB » | éliminée sur la tour actuelle (contrainte matérielle) ; à revoir si GPU ≥ 24 Go |
| TripoSG 1.5B (VAST) — [dépôt](https://github.com/VAST-AI-Research/TripoSG), [fiche](https://huggingface.co/VAST-AI/TripoSG) | code MIT ; licence des poids à relire sur la fiche | « at least 8GB VRAM » | **candidate prioritaire** à évaluer sur la tour : géométrie seule, marge mémoire faible sur 8 Go |
| Hunyuan3D 2.1 (Tencent) — [licence](https://huggingface.co/tencent/Hunyuan3D-2.1/blob/main/LICENSE) | Community License du 13 juin 2025 : « DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA » | — | **éliminée** : pas de licence pour un usage en France |

- **Test** : parcours complet sur le personnage original, contrôles calculés (voir `RELEASE_M08.md`).
- **Limite** : volumes primitifs lissés ; ni anatomie fine, ni plis, ni visage expressif. Une génération
  image→3D ou une sculpture humaine reste nécessaire pour viser une figurine de vitrine.
- **Réexamen** : après un essai TripoSG sur la tour (même critères, même socle, même trancheur), ou
  changement de GPU.

## D2. Droits : aucun personnage tiers sculpté ou rendu par Jarvis

- **Décision** : une demande de personnage tiers (ex. Végéta) est comprise et spécifiée, puis l'étape
  géométrie est BLOQUÉE. Le traitement n'est possible qu'avec un maillage fourni **et** une fiche de
  provenance/licence (`--mesh`, `--provenance`). Le contrôle de bout en bout utilise un personnage
  original, « La Sentinelle de l'atelier ».
- **Raison** : la mission demande de ne pas inventer de licence ; un test technique n'autorise pas la
  reproduction de la ressemblance d'un personnage protégé. Ce blocage est une règle, pas une panne.
- **Test** : `test_third_party_character_is_blocked_without_geometry`,
  `test_third_party_mesh_without_provenance_is_blocked`.
- **Réexamen** : si BOJ.ART obtient une licence ou un fichier officiel sous licence documentée.

## D3. Booléens et assemblage : manifold3d

- **Options** : booléens Blender, booléens trimesh (moteurs externes), manifold3d 3.5.4.
- **Décision** : manifold3d, qui garantit des solides manifold en sortie ; aucune dépendance GUI.
- **Test** : tenons/logements sans interférence (`check_fit`), volumes fermés après soustraction.
- **Réexamen** : si un défaut de booléen est observé sur un maillage importé dense.

## D4. Trancheur : PrusaSlicer en ligne de commande, profil d'hypothèse

- **Version testée** : PrusaSlicer 2.7.2 (paquet Ubuntu 24.04). Fraîcheur par rapport à la version amont :
  NON VÉRIFIÉE (téléchargements GitHub refusés par le proxy de la session).
- **Profil** : buse 0,4, PLA, couches 0,15 mm, 3 périmètres, gyroïde 15 %, supports organiques,
  volume d'hypothèse 250 × 210 × 220 mm. Ce n'est **pas** une machine du parc.
- **Sécurité** : en-tête « NE PAS ENVOYER À UNE MACHINE », `autoemit_temperature_commands = 0`
  (aucune commande M104/M109/M140/M190 vérifiée par test), fichier jamais transmis.
- **Constat** : `--export-3mf` de la CLI 2.7.2 n'écrit qu'un objet ; le projet 3MF multi-pièces est
  écrit par trimesh (géométrie seule, sans réglages trancheur) et relu pour vérifier les deux objets.
- **Alternatives non testées** : OrcaSlicer, Cura ; à comparer sur le même STL si le parc l'exige.
- **Réexamen** : dès que le parc et les profils réels sont inventoriés.

## D5. Rendus : Blender 4.0.2, Cycles CPU, vues argile

- Vues face/profil/dos/trois-quarts sans texture + vue maillage détaillée, fichier `.blend` natif.
- Lissage limité aux angles < 35° pour ne pas créer de faux reliefs sur les faces planes.
- Limite : rendu logiciel sans GPU, éclairage studio simple ; une appréciation, pas une mesure.

## D6. Visionneuse : three.js 0.180.0 réutilisé, copie complète

- **Constat (corrigé le 2026-11-02)** : sur la base `b49101e` de cette branche, `sites/atelier/dist/vendor`
  n'avait pas `three.core.js` ; dans Chromium, la requête répondait 404 et l'import three.js échouait
  (`preuves/atelier_three_core_absent_2026-11-02.json`, 03:08 UTC). Ce défaut était **déjà corrigé sur
  `main`** par `02be63c` (PR #12, fusionnée à 02:55 UTC avec `THREE-PROVENANCE.json` et une exception
  de taille épinglée dans `tools/validate_repository.py`). Après fusion de `main` (`e1a08fe`), revérifié
  dans Chromium : import réussi (r180), `three.core.js` servi
  (`preuves/atelier_three_core_verifie_2026-11-02.json`). Restent des 404 sans lien avec three.js :
  binaires exclus du dépôt (logo, polices, visuel) et API absente en service statique.
- **Décision** : garder pour la visionneuse figurine sa propre copie épinglée
  (`figurine/viewer/vendor/VENDOR.json`, empreintes SHA-256, licence MIT), en version minifiée : elle ne
  dépend pas d'un dossier de publication du site et reste sous la limite de 1 Mo sans nouvelle exception.
  Coût : deux copies de three 0.180.0 dans le dépôt (voir le backlog).
- **Test** : `tools/figurine_viewer_check.cjs` (Chromium + SwiftShader) : chargement des deux pièces,
  rotation, zoom, quatre vues, pièces séparées, vue éclatée, maillage, absence d'erreur console.

## D7. Choix de pose : règle écrite avant comparaison

- Trois intentions légères évaluées à 2 mm de voxel (sans génération coûteuse) : centre de masse dans
  l'appui des pieds (éliminatoire), puis remplissage de silhouette de face le plus proche de 0,42.
- Choix obtenu : « Garde basse ». Jugement artistique non validé par un tiers ; « Maillet levé » a une
  silhouette plus ouverte (0,34) mais une hauteur de geste qui réduit la taille du personnage à 200 mm.
- **Réexamen** : revue humaine des trois poses (Olsen ou sculpteur), puis ajustement de la règle.

## D8. Socle évidé imprimé retourné (boucle coût)

- Variable modifiée : évidement par dessous (parois 3 mm, plancher 2 mm sous les logements), socle
  tranché retourné pour éviter ponts et supports. Mesure avant/après sur le même trancheur et profil.
- Résultat et seuil : voir `preuves/boucles_2026-11-02.json`. Conservé : gain mesuré sans perte des
  critères calculés (stabilité, ajustement, épaisseurs ≥ 0,8 mm).

## D9. Épaisseurs par lancers de rayons groupés (boucle performance)

- Sans Embree, 1 500 rayons lancés d'un coup sur 180 k triangles montaient à ~4 Go de mémoire.
- Variable modifiée : paquets de 100 rayons. Mêmes valeurs mesurées (min/p1 identiques), mémoire et
  durée réduites. Conservé. Détail : `preuves/boucles_2026-11-02.json`.

## D10. Dépendances : une seule version de trimesh pour Jarvis (corrigé le 2026-11-02)

- **Constat** : `requirements-figurine.txt` épinglait trimesh 5.2.0 alors que la CAO M01
  (`apps/jarvis/requirements.txt`) épingle 4.11.1. Installer les deux fichiers ensemble échouait
  (`ResolutionImpossible`, reproduit avec `pip install --dry-run` pour win_amd64 / CPython 3.12),
  signalé par le banc d'essai d'un autre fil. Second écart trouvé en environnement isolé : l'export 3MF de
  trimesh exige lxml (extra « easy » de trimesh), fourni jusque-là par le conteneur et absent du fichier.
- **Options** : monter la CAO en 5.2.0 (il faudrait requalifier M01, CadQuery absent de ce conteneur) ;
  séparer deux environnements (deux installations sur la tour) ; **aligner la figurine sur 4.11.1**.
- **Décision** : aligner sur 4.11.1 et épingler lxml 6.1.3. La CAO M01 ne change pas de version.
- **Tests** : résolution combinée des six fichiers de dépendances Jarvis pour win_amd64 / CPython 3.12,
  roues binaires seules (108 paquets, sans installation sous Windows) ; 21 tests M08 dans un
  environnement Python 3.12 isolé créé depuis les fichiers ; parcours complet relancé avec ces versions
  (`preuves/environnement_aligne_2026-11-02.json`) ; `test_shared_pins_do_not_conflict` empêche le retour
  d'une double version.
- **Constat lié** : `pipeline.py` importait `resource` (POSIX seulement) et aurait échoué dès l'import sous
  Windows. Import rendu facultatif ; mesure mémoire Windows par `GetProcessMemoryInfo` **non testée**
  (pas de machine Windows ici), pic des processus enfants non mesuré sous Windows.
- **Réexamen** : montée de version commune de trimesh avec requalification CAO M01 et M08 sur la tour.
