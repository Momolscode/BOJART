# BOJ.ART — journal v2 et coffre STL de la tour

Le service local conserve les dossiers, les fiches du parc, les travaux **simulés**, les devis, les contenus et les originaux STL. SQLite décide et enregistre le résultat métier de chaque commande de journal. Le coffre conserve séparément les octets des fichiers avec leur empreinte SHA-256.

Cette version ne contient aucun connecteur d’imprimante, commande de slicer, moteur de voix ou lancement de fabrication. Un reçu du journal ne constitue jamais un reçu d’exécution physique.

## Lancement et périmètre local

Utiliser Node.js 24 ou ultérieur. Les vérifications décrites ici ont été réalisées avec Node.js 24.19.0, sans dépendance npm supplémentaire pour le service.

```sh
npm run start:local
```

Le point d’entrée est `http://127.0.0.1:3137`. Le service écoute uniquement sur l’interface de boucle locale ; `BOJ_JEV_PORT` permet de changer son port. Dans le dashboard ouvert sur cette origine locale, l’utilisateur active la conservation du journal et peut synchroniser les STL avec le coffre. Les trois écrans partagent la même autorité locale.

La version statique hébergée utilise son propre stockage navigateur. Elle ne peut pas appeler implicitement le `localhost` de la tour depuis son origine distante. Le transfert portable documenté ci-dessous permet de déplacer ses dossiers et fichiers sur la tour.

`BOJ_WORKSHOP_DATA_DIR`, facultatif, doit être un **chemin absolu** vers un dossier réservé aux données, hors de `dist/`.

| Système | Dossier par défaut |
|---|---|
| Windows | `%LOCALAPPDATA%\BOJ.ART\workshop` |
| macOS | `~/Library/Application Support/BOJ.ART/workshop` |
| Linux | `$XDG_STATE_HOME/bojart/workshop`, ou `~/.local/state/bojart/workshop` |

Le journal est dans `workshop.sqlite3`. Le coffre utilise le sous-dossier `assets/` : `assets.sqlite3` pour les associations immuables, `blobs/<sha256>.stl` pour les originaux et `staging/` pour les transferts temporaires. Les données restent hors des fichiers publics du site. Les clés des fournisseurs restent des variables du processus et ne sont pas exportées.

## Ce que confirme le protocole v2

Chaque lot est validé puis traité sous une transaction SQLite `BEGIN IMMEDIATE`. WAL et `synchronous=FULL` sont activés. La réponse est renvoyée après le `COMMIT` des opérations **et de leurs reçus métier**.

1. L’opération brute conserve son identifiant et ses octets JSON canoniques. Le même identifiant avec un autre contenu refuse le lot entier.
2. Le serveur attribue une séquence croissante au reçu. L’horloge et l’identifiant du client n’intercalent plus une commande arrivée tard devant une commande déjà confirmée.
3. Chaque mutation annonce `expected.entityVersion`. Une version périmée produit un reçu avec `outcome.ok:false`, conservé dans le journal. Son contenu n’est pas perdu et son effet n’est pas appliqué.
4. Un retry du même identifiant renvoie le même reçu, y compris le résultat refusé. Une réouverture ou une restauration compatible ne recalcule pas un autre gagnant.
5. Le navigateur reconstruit le préfixe confirmé dans l’ordre serveur, puis applique les commandes locales encore provisoires. Il distingue le reçu confirmé, la commande en attente et le conflit à examiner.

Les versions de concurrence sont distinctes des révisions géométriques. Les mutations d’un dossier, de ses pièces, de son devis ou de ses contenus partagent une version de dossier. Les mutations d’une machine et de son travail simulé partagent une version de machine. Ce choix conservateur peut demander de réappliquer une modification quand deux écrans modifient deux champs du même dossier. Il évite un écrasement silencieux. Les sélections et les messages de journal ne requièrent pas de version de ressource.

### Exemple de reçu

