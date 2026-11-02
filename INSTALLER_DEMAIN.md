# Jarvis : installation du 2 novembre 2026

Le dépôt contient le code M07 et son contexte de départ. La mémoire fonctionne avec Python 3.12 et SQLite FTS5, sans service payant. Le poste réel, ses modèles IA et ses périphériques restent à qualifier.

## 1. Préparer le poste

Installer Python **3.12** depuis [python.org](https://www.python.org/downloads/). Sous Linux, prévoir le paquet `venv` correspondant si le système le sépare. Récupérer ce dépôt avec Git ou **Code → Download ZIP**, puis extraire entièrement le ZIP dans un dossier utilisateur accessible en écriture.

Windows, sur le poste **RTX 4060 Ti 8 Go / RAM 16 Go** indiqué par l'utilisateur : double-cliquer **Installer_Tout_BOJART.cmd**. Il détecte ce qui manque, affiche le plan et demande **un seul accord**, puis enchaîne seul : Python 3.12 (s'il manque, avec une question à part), Ollama et FFmpeg avec winget, démarrage d'Ollama, Jarvis complet depuis le verrou Windows (mémoire, CAO, orchestration, voix), modèles du profil `speed` testés avant activation, puis le banc de contrôle. Chaque étape est écrite dans `%USERPROFILE%\BOJART\installation\` ; une étape en échec n'arrête que celles qui en dépendent, et une relance reprend sans effacer la mémoire. `python tools/installer_tout.py --simulation` montre le plan sans rien installer. Ce parcours est simulé par le banc et la CI Windows, pas encore exécuté sur la tour. Après réussite, ouvrir **Lancer_BOJART.cmd**. Voir le [guide dédié au poste](docs/memory/POSTE_RTX4060TI.md) pour les réglages et la recette.

**Installer_BOJART_4060Ti.cmd** reste disponible pour la mémoire et les modèles seuls (Ollama déjà installé et démarré), sans CAO, orchestration ni voix.

Pour préparer uniquement la mémoire, sans télécharger de modèles : **Installer_BOJART.cmd**, puis **Lancer_BOJART.cmd**.

Linux, dans le dossier extrait :

```bash
bash Installer_BOJART.sh
bash Lancer_BOJART.sh
```

L’installeur prépare `.venv`, indexe les documents et vérifie Python/FTS5. Le lanceur ouvre Jarvis ; choisir **Mémoire du projet**. Si le navigateur ne s’ouvre pas : `Lancer_BOJART.cmd --no-browser` ou `bash Lancer_BOJART.sh --no-browser`, puis ouvrir l’URL privée affichée. Garder la fenêtre du lanceur ouverte.

Le lanceur annonce les moteurs manquants. `Lancer_BOJART.cmd --check-only` ou `bash Lancer_BOJART.sh --check-only` effectue le contrôle avant ouverture. Voir [démarrage et reprise](docs/DEMARRAGE_ET_REPRISE.md) pour interpréter le rapport et télécharger un contexte sourcé.

Les raccourcis `Lancer_Jarvis` présents dans `jarvis/` et `jarvis/apps/jarvis/` rejoignent aussi ce lanceur. Depuis `jarvis/`, `Ouvrir_un_dossier_Jarvis.cmd` ou `bash Ouvrir_un_dossier_Jarvis.sh` ouvre un dossier existant avec le même environnement et la même mémoire. `Restaurer_Jarvis` utilise également le Python installé à la racine pour restaurer dans un nouveau dossier.

L’index est actualisé à chaque lancement. Aucune configuration du GPU n’est présumée. L’installateur peut être relancé sans effacer la mémoire.

## 2. Ce qui est disponible immédiatement

- Recherche des sources avec chemins, lignes et empreintes.
- Faits datés, décisions, corrections et contradictions ; séparation Jarvis, création et sites.
- Contexte à copier pour une tâche ; notes locales au statut proposition.
- Sauvegarde/restauration des documents, notes, épisodes et vecteurs.
- [Serveur MCP](docs/memory/MCP.md) pour un assistant de code compatible.

Les moteurs CAO/LangGraph, la voix et les modèles Ollama sont des installations explicites. La recherche ne dépend pas d’eux. Pour CAO et LangGraph :

```powershell
py -3.12 tools/prepare_installation.py --engines
```

