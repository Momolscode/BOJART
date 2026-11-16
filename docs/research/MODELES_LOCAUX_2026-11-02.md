# Modèles locaux pour Jarvis — sélection du 2 novembre 2026

Statut : sélection technique à essayer sur la tour BOJ.ART. Les sources ci-dessous ont été consultées le 2 novembre 2026, heure de Paris. La sélection initiale précédait l'information sur le matériel. Depuis, l'utilisateur indique une RTX 4060 Ti et sa photo montre 8 Go de mémoire graphique, 16 Go de RAM, un Ryzen 5 5600G et Windows 11. Le [profil du poste](../memory/POSTE_RTX4060TI.md) retient `speed`. Aucun poids n'a été téléchargé pendant cette préparation ; la mémoire actuellement disponible et les performances réelles restent inconnues. Les tailles publiées concernent les fichiers de poids, pas toute la mémoire nécessaire en fonctionnement.

## Choix pour le premier lancement

| Usage | Modèle retenu pour essai | Motif | Intégration préparée |
| --- | --- | --- | --- |
| Conversation réactive sur petite carte | Qwen3.5 4B, Q4_K_M | Variante compacte, environ 3,3 Go de poids ; premier candidat à essayer autour de 8 Go de VRAM | Profil `speed` |
| Conversation quotidienne | Gemma 4 12B, Q4_K_M | Compromis taille/capacités ; environ 8 Go de poids ; essai conseillé avec 16 Go de VRAM | Profil `balanced` |
| Analyse, code et préparation de projets | Qwen3.8 27B, Q4_K_M | Modèle récent spécialisé aussi dans le travail de code et les tâches longues ; environ 18 Go de poids | Profil `quality`, préférence pour 32 Go de VRAM ; essai possible à 24 Go avec marge mesurée |
| Recherche documentaire multilingue | Qwen3 Embedding 0.6B | 639 Mo annoncés ; laisse de la place à la conversation et aux outils créatifs | Même modèle dans les trois profils ; index commun existant |
| Création et édition d'images locales | FLUX.2 Klein 4B | Candidat pour les itérations rapides avec références ; poids sous Apache 2.0 selon l'éditeur | Sélection seulement, moteur d'image distinct à raccorder |

Les repères de VRAM sont **nos hypothèses d'essai**, pas des minima garantis par les éditeurs. Ils incluent une intention de marge pour le cache de contexte, les écrans et les autres applications ; le test local reste décisif. Ne pas additionner les VRAM de plusieurs cartes comme si elles formaient automatiquement une seule carte. Sur CPU ou GPU non identifié, commencer par le profil compact comme essai, sans promesse de rapidité.

Le choix `quality` privilégie le potentiel de réponse ; il ne signifie pas qu'un 27B répondra plus vite qu'un 4B. Les trois profils ne sont pas téléchargés ni chargés simultanément : l'installation choisit un modèle de conversation et un modèle d'embeddings. Le panneau Mémoire utilise un seul modèle de conversation configuré à la fois ; aucun routage automatique entre trois LLM n'est annoncé.

## Comparaisons utiles

