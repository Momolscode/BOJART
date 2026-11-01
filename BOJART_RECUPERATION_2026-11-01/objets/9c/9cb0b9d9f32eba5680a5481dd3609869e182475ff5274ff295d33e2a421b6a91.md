# BOJ.ART — Studio des contenus du dossier

Le Studio des contenus prépare et conserve les édits d’un **dossier précis** : intention, format, durée, quatre moments, publications de référence, légende et notes sonores. Chaque enregistrement ajoute une version consultable. L’export JSON décrit cette version et ses sources.

## Ouvrir le bon dossier

Depuis le dashboard, sélectionner le dossier à travailler puis ouvrir **Contenus**. L’accès direct est :

```text
?screen=pilotage&panel=contenus
```

Sur l’installation locale au port par défaut :

```text
http://127.0.0.1:3137/?screen=pilotage&panel=contenus
```

Le Studio capture l’identifiant du dossier à son ouverture. Une sélection effectuée dans une autre fenêtre ne réaffecte pas le formulaire ouvert. Le nom du dossier cible reste visible pendant la préparation.

Le **Studio de signature**, accessible avec `panel=studio`, conserve un autre rôle : présenter le film Baki existant et sa direction visuelle proposée. Les images de ce film ne deviennent pas automatiquement des images du dossier sélectionné. Le scénario déjà conservé dans le dossier sert de point de départ au brief d’un nouveau plan ; s’il est vide, les notes du dossier sont utilisées. Cette copie est limitée à 4 000 caractères et reste indépendante des modifications ultérieures du scénario.

## Préparer un édit

1. Créer un plan ou ouvrir un plan enregistré dans le dossier.
2. Choisir sa série : **Les œuvres**, **Le geste**, **Sur mesure**, **Prototype** ou **Disponible**. La série organise l’intention éditoriale.
3. Renseigner le titre, le brief, le format **9:16**, **1:1** ou **16:9**, puis une durée cible entière de **10 à 60 secondes**.
4. Décrire les quatre moments et sélectionner explicitement les publications utiles.
5. Ajouter la légende proposée et les notes sonores ; choisir le statut **brouillon** ou **prêt à monter**.
6. Enregistrer une version, puis exporter le plan JSON si nécessaire.

| Moment | Rôle de préparation |
|---|---|
| Détail | Choisir l’élément qui attire l’attention : matière, expression, finition ou caractéristique utile. |
| Geste | Montrer une étape, une technique, une main ou un essai. |
| Œuvre | Présenter la pièce entière, l’assemblage ou le résultat observé. |
| Signature | Préparer la conclusion et l’emblème à utiliser. |

Les quatre moments sont toujours présents. Chacun contient une note, une publication facultative et, pour une vidéo, une plage source facultative. Un brouillon peut donc conserver des choix encore ouverts. Le statut « prêt à monter » reste une déclaration de l’utilisateur ; l’export expose les sources ou passages restant à définir.

La durée saisie est un objectif éditorial. Elle ne change ni la vitesse des publications ni la durée d’un fichier vidéo existant. Les réglages du plan ne modifient pas le brief de fabrication, la révision des pièces, le devis ou le scénario conservé séparément.

## Choisir les sources et leurs passages

Le catalogue contient les **31 publications** de [`archive-index.json`](../dist/assets/archive-index.json). Sa projection dans [`content-catalog.js`](../dist/lib/content-catalog.js) permet d’appliquer les mêmes règles dans le navigateur et dans le service Node, sans recherche réseau lors de la sauvegarde d’un plan.

Une source reçoit une relation explicite :

| Relation | Signification |
|---|---|
| `reference` | La publication sert de référence visuelle, de geste ou de montage. Elle ne prouve pas que le dossier actuel représente la même pièce. |
| `project` | L’utilisateur déclare que le média concerne le dossier. Cette déclaration n’est pas une vérification automatique de la pièce, de sa taille ou de sa fabrication. |

