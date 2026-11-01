# BOJ.ART / Jarvis — Base métier documentée

**Version 1 — 30 octobre 2026.**

54 fiches, 10 procédures proposées, 38 références primaires et 8 structures de registre.

> Documentation préparée, pas recettes qualifiées. Aucun modèle réentraîné, aucune machine raccordée et aucun site modifié.

## Comment lire la base

Chaque fiche sépare le constat documentaire de son application proposée à BOJ.ART. Les exemples fabricant restent limités à leur portée ; aucune température, exposition, tolérance ou capacité machine universelle n’est préremplie. Les modèles des imprimantes et les références des matériaux restent inconnus.

Le changement de date de relecture est une politique documentaire de projet, pas une durée de validité établie par le fabricant. Une fiche ancienne reste visible avec avertissement ; sa mise à jour ne qualifie pas une recette.

## Fiches métier

### Conception & grands formats

#### K01 · Conserver le modèle source et la recette

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Les exports d’échange de CadQuery ne conservent pas l’ensemble de ses paramètres ; la recette Python reste nécessaire à la reproduction paramétrique.

**Application proposée :** Relier source, paramètres, version du moteur et exports STEP/STL/GLB. Modifier une copie versionnée, jamais l’unique original.

**Informations nécessaires :** source_native, parametres, version_moteur.