**Qwen3.8 27B** est le candidat principal pour une tour suffisamment équipée. La fiche officielle décrit texte/image/vidéo en entrée, raisonnement réglable et capacités de code. Le client Jarvis actuel transmet du texte ; sélectionner ce modèle ne raccorde pas automatiquement caméra ou vidéo. Les performances publiées par le fabricant ne remplacent pas un essai sur les dossiers BOJ.ART. Sources : [fiche Qwen](https://huggingface.co/Qwen/Qwen3.8-27B), [tag Q4 explicite](https://ollama.com/library/qwen3.8:27b-q4_K_M).

**Gemma 4 12B** est notre candidat intermédiaire. Les variantes 26B A4B et 31B sont des alternatives à comparer ensuite si la RAM/VRAM et les mesures le permettent. Le nombre de paramètres actifs d'un MoE ne représente pas l'ensemble des poids à loger. Sources : [fiche Google](https://huggingface.co/google/gemma-4-12B-it), [tag 12B Q4](https://ollama.com/library/gemma4:12b-it-q4_K_M), [famille Gemma 4](https://ollama.com/library/gemma4).

**Qwen3.5 4B** sert de candidat compact pour réduire la charge. Sa sélection ne valide ni le français de l'atelier ni la fiabilité des commandes ambiguës. Source : [tailles et variantes officielles](https://ollama.com/library/qwen3.5/tags).

**Qwen3.6 27B/35B** reste un concurrent intéressant pour les tâches de programmation ; il n'est pas installé en plus de Qwen3.8 par défaut. La comparaison doit porter sur un correctif réel BOJART, ses tests et le temps complet, pas uniquement sur un classement fournisseur. Source : [famille Ollama](https://ollama.com/library/qwen3.6).

**Ministral 3 8B/14B** reste une alternative multilingue ouverte. **Mistral Small 4** totalise 119 milliards de paramètres : les 6 milliards actifs ne font pas de lui un modèle de 6 milliards à charger. L'infrastructure de référence publiée est plus importante que notre poste encore inconnu ; pas de présélection pour le premier lancement. Sources : [Ministral 3](https://mistral.ai/news/mistral-3/), [Small 4](https://mistral.ai/news/mistral-small-4/).

**Qwen3 Embedding 0.6B** est retenu pour le coût de fonctionnement, pas comme vainqueur absolu du classement de recherche. Les variantes 4B/8B pourront être comparées sur les requêtes BOJ.ART ; elles consomment davantage de mémoire. Le bon couple est le même modèle et la même empreinte pour les documents et la question. Sources : [fiche officielle](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [distribution Ollama](https://ollama.com/library/qwen3-embedding:0.6b).

**EmbeddingGemma 2** est une alternative récente à comparer : version texte compacte 270M, extensions image/audio et espace partagé de 768 dimensions selon Google. Le client de mémoire actuel reste textuel ; une sélection de poids multimodaux n'indexerait pas automatiquement les rushes. La fiche Google indique un contexte de 8192 tokens ; ne pas reprendre sans contrôle les 256K affichés par certains tags de distribution. Ce candidat n'est pas ajouté au téléchargement initial avant comparaison sur nos requêtes. Sources : [fiche Google](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2), [guide développeur](https://developers.googleblog.com/embeddinggemma-2-the-developer-guide/), [distribution Ollama](https://ollama.com/library/embeddinggemma-2).

## Création : distinguer les moteurs

Un LLM prépare les briefs, raisonne sur les sources et écrit du code. La génération d'images, la vidéo, le rendu 3D et la fabrication ont leurs moteurs et leurs critères propres. La capacité de lire une image ne signifie pas capacité de la générer.

Pour l'image locale, essayer **FLUX.2 Klein 4B** en premier. Black Forest Labs publie des recettes et des mesures différentes selon la variante et le matériel ; ne pas transformer son temps sur une RTX 5090 en promesse sur notre poste. Le 9B peut être comparé pour la qualité, avec ses conditions de licence propres ; le fournisseur distingue Apache 2.0 pour le 4B et FLUX Non-Commercial pour le 9B. Sources : [famille Klein](https://bfl.ai/models/flux-2-klein), [usage local et licences](https://help.bfl.ai/articles/7108141705-can-i-run-or-fine-tune-flux-2-klein-locally).

Pour la vidéo locale, **Wan2.2 TI2V 5B** fournit une référence exécutable à examiner, pas une affirmation de meilleur modèle vidéo mondial. Sa recette officielle prévoit 720p et au moins 24 Go de VRAM avec déchargement de certains calculs vers la RAM. La qualité et le temps complet devront être comparés aux productions existantes. Source : [fiche Wan-AI](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B).

Critères créatifs BOJ.ART : fidélité aux photos authentiques de l'œuvre, proportions, continuité entre plans, matières, lumière, absence de détails inventés, résolution exportable et avis artistique. La génération d'une jolie image ne valide pas ces points. Le modèle et le rig G2 restent des pièces manquantes ; changer de générateur ne les reconstitue pas comme originaux. Aucun générateur d'images ou de vidéos n'est activé par les profils de conversation.

## Réactivité et cohérence

- Les commandes d'affichage connues du catalogue M07 sont résolues localement. Le statut « envoyé » reste distinct du reçu de la vue et de l'affichage réel sur un moniteur.
- Le modèle de conversation reçoit un contexte sélectionné et des références datées, pas toutes les archives. Les anciennes réponses aux sources périmées restent écartées.
- Une limite de contexte explicite et un garde en octets évitent l'envoi d'un paquet hors de l'enveloppe prévue. Ce garde conservateur n'est pas un tokenizer exact ni une preuve que le serveur respecte ses paramètres.
- Les profils demandent `think=false` et cinq minutes de maintien en mémoire. `speed` limite la sortie à 512 tokens et le contexte demandé à 16384 ; les deux autres profils conservent 768 et 32768. Ce réglage vise la conversation courante ; il n'est pas un mode de raisonnement approfondi ni une garantie de vitesse.
- Garder un seul calcul GPU lourd à la fois pendant la première recette. Le maintien en mémoire est une demande à Ollama, pas une réservation garantie ; un générateur d'images peut provoquer un déchargement/rechargement.
- Mesurer séparément le premier appel, les appels suivants, les temps de chargement, de génération et le temps observé par le client. L'interface actuelle affiche la réponse complète ; le temps au premier token n'est pas mesuré par ce parcours.

Sources de mise en œuvre : [API chat](https://docs.ollama.com/api/chat), [mémoire GPU, contexte et maintien en mémoire](https://docs.ollama.com/faq).

## Preuves attendues sur le poste

Le parcours [installation des modèles](../memory/INSTALLATION_MODELES.md) produit un rapport privé, avec empreintes, réponses à quatre cas synthétiques, contrôle de vecteurs et temps mesurés. Les seuils de 8/10/15 secondes pour les appels suivants sont des critères d'essai selon le profil, pas des performances déjà atteintes. Le résultat n'approuve pas automatiquement la porte `llm_qualified` ni la production réelle.

Après ce premier essai : vérifier les 14 requêtes documentaires existantes, un échange réel avec changement de dossier, un correctif de code avec tests, une demande sans preuve suffisante, puis un travail créatif de référence. Mesurer les commandes avec le navigateur réel, répéter au moins trente fois pour obtenir une distribution utile, et tester sous charge. Aucun classement absolu ni achat n'est décidé à partir des seules fiches publiques.
