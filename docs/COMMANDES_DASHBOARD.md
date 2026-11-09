# Commandes de dashboard disponibles

Référence d'usage du routeur local Jarvis, 2 novembre 2026. La chaîne reçoit une phrase écrite ou transcrite. Le catalogue ci-dessous concerne uniquement les vues de l'application.

| Phrase | Vue demandée |
|---|---|
| Affiche le dashboard atelier | Planning démonstratif à gauche |
| Affiche le dashboard planning | Planning démonstratif à gauche |
| Affiche le dashboard dossiers | Dossiers au centre |
| Affiche le dashboard Studio | Catalogue Studio à droite |
| Affiche le dashboard contenus | Préparations éditoriales à droite |
| Affiche le dashboard conception | Poste CAO du dossier au centre |
| Affiche le dashboard base métier | Base documentaire au centre |
| Affiche les trois dashboards | Planning, dossiers et modèle sélectionné ou Studio |

Pour chaque nom de vue, « Montre » et « Ouvre » remplacent aussi « Affiche », et « tableau de bord » remplace « dashboard ». Les accents, la casse, la ponctuation simple et le préfixe « Jarvis » sont normalisés. Les formulations supplémentaires ne sont pas nécessairement reconnues. Une négation ou une action ajoutée n'est pas retirée de la demande.

« Affiche un des dashboards » demande de préciser lequel. « Affiche le modèle à droite » exige une sélection dans le dossier actif. La scène des trois vues reste incomplète tant que ses trois reçus ne sont pas arrivés. En cas de réponse perdue, reprendre la même référence ; un changement de dossier ou de contexte peut imposer une nouvelle demande.

« Prépare un Végéta 3D d'un mètre à répartir sur les imprimantes » reste une demande non raccordée au runtime vocal. Elle ne crée pas de modèle et ne distribue aucune impression. Le prototype de préparation et de répartition est accessible uniquement par les essais séparés décrits dans [Simulations d'atelier](SIMULATIONS_ATELIER.md). Il utilise un parc fictif ; le fichier 3D, les profils du parc, les découpes et les estimations du slicer restent à fournir pour un projet réel.

Cette référence décrit le comportement du code. Le micro, le rendu sur les moniteurs et les machines de l'atelier nécessitent leurs preuves de fonctionnement sur le poste. Les résultats datés et leur portée sont conservés dans [le rapport d'essais](evidence/workflows-2026-11-02/README.md).
