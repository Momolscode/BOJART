# BOJ.ART — vers un Jarvis utilisable dans l’atelier

État du 31 octobre 2026. Version M06, construite sur M05. Ce document distingue ce qui a été réalisé, ce qui a été vérifié avec des doubles de test, et ce qui reste à qualifier sur la tour.

## Ce qui a changé

Le projet possède maintenant un point d’entrée commun pour la commande écrite et la transcription vocale, un graphe LangGraph exécuté localement, un journal persistant, un adaptateur Jev borné et une distribution immédiate aux vues. Les pages restent accessibles si LangGraph ou les moteurs IA manquent ; les commandes connues utilisent alors les règles locales.

Le graphe réellement exécuté comporte quatre nœuds : `route`, `guard`, `dispatch`, `receipt`. L’état est sauvegardé entre les étapes. La reprise explicite relit le journal et réexécute ces nœuds idempotents ; elle ne rejoue pas aveuglément un appel à Jev dont le résultat s’est perdu. Les checkpoints et le journal sont dans `missions.sqlite3`, déjà couverte par la sauvegarde globale M05. Aucun service LangGraph hébergé ni traçage LangSmith externe n’est utilisé.

L’application expose neuf intentions visuelles : modèle sélectionné, sources au centre, Studio à droite, planning démonstratif, dossiers, contenus, base métier, conception et interruption de la réponse. Une demande de conception ouvre le poste correspondant ; elle ne fabrique pas une pièce sans proposition paramétrique relue. Le catalogue Studio et les brouillons restent partagés entre les dossiers.

## La place exacte de Jev

Jev reçoit **le texte final de la demande et des choix autorisés**, après la transcription. Il propose une intention. Les mêmes contrôles locaux vérifient ensuite le dossier, la révision, le contexte, le délai et les fichiers. Jev ne reçoit ni audio, ni vidéo, ni fichiers de l’atelier dans cette intégration.

L’API documentée accepte du texte et des états structurés. La version `jev-1.14.0`, publiée le 14 octobre, est fixée explicitement ; l’alias changeant `jev-latest` n’est pas utilisé [1]. Le contrat `Choice` renvoie un choix, une distribution et un indicateur de confiance [2]. Cet indicateur décrit la distribution ; il ne certifie ni la vérité ni la sécurité d’une action [3].

Le code contrôle les identifiants, les probabilités finies, leur somme, le choix gagnant et la cohérence de la confiance. Les seuils conservateurs sont provisoires, non calibrés sur la voix de l’atelier. **Toute interprétation produite par Jev exige actuellement une confirmation visuelle**, même si le score est élevé. Les ordres locaux connus s’affichent directement.

L’appel distant est désactivé par défaut. Il exige `BOJ_JEV_ENABLED=1` et `TYPESAFE_API_KEY` dans l’environnement du serveur. Aucun secret n’est livré. Un échec ouvre une pause de 30 secondes ; il n’y a pas de répétition automatique de l’appel. Le navigateur n’obtient jamais la clé. La phrase saisie est transmise à TypeSafe uniquement quand l’intégrateur a activé ce mode et qu’aucune règle locale ne correspond.

La composition d’interface par Jev dans `json-render` constitue une piste distincte : le logiciel prépare les composants et leurs données, Jev choisit leur disposition. Cette API est encore expérimentale, et sa composition n’exécute pas les actions [4]. Elle n’a pas été ajoutée à M06 : nos vues existantes fournissent déjà un catalogue déterministe et vérifiable.

## Ce que les assistants existants nous apprennent

