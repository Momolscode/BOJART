#!/usr/bin/env python3
"""Restore the checked archive into a new directory; never execute recovered files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('Invalid relative path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Unsafe relative path')
    return Path(*path.parts)


def checked_source(root, name):
    path = root / safe_relative(name)
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Source escapes archive')
    if not path.is_file():
        raise ValueError('Missing part: ' + name)
    return path


def restore(root, destination):
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination must not exist')
    manifest = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported manifest')
    objects = manifest['objects']
    names = set()
    hashes = set()
    for obj in objects:
        name = str(safe_relative(obj['path']))
        if name in names or obj['sha256'] in hashes:
            raise ValueError('Duplicate object')
        names.add(name)
        hashes.add(obj['sha256'])
        if not re.fullmatch(r'[0-9a-f]{64}', obj['sha256']):
            raise ValueError('Invalid checksum')
        if not obj['parts'] or sum(p['bytes'] for p in obj['parts']) != obj['bytes']:
            raise ValueError('Invalid byte count')
        for part in obj['parts']:
            checked_source(root, part['path'])
    if len(objects) != manifest['unique_objects']:
        raise ValueError('Invalid object count')
    if sum(o['bytes'] for o in objects) != manifest['unique_bytes']:
        raise ValueError('Invalid total size')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bojart-restore-', dir=destination.parent) as tmp:
        stage = Path(tmp) / 'restored'
        stage.mkdir()
        for obj in objects:
            target = stage / safe_relative(obj['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            written = 0
            with target.open('xb') as out:
                for part in obj['parts']:
                    source = checked_source(root, part['path'])
                    part_digest = hashlib.sha256()
                    size = 0
                    with source.open('rb') as src:
                        while chunk := src.read(1024 * 1024):
                            size += len(chunk)
                            part_digest.update(chunk)
                            digest.update(chunk)
                            out.write(chunk)
                    if size != part['bytes'] or part_digest.hexdigest() != part['sha256']:
                        raise ValueError('Corrupted part: ' + part['path'])
                    written += size
            if written != obj['bytes'] or digest.hexdigest() != obj['sha256']:
                raise ValueError('Corrupted object: ' + obj['path'])
        for name in ['MANIFEST.json', 'MEDIA_RECOVERY.json', 'LIBRARY_RECOVERY.json',
                     'MEDIA_VALIDATION.json', 'COVERAGE.json', 'CONTEXT_RETRIEVAL.json',
                     'CATALOGUE.html', 'README.md']:
            if (root / name).is_file():
                shutil.copyfile(root / name, stage / name)
        if (root / 'sources').is_dir():
            shutil.copytree(root / 'sources', stage / 'sources')
        if destination.exists() or destination.is_symlink():
            raise FileExistsError('Destination appeared during restoration')
        stage.rename(destination)
    return {'objects_verified': len(objects), 'bytes_verified': manifest['unique_bytes']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    print(json.dumps(restore(Path(__file__).resolve().parent, args.destination)))
