# BOJ.ART / Jarvis — innovations utiles et plan d’intégration

**Recherche vérifiée le 30 octobre 2026.** Ce dossier prépare des évolutions ; il ne les déclare pas installées.

## Point de départ
La documentation fournie de Mission 02 décrit un dialogue borné pour un socle paramétrique, des propositions liées à une révision, un adaptateur Ollama désactivé par défaut et une capture vocale à raccorder. Elle distingue le panneau 3D du véritable troisième moniteur. Le PC cible, les modèles IA et les imprimantes ne sont pas qualifiés. Ce dossier ne remplace pas Mission 02 et ne modifie aucun site publié.

Contraintes préservées : projet BOJ.ART distinct d’UNUM/M-Tek ; 7–8 imprimantes envisagées ; FDM + résine ; trois écrans ; budget PC 3 000–5 000 € avec réemploi ; local prioritaire ; pas de dépense ou publication implicite ; identité fidèle à l’œuvre, pas seulement spectaculaire.

## 1. Mémoire audiovisuelle recherchable — PRIORITÉ A
**Nouvelle capacité proposée :** « Retrouve le passage où il peint la cicatrice, avant la révélation de la figurine. » Le résultat présente les extraits avec fichier d’origine, timecodes, œuvre, révision et disponibilité du disque.

**Brique vérifiée :** Qwen3-VL-Embedding-2B accepte texte, images et vidéo ; son dépôt officiel indique Apache 2.0 [S01]. Le reranker associé peut réordonner les résultats, mais il ne doit pas être chargé en permanence.

**Intégration proposée :** commencer par un inventaire de fichiers autorisés + empreintes, segmentation de plans, transcriptions et vignettes. Recherche textuelle simple comme baseline, recherche visuelle comme enrichissement. Chaque extrait pointe vers une source accessible. Les films générés, les rushes authentiques et les rendus refusés restent dans trois classes distinctes.

**Garde-fous :** un score de similarité n’est pas une preuve d’identité, de droit d’usage ou de conformité de couleur. Un disque absent reste marqué indisponible. Le contenu d’une légende ou d’un PDF n’est pas une instruction d’exécution.

**Réception :** jeu annoté de 30 recherches BOJ.ART, résultats pertinents dans les cinq premiers, timecodes ouvrables, suppression propagée et refus de source inconnue. Ces objectifs n’ont pas été mesurés ici.

## 2. Voix naturelle et référence à la sélection — PRIORITÉ A
**Nouvelle capacité proposée :** sélectionner un modèle puis dire « agrandis uniquement celui-ci à vingt-quatre centimètres », corriger « non, dix-huit » et interrompre la réponse vocale sans interrompre une impression.

**Briques vérifiées :** Pipecat documente détection des tours de parole et interruptions [S02], ainsi qu’un transport SmallWebRTC auto-hébergé sans service tiers requis [S03]. NVIDIA propose NeMo-Speech.cpp pour l’inférence locale [S04]. Parakeet TDT 0.6B v3 reconnaît notamment le français, sous CC BY 4.0 [S05]. Sa prise en charge dans NeMo-Speech.cpp est toutefois en phrase complète : pas de streaming avec état natif [S06]. Le moteur existant faster-whisper reste la référence de comparaison, pas un composant à supprimer sans mesure.

**Intégration proposée :** conserver le bouton/pédale pour parler au pilote. Fournir à l’interpréteur l’identifiant sélectionné, sa révision, l’écran et la dernière proposition, plutôt que lui demander de deviner le sens de « celui-là ». La commande garde ses préconditions même lorsque la présentation change.

**Garde-fous :** ne pas exécuter une transcription partielle. L’interruption du discours et l’annulation d’une action sont deux événements distincts. Le stop physique reste indépendant. Les micros ne doivent pas envoyer de données hors de la tour par repli caché.

**Réception :** silence, hésitation, changement d’unité, conversation de tiers, voix de Jarvis entendue par son micro, correction en cours de parole et travail GPU lourd. Mesurer intention ET paramètres, pas seulement les mots reconnus.

## 3. Missions qui survivent à une coupure — PRIORITÉ A
**Nouvelle capacité proposée :** un dossier reprend à la dernière étape confirmée après redémarrage, même si un modèle, un navigateur ou un fournisseur externe est indisponible.

