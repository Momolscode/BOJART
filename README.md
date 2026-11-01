# BOJ.ART — complément de récupération du 1 novembre 2026

62 originaux supplémentaires, 390 425 092 octets, dédoublonnés par SHA-256 contre les 3 340 objets de la collecte initiale. Total indexé : 3 402 originaux distincts.

- 41 résultats de génération supplémentaires, parmi 60 résultats Higgsfield téléchargés et comparés ; les 19 autres sont déjà dans la collecte initiale.
- 16 images/vidéos de référence supplémentaires, après comparaison des 41 URL d’entrée aux résultats et à la collecte initiale.
- 4 captures de conversations fournies par l’utilisateur et 1 document de transport.
- 76 fiches de génération avec prompts et paramètres ; 16 statuts sans résultat restent documentés.

## Restaurer

Python 3.9 ou plus, bibliothèque standard seulement. La destination doit être nouvelle.

```sh
git clone --depth 1 --branch archive/deep-recovery-2026-11-01 https://github.com/Momolscode/BOJART.git BOJART_COMPLEMENT
cd BOJART_COMPLEMENT
python RESTAURER.py --destination ../BOJART_COMPLEMENT_RESTAURE
```

Ouvrir `CATALOGUE.html` dans le dossier restauré. Les gros originaux sont stockés en fragments de 8 Mio ; le restaurateur recalcule chaque empreinte et assemble les octets dans leur ordre exact. Il ne lance aucun contenu récupéré et refuse une destination existante.

Le manifeste décrit les 62 fichiers et chaque fragment. `MEDIA_RECOVERY.json` rattache les résultats aux identifiants de génération ; `LIBRARY_RECOVERY.json` rattache les captures aux originaux. `sources/generations-original-metadata.json` conserve les 76 fiches. Les liens fournisseurs sont des références de provenance ; les nouveaux octets sont conservés ici.

## Limites de couverture

Les résumés de recherche de contexte sont identifiés comme tels dans `CONTEXT_RETRIEVAL.json`. Ils ne remplacent pas les conversations mot pour mot. Aucun accès au PC de l’atelier n’a été effectué. Le modèle et le rig exacts de la sculpture G2 n’ont pas été retrouvés ; la scène V35 révision 2 est déjà dans les archives initiales. La fiche TikTok 7099716894994730246 reste accessible, mais les liens testés n’ont fourni aucune vidéo exploitable. Voir `COVERAGE.json` pour les recherches effectuées et leurs limites.

Cette branche est une archive de données, distincte de `main` et de l’application Jarvis. Ne pas la fusionner dans le runtime.

La notice `BOJART_RECUPERATION_LIRE_D_ABORD.txt` est déjà dans `main` sous `docs/historical/` ; elle est référencée sans copie supplémentaire.