**Sources :** [S24 — CadQuery](https://cadquery.readthedocs.io/en/latest/importexport.html)

#### K02 · Unité et extensions du 3MF

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Le 3MF déclare une unité et peut exiger des extensions. Un lecteur qui ne les prend pas en charge ne doit pas traiter les extensions requises comme si elles étaient facultatives.

**Application proposée :** Relire dimensions et unités après import. Ne pas considérer un 3MF provenant d’un autre slicer comme un profil qualifié pour le parc.

**Informations nécessaires :** unite, dimensions_attendues, logiciel_source, extensions.

**Sources :** [S23 — 3MF Consortium](https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md)

#### K03 · Un maillage fermé n’est pas une validation mécanique

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Les outils d’analyse de maillage contrôlent notamment géométrie, volume ou surface. Ils ne démontrent pas à eux seuls la tenue de la pièce dans son usage réel.

**Application proposée :** Conserver séparément le contrôle numérique, la mesure physique et la validation artistique. Une réparation automatique doit être comparée à la géométrie initiale.

**Informations nécessaires :** unite, fonction_piece, rapport_mesh.

**Sources :** [S25 — Blender Extensions](https://extensions.blender.org/add-ons/print3d-toolbox/) ; [S08 — Prusa Research](https://help.prusa3d.com/fr/article/modelisation-en-pensant-a-limpression-3d_164135)

#### K04 · Jeux d’assemblage : aucun chiffre universel

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

L’ajustement dépend de la matière, de l’orientation, de la géométrie, de la calibration et des réglages. Prusa recommande de tester le jeu plutôt que de supposer une valeur universelle.

**Application proposée :** Imprimer un coupon tenon/logement avec le procédé et le post-traitement retenus. Mesurer puis tester avec les épaisseurs de colle, apprêt et peinture prévues.

**Informations nécessaires :** matiere_sku, orientation, coupon, etat_finition.

**Sources :** [S08 — Prusa Research](https://help.prusa3d.com/fr/article/modelisation-en-pensant-a-limpression-3d_164135)

#### K05 · Découper une grande sculpture pour l’assemblage

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La segmentation peut intégrer aligneurs et identifiants ; leur efficacité dépend de la précision et de la déformation des pièces réelles.

**Application proposée :** Placer les coupes selon accès, finition, efforts et emballage. Donner un identifiant à chaque segment, son ordre de montage et son interface avec le socle.

**Informations nécessaires :** hauteur_finale, volumes_utiles, plan_assemblage, transport.

**Sources :** [S21 — Formlabs](https://formlabs.com/fr/blog/how-to-create-models-larger-than-your-3d-printers-build-volume/)

#### K06 · Une figurine de 1 m se reconçoit, elle ne s’agrandit pas seulement

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

À géométrie pleine semblable, multiplier toutes les dimensions par cinq multiplie le volume par 125. C’est un calcul géométrique, pas une estimation de matière après évidement.

**Application proposée :** Revoir coques, renforts, centre de gravité, fixations et manutention. Ne pas reprendre automatiquement les parois d’une figurine de 20 cm.

**Informations nécessaires :** dimension_echelle, masse_estimee, fixation, transport.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

#### K07 · Choisir le procédé par fonction, pas par taille

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La finesse, l’orientation, les interfaces et la matière participent à la faisabilité. Le guide de conception distingue notamment rendu des surfaces et comportement selon l’orientation.

**Application proposée :** Comparaison FDM/résine/hybride par pièce : visibilité, charge, volume, temps de finition et coût conforme. La préférence initiale reste une intention à vérifier.

**Informations nécessaires :** usage, charge, detail_attendu, finition.

**Sources :** [S08 — Prusa Research](https://help.prusa3d.com/fr/article/modelisation-en-pensant-a-limpression-3d_164135)

### Matériaux

#### K08 · PLA : candidat pour les volumes décoratifs

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Le PLA est présenté comme facile à imprimer et adapté au détail ; il faut tenir compte de ses limites thermiques et de sa fragilité selon l’usage.

**Application proposée :** Candidat pour prototypes de forme et éléments décoratifs. Demander exposition à la chaleur, au soleil et aux chocs avant sélection ; conserver la référence exacte.

**Informations nécessaires :** sku, usage, environnement.

**Sources :** [S02 — Prusa Research](https://help.prusa3d.com/article/pla_2062)

#### K09 · PETG : usage fonctionnel à qualifier

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Le PETG possède une bonne ténacité et adhérence inter-couches ; son adhérence au plateau et ses fils peuvent demander une préparation spécifique.

**Application proposée :** Évaluer supports, boîtiers et interfaces. Comparer finition et démontage du plateau ; ne pas remplacer une recette PLA par PETG sans essai.

**Informations nécessaires :** sku, surface_plateau, usage.

**Sources :** [S03 — Prusa Research](https://help.prusa3d.com/article/petg_2059)

#### K10 · ASA : extérieur et déformation

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

L’ASA est présenté pour sa résistance aux UV et à la température ; son impression demande une gestion des déformations et des émissions.

**Application proposée :** Envisager pour décoration extérieure seulement après lecture de la fiche produit, étude de la machine et prévention du local. Pas de température universelle enregistrée.

**Informations nécessaires :** sku, enceinte, ventilation, conditions_service.

**Sources :** [S04 — Prusa Research](https://help.prusa3d.com/article/asa_1809) ; [S19 — INRS](https://www.inrs.fr/risques/fabrication-additive/prevention)

#### K11 · TPU : souplesse, grade et chemin de filament

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Les matériaux flexibles existent sous plusieurs grades ; leur alimentation, adhérence et réglages dépendent du matériau et de l’extrudeur.

**Application proposée :** Réserver un test aux pieds souples, amortisseurs ou protections. Documenter dureté, déformation attendue et compatibilité d’entraînement.

**Informations nécessaires :** sku, durete, extrudeur, usage.

**Sources :** [S05 — Prusa Research](https://help.prusa3d.com/fr/article/materiaux-flexibles_2057)

#### K12 · Nylon et PC : candidats avancés, pas substitutions automatiques

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Le guide matières distingue les polymères techniques et leurs exigences. L’humidité peut affecter fortement certains polyamides.

**Application proposée :** Créer une sélection documentaire pour prototypes techniques. Exiger la fiche du grade, les limites machine et des essais selon l’usage avant de proposer une recette.

**Informations nécessaires :** grade, TDS, capacites_machine, sechage.

**Sources :** [S01 — Prusa Research](https://help.prusa3d.com/filament-material-guide) ; [S06 — Prusa Research](https://help.prusa3d.com/article/drying-filament_332086)

#### K13 · Filament chargé : vérifier la buse et les propriétés

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Les charges carbone, verre ou kevlar peuvent être abrasives ; leur présence ne garantit pas une meilleure adhésion entre couches. Le polymère de base et le grade restent déterminants.

**Application proposée :** Vérifier buse, diamètre, alimentation et poussières lors de la finition. Ne pas qualifier une pièce porteuse uniquement parce que le filament est « carbone ».

**Informations nécessaires :** sku, charge, buse, TDS, essai_mecanique.

**Sources :** [S07 — Prusa Research](https://help.prusa3d.com/article/composite-materials-filled-with-carbon-kevlar-or-glass_167387)

#### K14 · Sécher selon le produit et la bobine

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La reprise d’humidité peut détériorer la surface et l’extrusion. Les instructions de séchage publiées pour Prusament sont spécifiques aux matériaux et aux bobines décrits.

**Application proposée :** Archiver marque, lot, ouverture, stockage et cycle de séchage autorisé. Ne pas recopier une température sur une bobine ou une résine différente.

**Informations nécessaires :** sku, lot, type_bobine, notice_sechage.

**Sources :** [S06 — Prusa Research](https://help.prusa3d.com/article/drying-filament_332086)

#### K15 · Fiche technique et FDS ont des rôles différents

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La FDS guide la manipulation et les risques ; les instructions de traitement identifient les conditions d’utilisation du matériau. Les propriétés finales dépendent aussi du cycle appliqué.

**Application proposée :** Pour chaque SKU : lier FDS, fiche technique, version, couleur, lot, procédés compatibles et preuves locales. Une fiche matériau n’est pas une recette imprimante.

**Informations nécessaires :** SDS, TDS, sku, version, lot.

**Sources :** [S15 — Formlabs](https://formlabs.com/support/Form-Cure-Time-and-Temperature-Settings/) ; [S17 — Formlabs](https://formlabs.com/support/Safety-with-Form-Wash/)

### Impression FDM

#### K16 · Calibrer dans un ordre reproductible

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

OrcaSlicer documente un parcours de calibration où température et débit conditionnent les essais suivants. Les menus doivent correspondre à la version installée.

**Application proposée :** Conserver le résultat de chaque coupon et une modification à la fois. Partir des profils et limites constructeur ; ne pas transformer une recommandation générique en commande.

**Informations nécessaires :** binaire_slicer, profil, materiau, coupon.

**Sources :** [S10 — OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer/wiki/calibration_guide)

#### K17 · La vitesse utile dépend du débit volumique

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Le débit maximal varie selon matière, machine, buse et extrudeur ; même une couleur ou une marque peut modifier le résultat.

**Application proposée :** Comparer qualité à débit réel, pas seulement mm/s annoncés. Archiver la limite mesurée avec le couple buse/matière et le profil exact.

**Informations nécessaires :** sku, couleur, buse, hotend, test_debit.

**Sources :** [S11 — OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer/wiki/volumetric_speed_calib)

#### K18 · Orientation : esthétique et résistance

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Les pièces FFF ne se comportent pas de façon identique dans toutes les directions. L’orientation influence aussi les surfaces en contact avec les supports.

**Application proposée :** Pour un support fonctionnel, orienter selon les efforts et vérifier un exemplaire représentatif. Pour une œuvre, comparer les marques et le temps de retouche.

**Informations nécessaires :** orientation, charges, faces_visibles, essais.

**Sources :** [S08 — Prusa Research](https://help.prusa3d.com/fr/article/modelisation-en-pensant-a-limpression-3d_164135)

#### K19 · Parois et remplissage : juger l’ensemble

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Prusa souligne l’importance des périmètres dans la résistance d’une pièce. Le remplissage seul ne décrit donc pas la structure finale.

**Application proposée :** Comparer parois, surfaces pleines, matière, orientation et forme. Ne pas déclarer « solide » une pièce seulement parce que son remplissage est élevé.

**Informations nécessaires :** perimetres, infill, orientation, usage.

**Sources :** [S09 — Prusa Research](https://help.prusa3d.com/article/layers-and-perimeters_1748)

#### K20 · Plateau et produit de nettoyage sont liés

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Les plaques lisses, satinées, texturées ou dédiées au nylon ne partagent pas automatiquement les mêmes compatibilités ni les mêmes produits d’entretien.

**Application proposée :** Identifier la surface exacte avant conseil. Une adhérence excessive peut aussi être un défaut ; tester la méthode de séparation indiquée par le fabricant.

**Informations nécessaires :** surface_id, materiau, notice_nettoyage.

**Sources :** [S37 — Prusa Research](https://help.prusa3d.com/fr/article/feuilles-dacier-flexible-guide_2195)

#### K21 · Défaut FDM : chercher avant de modifier

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La calibration comprend plusieurs facteurs interdépendants : température, débit, pression et rétraction. Une observation seule ne désigne pas toujours la cause.

**Application proposée :** Sur fils ou sous-extrusion : enregistrer photos, matière, profil et humidité ; comparer un seul changement dans les limites autorisées. Préserver le profil qui fonctionnait.

**Informations nécessaires :** photo, profil_revision, lot, symptome, changement.

**Sources :** [S10 — OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer/wiki/calibration_guide) ; [S06 — Prusa Research](https://help.prusa3d.com/article/drying-filament_332086)

### Impression résine

#### K22 · Exposition : recette propre au couple machine-résine

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** methode_documentee_valeurs_SL1_non_transferables.

La calibration résine Prusa montre que l’exposition et la hauteur de couche doivent correspondre au matériau ; pigments et viscosité influencent l’essai. Les valeurs SL1/SL1S ne sont pas universelles.

**Application proposée :** Relier fabricant/modèle/firmware, résine/SKU/lot, couche, conditions thermiques, paramètres de mouvement et résultat. Aucune durée UV par défaut dans cette base.

**Informations nécessaires :** machine, firmware, sku, layer_height, temperature, coupon.

**Sources :** [S12 — Prusa Research](https://help.prusa3d.com/article/resin-calibration-sl1-sl1s_112182)

#### K23 · Évidement : prévoir évacuation et accès

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

L’évidement économise matière et réduit certaines surfaces de séparation, mais peut emprisonner de la résine. La conception doit inclure des ouvertures de drainage adaptées.

**Application proposée :** Examiner chaque cavité et l’accès de nettoyage. Contrôler le maillage après l’opération ; ne pas fermer une cavité avant son contrôle de traitement.

**Informations nécessaires :** cavites, orientation, evacuation, acces_interieur.

**Sources :** [S13 — Prusa Research](https://help.prusa3d.com/article/hollowing_117285)

#### K24 · Effet ventouse : lire les cavités couche par couche

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Des cavités peuvent provoquer une aspiration pendant la séparation et causer déformation ou échec. Formlabs relie ce risque à l’orientation et aux ouvertures.

**Application proposée :** Contrôler orientation, cavités et supports ensemble ; relire l’aperçu des couches. Les angles publiés pour PreForm ne deviennent pas des réglages universels.

**Informations nécessaires :** orientation, cavites, preview_couches.

**Sources :** [S14 — Formlabs](https://formlabs.com/support/Preventing-suction-cups-in-PreForm/)

#### K25 · Contrôle des couches et des îlots

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

UVtools propose analyse, réparation, conversion et calibration pour des formats résine pris en charge. Cette compatibilité dépend du format et de la version.

**Application proposée :** Tester sur une copie les îlots, zones non supportées et modifications. Recontrôler le fichier final dans la chaîne de la machine ; ne pas supposer toutes les résines pilotables par G-code.

**Informations nécessaires :** format_machine, UVtools_version, fichier_original, rapport.

**Sources :** [S27 — UVtools — sn4k3](https://github.com/sn4k3/UVtools)

#### K26 · Lavage : produit, bain et géométrie

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Le lavage enlève la résine non polymérisée ; sa qualité dépend notamment du solvant, de sa contamination et de l’accès aux cavités.

**Application proposée :** Renseigner méthode autorisée, bain utilisé et contrôle de propreté. Séparer temps actif, durée de cycle et séchage dans la gamme.

**Informations nécessaires :** notice_resine, solvant, etat_bain, geometrie.

**Sources :** [S17 — Formlabs](https://formlabs.com/support/Safety-with-Form-Wash/) ; [S16 — Formlabs](https://formlabs.com/support/Using-Form-Cure/)

#### K27 · Post-polymériser après séchage complet

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Formlabs demande des pièces lavées et entièrement sèches pour Form Cure ; le temps et la température sont liés à la résine et à la version du poste.

**Application proposée :** Enregistrer le cycle exact et le contrôle des cavités. La base documentaire renvoie à la recette qualifiée ; elle ne donne pas un temps UV universel.

**Informations nécessaires :** resine_version, poste_cure, cycle, controle_sechage.

**Sources :** [S15 — Formlabs](https://formlabs.com/support/Form-Cure-Time-and-Temperature-Settings/) ; [S16 — Formlabs](https://formlabs.com/support/Using-Form-Cure/)

#### K28 · Supports imprimés mais pièce absente

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Un contrôle de fichier peut repérer des défauts géométriques ; l’exposition et le traitement doivent rester liés à une calibration appropriée.

**Application proposée :** Consigner le défaut, inspecter selon la notice la zone de fabrication avant relance et examiner supports/orientation/profil. Ne pas simplement augmenter l’exposition à chaque échec.

**Informations nécessaires :** photo, profil, inspection_bac, couches, calibration.

**Sources :** [S27 — UVtools — sn4k3](https://github.com/sn4k3/UVtools) ; [S12 — Prusa Research](https://help.prusa3d.com/article/resin-calibration-sl1-sl1s_112182)

#### K29 · Résine « à l’eau » : déchets à qualifier

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Une eau ou un solvant ayant été exposé à la résine reste à gérer selon les règles locales ; la facilité de lavage ne suffit pas à autoriser un rejet à l’évier.

**Application proposée :** Identifier chaque liquide contaminé, conserver la FDS et valider la filière avec le prestataire. Ne pas appliquer automatiquement les consignes de déchets ménagers d’un autre pays.

**Informations nécessaires :** SDS, liquide, filiere_locale.

**Sources :** [S18 — Formlabs](https://formlabs.com/support/Disposing-of-resin/) ; [S38 — Formlabs](https://formlabs.com/support/Washing-prints-with-TPM/)

### Finition & qualité

#### K30 · Apprêt et peinture : rendre le contrôle visible

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La préparation Formlabs prévoit retrait des marques, préparation de surface, apprêt puis inspection et éventuelle reprise avant finition.

**Application proposée :** Créer une éprouvette couleur/vernis et conserver la recette. Photographier sous lumière neutre puis créative ; la peinture ne doit pas masquer une fissure ou un raccord défectueux.

**Informations nécessaires :** peinture, appret, vernis, reference_couleur, controle.

**Sources :** [S22 — Formlabs](https://formlabs.com/support/Priming-Prints/)

#### K31 · Montage à blanc avant finition irréversible

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Une segmentation avec aligneurs doit tenir compte des variations dimensionnelles des pièces imprimées.

**Application proposée :** Faire un montage à blanc après les traitements nécessaires, contrôler accès et jeux, puis noter les reprises. Préserver les surfaces de collage selon la méthode qualifiée.

**Informations nécessaires :** segments, post_traitement, mesures, montage.

**Sources :** [S21 — Formlabs](https://formlabs.com/fr/blog/how-to-create-models-larger-than-your-3d-printers-build-volume/)

#### K32 · Critères de réception par pièce

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Proposition BOJ.ART : distinguer géométrie, ajustement, tenue attendue, surface, couleur et intégrité du transport.

**Application proposée :** Fixer les critères avec le brief avant production ; l’artiste et l’opérateur valident leurs domaines. Conserver instrument, unités, photos et résultat, sans certifier une charge non testée.

**Informations nécessaires :** criteres, instrument, mesures, validation_artiste.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

#### K33 · Emballage et socle font partie de la conception

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Proposition BOJ.ART : une œuvre grand format doit être conçue aussi pour la manipulation, le démontage éventuel et le transport.

**Application proposée :** Repérer les zones fragiles, définir protections et points de préhension, peser le colis fini et réaliser un contrôle de conditionnement. Aucune chute ni vibration certifiée sans protocole adapté.

**Informations nécessaires :** masse, gabarit, zones_fragiles, mode_transport.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

#### K34 · Prototypes et robotique : spécifier la fonction

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Proposition BOJ.ART : un prototype n’est pas automatiquement une pièce de service. Les usages porteurs, mobiles, chauds ou exposés exigent des critères propres.

**Application proposée :** Documenter efforts, cycles, interfaces, température, accessibilité et modes de défaillance. Vérifier les sous-ensembles avant des essais progressifs dans un espace contrôlé.

**Informations nécessaires :** fonction, charges, cycles, interfaces, risques.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

### Prévention & entretien

#### K35 · Prévention : d’abord la protection collective

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

L’INRS privilégie substitution, circuit fermé et captage à la source ; la ventilation générale est complémentaire et les protections individuelles s’ajoutent selon le risque.

**Application proposée :** Faire évaluer postes résine, ponçage et peinture. Ne pas conclure qu’une imprimante fermée ou un purificateur domestique suffit pour le local.

**Informations nécessaires :** local, produits, captage, evaluation_risques.

**Sources :** [S19 — INRS](https://www.inrs.fr/risques/fabrication-additive/prevention)

#### K36 · Les opérations annexes comptent aussi

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La notice INRS ED 148 souligne les expositions possibles à la préparation, au retrait, à la finition et à la maintenance, parfois plus importantes que pendant l’impression.

**Application proposée :** Séparer zones propres et contaminées, rangement produits et captation vidéo. Ne jamais retirer une protection ou arrêter un captage pour améliorer une prise de vue.

**Informations nécessaires :** plan_zones, procedure, formation.

**Sources :** [S20 — INRS](https://www.inrs.fr/media.html?refINRS=ED+148)

#### K37 · Solvants et consommables : consignes exactes

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Les consignes Form Wash renvoient aux précautions des solvants et à leurs fiches de sécurité. Les procédures dépendent des produits et équipements employés.

**Application proposée :** Stocker et étiqueter selon les FDS, former les opérateurs et prévoir la conduite à tenir en cas d’incident. Ne pas improviser mélange, chauffage ou recyclage d’un solvant.

**Informations nécessaires :** SDS, solvant, stockage, plan_incident.

**Sources :** [S17 — Formlabs](https://formlabs.com/support/Safety-with-Form-Wash/)

#### K38 · Entretien : une procédure par modèle

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** exemple_CORE_One_non_transferable.

La maintenance CORE One/+ distingue tiges, rails, surfaces et solvants ; certains lubrifiants y sont explicitement interdits sur certains organes.

**Application proposée :** Importer la notice de chaque machine et sa révision. Une périodicité ou graisse d’une autre imprimante reste une hypothèse rejetée, même si le mécanisme semble similaire.

**Informations nécessaires :** modele, organe, notice_revision, historique.

**Sources :** [S31 — Prusa Research](https://help.prusa3d.com/article/regular-printer-maintenance-core-one_829710)

### Pilotage & planning

#### K39 · Slicing automatisé : conserver les entrées effectives

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

OrcaSlicer possède une interface de commande pour charger, transformer et trancher avec des réglages. Les options doivent correspondre au binaire retenu.

**Application proposée :** Enregistrer modèle, unité, transformation, supports, versions et réglages réellement appliqués. Vérifier les sorties avant transfert ; ne pas invoquer une commande créée librement par un LLM.

**Informations nécessaires :** slicer_sha, profils_sha, model_sha, journal_slicing.

**Sources :** [S26 — OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_mode)

#### K40 · Une file d’impression n’est pas un contrôle de plateau

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

Moonraker décrit une file de travaux et ses transitions ; une commande en file n’atteste pas le retrait physique de l’objet précédent.

**Application proposée :** Garder la machine réservée jusqu’à son contrôle et sa préparation. Prévoir une confirmation opérateur ou un dispositif qualifié de libération ; ne pas confondre inactive et prête.

**Informations nécessaires :** etat_machine, travail_actif, plateau_libere, recette.

**Sources :** [S28 — Moonraker](https://moonraker.readthedocs.io/en/latest/external_api/job_queue/)

#### K41 · Pause, reprise et arrêt ne sont pas interchangeables

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

L’API OctoPrint utilise par défaut un basculement pour pause sans action explicite. Moonraker précise qu’un M112 placé dans sa file G-code ne s’exécute pas immédiatement.

**Application proposée :** Le connecteur doit choisir une opération explicite et relire l’état. La voix ne remplace pas l’arrêt physique ; qualifier les fonctions de sécurité hors de cette bibliothèque.

**Informations nécessaires :** connecteur, version_api, etat, procedure_arret.

**Sources :** [S29 — Moonraker](https://moonraker.readthedocs.io/en/latest/external_api/printer/) ; [S30 — OctoPrint](https://docs.octoprint.org/en/main/api/job.html)

#### K42 · Réponse perdue : conserver « résultat inconnu »

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Règle BOJ.ART proposée : un envoi sans réponse n’est ni un échec prouvé ni une autorisation de répéter une action physique.

**Application proposée :** Conserver identifiant, fichier, cible et heure. Relire le travail actif et les reçus avant décision ; ne jamais rejouer un démarrage à partir d’un simple conseil documentaire.

**Informations nécessaires :** operation_id, file_sha, machine_id, received_state.

**Sources :** [S28 — Moonraker](https://moonraker.readthedocs.io/en/latest/external_api/job_queue/) ; [S30 — OctoPrint](https://docs.octoprint.org/en/main/api/job.html)

#### K43 · Planifier aussi les ressources humaines

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

L’exemple Job Shop OR-Tools formalise les contraintes de succession et de non-chevauchement d’une ressource.

**Application proposée :** Modéliser opérateurs, machine, lavage/cure et cabine de peinture. Séparer temps actif et temps d’attente ; ne pas réserver deux fois la capacité d’un poste combiné.

**Informations nécessaires :** gamme, capacites, temps_actifs, temps_cycles.

**Sources :** [S36 — Google OR-Tools](https://developers.google.com/optimization/scheduling/job_shop)

#### K44 · Les sources documentaires ne donnent pas l’état actuel

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Règle BOJ.ART : la bibliothèque explique les procédures ; le stock et l’état du plateau doivent venir de mesures ou d’événements récents et identifiés.

**Application proposée :** Chaque observation opérationnelle a une date, un producteur et une cible. Une ancienne disponibilité ou une fiche trouvée sur Internet ne peut pas déclencher un travail.

**Informations nécessaires :** horodatage, producteur, cible, fraicheur.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

### Coûts & stocks

#### K45 · Coût d’une pièce conforme, pas seulement de matière

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Méthode proposée : inclure conception, matière des supports et reprises, occupation machine, travail actif, traitement, finition, contrôle, déchets, emballage et coûts imputés.

**Application proposée :** Séparer prévision et constat. Une somme calculée avec des champs inconnus doit rester une estimation incomplète, jamais un devis prêt à accepter.

**Informations nécessaires :** matiere, temps_actif, machine, rebuts, emballage.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

#### K46 · Marge et majoration : bases différentes

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Si C est le coût complet hors frais proportionnels, m la marge sur prix de vente et f les frais sur la même base, P = C / (1 − m − f), seulement si m + f < 1.

**Application proposée :** Formule de gestion, pas de conseil fiscal. Ne pas mélanger HT/TTC ni compter deux fois une commission. Enregistrer la méthode et les coûts manquants.

**Informations nécessaires :** base_fiscale_coherente, cout_complet, marge, commission.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

#### K47 · Stocks : réserver le disponible mesuré

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Règle proposée : distinguer quantité physique, réservée, consommée, perdue et en quarantaine ; garder unités et lots.

**Application proposée :** Mettre à jour à la pesée ou à l’événement contrôlé. Le filament prévu par le slicer n’est pas nécessairement la consommation réellement imputée.

**Informations nécessaires :** sku, lot, quantite, unite, reservation, mesure.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

#### K48 · Apprendre des défauts sans changer la recette tout seul

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Règle proposée : lier chaque défaut au modèle, à la révision, au lot, au profil, aux conditions, aux photos et à la correction testée.

**Application proposée :** Un cas similaire peut guider le diagnostic ; il ne prouve pas la cause. Une meilleure recette doit être approuvée et versionnée avant répétition.

**Informations nécessaires :** defaut, recette, lot, photos, cause_confirmee, resultat.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

### Studio & identité

#### K49 · Métadonnées vidéo : preuve technique, pas licence

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

FFprobe lit les caractéristiques des fichiers et des flux. Leur durée, codec ou présence audio ne démontrent ni les droits de publication ni la fidélité de la sculpture.

**Application proposée :** Réutiliser la séparation de Mission 03 : original, passage annoté, storyboard et génération. Conserver timecodes et empreintes ; valider la qualité en mouvement.

**Informations nécessaires :** media_sha, timecodes, categorie, droits, revue.

**Sources :** [S35 — FFmpeg](https://www.ffmpeg.org/ffprobe.html)

#### K50 · Les références réelles priment sur les concepts

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Règle BOJ.ART issue du projet : l’œuvre physique et sa fiche d’identité priment sur une illustration réinterprétée.

**Application proposée :** Relier chaque tournage et génération à une œuvre. Un plan rejeté pour short, visage ou proportions incorrects n’est jamais promu en référence principale du plan suivant.

**Informations nécessaires :** oeuvre_id, reference_reelle, character_lock, motif_rejet.

**Origine :** méthode proposée pour BOJ.ART ou calcul explicite, pas consigne d’un fabricant.

### Données & droits

#### K51 · Données privées : accès et destination explicites

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La CNIL rappelle les limites probabilistes des modèles et l’importance des données autorisées ; elle distingue déploiement local et services distants pour la confidentialité.

**Application proposée :** Séparer atelier, médias autorisés et données clients. Les connecteurs externes reçoivent seulement ce qui est nécessaire et autorisé ; ne pas indexer tout le PC par défaut.

**Informations nécessaires :** autorisation_dossier, roles, destination, donnees_minimales.

**Sources :** [S32 — CNIL](https://www.cnil.fr/fr/les-questions-reponses-de-la-cnil-sur-lutilisation-dun-systeme-dia-generative)

#### K52 · Droits sur personnage, fichier et média

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

L’INPI décrit les droits de reproduction, de représentation et d’adaptation. Leur disponibilité doit être vérifiée pour les usages effectivement prévus.

**Application proposée :** Documenter distinctement STL, personnage, photographies, musique et promotion payante. Un fichier acheté n’établit pas automatiquement tous ces droits.

**Informations nécessaires :** licence_stl, droits_personnage, droits_medias, usage.

**Sources :** [S34 — INPI](https://www.inpi.fr/ressources/propriete-intellectuelle/droit-dauteur)

#### K53 · Mesure marketing : consentement et attribution limitée

**Statut :** DOCUMENTÉ — NON QUALIFIÉ SUR LE PARC. **Portée :** principe_general.

La CNIL impose un consentement préalable pour les traceurs concernés, notamment publicitaires ; certaines fonctions nécessaires relèvent d’exemptions précises.

**Application proposée :** Relier les demandes à leur campagne lorsque la preuve existe. Conserver « inconnu » lorsque l’attribution manque ; ne pas promettre une identification parfaite de chaque spectateur.

**Informations nécessaires :** traceurs, consentement, utm, brief_id.

**Sources :** [S33 — CNIL](https://cnil.fr/fr/cookies-et-autres-traceurs/que-dit-la-loi)

#### K54 · Corpus ≠ modèle réentraîné ≠ recette qualifiée

**Statut :** RÈGLE BOJ.ART PROPOSÉE. **Portée :** principe_general.

Cette livraison est un corpus documentaire et un outil de recherche textuelle. Elle n’entraîne aucun modèle et ne rend aucune machine opérationnelle.

**Application proposée :** Faire répondre Jarvis avec les sources, leur portée et les données manquantes. Une règle documentaire ne peut pas être promue automatiquement en paramètre machine.

**Informations nécessaires :** source, scope, validation_locale.

**Sources :** [S32 — CNIL](https://www.cnil.fr/fr/les-questions-reponses-de-la-cnil-sur-lutilisation-dun-systeme-dia-generative)

## Procédures proposées

### P01 · Réception d’un projet 3D

Éviter une géométrie sans usage ni critères.

1. Attribuer projet, révision et provenance au brief et aux fichiers.
2. Renseigner échelle, unité, dimensions socle compris ou non, quantité, usage, exposition, finition et transport.
3. Séparer attentes esthétiques, interfaces, charges et fonctions critiques.
4. Vérifier les droits prévus pour création, vente et médias.
5. Conserver les inconnues ; ne pas accepter un délai fondé sur une capacité non mesurée.

**Preuves attendues :** brief, criteres_reception, liste_inconnues, droits.

**Condition :** Brief techniquement examiné ; inconnues bloquantes levées avant engagement.

### P02 · Qualification FDM d’une recette

Construire un couple machine/matière reproductible.

1. Lire les notices de la machine, de la surface et du SKU ; figer les versions et limites.
2. Inspecter la machine selon sa notice et confirmer la préparation du plateau.
3. Préparer les essais de température, débit et réglages associés selon la documentation de la version utilisée.
4. Réaliser un coupon d’ajustement et un segment représentatif du futur objet.
5. Mesurer après stabilisation et finition prévue ; enregistrer défauts, temps, matière et photos.
6. Faire approuver la recette et ses limites ; requalifier après changement pertinent.

**Preuves attendues :** machine, sku, buse, firmware, profil_sha, coupons, mesures.

**Condition :** Critères du projet atteints sur un exemplaire représentatif, pas seulement sur un cube.

### P03 · Qualification résine d’une recette

Éviter la copie de temps d’exposition entre machines.

1. Identifier résine exacte, FDS, compatibilité optique, poste, firmware et trancheur.
2. Vérifier le bac/film et les contrôles constructeur avant essais.
3. Calibrer les conditions recommandées pour la couche et les conditions thermiques retenues.
4. Imprimer un coupon de détail et de raccord représentatif.
5. Laver, sécher et post-polymériser selon la recette fabricant ; documenter ces opérations.
6. Mesurer, tester l’ajustement, constater la finition et faire approuver.

**Preuves attendues :** sku_version, lot, temperature, exposition, mouvements, post_traitement, coupon.

**Condition :** Recette et post-traitement qualifiés ensemble ; aucune recette générique prédéfinie.

### P04 · Figurine grand format hybride

Rendre le découpage compatible avec l’ensemble de la fabrication.

1. Définir hauteur finale, socle, masse cible, pose, stabilité et conditionnement.
2. Proposer les coupes selon détails, interfaces, manutention et accès de finition.
3. Choisir procédé et matériau par segment, puis vérifier le volume avec supports.
4. Concevoir cavités résine et accès au nettoyage ; contrôler les coupes en aperçu de couches.
5. Fabriquer un raccord à l’échelle finale, puis un segment représentatif.
6. Créer nomenclature, ordre d’assemblage, repères et gamme complète avant les lots.

**Preuves attendues :** nomenclature, plans_interfaces, orientation, supports, volumes, transport.

**Condition :** Montage d’essai et traitement accessibles ; la grande pièce n’est pas un simple STL agrandi.

### P05 · Diagnostiquer un échec

Remplacer les modifications aléatoires par un historique exploitable.

1. Sécuriser la situation selon la notice et isoler le travail concerné.
2. Enregistrer symptôme, photos, étape, fichier, profil, lot, matériel et dernier changement.
3. Séparer fait observé, cause possible et cause confirmée.
4. Choisir un contrôle discriminant et un seul changement dans la plage autorisée.
5. Comparer avec le témoin ; conserver les échecs et les résultats.
6. N’approuver la nouvelle recette qu’après validation de sa portée.

**Preuves attendues :** incident, photos, hypotheses, test, resultat.

**Condition :** Cause et correction suffisamment documentées ; pas d’augmentation aveugle des paramètres.

### P06 · Finition et fidélité BOJ.ART

Conserver l’apparence et les cotes de l’œuvre réelle.

1. Contrôler traitement et montage à blanc avant collage/peinture.
2. Valider un échantillon d’apprêt, peinture et vernis sur la matière prévue.
3. Protéger les interfaces et respecter les temps de traitement du produit.
4. Photographier sous lumière neutre pour comparaison, puis sous lumière créative.
5. Faire valider l’aspect et les critères techniques séparément.
6. Conserver recette couleur, gestes utiles et médias avec l’identifiant de l’œuvre.

**Preuves attendues :** echantillon, recette_couleur, photos, accord_artistique, controle_technique.

**Condition :** Validation de l’œuvre physique ; aucun rendu IA ne remplace le contrôle.

### P07 · Planifier et lancer un lot

Séparer préparation logique et disponibilité physique.

1. Confirmer projet, pièce, révision, fichiers et profils effectifs.
2. Réserver matériaux, machine, opérateur, traitement et finition.
3. Vérifier contrôles géométriques, prévention et état physique de préparation.
4. Créer une opération avec identifiant unique et reçu cible, via le connecteur qualifié.
5. Relire le travail actif ; en cas de réponse perdue, conserver l’état inconnu.
6. Ne libérer la machine qu’après retrait et préparation constatés.

**Preuves attendues :** operation_id, file_sha, resources, readiness, receipt, state.

**Condition :** Cette bibliothèque ne réalise aucune des commandes : raccordement et recette matérielle distincts.

### P08 · Chiffrer et apprendre du coût réel

Estimer le travail complet puis comparer aux réalisations.

1. Décomposer conception, machine, matières, supports, pertes, finition, contrôle, emballage et frais.
2. Séparer temps actif et cycles ; préciser ce qui est mesuré ou estimé.
3. Réserver une provision explicite pour les inconnues plutôt que masquer des zéros.
4. Calculer sur une base cohérente et conserver la version du devis.
5. À la clôture, relever quantités conformes, reprises et coûts imputés.
6. Comparer prévision/constaté avant d’ajuster la prochaine estimation.

**Preuves attendues :** couts, hypotheses, devis_revision, mesures, ecarts.

**Condition :** Pas de devis automatique lorsque les coûts indispensables manquent.

### P09 · Tenir la documentation à jour

Rendre les connaissances réutilisables sans créer de fausse certitude.

1. Référencer une source et sa portée exacte ; la synthèse reste séparée de l’original.
2. Stocker une date de consultation et une échéance de relecture choisie par le projet.
3. Rapprocher les nouveaux documents de la machine et du SKU concernés.
4. Signaler les contradictions, ne pas moyenner les valeurs incompatibles.
5. Faire qualifier un changement sur un exemplaire avant recette de production.
6. Garder l’ancienne version et tester la restauration.

**Preuves attendues :** source_url, scope, revision, date, contradiction, qualification.

**Condition :** Une documentation relue ne devient pas automatiquement une recette qualifiée.

### P10 · Relier fabrication, contenu et demande client

Préparer l’acquisition avec les œuvres réellement disponibles.

1. Associer chaque captation à l’œuvre, l’étape et les droits de diffusion.
2. Séparer originaux, concepts et générations ; réserver les passages authentiques comme références.
3. Préparer la version de montage et vérifier son sujet, son audio et sa destination.
4. Relier la publication autorisée à une offre réalisable et à un suivi conforme.
5. Suivre les demandes puis le délai et la marge constatés, sans exposer les coordonnées clients.
6. Ne pas augmenter automatiquement la publicité lorsque la capacité de finition est saturée.

**Preuves attendues :** oeuvre_id, media_sha, droits, montage, campagne, capacity.

**Condition :** Publication, dépense et promesse commerciale restent des opérations autorisées séparément.

## Références primaires

### S01 · Filament Material Guide
Prusa Research · https://help.prusa3d.com/filament-material-guide

**Portée :** Familles de filaments ; propriétés et réglages précis à vérifier par référence.
**Section :** Comparatif matériaux
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S02 · PLA
Prusa Research · https://help.prusa3d.com/article/pla_2062

**Portée :** Guide de famille PLA, pas une fiche de votre filament.
**Section :** Basic info; Description
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S03 · PETG
Prusa Research · https://help.prusa3d.com/article/petg_2059

**Portée :** Guide PETG ; surface et réglages à confirmer.
**Section :** Basic info; Tips
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S04 · ASA
Prusa Research · https://help.prusa3d.com/article/asa_1809

**Portée :** Guide ASA ; prévention à appliquer à votre local.
**Section :** Basic info; Tips
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S05 · Matériaux flexibles
Prusa Research · https://help.prusa3d.com/fr/article/materiaux-flexibles_2057

**Portée :** TPU/TPE : différences entre grades et extrudeurs.
**Section :** Description; difficulté impression
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S06 · Drying filament
Prusa Research · https://help.prusa3d.com/article/drying-filament_332086

**Portée :** Table de séchage Prusament : ne pas transposer à une autre marque ou bobine.
**Section :** Prevention; Prusament spool types; Temperatures
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S07 · Composite materials (carbon, kevlar, glass)
Prusa Research · https://help.prusa3d.com/article/composite-materials-filled-with-carbon-kevlar-or-glass_167387

**Portée :** Matériaux chargés ; compatibilité de la buse et grade exact.
**Section :** Basic info; Use a hardened nozzle
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S08 · Modélisation en pensant à l’impression 3D
Prusa Research · https://help.prusa3d.com/fr/article/modelisation-en-pensant-a-limpression-3d_164135

**Portée :** Conception FFF ; les exemples chiffrés constructeur ne sont pas des tolérances BOJ.ART.
**Section :** Tolérances; Orientation
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S09 · Layers and perimeters
Prusa Research · https://help.prusa3d.com/article/layers-and-perimeters_1748

**Portée :** PrusaSlicer ; résistance dépend aussi de la charge et de la fabrication.
**Section :** Perimeters; thin walls
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S10 · Calibration Guide
OrcaSlicer · https://github.com/OrcaSlicer/OrcaSlicer/wiki/calibration_guide

**Portée :** Documentation courante ; confirmer avec la version installée.
**Section :** Filament Calibration
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S11 · Max Volumetric Speed Calibration
OrcaSlicer · https://github.com/OrcaSlicer/OrcaSlicer/wiki/volumetric_speed_calib

**Portée :** Calibration propre au filament, à la buse et au montage.
**Section :** Calibration overview
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S12 · Resin Calibration (SL1/SL1S)
Prusa Research · https://help.prusa3d.com/article/resin-calibration-sl1-sl1s_112182

**Portée :** SL1/SL1S seulement pour les valeurs et menus ; méthode non directement portable.
**Section :** Exposure; calibration objects; layer height
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S13 · Hollowing
Prusa Research · https://help.prusa3d.com/article/hollowing_117285

**Portée :** Outil SLA PrusaSlicer ; géométrie après évidement à contrôler.
**Section :** Drainage; preview hollowed mesh
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S14 · Preventing suction cups in PreForm
Formlabs · https://formlabs.com/support/Preventing-suction-cups-in-PreForm/

**Portée :** PreForm et procédés résine ; orientation spécifique au fichier.
**Section :** Resolving suction cups
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S15 · Form Cure V1 time and temperature settings
Formlabs · https://formlabs.com/support/Form-Cure-Time-and-Temperature-Settings/

**Portée :** Form Cure V1 et résines Formlabs identifiées ; non universel.
**Section :** Settings by resin
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S16 · Using the Form Cure V1
Formlabs · https://formlabs.com/support/Using-Form-Cure/

**Portée :** Form Cure V1 ; ne pas transposer les temps ou températures.
**Section :** Washed and fully dried parts
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S17 · Safety with the Form Wash
Formlabs · https://formlabs.com/support/Safety-with-Form-Wash/

**Portée :** Équipement et solvants Formlabs ; FDS du fournisseur prioritaire.
**Section :** Safety; solvent handling
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S18 · Disposing of resin
Formlabs · https://formlabs.com/support/Disposing-of-resin/

**Portée :** Déchets résine : vérifier la filière locale et la FDS ; pas de règle universelle de déchets ménagers.
**Section :** Liquid resin; drains
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S19 · Fabrication additive : prévention
INRS · https://www.inrs.fr/risques/fabrication-additive/prevention

**Portée :** Prévention générale ; étude du local et des produits requise.
**Section :** Captage; organisation; nettoyage
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S20 · Fabrication additive utilisant des matières plastiques — ED 148
INRS · https://www.inrs.fr/media.html?refINRS=ED+148

**Portée :** Notice publique de la fiche ; résumé de la notice, pas analyse du PDF.
**Section :** Présentation des risques et opérations annexes
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S21 · Modèles plus gros que le volume d’impression
Formlabs · https://formlabs.com/fr/blog/how-to-create-models-larger-than-your-3d-printers-build-volume/

**Portée :** Méthode de segmentation ; les performances Formlabs citées ne valent pas pour votre parc.
**Section :** Division; identifiants; aligneurs
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S22 · Preparing prints for painting
Formlabs · https://formlabs.com/support/Priming-Prints/

**Portée :** Préparation de surface ; appliquer notices produit et prévention locale.
**Section :** Support marks; primer inspection
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S23 · 3MF Core Specification
3MF Consortium · https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md

**Portée :** 3MF Core ; extensions et implémentations à vérifier.
**Section :** 3.1; 3.4; requiredextensions; 5.1
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S24 · Importing and Exporting Files
CadQuery · https://cadquery.readthedocs.io/en/latest/importexport.html

**Portée :** CadQuery ; STEP/STL ne conservent pas toute la recette paramétrique.
**Section :** Introduction; export formats
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S25 · 3D Print Toolbox
Blender Extensions · https://extensions.blender.org/add-ons/print3d-toolbox/

**Portée :** Extension identifiée ; tests sur version de Blender requise.
**Section :** Analyze; Edit; Export
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S26 · CLI Mode
OrcaSlicer · https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_mode

**Portée :** Version du binaire à figer ; le tranchage ne prouve pas le transfert machine.
**Section :** Invocation; load settings; slice
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S27 · UVtools
UVtools — sn4k3 · https://github.com/sn4k3/UVtools

**Portée :** Formats résine explicitement supportés par la version retenue.
**Section :** File analysis; calibration; repair; conversion
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S28 · Job Queue Management
Moonraker · https://moonraker.readthedocs.io/en/latest/external_api/job_queue/

**Portée :** Machines Klipper/Moonraker compatibles et configurées.
**Section :** Queue states; duplicate jobs; transitions
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S29 · Printer Administration
Moonraker · https://moonraker.readthedocs.io/en/latest/external_api/printer/

**Portée :** API Moonraker ; aucun arrêt logiciel ne remplace la sécurité physique.
**Section :** G-code scripts; emergency stop; job management
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S30 · Job operations
OctoPrint · https://docs.octoprint.org/en/main/api/job.html

**Portée :** OctoPrint ; permissions et firmware à vérifier.
**Section :** Pause action; 409; 204 responses
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S31 · Regular printer maintenance (CORE One/+)
Prusa Research · https://help.prusa3d.com/article/regular-printer-maintenance-core-one_829710

**Portée :** CORE One/+ seulement ; ne pas copier lubrifiants ni périodicités vers un autre modèle.
**Section :** Rails; print sheet; electronics
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S32 · Questions-réponses sur un système d’IA générative
CNIL · https://www.cnil.fr/fr/les-questions-reponses-de-la-cnil-sur-lutilisation-dun-systeme-dia-generative

**Portée :** Cadre de protection des données ; à adapter aux traitements BOJ.ART.
**Section :** Limites; on premise; données soumises
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S33 · Cookies et traceurs : que dit la loi ?
CNIL · https://cnil.fr/fr/cookies-et-autres-traceurs/que-dit-la-loi

**Portée :** Site en France ; exemptions et dispositifs à qualifier.
**Section :** Consentement préalable
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S34 · Le droit d’auteur
INPI · https://www.inpi.fr/ressources/propriete-intellectuelle/droit-dauteur

**Portée :** Présentation générale ; ne détermine pas les droits d’une œuvre précise.
**Section :** Reproduction; adaptation; droits patrimoniaux
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S35 · FFprobe Documentation
FFmpeg · https://www.ffmpeg.org/ffprobe.html

**Portée :** Mesures de fichiers médias ; pas de preuve des droits ni de qualité artistique.
**Section :** show_entries; formats; streams
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S36 · The Job Shop Problem
Google OR-Tools · https://developers.google.com/optimization/scheduling/job_shop

**Portée :** Exemple de contraintes d’ordonnancement, pas un planning réel d’atelier.
**Section :** Precedence; no overlap; makespan
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S37 · Feuilles d’acier flexible : guide
Prusa Research · https://help.prusa3d.com/fr/article/feuilles-dacier-flexible-guide_2195

**Portée :** Plaques Prusa ; produit de nettoyage selon la surface exacte.
**Section :** Materials and sheet compatibility
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-04-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.

### S38 · Washing prints with TPM
Formlabs · https://formlabs.com/support/Washing-prints-with-TPM/

**Portée :** Lavage TPM et rinçage ; eaux contaminées à traiter selon la filière.
**Section :** Disposal of water and TPM
**Consultation :** 2026-10-30 · **Relecture proposée :** 2027-01-28

**Copie :** seul un lien et une synthèse sont fournis. Aucun document intégral de tiers n’est redistribué.
