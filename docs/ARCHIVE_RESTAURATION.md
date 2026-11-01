# Restauration de l'archive complète

Le dossier préparé BOJART/Marwin a été assemblé en ZIP avec empreintes SHA-256. Il est destiné à une **restauration dans un dépôt privé** ou un stockage privé auquel les personnes concernées sont autorisées.

## Procédure sûre
1. Confirmer que `Momolscode/BOJART` est privé.
2. Inspecter les anciens PDF, captures, médias et JSON pour données personnelles ou informations couvertes par des droits de tiers.
3. Extraire l'archive dans un dossier de staging séparé.
4. Exécuter le vérificateur de manifeste avant transfert.
5. Importer documents, médias et rendus en commits distincts, sans écraser les fichiers existants.
6. Pour les gros médias, prévoir Git LFS ou un stockage d'objets privé ; garder les références et hashes dans le dépôt.
7. Vérifier les chemins et SHA-256 réellement présents sur GitHub.
8. Les vidéos Higgsfield non encore téléchargées doivent être récupérées indépendamment et comparées au registre des jobs.

## Interdit
Ne jamais pousser les secrets, `.env`, conversations privées non revues, documents personnels, fichiers clients ou œuvres sans droits de publication dans un dépôt public. Un `.gitignore` ne protège pas un fichier qui a déjà été commité.
