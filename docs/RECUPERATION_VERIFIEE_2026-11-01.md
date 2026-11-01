# Récupération vérifiée — 1 novembre 2026

Le dépôt contient le code consolidé Jarvis M07, les sources des deux sites et la direction artistique. Ce complément ajoute le catalogue de la récupération étendue et ses notes de reprise. Les médias et archives restent dans les fichiers sauvegardés ci-dessous ; leurs octets ne sont pas hébergés dans ce dépôt.

## Contrôles exécutés pendant ce transfert

Les trois ZIP ont été téléchargés et comparés au fichier SHA-256 de livraison. Leur contrôle CRC est réussi. Les tailles et les empreintes SHA-256 des **3 340 contenus distincts** ont ensuite été recalculées, sans divergence. Les **6 445 emplacements** du catalogue désignent tous un contenu et une source connus. La collection couvre **219 sources**, dont **168 fichiers sauvegardés**, et **1 089 594 390 octets uniques**.

Ces nombres décrivent la collection de récupération. Ils ne sont ni un nombre de fichiers ajoutés à GitHub, ni une certification d'export intégral des conversations. Les 1 060 emplacements du catalogue initial du dépôt décrivent un autre périmètre ; les deux chiffres ne doivent pas être additionnés.

La [preuve structurée](../data/catalog/recovery-2026-11-01/verification.json) donne les empreintes des trois ZIP et le détail des vérifications. Le [registre des sources](../data/catalog/recovery-2026-11-01/sources.json), les fichiers `contents-part-*.jsonl` et `locations-*.jsonl` relient les contenus uniques à leurs emplacements. Les liens directs des fournisseurs et les chemins locaux absolus ne sont pas publiés dans cette projection.

## Restaurer les fichiers

Télécharger les trois parties avec le compte ChatGPT autorisé :

1. [Partie 1 sur 3](https://chatgpt.com/library?file_id=libfile_8fe4cb5dac708191a5b11d0767f110a1&account_id=personal)
2. [Partie 2 sur 3](https://chatgpt.com/library?file_id=libfile_e6d9a3e4475c81918f7f388c26378809&account_id=personal)
3. [Partie 3 sur 3](https://chatgpt.com/library?file_id=libfile_b6a6ca51d7588191948ab9c82e2d078d&account_id=personal)

Extraire les trois parties dans le même dossier. Elles complètent `BOJART_RECUPERATION_2026-11-01`. Ouvrir `CATALOGUE.html` pour consulter les fichiers. Depuis ce dossier, le programme livré permet de vérifier et restaurer M07 :

```bash
python RESTAURER.py --verify
python RESTAURER.py --source libfile_875f76c239cc8191a4c147a11293c9ff --destination JARVIS_M07_RESTAURE
```

Le dossier destination doit être nouveau. Ne pas restaurer une ancienne version par-dessus le dépôt courant. Les originaux, les variantes et les versions rejetées sont conservés ; leur présence ne vaut pas validation artistique.

## Reprendre le projet

Lire d'abord [l'état courant](../context/CURRENT.md) et [l'installation](INSTALLATION.md). Les deux [notes historiques](historical/recovery-2026-11-01/README.md) ajoutées ici conservent les observations faites avant la consolidation GitHub. Leurs mentions « aucun push » et leurs anciens commits décrivent cette étape passée.

Le catalogue permet de retrouver les sources de Jarvis, les audits, les dashboards, les rendus et les historiques. Il n'ajoute pas un accès automatique du runtime aux anciens chats. La voix réelle, les trois moniteurs, le matériel d'impression et la qualité artistique demandent leurs propres vérifications.

Limites conservées : les fichiers présents seulement sur le PC de l'atelier et l'ensemble mot pour mot des conversations ne sont pas certifiés récupérés. L'archive TikTok historique documente une vidéo manquante. Cette opération n'a lancé ni génération payante, ni impression, ni publication de site ou de réseau social.
