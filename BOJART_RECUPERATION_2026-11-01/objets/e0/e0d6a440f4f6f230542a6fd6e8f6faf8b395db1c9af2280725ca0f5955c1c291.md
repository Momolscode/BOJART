# BOJ.ART — Jarvis, tour de contrôle de l’atelier

## L’expérience visée

L’opérateur formule une intention, inspecte ce que Jarvis prépare, puis suit l’exécution depuis la tour. Le système conserve le contexte de la création : modèle, pièces, révisions, matière, profils, machines, préparation, contrôle qualité, coût et contenu associé.

La version web réexaminée le 19 octobre 2026 constitue l’interface et un outil de préparation dans le navigateur. Le service local de journal SQLite et de coffre STL est écrit et testé sur des bases isolées ; son installation sur la tour n’est pas attestée. Les services de voix, de génération 3D, de slicing, de contrôle machine et de publication sociale sont à développer ou raccorder. Les emplois du temps et états machine présentés sont des simulations.

## Les trois écrans

| Position | Vue | Priorité opérationnelle |
|---|---|---|
| Gauche — 01 | Atelier | Parc, charges, pièces affectées, progression, incidents et disponibilité. |
| Centre — 02 | Jarvis | Intention, mission active, prochaine action, décisions nécessaires et résultat des opérations. |
| Droite — 03 | Création | Œuvre, modèle 3D, coupe, orientation, plateaux, aperçu des couches et contenus. |

La vue panoramique montre les trois ensemble. Les liens séparés permettent une fenêtre par écran. Les données du même navigateur se synchronisent ; la configuration actuelle ne synchronise pas plusieurs ordinateurs.

## Ce qui fonctionne déjà

- Création de dossiers, brief, quantité, hauteur souhaitée et notes.
- Import de STL, calcul des dimensions selon l’unité interprétée et conservation du fichier original.
- Rotation, zoom, maillage, coupe 3D et démonstrateur de socle en éclaté.
- Parc de huit ressources de démonstration, profils éditables et distinction FDM/résine UV.
- Répartition simulée selon le procédé, l’enveloppe brute et la charge ; préservation des lots et révisions déjà planifiés.
- Vue de mission : fichiers relus, références absentes ou périmées, enveloppes du parc déclaré, raccordements requis et export JSON. La répartition simulée reste une branche distincte.
- Console de commandes ciblées, reçu d’action et journal. La reconnaissance vocale locale n’est pas raccordée.
- Chiffrage du lot, scénarios de contenu et vidéothèque des publications indexées.
- Vitrine distincte, réception persistante, administration privée des demandes et import d’une projection technique dans Jarvis. Le rapprochement V11 compare les paramètres de deux exports sans remplacer le dossier conservé.
- Scènes Canvas, vidéo originale montée en boucle, transitions, focus des écrans et mode immersif.

## Jarvis comme point de commande de tout le système

Les huit domaines utilisent le même dossier et un catalogue d’opérations. L’interface affiche l’état réel de chaque capacité : action dans le navigateur, simulation ou service à raccorder. Le centre visuel garde les décisions et commandes usuelles au premier plan ; l’administration détaillée s’ouvre dans un panneau.

| Domaine | Actions disponibles dans cette version | Raccordements prévus |
|---|---|---|
| Création | Brief, import STL et inspection. | Génération 3D et CAO pilotée. |
| Préparation | Mission, coupe visuelle et répartition simulée. | Supports, orientation, assemblage, slicing et couches. |
| Production | File de démonstration, actions ciblées de simulation. | Envoi machine et télémétrie réelle. |
| Contenus | Vidéothèque, films de référence et plans de montage versionnés. | Rendu du plan exact et comptes de publication. |
| Commerce | Vitrine distincte, réception de demandes, qualification et calcul de prix du lot. | Devis commercial versionné, accord, vente et paiement. |
| Ressources | Fiches des machines. | Stocks et consommations réelles. |
| Système | Journal navigateur, service local SQLite/coffre écrit, exports et liens des trois écrans. | Installation sur la tour, voix locale et connecteurs physiques. |
| Robotique | Nouveau dossier de prototype. | Validation spécialisée et contrôleurs matériels. |

