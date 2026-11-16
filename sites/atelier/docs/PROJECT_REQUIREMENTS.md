# BOJ.ART — registre du projet depuis la demande initiale

Révision du 19 octobre 2026, travaux V9 et extension acquisition V10. Ce registre rassemble les exigences exprimées dans la conversation et les décisions de conception qui en découlent. Il décrit des capacités vérifiables ; il ne donne pas de pourcentage de maturité. Le [réaudit acquisition V10](AUDIT_ACQUISITION_V10.md) complète le parcours commercial, ses données et ses critères de réussite.

## Objectif conservé

Créer pour BOJ.ART une tour de contrôle sur trois écrans, pilotée par Jarvis, qui relie création 3D, préparation, parc FDM et résine, opérations d’atelier, contenus, offres et demandes clients. Le projet concerne un atelier distinct d’UNUM et de M-Tek. Le PC dédié a été évoqué à 8 000 €, mais sa configuration n’est pas connue. Aucune caractéristique d’un autre ordinateur de l’utilisateur ne sert au dimensionnement de cette tour.

Jarvis doit réduire le nombre d’interventions nécessaires et rendre chaque ordre compréhensible. Une étape est terminée lorsque le résultat correspondant existe et peut être examiné : fichier mesuré, sortie du slicer, reçu machine, pièce contrôlée ou vidéo rendue. Un habillage visuel et une intention enregistrée ne constituent pas ces résultats.

## Sens des statuts

| Statut | Signification |
|---|---|
| Livré dans l’application | Fonction présente dans le code et accessible dans le parcours concerné. Sa publication relève de la validation globale de cette version. |
| Vérifié en test local | Cas reproduit avec code livré et fixtures ou transports contrôlés. Le périmètre du test reste explicitement indiqué. |
| Backend en qualification | Service écrit ; validation et raccordement applicatif encore en cours lors de ce relevé. |
| À raccorder | Interface, contrat ou intention présents ; moteur ou service externe non intégré en exploitation. |
| Futur à qualifier | Capacité exigeant conception, équipement, droits, exigences ou essais supplémentaires. |

Ces statuts ne signifient pas que l’atelier physique, ses imprimantes, ses comptes ou son PC sont déjà connectés.

## 1. Identité et expérience de la tour

| ID | Exigence issue des échanges | Réponse retenue | État et preuve |
|---|---|---|---|
| R01 | Écrire **BOJ.ART**, correction explicite de l’utilisateur. | Nom stable, emblème d’origine conservé ; aucune nouvelle ponctuation dans la marque. | Livré ; assets et interface. |
| R02 | Respecter les prises de vue, les œuvres et la signature initiale. | Références originales distinguées des projets nouveaux ; geste, détail, œuvre entière et signature servent de trame. | Direction documentée dans `IDENTITE_VISUELLE.md`. Analyse complète de toutes les vidéos encore à réaliser. |
| R03 | Une identité homogène, contemporaine et riche en motion design. | Fond noir, ivoire et carmin proposés, couleurs réelles des œuvres conservées ; mouvement associé à une sélection ou un résultat. | Interface et film de référence livrés. La charte reste une proposition à stabiliser avec l’artiste. |
| R04 | Trois écrans simultanés, lisibles une fois affichés. | Gauche : activité et attentes ; centre : décision et commande ; droite : contexte visuel. | Vues et communication entre fenêtres livrées. Trois moniteurs physiques, distance, résolution et charge GPU à qualifier. |
| R05 | Opérer très rapidement depuis le centre. | Décision active, cause, cible, actions principales et dernier reçu ; accès aux domaines secondaires conservé. | Refonte V9, vérification DOM/CSS dans `qa/check-control-workstation.cjs`. Aucun benchmark matériel de rapidité annoncé. |
| R06 | Plus de visuels, sans perdre le suivi du travail. | STL mesuré, six orientations, références, film et bureau de comparaison ; démonstration explicitement identifiée. | Fonctions présentes ; preview de couches réelles à raccorder au slicer. |
| R07 | « Jarvis au contrôle de tout ». | Un dossier relie les domaines et leurs dépendances ; les actions ont une cible et une version. Les questions descriptives précèdent le routage des actions. | Mission V2 et réponses descriptives vérifiées dans `qa/check-project-evidence.mjs`. Le moteur conversationnel local reste à raccorder. |

