# BOJ.ART — Vérification de la sauvegarde, 1 novembre 2026

## Conclusion
Le paquet local BOJART_MARWIN_PRET_GITHUB_2026-11-01.zip correspond exactement, par taille, SHA-256 et nombre de fichiers, au paquet couvert par le rapport de restauration du dépôt. Ce rapport annonce les **87 fichiers conservés dans les trois branches d’archive**, dont l’existence et les révisions ont été relues pendant ce contrôle.

Les anciens comptages de 43 puis 729 fichiers concernaient la branche principale et ne permettaient pas de conclure sur la sauvegarde globale. De même, les chemins absents de main ne sont pas des preuves de fichiers perdus : les originaux ont été classés dans les branches d’archive.

## Contrôles effectués maintenant
- Archive locale : 49 329 375 octets, 87 fichiers, lecture CRC sans erreur.
- SHA-256 : cf7465639afc7d903f2669a7ece914308593a82e3ec0e90d0064afeaa3e4a161.
- Les 85 entrées du manifeste principal correspondent aux octets locaux. Le manifeste principal lui-même et un ancien manifeste imbriqué ne sont pas couverts par cette liste ; ils font bien partie des 87 fichiers comparés par le rapport de récupération.
- Comparaison aux emplacements de main au commit 3c288214539adf97381f6053b43225485a873b6a : 6 fichiers identiques, 3 fichiers représentés intégralement par 20 blocs identiques, 10 versions différentes et 68 chemins absents. Ces 68 chemins NE SONT PAS 68 pertes : les archives séparées constituent la sauvegarde globale.
- Les 20 blocs comparés par empreintes Git correspondent aux fichiers originaux locaux ; ce contrôle n’est pas un nouveau téléchargement des blocs.
- Identité du paquet comparée à docs/evidence/recovery-resumption-2026-11-01.json : même SHA-256, même taille, 87 fichiers annoncés vérifiés.

## Branches d’archive confirmées
| Partie | Branche | Commit |
|---|---|---|
| 1 | archive/recovery-2026-11-01-part-1 | 635116df515f7910c5bc854176b642e282efbfb3 |
| 2 | recovery/partie-2-2026-11-01 | 2d2e01e3576e0a655729f6d273e9038e109f915a |
| 3 | archive/recovery-2026-11-01-part-3 | 6e743b8a8ba90b6ab24a579a1f8c5aebaa8ba967 |

## Ce qu’atteste le rapport déjà présent sur GitHub
Le rapport de récupération documente 3 340 contenus uniques, 1 089 594 390 octets, 219 sources et 6 445 emplacements. Il rapporte une restauration depuis les commits Git et une comparaison octet par octet aux trois ZIP d’origine, sans différence. Cette restauration globale est un résultat antérieur consigné : elle n’a PAS été réexécutée intégralement pendant ce contrôle.

## Limites
Cette sauvegarde porte sur la collecte retrouvée. Elle ne garantit ni un export intégral de toutes les conversations, ni la sauvegarde des fichiers uniquement présents sur le PC de l’atelier. Le rapport signale une vidéo TikTok manquante, identifiant 7099716894994730246. La validation des vidéos finales, de la voix, des imprimantes et de l’installation matérielle reste distincte.

Aucun nouveau média n’a été publié, aucun historique n’a été écrasé pendant ce contrôle.

## Sources relues via le connecteur GitHub
- docs/ETAT_ARCHIVES_2026-11-01.md au commit 3c288214539adf97381f6053b43225485a873b6a.
- docs/evidence/recovery-resumption-2026-11-01.json au même commit.
- Liste effective des branches du dépôt et arbres Git de main, docs/historical, runs, tools et archive/2026-11-01/chunks.
