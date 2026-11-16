# Banc vocal — conteneur small règles

Mesuré du 2026-11-02T14:53:05+00:00 au 2026-11-02T14:55:09+00:00 sur `3436f5352659554e4bac5af492b94af6c522ed2d` (modifications locales).

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v185-x86_64-with-glibc2.39, Python 3.13.18. GPU NVIDIA : aucun détecté.

Orchestration : `missing_dependency`. ASR : faster-whisper `whisper-small`, variante `runtime`. Corpus `71d7020519c541bd…` (80 prises).

## Résultat

Erreurs critiques (mauvaise vue ou affichage non voulu) : **0**.

| Groupe | Prises | Correctes | Issues |
|---|---:|---:|---|
| cible | 80 | 12 | commande_manquee 68, correct 12 |
| froid | 3 | 0 | mesure_a_froid 3 |

## Par condition sonore (phrases du catalogue)

| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |
|---|---:|---:|---:|---|---:|---:|
| atelier_fort | 16 | 1 | 1 | 0 / 16 / 0 | 13 853,9 | 13 853,9 |
| calme | 16 | 4 | 4 | 16 / 0 / 0 | 2 186,4 | 2 205,1 |
| imprimante | 16 | 2 | 2 | 0 / 16 / 0 | 14 037,6 | 14 216,2 |
| parole_fond | 16 | 1 | 1 | 0 / 16 / 0 | 13 972,7 | 13 972,7 |
| ventilateur | 16 | 4 | 4 | 16 / 0 / 0 | 2 251,2 | 2 820,6 |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 80 | 12 130,0 | 12 910,0 | 13 030,0 | 0 | — |
| Encodage WAV navigateur | 80 | 192,0 | 238,0 | 293,2 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 80 | 38,3 | 48,8 | 61,2 | 3 | 8,8 |
| Transcription (moteur faster-whisper) | 80 | 1 007,8 | 1 217,6 | 5 727,7 | 3 | 2 066,9 |
| Transcription (requête HTTP complète) | 80 | 1 035,5 | 1 257,5 | 5 769,9 | 3 | 2 077,5 |
| Intention (routeur local) | 80 | 2,3 | 3,2 | 4,5 | 3 | 2,4 |
| Garde de contexte | 80 | 0,3 | 0,5 | 2,5 | 3 | 0,4 |
| Distribution aux vues | 12 | 5,1 | 6,1 | 6,1 | 3 | 5,9 |
| Journal du tour | 80 | 1,2 | 5,3 | 6,8 | 3 | 5,8 |
| Orchestration (hors nœuds) | 80 | 6,7 | 10,3 | 11,8 | 3 | 6,2 |
| Tour complet (requête HTTP) | 80 | 13,8 | 21,5 | 24,3 | 3 | 23,6 |
| Affichage jusqu’au reçu (client) | 12 | 21,7 | 35,4 | 35,4 | 3 | 22,1 |
| De la fin de prise au reçu | 12 | 1 052,5 | 1 108,4 | 1 108,4 | 3 | 2 123,8 |
| Bout en bout depuis la fin de la parole | 12 | 2 271,7 | 14 216,2 | 14 216,2 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 3 | 769,5 |

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
| A1-upmc-pierre-parole_fond | affiche le dâche-boute-bâteau-vie | commande_manquee |
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
| … | 28 autres dans le JSON | |

## Limites

- Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.
- Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.
- Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.
- Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).
- Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.
