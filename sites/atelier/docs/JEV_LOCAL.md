# BOJ.ART — raccorder Jev à la tour locale

## État de livraison

Le code comprend une passerelle Node qui sert le dashboard et peut demander à l’API TypeSafe de choisir une vue existante. Aucun appel réel à TypeSafe n’a été effectué pour cette livraison. Aucune clé n’est fournie ou enregistrée. Le site hébergé reste une application statique ; ces deux modules ne deviennent pas un serveur sur l’hébergement par leur seule présence dans le dépôt.

La passerelle s’utilise sur le PC de la tour, avec une clé TypeSafe dans son environnement. Elle écoute uniquement sur `127.0.0.1` et sert le dossier `dist`. Un dashboard ouvert à cette adresse utilise l’API locale de la même origine. La clé reste dans le processus Node ; le navigateur ne reçoit ni cette clé, ni un champ permettant de choisir une URL de service.

**Le modèle Jev de cette intégration est un service cloud.** Le serveur d’interface est local. Cette distinction doit rester visible : installer la passerelle ne transforme pas le modèle TypeSafe en IA locale. Les données envoyées se limitent à la commande de présentation, aux identifiants/révisions du contexte et aux vues disponibles ; aucun STL, fichier vidéo, audio, image ou carnet de clients n’est joint.

## Ce que fait chaque composant

