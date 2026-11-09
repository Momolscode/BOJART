# État courant — 2 novembre 2026

## Chaîne vocale simulée — 2 novembre 2026

`tools/banc_voix.py` (ou `Mesurer_Voix_BOJART.cmd`) rejoue « Affiche le dashboard atelier » et ses variantes de l'audio au reçu d'affichage : 150 prises de synthèse Piper avec bruit d'atelier synthétique, passées par le vrai code navigateur (fin de prise, encodeur WAV), le vrai serveur, faster-whisper, `JarvisRuntime` (LangGraph, repli règles mesuré à part) et trois vues simulées ; chaque étape est chronométrée, 15 cas d'erreur et une sonde bruit seul. Sur conteneur Linux, `small` : aucune erreur critique (mauvaise vue, affichage non voulu) sur 830 prises, transcription ≈ 1 s, bout en bout ≈ 2,2 s au calme. Le vocabulaire de décodage ajouté à `voice.py` fait passer la commande cible de 12/80 à 65/80 sans élargir le routeur. Restent : fin de prise jamais automatique dès que le bruit est à 10 dB sous la parole (≈ 14 s), « dashboard dossiers » inaccessible à la voix (singulier entendu), voix de fond. Simulation seulement : ni la tour, ni un micro, ni une voix humaine. Voir `docs/BANC_VOIX.md` et `docs/evidence/voix-2026-11-02/README.md`.

## Banc de simulation pré-installation — 2 novembre 2026

