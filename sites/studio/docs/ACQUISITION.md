# BOJ.ART — Réception des demandes et passage vers Jarvis

## Périmètre livré

La vitrine reçoit un brief dans une base Cloudflare D1. Un reçu est retourné seulement après confirmation de la ligne conservée. L’administration permet de lire les demandes, corriger le nom, l’e-mail et le téléphone, déclarer leur statut, exporter un dossier et le supprimer. Le formulaire ne produit pas de tarif, n’envoie pas d’e-mail et ne téléverse pas de fichier 3D.

L’espace de suivi est `/administration`. Une demande particulière s’ouvre avec `/administration?demande=<requestId>`. Il est protégé par l’identité SIWC fournie par Sites **et** une liste explicite d’administrateurs côté serveur. La connexion à elle seule ne confère aucun droit d’administration.

## Configuration de déploiement

| Configuration | Usage |
| --- | --- |
| Liaison D1 `DB` dans `.openai/hosting.json` | Conservation des demandes, compteurs d’admission et identifiants de demandes supprimées. |
| Secret `BOJART_ADMIN_EMAILS` | E-mails administrateurs séparés par virgules, points-virgules ou retours à la ligne. Ce champ n’est jamais utilisé comme contact public. |
| Secret `BOJART_FORM_SECRET` | Valeur aléatoire serveur d’au moins 32 caractères pour les jetons de formulaire et la pseudonymisation des compteurs d’admission. |

Les secrets sont configurés avec Sites ; ils ne doivent apparaître ni dans les sources, ni dans le manifeste, ni dans le bundle navigateur. Les en-têtes `oai-authenticated-user-id` et `oai-authenticated-user-email` sont ceux du dispositif d’authentification hébergé Sites. Ce modèle suppose que ce dispositif reste la frontière de confiance ; ne pas exposer le Worker derrière un proxy qui laisse le visiteur fabriquer ces en-têtes.

Les deux migrations Drizzle sont générées et relues : création des trois tables, puis ajout explicite de la version de l’information sur les données. Aucun DDL n’est exécuté pendant une requête métier. Sites applique les migrations hébergées à la publication ; les essais SQLite du dépôt sont indépendants de cette base.

## Parcours de dépôt

1. Le navigateur prépare le brief et un UUID v4, puis conserve ce couple pendant une tentative incertaine.
2. `GET /api/briefs/token` renvoie `{ok:true,token,expiresAt}`. Le jeton HMAC expire après quinze minutes et dépend de l’origine du site.
3. `POST /api/briefs` reçoit un JSON avec le jeton dans `X-BOJART-Form-Token`. L’origine, la taille, le jeton, les champs et les bornes sont contrôlés côté serveur.
4. Le serveur normalise le brief, calcule son empreinte, vérifie une éventuelle réception antérieure, puis conserve une ligne unique.
5. La réponse contient la référence, l’UUID et la date de réception. La réponse n’affirme ni envoi d’e-mail, ni étude commerciale terminée, ni lecture de fichier.

Le contrat portable est `lib/acquisition-core.mjs`. Le champ `privacyAcknowledged` signifie que l’information sur les données a été portée à la connaissance du demandeur. Il n’est pas un accord de prospection ou d’abonnement à une newsletter.

### Reprises et erreurs

| Réponse | Signification et comportement client |
| --- | --- |
| `201`, `replayed:false` | La demande vient d’être conservée. Afficher le reçu. |
| `200`, `replayed:true` | La même demande était déjà conservée. Afficher le même reçu d’origine. |
| `409 idempotency_conflict` | Le même UUID a été utilisé pour un autre contenu. Ne pas créer automatiquement une nouvelle demande. |
| `403 token_expired` | Reprendre un jeton, puis renvoyer le même UUID et le même corps. |
| `410 request_deleted` | La demande a été supprimée. État terminal ; proposer un nouveau brief vierge seulement après action explicite. |
| `422 validation_failed` | Première tentative refusée : revenir aux champs. Après un ancien résultat inconnu : conserver l’UUID et demander une vérification. |
| `429 rate_limited` | Temporiser selon `Retry-After`. Conserver le même identifiant. |
| Réseau interrompu ou `503` | La réception peut être incertaine. Garder l’UUID et le contenu figés jusqu’à obtention du reçu ou d’un conflit explicite. |

