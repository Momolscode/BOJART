# Grille de conception des figurines BOJ.ART (2 novembre 2026)

Olsen a jugé le niveau de détail insuffisant (« il faut accentuer les détails », « élargir tes données
sur la conception »). Cette grille fixe les règles mesurables que suit la sculpture procédurale, avec
leurs sources. Elle ne vaut que pour des personnages originaux : un personnage protégé n'est ni
sculpté ni rendu (fiche D2), même « plus détaillé ».

## 1. Proportions

| Repère | Valeur | Source |
|---|---|---|
| Hauteur d'une figure idéale | 8 têtes ou plus, contre 7,5 pour une figure réaliste | Loomis, *Figure Drawing for All It's Worth* (1943), résumé par Proko |
| Torse (homme) | une tête du menton aux mamelons, une jusqu'au nombril, une jusqu'à l'entrejambe | idem |
| Largeur d'épaules / de hanches (homme) | 2⅓ têtes / 1,5 tête | idem |

Application : Ardoise v5 mesurait 6,8 têtes (tête de 25 mm pour 170 mm). La v6 passe à 7,4 têtes
(tête de 22,8 mm). Elle reste volontairement sous 8 pour garder un visage lisible à 20 cm : c'est un
choix de BOJ.ART, pas une règle des sources.

## 2. Ordre de travail

Règle de travail de BOJ.ART (pas de source citée) : formes primaires (silhouette, masses, pose), puis
secondaires (muscles, plaques, plis), puis tertiaires (gravures, rivets, textures). Un détail
tertiaire ne corrige pas une masse fausse : on le juge sur une vue rapprochée, après les masses.

## 3. Taille minimale d'un détail imprimable

| Procédé | Valeurs publiées | Source |
|---|---|---|
| Résine SLA (Form 4, résine Grey, couches de 50 µm) | parois 0,2 mm ; relief 0,1 mm ; gravure 0,15 mm ; fil 0,3 mm pour 7 mm de haut, 0,6 mm pour 30 mm ; trou 0,5 mm ; jeu 0,4 mm | Formlabs, *Form 4 design guide* |
| FDM (réseau Protolabs) | paroi minimale 0,8 mm ; surplomb jusqu'à 45° sans support ; pont de moins de 5 mm sans affaissement ; tenon d'au moins 5 mm | Protolabs Network, deux pages de conseils FDM |
| FDM, buse 0,4 mm | pas de valeur unique : les guides de fabricants donnent un trait de 0,5 à 0,6 mm et un relief de 0,4 à 0,5 mm | recherche du 2 novembre 2026, sources hétérogènes, à confirmer sur coupon |

Règles retenues pour Jarvis :

- **Niveau FDM** : relief ou gravure d'au moins 0,8 mm de large et 0,5 mm de profondeur.
- **Niveau résine** : au moins 0,3 mm. Un détail plus fin que le niveau FDM peut s'effacer en FDM sans
  fragiliser la pièce ; le contrôle d'épaisseur reste inchangé (minimum 0,8 mm, 1er centile 1,2 mm).
- **Résolution de calcul** : une gravure de 0,8 mm demande au moins deux voxels sur sa largeur, donc
  une grille de 0,4 mm. Le lissage passe de 6 à 3 itérations : 6 itérations effaçaient les gravures.
- **Constat à vérifier** : le tenon de Ø 4 mm du socle est sous les 5 mm conseillés pour le FDM (celui
  de Ø 5 mm est à la limite). Rien n'est changé ici : le coupon de la tâche 3 du backlog tranchera.

## 4. Plis de tissu

Le dessin du drapé enseigne sept types de plis. La liste varie selon les auteurs : Proko cite le pli
tuyau, le losange, le demi-nœud, la spirale, la compression, le drapeau et le pli inerte ; d'autres
listes remplacent compression et drapeau par zigzag et chute. Application :

- **Manteau** : plis tuyaux (tissu suspendu à la ceinture, qui s'ouvrent vers le bas, 13 plis,
  1,8 mm d'amplitude à l'ourlet) et ourlet ondulé. L'épaisseur reste constante : les plis déplacent la
  coque au lieu de l'amincir.
- **Pantalon** : plis de compression en bourrelets au-dessus des bottes, deux sillons derrière le genou.

## 5. Lisibilité constatée sur les rendus

