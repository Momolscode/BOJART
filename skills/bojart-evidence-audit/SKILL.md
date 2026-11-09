---
name: bojart-evidence-audit
description: Auditer une révision de BOJART ou relire une correction Jarvis avec couverture par fichier, preuves reproductibles et passation. Utiliser pour les audits explicites du dépôt, du runtime et de sa réception.
---

# Audit de BOJART fondé sur les preuves

Lire `AGENTS.md`, les décisions utilisateur courantes et les instructions du sous-projet. Fixer la révision distante, la base locale et les modifications avant de conclure. Si le dépôt avance, examiner le delta ; ne pas attribuer au nouveau code les tests d’un ancien SHA.

Construire une table de couverture : chemin, SHA-256, lecture complète/partielle/inventaire/non lu, lecture actuelle ou antérieure aux octets identiques, tests associés et limite. L’inventaire des fichiers et une archive restaurée ne prouvent pas une analyse sémantique. Distinguer conversations originales, captures, résumés et textes générés ; compter les pages effectivement récupérées.

Pour Jarvis, examiner séparément mémoire documentaire, graphe d’intentions, CAO, Studio/Growth, voix, planning, interfaces, installation et sauvegardes. Utiliser `data/preinstallation/requirements.json` comme exigences proposées et `tool-registry.json` comme catalogue, sans convertir leur présence en intégration. Ne pas fusionner les branches d’archive au runtime.

Pour une demande transversale, appliquer aussi `references/transversal.md` : les sites, la création, les données métier et la préparation des connecteurs restent dans le périmètre même lorsqu’un défaut mémoire monopolise le travail. La réussite d’un correctif local ne clôt pas à elle seule cet audit.

Chaque constat doit donner déclencheur, résultat attendu/observé, portée, chemin/lignes, preuve et priorité. Faire un contre-exemple ou une reproduction isolée quand utile. Les tests propres au produit doivent échouer avant correction et réussir après. Une erreur de préparation Windows 1314 est une limite de test, pas la preuve d’un défaut dans le garde testé. Compter les cas uniques, pas les erreurs de teardown comme nouveaux tests.

Séparer quatre niveaux : décrit, codé, testé en environnement isolé, réceptionné sur cible. Les doubles ASR/Jev, les trois reçus navigateur et le HTTP 200 ne valident respectivement ni la voix réelle, ni les moniteurs physiques, ni la fabrication. Préserver l’authenticité artistique et les sources réelles des essais.

Les commandes locales utiles sont décrites dans `references/acceptance.md`. Lire leur code avant une première exécution. Effectuer les vérifications déjà autorisées et nécessaires ; demander une décision seulement pour une action qui change réellement le périmètre. Ne pas ajouter de nouveau serveur, achat ou publication pour rendre un audit plus impressionnant.

Terminer avec les correctifs, preuves exécutées, défauts encore ouverts, données absentes et prochain lot vérifiable. Remettre le contexte court et les références complètes pour une session neuve ; le prochain auditeur doit pouvoir contredire les conclusions.
