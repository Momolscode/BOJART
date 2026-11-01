# BOJ.ART — réaudit global et améliorations V9

19 octobre 2026. Périmètre : demandes présentes dans le fil depuis le projet initial, documents du dépôt, application existante, services locaux et vérifications de cette version. Le [registre des 30 exigences](PROJECT_REQUIREMENTS.md) permet de retrouver chaque ambition et son état. Aucune caractéristique matérielle absente du dossier n’est inventée.

## Conclusion du réaudit

Le projet est cohérent comme tour de contrôle d’un atelier de fabrication et de création. Son unité doit être le dossier : brief, fichiers, préparation, fabrication, finition, contenus et commande client. Jarvis devient l’interface de ce dossier ; les moteurs spécialisés fournissent les résultats observables de chaque étape.

Le progrès décisif de cette version porte sur la confiance dans l’état affiché. La mission, la décision centrale et les conseils de préparation partagent désormais des preuves de lecture des fichiers. Le journal conserve les décisions métier confirmées ; le coffre conserve les originaux. L’interface donne la priorité à l’action utile et à sa justification.

L’application reste un poste de préparation et une base de coordination. Le Site publié est statique ; le service de la tour est du code fourni, testé localement, à installer sur le PC dédié. Aucun appel réel TypeSafe, rendu navigateur, microphone, slicer, transfert imprimante, paiement ou publication sociale n’a été validé pendant ce réaudit. Une boîte qui tient dans un volume ne devient pas une recette d’impression qualifiée.

## 1. Changements effectivement apportés

| Constat | Correction V9 | Conséquence pour l’opérateur |
|---|---|---|
| La mission pouvait s’appuyer sur des références de fichier et des dimensions déclarées. | Lecture du binaire, mesure, unité, identité de pièce, révision et SHA associés à la preuve ; compteurs reconstruits. | Un fichier absent ou périmé apparaît comme tel ; les dimensions de démonstration ne valident plus la préparation réelle. |
| Le centre privilégiait la scène décorative. | Prochaine décision, raison, cible, preuves et action directement visibles ; noyau animé compact ; huit domaines repliables. | Le centre explique ce qui mérite une intervention sans supprimer la signature visuelle. |
| « Orchestrer » mélangeait examen de mission et actions de simulation. | Relecture des preuves et ouverture de la mission de quinze étapes ; les simulations restent des commandes explicites. | Examiner le dossier ne génère pas implicitement des affectations, un devis ou un scénario. |
| Jev était surtout associé au choix d’une vue. | Bureau de décisions avec priorités, orientations et intention éditoriale, relié aux vrais constructeurs de contexte. | Un conseil ouvre l’élément concerné ; son dossier et sa version sont contrôlés jusqu’à l’ouverture. |
| Une opération arrivée tard pouvait changer le résultat reconstruit d’un conflit. | Séquence serveur, versions de ressource et reçus conservés dans la transaction SQLite. | Une modification confirmée conserve son résultat après arrivée concurrente, répétition ou reprise. |
| Les fichiers STL restaient dépendants du navigateur. | Coffre local immuable, empreintes vérifiées et archive portable `.bojassets`. | Les originaux et les fichiers remplacés peuvent être conservés et restaurés avec leurs associations. |

Les questions descriptives telles que « Pourquoi ? » ou « Où en est le dossier ? » suivent désormais un parcours de réponse sans mutation métier. Leur texte peut rejoindre le journal ; elles ne deviennent pas une action de fabrication.

## 2. Les trois écrans

**Gauche — Atelier.** Vue du parc, des travaux simulés et du référentiel des machines. Les fiches déclarées définissent la technologie et le volume utilisés par la préparation. Les machines physiques et leurs états restent à raccorder.

**Centre — Jarvis.** Projet actif, prochaine décision, preuves, commande et dernier retour. La mission relie quinze étapes. Le bureau Jev et la régie s’ouvrent depuis cette station. Les huit domaines conservent la vue d’ensemble : création, préparation, production, contenus, commerce, ressources, système et robotique.

**Droite — Création.** Modèle associé, œuvre de référence, film et éléments visuels envoyés depuis le centre. L’établi compare six rotations orthogonales du STL aux volumes déclarés. L’envoi d’une vue attend un retour de la fenêtre destinataire ; une fenêtre détectée ne prouve pas la présence d’un moniteur physique.

Le noir, l’ivoire, le carmin, les polices existantes et l’emblème d’origine sont conservés. Les couleurs propres aux œuvres restent dans les références. Le mouvement accompagne la lecture et les sélections ; le mode réduit reste accessible. La qualification finale doit porter sur les résolutions, la distance de lecture et la charge réelle des trois écrans de la tour.

## 3. Rôle précis de Jev

