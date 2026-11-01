# Faire progresser BOJ.ART avec des preuves

Point d'entrée du travail d'audit ajouté le 1 novembre 2026. Ce module complète les documents de production et la mémoire Jarvis ; il ne remplace ni les archives ni le contexte courant.

## Ce qui fonctionne ici

- `tools/audit_repository.py` inventorie tous les fichiers suivis par Git : chemin, taille et SHA-256. Il vérifie la syntaxe Python, les JSON/JSONL, les clés répétées, les valeurs non finies, les timelines reconnues et les manifestes `ASSETS.json`.
- Les contenus identiques sont regroupés sans suppression. Un média absent reste un avertissement ; un média présent avec une mauvaise empreinte devient une erreur.
- `bojart_ops` conserve demandes, budgets réservés, identifiants fournisseur et événements dans SQLite. Les écritures concurrentes sont sérialisées. Après une interruption, une demande déjà réclamée ne peut pas être relancée aveuglément.
- Le contrôle de revue refuse un relecteur `null`, une valeur non textuelle, des validations non booléennes et des critères inconnus. Il contrôle une déclaration ; il n'authentifie pas la personne et ne juge pas le film.

Python 3.12, bibliothèque standard uniquement. Aucun modèle, serveur, GPU, microphone, Jev ou imprimante n'est lancé par ces commandes.

```bash
python -m unittest discover -s tests_ops -v
python tools/audit_repository.py --output .bojart-audit
```

Le rapport décrit les fichiers suivis du répertoire de travail. Après des modifications locales, les empreintes font foi ; le SHA de base seul ne décrit pas ces modifications. Les fichiers ignorés, les archives ZIP et les médias externes ne sont pas inspectés sémantiquement. Les JSON volumineux sont signalés si la limite de lecture est dépassée.

## Suivi des changements

| Mécanisme | Déclencheur | Travail | Limite |
|---|---|---|---|
| GitHub Actions `BOJART data audit` | Push, pull request, lancement manuel | Tests et inventaire du dépôt ; rapport attaché au run pendant 14 jours | Contrôle technique ; délai de file GitHub possible ; aucune validation artistique |
| Automatisation ChatGPT `Auditer les évolutions BOJART` | PR ordinaires et mises à jour de `main` via la PR permanente n°1 | Lecture du contexte et des écarts ; reçus par SHA sur `audit/context-results` ; correctifs réversibles testés | Portée et état vérifiables dans les reçus ; délai de traitement possible ; médias externes non présumés lus |
| Veille IA locale Jarvis existante | Vendredi | Nouveautés utiles aux modèles 3D et à la production | Cadence conservée ; aucune installation présumée |

