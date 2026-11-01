# BOJART — récupération du 1 novembre 2026, partie 1 sur 3

Cette branche d’archive conserve **intégralement et sans modification** le ZIP fourni par l’utilisateur : `BOJART_RECUPERATION_2026-11-01_PARTIE_1_SUR_3.zip`.

- Taille exacte : **331 492 004 octets**.
- SHA-256 : `9f0544b915ebcd34482a0ff33076eb0ae25dfe333c9493b746f15a183c61fc8f`.
- 40 blocs binaires de 8 Mio au maximum, sans conversion des données.
- 1 112 objets récupérés et 8 fichiers de catalogue, index et restauration dans le ZIP.
- 1 112 empreintes d’objets vérifiées, aucune divergence ; contrôle CRC réussi à la lecture.
- 204 objets possédaient déjà une copie identique dans `main` au commit `1d76c6876de54c7bc37b777ae66bf031207a140d` ; la sauvegarde conserve le ZIP original plutôt que de modifier ses octets.

**Cette branche sert à la sauvegarde. Le logiciel actuel reste sur [main](https://github.com/Momolscode/BOJART/tree/main).** Les parties 2 et 3 ne sont pas incluses dans cette opération. Les métadonnées internes du ZIP décrivent aussi des objets de ces deux autres parties ; leur présence dans l’index ne signifie pas que leurs fichiers sont dans la partie 1.

## Récupérer le ZIP original

1. Sur cette branche, choisir **Code → Download ZIP**, puis extraire le téléchargement.
2. Ouvrir un terminal dans le dossier extrait et lancer avec Python 3.9 ou plus :

```sh
python RECONSTRUIRE.py
```

Le fichier original est reconstruit à côté du script. Chaque bloc puis l’archive complète sont vérifiés par SHA-256. Un fichier déjà présent n’est jamais écrasé. Le script ne lance aucun programme contenu dans l’archive et ne contacte aucun service.

Vérification seule, sans reconstruire le fichier :

```sh
python RECONSTRUIRE.py --verify
```

Après reconstruction, le ZIP s’extrait normalement. Pour réunir toute la collection, il faudra également extraire les parties 2 et 3 dans le même dossier de récupération. Les rendus, essais et anciens états restent historiques ; leur archivage n’atteste pas du fonctionnement des imprimantes ni de la validation artistique.

`MANIFESTE.json` donne les tailles et empreintes exactes des blocs. `CONTENU_PARTIE_1.json` inventorie les 1 112 objets réellement présents dans cette partie. L’index complet d’origine, les noms et la provenance sont conservés dans le ZIP.
