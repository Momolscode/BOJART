# BOJART — récupération, partie 2 sur 3

Cette branche conserve tous les contenus du fichier fourni
`BOJART_RECUPERATION_2026-11-01_PARTIE_2_SUR_3.zip`.

- 1 114 fichiers distincts, 363 198 124 octets décompressés.
- 193 contenus identiques réutilisés depuis les chemins existants du dépôt.
- 921 contenus ajoutés : 911 fichiers entiers et 10 fichiers découpés en 32 blocs.
- Les contrôles CRC du ZIP et les 1 114 empreintes SHA-256 sont valides.
- SHA-256 du ZIP source : `3c7fa81e053001df21138765c00f2424a50fd31e132fb5b56370908a514396a5`.

Les blocs de 8 Mio au maximum permettent le transfert par le connecteur GitHub,
limité à 16 Mio par requête. Le découpage ne modifie aucun octet du contenu.
`manifest.json` relie chaque chemin original aux fichiers ou blocs stockés.
Les originaux réutilisés sont inclus dans cette même branche ; aucun téléchargement
complémentaire ni accès à ChatGPT n'est nécessaire pour restaurer cette partie.

Depuis la racine du dépôt, avec Python 3.9 ou plus :

```sh
python recovery/2026-11-01/part02/restore.py --verify-only
python recovery/2026-11-01/part02/restore.py --destination ../BOJART_PARTIE_2_RESTAUREE
```

La destination doit être un nouveau dossier. Le programme vérifie toutes les
empreintes avant la restauration, reconstitue les chemins du ZIP, puis vérifie
également les octets écrits. Il n'exécute aucun programme récupéré.

Cette livraison concerne **uniquement la partie 2**. Son ZIP contient des objets,
sans le catalogue et l'index général de la collecte. Les parties 1 et 3 restent
nécessaires pour reconstituer la collecte complète et son catalogue.
Le conteneur ZIP lui-même n'est pas reproduit ; tous ses fichiers sont conservés.

Branche d'archive : `recovery/partie-2-2026-11-01`. Le code opérationnel de `main`
n'est pas modifié par cet import. Les fichiers récupérés sont des données
historiques : leur présence ne valide ni leur exécution ni leur qualité artistique.
La publication de cette archive a été demandée par l'utilisateur, y compris
sur le dépôt public. Elle ne modifie pas les règles générales de publication
des autres données du projet.