**Brique à étudier :** Temporal documente exécution durable et politiques de reprise [S07]. Ses activités sont normalement réessayées ; l’idempotence du destinataire reste nécessaire pour éviter un effet externe répété [S08].

**Décision pour BOJ.ART :** ne pas remplacer immédiatement le journal SQLite existant. D’abord formaliser les activités, leurs identifiants et leurs états ; comparer ensuite l’apport d’un moteur plus lourd sur un pilote isolé. Une base locale et une file durable peuvent suffire au démarrage.

**Contrat proposé :** une création géométrique bornée peut être rejouée avec le même identifiant ; une demande payante au résultat inconnu ou une commande imprimante au résultat inconnu ne peut pas l’être sans rapprochement avec le fournisseur ou la machine. Annulation, échec et résultat inconnu ne sont pas interchangeables.

**Réception :** perte de réponse APRÈS acceptation, redémarrage de l’agent, modification de dossier, serveur indisponible. Aucun "exactement une fois" promis par le seul orchestrateur.

## 4. Planning de la pièce finie — PRIORITÉ A/B
**Nouvelle capacité proposée :** « Quel délai change si une résine tombe en panne, ou si la peinture prend deux fois plus longtemps ? » Jarvis présente les opérations, les indisponibilités, les hypothèses et les étapes où la présence humaine est nécessaire.

**Brique vérifiée :** OR-Tools CP-SAT traite des contraintes de précédence et de non-chevauchement ; Google fournit aussi un exemple de machines alternatives [S09–S11]. C’est un solveur mathématique, pas un LLM.

**Livré ici :** petit prototype Python séparé, données entièrement fictives. Il réserve machine et station jusqu’au retrait, respecte les disponibilités de l’opérateur, partage une station lavage/cure et simule des changements de contexte. 22 tests Python exécutés. L’interface présente cinq scénarios précalculés.

**Limite de méthode :** OR-Tools n’a pas pu être installé ici, le téléchargement étant empêché par la résolution réseau de cet environnement. Le prototype livré utilise une heuristique indépendante (énumération de l’ordre des dossiers et placement glouton). Ce n’est pas une intégration OR-Tools et il ne prouve pas l’optimalité ni l’impossibilité globale d’un délai. "NO_PLAN_FOUND" signifie seulement qu’il n’a pas trouvé de plan.

**Étapes non modélisées :** placement de plusieurs pièces sur un plateau, capacités matières, stock, trajets, traitement détaillé, tous les postes de finition, emballage réel, interruption d’un cycle déjà lancé et décisions de maintenance. Les durées ne sont pas des paramètres de traitement résine. Les réservations ne sont pas une autorisation machine.

**Raccordement suivant :** remplacer les hypothèses par profils qualifiés et temps observés ; geler les tâches réellement lancées ; ajouter un vérificateur indépendant de chaque planning ; puis connecter la présentation, jamais le départ machine directement depuis le solveur.

## 5. Studio fidèle et montage reproductible — PRIORITÉ B
**Nouvelle capacité proposée :** « Reprends le montage validé, remplace uniquement le plan de rupture et garde exactement les raccords. »

**Brique vérifiée :** OpenTimelineIO conserve clips, plages temporelles, pistes, transitions, marqueurs et métadonnées, avec des médias externes référencés [S12]. Ce n’est ni un moteur de rendu ni une garantie de transfert de tous les effets After Effects.

**Intégration proposée :** montage versionné en OTIO + recettes de rendu + fichiers source identifiés. Séparer le rush de l’artiste, le storyboard de style et la référence d’identité. Chaque génération passe par trois portes : (1) fichier décodable et paramètres compatibles ; (2) personne/sculpture, vêtements, couleurs et détails cohérents ; (3) montage artistiquement approuvé. La porte 2 reste assistée et relue : la similarité visuelle ne certifie pas la fidélité.

**Préparation avant coût :** vrai média accessible, dimensions natives, durée, ratio sans déformation, rôle start/end correct, découpes sans grille ni légendes involontaires, modèle/version et prix relus, identifiant de demande réutilisé en cas de résultat incertain. Les quotas d’essais plafonnent les relances. Toute défaillance sans cause est conservée comme inconnue, pas attribuée au prompt sans preuve.