L’empreinte du dépôt initial reste inchangée lors d’une correction de contact. Un ancien envoi réseau identique retrouve ainsi son reçu sans remettre les anciennes coordonnées dans la demande. Le reçu public ne dévoile pas le statut commercial actuel ni les coordonnées corrigées.

Une réponse JSON 400, 413 ou 422 qui ne correspond pas au contrat ne démontre pas l’absence d’écriture. L’incertitude est enregistrée avant le POST ; les reprises conservent le même corps. Une panne du jeton avant le premier POST laisse le formulaire modifiable. Un verrou immédiat empêche deux événements rapprochés de préparer deux UUID.

La tentative complète est relue dans le stockage de cet onglet pendant au plus 24 heures. À la prochaine ouverture après expiration, son contenu et ses coordonnées sont retirés. Pour un ancien résultat inconnu, un avis minimal conserve l’UUID, le motif et la date de l’avis, afin de vérifier la réception avant de saisir un nouveau brief. Une tentative illisible utilise aussi cet avis. Il ne s’agit pas d’un reçu ; aucun envoi ou effacement côté serveur n’est déduit de l’expiration locale.

## Validation et admission

Le brief contient une famille `artwork`, `custom` ou `prototype`, un nom, un e-mail, une description, une quantité entière, une préférence de budget et le point de départ du projet. Le téléphone, l’usage envisagé, les dimensions en millimètres, l’échéance et les références sont facultatifs. Les dimensions sont des souhaits du demandeur, jamais des mesures prouvées d’un modèle.

Les limites principales sont : corps 24 Kio, description 20 à 6 000 caractères, cinq références HTTPS au maximum, quantité de 1 à 1 000, dimensions positives jusqu’à 100 000 mm. Les types, les clés inconnues, les dates impossibles, les liens contenant des identifiants et les adresses réseau locales sont refusés. Les liens fournis ne sont pas récupérés par le serveur.

L’admission utilise un champ discret anti-robot, un jeton HMAC et des compteurs atomiques : six nouvelles tentatives par minute et trente par jour pour une origine réseau pseudonymisée ; plafond global de trois cents tentatives admissibles par heure. Les doublons déjà conservés retrouvent leur reçu avant ces compteurs. Les trois réservations sont transactionnelles : une tentative refusée par un compteur individuel ne consomme aucune place du plafond global.

Le plafond global est réservé avant la création de nouvelles clés de compteurs. Une fois atteint, l’arrivée d’autres adresses réseau ne fait donc pas croître indéfiniment la table de limitation. Les clés individuelles sont des HMAC renouvelés chaque jour ; aucune adresse IP brute n’est conservée. Les clés expirées sont retirées par petits lots lors de nouvelles tentatives sous le plafond global. Ces mesures bornent une première mise en service ; elles ne constituent pas une preuve qu’un visiteur est humain. Un contrôle anti-abus spécialisé et une observation de la charge restent à qualifier avant une campagne importante.

## Administration et conservation

Chaque API de lecture, modification, export ou suppression refait la vérification d’identité et d’autorisation. Les mutations exigent aussi l’origine du site. Les réponses administratives et reçus portent `Cache-Control: no-store, private`.

Une modification porte la révision attendue. Deux fenêtres qui modifient la même version ne peuvent pas s’écraser silencieusement : la seconde reçoit `409 revision_conflict` et doit relire la demande. La version de l’information sur les données est stockée à la création et préservée dans les corrections et les exports.

