# BOJ.ART / Jarvis — Mission 03 : Studio des sources
Livraison du 30 octobre 2026. Extension des sources de Mission 02, et non modification du site publié.

## Ce qui fonctionne dans ce pack
- Un registre local SQLite relie 3 médias existants à leurs empreintes SHA-256.
- 8 passages éditoriaux sont repérés, dont 4 captations de la vraie figurine.
- Origine du fichier et nature du passage sont distinctes : une vidéo envoyée par l’utilisateur peut contenir une introduction animée ou un logo.
- Lecture à un timecode, recherche par mots-clés normalisés et filtre figurine réelle.
- Une sélection prépare un brief JSON versionné avec sa référence d’identité.
- Un passage mélangé, une illustration ou un plan refusé ne peut pas remplacer la référence authentique de cette recette.
- Les fichiers absents, altérés ou révisés invalident la préparation concernée.
- Un contenu déplacé peut être réindexé avec la même identité ; rien n’est supprimé des originaux.
- Export portable des médias, annotations et briefs, avec vérification des empreintes. Cet export n’est pas la sauvegarde globale du projet.

## Voir l’avancée sans rien installer
Ouvrir `APERCU_STUDIO_M03.html` dans un navigateur moderne. Les vidéos de prévisualisation sont incluses et allégées. Choisir un passage, cliquer sur « Lire ce passage », chercher « visage », filtrer « Figurine réelle », puis ouvrir le brief d’exemple.

Cet aperçu est autonome : son catalogue, son brief et ses contrôles ont été précalculés par le vrai module pendant la construction du pack. Il ne scanne pas votre disque et ne lance pas le serveur.

## Intégration sur la tour — pour Claude / l’intégrateur
Les lanceurs `Lancer_Jarvis.cmd` et `Lancer_Jarvis.sh` ouvrent le service `app/studio_workbench.py` sur localhost, avec les mêmes mécanismes de session que Mission 02. Ils préfèrent l’environnement `.venv` existant. Aucune installation ou commande physique automatique.

Prérequis : Python 3.11 ou plus, FFprobe/FFmpeg disponibles ; les dépendances CAO de `requirements.txt` restent nécessaires pour créer les socles. Aucun modèle IA n’est nécessaire pour la bibliothèque. Les options voix et Ollama de Mission 02 restent désactivées par défaut.

Le nouveau dossier d’état par défaut est `~/BOJART/mission03`. Il ne remplace pas les données Mission 02 d’un poste existant. Les trois vidéos d’exemple sont les seuls dossiers autorisés par défaut. L’ingestion générale du PC, la migration globale et l’installeur complet sont encore à intégrer.

Le Studio est accessible depuis « Ouvrir le Studio sources » sur le poste de dialogue. Les deux interfaces partagent un serveur et une session. Les bases métier 3D et médias restent distinctes ; leur sauvegarde unifiée est une étape à venir.

## Vérifications effectuées
Consulter `docs/PROGRES_ET_LIMITES_M03.md` et `preuves_m03/`.
- 50 tests du catalogue et des briefs.
- 20 tests HTTP du vrai service local (authentification, origine, lecture vidéo, sélection, refus).
- 172 tests hérités Missions 01/02 réexécutés.
- 19 contrôles Chromium de l’aperçu autonome.
- Essai de connexion directe Chromium/localhost bloqué par la politique de l’environnement de travail. Aucun contournement. La recette sur la vraie tour reste nécessaire.

## Ce que ce pack ne prétend pas faire
Pas de recherche sémantique ni d’analyse automatique des images. Les annotations sont manuelles et datées. Pas de nouveau montage rendu, génération, publication, achat de crédits, accès aux réseaux sociaux, contrôle d’imprimante ou reconnaissance vocale mesurée sur place. Pas de validation commerciale des œuvres ou musiques.

Les tests utilisent des petits médias et un utilisateur local. La limite volontaire de lecture est 64 Mio par média dans ce pilote. Elle ne convient pas encore à de gros rushes 4K : streaming, indexation incrémentale et isolation du décodeur restent à préparer.

## Origine des médias inclus
Les trois vidéos proviennent de cette conversation. Aucun fichier d’un ordinateur personnel, cloud ou réseau n’a été exploré. Les proxies intégrés à l’aperçu ne remplacent pas les originaux.