| Projet examiné | Apport utile pour BOJ.ART | Limite de la comparaison |
|---|---|---|
| Home Assistant Assist | Chaîne locale voix → intention → action → réponse ; commandes spécialisées rapides ; Wyoming pour relier les briques vocales [5][6] | Excellent point de comparaison pour la commande vocale ; ne fournit pas notre atelier CAO/Studio |
| OpenVoiceOS | Architecture de services et extensions pour un assistant vocal maîtrisé localement [7] | Projet à assembler et à maintenir ; aucune intégration automatique de nos machines |
| Leon | Outils déclarés, contexte et séparation des modes d’action ; piste pour un assistant personnel [8] | La branche 2.0 examinée est une Developer Preview ; ne pas la présenter comme une base d’atelier déjà qualifiée |
| Microsoft JARVIS / HuggingGPT | Orchestration d’outils et de modèles spécialisés pour des tâches composées [9] | Dépôt de recherche ; ce n’est pas une tour de contrôle vocale prête à brancher |
| Démonstration Jev de TypeSafe | Catalogue d’actions borné, choix explicite, vérification indépendante du résultat [10] | Démonstrateur ; ses résultats ne mesurent pas notre système |
| Pipecat / LiveKit | Gestion des tours de parole, interruptions et transport audio ; retour d’interface pendant les traitements [11][12] | Briques pour une future conversation continue, pas un remplacement de nos règles métier |

La conclusion est une décision d’architecture pour ce projet : conserver notre noyau de données et nos contrôles, y relier une chaîne vocale unique, et rendre chaque capacité observable. Multiplier les assistants en parallèle ne résoudrait pas la cohérence du dossier ni les accusés d’affichage.

## La fluidité, concrètement

M06 utilise une prise audio déclenchée par bouton, limitée à 15 secondes. `faster-whisper` traite le WAV localement lorsque ses fichiers de modèle sont configurés. Le bouton reste indisponible si les prérequis manquent. Le son brut n’est pas conservé. Une seule fenêtre réserve le microphone ; une fenêtre perdue libère sa réservation après expiration. La synthèse vocale utilise, si disponible, une voix française déclarée locale par le navigateur.

Les vues reçoivent un signal immédiat par SSE, puis retirent leur commande dans la file durable. Un contrôle périodique reprend le relais si ce flux est indisponible. Le signal SSE n’est pas un transport audio. Les commandes et les accusés ne bloquent plus derrière le verrou global d’un long calcul CAO. L’affichage du résultat, ses fichiers et sa révision sont vérifiés avant le reçu.

Les essais mesurent le délai du texte final envoyé au reçu d’affichage dans Chromium local. La première passe donne 63,3 à 88,1 ms. Une seconde, pendant d’autres tests, contient un pic de 1 413 ms : il est conservé dans les preuves. La dernière passe au calme donne **66,1 à 98 ms sur douze commandes** (médiane par rang : 79,4 ms). Pendant un vrai calcul CAO du même serveur, **les six affichages aboutissent avant la fin du calcul**, en 114,9 à 997,3 ms. Les petits échantillons sont dans `ACCEPTANCE_M06.json`, `final/ACCEPTANCE_M06.json` et `load/ACCEPTANCE_M06.json`. Ils excluent Jev et la reconnaissance réelle : ce n’est pas une promesse de latence vocale sur le PC cible.

Pour une conversation continue, la prochaine étape proposée est **Pipecat avec SmallWebRTC**, sous réserve d’une recette sur la tour. Sa documentation privilégie WebRTC pour l’audio navigateur ; sa séparation entre voix et travail d’interface évite de suspendre toute la conversation lors d’un traitement [11]. LiveKit reste une alternative, pas une seconde pile à faire fonctionner en même temps [12]. Le mot d’éveil, la détection de fin de parole et les interruptions naturelles ne sont pas livrés comme opérationnels dans M06.

## État de toutes les grandes fonctions

