# Atelier : demandes clients, devis et parc d'imprimantes simulé

État au 2 novembre 2026 : **codé et testé en isolation** (conteneur Linux, sans GPU ni machine). Rien n'est installé sur la tour. Aucune imprimante réelle n'est raccordée. Aucun prix de BOJ.ART n'est connu du dépôt.

## Ouvrir la page

1. Lancer Jarvis (`Lancer_Jarvis.cmd`), puis ouvrir `http://127.0.0.1:8767/atelier` (lien « Demandes, devis, parc » en bas de `/workspace`).
2. « Charger la démonstration » crée un dossier fictif, une demande, un devis non émettable et trois imprimantes simulées. Rejouer le bouton ne crée pas de doublon.
3. Sur la tour, « Jarvis, affiche le dashboard atelier » (alias : « affiche les devis », « affiche le parc ») montre le tableau atelier sur l'écran gauche : parc simulé, demandes ouvertes, devis.

Le même cookie de session, le contrôle d'origine, la limite de 8 Kio par requête et le verrou d'écriture de la console consolidée s'appliquent à toutes les routes `/api/atelier/*`.

## Ce qui est codé

### Demandes clients
- Origine obligatoire : vitrine, e-mail, téléphone, atelier, réseau social, salon, autre ou démonstration. Une demande garde la référence de sa source ; son résumé technique refuse les adresses e-mail et numéros de téléphone (ils restent dans la boîte d'origine).
- États : `recue` → `qualifiee` → `devis_envoye` → `acceptee` → `en_production` → `livree`, avec sorties `doublon`, `spam`, `non_realisable`, `abandonnee`, `refusee`. Chaque changement porte la révision lue ; une révision périmée est refusée.
- Entonnoir : compte les jalons réellement atteints (reçues, qualifiées, devis envoyés, acceptées, livrées) sur **toutes** les demandes, pas seulement les 200 affichées. Démonstration, doublons et spam sont exclus. Les rapports s'affichent en « n/m », sans taux extrapolé.

### Devis
- Formule : prix HT = coût de revient / (1 − marge − commission). C'est la formule de `calculateQuote` du site Atelier V11 (`sites/atelier/dist/lib/workshop.js`). Un test compare les deux moteurs au centime.
- Lignes : matière (avec pertes), temps machine, provision de reprise, main-d'œuvre (par lot ou par exemplaire), frais. Chaque ligne est arrondie au centime ; les totaux sont des sommes de lignes arrondies (calcul en `Decimal`).
- Estimations acceptées : métadonnées d'un G-code ASCII PrusaSlicer, OrcaSlicer ou Bambu Studio ; estimation géométrique résine depuis un STL ; ou mesure saisie. Une pièce FDM exige un tranchage. Un fichier tranché avec un profil de simulation bloque l'émission.
- TVA : `assujetti` (avec taux), `franchise_293B` (mention « TVA non applicable, art. 293 B du CGI ») ou `a_definir`. Sans régime, le TTC n'est pas calculé. Une valeur manquante n'est jamais remplacée par zéro.
- Émission impossible tant que : grille d'exemple, régime de TVA inconnu, émetteur absent (raison sociale, adresse, SIRET), délai absent, estimation de simulation. La liste des bloquants s'affiche sur le devis.
- Versions : numérotation `DV-AAAA-NNNN`. Un devis émis est figé : document, grille, entrée et calcul ont chacun leur SHA-256. Une modification produit la version suivante et remplace la précédente. Un document altéré en base est signalé « altéré » et refusé.
- Envoi déclaré : refusé si la date d'envoi dépasse la validité. Un devis émis passé sa validité s'affiche « expiré », envoyé ou non.
- Accord client : seulement sur la version émise courante, déclarée envoyée, dans sa durée de validité, avec l'empreinte affichée. Il crée une commande `CMD-…` dont `production_autorisee` vaut `false`. Le relevé réel (temps, matière) se compare ensuite au devis.
- Démonstration : coût de revient 147,38 €, total HT 210,54 €, TTC non calculé, 5 bloquants d'émission.
- **Devis imprimable** : « Version imprimable (PDF) » sur le détail d'un devis ouvre une page A4 ; le bouton lance l'impression du navigateur (« Enregistrer au format PDF »). Le client voit émetteur, destinataire, objet, délai, une ligne par pièce, opération et frais, les totaux HT/TVA/TTC, la mention de TVA et un cadre « Bon pour accord ». Coût de revient, marge et taux internes n'y figurent pas : chaque ligne reçoit le total HT au prorata de ses coûts, arrondi au centime par la méthode du plus fort reste, et la somme des lignes égale exactement le total HT. Un brouillon porte « DOCUMENT DE TRAVAIL — NON ÉMIS », une grille d'exemple « EXEMPLE — NE PAS ENVOYER », une version remplacée ou expirée son propre bandeau.

### Commandes : prévu / réel
- Un relevé correspond à une pièce imprimée. Une mesure opérateur exige le nom de la personne qui a mesuré ; un résultat simulé n'en a pas.
- Pour chaque pièce : prévu unitaire (temps, matière en g ou ml), nombre de mesures, écart en % de la médiane des mesures. Les résultats simulés sont listés à part et n'entrent jamais dans l'écart.
- Dérive par procédé, sur toutes les commandes intactes : rapport médian réel / prévu pour le temps et la matière, avec le nombre de pièces mesurées. La grille n'est jamais recalée automatiquement.

### Délais de réponse
L'entonnoir affiche, en jours et sur les dates déclarées : réception → premier devis envoyé, puis envoi → réponse (accord ou refus), avec médiane, maximum et effectif. Les dates d'envoi et d'accord saisies font foi, même si elles sont enregistrées plus tard.

### Parc d'imprimantes
- Fiche machine : identifiant, origine (`simulee` ou `declaree`), fabricant, modèle, procédé (FDM ou résine), volume utile et sa source, matières, interface (simulation, moonraker, octoprint, prusalink, bambu_lan, elegoo_sdcp, manuelle, inconnue), limites de température. L'adresse refuse tout identifiant ou secret.
- Autorisation par machine **et** par action : `lire_etat` (30 jours au plus), `televerser`, `chauffer`, `demarrer`, `pause`, `reprendre`, `annuler` (12 heures au plus). Un changement de fiche révoque les autorisations. L'arrêt d'urgence logiciel n'exige jamais d'autorisation.
- Ordre : l'intention est écrite avant l'exécution. Résultats : `confirme`, `refuse_machine` ou `inconnu`. Un résultat inconnu bloque tout nouvel ordre sur la machine jusqu'à une lecture d'état, qui rapproche l'ordre.
- Démarrage : fichier téléversé exact (SHA-256), confirmation « plateau libre » et nom de l'opérateur.
- Simulateur : état persistant, horloge injectée, accélération réglable. Pannes injectables : perte de liaison (effet non appliqué, résultat inconnu), réponse tardive (effet appliqué, accusé perdu), erreur buse.
- Machines déclarées réelles : seule `lire_etat` peut être autorisée, et tout ordre est refusé (« connecteur non raccordé »). Aucun code ne parle à une imprimante réelle.

### Sauvegarde et restauration
Les tables atelier vivent dans la base des missions et suivent la sauvegarde globale. À la restauration, tout ordre en cours devient `inconnu_restauration`, toutes les autorisations sont révoquées et chaque machine doit être relue. Le reçu de restauration compte ces deux effets.

## Ce que Jarvis ne fait pas

- Il n'envoie rien au client : « envoyé » est une déclaration de l'opérateur (`external_message_sent: false` sur chaque reçu).
- Il ne fixe aucun prix : la grille `jarvis/config/atelier/tarifs.exemple.json` est marquée exemple et ne peut pas émettre.
- Il ne produit pas de facture et ne valide pas les mentions légales.
- Il ne lit pas Cura, `.bgcode` ni 3MF ; la durée résine est un modèle (couches × exposition + cycle), pas la sortie d'un trancheur résine.

## À fournir par BOJ.ART avant un premier devis réel

1. Grille déclarée : prix matières, coût horaire par procédé, taux de main-d'œuvre, pertes, provision de reprise, marge, commission, durée de validité. Déclarant et date sont exigés.
2. Régime de TVA et, s'il y a lieu, le taux.
3. Émetteur : raison sociale, adresse, SIRET.
4. Relecture des mentions obligatoires du devis par la personne responsable. Les pages officielles (DGCCRF, service-public) ont renvoyé 403 ou une redirection hors sujet le 2 novembre : elles ne sont pas relues ici.

## Inventaire du parc

Le nombre et les modèles des imprimantes restent inconnus. Sur la tour, déclarer chaque machine dans la page (formulaire « Déclarer une machine réelle »), avec la source de son volume utile (fiche fabricant ou mesure). Le gabarit général du poste reste `jarvis/config/M04_INVENTAIRE_A_REMPLIR.json`.

## Connecteurs candidats (non codés)

| Interface | Ce qui est vérifié le 2 novembre 2026 | Point de vigilance |
|---|---|---|
| Moonraker (Klipper) | Documentation officielle lue : `GET /printer/info`, `POST /printer/objects/query`, `POST /printer/print/start|pause|resume|cancel`, `POST /printer/emergency_stop`, `POST /server/files/upload`. | Le champ `print=true` du téléversement démarre l'impression : ne jamais l'utiliser ; téléverser et démarrer restent deux ordres distincts. |
| OctoPrint | Documentation officielle lue : `GET /api/job` (états « Operational », « Printing », « Paused »… liste non exhaustive), `POST /api/job` avec `start`, `cancel`, `restart`, `pause` + `action`. | `pause` sans `action` bascule l'état : toujours préciser `pause` ou `resume`. |
| PrusaLink | Spécification `spec/openapi.yaml` du dépôt `prusa3d/Prusa-Link-Web` repérée par recherche ; `/api/v1/status`, `/api/v1/job`. Spécification non relue en entier. | Relire la spécification à la version du firmware installé. |
| Bambu Lab (LAN) | Sources secondaires seulement : depuis janvier 2025, le firmware réserve démarrage, déplacements et températures aux logiciels approuvés ; lecture seule sinon, sauf « Developer Mode ». | À vérifier sur le blog et le wiki Bambu avant tout choix. |
| Elegoo SDCP | Documentation communautaire seulement : WebSocket `ws://<ip>:3030/websocket`, découverte UDP 3000. | Pas de documentation officielle trouvée. |

Ordre proposé : une machine identifiée, lecture d'état seule, avec opérateur présent ; puis une action à la fois, chacune avec sa recette.

## Sources consultées le 2 novembre 2026

- Moonraker : https://moonraker.readthedocs.io/en/latest/external_api/printer/ et https://moonraker.readthedocs.io/en/latest/external_api/file_manager/ (lues).
- OctoPrint : https://docs.octoprint.org/en/master/api/job.html (lue).
- PrusaLink : https://github.com/prusa3d/Prusa-Link-Web/blob/f7fa76d8aca68d78e68151b4ed4fe38de28ff2ca/spec/openapi.yaml (repérée, non relue).
- PrusaSlicer, cas de test : https://raw.githubusercontent.com/prusa3d/PrusaSlicer/master/resources/test_data/test_vase.gcode (10 lignes de métadonnées extraites, provenance dans `jarvis/tests/fixtures/atelier/PROVENANCE.json`).
- Mentions du devis : https://www.economie.gouv.fr/dgccrf/les-fiches-pratiques/devis (403, non relue).

## Preuves

Voir `docs/evidence/atelier-devis-parc-2026-11-02/` : tests exécutés, contre-vérification géométrique avec trimesh, parcours navigateur et résultat du banc de la PR #17 sur l'arbre fusionné.

## Prochaine preuve

1. Déclarer la grille réelle, le régime de TVA et l'émetteur, puis émettre un devis à blanc, sans l'envoyer, et le faire relire.
2. Inventorier le parc sur la tour : une fiche par machine, avec modèle, interface et firmware.
3. Raccorder une seule machine en lecture d'état, opérateur présent, et conserver le reçu.
