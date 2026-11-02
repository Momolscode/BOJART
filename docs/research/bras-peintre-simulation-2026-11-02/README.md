# Bras peintre : bras achetables simulables et boucle d'apprentissage — 2 novembre 2026

Statut : **recherche et prototype logiciel**. Aucun bras, pinceau, peinture ou coupon n'a été acheté, piloté ou mesuré. Rien ici n'autorise un achat, une commande machine ou un message à un tiers. Le nom du partenaire qui projette la galerie reste hors de ce dépôt public.

Demande (source `painter-request-20261102`) : trouver des bras robotiques achetables qui ont déjà un modèle de simulation, puis créer une boucle de simulation où le bras apprend à reproduire un tableau ou à peindre d'une certaine manière.

Ce travail complète l'audit STRATES du même jour (`docs/research/strates-robotique-2026-11-02/README.md`, fusionné dans `main`) : banc d'essai ciblé avant tout achat, trait nominal de 7 mm, débordement ≤ 1 mm, jalons G0 à G4. La simulation ci-dessous reprend ce budget d'erreur et ne remplace aucun jalon.

## Comparatif court

Caractéristiques relues le 2 novembre 2026 sur les pages citées (`configs/painter/arms.json`, sources `web-*-20261102`). Prix indicatifs, hors porte-outil, capteur d'effort, sécurité et intégration.

| Bras | Portée | Répétabilité | Charge | Prix indicatif | Modèles de simulation existants |
|---|---|---|---|---|---|
| **UFACTORY xArm 6** | 700 mm | ±0,1 mm | 5 kg | 9 500 USD ; 8 122 GBP TTC | URDF constructeur (xarm_ros2) ; **FRIDA** le pilote ; Menagerie n'a que l'xArm7 |
| AgileX PiPER | 626 mm | ±0,1 mm | 1,5 kg | 2 400 € TTC ; 3 500 USD | MuJoCo Menagerie `agilex_piper`, URDF constructeur |
| UFACTORY Lite 6 | 440 mm | ±0,5 mm | 0,6 kg | dès 2 999 USD | Menagerie `ufactory_lite6`, URDF constructeur |
| Universal Robots UR5e | 850 mm | ±0,03 mm | 5 kg | sur devis | Menagerie `universal_robots_ur5e`, URDF, URSim |
| Franka Research 3 | 855 mm | < ±0,1 mm | 3 kg | sur devis | Menagerie `franka_fr3`, URDF ; **FRIDA** le pilote |
| SO-101 (LeRobot) | non publiée | non publiée | — | 500 USD | Menagerie `robotstudio_so101`, LeRobot |

Le projet de recherche le plus proche est **FRIDA** (CMU, GPL-3.0) : simulation différentiable des touches construite à partir de mesures réelles, replanification après photo de la toile, objectifs image, style ou texte. Il prend en charge xArm et Franka et propose un mode simulation seule.

## Ce que la simulation ajoute au comparatif

Mesures du 2 novembre, hôte Linux sans GPU ni robot : `docs/evidence/painter-simulation-2026-11-02/`.

**Accès à une toile de 90 × 65 cm** (portée × 0,85 pour garder le pinceau perpendiculaire, rayon mort 20 %) :

| Bras | Bras posé au bord | Bras en surplomb central |
|---|---|---|
| xArm 6 | 66 % | 99 % |
| PiPER | 54 % | 88 % |
| Lite 6 | 22 % | 27 % |
| UR5e / FR3 | 89 % | 100 % |

