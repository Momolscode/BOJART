#!/usr/bin/env python3
"""Verify the published source manifest; hashes detect changes, not authorship."""
from pathlib import Path, PurePosixPath
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def check(root=ROOT):
 manifest=json.loads((root/'preservation/REPOSITORY_MANIFEST.json').read_text())
 bad=[]
 for r in manifest['files']:
  rel=PurePosixPath(r['path'])
  if rel.is_absolute() or '..' in rel.parts or '\\' in r['path']:raise ValueError('Unsafe manifest')
  p=root.joinpath(*rel.parts)
  if not p.is_file() or p.is_symlink():bad.append({'path':r['path'],'error':'missing_or_link'});continue
  if p.stat().st_size!=r['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:bad.append({'path':r['path'],'error':'changed'})
 return {'ok':not bad,'verified_files':len(manifest['files']),'errors':bad,'scope':'tracked source snapshot only; original vault verified separately'}
if __name__=='__main__':
 r=check();print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(0 if r['ok'] else 1)
