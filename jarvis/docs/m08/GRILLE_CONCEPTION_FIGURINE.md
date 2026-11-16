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
- **Socle « basalte »** (Veille, fiche D16) : prisme hexagonal irrégulier, un sommet vers l'avant. Ses
  six côtés serrent les appuis au lieu d'un cercle : chacun passe à 10 mm au moins du point d'appui le
  plus avancé dans sa direction (plus 0 à 3 mm tirés avec une graine fixe). Biseau du dessus en facettes
  de pente 1,2 à 1,5, joint de colonne en V de 1 × 0,45 mm à flancs de 42°, chanfrein du dessous ;
  évidement polygonal à paroi de 3 mm. Imprimé retourné, sans support, comme le socle en strates.

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

## 8. Application à Veille (fiche D16)

Tailles à la hauteur de 200 mm : le maillage nominal est agrandi de 10 %, la tête encore de 14 %.

| Détail | Taille imprimée | Niveau |
|---|---|---|
| Sillons de peigne des cheveux | 0,9 × 0,6 mm | FDM |
| Ligne des cils (yeux clos) | 0,7 × 0,44 mm | résine (FDM limite) |
| Fente de la bouche | 0,8 × 0,4 mm | résine |
| Bandages des avant-bras, en hélice | relief 0,5 mm, pas de 4 mm | FDM limite |
| Bandes croisées sur le dos des mains | relief 0,55 mm | FDM limite |
| Mèches de la touffe du pinceau | 0,8 × 0,4 mm | résine (FDM limite) |
| Filet de la virole | 0,9 × 0,44 mm | FDM limite |
| Pointe de la touffe, hampe | Ø 1,8 mm, Ø 5,5 mm | FDM |
| Plis de la jupe et du pan du genou | 10 et 6 plis, 2,5 à 2,6 mm d'amplitude | FDM |
| Joint de colonne du socle | V de 1 × 0,45 mm, flancs à 42° | FDM limite |

Le trait carmin sur l'œil, signe du film, n'est pas sculpté : c'est de la peinture.

Constats de lisibilité propres à Veille :

- **Visage** : un devant de visage plat, large jusqu'aux tempes, puis une chute à pic vers l'oreille se
  lit comme un masque (arête de l'œil à la mâchoire). Retenu : masse du visage ovale, pommettes et joues
  orientées vers l'arrière, masse zygomatique entre la pommette et l'oreille, coin externe de l'œil en
  retrait.
- **Union douce** : là où deux surfaces se confondent (pan tombé du genou tangent à la rotule couverte),
  l'union douce gonfle la jonction d'un bourrelet. Retenu : union franche à cet endroit.
- **Bords fins** : un pli qui croise un bord coupé laisse une pointe ; une bande à arêtes vives finit en
  lame là où la surface qu'elle suit s'éloigne ; un sillon plus profond que la mèche laisse un éclat ;
  un drapé évasé finit en biseau au ras du socle. Retenu : plis effacés près des bords coupés, bande
  qui s'amincit en pente bornée (moins raide que l'étoffe, sinon elle recreuse un surplomb), sillons
  limités à 60 % de l'épaisseur de la mèche, ourlet d'aplomb sur les 1,5 derniers millimètres.
  Attention : décaler une intersection de champs (max) ne l'arrondit pas.
- **Contrôle** : 1 500 points tirés au hasard ne voient pas toujours une lame étroite. Pour une pièce
  aux bords fins, contre-vérifier sur 12 000 points avant de livrer.

## 9. Application à Fusain (fiche D17)

Tailles à la hauteur de 200 mm : le maillage nominal est agrandi de 14 %, la tête encore de 12 %.

| Détail | Taille imprimée | Niveau |
|---|---|---|
| Ruban du trait (épaisseur, largeur) | 3,0 à 4,1 mm, 6,6 à 17,7 mm | FDM |
| Stries de poils du trait | 0,6 à 0,7 × 0,3 à 0,6 mm, crêtes ≥ 0,8 mm | résine (FDM limite) |
| Strie des volutes de fumée | 0,45 × 0,34 mm | résine |
| Mèches des cheveux (larges et douces) | pas de 4,9 mm, relief 0,6 mm | FDM |
| Torsade du chignon | relief 0,75 mm | FDM limite |
| Barbe en collier, mèches du menton | 1,6 mm d'épaisseur, relief 0,4 mm | FDM, mèches résine |
| Fente de la bouche | 0,55 × 0,45 mm | résine |
| Col de la veste, ourlet d'emmanchure | 4,5 × 1,1 mm, 1,8 × 0,8 mm | FDM |
| Doigts de la main ouverte, serrés | Ø 2,6 à 2,7 mm, séparés par un pli | FDM (fragile) |
| Colonnes de basalte au pied du trait | 10 à 16 mm de large, 5,7 à 13,6 mm de haut | FDM |

Constats de lisibilité propres à Fusain :

