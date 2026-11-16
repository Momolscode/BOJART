# Banc vocal — conteneur large-v3-turbo LangGraph

Mesuré du 2026-11-02T14:55:10+00:00 au 2026-11-02T15:06:36+00:00 sur `3436f5352659554e4bac5af492b94af6c522ed2d` (modifications locales).

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v185-x86_64-with-glibc2.39, Python 3.13.18. GPU NVIDIA : aucun détecté.

Orchestration : `sqlite_ready`. ASR : faster-whisper `whisper-large-v3-turbo`, variante `runtime`. Corpus `71d7020519c541bd…` (150 prises).

## Résultat

Erreurs critiques (mauvaise vue ou affichage non voulu) : **0**.

| Groupe | Prises | Correctes | Issues |
|---|---:|---:|---|
| catalogue | 24 | 9 | commande_manquee 15, correct 9 |
| cible | 80 | 43 | commande_manquee 37, correct 43 |
| froid | 3 | 0 | mesure_a_froid 3 |
| hors_catalogue | 16 | 16 | correct 16 |
| interdit | 24 | 24 | correct 24 |
| limite | 6 | 6 | correct 6 |

## Par condition sonore (phrases du catalogue)

| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |
|---|---:|---:|---:|---|---:|---:|
| atelier_fort | 16 | 8 | 8 | 0 / 16 / 0 | 16 838,5 | 17 348,3 |
| calme | 28 | 15 | 15 | 28 / 0 / 0 | 5 160,3 | 5 708,9 |
| imprimante | 28 | 12 | 12 | 0 / 28 / 0 | 16 907,2 | 17 544,7 |
| parole_fond | 16 | 7 | 7 | 0 / 16 / 0 | 16 699,7 | 17 504,1 |
| ventilateur | 16 | 10 | 10 | 16 / 0 / 0 | 5 458,9 | 6 839,3 |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 147 | 12 080,0 | 12 940,0 | 13 230,0 | 0 | — |
| Encodage WAV navigateur | 150 | 190,5 | 247,7 | 301,3 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 150 | 38,2 | 50,2 | 63,9 | 3 | 9,0 |
| Transcription (moteur faster-whisper) | 150 | 3 949,4 | 4 540,4 | 5 648,6 | 3 | 9 489,8 |
| Transcription (requête HTTP complète) | 150 | 3 982,4 | 4 550,3 | 5 687,5 | 3 | 9 505,8 |
| Intention (routeur local) | 146 | 1,5 | 2,7 | 22,9 | 3 | 1,2 |
| Garde de contexte | 146 | 0,5 | 0,7 | 0,9 | 3 | 0,7 |
| Distribution aux vues | 53 | 5,4 | 13,3 | 22,0 | 3 | 5,2 |
| Journal du tour | 146 | 1,2 | 4,6 | 6,1 | 3 | 1,9 |
| Orchestration (hors nœuds) | 146 | 15,5 | 26,0 | 40,3 | 3 | 22,2 |
| Tour complet (requête HTTP) | 146 | 24,4 | 38,2 | 52,6 | 3 | 32,4 |
| Affichage jusqu’au reçu (client) | 53 | 14,7 | 252,1 | 257,1 | 3 | 14,1 |
| De la fin de prise au reçu | 53 | 4 062,9 | 4 537,4 | 4 589,3 | 3 | 9 550,4 |
| Bout en bout depuis la fin de la parole | 53 | 16 073,1 | 17 500,3 | 17 544,7 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 3 | 5 015,7 |

## Cas d’erreur : 15/15 conformes

| Cas | Famille | Injection | Attendu | Conforme |
|---|---|---|---|---|
| wav_tronque | coupure | en-tête WAV intact, 4 000 derniers octets perdus | refus 409 « Audio tronqué », aucun tour | oui |
| prise_trop_longue | coupure | 549078 octets (> 15 s) | refus avant transcription | oui |
| format_non_conforme | coupure | WAV annoncé à 48 kHz | refus 409 du format | oui |
| micro_reserve_ailleurs | coupure | une seconde fenêtre demande le micro | réservation et transcription refusées | oui |
| transcriptions_simultanees | reponse_tardive | deux envois simultanés de la même prise | une transcription acceptée, l’autre refusée sans file d’attente | oui |
| prise_annulee_pendant_transcription | coupure | la fenêtre annule la prise pendant la transcription | transcription écartée, aucun tour | oui |
| contexte_modifie_pendant_transcription | reponse_tardive | le fichier de contexte change pendant la transcription | tour STALE, aucune vue servie | oui |
| dossier_modifie_pendant_transcription | reponse_tardive | une autre fenêtre enregistre une révision du dossier | tour STALE, aucune vue servie | oui |
| ecran_en_retard | reponse_tardive | la vue atelier accuse 3 s après réception | reçu « affiché » seulement après l’accusé (≥ 3 000 ms) | oui |
| accuse_tardif_apres_changement | reponse_tardive | le contexte change entre la réception et l’accusé de la vue atelier | accusé refusé, vue « stale », aucun reçu « affiché » | oui |
| ecran_absent_puis_revenu | reponse_tardive | la vue atelier ne demande plus de commande pendant 3 s | pas de reçu pendant l’absence, affichage au retour | oui |
| coupure_pendant_distribution | coupure | la première distribution échoue (OSError) | tour INTERRUPTED, reprise de la même référence : une seule commande, affichée | oui |
| reprise_apres_120_s | reponse_tardive | reprise d’un tour interrompu 121 s après la demande | tour STALE, aucune commande | oui |
| double_envoi | coupure | le même tour est renvoyé après une réponse perdue | même référence, aucune commande supplémentaire | oui |
| redemarrage_avant_affichage | coupure | serveur arrêté puis relancé sur le même dossier avant tout accusé ; vues réappairées | commande conservée, affichée une fois, aucune duplication | oui |