Le [contrat de décision](JEV_DECISIONS.md) fixe les entrées, les candidats, les sorties et leur durée de validité. Les règles du logiciel déterminent les options possibles. Jev compare ces options ; le navigateur retrouve ensuite la cible dans le catalogue actuel.

| Domaine livré | Ce que Jev peut comparer | Ouverture disponible |
|---|---|---|
| Priorités | Fichiers du dossier, fiches machines et dernières versions de plans d’édit | Bonne pièce, fiche ou intention enregistrée |
| Préparation | Rotations dont la boîte brute mesurée tient dans un volume déclaré | Pièce, machine et orientation correspondantes dans l’établi |
| Éditorial | Cinq séries : œuvre, geste, sur mesure, prototype et disponibilité | Nouveau brouillon d’intention, sans remplacer une version enregistrée |
| Régie visuelle existante | Modèle, œuvres, film ou parc | Présentation sur une station avec retour d’affichage |

Une réponse périmée, un dossier changé ou une option injectée sont refusés. Les règles locales et l’examen manuel restent disponibles sans fournisseur. Le conseil n’accorde aucune capacité d’impression ou de publication.

L’API intégrée est celle de TypeSafe. Les [skills officiels](https://github.com/typesafe-ai/skills) sont des recettes d’intégration ; ils ne fournissent pas les poids d’un modèle Jev installé sur le PC. La [documentation des modèles](https://docs.typesafe.ai/models), relue le 19 octobre 2026, présente Jev 1.14 comme version la plus récente et conserve un alias stable 1.13. La version configurée reste explicitement fixée ; une évolution doit passer les scénarios BOJ.ART, en particulier en français, avant adoption. Les tests de cette livraison utilisent des réponses contrôlées, sans mesurer la qualité réelle du fournisseur.

## 4. Fabrication : architecture retenue et travail restant

L’intention initiale — socles et petites pièces en FDM, figurines importantes en résine — est conservée comme préférence de départ. Elle doit être confrontée au détail attendu, à l’effort mécanique, au poids, aux assemblages, à la finition et aux procédés disponibles. Une pièce de grande taille ne suffit pas à déterminer son matériau.

Pour une création d’un mètre, la chaîne cible reste : brief dimensionnel ; géométrie source ; découpe artistique et mécanique ; connecteurs et jeux ; préparation selon procédé ; supports et placement ; slicing ; lecture de la sortie ; transfert ; suivi ; opérations de finition ; assemblage et contrôle. La V9 apporte la lecture fiable des fichiers et leur comparaison dimensionnelle. Elle ne génère pas automatiquement une sculpture manufacturable ni sa découpe complète.

Le premier jalon matériel doit être **une FDM et une résine qualifiées**, avec leur configuration exacte. Pour chacune : une recette, une version de profil, une sortie machine identifiable, un aperçu provenant de cette sortie, un transfert vérifié et une pièce réelle contrôlée. L’identité des futurs plateaux et travaux physiques doit être séparée de la révision de géométrie ; les travaux actuels représentent encore la simulation.

Le cas critique de la future commande est une réception perdue. Si la machine a peut-être reçu le travail, l’état devient « résultat inconnu » jusqu’à rapprochement. Il ne faut pas transformer l’absence de réponse en nouveau départ automatique. Le journal V2 fournit une base de conservation, mais les reçus du logiciel ne remplacent pas ceux de l’équipement.

L’ordonnancement devra intégrer lavage, séchage, polymérisation selon recette, retrait des supports, assemblage, peinture et contrôle. Le temps humain et les postes de finition peuvent devenir les contraintes réelles de l’atelier. Le budget évoqué du PC ne permet pas de déduire son GPU, sa mémoire ou les modèles locaux qu’il exécutera.

## 5. Signature, contenus et activité commerciale

Le fonds documenté compte 31 publications, dont 30 vidéos ; 29 binaires vidéo ont été récupérés. Une vidéo manque. Ce relevé antérieur est conservé comme inventaire, pas comme preuve d’une analyse exhaustive de tous les contenus réalisée pendant ce réaudit. Les sources sont décrites dans [VIDEO_SKILLS.md](VIDEO_SKILLS.md).

La signature retenue relie geste, détail, présentation de l’œuvre et emblème. Le film Baki existant reste une référence réalisée à partir des sources documentées. Les plans d’édit du dossier sont versionnés ; ils ne sont pas encore des rendus conformes à toutes les coupes et sources choisies.

Le jalon vidéo utile est un moteur qui produit une prévisualisation et un export à partir de la même version du plan. Il doit conserver les originaux, les repères temporels, le cadrage, le son et la provenance. La priorité de captation est une collection courte de plans réellement utilisables : ensemble, détail, geste, échelle et son d’atelier. Les règles proposées figurent dans [IDENTITE_VISUELLE.md](IDENTITE_VISUELLE.md).

Le développement commercial doit relier un contenu à une demande puis à un dossier chiffré. Trois familles d’offres sont retenues : œuvres et éditions, créations sur mesure, prototypes sur cahier des charges. Les devis locaux existent ; stock, paiement, attribution d’acquisition et gestion commerciale complète restent à raccorder. La vitrine publique devra présenter les œuvres et disponibilités autorisées, tandis que la tour conserve les données d’administration.

## 6. Skills et moteurs : sélection utile

Un skill apporte des méthodes et des conventions ; il doit être relié à un moteur pour produire un fichier ou une action vérifiable. Les candidats retenus ne sont pas déclarés installés sur la tour.

| Besoin | Candidat | Limite de la sélection |
|---|---|---|
| Décisions Jev | [TypeSafe skills](https://github.com/typesafe-ai/skills) | Fournisseur hébergé et qualité en français à évaluer |
| Compositions vidéo reproductibles | [Remotion skills](https://github.com/remotion-dev/skills) | Relier les plans du dossier au moteur de rendu ; vérifier les conditions applicables au moteur |
| Recettes de format court | [iart-ai/tiktok-video-skills](https://github.com/iart-ai/tiktok-video-skills) | Méthodes de contenu et d’animation ; ce dépôt ne remplace pas la lecture des vidéos BOJ.ART |
| Collecte complémentaire TikTok | [FlowExtractAPI](https://github.com/FlowExtractAPI/tiktok-video-downloader) | Dépendance au service à examiner pour la vidéo manquante ou de nouvelles publications |
| Slicing FDM | [OrcaSlicer CLI](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_mode) | Profils, version binaire et matériel exacts à qualifier ; transport séparé |
| Analyse de fichiers résine | [UVtools](https://github.com/sn4k3/UVtools) | Formats et fonctions compatibles à vérifier selon imprimante |
| Voix et compréhension locales | Ollama, whisper.cpp, Piper | Candidats documentés dans le registre ; configuration PC et essais français requis |

Les références détaillées, alternatives conditionnelles et jalons sont conservés dans le registre des exigences. Ajouter tous les outils d’un catalogue n’est pas un critère de réussite. Le critère utile est un parcours complet, reproductible et compatible avec le matériel choisi.

## 7. Conservation et vérification

La continuité possède deux exports : journal JSON et archive STL `.bojassets`. Le navigateur peut produire l’archive portable ; le coffre de la tour fournit la restauration vérifiée. Les fichiers remplacés encore référencés par l’historique sont inclus. Les deux exports ne constituent pas un snapshot atomique unique ; suspendre les modifications pendant leur prise et les conserver ensemble. Le transfert vers une origine locale est décrit dans [WORKSHOP.md](../local/WORKSHOP.md).

Les cas couverts comprennent lecture de vrais STL binaires et ASCII, unités, matrices Three, modèle manquant, import concurrent, changement de dossier pendant lecture, invalidation du conseil, ouverture de la cible, SQLite, migration, reçu perdu, conflit stable, connexion simultanée, clone divergent, coffre corrompu et archive restaurée octet pour octet.

| Vérification ciblée V9 | Groupes passés |
|---|---:|
| Preuves de projet | 20 |
| Contrats des décisions | 22 |
| Poste central | 8 |
| Bureau des décisions | 13 |
| Autorité du journal | 11 |
| Coffre STL | 8 |
| Raccordement de la passerelle V9 | 4 |

Les suites d’intégration de l’interface, de la préparation, du studio, des trois fenêtres, du backend et de la continuité passent également. Les rapports sont dans `qa/`. Ils utilisent le vrai code métier, des fichiers et bases temporaires, JSDOM et des transports contrôlés. Le navigateur graphique, le rendu WebGL matériel, la tour physique et le fournisseur Jev réel n’ont pas été exercés. La capacité de prévisualisation requise par le workflow Sites était indisponible ; aucune capture de rendu n’est revendiquée.

## Prochaine progression du projet

1. Installer le service sur la tour dédiée et restaurer un dossier avec ses originaux ; vérifier les trois postes à leur résolution réelle.
2. Qualifier une FDM et une résine sur une chaîne fichier → slicing → aperçu → transfert → pièce contrôlée, puis étendre au parc.
3. Réaliser un projet mixte avec assemblage, finition et captation ; mesurer les reprises et le temps humain.
4. Produire un rendu vidéo conforme au plan enregistré et lancer une offre dont coûts, délais et résultat sont suivis.

Les mesures à recueillir sont le temps pour identifier un blocage, les pièces conformes terminées par heure humaine, le taux et les causes des reprises, les écarts de coût et de délai et les demandes qualifiées issues du contenu. Aucun score de maturité ou résultat commercial n’est déduit des données de démonstration.