## 2. Création et fabrication

| ID | Exigence | Réponse retenue | État et preuve |
|---|---|---|---|
| R08 | Sept à huit imprimantes FDM et résine. | Registre pour identifier chaque machine, son procédé, volume, firmware, matière, profils et essai. Les emplacements de démonstration ne deviennent pas des machines réelles. | Registre livré et testé ; liste exacte du parc à renseigner et à qualifier. |
| R09 | Socles et petites pièces FDM, grandes figurines résine. | Préférence initiale conservée comme hypothèse de travail, à comparer aux exigences de détail, poids, résistance et finition. La taille seule ne décide pas du procédé. | Critères de conception ; sélection matière et fabrication physique à qualifier. |
| R10 | Demander une figurine d’un mètre. | Brief dimensionnel, géométrie source, découpes artistiques et mécaniques, assemblages et contrôle de stabilité. La hauteur du brief ne redimensionne pas un STL. | Dossier et inspection livrés. Génération, découpe, connecteurs et validation de sculpture à raccorder. |
| R11 | Répartir les STL aux bons endroits selon les caractéristiques des machines. | Comparer les mesures du binaire aux seules fiches déclarées, garder les unités, l’identité du fichier et la révision. | Mesure et enveloppes vérifiées ; supports, nesting, collisions, profils qualifiés et planning de plateaux restent à réaliser. |
| R12 | Slicer et voir avant d’imprimer. | Slicer identifié, profils conservés, sortie vérifiée, aperçu des couches du même fichier. | À raccorder. La coupe 3D actuelle et l’orientation d’une boîte brute ne sont pas des couches de fabrication. |
| R13 | Lancer une campagne automatiquement. | Lot, plateau et travail distincts de la révision de pièce ; connecteurs par technologie ; reçus stables et gestion du résultat inconnu. | Exécution physique future. La simulation est isolée du chemin nominal de fabrication dans la mission V2. |
| R14 | Tout ordonner sans interventions répétitives. | Automatiser les étapes réversibles et les recettes qualifiées dans des règles définies ; rendre les exceptions ciblées et expliquées. | Relecture coordonnée et conseils présents. Politique d’exécution physique à définir après qualification d’au moins une FDM et une résine. |
| R15 | Faire plus que des figurines : prototypes, objets et robotique. | Offres fondées sur des capacités réellement démontrées ; dossiers, exigences et essais par famille d’usage. | Dossiers et branche de mission présents. CAO, protocoles fonctionnels et actionneurs futurs à qualifier. |
| R16 | Prendre en compte tout le matériel de l’atelier. | Le planning inclut impression, retrait, lavage, séchage, polymérisation selon procédé, assemblage, peinture et contrôle. | Périmètre défini ; inventaire des postes, temps humains et capacité réelle à collecter. |

Le mot « résine » désigne ici la résine photopolymère UV des imprimantes concernées. Un procédé d’époxy de coulée ou d’assemblage serait une opération distincte, avec sa propre recette et ses équipements.

## 3. IA locale et Jev

