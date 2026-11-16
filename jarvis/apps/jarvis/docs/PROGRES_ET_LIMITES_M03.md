# Mission 03 — bilan vérifiable
Date : 30 octobre 2026.

## Pourquoi cette évolution
Le studio vidéo BOJ.ART doit retrouver la bonne œuvre avant de la transformer. Dans le fichier fourni `v24044gl0000cuei73fog65q7gjmvfc0.mp4`, les images contrôlées à 0,6 s et 2,8 s présentent un logo/une séquence animée ; les images à 5,0, 7,0, 8,5 et 10,2 s montrent la sculpture ; la fin comporte un habillage et une ancienne promotion. Le fichier entier n’est donc pas une référence homogène du personnage.

Les mesures FFprobe exécutées ici : durée 15,1 s, vidéo H.264 512 × 1108, 30 i/s et piste audio AAC. Une présence audio ne démontre ni une licence, ni une qualité sonore adaptée.

## Fonction réellement ajoutée
`app/media_library.py` associe le contenu par empreinte à des emplacements, puis distingue les passages. Les mots-clés de recherche sont des annotations : le programme n’a pas « reconnu » une cicatrice ou de la peinture avec un modèle de vision.

Le dossier V6 sert à rappeler les caractéristiques artistiques ; il n’effectue pas une reconnaissance biométrique automatique. Une référence admissible pour ce pilote exige une captation de la figurine et une validation interne explicite. L’API n’offre pas de commande au LLM pour approuver librement un contenu.

## Intégration avec Mission 02
`app/studio_workbench.py` étend le même serveur local et la même session. Les fonctions de socle, de proposition et d’audio préparé sont conservées. Un lien relie le poste à la bibliothèque. Le port par défaut est 8767 ; le service écoute seulement 127.0.0.1. Pas de service public.

Nouveaux endpoints : catalogue, lecture de média identifié par empreinte, préparation de brief, relecture du brief et rafraîchissement des disponibilités. Pas de chemin de fichier arbitraire accepté du navigateur ; pas d’endpoint d’achat, de génération ou de publication.

## Contrôles livrés
- Déplacement : réimport du même contenu sous un nouveau chemin -> même identité, pas de doublon de contenu.
- Mutation ou retrait : ancien identifiant conservé, disponibilité signalée ; la préparation n’utilise pas un substitut.
- Édition d’annotation : révision obligatoire ; un brief antérieur devient périmé.
- Reprise : la même demande retrouve le même brief ; un contenu différent sous le même identifiant est refusé.
- Sélection : passages réels et éventuellement générations distingués ; concepts et contenus mélangés doivent être séparés avant réutilisation.
- Droits : inconnus par défaut. Préparer n’autorise jamais à publier ; les justificatifs doivent être saisis explicitement.
- Interprétation des textes : étiquettes et notes affichées comme texte, jamais exécutées.

## Sauvegarde : portée exacte
L’export portable contient médias exacts, catalogue, annotations et briefs, sans chemins absolus du poste. Il est contrôlé à la relecture. La restauration applicative n’est pas implémentée. La sauvegarde du dossier 3D de Mission 02 reste séparée ; l’interface le précise. Aucune garantie de reprise globale du futur atelier n’est revendiquée.

## Recette exécutée
50 tests du registre, 20 tests HTTP réels, 172 régressions des Missions 01/02, 19 contrôles de l’aperçu autonome. L’aperçu a été inspecté visuellement en desktop et mobile. Aucune impression, écoute de microphone ou IA n’a été exécutée.

Le premier essai direct de Chromium vers localhost a été bloqué (`ERR_BLOCKED_BY_ADMINISTRATOR`). Aucun réglage de sécurité n’a été modifié. Les contrôles visuels portent sur l’aperçu autonome alimenté par les données réelles précalculées ; le serveur a été testé séparément avec le client HTTP Python. Cela ne valide pas encore le navigateur du PC cible.

## Limites à traiter ensuite
1. Ingestion de dossiers explicitement autorisés, sans parcourir tout le PC par défaut.
2. Décodage isolé et streaming pour les gros rushes ; limites de ressources renforcées.
3. Recherche sémantique : comparer ensuite un modèle local sur des passages dont on connaît la réponse.
4. Proposition de plans et moteur de montage partageant une même recette et une même version.
5. Validation artistique en mouvement, fichiers sources 3D de la sculpture et travail sonore de meilleure qualité. Ce module ne prétend pas résoudre les VFX 3D à lui seul.
6. Sauvegarde/restauration unifiée des projets, modèles, médias et configurations.
7. Qualification sur la tour, puis sur une FDM et une résine réelles.

## Documentation primaire consultée
FFmpeg / FFprobe, extraction de métadonnées et format JSON :
https://www.ffmpeg.org/ffprobe.html
Options communes et restrictions de protocole :
https://www.ffmpeg.org/ffprobe-all.html

Les bibliothèques ici ne téléchargent aucun modèle ni média. Le premier import de trois fichiers du pack utilise le FFprobe installé. Leur contenu reste local.
