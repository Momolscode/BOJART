# État courant — 1 novembre 2026

BOJ.ART vise un atelier artistique augmenté : conception, FDM/résine, finition, contenus, devis et suivi, coordonnés par Jarvis sur trois écrans. Ce projet reste indépendant d’UNUM et de M-Tek.

## Logiciel

Base M07 : `84aff373fe78db173e9601f285ce908f64587c55`. Les 437 fichiers du manifeste concordent avec les octets récupérés. Recette réexécutée : 578 tests Python et 7 tests de signal réussis. La recette navigateur historique ne mesure pas la tour réelle.

M07 conserve LangGraph et ses checkpoints SQLite, des dossiers CAO, trois vues avec reçus, un catalogue Studio et des brouillons Growth. CAO paramétrique bornée. Connecteurs imprimantes, découpe multi-pièces, publication et statistiques restent à raccorder.

La consolidation ajoute une mémoire documentaire locale : originaux préservés, versions, recherche FTS5 citée, import idempotent et restauration vérifiée. Le panneau `/memory` ajoute la recherche citée, les contextes bornés et les notes au statut proposition. Le lanceur indexe le contexte sélectionné dans la même base `memory.sqlite`. Le serveur MCP expose cette mémoire aux assistants compatibles. Les embeddings hybrides et la conversation via Ollama sont facultatifs, à configurer après essai local. Seuls les échanges de ce panneau sont mémorisés comme épisodes : les journaux de commandes M07 restent séparés. Ce n’est ni un entraînement de modèle ni une compréhension automatique des images.

Le lanceur vérifie le schéma, la configuration explicite et les imports natifs ; `--check-only` ajoute le contrôle des objets. La reprise JSON conserve versions et empreintes des sources. Voir `docs/DEMARRAGE_ET_REPRISE.md` pour la recette logicielle ; la tour réelle reste à qualifier.

Après restauration des cinq bases opérationnelles, une proposition antérieure d'affichage ou de création CAO ne peut plus déclencher de nouveau travail. Il faut préparer une nouvelle demande dans l'espace restauré. Les résultats déjà enregistrés et leurs reçus restent disponibles sans recalcul. Cette révocation persiste après redémarrage et nouvelle sauvegarde.

## Voix et Jev

Jev intervient après transcription sur texte et contexte structuré ; l’application vérifie ensuite ses choix. L’adaptateur vise le service TypeSafe `jev-1.14.0`, facultatif. Jev n’est ni ASR, ni TTS, ni autorité machine. Les ordres connus restent locaux. Micro, poids multilingues, précision française et moniteurs demandent une recette sur place. Pipecat est étudié, sans service actif.

## Création

**Le dernier geste R03** est la dernière coupe retrouvée : 9,25 s, 720 × 1280, 24 i/s. G1 pinceau est nouveau ; le personnage vient du TEST19 historique. Le plan G2 fidèle, son modèle exact et son rig manquent. Le retour positif après R02 ne valide pas un master final R03. L’audience n’est pas mesurée. Voir `creative/CURRENT.md`.

## Sites et données

Atelier V11 : `58309e61e2d70364b3a18223f706a478761da8b3`.
Studio V3 : `87306314a847c6d2f109bf5833345b3b80af22e1`.
Copies classées sous `sites/`, sans modification des publications. Leur raccordement à une base commune reste à faire.

Le catalogue couvre 1 060 emplacements de trois archives, deux sources de sites et du dépôt distant, soit 1016 contenus distincts. Ce n’est pas l’ensemble des conversations ou du PC. Les 100 résultats documentaires inventoriés sont des candidats, pas 100 contenus intégralement lus. Quatre MP4 de 48 octets restent signalés comme anomalies externes.

## Prochaines preuves

1. Installer sur la tour, importer les exports utiles, vérifier recherche et restauration.
2. Qualifier voix française, bruit, trois écrans, charge CAO et reprise après coupure.
3. Inventorier le parc, qualifier une FDM et une résine avec opérateur, puis étendre.

GPU, OS, modèles d’imprimantes et nombre exact de machines sont inconnus. Les mentions 7–8 puis « une dizaine » ne remplacent pas un inventaire.

## Complément de récupération vérifié

La collecte étendue de 219 sources est conservée sur les trois branches de récupération GitHub : 3 340 contenus uniques et leurs 6 445 emplacements vérifiés. Tous les contenus ont été restaurés depuis les commits distants puis comparés octet par octet aux trois ZIP d'origine. Les 87 fichiers du paquet créatif préparé et les 22 textes du transfert interrompu sont inclus. Voir `docs/ETAT_ARCHIVES_2026-11-01.md` pour la preuve et la commande de restauration commune. Ce périmètre dépasse le catalogue initial et ne doit pas lui être additionné. Il ne certifie pas la récupération intégrale des conversations ou du PC.

## Pilotage des prochaines sessions

Le registre `ops/orchestration.json` ordonne les domaines, les tâches et leurs dépendances. Le workflow d’audit produit un plan de lecture à chaque poussée à partir des empreintes existantes ; une observation contextuelle d’un autre SHA ne valide pas la révision courante. Voir `docs/ORCHESTRATION.md`. Le classement ne remplace pas la lecture des sources ni la qualification matérielle et artistique.

## Récupération approfondie

Le complément du 1 novembre ajoute 62 originaux distincts : 57 médias, quatre captures de conversations et un document de transport. Les 60 résultats et 41 URL de référence Higgsfield ont été téléchargés et comparés. Total avec la collecte initiale : 3 402 originaux indexés. Restauration des nouveaux octets depuis GitHub et comparaison aux téléchargements : réussies. Voir `docs/RECUPERATION_APPROFONDIE_2026-11-01.md`. Les conversations intégrales, les fichiers uniquement sur le PC, le modèle/rig G2 et une vidéo TikTok restent non récupérés ou non certifiés.
