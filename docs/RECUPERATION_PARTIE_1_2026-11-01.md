# Récupération BOJART du 1 novembre 2026 — partie 1 sur 3

Le ZIP demandé a été intégralement sauvegardé sur GitHub dans la [branche de récupération](https://github.com/Momolscode/BOJART/tree/archive/recovery-2026-11-01-part-1).

| Contrôle | Résultat |
|---|---|
| Fichier original | `BOJART_RECUPERATION_2026-11-01_PARTIE_1_SUR_3.zip` |
| Taille exacte | 331 492 004 octets |
| Objets dans cette partie | 1 112, plus 8 fichiers d’index et de restauration |
| Découpage de transport | 40 blocs binaires, reconstruction sans perte |
| Empreintes des objets | 1 112 conformes |
| Empreintes Git des blocs envoyés | 40 conformes |
| Reconstruction locale | SHA-256 identique au ZIP original |
| Relecture depuis GitHub | 331 492 004 octets relus ; 40 blocs et SHA-256 final conformes |
| Commit de sauvegarde | [`635116df515f7910c5bc854176b642e282efbfb3`](https://github.com/Momolscode/BOJART/commit/635116df515f7910c5bc854176b642e282efbfb3) |

SHA-256 du ZIP :

```text
9f0544b915ebcd34482a0ff33076eb0ae25dfe333c9493b746f15a183c61fc8f
```

La branche contient le manifeste, la liste des 1 112 objets, les blocs et `RECONSTRUIRE.py`. Son README explique le téléchargement et la reconstruction du ZIP avec Python standard. Le programme vérifie chaque bloc et l’archive finale, refuse d’écraser une destination existante et ne lance aucun code récupéré.

La conservation de cette archive complète, demandée explicitement, est isolée sur une branche de sauvegarde. Les règles ordinaires de `main` restent celles d’un dépôt de sources : aucune réinstallation des anciens fichiers par-dessus le Jarvis actuel. Au commit `1d76c6876de54c7bc37b777ae66bf031207a140d`, 204 objets de la partie 1 avaient déjà une copie identique dans `main` ; la sauvegarde conserve volontairement les octets exacts du ZIP original.

**Périmètre : uniquement la partie 1 fournie dans cette demande.** Les parties 2 et 3 ne sont pas transférées par cette opération. L’index interne décrit la collection complète, mais ne prouve pas la présence des deux autres parties. Cette sauvegarde ne constitue ni un export intégral des conversations, ni une validation du Jarvis sur le matériel réel.

[Preuve de relecture distante](evidence/recovery-part-1-2026-11-01.json).
