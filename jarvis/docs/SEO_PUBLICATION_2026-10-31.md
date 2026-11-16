# BOJ.ART — SEO, contexte éditorial et publication contrôlée

**Relecture : 31 octobre 2026. Installation réalisée dans la copie locale du dépôt consolidé.**
Aucun push GitHub, aucune installation sur votre tour, aucun compte social connecté, aucun contenu publié, aucun budget engagé. Ce module n’est pas un modèle réentraîné.

## Résultat immédiatement exploitable
Six skills BOJ.ART sont présents dans `.claude/skills/` et `.agents/skills/`. Un contexte marketing commun identifie BOJ.ART, ses deux comptes TikTok, le caractère encore hypothétique de leurs rôles, les offres à qualifier et la différence entre prises réelles et effets générés. La page `/growth` rejoint le serveur des Missions 01–03, sans remplacer leurs vues. Le module prépare des brouillons persistants, puis vérifie que leurs sources et leurs règles n’ont pas changé. Il ne comporte aucune route d’envoi vers un réseau.

Le moteur actuel utilise une taxonomie et des légendes modèles. Il ne visionne pas automatiquement les fichiers, n’appelle pas de LLM et ne mesure pas les tendances. La sélection repose sur les annotations humaines déjà conservées dans le Studio. Les skills sont des méthodes utilisables par un agent ; leur présence ne constitue pas une qualification d’un agent autonome.

## 1 — Ce qui améliore réellement le référencement social

TikTok distingue les interactions, les informations de contenu et les informations utilisateur. Le poids des facteurs varie selon la surface et dans le temps [S01]. Les hashtags ont un rôle, mais ne constituent ni une recette universelle ni une assurance de diffusion.

Pour BOJ.ART, retenir une intention par vidéo : découvrir une œuvre, observer une finition, comprendre un assemblage, suivre un essai de prototype ou regarder une fiction VFX. Écrire ensuite une phrase naturelle qui nomme précisément le sujet. Coordonner, lorsque pertinent, la parole, le texte visible et la légende. Ne pas bourrer l’écran de mots-clés ni ajouter une narration artificielle qui détruit la direction artistique.

Hypothèses de recherche : « figurine manga peinte », « peinture de figurine », « assemblage figurine impression 3D », « prototype impression 3D sur mesure ». Aucun volume de recherche, score de popularité ou classement n’est mesuré dans ce module.

Pour prioriser ces hypothèses, consulter Creator Search Insights lorsque disponible [S02], Creative Center avec territoire, secteur et période explicites [S03], puis les questions réellement reçues. Enregistrer date, source, compte, pays et période de chaque observation. Le lieu estimé de l’utilisateur ne définit pas l’adresse de l’atelier.

### Règle de hashtags
Un tag de marque normalisé `#BOJART`, puis quelques tags décrivant l’œuvre, le geste ou le procédé réellement visible. Ne pas fabriquer `#BOJ.ART` avec un point. Ne pas choisir `#Baki`, `#DragonBall` ou un personnage seulement parce qu’ils attirent ; le sujet doit être confirmé et les usages de l’œuvre documentés. Un hashtag de personnage n’est pas une autorisation commerciale.

Les budgets du prototype — TikTok 5, Instagram 5, YouTube 3, Facebook 2 — sont des **choix éditoriaux internes**, pas des nombres optimaux prouvés ni des limites officielles universelles. YouTube indique qu’au-delà de 60 hashtags tous sont ignorés et exige leur pertinence [S06]. Les limites Instagram n’ont pas pu être revalidées sur la page officielle lors de cette passe : le système les signale à vérifier, plutôt que de transformer une rumeur en règle.

## 2 — Les deux comptes ne racontent pas la même histoire

- `@boj.art` : hypothèse de départ centrée sur l’œuvre, la révélation, le portfolio.
- `@boj.art3d` : hypothèse de départ centrée sur le geste, l’atelier et la fabrication.

