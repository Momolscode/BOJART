#!/usr/bin/env python3
"""Validate public source policy, structured provenance and an exact byte manifest."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
MANIFEST='data/catalog/repository_manifest.json'
PRIVATE_EXT={'.zip','.bundle','.mp4','.mov','.mp3','.wav','.sqlite','.sqlite3','.db','.pem','.key','.png','.jpg','.jpeg','.webp','.pdf','.ttf'}
SECRET=[re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(r'github_pat_[A-Za-z0-9_]{40,}'),re.compile(r'sk-proj-[A-Za-z0-9_-]{30,}'),re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(r'https?://[^\s"<>]+[?&](?:X-Amz-Signature|sig)=[A-Za-z0-9%]{20,}')]

def names(root=ROOT):
    data=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root)
    return sorted(set(x for x in data.decode().split('\0') if x))

def validate(write_manifest=False):
    issues=[];files=[]
    for name in names():
        p=ROOT/name;rel=PurePosixPath(name)
        if p.is_symlink() or not p.is_file() or '..' in rel.parts:issues.append({'path':name,'error':'missing_or_unsafe'});continue
        if p.suffix.lower() in PRIVATE_EXT or (p.name.startswith('.env') and p.name!='.env.example') or any(part in {'node_modules','.venv','private','objects'} for part in rel.parts):
            issues.append({'path':name,'error':'private_or_binary_in_public_git'});continue
        b=p.read_bytes()
        if len(b)>1_000_000:issues.append({'path':name,'error':'file_over_source_limit'})
        try:text=b.decode('utf-8')
        except UnicodeDecodeError:issues.append({'path':name,'error':'non_utf8'});continue
        if '\x00' in text or re.search(r'data:(?:video|image)/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/]{100,}',text):issues.append({'path':name,'error':'embedded_media'})
        if any(pattern.search(text) for pattern in SECRET):issues.append({'path':name,'error':'possible_secret'})
        if re.search(r'https://[a-zA-Z0-9.-]+\.cloudfront\.net/user_[^\s"<>]+',text):issues.append({'path':name,'error':'direct_private_media_locator'})
        if name!=MANIFEST:files.append({'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    claims=[json.loads(x) for x in (ROOT/'data/knowledge/claims.jsonl').read_text().splitlines()]
    sources=json.loads((ROOT/'data/knowledge/sources.json').read_text())
    source_ids={s['source_id'] for s in sources};claim_ids={c['claim_id'] for c in claims}
    for source in sources:
        if 'path' in source:
            p=ROOT/source['path']
            if not p.resolve().is_relative_to(ROOT) or not p.is_file():issues.append({'source':source['source_id'],'error':'missing_source_evidence'})
    if len(claim_ids)!=len(claims):issues.append({'error':'duplicate_claim_id'})
    for c in claims:
        if c['project'] not in {'bojart.jarvis','bojart.creative','bojart.sites'} or c['status'] not in {'user_decision','source_reported','observed','proposal'}:issues.append({'claim':c['claim_id'],'error':'invalid_classification'})
        if not c['sources'] or not set(c['sources'])<=source_ids:issues.append({'claim':c['claim_id'],'error':'missing_provenance'})
        if not set(c['supersedes'])<=claim_ids or c['claim_id'] in c['supersedes']:issues.append({'claim':c['claim_id'],'error':'invalid_supersession'})
    # Reject cycles so "current" cannot depend on a circular correction chain.
    graph={c['claim_id']:c['supersedes'] for c in claims}
    def visit(n,stack):
        if n in stack:raise ValueError('supersession_cycle')
        for parent in graph[n]:visit(parent,stack|{n})
    try:
        for c in graph:visit(c,set())
    except (ValueError,KeyError):issues.append({'error':'invalid_claim_graph'})
    for r in json.loads((ROOT/'data/knowledge/index.json').read_text()):
        p=ROOT/r['path']
        if not p.resolve().is_relative_to(ROOT) or not p.is_file():issues.append({'path':r['path'],'error':'missing_canonical_document'})
    if write_manifest and not issues:
        (ROOT/MANIFEST).write_text(json.dumps({'schema_version':1,'scope':'public monorepo files except this manifest; external originals separately inventoried','files':files},ensure_ascii=False,indent=2)+'\n')
    elif not (ROOT/MANIFEST).is_file():issues.append({'error':'manifest_missing'})
    else:
        expected=json.loads((ROOT/MANIFEST).read_text())['files']
        actual={f['path']:f for f in files};expected_map={f['path']:f for f in expected}
        for path in actual.keys()|expected_map.keys():
            if actual.get(path)!=expected_map.get(path):issues.append({'path':path,'error':'manifest_mismatch'})
    return {'ok':not issues,'files':len(files),'claims':len(claims),'issues':issues,'note':'Pattern scan is not a guarantee of absence of all sensitive content.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write-manifest',action='store_true');a=p.parse_args()
    result=validate(a.write_manifest);print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['ok'] else 1)
