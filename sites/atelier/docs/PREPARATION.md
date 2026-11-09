# BOJ.ART — préparation des pièces

Le workbench confronte les dimensions du **STL effectivement disponible sur le poste** au volume utile renseigné dans la fiche d’une machine. Il prépare une inspection visuelle et un rapport exportable. Il ne modifie pas le fichier et ne produit pas de fichier de fabrication.

## Parcours

1. Ouvrir le dossier à préparer et importer ses STL.
2. Renseigner les machines de l’atelier : identité, procédé, volume utile XYZ en mm et source de ces dimensions.
3. Ouvrir la préparation du projet. Le contrôle relit les fichiers accessibles dans ce navigateur et mesure leur boîte englobante.
4. Choisir une pièce, une machine et une des six orientations. La scène et le rapport emploient les mêmes axes et les mêmes rotations.
5. Examiner les écarts bruts sur X, Y et Z ainsi que les informations de matière, de slicer et d’essai.
6. Exporter le rapport. Il contient le dossier inspecté, les versions des fiches, les mesures et la sélection calculée. Les STL restent des fichiers distincts.

Une référence à un fichier dans un dossier ne garantit pas que son binaire soit disponible sur un autre navigateur. Le contrôle distingue **sans fichier associé**, **fichier à relire**, **fichier absent**, **fichier invalide** et **fichier mesuré**. Un dossier restauré peut donc demander de retrouver ses fichiers.

## Données qui alimentent le calcul

Le module `dist/lib/preparation.js` utilise exclusivement les fiches obtenues avec `fleetRecordOf(machine)`. Une fiche participe à une correspondance lorsque son `origin` vaut `declared`. Les champs de simulation `machine.tech`, `machine.volume`, `machine.material`, `machine.qualified` et le nom de démonstration ne sont jamais utilisés comme caractéristiques réelles.

| Information | Source | Ce qu’elle établit |
| --- | --- | --- |
| Procédé machine | `registry.technology` | FDM, résine ou information manquante. |
| Volume utile | `registry.usableVolumeMm` | Enveloppe XYZ déclarée en mm. |
| Source du volume | `registry.volumeSource` | Référence ou explication fournie par l’atelier. |
| Matière | `registry.material` | Nom déclaré sur cette machine ; la matière requise par chaque pièce n’est pas encore spécifiée. |
| Slicer et profils | `registry.slicer` | Références déclarées du logiciel, de sa version, du profil machine et du profil matière. |
| Essai | `registry.qualification` | État déclaré, date, responsable et référence du résultat. |
| Mesures de la pièce | Lecture locale du binaire avec `inspectSTL` | Boîte englobante courante et nombre de triangles. |
| Dimensions du dossier | `piece.dims` | Information mémorisée, affichée séparément lorsqu’aucun binaire n’a été mesuré. |

Les profils restent des références textuelles : leurs fichiers ne sont pas chargés par ce contrôle. Un essai documenté n’est pas annoncé comme une qualification physique vérifiée. Une fiche complète ne déclenche aucune connexion.

### Unités et dimensions

`inspectSTL` interprète actuellement les coordonnées en `mm` ou en `inch`, puis retourne les dimensions en millimètres. Les coordonnées en pouces sont converties une seule fois, au moment de la lecture. `piece.dims` est déjà exprimé en mm et ne doit pas être reconverti par le moteur de correspondance.

Une ancienne valeur d’unité `cm`, `m`, `in` ou `inches` demande une correction explicite ; le moteur ne lui attribue pas silencieusement une autre interprétation. Une hauteur souhaitée de 1 m dans le dossier ne redimensionne jamais le STL.

Si les dimensions relues diffèrent de celles mémorisées dans le dossier, le rapport utilise les mesures du binaire et signale la divergence. Le fichier original et le dossier restent inchangés.

## Orientations et comparaison

`PREPARATION_ORIENTATIONS` est la source commune au calcul et à la scène. L’axe de sortie `i` est l’axe d’entrée `axes[i]` multiplié par `signs[i]`.

