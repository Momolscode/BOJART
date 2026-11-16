# M07 — une commande pour composer trois vues

Base : M06 `d6a1ddb3f823717df71c85fcd44b583fe05b9e84`. Branche `improvement/m07-voice-scenes-2026-11-01`.

## Résultat

« Ouvre la tour de contrôle » crée un plan visuel conservé, composé de trois demandes distinctes. Chaque vue garde son reçu. Une réponse perdue ou une distribution partielle reprend les mêmes références. Le modèle à droite doit être explicitement sélectionné ; sinon le Studio apparaît. Le planning reste démonstratif.

Le choix de Jev peut être confirmé ou annulé par une phrase vocale explicite liée à la proposition courante. L’option de fin de prise sur pause évite le second clic quand le signal s’y prête. Le contexte est figé avant l’écoute. Les traitements tardifs ne peuvent plus annuler la nouvelle capture ou lui imposer un résultat périmé.

Le graphe LangGraph reste volontairement petit : `route`, `guard`, `dispatch`, `receipt`. Les deux sorties de guard sont déclarées explicitement. Son export normalisé est fourni avec le JSON du graphe réel. Le schéma global inclut aussi la capture, les vues et les fonctions encore à raccorder.

## Validation

Voir `docs/evidence/m07-2026-11-01/TESTS_SUMMARY.json` et les journaux. Les 22 nouveaux contrats M07 couvrent notamment les trois reçus, la reprise partielle, la restauration, la migration de schéma M06 et les confirmations vocales mal ciblées ou périmées. Sept tests de signal vérifient la détection de pause et ses bornes. La recette Chromium vérifie les parcours vocaux avec un signal synthétique et des doubles ASR/Jev identifiés ; la régression M05 vérifie deux calculs CAO réels et les restaurations.

Les preuves distinguent capture, reconnaissance réelle, service Jev, navigateur et matériel. Aucun test sur microphone physique, aucun appel Jev réel ni mapping des moniteurs n’est revendiqué. Les mesures de latence M06 demeurent historiques, avec leur pic conservé ; elles ne constituent pas une mesure vocale de M07.

## Compatibilité et conservation

Deux colonnes sont ajoutées à la table des tours existante : le plan visuel et l’origine de l’approbation. Aucune sixième base n’est introduite. Les sauvegardes globales couvrent ces données et les checkpoints. Les anciennes commandes simples restent consultables. Les archives de versions précédentes sont préservées.

Les clés de session du navigateur et le dossier de données `mission05` gardent leur nom pour reprendre les tentatives et données existantes. Les en-têtes actuels de la régie indiquent M07. Aucun push GitHub ni déploiement sur la tour n’est attesté par cette livraison.

## Conditions avant usage réel

Suivre `INSTALLATION_ET_REPRISE.txt` pour les dépendances, poids STT, clé Jev facultative, permissions micro et trois vues. Le bruit et les pauses doivent être évalués sur place. La création CAO conserve le circuit du poste dédié. La découpe, les imprimantes, le rendu vidéo externe et la publication restent à raccorder. La conversation continue avec Pipecat est une évolution documentée, pas un service actif.
