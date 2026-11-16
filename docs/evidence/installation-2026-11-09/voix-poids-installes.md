# Banc vocal — installation integree small

Mesuré du 2026-11-09T22:16:40+00:00 au 2026-11-09T22:18:29+00:00 sur `e224529b2ae80268fcbfa06f8628001ec2627158` (modifications locales).

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v310-x86_64-with-glibc2.39, Python 3.12.3. GPU NVIDIA : aucun détecté.

Orchestration : `sqlite_ready`. ASR : faster-whisper `faster-whisper-small-536b0662`, variante `runtime`. Corpus `71d7020519c541bd…` (40 prises).

## Résultat

Erreurs critiques (mauvaise vue ou affichage non voulu) : **0**.

| Groupe | Prises | Correctes | Issues |
|---|---:|---:|---|
| cible | 40 | 37 | commande_manquee 3, correct 37 |
| froid | 1 | 0 | mesure_a_froid 1 |

## Par condition sonore (phrases du catalogue)

| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |
|---|---:|---:|---:|---|---:|---:|
| atelier_fort | 8 | 8 | 8 | 0 / 8 / 0 | 13 992,6 | 14 763,7 |
| calme | 8 | 8 | 8 | 8 / 0 / 0 | 2 456,4 | 2 544,6 |
| imprimante | 8 | 8 | 8 | 0 / 8 / 0 | 13 904,5 | 14 616,5 |
| parole_fond | 8 | 5 | 5 | 0 / 8 / 0 | 13 957,3 | 14 746,2 |
| ventilateur | 8 | 8 | 8 | 8 / 0 / 0 | 2 509,5 | 4 862,0 |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 40 | 12 080,0 | 12 910,0 | 12 910,0 | 0 | — |
| Encodage WAV navigateur | 40 | 190,3 | 248,6 | 264,6 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 40 | 44,4 | 76,9 | 86,2 | 1 | 9,0 |
| Transcription (moteur faster-whisper) | 40 | 1 316,4 | 1 718,2 | 17 435,5 | 1 | 2 776,5 |
| Transcription (requête HTTP complète) | 40 | 1 352,9 | 1 763,8 | 17 489,0 | 1 | 2 787,8 |
| Intention (routeur local) | 40 | 1,7 | 2,4 | 3,1 | 1 | 1,6 |
| Garde de contexte | 40 | 0,8 | 1,0 | 1,5 | 1 | 0,8 |
| Distribution aux vues | 37 | 8,2 | 11,9 | 14,0 | 1 | 7,0 |
| Journal du tour | 40 | 2,2 | 3,3 | 4,0 | 1 | 2,1 |
| Orchestration (hors nœuds) | 40 | 23,0 | 34,7 | 50,6 | 1 | 33,6 |
| Tour complet (requête HTTP) | 40 | 38,8 | 51,7 | 64,3 | 1 | 46,7 |
| Affichage jusqu’au reçu (client) | 37 | 20,4 | 31,7 | 257,9 | 1 | 16,8 |
| De la fin de prise au reçu | 37 | 1 400,1 | 1 831,6 | 2 346,5 | 1 | 2 851,3 |
| Bout en bout depuis la fin de la parole | 37 | 13 730,3 | 14 746,2 | 14 763,7 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 1 | 985,6 |

## Cas d’erreur : 15/15 conformes

| Cas | Famille | Injection | Attendu | Conforme |
|---|---|---|---|---|
| wav_tronque | coupure | en-tête WAV intact, 4 000 derniers octets perdus | refus 409 « Audio tronqué », aucun tour | oui |
| prise_trop_longue | coupure | 549078 octets (> 15 s) | refus avant lecture du WAV | oui |
| format_non_conforme | coupure | WAV annoncé à 48 kHz | refus 409 du format | oui |
| micro_reserve_ailleurs | coupure | une seconde fenêtre demande le micro | réservation et transcription refusées | oui |
| transcriptions_simultanees | reponse_tardive | deux envois simultanés de la même prise | une transcription acceptée, l’autre refusée sans file d’attente | oui |
| prise_annulee_pendant_transcription | coupure | la fenêtre annule la prise pendant la transcription | transcription écartée, aucun tour | oui |
| contexte_modifie_pendant_transcription | reponse_tardive | le fichier de contexte change pendant la transcription | tour STALE, aucune vue servie | oui |
| dossier_modifie_pendant_transcription | reponse_tardive | une autre fenêtre enregistre une révision du dossier | tour STALE, aucune vue servie | oui |
| ecran_en_retard | reponse_tardive | la vue atelier accuse 3 s après réception | reçu « affiché » seulement après l’accusé (≥ 3 000 ms depuis le tour, horloge du serveur) | oui |
| accuse_tardif_apres_changement | reponse_tardive | le contexte change entre la réception et l’accusé de la vue atelier | accusé refusé, vue « stale », aucun reçu « affiché » | oui |
| ecran_absent_puis_revenu | reponse_tardive | la vue atelier ne demande plus de commande pendant 3 s | pas de reçu pendant l’absence, affichage au retour | oui |
| coupure_pendant_distribution | coupure | la première distribution échoue (OSError) | tour INTERRUPTED, reprise de la même référence : une seule commande, affichée | oui |
| reprise_apres_120_s | reponse_tardive | reprise d’un tour interrompu 121 s après la demande | tour STALE, aucune commande | oui |
| double_envoi | coupure | le même tour est renvoyé après une réponse perdue | même référence, aucune commande supplémentaire | oui |
| redemarrage_avant_affichage | coupure | serveur arrêté puis relancé sur le même dossier avant tout accusé ; vues réappairées | commande conservée, affichée une fois, aucune duplication | oui |

## Prises non conformes (extrait)

| Prise | Entendu | Issue |
|---|---|---|
| A1-gilles-parole_fond | Affiche le dashboard à atelier, penses à vérifier la livraison avant midi, le colis de rés | commande_manquee |
| A2-upmc-pierre-parole_fond | Le collid Fiche le dashboard d'atelier | commande_manquee |
| A2-gilles-parole_fond | Jarvis, affiche le dashboard atelier, le collier de résine arrive demain matin. | commande_manquee |

## Limites

- Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.
- Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.
- Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.
- Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).
- Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.
