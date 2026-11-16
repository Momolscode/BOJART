# Raccordement prévu à Mission 03

## Constat de reprise
La documentation et l’inventaire de l’archive Mission 03 ont été lus dans cette livraison. Elle distingue déjà médias réels/concepts/générations, références et versions. La bibliothèque métier reprend cette séparation pour la fabrication : documentation générale, instructions exactes, recette qualifiée, état actuel.

## Interface proposée
Importer `KnowledgeBase` depuis `app/base_metier.py`. `search()` renvoie les fiches et sources, leur portée et la nécessité de relecture. Fournir ce paquet à l’agent avant formulation d’un conseil. Une réponse finale doit conserver les références et les inconnues.

## Contrat de lecture
`query`, `domain`, `limit`, `as_of` -> fiches documentaires + URL sources + portée + avertissements. `allowed_to_execute` reste toujours false.

## Pas d’intégration déployée revendiquée
Aucun endpoint n’a été ajouté à Mission 03 ; aucune archive historique écrasée. Le raccordement au serveur local, au RAG multimodal et à son interface sera une étape distincte avec ses tests d’authentification, de session et de charge.

## Priorité de l’information
Les faits généraux éclairent une décision. Les réglages doivent venir des notices du matériel/SKU exacts et d’une recette validée dans leurs limites. Une contradiction de sécurité bloque la décision, elle n’est pas tranchée par simple similarité sémantique. L’état machine et le stock viennent d’observations actuelles séparées.

## À ne pas recopier
Un profil d’une machine voisine, un cycle Form Cure V1 vers une autre unité UV, une graisse pour tiges vers des rails différents, une licence de STL vers les droits du personnage, ou un prix dérivé sans coût complet.

## Données à recueillir automatiquement lorsque la tour sera accessible
Commencer par inventaire logiciel/matériel en lecture seule dans le périmètre autorisé. Ne pas examiner tous les disques personnels. Les notices, FDS et profils seront reliés aux identifiants exacts, puis les coupons et temps constatés compléteront la base. La collecte ne peut pas inventer les observations physiques absentes.
