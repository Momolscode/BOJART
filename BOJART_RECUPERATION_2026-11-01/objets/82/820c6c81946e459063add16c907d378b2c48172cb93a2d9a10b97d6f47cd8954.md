# BOJ.ART — décisions Jev transversales

Contrat : `bojart.jev-advisory.2026-10-19.v1`.

## Ce qui est livré

Trois domaines de conseil disposent d’un schéma fermé, de constructeurs liés au dossier, de règles locales, d’un transport vers la passerelle et d’un fournisseur TypeSafe injectable. Les candidats sont reconstruits à partir des mêmes faits dans le navigateur et sur le serveur.

| Domaine | Entrées réelles du logiciel | Choix autorisé | Effet disponible |
|---|---|---|---|
| `preparation` | Mesures du STL dans l’établi, révision de pièce, identifiant et empreinte éventuelle de fichier, fiche machine versionnée, volume déclaré | Une des six rotations à angles droits dont la boîte brute tient dans le volume déclaré | Examiner cette orientation dans l’établi |
| `attention` | États des fichiers du dossier, fiches du parc, dernières versions enregistrées des intentions de montage | Une pièce, une fiche machine, un plan existant ou une nouvelle intention à examiner | Ouvrir le bon élément |
| `editorial` | Type de projet déclaré, catalogue des cinq séries BOJ.ART, dernier plan enregistré ciblé s’il est fourni | Œuvres, geste, sur mesure, prototype ou disponible | Préparer une intention de série |

Le routage visuel existant reste distinct (`visual-router.js`, `jev-provider.mjs`, `/api/visual-decision`). Il choisit une présentation parmi quatre vues ; il ne commande pas une machine.

Ce contrat ne produit ni slicing, ni affectation physique, ni fichier machine, ni rendu vidéo, ni publication, ni message client. Ces capacités ne peuvent pas être ajoutées par une réponse du modèle. Les domaines futurs apparaissent dans `DECISION_DOMAINS` avec le statut `future_contract`, jamais comme connectés.

La connexion TypeSafe n’est déclarée dans le statut qu’après une réponse contrôlée par le fournisseur. `lastVerifiedAt` date ce dernier appel réussi ; ce n’est pas une mesure continue de disponibilité. Aucun appel TypeSafe réel ni benchmark français n’est attesté par les tests synthétiques de ce module.

## Fichiers et exports

| Module | Exports utiles |
|---|---|
| `dist/lib/decision-contract.js` | `DECISION_DOMAINS`, `DECISION_POLICY_VERSION`, `DECISION_LIMITS`, `DecisionError`, `normalizeDecisionRequest`, `decisionCandidates`, `decisionFingerprint`, `recommendLocalDecision`, `decisionRuleExplanation`, `validateProjectDecision` |
| `dist/lib/decision-context.js` | `buildPreparationDecisionRequest`, `buildAttentionDecisionRequest`, `buildEditorialDecisionRequest` |
| `dist/lib/decision-client.js` | `requestProjectDecision`, `getDecisionProviderStatus` |
| `local/jev-decisions.mjs` | `createJevDecisionProvider`, `createDecisionService`, `buildTypeSafeDecisionRequest`, `normalizeTypeSafeDecisionResponse` |
| `qa/check-project-decisions.mjs` | Vérification pure des contrats, projections, abstentions, délais et changements de contexte |

## Constructeurs du navigateur

Tous les constructeurs renvoient `{request, options, unavailableReason}`. `request` vaut `null` lorsqu’aucun candidat n’est possible. Cela demande d’afficher la raison et les commandes de l’établi déjà disponibles ; il ne faut ni inventer un modèle ni substituer des dimensions de simulation.

```js
const bundle = buildPreparationDecisionRequest(report, {
  requestId: crypto.randomUUID(),
  pieceId: selection.pieceId,
  machineId: selection.machineId,
  goal: 'balanced' // 'clearance' | 'low_height' | 'balanced'
});

const attention = buildAttentionDecisionRequest(report, project, {
  requestId: crypto.randomUUID(),
  goal: 'blockers' // 'blockers' | 'next_step'
});

const editorial = buildEditorialDecisionRequest(project, {
  requestId: crypto.randomUUID(),
  goal: 'showcase', // 'showcase' | 'technique' | 'custom_order' | 'prototype' | 'offer'
  planId: null // identifiant d’un plan enregistré pour reprendre cette intention
});
```

Le rapport d’attention doit correspondre à l’identifiant et à la révision du dossier, ainsi qu’à chaque pièce, fichier et unité qu’il décrit. Les travaux simulés ne sont jamais lus. La disponibilité des sources vidéo vient du catalogue conservé ; ce n’est pas une nouvelle lecture de tous les binaires vidéo.

### Options et actions de présentation

Une option contient `{id, label, summary, target, facts}`. Le texte destiné à l’écran peut reprendre un nom de pièce ou de plan. Ces noms ne sont pas envoyés au modèle.

