# Banc vocal — conteneur small vocabulaire

Mesuré du 2026-11-02T14:47:23+00:00 au 2026-11-02T14:51:02+00:00 sur `3436f5352659554e4bac5af492b94af6c522ed2d` (modifications locales).

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v185-x86_64-with-glibc2.39, Python 3.13.18. GPU NVIDIA : aucun détecté.

Orchestration : `sqlite_ready`. ASR : faster-whisper `whisper-small`, variante `vocabulaire`. Corpus `71d7020519c541bd…` (150 prises).

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
| atelier_fort | 16 | 13 | 13 | 0 / 16 / 0 | 13 935,8 | 14 637,4 |
| calme | 28 | 21 | 21 | 28 / 0 / 0 | 2 253,6 | 2 403,5 |
| imprimante | 28 | 20 | 20 | 0 / 28 / 0 | 14 034,1 | 14 425,1 |
| parole_fond | 16 | 7 | 7 | 0 / 16 / 0 | 14 173,5 | 14 469,1 |
| ventilateur | 16 | 15 | 15 | 16 / 0 / 0 | 2 438,4 | 4 798,4 |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 147 | 12 080,0 | 12 940,0 | 13 230,0 | 0 | — |
| Encodage WAV navigateur | 150 | 190,5 | 247,7 | 301,3 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 150 | 38,8 | 68,8 | 82,5 | 3 | 8,8 |
| Transcription (moteur faster-whisper) | 150 | 1 079,9 | 1 344,5 | 11 218,4 | 3 | 2 517,2 |
| Transcription (requête HTTP complète) | 150 | 1 112,0 | 1 401,9 | 11 257,9 | 3 | 2 530,2 |
| Intention (routeur local) | 146 | 1,4 | 2,6 | 4,5 | 3 | 1,1 |
| Garde de contexte | 146 | 0,5 | 0,7 | 1,4 | 3 | 0,5 |
| Distribution aux vues | 77 | 5,9 | 12,9 | 15,8 | 3 | 5,8 |
| Journal du tour | 146 | 2,0 | 4,8 | 12,7 | 3 | 2,5 |
| Orchestration (hors nœuds) | 146 | 16,7 | 25,5 | 56,7 | 3 | 24,1 |
| Tour complet (requête HTTP) | 146 | 28,4 | 40,2 | 71,4 | 3 | 35,9 |
| Affichage jusqu’au reçu (client) | 77 | 18,1 | 31,3 | 258,6 | 3 | 17,7 |
| De la fin de prise au reçu | 77 | 1 237,2 | 1 458,9 | 1 554,5 | 3 | 2 588,0 |
| Bout en bout depuis la fin de la parole | 77 | 13 139,6 | 14 425,5 | 14 637,4 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 3 | 846,7 |

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
| A2-upmc-pierre-parole_fond | Le collier de résine arrive demain matin. Afiche le dash beau d'atelier. Le collier de rés | commande_manquee |
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
