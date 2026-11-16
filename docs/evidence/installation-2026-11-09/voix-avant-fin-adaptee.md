# Banc vocal — small A-ancien

Mesuré du 2026-11-09T22:32:14+00:00 au 2026-11-09T22:35:24+00:00 sur `e224529b2ae80268fcbfa06f8628001ec2627158` (modifications locales).

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v310-x86_64-with-glibc2.39, Python 3.12.3. GPU NVIDIA : aucun détecté.

Orchestration : `sqlite_ready`. ASR : faster-whisper `faster-whisper-small-536b0662`, variante `runtime`. Corpus `d11aeb0bc6b74a17…` (114 prises).

## Résultat

Erreurs critiques (mauvaise vue ou affichage non voulu) : **0**.

| Groupe | Prises | Correctes | Issues |
|---|---:|---:|---|
| catalogue | 18 | 7 | commande_manquee 11, correct 7 |
| cible | 60 | 45 | commande_manquee 15, correct 45 |
| froid | 1 | 0 | mesure_a_froid 1 |
| hors_catalogue | 12 | 12 | correct 12 |
| interdit | 18 | 18 | correct 18 |
| limite | 6 | 5 | commande_manquee 1, correct 5 |

## Par condition sonore (phrases du catalogue)

| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |
|---|---:|---:|---:|---|---:|---:|
| atelier_fort | 12 | 11 | 11 | 0 / 12 / 0 | 14 057,4 | 14 457,1 |
| calme | 21 | 12 | 12 | 21 / 0 / 0 | 2 464,6 | 2 792,4 |
| imprimante | 21 | 14 | 14 | 0 / 21 / 0 | 14 070,8 | 14 493,3 |
| parole_fond | 12 | 4 | 4 | 0 / 12 / 0 | 13 902,0 | 14 591,6 |
| ventilateur | 12 | 11 | 11 | 12 / 0 / 0 | 2 557,0 | 4 810,6 |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 111 | 11 820,0 | 12 710,0 | 13 240,0 | 0 | — |
| Encodage WAV navigateur | 114 | 222,4 | 359,2 | 413,8 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 114 | 42,4 | 79,3 | 90,4 | 1 | 15,8 |
| Transcription (moteur faster-whisper) | 114 | 1 283,8 | 1 634,3 | 2 360,8 | 1 | 3 297,4 |
| Transcription (requête HTTP complète) | 114 | 1 319,6 | 1 676,6 | 2 453,7 | 1 | 3 315,2 |
| Intention (routeur local) | 110 | 2,0 | 3,1 | 6,7 | 1 | 1,6 |
| Garde de contexte | 110 | 0,7 | 1,1 | 1,6 | 1 | 0,7 |
| Distribution aux vues | 52 | 7,4 | 12,3 | 28,7 | 1 | 9,0 |
| Journal du tour | 110 | 1,6 | 3,3 | 6,2 | 1 | 2,4 |
| Orchestration (hors nœuds) | 110 | 21,7 | 30,2 | 43,2 | 1 | 42,8 |
| Tour complet (requête HTTP) | 110 | 33,7 | 48,8 | 64,7 | 1 | 59,2 |
| Affichage jusqu’au reçu (client) | 52 | 20,1 | 248,5 | 249,4 | 1 | 13,1 |
| De la fin de prise au reçu | 52 | 1 444,3 | 1 689,9 | 1 899,4 | 1 | 3 387,6 |
| Bout en bout depuis la fin de la parole | 52 | 13 519,6 | 14 457,1 | 14 591,6 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 1 | 1 170,2 |

## Cas d’erreur : 15/15 conformes

| Cas | Famille | Injection | Attendu | Conforme |
|---|---|---|---|---|
| wav_tronque | coupure | en-tête WAV intact, 4 000 derniers octets perdus | refus 409 « Audio tronqué », aucun tour | oui |
| prise_trop_longue | coupure | 567254 octets (> 15 s) | refus avant lecture du WAV | oui |
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
| A1-gilles-calme | Affiche le dashboard à l'atelier. | commande_manquee |
| A1-gilles-ventilateur | Affiche le dashboard à l'atelier. | commande_manquee |
| A1-gilles-imprimante | Affiche le dashboard à l'atelier. | commande_manquee |
| A1-gilles-atelier_fort | Affiche le dashboard à la tenue. | commande_manquee |
| A1-gilles-parole_fond | Affiche le dashboard de l'atelier à vérifier la livraison avant-midi. Le collier de Rézena | commande_manquee |
| A1-upmc-jessica-calme | Affiche le dashboard de l'atelier. | commande_manquee |
| A1-upmc-jessica-imprimante | Affiche le dashboard de l'atelier. | commande_manquee |
| A1-upmc-jessica-parole_fond | Affiche le dashboard de l'atelier. | commande_manquee |
| A2-gilles-parole_fond | Jarvis, affiche le dashboard atelier, le collier de résignation avant midi. Le collier de  | commande_manquee |
| A3-gilles-parole_fond | Affiche le tableau de bord à atelier, vérifiez la livraison avant midi. Le colis de résine | commande_manquee |
| A3-upmc-pierre-parole_fond | Affiche le tableau de bord à tolier. | commande_manquee |
| A4-gilles-calme | Montre le dashboard àelier. | commande_manquee |
| A4-gilles-parole_fond | Montre le dashboard atelier, vérifiez la livraison avant midi. Le collier de résénarie, de | commande_manquee |
| A4-upmc-jessica-parole_fond | Montre le dashboard d'atelier. | commande_manquee |
| A4-upmc-pierre-parole_fond | Montre le dashboard d'atelier. | commande_manquee |
| B1-gilles-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-gilles-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-jessica-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-jessica-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-pierre-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-pierre-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B2-gilles-calme | Affiche le dashboard de Studio. | commande_manquee |
| B3-gilles-calme | Affiche les trois dashes longues. | commande_manquee |
| B3-gilles-imprimante | Affiche les trois d'Archelon. | commande_manquee |
| B3-upmc-pierre-calme | Affiche et 3 dashboards. | commande_manquee |
| B3-upmc-pierre-imprimante | Affiche et 3 dashboards. | commande_manquee |
| E-voix-faible-gilles | Affiche le dashboard à l'atelier. | commande_manquee |

## Limites

- Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.
- Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.
- Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.
- Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).
- Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.
