# Diagnostic du poste et des outils BOJ.ART

Le diagnostic relève les prérequis du poste qui l'exécute. Il prépare la collecte `target_hardware` définie dans la recherche d'outils et indique les vérifications suivantes. Il ne choisit pas un modèle IA à partir d'un nom de carte supposé.

## Utilisation sur la tour

Sous Windows, ouvrir **Diagnostic_BOJART.cmd**. Sous Linux :

```bash
bash Diagnostic_BOJART.sh
```

Python 3.12 doit être installé. Le script utilise le Python de `.venv` s'il existe, pour observer les bibliothèques de Jarvis. Il affiche un résumé et conserve un nouveau rapport JSON daté dans `~/BOJART/diagnostics` (`%USERPROFILE%\BOJART\diagnostics` sous Windows). Il ne remplace pas les rapports précédents.

Pour afficher le JSON sans enregistrer de fichier, depuis le Python de Jarvis :

```bash
python tools/diagnose_environment.py
```

Pour ajouter cet inventaire au contrôle existant du lanceur :

```bash
python tools/start_jarvis.py --check-only --check-tools
```

Le lancement ordinaire garde son comportement et sa durée : les nouvelles sondes sont explicites. Le contrôle `--check-only` conserve son code de sortie `2` pour les prérequis du poste manquants. Le diagnostic d'environnement seul renvoie `0` quand l'observation a été produite, même si des outils manquent ; ce code ne signifie pas que la production est prête.

## Essai réel de l'export vidéo et audio

Depuis le Python de Jarvis, avec FFmpeg et FFprobe installés :

```bash
python tools/diagnose_environment.py --check-media --save --summary
```

Cette option crée un clip synthétique temporaire de deux secondes, 720 × 1280, 24 images/s, H.264 `yuv420p` et AAC mono à 48 kHz. FFprobe compte les 48 images et vérifie les pistes, leurs durées et leur décalage de départ. FFmpeg décode ensuite tout le fichier avec arrêt sur erreur. Le signal audio est décodé en PCM pour mesurer le nombre d'échantillons, le niveau moyen et la crête. Le fichier doit garder la même empreinte pendant ces contrôles ; il est supprimé après l'essai.

Le rapport `media_check` conserve les versions, les étapes chronométrées, les mesures, l'empreinte du clip et le résultat du nettoyage. Le code de sortie vaut **2** si l'essai demandé est bloqué ou échoue, et **0** s'il réussit. Un rapport d'échec est également enregistré avec `--save`. Les raccourcis habituels restent un inventaire sans génération ; seul `--check-media` déclenche cet essai.

Un `missing_tools` demande de localiser FFmpeg/FFprobe avec `--tool-path` ou de les installer. Un `process_failed` à l'étape `encode` peut notamment signaler un binaire sans `libx264`, AAC ou les filtres requis ; vérifier cette installation avant de relancer. `timeout` indique qu'une étape a dépassé son délai : 30 secondes pour l'encodage, 15 pour chacune des trois lectures. Aucun autre encodeur n'est substitué silencieusement. Les commandes et la mire sont fixes ; aucun média, projet ou script utilisateur n'est ouvert, aucun shell n'est lancé.

Un résultat `passed` prouve uniquement ce petit export CPU sur le poste exécutant la commande. Il ne qualifie ni le montage R03, ni Blender, After Effects, les VFX, le GPU ou le son à l'écoute. `production_ready`, `artistic_approval` et `physical_hardware_qualified` restent faux. Les compteurs d'essai sont dans `media_check.synthetic_exports_created` ; `render_jobs` de l'inventaire ne compte pas ces mires techniques.

## Ce qui est relevé

| Élément | Observation | Vérification encore nécessaire |
| --- | --- | --- |
| Système, CPU, RAM | Système courant, architecture, processeurs logiques, RAM visible | Confirmer qu'il s'agit de la tour BOJ.ART et mesurer sous charge |
| GPU NVIDIA | Nom, VRAM totale **par carte**, pilote via `nvidia-smi` | Runtime CUDA, mémoire disponible pendant le travail, performances réelles |
| FFmpeg, FFprobe, Blender, Node | Exécutable trouvé et réponse de version reconnue | Export, rendu et bridge réels |
| Ollama, OrcaSlicer, UVtools, `aerender` | Présence du binaire | Service/modèles, profils de fabrication, projet Adobe avec polices et plugins |
| LangGraph, CadQuery, Trimesh, Manifold, faster-whisper, CTranslate2, Pipecat, Docling, OpenTimelineIO | Métadonnées des paquets du Python utilisé | Import natif, poids éventuels et essai de la fonction |