**Coupon STRATES virtuel** (trait de 7 mm sur 150 mm, débordement + incertitude ≤ 1 mm, largeur 6–8 mm sur 90 % de la longueur). Le scénario nominal tire chaque poste du budget avec un écart type égal à la moitié de son allocation. Sur 59 essais : UR5e et FR3 58/59, PiPER 56/59, xArm 6 52/59, **Lite 6 26/59**. Dans le scénario pessimiste (écart type égal à l'allocation), aucun bras ne réussit. Le budget de 1 mm est donc tenu seulement si chaque poste reste nettement sous son allocation : c'est le procédé qu'il faut mesurer (G1), pas seulement le bras.

## Recommandation

1. **Simuler et développer sur un modèle xArm 6.** Sa portée couvre presque toute la toile en surplomb. Sa répétabilité tient le budget. Sa charge laisse de la place pour un capteur d'effort et un porte-pinceau compliant. Surtout, FRIDA le pilote déjà : c'est le chemin le plus court vers une boucle réelle.
2. **PiPER comme option économique** pour un banc de coupons. Même répétabilité annoncée, modèle MuJoCo officiel dans Menagerie, mais charge de 1,5 kg et couverture partielle de la toile. Fiche relue chez un revendeur, à confirmer chez le constructeur.
3. **Écarter le Lite 6** pour cette œuvre : portée de 440 mm et ±0,5 mm de répétabilité.
4. **SO-101** seulement pour mettre au point la chaîne logicielle (LeRobot, collecte d'épisodes), pas pour la tolérance.
5. UR5e et FR3 sont les plus confortables ; prix sur devis. À considérer si un laboratoire ou un intégrateur en prête un pour l'essai recommandé par STRATES.

Aucun achat avant G0 (fiche d'acceptation signée) et G1 (coupons mesurés). Une démonstration en simulation ne qualifie ni le dépôt de peinture ni l'accès réel.

## Prototype : `bojart_painter`

Python standard, sans dépendance ni GPU. Il ne pilote aucun robot.

```bash
python -m bojart_painter arms --output rapport-bras.json
python -m bojart_painter simulate --target synthetic:paysage --style reproduction aplats_geometriques --compare --save-ppm hors-git/
python -m bojart_painter simulate --target ppm:/chemin/oeuvre-domaine-public.ppm --style reproduction --until-converged --episodes hors-git/episodes.jsonl
python -m bojart_painter coupon --arm agilex_piper --trials 59
python -m bojart_painter hd --image /chemin/hors-git/oeuvre-domaine-public.jpg --style fin --strokes 16000 --save-png hors-git/
python -m unittest discover -s tests_painter -v
```

Boucle `simulate` (inspirée de FRIDA, sans son code) :

1. **Planifier** un lot de touches (Bézier, largeur, couleur) sur la dernière photo. Chaque touche est choisie parmi des candidates, tirées là où l'écart à la cible est grand, selon le modèle de dépôt supposé.
2. **Exécuter** sur une toile « physique » simulée, tenue à l'écart. Son modèle de dépôt est caché (largeur × 1,2, opacité 0,72). S'y ajoutent l'erreur de position du bras (répétabilité + recalage) et une erreur de teinte.
3. **Photographier** (bruit capteur). Isoler quatre touches par lot pour **recaler** largeur et opacité sur une grille.
4. **Replanifier** depuis la photo.

Une **manière de peindre** (`configs/painter/styles.json`) combine palette réduite (k-means sur la cible), plage de largeurs du gros au fin, longueur, orientation (contours, orthogonale, libre) et courbure. Ce sont des contraintes de gestes, pas l'imitation d'un artiste nommé.

Résultats (3 graines, 200 touches, toile 90 × 65 cm à 10 mm/pixel) :

- Le recalage retrouve le dépôt caché : gain 1,2 et opacité 0,70–0,75, dans tous les cas.
- Boucle fermée avec recalage contre plan unique en boucle ouverte : erreur plus basse 3/3 sur paysage/reproduction (−24 %), paysage/aplats et composition/aplats. Sur composition/reproduction, aucune différence nette (1/3).
- Le recalage pèse surtout sur les aplats larges et opaques ; pour des touches fines, la replanification compense déjà une bonne part de l'erreur.
- Avec un budget fixe de 200 touches, le style « touches courtes » s'arrêtait avant le ciel. L'option `--until-converged` continue désormais par lots tant qu'il reste de la toile vierge ou que l'erreur baisse d'au moins 2 % par lot (plafond `--max-strokes`). Sur le paysage, graine 1 : touches courtes 2 449 touches, 0 % de toile vierge, PSNR 34,1 dB, environ 2 h 38 de bras estimées ; reproduction 1 300 touches, PSNR 35,5 dB, environ 1 h 46. Rapport : `simulate-paysage-converge-seed1.json`.

## Rendu haute définition (`bojart_painter/hd.py`, numpy facultatif)

Les premiers rendus, à 10 mm par pixel avec 200 touches sur une cible en aplats, ressemblaient à une peinture d'enfant. C'était une limite de la démonstration, pas de la méthode. La version HD reprend la même boucle (monde caché, recalage, replanification par lots) à 2 mm par pixel, avec des pinceaux de 30 mm jusqu'à 2,5 mm, une orientation le long des contours et une texture de poils.

Essai sur *La Nuit étoilée* (1889, domaine public). L'image source est restée hors Git ; seule son empreinte figure dans le rapport. Avec 13 236 touches (PSNR 19,4 dB, contre 17,9 dB pour l'empâtement à 12 couleurs en 4 618 touches), le rendu reproduit composition, couleurs et tourbillons principaux, avec des touches visibles. Le recalage retrouve encore le dépôt caché (1,15 / 0,80 pour 1,15 / 0,82). Les tourbillons fins et le relief de l'empâtement d'origine ne sont pas atteints. Rapports : `hd-nuit-etoilee-*.json`.

À 1 mm par pixel avec des pinceaux jusqu'à 1,5 mm (`--style tres_fin`), 41 703 touches donnent PSNR 21,0 dB et SSIM 0,64 contre 19,4 dB et 0,44 pour la version à 13 236 touches, comparées sur la même grille. La fidélité monte encore à la fin de l'essai : aucun plateau n'est atteint, mais la durée de bras estimée passe à environ 28 h. Une copie qui trompe à 1–2 m paraît accessible avec une capture haute définition de l'original, l'étalonnage des mélanges et une peinture en couches ; le relief, la trajectoire exacte des touches et le vieillissement restent hors de portée, et une copie doit rester déclarée (domaine public, dimensions différentes, mention « d'après », sans la signature d'origine).

C'est le niveau visé pour une œuvre pilote de 90 × 56 cm : une réinterprétation à touches visibles, pas une copie indiscernable. La durée de bras est estimée à 6–9 h pour 10 000 à 13 000 touches, recharges comprises ; c'est une hypothèse de vitesse, pas une mesure.

Le rendu 3D du bras (modèle xArm 7 de MuJoCo Menagerie, toile réduite à 40 × 29 cm) a été produit hors du dépôt. Les modèles Menagerie gardent leur licence propre et ne sont pas versés ici.

## Après 2 à 3 semaines avec le matériel (projection)

Le bras n'« apprend » pas comme un modèle de langage. Les trois semaines servent surtout à mesurer le vrai dépôt (quelques centaines de touches photographiées), à recaler la toile et la caméra, et à fixer la recette : peinture, dilution, recharge, essuyage. Projection simulée (`--style atelier_3_semaines`, `hd-nuit-etoilee-atelier-3-semaines-seed1.json`) : 10 peintures pré-mélangées, pinceaux de 20, 8 puis 3 mm, toile de 50 × 31 cm, erreur de position 0,5 mm. Résultat : 5 032 touches, environ 3 h 30 de bras estimées, PSNR 17,7 dB et SSIM 0,29 à 1 mm. Le dépôt caché (1,25 / 0,75) est retrouvé.

| Semaine | Objectif réaliste |
|---|---|
| 1 | Montage, sécurité, recalage toile/caméra, bibliothèque de 200 à 500 touches mesurées ; aplats au gros pinceau. |
| 2 | Modèle de dépôt mesuré branché dans la boucle, photo et replanification ; petites toiles avec deux pinceaux. |
| 3 | Trois pinceaux, toile de 50 cm en une demi-journée, styles « reproduction » et « empâtement » ; coupon STRATES mesuré. |

Visuels associés (rendus hors dépôt, reproductibles) :

- **Semaine 1** : `bojart_painter/calibration.py` peint 30 touches de référence (3 pinceaux × 10 pots) sur un carton, puis les mesure sur une photo bruitée. La largeur ×1,25 du dépôt caché est retrouvée pour les pinceaux de 20 et 8 mm, et ×1,33 pour 3 mm à cause de la résolution de la photo (0,5 mm). La couverture au milieu de la touche vaut environ 0,54 : opacité × stries × charge restante. Rapport : `calibration-semaine1-seed1.json`.
- **Semaine 3** : `tools/render_painter_cell.py` rejoue, à l'identique, les touches exécutées par le peintre HD (`run(record=True)`) avec le modèle xArm 7 de MuJoCo Menagerie. La scène comprend une toile de 50 × 31 cm, 10 pots, trois pinceaux sur un support, un chiffon et une caméra sur potence. L'animation montre les recharges, l'essuyage et le changement de pinceau. Chaque lot est exécuté pinceau par pinceau puis pot par pot (`group_by_color=True`) : 93 changements de couleur au lieu de 4 371, pour un SSIM de 0,284 contre 0,287. Résultat : 5 189 touches, 903 recharges, environ 3 h 40 de bras estimées. La cinématique inverse atteint chaque point de la toile à moins de 0,9 mm (95 % sous 0,07 mm). Elle reste simplifiée (sans dynamique ni collisions) : c'est une illustration, pas une preuve d'accès. Rapport : `atelier-animation-seed1.json`.

Hors de portée en trois semaines : mélange automatique des couleurs, détails sous 2–3 mm, relief, toile de 90 cm sans surveillance, copie indiscernable.

## Limites

- Le monde « physique » est lui-même un modèle. Le recalage ne prouve que la logique de la boucle. La peinture réelle (charge du pinceau, séchage, mélange, relief) demande les mesures G1.
- Résolution de 10 mm/pixel pour la toile entière ; le coupon est modélisé par colonnes de 0,1 mm. Les deux échelles ne sont pas couplées.
- Accès calculé par sphère de portée, pas par la cinématique inverse du constructeur. Le contrôle suivant consiste à charger le modèle MuJoCo/URDF du bras retenu et à vérifier l'orientation du pinceau sur tout le trajet (G2).
- « À la perfection » n'est pas un critère mesurable. Il faut un seuil d'acceptation : écart couleur, débordement, durée, avis artistique.
- Reproduire une œuvre : uniquement le domaine public ou avec un accord écrit, et la copie doit rester identifiée comme reproduction. Aucune image d'œuvre n'est versée dans Git.

## Suite proposée

1. Brancher un backend MuJoCo (`mujoco` + modèle Menagerie ou URDF xArm 6) pour la cinématique inverse et l'accès réel, en option du prototype.
2. Remplacer le modèle de dépôt par des mesures de coupons G1 (réel → sim), puis comparer à la simulation différentiable de FRIDA.
3. Utiliser le journal d'épisodes JSONL pour entraîner une politique (LeRobot ou apprentissage par renforcement) seulement après que la recette programmée sert de référence, comme le prévoit l'audit STRATES.