`tools/banc_preinstallation.py` (ou `Banc_BOJART.cmd`) rejoue les 38 actions de Jarvis cataloguées dans `data/preinstallation/actions-jarvis.json` : toutes les suites (dont les suites Jarvis M02–M07, absentes de la CI jusque-là), 16 scénarios HTTP contre le vrai serveur avec trois écrans simulés, arrêt brutal et base corrompue, contrôles de corruption et pièges Windows, encodage cp1252 et roues Windows cp312. Corrigés : lanceurs `.cmd` en CRLF, `PYTHONUTF8` manquant, E/S texte sans UTF-8 explicite, message de base corrompue, chemins Windows non canoniques (noms courts 8.3) dans la restauration d'archive. Restent : médias M07, logo et polices du site hors dépôt, dépendances transitives non épinglées (traité depuis par les verrous Windows `jarvis/locks/`, générés par la CI Windows), reprise manuelle d'un tour reçu pendant un autre. Non codé dans `main` : figurine/découpe/tranchage (PR #15), inventaire et pilotage des imprimantes, devis. Simulation uniquement : aucune qualification de la tour, de la voix, des moniteurs ou des machines. Voir `docs/BANC_SIMULATION_PREINSTALLATION.md`.

## Audit transversal local V5 — 2 novembre 2026

La copie de passation intègre le distant c71628cf20426dd8b4bdedbab2dcf403f5135667 et les corrections locales antérieures. Les anciens comptes de fichiers/tests ci-dessous restent rattachés à leurs recettes ; le manifeste et les preuves V5 décrivent la livraison actuelle. Elle est publiée par rejeu exact de ses 926 fichiers puis réconciliée avec `b49101e`. Voir `docs/evidence/handoff-v5-2026-11-02/README.md`. Les rapports détaillés et les recettes du paquet restent hors du dépôt public.

Le profil matériel déclaré est dans `data/preinstallation/target-profile.json`. Les fonctions sont évaluées séparément : code, simulation, configuration disponible et qualification réelle. Les tableaux de bord ont des alias bornés ; le prototype de répartition de 1 m travaille sur 24 boîtes et 8 machines fictives, hors voix et sans géométrie réelle. Voir `docs/COMMANDES_DASHBOARD.md` et `docs/SIMULATIONS_ATELIER.md`.

La recherche V5 ajoute 31 références officielles, 15 propositions et 10 contrats de qualification : `docs/research/audit-transversal-2026-11-02/`. Les recettes restent non exécutées tant qu’aucun reçu ne les qualifie. Les données terrain sont des gabarits historiques ; elles ne remplacent ni un inventaire ni une mesure. Le contexte actif est nettoyé sans supprimer les originaux.


## Atelier : demandes, devis et parc simulé — 2 novembre 2026

La page `/atelier` de la console consolidée suit les demandes clients, calcule des devis versionnés et pilote un parc d'imprimantes **simulé**. Le devis reprend la formule `calculateQuote` d'Atelier V11, au centime, à partir des métadonnées PrusaSlicer/OrcaSlicer/Bambu Studio ou d'une estimation résine depuis un STL. Un devis émis est figé par empreintes ; l'accord client crée une commande sans autoriser la production.

Les ordres machine exigent une autorisation par machine et par action. Un résultat inconnu bloque la machine jusqu'à une lecture d'état. Les machines déclarées réelles ne reçoivent aucun ordre : aucun connecteur n'est raccordé. La restauration révoque les autorisations et rend inconnus les ordres en cours.

Un devis s'imprime en A4 (PDF par le navigateur) sans coût ni marge visibles ; un bandeau marque tout document non émis. Chaque commande compare le prévu aux mesures de l'opérateur, et l'entonnoir donne les délais réception → envoi → réponse. Aucun devis réel n'est émettable : grille, TVA et émetteur de BOJ.ART restent à saisir dans le formulaire de la page. Le parc réel reste à inventorier. Voir `docs/ATELIER_DEVIS_PARC.md` et `docs/evidence/atelier-devis-parc-2026-11-02/`. Codé et testé en isolation (47 tests atelier, parcours navigateur, banc de la PR #17 sur l'arbre fusionné) ; ni installé sur la tour, ni qualifié sur une machine.

## Robotique — STRATES, 2 novembre 2026

La session « bras robotique » porte sur la peinture au pinceau d’un relief mural stratifié. Elle est liée à l’atelier et à Jarvis. Un audit documentaire de 12 pages recommande un banc d’essai ciblé avant tout achat de cellule. Il faut d’abord figer une recette distincte des figurines, puis mesurer matière, contact et débordement ≤ 1 mm. Aucune performance physique n’est acquise.

Deux vidéos générées illustrent la direction artistique ; elles ne prouvent ni le dépôt ni la précision. La conversation source n’a pas été lue. Le PDF, ses montants et les médias restent hors du dépôt public. Voir `docs/research/strates-robotique-2026-11-02/README.md`.

La prochaine preuve est inscrite au registre de pilotage : tâche `strates-g0` dans `ops/orchestration.json`, bloquée tant que la fiche d’acceptation STRATES n’est pas signée. Elle ne déclenche ni mesure, ni achat, ni commande machine.

## Projet

BOJ.ART vise un atelier artistique augmenté : conception, FDM/résine, finition, contenus, devis et suivi, coordonnés par Jarvis sur trois écrans. Ce projet reste indépendant d’UNUM et de M-Tek.

## Logiciel

Base M07 : `84aff373fe78db173e9601f285ce908f64587c55`. Les 437 fichiers du manifeste concordent avec les octets récupérés. Recette réexécutée : 578 tests Python et 7 tests de signal réussis. La recette navigateur historique ne mesure pas la tour réelle.

M07 conserve LangGraph et ses checkpoints SQLite, des dossiers CAO, trois vues avec reçus, un catalogue Studio et des brouillons Growth. CAO paramétrique bornée. Connecteurs imprimantes, découpe multi-pièces, publication et statistiques restent à raccorder. Les devis et le parc simulé sont décrits plus haut (section Atelier).

La consolidation ajoute une mémoire documentaire locale : originaux préservés, versions, recherche FTS5 citée, import idempotent et restauration vérifiée. Le panneau `/memory` ajoute la recherche citée, les contextes bornés et les notes au statut proposition. Le lanceur indexe le contexte sélectionné dans la même base `memory.sqlite`. Le serveur MCP expose cette mémoire aux assistants compatibles. Les embeddings hybrides et la conversation via Ollama sont facultatifs, à configurer après essai local. Seuls les échanges de ce panneau sont mémorisés comme épisodes : les journaux de commandes M07 restent séparés. Ce n’est ni un entraînement de modèle ni une compréhension automatique des images.

Le lanceur vérifie le schéma, la configuration explicite et les imports natifs ; `--check-only` ajoute le contrôle des objets. La reprise JSON conserve versions et empreintes des sources. Voir `docs/DEMARRAGE_ET_REPRISE.md` pour la recette logicielle ; la tour réelle reste à qualifier.

Après restauration des cinq bases opérationnelles, une proposition antérieure d'affichage ou de création CAO ne peut plus déclencher de nouveau travail. Il faut préparer une nouvelle demande dans l'espace restauré. Les résultats déjà enregistrés et leurs reçus restent disponibles sans recalcul. Cette révocation persiste après redémarrage et nouvelle sauvegarde.

Le Studio gère un catalogue vide et permet de choisir une référence authentique et les passages du brief sans dépendre des identifiants des médias d'exemple. Les images statiques de démonstration ne servent plus de miniatures pour des sources locales non reliées à leur empreinte. Dans Studio et Growth, un changement de sélection écarte les réponses tardives et désactive l'export du résultat précédent. Ces contrôles ne rendent ni vidéo ni publication.

## Voix et Jev

Jev intervient après transcription sur texte et contexte structuré ; l’application vérifie ensuite ses choix. L’adaptateur vise le service TypeSafe `jev-1.14.0`, facultatif. Jev n’est ni ASR, ni TTS, ni autorité machine. Les ordres connus restent locaux. Micro, poids multilingues, précision française et moniteurs demandent une recette sur place ; le banc vocal simulé fixe la référence à comparer (`docs/BANC_VOIX.md`). Pipecat est étudié, sans service actif.

## Création

**Le dernier geste R03** est la dernière coupe retrouvée : 9,25 s, 720 × 1280, 24 i/s. G1 pinceau est nouveau ; le personnage vient du TEST19 historique. Le plan G2 fidèle, son modèle exact et son rig manquent. Le retour positif après R02 ne valide pas un master final R03. L’audience n’est pas mesurée. Voir `creative/CURRENT.md`.

## Sites et données

Atelier V11 : `58309e61e2d70364b3a18223f706a478761da8b3`.
Studio V3 : `87306314a847c6d2f109bf5833345b3b80af22e1`.
Copies classées sous `sites/`, sans modification des publications. Leur raccordement à une base commune reste à faire.

Le catalogue couvre 1 060 emplacements de trois archives, deux sources de sites et du dépôt distant, soit 1016 contenus distincts. Ce n’est pas l’ensemble des conversations ou du PC. Les 100 résultats documentaires inventoriés sont des candidats, pas 100 contenus intégralement lus. Quatre MP4 de 48 octets restent signalés comme anomalies externes.

## Prochaines preuves

Sélection d'outils et de skills du 1 novembre : voir `docs/research/launch-toolchain-2026-11-01/README.md`. Elle référence 18 dépôts à des commits examinés, 26 fiches, 14 besoins de données et les 12 portes de recette existantes. Les propositions sont indexées dans la mémoire ; aucun outil tiers n'est installé ou qualifié sur la tour par cette recherche. Metricool n'est pas retenu pour cette demande ; la collecte proposée utilise les données natives disponibles.

1. Installer sur la tour, importer les exports utiles, vérifier recherche et restauration.
2. Qualifier voix française, bruit, trois écrans, charge CAO et reprise après coupure.
3. Inventorier le parc, qualifier une FDM et une résine avec opérateur, puis étendre.

GPU : le 2 novembre, l'utilisateur indique une RTX 4060 Ti. Sa photo montre 8 Go de mémoire graphique, 16 Go de RAM, un Ryzen 5 5600G et Windows 11 Professionnel Insider Preview 25H2. Ces informations rapportées remplacent l'incertitude sur le poste ; elles ne prouvent ni pilote, ni VRAM libre, ni fonctionnement réel. Le stockage affiché de 932 GB n'est pas une mesure d'espace libre. Passage à 32 Go de RAM décidé, pas encore constaté. Voir `docs/memory/POSTE_RTX4060TI.md` et les décisions directes dans `docs/preinstallation/DECISIONS_UTILISATEUR.txt`. Les modèles d'imprimantes et le nombre exact de machines restent inconnus ; les mentions 7–8 puis « une dizaine » ne remplacent pas un inventaire.

## Mémoire : correction de reprise du 2 novembre

La copie locale V4 corrige la réservation des inférences concurrentes, le contrôle des extraits dérivés, la saturation du contexte par des contradictions hors sujet et la projection du registre par projet. Voir `docs/memory/HARDENING_2026-11-02.txt`. Les rapports V3 qui les décrivent ouverts sont historiques. La réception locale de ces invariants ne qualifie ni les vrais modèles ni les machines. Le correctif est publié avec la révision V5.

Le relevé du poste est désormais exécutable avec `Diagnostic_BOJART.cmd` ou `bash Diagnostic_BOJART.sh` : système, RAM, GPU NVIDIA/VRAM par carte, présence des outils et certaines versions. Voir `docs/DIAGNOSTIC_OUTILS.md`. Le rapport reste local ; une exécution dans l'environnement de développement ne confirme pas le matériel de la tour. Présence, version et qualification de la fonction restent distinctes.

## Complément de récupération vérifié

La collecte étendue de 219 sources est conservée sur les trois branches de récupération GitHub : 3 340 contenus uniques et leurs 6 445 emplacements vérifiés. Tous les contenus ont été restaurés depuis les commits distants puis comparés octet par octet aux trois ZIP d'origine. Les 87 fichiers du paquet créatif préparé et les 22 textes du transfert interrompu sont inclus. Voir `docs/ETAT_ARCHIVES_2026-11-01.md` pour la preuve et la commande de restauration commune. Ce périmètre dépasse le catalogue initial et ne doit pas lui être additionné. Il ne certifie pas la récupération intégrale des conversations ou du PC.

## Pilotage des prochaines sessions

Le registre `ops/orchestration.json` ordonne les domaines, les tâches et leurs dépendances. Le workflow d’audit produit un plan de lecture à chaque poussée à partir des empreintes existantes ; une observation contextuelle d’un autre SHA ne valide pas la révision courante. Voir `docs/ORCHESTRATION.md`. Le classement ne remplace pas la lecture des sources ni la qualification matérielle et artistique.

## Récupération approfondie

Le complément du 1 novembre ajoute 62 originaux distincts : 57 médias, quatre captures de conversations et un document de transport. Les 60 résultats et 41 URL de référence Higgsfield ont été téléchargés et comparés. Total avec la collecte initiale : 3 402 originaux indexés. Restauration des nouveaux octets depuis GitHub et comparaison aux téléchargements : réussies. Voir `docs/RECUPERATION_APPROFONDIE_2026-11-01.md`. Les conversations intégrales, les fichiers uniquement sur le PC, le modèle/rig G2 et une vidéo TikTok restent non récupérés ou non certifiés.

## Préparation des modèles — 2 novembre 2026

Trois profils locaux sont préparés : `speed`, `balanced`, `quality`. Voir `docs/research/MODELES_LOCAUX_2026-11-02.md` pour les candidats datés et `docs/memory/INSTALLATION_MODELES.md` pour le parcours exécutable. Celui-ci contrôle des réponses synthétiques, les temps et les vecteurs avant d'activer les réglages. La mémoire épingle les empreintes des modèles et refuse les changements observés pendant une inférence. Le contexte, la limite de sortie et le maintien en mémoire sont explicites. Ces ajouts ne constituent pas une installation ni une qualification de la tour, de la création ou de la voix.

Pour la RTX 4060 Ti 8 Go rapportée, le profil retenu pour essai est `speed` : Qwen3.5 4B Q4_K_M et Qwen3 Embedding 0.6B, contexte demandé de 16 384 tokens et réponse de 512 tokens maximum. `Installer_BOJART_4060Ti.cmd` prépare et mesure ce profil après installation de Python 3.12 et Ollama. Le contexte adapte ses sources et l'historique sous une enveloppe UTF-8, sans couper de fait, passage ou champ historique ni relancer la recherche. Les originaux sont conservés. Aucun modèle réel n'a été essayé sur le poste pendant cette préparation.

## Chaîne figurine M08 — 2 novembre 2026

Premier parcours reproductible « demande → figurine → visualisation → tranchage » : `jarvis/tools/figurine_pipeline.py`. La phrase passe par le point d'entrée texte de Jarvis (`dialogue.interpret`, intention `create_figurine`). Niveau N2 obtenu dans un conteneur Linux sans GPU sur le personnage original de contrôle : maillage fermé, contrôles calculés, socle à tenons détrompés, rendus Blender, visionneuse vérifiée dans Chromium, tranchage PrusaSlicer 2.7.2 avec profil d'hypothèse. La voix, la tour, le tableau de bord réel et l'impression restent non testés. Le cas Végéta est compris mais bloqué avant toute géométrie (droits). Le 2 novembre, Olsen a choisi à la place un guerrier original et vendable, « Ardoise, le duelliste des strates » : même chaîne, même niveau N2, fichiers dans le dossier du projet `figurine-m08/ardoise/`. Le même jour, Olsen a jugé le détail insuffisant : Ardoise v6 ajoute visage construit, poings, rivets, gravures, plis et socle en strates d'ardoise, selon une grille de conception sourcée (`jarvis/docs/m08/GRILLE_CONCEPTION_FIGURINE.md`, fiche D13). Les dépendances de la chaîne s'installent avec celles de Jarvis (trimesh 4.11.1 commun, résolution Windows Python 3.12 vérifiée sans installation). Le `three.core.js` manquant de l'Atelier, vu sur l'ancienne base de la branche, était déjà réparé sur `main`. Pour Végéta (pièce de collection, pas de vente), Olsen a choisi un fichier de fan imprimé à la maison (fiche D14) : en attente du fichier ; le socle d'exposition pour une figurine officielle reste prêt (`jarvis/tools/socle_vitrine.py`, fiche D15). Le 3 novembre : Veille, héroïne du film « Un seul trait », sur socle de basalte (fiche D16) ; Fusain, lutteur original dans le style des pièces de BOJ (fiche D17). Voir `jarvis/docs/m08/`.
