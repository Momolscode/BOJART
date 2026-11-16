# Reconstruire les sources de production R03

Les cinq médias requis par `productions/le-dernier-geste/ASSETS.json` correspondent à des objets de la collecte de récupération. Le rapprochement utilise leur SHA-256 et leur taille, sans choisir un fichier au nom ressemblant. L'outil prépare une copie de travail hors du dépôt public et laisse les originaux en place.

| Source et rôle conservé | Partie d'archive | Octets |
|---|---:|---:|
| Vidéo authentique BOJ.ART | 2 | 9 310 485 |
| TEST19, ancien essai provisoire pour G2 | 1 | 2 239 592 |
| Composition V21 | 3 | 485 805 |
| Macro de pinceau G1 | 3 | 2 077 736 |
| Préécoute du Foley de pinceau | 1 | 163 344 |

Total : **14 276 962 octets**. La recette actuelle, ses paramètres et ses limites sont copiés depuis le dépôt courant. Aucun programme d'une archive n'est exécuté. TEST19 conserve son rôle historique ; cette reconstruction ne fournit pas le modèle, le rig ou le plan G2 définitif.

## Préparer le dossier

Depuis la racine du dépôt, Git et Python 3.12 disponibles :

1. Si la collecte n'est pas encore restaurée, lancer le restaurateur existant. Choisir une destination neuve ; les trois commits sont épinglés et les octets vérifiés.

   ```bash
   python tools/restore_recovery_2026_11_01.py --fetch --destination ../BOJART_RECUPERE
   ```

2. Examiner le rapprochement sans copie, téléchargement ou exécution :

   ```bash
   python tools/prepare_production.py
   ```

3. Préparer un nouveau dossier externe. Son parent doit déjà exister ; un dossier existant est refusé.

   ```bash
   python tools/prepare_production.py --collection ../BOJART_RECUPERE/BOJART_RECUPERATION_2026-11-01 --destination ../BOJART_R03_TRAVAIL
   ```

4. Le dossier `../BOJART_R03_TRAVAIL/le-dernier-geste/` contient les cinq médias aux chemins attendus, les recettes actuelles et `RECOVERY_RECEIPT.json`. Contrôle indépendant :

   ```bash
   python ../BOJART_R03_TRAVAIL/le-dernier-geste/verify_assets.py
   ```

Les étapes 2 et 3 fonctionnent sans réseau. L'étape 3 recalcule les empreintes des sources et des copies, puis publie le dossier complet. Une erreur laisse la destination finale absente ; un dossier apparu entre-temps est préservé. Les liens symboliques et les collisions de chemins, y compris sous Windows, sont refusés.

## États et preuves

Le plan d'orchestration après chaque poussée affiche `catalogued` lorsque la recette correspond au catalogue. Ce statut ne signifie pas que les octets viennent d'être téléchargés ou décodés. Le reçu de préparation indique `copied_verified` seulement après vérification de tous les médias et fichiers de recette. Les entrées absentes du catalogue restent visibles et bloquent la préparation.

Les entrées sources et les recettes sont liées au manifeste du dépôt, puis aux empreintes de l'audit. Un manifeste périmé ou un fichier modifié depuis l'audit fait échouer le rapprochement. Les anciens indicateurs de transfert du catalogue restent des observations historiques ; les commits d'archive du restaurateur et la comparaison effective des octets définissent la provenance utilisée ici.

La préparation ne crée aucun rendu, n'appelle aucun fournisseur et n'accorde aucune validation artistique. Les cinq avertissements « média non matérialisé » peuvent rester présents dans l'audit du dépôt public : la copie de travail est volontairement externe. Le rendu, l'écoute, les droits de diffusion et le G2 final ont leurs propres contrôles.

Recette exécutée le 2 novembre 2026 : [preuve et portée](../evidence/production-recovery-2026-11-02.json). Guide des archives : [restaurer la collecte](../ETAT_ARCHIVES_2026-11-01.md).
