#!/usr/bin/env python3
"""Restore only exact, registered demo assets from the user's local M07 archive."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_ARCHIVE='4227b83a46596d788b305c03ceb01cf00be727cb34d8f17ab7d485107d50a58b'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def hydrate(archive, destination=ROOT/'jarvis'):
    archive=Path(archive);destination=Path(destination).resolve()
    if sha(archive)!=EXPECTED_ARCHIVE:raise ValueError('Archive différente de la livraison M07 vérifiée.')
    records=[json.loads(line) for line in (ROOT/'data/catalog/assets.jsonl').read_text(encoding='utf-8').splitlines()]
    selected=[r for r in records if r['origin']=='library:libfile_875f76c239cc8191a4c147a11293c9ff' and r['source_path'].startswith(('apps/jarvis/studio_media/','apps/jarvis/studio_assets/'))]
    prepared=[]
    with zipfile.ZipFile(archive) as z:
        for r in selected:
            path=destination/r['source_path']
            if not path.resolve().is_relative_to(destination) or path.is_symlink():raise ValueError('Destination invalide.')
            data=z.read('BOJART_JARVIS_M07/'+r['source_path'])
            if hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError('Média altéré.')
            if path.exists() and sha(path)!=r['sha256']:raise ValueError('Refus de remplacer un fichier différent.')
            prepared.append((path,data))
    for path,data in prepared:
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(data)
    return {'restored_or_verified':len(prepared),'paths':[str(p.relative_to(destination)) for p,_ in prepared]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args()
    print(json.dumps(hydrate(a.archive),indent=2))