```json
{
  "version": 1,
  "seq": 1,
  "operationId": "screen-a-command-1",
  "receivedAt": 1700000010000,
  "entityKey": "[\"project\",\"sculpture-xl\"]",
  "entityVersionBefore": 0,
  "entityVersionAfter": 1,
  "outcome": {"ok": true, "message": "Dossier mis à jour."}
}
```

`accepted` dans l’enveloppe HTTP signifie « nouvelle opération et reçu conservés ». Il faut lire `receipt.outcome.ok` pour savoir si la modification métier a été appliquée. Aucun champ de ce reçu ne signifie qu’une imprimante a exécuté une commande.

Les reçus et la genèse sont associés au moteur `bojart.reducer.v2`. Une relecture incompatible est refusée explicitement. Le moteur ne remplace pas un reçu historique par son résultat courant.

## Migration conservatrice de la version précédente

Avant une mise à niveau d’une tour utilisée, conserver son export de journal v1 et ses originaux. Une copie brute du dossier de données nécessite d’arrêter proprement le service ; ne pas copier uniquement le fichier SQLite pendant des écritures WAL.

À l’ouverture d’une base SQLite reconnue en schéma v1 :

- Les lignes originales de la table `operations`, leurs empreintes et leur ordre d’arrivée SQLite restent inchangés.
- L’ancien ordre de reconstruction `clock`, puis `id`, est lu **une fois** pour figer les résultats qui étaient visibles avant la migration.
- Une table `decisions` conserve ces résultats dans une séquence explicite. La genèse complète est persistée avec son empreinte et une identité d’atelier `workspaceId` est créée.
- La migration est une seule transaction. Une erreur conserve la base existante ; aucune base vierge de remplacement n’est créée.

Le gagnant d’un ancien conflit n’est pas changé pour lui appliquer rétroactivement la nouvelle règle. Après migration, les nouvelles commandes suivent l’ordre du serveur et annoncent leur version attendue.

Le frontend et le service doivent être mis à niveau ensemble. Un POST d’opérations HTTP v1 reçoit `426 upgrade_required`. Les **fichiers de sauvegarde v1** restent importables : ils peuvent initialiser un atelier vide ou répéter des opérations déjà présentes. Un historique v1 contenant des opérations inédites ne peut pas réordonner une autorité existante ; il reçoit `409 legacy_merge_requires_review` et reste disponible pour examen dans un atelier vide.

Une restauration v2 dans une base vierge préserve `workspaceId`, la genèse et les reçus. Elle garde une nouvelle identité de base `instanceId`. Une restauration sur une base existante doit partager le même préfixe confirmé ; une branche divergente est refusée. Un ancien export compatible n’efface pas des commandes plus récentes. Le client revérifie tout son ancien préfixe après une connexion ou reconnexion, y compris vers un clone dont le `workspaceId` est identique.

## Contrat HTTP du journal

Toutes les routes passent d’abord par les contrôles `Host`, `Origin` et `Sec-Fetch-Site` de la passerelle. Aucun CORS n’est ouvert. Les POST du journal utilisent `Content-Type: application/json`. Le client ne fournit jamais de chemin de fichier serveur.

### Champs communs

| Champ | Signification |
|---|---|
| `ok`, `version:2` | Enveloppe reconnue du protocole v2 |
| `instanceId` | Identité de la base locale, persistée à la réouverture |
| `workspaceId` | Identité portable de la séquence de l’atelier |
| `seed` | Origine historique `{version:1,at}`, ou `null` avant initialisation |
| `genesis` | Snapshot initial complet `bojart.workshop.genesis.v1`, ou `null` |
| `reducerVersion` | `bojart.reducer.v2` |
| `cursor`, `operationCount` | Nombre de reçus confirmés ; séquence continue |
| `lastWriteAt` | Heure serveur du dernier enregistrement |