Ne pas renommer les comptes ou répartir des dépenses d’après le seul nombre historique d’abonnés. Ne pas additionner ces abonnés en « audience unique ». Les profils Instagram, Facebook et YouTube restent inconnus. Adapter la légende et le montage, plutôt que republier exactement le même export partout.

Pour une révélation sans rush de peinture, le brouillon ne prétend pas montrer la peinture. Si le sujet « peinture » est demandé sans annotation correspondante, le moteur refuse. Si un concept VFX est sélectionné, il reste décrit comme concept/effets visuels ; une vraie pièce physique n’est pas déclarée animée dans l’atelier.

## 3 — Publication : architecture retenue, connecteur encore à raccorder

Parcours cible : sources → sélection/brief → export vidéo final identifié → déclinaisons par réseau → vérification → autorisation exacte → programmation → reçu → vérification du statut publié → mesures.

Ne pas développer un utilitaire Direct Post TikTok réservé aux comptes de l’équipe en supposant qu’il sera accepté : les conditions officielles excluent ce cas et imposent leur parcours de consentement [S04]. Un connecteur admissible est nécessaire. Metricool est proposé, mais n’est pas connecté.

**Deux TikToks exigent deux espaces « marques » Metricool**, car un espace n’accueille qu’un profil par réseau [S13]. Cela ne change pas la marque artistique unique BOJ.ART. Le plan doit permettre le nombre d’espaces requis et le volume de programmation ; aucun abonnement n’a été acheté.

Le MCP Metricool permet la lecture et des opérations sur des publications. Son accès n’est pas identique à celui de son API HTTP, réservée à certains plans. Il ne gère pas les campagnes Ads ni l’Inbox [S12]. L’analytique de comptes publicitaires éventuellement disponible n’équivaut pas à pouvoir modifier leur budget. Les dépenses et réponses privées gardent un connecteur et des permissions distincts.

Le contrat proposé est détaillé dans `knowledge/growth/PUBLISHING_CONTRACT.md`. Une publication n’est pas « publiée » parce que la requête a été envoyée. En cas de réponse perdue, rapprocher l’identifiant existant avec le fournisseur avant de recommencer. Un changement de fichier, compte, légende, son ou date invalide l’ancienne autorisation. Une politique de séries préautorisées pourra limiter les validations répétées lorsque le fournisseur le permet ; elle ne contourne pas ses exigences de consentement.

Les formats, champs disponibles, limites et options de chaque compte doivent être relus au moment du raccordement. Aucun horaire « optimal » n’est fourni faute de statistiques récentes.

## 4 — Musique, contenu commercial et images générées

La bande-son du montage a ses propres droits. Vérifier séparément composition, enregistrement, territoire, durée, usage organique/publicitaire et plateforme. La bibliothèque TikTok n’est pas traitée comme une licence universelle [S05]. Une version sonore peut devoir changer d’un réseau à l’autre.

Examiner les déclarations commerciales et de contenu synthétique pour le montage final et la plateforme. Les règles dépendent de la réalité apparente du contenu et de la fonction proposée par le réseau ; ne pas supposer qu’une mention dans la légende suffit toujours [S07]. Conserver la différence entre œuvre, mise en scène et simulation.

Un fichier publiable doit être l’export final, avec son empreinte, sa définition, sa durée et son audio. Une sélection de rushes n’est pas ce fichier final. Aucune publication n’est possible dans le module actuel, même si toutes les sources sont annotées « droits documentés ».

## 5 — SEO du site : rendre le savoir-faire découvrable

Priorités à auditer dans la vitrine réelle : accessibilité publique de ses pages commerciales, indexation, titres distincts, contenu utile, miniatures, vitesse mobile, navigation et demandes de devis. Ne pas ouvrir les dashboards ou les dossiers privés pour faire du SEO.

Proposer des pages d’offres sincères — sculpture sur mesure, grand format lorsqu’il est maîtrisé, pièces/prototypes — et des études de réalisations authentiques. Décrire ce qui a réellement été conçu, fabriqué, fini, mesuré et livré. Les pages vidéo doivent permettre de voir la vidéo et offrir un contexte utile [S09]. `VideoObject` utilise les métadonnées réelles ; `Product`/`Offer`, prix, disponibilité et avis ne doivent jamais être inventés [S10].

