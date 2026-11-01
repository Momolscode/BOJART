# BOJ.ART — ce qui rapproche réellement Jarvis de l’usage quotidien

Recherche actualisée le 1 novembre 2026, heure de Paris. Base M06 récupérée depuis son archive et vérifiée : 411 fichiers du manifeste intacts. Le développement M07 prolonge cette base ; les recettes historiques ne sont pas des mesures de la tour réelle.

## Réponse à l’objectif

Oui, le système se rapproche d’un assistant d’atelier utilisable : il conserve un dossier, comprend des commandes déclarées, affiche leur résultat, vérifie les reçus et reprend une tentative. La sensation « Jarvis » dépend maintenant surtout de la chaîne vocale réelle, des temps sous charge et des données du parc.

Le nouvel ordre « Ouvre la tour de contrôle » compose une scène dans trois vues déjà ouvertes : planning démonstratif à gauche, dossiers au centre, modèle explicitement sélectionné ou Studio à droite. Il ne sélectionne pas un modèle au hasard. Le succès exige les trois reçus de rendu. Une distribution partielle reprend les mêmes identifiants ; elle ne crée pas trois commandes supplémentaires.

M07 permet également de dire « Confirme cet affichage » ou « Annule cette proposition » pour la proposition visuelle courante. Le dossier, la fenêtre, la révision et le délai sont revérifiés. « Oui » seul n’est pas suffisant. Cette autorisation porte uniquement sur l’affichage proposé.

## Recherche sur les assistants existants

| Projet | Ce qu’il apporte à notre conception | Décision pour BOJ.ART |
|---|---|---|
| Home Assistant Assist | Chaîne locale de reconnaissance, intentions et réponse. Deux approches STT : vocabulaire fermé rapide ou transcription ouverte [1]. Wyoming relie les services vocaux [2]. | Garder des commandes locales rapides. Ne pas remplacer tout notre atelier par un système de domotique. |
| OpenVoiceOS | Assistant vocal libre, modulaire, avec mot d’éveil, extensions, parole et affichage [3]. | Source utile pour la modularité et les satellites. Son installation demande de l’assemblage ; aucun raccordement implicite de nos imprimantes. |
| Leon | Architecture autour d’outils déclarés, contexte, mémoire et reprise. Sa branche 2.0 examinée reste une Developer Preview [4]. | Distinguer un outil présent, activé et réellement disponible. Conserver notre noyau de dossiers et de preuves. |
| Microsoft JARVIS / HuggingGPT | Recherche sur la planification et la coordination de modèles spécialisés [5]. | Référence d’orchestration, sans le traiter comme un atelier vocal déjà opérationnel. |
| Pipecat | Séparation de la conversation et de l’interface ; UIWorker peut utiliser JevClassifier [6]. Détection de parole et de fin de tour plus riche qu’un seuil de silence [7]. | Candidat retenu pour une évolution continue avec SmallWebRTC. M07 garde sa chaîne WAV locale ; aucun service Pipecat audio n’est annoncé actif. |
| LiveKit Agents | Gestion des tours, fausses interruptions et réglages de latence [8]. | Alternative à Pipecat. Choisir une seule pile de conversation, après essais sur la tour. |

Ce tableau exprime notre analyse d’intégration, pas un classement de performances. Les temps annoncés par les éditeurs ne sont pas des mesures de BOJ.ART.

## Jev : bon emplacement, limites précises

Jev intervient après le texte final et le contexte : il choisit parmi les intentions déclarées. Le logiciel vérifie ensuite cette proposition. La reconnaissance et la synthèse restent des moteurs séparés. Le Jev utilisé ici est le service hébergé de TypeSafe, appelé par une API ; les ordres locaux connus peuvent fonctionner sans lui [9].

La documentation TypeSafe confirme `jev-1.14.0`. Elle précise aussi que l’anglais est son meilleur terrain actuel : il faut évaluer les formulations françaises de l’atelier [9]. Nous conservons donc la confirmation des interprétations Jev. Une distribution concentrée et un score élevé ne prouvent pas que l’intention est correcte ; la confiance est calculée à partir des probabilités [10].

Une découverte utile est l’intégration officielle `pipecat.classifiers.typesafe.jev`. Le paquet Pipecat 1.15.0 a été téléchargé pour inspection, sans installation de la pile audio. Son SHA-256 correspond à celui publié sur PyPI [11]. Les modules Jev, UIWorker et SmallWebRTC y sont présents. Le constructeur JevClient expose notamment `model`, `timeout` et `max_retries`.

Attention aux valeurs par défaut : la documentation du client Pipecat indique Jev 1.13 et trois répétitions sur certaines réponses de saturation [12]. Une future connexion devra fixer explicitement le modèle et le budget de répétition. L’adaptateur M07 conserve son modèle 1.14 et l’absence de répétition automatique lorsqu’un résultat s’est perdu. Une API inspectée n’est pas encore une conversation exécutée.

