# Reproduire et compléter la recette
Les nombres attendus ci-dessous appartiennent aux références épinglées. Sur une autre version, consigner les résultats observés sans imposer les anciens nombres. Garder les journaux hors du dépôt public tant qu’ils n’ont pas été relus.

## Code et environnement
Conserver ce dossier à côté du clone si l’on revient à un commit antérieur à son ajout.

```bash
git clone https://github.com/Momolscode/BOJART.git BOJART-audit-2026-11-01
cd BOJART-audit-2026-11-01
git checkout --detach e5cd9f3f18f744b800aa8bb655a70fa643c634a1
python3.12 --version
python3.12 -c 'import sqlite3; print(sqlite3.sqlite_version); sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(text)")'
node --version
```

Utiliser Python 3.12. L’évaluation initiale utilisait Python 3.12.14 et SQLite 3.53.1 sous Linux. Relever les versions effectives et le SHA avec `git rev-parse HEAD`.

## Suites sélectionnées
Depuis la racine du clone à e5cd9f3 :

```bash
python3.12 -m unittest discover -s tests -v
python3.12 -m unittest discover -s tests_agent -v
python3.12 -m unittest discover -s jarvis/tests -p test_jarvis_m06.py -v
python3.12 -m unittest discover -s jarvis/tests -p test_jarvis_m07.py -v
node --test jarvis/tests/voice_endpoint.test.cjs jarvis/tests/memory_context.test.cjs
python3.12 tools/evaluate_memory.py
python3.12 tools/validate_repository.py
```

Résultats locaux de référence : 37, 25, 42 et 22 tests Python ; 11 tests JavaScript ; 10 cas documentaires. La commande de validation complète est fournie pour la reproduction ; ne pas confondre la validation du paquet documentaire avec celle du monorepo.

Dans une copie propre de la référence 3c28821 :

```bash
git checkout --detach 3c288214539adf97381f6053b43225485a873b6a
python3.12 -m unittest discover -s tests_ops -v
```

Résultat local de référence : 46 tests opérations. Les suites utilisent des états temporaires et des doubles de certains services.

## Installation minimale et HTTP
Revenir à e5cd9f3 dans une copie propre. Créer des états neufs ; ne pas réutiliser les données de l’atelier.

```bash
git checkout --detach e5cd9f3f18f744b800aa8bb655a70fa643c634a1
export BOJART_AUDIT_ROOT="$(mktemp -d)"
export BOJART_MEMORY_STATE="$BOJART_AUDIT_ROOT/memory"
bash Installer_BOJART.sh
bash Lancer_BOJART.sh --no-browser --state "$BOJART_AUDIT_ROOT/runtime"
```

Depuis un second terminal, vérifier http://127.0.0.1:8767/workspace, /memory, /tower, /studio, /growth et /knowledge. Lire également /health et /api/jarvis/status. En installation minimale, l’absence des moteurs facultatifs peut être signalée ; enregistrer le mode effectif et les fonctions disponibles. HTTP 200 ne suffit pas à qualifier une interface visuellement.

Chercher « Jev et voix » dans la mémoire et vérifier les sources et lignes retournées. Arrêter le serveur proprement avant la restauration.

Dans le terminal où les variables ci-dessus sont définies :

```bash
.venv/bin/python -m bojart_memory --state "$BOJART_MEMORY_STATE" backup "$BOJART_AUDIT_ROOT/snapshot"
.venv/bin/python -m bojart_memory restore "$BOJART_AUDIT_ROOT/snapshot" "$BOJART_AUDIT_ROOT/restored"
.venv/bin/python -m bojart_memory --state "$BOJART_AUDIT_ROOT/restored" verify
```

La destination de restauration doit être neuve. Contrôler les empreintes et la recherche après restauration. Tester séparément les cinq bases opérationnelles M07 selon les procédures du dépôt.

## Moteurs et matériel — recette supplémentaire
Dans une copie de qualification, après inspection des dépendances :

```bash
python3.12 tools/prepare_installation.py --engines
```

Relever les versions installées et vérifier que le statut LangGraph annonce son moteur SQLite opérationnel, pas le repli. Exécuter une proposition CAO confirmée et contrôler les exports réels STL/STEP/GLB. Tester interruption, redémarrage, annulation, double requête et reçus manquants.

`--voice` installe les bibliothèques voix ; les poids sont à fournir séparément. Qualifier le micro, le français, le bruit et la latence. Jev est un service distant facultatif ; ne jamais déposer une clé dans les logs. Sur Windows, suivre les scripts .cmd et les instructions de la version examinée ; l’évaluation Linux ne valide pas ce parcours.

## Examiner la version actuelle
Repartir d’un clone propre, épingler sa tête et examiner DELTA_A_REEXAMINER.json. Rejouer les suites concernées et, si présent sur cette version :

```bash
python3.12 tools/check_startup.py --output .bojart-audit/startup.json
```

Consulter les CI du même SHA et joindre leurs liens. La tête préparée pour ce dossier est 9f58fa29f0051cc8a7098855359a8a6dd0eef7e6 ; elle peut évoluer ensuite. Remplir RETOUR_AUDITEUR.md avec trois verdicts séparés.

## Vérifier le dossier téléchargé
Depuis la racine du dossier d’audit, ce contrôle Python vérifie les fichiers décrits, hors MANIFESTE.json lui-même :

```python
import hashlib, json
from pathlib import Path
root = Path(".").resolve()
manifest = json.loads((root / "MANIFESTE.json").read_text(encoding="utf-8"))
for entry in manifest["files"]:
    path = (root / entry["path"]).resolve()
    assert path.is_relative_to(root), entry["path"]
    raw = path.read_bytes()
    assert len(raw) == entry["bytes"], entry["path"]
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]
print("Empreintes du dossier vérifiées")
```
