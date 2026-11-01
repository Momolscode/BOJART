# BOJ.ART / JARVIS — Mission 05

Version locale du 31 octobre 2026. Cette mission fiabilise la reprise du travail : plusieurs dossiers CAO, sauvegarde globale, restauration indépendante et traitement des interruptions. Elle ne déclare pas les équipements physiques prêts.

## Changements utilisables

- Le lanceur ouvre `/workspace`. Cette page affiche les dossiers, leurs révisions, les créations en cours/conservées/interrompues/en échec, les médias et les brouillons.
- Chaque dossier possède ses propositions CAO, révisions, historique et vues de régie. Un modèle d'un autre dossier est refusé. Les anciens identifiants restent lisibles ; le dossier pilote est conservé.
- Studio et Growth gardent un catalogue commun à l'atelier. Ce ne sont pas des espaces clients isolés.
- Le contexte de référence appartient désormais au dossier de travail. L'application et les tests ne modifient plus le contexte livré avec les sources.
- Une sauvegarde globale contient les cinq bases SQLite, les fichiers CAO avec recettes et reçus, les médias référencés, le contexte et les fichiers de créations inachevées. Son inventaire SHA-256 est vérifié.
- La restauration crée exclusivement un nouveau répertoire. Elle vérifie les bases, les fichiers et les liens médias, rétablit les chemins locaux et conserve les identifiants et révisions. Les anciens appairages navigateur sont retirés et les commandes d'affichage en attente sont neutralisées.
- Une création laissée en cours à l'arrêt devient `INTERRUPTED`. L'utilisateur peut vérifier un résultat entièrement conservé sans recalcul, ou clôturer l'essai en échec en gardant les fichiers. Les états des propositions suivent ceux des opérations.
- Un verrou système réserve l'espace de travail à une instance de ce serveur. La fermeture attend la fin des modifications acceptées avant de libérer le verrou.
- Les tentatives de création de dossier, d'envoi en régie et de sauvegarde conservent leur identifiant dans l'onglet. Une réponse perdue peut être réconciliée sans dupliquer le travail.
- Les vues conservent le dossier sélectionné, y compris leurs liens de retour. Le tableau de bord retrouve les dernières sauvegardes locales et le dernier contrôle d'intégrité daté.

## Démarrer ou reprendre

Dépendances du socle : Python 3.11+, CadQuery 2.8.0, Trimesh 4.11.1 et FFprobe. Aucune installation automatique n'est lancée. L'essai de cette mission a utilisé Linux / Python 3.12.14. Les scripts Windows sont fournis mais leur exécution sur le PC cible reste à vérifier.

- `Lancer_Jarvis.cmd` sous Windows, ou `bash Lancer_Jarvis.sh` sous Linux : nouvel espace par défaut dans `~/BOJART/mission05`.
- `Ouvrir_un_dossier_Jarvis.cmd` ou `.sh` : choisir un espace existant ou restauré. Le sélecteur exige Tkinter ; à défaut, utiliser l'option `--state`.
- En ligne de commande : `python apps/jarvis/app/consolidated_workbench.py --state "/chemin/espace" --no-browser`.
- Pour un autre port : ajouter `--port 8768`. L'écoute reste limitée à `127.0.0.1`.

Avant d'ouvrir un ancien espace M04, fermer l'ancien serveur et conserver une copie de son répertoire complet. L'ouverture M05 ajoute les profils de dossiers et les colonnes de routage ; elle ne supprime pas l'historique. Les archives M04 originales restent inchangées. Les données réellement restées sur le PC de l'utilisateur n'ont pas été récupérées par cette mission.

## Sauvegarde et restauration

Depuis « Dossiers & sauvegardes », lancer le contrôle, puis créer et télécharger la sauvegarde. La laisser sur le même disque ne protège pas d'une panne de ce disque.

Le périmètre exact des bases est :