## Prises non conformes (extrait)

| Prise | Entendu | Issue |
|---|---|---|
| A1-siwis-parole_fond | Affiche le dashboard d'atelier. | commande_manquee |
| A1-upmc-jessica-imprimante | Affiche le dashboard d'atelier. | commande_manquee |
| A1-upmc-jessica-parole_fond | Affiche le dashboard d'atelier. | commande_manquee |
| A1-upmc-pierre-calme | Affiche le dashboard battevier. | commande_manquee |
| A1-upmc-pierre-ventilateur | Affiche le dashboard battevier. | commande_manquee |
| A1-upmc-pierre-imprimante | Affiche le dashboard battevier. | commande_manquee |
| A1-upmc-pierre-atelier_fort | Affiche le dashboard bateau de vie. | commande_manquee |
| A1-upmc-pierre-parole_fond | le colis de résine arrive demain matin, pense vérifier la livraison avant | commande_manquee |
| A1-gilles-imprimante | affichent le Dashboard Atelier. | commande_manquee |
| A1-gilles-atelier_fort | affiche le dashboard à atelier. | commande_manquee |
| A2-siwis-calme | Jarvi affiche le dashboard atelier. | commande_manquee |
| A2-siwis-ventilateur | Jarvi affiche le dashboard atelier. | commande_manquee |
| A2-siwis-imprimante | Jarvi affiche le dashboard atelier. | commande_manquee |
| A2-siwis-atelier_fort | Jarvi affiche le dashboard atelier. | commande_manquee |
| A2-upmc-jessica-calme | Jarvi affiche le dashboard d'atelier. | commande_manquee |
| A2-upmc-jessica-ventilateur | Jarvie affiche le dashboard atelier. | commande_manquee |
| A2-upmc-jessica-imprimante | Jarvi affiche le dashboard d'atelier. | commande_manquee |
| A2-upmc-jessica-atelier_fort | Jarvis affiche le dashboard d'atelier. | commande_manquee |
| A2-upmc-jessica-parole_fond | Jarvis affiche le dashboard d'atelier. | commande_manquee |
| A2-upmc-pierre-calme | Jarvie affiche le dash beau d'atelier. | commande_manquee |
| A2-upmc-pierre-ventilateur | Jarvie affiche le dashboard d'atelier. | commande_manquee |
| A2-upmc-pierre-imprimante | Jarvie affiche le dash beau d'atelier. | commande_manquee |
| A2-upmc-pierre-atelier_fort | Jarvis affiche le dash beau d'atelier. | commande_manquee |
| A2-upmc-pierre-parole_fond | Jarvis affiche le dash Baudatelier. | commande_manquee |
| A2-gilles-calme | Jarvis t'affiche le dashboard de l'atelier. | commande_manquee |
| A2-gilles-ventilateur | Jarovie t'affiche le dashboard de l'atelier. | commande_manquee |
| A2-gilles-imprimante | Jaravi affiche le dashboard atelier. | commande_manquee |
| A2-gilles-atelier_fort | Jalovie affiche le dashboard atelier. | commande_manquee |
| A2-gilles-parole_fond | le colis de résine arrive demain matin | commande_manquee |
| A3-gilles-atelier_fort | affiche le tableau de bord à tailler. | commande_manquee |
| A3-gilles-parole_fond | affiche le tableau de bord atelier pense vérifier la livraison avant midi le colis de rési | commande_manquee |
| A4-upmc-pierre-calme | Montre le tâche pour l'atelier. | commande_manquee |
| A4-upmc-pierre-ventilateur | Montre le tâche pour l'atelier. | commande_manquee |
| A4-upmc-pierre-imprimante | Montre le tâche pour l'atelier. | commande_manquee |
| A4-upmc-pierre-atelier_fort | Montre le tâche pour l'atelier. | commande_manquee |
| A4-upmc-pierre-parole_fond | Montre le tâche pour l'atelier. | commande_manquee |
| A4-gilles-parole_fond | le colis de résine arrive demain matin | commande_manquee |
| B1-siwis-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-siwis-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-jessica-calme | Affiche le dashboard de dossier. | commande_manquee |
| … | 12 autres dans le JSON | |

## Limites

- Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.
- Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.
- Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.
- Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).
- Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.
