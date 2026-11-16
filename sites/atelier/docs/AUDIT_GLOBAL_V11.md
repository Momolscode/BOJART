# BOJ.ART — audit global et cohérence du projet · V11

Audit du 19 octobre 2026. Périmètre : tour Jarvis, vitrine, acquisition, données, préparation FDM/résine, Jev, contenus et trajectoire vers l’atelier physique. Ce rapport complète le [registre des exigences](PROJECT_REQUIREMENTS.md), le [réaudit V9](RE_AUDIT_V9.md) et l’[audit acquisition V10](AUDIT_ACQUISITION_V10.md).

## Conclusion

Le concept est cohérent : un même dossier peut relier une demande, sa conception, sa fabrication et ses contenus, avec une interface centrale et deux écrans de contexte. Les principales défaillances reproduites dans cette revue portent sur la conservation des données, les reprises après interruption et certaines actions concurrentes. Ces défauts sont plus urgents que l’ajout de fonctions visuelles supplémentaires, car le système doit d’abord conserver exactement le travail qu’il annonce avoir enregistré.

La préparation numérique est déjà substantielle. L’atelier autonome demeure une capacité à réaliser et à qualifier : ni le slicing physique, ni les imprimantes, ni la voix locale ne sont actuellement attestés comme raccordés. Cette distinction est largement présente dans les sources V9/V10 ; il faut la maintenir dans chaque évolution.

Deux améliorations opérationnelles découlent directement de l’audit : rendre explicites les caractéristiques interprétées à l’import STL et montrer ce qui change entre deux demandes client, sans écraser le travail réalisé. Elles raccourcissent les décisions de l’opérateur avec des données qu’il peut examiner.

## 1. Nature et limites de la revue

Sources restaurées pour l’audit :

| Application | Révision de départ | Périmètre principal |
| --- | --- | --- |
| Atelier | `31ca88e9e0c40a945b6c77193989dad1f3614282` | `dist/`, `local/`, `docs/` et suites ciblées `qa/` |
| Vitrine | `11ced14511012cace74fb6df90b81bd7e80798e9` | Formulaire, réception, administration, schéma et documentation |

La revue combine lecture des sources, scénarios contradictoires, exécution des réducteurs et du stockage SQLite sur bases isolées, et interactions DOM. Elle ne constitue ni un test d’intrusion complet du service hébergé, ni une certification juridique, ni une qualification d’imprimante. Aucun compte client réel, paiement, envoi social ou mouvement machine n’a servi de fixture.

Les conclusions emploient quatre catégories :

- **Défaut vérifié** : un comportement incorrect a été identifié dans le code et, lorsque précisé, reproduit par un scénario.
- **Incohérence documentaire** : l’explication d’une capacité diverge du comportement actuel.
- **Risque conditionnel** : problème susceptible d’apparaître lors d’un raccordement ou d’un changement d’exploitation ; aucun incident physique n’est affirmé.
- **Capacité absente** : partie de l’objectif qui n’est pas encore exécutée par le système.

Les priorités désignent l’ordre de traitement. Elles ne sont pas des scores de sécurité normalisés.

## 2. Défauts vérifiés et corrections

