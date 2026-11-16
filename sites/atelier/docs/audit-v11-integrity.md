# BOJ.ART — audit contradictoire de l’intégrité, V11

Date : 19 octobre 2026. Périmètre : journal navigateur, autorité SQLite, reçus et sauvegardes, coffre STL, transmission au coffre. Lecture complémentaire des contrats d’import vitrine et de décision Jev. L’interface de récupération est intégrée séparément par le travail principal dans `dist/app.js` et `dist/lib/integrity-view.js`.

## Résultat

Trois défauts ont été reproduits puis corrigés. Ils concernent la continuité des dossiers et la fiabilité des accusés de conservation. Ils n’ont nécessité ni remise à zéro, ni suppression de données, ni migration du schéma SQLite. Le moteur de décision métier reste `bojart.reducer.v2` : le sens des opérations valides et des reçus antérieurement confirmés n’est pas modifié.

| Défaut vérifié | Avant correction | Comportement livré |
|---|---|---|
| Journal navigateur illisible | Une opération JSON corrompue était ignorée. Le dossier pouvait disparaître de l’affichage et les nouvelles écritures restaient autorisées. Une origine illisible ou manquante pouvait être remplacée par une nouvelle date. | Lecture complète et validation avant adoption d’un nouvel état. Écritures et fusion suspendues lorsque l’intégrité échoue. Données brutes conservées, dernier état cohérent maintenu ; état vide explicite au premier démarrage bloqué. |
| Tampon STL modifié pendant l’écriture | Le dépôt utilisait les octets fournis par référence. Une modification du tampon après l’appel pouvait produire un reçu positif pour des octets dont le SHA ne correspondait plus au fichier écrit. | Le dépôt et le client prennent une copie des octets avant le calcul SHA et toute attente asynchrone. Le client capture également les champs du manifeste. |
| Nouvelle tentative STL sans date initiale | Le client générait une date différente à chaque envoi. Un même identifiant et un même fichier pouvaient alors être refusés comme manifeste différent après une perte de réponse. | Quand la date n’est pas fournie, le client laisse le dépôt l’attribuer puis la restituer depuis l’original. Une reprise, même avec un nouveau client, reçoit le même manifeste. |

## 1. Journal navigateur : un échec de lecture doit être visible

### Reproduction sur V10

Un stockage isolé a reçu un dossier de test créé par `WorkshopStore.dispatch('ADD_PROJECT', ...)`. Une seule valeur a ensuite été remplacée par du JSON incomplet. Le redémarrage du store produisait :

```json
{"test":"corrupt-operation","added":true,"preservedProject":false,"error":null,"seedWasRewritten":false,"canKeepWriting":true}
```

Pour une origine JSON invalide ou supprimée, la même reproduction montrait `seedWasRewritten: true` et `canKeepWriting: true`. Aucun fichier utilisateur réel n’a été modifié lors de ces tests.

### Correction

`dist/lib/workshop.js` exige désormais une origine reconnue et chaque opération complète avant d’adopter un état. Une opération ne peut pas changer d’identifiant par son nom de clé. Une disparition ou une substitution d’opération déjà lue dans la session provoque un signalement ; un reçu confirmé ne peut pas disparaître ou raccourcir silencieusement la séquence déjà lue.

Une erreur de lecture n’entraîne plus une nouvelle démonstration dans l’historique. Le premier chargement bloqué contient des listes vides. Lorsqu’un état a déjà été validé, il reste disponible pour consultation jusqu’à réparation. Les événements `change` conservent leur contrat ; l’application lit `store.integrityError` pour afficher le mode de récupération.

Le manque d’espace reste une situation différente : une opération qui ne peut pas être écrite est conservée en mémoire et indiquée comme telle. Un échec d’écriture d’un nouveau reçu n’invalide pas les anciens reçus persistés ; le nouveau reçu peut rester en mémoire jusqu’à reprise.

### Interface de récupération

- `store.integrityError` : texte explicatif ou `null`. `authorityError` conserve le même blocage pour les chemins existants.
- `store.recoverRawStorage()` : copie de travail `bojart.workshop.recovery.v1`, avec date, raison, textes bruts des seules clés du journal, opérations volatiles et dernier journal validé s’il existe.
- `store.recheckIntegrity()` : relit le stockage, sans réparation automatique, et retourne `{ok, message, retainedState}`.

La copie de récupération ne constitue pas une sauvegarde automatiquement réimportable. Elle donne les éléments nécessaires à une réparation précise sans écraser les originaux. Elle contient les données du journal et doit être conservée comme un document de l’atelier. Les autres données du navigateur, les secrets externes et les fichiers STL binaires n’y sont pas inclus.

## 2. Coffre STL : le reçu doit correspondre aux octets conservés

### Reproduction sur V10

L’appel à `createWorkshopAssetRepository().put()` a reçu un tampon et son empreinte correcte. Le tampon a été modifié immédiatement après l’appel, pendant l’attente d’écriture. Résultat observé :

```json
{"receivedSuccess":true,"fileCount":1,"read":"asset_integrity"}
```

Le dépôt confirmait ainsi un fichier qui échouait à sa première relecture. Cette reproduction utilise un fichier synthétique dans un répertoire temporaire.