| Fonction | État M06 | Preuve ou condition restante |
|---|---|---|
| Dossiers, versions, CAO paramétrique, aperçu 3D | Conservés et testés | Deux calculs réels dans la recette de régression |
| Sauvegarde globale et restauration | Conservées ; journal et checkpoints ajoutés | Restauration dans un nouveau dossier ; anciennes commandes neutralisées |
| Commande écrite vers les vues | Fonctionnelle | Chromium, vrai rendu et reçu logiciel |
| Microphone → transcription → commande | Code relié ; chaîne testée avec audio synthétique et faux ASR | Installer les poids du modèle, mesurer la reconnaissance et le bruit sur le vrai micro |
| LangGraph | Installé et exécuté dans l’environnement de développement | Installer les dépendances verrouillées sur le PC cible |
| Jev | Adaptateur implémenté, contrat et pannes testés avec doubles | Clé absente ; aucun appel réel ni taux de précision mesuré |
| Parole de retour | Code relié au navigateur | Voix française locale et haut-parleurs à essayer |
| Conversation continue / mot d’éveil | Conçus, non implémentés | Choisir et qualifier une seule pile audio |
| Base métier | Recherche locale sourcée | Recherche par mots-clés, sans compréhension sémantique ajoutée |
| Studio / contenus | Consultation et préparation existantes reliées aux vues | Rendu vidéo et publication externes non connectés |
| Planning | Démonstration signalée | Parc, durées et disponibilité réels à renseigner |
| Découpe, FDM et résine | Aucun adaptateur physique actif | Profils, protocoles, opérateur et une première machine de chaque type à qualifier |
| Comptes sociaux / statistiques | Non connectés | Accès propriétaire et validation des réponses API |
| Sites et devis | Sources récupérées séparément | Pas de nouveau raccordement ou déploiement dans M06 |

## Ce que signifie « enrichir Jarvis »

L’enrichissement durable de cette version est vérifiable : code, sources de recherche, commandes déclarées, journal, checkpoints et recette. Cela ne constitue pas un réentraînement du modèle ni la récupération du chat complet. Les documents ne deviennent pas automatiquement des faits sur le matériel. Les observations du PC réel, les références des imprimantes et les essais de voix doivent alimenter des données datées et sourcées.

On peut réduire les erreurs et organiser leur récupération ; on ne peut pas garantir qu’aucun problème n’arrivera. La cible est : un problème visible, aucune action physique incontrôlée, un travail conservé, et une reprise qui ne multiplie pas les effets.

## Sources primaires consultées le 31 octobre 2026

1. TypeSafe, modèles et formats d’entrée : https://docs.typesafe.ai/models
2. TypeSafe, contrat Choice : https://docs.typesafe.ai/primitives/choice
3. TypeSafe, signification de la confiance : https://docs.typesafe.ai/confidence
4. json-render, intégration expérimentale Jev : https://json-render.dev/docs/jev
5. Home Assistant, choix d’une chaîne vocale locale : https://www.home-assistant.io/voice_control/voice_remote_local_assistant/
6. Home Assistant, Wyoming : https://www.home-assistant.io/integrations/wyoming
7. OpenVoiceOS, manuel technique : https://openvoiceos.github.io/beta-technical-manual/
8. Leon, architecture de la branche develop : https://github.com/leon-ai/leon/blob/develop/core/context/ARCHITECTURE.md
9. Microsoft JARVIS : https://github.com/microsoft/JARVIS
10. TypeSafe, démonstration Jev Browser : https://github.com/TypeSafeAI/typesafe-playground/blob/main/docs/jev-browser-agent.md
11. Pipecat, transport et interface : https://docs.pipecat.ai/client/concepts/choosing-a-transport et https://docs.pipecat.ai/pipecat/learn/ui-worker
12. LiveKit, tours de parole et interruptions : https://docs.livekit.io/agents/logic/turns/
13. LangGraph, persistance et interruption : https://docs.langchain.com/oss/python/langgraph/persistence et https://docs.langchain.com/oss/python/langgraph/interrupts
14. LangGraph SQLite 3.1.3 : https://pypi.org/project/langgraph-checkpoint-sqlite/3.1.3/
15. faster-whisper, moteur local : https://github.com/SYSTRAN/faster-whisper

Les performances publiées par ces projets n’ont pas été utilisées comme des mesures de BOJ.ART.
