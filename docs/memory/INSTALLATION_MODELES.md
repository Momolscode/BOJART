# Installer et mesurer les modèles de Jarvis

Ce parcours active la conversation textuelle du panneau **Mémoire du projet** et la recherche sémantique dans la mémoire existante. Les commandes d'affichage M07 gardent leur circuit local. La voix, la génération d'images et les imprimantes ont des installations distinctes.

## 1. Choisir un profil après inventaire

Ouvrir Jarvis et consulter son diagnostic matériel, ou relever le modèle de GPU, sa VRAM et la RAM du poste. Lire la [sélection datée](../research/MODELES_LOCAUX_2026-11-02.md). Les trois profils disponibles sont `speed`, `balanced` et `quality`. Aucun profil n'est choisi à partir du prix de l'ordinateur.

Pour afficher les profils sans réseau, sans création de mémoire et sans téléchargement :

```bash
python tools/setup_local_models.py
```

Installer puis démarrer [Ollama](https://ollama.com/download). Le service doit répondre sur `http://127.0.0.1:11434`, ou sur le port local déjà renseigné dans `models.json`.

## 2. Préparation complète

Depuis le dossier BOJART, sous Windows, exemple pour le profil intermédiaire :

```powershell
py -3.12 tools/prepare_installation.py --model-profile balanced --download-models
```

Sous Linux :

```bash
python3.12 tools/prepare_installation.py --model-profile balanced --download-models
```

Remplacer `balanced` par le profil choisi. Le téléchargement est explicitement demandé par `--download-models` ; sans ce paramètre, les modèles doivent déjà être présents. Seuls les deux modèles du profil sont concernés. L'installation d'Ollama elle-même reste une étape préalable.

Si l'environnement BOJART est déjà prêt :

```powershell
.venv\Scripts\python.exe tools/setup_local_models.py --profile balanced --apply --download
```

```bash
.venv/bin/python tools/setup_local_models.py --profile balanced --apply --download
```

Ces commandes sont des alternatives selon le système, pas des étapes à cumuler. Le téléchargement peut prendre du temps. Le programme appelle le binaire Ollama installé avec des arguments fixes ; il ne télécharge pas un script à exécuter.

## 3. Ce que le programme vérifie

1. Configuration existante lisible, service local et capacités déclarées des modèles.
2. Trois vecteurs synthétiques : dimensions cohérentes, doublon proche et texte distinct différent.
3. Quatre réponses synthétiques : projet BOJ.ART, VRAM inconnue, texte importé trompeur, référence au sein d'un contexte plus long.
4. Temps complet de chaque appel et statistiques que fournit Ollama. Le premier appel peut déjà être chaud ; il n'est pas présenté comme un démarrage à froid garanti. Les trois suivants doivent respecter le seuil du profil.
5. Index documentaire et vecteurs dans le même `memory.sqlite` ; empreintes encore identiques après indexation.
6. Écriture atomique du nouveau `models.json` seulement après réussite de ces étapes.

Une panne, un contrôle échoué ou une indexation interrompue conserve les anciens réglages de modèles. Des documents et vecteurs ont pu être ajoutés à la même mémoire ; ils restent versionnés et les vecteurs gardent leur empreinte de modèle. Relancer reprend les éléments manquants. Un téléchargement déjà réussi reste dans Ollama.

Un rapport `model-qualification-IDENTIFIANT.json` est créé dans le dossier privé de mémoire. Il contient uniquement les réponses aux exemples synthétiques, les mesures et les empreintes ; pas d'export automatique des conversations. Code de retour 0 : profil activé après ces essais. Code 2 : échec des contrôles ou de l’activation ; une autre erreur d’interruption peut retourner un autre code non nul. `production_ready` reste faux : quelques essais logiciels ne qualifient pas tout l'atelier.

Les seuils sont des objectifs d'essai, pas une promesse de vitesse. `--max-followup-ms 12000` permet un seuil choisi explicitement ; augmenter ce nombre ne rend pas le modèle plus rapide. Lire les réponses du rapport, puis tester de vraies questions BOJ.ART. Les quatre contrôles utilisent des critères textuels limités et ne prouvent pas une résistance générale aux instructions trompeuses.

## 4. Ouvrir et conserver les preuves

Lancer BOJART puis **Mémoire du projet → Parler à Jarvis**. Vérifier une réponse citée, fermer, relancer et vérifier la continuité. Le panneau reste textuel et ne déclenche aucune commande machine par une réponse de modèle.

```bash
python -m bojart_memory.agent_cli models
python tools/evaluate_memory.py
```

La deuxième commande mesure la recherche lexicale sur les documents du dépôt ; ce n'est pas un score du nouveau LLM ou des embeddings. Les rapports de modèle conservent leurs propres mesures.

`model_changed` signifie que le tag local ne correspond plus à l'empreinte configurée : refaire les essais du profil. Les anciennes réponses et les anciens vecteurs ne sont pas réétiquetés. La recherche par mots reste disponible si la recherche sémantique est indisponible. Les vérifications avant/après inférence détectent les changements observés de tag ; elles ne constituent pas un verrou interprocessus sur le gestionnaire de modèles.

Un `models.json` invalide doit être conservé puis renommé avant une nouvelle préparation ; ne pas déplacer `memory.sqlite` ou `objects` pour réparer les réglages. Une seule préparation de modèles à la fois. Conserver séparément `models.json` et les rapports avec les sauvegardes privées : ils ne sont pas inclus automatiquement dans la sauvegarde documentaire.

Réglages : `chat_options` accepte `num_ctx` de 8192 à 65536, `num_predict` de 128 à 2048, `think` booléen et `keep_alive` de 0 à 1800 secondes. Les profils demandent 32768, 768, faux et 300. Modifier un réglage impose de remesurer la configuration ; le résultat précédent ne prouve pas la nouvelle vitesse. Le garde de taille peut refuser un long paquet au lieu de laisser le serveur le tronquer silencieusement. Le temps au premier token et la diffusion progressive à l'écran restent non mesurés/non raccordés par ce parcours.
