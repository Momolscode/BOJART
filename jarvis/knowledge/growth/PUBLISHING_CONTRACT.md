# Contrat de publication proposé — non connecté

Ce document n’installe pas une API de publication. Le code présent prépare et revalide les brouillons uniquement.

## Identité immuable
Clé interne de campagne ; identifiant œuvre ; révision des annotations ; SHA256 du rendu final ; compte autorisé (ID fournisseur ET réseau, pas seulement handle) ; marque Metricool ; texte ; tags ; miniature ; audio ; déclaration commerciale/synthétique ; réglages de confidentialité ; date et fuseau ; ensemble des règles revalidées.

## États distincts
`draft` → `needs_review` → `approved` → `scheduled` → `publishing` → `published_confirmed`.
Exceptions : `blocked`, `rejected`, `expired`, `provider_unknown`, `failed_confirmed`, `cancelled_confirmed`.
La présente version reste `review_required` et ne permet aucune transition vers un envoi.

## Avant activation
1. Lire les comptes autorisés, capacités et limitations réelles du fournisseur.
2. Vérifier les deux marques pour les deux TikTok et leurs ID distincts. Ne jamais supposer le nom du compte Instagram.
3. Contrôler fichier final, droits, détails commerciaux, divulgations et consentement de plateforme.
4. Montrer une prévisualisation de la publication exacte. Lier l’accord à son empreinte et à un créneau. Prévoir une politique de série, des limites et une expiration si le fournisseur le permet.
5. Enregistrer une intention unique avant envoi. Employer une clé idempotente seulement si le fournisseur la documente ; ne jamais inventer une garantie réseau.
6. Garder le reçu ; relire l’état. Une réponse perdue ne doit pas provoquer un nouvel envoi automatique.
7. Un ID de programmation n’est pas une preuve de publication. Conserver les états séparés.
8. Réconcilier avant toute reprise ; pas de scraping authentifié, contournement d’API ou cookie récupéré au hasard.

## Confidentialité et limites
Pas de noms de clients dans UTM, tags ou prompts externes sans nécessité/autorisation. Stockage des jetons hors du dépôt. Les Ads, commentaires et messages privés ne sont pas une extension implicite du consentement à publier un film. Le MCP Metricool ne permet pas la gestion de campagne Ads documentée au 31/10/2026.

## Recette future indispensable
Compte bac à sable lorsque disponible ; brouillon créé puis relu ; mauvaise cible refusée ; révocation de connexion ; réponse perdue ; changement de légende ; doublon ; file d’attente ; media inaccessible ; reçu existant retrouvé ; prévisualisation fidèle au texte final ; limites du réseau recontrôlées ; comptabilité et suppression des secrets. Aucun de ces scénarios fournisseur n’a été exécuté ici.
