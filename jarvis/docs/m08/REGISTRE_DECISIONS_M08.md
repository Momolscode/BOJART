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

## D11. Deuxième personnage original : « Ardoise, le duelliste des strates » (2 novembre 2026)

- **Contexte** : Olsen a noté que la figurine « ne ressemble pas du tout à Végéta ». C'est voulu (D2).
  Sur la carte de décision du 2 novembre (09:10 UTC), Olsen a choisi « un guerrier original BOJ.ART »,
  vendable, plutôt qu'un fichier sous licence ou le seul personnage de contrôle.
- **Design** : crâne rasé et tresse passée sur l'épaule droite ; long manteau ouvert devant et fendu dans le
  dos ; une seule épaulière en plaques empilées ; cuirasse en strates (les couches de l'impression FDM
  deviennent un motif voulu, en écho au travail STRATES de BOJ.ART) ; grande lame à deux mains en gradins.
- **Garde-fous de distinction, écrits avant de sculpter** : aucune chevelure dressée, aucune armure à
  épaulettes symétriques ni combinaison, ni gants ni bottes blancs, aucune pose de tir d'énergie ni pose
  signature empruntée. Un nom et une identité propres à BOJ.ART.
- **Itérations sur rendus argile basse résolution (auto-évaluation)** : v1 trop maigre, manteau en
  planches ; v2 carrure renforcée et manteau en coque conique ; v3 pose « Élan » cassée (10 corps)
  remplacée par « Garde », bras renforcés ; v4 cuirasse à marches nettes, car les bandes se lisaient comme
  des côtes.
- **Pose** : trois intentions (Serment, Défi, Garde), même règle écrite que pour la Sentinelle. Une demande
  « au repos » donne Serment, « combat » donne Garde.
- **Limite** : prototype procédural, pas une sculpture de vitrine. La qualité vitrine passe par une
  génération image → 3D à partir d'un dessin original d'Ardoise (D1), puis par les mêmes contrôles.

## D12. Tenons sous les deux plus grands appuis (fabrication v3)

- **Constat** : en pose Serment, la pointe de la lame touche le sol. L'ancienne règle séparait les appuis
  par le signe de x : la pointe tirait les deux tenons vers l'avant (essai sur pièces simples : décalage de
  1,6 mm en y et de 0,9 mm vers l'intérieur).
- **Décision** : regrouper les appuis par voisinage (distance de liaison qui suit la résolution du
  maillage) et poser les tenons sous les deux plus grands ; tous les appuis dimensionnent le socle.
- **Tests** : `test_pegs_go_under_the_feet_not_under_a_third_contact`,
  `test_original_warrior_rest_pose_until_renders`.
- **Non-régression** : la Sentinelle relancée avec la fabrication v3 (nouvel identifiant de tâche
  `702d5b9d10f7a9c1`, puisque la version de fabrication entre dans l'identité) redonne la preuve
  `execution-d70b23ab2e4e3376` : `spec.json`, `pose_study.json`, `assembly.json`, `checks.json`,
  `tranchage.json` et profil identiques octet pour octet, ainsi que les trois STL (comparés aux fichiers
  de l'exécution d'origine, conservés hors Git) ; G-code identique hors la ligne
  d'horodatage de PrusaSlicer ; rendus identiques au pixel ; 3MF identique hors les UUID aléatoires que
  trimesh écrit à chaque export. Ardoise relancé dans l'environnement épinglé (Python 3.12, trimesh
  4.11.1) : même tâche, mêmes sorties (`preuves/contre_epreuves_fabrication_v3_2026-11-02.json`).
- **Lié** : les résidus du marching cubes (volume < 1 mm³, plus petits que deux voxels) sont retirés et
  comptés dans le résultat de l'étape géométrie ; un vrai élément flottant reste éliminatoire.

## D13. Passe « détails » sur Ardoise et grille de conception (2 novembre 2026, 11:20 UTC)