| Identifiant | Axes source vers XYZ machine | Signes |
| --- | --- | --- |
| `xyz` | X, Y, Z | +, +, + |
| `yxz` | Y, X, Z | +, −, + |
| `xzy` | X, Z, Y | +, −, + |
| `zxy` | Z, X, Y | +, +, + |
| `yzx` | Y, Z, X | +, +, + |
| `zyx` | Z, Y, X | +, −, + |

Ces transformations ont toutes un déterminant de +1. Elles déplacent les axes par une rotation propre et ne reflètent pas le modèle. Le signe ne change pas la taille de sa boîte englobante. Six permutations suffisent à comparer les dimensions de cette boîte ; elles ne décrivent pas toutes les orientations physiques possibles d’un objet.

Pour chaque axe, le rapport calcule :

`écart brut = dimension du volume déclaré − dimension orientée du STL`

Un écart négatif indique un dépassement. Une valeur nulle signifie une égalité dimensionnelle brute ; elle ne réserve aucune place pour les supports ou pour une tolérance. Aucune marge arbitraire n’est ajoutée.

Le moteur distingue le **résultat géométrique** de la **correspondance de procédé**. Une boîte peut tenir géométriquement dans une machine d’un autre procédé, mais cette machine ne figure pas parmi les orientations candidates de la pièce. `bestOrientationId` désigne simplement la première orientation qui tient dans l’ordre affiché ; il ne s’agit pas d’une recommandation de supports ou de qualité d’impression.

### Interprétation des états

| État | Signification |
| --- | --- |
| `not_declared` | La fiche ne décrit pas encore une machine déclarée. |
| `technology_unknown` | Le procédé de la pièce ou de la machine est manquant. |
| `technology_mismatch` | Les procédés déclarés ne correspondent pas. |
| `volume_missing` | Le volume utile n’est pas renseigné. |
| `file_unchecked` | Le binaire courant n’a pas été contrôlé sur ce poste. |
| `file_missing` | Aucun fichier n’est associé, ou le binaire est absent. |
| `file_invalid` | Le fichier ou ses mesures ne permettent pas le contrôle. |
| `non_volumetric` | Le STL est mesuré mais sa boîte a au moins une dimension nulle. |
| `fits` | La boîte brute et le procédé correspondent à au moins une orientation testée. |
| `exceeds` | La boîte dépasse dans les six permutations testées. |

`exceeds` ne prouve pas qu’aucune orientation oblique ne pourrait tenir. Le moteur ne recherche pas de rotations continues et ne découpe pas la pièce.

## Limites de la préparation

La fiche décrit une enveloppe rectangulaire XYZ. Un plateau circulaire ou une zone interdite ne sont pas représentés par ces trois nombres. Leur contour nécessite un contrôle supplémentaire ou une enveloppe rectangulaire réellement utilisable renseignée par l’atelier.

La mesure du STL n’établit ni fermeture du maillage, ni solidité, ni qualité de surface. Un maillage ouvert peut avoir une boîte qui tient. Un maillage plat peut être mesuré et affiché sans être considéré comme une pièce volumique.

Le contrôle n’évalue pas les supports, le brim, le raft, l’évidement, le drainage, les collisions, le retrait de matière ou les tolérances. Chaque pièce est examinée seule. La quantité du dossier ne produit ni placement de lot, ni nesting, ni durée estimée.

Les capacités `canSlice` et `canStartPhysicalPrint` restent toujours fausses. Il n’existe aucun nouveau type d’opération d’impression, de mise en file ou de journal dans cette phase. L’association d’un fichier à une pièce utilise l’opération `UPDATE_PIECE` existante. Les fonctions de simulation restent séparées du contrôle sur fiches déclarées.

## Contrat d’intégration

```js
inspectDeclaredPreparation(state, projectId, {assetEvidence: []})
exportDeclaredPreparation(report, {pieceId, machineId, orientationId}, at)
```

Le dossier est explicite. Un identifiant inconnu ou ambigu produit une erreur au lieu de choisir le dossier actif ou le premier dossier.

