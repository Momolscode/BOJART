# BOJ.ART — récupération du 1 novembre 2026, partie 3 sur 3

Cette branche conserve les **1 114 fichiers originaux** de
`BOJART_RECUPERATION_2026-11-01_PARTIE_3_SUR_3.zip`, soit **363 198 134 octets**
décompressés, à la demande explicite du propriétaire de `Momolscode/BOJART`.
Elle est une sauvegarde historique, séparée du code actif de Jarvis sur `main`.
Ne pas fusionner cette branche d'archive dans le runtime.

Les objets comprennent notamment **33 vidéos MP4, 3 bundles Git, 2 ZIP et 5 PDF**,
ainsi que code, images, audio, documents et sauvegardes. Les versions anciennes,
variantes et résultats rejetés sont conservés ; leur présence ne signifie pas
qu'ils constituent la version actuelle ou une réalisation validée.

## Télécharger et restaurer

Télécharger cette branche avec **Code → Download ZIP**, puis décompresser le ZIP
GitHub. Depuis le dossier contenant ce README, lancer :

```bash
python3 RECONSTRUIRE.py --verify-only
python3 RECONSTRUIRE.py --destination ../BOJART_PARTIE_3_RESTAUREE
```

Sous Windows, `python` peut remplacer `python3`. Décompresser dans un chemin court
(par exemple `C:\BOJART`) : certains chemins relatifs atteignent 194 caractères.
Le programme utilise uniquement la bibliothèque standard de Python 3.9 ou plus récent.
La destination doit être un dossier neuf,
hors du dossier source. Le programme refuse toute destination déjà existante,
vérifie les sources avant écriture, ne remplace aucun fichier et n'exécute ni ne
décompresse le code ou les archives récupérés. Une erreur produit un bilan JSON
avec `ok: false` et un code de sortie non nul.

Le résultat attendu est : **1 114 objets, 363 198 134 octets, 6 objets reconstitués
à partir de 23 fragments**. Les fichiers apparaissent dans
`BOJART_PARTIE_3_RESTAUREE/BOJART_RECUPERATION_2026-11-01/objets/` avec leurs chemins
et leurs octets d'origine. Le ZIP de transport initial n'est pas reconstruit :
ses 1 114 fichiers le sont. Il faut environ 364 Mo disponibles pour la destination,
en plus de la copie téléchargée.

L'option `--source /chemin/source` permet de lire les objets dans un autre dossier ;
le manifeste contrôlé reste celui livré à côté du programme.

## Stockage et intégrité

**1 108 fichiers sont directement disponibles. Six gros objets sont stockés en
23 fragments binaires ordonnés** de 8 Mio maximum, soit **1 131 fichiers physiques**.
Cette découpe permet leur transfert par le connecteur GitHub. Elle ne change pas
les octets restaurés. Parmi les 33 MP4, **32 sont directement lisibles et un est
reconstitué par le programme**. Les trois bundles Git, un ZIP et un autre fichier
binaire sont également reconstitués.

`MANIFESTE_PARTIE_3.json` contient les tailles et les empreintes SHA-256 et SHA-1
Git des originaux et des fragments, ainsi que leur ordre. Le programme épingle
l'identité exacte de ce manifeste et vérifie chaque fragment puis chaque original
assemblé. Les signatures de secrets connues restent contrôlées, y compris entre
deux fragments ; ce contrôle de motifs ne garantit pas l'absence de toute donnée
sensible dans un format compressé.

Le ZIP fourni fait **340 986 970 octets** et son SHA-256 est :

```text
6a23245cda664686f0d8dac40d49107032bd5f94a09a686edaa833ed39300b06
```

La comparaison au commit `ccb79a118e04c282bcd8cd1dc0fd514a9810ebeb` a identifié
**202 blobs déjà présents à l'identique**. Git réutilise ces contenus ; leurs
emplacements existants restent indiqués dans le manifeste. Les recouvrements
internes aux bundles et ZIP sont conservés afin de préserver les sources.

## Portée

Cette branche conserve **la partie 3 uniquement**. Elle ne certifie pas un export
intégral des conversations ni l'installation de Jarvis sur la tour de l'atelier.
La partie 3 ne contient pas le catalogue général des noms d'origine. Les
correspondances et la provenance sont décrites dans le
[catalogue de récupération sur main](https://github.com/Momolscode/BOJART/tree/main/data/catalog/recovery-2026-11-01).
La [partie 1](https://github.com/Momolscode/BOJART/tree/archive/recovery-2026-11-01-part-1)
dispose de sa propre branche de sauvegarde. La présence d'un index décrivant les
trois parties ne prouve pas à elle seule que leurs octets ont tous été transférés.
