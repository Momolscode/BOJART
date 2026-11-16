# BOJ.ART — Audit contradictoire de l’acquisition, V11

Date : 19 octobre 2026. Source examinée : `11ced14511012cace74fb6df90b81bd7e80798e9`, puis corrections locales décrites ici. La publication est effectuée séparément par le coordinateur du projet.

## Verdict

L’administration applique déjà l’identité fournie par Sites et une liste explicite d’administrateurs sur chaque opération côté serveur. L’effacement transactionnel, les contrôles d’origine, le jeton HMAC, la révision attendue et l’empreinte d’export étaient présents. Les essais n’ont pas révélé de route permettant à une session non autorisée de lire les demandes.

L’audit a trouvé des défauts de disponibilité, de reprise et de cohérence des actions. Ils ont été reproduits avant correction dans le code réel avec SQLite, React et des réponses différées. Aucun dossier client réel n’a été consulté, créé ou supprimé pour ces essais. Le statut public de la vitrine n’accorde pas l’administration aux visiteurs.

## Défauts démontrés et corrections

| Priorité | Reproduction avant correction | Conséquence | Correction livrée |
|---|---|---|---|
| P1 | 305 essais depuis un même client : 6 demandes admises, compteur global à 300. | Un client déjà limité pouvait épuiser la réception commune. | Réservation du quota global et des deux quotas client dans une seule transaction. Un refus client ne débite plus le quota commun. |
| P1 | 50 essais concurrents d’un même client : 6 admis mais 50 unités globales consommées. | Les demandes refusées consommaient aussi la limite journalière. | Les trois réservations sont liées dans le même lot SQL ; 6 unités sont consommées dans ce scénario. |
| P1 | Après un POST dont l’écriture est supposée réussie, retour JSON 400 non reconnu par le client. | L’UUID était effacé et le prochain envoi pouvait créer une seconde demande. | Seuls les couples statut/code de rejet attendus sont reconnus ; les réponses inconnues conservent le contenu et l’identifiant. |
| P1 | Une première réponse est perdue ; le nouvel essai reçoit `422 validation_failed`. | L’UUID du premier envoi était perdu malgré son résultat inconnu. | L’incertitude du premier POST est enregistrée avant l’appel. Un refus ultérieur ne permet pas d’en déduire l’absence d’un premier enregistrement. |
| P1 | Deux événements d’envoi arrivent avant le nouveau rendu React. | Deux opérations avec deux UUID étaient préparées. | Verrou immédiat en mémoire avant le premier appel asynchrone. |
| P2 | L’administrateur sélectionne B puis déclenche immédiatement l’ancien bouton Enregistrer de A. | Une écriture pouvait encore cibler A alors qu’une lecture de B était en cours. | Verrous immédiats de lecture et d’écriture, identité de génération et rejet de l’action pendant le changement de dossier. |
| P2 | Le serveur retourne `410 request_deleted`. | Le formulaire proposait indéfiniment de renvoyer une demande supprimée. | État terminal « Demande supprimée », conservé lors de la réouverture. Nouveau brief vierge uniquement après action explicite. |
| P2 | Le service de jeton échoue avant tout POST. | Le brief non envoyé devenait impossible à modifier. | Une tentative qui n’a pas atteint POST reste éditable. Une ancienne tentative incertaine conserve son identifiant. |
| P2 | Une tentative incertaine est rouverte après 48 heures. | L’expiration après 24 heures effaçait silencieusement sa continuité et ouvrait un nouveau formulaire. | Le contenu et les coordonnées sont retirés de cet onglet ; un avis minimal conserve l’UUID pour vérification. La nouvelle saisie nécessite un choix explicite. |
| P3 | L’horloge avance pour une correction, puis recule de 30 secondes pour la suivante. | `updatedAt` pouvait devenir antérieur à la modification précédente. | L’horodatage est au moins égal à la date de création et à la dernière modification. |

P1 indique ici un risque de doublon ou de disponibilité de l’acquisition. Ce classement est interne au projet ; aucun score CVSS ou audit de sécurité externe n’est revendiqué.

## Comportement de reprise

Le client distingue désormais quatre situations :

1. **Avant POST** : aucune tentative nouvelle n’est parvenue à la réception ; le brief peut être corrigé.
2. **Après POST, résultat inconnu** : même contenu, même UUID, aucun reçu inventé. Un retour JSON mal formé, un délai dépassé ou une réponse qui ne correspond pas au contrat ne réinitialise pas la tentative.
3. **Reçu reconnu** : l’UUID, le format du reçu, la référence et la date sont vérifiés ; la tentative locale est retirée.
4. **Suppression reconnue** : l’ancienne demande n’est plus renvoyée. Le visiteur peut garder une copie ou commencer volontairement un nouveau brief vierge.

