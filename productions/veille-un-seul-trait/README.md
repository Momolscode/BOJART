# Veille — « Un seul trait » (V1.1 prête à poster)

**Coupe de travail du 2 novembre 2026 : 13,67 s, 328 images, 24 i/s, 1080 × 1920.** Premier film de la direction V.02 : un pinceau pose un trait carmin sur le visage d'une sculpture, puis la pièce ouvre les yeux. Signature : « Chaque pièce porte un geste. »

Veille est un **personnage original** créé pour BOJ.ART. Aucun élément n'emprunte à un personnage existant. Les images et vidéos sont des générations IA présentées comme concept ; elles ne décrivent pas une pièce réellement fabriquée.

## Règles V.02 appliquées

- Le carmin `#F13A54` n'existe que dans le geste ; tout le reste est charbon `#09090D`, ivoire et matière.
- Une seule lumière rasante, un seul événement physique par plan.
- Chaque plan vidéo est contraint par deux images-clés contrôlées (début et fin), dérivées d'une seule image de référence.
- Typographie (Barlow Condensed, Manrope) posée au montage, jamais générée.
- Toute voix est vérifiée par transcription avant montage.

## Fichiers

- [RECETTE.json](RECETTE.json) : modèles, prompts, rejets motivés, coupes, contrôles et crédits dépensés.
- `cards.py` : carton final, sous-titres et couverture titrée.
- `sound.py` : bed sonore original synthétisé (nappe, pinceau, montée, impact).
- `edit.sh` : montage FFmpeg complet, mixage voix et normalisation −14 LUFS.

Les médias (images, clips, voix, master) restent hors du dépôt, conformément à [SECURITY.md](../../SECURITY.md).

## Reproduire

Prérequis : Python 3 avec Pillow et NumPy, FFmpeg avec libx264, polices Barlow Condensed SemiBold et Manrope (Google Fonts, licence OFL).

1. Dossier de travail `W` contenant `lot/` (clips `shotA.mp4`, `shotB.mp4`, `cover.png`, voix) et `build/` (ces scripts) ; polices dans `W/fonts/`.
2. `python3 build/cards.py W/fonts W/build`
3. `bash build/edit.sh W [chemin_voix]`

Le script écrit `build/BOJART_Veille_UnSeulTrait_V1.mp4`.

## V1.1 prête à poster

**12,67 s, 304 images.** Mêmes plans et même son que la V1, habillage refait pour la publication en Reel, TikTok et Short :

- tous les textes dans la zone visible commune aux trois réseaux (x 120–888, y 288–1248, x ≤ 780 sous y 840) ;
- mention « Généré par IA » incrustée de la première à la dernière image (AI Act, art. 50(4), applicable depuis le 2 août 2026) ;
- accroche « Un seul trait. » dès la première image, carton ramené à 2 s avec le pied « Veille · concept original / pas encore sculptée » ;
- calques convertis en BT.709 et fichier étiqueté BT.709 (le carmin du carton V1 virait à l'orange sur téléphone) ;
- intermédiaires sans perte, GOP fermé de 12 images, moov en tête.

Reproduire : `python3 build/cards_v11.py W/fonts W/build`, puis `bash build/edit_v11.sh W [chemin_voix]`. Le script écrit `build/BOJART_Veille_UnSeulTrait_V1-1.mp4` et `cards_v11.py` écrit `v11_layout.json`, qui sert à vérifier que chaque texte reste dans la zone visible.

Contrôles : décodage intégral OK, −14,5 LUFS, −1,4 dBTP, LRA 7,2 LU ; transcription fr 0,99, phrases exactes ; aucun texte hors zone ; contraste au pire sur les 10 % de fond les plus clairs : mention 6,4:1, accroche 3,1:1, phrase 2 13,6:1. Les obligations de publication (réglages IA par plateforme, première ligne de légende) sont dans [RECETTE.json](RECETTE.json), clé `v1_1.publication`.

## Contrôles et limites

Décodage intégral réussi. −14,5 LUFS intégrés, −1,5 dBTP, LRA 7,1 LU. Transcription du mix : français détecté à 0,99, les deux phrases exactes. Coupes examinées image par image autour de 4,125 s et 10,67 s.

Limites connues : le trait du plan A s'interrompt sur la paupière alors qu'il est continu sur le plan large ; le plan B ouvre les yeux vers 1,5 s de clip, plus tôt que demandé (compensé par une pose de 1,5 s) ; le son est un bed synthétisé de travail, pas un design sonore final. Écoute casque et téléphone non réalisée. L'emblème BOJ.ART original doit remplacer le mot-symbole typographique du carton. Aucune publication, aucune mesure d'audience.