Les pushes directs sur `main` actualisent désormais la [PR de surveillance n°1](https://github.com/Momolscode/BOJART/pull/1), qui doit rester ouverte et ne pas être fusionnée. Ce relais utilise l'événement PR pris en charge par le connecteur. La [procédure et les preuves de recette](SURVEILLANCE_CONTEXTUELLE.md) expliquent comment vérifier les lancements et les reçus. Un lancement en cours ou un reçu partiel ne vaut pas validation complète. Les branches sans PR restent couvertes par les contrôles techniques seulement. Un contrôle en échec ne bloque pas à lui seul une fusion : aucune règle de protection de branche n'a été modifiée.

## Relier les informations

| Entité | Clé stable | Preuve à garder |
|---|---|---|
| Source | SHA-256 + identifiant d'origine | Octets originaux, chemins, date et provenance |
| Décision | Identifiant, date, domaine | Consigne de Morgan ou constat, source exacte, décision remplacée |
| Plan | Production + `shot_id` + version | Geste, référence, critère de réussite, défaut principal |
| Génération | Empreinte de requête + `provider_job_id` | Modèle, prompt, paramètres, références et empreintes, plafond, statut brut |
| Montage | Version de l'EDL | Sources, points d'entrée, images, sons, correspondance vers les jobs |
| Revue | Plan/export + version | Mesures techniques, jugement artistique, retour utilisateur et audience séparés |

La mémoire documentaire doit indexer ces références et fournir des extraits sourcés par domaine (`bojart.jarvis`, `bojart.creative`, `bojart.sites`). Réutiliser `bojart_memory`, maintenant consolidé dans le dépôt ; ne pas créer une deuxième base documentaire. Le présent journal n'est qu'un état de production. Les versions historiques restent consultables et ne deviennent pas automatiquement des décisions actuelles.

La réponse à « où en est G2 ? » doit réunir `STATUT_G2.json`, la revue R03, le dernier reçu fournisseur et la source authentique. Elle doit exposer l'absence de plan fidèle, plutôt que déduire un succès du mot `completed` présent dans un ancien essai.

## Journal de génération local

Le fichier par défaut se trouve dans `~/BOJART/operations/generations.sqlite3`, hors dépôt. Pour un essai isolé, utiliser `--db .bojart-state/essai.sqlite3`.

```bash
# Démonstration locale uniquement : aucun appel fournisseur, aucun crédit dépensé.
python -m bojart_ops --db .bojart-state/essai.sqlite3 budget demo 30
python -m bojart_ops --db .bojart-state/essai.sqlite3 plan demo-g1 ops/request-example.json --budget demo --max-credits 28
python -m bojart_ops --db .bojart-state/essai.sqlite3 begin demo-g1
python -m bojart_ops --db .bojart-state/essai.sqlite3 unknown demo-g1
python -m bojart_ops --db .bojart-state/essai.sqlite3 show demo-g1
```

Avant un appel réel autorisé : vérifier le catalogue et le devis actuels, préparer les références et leur empreinte, conserver la requête exacte, réserver le plafond, puis réclamer la demande avec `begin`. Appeler ensuite le fournisseur depuis l'adaptateur autorisé et enregistrer **son vrai identifiant** avec `receipt RUN JOB_ID STATUT`. `begin` seul n'envoie rien. Une réponse perdue laisse `submitting` ou `unknown` : rechercher le job avant toute autre action. Ne jamais inventer un identifiant pour terminer la file.

`receipt` conserve aussi les statuts non reconnus et les traduit en `unknown`. `ip_detected` et `nsfw` deviennent `blocked` et ne sont jamais réessayés automatiquement. Les réservations ne sont pas remboursées sur une simple erreur ; aucun remboursement fournisseur n'est inféré. Une variation intentionnelle utilise un nouveau nom de variation et un plafond explicitement disponible.

Après téléchargement par une route autorisée, `attach RUN FICHIER --sha256 EMPREINTE` compare les octets. Il ne décode pas la vidéo et ne l'approuve pas. Les reçus historiques sont dans `ops/higgsfield-observations.json`, séparés de ce journal neuf : aucun coût ou prompt historique inconnu n'est inventé pour les importer.

`backup NOUVEAU_FICHIER` effectue une sauvegarde SQLite cohérente, sans écrasement. Tester la copie dans un nouveau répertoire avant de remplacer un état actif. Les sauvegardes de la mémoire documentaire, du journal, des bases Jarvis et des médias restent distinctes.

## Prochaines preuves à obtenir

1. Le code M07 est consolidé sous `jarvis/` et sa recette logicielle a été réexécutée ; voir [les preuves](evidence/consolidation-2026-11-01.json). Qualifier maintenant la tour réelle, en distinguant voix simulée, Jev réel et vrai microphone.
2. Relier un seul adaptateur Higgsfield au journal, avec test d'interruption entre soumission et reçu, dans un essai borné. Aucun adaptateur payant n'est activé par ce changement.
3. Qualifier G2 sur la sculpture authentique : même visage, peinture, main, socle et geste. Les refus fournisseur restent terminaux ; choisir une méthode autorisée et adaptée.
4. Exporter une timeline de référence via OpenTimelineIO, puis comparer les 222 images de R03 et la piste son après import. Les effets FFmpeg, recadrages et traitements audio exigent une vérification séparée.
5. Sur l'atelier réel, connecter d'abord une machine en lecture seule, inventorier firmware/profil/matériau, puis effectuer un essai supervisé. Jev propose une action typée ; les gardes de l'atelier et les reçus conservent l'autorité d'exécution.

Recherche et critères : [OUTILS_ET_ESSAIS.md](OUTILS_ET_ESSAIS.md). Constat initial : [AUDIT_CONTINU_2026-11-01.md](AUDIT_CONTINU_2026-11-01.md).
