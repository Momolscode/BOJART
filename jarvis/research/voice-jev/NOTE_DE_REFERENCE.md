# BOJ.ART / JARVIS — voix, décisions et écrans
## Réaudit de placement de Jev et comparaison d'assistants existants

**Date de recherche : 30 octobre 2026.**
**Statut : conclusions documentaires et architecture proposée. Rien n'est installé par ce dossier.**

## 1. Ce que nous avons effectivement examiné

- Le code applicatif et la configuration du pack joint Mission 03, qui reprend Mission 02.
- Les bilans de livraison de Missions 02 et 03.
- L'infographie précédente « JARVIS 5 — BOJ.ART ».
- Les documentations primaires listées ci-dessous.

Le fichier PREUVES_LECTURE_M03.json conserve l'empreinte du pack et celle des 16 fichiers applicatifs examinés. Aucun test antérieur n'a été réexécuté dans cette recherche. Aucun accès à la tour ni au code actuellement déployé n'est revendiqué.

### État établi dans ce périmètre

| Fonction | Constat |
|---|---|
| Ollama | Adaptateur présent ; désactivé dans la configuration exemple. |
| Voix | Capture limitée et transcripteur facultatif présents ; désactivés dans la configuration exemple. L'exécution faster-whisper prévue utilise des poids locaux, sur CPU. |
| Jev | Aucun branchement identifié dans les 16 modules applicatifs examinés. Les décisions de conception antérieures ne prouvent pas un appel réel. |
| LangGraph | Aucun branchement identifié dans ces modules. Un graphe dessiné ne prouve pas son exécution. |
| Trois écrans | Le bilan M02 précise que « à droite » désigne son panneau 3D ; l'appairage des moniteurs physiques reste à réaliser. |
| Fidélité artistique | Le catalogue et les références réelles existent ; ils ne constituent pas une reconnaissance automatique de la figurine. |

## 2. Corrections du schéma précédent

1. Retirer « Jev » des cases transcription, dialogue vocal et synthèse vocale. Jev évalue des décisions structurées ; il n'est pas le microphone ni la voix. La documentation actuelle des modèles indique des entrées textuelles, sans audio ni vidéo ; l'API a séparément des fonctions image expérimentales. [S1, S2]
2. Placer les contrôles de permissions, de version, de disponibilité et de budget AVANT les effets. Conserver également une vérification du résultat APRÈS l'exécution.
3. Séparer documentation retrouvée, faits métier et télémétrie récente. Une fiche ne prouve jamais qu'un plateau est libre.
4. Montrer deux parcours : une commande connue va directement vers un outil contrôlé ; une demande complexe passe par la recherche et la planification.
5. Distinguer statut de tâche, statut du fichier et accusé de chargement à l'écran. Une carte « en cours » n'est pas une réalisation terminée.

## 3. Assistants et briques examinés

- **Home Assistant Assist** : exemple concret de pipeline vocal local et de commandes fermées rapides. À étudier pour la voix et les équipements périphériques, pas comme moteur de sculpture. [S3]
- **OpenVoiceOS** : assistant modulaire avec skills, plugins et bus de messages. Sa documentation souligne le travail d'installation et le statut ancien de certaines parties graphiques. À étudier pour les contrats de skills, sans imposer toute sa pile à BOJ.ART. [S4]
- **Leon 2.0 Developer Preview** : modes contrôlés et agentiques, outils et contexte. Son README avertit que le site documentaire reflète surtout l'ancienne architecture. Intéressant pour comparer les parcours, non qualifié ici pour la production. [S5, S6]
- **Microsoft JARVIS / HuggingGPT** : référence de recherche sur la décomposition de tâches et le choix de modèles spécialisés. Le README consulté présente un environnement historique ; ce n'est pas notre installateur atelier. [S7]
- **Pipecat** : candidat prioritaire pour la couche vocale. La documentation décrit un UIWorker et des échanges bidirectionnels avec l'interface ; le SmallWebRTC est destiné aux implémentations légères et essais locaux. Versions et compatibilité restent à vérifier avant adoption. [S8, S9]
- **LiveKit Agents** : alternative à Pipecat pour les tours de parole et interruptions. Comparaison utile, pas installation simultanée de deux couches vocales. [S10]

Aucun de ces projets n'a été exécuté dans cette recherche. Leur documentation ne qualifie pas notre atelier ni ses procédés.

## 4. Place proposée de Jev

### Usage pertinent

Jev reçoit une transcription finale et un contexte réduit : projet, révision, sélection, état utile, candidats déjà disponibles. Il peut choisir une intention parmi plusieurs, classer des éléments à examiner ou proposer une disposition d'interface.

### Usage inutile ou incorrect

Ne pas l'appeler pour chaque clic, pour une commande claire déjà reconnue, pour calculer une cote exacte ou pour remplacer la validation d'une commande physique. Ne pas lui transmettre tout le catalogue privé pour ouvrir une vue.

### Local et distant

Le service Jev de TypeSafe est distant. Un fonctionnement entièrement local exige un parcours de règles et/ou un décideur local qualifié séparément. Un JSON valide et une forte confiance déclarée ne prouvent pas la justesse. Tester les demandes françaises et les ambiguïtés.

### Affichage génératif