« Orchestre mon projet » relit les STL accessibles pour le dossier ciblé, confronte les preuves aux fiches déclarées et ouvre la mission complète. Son retour donne le nombre de fichiers relus, de correspondances d’enveloppe et de plans de montage conservés. Cette commande n’effectue plus automatiquement de répartition simulée, de calcul de coût ou de création de scénario. Ces actions restent accessibles séparément dans leurs parcours. Un dossier modifié pendant la lecture demande de revoir les preuves courantes.

La mission complète exportable décrit les étapes et leurs dépendances. Une étape « action disponible » exprime une possibilité d’intervention, pas une validation de son résultat. La référence d’un STL ne suffit pas à prouver que son binaire est actuellement accessible. La commande écrite utilise les intentions reconnues par le code ; elle ne prouve pas la présence d’un modèle conversationnel local.

Le mode immersif utilise des compositions dédiées : grand noyau de commande au centre, parc contenu à gauche, scène de création occupant la hauteur disponible à droite. Les listes longues gardent un défilement interne. Les trois fenêtres conservent leur rôle et partagent l’état des dossiers dans le même navigateur. Jarvis peut envoyer un aperçu vers Création et demander la vue du parc sur Atelier. La fenêtre cible confirme son affichage après vérification du projet, de la pièce, de leurs révisions et du chargement. Une commande de navigation manuelle reste locale. Un écran absent, occupé par un formulaire ou incapable de charger la 3D ne produit pas de confirmation de réussite.

## Parcours de fabrication à réaliser

### 1. Transformer l’intention en un dossier précis

« Prépare cette sculpture à un mètre » doit produire un brief : hauteur assemblée, nombre d’exemplaires, références autorisées, finition, contraintes d’assemblage et échéance. Jarvis propose ou récupère une géométrie et conserve les versions. Une image de référence ou un modèle généré ne devient pas automatiquement une géométrie imprimable.

### 2. Préparer la géométrie

Le moteur spécialisé contrôle échelle, maillage, orientation, épaisseurs, stabilité et géométrie d’assemblage. Pour les grandes pièces : segmentation, détrompeurs, clés d’assemblage, jeux et repérage. Pour la résine : évidement, drainage et accès au post-traitement selon la pièce. Les choix restent inspectables dans l’écran Création.

### 3. Affecter les procédés et les ressources

Le projet peut combiner résine et FDM. Le procédé dépend du détail, de la résistance, du volume, de la masse et de la finition attendue. Les grandes figurines en résine demandent une segmentation adaptée aux machines ; un simple test d’enveloppe ne valide pas leur fabricabilité. Les socles et petites pièces adaptés au FDM suivent leurs profils propres.

Le planificateur confronte les profils machine/matière, le plateau réellement libre, l’encombrement avec supports et marges, le stock, les travaux en cours, les durées estimées et l’échéance. Il propose un plan explicable. La version actuelle contrôle seulement le procédé et l’enveloppe brute avant de répartir une simulation.

### 4. Slicer et obtenir de vrais aperçus

Le slicer s’exécute sur la tour ou un worker local. Chaque tâche reçoit les fichiers identifiés, les transformations approuvées et une version précise des profils. Elle renvoie le fichier machine, les paramètres utilisés, un aperçu des couches, les estimations et les éventuels avertissements.

Le dashboard compare ces résultats au plan. Le contrôle de coupe 3D actuel n’est pas cet aperçu de couches : il montre une coupe de la géométrie sans fabriquer de trajectoires ni d’images d’exposition.

### 5. Envoyer le bon fichier à la bonne machine

L’orchestrateur associe explicitement le fichier sorti du slicer, sa révision, son empreinte, le profil utilisé, la matière et l’identifiant de la machine. L’état réel de la machine doit être récent. Le démarrage reçoit un accusé de la machine et devient un travail suivi, avec pause, reprise ou annulation selon les capacités du protocole.

Une reconnexion ne doit pas relancer un travail déjà envoyé. Une répétition vocale ne doit pas dupliquer une impression. Les tâches gardent des identifiants stables et un journal des résultats. La version web ne transmet actuellement aucune commande physique.

### 6. Continuer après l’impression

L’impression achevée produit des tâches de retrait, lavage et polymérisation quand nécessaires, assemblage, préparation de surface, peinture et contrôle qualité. Un travail ne devient pas une figurine vendable au seul signal « impression terminée ».

## Fonctions à forte valeur ajoutée

