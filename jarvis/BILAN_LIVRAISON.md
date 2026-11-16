# BOJ.ART — bilan de consolidation

**Publication GitHub non effectuée.** Un dépôt Git local, les sources consolidées et un coffre des originaux ont été préparés. Destination privée à choisir entre les deux comptes liés ; la session présente ne dispose pas d'une commande d'écriture GitHub ou d'un CLI authentifié. Le PC distant est hors ligne.

## Ce qui est conservé
81 chemins de fichiers joints, correspondant à 75 contenus uniques, tous restaurés et comparés par SHA-256. Les 12 archives ZIP historiques restent intactes dans le coffre. Les fichiers présents dans les packs sont également déployés en sources lisibles selon leur provenance. Cinq manifestes historiques, représentant 222 entrées, ont été comparés à l'import initial : zéro écart. Une copie indépendante du pack reste nécessaire ; GitHub ne constitue pas une garantie absolue contre toute perte.

## Ce qui est amélioré
- La bibliothèque métier est reliée au même serveur local que le dialogue et le Studio.
- Une interface permet sa recherche textuelle et affiche les sources.
- Des propositions de commandes d'affichage relient dossier, révision, tour de parole et modèle contrôlé.
- Les répétitions retrouvent la proposition d'origine ; les résultats périmés sont identifiés.
- Jev n'est pas utilisé pour les ordres connus, n'est pas confondu avec la voix et ne donne pas de permission machine.
- La mémoire de reprise sépare demandes utilisateur, fichiers présents, décisions, prototypes, hypothèses et lacunes.
- Le transfert GitHub est préparé pour un dépôt privé, une branche de récupération, un tag et une Release vérifiée par retéléchargement, sans écraser l'historique distant.

## Preuves de cette session
59 nouveaux tests de consolidation/préservation, 242 tests de non-régression des Missions 01–03, 40 tests métier et 22 tests planning : **363 tests réussis**, plus cinq sous-tests pytest. Les rapports bruts sont dans `proofs/current/`. Le rapport de 38 tests y est un sous-ensemble exécuté auparavant, non additionné.

La restauration des originaux est testée. La restauration du bundle est vérifiée séparément dans le rapport externe de livraison, pour éviter une référence circulaire entre le hash du bundle et son contenu. Les empreintes sont des contrôles d'intégrité, pas une signature cryptographique d'éditeur.

## Ce qui n'est pas récupéré ou raccordé
Sources complètes V11 des sites hébergés et ancien historique Git ; base commerciale D1 ; rushes non montés ; bibliothèque complète ; export intégral du chat ; fichiers et télémétrie du PC cible. La liste détaillée est dans `preservation/COVERAGE.md`.

Microphone réel, LLM local, Jev, LangGraph, imprimantes, comptes sociaux et trois moniteurs appairés restent à intégrer/qualifier. Les nouvelles propositions d'affichage n'exécutent aucune commande et n'affirment pas qu'un écran l'a chargée. Aucun site ni appareil n'a été modifié pendant cette livraison.

## Pour reprendre
Lire `context/START_HERE.md`, `context/HANDOFF_CLAUDE.md`, puis `docs/CONSOLIDATION.md`. Vérifier le dépôt avant de le modifier. Utiliser un nouvel état local, jamais un écrasement des anciennes bases. Le code ne constitue pas encore un installateur plug-and-play final.