- **Paréidolie** : deux rivets côte à côte au-dessus d'une arête se lisent comme un visage (constaté
  deux fois sur les genouillères). Pas de paire symétrique de petits reliefs sur une plaque frontale ;
  préférer des strates horizontales.
- **Mains** : des doigts en anneaux autour d'un manche épais se lisent comme des bagues. Retenu : poing
  en bloc (environ 10 mm pour une tête de 23 mm), rangée de quatre jointures, sillons entre les
  doigts, pouce replié, et un manche aminci à 5,4 mm de diamètre.
- **Visage** : des orbites trop creuses donnent un regard « vide ». Retenu : globe presque à fleur du
  visage, paupière supérieure fine, arcades fondues.
- **Bords roulés et bourrelets** : une capsule s'étend d'un rayon de chaque côté de son segment. Un
  bord de brassard en capsule devient une boule (« bouée » sur l'avant-bras). Retenu : anneau plein à
  arêtes arrondies (`details.ring`) et brassard coupé net aux deux bouts.

## 6. Socle

Un socle de vitrine se lit avant la figurine. Retenu pour Ardoise : un socle « en strates », cinq
plaques d'ardoise empilées aux bords cassés (polygones de 17 à 19 sommets tirés avec une graine fixe,
± 0,7 mm), 0,8 mm plus larges à chaque plaque vers le bas, et une strie de clivage en V.

- **Impression** : le socle évidé s'imprime retourné, dessus sur le plateau. Tout élargissement vers le
  bas est donc un chanfrein, plus raide que 45° (pente 1,15) ; une plaque qui déborde de celle du
  dessous devient une contre-dépouille tournée vers le haut à l'impression ; les flancs des stries
  sont à 42°. Aucun support.
- **Dessus plat** : c'est le plan de joint des semelles, posé sur le plateau. La marge autour des
  pieds reste d'au moins 7 mm (mesurée à chaque exécution, `assembly.json`).
- **Socle lisse** : le cylindre chanfreiné reste celui de la Sentinelle et des maillages importés.

## 7. Application à Ardoise v6

| Détail | Taille | Niveau |
|---|---|---|
| Rivets (cuirasse, épaulière, brassards, ceinture) | Ø 1,6 à 1,7 mm, relief 0,8 mm | FDM |
| Filets gravés des plaques d'épaulière | 0,84 × 0,5 mm | FDM limite |
| Gouttière de la lame | 2,2 × 0,7 mm sur chaque face | FDM |
| Sillons entre les doigts | 0,72 × 0,65 mm | FDM limite |
| Cicatrice du sourcil, strates gravées de la tempe | 0,8 à 0,84 × 0,4 à 0,45 mm | résine (FDM limite) |
| Ligne de la bouche | 0,5 × 0,45 mm | résine |
| Gainage de la poignée | relief de 0,3 mm | résine |
| Plis du manteau | 13 plis, 1,8 mm d'amplitude | FDM |
| Pouce et jointures | pouce Ø 2,6 à 4 mm, jointures Ø 2,9 mm | FDM |
| Bords roulés des brassards | 1,2 mm de large, relief 0,55 mm | FDM |
| Bourrelets du pantalon au-dessus des bottes | 1,1 mm de haut, relief 0,6 mm, sillons de 0,7 mm | FDM limite |
| Strates du socle | marches de 0,8 mm ± 0,7 mm, strie en V de 1 × 0,45 mm | FDM (strie : limite) |

## 8. Limites

Auto-évaluation sur rendus argile : ni revue indépendante, ni impression. La sculpture procédurale
reste en dessous d'une sculpture numérique faite à la main ou d'une génération image→3D (tâche 2 du
backlog). Les valeurs FDM pour buse de 0,4 mm sont à confirmer sur un coupon imprimé.

## Sources

- [Proko : proportions idéalisées selon Loomis](https://proko.com/human-figure-proportions-idealistic-loomis)
- [Formlabs : Form 4 design guide](https://formlabs.com/white-papers/form-4-design-guide/)
- [Protolabs Network : éléments clés de conception pour l'impression 3D](https://www.hubs.com/knowledge-base/key-design-considerations-3d-printing/)
- [Protolabs Network : concevoir des pièces pour le FDM](https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/)
- [Proko : revue des sept plis](https://www.proko.com/lesson/a-review-of-the-7-folds)
