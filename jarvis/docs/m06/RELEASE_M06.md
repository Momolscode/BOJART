# M06 — commandes, orchestration et fluidité des vues

Base : M05 `2e0610fbe52b9d4a8d2f4ad14e7c251fadaee84b`. Branche : `improvement/m06-voice-orchestration-2026-10-31`. Publication GitHub non effectuée.

## Comportement livré

Dans `/tower`, « Montre les dossiers au centre » crée un tour identifié, traverse LangGraph, vérifie le contexte, distribue une commande persistante, puis affiche le reçu du navigateur après rendu. Les transcriptions utilisent la même chaîne. L'utilisateur peut interrompre une prise et écarter une transcription arrivée en retard. Un second onglet ne peut pas réserver le même microphone.

Le graphe utilise `route → guard → dispatch → receipt`, avec branche directe `guard → receipt` pour le refus, la clarification ou la confirmation requise. Les checkpoints et tours occupent des tables supplémentaires dans `missions.sqlite3`. Le fonctionnement sans dépendance LangGraph est explicitement signalé et préserve les règles locales. Les écritures de commande et les accusés ne conservent pas le verrou long d'un calcul CAO.

Jev dispose d'un adaptateur réel pour `jev-1.14.0`, désactivé par défaut, avec identifiants de choix bornés, contrôle des probabilités, timeout réseau, pause après erreur, absence de répétition automatique et marqueur durable avant appel. Les tests du contrat utilisent un double. Les choix Jev exigent actuellement une confirmation visuelle ; leur précision n'a pas été mesurée en conditions réelles.

La régie expose neuf intentions : modèle, sources, Studio, planning démonstratif, dossiers, contenus, base métier, conception et silence. La conception s'ouvre sur un dossier ; la création conserve son circuit de proposition/confirmation. Les nouvelles cartes ne prétendent pas générer un contenu ou commander une imprimante.

## Validation

Lire `docs/evidence/m06-2026-10-31/TESTS_SUMMARY.json` pour le compte final et l'environnement ; `TESTS_FINAL.log` conserve la sortie des suites. La recette Chromium M06 est dans `ACCEPTANCE_M06.json`. La régression M05 inclut treize contrôles navigateur, deux vrais modèles CAO, sauvegarde globale et deux générations de restauration.

Les douze mesures initiales vont de 63,3 à 88,1 ms ; une passe simultanée à d’autres tests présente un pic de 1 413 ms. La dernière passe au calme donne 66,1 à 98 ms. Six affichages pendant un vrai calcul CAO aboutissent avant sa fin, en 114,9 à 997,3 ms. Ces mesures excluent reconnaissance vocale et Jev. La dernière recette M06 comporte treize contrôles navigateur et un calcul CAO supplémentaire. La capture audio est testée avec un flux synthétique et un faux ASR, explicitement nommés dans les scripts et preuves. Le moteur faster-whisper 1.2.1 et CTranslate2 ont été importés dans l'environnement de développement ; les poids ne sont pas présents.

## Reprise et configuration

Suivre `INSTALLATION_M06.txt`. Les lanceurs existants sont préservés. L'option `--config` du serveur consolidé permet de choisir une configuration de voix/Ollama. `tools/m06_preflight.py` ne fait aucun appel réseau, n'active aucun microphone et n'affiche aucune clé. Après une restauration, les tours incomplets ne sont plus confirmables et les distributions antérieures ne sont pas relancées.

Avant une installation réelle : conserver une sauvegarde M05, installer dans un nouveau dossier de code et reprendre explicitement le dossier de données. Les mises à jour n'effacent pas les sources ni les archives historiques.

## Limites

Pas d'installation sur le PC cible, de microphone réel, de benchmark français, de mot d'éveil, de détection naturelle des interruptions, de Pipecat actif, de Jev en direct, de mapping physique des moniteurs, d'impression, de publication ou de paiement qualifiés. Le serveur reste local et mono-utilisateur. SQLite convient ici à cette portée, pas à une plateforme multi-utilisateurs. Les visites, sources documentaires et tests ne réentraînent pas le modèle et ne reconstituent pas le chat perdu.
