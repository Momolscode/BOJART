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

`next_actions` propose la prochaine vérification pour chaque outil. `services_not_probed` signale les raccordements distants à essayer ultérieurement : Moonraker, le bridge Adobe, Higgsfield et les sources natives SEO/TikTok. Aucune analyse de réseau, connexion à un compte, installation, génération, commande d'imprimante ou publication n'est effectuée. Metricool reste hors de cette demande.

Les rapports du poste restent hors du dépôt public. `--output CHEMIN_JSON` permet de choisir un nouveau fichier extérieur au dépôt. Le diagnostic ne relève ni nom d'hôte, ni numéro de série, ni identifiant de compte ; contrôler néanmoins le fichier avant partage.

## Preuves et références

La recette logicielle figure dans `tests/test_environment_diagnostic.py`, exécutée par la CI mémoire sous Windows et Linux. Les GPU des tests sont des données synthétiques. Le relevé effectué dans l'environnement de développement ne décrit pas la tour.

Documentation officielle consultée le 2 novembre 2026 : [requêtes NVIDIA](https://docs.nvidia.com/deploy/nvidia-smi/), [champs NVIDIA](https://nvidia.custhelp.com/app/answers/detail/a_id/3751/~/useful-nvidia-smi-queries), [options Blender](https://docs.blender.org/manual/en/5.0/advanced/command_line/arguments.html), [mémoire Windows](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/ns-sysinfoapi-memorystatusex), [processus Python](https://docs.python.org/3/library/subprocess.html), [FFmpeg](https://ffmpeg.org/ffmpeg.html).