La genèse v1 est un snapshot de démonstration figé. Changer ce scénario initial exige un nouveau format de genèse ; modifier silencieusement la fonction de seed v1 rendrait les sauvegardes incompatibles.

### Routes

| Route | Comportement |
|---|---|
| `GET /api/workshop/status` | Champs communs, `storage:"sqlite"`, `durable:true`, limites et capacités ; ne crée pas l’origine |
| `GET /api/workshop/operations?after=0` | Opérations et reçus alignés, `nextCursor`, `hasMore` ; 200 entrées au maximum |
| `POST /api/workshop/operations` | Transaction d’opérations nouvelles, reçus persistés et doublons |
| `GET /api/workshop/backup` | Export JSON v2 contrôlé ; `409 not_initialized` si aucune origine |
| `POST /api/workshop/backup` | Restauration vérifiée d’un export v1 ou v2 |

Le POST d’opérations reçoit :

```json
{
  "version": 2,
  "workspaceId": "workspace-00000000-0000-0000-0000-000000000000",
  "seed": {"version": 1, "at": 1700000000000},
  "operations": []
}
```

L’exemple utilise une identité factice : un client utilise le `workspaceId` réellement fourni par le service. L’enveloppe d’une opération conserve `version:1`, `id`, `clock`, `at`, `type`, `payload`, `expected`, `context`. La version de protocole HTTP et la version d’opération sont deux contrats distincts.

La réponse POST ajoute `accepted`, `duplicates` et un reçu stable pour chaque identifiant soumis. Un HTTP 200 peut donc contenir des refus métier. En cas de réponse réseau perdue, le client relit la séquence ou renvoie les **mêmes identifiants et contenus**. Il ne fabrique pas une nouvelle identité de commande pour un retry.

Le statut du journal annonce `capabilities:{printerCommands:false,stlStorage:false,businessReceipts:true,persistedGenesis:true}`. `stlStorage:false` décrit exclusivement le périmètre du **journal JSON** ; le service séparé du coffre annonce sa capacité de stockage binaire.

| Limite | Valeur |
|---|---:|
| Opérations par POST | 100 |
| Taille d’une opération | 65 536 octets |
| Corps d’un POST d’opérations | 2 097 152 octets |
| Page, opérations et reçus compris | 200 entrées / environ 2 Mio au maximum |
| Export/import JSON | 16 777 216 octets |
| Opérations conservées | 50 000 |

Un dépassement refuse l’action sans purge. Les principaux codes sont `upgrade_required`, `expected_version_required`, `seed_conflict`, `authority_conflict`, `operation_id_conflict`, `legacy_merge_requires_review`, `checksum_mismatch`, `cursor_out_of_range`, `journal_full`, `backup_too_large` et `storage_unavailable`. Les détails SQLite et chemins internes ne sont pas renvoyés au navigateur.

## Coffre des originaux STL

`local/workshop-assets.mjs` exporte :

```js
createWorkshopAssetRepository({directory, now})
handleWorkshopAssetRequest({request, response, pathname, assets})
```

Le handler est appelé **après** la validation d’origine de la passerelle ; il ne crée aucun serveur d’écoute. Les méthodes du dépôt sont `status`, `list`, `put`, `get`, `exportArchive`, `restoreArchive`, `close`.

Chaque association immuable contient `{id,name,sha256,byteLength,createdAt,format:"stl"}`. Un upload calcule et vérifie le SHA-256 des octets, écrit puis synchronise le binaire, et confirme ensuite son association SQLite. Une répétition identique est un doublon. Le même ID avec un autre nom, timestamp ou binaire est refusé. Le hash détermine le nom du fichier sur disque ; le nom choisi par l’utilisateur n’est jamais un chemin d’extraction.

Une lecture revérifie le hash. Un binaire absent peut être récupéré depuis une archive vérifiée. Un binaire présent mais corrompu est signalé ; le service ne l’écrase pas automatiquement. Il faut conserver sa trace et traiter ce défaut de stockage. Une interruption avant la transaction des associations peut laisser un binaire immuable non référencé ; cette version ne le supprime pas automatiquement.