- **Trait** : un ruban fait de boîtes successives montre des festons à chaque raccord. Retenu : ruban
  continu, balayé le long du chemin (point le plus proche, repère interpolé). Vu par la tranche, un
  ruban se lit comme un fouet : il reste dans le plan moyen de son chemin, face au spectateur. Des stries
  parallèles sur toute la longueur se lisent comme de la tôle ondulée : stries irrégulières et
  interrompues, plus profondes vers le haut. Des sillons qui se chevauchent creusent deux fois et percent
  le ruban : gravure en une seule passe (le sillon le plus proche décide), profondeur bornée à 30 % de la
  demi-épaisseur, une strie sur deux s'efface quand le trait s'affine (crêtes d'au moins 0,8 mm).
- **Fumée** : des boules en chapelet se lisent comme un tentacule, un petit crochet comme une crosse de
  fougère. Retenu : volute enroulée sur elle-même, le motif de nuage de la peinture à l'encre.
- **Vêtement** : une coque qui épouse le tronc ne se lit comme un vêtement que par ses bords. Retenu :
  emmanchures dégagées avec ourlet, col en bande qui fait le tour du cou ; seule, une bande en V se
  lisait comme un emblème. Une ceinture en ellipsoïde bombe en dôme : ceinture en couche qui épouse la
  taille.
- **Bords d'étoffe** : une coupe lue dans l'espace (cylindre autour du cou, ellipsoïde autour de
  l'épaule, distance au bras) passe par endroits presque parallèle à la couche et y laisse une lame :
  bord d'encolure autour de la bosse des trapèzes, ourlet en capuchon au-dessus du deltoïde, ourlet le
  long du bras couché dans le dos (lames de 0,05 à 0,4 mm au contrôle à 0,4 mm). Retenu : chaque coupe
  est lue au pied de la normale, sur le tronc (gradient par différences, quatre évaluations du tronc),
  ce qui extrude chaque bord d'équerre à travers la couche. L'étoffe porte sur le tronc sans le cou.
  L'étoffe ne doit pas toucher le bras : un bord qui bute contre lui ferme une poche creuse (élément
  flottant) ou une lame ; emmanchure à 4 mm du bras mesurés sur le tronc et bords d'au plus 3 mm de
  haut, il reste au moins 1 mm. La ceinture suit la même règle : coupée par deux plans dans l'espace,
  son arête haute faisait un coin de 67° là où la cage s'évase au-dessus de la taille (0,25 mm à la
  contre-vérification) ; lue au pied de la normale, l'arête passe à 81°.
- **Plis tuyaux** : des plis réglés par l'angle autour d'un axe convergent en étoile de lames là où
  l'axe ressort de la surface (axe de la cuisse prolongé sous un genou plié). Retenu : plis effacés à
  moins de 7 mm de l'axe.
- **Doigts** : une fente de 0,2 à 0,3 mm entre deux doigts ne s'imprime pas et se maille en voiles
  minces. Retenu : doigts serrés qui se touchent, séparés par un pli.
- **Bouts de bandage** : une bande coupée net qui dépasse de la pièce suivante (bande de 4 à 4,45 mm de
  rayon sur le raccord de 3,3 mm du poing) laisse un anneau à dents de scie : lèvre de 0,13 mm au
  contrôle local. Retenu : les deux derniers millimètres de la bande se resserrent en cône jusqu'au
  rayon du raccord. Chez Veille, les bouts sont cachés par la manche et la main.
- **Couches d'épaisseur variable (barbe, cheveux)** : une couche « champ moins e » dont l'épaisseur e
  grandit quand on s'éloigne de la surface se décolle en lame. Régler e sur une grandeur qui ne croît
  pas le long de la normale (distance à l'axe de la mâchoire, angle autour de la verticale) et l'annuler
  sur les bords. Seul, un ellipsoïde de cheveux remplit les creux des tempes : borner la couche à
  quelques millimètres du visage.
- **Grille** : à 2 mm, les doigts d'une main ouverte (Ø 2 à 2,4 mm) ne sont pas résolus et le contrôle
  d'épaisseur les signale à juste titre ; le parcours rapide de Fusain se teste à 1,5 mm.
- **Contrôle** : la première version a été refusée par la chaîne à 0,4 mm (0,27 % de la surface sous
  0,8 mm, minimum 0,05 mm). Un contrôle local par boîtes (maillage d'une région à 0,4 mm, 6 000 points)
  localise ces lames en une à deux minutes par région, avant de relancer la chaîne complète. Un
  défaut de quelques millimètres carrés passe entre les points : l'arête de ceinture est passée à
  travers les 1 500 points de la chaîne, la lèvre du bandage à travers les 12 000 de la
  contre-vérification. Avant de livrer : contrôle local dense de chaque région, avec une deuxième
  graine.

## 10. Limites

Auto-évaluation sur rendus argile : ni revue indépendante, ni impression. La sculpture procédurale
reste en dessous d'une sculpture numérique faite à la main ou d'une génération image→3D (tâche 2 du
backlog). Les valeurs FDM pour buse de 0,4 mm sont à confirmer sur un coupon imprimé.

## Sources

- [Proko : proportions idéalisées selon Loomis](https://proko.com/human-figure-proportions-idealistic-loomis)
- [Formlabs : Form 4 design guide](https://formlabs.com/white-papers/form-4-design-guide/)
- [Protolabs Network : éléments clés de conception pour l'impression 3D](https://www.hubs.com/knowledge-base/key-design-considerations-3d-printing/)
- [Protolabs Network : concevoir des pièces pour le FDM](https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/)
- [Proko : revue des sept plis](https://www.proko.com/lesson/a-review-of-the-7-folds)
