# Outils et données de conception 3D — veille du 4 novembre 2026

Demande d'Olsen (4 novembre 2026) : rechercher les outils et les données dont l'atelier aurait besoin pour la conception 3D et la préparation à l'impression. **Cette veille ne change aucun code, n'installe rien, n'achète rien et ne génère rien.** Base examinée : `main` à `3436f5352659554e4bac5af492b94af6c522ed2d`, plus la branche de la PR #15 (chaîne figurine M08) pour ne pas dupliquer.

Résumé lisible : document « Outils 3D de l'atelier — veille du 4 novembre 2026 » (Claude Docs, lien dans la PR). Détail sourcé : les fichiers ci-dessous.

## Décision proposée

Garder la chaîne M08 (trimesh, manifold3d, PrusaSlicer en ligne de commande, Blender en ligne de commande) et l'étendre par essais bornés. Toute la chaîne peut rester gratuite et scriptable sous Windows ; les achats envisagés (ZBrush, Nomad Sculpt, Split3r, CHITUBOX, Lychee) restent des secours décidés après essai ou inventaire.

| Étape | Déjà dans le dépôt | Premier essai proposé |
|---|---|---|
| Sculpt et modélisation | Blender 4.0.2 (conteneur), CadQuery 2.8.0 | Blender 5.2.3 LTS + 3D Print Toolbox 1.5.0 |
| Génération IA (personnage original) | — | Tripo H3.1, Hunyuan3D v3, Meshy 7 via Higgsfield ; TRELLIS.2 natif ComfyUI, TripoSG corrigé, Hi3DGen en local |
| Numérisation | — | RealityScan 2.2 ; COLMAP 4.2.1 en libre |
| Contrôle et réparation | trimesh 4.11.1, manifold3d 3.5.4 | trimesh 4.12.2 ; PyMeshLab ou pymeshfix pour les imports, jamais en silence |
| Découpe d'un mètre | tenons figurine (manifold3d) | script manifold3d : coupes planes, goujons, jeu, numérotation |
| Tranchage FDM | PrusaSlicer 2.7.2 | PrusaSlicer 2.9.7 ou OrcaSlicer 2.4.2 en CLI, un seul après inventaire |
| Tranchage résine | — | PrusaSlicer 2.9.7 SLA puis UVtools 7.1.2 (`convert`, `print-issues`) |
| Contrôle du fichier tranché | — | relecteur G-code à écrire ; UVtools ; reçu avec empreintes |
| Pilotage | parc simulé (PR #18) | lecture d'état seule, interface par famille (voir `pilotage-donnees.json`) |

## Ce qui contredit ou complète le dépôt

- **PrusaSlicer 2.7.2** (février 2024) a environ 32 mois de retard sur 2.9.7 (2 novembre 2026) : correctifs de sécurité 3MF et G-code binaire, refonte SLA de 2.9.1 et 2.9.5. Ne pas suivre la 3.0 alpha, dont la CLI change.
- **Blender 4.0.2** n'est plus maintenu. LTS courantes : 5.2 (5.2.3) et 4.5. L'API Python a changé en 5.2 : requalifier les scripts de rendu.
- **trimesh** : épinglé 4.11.1, dernière 4.x 4.12.2, amont 5.2.0. Passer d'abord par 4.12.2 sans réépingler deux versions (`test_shared_pins_do_not_conflict`).
- **TRELLIS.2** : « Linux et 24 Go » reste vrai pour le code officiel, mais ComfyUI l'intègre nativement depuis le 22 août 2026 (PyTorch pur, int8 de 5,25 Go, détourage BiRefNet). Le passage en 8 Go est à mesurer. Le code officiel n'est pas propre commercialement (RMBG-2.0, nvdiffrast).
- **TripoSG** : poids MIT confirmés, mais le chemin par défaut charge RMBG-1.4 et diso, non commerciaux. Correctif : entrée RGBA déjà détourée et `use_flash_decoder=False`.
- **Hunyuan3D** : l'exclusion UE couvre toute la famille ouverte (2.0, 2mini, 2.1, Omni, Part). Le service en ligne (v3, v3.1 via Higgsfield) n'a pas cette clause mais impose la mention IA et garde un droit perpétuel sur les contenus.
- **build123d 0.13.0** est incompatible avec CadQuery 2.8.0 dans le même environnement (OCP).
- **Autodesk Fusion** en licence personnelle interdit la vente.
- **Ponts MCP** : le serveur Blender officiel du Blender Lab exécute du Python sans garde (VM recommandée) ; aucun serveur MCP d'imprimante ne propose une vraie lecture seule. La règle « pas de MCP à Python arbitraire par défaut » est confirmée.
- **Imprimantes** : les descriptions de vidéos des archives du site citent `#ender5pro`, `#ender5plus`, `#elegoosaturn`, `#elegoomars`. Indice public, pas inventaire.

Contre-vérifications faites par le fil principal : `VERIFICATIONS.json`.

## Fichiers

| Fichier | Contenu |
|---|---|
| `CATALOGUE.json` | Index des 161 fiches : recommandation, version, licence, coût, URL officielle, statut de preuve |
| `ia3d-local.json` | 31 fiches : génération 3D locale, rig et retopo IA, moyens d'exécution (ComfyUI, WanGP) |
| `ia3d-en-ligne.json` | 17 fiches : Meshy, Tripo, Rodin, Hunyuan cloud, Higgsfield, services de rig ; CGU, prix, propriété des sorties |
| `modelisation-numerisation.json` | 40 fiches : sculpt, CAO, retopo, rendu, visionneuses, numérisation, ponts MCP |
| `preparation-impression.json` | 31 fiches : réparation, découpe, tranchage FDM et résine, contrôle ; décisions bloquées par l'inventaire |
| `pilotage-donnees.json` | 42 fiches : interfaces machines, supervision, profils, FDS/TDS, calibration, jeux de test ; 25 champs d'inventaire ; sources de règles de conception |
| `higgsfield-couts-3d.json` | Coûts en crédits relevés par préflight, sans job soumis |
| `BANCS.json` | 8 bancs d'essai proposés avec mesures et seuils, tous non exécutés |
| `VERIFICATIONS.json` | Affirmations recoupées par le fil principal |
| `bancs/` | Scripts et résultats des bancs B3, B4 et B5 exécutés le 4 novembre (aucun maillage ni G-code versionné, empreintes seules) |

Recommandations : 27 essais prioritaires, 43 candidats, 47 recherche seulement, 28 rejetés, 4 déjà présents, 12 conditionnés à l'inventaire. « Essai prioritaire » veut dire « à mesurer en premier », pas « adopté ».

## Limites

- Lecture web du 4 novembre 2026 par cinq recherches parallèles, puis recoupement partiel. Chaque fiche porte son statut de preuve ; plusieurs prix (ZBrush, Lychee, Tango, Netfabb en euros) viennent de sources tierces et restent marqués non vérifiés.
- Rien n'est installé ni mesuré sur la tour. Les besoins VRAM sont ceux annoncés par les auteurs ou rapportés par des utilisateurs.
- Ce n'est pas un avis juridique. Relire les licences maison (Hi3D, DINOv3, Stability, CGU des services) avant une vente.
- Aucun personnage protégé n'est utilisé ni proposé en entrée.

## Bancs gratuits exécutés le 4 novembre 2026

Exécutés dans le conteneur de session (Linux, 4 cœurs, sans GPU), pas sur la tour. PrusaSlicer 2.7.2 vient d'Ubuntu ; PrusaSlicer 2.9.7 et OrcaSlicer 2.4.2 viennent de Flathub, lancés hors bac à sable. Rien n'est imprimé ni envoyé à une machine.

**B3, 12 fichiers piégés** (`bancs/B3-resultats.json`). Les contrôles M08 seuls donnent 11 verdicts justes sur 12 et un faux « prêt » : la pièce de 400 mm passe, puis le trancheur l'arrête. Trois verdicts justes le sont pour une mauvaise raison : les cubes en pouces et en mètres sont refusés pour « paroi < 0,8 mm » au lieu d'une échelle suspecte, et le STL tronqué fait planter la chaîne au lieu d'être refusé. Les trancheurs en second avis ne voient que 3 défauts sur 11. PrusaSlicer retourne des normales inversées sans le signaler. Chevauchement, arête non-variété et cavité fermée passent en « manifold = yes ». La porte d'import proposée (contrôle d'octets, échelle, volume machine, coques, puis contrôles M08) classe les 12 fichiers correctement, mais elle a été écrite en connaissant les pièges : elle reste à éprouver sur des fichiers réels (sorties B1, scans).

**B4, trancheurs** (`bancs/B4-resultats.json`). Aucun des trois trancheurs ne fait d'erreur, chacun est déterministe et le relecteur de G-code accepte les trois sorties : liste blanche, bornes du volume, températures.

| Ardoise v6, profil M08 | Temps estimé | Filament | Tranchage (médiane, n = 3) |
|---|---|---|---|
| PrusaSlicer 2.7.2 | 11 h 58 min 43 s | 98,57 g | 28,4 s |
| PrusaSlicer 2.9.7 | 12 h 0 min 1 s | 98,55 g | 29,3 s |
| OrcaSlicer 2.4.2, profil traduit | 14 h 5 min 27 s | 110,85 g | 35,5 s |

La 2.7.2 reproduit au chiffre près le tranchage M08 du 2 novembre. La montée en 2.9.7 ne change presque rien sur ce profil. L'écart d'Orca vient de ses supports organiques (+49 % de filament) ; parois et remplissage restent à 2 % près. Deux pièges sont relevés pour Orca. Sans valeurs écrites en clair, il applique les siennes (débit plafonné à 2 mm³/s). Il ajoute aussi une chauffe M190 et M104 sans attente M109 : le début de G-code des vraies machines devra porter M109.

**B5, découpe à 1 m** (`bancs/B5-resultats.json`). Ardoise passe à 1 000 mm (443 × 391 × 1 000 mm) et donne 18 pièces étanches qui tiennent dans 240 × 200 × 220 mm. Le banc place 34 goujons (31 de 8 mm, 3 de 4 mm) et grave le numéro de joint sur les deux faces, lisible de chaque côté. Après export STL et remontage virtuel, l'écart avec le modèle d'origine est de 0,00003 mm, sans interférence de goujon. La première exécution échouait avec 2,5 mm d'écart : des trous débouchaient là où la peau rentre près du plan de coupe. La position des goujons est maintenant vérifiée sur toute leur profondeur. Restent trois points :
- deux joints n'ont pas la place d'un numéro gravé ;
- les alertes « paroi fine » de M08 sur ces pièces viennent presque toutes du biseau le long des coupes ;
- l'outil Couper de PrusaSlicer en ligne de commande ne sert pas de secours. La 2.7.2 n'écrit rien. La 2.9.7 superpose les deux moitiés dans un seul STL et, sans `--output`, écrase le fichier d'entrée.

Le jeu des goujons (0,15 mm par côté) reste une hypothèse à mesurer sur un coupon imprimé.

## Prochaine preuve

1. B1 (IA en ligne sur Veille, 88 crédits Higgsfield) est approuvé par l'utilisateur et attend la recharge du compte.
2. Intégrer à la chaîne M08, avec leurs tests, la porte d'import de B3 et la découpe de B5. Il faut aussi traiter à part le biseau des pièces découpées.
3. B2, B6, B7 et B8 attendent la tour, l'inventaire des machines ou des photos d'œuvre. Sur la tour, rejouer B4 avec les installations Windows de PrusaSlicer 2.9.7 et d'OrcaSlicer 2.4.2.