Le coffre atteste la conservation des octets. L’extension `.stl` et un hash valide ne certifient ni la validité du maillage, ni sa capacité à être fabriqué. L’inspection géométrique et les qualifications restent des étapes séparées.

### Routes binaires

| Route | Données |
|---|---|
| `GET /api/workshop/assets/status` | Capacités réelles du coffre et nombre de fichiers |
| `GET /api/workshop/assets?after=0` | Manifeste paginé, 100 associations au maximum |
| `POST /api/workshop/assets/:id` | Octets originaux, `application/octet-stream` |
| `GET /api/workshop/assets/:id` | Octets avec ID, nom, taille, date et SHA-256 dans les en-têtes |
| `GET /api/workshop/assets/backup` | Téléchargement `.bojassets` |
| `POST /api/workshop/assets/restore` | Archive brute `.bojassets` |

L’upload d’un fichier utilise `X-BOJ-File-Name` encodé par `encodeURIComponent`, `X-BOJ-SHA256` et `X-BOJ-Created-At`. Le client réutilise le timestamp du record original pour ses retries.

`dist/lib/workshop-assets.js` exporte `assetSHA256(buffer)` et `createWorkshopAssetClient()`. Le client fournit `status()`, `putAsset(record)`, `readAsset(id,{expectedSha256})`, `listAssets(after)`, `restoreBackup(file)` et `backupURL`. Il vérifie le reçu et les bytes téléchargés. Une lecture de fichier absent renvoie `null` uniquement si le service retourne `asset_missing` ; l’absence de service et les défauts d’intégrité sont des erreurs distinctes.

Le statut est borné à 2,5 secondes ; un transfert complet à 120 secondes. Les lectures téléchargées sont plafonnées pendant le streaming, même si le serveur ment sur `Content-Length`. La passerelle accorde une fenêtre serveur plus longue aux gros transferts. Au maximum deux transferts de fichiers sont traités simultanément par dépôt.

| Limite | Valeur |
|---|---:|
| Un original STL | 50 Mio |
| Associations | 10 000 |
| Manifeste d’archive | 16 Mio |
| Archive côté tour | 1 Gio |
| Export navigateur portable | 256 Mio |

Le champ optionnel `piece.assetSha256` lie une pièce à son original. Remplacer `assetId` sans fournir de nouveau hash efface l’ancien hash. Modifier le fichier ou son empreinte invalide la révision de pièce et les preuves de préparation dépendantes.

## Sauvegarder et restaurer l’ensemble des dossiers et STL

Il existe **deux exports complémentaires**, chacun avec une restauration vérifiée. Il ne s’agit pas d’un paquet transactionnel unique de toute la tour.

| Export | Contient | Exclut |
|---|---|---|
| Journal `.json` v2 | Dossiers, opérations, fiches, devis, contenus, genèse, reçus | Octets STL, secrets, états physiques |
| Coffre `.bojassets` | Originaux STL et leurs associations avec SHA-256 | Journal, secrets, états physiques |

Un navigateur sans autorité locale exporte encore un JSON v1 restaurable. Dès qu’il a reçu une autorité v2, son JSON inclut les reçus confirmés et peut aussi contenir des commandes locales explicitement provisoires. Le serveur décide ces commandes provisoires après le préfixe confirmé quand il restaure un export compatible.

Pour passer du site hébergé à une tour vide :

1. Arrêter les modifications pendant la prise des deux exports. Exporter le JSON du journal et l’archive des originaux depuis le même navigateur.
2. L’export navigateur collecte les fichiers courants **et les anciens originaux référencés par les opérations d’import**, y compris un import ultérieurement remplacé ou refusé. Il refuse d’annoncer une sauvegarde si un original requis manque ou si son hash diffère.
3. Sur l’origine locale, restaurer d’abord l’archive des STL, puis le JSON dans l’atelier visé. Une pièce peut ainsi retrouver ses octets par ID et vérifier le hash attendu.
4. Vérifier le reçu de restauration du coffre et ouvrir les modèles associés. Conserver les deux exports ensemble sur un autre support que le disque de la tour.