Les seules valeurs de `target.action` sont :

| Action | Paramètres locaux supplémentaires |
|---|---|
| `inspect_orientation` | `projectId`, `pieceId`, `machineId`, `orientationId` |
| `inspect_piece` | `projectId`, `pieceId` |
| `inspect_machine` | `projectId`, `machineId` |
| `inspect_edit` | `projectId`, `planId`, `planRevision` |
| `create_edit` | `projectId` |
| `prepare_series` | `projectId`, `series`, `planId` ou `null` |

L’application est responsable de l’ouverture de la vue ou de l’intention. Elle retrouve la cible dans les options actuelles ; elle n’interprète jamais une URL, du code ou une cible fournie par Jev.

## Paquet de préparation : exemple de structure

L’exemple suivant est synthétique. Il décrit un schéma d’intégration, pas un STL ou une machine réellement qualifiés.

```json
{
  "format": "bojart.decision-request.v1",
  "policyVersion": "bojart.jev-advisory.2026-10-19.v1",
  "requestId": "decision-001",
  "domain": "preparation",
  "goal": "clearance",
  "context": {"projectId": "project-1", "projectRevision": 4},
  "evidence": {
    "source": "declared_preparation_v1",
    "piece": {
      "id": "piece-1", "revision": 2, "assetId": "asset-1",
      "unit": "mm", "sha256": null, "technology": "fdm",
      "dimensionsMm": [80, 40, 60]
    },
    "machine": {
      "id": "machine-1", "revision": 1, "declared": true,
      "technology": "fdm", "usableVolumeMm": [120, 90, 130],
      "profilesDeclared": true, "qualificationStatus": "not_started"
    }
  }
}
```

Le serveur refuse les clés supplémentaires, les domaines futurs, les objectifs inconnus, les listes creuses, les identifiants ambigus et les nombres hors limites. Le corps est plafonné à 64 Kio et le nombre de candidats à 64. Un appel ne peut pas choisir son endpoint, son modèle, son prompt, ses outils ou ses critères. Le modèle et les seuils relèvent de la configuration du serveur.

L’empreinte du paquet ne remplace pas celle du STL. `sha256: null` signifie qu’aucune empreinte de binaire n’a été fournie par le contrôle du navigateur. Le conseil conserve alors cette limite. Les rotations ne prouvent ni fermeture du maillage, ni solidité, ni bonne orientation d’impression.

## Fraîcheur : contrôler avant, après et lors de l’ouverture

`requestProjectDecision` exige une fonction `getCurrentRequest`. Elle reconstruit le paquet lié au même projet avec le même `requestId`, les mêmes sélections et le même objectif. Elle retourne le paquet, pas l’enveloppe `{request, options}`. Un changement de pièce, fichier, unité, fiche machine ou plan ciblé change les preuves pertinentes de son domaine. Le contexte reste lié au dossier d’origine ; changer de dossier affiché peut invalider la demande en retournant `null`.

```js
const requestId = crypto.randomUUID();
const args = {requestId, pieceId, machineId, goal: 'balanced'};
const buildCurrent = () => {
  const current = getContext(); // dossier et rapport actuels, pas une copie périmée
  if (!current || current.project.id !== projectId) return null;
  return buildPreparationDecisionRequest(current.report, args);
};

const initial = buildCurrent();
if (!initial?.request) return;
const result = await requestProjectDecision(initial.request, {
  getCurrentRequest: () => buildCurrent()?.request ?? null
});

// Lorsqu’une carte de conseil est ouverte, même après un délai :
const current = buildCurrent();
if (!current?.request) return;
await validateProjectDecision(result, current.request);
const option = current.options.find(item => item.id === result.decision.candidateId);
if (option) onInspect(option.target);
```

Le client compare une empreinte SHA-256 du paquet complet avant et après l’appel. Le résultat contient cette empreinte, le contexte, l’identifiant de demande, la version de politique, le fournisseur et la date. Il expire après 60 secondes ; une date serveur de plus de cinq secondes dans le futur est refusée. Les deux horloges sont supposées être celles de la même tour.

Cette empreinte détecte les écarts du paquet. Elle n’est ni une signature d’authentification, ni une relecture indépendante des STL sur le serveur. La provenance demeure `client_snapshot_advisory`. Le service peut recevoir un résolveur central de contexte pour effectuer une deuxième vérification côté serveur ; sans ce résolveur, il ne prétend pas l’avoir effectuée.

## TypeSafe, règles locales et abstention

Le conseil local utilise des règles déterministes visibles : marge minimale de boîte brute, hauteur brute, priorité des données manquantes ou série correspondant à l’objectif. `provider` vaut `local_rules`, `model` et les scores valent `null`. Il ne doit pas être présenté comme une réponse de Jev.

