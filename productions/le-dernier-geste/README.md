# Le dernier geste — R03

**Coupe de travail du 1 novembre 2026 : 9,25 s, 222 images, 24 i/s, 720 × 1280.** Le film associe la matière peinte, un geste de pinceau, un mouvement contenu de la figurine, une révélation réelle dans l’atelier et l’emblème original.

Le pinceau termine son trait ; la coupe donne ensuite l’impression que l’œuvre répond. Le raccord peinture/cicatrice est une fiction de montage, pas la captation documentaire d’un geste réellement filmé sur cette sculpture.

## Ce qui a été produit

- G1 : macro de pinceau terminée, paramètres dans [G1_PARAMETRES.json](R02_LE_DERNIER_GESTE/G1_PARAMETRES.json). Le trait est plus large que prévu ; le raccord exact à la cicatrice reste à améliorer.
- R03 : montage du G1 existant, du TEST19 historique, des prises authentiques et de la signature. La fin tardive de TEST19, où le visage sortait du cadre, est remplacée par un détail continu du poing qui se ferme.
- Son : composition V21 rééditée et Foley de pinceau BenDrain. Source et licence déclarée dans [FOLEY_PROVENANCE.json](R02_LE_DERNIER_GESTE/FOLEY_PROVENANCE.json).

Le [plan G2 définitif](STATUT_G2.json) reste à produire. TEST19 est un ancien essai utilisé pour la prévisualisation, pas une nouvelle génération R03. R01 et R02 sont conservées dans le paquet privé complet.

## Reproduire le montage

Prérequis : Python 3 et FFmpeg avec libx264. Aucun appel à une API de génération n’est effectué par le script de montage.

1. Récupérer le paquet complet privé du projet auprès de son responsable.
2. Décompresser ses médias dans ce dossier en conservant les chemins de [ASSETS.json](ASSETS.json).
3. Vérifier les cinq sources : `python3 verify_assets.py`.
4. Lancer `python3 R03_LE_DERNIER_GESTE/build_dernier_geste_r03.py`.

Le script écrit `R03_LE_DERNIER_GESTE/BOJART_LE_DERNIER_GESTE_R03.mp4`. Les options `--legacy CHEMIN` et `--r02 CHEMIN` permettent d’indiquer d’autres emplacements de médias. Les durées, cadrages et couches audio figurent dans [EDL_R03.json](R03_LE_DERNIER_GESTE/EDL_R03.json).

## Vérifications et limites

Décodage intégral réussi ; neuf images générales et quatre images autour de chacune des six coupes examinées. Mesures audio : −15,18 LUFS intégrés, −1,49 dBTP. Ces contrôles ne valent pas validation artistique finale. Écoute casque/téléphone encore à réaliser ; aucun résultat d’audience établi. Détails dans [REVUE_R03.json](R03_LE_DERNIER_GESTE/REVUE_R03.json).

Les sources réelles proviennent d’une vidéo de diffusion de 512 pixels de large. Leur export en 720p ne reconstitue pas les détails absents ; le détail du poing est lui aussi agrandi.

Le dépôt suit [SECURITY.md](../../SECURITY.md) : les MP4, archives et journaux de session restent dans le stockage privé. Ce dossier contient la recette de montage, les paramètres utiles et les preuves techniques publiables.
