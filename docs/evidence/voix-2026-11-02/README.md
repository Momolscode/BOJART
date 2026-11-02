# Chaîne vocale simulée — mesures du 2 novembre 2026

**Statut : testé en simulation sur un conteneur Linux.** Rien n'est installé ni réceptionné sur la tour ; aucune voix humaine, aucun micro réel, aucun moniteur. Procédure et outils : [BANC_VOIX.md](../../BANC_VOIX.md).

## Ce qui a été rejoué

« Affiche le dashboard atelier » et ses variantes, de l'audio au reçu d'affichage :

1. **Prise** : 150 prises générées une fois (`corpus-2026-11-02.json`, manifeste `71d70205…`), quatre voix françaises Piper (siwis, upmc jessica, upmc pierre, gilles), cinq ambiances pour la phrase cible, cas limites. Chaque flux micro de 15 s à 48 kHz passe par le **vrai** `voice_endpoint.js` (fin de prise automatique) et le **vrai** encodeur WAV de `capture.js`, exécutés par Node.
2. **Transcription** : `POST /api/voice/transcribe` du vrai serveur → `LocalVoice` → faster-whisper 1.2.1 (PyAV 18.1.0), poids épinglés, CPU int8 4 fils.
3. **Intention, garde de contexte, distribution** : `POST /api/jarvis/turn` → `JarvisRuntime` (LangGraph + SQLite ; repli règles mesuré à part).
4. **Affichage simulé** : trois vues appairées (atelier, pilotage, création) qui suivent le protocole de `tower_screen.js` : événements, poll, accusé logiciel.
5. **Reçu** : `GET /api/jarvis/turn`, relu à chaque événement comme la console.

Hôte : Intel Xeon 2,1 GHz, 4 cœurs logiques, 15,7 Go, Linux, Python 3.13.18, aucun GPU. Mesures chaudes : une prise d'échauffement exclue, puis chaque prise une fois. Mesures froides : trois démarrages neufs du serveur, chargement du modèle compris (cache disque du système chaud).

## Résultat

| Mesure | Cible correcte (80) | Catalogue (24) | Refus attendus (46) | Erreurs critiques | Cas d'erreur | Transcription, médiane |
|---|---:|---:|---:|---:|---:|---:|
| **`small`, code final (référence)** | **65** | 11 | 46 | **0** | 15/15 | 1 001 ms |
| `small`, réglage d'origine (sans vocabulaire) | 12 | 6 | 46 | **0** | 15/15 | 1 133 ms |
| `small`, variante vocabulaire avant le changement | 65 | 11 | 46 | **0** | 15/15 | 1 080 ms |
| `base`, sans vocabulaire | 0 | 3 | 46 | **0** | 15/15 | 508 ms |
| `large-v3-turbo`, sans vocabulaire | 43 | 9 | 46 | **0** | 15/15 | 3 949 ms |
| `small`, sans vocabulaire, repli règles (80 prises cibles) | 12 | — | — | **0** | 15/15 | 1 008 ms |

« Refus attendus » : formulations hors catalogue, négations, commande physique, tableau non précisé et cas limites, qui ne doivent rien afficher. « Erreur critique » : une mauvaise vue ou un affichage non voulu. **Aucune sur les 830 prises rejouées** : une commande mal entendue devient une commande manquée, jamais une autre vue.

La référence est mesurée sur le commit `dad184c` (arbre propre), avec `voice.py` tel qu'il est livré. Les autres mesures datent d'avant le rebasage sur la PR #17 (`3436f53` plus le banc, non encore commité) ; le seul changement de code qui les sépare de la référence est le vocabulaire de `voice.py`. La variante « vocabulaire » mesurée avant donne exactement le même classement que la référence.

## Latence par étape — référence

Mesures chaudes, en millisecondes.

| Étape | n | Médiane | p95 | Max |
|---|---:|---:|---:|---:|
| Fin de prise après la parole, pause détectée (temps audio, calme ou ventilateur) | 66 | 1 059 | 1 914 | 3 365 |
| Encodage WAV navigateur (Node) | 150 | 191 | 248 | 301 |
| Contrôle du WAV | 150 | 38 | 48 | 78 |
| Transcription (moteur) | 150 | 1 001 | 1 185 | 6 643 |
| Transcription (requête HTTP) | 150 | 1 029 | 1 224 | 6 684 |
| Intention (routeur local) | 146 | 1 | 2 | 7 |
| Garde de contexte | 146 | 0,5 | 0,7 | 1 |
| Distribution aux vues | 77 | 5 | 11 | 12 |
| Tour complet (requête HTTP) | 146 | 26 | 35 | 49 |
| Affichage jusqu'au reçu | 77 | 16 | 30 | 255 |
| De la fin de prise au reçu | 77 | 1 090 | 1 290 | 1 348 |
| **Bout en bout, calme** (depuis la fin de la parole ; le max est la voix faible) | 22 | 2 175 | 2 437 | 5 132 |
| **Bout en bout, imprimante** (prise arrêtée par la limite de 15 s) | 20 | 13 878 | 14 217 | 14 292 |