Après 24 heures, le formulaire ne conserve plus le contenu d’une tentative incertaine lorsqu’il la relit. Il crée un avis dans `sessionStorage` limité à l’UUID, au motif et à la date de cet avis. Il ne s’agit ni d’un reçu ni d’une preuve de traitement. L’avis disparaît lors de son abandon explicite ou avec la session du navigateur. Il n’y a pas de minuterie exécutée lorsque l’onglet est fermé : l’expiration est évaluée à la prochaine ouverture du formulaire.

Les tentatives illisibles passent également par un avis de reprise. Le téléchargement de cet avis ne contient aucune coordonnée ni description. Il reste impossible de garantir une reprise après suppression manuelle de tout le stockage du navigateur ; la copie téléchargée constitue alors le repère à conserver.

## Administration et mutations

Chaque API d’administration vérifie l’autorisation côté serveur. La page protégée constitue une entrée de navigation, pas l’unique protection. Les en-têtes d’identité sont supposés fournis et nettoyés par la plateforme Sites : les tests locaux injectent ces en-têtes et ne constituent pas une validation indépendante de l’infrastructure SIWC.

Une lecture en cours interdit immédiatement une mutation de l’ancien dossier. Une écriture interdit immédiatement le changement de sélection. Les réponses d’une ancienne génération ne remplacent pas la sélection actuelle. Les appels ont un délai de 20 secondes ; une réponse perdue après mutation conduit à relire le dossier. Une modification reste soumise à la révision SQL attendue.

Le lien d’export produit la version enregistrée dans la boîte. Une empreinte SHA-256 détecte une altération accidentelle du fichier ; elle n’est pas une signature attestant son auteur. Le passage dans Jarvis reste un export/import examiné par l’opérateur.

## Preuves conservées

| Fichier | Rôle |
|---|---|
| `qa/acquisition-v11-before.json` | 17 groupes de base réussis et 3 nouveaux échecs backend avant correction. |
| `qa/acquisition-ui-v11-before.json` | Les 6 premiers groupes contradictoires UI échouaient avant correction. |
| `qa/acquisition-ui-v11-expiry-before.json` | Reproduction distincte de l’expiration silencieuse, après correction des six premiers groupes. |
| `qa/acquisition-results.json` | Résultat du moteur réel SQLite, WebCrypto et Request/Response. |
| `qa/acquisition-ui-v11-results.json` | Résultat des courses d’interface et des scénarios de reprise dans React. |
| `qa/storefront-results.json` | Régressions du parcours, des composants visuels et de la navigation clavier. |

Commandes de contrôle :

```sh
node qa/check-acquisition.mjs
node qa/check-acquisition-ui-v11.cjs
node qa/check-storefront.cjs
node node_modules/typescript/bin/tsc --noEmit
git diff --check
```

## Limites et suites utiles

Les contrôles locaux ne remplacent pas une recette dans un navigateur avec une session réelle et une demande de test explicitement isolée sur le déploiement. Aucun rendu graphique, lecteur d’écran, connecteur d’imprimante, service de messagerie ou paiement n’a été vérifié ici. Les migrations et l’audience ne sont pas modifiées par cet audit.

Le calcul du quota utilise le caractère transactionnel et séquentiel de `D1Database.batch()` ainsi que `changes()` de SQLite. Un test sur la base hébergée sera utile à la recette du déploiement ; les reproductions actuelles exécutent le SQL dans SQLite avec un adaptateur D1 local.

L’éditeur légal, le contact professionnel, la politique de conservation effective et les conditions de vente restent à confirmer dans le travail global d’ouverture commerciale. Le fait que les protections techniques soient présentes ne signifie pas que ces contenus sont juridiquement finalisés.

La prochaine extension utile est un suivi des changements significatifs de devis et d’accord, avec les versions conservées et une réception client vérifiable. Elle doit prolonger les invariants d’identifiant, de version et de preuve plutôt qu’ajouter des statuts sans pièce justificative.

## Sources techniques primaires

- [Cloudflare — D1Database et batch](https://developers.cloudflare.com/d1/worker-api/d1-database/) : exécution séquentielle des instructions et annulation du lot en cas d’erreur.
- [SQLite — fonctions scalaires, changes](https://sqlite.org/lang_corefunc.html) : nombre de lignes modifiées par la dernière instruction INSERT, UPDATE ou DELETE.

Sources consultées le 19 octobre 2026. Les constats propres à BOJ.ART sont issus du code et des reproductions référencées ci-dessus.