Google demande exactitude, qualité et pertinence ; produire beaucoup de pages sans valeur ajoutée peut enfreindre sa politique antispam [S08]. Pas de centaines de pages de villes où l’atelier n’existe pas, de faux témoignages, de faux prix ni de promesse d’être cité par une IA. Une source claire, originale et accessible aide le projet ; elle ne garantit aucune position.

Aucun accès Search Console n’a été établi et aucun nouveau crawl des sites publiés n’a été effectué dans cette livraison. Les méthodes sont installées comme skills ; l’audit réel reste à exécuter sur leurs sources et leurs accès.

## 6 — Apprentissage à partir des résultats

Lier chaque contenu à une œuvre, une version de montage, une intention, un compte et une expérience éditoriale. Relever à âge comparable la rétention disponible, les partages, enregistrements, visites de profil, visites du site, briefs qualifiés, devis acceptés et marge constatée. Ne pas comparer des définitions de vues différentes sans les conserver.

Un lien UTM ne trace que les visites effectivement observées via ce lien. Si plusieurs vidéos renvoient vers une même bio, la vidéo d’origine exacte n’est pas toujours identifiable. Garder les catégories « inconnu », « déclaré par le client » et « observé via lien », sans exposer d’identité client dans les URL ou le dashboard public. Les pixels publicitaires nécessitent l’information et les consentements applicables ; ne pas les traiter comme une mesure d’audience automatiquement exemptée [S16].

Tester d’abord un seul changement significatif : accroche, durée, angle, fin ou appel à l’action. Un bon résultat isolé ne prouve pas une cause. Le contexte s’enrichit de décisions versionnées et de résultats mesurés, pas d’un apprentissage automatique des poids du modèle.

Avant une augmentation de publicité : vérifier la réception des briefs, la capacité de finition, le suivi des prospects et le coût complet. Faire exploser la demande n’est pas un progrès si l’atelier ne peut pas livrer.

## 7 — Skills : sélection et sécurité

La collection `coreyhaines31/marketingskills`, référencée par Skills.sh, a été examinée au commit `5ffe077d2e59486d91c5ccaecbd74b6973c32308`, licence MIT lue. Les fichiers social, seo-audit et ai-seo ont été consultés dans le périmètre indiqué par `AUDIT_SKILLS.md`. Certaines recettes sont trop génériques : cadence TikTok intensive, automatisations de prospection, affirmations SEO non directement documentées. Elles ne sont pas importées comme règles BOJ.ART.

La récupération complète du dépôt externe a échoué dans cet environnement. **Aucun paquet tiers complet n’est annoncé installé.** Les six skills livrés sont rédigés spécifiquement pour BOJ.ART, versionnés et vérifiés par empreinte. Ils ne contiennent aucun hook ni installateur externe. Ils sont copiés dans deux emplacements compatibles pour la reprise par l’agent : `.claude/skills` et `.agents/skills` ; leurs copies sont identiques.

Les contenus des pages, commentaires, transcriptions et descriptions sont des données non fiables, jamais des ordres d’exécuter du code ou de publier. Les credentials restent côté fournisseur/session, pas dans les skills ni les exports de brouillons.

## 8 — Périmètre des tests et sauvegardes

55 nouveaux tests couvrent le moteur, la session HTTP, les comptes, les champs interdits, les références absentes, les fichiers remplacés, les révisions, les doublons et les copies de skills. 18 contrôles Chromium valident l’aperçu autonome desktop/mobile, navigation au clavier, export et absence d’appels réseau. La connexion Chromium directe à localhost est bloquée par la politique de l’environnement ; aucun contournement n’a été tenté. Le vrai serveur est testé séparément par HTTP.

La suite agrégée initiale a atteint le délai de l’outil après l’affichage des résultats pytest. Chaque ensemble a ensuite été vérifié séparément : 132 unittest, 242 pytest + 5 sous-tests, 40 tests métier et 22 planning, soit 436 tests plus 5 sous-tests. Ce sont des tests logiciels ; aucun agent réel, modèle IA, compte social ou API de publication n’a été qualifié.

