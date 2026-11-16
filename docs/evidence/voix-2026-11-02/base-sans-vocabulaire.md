# Banc vocal — conteneur base LangGraph

Mesuré du 2026-11-02T14:51:03+00:00 au 2026-11-02T14:53:05+00:00 sur `3436f5352659554e4bac5af492b94af6c522ed2d` (modifications locales).

Hôte : Intel(R) Xeon(R) Processor @ 2.10GHz, 4 cœurs logiques, 15.7 Go, Linux-6.18.44-fc-v185-x86_64-with-glibc2.39, Python 3.13.18. GPU NVIDIA : aucun détecté.

Orchestration : `sqlite_ready`. ASR : faster-whisper `whisper-base`, variante `runtime`. Corpus `71d7020519c541bd…` (150 prises).

## Résultat

Erreurs critiques (mauvaise vue ou affichage non voulu) : **0**.

| Groupe | Prises | Correctes | Issues |
|---|---:|---:|---|
| catalogue | 24 | 3 | commande_manquee 21, correct 3 |
| cible | 80 | 0 | commande_manquee 80 |
| froid | 3 | 0 | mesure_a_froid 3 |
| hors_catalogue | 16 | 16 | correct 16 |
| interdit | 24 | 24 | correct 24 |
| limite | 6 | 6 | correct 6 |

## Par condition sonore (phrases du catalogue)

| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |
|---|---:|---:|---:|---|---:|---:|
| atelier_fort | 16 | 0 | 0 | 0 / 16 / 0 | — | — |
| calme | 28 | 2 | 2 | 28 / 0 / 0 | 1 626,6 | 1 641,7 |
| imprimante | 28 | 1 | 1 | 0 / 28 / 0 | 13 138,0 | 13 138,0 |
| parole_fond | 16 | 0 | 0 | 0 / 16 / 0 | — | — |
| ventilateur | 16 | 0 | 0 | 16 / 0 / 0 | — | — |

## Latence par étape (ms)

| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |
|---|---:|---:|---:|---:|---:|---:|
| Fin de prise après la parole (porte d’énergie, temps audio) | 147 | 12 080,0 | 12 940,0 | 13 230,0 | 0 | — |
| Encodage WAV navigateur | 150 | 190,5 | 247,7 | 301,3 | 0 | — |
| Contrôle du WAV (voice.validate_audio) | 150 | 38,8 | 62,4 | 82,3 | 3 | 8,5 |
| Transcription (moteur faster-whisper) | 150 | 508,3 | 1 516,0 | 2 111,7 | 3 | 982,3 |
| Transcription (requête HTTP complète) | 150 | 540,5 | 1 562,1 | 2 155,5 | 3 | 992,6 |
| Intention (routeur local) | 146 | 1,6 | 2,6 | 3,2 | 3 | 1,3 |
| Garde de contexte | 146 | 0,5 | 0,8 | 1,1 | 3 | 0,5 |
| Distribution aux vues | 4 | 5,8 | 6,9 | 6,9 | 3 | 5,5 |
| Journal du tour | 146 | 1,0 | 2,3 | 5,6 | 3 | 4,3 |
| Orchestration (hors nœuds) | 146 | 16,6 | 25,3 | 32,6 | 3 | 22,5 |
| Tour complet (requête HTTP) | 146 | 23,1 | 32,9 | 39,1 | 3 | 34,7 |
| Affichage jusqu’au reçu (client) | 4 | 18,2 | 32,1 | 32,1 | 3 | 17,4 |
| De la fin de prise au reçu | 4 | 557,3 | 616,5 | 616,5 | 3 | 1 044,2 |
| Bout en bout depuis la fin de la parole | 4 | 3 136,4 | 13 138,0 | 13 138,0 | 0 | — |
| Chargement du modèle (froid) | 0 | — | — | — | 3 | 330,1 |

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
| A1-siwis-calme | Affiche le dashbeau d'atelier. | commande_manquee |
| A1-siwis-ventilateur | A fish le dash peut d'atelier. | commande_manquee |
| A1-siwis-imprimante | affiche le dashbeau d'atelier. | commande_manquee |
| A1-siwis-atelier_fort | A fish le dashre d'atelier. | commande_manquee |
| A1-siwis-parole_fond | Le colis d'affiches le dashe peut d'atomer. Pense à vérifier la livraison avant midi. Le c | commande_manquee |
| A1-upmc-jessica-calme | Affiche le dashbeau d'atelier. | commande_manquee |
| A1-upmc-jessica-ventilateur | à fiche le dash beau d'atelier. | commande_manquee |
| A1-upmc-jessica-imprimante | à fiche le Dashboard à tevis. | commande_manquee |
| A1-upmc-jessica-atelier_fort | Affiche le bâge bout de la teveux. | commande_manquee |
| A1-upmc-jessica-parole_fond | A fiche, le Dajbo d'Atoly. Pense à vérifier la livraison avant midi. Le colis de Rézin arr | commande_manquee |
| A1-upmc-pierre-calme | A fiche, le Dash bout bâteau vier. | commande_manquee |
| A1-upmc-pierre-ventilateur | A fiche, le dache bout batovié. | commande_manquee |
| A1-upmc-pierre-imprimante | En finit, le dash bout de bateau vire. | commande_manquee |
| A1-upmc-pierre-atelier_fort | à fiche, il va toujours être d'autant dix. | commande_manquee |
| A1-upmc-pierre-parole_fond | Le colis de l'hiveraison, avant midi, le colis de raisines arrivent demain matin. | commande_manquee |
| A1-gilles-calme | Affiche le dashbon à ta vie. | commande_manquee |
| A1-gilles-ventilateur | à fichir le dashbole à ta vie. | commande_manquee |
| A1-gilles-imprimante | à fiches le dashbole à t'aillis. | commande_manquee |
| A1-gilles-atelier_fort | Affichez-le d'asphole, a-t-il. | commande_manquee |
| A1-gilles-parole_fond | Le colis affichent le dashboard à telier Le colis de Rézin arrivent demain matin Le colis  | commande_manquee |
| A2-siwis-calme | Jarvi, affiche le dage beau d'atelier. | commande_manquee |
| A2-siwis-ventilateur | J'arvi à fiche le dache beau d'atelier. | commande_manquee |
| A2-siwis-imprimante | J'arvi à fiche le dache beau d'atelier. | commande_manquee |
| A2-siwis-atelier_fort | J'arvie à fiche le d'âgement d'atelier. | commande_manquee |
| A2-siwis-parole_fond | Le colis de la livraison avant midi, le colis de raisin arrive demain matin, pense à vérif | commande_manquee |
| A2-upmc-jessica-calme | J'arvi à fiche le dache boudatelier. | commande_manquee |
| A2-upmc-jessica-ventilateur | J'arvie à fiche le dache beau d'atelier. | commande_manquee |
| A2-upmc-jessica-imprimante | J'arrivis à fiche le dache bouddha telé. | commande_manquee |
| A2-upmc-jessica-atelier_fort | Jardis affiche le datteau de l'huile. | commande_manquee |
| A2-upmc-jessica-parole_fond | le collier de la livraison avant midi. | commande_manquee |
| A2-upmc-pierre-calme | Jervie, infiche le Dache-Baudatelier. | commande_manquee |
| A2-upmc-pierre-ventilateur | Jarvis, infiche le dash beau d'atelier. | commande_manquee |
| A2-upmc-pierre-imprimante | J'arvi un fiche de dache beau d'atelier. | commande_manquee |
| A2-upmc-pierre-atelier_fort | J'arbis, un fiche de dache brûle à tourner. | commande_manquee |
| A2-upmc-pierre-parole_fond | Le colis de la livraison avant midi, le colis de la livraison avant midi. | commande_manquee |
| A2-gilles-calme | J'arrivis à fiche le Dashboard à tuer. | commande_manquee |
| A2-gilles-ventilateur | J'arrivis à fiche le dashboard à tuer. | commande_manquee |
| A2-gilles-imprimante | J'arrivis à fichre le dashbole de la tuyée. | commande_manquee |
| A2-gilles-atelier_fort | J'arrivis à fûcher le dashbole de la taille. | commande_manquee |
| A2-gilles-parole_fond | Le colis de Jarovie a fiché mes dashboards à tous Le colis de Rézin arrive demain matin Pe | commande_manquee |
| … | 61 autres dans le JSON | |

## Limites

- Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.
- Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.
- Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.
- Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).
- Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.
