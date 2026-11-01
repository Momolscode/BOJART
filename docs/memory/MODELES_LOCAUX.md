# Vérifier les modèles locaux avant utilisation

La recherche par mots et les contextes cités fonctionnent sans modèle IA. Une configuration de modèle invalide ou un service Ollama indisponible ne doit pas empêcher de consulter les documents. La conversation générée et les embeddings restent des fonctions à configurer explicitement.

## Diagnostic sans génération

Avec le Python de l’environnement BOJ.ART :

```bash
python -m bojart_memory.agent_cli models
python tools/doctor.py --check-models
```

La première commande lit `models.json` et, pour les rôles configurés, interroge uniquement les métadonnées du service local. Elle ne crée pas de mémoire vide et ne transmet ni documents, ni question, ni historique. Aucun téléchargement de poids, calcul d’embeddings ou appel de conversation n’est déclenché.

Le diagnostic standard et le statut du panneau lisent seulement la configuration, sans requête à Ollama. Le lanceur accepte aussi `--check-models` ; `--check-only` conserve son diagnostic logiciel plus large.

| Statut d’un rôle | Signification |
|---|---|
| `not_configured` | Aucun modèle choisi pour ce rôle |
| `not_probed` | Configuration lisible ; disponibilité non interrogée |
| `metadata_available` | Modèle trouvé, empreinte lue et capacité déclarée conforme |
| `model_missing` | Nom absent de la liste locale |
| `wrong_capability` | Le modèle ne déclare pas le rôle demandé |
| `capabilities_unknown` | Le serveur ne fournit pas les capacités nécessaires au contrôle |
| `remote_refused` | Une référence à un modèle distant a été détectée |
| `invalid_metadata` | Métadonnées du serveur non exploitables |
| `unavailable` | Service ou réponse indisponible |
| `configuration_invalid` | Fichier de configuration à corriger |

Un code de sortie `2` de la commande `models` signale un problème. Un rôle non configuré reste normal si la fonction n’est pas souhaitée. `metadata_available` ne prouve ni la qualité des réponses, ni la capacité de la RAM ou du GPU à exécuter le modèle.

## Configurer le bon rôle

Après téléchargement explicite du modèle dans Ollama :

```bash
python -m bojart_memory.agent_cli configure --embedding-model NOM_LOCAL
python -m bojart_memory.agent_cli configure --chat-model NOM_LOCAL
python -m bojart_memory.agent_cli models
```

La configuration des embeddings exige la capacité `embedding`, celle de la conversation la capacité `completion`. Un port local personnalisé déjà présent est conservé. Les changements sont écrits après les contrôles ; une erreur de validation ou d’écriture laisse le fichier précédent en place.

Si `models.json` est invalide, le conserver sous un autre nom avant de recréer la configuration avec ces commandes. Il se trouve dans le dossier mémoire sélectionné, par défaut `~/BOJART/memory`. Ne pas déplacer `memory.sqlite` ni `objects/` pour réparer seulement les modèles.

Après un changement de modèle d’embeddings, exécuter `python -m bojart_memory.agent_cli embed`. Les index restent associés à l’empreinte du modèle. La vérification des originaux et des faits reste active, même lorsque l’inférence facultative est indisponible.

## Références et portée

Contrat consulté le 1 novembre 2026 : [API officielle Ollama](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml), [liste des modèles](https://docs.ollama.com/api/tags) et [embeddings](https://docs.ollama.com/capabilities/embeddings). Le diagnostic utilise `GET /api/tags` puis `POST /api/show`, sans fournir de texte à traiter.

Les tests utilisent un serveur local de métadonnées simulé, avec modèles absents, réponses invalides, capacités incompatibles et service arrêté. Ils contrôlent aussi la recherche, la conservation des fichiers et l’absence de création de base par le diagnostic. Ils ne qualifient aucun modèle réel ni le matériel de BOJ.ART.