| Priorité | Constat | Conséquence | Correction / preuve de cette révision |
| --- | --- | --- | --- |
| P0 | Le navigateur pouvait ignorer un événement de journal illisible ou remplacer une origine invalide/absente. | Reprendre une vue incomplète du travail sans rendre la perte visible. | Conservation des données brutes, état prudent, mutations et fusion suspendues, récupération exportable et réexamen explicite. Scénarios dans `qa/check-v11-integrity.mjs`. |
| P0 | Le coffre travaillait sur un tampon partagé pendant une écriture asynchrone. | Une mutation après l’appel pouvait produire un reçu accepté puis un échec d’intégrité à la première relecture. | Capture des octets et du manifeste avant l’attente asynchrone, côté dépôt et client. Même suite d’intégrité. |
| P1 | Un réessai du coffre sans date d’origine pouvait reconstruire une nouvelle date côté client. | Après une réponse perdue, la nouvelle tentative du même fichier pouvait différer de celle déjà conservée. | Date attribuée et restituée par le serveur quand elle n’est pas fournie ; reprise vérifiée après conservation puis nouvelle instance cliente. |
| P1 | Certaines réponses d’erreur après un dépôt incertain perdaient l’identifiant de la demande. | Une nouvelle tentative pouvait ne plus représenter le dépôt d’origine. | Révision des transitions du formulaire : distinguer rejet connu, résultat inconnu et demande supprimée. Les sept groupes React contradictoires passent. |
| P1 | Des demandes déjà refusées consommaient encore les limites globales. | Un client bruyant pouvait épuiser une capacité de réception utile aux autres visiteurs. Reproduction : 305 essais, 6 admis, quota global porté à 300. | Admission et compteurs conditionnés ensemble. Test concurrent : 50 essais d’un même client, 6 admis ; les essais refusés ne doivent plus polluer les autres compteurs. |
| P3 | Un changement d’horloge pouvait faire reculer la date de modification administrative. | Une correction plus récente pouvait paraître antérieure à la version conservée. | Date de modification protégée contre le recul, avec test de révision. |
| P1 | Deux clics très proches pouvaient préparer deux identités de demande ; une panne de jeton avant tout dépôt pouvait figer le brief. | Duplication potentielle ou blocage injustifié de la saisie. | Verrou et états de tentative explicités dans le formulaire ; cas couverts par les essais React ciblés. |
| P2 | Le parcours administratif permettait une sélection B suivie d’un enregistrement immédiat sur A. | Risque de modifier la mauvaise demande. | Verrous immédiats de lecture/écriture et générations de réponse ; le scénario de sélection B puis enregistrement de A est vérifié après correction. |
| P2 | Une tentative incertaine expirée après 24 heures disparaissait sans laisser de repère. | Repartir avec une autre identité alors qu’un premier dépôt peut exister. | Avis minimal dans la session de l’onglet, sans coordonnées ni description ; nouvelle saisie seulement après choix explicite. Les cas supprimé, illisible et expiré sont distingués. |
| P1 | L’import STL général attribuait silencieusement `mm` et `resin`. | Première inspection fondée sur une unité ou un procédé non choisis, notamment pour un socle ou un prototype FDM. | Choix explicite de l’unité et du procédé avant analyse/enregistrement. Neuf groupes d’intégration passent avec le parseur STL réel, dont lot mixte, interruption, révision concurrente et reprise partielle. |
| P2 | Un export client différent affichait un conflit sans détailler ses paramètres. | L’opérateur ne pouvait pas distinguer une variation technique d’un autre changement dans la demande source. | Comparateur en lecture seule livré ; huit paramètres, différences, ordre des révisions et accès au dossier conservé. Ne change pas le refus d’import. |
| P2 | `JARVIS.md` décrivait encore l’ancienne orchestration et Jev comme non identifié. | Attente d’une répartition, d’un calcul ou d’un scénario que l’action centrale ne réalise plus. | Description alignée sur la relecture des fichiers, l’ouverture de mission, le bureau de conseils Jev et la vitrine existante. |

La disparition complète d’un événement navigateur non confirmé, avant redémarrage et sans reçu extérieur, ne peut pas être démontrée uniquement à partir de ce qui reste sur le poste. La récupération brute permet de conserver les éléments présents ; elle ne promet pas de reconstruire des octets disparus. De même, une empreinte vérifie la cohérence d’un contenu et ne certifie pas son émetteur.

## 3. Ouverture de la vitrine : incohérence d’exploitation à traiter