Pour TypeSafe, le serveur convertit les candidats en alias `c01`, `c02`, etc. Il transmet seulement l’objectif, les descriptions écrites des candidats et des faits bornés : dimensions, marges, procédés, états, comptes et séries. Les identifiants de projets, machines, pièces, fichiers et plans, les noms, notes, chemins, empreintes et binaires restent hors de la requête TypeSafe. Les dimensions et métadonnées ainsi transmises restent des données du projet : elles ne deviennent pas publiques ni anonymes au sens d’une garantie juridique.

Une réponse `choice` est acceptée uniquement si tous les candidats attendus et `none` figurent dans une distribution finie qui totalise 1, si le choix correspond à sa valeur la plus élevée et si le modèle effectif est conforme à la configuration. La probabilité du meilleur choix doit atteindre 0,8 et son écart au deuxième 0,15. Les seuils peuvent être renforcés côté serveur ; ils sont **expérimentaux**, sans calibration BOJ.ART française démontrée. La `confidence` est conservée séparément.

Une ambiguïté ou une probabilité insuffisante donne `candidateId: null`, avec `reason: uncertain` ou `no_match`. La réponse ne doit pas être convertie en action par défaut. Les options manuelles restent disponibles.

Le fournisseur appelle uniquement `https://api.typesafe.ai/v1/systemone`, avec clé dans l’en-tête serveur. Redirections refusées, une comparaison en cours à la fois par instance, délai de huit secondes par défaut, corps réponse limité à 64 Kio, erreurs normalisées sans corps amont, aucune réémission automatique. Le client conserve un délai de dix secondes par défaut.

## Raccordement de la passerelle

```js
const decisionProvider = createJevDecisionProvider({
  apiKey: env.TYPESAFE_API_KEY || '',
  model: env.JEV_MODEL || DEFAULT_JEV_MODEL
});
const decisions = createDecisionService({provider: decisionProvider});

// Dans le handler local existant, après ses contrôles Host/Origin :
// GET ou HEAD /api/decisions/status -> decisions.status()
// POST /api/decisions -> decisions.decide(await readJson(request, 65536))
```

`createDecisionService` accepte en option `getCurrentRequest(input)`, qui retourne le paquet reconstruit depuis l’autorité centrale. Le résolveur est appelé avant et après le fournisseur. Il doit inclure les preuves réellement conservées, sans déclarer vérifié un fichier qui ne se trouve pas dans le service central.

La passerelle existante conserve ses contrôles d’origine et son écoute sur boucle locale. Ce contrat n’ajoute pas d’accès distant, d’authentification LAN ou de contrôle de machine. Les erreurs du module serveur sont normalisées en `JevError`, reconnu par le handler existant.

## Domaines futurs : conditions de raccordement

| Domaine | Condition avant l’ouverture d’un contrat actif |
|---|---|
| Slicing | Moteur identifié, profils stockés avec empreintes, recette et format vérifiés ; Jev compare des recettes déjà admissibles. |
| Répartition | Plateaux réellement calculés, capacité connue, machines et opérations humaines disponibles ; Jev compare les plans d’un planificateur. |
| Qualité / incident | Données datées associées au bon travail, procédures de reprise, résolution des réponses inconnues ; Jev priorise l’examen. |
| Commercial | Catalogue d’offres qualifiées, coûts calculés, état des droits et contraintes du brief ; Jev oriente sans envoyer d’engagement. |
| Publication | Rendus identifiés, droits, compte et parcours admissibles ; aucune API privée interne supposée apte à publier publiquement. |
| Robotique | Exigences, configuration et résultats d’essai ; les contrôleurs d’actionneurs restent hors du service de décision. |

## Validation et sources

Exécuter `node qa/check-project-decisions.mjs`. Les 22 groupes vérifient les schémas fermés, les candidats disponibles, la séparation de la simulation, les fichiers et versions, la minimisation de la requête TypeSafe, les règles locales, l’abstention, les distributions invalides, les changements de contexte, l’expiration, les erreurs, la concurrence et les délais. Ils utilisent des mesures synthétiques et un transport injecté. Aucun serveur, navigateur, compte TypeSafe, slicer, imprimante, rendu ou publication n’est sollicité.

Sources primaires consultées le 19 octobre 2026 :

- [API TypeSafe](https://docs.typesafe.ai/api) : schéma `choice`, distribution, modèle effectif, usage et erreurs.
- [Modèles TypeSafe](https://docs.typesafe.ai/models) : entrée textuelle, modèle hébergé, identifiants versionnés, alias et recommandation d’évaluation sur la langue d’usage.

La documentation indique Jev 1.14 disponible depuis le 14 octobre 2026, tandis que l’alias stable consulté reste sur 1.13. Le code garde le modèle versionné `jev-1.13.0` existant par défaut. Un changement de modèle appelle une évaluation française de BOJ.ART et une révision explicite de la configuration ; la nouveauté seule ne prouve pas une amélioration de ces décisions.
