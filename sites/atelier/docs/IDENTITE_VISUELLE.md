# BOJ.ART — direction visuelle V.01

État du 18 octobre 2026. Ce document définit la direction proposée pour les prochains contenus et la tour de contrôle. Les références sont les publications originales ; les règles nouvelles ci-dessous sont des choix de conception. Elles ne prétendent pas décrire une charte déjà approuvée par l’artiste.

## Références et noyau de la signature

L’édit de référence relie deux publications du même projet Baki : [présentation de l’œuvre, UV et emblème](https://www.tiktok.com/@boj.art/video/7467517355535404310) et [mise en peinture, partie 2](https://www.tiktok.com/@boj.art/video/7464268707989114134). Les sources, coupes, dimensions et empreintes se trouvent dans `dist/assets/brand-film-sources.json` ; les images de référence et le master sont conservés à côté.

La proposition prend appui sur quatre éléments visibles dans ces sources : le relief de la pièce, le geste du pinceau, la présence de l’œuvre entière et l’emblème manga blanc et rouge. La lumière UV appartient à un plan particulier ; elle ne devient pas un filtre à appliquer à toutes les œuvres. Les variantes historiques de la marque restent dans l’archive.

Le nom courant s’écrit **BOJ.ART**. L’emblème original reste une image de référence intacte ; son lettrage n’est pas redessiné avec la police des contrôles.

## Une grammaire réutilisable

| Moment | Fonction | Prise de vue à rechercher | Habillage proposé |
|---|---|---|---|
| Détail | Donner envie de regarder | Matière, visage, gravure ou mécanisme ; point précis et lumière lisible. | Accroche courte, entrée franche, texte hors de la zone utile. |
| Geste | Montrer le savoir-faire | Main, outil, peinture, assemblage ou mesure ; garder le contact outil/pièce visible. | Titres courts et repères discrets ; conserver le son réel lorsqu’il est exploitable. |
| Œuvre | Faire comprendre la pièce | Ensemble avec socle, volume ou prototype en fonction ; mouvement de caméra maîtrisé. | Laisser respirer le plan. Donner une échelle ou une dimension réelle quand elle est connue. |
| Emblème | Rendre la série reconnaissable | Emblème original, sur un espace propre. | Une fin stable ; appel à l’action distinct selon la disponibilité réelle de la pièce. |

Les quatre moments forment un vocabulaire. Chaque film choisit leur durée et peut en changer l’ordre si l’histoire le justifie. Une séquence ne doit pas laisser croire que des étapes de projets différents appartiennent à la même fabrication.

Pour les futures prises, enregistrer une vue entière stable, un détail, le geste et un mouvement autour de la pièce. Garder une marge autour du socle, des pointes et des outils. Prévoir quelques secondes avant et après l’action pour permettre une coupe. Stabiliser l’exposition et la balance des blancs au sein d’une séquence ; comparer le rendu de la peinture à la pièce réelle. Un cadre propre peut rester un vrai atelier, avec ses outils et sa matière.

## Palette et mouvement

L’interface et les marges du film utilisent le charbon `#09090D`, l’ivoire `#F4F0ED` et le carmin `#F13A54`. Les boutons principaux utilisent une variante carmin plus sombre pour la lisibilité du texte. Les couleurs des œuvres restent indépendantes de cette palette. Barlow Condensed porte les titres ; Manrope porte les informations et les contrôles.

Le mouvement doit expliquer le changement en cours. Propositions : réponse de commande courte, entrée de panneau de quelques centaines de millisecondes, transition diagonale entre scènes et repère temporel lié à la lecture. Les animations ambiantes restent lentes et limitées à la zone de scène. Un état de machine, une progression d’impression ou un accusé de réception ne doit jamais être produit par une boucle décorative.

Le mode réduit garde la sélection, la position dans la vidéo et l’état des opérations visibles. La vidéo se lit à la demande ; une arrivée sur l’écran 03 confirme l’ouverture de la vue, pas le démarrage d’un son ou d’une lecture.

## Trois écrans et travail créatif

**Atelier à gauche** présente les ressources, les pièces, les affectations et les besoins de préparation. **Jarvis au centre** garde le projet actif, reçoit l’intention et montre les décisions à prendre. **Création à droite** reçoit le modèle 3D, la coupe ou le film. Chaque moniteur ouvre sa propre fenêtre en plein écran.

Le Studio complète cette organisation : lecture par chapitres, provenance, paramètres du prochain édit et export du plan. Les fonctions créatives futures devront partager les mêmes identifiants de projet, révision et sources que l’atelier. Un film de référence reste explicitement distinct d’une preuve d’avancement du projet actif.

## Séries de contenus à développer

| Série proposée | Récit | Sortie utile |
|---|---|---|
| Du détail à l’œuvre | Une pièce finie, son geste et sa présence. | Film de portfolio et couverture cohérente. |
| Le geste de l’atelier | Une décision de fabrication ou de finition visible. | Séquence de savoir-faire, contextualisée par le projet. |
| De l’idée à la pièce | Brief, modèle, étape physique et résultat. | Cas de commande sur mesure, avec les accords de présentation nécessaires. |
| Prototype en mouvement | Besoin, assemblage, essai et observation. | Démonstration fonctionnelle documentée ; les mesures restent exactes. |
| Une pièce disponible | Œuvre entière, détails, dimensions et offre réelle. | Fiche vitrine reliée au même objet et à son état de vente. |

Ces séries couvrent figurines, socles, objets, assemblages et prototypes. Elles sont une proposition éditoriale ; le Site actuel ne publie pas automatiquement de produit ou de contenu social.

## Maintenir une identité actuelle

Le nom, l’emblème, la place du geste et la lisibilité de l’œuvre constituent les repères stables. Les outils, transitions, formats et recettes peuvent évoluer par version. Une nouveauté de modèle ou de plugin n’est adoptée que si une comparaison sur des plans BOJ.ART montre un bénéfice concret.

Chaque essai conserve les sources, les paramètres, la version de l’outil, le fichier rendu et les observations de revue. Comparer les exports sur la même séquence et à la même taille. Examiner le cadrage, la couleur de la peinture, la netteté, les raccords, la typographie et le son. Éviter un score automatique de « conformité à la signature » sans critères éprouvés.

Les candidats créatifs et leurs limites figurent dans [la recherche des skills](../qa/creative-skills-research.md). Le premier ordre d’intégration proposé est : lecture des sources et annotations, compositions de motion réutilisables, son, puis traitement couleur qualifié. Cette chaîne reste à raccorder au Studio ; le film V.01 a été rendu avec une recette FFmpeg explicite.
