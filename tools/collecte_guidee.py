#!/usr/bin/env python3
"""Collecte guidée des contenus BOJ.ART (lancée par Collecter_BOJART.cmd).

  python tools/collecte_guidee.py                       # parcours guidé : désigner les dossiers, voir le plan, un accord
  python tools/collecte_guidee.py ajouter DOSSIER [--nom N] [--projet P]
  python tools/collecte_guidee.py sources               # dossiers déjà désignés
  python tools/collecte_guidee.py plan                  # ce qui serait collecté (JSON), sans rien copier
  python tools/collecte_guidee.py collecter [--oui]     # passage complet sur les dossiers désignés
  python tools/collecte_guidee.py verifier              # relire tous les originaux conservés
  python tools/collecte_guidee.py simulation            # essai complet sur des dossiers synthétiques temporaires

Magasin : ~/BOJART/collecte (BOJART_COLLECTE pour un autre emplacement). Mémoire : ~/BOJART/memory.
Les sources ne sont jamais modifiées ni supprimées ; rien n'est publié ni envoyé.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bojart_ops import collecte as co  # noqa: E402
from bojart_ops import installation_tout as it  # noqa: E402

PROJECT_MENU = {'1': ('bojart.creative', 'Création et atelier (vidéos, photos, pièces)'),
                '2': ('bojart.jarvis', 'Jarvis (conversations, organisation)'),
                '3': ('bojart.sites', 'Sites et boutique')}


def gib(n):
    return f'{n / 1e9:.1f} Go'


def probe_for_videos():
    ffmpeg = it.find_ffmpeg()
    if not ffmpeg:
        return None
    ffprobe = ffmpeg.with_name('ffprobe' + ffmpeg.suffix)
    return co.ffprobe_metadata(ffprobe) if ffprobe.is_file() else None


def pick_folder():
    try:
        import tkinter
        from tkinter import filedialog
        window = tkinter.Tk()
        window.withdraw()
        window.attributes('-topmost', True)
        chosen = filedialog.askdirectory(title='Choisir un dossier à collecter pour Jarvis', mustexist=True)
        window.destroy()
        return chosen or None
    except Exception:  # no display or no tkinter: fall back to the console
        typed = input('Chemin du dossier (vide pour arrêter) : ').strip().strip('"')
        return typed or None


def ask(question, default='n'):
    answer = input(f'{question} [{"O/n" if default == "o" else "o/N"}] ').strip().lower() or default
    return answer in ('o', 'oui')


def print_plan(plan):
    print('\nÀ collecter :')
    for entry in plan['par_source']:
        s = entry['source']
        new = ', '.join(f'{n} {g}' for g, n in sorted(entry['nouveaux'].items())) or 'rien de nouveau'
        print(f'  - {s["nom"]} ({s["chemin"]}) : {new} ; déjà vus : {entry["deja_vus"]}')
        ignored = entry['ignores']
        if ignored.get('absent'):
            print('      dossier absent (disque débranché ?) : ignoré cette fois')
        others = sum(ignored['autres'].values())
        if ignored['liens'] or ignored['caches_ou_prives'] or others:
            print(f'      ignorés : {ignored["liens"]} lien(s), {ignored["caches_ou_prives"]} caché(s) ou privé(s), {others} autre(s) format(s)')
    print(f'  Volume à lire : {gib(plan["octets_a_lire"])} ; espace libre : {gib(plan["espace_libre"])}')


def run_collect(c, assume_yes=False):
    plan = c.plan()
    print_plan(plan)
    if not plan['elements']:
        print('Rien de nouveau : tout est déjà collecté.')
        return 0
    if not plan['espace_suffisant']:
        print(f'Espace insuffisant (marge de {gib(co.MARGIN_BYTES)} gardée) : rien n’a été copié.')
        return 2
    if not assume_yes:
        if not sys.stdin or not sys.stdin.isatty():
            print('Accord requis : relancer dans une console, ou avec --oui.')
            return 2
        if not ask('Lancer la collecte maintenant ?'):
            print('Rien n’a été copié.')
            return 3
    start = datetime.now()
    result = c.collect(plan, probe=probe_for_videos(), progress=lambda m: print('  ' + m))
    check = c.verify()
    stamp = f'{start:%Y%m%d-%H%M%S}'
    report = c.write_report({'schema': 'bojart.collecte.v1', 'debut': start.isoformat(timespec='seconds'),
                             'fin': datetime.now().isoformat(timespec='seconds'), 'magasin': str(c.store),
                             'memoire': str(c.memory_state), 'sources': c.sources(),
                             'plan': {k: v for k, v in plan.items() if k != 'elements'} | {'elements': len(plan['elements'])},
                             'resultat': result, 'verification': check}, stamp)
    counts = result['comptes']
    print(f'\nCopiés et vérifiés : {counts["copie"]} ; déjà présents (même contenu) : {counts["doublon"]} ; '
          f'textes en mémoire : {counts["memoire"]} ; exports ChatGPT : {counts["sessions"]} ; '
          f'refusés par la mémoire (original gardé) : {counts["refuse"]} ; erreurs : {counts["erreur"]}')
    for problem in result['problemes'][:20]:
        print(f'  ! {problem["fichier"]} : {problem["detail"]}')
    print(f'Vérification du magasin : {check["verifies"]} originaux relus, ' + ('aucune anomalie.' if check['ok'] else
          f'{len(check["manquants"])} manquant(s), {len(check["alteres"])} altéré(s).'))
    print(f'Rapport : {report}')
    return 0 if check['ok'] and not counts['erreur'] else 1


def guided(c):
    print('Collecte guidée BOJ.ART : tes dossiers sont copiés et vérifiés, jamais modifiés ni publiés.')
    known = c.sources()
    if known:
        print('Dossiers déjà désignés :')
        for s in known:
            print(f'  - {s["nom"]} : {s["chemin"]}')
    while not known or ask('Ajouter un autre dossier (disque externe, ancien PC, Drive synchronisé, export) ?'):
        folder = pick_folder()
        if not folder:
            break
        print('Ce dossier concerne :')
        for key, (_, label) in PROJECT_MENU.items():
            print(f'  {key}. {label}')
        project = PROJECT_MENU.get(input('Choix [1] : ').strip() or '1', PROJECT_MENU['1'])[0]
        try:
            row = c.add_source(folder, project=project)
            print(('Déjà désigné : ' if row.get('deja_designe') else 'Ajouté : ') + row['chemin'])
        except ValueError as exc:
            print(f'Refusé : {exc}')
        known = c.sources()
    if not known:
        print('Aucun dossier désigné : rien à collecter.')
        return 0
    return run_collect(c)


# --- Simulation complète sur des dossiers synthétiques --------------------------------

def _bytes(label, size):
    out, counter = bytearray(), 0
    while len(out) < size:
        out += hashlib.sha256(f'{label}:{counter}'.encode()).digest()
        counter += 1
    return bytes(out[:size])


def simulation():
    with tempfile.TemporaryDirectory(prefix='bojart-collecte-', ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp).resolve()
        disk = tmp / 'Disque externe' / 'Vidéos BOJ.ART'
        old_pc = tmp / 'Ancien PC'
        files = {
            disk / 'Atelier épreuve.mp4': _bytes('atelier', 300_000),
            disk / 'sous dossier' / 'Making-of.MOV': _bytes('making', 200_000),
            old_pc / 'copie Atelier.mp4': _bytes('atelier', 300_000),
            old_pc / 'notes atelier.md': 'Notes de l’atelier : vernis Zéphyrine, séchage 24 h.\n'.encode('utf-8'),
            old_pc / 'ancien.txt': 'Fiche ancienne : vernis à l’eau'.encode('cp1252'),
            old_pc / '.env': b'TOKEN=ne-pas-collecter\n',
            old_pc / '.cache' / 'vignette.mp4': _bytes('cache', 1000),
            old_pc / 'logiciel.exe': b'MZ',
        }
        for path, data in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        export = old_pc / 'export chatgpt.zip'
        with zipfile.ZipFile(export, 'w') as z:
            z.writestr('conversations.json', json.dumps([{'title': 'Essai Quasarine', 'mapping': {}}], ensure_ascii=False))
            z.writestr('chat.html', '<p>non extrait</p>')
        links = 0
        try:
            os.symlink(disk / 'Atelier épreuve.mp4', old_pc / 'lien.mp4')
            links = 1
        except (OSError, NotImplementedError):
            pass
        before = {str(p): co.file_sha(p) for p in tmp.rglob('*') if p.is_file() and not p.is_symlink()}
        checks = {}
        with co.Collecte(tmp / 'collecte', tmp / 'memoire') as c:
            c.add_source(disk, project='bojart.creative')
            c.add_source(old_pc, project='bojart.creative')
            checks['dossier_designe_une_seule_fois'] = c.add_source(disk).get('deja_designe') is True
            try:
                c.add_source(tmp)
                checks['dossier_contenant_la_collecte_refuse'] = False
            except ValueError:
                checks['dossier_contenant_la_collecte_refuse'] = True
            first_plan = c.plan()
            first = c.collect(first_plan)
            second_plan = c.plan()
            counts = first['comptes']
            ignored = first_plan['par_source'][1]['ignores']
            checks['copies_verifiees_et_doublon_reconnu'] = (counts['copie'], counts['doublon']) == (5, 1)
            checks['aucune_relecture_au_second_passage'] = second_plan['elements'] == []
            checks['non_utf8_refuse_par_la_memoire_mais_conserve'] = (counts['refuse'] == 1 and
                                                                     any(p['fichier'] == 'ancien.txt' for p in first['problemes']))
            checks['secrets_et_dossiers_caches_ignores'] = ignored['caches_ou_prives'] >= 2 and ignored['autres'].get('.exe') == 1
            checks['liens_ignores'] = ignored['liens'] >= links
            stored = [p for p in c.store.rglob('*') if p.is_file()]
            checks['copies_en_lecture_seule'] = bool(stored) and all(not (p.stat().st_mode & stat.S_IWUSR) for p in stored)
            checks['magasin_verifie'] = c.verify()['ok']
            from bojart_memory import Memory
            with Memory(c.memory_state, readonly=True) as memory:
                notes = memory.search('Zéphyrine', project='bojart.creative', limit=3)['results']
                session = memory.search('Quasarine', project='bojart.jarvis', limit=3)['results']
            checks['texte_retrouve_en_memoire'] = counts['memoire'] == 1 and bool(notes)
            checks['export_chatgpt_retrouve_en_memoire'] = counts['sessions'] == 1 and bool(session)
            after = {str(p): co.file_sha(p) for p in tmp.rglob('*') if p.is_file() and not p.is_symlink()
                     and not p.resolve().is_relative_to(tmp / 'collecte') and not p.resolve().is_relative_to(tmp / 'memoire')}
            checks['sources_intactes'] = after == before
            victim = stored[0]
            os.chmod(victim, stat.S_IREAD | stat.S_IWRITE)
            with open(victim, 'ab') as handle:
                handle.write(b'!')
            checks['alteration_detectee'] = victim.relative_to(c.store).as_posix() in c.verify()['alteres']
    return {'simulation': True, 'ok': all(checks.values()), 'controles': checks, 'premier_passage': counts}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base', type=Path, help='Magasin de la collecte (par défaut ~/BOJART/collecte).')
    p.add_argument('--memoire', type=Path, help='Mémoire de Jarvis (par défaut ~/BOJART/memory).')
    sub = p.add_subparsers(dest='cmd')
    add = sub.add_parser('ajouter')
    add.add_argument('dossier', type=Path)
    add.add_argument('--nom')
    add.add_argument('--projet', choices=co.PROJECTS, default='bojart.creative')
    sub.add_parser('sources')
    sub.add_parser('plan')
    run = sub.add_parser('collecter')
    run.add_argument('--oui', action='store_true')
    sub.add_parser('verifier')
    sub.add_parser('simulation')
    a = p.parse_args(argv)
    if a.cmd == 'simulation':
        result = simulation()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['ok'] else 1
    with co.Collecte(a.base, a.memoire) as c:
        if a.cmd == 'ajouter':
            print(json.dumps(c.add_source(a.dossier, a.nom, a.projet), ensure_ascii=False, indent=2))
        elif a.cmd == 'sources':
            print(json.dumps(c.sources(), ensure_ascii=False, indent=2))
        elif a.cmd == 'plan':
            plan = c.plan()
            print(json.dumps({k: v for k, v in plan.items() if k != 'elements'} | {'elements': len(plan['elements'])},
                             ensure_ascii=False, indent=2))
        elif a.cmd == 'collecter':
            return run_collect(c, a.oui)
        elif a.cmd == 'verifier':
            result = c.verify()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['ok'] else 1
        else:
            return guided(c)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except ValueError as exc:
        sys.exit(f'Refusé : {exc}')
    except KeyboardInterrupt:
        sys.exit('Collecte interrompue : relancer pour reprendre, rien de ce qui est déjà vérifié n’est recopié.')
