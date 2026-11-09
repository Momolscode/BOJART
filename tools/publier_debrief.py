#!/usr/bin/env python3
"""Pousser sur GitHub le débrief de la tour (lancé par Publier_Debrief_BOJART.cmd).

  python tools/publier_debrief.py                    # montre ce qui part, demande l'accord, pousse
  python tools/publier_debrief.py --note "micro OK"  # ajoute une phrase de l'opérateur au débrief
  python tools/publier_debrief.py --simulation       # prépare et contrôle tout, sans pousser
  python tools/publier_debrief.py --avec-diagnostic  # joint aussi le diagnostic du poste
  python tools/publier_debrief.py essai              # essai complet sur un faux dépôt local, sans réseau

Seuls les rapports écrits par Jarvis dans ~/BOJART partent (installation, banc, voix, mesures),
nettoyés du dossier personnel, du nom de session et du nom du poste, sur une branche neuve
tour/debrief-… du dépôt approuvé. Jamais main, jamais de poussée forcée, aucun média.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bojart_ops import debrief_tour as dt  # noqa: E402

ROOT = dt.ROOT


def options(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('commande', nargs='?', choices=('publier', 'essai'), default='publier')
    p.add_argument('--oui', action='store_true', help='Accord donné à l’avance.')
    p.add_argument('--simulation', action='store_true', help='Tout préparer et contrôler, sans pousser.')
    p.add_argument('--note', default='', help='Une phrase de l’opérateur, publiée avec le débrief.')
    p.add_argument('--avec-diagnostic', action='store_true', help='Joindre le dernier diagnostic du poste.')
    return p.parse_args(argv)


def hint(message):
    low = message.lower()
    if any(k in low for k in ('could not read username', 'authentication failed', 'terminal prompts disabled', 'permission denied', '403')):
        return ('Connexion GitHub refusée. Sur la tour : ouvrir « Git Bash », lancer « git ls-remote ' + dt.REMOTE_URL + ' » '
                'et se connecter dans la fenêtre qui s’ouvre, avec un compte qui a le droit d’écrire dans le dépôt. Puis relancer.')
    if any(k in low for k in ('could not resolve host', 'unable to access', 'timed out')):
        return 'GitHub injoignable : vérifier la connexion Internet, puis relancer. Rien n’a été poussé.'
    return None


def publier(a):
    git = dt.find_git()
    if not git:
        print('Git absent : relancer Installer_Tout_BOJART.cmd (il installe Git), ou « winget install --id Git.Git -e ».', file=sys.stderr)
        return 2
    families = dt.DEFAULT_FAMILIES + (('diagnostic',) if a.avec_diagnostic else ())
    stamp = datetime.now()
    interactive = not (a.oui or a.simulation)
    if interactive and not (sys.stdin and sys.stdin.isatty()):
        print('Accord requis : relancer dans une console, ou avec --oui.')
        return 2
    try:
        kept, aside = dt.collect(families=families)
        note = a.note
        if interactive and kept and not note:
            note = input('Une phrase à joindre au débrief (Entrée pour ne rien ajouter) : ')
        folder, files, refused = dt.prepare(kept, note=note, stamp=stamp, aside=aside)
        print(f'Débrief de la tour : {len(files) - 1} rapport(s), dossier {folder}')
        for rel, text in sorted(files.items()):
            print(f'  {rel[len(folder) + 1:]:<60} {len(text.encode("utf-8")):>9} octets')
        for item in refused:
            print(f'  laissé sur la tour : {item["fichier"]} ({item["raison"]})')
        print(f'Destination : {dt.WEB_URL}, branche neuve tour/debrief-{stamp:%Y%m%d-%H%M%S} (jamais main).')
        print('Ce dépôt est PUBLIC : ces rapports (résultats, versions, système, processeur, carte graphique) seront lisibles par tous.')
        print('Aucun média, aucune base, aucune donnée client ne part.')
        if interactive:
            if input('Publier ce débrief ? [o/N] ').strip().lower() not in ('o', 'oui'):
                print('Rien n’a été poussé.')
                return 1
        clone = dt.find_clone(ROOT, git=git)
        result = dt.publish(files, folder, clone=clone, git=git, stamp=stamp, push=not a.simulation)
    except dt.Refused as error:
        print(f'Refusé : {error}', file=sys.stderr)
        extra = hint(str(error))
        if extra:
            print(extra, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('Débrief poussé. Le lire : ' + result['voir'] if result['pousse'] else 'Simulation : tout est prêt et contrôlé, rien n’a été poussé.')
    return 0


def essai():
    """End to end on a local fake « GitHub », with planted personal data and a planted token. No network."""
    git = dt.find_git()
    if not git:
        print(json.dumps({'ok': None, 'detail': 'Git absent : essai non exécuté.'}, ensure_ascii=False))
        return 0
    from bojart_ops.banc_statique import manifest_files
    tmp = Path(tempfile.mkdtemp(prefix='bojart-debrief-essai-'))
    controls = {}
    try:
        def run(args, cwd):
            return subprocess.run([str(git), *args], cwd=str(cwd), capture_output=True, text=True, encoding='utf-8', errors='replace', check=True).stdout
        seed, origin = tmp / 'graine', tmp / 'github' / 'BOJART.git'
        # The published tree, as the manifest lists it, becomes the first commit of the fake remote: the same
        # files in a clone, in a « Download ZIP » copy and in a working copy with changes not yet committed.
        for name in manifest_files(ROOT):
            if (ROOT / name).is_file():
                (seed / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, seed / name)
        run(['init', '-q', '-b', 'main'], seed)
        run(['add', '-A', '-f'], seed)
        run(['-c', 'user.name=essai', '-c', 'user.email=essai@exemple.invalid', 'commit', '-q', '--no-gpg-sign', '-m', 'graine'], seed)
        origin.parent.mkdir(parents=True)
        run(['clone', '-q', '--bare', str(seed), str(origin)], tmp)
        main_before = run(['rev-parse', 'refs/heads/main'], origin).strip()
        home = tmp / 'Users' / 'Camille Exemple'
        env = {'USERPROFILE': str(home), 'USERNAME': 'Camille Exemple', 'COMPUTERNAME': 'TOUR-ESSAI'}
        base = home / 'BOJART'
        for folder in ('installation', 'banc', 'banc-voix/rapports', 'benchmarks'):
            (base / folder).mkdir(parents=True)
        (base / 'installation/installation-20261109-000000.json').write_text(json.dumps({
            'journal': str(base / 'installation'), 'poste': 'TOUR-ESSAI', 'contact': 'camille@exemple.fr',
            'synthese': {'termine': True, 'reste_a_faire': []}}), encoding='utf-8')
        (base / 'banc/banc-1.json').write_text(json.dumps({'python_teste': str(home / 'BOJART/.venv/python.exe'),
                                                           'synthese': {'tests_executes': 3}}), encoding='utf-8')
        (base / 'banc/banc-1.md').write_text(f'# Banc\n\nPython : `{home}`\n', encoding='utf-8')
        (base / 'banc/capture.png').write_bytes(b'\x89PNG\r\n\x1a\n' + bytes(64))
        (base / 'banc-voix/rapports/mesure.md').write_text('# Voix\n', encoding='utf-8')
        clone = tmp / 'tour' / 'BOJART'
        run(['clone', '-q', str(origin), str(clone)], tmp)
        head_before, status_before = run(['rev-parse', 'HEAD'], clone).strip(), run(['status', '--porcelain'], clone)
        stamp = datetime(2026, 11, 9, 12, 0, 0)
        kept, aside = dt.collect(home)
        folder, files, refused = dt.prepare(kept, home, env, 'TOUR-ESSAI', note=f'essai depuis {home}', stamp=stamp, aside=aside)
        # The fake remote is approved under the exact name Git gives it (Windows rewrites the path).
        common = dict(clone=clone, git=git, approved=run(['remote', 'get-url', 'origin'], clone).strip(), out=lambda *_: None)
        result = dt.publish(files, folder, stamp=stamp, **common)
        pushed = run(['ls-tree', '-r', '--name-only', result['branche']], origin).splitlines()
        seeded = set(run(['ls-tree', '-r', '--name-only', 'main'], origin).splitlines())
        text = ''.join(run(['show', f'{result["branche"]}:{p}'], origin) for p in pushed if p.startswith(folder + '/'))
        controls['branche_neuve_poussee'] = result['pousse'] and dt.BRANCH.match(result['branche']) is not None
        controls['main_inchange'] = run(['rev-parse', 'refs/heads/main'], origin).strip() == main_before
        controls['seuls_le_dossier_et_le_manifeste_changent'] = (
            {p for p in pushed if p not in seeded} == set(files)
            and run(['diff', '--name-only', 'main', result['branche']], origin).split() == sorted([dt.MANIFEST, *files]))
        controls['donnees_personnelles_retirees'] = not any(s in text for s in ('Camille', 'TOUR-ESSAI', 'exemple.fr', str(tmp)))
        controls['media_laisse_sur_la_tour'] = any(r['fichier'] == 'capture.png' for r in refused) and not any(p.endswith('.png') and p.startswith(folder) for p in pushed)
        controls['copie_de_travail_intacte'] = (run(['rev-parse', 'HEAD'], clone).strip() == head_before
                                               and run(['status', '--porcelain'], clone) == status_before)
        controls['identite_neutre'] = run(['log', '-1', '--format=%an <%ae>', result['branche']], origin).strip() == f'{dt.IDENTITY[0]} <{dt.IDENTITY[1]}>'
        secret = dict(files)
        secret[f'{folder}/installation/jeton.json'] = json.dumps({'jeton': 'ghp_' + 'A' * 36})
        heads = run(['for-each-ref', '--format=%(refname)', 'refs/heads'], origin)
        try:
            dt.publish(secret, folder, stamp=datetime(2026, 11, 9, 12, 0, 1), **common)
            controls['jeton_refuse'] = False
        except dt.Refused as error:  # refused by the repository gate, for that file, and nothing reached the remote
            controls['jeton_refuse'] = ('possible_secret' in str(error) and 'jeton.json' in str(error)
                                        and run(['for-each-ref', '--format=%(refname)', 'refs/heads'], origin) == heads)
        try:
            dt.publish(files, folder, stamp=stamp, **common)
            controls['branche_existante_refusee'] = False
        except dt.Refused:
            controls['branche_existante_refusee'] = True
        try:
            dt.publish(files, folder, stamp=datetime(2026, 11, 9, 12, 0, 2), **{**common, 'approved': dt.APPROVED})
            controls['autre_depot_refuse'] = False
        except dt.Refused:
            controls['autre_depot_refuse'] = True
        dry = dt.publish(files, folder, stamp=datetime(2026, 11, 9, 12, 0, 3), push=False, **common)
        controls['simulation_ne_pousse_rien'] = not dry['pousse'] and run(['for-each-ref', '--format=%(refname)', 'refs/heads'], origin) == heads
        controls['arbre_temporaire_retire'] = run(['worktree', 'list', '--porcelain'], clone).count('worktree ') == 1
        ok = all(controls.values())
        print(json.dumps({'ok': ok, 'controles': controls, 'fichiers_pousses': len(files), 'git': run(['--version'], tmp).strip()}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    except (dt.Refused, subprocess.CalledProcessError, OSError) as error:
        detail = getattr(error, 'stderr', None) or str(error)
        print(json.dumps({'ok': False, 'controles': controls, 'detail': str(detail)[-600:]}, ensure_ascii=False, indent=2))
        return 1
    finally:
        def writable(func, path, _):
            os.chmod(path, 0o700)
            func(path)
        shutil.rmtree(tmp, onerror=writable)


def main(argv=None):
    a = options(argv)
    return essai() if a.commande == 'essai' else publier(a)


if __name__ == '__main__':
    raise SystemExit(main())
