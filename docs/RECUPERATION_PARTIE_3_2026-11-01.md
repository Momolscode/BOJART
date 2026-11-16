# Récupération BOJART du 1 novembre 2026 — partie 3 sur 3

Les **1 114 fichiers** de `BOJART_RECUPERATION_2026-11-01_PARTIE_3_SUR_3.zip`
sont conservés dans la
[branche de récupération dédiée](https://github.com/Momolscode/BOJART/tree/archive/recovery-2026-11-01-part-3),
à la demande explicite du propriétaire du dépôt. Cette branche historique est
séparée du code actif ; elle ne doit pas être fusionnée dans le runtime.

Publication vérifiée : [commit `6e743b8`](https://github.com/Momolscode/BOJART/commit/6e743b8a8ba90b6ab24a579a1f8c5aebaa8ba967).
Les 1 135 fichiers de la branche (1 131 données et 4 fichiers d'accompagnement)
ont été relus dans l'arbre distant avec leurs empreintes et leurs modes Git.
Voir la [preuve de publication](evidence/recovery-part3-2026-11-01.json).

| Contrôle | Résultat |
|---|---|
| ZIP fourni | 340 986 970 octets |
| Contenu décompressé | 1 114 objets distincts, 363 198 134 octets |
| Types principaux | 33 MP4, 3 bundles Git, 2 ZIP, 5 PDF |
| Stockage | 1 108 fichiers directs et 23 fragments pour 6 gros objets |
| Vidéos | 32 MP4 directs ; 1 MP4 reconstitué sans perte |
| Intégrité | Tailles, SHA-256 et SHA-1 Git des objets et fragments |
| Déduplication Git | 202 blobs déjà présents à la révision de comparaison |

SHA-256 du ZIP fourni :

```text
6a23245cda664686f0d8dac40d49107032bd5f94a09a686edaa833ed39300b06
```

Le manifeste `MANIFESTE_PARTIE_3.json` et le programme autonome `RECONSTRUIRE.py`
se trouvent dans la branche d'archive. Après téléchargement de cette branche :

```bash
python3 RECONSTRUIRE.py --verify-only
python3 RECONSTRUIRE.py --destination ../BOJART_PARTIE_3_RESTAUREE
```

Sous Windows, utiliser `python` si nécessaire et un chemin court comme `C:\BOJART`.
Le programme demande Python 3.9 ou plus récent. La destination doit être neuve.
L'outil vérifie toutes les sources avant écriture, contrôle les fragments et leurs
concaténations, puis restitue les 1 114 chemins d'origine sans écrasement. Il ne
décompresse ni n'exécute les archives historiques. La restauration produit les
fichiers du ZIP, pas une nouvelle copie du conteneur ZIP initial.

La comparaison de déduplication porte sur `ccb79a118e04c282bcd8cd1dc0fd514a9810ebeb`.
Les chemins de récupération sont conservés ; les blobs identiques sont réutilisés
par Git. Les bundles et ZIP restent restaurables sans modification de leurs octets.

**Périmètre : la partie 3 fournie dans cette demande.** La
[partie 1](RECUPERATION_PARTIE_1_2026-11-01.md) relève d'un transfert distinct.
Le [catalogue global](RECUPERATION_VERIFIEE_2026-11-01.md) décrit la provenance et
les noms d'origine, mais un index ne prouve pas à lui seul le transfert de tous
les médias. La récupération ne certifie ni toutes les conversations originales,
ni la qualité artistique des rendus, ni l'installation matérielle de Jarvis.
