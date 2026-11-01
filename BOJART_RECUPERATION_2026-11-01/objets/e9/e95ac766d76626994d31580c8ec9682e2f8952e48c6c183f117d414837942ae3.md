# BOJ.ART — Baki, du détail à l’œuvre

Recette du premier édit de signature : **22,7 s, 720 × 1280, 30 i/s, sans audio**. Huit plans suivent le détail, le geste, l’œuvre et l’emblème original. Les deux publications concernent le même projet Baki annoncé comme une figurine de 60 cm.

## Entrées

Le rendu lit une archive **déjà extraite**. Aucun téléchargement ni appel réseau n’est prévu.

| Fichier sous le dossier d’archive | SHA-256 attendu |
|---|---|
| `posts/7467517355535404310/video.mp4` | `27f922de227cd93c79ba5ca11f3adf9c08d883436ed27590d0abae2936ac44e8` |
| `posts/7464268707989114134/video.mp4` | `9ca3bd55f02e5841a1f8fba53adef40b4bd5c13954c6f8ff615dfe6ab3d56bf4` |

Le script refuse une source dont le hash diffère. Il faut Python 3, `ffmpeg`, `ffprobe`, et les polices `display.ttf` et `body.ttf` présentes dans le dossier d’assets. Le master de référence a été produit avec FFmpeg 6.1.1 ; des versions d’encodeur différentes peuvent produire des octets différents.

## Reproduire

Depuis la racine du dépôt, en adaptant les deux dossiers d’archive et d’export :

```bash
python3 creative/brand-film-v1/render.py \
  --archive-root ./archives/BOJ_ART_Archive_TikTok \
  --output-dir ./exports/brand-film-v1 \
  --assets-dir ./dist/assets
```

Les trois destinations sont des arguments explicites. Le dossier `--assets-dir` fournit les polices et reçoit une copie du master, le preview, le poster et les quatre images de contrôle. **Les fichiers du rendu portant les mêmes noms sont remplacés** : pour conserver toutes les sorties d’une version précédente, utiliser de nouveaux dossiers d’export et d’assets, avec les deux polices dans ce dernier. Aucun rendu n’est lancé par `--help`.

## Contenu conservé

- `render.py` : script de rendu, vérification des sources et décodage du master.
- `recipe.json` : coupes, sources, hashes, chapitres et résultats de contrôle du master validé.
- `filter.ffmpeg` : filtre du master sous forme de modèle portable ; `{assets_dir}` représente l’argument du même nom. Le script génère le filtre résolu dans le dossier de sortie.

Le master `BOJ_ART_Edit_Signature_v1.mp4`, la recette complète et le filtre résolu sont conservés dans `--output-dir`. Après son décodage de contrôle réussi, le master est aussi copié sous `--assets-dir/brand-film-master.mp4`, le nom utilisé par le Studio.

Le dossier d’assets reçoit également `brand-film-preview.mp4`, le poster, les quatre images de contrôle et le manifeste public `brand-film-sources.json`. Ce manifeste désigne `brand-film-master.mp4`, donne `BOJ_ART_Edit_Signature_v1.mp4` comme nom de téléchargement, et omet la commande FFmpeg ainsi que le chemin du filtre. La recette complète avec la commande de reproduction reste dans le dossier d’export.

## Décisions de montage

Les plans verticaux gardent leur cadre et leurs proportions. Pour la peinture, seul le bandeau horizontal est extrait à **x=0, y=662, 576 × 324 px**, puis affiché à **640 × 360 px**. Le geste reste entier ; l’original archivé conserve son ancien habillage. Deux fondus courts relient les chapitres, et le logo original termine le film. Les couleurs et la vitesse des images sources sont conservées.

Les résultats visuels inscrits dans `recipe.json` concernent le master déjà validé. Après un nouveau rendu, examiner les quatre images, les raccords et le film à vitesse réelle avant d’utiliser cette nouvelle version.
