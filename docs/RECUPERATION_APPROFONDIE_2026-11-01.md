# Récupération approfondie BOJ.ART — 1 novembre 2026

Le complément ajoute **62 originaux distincts, 390 425 092 octets**, aux 3 340 objets de la collecte initiale. Le périmètre indexé atteint 3 402 originaux. Les contrôles comparent les empreintes, pas seulement les noms de fichiers.

Archive : [`archive/deep-recovery-2026-11-01`](https://github.com/Momolscode/BOJART/tree/81d43e7910f17ebb85fdccab244b3f53bf360f9d), commit `81d43e7910f17ebb85fdccab244b3f53bf360f9d`.

| Élément | Résultat |
| --- | --- |
| Générations BOJ.ART identifiées | 76 fiches, avec prompts, paramètres et statuts |
| Résultats de génération | 60 téléchargés ; 41 supplémentaires et 19 déjà archivés |
| Références d'entrée | 41 URL téléchargées ; 16 médias supplémentaires après dédoublonnage |
| Captures de conversations fournies par l'utilisateur | 4 originales supplémentaires |
| Document de transport | 1 original supplémentaire |
| Notice de récupération | Déjà présente dans `docs/historical/`, référencée sans nouvelle copie |

Les 57 médias supplémentaires contiennent les résultats et sources des essais créatifs retrouvés. Les versions rejetées conservent leur statut historique. La sauvegarde ne constitue pas une validation artistique.

## Restaurer et consulter

Python 3.9 ou plus. La destination doit être nouvelle.

```sh
git clone --depth 1 --branch archive/deep-recovery-2026-11-01 https://github.com/Momolscode/BOJART.git BOJART_COMPLEMENT
cd BOJART_COMPLEMENT
git rev-parse HEAD
python RESTAURER.py --destination ../BOJART_COMPLEMENT_RESTAURE
```

La tête attendue est le commit ci-dessus. Ouvrir ensuite `CATALOGUE.html` dans le dossier restauré. Les 85 blobs de données sont contrôlés puis réassemblés en 62 originaux. Le restaurateur vérifie tailles et SHA-256, refuse une destination existante, les traversées de chemin et les liens sortants, et n'exécute aucun fichier récupéré.

`MANIFEST.json` décrit chaque original et ses fragments. `MEDIA_RECOVERY.json` relie les téléchargements aux générations. `LIBRARY_RECOVERY.json` préserve les identifiants des captures. `sources/generations-original-metadata.json` contient les fiches fournisseur. `MEDIA_VALIDATION.json` conserve les contrôles de format ; `COVERAGE.json` décrit le périmètre et les limites. La preuve de restauration distante est dans [`evidence/deep-recovery-2026-11-01.json`](evidence/deep-recovery-2026-11-01.json).

Cette branche reste séparée du runtime : ne pas la fusionner dans `main`. Pour les trois archives initiales, voir [`ETAT_ARCHIVES_2026-11-01.md`](ETAT_ARCHIVES_2026-11-01.md).

## Recherche et limites

L'inventaire a parcouru 722 fichiers sauvegardés, trois pages d'historique Higgsfield contenant 150 entrées, les 12 Pages accessibles et les sources connectées pertinentes. Les recherches Drive et Notion « BOJ » et « Jarvis » n'ont donné aucun résultat supplémentaire. Les 16 courriels trouvés sur le compte lié au dépôt sont des notifications GitHub, sans pièce jointe source ; l'autre compte interrogé demande une reconnexion.

Le ZIP M07 transmis de nouveau contient 441 entrées de fichiers déjà présentes : il n'est pas ajouté comme une nouvelle version de travail. La scène V35 est toujours en révision 2, avec les mêmes empreintes fournisseur ; ses fichiers Blender, GLB et aperçu figurent dans la collecte initiale.

Restent non récupérés ou non certifiés :

- Les conversations originales intégrales. La recherche de contexte fournit des synthèses ; les quatre captures ne restituent que les passages visibles. L'export des données ChatGPT est la prochaine source nécessaire pour vérifier les échanges mot pour mot. Il ne faut pas présumer qu'il contiendra des éléments supprimés.
- Les fichiers présents uniquement sur le PC de l'atelier, dont d'éventuels rushes ou projets de montage natifs.
- Le maillage et le rig exacts de la sculpture pour G2 : V35 ne les prouve pas.
- La vidéo TikTok `7099716894994730246` : métadonnées accessibles, mais essais de téléchargement aboutissant à HTTP 403, HTTP 404 ou à une page HTML.
- Les éventuels contenus non indexés, supprimés ou versions historiques non exposées par les outils disponibles.

Les anciens comptes rendus et les synthèses restent datés. Leur présence ne remplace pas la preuve actuelle des fichiers. Aucun nouveau rendu payant, déploiement de site, message externe ou accès aux machines de l'atelier n'a été lancé.