La composition d’interface Jev de json-render est une autre fonction, encore expérimentale : l’application prépare les composants et les données, le modèle les agence [13]. Elle ne fabrique pas les données manquantes et ne dispense pas des contrôles d’action. M07 utilise une scène de trois vues définie par le logiciel ; aucune disposition générée librement n’est intégrée.

## La fluidité gagne d’abord à être cohérente

Deux défauts du parcours précédent ont été corrigés. Le contexte vocal est maintenant figé au début de l’écoute : un changement de dossier pendant la transcription entraîne un refus. Une réponse asynchrone ancienne ne peut plus nettoyer la nouvelle capture après une annulation suivie d’une reprise.

Une option termine maintenant la prise après une pause. Elle utilise l’énergie audio, avec une durée minimale de signal, une pause d’environ 1,1 seconde, un arrêt sans parole et un plafond de 15 secondes. C’est un mécanisme de fin de prise, sans compréhension sémantique. Une imprimante bruyante peut le perturber ; le bouton de fin manuelle demeure disponible. Il faut régler et mesurer cette fonction avec le vrai micro.

Une conversation naturelle demande davantage : annulation d’écho, distinction parole/bruit, fin de tour, interruption intentionnelle, reprise après fausse interruption et synchronisation du texte réellement entendu. Pipecat documente cette distinction [7] ; LiveKit documente notamment la reprise après certaines fausses interruptions [8]. Les ajouter sans recette pourrait aggraver la fluidité.

Les mesures M06 sont conservées : 66–98 ms pour la dernière série texte → reçu d’affichage au calme, 115–997 ms sous calcul CAO, et un pic de 1,4 seconde dans une autre passe. Elles excluent STT et Jev. M07 vérifie fonctionnellement l’arrêt sur pause et les trois vues ; il ne transforme pas ces chiffres en promesse de délai vocal sur le PC cible.

## Ce qui est préintégré et ce qui exige encore une connexion réelle

| Capacité | État du code | Condition restante |
|---|---|---|
| Texte → LangGraph → vues | Implémenté et testé | Installer le paquet sur la tour |
| Scène des trois vues | Implémentée, reçus distincts et reprise | Ouvrir/appairer les vues puis les placer sur les moniteurs |
| Capture et arrêt sur pause | Implémentés, signal synthétique testé | Micro réel et bruit à qualifier |
| Reconnaissance faster-whisper | Adaptateur local présent ; bibliothèque installée en développement | Poids du modèle et qualité française |
| Jev | Adaptateur présent, schémas et pannes testés avec doubles | Clé privée et évaluation réelle en français |
| Confirmation vocale | Reliée à la proposition visuelle courante | Qualifier le transcripteur réel |
| Réponse parlée | Code navigateur présent | Voix française locale et haut-parleurs |
| CAO | Création paramétrique existante, sur proposition confirmée dans le poste | Pas de nouvelle création vocale autonome dans M07 |
| Studio et contenus | Catalogue, briefs et brouillons existants | Pas de rendu externe ni publication connectés |
| Découpe et parc machines | Architecture décrite | Inventaire, profils, protocoles et essais réels |
| Conversation continue / mot d’éveil | Candidats documentés | Pile audio unique et recette matérielle |

L’objectif « aucun problème » devient un contrat vérifiable : pas de succès sans preuve, pas de répétition aveugle, pas de réponse périmée appliquée, sauvegarde et reprise. La fiabilité finale exige les essais sur la tour. L’enrichissement livré est du code, des sources et des données de reprise ; il ne constitue pas un réentraînement de mon modèle ni de Jev.

## Sources primaires

Consultées le 1 novembre 2026. Paraphrases ; aucune performance tierce reprise comme résultat de notre atelier.

1. https://www.home-assistant.io/voice_control/voice_remote_local_assistant/
2. https://www.home-assistant.io/integrations/wyoming/
3. https://openvoiceos.github.io/beta-technical-manual/
4. https://github.com/leon-ai/leon/blob/develop/README.md et https://github.com/leon-ai/leon/blob/develop/core/context/ARCHITECTURE.md
5. https://github.com/microsoft/JARVIS
6. https://docs.pipecat.ai/pipecat/learn/ui-worker
7. https://docs.pipecat.ai/pipecat/learn/speech-input
8. https://docs.livekit.io/agents/logic/turns/tuning/
9. https://docs.typesafe.ai/models
10. https://docs.typesafe.ai/confidence
11. https://pypi.org/project/pipecat-ai/1.15.0/
12. https://docs.pipecat.ai/api-reference/server/classifiers/jev
13. https://json-render.dev/docs/jev