| Base | Données |
| --- | --- |
| `missions.sqlite3` | Dossiers, révisions, opérations et propositions de dialogue |
| `display-proposals.sqlite3` | Propositions d'affichage |
| `control-tower.sqlite3` | Appairages locaux, commandes et accusés |
| `studio/media.sqlite` | Médias, chemins, annotations et briefs |
| `growth/growth.sqlite` | Brouillons Growth |

Les modifications de l'application sont sérialisées pendant la copie. Chaque base est copiée par l'API SQLite de sauvegarde sous réservation des écritures des cinq bases. Ne pas éditer directement les fichiers de l'espace pendant une sauvegarde.

Pour restaurer : lancer `Restaurer_Jarvis.cmd` ou `.sh`, choisir le ZIP puis un **nouveau nom de dossier**, et ouvrir ce résultat avec `Ouvrir_un_dossier_Jarvis`. Alternatives sans sélecteur :

```sh
python tools/restore_workspace.py "/chemin/bojart-global-ID.zip" --verify
python tools/restore_workspace.py "/chemin/bojart-global-ID.zip" "/chemin/nouveau-dossier"
python apps/jarvis/app/consolidated_workbench.py --state "/chemin/nouveau-dossier"
```

Un dossier existant n'est jamais écrasé. Les chemins sortant de l'archive, doublons de casse, liens symboliques, inventaires incomplets et empreintes divergentes sont refusés. La restauration n'exécute pas les recettes Python archivées. Une restauration interrompue conserve un marqueur bloquant une ouverture accidentelle ; un échec géré retire uniquement le nouveau dossier créé par cette tentative.

Limites délibérées : 1 Gio décompressé, 20 000 fichiers, médias référencés par le catalogue. Les secrets, cookies, modèles IA, pilotes, profils machine externes, anciennes sauvegardes et états des sites hébergés sont exclus. Les anciens ZIP de sauvegarde CAO seuls ne sont pas des sauvegardes globales M05 : ils doivent rester conservés séparément.

## Preuves et limites de lancement

La recette automatique compte 514 tests réussis, dont 34 nouveaux scénarios de continuité, ainsi que 13 contrôles navigateur réel et 5 contrôles des lanceurs Linux. `docs/evidence/m05-2026-10-31/TESTS_SUMMARY.json` donne les nombres et les empreintes des fichiers exécutés ; `ACCEPTANCE_M05.json` consigne le parcours dans Chromium.

Le navigateur a réellement créé deux socles de 180 et 240 mm, vu leurs maillages, obtenu des accusés des trois rôles de vues, préparé un brief Studio et un brouillon Growth, puis téléchargé la sauvegarde vérifiée. Une réponse d'envoi perdue a été simulée ; la reprise après rechargement conserve le même identifiant. La restauration a été relue après retrait de l'espace initial, puis une seconde génération de sauvegarde a été restaurée.

Les deux modèles comportent un solide CAO valide et un STL fermé à normales cohérentes ; les dimensions restent dans la tolérance numérique de 0,15 mm. Cela ne certifie pas la résistance, le matériau, le tranchage ou une impression.

Toujours à qualifier sur la tour réelle : Windows et dépendances, microphone, voix, modèle local, Jev, trois moniteurs physiques, une FDM, une résine et son post-traitement, comptes sociaux et tunnel de devis. L'indicateur de production reste donc à `false`. Aucun déploiement public, achat, impression ou envoi social n'a été effectué.

## Rejouer la recette

```sh
python tools/run_checks.py
python tools/m05_smoke.py
python tools/verify_repository.py
```

La recette navigateur exige Node, Playwright et Chromium. `BOJ_TEST_CHROMIUM` permet de désigner un exécutable Chromium déjà installé. Les captures produites pendant la recette servent au contrôle visuel local ; elles ne font pas partie du paquet livré. Les espaces d'essai sont temporaires et ne doivent pas être confondus avec les données de l'atelier.

Références techniques : [SQLite Online Backup](https://www.sqlite.org/backup.html), [Python sqlite3](https://docs.python.org/3/library/sqlite3.html), [verrou Windows msvcrt](https://docs.python.org/3/library/msvcrt.html). Elles décrivent les mécanismes employés, pas une qualification du matériel cible.
