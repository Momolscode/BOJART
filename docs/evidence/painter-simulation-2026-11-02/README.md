# Preuves — simulation du bras peintre, 2 novembre 2026

Hôte : conteneur Linux, Python 3.13, sans GPU, robot ni caméra. Code : `bojart_painter/` ; empreintes du code et des configurations dans chaque rapport (`runtime.fingerprints`).

| Fichier | Commande |
|---|---|
| `arms.json` | `python -m bojart_painter arms --output …` (59 essais coupon par bras et par scénario, graine 1) |
| `simulate-paysage-seed1.json` | `python -m bojart_painter simulate --target synthetic:paysage --style reproduction touches_courtes aplats_geometriques gestuel --compare --seed 1` |
| `simulate-{paysage,composition}-seed{1,2,3}.json` | `… --style reproduction aplats_geometriques --compare --seed N` |
| `simulate-paysage-converge-seed1.json` | `… --target synthetic:paysage --style touches_courtes reproduction --until-converged --seed 1` (arrêt sur toile couverte et gain < 2 %) |
| `summary.json` | Agrégat des rapports ci-dessus et leurs SHA-256 |

Les rendus PPM sont restés hors Git ; une planche de la graine 1 a été remise à l'utilisateur hors du dépôt.

Lecture : le monde « physique » est un modèle caché (largeur × 1,2, opacité 0,72). Ces rapports montrent que la boucle retrouve ce modèle et que la replanification réduit l'écart à la cible dans la plupart des cas. Ils ne mesurent ni un bras, ni une peinture, ni un coupon. Les taux du coupon dépendent entièrement de l'hypothèse « écart type = allocation / 2 » appliquée au budget STRATES. Trois graines suffisent pour des tendances, pas pour établir une significativité.

Analyse et recommandation : `docs/research/bras-peintre-simulation-2026-11-02/README.md`.
