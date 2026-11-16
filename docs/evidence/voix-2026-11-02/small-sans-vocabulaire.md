# Banc vocal — conteneur small LangGraph

Mesuré du 2026-11-02T14:43:44+00:00 au 2026-11-02T14:47:22+00:00 sur `3436f5352659554e4bac5af492b94af6c522ed2d` (modifications locales).

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v185-x86_64-with-glibc2.39, Python 3.13.18. GPU NVIDIA : aucun détecté.

Orchestration : `sqlite_ready`. ASR : faster-whisper `whisper-small`, variante `runtime`. Corpus `71d7020519c541bd…` (150 prises).

## Résultat

Erreurs critiques (mauvaise vue ou affichage non voulu) : **0**.

| Groupe | Prises | Correctes | Issues |
|---|---:|---:|---|
| catalogue | 24 | 6 | commande_manquee 18, correct 6 |
| cible | 80 | 12 | commande_manquee 68, correct 12 |
| froid | 3 | 0 | mesure_a_froid 3 |
| hors_catalogue | 16 | 16 | correct 16 |
| interdit | 24 | 24 | correct 24 |
| limite | 6 | 6 | correct 6 |

## Par condition sonore (phrases du catalogue)

| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |
|---|---:|---:|---:|---|---:|---:|
| atelier_fort | 16 | 1 | 1 | 0 / 16 / 0 | 14 081,6 | 14 081,6 |
| calme | 28 | 7 | 7 | 28 / 0 / 0 | 2 219,5 | 2 397,3 |
| imprimante | 28 | 5 | 5 | 0 / 28 / 0 | 14 439,2 | 14 655,1 |
| parole_fond | 16 | 1 | 1 | 0 / 16 / 0 | 14 172,6 | 14 172,6 |
| ventilateur | 16 | 4 | 4 | 16 / 0 / 0 | 2 364,9 | 2 889,4 |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 147 | 12 080,0 | 12 940,0 | 13 230,0 | 0 | — |
| Encodage WAV navigateur | 150 | 190,5 | 247,7 | 301,3 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 150 | 38,9 | 66,4 | 82,7 | 3 | 8,5 |
| Transcription (moteur faster-whisper) | 150 | 1 132,9 | 1 385,4 | 3 900,0 | 3 | 2 210,0 |
| Transcription (requête HTTP complète) | 150 | 1 173,9 | 1 427,1 | 3 973,1 | 3 | 2 219,8 |
| Intention (routeur local) | 146 | 1,7 | 3,1 | 5,7 | 3 | 1,2 |
| Garde de contexte | 146 | 0,5 | 0,8 | 4,4 | 3 | 0,5 |
| Distribution aux vues | 19 | 5,4 | 19,9 | 19,9 | 3 | 5,8 |
| Journal du tour | 146 | 1,3 | 4,4 | 5,7 | 3 | 3,9 |
| Orchestration (hors nœuds) | 146 | 16,3 | 26,5 | 35,6 | 3 | 22,1 |
| Tour complet (requête HTTP) | 146 | 24,1 | 37,7 | 49,1 | 3 | 36,6 |
| Affichage jusqu’au reçu (client) | 19 | 17,1 | 253,0 | 253,0 | 3 | 27,9 |
| De la fin de prise au reçu | 19 | 1 151,1 | 1 552,0 | 1 552,0 | 3 | 2 284,3 |
| Bout en bout depuis la fin de la parole | 19 | 2 449,5 | 14 655,1 | 14 655,1 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 3 | 769,6 |

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
| A1-siwis-atelier_fort | Affiche le dash pour l'atelier. | commande_manquee |
| A1-siwis-parole_fond | Le colis de résine arrive demain matin, pense à vérifier la livraison avant midi. Le colis | commande_manquee |
| A1-upmc-jessica-calme | Affiche le dash beau d'atelier. | commande_manquee |
| A1-upmc-jessica-ventilateur | affiche le dâche beau d'atelier. | commande_manquee |
| A1-upmc-jessica-imprimante | affiche le dâche beau d'atelier | commande_manquee |
| A1-upmc-jessica-atelier_fort | affiche le dage baudateux | commande_manquee |
| A1-upmc-jessica-parole_fond | affiche le dage dans l'atelier | commande_manquee |
| A1-upmc-pierre-calme | affiche le dashboot-batovier | commande_manquee |
| A1-upmc-pierre-ventilateur | affiche le dashboard bâtovier. | commande_manquee |
| A1-upmc-pierre-imprimante | affiche le dash bout-bâteau-vier | commande_manquee |
| A1-upmc-pierre-atelier_fort | affiches de daches ou de bateaux d'huile | commande_manquee |
| A1-upmc-pierre-parole_fond | Le collier de résine arrive demain matin. | commande_manquee |
| A1-gilles-ventilateur | Affichent le dashboard atelier. | commande_manquee |
| A1-gilles-imprimante | Affichent le dashboard atelier. | commande_manquee |
| A1-gilles-atelier_fort | Affichent le dashboard atelier. | commande_manquee |
| A1-gilles-parole_fond | affichent le dashboard à l'atelier. | commande_manquee |
| A2-siwis-calme | Jarvie affiche le dashboard atelier. | commande_manquee |
| A2-siwis-ventilateur | Jarvis affiche le dage beau d'atelier. | commande_manquee |
| A2-siwis-imprimante | Jarvie affiche le dâge beau d'atelier. | commande_manquee |
| A2-siwis-atelier_fort | Jarvis affiche le dage beau d'atelier. | commande_manquee |
| A2-siwis-parole_fond | Jarvie affiche le dâge beau-d'atelier. | commande_manquee |
| A2-upmc-jessica-calme | Jarvis affiche le dinge beau d'atelier. | commande_manquee |
| A2-upmc-jessica-ventilateur | Jarvis affiche le dinge beau d'atelier. | commande_manquee |
| A2-upmc-jessica-imprimante | J'arrive à afficher le dage bout d'atelier. | commande_manquee |
| A2-upmc-jessica-atelier_fort | Jardis affiche le dinge bouddha tenu | commande_manquee |
| A2-upmc-jessica-parole_fond | Le colis de résine arrive demain matin. Pense à vérifier la livraison avant midi. | commande_manquee |
| A2-upmc-pierre-calme | Jarvis, affiche le dash beau d'atelier. | commande_manquee |
| A2-upmc-pierre-ventilateur | Jarvis, affiche le dash beau d'atelier. | commande_manquee |
| A2-upmc-pierre-imprimante | Jarvis, affiche le dache beau d'atelier. | commande_manquee |
| A2-upmc-pierre-atelier_fort | Jarvis, affiche le dache beau d'atelier. | commande_manquee |
| A2-upmc-pierre-parole_fond | Le colis de résine arrive demain matin. A fiche le dâche Baudatoisier. Le colis de résine  | commande_manquee |
| A2-gilles-calme | J'arrivée, t'affiche le dachement de la tuyée. | commande_manquee |
| A2-gilles-ventilateur | J'arrive vite à fichre le dachement de la tuyée. | commande_manquee |
| A2-gilles-imprimante | J'ai envie d'afficher le dashboard à tuyer. | commande_manquee |
| A2-gilles-atelier_fort | J'en revis, affiche le dache-bois-dratille. | commande_manquee |
| A2-gilles-parole_fond | Le colis de résine arribe demain matin, pense à vérifier la livraison avant midi. | commande_manquee |
| A3-siwis-imprimante | Affiche le tableau de bord à tenuier. | commande_manquee |
| A3-upmc-jessica-calme | Affiche le tableau de bord à tolis. | commande_manquee |
| A3-upmc-jessica-ventilateur | affiche le tableau de bord à tolier. | commande_manquee |
| A3-upmc-jessica-imprimante | affiche le tableau de bord à tenir. | commande_manquee |
| … | 46 autres dans le JSON | |

## Limites

- Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.
- Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.
- Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.
- Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).
- Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.