Linux : remplacer `py -3.12` par `python3.12`. Ajouter `--voice` pour les bibliothèques voix ; les poids, FFmpeg, le micro et la configuration restent à préparer selon [INSTALLATION.md](docs/INSTALLATION.md). Sous Windows, l’installateur installe le **verrou** `jarvis/locks/windows-cp312-<profil>.txt` : toutes les versions, dépendances indirectes comprises, avec l’empreinte SHA-256 de chaque roue (`pip install --require-hashes --no-deps`, puis `pip check`). C’est l’environnement installé et testé par la CI Windows du banc. Si le verrou manque ou ne correspond plus aux requirements, l’installateur le dit et revient aux versions principales épinglées. L’installation n’a pas encore été essayée sur le poste lui-même.

## 3. Installer les modèles locaux choisis

La [sélection du 2 novembre](docs/research/MODELES_LOCAUX_2026-11-02.md) propose trois profils : `speed` (Qwen3.5 4B), `balanced` (Gemma 4 12B) et `quality` (Qwen3.8 27B). Tous utilisent Qwen3 Embedding 0.6B. Pour le poste RTX 4060 Ti 8 Go rapporté, retenir **`speed`** pour le premier essai. Les tailles de poids ne sont pas toute la VRAM nécessaire.

Installer et démarrer [Ollama](https://ollama.com/download). Commande Windows équivalente à l'installeur dédié ; inutile de la répéter après une installation réussie :

```powershell
py -3.12 tools/prepare_installation.py --model-profile speed --download-models
```

Linux : remplacer `py -3.12` par `python3.12`. Cette commande prépare aussi l'environnement Python, télécharge seulement les modèles manquants du profil, mesure quatre réponses synthétiques, contrôle les embeddings et indexe la mémoire. Les nouveaux réglages sont activés seulement après réussite. Sans `--download-models`, les modèles doivent déjà être installés. Une seule préparation à la fois.

Le [guide des modèles](docs/memory/INSTALLATION_MODELES.md) explique les profils, seuils, rapports privés et réparations. Les poids téléchargés restent locaux ; aucun service d'inférence payant n'est appelé. Les empreintes sont conservées et contrôlées avant/après les inférences pour éviter le mélange de modèles après une mise à jour. Une panne du modèle laisse la recherche par mots disponible.

Pour **Parler à Jarvis**, ouvrir **Mémoire du projet** après activation. Les échanges et leur contexte exact sont conservés ; les réponses restent à vérifier. L'historique écarte les anciennes réponses dont les preuves ont changé : voir [continuité des conversations](docs/memory/CONVERSATIONS.md). Le panneau n'exécute pas de commandes d'atelier. Les générateurs d'images, la voix et les imprimantes ne sont pas activés par ces profils.

Si un modèle local est déjà choisi hors de ces profils, les commandes `python -m bojart_memory.agent_cli configure --chat-model NOM_LOCAL` et `--embedding-model NOM_LOCAL` restent disponibles. Cette configuration manuelle vérifie seulement les métadonnées ; elle ne remplace pas les essais. Exécuter `python -m bojart_memory.agent_cli embed` après ajout de documents pour actualiser les vecteurs.

## 4. Contrôle avant travail réel

1. Rechercher « rôle Jev » dans Jarvis ; « G2 » dans Création. Vérifier les sources et les inconnues.
2. Ajouter une note datée, fermer Jarvis, relancer et retrouver cette note.
3. Dans Mémoire, créer une sauvegarde. Tester sa restauration dans un **nouveau** dossier :

```bash
python -m bojart_memory restore CHEMIN_SAUVEGARDE CHEMIN_NOUVELLE_MEMOIRE
python -m bojart_memory --state CHEMIN_NOUVELLE_MEMOIRE verify
```

4. Faire l’inventaire du PC, du GPU, des écrans et du micro avant d’activer les fonctions correspondantes. Les imprimantes ne sont pas raccordées par cette installation.

La mémoire privée est dans `~/BOJART/memory` (`%USERPROFILE%\BOJART\memory` sous Windows). `BOJART_MEMORY_STATE` permet un autre emplacement. Les sauvegardes du panneau vont dans le dossier voisin `memory-backups`. Elles incluent la base et ses originaux ; la configuration Ollama et le rapport d’installation sont à recopier séparément. Les sauvegardes des dossiers M07 restent distinctes.

Les conversations ChatGPT antérieures ne se synchronisent pas automatiquement. Pour importer un export choisi :

```bash
python -m bojart_memory ingest CHEMIN_EXPORT --project bojart.jarvis --collection sessions --provenance "Export sélectionné, origine et date"
```

Les originaux restent hors du dépôt public. Consulter [OUTILS_ET_ARCHITECTURE.md](docs/memory/OUTILS_ET_ARCHITECTURE.md) pour les choix techniques et [VALIDATION.json](docs/memory/VALIDATION.json) pour la portée des essais.
