# Jarvis BOJ.ART — laboratoire d’innovations

Recherche du 30 octobre 2026, dossier de reprise indépendant. **Ce pack n’est pas un installateur Jarvis et ne met aucun service à jour.**

- `docs/INNOVATIONS_JARVIS.md` : innovations, arbitrages, réception et limites.
- `docs/SOURCES.md` : 18 sources primaires.
- `APERCU_PLANNING.html` : cinq scénarios précalculés, sans dépendance ni appel réseau.
- `prototype/planner.py` : moteur de démonstration Python standard, sans IA ni OR-Tools.
- `exemples/` : entrées fictives, durées en minutes abstraites.
- `preuves/` : résultats, tests, captures et provenance.
- `REPRISE_CLAUDE.txt` : consignes de reprise.

## Réception faite dans le conteneur de travail
22 tests Python exécutés ; 14 contrôles d’interface sous Chromium avec HTML injecté (set_content). La navigation file:// est interdite par la politique du navigateur de test ; aucune protection n’a été désactivée. La page est livrée comme HTML autonome pour ouverture locale sur un navigateur qui l’autorise.

## Exécution par l’intégrateur
Le moteur demande Python 3.10 ou plus. Aucune dépendance tierce pour la simulation.

```sh
cd prototype
python -m unittest -v test_planner
python build_examples.py
python planner.py ../exemples/base.json --out ../preuves/reexecution.json
```

Le test d’interface utilise Playwright et un navigateur Chromium installé ; son chemin `/usr/bin/chromium` correspond à l’environnement de test, pas à Windows. Adapter le chemin côté intégrateur, sans modifier les protections du navigateur.

## Limites impératives
Heuristique à horizon borné, jusqu’à six dossiers. Pas de preuve d’optimalité. Données synthétiques seulement. Les durées de post-traitement NE SONT PAS des consignes résine. Pas de stock, nesting, télémétrie, impression, publication, compte client ou validation de sécurité. Une imprimante dans le planning n’est jamais déclarée physiquement prête.

OR-Tools a été documenté, mais son installation d’essai a échoué ici par absence de résolution réseau. Le détail est conservé dans les preuves. Ne pas présenter ce laboratoire comme un backend CP-SAT déjà intégré.

Aucun modèle IA téléchargé, aucun crédit consommé, aucune donnée du PC cible consultée. Budget de référence inchangé : 3 000–5 000 €, réemploi d’abord.