À froid (3 démarrages) : chargement du modèle 775 ms, première transcription 2 067 ms, de la fin de prise au reçu 2 131 ms. Le repli règles coûte 14 ms par tour contre 24 ms pour LangGraph, avec la même reconnaissance. `large-v3-turbo` met 3,9 s par transcription et 5 s à charger sur ce processeur, pour un résultat moins bon que `small` avec vocabulaire.

**La transcription représente plus de 90 % du temps entre la fin de prise et le reçu.** Intention, garde, distribution et accusé tiennent en quelques dizaines de millisecondes.

## Constats

1. **La reconnaissance était le goulot.** Avec le réglage d'origine, `small` ne faisait afficher la vue atelier que 12 fois sur 80, et 4 sur 16 au calme. Le mot anglais « dashboard » devenait « dash beau d'atelier », « dashboot-batovier » ; « Jarvis » devenait « Jarvi », « Jarvie » ou « J'arrivée ». Le routeur exact refusait alors la phrase : commande manquée, sans danger.
2. **Un vocabulaire de décodage règle l'essentiel ; il est désormais dans `voice.py`.** `initial_prompt` = « Jarvis, affiche le dashboard atelier, dossiers, Studio, contenus, conception. » fait passer `small` à 65/80 : 15/16 au calme, 15/16 avec ventilateur, 15/16 avec imprimante, 13/16 en atelier fort, 7/16 avec une voix de fond. Aucune erreur critique, les 8 « N'affiche pas… » restent refusées, aucun coût en latence. Le routeur n'est pas élargi. La mesure sans vocabulaire reste possible : `--variante sans_vocabulaire`.
3. **« Affiche le dashboard dossiers » est inaccessible à la voix.** « dossiers » et « dossier » se prononcent pareil ; la transcription écrit le singulier, le routeur exige le pluriel : 0/8 dans toutes les mesures. Accepter le singulier de « dossiers », « contenus » et « trois dashboards » aurait ajouté 7 commandes correctes par mesure, sans aucun affichage dangereux (recalcul sur les transcriptions enregistrées). **Proposition, non codée.**
4. **Dans le bruit, la prise ne s'arrête pas seule.** La porte d'énergie (seuil RMS 0,015) ne voit jamais la pause dès que le bruit est à 10 dB sous la parole (imprimante, atelier fort, voix de fond) : 82 prises sur 82 courent jusqu'à 15 s et le bout en bout passe de 2,2 s à 14 s. Avec le ventilateur (20 dB), la pause est détectée (médiane 1,13 s, jusqu'à 3,4 s). Le bouton « Terminer » reste la sortie manuelle. À l'inverse, une voix 16 dB trop faible n'ouvre jamais la porte : la prise s'arrête à 6 s (« aucune parole »), l'audio est quand même transcrit et la commande passe.
5. **Une voix de fond se mélange à la commande** : 7/16 seulement, la transcription contient aussi la phrase de fond.
6. **Le bruit seul n'invente aucune commande** (sonde ci-dessous), mais faster-whisper écrit parfois une phrase fantôme connue (« Sous-titres réalisés par la communauté d'Amara.org ») sur un bruit d'atelier fort ; le routeur la refuse.
7. **Les 15 cas d'erreur se comportent comme prévu** dans toutes les mesures (tableau ci-dessous).
8. **PyAV 19 cassait toute transcription** (`metadata_errors` retiré, `TypeError` dans faster-whisper 1.2.1), trouvé par ce banc comme par le banc de pré-installation. Le correctif `av==18.1.0`, le verrou Windows et le contrôle `tools/verifier_voix.py` viennent de la PR #17, sur laquelle cette branche repose.

## Sonde bruit seul

`tools/banc_voix.py bruit` : 56 flux de 15 s sans parole (calme ; ventilateur, imprimante et atelier fort au niveau du corpus puis 10 dB plus fort ; 8 graines par cas), passés par le vrai code navigateur puis `LocalVoice` et le routeur exact. Mesuré avant le changement de `voice.py`, la variante « vocabulaire » ayant exactement ses paramètres.