- **Contexte** : Olsen a redemandé Végéta « avec plus de détails ». Refus maintenu (D2) : un personnage
  protégé n'est ni sculpté ni rendu, et plus il serait ressemblant, plus la contrefaçon serait nette à la
  vente. La critique du niveau de détail est juste et retenue. Une carte propose : Ardoise détaillé
  (recommandé, travail lancé en attendant), un combattant original style manga, ou Végéta seulement
  depuis un fichier fourni avec une licence écrite qui autorise la vente.
- **Options pour le détail** : sculpture numérique à la main (hors de portée d'un agent sans
  interface) ; génération image → 3D sur la tour (D1, tour non disponible) ; génération dans un service
  en ligne (crédits payants et envoi de données : autorisation d'Olsen nécessaire, non demandée ici) ;
  **enrichir la sculpture procédurale selon une grille sourcée**.
- **Décision** : grille `GRILLE_CONCEPTION_FIGURINE.md` (proportions de Loomis, détail imprimable
  Formlabs et Protolabs, types de plis) ; module réutilisable `figurine/details.py` (poing de sculpteur,
  rivets, gravure, plaque, poignée gainée, plis tuyaux, évaluation locale par boîte) ; Ardoise v6 à
  7,4 têtes, visage construit, poings, musculature du bras nu, plis du manteau et du pantalon,
  genouillères en strates, rivets et gravures ; grille de 0,4 mm et 3 itérations de lissage pour ce
  personnage (registre `voxel` / `smooth_iterations`), la Sentinelle garde 0,6 mm et 6 itérations.
  Socle « en strates » pour Ardoise (`fabrication._strata_base`, style `strates` du registre) : cinq
  plaques d'ardoise aux bords cassés, plus larges vers le bas, imprimables retournées sans support
  (chanfreins plus raides que 45°), dessus plat gardé comme plan de joint. Le socle lisse ne change
  pas : sa version reste `bojart.fabrication.v3` dans l'identité, le style « strates » y ajoute la
  sienne (`bojart.socle.strates.v1`).
- **Écartés en cours de route (rendus)** : doigts en anneaux (lus comme des bagues), genouillères à
  arête centrale ou à rivets côte à côte (lues comme des visages), orbites profondes (regard vide),
  bords de brassards en capsules (une capsule s'étend d'un rayon de chaque côté : « bouées » sur les
  avant-bras ; remplacées par des anneaux `details.ring`).
- **Réexamen** : comparaison avec une génération image → 3D d'un dessin original d'Ardoise sur la tour
  (backlog, tâche 2) et revue par Olsen ou un sculpteur.

## D14. Végéta depuis un fichier sous licence (choix d'Olsen, 2 novembre 2026, 12:26 UTC)

- **Contexte** : sur la carte de la fiche D13, Olsen a choisi « Végéta depuis un fichier sous licence » :
  il fournit un modèle 3D et une licence écrite qui autorise la vente ; Jarvis contrôle le fichier,
  ajoute le socle et le tranche, sans sculpter le personnage.
- **Condition** : la licence doit venir des ayants droit de Dragon Ball (Bird Studio/Shueisha, Toei
  Animation) ou d'un licencié officiel, et couvrir la fabrication et la vente de figurines (objet,
  territoire, durée). Une licence « commerciale » vendue avec un STL de fan ne suffit pas : le
  sculpteur ne peut pas céder des droits sur un personnage qui n'est pas à lui. Jarvis vérifie le
  contenu du document et le garde comme fiche de provenance (`--provenance`) ; il ne peut pas en
  attester la validité juridique.
- **Décision** : pour un personnage sous droits de tiers, la chaîne ne produit aucune image de sa
  ressemblance, même depuis un fichier sous licence : rendus marqués SKIPPED, pas d'aperçu des couches
  (`FigurineRun._no_images`), contrôle de la visionneuse refusé sans capture (code 3). Contrôles,
  réparation surveillée, socle lisse à tenons, export 3MF et tranchage restent faits. Test :
  `test_licensed_third_party_mesh_is_processed_without_any_image`.
- **Précision d'Olsen (13:32 UTC)** : toutes les figurines ne sont pas faites pour la vente ; celle-ci irait
  dans la collection de BOJ.ART, pour les enfants. La condition de licence de vente reste valable pour
  toute pièce vendue, mais ne concerne pas cette pièce-là.
