# BOJ.ART — Jarvis, la tour de contrôle · V11

BOJ.ART réunit création 3D, préparation, parc FDM/résine, contenus et dossiers commerciaux dans un poste à trois écrans. La V9 met au centre **la prochaine décision du dossier, les preuves disponibles et l’action utile**. Elle apporte un journal local avec reçus métier stables, un coffre des originaux STL et un bureau de conseils Jev.

La V10 ajoute le parcours **demande client → qualification → dossier technique**, relié à une [vitrine BOJ.ART distincte](https://bojart-studio.yellowghost64.chatgpt.site/). Le [réaudit acquisition V10](docs/AUDIT_ACQUISITION_V10.md) décrit ce qui est livré et les capacités encore nécessaires jusqu’à la livraison et au SAV.

La **V11** corrige les interruptions et les actions concurrentes constatées par l’[audit global](docs/AUDIT_GLOBAL_V11.md). Elle ajoute un état de récupération lorsqu’un journal devient illisible, le choix explicite unité/procédé pour chaque STL et la comparaison de deux révisions d’une demande. La tour reste à accès propriétaire ; la vitrine est publique lors de la vérification du 19 octobre 2026, avec des informations commerciales encore à compléter.

Le [registre des exigences](docs/PROJECT_REQUIREMENTS.md) rassemble le projet depuis la demande initiale, ses capacités livrées et ses raccordements futurs.

## Installer les trois vues

Ouvrir chaque lien dans une fenêtre du même navigateur, puis placer les fenêtres sur les moniteurs :

| Position | Station | Rôle |
|---|---|---|
| Gauche | [01 · Atelier](https://bojart-atelier.yellowghost64.chatgpt.site/?screen=atelier&station=atelier&immersive=1) | Parc, fiches et file simulée |
| Centre | [02 · Jarvis](https://bojart-atelier.yellowghost64.chatgpt.site/?screen=pilotage&station=pilotage&immersive=1) | Dossier, décision active, mission et administration |
| Droite | [03 · Création](https://bojart-atelier.yellowghost64.chatgpt.site/?screen=creation&station=creation&immersive=1) | Modèles, œuvres et films |

`station` conserve le rôle de la fenêtre ; `immersive=1` masque la navigation périphérique. Le dock permet de sortir de ce mode. Le plein écran du navigateur reste indépendant. La vue `?screen=panorama` présente les trois compositions ensemble. Sur la tour locale, utiliser les mêmes paramètres avec l’origine `http://127.0.0.1:3137`.

La régie adresse modèle, œuvres, film ou parc à la bonne station et attend son retour. Une fenêtre absente, un contexte devenu obsolète ou un formulaire ouvert produit un refus explicite. Les indicateurs détectent des fenêtres, sans certifier le branchement physique des moniteurs. Un reçu d’affichage confirme l’ouverture de la vue, pas une lecture vidéo ou une impression.

## Du dossier à sa prochaine étape

Le poste central présente le projet actif, une décision prioritaire, sa cause, sa cible et les actions disponibles. Huit domaines restent accessibles : création, préparation, production, contenus, commerce, ressources, système et robotique.

« Orchestre mon projet » relit les fichiers et ouvre une mission fondée sur leurs preuves actuelles. Cette action ne crée plus automatiquement un devis, un scénario ou une affectation simulée. Les états distinguent références enregistrées, fichiers réellement relus, données manquantes, incompatibilités et services à raccorder.

L’établi de préparation associe un STL à une pièce, mesure ses octets selon l’unité choisie, puis compare ses dimensions aux volumes du parc déclaré. Six orientations orthogonales sont inspectables dans une enveloppe 3D ; le rapport s’exporte en JSON. Les imports et les formulaires gardent leur dossier cible et refusent une révision devenue obsolète.

L’import de nouveaux STL commence par un choix par fichier : **millimètres ou pouces**, puis **FDM ou résine UV**. Aucun de ces choix n’est présélectionné. Un lot peut contenir les deux procédés ; la liste indique les pièces ajoutées et les fichiers restant à reprendre. Une reprise ne recrée pas les pièces déjà ajoutées. L’import conserve sa cible et ne remplace pas un formulaire déjà ouvert.

La coupe visuelle reste une inspection du modèle. Supports, évidement, drainage, placement sur plateau, couches du slicer et résistance mécanique nécessitent leurs propres contrôles. Voir [PREPARATION.md](docs/PREPARATION.md).

## De la vitrine au dossier technique

Le centre, le domaine Commerce et l’onglet Demandes ouvrent les demandes importées. Accès direct : [`?panel=inquiries`](https://bojart-atelier.yellowghost64.chatgpt.site/?panel=inquiries).

1. Exporter une demande depuis l’administration de la vitrine. Le fichier `bojart.inquiry.export.v1` comporte sa référence et une empreinte d’intégrité.
2. Choisir **Importer une demande** dans Jarvis. Le document et son empreinte sont vérifiés avant l’aperçu ; aucun dossier n’est encore créé.
3. Examiner la demande et saisir, si nécessaire, une synthèse technique séparée. Confirmer **Créer le dossier technique**.
4. Jarvis conserve la référence, la révision, les empreintes et les paramètres structurés. Le nom, les coordonnées et le texte original restent dans la boîte source ; ils ne sont pas copiés automatiquement dans le journal atelier.
5. Examiner les points à qualifier, retrouver la demande source dans son administration privée, puis compléter le dossier et son chiffrage.

Le même export rouvre le dossier existant. Une autre version du contenu portant la même identité affiche un conflit et ne remplace pas le travail de l’atelier. Un changement de date d’export seul ne crée pas un nouveau dossier. Les deux fenêtres qui importent simultanément partagent le même identifiant de dossier ; le service local conserve le résultat confirmé et le conflit éventuel.

La V11 compare huit paramètres structurés contre leur valeur importée d’origine. Elle indique les différences, les révisions anciennes et les points à revoir, même si le dossier de travail a depuis évolué. Le bouton « Ouvrir le dossier conservé » garde sa cible explicite ; cette comparaison ne réalise aucune fusion automatique.

Une dimension inconnue reste vide, sans hauteur par défaut. Le dossier créé ne contient ni STL inventé, ni prix, ni accord de fabrication. Les coûts existants doivent être renseignés ; le calcul produit toujours un brouillon. Les questions de qualification s’exportent pour relecture sans envoi de message.

La liste de Jarvis contient les imports locaux, pas une consultation en direct de la boîte de réception. L’export source contient des données personnelles et doit suivre sa politique de conservation. La synthèse technique est saisie par l’opérateur : aucun mécanisme d’anonymisation automatique n’est annoncé. L’empreinte vérifie le contenu et ne certifie pas l’émetteur.

Installer le code V11 du service local avec les écrans V11 pour bénéficier aussi des corrections du coffre. La publication du site hébergé ne met pas à jour le service du PC. Le format de transport et la base SQLite restent en v2 ; la genèse et les anciennes opérations conservent leur interprétation. Les anciens écrans peuvent ne pas savoir relire le champ technique de demande ajouté en V10.

## Le bureau « Conseils & Jev »

Le bureau propose trois comparaisons bornées : une orientation brute compatible, le prochain élément à examiner et une intention éditoriale parmi les cinq séries BOJ.ART. Les règles locales fonctionnent sans compte et sont identifiées comme telles. Jev peut comparer les candidats par la passerelle TypeSafe lorsque celle-ci est configurée.

Les réponses sont liées au dossier, aux fichiers et aux versions concernés ; elles expirent et sont revérifiées avant ouverture. Une réponse incertaine laisse le choix manuel disponible. Le routage visuel conserve son contrat distinct de quatre vues.

L’API Jev utilisée est hébergée. Les skills d’intégration ne constituent pas un modèle Jev installé localement. Aucun appel TypeSafe réel ni précision française sur la tour cible n’est attesté par les tests. Contrats, données transmises et limites : [JEV_DECISIONS.md](docs/JEV_DECISIONS.md) et [JEV_LOCAL.md](docs/JEV_LOCAL.md).

## Conserver les dossiers et leurs originaux

Le site hébergé conserve son journal dans le navigateur et ses STL dans IndexedDB. Sur la tour, Node.js **24 ou ultérieur** permet de lancer le dashboard, la passerelle, SQLite et le coffre :

```sh
npm run start:local
```

Le service écoute uniquement sur `127.0.0.1:3137`. Les données restent hors de `dist/` ; les clés éventuelles restent côté serveur. Le site distant ne se connecte pas implicitement au `localhost` de l’atelier.

Le protocole v2 enregistre chaque opération et son résultat métier dans une transaction. Les commandes concurrentes suivent une séquence serveur et une version attendue ; une commande refusée reste consultable. Un retry conserve son reçu. La migration SQLite v1 préserve les anciennes opérations et fige leur résultat historique. Mettre à jour le service et les écrans ensemble : les POST d’opérations v1 sont explicitement refusés.

La continuité propose **deux exports complémentaires** :

| Export | Contenu |
|---|---|
| Journal `.json` | Dossiers, opérations, versions, genèse et reçus lorsqu’une autorité v2 est présente |
| Archive `.bojassets` | Octets originaux des STL, identifiants et empreintes SHA-256 |

L’export navigateur inclut les originaux courants et remplacés référencés par l’historique. Il refuse un fichier requis absent ou une empreinte divergente. L’archive peut être restaurée dans le coffre de la tour ; tous ses fichiers sont vérifiés avant de rendre leurs associations visibles.

Conserver les deux exports, arrêter les modifications pendant leur création et restaurer les deux avant de reprendre le travail sur un autre poste. Ils n’ont pas de snapshot commun et ne sauvegardent ni secrets ni états physiques. Limites : 50 Mio par STL, 256 Mio par archive navigateur, 1 Gio par archive serveur. Procédures, API et garanties : [local/WORKSHOP.md](local/WORKSHOP.md).

Si une origine, une opération ou un reçu conservé devient illisible, la V11 suspend les modifications et la synchronisation. Le dernier état cohérent reste en mémoire lorsqu’il existe ; un premier démarrage bloqué n’invente aucun dossier de remplacement. Le panneau propose une **copie de récupération** des entrées brutes disponibles et de la dernière lecture cohérente, puis un **réexamen** après réparation. Cette copie limitée à 16 Mio n’inclut pas les STL et ne s’importe pas comme une sauvegarde normale. Les détails et limites sont dans l’[audit d’intégrité](docs/audit-v11-integrity.md).

## Signature BOJ.ART et studio

L’interface reprend l’emblème original, le blanc, le noir et les accents rouges/magenta, avec Barlow Condensed et Manrope. Le mouvement accompagne sélection, ouverture et retour d’action. Le mode réduit conserve les contrôles ; les boucles décoratives ne représentent aucune télémétrie.

La [vidéothèque](dist/assets/archive-index.json) indexe **31 publications recensées au 18 octobre 2026** : 30 vidéos et un carrousel. L’archive distincte documente 29 vidéos récupérées et sept images ; la vidéo `7099716894994730246` manque. Le site propose 28 aperçus vidéo silencieux ; le concours n’a pas d’aperçu pour éviter l’exposition des participants.

Deux rendus de référence sont présents : la boucle d’atelier de **18,8 secondes** et « Baki — Du détail à l’œuvre », **22,7 secondes**, master **720 × 1 280 à 30 i/s**, silencieux. Ils proviennent des œuvres et gestes originaux ; sources et transformations sont documentées pour [Baki](dist/assets/brand-film-sources.json) et [la boucle](dist/assets/atelier-motion-sources.json).

Le studio des dossiers conserve des intentions de montage versionnées, leurs sources, formats, légendes et notes sonores. Son export décrit un montage à réaliser. Direction proposée : [IDENTITE_VISUELLE.md](docs/IDENTITE_VISUELLE.md). Usage : [PROJECT_STUDIO.md](docs/PROJECT_STUDIO.md). Recette du film : [brand-film-v1](creative/brand-film-v1/README.md). Candidats de skills : [VIDEO_SKILLS.md](docs/VIDEO_SKILLS.md).

## Vérifier et poursuivre

Les vérifications significatives couvrent concurrence et reprise du journal, transfert des originaux navigateur/serveur, contrats Jev, fraîcheur des preuves, interfaces et préparation :

```sh
node qa/check-workshop-authority.mjs
node qa/check-workshop-assets.mjs
node qa/check-workshop-backend.mjs
node qa/check-project-decisions.mjs
node qa/check-project-evidence.mjs
node --experimental-vm-modules qa/check-durable-integration.cjs
node --experimental-vm-modules qa/check-interface.cjs
node --experimental-vm-modules qa/check-preparation-integration.cjs
node qa/check-inquiry-import.mjs
node --experimental-vm-modules qa/check-inquiry-interface.cjs
node --experimental-vm-modules qa/check-inquiry-revisions.cjs
node qa/check-v11-integrity.mjs
node --experimental-vm-modules qa/check-v11-recovery-ui.cjs
node --experimental-vm-modules qa/check-v11-stl-import.cjs
```

Les rapports dans `qa/` précisent les fixtures utilisées. SQLite, les parseurs et les transports injectés sont vérifiés ; le rendu navigateur/WebGL et les trois moniteurs physiques restent à examiner sur la tour. Aucun test ne lance une imprimante.

L’inventaire matériel, les profils qualifiés, les lots distincts des révisions, le slicing, la voix locale, les connecteurs machine, les rendus automatisés, la publication sociale et les paiements restent à raccorder. Les ressources et travaux initiaux sont simulés. Le démonstrateur 3D fourni est un socle original, pas un STL de personnage. La trajectoire générale figure dans [JARVIS.md](docs/JARVIS.md).

Seul `dist/` est destiné à la publication statique. Les licences des bibliothèques, polices et fichiers concernés restent incluses auprès de leurs ressources.
