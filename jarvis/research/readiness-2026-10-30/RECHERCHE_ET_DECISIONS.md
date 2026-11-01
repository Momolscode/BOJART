# BOJ.ART / JARVIS — recherches orientées exploitation
30 octobre 2026 · extension au dépôt préparé pour Momolscode

## Conclusion
La meilleure avancée n’est pas un nouveau « grand Jarvis » à installer : c’est la qualification de quelques parcours fiables, dans le même environnement. La priorité reste une voix qui désigne le bon dossier, un modèle réel rendu sur le bon écran, puis une production et un contenu suivis jusqu’à leur résultat.

## Corrections immédiatement effectuées dans cette copie locale
Le paquet de publication choisi pour Momolscode contenait encore dans son bundle des documents annonçant une destination inconnue et un script autorisant aussi eaglemic. START_HERE, DECISIONS et la procédure de transfert sont actualisés. Le script du dépôt refuse maintenant toute destination différente de Momolscode/bojart-jarvis, y compris un autre projet du même compte. Le lanceur extérieur du paquet Momolscode était déjà restreint ; le défaut concernait la cohérence du dépôt récupéré.

Les anciens bilans et archives ne sont pas réécrits : ils restent des observations datées. Le manifeste de la nouvelle copie est actualisé séparément. Aucune tentative de publication n’a été faite pendant cette recherche.

## Correction supplémentaire : durée de vie des connexions SQLite
La réexécution des tests a émis des ResourceWarning pour des connexions non fermées. La documentation Python confirme que `with connection:` gère commit/rollback mais ne ferme pas la connexion [S13]. Dans la copie locale, `Store.connect`, `DisplayProposals.db` et la cible de sauvegarde ferment désormais explicitement leurs ressources en conservant commit et rollback. Les recettes historiques exportées restent inchangées. Des tests vérifient les connexions fermées, le commit, le rollback, les lectures répétées et la sauvegarde. Cette correction ne constitue pas une validation de charge 24/7 ni un audit exhaustif des ressources.

## Deux limites techniques confirmées par lecture
1. `apps/jarvis/app/display_contracts.py` ne permet encore que le dossier `BOJ-PILOTE-001` et des phrases connues. L’interface locale n’est donc pas une régie multi-projet complète. À généraliser avec tests d’isolation, pas en remplaçant simplement un nom.
2. `apps/jarvis/app/consolidated_workbench.py` indique explicitement `screen_pairing=not_connected`, `voice_session=not_connected`, `jev=not_connected`, `langgraph=not_installed`, `physical_commands=false`. Ces statuts restent honnêtes et inchangés.

## 1. Faire réagir les écrans sans attendre un long raisonnement
Pipecat fournit une liaison UI bidirectionnelle et des exemples de progression de tâches [S01–S02]. Nous retenons les commandes applicatives typées plutôt qu’un robot qui clique librement. Proposition BOJ.ART : accusés « reçu », « chargé », « rendu », horodatés ; sélection et révision liées au tour de parole ; pas de confirmation orale d’un affichage absent. Les commandes simples restent locales. Jev n’est sollicité que pour une décision réellement ambiguë [S08].

Recette : « affiche le modèle à droite », correction immédiate, écran débranché, résultat tardif. Mesurer latence, mauvaise cible et blocage, puis vérifier en charge réelle. Rien de cela n’est annoncé comme installé.

## 2. Du fichier isolé au dossier de fabrication
La spécification 3MF décrit unités, composants et transformations ; l’extension Production permet d’identifier les pièces [S03–S04, S12]. À utiliser lorsque chaque maillon est compatible, tout en gardant CAO native/STEP, projet slicer et manifeste. Le STL reste possible avec une unité explicitement attachée au dossier.

Un 3MF n’est ni une preuve d’imprimabilité, ni un format universel de paramètres de tous les slicers, ni la conservation de l’historique paramétrique. Tester un aller-retour avec dimensions, IDs et assemblage. Associer ensuite recette machine/matière, supports, lavage/cure, raccords, contrôle et coût.

## 3. Éviter de jeter un plateau FDM entier
Klipper documente l’exclusion d’un objet avec configuration et G-code adaptés [S05]. Proposition conditionnelle : laisser l’opérateur sélectionner la pièce défaillante et poursuivre les autres seulement si les conditions physiques le permettent. Une pièce décollée, des débris ou des objets en interaction peuvent rendre la poursuite dangereuse. La résine ne reçoit aucune promesse équivalente sans interface spécifique qualifiée.

## 4. Mesurer la capacité réelle de chaque connecteur
Un outil annoncé dans un catalogue MCP n’est pas nécessairement qualifié pour notre atelier. Le protocole décrit outils et schémas ; les annotations restent dépendantes de leur source [S10–S11]. Construire une fiche par adaptateur : version, auth, opérations, preuve de lecture, preuve d’effet, arrêt/récupération, état frais. Un connecteur seulement lisible reste explicitement en lecture seule.

## 5. Qualifier le Jarvis sur des situations BOJ.ART
Les 36 cas français joints sont des spécifications : correction 24/18 cm, sélection périmée, interruption de voix sans arrêt machine, réponse fournisseur perdue, source média remplacée, attribution commerciale incomplète, saturation GPU et restauration. Ils devront être joués sur le PC ; aucune performance IA n’est mesurée ici. Les structures JSON [S07] servent au contrat, pas à noter la vérité du résultat.

