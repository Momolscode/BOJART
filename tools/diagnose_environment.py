#!/usr/bin/env python3
"""Inventaire local BOJ.ART : matériel et outils, sans installation ni rendu."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_ops.environment import EXECUTABLES, report


def summary(result):
    values = result['target_hardware_dataset']['values']
    ram = f"{values['ram_gib']:.1f} Gio" if values['ram_gib'] is not None else 'inconnue'
    lines = ['BOJ.ART — diagnostic du poste exécutant cette commande',
             f"Système : {values['os_version']} | RAM visible : {ram}"]
    for device in result['gpu']['devices']:
        vram = f"{device['vram_gib']:.1f} Gio" if device['vram_gib'] is not None else 'inconnue'
        lines.append(f"GPU : {device['name']} | VRAM : {vram}")
    if not result['gpu']['devices']:
        lines.append('GPU NVIDIA : non observé ; les autres fournisseurs ne sont pas sondés.')
    for key, row in result['executables'].items():
        if key == 'nvidia_smi':
            continue
        state = 'version '+row['version']+' vérifiée' if row['version_probe'] == 'verified' else (
            'détecté, version non vérifiée' if row['detected'] else 'non trouvé dans les chemins examinés')
        lines.append(f'{key} : {state}')
    lines += ['Le rapport JSON contient les dépendances Python et les prochaines vérifications.',
              'Micro, écrans, imprimantes, comptes et parcours de création restent à qualifier.']
    return '\n'.join(lines)


def save_report(result, destination):
    destination = destination.expanduser().resolve()
    if destination.is_relative_to(ROOT):
        raise ValueError('Conserver le rapport du poste hors du dépôt public.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: a second observation cannot replace an earlier receipt.
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool-path', action='append', default=[], metavar='ID=CHEMIN',
                        help='Binaire absolu déjà installé. IDs : '+', '.join(EXECUTABLES))
    parser.add_argument('--summary', action='store_true', help='Afficher un résumé lisible ; le fichier enregistré reste complet.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--save', action='store_true', help='Enregistrer sous ~/BOJART/diagnostics.')
    group.add_argument('--output', type=Path, help='Nouveau fichier JSON hors du dépôt.')
    args = parser.parse_args(argv)
    overrides = {}
    for value in args.tool_path:
        key, sep, path = value.partition('=')
        if not sep or key in overrides or key not in EXECUTABLES or not path:
            parser.error('--tool-path exige un identifiant connu et unique, puis =CHEMIN.')
        overrides[key] = path
    try:
        result = report(tool_paths=overrides)
        if args.save or args.output:
            date = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            destination = args.output or Path.home()/'BOJART/diagnostics'/f'{date}-{uuid.uuid4().hex[:8]}.json'
            saved = save_report(result, destination)
            print(f'Rapport enregistré : {saved}', file=sys.stderr)
        print(summary(result) if args.summary else json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        print('Diagnostic interrompu : '+type(exc).__name__+'. Vérifier les arguments et le dossier de sortie.', file=sys.stderr)
        return 2
    # Success means the observation completed, never that the workshop is qualified.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