Le changement de dossier verrouille immédiatement les actions de l’ancienne sélection, avant même le nouveau rendu de l’interface. Pendant une écriture, le changement de sélection est empêché. Les réponses tardives sont rattachées à leur génération. Un délai de 20 secondes libère l’interface et propose une relecture lorsque la réponse d’une mutation n’a pas été reçue. La date d’une modification ne recule pas avant celle de la version précédente.

Les statuts `new`, `reviewing`, `awaiting_details`, `quoted`, `accepted`, `declined`, `archived` sont des indications de suivi déclarées par l’atelier. Aucun ne constitue à lui seul un devis signé, une preuve d’accord ou un paiement.

La suppression utilise une transaction : création d’un identifiant de suppression minimal, puis retrait du dossier complet. En cas d’échec, l’ensemble est annulé. Le marqueur restant contient uniquement l’UUID et la date de suppression. Il empêche un ancien envoi retardé de recréer le brief. Il ne conserve ni contact, ni contenu, ni empreinte de ce contenu. Les exports téléchargés ne peuvent pas être effacés à distance ; ils doivent être gérés séparément.

La proposition de revue des demandes sans suite après douze mois est un choix d’organisation à confirmer avec le responsable du traitement. **Aucune suppression automatique des demandes n’est annoncée ou exécutée.** La boîte permet aujourd’hui une suppression manuelle réelle. Il faudra attribuer la responsabilité de cette revue, qualifier la durée et documenter les copies et sauvegardes de production.

## Export vers l’atelier

L’export privé est `GET /api/admin/briefs/<requestId>/export`.

```json
{
  "format": "bojart.inquiry.export.v1",
  "exportedAt": "2026-10-19T12:00:00.000Z",
  "source": "BOJ.ART",
  "inquiry": {
    "format": "bojart.inquiry.v1",
    "requestId": "UUID v4 du dépôt",
    "reference": "BOJ-AAAAMMJJ-12CHIFFRESHEX",
    "createdAt": "date ISO",
    "updatedAt": "date ISO",
    "revision": 1,
    "status": "new",
    "privacyVersion": "2026-10-19"
  },
  "sha256": "empreinte hexadécimale de 64 caractères"
}
```

L’exemple abrégé omet les champs du brief requis par le contrat. Le serveur calcule `sha256(canonicalJSON({format,exportedAt,source,inquiry}))` ; les clés d’objets sont triées récursivement et l’ordre des tableaux reste inchangé. Le SHA vérifie l’intégrité du fichier ; **il ne constitue pas une signature d’authenticité de l’émetteur**.

Le passage Jarvis examine l’export avant de créer un dossier et conserve une référence vers la source, les paramètres techniques utiles et une synthèse choisie. Les coordonnées et le brief client brut n’ont pas à rejoindre le journal immuable de production. La source administrable et supprimable reste cette boîte D1. Un fichier déclaré prêt dans le formulaire n’apporte aucune preuve de réception, de mesure ou de compatibilité d’un STL.

## Vérification

`node qa/check-acquisition.mjs` applique les vraies migrations à Node SQLite, puis exerce le service avec de vrais objets Request/Response et WebCrypto. L’adaptateur reproduit l’API D1 et ses transactions. Le rapport est `qa/acquisition-results.json` ; `qa/inquiry-export-fixture.json` est un exemple produit par le dépôt puis l’export, avec des données de test fictives.

Les essais couvrent validation, jetons, contrôle d’accès, réception et reprise, conflits concurrents, limites atomiques, erreurs réelles d’insertion, correction des contacts, préservation de la version de l’information, export et altération, suppression et rollback, pagination. Ils ne prouvent pas à eux seuls le fonctionnement de D1 hébergé, de la session SIWC, du rendu graphique ou d’un service de messagerie. Le build et le résultat natif de publication doivent être vérifiés séparément.

`node qa/check-acquisition-ui-v11.cjs` rejoue les courses React et les réponses différées qui ont révélé les défauts de reprise. Voir [l’audit V11](audit-v11-acquisition.md) pour les preuves avant correction et les limites exactes.