Un bon score moyen ne compense pas une action sur la mauvaise machine. Séparer précision d’intention, cible, paramètres, refus nécessaires, temps de réponse et effet réel. Conserver les versions exactes des modèles et des outils.

## 6. Le Studio doit apprendre de nos essais sans réutiliser leurs erreurs
Conserver trois identités : marque BOJ.ART, œuvre réelle, version du plan. Le short bordeaux appartient à cette figurine, pas à tous les héros futurs. Avant chaque génération : référence intègre, bonne œuvre, rôle média correct, catalogue fournisseur revérifié, durée et format mesurés, devis et autorisation liés à la requête. En cas d’incertitude réseau, récupérer le statut avant de générer à nouveau.

Une reprise LangGraph peut rejouer un nœud [S09] : le reçu fournisseur et l’idempotence restent nécessaires. Un refus de droits fournisseur n’est pas traité comme une panne à contourner ; conserver le refus et utiliser une autre œuvre autorisée lorsque nécessaire.

## 7. Garder la tour réactive
Ollama expose le maintien en mémoire et la gestion de concurrence [S06]. Réserver les réponses courtes et l’interface ; mettre vidéo, génération 3D et indexation en file. L’arrêt de la voix n’annule pas un outil matériel. Désactiver explicitement les fonctions cloud lorsque le mode local est demandé ; aucun fallback caché.

## 8. Vendre ce que l’atelier peut livrer
Règle de conception BOJ.ART : une acceptation porte sur un devis versionné ; la publicité respecte capacité de finition et plafond de dépenses. Les cotes, la quantité ou la finition changées entraînent une étude d’impact. Le rendu spectaculaire ne promet pas une pièce techniquement prête. Les données privées restent à part des affichages publics.

## Priorités
P0 : contexte cohérent, sauvegardes restaurables, capabilities vérifiées, identité des dossiers.
P1 : multi-projet contrôlé, appairage des écrans, voix réelle et benchmark commun, essais 3MF.
P2 : FDM et résine pilotes, exclusion conditionnelle, Studio reproductible et boucle commerciale.

## Périmètre de cette livraison
Recherche documentaire et correction ciblée de destination dans une copie locale. Pas de mise à jour des sites, pas de push, pas de PC distant contacté, pas d’impression, pas de téléchargement de modèles et pas de crédits engagés. Aucun système n’est garanti « sans aucun problème » ; les procédures visent à détecter, limiter et reprendre les échecs.

## Références

- **S01 — Pipecat — Controlling the UI** : https://docs.pipecat.ai/pipecat/learn/ui-worker
  Portée : Canal bidirectionnel entre agent vocal et interface ; remontée d’état et commandes applicatives.

- **S02 — Pipecat — exemple async-tasks** : https://github.com/pipecat-ai/pipecat/blob/main/examples/multi-worker/ui-worker/async-tasks/README.md
  Portée : Exemple de travaux parallèles et de progression dans une interface ; ce n’est pas un connecteur BOJ.ART.

- **S03 — 3MF Consortium — Specifications** : https://3mf.io/spec/
  Portée : Spécification et extensions, notamment Production et Materials ; compatibilité à vérifier par logiciel.

- **S04 — 3MF Consortium — Core specification** : https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md
  Portée : Le modèle comporte notamment unités, ressources, composants et transformations ; conserver aussi la source paramétrique.

- **S05 — Klipper — Exclude Objects** : https://www.klipper3d.org/Exclude_Object.html
  Portée : Exclusion d’un objet pendant une impression avec configuration et marqueurs appropriés ; ne vaut pas pour tout firmware ni pour la résine.

- **S06 — Ollama — FAQ** : https://docs.ollama.com/faq
  Portée : Chargement et durée de maintien des modèles, concurrence, file d’attente et désactivation des fonctions cloud.

- **S07 — Ollama — Structured outputs** : https://docs.ollama.com/capabilities/structured-outputs
  Portée : Réponses contraintes par schéma JSON ; la conformité du format n’établit pas la justesse de la décision.

- **S08 — TypeSafe — Models** : https://docs.typesafe.ai/models
  Portée : Jev est un décideur typé sur état textuel ; pas un moteur audio/vidéo. Versions et capacités à vérifier avant intégration.

- **S09 — LangGraph — Interrupts** : https://docs.langchain.com/oss/python/langgraph/interrupts
  Portée : Pause et reprise avec persistance ; les effets de bord doivent tenir compte de la réexécution de nœuds.

- **S10 — MCP — Tools specification** : https://modelcontextprotocol.io/specification/2025-11-25/server/tools
  Portée : Découverte d’outils et schémas ; les annotations ne constituent pas à elles seules une autorisation d’exécuter.

- **S11 — MCP — Tool annotations as risk vocabulary** : https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/
  Portée : Les annotations sont des indices de risque dont l’usage dépend de la confiance dans le serveur.

- **S12 — 3MF Production Extension** : https://github.com/3MFConsortium/spec_production/blob/master/3MF%20Production%20Extension.md
  Portée : Identifiants de pièces et ressources de production ; tester la conservation à l’aller-retour.

- **S13 — Python sqlite3** : https://docs.python.org/3/library/sqlite3.html#how-to-use-the-connection-context-manager
  Portée : fermeture de connexion distincte de la transaction.