- **Cadre de l'usage privé** (indication sourcée, pas un avis d'avocat) : l'exception de copie privée
  (Code de la propriété intellectuelle, art. L122-5, 2°) exige une source licite et un usage strictement
  privé du copiste, et exclut « les copies des oeuvres d'art destinées à être utilisées pour des fins
  identiques à celles pour lesquelles l'oeuvre originale a été créée »
  ([texte reproduit](https://www.baumann-avocats.com/CPI/article-l122-5-du-code-de-la-propriete-intellectuelle.php)).
  Au Sénat, le 17 avril 2015, le co-rapporteur François Pillet a déclaré que « par nature, les œuvres d'art
  matérielles sont exclues de l'autorisation légale de copie privée »
  ([compte rendu de presse](https://www.journaldugeek.com/2015/04/27/pas-de-redevance-copie-privee-imprimante-3d/)) ;
  voir aussi le [rapport du CSPLA sur l'impression 3D](https://www.culture.gouv.fr/Espace-documentation/Rapports/Commission-du-CSPLA-sur-l-impression-3D)
  (5 juillet 2016). Aucune décision de justice trouvée sur une figurine imprimée. La copie privée ne couvre
  donc sans doute pas une figurine imprimée. La première réponse donnée à Olsen disait le contraire ;
  elle a été corrigée dans le fil le jour même.
- **Fichiers disponibles** (recherche du 2 novembre 2026) : aucun fichier Végéta autorisé par les ayants
  droit. Les fichiers en vente (CGTrader, Gumroad…) sont des créations de fans ; leurs licences « usage
  personnel » ou « libre de droits » viennent des sculpteurs et ne valent pas autorisation des ayants droit.
- **Voies proposées à Olsen** (carte du 2 novembre, 13:42 UTC) :
  1. recommandée : une figurine officielle (Banpresto, Bandai) posée sur un socle BOJ.ART original, dessiné
     par Jarvis à la mesure de son socle d'origine (fiche D15) ; rien du personnage n'est modélisé ;
  2. un fichier de fan imprimé pour la maison, décision et responsabilité d'Olsen (reproduction non
     autorisée au sens strict) : fiche de provenance avec la source réelle et « usage : collection
     privée » ; ni vente, ni don hors du foyer, ni concours, ni photo publiée sur les réseaux ou la
     boutique de BOJ.ART ; mêmes garde-fous qu'au-dessus (aucune sculpture ni image du personnage).
- **Choix d'Olsen (14:01 UTC)** : voie 2, un fichier de fan imprimé pour la maison. Les sorties restent hors
  de Git, dans un dossier à part du projet marqué « collection privée » (fiche de provenance et note).
- **État** : en attente du fichier et de sa source (boutique, sculpteur). La chaîne attend un seul
  maillage : un kit en plusieurs pièces devra être assemblé ou traité pièce par pièce.

## D15. Socle d'exposition pour une figurine du commerce (2 novembre 2026)

- **Contexte** : voie recommandée de la fiche D14 ; sert aussi à toute figurine officielle de la collection.
- **Décision** : `fabrication.display_socle` et `tools/socle_vitrine.py` dessinent un socle en plaques
  d'ardoise (même dessin que le socle d'Ardoise) avec une empreinte ronde ou ovale où se pose le socle
  d'origine de la figurine (jeu de 0,4 mm par côté, 3 mm de profondeur), ou un dessus plat pour un socle
  d'origine irrégulier (« libre »). Aucune géométrie ni image du personnage : les rendus montrent le socle
  seul.
- **Sens d'impression** : à l'endroit, dessous plein. Retourné comme le socle d'Ardoise, le fond de
  l'empreinte formerait un pont de plusieurs centimètres. Les plaques restent donc en retrait d'au moins
  0,3 mm sur celle du dessous (`_strata_base(upright=True)`), sans dévers : surplomb mesuré 0 %. Le
  chemin par défaut du socle en strates est inchangé (sommets identiques, identifiant d'Ardoise gardé).
- **Essai sur cotes d'hypothèse** (socle d'origine rond de 80 mm, en attendant les cotes réelles) :
  106 × 105 × 16 mm, bord minimal de 6,6 mm autour de l'empreinte, maillage fermé, 4 h 31 et 43 g de PLA
  estimés par PrusaSlicer 2.7.2 sous profil d'hypothèse (`preuves/socle-vitrine-hypothese-ronde-80/`).
- **Tests** : `test_display_socle_holds_an_original_base_and_prints_upright`,
  `test_display_socle_tool_reports_without_any_character`.
- **Réexamen** : cotes réelles relevées au pied à coulisse, puis une bague d'essai imprimée pour
  calibrer le jeu (N3).

## D16. Troisième personnage original : « Veille, la gardienne du trait » (3 novembre 2026)

- **Contexte** : le 2 novembre à 23:46 UTC, Olsen a demandé une figurine « en te basant sur les œuvres
  existantes de Boj.art ». Lecture retenue : Veille, l'héroïne du film BOJ.ART « Un seul trait »
  (contenu premium V.02), personnage original de la maison. Les pièces de la collection faites d'après
  des personnages protégés restent exclues (D2, D14).
- **Design, d'après les images de référence du film** : figure androgyne agenouillée, genou gauche au
  sol, pied droit nu posé devant ; yeux clos ; côtés du crâne rasés, dessus plaqué en arrière ; robe
  tombée de l'épaule droite à bord roulé, haut col à gauche, bord croisé devant, jupe étalée au sol, pan
  tombé du genou avant ; avant-bras bandés jusque sur le dos des mains ; grand bâton-pinceau tenu droit
  à deux mains (virole, touffe à quatorze mèches) ; socle de basalte.
- **Garde-fous** : aucun personnage existant ni sosie ; ni arme, ni armure, ni pose de combat (une
  demande « combat » ou « repos » garde la pose de veille). Le trait carmin sur l'œil, signe du film,
  est de la peinture : il n'est pas sculpté.
- **Construction** : `figurine/veille.py`, même méthode que les autres personnages (champ de distance,
  grille de 0,4 mm, 3 itérations de lissage). Les poses sont écrites dans un repère miroir en x : de
  face, le bâton est à droite de l'image, comme sur les références. Un décalage de quelques micromètres
  (`JITTER`) évite des zéros exacts du champ sur les nœuds de la grille, qui avaient produit une arête
  non manifold au pas de 0,5 mm ; il ne touche que Veille. La robe est un volume plein, sauf le pan du
  genou, en étoffe de 3,5 mm à la hauteur de 200 mm.
- **Écartés en cours de route (rendus et contrôles)** : encolure en écharpe ; manche en boule au coude ;
  cheveux en crête ; pan du genou en abat-jour avec rebord (l'union douce de deux surfaces confondues
  gonfle un bourrelet : union franche à cet endroit) ; visage en masque, avec une arête de l'œil à la
  mâchoire (le devant du visage tombait à pic : masse zygomatique, joues et pommettes orientées vers
  l'arrière). Le premier passage complet a été refusé par le contrôle d'épaisseur (0,3 % de la surface
  sous 0,8 mm). Une analyse sur 12 000 points a trouvé la pointe du pan du genou là où un pli croisait
  la coupe, une lame au bout du bord roulé sur l'épaule couverte et un biseau de la jupe au ras du
  sol ; une deuxième, la même lame (décaler une intersection ne l'arrondit pas) et des éclats au bord
  des sillons de peigne, là où la mèche s'amincit vers la nuque. Corrigé par des plis effacés près des
  bords coupés, un bord roulé qui s'amincit en pente bornée, des sillons jamais plus profonds que la
  mèche et un ourlet d'aplomb sur les 1,5 derniers millimètres.
- **Socle « basalte »** (`fabrication._basalt_base`, `bojart.socle.basalte.v1`) : prisme hexagonal
  irrégulier, un sommet vers l'avant. Chaque côté passe à 10 mm au moins des appuis (plus 0 à 3 mm
  tirés avec une graine fixe). Biseau du dessus en facettes de pente 1,2 à 1,5, joint de colonne en V
  à flancs de 42°, chanfrein du dessous, évidement polygonal à paroi de 3 mm : imprimable retourné
  sans support. `base_radius_mm` y est le rayon du disque inscrit autour du centre des appuis, une borne
  prudente pour la stabilité. Les socles lisse et en strates donnent les mêmes octets qu'avant
  (maillages et informations comparés au commit précédent).
- **Tenons** : Ø 4 sous le pied nu, Ø 5 sous la robe posée ; la pointe du bâton est un troisième appui,
  sans tenon (D12).
- **Demande** : « veille » est aussi un mot courant. Le nom ne compte que dans une demande qui parle
  d'une figurine (figurine, statuette, personnage, buste, 3D, sculpture), jamais dans « en veille »,
  « mode veille » ou « la veille de/du/des/d' », sauf devant un nombre (« la Veille de 20 cm »).
  « Jarvis, mets-toi en veille » ne lance donc aucune figurine.
- **Exécution** (N2, conteneur Linux, Python 3.12.3, trimesh 4.11.1) : tâche `ed77ed8e1f71b0f4`,
  518 570 triangles, un seul corps fermé, CONFORME_AUX_CRITERES_CALCULES, épaisseur min / p1
  1,92 / 3,71 mm, aucun point sous 1,2 mm sur 12 000 à la contre-vérification, tranchage estimé à
  12 h 22 et 103,7 g (figurine) et 5 h 53 et 53,0 g (socle), visionneuse 13/13
  (`preuves/execution-ed77ed8e1f71b0f4-veille/`).
- **Tests** : `test_veille_and_everyday_uses_of_the_word`, `test_standby_phrases_never_start_a_figurine`,
  `test_basalt_base_hugs_the_contacts_and_prints_upside_down`,
  `test_heroine_kneels_on_foot_and_robe_until_renders`, et `test_character_defaults_keep_published_identities`
  étendu à Veille.
- **Réexamen** : avis d'Olsen sur les rendus ; essai image→3D à partir des images du film sur la tour
  (backlog, tâche 2) ; impression d'essai (N3).

## D17. Quatrième personnage original : « Fusain, le lutteur au trait de charbon » (3 novembre 2026)

- **Contexte** : le 3 novembre à 10:18 UTC, Olsen a demandé une figurine d'après « les figurines qu'il a
  faites » sur le compte TikTok @boj.art. Les huit vidéos lisibles (listes de lecture) montrent toutes
  des personnages protégés : Baki Hanma de 60 cm, Aphrodite de Record of Ragnarok, Goku contre Freezer,
  Mileena, Elfen Lied. Ni copie ni sosie (D2, D14). Carte posée (un original dans son style, ses
  fichiers pour la maison sans image, un socle pour ses pièces) ; Olsen a choisi à 10:40 UTC « un
  original dans son style ».
- **Ce qui est repris de BOJ (savoir-faire, jamais le personnage)** : la grande pièce de vitrine, le
  socle qui raconte l'action (chez lui, des rochers d'où monte un tourbillon de fumée), des volumes
  faits pour la peinture à la main.
- **Design** : lutteur en fente avant, jambe gauche fléchie devant ; paume droite ouverte tendue devant,
  doigts vers le haut ; poing gauche ramené à la hanche ; veste sans manches ouverte en V, col en bande
  autour de l'encolure, ceinture large nouée ; pantalon ample serré aux mollets par des bandes ; pieds
  nus ; avant-bras bandés ; cheveux tirés en arrière en chignon bas torsadé, barbe courte en collier. Le
  trait de pinceau, ruban de charbon en croissant, sort de colonnes de basalte et monte jusqu'au talon de
  sa main (troisième appui du bras tendu) ; deux volutes de fumée enroulées montent des blocs. Même
  univers que Veille (bandages, basalte, carmin).
- **Garde-fous de distinction** : ni torse nu en short, ni garde de boxe poings levés, ni cheveux en
  pointes ou ébouriffés, ni yeux rougeoyants, ni tatouage, ni chapelet, ni aura de fumée en anneaux
  copiée d'un socle existant, ni pose signature d'un personnage protégé. Le trait de charbon en travers
  des yeux est de la peinture.
- **Construction** : `figurine/fusain.py`, même méthode (champ de distance, grille de 0,4 mm,
  3 itérations de lissage, tête agrandie de 12 %, socle « basalte » de D16). Nouveau : un ruban continu
  balayé le long d'un chemin (point le plus proche du chemin, repère interpolé, section rectangulaire
  arrondie), qui sert au trait et aux volutes ; prismes hexagonaux pour les colonnes de basalte.
- **Écartés en cours de route (rendus et contrôles)** : trait en chapelet de boîtes (festons à chaque
  raccord), en ruban vu par la tranche (un fouet), puis strié régulièrement (tôle ondulée) ; fumée en
  boules (un tentacule) puis en crochet (une crosse de fougère) ; col en V seul (un emblème) ; ceinture
  en ellipsoïde (un dôme sous le V) ; barbe en couche coupée net (tablettes plates sur les joues), puis
  d'épaisseur réglée sur |x| (la couche grandissait en s'éloignant du visage et se décollait en lame) :
  barbe en collier le long de la mâchoire, épaisseur nulle sur ses bords ; cheveux en ellipsoïde seul
  (plaques en œillères dans le creux des tempes) : couche bornée à 1,6 mm du visage. Un bord
  d'emmanchure qui butait contre le deltoïde du bras tendu fermait une poche creuse, vue comme un
  élément flottant au pas de 1 mm.
- **Contrôle d'épaisseur refusé, puis corrigé** : la première version complète à 0,4 mm a été refusée
  par la chaîne (0,27 % de la surface sous 0,8 mm, minimum 0,05 mm ; rien livré). La
  contre-vérification sur 12 000 points, des coupes puis un contrôle local par régions ont trouvé six
  causes : col d'encolure presque parallèle à la couche autour de la bosse des trapèzes (lame derrière
  la nuque), ourlet d'emmanchure en capuchon au-dessus du deltoïde (bords « effilochés » au sommet des
  épaules sur les rendus), ourlet en croissant le long du bras gauche couché dans le dos, stries du
  trait qui se chevauchaient et perçaient le ruban près de la main, plis du pantalon en étoile sous le
  genou gauche, et fentes de 0,2 à 0,3 mm entre les doigts. Corrections : coupes du vêtement lues au
  pied de la normale sur le tronc sans le cou (chaque bord traverse l'étoffe d'équerre), emmanchure à
  4 mm du bras mesurés sur le tronc, stries gravées en une passe et bornées à 30 % de la
  demi-épaisseur (une sur deux s'efface quand le trait s'affine), plis effacés près de l'axe de la
  cuisse, doigts serrés. Contrôle local par régions à 0,4 mm ensuite (buste, taille, tête, main,
  trait, jambes, cuisses) : aucun point sous 1,2 mm (minimum 1,56 mm).
