# Banc vocal — conteneur small (référence)

Mesuré du 2026-11-02T15:09:47+00:00 au 2026-11-02T15:13:05+00:00 sur `dad184c1d5150fba9e7958eebbed3c86a49cd98a`.

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v185-x86_64-with-glibc2.39, Python 3.13.18. GPU NVIDIA : aucun détecté.

Orchestration : `sqlite_ready`. ASR : faster-whisper `whisper-small`, variante `runtime`. Corpus `71d7020519c541bd…` (150 prises).

## Résultat

Erreurs critiques (mauvaise vue ou affichage non voulu) : **0**.

| Groupe | Prises | Correctes | Issues |
|---|---:|---:|---|
| catalogue | 24 | 11 | commande_manquee 13, correct 11 |
| cible | 80 | 65 | commande_manquee 15, correct 65 |
| froid | 3 | 0 | mesure_a_froid 3 |
| hors_catalogue | 16 | 16 | correct 16 |
| interdit | 24 | 24 | correct 24 |
| limite | 6 | 6 | correct 6 |

## Par condition sonore (phrases du catalogue)

| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |
|---|---:|---:|---:|---|---:|---:|
| atelier_fort | 16 | 13 | 13 | 0 / 16 / 0 | 13 772,8 | 14 309,0 |
| calme | 28 | 21 | 21 | 28 / 0 / 0 | 2 164,5 | 2 367,4 |
| imprimante | 28 | 20 | 20 | 0 / 28 / 0 | 13 877,5 | 14 217,1 |
| parole_fond | 16 | 7 | 7 | 0 / 16 / 0 | 13 939,2 | 14 336,1 |
| ventilateur | 16 | 15 | 15 | 16 / 0 / 0 | 2 289,9 | 4 538,1 |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 147 | 12 080,0 | 12 940,0 | 13 230,0 | 0 | — |
| Encodage WAV navigateur | 150 | 190,5 | 247,7 | 301,3 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 150 | 38,1 | 47,8 | 78,1 | 3 | 8,6 |
| Transcription (moteur faster-whisper) | 150 | 1 001,3 | 1 184,5 | 6 643,4 | 3 | 2 067,0 |
| Transcription (requête HTTP complète) | 150 | 1 029,1 | 1 224,0 | 6 683,9 | 3 | 2 077,0 |
| Intention (routeur local) | 146 | 1,3 | 2,3 | 7,3 | 3 | 1,1 |
| Garde de contexte | 146 | 0,5 | 0,7 | 1,1 | 3 | 0,5 |
| Distribution aux vues | 77 | 5,2 | 11,1 | 11,8 | 3 | 4,9 |
| Journal du tour | 146 | 1,9 | 4,5 | 6,5 | 3 | 3,8 |
| Orchestration (hors nœuds) | 146 | 15,6 | 23,1 | 36,2 | 3 | 18,4 |
| Tour complet (requête HTTP) | 146 | 25,8 | 35,1 | 49,3 | 3 | 30,6 |
| Affichage jusqu’au reçu (client) | 77 | 16,2 | 30,4 | 254,7 | 3 | 20,8 |
| De la fin de prise au reçu | 77 | 1 090,2 | 1 290,0 | 1 347,5 | 3 | 2 131,4 |
| Bout en bout depuis la fin de la parole | 77 | 12 918,1 | 14 217,1 | 14 336,1 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 3 | 775,4 |

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
| A1-gilles-parole_fond | Affiche le dashboard à atelier, penses à vérifier la livraison avant midi, le colis de rés | commande_manquee |
| A2-upmc-pierre-parole_fond | Jarvis affiche le dashboard atelier, le collier de résine arrive demain matin. Pense à vér | commande_manquee |
| A2-gilles-parole_fond | Jarvis, affiche le dashboard atelier, le collier de résine arrive demain matin. | commande_manquee |
| A3-siwis-parole_fond | Affiche le tableau de bord atelier, pense à vérifier la livraison avant midi, le colis de  | commande_manquee |
| A3-upmc-jessica-parole_fond | Affiche le tableau de bord atelier, le colis de résine arribe demain matin. | commande_manquee |
| A3-upmc-pierre-atelier_fort | Affiche le tableau de bord à tolier. | commande_manquee |
| A3-upmc-pierre-parole_fond | Affiche le tableau de bord à tolis, le colis de résine arribe demain matin. | commande_manquee |
| A3-gilles-atelier_fort | Affiche le tableau de bar atelier. | commande_manquee |
| A3-gilles-parole_fond | Affiche le tableau de bord àelier. Pense à vérifier la livraison avant midi. Le colis de r | commande_manquee |
| A4-upmc-pierre-calme | Montre le tâche pour d'atelier. | commande_manquee |
| A4-upmc-pierre-ventilateur | Montre le tâche pour d'atelier. | commande_manquee |
| A4-upmc-pierre-imprimante | Montre le tâche pour d'atelier. | commande_manquee |
| A4-upmc-pierre-atelier_fort | Montre le tâche pour l'atelier. | commande_manquee |
| A4-upmc-pierre-parole_fond | Montre le tâche pour l'atelier. | commande_manquee |
| A4-gilles-parole_fond | Le colis de résine arribe, demain matin, passe à vérifier la livraison avant midi. | commande_manquee |
| B1-siwis-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-siwis-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-jessica-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-jessica-imprimante | Affiche le dashboard de dossier. | commande_manquee |
| B1-upmc-pierre-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-upmc-pierre-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B1-gilles-calme | Affiche le dashboard dossier. | commande_manquee |
| B1-gilles-imprimante | Affiche le dashboard dossier. | commande_manquee |
| B2-gilles-calme | Affiche le dashboard de Studio. | commande_manquee |
| B2-gilles-imprimante | Affiche le dashboard de Studio. | commande_manquee |
| B3-upmc-pierre-imprimante | Affiche les trois dashes bonnes. | commande_manquee |
| B3-gilles-calme | Affiche les trois d'achévanse. | commande_manquee |
| B3-gilles-imprimante | Affiche les trois d'achelons. | commande_manquee |

## Limites

- Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.
- Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.
- Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.
- Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).
- Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.