L'intégration Jev de json-render est expérimentale. L'application fournit les composants, valeurs et liaisons autorisés ; la composition ne réalise pas les actions. Je la réserve aux vues exploratoires. Les commandes critiques et leurs positions restent fixes. [S11]

## 5. Ce qui donnera réellement la fluidité

### Contrat de contexte

Chaque intention transporte : session, tour de parole, projet, révision, pièce sélectionnée, écran cible, identifiant de commande et référence du fichier. Une réponse dépassée ne change pas le nouveau dossier.

### Régie des écrans

Les trois fenêtres sont appairées à des rôles. Une seule session audio parle et écoute ; les deux autres affichent. Un écran déconnecté est annoncé et le résultat reste consultable au centre. Les accusés de chargement ne sont pas confondus avec une preuve de fabrication.

### Réponse progressive

L'interface peut afficher écoute, transcription et tâche en cours pendant le travail. Un aperçu existant arrive sans attendre la fin de la réponse orale. Un nouveau modèle 3D ou un rendu vidéo s'affiche seulement après sa production réelle. Les prévisualisations spéculatives n'envoient aucune commande machine.

### Temps cibles proposés, non mesurés

- Retour d'interface : au plus 200 ms après réception de l'événement local.
- Affichage d'un actif déjà disponible et préchargé : p95 au plus 1 s après transcription finale, dans le protocole de test retenu.
- Interruption de la réponse parlée : au plus 300 ms après détection validée de l'interruption.
- La durée d'une génération 3D, d'un slicing ou d'un montage n'est pas assimilée à ces délais d'interface.

Les mesures doivent indiquer cache chaud/froid, taille des fichiers, matériel, bruit et charge GPU. Ces objectifs ne sont pas une promesse pour la tour inconnue.

### Interface et transport

AG-UI décrit le transport d'événements et la synchronisation d'état ; json-render décrit la composition. Ce sont deux fonctions différentes. RTVI peut déjà couvrir le lien voix-écran : ne pas ajouter un deuxième bus complet sans besoin démontré. [S8, S12]

## 6. Missions longues et sécurité

LangGraph peut conserver l'état et reprendre une mission interrompue. Son mécanisme de reprise peut réexécuter un nœud : les effets doivent être isolés, identifiés et rapprochés des reçus externes. Un checkpoint ne garantit pas l'absence de deuxième impression ou deuxième facturation. [S13, S14]

La validation se fait avant la transmission ; le résultat est observé après. Une réponse perdue mène à un état inconnu puis à une réconciliation. La correction de parole « non, seulement le socle » annule une proposition non exécutée ; elle n'annule pas rétroactivement une action physique.

## 7. Première recette à qualifier

1. « Affiche cette pièce à droite » : vérifier projet, révision, écran et fichier réellement chargé.
2. « Agrandis le socle à 24 cm » : proposition puis nouvelle géométrie ; autre pièce inchangée.
3. « Non, 18 cm » : dernière intention liée à la bonne proposition.
4. « Montre les plans de peinture » : sources authentiques et timecodes, aucun faux rush.
5. Interrompre la voix de Jarvis : arrêter l'audio, pas une imprimante.
6. Reconnecter une fenêtre : pas de double commande ni de double réponse vocale.
7. Rendre Jev indisponible : commandes locales connues encore utilisables ; ambiguïtés affichées.
8. Charger un rendu lourd : garder le journal et la régie réactifs, mesurer les délais.

## 8. Décision proposée

Conserver les fichiers et modèles M01–M03. Construire une couche de session et d'événements commune. Évaluer Pipecat sur la voix et l'interface, LiveKit comme alternative. Placer Jev dans les choix ambigus et les vues adaptatives, jamais comme source audio ni autorité machine. Utiliser LangGraph uniquement pour les missions nécessitant plusieurs étapes et une reprise durable. Ne pas installer toutes les références comparées.

## Sources primaires consultées

S1 — TypeSafe, modèles : https://docs.typesafe.ai/models
S2 — TypeSafe, System One : https://docs.typesafe.ai/api/system-one
S3 — Home Assistant, voix locale : https://www.home-assistant.io/voice_control/voice_remote_local_assistant/
S4 — OpenVoiceOS, manuel : https://openvoiceos.github.io/beta-technical-manual/
S5 — Leon, README develop : https://github.com/leon-ai/leon/blob/develop/README.md
S6 — Leon, architecture : https://github.com/leon-ai/leon/blob/develop/core/context/ARCHITECTURE.md
S7 — Microsoft JARVIS : https://github.com/microsoft/JARVIS/blob/main/README.md
S8 — Pipecat, voix et interface : https://docs.pipecat.ai/pipecat/learn/ui-worker
S9 — Pipecat, SmallWebRTC : https://docs.pipecat.ai/api-reference/client/js/transports/small-webrtc
S10 — LiveKit, tours de parole : https://docs.livekit.io/agents/logic/turns/
S11 — json-render, Jev expérimental : https://json-render.dev/docs/jev
S12 — AG-UI, états : https://docs.ag-ui.com/concepts/state
S13 — LangGraph, persistance : https://docs.langchain.com/oss/python/langgraph/persistence
S14 — LangGraph, interruptions : https://docs.langchain.com/oss/python/langgraph/interrupts

Les contenus web peuvent évoluer. Le dossier est une décision d'architecture à partir de ces documents, pas une certification de leurs implémentations.
