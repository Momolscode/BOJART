# Consolidation BOJ.ART — 30 octobre 2026

## État précis
Cette livraison crée un dépôt Git local et un coffre des originaux. Aucune publication GitHub n'a été réalisée. Aucun site hébergé, compte social, machine ou fichier du PC utilisateur n'a été modifié.

## Changements applicatifs effectifs
La base de départ est Mission 03, contenant les Missions 01 et 02. L'extension ajoute :
- un seul serveur local pour dialogue, Studio et recherche métier ;
- une page `/knowledge` servant les 54 fiches, leurs sources et leur statut ;
- `GET /api/knowledge/search` avec recherche FTS5 textuelle, sans LLM ;
- `GET /api/context/distilled` pour un contexte versionné et identifié par SHA-256 ;
- `GET /api/control/state` exposant honnêtement les capacités et les connexions absentes ;
- `POST /api/control/prepare` qui prépare des commandes d'affichage connues avec projet, révision, tour de parole et référence du modèle.

Les requêtes utilisent la session locale et les contrôles d'origine du serveur existant. La recherche ouvre une base en mémoire par requête, sans partage d'une connexion SQLite entre threads. Les sources du corpus ne sont pas des autorisations d'exécuter.

## Affichage : ne pas confondre préparation et exécution
Une commande comme « affiche le modèle à droite » retrouve un GLB contrôlé et prépare une proposition liée au dossier. Les répétitions identiques retrouvent le même reçu ; un identifiant réutilisé pour un contenu différent est refusé. Une version ou un fichier modifié rend la proposition périmée. L'ordonnanceur n'appelle pas Jev pour ces ordres connus.

**Le transport vers trois moniteurs physiques n'est PAS raccordé.** `executed=false` et `display_acknowledged=false` restent explicites. « Arrête de parler » ne signifie pas « arrête l'impression » : la proposition concerne seulement la parole. Les commandes machines et toute instruction inconnue sont refusées par cette extension.

## Démarrage
Les lanceurs à la racine utilisent l'environnement Python `.venv` s'il existe. Sinon ils essaient Python déjà installé. Ils n'installent ni ne mettent à jour automatiquement une dépendance. L'état neuf est conservé dans `~/BOJART/consolidated-2026-10-30` pour ne pas écraser l'état M02/M03. Le service n'écoute que `127.0.0.1`.

Les lanceurs historiques restent dans `apps/jarvis/`. La version courante est lancée depuis la racine consolidée. L'ancien manifeste M03 est conservé dans `apps/jarvis/heritage/MANIFESTE_SOURCE_M03.json` ; il décrit l'entrée historique, pas les modifications présentes. Le manifeste de livraison courant est `preservation/REPOSITORY_MANIFEST.json`.

## Pas installé / pas validé ici
Aucun Pipecat, LangGraph, moteur Jev actif, transcripteur réel, modèle Ollama chargé, appairage de moniteurs, connexion imprimante ou synchronisation du site public. Le laboratoire planning emploie des données fictives. Les contenus générés ne prouvent pas la fidélité artistique ; les socles n'ont pas été imprimés ou testés mécaniquement.

## Recette
Les journaux datés de cette livraison sont dans `proofs/current/`. Les tests hérités vérifient la non-régression ; ils ne doivent pas être additionnés une seconde fois aux sous-ensembles historiques. Les tests HTTP utilisent le vrai serveur local. Aucune revue graphique sur navigateur ni essai des trois écrans physiques n'est revendiqué pour cette consolidation. La publication GitHub n'a été testée qu'en mode plan/validation, sans accès distant d'écriture.