| Élément | Rôle vérifié | Intérêt pour BOJ.ART |
|---|---|---|
| [Skill officiel TypeSafe](https://github.com/typesafe-ai/skills) — MIT | Fournit les instructions et références de l’API à un agent de développement. | Source principale pour maintenir les questions et le raccordement. |
| [wuyoscar/jev-skill](https://github.com/wuyoscar/jev-skill) — MIT | Collection de skills et de cas d’usage. Son cas « dashboard view » choisit un composant existant. | Référence de conception, sans confondre une recette avec une exécution réelle. |
| [etweisberg/jev-ui](https://github.com/etweisberg/jev-ui) — annoncé MIT dans son README | Composants React `Branch`, `Rank` et `Gate` pour sélectionner, classer ou ajouter des éléments de présentation. | C’est la correspondance la plus directe au besoin de visuels adaptatifs. Le dashboard actuel utilise son propre moteur de rendu et n’exige pas une migration React. |
| [aiwithenoch/Jev-Skill](https://github.com/aiwithenoch/Jev-Skill) — MIT-0 | Harnais de décisions, validation et évaluation, avec des adaptateurs de modèles locaux. | Piste pour comparer ensuite un modèle local avec le même jeu de commandes ; ce n’est pas le modèle propriétaire Jev. |
| `local/jev-provider.mjs` | Construit la requête officielle, valide la réponse, applique les seuils et normalise les erreurs. | Ne permet que `model`, `art`, `film`, `production` ou `none`. |
| `local/jev-gateway.mjs` | Sert les fichiers du dashboard et deux routes HTTP locales. | Garde la clé côté serveur et limite les requêtes au navigateur de la tour. |

Jev choisit une présentation. Les visuels, vidéos, effets de transition, modèles 3D et couleurs BOJ.ART restent produits par les composants du dashboard. Les choix de vue ne modifient pas un projet, ne lancent pas de slicer, n’allument pas d’imprimante et ne publient aucun contenu.

## Lancer sur la tour

Il faut Node.js 20 ou une version ultérieure. Les modules utilisent uniquement sa bibliothèque standard : aucune dépendance npm supplémentaire n’est nécessaire pour la passerelle.

Depuis le dossier du projet, une ouverture sans clé permet de vérifier le service local sans appeler TypeSafe :

```sh
node local/jev-gateway.mjs
```

Ouvrir ensuite `http://127.0.0.1:3137`. Le statut indique « non configuré » et aucun appel au modèle n’est possible. Pour activer l’option, renseigner `TYPESAFE_API_KEY` dans les réglages de secrets du processus local, puis redémarrer. La clé n’a pas à être écrite dans le code, saisie dans le dashboard ou partagée dans une conversation.

| Variable d’environnement | Défaut | Usage |
|---|---|---|
| `TYPESAFE_API_KEY` | Absente | Clé du compte TypeSafe. Son absence conserve le mode non configuré. |
| `JEV_MODEL` | `jev-1.13.0` | Version fixée pour rendre l’intégration reproductible. Accepte aussi une autre version `jev-x.y.z`, `jev-latest` ou `jev-preview`. |
| `BOJ_JEV_PORT` | `3137` | Port local entre 1024 et 65535. |
| `BOJ_JEV_MIN_PROBABILITY` | `0.8` | Probabilité minimale du choix retenu. |
| `BOJ_JEV_MIN_MARGIN` | `0.15` | Écart minimal entre le meilleur choix et le suivant. |

Les deux seuils sont **expérimentaux, non étalonnés sur les commandes BOJ.ART**. Ils ne représentent pas une garantie de justesse. La documentation TypeSafe indique que la qualité dépend de la langue et recommande des évaluations sur les données du domaine. Au 18 octobre 2026, `jev-latest` pointe vers `jev-1.13.0` ; `jev-preview` pointe vers `jev-1.14.0`, version publiée le 14 octobre. Chaque réponse renvoie le modèle effectif ; une version différente de celle explicitement fixée est refusée par l’adaptateur.

Les trois fenêtres doivent partager la même origine et le même profil navigateur pour coordonner leurs vues :

```text
http://127.0.0.1:3137/?screen=atelier&station=atelier&immersive=1
http://127.0.0.1:3137/?screen=pilotage&station=pilotage&immersive=1
http://127.0.0.1:3137/?screen=creation&station=creation&immersive=1
```

Le stockage du navigateur est propre à l’origine. Les dossiers enregistrés sur le site hébergé ne se retrouvent pas automatiquement à l’adresse locale, et changer de port crée aussi une autre origine. Une synchronisation entre ces installations constitue un travail distinct.

## Contrat du dashboard vers la passerelle

`GET /api/visual-decision/status` ne déclenche aucun appel au fournisseur. Exemple sans clé :

```json
{
  "ok": true,
  "provider": "typesafe",
  "configured": false,
  "connected": false,
  "availability": "unconfigured",
  "model": "jev-1.13.0",
  "lastVerifiedAt": null,
  "thresholds": {"minProbability": 0.8, "minMargin": 0.15, "experimental": true}
}
```

Avec une clé, `configured` devient vrai et `availability` vaut `configured`. `connected` ne devient vrai qu’après la validation complète d’une réponse réelle du fournisseur. `lastVerifiedAt` date cette vérification ; il ne constitue pas une sonde continue de disponibilité. Le démarrage du processus ou une nouvelle tentative remet `connected` à faux tant qu’aucune réponse valide n’est revenue. Après une erreur, la date de la dernière réussite reste consultable et la disponibilité redevient `configured`.

`POST /api/visual-decision` accepte uniquement cette structure :

```json
{
  "requestId": "visual-17",
  "command": "Montre le modèle de cette pièce",
  "context": {
    "projectId": "project-a",
    "projectRevision": 4,
    "pieceId": "piece-b",
    "pieceRevision": 2
  },
  "availableViews": ["model", "art", "film", "production"]
}
```

`projectId` et `projectRevision` sont obligatoires. `pieceId` et `pieceRevision` sont présents ensemble ou absents ensemble. Les révisions sont des entiers strictement positifs. `availableViews` est un sous-ensemble non vide sans doublons des quatre vues autorisées. La passerelle ajoute toujours `none` à la question ; ce choix n’est pas envoyé dans `availableViews`. Une commande vide, supérieure à 2 000 caractères, ou un champ supplémentaire comme `endpoint`, `apiKey`, `model` ou `action` est refusé. Le corps HTTP est limité à 16 Kio.

Exemple de réponse **illustrative, pas une exécution enregistrée** :

```json
{
  "ok": true,
  "requestId": "visual-17",
  "context": {"projectId": "project-a", "projectRevision": 4, "pieceId": "piece-b", "pieceRevision": 2},
  "provider": "typesafe",
  "model": "jev-1.13.0",
  "decision": {
    "view": "model",
    "selectedView": "model",
    "reason": "selected",
    "probability": 0.88,
    "margin": 0.84,
    "confidence": 0.85,
    "probabilities": {"model": 0.88, "art": 0.04, "film": 0.03, "production": 0.02, "none": 0.03}
  },
  "usage": {"input_tokens": 342, "output_tokens": 22}
}
```

Une décision incertaine conserve `selectedView` et ses scores pour l’examen, mais renvoie `view: "none"` et `reason: "uncertain"`. Quand Jev sélectionne lui-même `none`, la raison est `no_match`. Le frontend doit vérifier le `requestId`, le contexte et les révisions encore en vigueur avant de demander le rendu via le bus d’affichage. Seul l’accusé de réception de l’écran cible peut confirmer que la vue a été chargée ; une décision Jev ne suffit pas.

Les erreurs utilisent `{ "ok": false, "code": "…", "message": "…" }`. Aucun corps d’erreur brut du fournisseur ni exception technique n’est renvoyé au navigateur. Un appel dure au maximum huit secondes, aucune relance automatique n’est effectuée et une seule demande peut être en cours dans le processus.

## Contrat officiel utilisé

```text
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <clé présente seulement côté serveur>
Content-Type: application/json
```

Le corps contient `model`, `state` et `questions.visual`, une question `choice` avec un dictionnaire `criteria` décrivant les vues réellement disponibles et `none`. La réponse doit contenir le modèle effectif, `answers.visual.type`, `choice`, `confidence`, une distribution `probabilities` sur exactement les choix soumis, et `usage`. L’adaptateur vérifie notamment que les probabilités sont finies, comprises entre zéro et un, totalisent un à l’arrondi près, et que le choix renvoyé a la plus forte probabilité.

Sources primaires consultées le 18 octobre 2026 : [API TypeSafe](https://docs.typesafe.ai/api), [modèles et alias](https://docs.typesafe.ai/models), [confiance](https://docs.typesafe.ai/confidence), [skill officiel](https://docs.typesafe.ai/agent-skill), [conditions du service hébergé](https://typesafe.ai/legal/mca).

## Vidéo, images et modèle local

La documentation [State](https://docs.typesafe.ai/concepts/state) indique que Jev n’accepte pas directement l’audio ou la vidéo. Il faut une chaîne séparée pour acquérir les fichiers, extraire des images clés, transcrire l’audio et décrire les scènes. La fonctionnalité [Images](https://docs.typesafe.ai/images) permet de soumettre des images fixes et des questions de localisation ; TypeSafe la présente actuellement comme expérimentale, désactivée par défaut. Elle n’est pas activée dans cette intégration.

La lecture native des clips dans le dashboard ne dépend donc pas de Jev. Le serveur prend en charge les requêtes HTTP `Range` pour les vidéos locales et garde les erreurs de lecture séparées des décisions du modèle.

Pour une tour entièrement autonome hors ligne, un modèle local peut être évalué derrière le même contrat interne. Le harnais MIT-0 mentionné plus haut sait envelopper plusieurs serveurs locaux, mais chaque modèle, licence, score et besoin matériel doit être évalué séparément. Aucun de ces modèles n’a été installé ou testé pour cette livraison.

## Vérifications livrées

```sh
node qa/check-jev-gateway.mjs
```

Cette commande emploie un faux fournisseur, des réponses HTTP injectées et des flux locaux. Elle ne crée aucun serveur en écoute et n’appelle pas TypeSafe. Elle vérifie le schéma, la sélection et l’abstention, les erreurs, le délai, l’absence d’exposition de la clé, les origines autorisées, les chemins de fichiers et les plages d’octets vidéo. Elle ne prouve ni la précision linguistique réelle de Jev, ni le rendu navigateur, ni une connexion aux imprimantes.
