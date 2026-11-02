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
