# BOJ.ART — trois compléments créatifs à qualifier

Recherche ciblée du 18 octobre 2026. Périmètre : finition vidéo et couleur, sound design, choix de plans et contrôle de la signature. Les packs déjà audités ne sont pas réévalués ici. Aucune installation, génération payante, connexion de compte, soumission de média ou modification de l’application n’a été effectuée pour cette recherche.

## Décision

Le meilleur ajout immédiatement crédible est le skill officiel **ElevenLabs sound-effects**, à garder comme option cloud pour des sons de création. Deux outils locaux méritent des essais ciblés : **video-evidence** pour l’audit des plans et **color-grading-skill** pour exécuter une correction couleur déjà décidée. Ces deux projets communautaires ne remplacent pas les choix actuels sans qualification. En particulier, le fichier SKILL.md couleur doit être corrigé avant toute installation automatique.

| Candidat | Nature vérifiée | Licence du dépôt | Emplacement du traitement | Décision BOJ.ART |
|---|---|---|---|---|
| [sound-effects — ElevenLabs](https://github.com/elevenlabs/skills/tree/main/sound-effects) | Vrai SKILL.md officiel et exemples d’appel API. | MIT, fichier LICENSE consulté. | Description envoyée au service ElevenLabs ; audio reçu puis conservé localement. | Option pertinente pour une petite bibliothèque sonore BOJ.ART. Aucun raccordement actif. |
| [video-evidence — kenchikuliu](https://github.com/kenchikuliu/video-evidence) | Vrai SKILL.md, scripts CLI et tests. | AGPL-3.0 ; le modèle YOLO11n fourni est également indiqué sous AGPL-3.0. | Analyse locale ; revue Ollama facultative ; génération distante dans une branche distincte. | Laboratoire pour comparer des montages avec des preuves temporelles. Ne pas remplacer claude-real-video à ce stade. |
| [color-grading-skill — kajisho5](https://github.com/kajisho5/color-grading-skill) | SKILL.md et moteur CLI Python 0.4.0. | MIT, fichier LICENSE et pyproject.toml consultés. | Local, via un checkout ffmpeg-skill et les exécutables FFmpeg/FFprobe. | Contrat technique intéressant ; installation du skill suspendue à la correction du YAML et à des essais sur copies de référence. |

Ces licences couvrent les dépôts. Les licences des médias, LUT, logiciels, modèles et services restent des éléments distincts. Les évaluations ci-dessous portent sur les fichiers et documents consultés, pas sur des exécutions réalisées dans l’atelier.

## 1. Sound Effects officiel : textures, accents et retours sonores

Le [SKILL.md](https://github.com/elevenlabs/skills/blob/main/sound-effects/SKILL.md) existe dans l’organisation du fournisseur. Il décrit la génération d’effets à partir d’un texte, avec durée, boucle et influence du prompt. Le dépôt contient un dispositif d’évaluation ; sa présence ne constitue pas un benchmark BOJ.ART. La [licence MIT](https://github.com/elevenlabs/skills/blob/main/LICENSE) a été vérifiée séparément du README.

Pour BOJ.ART, je proposerais trois familles à écouter avant choix : une texture discrète pour la création, un accent de révélation d’œuvre, et de courts retours d’interface. Leur utilisation dans la tour devrait rester désactivable et les alertes importantes conserver une indication visuelle. Cette direction sonore reste une proposition à confronter aux originaux archivés.

**Coût et données.** L’API demande une clé et un accès internet. La [tarification officielle](https://elevenlabs.io/pricing/api) décrit une facturation du service ; aucun tarif contractuel propre au compte BOJ.ART n’est connu. La [référence API](https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert) indique une durée de 0,5 à 30 secondes. Elle indique aussi que le mode sans rétention est réservé aux clients Enterprise : ne pas promettre ce mode par défaut.

**Commandes à encadrer.** Le skill propose un onboarding par `npx …@latest`, qui installe/exécute un outil et configure une clé. Cette commande n’a pas été lancée. Pour une intégration future, figer la version approuvée, protéger la clé côté processus, borner le nombre de générations et utiliser des noms de sorties uniques : les exemples d’écriture peuvent remplacer un fichier existant. Les prompts de son ne doivent pas contenir d’informations client inutiles.

**Ce qu’il ne fait pas.** Il ne construit pas automatiquement une signature sonore validée et ne mixe pas un film complet. Pour les gestes authentiques de l’atelier, les prises de son originales restent des références utiles ; un effet généré doit être identifié comme tel.

## 2. Video Evidence : relier les choix de montage aux sources

Le [SKILL.md](https://github.com/kenchikuliu/video-evidence/blob/main/SKILL.md) distingue les observations horodatées de leur interprétation. Le [README](https://github.com/kenchikuliu/video-evidence/blob/main/README.md) décrit des fichiers d’analyse, une timeline, une revue sémantique optionnelle et un plan de montage. Le dépôt est communautaire et très récent ; aucun essai comparatif local ne permet d’affirmer qu’il lit mieux les vidéos BOJ.ART que le candidat déjà retenu.

**Dépendances et données.** Python 3.10+, FFmpeg/FFprobe et des [paquets d’analyse](https://github.com/kenchikuliu/video-evidence/blob/main/requirements.txt) sont requis. La [documentation de workflow](https://github.com/kenchikuliu/video-evidence/blob/main/references/workflow.md) ajoute Whisper et un modèle de vision Ollama si nécessaire. Les téléchargements de modèles et le calcul ont un coût matériel, même sans API payante. La [licence](https://github.com/kenchikuliu/video-evidence/blob/main/LICENSE) est AGPL-3.0 ; elle doit être examinée avant de distribuer une adaptation ou d’intégrer ce composant à un service.

**Intérêt précis pour le Studio.** Chaque recommandation de plan pourrait pointer vers la publication, l’intervalle temporel et les observations qui la justifient. Une scène sans détection ne serait pas déclarée vide. La présence d’une réponse JSON du modèle ne serait pas assimilée à une preuve de conformité visuelle.

**Commandes à encadrer.** L’analyse et le plan se distinguent du rendu FFmpeg, qui écrit un fichier. Le workflow comporte aussi une génération MiniMax/Seedance avec soumission payante et upload explicites : cette branche n’est pas nécessaire pour analyser l’archive BOJ.ART et resterait désactivée par défaut. Préserver les sources, vérifier la destination de rendu et reprendre un même travail interrompu au lieu de multiplier les générations.

**Limite métier.** OCR, détection d’objets et coupures candidates ne constituent pas une mesure fiable de l’identité artistique. Les couleurs, cadrages, gestes et rythmes doivent être comparés à un petit corpus BOJ.ART annoté. Une détection COCO n’identifie pas la signature de l’artiste.

## 3. Color Grading : exécuter un traitement explicite

Le [README](https://github.com/kajisho5/color-grading-skill) décrit cinq opérations typées, dont conversion HDR/SDR, LUT et corrections primaires. Le [pyproject.toml](https://github.com/kajisho5/color-grading-skill/blob/main/pyproject.toml) identifie Python 3.9+ et la version 0.4.0. Le moteur s’appuie sur un autre checkout, ffmpeg-skill ; ces dépendances doivent être figées et vérifiées ensemble.

**Défaut constaté.** GitHub signale actuellement une erreur YAML dans le [SKILL.md](https://github.com/kajisho5/color-grading-skill/blob/main/SKILL.md). Je ne le classe donc pas comme prêt à installer. Le fichier expose néanmoins un contrat utile : paramètres explicites, plan préalable, sorties bornées et provenance. Une correction du frontmatter doit être vérifiée avant intégration ; elle n’a pas été effectuée dans le dépôt tiers.

**Coût et données.** Le [fichier LICENSE](https://github.com/kajisho5/color-grading-skill/blob/main/LICENSE) confirme MIT. La [politique de sécurité](https://github.com/kajisho5/color-grading-skill/blob/main/SECURITY.md) décrit un outil d’exécution local, sans compte ni service réseau. Les LUT et les versions des logiciels restent à sélectionner séparément ; le skill ne choisit pas l’aspect artistique.

**Commandes à encadrer.** Le projet annonce un schéma refusant les commandes et filtres arbitraires. Ce mécanisme n’a pas été exécuté dans cette recherche. Imposer des racines d’entrée/sortie, une copie de travail, des sorties uniques et une politique explicite pour l’écrasement. Contrôler l’image et les métadonnées après l’opération : le succès technique ne prouve pas que la couleur respecte BOJ.ART.

**Mainteneur.** Projet indépendant avec code, tests et documentation de sécurité ; il n’annonce pas plusieurs branches de maintenance. Qualification nécessaire avant utilisation dans un traitement automatique d’originaux.

## Règles à intégrer au Studio avant d’ajouter ces outils

Les règles suivantes sont des décisions proposées pour BOJ.ART. Elles peuvent être mises en œuvre avec les composants déjà retenus, sans installer les nouveaux candidats.

1. **Chaque choix de plan garde sa preuve.** Publication source, timecodes de début/fin, rôle du plan, recadrage, raison du choix et résultat de la revue. Une observation incertaine reste marquée comme telle.
2. **Les originaux et les variantes ont des identités distinctes.** Conserver l’empreinte du fichier source, les paramètres d’export, la version des outils et l’empreinte du résultat. Un export ne doit pas écraser l’original.
3. **La couleur est revue sur une référence approuvée.** Lire les métadonnées du média, définir le traitement et comparer avant/après. Ne pas appliquer un LUT universel sur des plans d’espaces colorimétriques différents.
4. **Le son possède son propre plan.** Pour chaque piste : origine, rôle, intervalle, niveau, fondus et statut de validation. Distinguer audio original, audio sous licence et effet généré. L’absence de piste ne doit pas être masquée par un libellé de mix terminé.
5. **La signature n’est pas un score inventé.** Montrer les observations sur logo, texte, composition, lumière, couleur, rythme et son, avec un aperçu comparatif. Les seuils éventuels doivent être qualifiés sur les originaux.
6. **Les outils rendent des résultats observables.** Plan préparé, rendu en cours, fichier présent, inspection réalisée et publication sont des étapes différentes. Le Studio ne doit pas déduire l’étape suivante du seul succès de la précédente.

### Ordre recommandé

Commencer par annoter quelques séquences représentatives de l’archive et formaliser les règles visuelles/sonores. Relier ces annotations aux compositions Remotion déjà retenues. Tester ensuite Video Evidence sur ce même corpus. Ajouter Sound Effects seulement si les prises de son et ressources existantes ne couvrent pas le besoin. Qualifier l’exécution couleur après correction du SKILL.md et comparaison de rendus. Aucun des trois candidats n’est actuellement activé dans la tour.