Chaque preuve locale est liée à :

```js
{
  projectId, pieceId, pieceRevision, assetId, unit,
  status: 'measured', // ou 'missing', 'invalid'
  dimsMm, triangles, byteLength, checkedAt,
  sha256 // facultatif ; 64 caractères hexadécimaux, ou null
}
```

Une preuve mesurée exige une boîte finie, au moins un axe positif, 1 à 2 000 000 triangles et une taille comprise entre 15 octets et 50 Mo. Les limites suivent le lecteur STL existant. Une preuve correspondant à une autre révision, à une autre unité ou à un autre fichier n’est pas retenue. Des preuves concurrentes ambiguës demandent une nouvelle lecture.

Le contrôleur doit également invalider les lectures asynchrones après un changement de pièce source et à la fermeture de la vue. Il doit conserver le dossier ciblé lorsqu’un autre écran modifie la sélection globale.

### Association d’un fichier à une pièce existante

Un import ciblé capture la pièce et le fichier qu’elle référence **avant** la lecture asynchrone du nouveau STL. L’opération d’association fournit ensuite ces deux gardes ensemble :

```js
{
  projectId, id: pieceId,
  expectedPieceRevision: revisionAvantLecture,
  expectedAssetId: assetIdAvantLecture || null,
  patch: {assetId: nouvelAssetId, dims, triangles, unit}
}
```

Le store relit son état avant le dispatch. Le reducer vérifie les gardes avant toute modification, puis les vérifie encore lors d’un rejeu du journal. Si la pièce a disparu, si sa révision a changé ou si son fichier est différent, l’association est refusée et le fichier déjà associé reste intact. Le contrôle du fichier protège aussi contre deux branches qui portent le même numéro de révision mais un fichier différent.

Les deux gardes sont optionnelles pour conserver le comportement des anciennes opérations. Si une garde est présente, l’autre devient obligatoire ; le contexte du journal doit également viser le même dossier. Une révision invalide, une garde partielle ou une sélection périmée ne doit pas être réessayée en supprimant ces champs.

**Service local :** mettre à jour les sources de l’atelier puis redémarrer le service local avant d’utiliser l’association ciblée avec synchronisation. Son validateur doit connaître ces deux nouveaux champs de `UPDATE_PIECE`. Conserver la base de données existante ; aucune réinitialisation ou suppression du journal n’est nécessaire. Un service resté sur l’ancienne version peut refuser ces opérations ; ce refus ne doit pas être contourné en retirant les gardes.

## Export et vérification

Le format d’export est `bojart.declared-preparation-export.v1`. Il contient un instantané indépendant du rapport et, si elle a été calculée, la sélection pièce–machine–orientation. Une sélection inconnue ou une orientation non calculée est refusée. Un rapport incomplet reste exportable avec une sélection d’orientation nulle.

L’empreinte SHA256 facultative identifie les octets relus pour le contrôle. Elle ne remplace ni la présence du STL, ni la validation de fabrication. Les fichiers de maillage ne sont pas incorporés à l’export.

Les vérifications métier s’exécutent avec :

```sh
node qa/check-preparation.mjs
```

Elles couvrent le registre réel, l’isolation des profils de démonstration, les rotations sans miroir, les axes et limites, les preuves périmées, les unités, les maillages plats, l’export du dossier exact et la protection contre un import ciblé qui termine après une modification sur un autre écran. La vérification de la vue et du lecteur STL réel appartient à la suite d’intégration. Ces contrôles ne constituent pas une vérification du rendu dans un navigateur physique ni un essai d’imprimante.

Un contrôle ciblé supplémentaire a suivi trois opérations d’association dans un aller-retour sauvegarde navigateur → restauration SQLite → fermeture/réouverture de la base → sauvegarde du service → reprise dans un nouveau store. Les deux gardes ont été conservées dans les trois opérations. Le validateur du service a refusé une garde partielle ; l’import périmé est resté refusé après restauration, et le dernier fichier valide est resté associé. Ce contrôle utilise une base temporaire isolée, sans imprimante ni réseau.