- **Correction de la chaîne (toutes les figurines)** : la relance suivante a été refusée autrement
  (« volume non fermé », 186 arêtes non-manifold, 186 éléments flottants). Le maillage nominal sortait
  retourné (volume négatif) : un résidu ouvert du marching cubes, accroché à la figure, rendait
  l'ensemble non fermé, et `fix_normals()` de trimesh n'inverse alors rien ; l'union des tenons rendait
  des morceaux. `sculpt.drop_residue_and_orient` retire les résidus (moins de 1 mm³ et de deux pas de
  grille) puis oriente chaque corps fermé (`fix_normals(multibody=True)`). Sans effet sur un maillage
  d'un seul corps déjà fermé, comme ceux des figurines livrées ; test
  `test_open_residue_does_not_leave_the_figure_inside_out`.
- **Contre-vérification de la version conforme, puis corrigée** : la version suivante est passée
  (CONFORME, aucun point sous 0,8 mm sur les 1 500 de la chaîne), mais sa contre-vérification sur
  12 000 points a trouvé un point à 0,25 mm sur l'arête haute de la ceinture, côté droit : coupée par
  deux plans dans l'espace, elle faisait un coin aigu de 67° là où la cage s'évase au-dessus de la
  taille. Un contrôle local plus dense a trouvé ensuite une lèvre de 0,13 mm au bout du bandage du
  poignet gauche : la bande, coupée net, dépassait du raccord du poing (3,3 mm de rayon) de 0,7 à
  1,15 mm en anneau à dents de scie. Corrections : ceinture coupée au pied de la normale, comme la
  veste (arête à 81°) ; deux derniers millimètres du bandage resserrés en cône jusqu'au rayon du
  raccord. Cette version n'a pas été livrée. Deuxième passe par régions sur la version retenue
  (onze régions, 69 468 points, autre graine) : aucun point sous 0,8 mm, sauf au pied du trait, où
  trois points de 0,71 à 0,76 mm marquent la peau d'une fente entre la volute de gauche, le petit bloc
  et l'appui du trait (0,04 % des points de la région, sous le seuil de 0,2 % ; imprimable en FDM, à
  combler avant une version résine). Contrôle dense des bouts de bandage et de la ceinture : minimum
  2,2 mm.
