# Veille — « Un seul trait » (V1, proposition)

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

## Contrôles et limites

Décodage intégral réussi. −14,5 LUFS intégrés, −1,5 dBTP, LRA 7,1 LU. Transcription du mix : français détecté à 0,99, les deux phrases exactes. Coupes examinées image par image autour de 4,125 s et 10,67 s.

Limites connues : le trait du plan A s'interrompt sur la paupière alors qu'il est continu sur le plan large ; le plan B ouvre les yeux vers 1,5 s de clip, plus tôt que demandé (compensé par une pose de 1,5 s) ; le son est un bed synthétisé de travail, pas un design sonore final. Écoute casque et téléphone non réalisée. L'emblème BOJ.ART original doit remplacer le mot-symbole typographique du carton. Aucune publication, aucune mesure d'audience.