| Variante | Flux | Sans parole | Texte fantôme | Commande déclenchée |
|---|---:|---:|---:|---:|
| sans vocabulaire | 56 | 47 | 9 (« Sous-titres réalisés par la communauté d'Amara.org » ×7, « … » ×2) | **0** |
| avec vocabulaire (réglage livré) | 56 | 46 | 10 (« Sous-titrage ST' 501 » ×7, « … » ×3) | **0** |

Le vocabulaire n'est jamais recopié dans la transcription. Le ventilateur reste sous le seuil de la porte : 16 flux s'arrêtent à 6 s sans parole ; 40 flux d'imprimante ou d'atelier courent jusqu'à 15 s.

## Cas d'erreur

Après la vraie transcription, ces cas imposent le texte exact de la commande : leur verdict ne dépend pas du modèle. Le banc de pré-installation (PR #17) couvre déjà en texte le rejeu, la coupure brutale du serveur, la concurrence et l'annulation ; ici, les familles sont rejouées après une vraie prise.

| Cas | Injection | Observé |
|---|---|---|
| WAV tronqué | 4 000 derniers octets perdus | 409 « Audio tronqué », aucun tour |
| Prise trop longue | 549 078 octets | 413 avant transcription |
| Format non conforme | WAV annoncé à 48 kHz | 409 du format |
| Micro réservé ailleurs | une seconde fenêtre demande le micro | réservation et transcription refusées (409) |
| Deux envois simultanés | même prise envoyée deux fois | 200 puis 409, sans file d'attente |
| Prise annulée pendant la transcription | annulation de la fenêtre | 409, aucun tour |
| Contexte modifié pendant la transcription | fichier de contexte changé | tour `STALE`, aucune commande |
| Dossier modifié pendant la transcription | nouvelle révision du dossier | tour `STALE`, aucune commande |
| Vue en retard | accusé 3 s après réception | reçu « affiché » à 3 008 ms, pas avant |
| Accusé tardif après changement | contexte changé avant l'accusé | accusé refusé (409), vue « stale » |
| Vue absente puis revenue | plus de poll pendant 3 s | en file pendant l'absence, affichée au retour |
| Coupure pendant la distribution | `OSError` injectée | `INTERRUPTED`, reprise : une seule commande |
| Reprise après 120 s | reprise 121 s après la demande | `STALE`, aucune commande |
| Double envoi | même tour renvoyé | même référence, aucune commande en plus |
| Redémarrage avant l'affichage | serveur relancé, vues réappairées | commande conservée, affichée une fois |

## Limites

- Voix de synthèse Piper et bruit synthétique : plafond optimiste, pas une voix humaine dans l'atelier. Les voix « tom » (licence AGPL) et « mls » (inintelligibles même pour `large-v3-turbo` sur une prise propre) sont exclues.
- Réduction de bruit, gain automatique et annulation d'écho du navigateur (`getUserMedia` les demande) non simulés ; ils changent le niveau vu par la porte d'énergie.
- Phrases de confirmation vocale (« Confirme cet affichage ») non mesurées avec le vocabulaire.
- Vues simulées par des clients HTTP : aucun rendu, aucun moniteur.
- Processeur du conteneur (Xeon 2,1 GHz, 4 cœurs) différent du Ryzen 5 5600G de la tour ; GPU non utilisé, comme `voice.py`.
- Chaque mesure vaut pour cet hôte, ce SHA, ce corpus et ces poids.

## Reproduire sur la tour

1. Copier `corpus-voix-2026-11-02.zip` (dossier partagé du projet `banc-voix/`, 47,6 Mo, SHA-256 `f4c7b61f82f46a413d31d91dd1658df51605bbafd698d49726e7c03827ec0f34`) et l'extraire dans `%USERPROFILE%\BOJART\banc-voix\` : on obtient `corpus-2026-11-02\corpus.json` et `envoi\`.
2. Lancer `Mesurer_Voix_BOJART.cmd` : contrôle du décodage audio, accord avant de télécharger `small` épinglé, mesure, puis sonde bruit seul. Rapports dans `%USERPROFILE%\BOJART\banc-voix\rapports\`.
3. Comparer : `python tools/banc_voix.py comparer docs/evidence/voix-2026-11-02/small-reference.json <rapport de la tour>.json`. La comparaison refuse un corpus, des poids ou des réglages de transcription différents.

Prochaine preuve : la même mesure sur la tour, puis des prises au vrai micro dans l'atelier, imprimantes en marche.

## Fichiers

| Fichier | Contenu |
|---|---|
| `corpus-2026-11-02.json` | Manifeste du corpus : empreinte de chaque WAV, voix, code navigateur, outils |
| `small-reference.json` / `.md` | Référence : `small`, code final, LangGraph |
| `small-sans-vocabulaire.json` / `.md` | `small`, réglage d'origine |
| `small-variante-vocabulaire.json` / `.md` | `small`, vocabulaire en variante, avant le changement |
| `base-sans-vocabulaire.json` / `.md` | `base`, réglage d'origine |
| `large-v3-turbo-sans-vocabulaire.json` / `.md` | `large-v3-turbo`, réglage d'origine |
| `small-sans-vocabulaire-repli-regles.json` / `.md` | `small`, repli règles, 80 prises cibles |
| `bruit-seul-small.json` / `.md` | Sonde bruit seul, deux variantes |
