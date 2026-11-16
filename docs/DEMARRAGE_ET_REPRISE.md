# Démarrage et reprise de session

L’installation de départ est décrite dans [INSTALLER_DEMAIN.md](../INSTALLER_DEMAIN.md). Elle initialise la mémoire avec Python 3.12. Les moteurs CAO, la voix et les modèles locaux se préparent séparément.

## Vérifier avant ouverture

Depuis le Python de `.venv` :

```bash
python tools/start_jarvis.py --check-only
```

Le diagnostic importe réellement les moteurs CAO/LangGraph dans un processus borné et contrôle les objets de la mémoire existante. Il n’indexe pas les documents, ne lance pas le serveur et ne crée pas de nouveaux dossiers de données. Un chemin `--config` explicite doit exister et être valide. Un paquet présent avec un import natif défaillant reste indisponible.

Le code de sortie `2` signale des prérequis manquants ou un problème de données/configuration ; lire `workstation_blockers`. `memory_ready` concerne Python/FTS5. `workstation_ready` concerne les dépendances CAO/média et la voix si elle est demandée. LangGraph et les modèles restent facultatifs, avec leurs replis documentés. La qualification matérielle reste distincte.

Ajouter `--check-tools` relève aussi le matériel et les outils de création disponibles sur ce poste, sans initialiser les données. Le [diagnostic des outils](DIAGNOSTIC_OUTILS.md) peut également s'exécuter séparément et enregistrer un rapport privé. Ces observations n'activent aucune porte de qualification.

`Lancer_BOJART` ouvre par défaut la mémoire et les fonctions disponibles, en annonçant les moteurs manquants. Pour exiger aussi les dépendances du poste :

```bash
python tools/start_jarvis.py --require-workstation
```

Les problèmes de schéma/configuration ou de dossiers imbriqués restent bloquants dans tous les modes. La vérification profonde des objets est explicite (`--check-only` ou `tools/doctor.py --verify-memory`) ; un lancement normal contrôle le schéma puis les sources utilisées pour l’index et la recherche.

Les données M07 (`--state`) et la mémoire (`BOJART_MEMORY_STATE`) doivent être dans des dossiers distincts et non imbriqués. CLI, lanceur, interface et MCP partagent le même emplacement mémoire par défaut. L’option explicite `--state` des commandes mémoire garde priorité sur l’environnement.

## Transmettre le contexte

1. Dans **Mémoire du projet**, choisir le domaine et poser une question précise.
2. Utiliser **Préparer le contexte**, puis **Copier le contexte** ou **Télécharger la reprise**.
3. Transmettre le JSON à la prochaine session choisie : texte, statuts, versions et empreintes des passages, références du registre et éléments écartés.
4. Lire le code concerné avant modification. Après travail, consigner les nouvelles preuves et décisions, puis actualiser l’index.

Le budget compte les caractères Unicode du champ `text`, pas les jetons d’un modèle ni toute la taille du JSON. Le SHA-256 porte sur ce texte exact. Les empreintes identifient les sources ; elles ne certifient pas la vérité d’une affirmation. Une source altérée est écartée ou produit une erreur. Les notes restent des propositions jusqu’à revue.

Le téléchargement reste local et peut contenir tes données importées : vérifier son contenu avant partage. Changer de domaine ou de question invalide les anciens résultats. Une réponse tardive ne remplace pas le nouveau contexte.

La recherche donne d’abord une place aux sources distinctes, puis complète avec les autres passages. La sélection intervient avant la limite de passages, en recherche lexicale et sémantique, puis après leur fusion : un document long ne masque plus une source plus courte en remplissant une fenêtre intermédiaire. Le nombre final de résultats et le budget de contexte restent bornés ; cette diversification ne prouve pas la pertinence sémantique.

Si une source retrouvée est absente ou altérée, son exclusion est signalée dans la recherche et le contexte. Une réponse du modèle sans citation reconnue est également signalée. Une citation reconnue n’est pas une validation de la réponse.

La régression dédiée utilise deux documents synthétiques et plus de 200 passages, ainsi qu’un double d’embeddings sans appel de modèle : `python -m unittest discover -s tests_agent -p 'test_retrieval_diversity.py' -v`.

```bash
python -m bojart_memory.agent_cli context "Que manque-t-il pour G2 ?" --project bojart.creative
python -m bojart_memory.agent_cli context "Comment restaurer la mémoire ?" --project bojart.jarvis
```

## Recette reproductible

```bash
python tools/check_startup.py --output .bojart-audit/startup.json
```

Données temporaires : deux démarrages par le vrai lanceur, session HTTP authentifiée, contexte inchangé après redémarrage, absence de doublons et restauration dans un nouveau dossier sans dépôt source. Les données de travail du propriétaire ne sont pas utilisées.

Avec Playwright et un Chromium déjà disponibles, `--browser --chromium CHEMIN_CHROMIUM` ajoute les contrôles d’interface, de téléchargement, de réponse périmée et de rendu mobile. Aucun navigateur n’est téléchargé. La recette sans navigateur est exécutée à chaque push/PR par le workflow de continuité.

Preuves : [startup-2026-11-01.json](evidence/startup-2026-11-01.json). Les essais sur cet hôte Linux ne remplacent pas la recette du GPU, du micro, des trois moniteurs ou des imprimantes de l’atelier.

## Interruption pendant une mise à jour

Les imports documentaires sont désormais validés par lot complet. Une erreur conserve les références précédentes, et la construction d’un contexte utilise un même instantané pour ses faits et ses passages. Voir [la recette de résilience mémoire](memory/RESILIENCE.md).

Pour simuler un arrêt forcé du processus avec des données temporaires : `python tools/check_startup.py --abrupt --output .bojart-audit/forced-restart.json`.

Sous Windows, le serveur reste dans le processus du lanceur. La recette d’arrêt forcé vérifie sa fermeture et la réouverture du même dossier, sans serveur orphelin.
