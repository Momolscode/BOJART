# Banc vocal — small C-adaptatif2

Mesuré du 2026-11-09T22:28:56+00:00 au 2026-11-09T22:32:13+00:00 sur `e224529b2ae80268fcbfa06f8628001ec2627158` (modifications locales).

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v310-x86_64-with-glibc2.39, Python 3.12.3. GPU NVIDIA : aucun détecté.

Orchestration : `sqlite_ready`. ASR : faster-whisper `faster-whisper-small-536b0662`, variante `runtime`. Corpus `daf6342acf518dd7…` (114 prises).

## Résultat

Erreurs critiques (mauvaise vue ou affichage non voulu) : **0**.

| Groupe | Prises | Correctes | Issues |
|---|---:|---:|---|
| catalogue | 18 | 8 | commande_manquee 10, correct 8 |
| cible | 60 | 46 | commande_manquee 14, correct 46 |
| froid | 1 | 0 | mesure_a_froid 1 |
| hors_catalogue | 12 | 12 | correct 12 |
| interdit | 18 | 18 | correct 18 |
| limite | 6 | 6 | correct 6 |

## Par condition sonore (phrases du catalogue)

| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |
|---|---:|---:|---:|---|---:|---:|
| atelier_fort | 12 | 10 | 10 | 9 / 3 / 0 | 8 356,2 | 14 349,1 |
| calme | 21 | 14 | 14 | 21 / 0 / 0 | 2 486,9 | 2 703,8 |
| imprimante | 21 | 14 | 14 | 15 / 6 / 0 | 6 105,8 | 14 427,7 |
| parole_fond | 12 | 6 | 6 | 0 / 12 / 0 | 14 355,3 | 16 437,3 |
| ventilateur | 12 | 10 | 10 | 12 / 0 / 0 | 2 480,0 | 2 746,0 |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 111 | 1 076,0 | 12 510,0 | 12 890,0 | 0 | — |
| Encodage WAV navigateur | 114 | 88,7 | 373,4 | 419,8 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 114 | 17,3 | 67,2 | 92,5 | 1 | 10,9 |
| Transcription (moteur faster-whisper) | 114 | 1 347,9 | 1 607,6 | 3 912,7 | 1 | 3 221,2 |
| Transcription (requête HTTP complète) | 114 | 1 379,1 | 1 671,7 | 3 960,0 | 1 | 3 234,6 |
| Intention (routeur local) | 110 | 2,0 | 3,8 | 6,1 | 1 | 1,5 |
| Garde de contexte | 110 | 0,8 | 1,2 | 1,8 | 1 | 0,8 |
| Distribution aux vues | 55 | 8,1 | 19,6 | 26,7 | 1 | 6,0 |
| Journal du tour | 110 | 1,5 | 3,3 | 6,6 | 1 | 2,6 |
| Orchestration (hors nœuds) | 110 | 21,8 | 33,1 | 42,1 | 1 | 36,9 |
| Tour complet (requête HTTP) | 110 | 32,7 | 52,3 | 56,2 | 1 | 51,6 |
| Affichage jusqu’au reçu (client) | 55 | 18,8 | 52,0 | 255,4 | 1 | 16,8 |
| De la fin de prise au reçu | 55 | 1 445,5 | 1 726,3 | 4 018,0 | 1 | 3 303,0 |
| Bout en bout depuis la fin de la parole | 55 | 2 703,8 | 14 427,7 | 16 437,3 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 1 | 1 272,9 |

## Cas d’erreur : 15/15 conformes

| Cas | Famille | Injection | Attendu | Conforme |
|---|---|---|---|---|
| wav_tronque | coupure | en-tête WAV intact, 4 000 derniers octets perdus | refus 409 « Audio tronqué », aucun tour | oui |
| prise_trop_longue | coupure | 562646 octets (> 15 s) | refus avant lecture du WAV | oui |
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
| A1-gilles-parole_fond | Affiche le dashboard atelier, pense à vérifier la livraison avant midi. Le collid résine à | commande_manquee |
| A1-upmc-jessica-calme | Affiche le dashboard à deux. | commande_manquee |
| A1-upmc-jessica-ventilateur | Affiche le dashboard. | commande_manquee |
| A1-upmc-jessica-imprimante | Affiche le dashboard. | commande_manquee |
| A1-upmc-jessica-atelier_fort | Affiche le dashboard. | commande_manquee |
| A1-upmc-jessica-parole_fond | Affiche le dashboard. | commande_manquee |
| A2-gilles-parole_fond | Jarvis affiche le dashboard atelier, la livraison avant midi. Le collide résine à la vive  | commande_manquee |
| A2-upmc-pierre-parole_fond | Jarvis, affiche le dashboard à l'atelier. | commande_manquee |
| A3-gilles-parole_fond | Affiche le tableau de bord à tevier, à vérifier la livraison avant midi. Le collide résine | commande_manquee |
| A4-gilles-calme | Montre le dashboard de l'atelier. | commande_manquee |
| A4-gilles-ventilateur | Montre le dashboard de l'atelier. | commande_manquee |
| A4-gilles-imprimante | Montre le dashboard de l'atelier. | commande_manquee |
| A4-gilles-atelier_fort | Montre le dashboard de l'Atelier. | commande_manquee |
| A4-gilles-parole_fond | Montre le dashboard de l'atelier, pense à vérifier la livraison avant midi. Le collide rés | commande_manquee |
| B1-gilles-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-gilles-imprimante | Affiche le dashboard de dossier. | commande_manquee |
| B1-upmc-jessica-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-jessica-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-pierre-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-pierre-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B2-gilles-calme | Affiche le dashboard de Studio. | commande_manquee |
| B2-gilles-imprimante | Affiche le dashboard de Studio. | commande_manquee |
| B3-gilles-calme | Affiche les trois dashes ondes. | commande_manquee |
| B3-gilles-imprimante | Affiche les trois dash-longs. | commande_manquee |

## Limites

- Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.
- Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.
- Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.
- Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).
- Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.
