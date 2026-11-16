# Jarvis sur le poste RTX 4060 Ti de BOJ.ART

Préparation du 2 novembre 2026, heure de Paris. La carte est déclarée par l'utilisateur ; les autres caractéristiques sont lues sur sa photo des informations système. Il ne s'agit pas d'un diagnostic exécuté sur le PC. Sources du registre : `hardware-user-20261102`, `hardware-photo-20261102`. La photo et les identifiants Windows restent hors du dépôt.

| Élément | Information reçue |
| --- | --- |
| GPU | NVIDIA GeForce RTX 4060 Ti, d'après l'utilisateur |
| Mémoire graphique | 8 Go affichés sur la photo |
| RAM | 16 Go |
| Processeur | AMD Ryzen 5 5600G |
| Système | Windows 11 Professionnel Insider Preview, 25H2 |
| Stockage | 932 GB affichés ; espace libre non établi |

La VRAM actuellement libre, le pilote, l'espace disque libre et la stabilité sous charge restent à mesurer. NVIDIA distribue des variantes 8 et 16 Go de cette carte ; ce parcours retient les **8 Go visibles sur la photo**. Références : [carte NVIDIA](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4060-4060ti/), [compatibilité GPU Ollama](https://docs.ollama.com/gpu).

## Profil retenu pour le premier essai

`speed` : **Qwen3.5 4B Q4_K_M** pour la conversation et **Qwen3 Embedding 0.6B** pour retrouver les documents. Les tags sont `qwen3.5:4b-q4_K_M` et `qwen3-embedding:0.6b`. Les poids de conversation sont annoncés autour de 3,3 Go ; il faut aussi loger le cache, les embeddings, Windows et les autres applications. Ce choix est une proposition technique adaptée au matériel rapporté, pas une qualification de performance. [Tag de conversation](https://ollama.com/library/qwen3.5:4b-q4_K_M).

Réglages préparés : contexte demandé **16 384 tokens**, réponse limitée à **512 tokens**, `think=false`, maintien en mémoire demandé de **300 secondes**. Le budget documentaire se réduit selon la question et l'historique réellement envoyés. Les faits, passages et champs historiques sont conservés entiers ou omis ; leurs originaux restent dans la mémoire. L'enveloppe UTF-8 est conservatrice, pas un compte exact de tokens. Une seule recherche documentaire est effectuée par question.

Gemma 4 12B et Qwen3.8 27B restent des candidats pour des machines plus équipées ; ils ne sont pas téléchargés par ce parcours. Un plus grand contexte consomme davantage de VRAM ; éviter un déchargement massif vers le CPU si la priorité est la réactivité. [Contexte Ollama](https://docs.ollama.com/context-length).

## Installation sur Windows

1. Installer **Python 3.12**, puis [Ollama pour Windows](https://ollama.com/download/windows), et démarrer Ollama. Ouvrir une nouvelle fenêtre après installation pour actualiser le PATH.
2. Récupérer la révision actuelle de BOJART et extraire entièrement l'archive dans un dossier utilisateur accessible en écriture.
3. Double-cliquer **`Installer_BOJART_4060Ti.cmd`**. Ce choix lance explicitement le téléchargement des deux modèles manquants, prépare Python, indexe la mémoire, mesure des réponses synthétiques et active les réglages seulement si les contrôles réussissent. Les modèles déjà présents ne sont pas mis à jour automatiquement.
4. Après réussite, ouvrir **`Lancer_BOJART.cmd`**, puis **Mémoire du projet → Parler à Jarvis**.

Commande équivalente depuis le dossier BOJART, sans cumuler les deux méthodes :

```powershell
py -3.12 tools/prepare_installation.py --model-profile speed --download-models
```

Une seule installation à la fois. Le téléchargement et l'indexation initiale peuvent prendre du temps. Une interruption conserve les anciens réglages ; consulter le message et le rapport privé `model-qualification-IDENTIFIANT.json`. Le [guide des modèles](INSTALLATION_MODELES.md) précise la réparation et les limites des contrôles. Les quatre cas synthétiques incluent volontairement un matériel fictif inconnu : ce cas vérifie la capacité à ne pas inventer une réponse, il ne remplace pas les faits de ce poste.

## Vérifier sur le PC

Pendant une réponse, ouvrir un second terminal et exécuter `ollama ps` : relever le modèle, le contexte et la répartition GPU/CPU. Comparer ces données au diagnostic matériel de Jarvis. Le premier essai doit se faire sans génération d'images, rendu 3D ou jeu concurrent. Fermer ces applications ne supprime pas leurs fichiers.

Dans Jarvis, demander la carte graphique, la RAM et le système du poste ; contrôler les références. Faire ensuite deux échanges sur un dossier, relancer Jarvis et retrouver la conversation. Les temps du rapport sont mesurés sur des exemples synthétiques ; le seuil de huit secondes des appels suivants est un critère d'essai, pas une vitesse déjà atteinte. L'interface affiche la réponse complète ; la diffusion progressive n'est pas raccordée ici.

La génération d'images, la vidéo, la voix et les imprimantes restent des recettes distinctes. Les 8 Go ne permettent pas de présumer que tous ces moteurs fonctionneront simultanément. Les commandes connues de M07 gardent leur résolution locale ; une réponse textuelle du panneau Mémoire ne commande pas une machine.

L'inventaire des imprimantes reste incomplet : leurs modèles et leur nombre exact ne sont pas confirmés. La déclaration du GPU et la photo du PC ne renseignent pas le parc de fabrication.