| Fonction proposée | Ce qu’elle apporte | État |
|---|---|---|
| Préparation complète depuis une intention | Un dossier et ses prochaines actions immédiatement visibles. | Interface présente ; moteurs spécialisés à raccorder. |
| Comparaison qualité / coût / délai | Plusieurs plans de production expliqués, à paramètres comparables. | À développer. |
| Placement visuel sur les plateaux | Orientation, supports, marges et occupation avant slicing. | À développer. |
| Préparation par versions | Retrouver exactement le fichier, le profil et les conditions d’une pièce réussie. | Révisions du dossier présentes ; chaîne complète à développer. |
| Suivi des pièces par QR | Relier pièce physique, lot, poste de finition et dossier client. | À développer. |
| Assemblage guidé en 3D | Montrer ordre, détrompeurs et points de contrôle d’une grande sculpture. | Éclaté de démonstration présent ; assemblages réels à développer. |
| Surveillance visuelle | Comparer des images d’atelier à des événements et signaler un doute utile. | Caméras et règles à raccorder ; aucune détection revendiquée. |
| Reprise ciblée d’un échec | Réimprimer uniquement la pièce et la révision nécessaires. | Gestion de révisions présente ; reprise matérielle à développer. |
| Stocks et maintenance | Anticiper manque de matière, consommables et indisponibilité d’une machine. | À développer. |
| Contenu issu de la fabrication | Associer les plans filmés, étapes et scénario à une création. | Archive et scénario présents ; capture/montage automatisés à raccorder. |
| Catalogue et sur-mesure | Relier œuvre, option, demande client, devis et dossier de fabrication. | Vitrine et réception développées ; devis commercial, disponibilité de vente et paiement à compléter. |
| Rapprochement des demandes | Voir ce qui change dans les paramètres d’un nouvel export avant de reprendre l’étude. | Comparateur V11 en lecture seule ; aucun remplacement ou accord automatique. |
| Mode prototype / robotique | Gérer plusieurs itérations d’une pièce fonctionnelle et ses contraintes. | Dossiers disponibles ; contrôles spécialisés à développer. |

## Architecture proposée

La tour héberge un service d’orchestration, un stockage des fichiers et une base de données persistante. La reconnaissance vocale locale et le modèle de langage interprètent l’intention. Ils appellent des opérations structurées ; les moteurs de géométrie, les slicers et les connecteurs machine exécutent leur tâche respective et renvoient un résultat vérifiable.

Le dashboard peut recevoir les mises à jour du service local de journal lorsqu’il est installé sur la tour. Chaque état indique sa source et sa fraîcheur. L’accès distant éventuel ne remplace pas ce service pour les tâches qui doivent continuer quand le réseau extérieur est indisponible.

Jev est identifié : le projet prépare une passerelle vers le modèle de décisions typées TypeSafe, avec règles locales de repli. Le bureau de conseils et les quatre vues du routeur possèdent des contrats distincts ; une suggestion ne produit pas un fichier de fabrication. Les bibliothèques communautaires de sélection de vues ne constituent ni un moteur de génération d’images ni un Jev officiel installé localement. Aucun appel TypeSafe réel sur la tour n’est attesté. Voir [JEV_LOCAL.md](JEV_LOCAL.md) et [JEV_DECISIONS.md](JEV_DECISIONS.md).

Les choix du modèle local, du nombre de workers et des formats de prévisualisation doivent suivre les caractéristiques exactes de la tour et du parc. Le budget seul ne détermine pas une configuration ni une performance mesurée.

## Points d’intégration vérifiés

- **Moonraker / Klipper** expose des opérations de consultation, de souscription d’état et de gestion d’impression. Le connecteur doit vérifier les capacités et l’état de la machine. Source : [Printer Administration](https://moonraker.readthedocs.io/en/latest/external_api/printer/).
- **OctoPrint** documente l’import, la sélection et les opérations sur les fichiers ; le slicing dépend du moteur disponible et configuré. Sources : [File operations](https://docs.octoprint.org/en/main/api/files.html) et [Slicing](https://docs.octoprint.org/en/main/api/slicing.html).
- **UVtools** fournit de l’analyse, de la manipulation et de la conversion de fichiers résine ainsi qu’une interface en ligne de commande. Cela ne prouve pas une compatibilité universelle ni le pilotage réseau de toutes les imprimantes résine. Source : [dépôt et documentation UVtools](https://github.com/sn4k3/UVtools).

Ces interfaces rendent l’architecture envisageable. Le raccordement concret reste à qualifier sur les modèles, firmwares et formats du parc BOJ.ART.
