#!/usr/bin/env python3
"""Restore the three pinned BOJART recovery branches without running their code."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'BOJART_RECUPERATION_2026-11-01'
REMOTE = 'https://github.com/Momolscode/BOJART.git'
PARTS = {
    1: ('635116df515f7910c5bc854176b642e282efbfb3', 'MANIFESTE.json'),
    2: ('2d2e01e3576e0a655729f6d273e9038e109f915a', 'recovery/2026-11-01/part02/manifest.json'),
    3: ('6e743b8a8ba90b6ab24a579a1f8c5aebaa8ba967', 'MANIFESTE_PARTIE_3.json'),
}


def safe_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or '\\' in name or ':' in name or any(ord(c) < 32 for c in name)
            or any(p in {'', '.', '..', '.git'} for p in name.split('/'))):
        raise ValueError(f'Unsafe path: {name}')
    return path


class GitReader:
    """Read objects through Git's binary-safe batch protocol, with bounded RAM."""
    def __enter__(self):
        self.process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        return self

    def __exit__(self, *exc):
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.wait()

    def copy(self, commit, name, writer):
        safe_path(name)
        self.process.stdin.write(f'{commit}:{name}\n'.encode())
        self.process.stdin.flush()
        header = self.process.stdout.readline().decode().strip().split()
        if len(header) != 3 or header[1] != 'blob':
            raise ValueError(f'Missing Git blob: {commit}:{name}')
        size = int(header[2])
        sha = hashlib.sha256()
        git_sha = hashlib.sha1(f'blob {size}\0'.encode())
        remaining = size
        while remaining:
            chunk = self.process.stdout.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError('Truncated Git blob')
            writer.write(chunk)
            sha.update(chunk)
            git_sha.update(chunk)
            remaining -= len(chunk)
        if self.process.stdout.read(1) != b'\n' or git_sha.hexdigest() != header[0]:
            raise ValueError('Invalid Git blob framing or checksum')
        return size, sha.hexdigest()

    def json(self, commit, name):
        with tempfile.TemporaryFile() as stream:
            self.copy(commit, name, stream)
            stream.seek(0)
            return json.load(stream)


def check_file(path, size, sha256):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if path.stat().st_size != size or digest.hexdigest() != sha256:
        raise ValueError(f'Checksum mismatch: {path.name}')


def restore(destination: Path, fetch=False):
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Choose a new destination; existing data is never overwritten')
    for commit, _ in PARTS.values():
        present = subprocess.run(['git', 'cat-file', '-e', commit + '^{commit}'],
                                 cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if present.returncode:
            if not fetch:
                raise ValueError('Archive commits missing: repeat with --fetch')
            subprocess.run(['git', 'fetch', '--depth=1', REMOTE, commit], cwd=ROOT, check=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Build privately beside the destination, then publish only a complete result.
    with tempfile.TemporaryDirectory(prefix='.bojart-restore-', dir=destination.parent) as temp:
        work = Path(temp)
        collection = work / PREFIX
        collection.mkdir()
        evidence = []
        with GitReader() as reader:
            commit, manifest_path = PARTS[1]
            manifest = reader.json(commit, manifest_path)
            archive = work / manifest['archive']['filename']
            safe_path(manifest['archive']['filename'])
            with archive.open('xb') as writer:
                for part in manifest['parts']:
                    if writer.tell() != part['offset']:
                        raise ValueError('Invalid archive chunk order')
                    got = reader.copy(commit, part['path'], writer)
                    if got != (part['bytes'], part['sha256']):
                        raise ValueError('Archive chunk checksum mismatch')
            check_file(archive, manifest['archive']['bytes'], manifest['archive']['sha256'])
            seen = set()
            with zipfile.ZipFile(archive) as source:
                for entry in source.infolist():
                    path = safe_path(entry.filename)
                    if entry.is_dir() or path.parts[0] != PREFIX or entry.filename in seen:
                        raise ValueError('Unexpected or duplicate ZIP entry')
                    if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('ZIP symlinks are not supported')
                    seen.add(entry.filename)
                    output = work / str(path)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(entry) as content, output.open('xb') as writer:
                        shutil.copyfileobj(content, writer, 1024 * 1024)
            index = json.loads((collection / 'INDEX.json').read_text(encoding='utf-8'))
            evidence.append({'part': 1, 'commit': commit, 'transport': 'exact_zip',
                             'zip_sha256': manifest['archive']['sha256'], 'chunks_verified': len(manifest['parts'])})
            for number in (2, 3):
                commit, manifest_path = PARTS[number]
                manifest = reader.json(commit, manifest_path)
                entries = manifest['entries'] if number == 2 else manifest['objects']
                for entry in entries:
                    relative = safe_path(entry['archive_path'])
                    if relative.parts[0] != PREFIX:
                        raise ValueError('Unexpected archive root')
                    output = work / str(relative)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    paths = entry.get('repository_paths') if number == 2 else (
                        [p['repo_path'] for p in entry['parts']] if entry['storage'] == 'chunks'
                        else [entry['repo_path']])
                    with output.open('xb') as writer:
                        for path in paths:
                            reader.copy(commit, path, writer)
                    check_file(output, entry['size'] if number == 2 else entry['bytes'], entry['sha256'])
                evidence.append({'part': number, 'commit': commit, 'transport': 'original_contents',
                                 'files_verified': len(entries)})
        objects = index['objects']
        if len(objects) != 3340 or len({o['sha256'] for o in objects}) != 3340:
            raise ValueError('Unexpected object count or duplicate object')
        for entry in objects:
            path = collection / str(safe_path(entry['path']))
            check_file(path, entry['bytes'], entry['sha256'])
        expected = {entry['path'] for entry in objects}
        actual = {p.relative_to(collection).as_posix() for p in (collection / 'objets').rglob('*') if p.is_file()}
        if actual != expected:
            raise ValueError('Restored object inventory differs from INDEX.json')
        source_ids = {s['id'] for s in index['sources']}
        by_hash = {o['sha256']: o for o in objects}
        for entry in index['occurrences']:
            if entry['source_id'] not in source_ids or entry['sha256'] not in by_hash:
                raise ValueError('Broken provenance reference')
            if entry['bytes'] != by_hash[entry['sha256']]['bytes']:
                raise ValueError('Provenance size mismatch')
        report = {'schema_version': 1, 'ok': True, 'parts': evidence,
                  'objects': len(objects), 'unique_bytes': sum(o['bytes'] for o in objects),
                  'sources': len(index['sources']), 'occurrences': len(index['occurrences']),
                  'verification': 'All bytes read from pinned Git commits; Git SHA-1, SHA-256, sizes and ZIP CRC checked',
                  'limits': 'Recovery collection only; not a complete ChatGPT export or workshop PC backup'}
        (collection / 'VERIFICATION_GITHUB.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # Reserve the destination with mkdir (atomic refusal if another process created it).
        destination.mkdir()
        try:
            collection.rename(destination / PREFIX)
        except Exception:
            destination.rmdir()
            raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--fetch', action='store_true', help='Fetch missing pinned commits from Momolscode/BOJART')
    args = parser.parse_args()
    print(json.dumps(restore(args.destination, args.fetch), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