**Réception :** remplacer un plan n’altère pas les autres ; aucune génération rejetée ne devient référence automatique ; le rendu rouvre sur les mêmes sources/timecodes ; piste audio et droits associés présents. Les skills officiels Remotion sont des candidats pour les recettes, pas des outils déjà installés [S16].

## 6. Conception 3D guidée par les différences — PRIORITÉ B
**Nouvelle capacité proposée :** « Agrandis le socle, mais garde exactement l’entraxe des fixations. » Le panneau compare avant/après : dimensions, interfaces qui doivent rester stables, volumes et faces réellement modifiés.

**Voie retenue :** recettes paramétriques CadQuery existantes d’abord, puis visualisation Blender/FreeCAD selon besoin. Ajouter des paramètres par familles : socles, boîtiers, supports, articulations. Une demande hors recette déclenche une étude au lieu d’exécuter du code Python arbitraire généré par le LLM.

**Laboratoire créatif :** TRELLIS.2 reste un candidat de génération image→3D ; dépôt officiel sous MIT, Linux testé, GPU NVIDIA d’au moins 24 Go annoncé [S13]. Les temps publiés sur H100 ne sont pas transposables à votre future tour. Le modèle accepte aussi des topologies non adaptées directement à l’impression ; ses sorties requièrent une préparation et un contrôle propres à l’usage.

**Exclusion vérifiée :** CAD-Recode est intéressant pour reconstruire du CadQuery depuis un nuage de points, mais son dépôt consulté porte une licence CC BY-NC 4.0 [S14]. Il n’entre donc pas par défaut dans la pile commerciale BOJ.ART sans droits supplémentaires adaptés.

## 7. Un laboratoire d’amélioration qui ne casse pas la production — PRIORITÉ A
Chaque candidat (modèle, runtime, skill, slicer) possède une version, un fournisseur, sa licence de code ET de poids, ses ressources observées et ses tests. D’abord un mode témoin : il propose sans agir et on le compare à la version retenue. Une mise à jour ne remplace pas automatiquement celle qui pilote les dossiers.

Ollama expose des réglages de chargement et de concurrence ; contexte et parallélisme consomment de la mémoire supplémentaire [S15]. Prévoir une file de travaux lourds plutôt que six modèles simultanément. Les services de dossiers, reçus et télémétrie doivent rester utilisables quand un rendu monopolise le GPU.

Jev reste un adaptateur facultatif. Sa documentation actuelle présente Jev 1.14 comme nouvelle version et un alias stable encore différent ; utiliser une version explicite plutôt qu’un alias mobile pour les décisions qualifiées [S18]. Une confiance renvoyée ne vaut pas une validation d’atelier.

**Critères :** exactitude sur les contraintes, erreurs de cible, latence sous charge, mémoire, restauration, fonctionnement hors ligne. Aucun nouveau modèle n’est exécuté dans cette livraison. Le skill officiel webapp-testing est un candidat pour automatiser la recette des écrans [S17] ; aucun skill tiers n’est installé automatiquement.

## Les premières itérations que je recommande
1. Mémoire médias et références : corpus BOJ.ART autorisé, fichiers stables, timecodes et provenance.
2. Recettes CAO et sélection à la voix : compléter Mission 02, mesurer la transcription et la correction de paramètres.
3. Planning hors machines : alimenter le prototype par une fiche de capacités et des observations, puis comparer avec CP-SAT.
4. Chaîne de génération/rendu : contrôle préalable, budget, recette et approbation de fidélité.
5. Qualification d’une FDM et d’une résine : préconditions, reprise et contrôle physique avant extension.

L’atelier non installé n’empêche pas de développer les contrats, les tests, l’interface, la conservation et les outils de préparation. Il empêche de qualifier honnêtement le comportement du matériel et les performances de la tour. Aucun achat supplémentaire n’est justifié par cette recherche seule.

## Ce qui a été fait et non fait
**Fait :** lecture des documents fournis de Mission 02, recherche primaire, sélection des innovations, code de planning isolé, exemples, tests et présentation interactive.
**Non fait :** installation sur PC, connexion micro ou machines, chargement de nouveaux poids, modification des sites, accès comptes sociaux, nouvelle génération payante ou qualification de sécurité industrielle.
