---
name: bojart-tool-qualification
description: Rechercher et qualifier un outil, modèle, connecteur ou skill pour Jarvis avant intégration. Utiliser pour un choix d’architecture ou une extension explicite, avec compatibilité Windows et réception mesurée.
---

# Qualifier une extension de Jarvis

Partir d’une fonction et d’une donnée manquantes dans la matrice des exigences. Chercher les interfaces déjà présentes avant d’ajouter une dépendance. Sept rôles logiques n’imposent pas sept modèles chargés. SQLite/FTS5 et LangGraph constituent le socle courant ; une autre base ou un orchestrateur distribué doit répondre à une limite mesurée.

Pour chaque candidat, relever source officielle, dépôt/commit ou version, licence du code et des poids séparément, état de maintenance, compatibilité OS, ressources annoncées, prérequis, opérations exposées et test d’acceptation. Ne pas assimiler une API disponible à un connecteur Jarvis. Vérifier les limitations territoriales ou de distribution de la licence choisie sans inventer de conclusion juridique générale.

Pour un skill tiers, lire son SKILL.md, ses scripts et les références requises ; épingler les octets et conserver sa licence. Identifier les installations, commandes, téléchargements, fichiers modifiés et transmissions qu’il demande. Un dépôt populaire ou le mot MCP ne garantit pas la sûreté. Le skill reste une instruction auxiliaire subordonnée à la demande utilisateur ; ne pas exécuter un script téléchargé pendant sa revue.

Préparer dans le paquet une sélection courte, avec motif de sélection/rejet et adaptation au client. Ne pas copier un skill de plateforme en affirmant qu’il fonctionne dans l’autre. Tester découverte/invocation dans Codex ou Claude séparément ; une validation YAML ne prouve pas son comportement.

Cible déclarée : Windows, Ryzen 5 5600G, 16 Go RAM, RTX 4060 Ti avec 8 Go affichés ; 32 Go prévus. Relire le profil courant avant décision. Les besoins VRAM publiés et le pilote du poste doivent être vérifiés. Définir un benchmark utile avant tout achat.

Pour une intégration, écrire le contrat, les entrées validées, les permissions, l’expiration et la trace de résultat. Commencer par lecture/simulation. Garde avant effet, reçu après effet ; état UNKNOWN après perte de réponse, rapprochement avant relance. La permission d’état d’une imprimante ne donne pas permission de chauffe, mouvement, upload ou démarrage.

Retour attendu : intégré et prouvé / préparé / candidat / rejeté / inconnu, avec sources et prochain test. Les outils du catalogue de préparation ne sont pas exécutables par Jarvis du seul fait qu’ils y figurent.