Le contrôle de configuration de cette revue trouve la vitrine accessible publiquement, alors que les sources de départ annoncent une première publication privée et que les mentions/notice comportent encore des informations « à renseigner ». La réception distante existe ; sa disponibilité technique ne suffit donc pas à prouver que l’ouverture commerciale est préparée.

Le point prioritaire est de rendre cohérents l’état présenté au visiteur, le dépôt autorisé côté serveur et les informations effectives sur BOJ.ART. L’identité de M-Tek, d’UNUM ou du compte administrateur ne doit pas servir de remplacement automatique. Le suivi de publication doit préciser le comportement effectif du formulaire après correctif, sans supposer qu’un changement d’audience a été demandé.

La révision publiée préserve l’accès public et le formulaire de réception existant. La notice indique maintenant explicitement les informations encore manquantes et décrit la copie temporaire dans la session de l’onglet ainsi que son avis de reprise. Le README reflète l’audience constatée. Aucune identité juridique, adresse ou condition commerciale n’a été inventée pour compléter ces champs.

Les informations de l’éditeur et de l’hébergeur doivent être adaptées au site et à l’activité ; voir [Ministère de l’Économie — mentions d’un site professionnel](https://www.economie.gouv.fr/entreprises/developper-son-entreprise/innover-et-numeriser-son-entreprise/mentions-sur-votre-site-internet-les-obligations-respecter), publié le 11 décembre 2025 et consulté le 19 octobre 2026. La [CNIL — exemples de formulaires](https://www.cnil.fr/fr/exemples-de-formulaire-de-collecte-de-donnees-caractere-personnel), consultée le même jour, rappelle que les mentions doivent préciser le responsable, la finalité, les destinataires, la conservation et l’exercice des droits, selon le traitement concerné. Ses exemples doivent être adaptés.

Cette revue ne conclut pas à une conformité globale. Elle identifie les données et les décisions d’exploitation qui manquent réellement à ce dossier.

## 4. Ce qu’il faut conserver dans l’architecture

Les versions existantes ont déjà résolu plusieurs erreurs de conception courantes :

- Les fiches du parc déclaré restent distinctes des machines de démonstration.
- Les mesures viennent des octets du STL relu et de l’unité interprétée ; une hauteur souhaitée ne redimensionne pas le modèle.
- Un volume brut compatible ne valide pas les supports, les couches ou la résistance.
- Les conseils et les affichages Jev ont des cibles, des versions et des conditions de fraîcheur.
- Le reçu du journal décrit une opération de données ; il n’est pas un reçu d’imprimante.
- Le journal et les octets STL sont conservés et exportés séparément, avec les limites de snapshot documentées.
- La boîte de demandes détient les coordonnées ; Jarvis reçoit une projection technique et une référence, sans recopier automatiquement le texte libre.
- Les coûts humains, les matières, les autres coûts, la marge et la commission existent déjà dans le chiffrage. La ventilation et les données observées restent à compléter.
- Les plans de montage sont versionnés ; la présence d’un plan ne signifie pas qu’une vidéo correspondante a été rendue.

Ces mécanismes doivent devenir les contrats des futurs connecteurs. Les remplacer par un agent qui annonce seul la réussite ferait perdre des garanties déjà présentes dans le projet.

## 5. Fabrication mixte : points encore absents

### Dossier, version de pièce, lot et travail machine

Une révision de STL décrit une géométrie. Une commande peut demander plusieurs exemplaires de cette même révision. Un lot peut être réparti sur plusieurs plateaux ; une reprise peut concerner seulement une pièce. Ces identités doivent être distinctes avant le premier envoi physique. Les travaux actuels représentent une simulation historique et ne doivent pas devenir des ordres matériels par simple changement de connecteur.

Pour chaque travail futur, conserver au minimum la pièce/révision source, les transformations appliquées, le fichier machine exact, ses profils, sa matière, sa machine cible et son résultat observé. L’état inconnu après une interruption doit rester un état à rapprocher.

### Deux chaînes de préparation

[PrusaSlicer](https://github.com/prusa3d/PrusaSlicer) documente FDM et mSLA, ainsi qu’une interface en ligne de commande. [UVtools](https://github.com/sn4k3/UVtools) documente l’analyse des couches résine, des îlots et de pièges à résine, ainsi que la conversion de nombreux formats. Sa documentation indique aussi que certaines propriétés sont ignorées lorsqu’un format cible ne les supporte pas. Sources consultées le 19 octobre 2026.

La conclusion d’intégration est donc conditionnelle : choisir le moteur et le format à partir du modèle exact de machine et de son firmware, puis qualifier la sortie. Un slicer disponible ou un fichier converti ne suffit pas à prouver une chaîne universelle pour toutes les résines.

Le choix FDM/résine doit porter sur chaque pièce et sur son résultat attendu : détail, usage, assemblage, masse et finition. La préférence initiale « socles/petites pièces en FDM, grandes figurines en résine » reste une hypothèse à comparer, pas une règle déduite de la seule taille. L’époxy de coulée ou d’assemblage serait une opération distincte de la résine UV d’impression.

### Reprise après perte de réponse

La documentation [Moonraker — commandes et état](https://moonraker.readthedocs.io/en/latest/external_api/printer/) distingue le démarrage, la consultation et les mises à jour d’état. L’[historique](https://moonraker.readthedocs.io/en/latest/external_api/history/) conserve une identité de travail et des états comprenant interruption et déconnexion. Sources consultées le 19 octobre 2026.

Recommandation de conception issue de ces interfaces : lorsqu’un démarrage perd sa réponse, relire l’état et l’historique de la cible avant d’envisager un renvoi. Une machine momentanément inaccessible n’établit ni l’échec du démarrage, ni l’arrêt physique du travail. Les essais devront reproduire cette ambiguïté sur chaque protocole qualifié.

### La capacité après l’imprimante

L’ordonnancement doit également représenter retrait, préparation de surface, lavage et polymérisation selon procédé, séchage, assemblage, peinture, contrôle, emballage et remise. Les temps humains et les ressources de finition conditionnent les délais et le coût du lot. Une occupation de huit plateaux ne constitue pas une capacité commerciale de huit commandes terminées en parallèle.

## 6. Jev, voix et trois écrans

[TypeSafe](https://docs.typesafe.ai/introduction) décrit Jev comme un modèle qui répond à des questions typées. La [page des modèles](https://docs.typesafe.ai/models), consultée le 19 octobre 2026, précise des entrées textuelles et recommande une évaluation sur la langue d’usage. Elle distingue une version publiée le 14 octobre de l’alias stable ; le projet a raison de conserver une version identifiée et de demander une évaluation avant changement.

La bibliothèque communautaire [jev-ui](https://github.com/etweisberg/jev-ui) choisit parmi des composants préexistants avec des règles de repli ; les actions restent détenues par l’application. Elle convient comme référence pour « afficher le bon contexte », mais n’apporte pas un moteur qui génère une scène, un STL ou un rendu. Un candidat référencé n’est pas automatiquement installé ou raccordé.

L’IA locale de la tour conserve un chantier distinct : reconnaissance de la parole, interprétation française, gestion du bruit et des ambiguïtés, retour vocal, allocation des ressources pendant le slicing/rendu. Le prix annoncé de la tour ne permet pas d’en déduire ses performances. La nomenclature CPU/GPU/VRAM/RAM et les mesures sur les tâches retenues restent nécessaires.

Les trois écrans partagent déjà un rôle et un contexte contrôlés. L’affichage doit conserver une place stable aux erreurs, aux résultats inconnus et aux actions importantes. Une recommandation Jev peut mettre une vue en avant ; elle ne doit pas être l’unique voie pour retrouver une information ou une commande. La revue graphique à la résolution réelle, à la distance d’usage et sous charge GPU demeure à réaliser.

## 7. Identité, médias et acquisition

BOJ.ART dispose d’originaux, de films de référence et d’une direction cohérente : emblème, contrastes, typographie, geste, détail et œuvre entière. L’archive documente néanmoins une couverture datée et une vidéo manquante ; elle ne doit pas être annoncée comme intégrale ou à jour sans nouvel inventaire. L’analyse du langage de montage de toutes les vidéos reste une tâche différente de leur simple récupération.

Les deux dépôts proposés au début du projet ont des rôles distincts, vérifiés le 19 octobre 2026 :

| Référence | Capacité documentée | Conséquence pour BOJ.ART |
| --- | --- | --- |
| [iart-ai/tiktok-video-skills](https://github.com/iart-ai/tiktok-video-skills) | Guides de formats courts, sous-titres et habillages animés. | Candidat pour formaliser les recettes d’édition ; ne constitue pas une archive ou un lecteur de toutes les vidéos. |
| [FlowExtractAPI/tiktok-video-downloader](https://github.com/FlowExtractAPI/tiktok-video-downloader) | Dépôt consulté composé d’un README et d’une image, décrivant un Actor Apify. | Piste de service externe ; le dépôt ne fournit pas un moteur local autonome prêt à intégrer. |

La trajectoire utile est une chaîne de contenu vérifiable : sources retenues, usage autorisé, plan versionné, rendu exact, revue visuelle/sonore, publication et lien vers l’offre. Les statistiques doivent suivre les demandes réellement reçues, les devis, les commandes et le coût observé. Le nombre de vues sociales et le nombre de demandes ne suffisent pas à calculer une rentabilité.

## 8. Innovation livrée : rapprochement de deux demandes

Le nouvel aperçu d’import compare la projection technique d’origine et celle du fichier reçu. Il affiche les huit paramètres séparément : offre, quantité, largeur, hauteur, profondeur, budget souhaité, date souhaitée et point de départ du modèle. Les valeurs inconnues restent explicites. Les changements donnent des questions de revue sur le lot, l’échelle, la conception, le calendrier ou le chiffrage.

Le comparateur emploie les paramètres importés à l’origine, même si l’opérateur a déjà modifié quantité, notes ou calcul dans son dossier courant. Il signale un export plus ancien ou un contenu différent portant le même numéro de révision. Une identité divergente, une correspondance ambiguë ou une projection invalide refuse la comparaison.

Si les paramètres sont identiques, le message indique seulement que le contenu ou le suivi de la demande source a changé. L’ancien contact et le texte libre n’étant pas copiés dans le journal atelier, le système ne prétend pas reconnaître le champ privé modifié. Une nouvelle contrainte écrite peut exiger une revue même lorsque les huit champs structurés sont identiques.

Le bouton « Ouvrir le dossier conservé » garde une cible explicite. Le comparateur ne fusionne rien, ne modifie pas le refus d’import et ne traite pas un statut commercial comme un accord. C’est une amélioration du traitement des changements, avant le futur mécanisme d’avenant ou de nouvelle proposition commerciale.

## 9. Priorités concrètes après V11

1. **Finir la mise en exploitation de l’acquisition.** Cohérence entre information publique, réception autorisée, coordonnées de l’activité, revue administrative et conservation. Tester une vraie demande de bout en bout avec une session autorisée, sans la confondre avec une fixture.
2. **Relier la proposition à son accord.** Séparer estimation, devis émis, version acceptée, commande et paiement. Une évolution du dossier produit une nouvelle proposition explicite ; elle ne réécrit pas le document déjà accepté.
3. **Qualifier une FDM et une résine.** Même dossier pilote, fichiers mesurés, profils identifiés, sortie slicer, aperçu exact, envoi, interruption contrôlée, pièce finie et résultat de contrôle. Le parc entier suivra ces recettes vérifiées.
4. **Mesurer une réalisation mixte complète.** Comparer matières et heures prévues/observées, réserver la finition et documenter assemblage, emballage et remise. Les futures offres et le planning reposent ensuite sur ces observations.
5. **Relier une réalisation à son contenu.** Produire un montage exact depuis un plan versionné, le revoir, puis mesurer les demandes attribuées à sa page d’arrivée. Le rythme et les traitements visuels évolueront à partir des réalisations BOJ.ART effectivement disponibles.

Les programmes de robotique devront avoir leurs propres exigences, nomenclatures, essais et limites fonctionnelles. Un portfolio de figurines et une imprimante disponible ne valident pas, à eux seuls, une offre de robot utilisable.

## 10. Vérifications et clôture de la révision

Le comparateur V11 est vérifié par :

```sh
node --experimental-vm-modules qa/check-inquiry-revisions.cjs
```

**Neuf groupes passés** dans `qa/inquiry-revisions-results.json` : huit champs, valeurs inconnues, absence de calcul de prix, changements source seuls, ordre des révisions, identités, rendu DOM sémantique, distinction origine/travail courant, ouverture du bon dossier, conservation des données, CSS et réduction du mouvement. La suite utilise l’application et le store réels dans JSDOM avec des exports synthétiques dont l’intégrité est vérifiée.

Le [rapport ciblé d’intégrité](audit-v11-integrity.md) décrit les trois défauts de journal/coffre, leurs reproductions et leurs limites. `qa/check-v11-integrity.mjs` comporte 16 groupes passés ; les huit groupes du coffre ont aussi été réexécutés après sa dernière correction. La récupération dans l’application complète comporte six groupes passés : ouverture corrompue sans remplacement, copie brute, réexamens successifs, réparation puis reprise, brouillon conservé et commandes bloquées. Les vingt groupes de continuité et les dix-sept groupes trois écrans passent sur la version corrigée.

La vitrine conserve les preuves avant/après dans son propre dépôt : `docs/audit-v11-acquisition.md`, `qa/acquisition-results.json` et `qa/acquisition-ui-v11-results.json`. Vingt groupes backend, sept groupes contradictoires React et douze groupes de régression vitrine passent. TypeScript et la compilation officielle sont terminés sans erreur. La version vitrine n° 3, commit `87306314a847c6d2f109bf5833345b3b80af22e1`, a été publiée avec succès le 19 octobre 2026 ; son audience publique a été préservée.

Le navigateur graphique, le WebGL, la connexion SIWC interactive et les transactions de la base D1 hébergée n’ont pas fait l’objet d’une recette de bout en bout dans cette revue. Aucun compte social, appel Jev réel, envoi client, paiement ou imprimante n’a été raccordé par ces corrections. La publication de la tour ne déploie pas le service Node sur le PC : le code V11 du dossier `local/` doit aussi y être installé pour bénéficier des corrections du coffre.

La recette de l’import général est conservée dans `qa/check-v11-stl-import.cjs` et `qa/v11-stl-import-results.json` : neuf groupes passent avec le parseur STL réel, le store et l’application complète. Elle couvre choix vides, lot mm/FDM et pouces/résine, changement de projet actif sans changement de destination, double soumission, fermeture pendant lecture, révision concurrente, reprise d’un seul fichier après échec et préservation de trois types de brouillons. Si une fermeture intervient après le début d’une écriture de fichier, des octets peuvent rester conservés sans association ; aucune pièce tardive n’est ajoutée au dossier. Cette limite est testée et ne constitue pas une annulation de transfert garantie.

Les corrections d’import, de sélection administrative et d’admission sont donc vérifiées au niveau applicatif dans les conditions décrites. L’inventaire réel des machines, les spécifications de la tour, les profils matière/slicer et les informations commerciales propres à BOJ.ART restent les prochaines entrées indispensables. La prochaine recette opérationnelle doit prouver une chaîne complète sur le matériel et les comptes de l’atelier.