- **Demande** : « fusain » est aussi un mot courant (la technique, le crayon, l'arbuste). Le nom ne
  compte qu'avec un mot de figurine, et jamais dans « au fusain », « en fusain », « des fusains » ni
  « crayon / bâton / mine de fusain ». « Jarvis, dessine un portrait au fusain » ne lance rien ;
  « Jarvis, fais une statuette au fusain » demande quel personnage.
- **Tenons** : sous les deux plus grands appuis (D12). Les colonnes du trait sont toujours le plus
  grand ; les deux semelles ont presque la même surface, si bien que le second tenon peut passer d'un
  pied à l'autre selon le pas de grille. À 0,4 mm : Ø 4 sous les colonnes du trait, Ø 5 sous le pied
  droit, en arrière ; le pied gauche, devant, reste un appui sans tenon.
- **Exécution** (N2, conteneur Linux, Python 3.12.3, trimesh 4.11.1) : tâche `157d5194ebed0087`
  (l'identifiant dépend de la demande et des versions, pas de la géométrie : les relances le gardent),
  géométrie en 4 min et chaîne complète en 7 min 36 s pendant que deux contrôles locaux tournaient en
  parallèle (6 min 10 s seule, version précédente), 672 924 triangles, un seul corps fermé (un résidu du
  marching cubes retiré), CONFORME_AUX_CRITERES_CALCULES, épaisseur min / p1 1,97 / 2,68 mm, aucun point
  sous 0,8 mm sur 12 000 à la contre-vérification (un seul sous 1,2 mm : 0,93 mm, au pied du trait, dans
  la fente notée plus haut ; `contre_verification_epaisseur.json`), surplombs sur 9,4 % de la surface,
  centre de gravité à 44,5 mm du bord du socle, socle de 120 × 188 × 18 mm, tranchage estimé à 16 h 34
  et 133,9 g (figurine) et 8 h 30 et 76,2 g (socle), visionneuse 13/13
  (`preuves/execution-157d5194ebed0087-fusain/`).
- **Tests** : `test_fusain_and_everyday_uses_of_the_word`, `test_fusain_stroke_carries_the_open_hand_from_the_rocks`,
  `test_fusain_bandage_ends_flush_with_the_wrist`, `test_open_residue_does_not_leave_the_figure_inside_out`,
  `test_wrestler_stands_on_his_stroke_until_renders` (pas de 1,5 mm : à 2 mm, les doigts de la main
  ouverte ne sont pas résolus) et `test_character_defaults_keep_published_identities` étendu à Fusain.
- **Réexamen** : avis d'Olsen et de BOJ sur les rendus ; grande échelle (à 20 cm, la figurine seule,
  tenons compris, mesure 188 mm de haut ; au-delà d'environ 23 cm, elle dépasse les 220 mm de hauteur
  du plateau d'hypothèse : découpe en pièces et clés d'assemblage à concevoir) ; essai image→3D sur la
  tour (backlog, tâche 2) ; impression d'essai (N3).
