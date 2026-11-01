# BOJ.ART — atelier, Jarvis et direction artistique

Point d’entrée consolidé : [contexte courant](context/CURRENT.md), [installation](docs/INSTALLATION.md), [passation](context/SESSION_HANDOFF.md).

| Dossier | Contenu | État |
|---|---|---|
| `jarvis/` | M07, CAO, trois vues, Studio, Growth, base métier | Code local ; matériel à qualifier |
| `bojart_memory/` | Import, versions, recherche sourcée, sauvegarde/restauration | Implémenté ; sans LLM ni accès automatique aux chats |
| `creative/` | Direction, exigences et statut courant | R03 est une coupe de travail |
| `productions/`, `runs/` | Scripts de montage, timelines, sources et essais | R01–R03 et générations historisées |
| `sites/atelier/`, `sites/studio/` | Sources V11/V3 | Copies ; publications d’origine conservées |
| `data/catalog/` | Empreintes et provenance | 1 060 emplacements, 1016 contenus distincts |
| `data/knowledge/` | Affirmations, sources et contradictions | Distillation révisable |

Les médias, bases actives, conversations brutes et archives restent hors du dépôt public. Le catalogue référence les originaux ; il ne transfère pas leurs octets sur GitHub. Les historiques M07 et Sites restent dans leurs sources d’origine.

## Démarrer

La mémoire seule fonctionne avec Python standard et SQLite FTS5 :

```bash
python3 -m bojart_memory index-repo
python3 -m bojart_memory search "Jev et voix" --project bojart.jarvis
```

Pour le poste complet, suivre [INSTALLATION.md](docs/INSTALLATION.md), puis `Lancer_BOJART.sh` ou `Lancer_BOJART.cmd`. Le lanceur indexe les documents sélectionnés et ouvre l’application. **Mémoire du projet** retrouve les passages avec provenance et numéros de lignes.

## Reprendre

Lire `context/CURRENT.md`, vérifier les sources du domaine concerné, importer les nouveaux documents localement, puis consigner les décisions avec leurs preuves. Voir [le protocole GitHub](docs/GITHUB_WORKFLOW.md) et [les données](docs/DATA_GOVERNANCE.md).

Les poids ASR, le micro, les moniteurs, le GPU et les imprimantes restent à qualifier sur la tour. Jev est facultatif et distant. Conversation continue, commandes physiques, publication sociale et synchronisation automatique des chats ne sont pas activées. Les sites et Jarvis partagent un dépôt, pas encore une base métier commune.

Le montage courant est **Le dernier geste R03** ; son plan G2 fidèle manque. Une réussite technique ne vaut pas validation artistique ou mesure d’audience.

Les apports des autres sessions sont conservés : [recette R03](productions/le-dernier-geste/README.md), [recherche artistes](docs/RECHERCHE_ARTISTES.md), [pistes RTX](docs/PRODUCTION_RTX.md), [restauration des archives](docs/ARCHIVE_RESTAURATION.md) et [pipeline créatif historique](docs/CREATIVE_PIPELINE_HISTORIQUE.md).

Les archives et médias simplement référencés ne sont pas tous hébergés ici. Les documents anciens sous `docs/historical/` décrivent leur époque ; le contexte courant distingue ce qui a été récupéré depuis. Voir [les preuves de consolidation](docs/evidence/consolidation-2026-11-01.json).

Les ajouts simultanés sont intégrés : [audit et journal des générations](docs/OPERATIONS.md), `bojart_ops/`, `tests_ops/` et leur workflow GitHub. Ils complètent la mémoire documentaire ; les sauvegardes restent distinctes.