Aucune publication n’est choisie à la création du brouillon. Une publication utilisée dans un moment doit aussi figurer dans les sources du plan, avec une seule relation pour ce plan. Un identifiant absent du catalogue est refusé.

**Les timecodes concernent la vidéo originale.** L’aperçu du dashboard peut ne montrer qu’un extrait de quelques secondes ; son début et sa durée sont conservés séparément. Par exemple, un passage situé à 24 secondes dans la vidéo originale n’est pas visible dans un aperçu limité à 4–10 secondes. Le choisir dans le plan ne signifie pas qu’il a été visionné dans cet aperçu.

Pour une vidéo dont la durée est connue, le début et la fin doivent être renseignés ensemble et respecter `0 ≤ début < fin ≤ durée originale`. Les champs peuvent tous deux rester vides. Une photographie ne possède pas de plage vidéo source. Lorsque la durée originale est inconnue, le passage reste à définir.

La publication `7099716894994730246` reste répertoriée comme indisponible dans l’archive. Elle peut être citée dans une préparation avec son incertitude, mais aucun passage chronométré ne peut être validé pour ce média. Une publication conservée dans l’archive peut aussi ne pas posséder d’aperçu dans le dashboard. L’export distingue ces situations.

## Versions, brouillons et concurrence

L’opération `SAVE_EDIT_PLAN` porte le dossier cible, un identifiant stable de plan, la révision attendue, l’identité de cette version de base (`expectedVersionId`) et le contenu complet du plan. La création attend la révision `0` avec une identité nulle. Une mise à jour attend le numéro et l’`operationId` de la dernière version conservée. Chaque réussite ajoute un snapshot avec son numéro, son identité d’opération, sa date, le nom du dossier et sa révision à cet instant.

Les versions précédentes restent consultables. Reprendre une ancienne version prépare une nouvelle version ; l’ancienne n’est pas réécrite. Une modification ultérieure du scénario du dossier n’altère pas le brief déjà copié dans un plan enregistré.

L’interface conserve la saisie lorsqu’un autre écran modifie le même plan et demande un choix explicite avant de poursuivre. Elle compare la révision **et le contenu conservé**, car deux créations concurrentes peuvent produire chacune une version `1` avant le rapprochement des journaux. La sauvegarde et l’export de la saisie obsolète sont alors refusés jusqu’à la reprise explicite sur l’état conservé ou au choix d’un autre plan.

Le contrôle ne dépend pas de l’arrivée d’une notification à l’écran. Avant une sauvegarde, le store relit le journal puis vérifie ensemble la révision et l’identité de la version attendue, avant toute modification. Une version `1` remplacée par une autre version `1` possède une identité différente : la saisie ancienne ne peut pas devenir silencieusement la version suivante de ce nouvel historique. L’export relit lui aussi le journal et vérifie l’identité de la version consultée.

Le journal conserve les opérations reçues, y compris les opérations en conflit lors d’une fusion. La reconstruction utilise l’ordre logique des opérations pour déterminer l’historique visible ; elle ne fusionne pas automatiquement les textes de deux plans concurrents. Un accusé de réception de la base locale confirme la conservation des opérations ; le résultat métier peut toujours signaler un conflit.

Un brouillon non enregistré reste une saisie de l’interface. **Enregistrer une version** est l’action qui l’ajoute au journal. Les commandes de reprise et les brouillons conservés dans le panneau permettent de faire un choix, mais ne constituent pas une sauvegarde indépendante du navigateur.

### Limites actuelles

| Élément | Limite |
|---|---:|
| Plans par dossier | 20 |
| Versions par plan | 50 |
| Publications déclarées par plan | 31 |
| Titre | 120 caractères |
| Brief | 4 000 caractères |
| Légende | 2 200 caractères |
| Note de chaque moment | 1 000 caractères |
| Notes sonores | 2 000 caractères |
| Plan JSON normalisé | 32 Kio |