| ID | Exigence | Réponse retenue | État et preuve |
|---|---|---|---|
| R17 | Communiquer les ordres en vocal depuis la tour. | Micro, transcription, compréhension, plan structuré, exécution et retour vocal séparés. Prioriser questions, affichage et préparation avant les ordres physiques. | À raccorder ; aucun microphone ou modèle de voix testé sur la tour cible. |
| R18 | IA locale et fonctionnement autonome. | Conserver service atelier, fichiers, règles et contrôles sur la tour. Mettre en file les tâches lourdes de 3D et vidéo ; garder la commande disponible. | Service local disponible ; modèle et dimensionnement matériel à choisir sur la configuration exacte. |
| R19 | Jev choisit les visuels d’un écran. | Catalogue de quatre vues, projet et révision capturés, réponse bornée, accusé de l’écran destinataire. | Code et tests livrés ; compte TypeSafe et appel réel sur la tour non attestés. Voir `JEV_LOCAL.md`. |
| R20 | Jev intervient dans toutes les actions pertinentes. | Trois domaines actifs de conseil : orientation brute, prochain élément à examiner et intention éditoriale. Contrats futurs pour slicing, planning, qualité, commercial, diffusion et robotique. | Contrats et transport vérifiés dans `qa/check-project-decisions.mjs`. Voir `JEV_DECISIONS.md` pour les entrées, sorties et limites. |
| R21 | Conserver un contrôle fluide si Jev est indisponible. | Options manuelles et règles locales identifiées comme telles ; aucun faux score d’IA. | Vérifié en test local, avec erreur réseau et absence de clé. |
| R22 | Distinguer service open source et modèle local. | Les skills Jev sont des recettes d’intégration. L’API Jev utilisée est hébergée chez TypeSafe ; elle reçoit ici des faits minimisés, pas les vidéos ou les binaires. | Architecture explicite ; aucun poids Jev local livré. Une substitution par un modèle local doit être évaluée sous le même contrat. |

Les résultats du modèle ne créent pas de capacité d’exécution. Chaque conseil est lié à son paquet de preuves, a une durée de validité et doit être contrôlé de nouveau lorsque son élément est ouvert. L’empreinte du paquet détecte un changement ; elle ne constitue pas une authentification ni une qualification matérielle.

## 4. Contenus, commercial et conservation

| ID | Exigence | Réponse retenue | État et preuve |
|---|---|---|---|
| R23 | Collecter toutes les vidéos pour respecter la signature de A à Z. | Archive avec identités, originaux, métadonnées, aperçus et indisponibilités explicites ; analyse distincte de la collecte. | Relevé documenté : 31 publications, 30 vidéos, 29 binaires vidéo récupérés. Une vidéo manque ; l’analyse audiovisuelle exhaustive reste à faire. Voir `VIDEO_SKILLS.md`. |
| R24 | Éditer les vidéos dans le style BOJ.ART. | Plans d’intention versionnés, sources, repères dans l’original, direction sonore et légende. Prévisualisation finale et rendu liés à la même version. | Studio d’intention et référence livrés. Le lecteur d’aperçu court ne relit pas toutes les coupes originales ; rendu exact à raccorder. |
| R25 | Acquisition client et réseaux sociaux. | Préparer rendus, textes, déclinaisons et suivi de provenance du contact ; conserver une demande identifiable et qualifiable. | V10 : entrée Demandes, import vérifié, qualification et lien à la source. Archives et texte présents ; comptes sociaux, diffusion et attribution commerciale complète à raccorder. |
| R26 | Site vitrine et œuvres directement vendables. | Façade distincte de l’administration privée : œuvres autorisées, offres compréhensibles et demande. La vente nécessite stock, conditions et paiement. | Vitrine V10 développée dans le dépôt `bojart-vitrine` ; publication et réception documentées dans sa livraison. Paiement et stock réel ne sont pas raccordés par l’import atelier. |
| R27 | Pièces et figurines sur mesure. | Demande, synthèse technique, proposition, versions validées, devis, réalisation et réception reliés au dossier. | V10 : demande exportée reliée au dossier sans duplication automatique des coordonnées. Dossiers et calcul de coût disponibles ; devis commercial versionné, accord et paiement à raccorder. |
| R28 | Transformer les capacités du matériel en offres. | Trois familles initiales : œuvres/éditions, création sur mesure, prototypes selon exigences. Définir exclusions, mesures et livrables pour chaque offre. | Conception documentée ; aucune offre universelle ou marge réelle déduite des démonstrations. |
| R29 | Ne plus perdre le travail lors d’un blocage ou d’une reprise. | Identités stables, journal, sauvegardes et conservation des fichiers. Les rapports et les binaires ont des périmètres explicites. | Journal V2 et coffre STL vérifiés localement : 11 groupes pour l’autorité et 8 pour les fichiers dans `qa/check-workshop-authority.mjs` et `qa/check-workshop-assets.mjs`, avec SQLite, binaires et transport injecté. Aucune restauration sur la tour physique attestée. Voir `local/WORKSHOP.md` pour le contrat. |
| R30 | Réauditer et continuer à améliorer l’ensemble. | Registre des exigences, vérifications significatives, preuves datées, limites visibles et choix techniques versionnés. | Ce registre, réaudits V9/V10, QA des preuves, de Jev et des demandes. Le réaudit V10 couvre jusqu’à livraison/SAV, données, droits, coûts, capacité et reprises. La qualification physique reste une étape propre. |