Le contrôle d'import CAO/LangGraph existant reste dans `tools/doctor.py --probe-imports`. Les métadonnées de paquets ne le remplacent pas. La présence de Node n'établit pas celle d'AE MCP Bridge ou de Remotion.

Un résultat `not_found` signifie **non trouvé dans les chemins examinés**, pas « logiciel absent du PC ». Les logiciels graphiques sont souvent installés hors du `PATH`. On peut alors donner leur binaire exact, sans arguments supplémentaires :

```powershell
python tools/diagnose_environment.py --save --summary --tool-path "blender=C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
```

Le chemin ci-dessus est un exemple à remplacer par celui de l'installation réelle. `--tool-path aftereffects=CHEMIN_ABSOLU_AERENDER` relève le moteur Adobe sans l'exécuter. Les identifiants reconnus sont indiqués par `--help`. Aucun script `.cmd`, `.bat` ou `.ps1` n'est lancé par cette option.

## Lire le résultat

`detected` signifie que le binaire a été trouvé. `version_probe: verified` ajoute une réponse de version reconnue. `integration_qualified` reste faux : chaque outil exige sa recette métier. Les commandes de version sont fixes, sans shell, avec un délai maximal de quatre secondes par processus. Les sorties d'erreur et les chemins des exécutables ne sont pas copiés dans le rapport.

La VRAM n'est pas additionnée entre cartes. Une valeur indisponible reste `null`. L'absence de `nvidia-smi` ne prouve pas l'absence de GPU ; AMD, Intel et Apple ne sont pas sondés. La RAM annoncée est celle visible par le système et peut dépasser la limite d'un conteneur. Le pilote NVIDIA ne prouve pas l'installation de CUDA.

Le rapport complète certains champs du jeu `target_hardware`, en conservant `complete: false` et les champs manquants. Le micro, les moniteurs physiques, les imprimantes, les polices/plugins Adobe et les comptes restent à relever séparément. Les portes de lancement existantes et le registre de recherche ne sont pas modifiés par ce relevé.

`next_actions` propose la prochaine vérification pour chaque outil. `services_not_probed` signale les raccordements distants à essayer ultérieurement : Moonraker, le bridge Adobe, Higgsfield et les sources natives SEO/TikTok. Aucune analyse de réseau, connexion à un compte, installation, commande d'imprimante ou publication n'est effectuée. La seule génération possible est la mire locale explicitement demandée par `--check-media`. Metricool reste hors de cette demande.

Les rapports du poste restent hors du dépôt public. `--output CHEMIN_JSON` permet de choisir un nouveau fichier extérieur au dépôt. Le diagnostic ne relève ni nom d'hôte, ni numéro de série, ni identifiant de compte ; contrôler néanmoins le fichier avant partage.

## Preuves et références

La recette logicielle figure dans `tests/test_environment_diagnostic.py`, exécutée par la CI mémoire sous Windows et Linux. Les GPU des tests sont des données synthétiques. Le relevé effectué dans l'environnement de développement ne décrit pas la tour.

`tests/test_media_check.py` injecte les pannes de processus, métadonnées, fichiers et audio. Le job Linux `media-export` installe FFmpeg puis exécute le vrai export et conserve son reçu en artefact de CI, même en cas d'échec. Les tests Windows portent sur le logiciel et ses pannes simulées ; aucun export Windows réel n'est revendiqué par ce job. La mesure locale datée est conservée dans `docs/evidence/synthetic-media-check-2026-11-02.json`.

Documentation officielle consultée le 2 novembre 2026 : [requêtes NVIDIA](https://docs.nvidia.com/deploy/nvidia-smi/), [champs NVIDIA](https://nvidia.custhelp.com/app/answers/detail/a_id/3751/~/useful-nvidia-smi-queries), [options Blender](https://docs.blender.org/manual/en/5.0/advanced/command_line/arguments.html), [mémoire Windows](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/ns-sysinfoapi-memorystatusex), [processus Python](https://docs.python.org/3/library/subprocess.html), [FFmpeg](https://ffmpeg.org/ffmpeg.html), [FFprobe](https://ffmpeg.org/ffprobe.html), [filtres synthétiques FFmpeg](https://www.ffmpeg.org/ffmpeg-filters.html).
