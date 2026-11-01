# BOJ.ART — dossier d’audit Jarvis
Date de l’évaluation : 1 novembre 2026. Dépôt : https://github.com/Momolscode/BOJART

**Verdict provisoire : le socle local démarre ; l’atelier autonome complet reste à qualifier et à compléter.** Ce dossier permet de contester et reproduire cette conclusion. Il ne certifie ni la tour de l’atelier ni l’ensemble de la branche main actuelle.

## Commencer
1. Lire [RAPPORT.md](RAPPORT.md) et [PREUVES.json](PREUVES.json).
2. Ouvrir [SCHEMA_ORCHESTRATION.svg](SCHEMA_ORCHESTRATION.svg) dans un navigateur. Le SVG est l’image vectorielle ; [GRAPHE_EXECUTE.mmd](GRAPHE_EXECUTE.mmd) décrit les quatre nœuds du graphe réel.
3. Transmettre [MISSION_AUDITEUR.txt](MISSION_AUDITEUR.txt) avec ce dossier et l’accès au dépôt à l’auditeur ou à Claude.
4. Suivre [REPRODUIRE.md](REPRODUIRE.md), puis remplir [RETOUR_AUDITEUR.md](RETOUR_AUDITEUR.md).
5. Contrôler les empreintes de [MANIFESTE.json](MANIFESTE.json). Les sources épinglées sont dans [SOURCES.json](SOURCES.json).

## Versions et portée
| Référence | Portée des preuves |
|---|---|
| e5cd9f3f18f744b800aa8bb655a70fa643c634a1 | Installation minimale, HTTP, mémoire, restauration, suites mémoire/agents/M06/M07/JavaScript |
| 3c288214539adf97381f6053b43225485a873b6a | Lecture finale du graphe, schéma et relance des 46 tests opérations |
| 461d46ff39caaf142ce37a3e0b78f22dfcc2e842 | Tête relue pour préparer cette publication ; changements de démarrage/mémoire à réexaminer |

La tête relue contient deux commits après 3c28821. [DELTA_A_REEXAMINER.json](DELTA_A_REEXAMINER.json) liste leurs chemins. Les anciens résultats locaux ne deviennent pas des résultats de cette tête par simple rattachement du dossier.

Les sorties sélectionnées sont des transcriptions d’observations, pas des journaux bruts complets : voir [preuves/SORTIES_OBSERVEES.txt](preuves/SORTIES_OBSERVEES.txt). L’environnement ayant été déconnecté avant l’empaquetage, les journaux locaux complets ne sont pas joints. Les preuves de démarrage déjà versionnées par une autre session sont référencées séparément.

## Télécharger et utiliser
Le workflow « BOJART audit dossier » contrôle les empreintes et produit l’artefact ZIP `BOJART_DOSSIER_AUDIT_JARVIS_2026-11-01`. Consulter https://github.com/Momolscode/BOJART/actions/workflows/jarvis-audit-dossier.yml et télécharger l’artefact du commit souhaité. Les artefacts ont une rétention de 90 jours ; le dossier versionné reste disponible et le workflow peut être relancé.

Le ZIP contient le dossier d’audit, pas une copie complète du logiciel, des modèles ou des données de l’atelier. L’auditeur doit consulter le dépôt aux références indiquées. La validation du ZIP confirme ses fichiers, pas la préparation opérationnelle du Jarvis.
