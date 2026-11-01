# Jarvis : installation du 2 novembre 2026

Le dépôt contient le code M07 et son contexte de départ. La mémoire fonctionne avec Python 3.12 et SQLite FTS5, sans service payant. Le poste réel, ses modèles IA et ses périphériques restent à qualifier.

## 1. Préparer le poste

Installer Python **3.12** depuis [python.org](https://www.python.org/downloads/). Sous Linux, prévoir le paquet `venv` correspondant si le système le sépare. Récupérer ce dépôt avec Git ou **Code → Download ZIP**, puis extraire entièrement le ZIP dans un dossier utilisateur accessible en écriture.

Windows : double-cliquer **Installer_BOJART.cmd**, puis **Lancer_BOJART.cmd**.

Linux, dans le dossier extrait :

```bash
bash Installer_BOJART.sh
bash Lancer_BOJART.sh
```

L’installeur prépare `.venv`, indexe les documents et vérifie Python/FTS5. Le lanceur ouvre Jarvis ; choisir **Mémoire du projet**. Si le navigateur ne s’ouvre pas : `Lancer_BOJART.cmd --no-browser` ou `bash Lancer_BOJART.sh --no-browser`, puis ouvrir l’URL privée affichée. Garder la fenêtre du lanceur ouverte.

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

Linux : remplacer `py -3.12` par `python3.12`. Ajouter `--voice` pour les bibliothèques voix ; les poids, FFmpeg, le micro et la configuration restent à préparer selon [INSTALLATION.md](docs/INSTALLATION.md). Les versions M07 sont fixées ; leur installation Windows n’a pas encore été essayée sur le poste.

## 3. Activer la recherche sémantique locale

Installer [Ollama](https://ollama.com/download), le démarrer, puis télécharger explicitement le modèle :

```bash
ollama pull embeddinggemma
```

Depuis le dépôt avec le Python de `.venv` :

```bash
python -m bojart_memory.agent_cli configure --embedding-model embeddinggemma
python -m bojart_memory.agent_cli embed
```

Dans ces commandes, utiliser `.venv\Scripts\python.exe` sous Windows ou `.venv/bin/python` sous Linux. Relancer `embed` après l’ajout de documents. Le modèle doit être présent localement. Si Ollama est arrêté, la recherche par mots continue. Les vecteurs sont associés à l’empreinte exacte du modèle ; changer de modèle nécessite sa propre indexation.

Pour **Parler à Jarvis**, choisir un modèle de conversation adapté à la RAM/VRAM, le télécharger dans Ollama, puis exécuter `python -m bojart_memory.agent_cli configure --chat-model NOM_LOCAL`. Aucun modèle de conversation universel n’est présélectionné. Les échanges de ce panneau et leur contexte exact sont conservés ; les réponses restent à vérifier. Le panneau n’exécute pas de commandes d’atelier.

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
