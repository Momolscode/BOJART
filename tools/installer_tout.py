#!/usr/bin/env python3
"""Installation complète de Jarvis sur la tour, en une fois (lancé par Installer_Tout_BOJART.cmd).

  python tools/installer_tout.py                 # montre le plan, demande un accord, installe tout
  python tools/installer_tout.py --oui           # sans question (accord donné à l'avance)
  python tools/installer_tout.py --simulation    # plan seul, en JSON : rien n'est installé ni téléchargé

Étapes : Ollama, FFmpeg et Git (winget, si absents), démarrage d'Ollama, Jarvis complet depuis les
verrous Windows (voix et chaîne figurine comprises), poids de la voix et son activation, modèles
locaux du profil, banc de contrôle. Journal : ~/BOJART/installation/.
Aucune imprimante, publication, dépense ou suppression de données.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bojart_ops import installation_tout as it  # noqa: E402


def options(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--oui', action='store_true', help='Accord donné à l’avance pour toutes les étapes du plan.')
    p.add_argument('--simulation', action='store_true', help='Détecter et planifier seulement ; sortie JSON.')
    p.add_argument('--profil', choices=('speed', 'balanced', 'quality'), default='speed', help='Profil de modèles (speed pour la 4060 Ti 8 Go).')
    p.add_argument('--sans-voix', action='store_true', help='Ni bibliothèques ni poids voix.')
    p.add_argument('--sans-figurine', action='store_true', help='Ne pas installer la chaîne figurine M08.')
    p.add_argument('--sans-modeles', action='store_true', help='Ni Ollama ni modèles.')
    p.add_argument('--sans-banc', action='store_true', help='Ne pas lancer le banc à la fin.')
    p.add_argument('--journal', type=Path, help='Chemin d’un journal neuf (par défaut ~/BOJART/installation/).')
    return p.parse_args(argv)


def revision():
    manifest = it.ROOT / 'data/catalog/repository_manifest.json'
    return hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.exists() else None


def main(argv=None):
    a = options(argv)
    now = datetime.now()
    state = it.detect()
    steps = it.plan(state, profile=a.profil, voice=not a.sans_voix, models=not a.sans_modeles, bench=not a.sans_banc,
                    figurine=not a.sans_figurine, stamp=f'{now:%Y%m%d-%H%M%S}')
    notes = it.warnings(state, models=not a.sans_modeles, profile=a.profil)
    if a.simulation:
        result = {'simulation': True, 'etat': state, 'plan': [{k: s.get(k) for k in ('id', 'type', 'titre', 'depend_de')} for s in steps],
                  'avertissements': notes}
        if a.journal:
            with a.journal.open('x', encoding='utf-8', newline='\n') as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print('Ce qui est déjà là :')
    for key, label in (('ollama', 'Ollama'), ('ffmpeg', 'FFmpeg'), ('git', 'Git'), ('winget', 'winget')):
        print(f'  {label} : {state[key] or "absent"}')
    print(f'  Ollama répond : {state["ollama_actif"] or "non"} ; espace libre : {state["espace_libre_go"]} Go')
    print('\nPlan :')
    for i, step in enumerate(steps, 1):
        print(f'  {i}. {step["titre"]}')
    for note in notes:
        print('  ! ' + note)
    if not state['python_312']:
        print('Installation arrêtée : Python 3.12 requis.')
        return 2
    if not a.oui:
        if not sys.stdin or not sys.stdin.isatty():
            print('Accord requis : relancer dans une console, ou avec --oui.')
            return 2
        if input('\nTout lancer maintenant ? [o/N] ').strip().lower() not in ('o', 'oui'):
            print('Rien n’a été installé.')
            return 3
    path = a.journal or it.new_journal_path(now=now)
    journal = it.Journal(path, {'schema': 'bojart.installation-complete.v1', 'debut': now.isoformat(timespec='seconds'),
                                'manifeste_sha256': revision(), 'options': vars(a) | {'journal': str(path)},
                                'etat_initial': dict(state), 'etapes': []})
    records = it.execute(steps, state, journal)
    journal.data['fin'] = datetime.now().isoformat(timespec='seconds')
    journal.data['synthese'] = it.summary(records)
    journal.save()
    print('\n================ Résultat ================')
    if journal.data['synthese']['termine']:
        print('Tout est installé. Ouvrir Lancer_BOJART.cmd.')
        print('Pour rapatrier vidéos, photos et documents : Collecter_BOJART.cmd.')
        print('Pour envoyer le débrief de cette installation sur GitHub : Publier_Debrief_BOJART.cmd.')
    else:
        print('Reste à faire :')
        for line in journal.data['synthese']['reste_a_faire']:
            print('  - ' + line)
        print('Relancer Installer_Tout_BOJART.cmd après correction : les étapes déjà faites sont reconnues.')
    print(f'Journal : {path}')
    return 0 if journal.data['synthese']['termine'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit('Installation interrompue : relancer pour reprendre, les étapes déjà faites sont reconnues.')
