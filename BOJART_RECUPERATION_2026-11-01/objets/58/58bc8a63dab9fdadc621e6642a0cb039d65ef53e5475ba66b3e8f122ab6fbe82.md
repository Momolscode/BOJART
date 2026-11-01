# BOJ.ART — lecture vidéo, références et skills

Audit réalisé le **18 octobre 2026**. Cette note distingue l’acquisition d’une vidéo, son analyse et la fabrication d’un nouveau montage. Les trois dépôts ci-dessous ont été consultés en lecture seule : **aucun de leurs scripts n’a été installé ni exécuté pour cet audit**.

## Décision

Retenir **claude-real-video** comme candidat pour préparer les originaux à une analyse multimodale, et **iart-ai/tiktok-video-skills** comme référence de réalisation pour les futurs montages. FlowExtract reste un connecteur d’acquisition possible ; la collection déjà archivée ne nécessite pas un nouveau téléchargement complet.

Un skill ne constitue pas à lui seul un modèle de vision. Le pipeline extrait des images et du texte ; l’agent qui les examine produit l’analyse. Pour une chaîne entièrement locale, ce dernier doit également utiliser un modèle multimodal local.

## 1. FlowExtractAPI/tiktok-video-downloader

- Dépôt : <https://github.com/FlowExtractAPI/tiktok-video-downloader>
- Révision consultée : `0f42366894a4e35bb56d4f88b5b7a1fce399043b`.
- README conservé comme référence : <https://github.com/FlowExtractAPI/tiktok-video-downloader/blob/0f42366894a4e35bb56d4f88b5b7a1fce399043b/README.md>

L’arbre public consulté contient seulement `README.md` et une image d’exemple. Il ne fournit ni le moteur de scraping, ni un `SKILL.md`, ni un fichier `LICENSE`. Ce dépôt documente un Actor Apify ; sa présence sur GitHub ne suffit donc pas à en faire un collecteur open source réutilisable localement.

L’Actor récupère des métadonnées publiques, des pistes de sous-titres déjà générées par TikTok et, en option, un MP4. Il ne retranscrit pas les vidéos dépourvues de piste native et n’analyse pas leurs images. Les adresses CDN directes expirent. Le téléchargement optionnel utilise un second Actor, facturé séparément en plus des événements du premier.

L’intégration par API exige un compte et un jeton **Apify**. Le texte « no API key » du README ne signifie pas que l’automatisation Apify est anonyme ou gratuite. La facturation comprend notamment le démarrage, le résultat, la transcription effectivement récupérée et le téléchargement activé. Les tarifs doivent être relus au moment d’un raccordement.