Les limites sont exportées par `EDIT_LIMITS`. Les atteindre produit un refus explicite, sans purge. Après 50 versions d’un plan, un autre plan peut être créé si le dossier reste sous sa limite de 20 plans.

## Exporter la version enregistrée

Le fichier a le format `bojart.project-edit-plan.v1`. Il contient notamment :

- Le dossier cible, son nom et sa révision au moment de la version, ainsi que son nom et sa révision actuels dans des champs distincts.
- L’identifiant du plan, le numéro de version, son `operationId` et sa date d’enregistrement.
- Le brief, les quatre moments, les relations des sources, les passages, la légende et les notes sonores.
- Les URL des publications, leurs disponibilités et durées connues, ainsi que les informations propres aux aperçus.
- Les choix restant ouverts et les indications `renderRequested:false` et `publicationRequested:false`.

L’export vérifie que la version demandée appartient au dossier explicitement ciblé. Une version étrangère ou dont l’identité ou le contenu diffère du snapshot enregistré est refusée. Une version historique conserve son ancien nom de dossier, même après renommage ou sélection d’un autre dossier dans une autre fenêtre.

Cet export est **un plan de montage**, sans nouvelle vidéo, fichier audio, archive média ou publication sociale. Pour conserver et restaurer l’ensemble des versions et des opérations, utiliser la sauvegarde du journal dans **Continuité**, accessible avec `?screen=pilotage&panel=continuite`.

## Journal du navigateur et service SQLite

Dans le Site statique, les versions enregistrées rejoignent le journal de ce navigateur. Les fenêtres ouvertes sur la même origine partagent ces opérations. Si le stockage du navigateur est indisponible, l’interface indique une conservation limitée à la fenêtre.

Sur la tour, le service optionnel ajoute le journal SQLite lorsque la liaison locale est activée dans **Continuité**. Les plans utilisent les mêmes opérations et sauvegardes que les dossiers, devis et fiches du parc. Les renvois identiques sont dédupliqués ; la restauration ajoute les opérations manquantes avec la même origine de journal. La documentation complète se trouve dans [`local/WORKSHOP.md`](../local/WORKSHOP.md).

### Mettre à jour un service déjà lancé

Le processus Node charge les validateurs au démarrage. **Mettre à jour la page seule ne suffit pas** : une ancienne passerelle peut continuer à répondre tout en refusant le nouveau type `SAVE_EDIT_PLAN`.

1. Conserver une sauvegarde du journal et les paramètres du service, notamment le dossier de données choisi.
2. Arrêter normalement le processus local, puis mettre à jour le code du projet, y compris `dist/lib/workshop.js`, `dist/lib/edit-plan.js` et `dist/lib/content-catalog.js`.
3. Relancer le service avec Node.js 24 ou ultérieur, depuis la racine du projet :

   ```sh
   npm run start:local
   ```

4. Recharger les fenêtres de l’origine locale et vérifier l’état de la liaison dans **Continuité**.

Le répertoire de données SQLite et l’identité du journal doivent être conservés lors de cette mise à jour. Les opérations en attente gardent leurs identifiants ; un renvoi après reconnexion est dédupliqué. En cas de refus « opération invalide » après mise à jour du dashboard, vérifier d’abord que le processus local a lui aussi été mis à jour et redémarré.

## Vérifications du lot

[`qa/check-edit-plan.mjs`](../qa/check-edit-plan.mjs) vérifie les brouillons, les plages originales, les types stricts, les limites, la reprise du stockage et le refus d’une version remplacée avant notification. La QA du Studio de projet couvre aussi les interactions de formulaire, les conflits, les exports historiques et le parcours sauvegarde navigateur → SQLite fermé/réouvert → restauration additive. Ces contrôles ne constituent pas une mesure de qualité artistique ni une vérification de rendu sur les trois moniteurs.
