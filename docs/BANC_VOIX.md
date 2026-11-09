# Banc de la chaîne vocale

État du 2 novembre 2026. Le banc rejoue « Affiche le dashboard atelier » et ses variantes **de l'audio au reçu d'affichage**, sans la tour, et mesure chaque étape séparément. Il sert à trouver avant l'installation ce qui casse la voix, puis à comparer les mêmes prises sur la tour.

Résultats datés et limites : [rapport du 2 novembre 2026](evidence/voix-2026-11-02/README.md). Référence à comparer avec la tour : `docs/evidence/voix-2026-11-02/small-reference.json`.

## Ce qui est réellement exécuté

| Étape | Code exécuté | Doublure |
|---|---|---|
| Fin de prise | `voice_endpoint.js` (porte d'énergie) et l'encodeur WAV de `capture.js`, tels quels, dans Node | Flux micro simulé : synthèse vocale Piper + bruit synthétique. Pas de `getUserMedia`, ni réduction de bruit, gain automatique ou annulation d'écho du navigateur |
| Réservation du micro | `POST /api/voice/lease` du vrai serveur | — |
| Transcription | `POST /api/voice/transcribe` → `LocalVoice` → faster-whisper 1.2.1, poids locaux, CPU int8 4 fils (paramètres de `voice.py`, vocabulaire de décodage compris) | — |
| Intention, garde, distribution | `POST /api/jarvis/turn` → `JarvisRuntime` (moteur `sqlite_ready`, ou repli règles avec `--sans-langgraph`) | État du dossier figé au début de la prise, comme `tower_voice.js` |
| Affichage | Trois vues appairées qui suivent le protocole de `tower_screen.js` (événements, poll, accusé) | Aucun rendu : l'accusé reste logiciel |
| Reçu | `GET /api/jarvis/turn`, relu à chaque événement comme la console | — |

Les étapes internes du runtime (intention, garde, distribution, journal) sont chronométrées par instrumentation autour des méthodes existantes, sans modifier leur code. Base temporaire neuve à chaque mesure. Aucun Jev, aucun LLM, aucune imprimante, aucun service distant.

## Corpus

`tools/banc_voix.py corpus` produit 150 prises : 12 phrases × 4 voix françaises Piper (siwis CC-BY, upmc jessica et pierre CC-BY-SA, gilles CC0), cinq ambiances pour la phrase cible (calme, ventilateur à 20 dB, imprimante à 10 dB, atelier fort à 5 dB, voix de fond à 10 dB), deux pour les autres, plus six cas limites (voix faible, saturation, parole coupée, silence, bruit seul, bruit fort seul). Exclues : la voix « tom » (licence AGPL) et les voix « mls », inintelligibles même pour `large-v3-turbo` sur une prise propre. Chaque prise attend un résultat : la bonne vue, ou **aucun affichage** (commande inconnue ou physique, négation, tableau non précisé, formulation hors catalogue).

Les WAV restent hors de Git (politique du dépôt public). Le manifeste `corpus.json` garde l'empreinte SHA-256 de chaque WAV envoyé, des voix, du code navigateur et des outils ; celui du 2 novembre est versionné dans `docs/evidence/voix-2026-11-02/`. Un corpus altéré est refusé. Pour comparer deux machines, rejouer **le même dossier de corpus** : la synthèse Piper n'est pas déterministe. Le corpus du 2 novembre est déposé dans le dossier partagé du projet (`banc-voix/corpus-voix-2026-11-02.zip`).

## Commandes

```sh
# Préparer (une fois) : moteur vocal et modèle épinglé
python -m pip install -r jarvis/requirements-voice.txt -r jarvis/requirements-orchestration.txt
python tools/banc_voix.py modele --nom small --dossier ~/BOJART/modeles/whisper-small --je-confirme-le-telechargement

# Générer un corpus (Piper et Node requis ; déjà fait pour le corpus du 2 novembre)
python tools/banc_voix.py corpus --sortie CORPUS --piper piper --voix DOSSIER_VOIX_PIPER

# Mesurer (rapport JSON + Markdown neufs ; jamais écrasés)
python tools/banc_voix.py mesurer --corpus CORPUS --modele ~/BOJART/modeles/whisper-small --sortie rapports/ --libelle "tour small"

# Bruit seul : la reconnaissance ne doit inventer aucune commande (code 1 sinon)
python tools/banc_voix.py bruit --modele ~/BOJART/modeles/whisper-small --sortie rapports/ --libelle "tour small"

# Comparer deux mesures étape par étape (refuse corpus, poids, variantes ou réglages de transcription différents)
python tools/banc_voix.py comparer reference.json tour.json
```

Options de `mesurer` : `--sans-langgraph` (repli règles), `--variante sans_vocabulaire` (retire le vocabulaire de décodage de `voice.py`, pour comparer avec le réglage d'origine), `--limite N`, `--froids N`, `--sans-scenarios`. Code de sortie 1 si une erreur critique (mauvaise vue, affichage non voulu) ou un cas d'erreur non conforme est observé.

Sur la tour : `Mesurer_Voix_BOJART.cmd` vérifie d'abord le décodage audio avec `tools/verifier_voix.py` (banc de pré-installation, PR #17), demande l'accord avant de télécharger le modèle `small` épinglé, mesure le corpus extrait dans `%USERPROFILE%\BOJART\banc-voix\corpus-2026-11-02`, puis lance la sonde bruit seul.

Le workflow `.github/workflows/voice-bench.yml` génère un corpus de trois voix et mesure `small` sous Linux et Windows ; les cas d'erreur doivent tous être conformes et le moteur d'orchestration doit être `sqlite_ready`.

## Cas d'erreur

Quinze scénarios au niveau de la voix, chacun avec son injection, son attendu et son observation : WAV tronqué, prise trop longue, format non conforme, micro réservé par une autre fenêtre, deux envois simultanés, prise annulée pendant la transcription, contexte ou dossier modifiés pendant la transcription, vue en retard, accusé tardif après changement de contexte, vue absente puis revenue, coupure pendant la distribution, reprise après 120 s, double envoi, redémarrage du serveur avant l'affichage. Après la vraie transcription, ces cas imposent le texte exact de la commande : leur verdict ne dépend pas de la qualité du modèle. Le banc de pré-installation (`bojart_ops/banc_http.py`, PR #17) couvre déjà, en texte, le rejeu, la coupure brutale du serveur, la concurrence et l'annulation ; ici, les mêmes familles sont rejouées après une vraie prise (réservation du micro, transcription, état figé du dossier).

## Lecture des mesures

- **Fin de prise** : temps audio entre la fin de la parole et la décision de la porte d'énergie. Il ne dépend pas de la machine.
- **Transcription** : moteur seul, contrôle du WAV et requête HTTP complète, séparés.
- **Froid** : serveur neuf, chargement du modèle compris ; le cache disque du système reste chaud.
- **Bout en bout** : fin de prise + encodage + transcription + tour + reçu d'affichage.
- Médiane, p95 au rang le plus proche, maximum et effectif `n` ; une mesure vaut pour son hôte, son SHA, son corpus et ses poids.

Ce banc ne qualifie ni le micro de la tour, ni une voix humaine, ni le bruit réel de l'atelier, ni les moniteurs. Ces recettes restent la porte `speech_offline` de `launch_readiness.py`.

## Fin de prise dans le bruit — 9 novembre 2026

Constat du 2 novembre : dès que le bruit d'atelier dépasse le seuil fixe de la porte d'énergie, la prise ne s'arrête qu'à la limite de 15 s (≈ 12 s d'attente après la phrase). `voice_endpoint.js` garde sa règle d'origine, prise par prise, et ajoute une seconde façon de conclure : le fond est mesuré comme la trame de 20 ms la plus calme des 3 dernières secondes ; une fois qu'au moins 0,25 s de trames nettement au-dessus de ce fond (× 2,5) a été entendue, 1,1 s sans trame saillante vaut une pause, même si le bruit reste au-dessus du seuil fixe. Au calme et avec la ventilation, rien ne change.

Mesure avant/après sur le même protocole (114 prises, trois voix Piper, `small` épinglé installé par l'installateur, conteneur Linux) : `docs/evidence/installation-2026-11-09/fin-de-prise-bruit.json`.

| Condition | Prises | Fin médiane après la phrase (avant → après) | Fins ≤ 3 s (après) | Arrêtées par la limite (avant → après) | Correctes (avant → après) |
|---|---:|---|---:|---|---|
| calme | 39 | 1,03 s → 1,02 s | 39 | 0 → 0 | 27 → 29 sur 36 |
| ventilateur | 12 | 1,08 s → 1,03 s | 12 | 0 → 0 | 11 → 10 sur 12 |
| imprimante | 36 | 12,43 s → 3,83 s | 16 | 36 → 11 | 29 → 29 sur 36 |
| atelier fort | 12 | 12,34 s → 2,89 s | 6 | 12 → 3 | 11 → 10 sur 12 |
| voix de fond | 12 | 12,34 s → 12,38 s | 0 | 12 → 12 | 4 → 6 sur 12 |

Erreurs critiques : 0 avant, 0 après ; 87 puis 90 prises correctes sur 114 (la synthèse Piper n'est pas identique au bit près d'une génération à l'autre : ± 2 prises est du bruit de mesure). Aucune prise ne se termine avant la fin de la phrase (délai minimal 0,63 s, voix faible). Sonde bruit seul refaite : 0 commande déclenchée sur 112 flux, comme le 2 novembre. Restent : un tiers des prises avec imprimante attend encore la limite (pas du moteur irréguliers), et une voix de fond est de la parole : elle tient toujours la prise ouverte. À confirmer au vrai micro dans l'atelier, avec les traitements du navigateur.