L’archive de Baki et le film de référence documentent les œuvres d’origine. Ils ne prouvent pas qu’un STL importé, un nouveau dossier d’un mètre ou un prototype fonctionnel correspond à ces réalisations.

## 5. Décisions structurantes de la V9

### Une seule base de preuves pour la mission et les conseils

`project-evidence.js` relit les binaires avec le même inspecteur STL que l’application. Les preuves sont attachées au dossier, à la pièce, à sa révision, à son fichier et à son unité. Un résultat tardif est abandonné si la géométrie ciblée change. Les fiches du parc sont relues pour construire le rapport actuel.

La mission reconstruite ne prend pas un compteur « mesuré » pour une preuve. Elle recalcule ses résumés à partir des preuves individuelles validées. Un rapport étranger, un ancien profil ou une empreinte incohérente ne remplace pas l’état actuel. La hauteur du brief et les dimensions de simulation restent séparées.

### Des décisions stables avant les commandes physiques

Le journal V2 prépare une autorité centrale avec ordre serveur, résultat métier conservé et versions par dossier ou machine. La base initiale est conservée plutôt que redéfinie par un changement de code. Le coffre conserve les binaires selon leurs empreintes, avec validation complète avant association lors d’une restauration.

Le protocole d’une imprimante devra cependant être qualifié séparément. Un ordre peut avoir atteint la machine même si sa réponse se perd. Le résultat devient alors inconnu jusqu’à rapprochement ; un simple renvoi automatique n’est pas une preuve de bon fonctionnement.

### Une signature qui traverse les supports

L’interface, la vidéo, la fiche d’œuvre et le dossier client partagent des éléments maîtrisés : nom, emblème, typographie, couleur et rythme. Le style des œuvres reste celui des sources. Le motion design guide la lecture et montre la relation entre une action, sa cible et son résultat.

Les séries éditoriales doivent être testées sur au moins une œuvre, une commande et un prototype réel. Les rushes à prévoir sont le geste, le détail, l’ensemble et l’échelle ; conserver également des sons d’atelier utilisables. Un agrandissement d’une vidéo ancienne ne crée pas de détail original supplémentaire.

## 6. Skills et moteurs retenus pour les travaux futurs

La table distingue les skills de méthode des moteurs et API qu’ils peuvent piloter. Aucun outil de cette table n’est déclaré installé sur le PC cible. L’installation et les licences seront vérifiées avec les versions retenues et le périmètre d’exploitation.

