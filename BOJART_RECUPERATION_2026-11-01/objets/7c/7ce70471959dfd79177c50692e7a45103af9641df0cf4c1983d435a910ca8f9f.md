# Reprise BOJ.ART / Jarvis — instructions pour l’intégrateur

Commencer par README.md, CONTEXTE_LISIBLE.md et docs/AMELIORATIONS_CONSOLIDEES.md.

## Contraintes à préserver
- Projet indépendant d’UNUM et M-Tek. Budget tour 3 000–5 000 €, réemploi avant achat.
- 7–8 imprimantes envisagées, mais parc et PC inconnus. Trois écrans. Voix locale souhaitée.
- Propriétaire souhaite une mise en place prise en charge, sans listes de commandes à lui faire recopier.
- Les deux comptes sont @boj.art et @boj.art3d. Aucune statistique actuelle connectée dans ce module.
- La sculpture originale est la référence de personnage. Les concepts générés ne prouvent pas son identité.

## Avant installation
Récupérer les sources actuelles, sauvegardes et fichiers associés des sites existants. Ne pas déployer ce module isolé par-dessus une application sans examiner son schéma et ses migrations. Ne pas demander une nouvelle fois le budget ou confondre une absence d’accès avec une absence de matériel.

Auditer le PC après autorisation explicite. Ne pas collecter les secrets ou parcourir les dossiers privés sans périmètre. Proposer une installation par environnement isolé et conserver un plan de retour arrière. Ne pas désactiver le pare-feu, les politiques d’exécution ou les protections des machines.

## Mode d’exécution
La commande écrite supportée est une grammaire limitée, pas un LLM. Une sortie IA future doit passer par BaseSpec et Store, jamais être exécutée comme Python libre. Aucun endpoint machine dans cette version. Les simulations ne prouvent aucune fabrication réelle.

Le navigateur de préparation bloquait localhost. Les tests d’interface utilisaient un transport simulé ; les tests HTTP étaient séparés. Exécuter `tests/test_browser.py` sur la tour avec un navigateur autorisé. Le chemin Chromium est à adapter dans le test ; l’application elle-même fonctionne dans un navigateur courant.

## Livraison suivante attendue
1. Inventaire réel PC et ressources.
2. Recette du module local depuis l’interface, avec modèles 180 et 240 mm.
3. Sauvegarde restaurée dans un nouveau dossier et fichiers comparés.
4. Interprétation locale générale sous contrat, évaluée en français, voix ensuite.
5. Un seul connecteur qualifié à la fois ; aucun départ automatique si résultat précédent inconnu.

Ne pas déclarer « installé », « connecté », « imprimé », « publié » ou « validé artistiquement » sur la seule base d’un rapport, d’un statut fournisseur ou d’un prompt. Conserver la preuve et sa portée. Les appels payants et publications requièrent leur propre autorisation ; aucune des confirmations antérieures de crédits n’est un budget illimité.
