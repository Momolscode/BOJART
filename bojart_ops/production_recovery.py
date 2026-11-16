"""Join a production recipe to archived bytes; prepare an isolated workspace."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tempfile

from .audit import strict_json
from .orchestration import require, safe_path
from tools.restore_recovery_2026_11_01 import PARTS

PROJECT = 'productions/le-dernier-geste'
CATALOG = 'data/catalog/recovery-2026-11-01'
MANIFEST = 'data/catalog/repository_manifest.json'
RECEIPT = 'RECOVERY_RECEIPT.json'


def portable_path(name):
    safe_path(name)
    for part in name.split('/'):
        require(part.lower() != '.git' and not re.search(r'[<>"|?*]', part)
                and not part.endswith((' ', '.'))
                and not re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part),
                'Non-portable production path')
    return name


def regular(root, name):
    path = root / portable_path(name)
    require(path.resolve().is_relative_to(root), 'Source outside root')
    require(not any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)),
            'Source symlink refused')
    require(path.is_file(), 'Source file missing')
    return path


def metadata(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def record_ok(row):
    require(isinstance(row, dict), 'Invalid content record')
    portable_path(row['path'])
    require(type(row['bytes']) is int and row['bytes'] >= 0, 'Invalid byte count')
    require(isinstance(row['sha256'], str) and re.fullmatch('[0-9a-f]{64}', row['sha256']),
            'Invalid content digest')


def build_plan(repo, project=PROJECT):
    """Read current source policy and join on SHA-256, never on a similar name."""
    repo = Path(repo).resolve()
    portable_path(project)
    require(project.startswith('productions/'), 'Production project required')
    inputs = {}

    def read(name):
        path = regular(repo, name)
        require(path.stat().st_size <= 1_000_000, 'Metadata too large')
        raw = path.read_bytes()
        inputs[name] = metadata(raw)
        return raw

    manifest = strict_json(read(MANIFEST).decode('utf-8'))
    require(manifest.get('schema_version') == 1, 'Unknown repository manifest')
    entries = {}
    for row in manifest['files']:
        require(row['path'] not in entries, 'Duplicate repository path')
        entries[row['path']] = row

    def registered(name):
        raw = read(name)
        require(name in entries and all(inputs[name][key] == entries[name][key]
                                       for key in ('bytes', 'sha256')), 'Source differs from repository manifest')
        return raw

    assets = strict_json(registered(project + '/ASSETS.json').decode('utf-8'))['assets']
    require(isinstance(assets, list) and 0 < len(assets) <= 1000, 'Invalid asset list')
    catalogue = {}
    for part in sorted(PARTS):
        name = f'{CATALOG}/contents-part-{part:02d}.jsonl'
        for line in registered(name).decode('utf-8').splitlines():
            if not line.strip():
                continue
            row = strict_json(line)
            record_ok(row)
            require(type(row['part']) is int and row['part'] == part and row['path'].startswith('objets/'),
                    'Invalid archive location')
            require(row['sha256'] not in catalogue, 'Duplicate catalogue digest')
            catalogue[row['sha256']] = row

    output_names, selected = {RECEIPT.casefold()}, []
    for asset in assets:
        record_ok(asset)
        require(asset['bytes'] > 0, 'Empty media asset refused')
        require(isinstance(asset.get('role'), str) and asset['role'].strip(), 'Asset role missing')
        name = asset['path']
        require(name.casefold() not in output_names, 'Colliding output paths')
        output_names.add(name.casefold())
        archived = catalogue.get(asset['sha256'])
        row = {k: asset[k] for k in ('path', 'bytes', 'sha256', 'role')}
        row['status'] = 'catalogued' if archived else 'not_found_in_catalogue'
        row['archive'] = None
        if archived:
            require(archived['bytes'] == asset['bytes'], 'Catalogue size conflicts with recipe')
            row['archive'] = {'part': archived['part'], 'commit': PARTS[archived['part']][0],
                              'collection_path': archived['path']}
        selected.append(row)

    recipes = []
    for name in sorted(entries):
        if not name.startswith(project + '/'):
            continue
        relative = name[len(project) + 1:]
        portable_path(relative)
        require(Path(relative).suffix in {'.md', '.json', '.py'} or Path(relative).name == '.gitignore',
                'Only reviewed text recipes may be copied')
        require(relative.casefold() not in output_names, 'Recipe or receipt collides with media')
        output_names.add(relative.casefold())
        raw = registered(name)
        recipes.append({'path': relative, **metadata(raw)})
    # Also reject a file being used as the parent directory of another output.
    require(not any('/'.join(name.split('/')[:i]) in output_names
                    for name in output_names for i in range(1, len(name.split('/')))), 'Output path hierarchy conflict')
    matched = sum(row['archive'] is not None for row in selected)
    return {'schema': 'bojart.production-recovery-plan.v1', 'project': project,
            'summary': {'assets': len(selected), 'catalogued_assets': matched,
                        'required_bytes': sum(row['bytes'] for row in selected), 'recipe_files': len(recipes)},
            'complete': matched == len(selected), 'assets': selected, 'recipes': recipes,
            'inputs': inputs, 'source_bytes_verified': False, 'scripts_executed': 0,
            'artistic_approval': False, 'target_hardware_qualified': False,
            'limits': ['Catalogue match is not a new verification of archive bytes.',
                       'Historical TEST19 remains provisional; this does not recover or approve final G2.']}


def load_production(repo, audit, config):
    settings = config.get('production_recovery')
    if settings is None:
        return None
    require(isinstance(settings, dict) and set(settings) == {'project'}, 'Invalid production recovery configuration')
    result = build_plan(repo, settings['project'])
    inventory = {row['path']: row for row in audit['files']}
    require(all(name in inventory and all(row[key] == inventory[name][key] for key in ('bytes', 'sha256'))
                for name, row in result['inputs'].items()), 'Production inputs changed since audit')
    return result


def copy_verified(source, target, expected):
    target.parent.mkdir(parents=True, exist_ok=True)
    size, digest = 0, hashlib.sha256()
    with source.open('rb') as reader, target.open('xb') as writer:
        while block := reader.read(1024 * 1024):
            size += len(block)
            require(size <= expected['bytes'], 'Source exceeds registered size')
            writer.write(block)
            digest.update(block)
    require(size == expected['bytes'] and digest.hexdigest() == expected['sha256'], 'Source content differs')
    with target.open('rb') as reader:
        require(hashlib.file_digest(reader, 'sha256').hexdigest() == expected['sha256'], 'Copied content differs')


def prepare_workspace(repo, collection, destination, project=PROJECT):
    """Copy exact media and current recipes; never run a script or replace data."""
    repo = Path(repo).resolve()
    collection = Path(collection).expanduser().absolute()
    destination = Path(destination).expanduser().absolute()
    require(not any(p.is_symlink() for p in (collection, *collection.parents, destination, *destination.parents)),
            'Linked input or destination refused')
    collection = collection.resolve(strict=True)
    require(collection.is_dir(), 'Recovery collection required')
    if destination.exists():
        raise FileExistsError('Choose a new destination; existing data is never overwritten')
    require(destination.parent.is_dir(), 'Destination parent must already exist')
    destination = destination.resolve()
    require(not destination.is_relative_to(repo) and not destination.is_relative_to(collection),
            'Destination must be outside the repository and recovery collection')
    plan = build_plan(repo, project)
    require(plan['complete'], 'Required media missing from catalogue')
    # Validate every selected path before making any output directory.
    sources = [(regular(collection, row['archive']['collection_path']), row) for row in plan['assets']]
    recipes = [(regular(repo, project + '/' + row['path']), row) for row in plan['recipes']]
    with tempfile.TemporaryDirectory(prefix='.bojart-production-', dir=destination.parent) as temp:
        workspace = Path(temp) / Path(project).name
        workspace.mkdir()
        for source, row in sources + recipes:
            copy_verified(source, workspace / row['path'], row)
        receipt = {'schema': 'bojart.production-recovery-receipt.v1',
                   'project': project, 'summary': plan['summary'], 'inputs': plan['inputs'],
                   'assets': [{**row, 'status': 'copied_verified'} for row in plan['assets']], 'recipes': plan['recipes'],
                   'source_bytes_verified': True, 'copied_bytes_verified': True,
                   'scripts_executed': 0, 'renders_created': 0, 'provider_calls': 0,
                   'artistic_approval': False, 'target_hardware_qualified': False}
        (workspace / RECEIPT).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        destination.mkdir()  # Atomic refusal if another process reserved this name.
        try:
            workspace.rename(destination / workspace.name)
        except Exception:
            destination.rmdir()
            raise
    return receipt