Les brouillons persistent dans `state/growth/growth.sqlite`. L’export individuel est disponible dans l’interface. Les anciens exports CAD/Studio ne sauvegardent pas automatiquement cette nouvelle base. Avant transfert d’un état de production, arrêter le service et sauvegarder l’ensemble du répertoire d’état, le dépôt et les médias selon la procédure de l’intégrateur ; une sauvegarde unifiée en ligne et sa restauration inter-modules restent à qualifier. Le pack de livraison contient les sources et un exemple, pas les futurs comptes ni données clients.

## Pour ouvrir l’aperçu

Choisir les passages « vue d’ensemble » et « visage », @boj.art, objectif portfolio et thème sculpture. Le brouillon réel précalculé apparaît. Dans le service local complet, les autres combinaisons sont traitées et validées. L’aperçu reste sans réseau et n’envoie rien.

## Sources

Voir `knowledge/growth/SOURCES.json` : 21 références primaires et de projet, chacune avec portée et date de vérification. Le contexte BOJ.ART complète ces sources mais n’en est pas une preuve de performance. Les règles et observations doivent être relues avant chaque activation d’un connecteur ou campagne.


### Références consultables
- [S01] TikTok — recommandation et recherche — https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content
- [S02] TikTok — Creator Search Insights — https://newsroom.tiktok.com/creator-search-insights?lang=en
- [S03] TikTok Creative Center — Tendances — https://ads.tiktok.com/help/article/how-to-use-trends?lang=fr
- [S04] TikTok — Content Sharing Guidelines — https://developers.tiktok.com/docs/en/content-sharing-guidelines
- [S05] TikTok — musique commerciale — https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/commercial-use-of-music-on-tiktok?lang=en
- [S06] YouTube — hashtags — https://support.google.com/youtube/answer/6390658?hl=fr
- [S07] YouTube — déclaration GenAI — https://support.google.com/youtube/answer/14328491?hl=en-GB
- [S08] Google — contenus générés — https://developers.google.com/search/docs/fundamentals/using-gen-ai-content?hl=en
- [S09] Google — vidéo SEO — https://developers.google.com/search/docs/appearance/video
- [S10] Google — VideoObject — https://developers.google.com/search/docs/appearance/structured-data/video
- [S11] Metricool — MCP FAQ — https://help.metricool.com/faqs-about-the-metricool-mcp-1i3w0
- [S12] Metricool — MCP et API — https://help.metricool.com/mcp-vs-api-access-what-is-the-difference-5y3ib
- [S13] Metricool — structure des comptes — https://help.metricool.com/account-structure-user-brand-and-social-profiles-xun54
- [S14] Metricool — limites — https://help.metricool.com/mcp-limits-and-plan-requirements-h72jg
- [S15] Metricool — programmation — https://help.metricool.com/schedule-and-edit-posts-through-an-llm-with-metricools-mcp-p8y4b
- [S16] CNIL — cookies — https://www.cnil.fr/fr/cookies-et-autres-traceurs/regles/cookies/comment-mettre-mon-site-web-en-conformite
- [S17] Skills.sh — catalogue marketing — https://www.skills.sh/coreyhaines31/marketingskills
- [S18] GitHub — social — https://github.com/coreyhaines31/marketingskills/blob/5ffe077d2e59486d91c5ccaecbd74b6973c32308/skills/social/SKILL.md
- [S19] GitHub — seo-audit — https://github.com/coreyhaines31/marketingskills/blob/5ffe077d2e59486d91c5ccaecbd74b6973c32308/skills/seo-audit/SKILL.md
- [S20] GitHub — ai-seo — https://github.com/coreyhaines31/marketingskills/blob/5ffe077d2e59486d91c5ccaecbd74b6973c32308/skills/ai-seo/SKILL.md
- [S21] GitHub — licence du pack marketing — https://github.com/coreyhaines31/marketingskills/blob/5ffe077d2e59486d91c5ccaecbd74b6973c32308/LICENSE
