# Procédure actuelle

Destination : **Momolscode/BOJART**, publique. Suivre `../../docs/GITHUB_WORKFLOW.md`. L’ancien script est conservé sous `tools/legacy_publish_github.py` pour ses tests historiques, pas comme lanceur actuel.

## Document historique conservé

# Publication privée et reprise — procédure de l'intégrateur

## Situation
La destination a été choisie : **`Momolscode/bojart-jarvis`, privé**. Le paquet précédent n’avait pas été poussé et cette recherche n’a réalisé aucun transfert GitHub. Les anciens constats d’accès et de PC hors ligne restent des observations datées, pas des contrôles actuels. Une session CLI autorisée est nécessaire pour publier.

## Livrables complémentaires
- **Bundle Git** : historique créé ici, code, guides, contexte, provenance, tests. Ne contient pas l'ancien historique Git des sites.
- **Coffre ZIP** : les octets exacts des 81 chemins de fichiers joints, dont 12 ZIP historiques ; dédupliqués en 75 objets.
- **Manifestes** : tailles et empreintes. Ils détectent une modification, mais ne prouvent pas l'identité de l'auteur et ne remplacent pas une sauvegarde indépendante.

## Exécution par Claude / intégrateur autorisé
Sur la machine autorisée, Git et le CLI `gh` doivent déjà être disponibles. L'authentification se fait par leur interface habituelle, jamais en collant un token dans le chat. Ne pas utiliser un token ancien visible dans des historiques de conversation.

Le script livré `PUBLIER_GITHUB.py` prend `--repo Momolscode/bojart-jarvis --delivery CHEMIN` et affiche seulement son plan par défaut. L'option `--execute` autorise les écritures ; ajouter `--create-private` seulement pour créer une destination privée explicitement choisie. Le script refuse désormais les autres comptes et les autres dépôts, conformément à la destination approuvée. Aucune publication n'est lancée simplement en ouvrant ou téléchargeant le pack.

Le script exige une session `gh` correspondant au propriétaire choisi, contrôle la visibilité privée, vérifie les fichiers, clone le bundle, publie une branche de récupération et son tag sans force-push, conserve les branches existantes, crée une Release en brouillon, joint les archives, retélécharge chaque pièce et compare les empreintes avant de finaliser la Release. Pas d'écrasement des pièces existantes. En cas de conflit, il s'arrête pour examen. Il ne crée pas de GitHub Pages et ne déploie pas les sites.

La publication est considérée réussie uniquement si `delivery_result.json` annonce `pushed_and_redownload_verified`, avec le dépôt et le commit attendus. Le fichier n'existe pas dans cette livraison, puisque le push n'a pas été réalisé.

## Après publication
Conserver aussi le pack sur un support indépendant. Un clone Git ne récupère pas à lui seul les pièces jointes de la Release. Copier le coffre et son manifeste. Définir ensuite la stratégie de conservation des futurs rushes, données commerciales et modèles volumineux (stockage dédié ou LFS selon budget et quotas), puis tester leur restauration.

## Reprise locale sans GitHub
`git clone BOJART_JARVIS_2026-10-30.bundle bojart-jarvis` restaure le dépôt. Exécuter `python tools/verify_repository.py` depuis le clone. `RESTAURER_ORIGINAUX.py COFFRE.zip --restore NOUVEAU_DOSSIER` vérifie puis restitue les originaux dans un dossier qui ne doit pas exister. Certains chemins d'alias sont longs : préférer un répertoire de restauration court sous Windows, ou activer la prise en charge des chemins longs selon la politique du poste.

## Confidentialité
Les secrets et la base commerciale du site n'ont pas été récupérés ici et ne doivent pas être committés. Un dépôt privé réduit l'exposition mais ne justifie pas d'y stocker mots de passe, API keys ou informations clients. Les futurs exports commerciaux nécessitent une sauvegarde chiffrée distincte.

## Ajout recherche et contexte
Le correctif livré séparément est destiné à une copie de travail du dépôt, après restauration du bundle de base. Il ne réécrit pas ce bundle ni le coffre historique. Un nouveau commit et un nouvel export doivent être produits pour inclure ces changements dans une future publication ; ne pas modifier silencieusement les empreintes du paquet historique.