Sources du service : [fonctionnement](https://apify.com/dz_omar/tiktok-video-downloader), [API](https://apify.com/dz_omar/tiktok-video-downloader/api), [tarifs](https://apify.com/dz_omar/tiktok-video-downloader/pricing).

## 2. iart-ai/tiktok-video-skills

- Dépôt : <https://github.com/iart-ai/tiktok-video-skills>
- Révision consultée : `2a775336b5a638cbf8a61dbd785f9a1b649be016`.
- Licence : [MIT](https://github.com/iart-ai/tiktok-video-skills/blob/2a775336b5a638cbf8a61dbd785f9a1b649be016/LICENSE).
- Instructions : [short-form-video/SKILL.md](https://github.com/iart-ai/tiktok-video-skills/blob/2a775336b5a638cbf8a61dbd785f9a1b649be016/skills/short-form-video/SKILL.md), [caption-animation/SKILL.md](https://github.com/iart-ai/tiktok-video-skills/blob/2a775336b5a638cbf8a61dbd785f9a1b649be016/skills/caption-animation/SKILL.md).

Le pack fournit quatre skills : construction d’un format court, sous-titres animés, compte à rebours et titres animés. Il aide à écrire et fabriquer une vidéo, sans effectuer une lecture multimodale de références existantes.

Les exemples reposent sur Remotion ou CSS. Pour les sous-titres, ils proposent une transcription Whisper locale ou AssemblyAI, service distant. Les helpers utilisent FFmpeg/FFprobe ; `seek-shot.sh` lance Playwright par `npx`. Aucun service iart obligatoire n’a été identifié dans les fichiers audités. Les dépendances et leurs licences restent à vérifier pour le mode de production effectivement retenu.

Points à adapter avant réutilisation : les statistiques de rétention du skill ne comportent pas de sources ; elles ne sont pas des garanties de performance. Certains exemples CSS séparent le nombre de son unité (`.26 s`, `.18 em`), ce qui doit être corrigé. Le modèle Whisper `medium.en` cité dans les instructions de captions ne convient pas au français. Les valeurs de cadrage et le style de sous-titres doivent être adaptés aux vidéos BOJ.ART, puis vérifiés dans le rendu final.

Les outils de capture fournis ne remplacent pas le protocole de vérification autorisé du Site. Aucun lancement de Playwright ne découle de cet audit.

## 3. claude-real-video — candidat retenu pour la lecture

- Dépôt : <https://github.com/HUANGCHIHHUNGLeo/claude-real-video>
- Révision consultée : `ab4b9b2b23790f5d63a6d15165d3d8ba284c6023`.
- Version déclarée dans `pyproject.toml` : **0.10.7**.
- Licence : [MIT](https://github.com/HUANGCHIHHUNGLeo/claude-real-video/blob/ab4b9b2b23790f5d63a6d15165d3d8ba284c6023/LICENSE).
- Skill retenu : [skills/claude-real-video/SKILL.md](https://github.com/HUANGCHIHHUNGLeo/claude-real-video/blob/ab4b9b2b23790f5d63a6d15165d3d8ba284c6023/skills/claude-real-video/SKILL.md).
- Dépendances : [pyproject.toml](https://github.com/HUANGCHIHHUNGLeo/claude-real-video/blob/ab4b9b2b23790f5d63a6d15165d3d8ba284c6023/pyproject.toml).
- Pipeline inspecté statiquement : [core.py](https://github.com/HUANGCHIHHUNGLeo/claude-real-video/blob/ab4b9b2b23790f5d63a6d15165d3d8ba284c6023/src/claude_real_video/core.py).

Le cœur libre prépare des images sélectionnées par changement de scène et couverture temporelle, les dédoublonne et conserve une correspondance avec les timecodes source dans `frames.json`. Il utilise les sous-titres disponibles ou une transcription locale. Il produit notamment les images, les transcriptions, des planches en option et `MANIFEST.txt`, que l’agent examine pour répondre avec des preuves visuelles et textuelles.

Il nécessite Python 3.10 ou plus, FFmpeg/FFprobe, Pillow et yt-dlp. Les moteurs de transcription sont des dépendances optionnelles : Whisper, faster-whisper, ou une variante MLX pour les machines compatibles. Les modèles peuvent nécessiter un téléchargement initial. La préparation de fichiers locaux n’exige pas de clé d’API ; si les images et le texte sont ensuite remis à un modèle distant, ces éléments partent chez son fournisseur.

Le cœur MIT gratuit est distinct de **crv Pro**, une offre payante. Ne pas attribuer au cœur libre les fonctions avancées de mesure des mouvements de caméra, de rythme ou d’émotion annoncées pour Pro.

Limites de fidélité : un budget d’images trop faible ou un dédoublonnage agressif peut perdre un mouvement bref. La suppression des plans répétés est utile pour lire un contenu, mais fausse une mesure directe de son rythme de montage. Les scènes importantes doivent être inspectées plus finement et les timecodes des coupes conservés séparément. La détection de parole réduit les erreurs sur la musique et le silence sans garantir une transcription parfaite.

## Collection BOJ.ART déjà disponible

Le manifeste local `tmp/bojart-archive/BOJ_ART_Archive_TikTok/manifest.json`, relatif à la racine de travail de cette session, et le `README_FR.md` de cette même archive indiquent :

| Élément | Couverture vérifiée dans l’archive |
|---|---:|
| Publications publiques identifiées | 31 |
| Vidéos identifiées | 30 |
| Vidéos MP4 archivées, avec piste audio | 29 |
| Vidéo dont le média demeure indisponible | 1 |
| Publication photo | 1 carrousel, 7 photos |
| Couvertures | 31 |
| Pistes VTT natives | 4 pistes sur 2 vidéos |
| Durée cumulée des MP4 | 818,66 secondes environ |

Les quatre pistes sont le français ASR et sa traduction anglaise fournis par TikTok pour deux vidéos. Elles ne représentent ni quatre vidéos transcrites, ni une transcription humaine validée. Aucune transcription nouvelle n’a été réalisée lors de cet audit.

La vidéo manquante conserve son entrée, sa couverture et ses métadonnées ; l’archive ne prétend pas posséder son fichier. La collecte porte sur les publications publiques observées, et non sur les contenus privés, les brouillons, les lives ou les rushes caméra. Les fichiers archivés sont des versions de diffusion TikTok.

## Workflow de fidélité BOJ.ART

1. **Conserver les originaux.** Utiliser les MP4 existants, leur identifiant de publication, leur URL canonique et leur empreinte. Produire les analyses dans un dossier distinct par vidéo et par révision ; ne jamais mélanger deux sources dans le même dossier de sortie.
2. **Préparer les preuves.** Vérifier le décodage, extraire des scènes et des images horodatées, conserver l’audio. Réutiliser les VTT français disponibles ; ne transcrire que les séquences parlées qui le nécessitent. Distinguer explicitement « pas de parole », « transcription indisponible » et « erreur de traitement ».
3. **Lire le visuel et le son ensemble.** Examiner les planches chronologiques puis les images individuelles pour les cadrages, la lumière, les matériaux, la peinture et la typographie. Revenir au clip complet lorsque le rythme ou un geste ne peut pas être établi à partir des images retenues.
4. **Documenter la signature.** Relier chaque observation à une vidéo et à un intervalle précis. Distinguer les caractéristiques effectivement observées des choix proposés pour l’interface : une couleur d’accent ou une durée de transition choisie pour le dashboard ne doit pas être présentée comme une mesure historique du compte.
5. **Décliner avec cohérence.** Transmettre cette référence aux templates de montage, aux titres et aux trois écrans. Les recettes générales d’iart restent subordonnées à la signature BOJ.ART et au rôle de chaque vue.
6. **Vérifier chaque résultat.** Contrôler les images clés, le son et le fichier exporté avec les vraies sources et les vrais paramètres. Conserver la provenance, les timecodes utilisés, la version des outils, les limites d’échantillonnage et les corrections apportées.

## État de raccordement

Cet audit établit un choix de composants et une méthode de travail. **Il ne constitue ni une installation de ces skills, ni une analyse terminée des 29 vidéos par ces outils, ni un raccordement de modèle local ou d’API.** Le Site dispose de médias issus de l’archive ; ce document ne change pas leurs droits d’accès ni les connexions externes.