| Travail futur | Skill ou composant | Décision d’usage |
|---|---|---|
| Maintenir les décisions typées Jev | [Skill officiel TypeSafe](https://github.com/typesafe-ai/skills) | Référence officielle de conception des questions et des contrats ; le code BOJ.ART conserve ses candidats et ses limites. |
| Analyser les références vidéo | [claude-real-video](https://github.com/HUANGCHIHHUNGLeo/claude-real-video) | Candidat d’extraction de frames avec timecodes et transcription. Conserver les originaux pour examiner le rythme ; ne pas attribuer au cœur libre toutes les fonctions de l’offre Pro. |
| Réaliser les compositions vidéo | [Skills officiels Remotion](https://github.com/remotion-dev/skills) | Priorité aux pratiques de composition, animation, sous-titres et rendu reproductible. Les conditions du moteur Remotion restent une vérification distincte. |
| Adapter des recettes de format court | [iart-ai/tiktok-video-skills](https://github.com/iart-ai/tiktok-video-skills) | Référence complémentaire, à adapter au français et à la charte ; elle ne lit pas à elle seule l’identité des vidéos. |
| Collecte complémentaire des publications | [FlowExtractAPI](https://github.com/FlowExtractAPI/tiktok-video-downloader) | Service d’acquisition à examiner en cas de besoin précis. Ne pas présumer un moteur autonome libre ni retélécharger les 29 vidéos déjà archivées. |
| Slicing FDM | [OrcaSlicer CLI](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_mode) / [PrusaSlicer](https://github.com/prusa3d/PrusaSlicer) | Moteurs candidats à envelopper dans un contrat local. Tester le binaire, le profil, le format et la machine exacts ; le transport est un autre composant. |
| Inspection et préparation de fichiers résine | [UVtools](https://github.com/sn4k3/UVtools) | Complément de contrôle de couches et formats ; compatibilité à vérifier pour chaque machine. |
| Préparation dans un parc Formlabs | [PreForm Local API](https://developer.formlabs.com/api-reference/) | Option conditionnelle à ce matériel ; aucune recommandation d’achat n’est déduite de sa disponibilité. |
| États et commandes des imprimantes compatibles | [Moonraker](https://moonraker.readthedocs.io/en/latest/external_api/printer/) / [OctoPrint](https://docs.octoprint.org/en/main/api/job.html) | Connecteurs à qualifier avec identités de travaux et cas d’interruption. Un nom de skill n’apporte pas une compatibilité universelle. |
| Compréhension locale et voix | [Ollama](https://docs.ollama.com/capabilities/tool-calling), [whisper.cpp](https://github.com/ggml-org/whisper.cpp), [Piper](https://github.com/OHF-Voice/piper1-gpl) | Candidats à évaluer sur le matériel exact et le français. Examiner séparément licences des modèles et voix, latence et ressources utilisées. |

Les sources vidéo approfondies et les versions examinées figurent dans `VIDEO_SKILLS.md` et `qa/creative-skills-research.md`. Les sources Jev actualisées figurent dans `JEV_DECISIONS.md`. Les composants de fabrication figurent dans `JARVIS.md` et l’audit conceptuel. Ces listes constituent un choix argumenté de candidats, pas un certificat d’installation ou de performance.

## 7. Prochains jalons et critères de réussite

| Jalon | Résultat attendu | Vérification utile |
|---|---|---|
| A. Conservation et mission cohérente | Dossier, fichiers, révisions, preuves et conseils donnent une seule situation lisible. | Deux clients concurrents, reprise après fermeture, restauration sur client neuf, STL retrouvé avec la même empreinte. |
| B. Une FDM et une résine qualifiées | Une recette complète par configuration avec slicing, aperçu, transfert et suivi. | Bonne pièce, bonne machine, bonne matière ; réception perdue sans second départ involontaire ; mesures de la pièce réelle. |
| C. Réalisation mixte | Assemblage, finition, contrôle et captation reliés au même dossier. | Jeux d’assemblage, résultat de finition, temps humains et retouches observés ; rushes reliés à l’œuvre. |
| D. Offre et acquisition | Une offre compréhensible, chiffrée et réalisable, avec un parcours client et des contenus. | Contact qualifié, devis, réalisation et coût complet suivis ; rendu final et parcours social contrôlés. |

Les indicateurs proposés sont les pièces conformes terminées par heure humaine, le taux et la cause des reprises, l’écart entre coût prévu et observé, le respect du délai, la rapidité d’identification d’un blocage et les demandes qualifiées issues des contenus. Ils restent à mesurer ; les données de démonstration ne servent pas de résultats commerciaux ou industriels.

Informations à collecter au moment des raccordements : modèles et quantités d’imprimantes, firmwares, formats et API disponibles ; matières ; configuration du PC et écrans ; réseau ; postes de finition et moyens d’atelier ; captation vidéo et audio ; droits et licences des œuvres et modèles ; coûts et temps humains. Leur absence ne bloque pas les améliorations logicielles actuelles, mais elle empêche de déclarer l’autonomie physique acquise.
