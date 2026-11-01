# Reprise vérifiée du transfert BOJ.ART — 1 novembre 2026

**Les 3 340 contenus uniques de la collecte sont présents sur GitHub et ont été restaurés depuis ses trois branches d'archive.** Les fichiers restaurés ont ensuite été comparés octet par octet aux trois ZIP d'origine : aucune différence. La collection représente 1 089 594 390 octets, 219 sources et 6 445 emplacements documentés.

La reprise de la mission interrompue n'a pas réenvoyé ces médias. Elle relie les trois sauvegardes, ajoute un restaurateur commun et corrige le contrôle du dépôt devenu incompatible avec l'archive binaire déjà fusionnée par la PR #3.

| Partie | Révision vérifiée | Contenu restaurable |
|---|---|---|
| 1 | [635116df](https://github.com/Momolscode/BOJART/tree/635116df515f7910c5bc854176b642e282efbfb3) | 1 112 objets et 8 fichiers de catalogue ; ZIP exact reconstitué depuis 40 blocs |
| 2 | [2d2e01e3](https://github.com/Momolscode/BOJART/tree/2d2e01e3576e0a655729f6d273e9038e109f915a) | 1 114 objets ; contenus exacts, avec réutilisation des fichiers identiques |
| 3 | [6e743b8a](https://github.com/Momolscode/BOJART/tree/6e743b8a8ba90b6ab24a579a1f8c5aebaa8ba967) | 1 114 objets ; contenus exacts, dont les gros fichiers découpés |

Les 87 fichiers du paquet `BOJART_MARWIN_PRET_GITHUB_2026-11-01.zip` et les 22 textes de la file de transfert interrompue sont tous dans cette collection, avec les mêmes empreintes. Le [rapport de contrôle](evidence/recovery-resumption-2026-11-01.json) relie chaque texte à sa partie et à son objet. Les noms d'origine se retrouvent dans `INDEX.json` et `CATALOGUE.html`.

## Restaurer toute la collecte

Depuis un clone à jour de `Momolscode/BOJART`, avec Git et Python 3.9 ou plus :

```sh
python tools/restore_recovery_2026_11_01.py --fetch --destination ../BOJART_RECUPERE
```

Choisir une destination qui n'existe pas et prévoir environ 2 Go libres pendant la restauration, en plus du dépôt Git. La commande télécharge seulement les commits d'archive manquants. Elle ne change pas la branche active, ne fusionne pas les archives et n'exécute aucun programme historique. Le téléchargement initial peut prendre du temps, sans affichage de progression détaillé.

Elle vérifie les octets Git, les tailles, les SHA-256, le CRC du ZIP reconstitué et les liens du catalogue. Le dossier final n'est créé qu'après validation. Ouvrir ensuite :

```text
BOJART_RECUPERE/BOJART_RECUPERATION_2026-11-01/CATALOGUE.html
```

La collection contient Jarvis M01–M07, les sources et historiques des sites, les audits, dashboards, documents de direction et médias récupérés. Elle garde les versions historiques et rejetées, sans les substituer au logiciel courant.

## Portée exacte

- Les 3 340 contenus de cette collecte sont vérifiés ; cela ne certifie pas un export mot pour mot de toutes les conversations ChatGPT.
- Les fichiers qui n'existent que sur le PC de l'atelier ne sont pas couverts.
- L'archive TikTok d'origine signale toujours une vidéo manquante : `7099716894994730246`.
- L'installation matérielle, les commandes vocales réelles, les imprimantes et l'approbation artistique restent à vérifier séparément.

Les notes historiques annonçant « médias externes » décrivent l'état avant les envois des parties. Cette page et sa preuve constituent le constat actuel de présence sur GitHub. La petite archive sous `archive/2026-11-01/` conserve son périmètre propre ; elle n'est pas la sauvegarde globale.
