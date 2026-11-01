# Passation — consolidation du 1 novembre 2026

Demande : orchestrer les poussées vers `Momolscode/BOJART`, classer la direction artistique et Jarvis, améliorer la continuité et préparer la gestion future des données sur la tour.

Sources examinées : M07, archive créative préparée pour GitHub, sources R01–R03, notes actuelles, sources Sites V11/V3 et BOJART à `6bc5645c23eeec5e2b7f707b46fde8a0c64a1b5f` avant consolidation. Provenance : `data/catalog/` et `data/knowledge/sources.json`.

Décisions : conserver les chemins relatifs du runtime dans `jarvis/`; séparer sites, création et mémoire ; conserver les variantes/rejets ; garder les médias personnels hors du dépôt public. Le contexte courant corrige l’audit arrêté à R02. Aucun nouveau rendu payant ni publication de site/réseau n’a été lancé.

Chaque prochaine passation contient : objectif, sources datées, faits nouveaux, décisions, fichiers modifiés, tests réellement exécutés, limites et prochaine preuve. Citer la décision remplacée. Un conflit non résolu reste visible ; le fichier le plus récent n’est pas automatiquement le plus vrai.

Le runtime local n’accède pas automatiquement aux anciens chats ni à leurs pièces jointes. Importer les exports autorisés ou intégrer un connecteur documenté dont on teste la couverture.

Concurrence détectée : la branche a avancé vers `1ca60c3571c78f9303b8b4d54e82e34ae3e439f7`. Les 23 nouveaux chemins distants et les évolutions README/PRODUCTION ont été récupérés et rapprochés. `productions/` reste la racine des recettes exécutables ; `creative/` conserve la direction.

Deux avances supplémentaires ont été rapprochées : `b68878fc5040a15dcee9a89ca415a94cbc946880` et `0c72455bec644dafffc142b5d72fcf81b8d9b1ac`. Leurs neuf nouveaux fichiers historiques et de génération sont conservés, ainsi que la clarification de couverture du README dans `docs/CREATIVE_PIPELINE_HISTORIQUE.md`. Les liens directs vers des médias personnels ont été retirés de la version publique courante ; cela ne modifie pas les anciens commits.

Dernière réconciliation : `cd71c6ba640f304248702d8a3e64c60f900f9d0b`, avec le module `bojart_ops`, ses tests et son workflow, les corrections du contrôle artistique et les observations de génération. Leur publication concurrente est conservée comme parent de la consolidation.

## Préparation mémoire — 1 novembre 2026

Extension intégrée sur la consolidation `30b3fb9858d81e5499d0a51ed8df6c317b771d7c`, sans second magasin documentaire. Voir `INSTALLER_DEMAIN.md`, `docs/memory/MCP.md` et `docs/memory/VALIDATION.json`. Installation prévue le 2 novembre ; OS non décidé. Les modèles sont facultatifs et non téléchargés. Les faits de référence viennent du registre sourcé ; les notes locales sont des propositions. La sauvegarde documentaire existante inclut les tables supplémentaires. Les sauvegardes opérationnelles M07 restent distinctes.

## Complément de transfert — 1 novembre 2026

Demande : pousser sur GitHub BOJ.ART. Base distante relue : `1d76c6876de54c7bc37b777ae66bf031207a140d`. Les 694 blobs du dépôt ont été restaurés avec vérification de leur empreinte Git avant préparation. Le paquet créatif actuel est déjà représenté par le catalogue initial et ses documents publics ; aucune ancienne variante ne remplace la version courante.

Trois archives de récupération ont passé CRC et SHA-256, puis les 3 340 contenus uniques ont été relus et contrôlés par taille et SHA-256. Les 6 445 emplacements se rattachent à 219 sources connues. Ajouts : catalogue public de provenance, note originale Jarvis 5, guide de restauration et entrée dans la mémoire documentaire. Le mode d’emploi de récupération, ajouté simultanément par une autre session, est réutilisé sans doublon. Les contenus multimédias et archives restent externes, explicitement signalés. Les tests logiciels hérités ne sont pas une conséquence de cette vérification de données.

Réconciliation avant envoi : les évolutions distantes jusqu’à `9a78aab6987905030e96112d0229ae0ba8ae53a5` sont préservées, y compris l’extension mémoire, les lanceurs et la correction des tests Windows.