Les deux fichiers n’ont pas de numéro de snapshot commun. Si des commandes ou imports interviennent entre les deux exports, ils peuvent décrire deux instants différents. L’interface distingue les périmètres et les références absentes ; elle ne promet pas un snapshot atomique de l’ensemble des données.

### Format portable `.bojassets`

- 8 octets ASCII : `BOJAST01`.
- Un entier non signé de 4 octets, big-endian : longueur UTF-8 du manifeste.
- Le manifeste JSON.
- Les octets de chaque asset concaténés, dans l’ordre du tableau `assets`.

Le corps du manifeste est `{format:"bojart.assets.backup.v1",exportedAt,assets}`. Son champ `sha256` est l’empreinte de `canonicalWorkshopJSON(corps)`. Chaque entrée d’asset contient son propre hash, sa longueur exacte, son ID et ses métadonnées.

La restauration contrôle l’enveloppe, la taille totale, tous les IDs, le hash du manifeste et les hashes de **tous** les STL avant de rendre une association visible. Une deuxième phase conserve les fichiers immuables, puis une unique transaction ajoute les associations. Une archive tronquée, corrompue, avec chemins ou identités contradictoires est refusée. Les SHA-256 vérifient l’intégrité ; ce ne sont pas des signatures d’authentification.

## Vérifications réalisées et limites restantes

```sh
node qa/check-workshop-authority.mjs
node qa/check-workshop-assets.mjs
node qa/check-workshop-backend.mjs
node --experimental-vm-modules qa/check-durable-integration.cjs
```

- **Autorité : 11 scénarios.** Le cas synthétique `z-fenetre` arrivé avant `a-fenetre` conserve désormais le premier reçu accepté et le même STL après arrivée concurrente, retry et réouverture. Tests aussi des versions attendues, migration v1 byte-for-byte, backup v2, branche refusée, deux écrans au premier raccordement, genèse, reprise navigateur et remplacement de SHA.
- **Coffre : 8 scénarios.** Octets exacts, identité immuable, réouverture, export/restauration, refus sans association partielle, binaire absent, corruption, export navigateur avec originaux historiques vers le serveur, HTTP et timeout.
- **Backend : 14 groupes.** Contrat v2, pagination, validation, sauvegardes et protections HTTP dans la passerelle réelle.
- **Intégration : 20 groupes.** Contextes JSDOM isolés, store réel, sauvegarde navigateur, SQLite, ACK perdu, reprise, conflits, formulaires non enregistrés et indicateurs de conservation.

Ces tests utilisent des bases temporaires et des flux HTTP injectés. Aucun serveur d’écoute, navigateur graphique, fournisseur Jev ou équipement n’est lancé. La réouverture est vérifiée ; une coupure électrique réelle, la résistance d’un SSD, un manque d’espace disque et le rendu WebGL ne le sont pas. La synchronisation des répertoires est demandée sur les systèmes qui la supportent ; certaines plateformes Windows ne fournissent pas cette garantie via l’API de fichiers utilisée.

Le journal relit encore les opérations et reçus pour valider ses transactions. Un checkpoint versionné et une récupération incrémentale sont à dimensionner avant un historique volumineux. La séparation des lots de production et des révisions géométriques reste à réaliser ; les IDs actuels de travaux représentent toujours la simulation historique. Avant tout envoi physique, ajouter une file matérielle durable, un adaptateur qualifié par imprimante et une réconciliation explicite des commandes dont le résultat est inconnu.

Références techniques : [SQLite dans Node.js](https://nodejs.org/api/sqlite.html), [WAL](https://www.sqlite.org/wal.html), [synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous).