### Correction

`local/workshop-assets.mjs` borne la taille avant copie, capture le contenu puis calcule son empreinte avant toute écriture asynchrone. `dist/lib/workshop-assets.js` capture également les octets, le nom, l’identifiant, la date éventuelle et l’empreinte attendue avant son premier `await`.

Le test couvre un `ArrayBuffer` et une vue partielle de tampon : seule la portion désignée est transférée. Les règles d’identifiant immuable, de manifeste stable, de restauration contrôlée et de comparaison des empreintes restent actives.

## 3. Coffre STL : reprise d’un envoi sans date fournie

Une reprise du même appel client sans `createdAt` donnait auparavant :

```json
{"firstSaved":true,"retry":"asset_id_conflict"}
```

La route du dépôt savait déjà retrouver la date de l’identifiant existant. Le client fabriquait cependant une nouvelle date et l’envoyait à chaque tentative. La correction omet ce champ lorsqu’il n’est pas fourni ; le reçu doit encore confirmer exactement l’identifiant, le nom, la taille et l’empreinte, et fournir une date valide.

Un scénario simule maintenant la perte de réponse après conservation, puis une reprise avec une nouvelle instance du client. Une seule entrée demeure dans le coffre et le reçu retrouve la date initiale. Les originaux possédant une date explicite gardent leur comportement antérieur.

## Vérifications exécutées

| Commande | Couverture et résultat |
|---|---|
| `node qa/check-v11-integrity.mjs` | 16 groupes : stockage corrompu, origine absente, opérations substituées, reprise, copie brute, panne de lecture, quotas, autorité, multi-écrans, tampons mutables et reprise du coffre sans date. |
| `node qa/check-workshop-authority.mjs` | 11 groupes : ordre confirmé, collisions, migration ancienne, genèse, reprise et refus de corruption SQLite. |
| `node qa/check-workshop-backend.mjs` | 14 groupes : transactions, doublons, sauvegardes, pagination, contrats et routes injectées. |
| `node qa/check-workshop-assets.mjs` | 8 groupes : octets originaux, immutabilité, archives et restauration, client, réponses incohérentes et délai borné. |
| `node --experimental-vm-modules qa/check-durable-integration.cjs` | 20 groupes : plusieurs contextes JSDOM, formulaires conservés, import additif, pertes d’accusé et tour SQLite temporaire. |
| `node --experimental-vm-modules qa/check-v11-recovery-ui.cjs` | 6 groupes sur l’application complète : démarrage bloqué, copie téléchargée, absence de boucle de réexamen, reprise, brouillon intact et garde des commandes. |
| `node qa/check-inquiry-import.mjs` | 12 groupes de régression exécutés après la correction du lecteur : projection technique, séparation des contacts, conflits et export vers l’autorité. Le comparateur V11 possède sa propre suite. |

Les résultats sont conservés dans `qa/v11-integrity-results.json` et les fichiers de résultat associés aux suites. Ils portent sur le code réellement présent. Aucun serveur d’écoute, accès matériel, compte social, paiement ou message client n’a été déclenché. Les tests JSDOM n’établissent pas une validation graphique, WebGL ou navigateur réel.

## Limites restantes et décisions d’architecture

1. **Conservation navigateur et autorité sont distinctes.** Un événement supprimé avant un redémarrage, dans un ancien journal sans reçu externe ni sauvegarde de référence, peut être impossible à prouver absent. Le navigateur conserve les travaux locaux ; l’autorité SQLite et les sauvegardes vérifiées apportent une référence indépendante. La nouvelle vérification n’est pas un mécanisme d’authentification des données.
2. **Les empreintes établissent la cohérence d’un contenu.** Une personne capable de modifier à la fois un fichier JSON et son empreinte peut fabriquer un document cohérent. Le SHA d’un export vitrine ne prouve donc pas à lui seul l’identité de son émetteur. L’import reste un examen opérateur à partir de l’administration privée.
3. **Le coffre et le journal ont deux sauvegardes.** Le fichier JSON de l’atelier ne contient pas les STL. La restauration d’un poste doit vérifier le journal et l’archive `.bojassets`, puis relire les fichiers référencés. Un essai de restauration sur le poste réel reste à organiser.
4. **Jev reste consultatif.** Les contrats examinés limitent ses sorties aux choix disponibles, au contexte et aux révisions, avec délai d’expiration et abstention. Les entrées fournisseur n’ajoutent aucune capacité de slicing, d’impression ou de publication. Ces garanties ne remplacent pas la qualification d’un futur connecteur physique.
5. **Un état physique inconnu doit rester inconnu.** Lorsqu’un futur envoi à une imprimante perd sa réponse, il faudra interroger le travail identifié et son empreinte avant d’autoriser une reprise. La nouvelle fiabilité du transfert de fichiers n’équivaut pas à cette garantie machine.
6. **Le déploiement du service local est distinct de la vitrine hébergée.** Les corrections du navigateur sont incluses au site. Le code `local/` devra également être utilisé sur la tour pour bénéficier des corrections du dépôt STL ; aucune machine distante n’a été mise à jour par cet audit.
