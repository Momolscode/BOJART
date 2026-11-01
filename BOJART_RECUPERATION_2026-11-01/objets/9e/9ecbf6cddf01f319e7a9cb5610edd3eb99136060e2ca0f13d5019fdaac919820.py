#!/usr/bin/env python3
"""Fetch the exact public NuGet artifacts used by this investigation."""
import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    results = []
    for target in json.loads((ROOT / 'provenance/TARGETS.json').read_text()):
        if not target['download_url'].startswith('https://api.nuget.org/v3-flatcontainer/'):
            raise ValueError('Expected the pinned public NuGet origin')
        folder = a.out / (target['package'] + '.' + target['version'])
        folder.mkdir(exist_ok=True)
        package = folder / 'original.nupkg'
        if not package.exists():
            urllib.request.urlretrieve(target['download_url'], package)
        if hashlib.sha256(package.read_bytes()).hexdigest() != target['package_sha256']:
            raise ValueError('Package identity mismatch; existing file left unchanged')
        dest = folder / target['member']
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(package) as z:
            data = z.read(target['member'])
        if hashlib.sha256(data).hexdigest() != target['dll_sha256']:
            raise ValueError('Selected DLL identity mismatch')
        if dest.exists() and dest.read_bytes() != data:
            raise ValueError('Destination differs; use a fresh folder')
        dest.write_bytes(data)
        results.append({'package': target['package'], 'version': target['version'],
                        'dll': str(dest.resolve()), 'sha256_verified': True})
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
