#!/usr/bin/env python3
"""Vérifier et restaurer sans perte la partie 3 BOJ.ART avec Python standard."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
RECOVERY_MANIFEST="MANIFESTE_PARTIE_3.json"

RECOVERY_PREFIX='BOJART_RECUPERATION_2026-11-01'


RECOVERY_SOURCE='BOJART_RECUPERATION_2026-11-01_PARTIE_3_SUR_3.zip'


RECOVERY_SOURCE_SHA256='6a23245cda664686f0d8dac40d49107032bd5f94a09a686edaa833ed39300b06'


RECOVERY_OBJECTS_SHA256='b46622800604e0f2518da7f125711eed21cdb01e4e5a4347fb20a79be59b6fe6'


RECOVERY_OBJECT_RE=re.compile(r'BOJART_RECUPERATION_2026-11-01/objets/([0-9a-f]{2})/([0-9a-f]{64})\.[a-z0-9]+')


RECOVERY_FIELDS=('archive_path','repo_path','bytes','sha256','git_blob_sha1','storage')


RECOVERY_PART_FIELDS=('repo_path','bytes','sha256','git_blob_sha1')


SECRET=[re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(r'github_pat_[A-Za-z0-9_]{40,}'),re.compile(r'sk-proj-[A-Za-z0-9_-]{30,}'),re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(r'https?://[^\s"<>]+[?&](?:X-Amz-Signature|sig)=[A-Za-z0-9%]{20,}')]


def recovery_fingerprint_valid(entry):
    return bool(isinstance(entry,dict) and type(entry.get('bytes')) is int and entry['bytes']>=0
                and isinstance(entry.get('sha256'),str) and re.fullmatch(r'[0-9a-f]{64}',entry['sha256'])
                and isinstance(entry.get('git_blob_sha1'),str)
                and re.fullmatch(r'[0-9a-f]{40}',entry['git_blob_sha1']))


def recovery_entry_valid(entry):
    if not recovery_fingerprint_valid(entry):return False
    path=entry.get('repo_path');match=RECOVERY_OBJECT_RE.fullmatch(path) if isinstance(path,str) else None
    if not (match and entry.get('archive_path')==path and match[1]==match[2][:2]
            and entry['sha256']==match[2]):return False
    if entry.get('storage')=='file':return 'parts' not in entry
    parts=entry.get('parts')
    if entry.get('storage')!='chunks' or not isinstance(parts,list) or len(parts)<2:return False
    for i,part in enumerate(parts,1):
        if (not recovery_fingerprint_valid(part) or not 0<part['bytes']<=8388608
            or part.get('repo_path')!=f"{path}.parts/{i:04d}-{part['sha256']}.chunk"):
            return False
    return sum(part['bytes'] for part in parts)==entry['bytes']


def recovery_physical_entries(entries):
    physical={}
    for entry in entries.values():
        if entry['storage']=='file':physical[entry['repo_path']]=entry
        else:
            for i,part in enumerate(entry['parts'],1):
                physical[part['repo_path']]={**part,'logical_path':entry['repo_path'],'part_index':i}
    return physical


def load_recovery_manifest(root=ROOT):
    path=root/RECOVERY_MANIFEST
    if not path.exists():return {},[]
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        return {},[{'path':RECOVERY_MANIFEST,'error':'unsafe_recovery_manifest'}]
    try:
        manifest=json.loads(path.read_text(encoding='utf-8'))
        source=manifest['source'];objects=manifest['objects']
        if (manifest.get('schema_version')!=1 or source.get('filename')!=RECOVERY_SOURCE
            or source.get('sha256')!=RECOVERY_SOURCE_SHA256 or source.get('bytes')!=340986970
            or source.get('part')!=3 or source.get('parts')!=3
            or manifest.get('object_count')!=1114 or not isinstance(objects,list)
            or len(objects)!=1114 or not all(recovery_entry_valid(x) for x in objects)):
            raise ValueError('invalid_recovery_manifest')
        entries={entry['repo_path']:entry for entry in objects}
        if len(entries)!=len(objects):raise ValueError('duplicate_recovery_path')
        canonical=[]
        for entry in sorted(objects,key=lambda entry:entry['repo_path']):
            identity={key:entry[key] for key in RECOVERY_FIELDS}
            if entry['storage']=='chunks':
                identity['parts']=[{key:part[key] for key in RECOVERY_PART_FIELDS} for part in entry['parts']]
            canonical.append(identity)
        digest=hashlib.sha256(json.dumps(canonical,ensure_ascii=False,sort_keys=True,
                                      separators=(',',':')).encode('utf-8')).hexdigest()
        if digest!=RECOVERY_OBJECTS_SHA256 or manifest.get('canonical_objects_sha256')!=digest:
            raise ValueError('recovery_allowlist_mismatch')
        if sum(entry['bytes'] for entry in objects)!=363198134 or manifest.get('uncompressed_bytes')!=363198134:
            raise ValueError('recovery_total_mismatch')
        if (len(recovery_physical_entries(entries))!=1131 or manifest.get('physical_file_count')!=1131
            or sum(entry['storage']=='chunks' for entry in objects)!=6 or manifest.get('chunked_objects')!=6
            or sum(len(entry.get('parts',[])) for entry in objects)!=23 or manifest.get('chunk_files')!=23):
            raise ValueError('recovery_storage_mismatch')
        return entries,[]
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return {},[{'path':RECOVERY_MANIFEST,'error':'invalid_recovery_manifest'}]


def read_recovery_file(root,name,entry):
    """Read exact physical bytes; callers validate their allowlisted path first."""
    root=root.resolve();path=root/name
    if (not path.resolve().is_relative_to(root) or not path.is_file()
        or any(p.is_symlink() for p in [path,*path.parents] if p!=root and root in p.parents)):
        raise ValueError('missing_or_unsafe_recovery_object')
    try:payload=path.read_bytes()
    except OSError as exc:raise ValueError('unreadable_recovery_object') from exc
    sha256=hashlib.sha256(payload).hexdigest()
    git_sha=hashlib.sha1(f'blob {len(payload)}\0'.encode()+payload).hexdigest()
    if len(payload)!=entry['bytes'] or sha256!=entry['sha256'] or git_sha!=entry['git_blob_sha1']:
        raise ValueError('recovery_object_mismatch')
    return payload


def recovery_secret_present(payload):
    # Latin-1 preserves every byte and ASCII credential signature, even in a binary.
    text=payload.decode('latin-1')
    return any(pattern.search(text) for pattern in SECRET)


def read_recovery_payload(root,entry):
    """Reconstruct and verify one logical original, including across chunk boundaries."""
    if not recovery_entry_valid(entry):raise ValueError('invalid_recovery_entry')
    if entry['storage']=='file':payload=read_recovery_file(root,entry['repo_path'],entry)
    else:
        payload=b''.join(read_recovery_file(root,part['repo_path'],part) for part in entry['parts'])
        if (len(payload)!=entry['bytes'] or hashlib.sha256(payload).hexdigest()!=entry['sha256']
            or hashlib.sha1(f'blob {len(payload)}\0'.encode()+payload).hexdigest()!=entry['git_blob_sha1']):
            raise ValueError('recovery_original_mismatch')
    if recovery_secret_present(payload):raise ValueError('possible_secret')
    return payload


def check_recovery_object(root,name,entries):
    """Check an allowlisted physical file or fragment without executing it."""
    entry=entries.get(name)
    valid=False
    if isinstance(entry,dict) and entry.get('repo_path')==name:
        if entry.get('storage')=='file':valid=recovery_entry_valid(entry)
        elif isinstance(entry.get('logical_path'),str) and type(entry.get('part_index')) is int:
            match=RECOVERY_OBJECT_RE.fullmatch(entry['logical_path'])
            valid=bool(match and match[1]==match[2][:2] and entry['part_index']>0
                       and recovery_fingerprint_valid(entry) and 0<entry['bytes']<=8388608
                       and name==f"{entry['logical_path']}.parts/{entry['part_index']:04d}-{entry['sha256']}.chunk")
    if not valid:return None,[{'path':name,'error':'unlisted_recovery_object'}]
    try:
        payload=read_recovery_file(root,name,entry)
        issues=[{'path':name,'error':'possible_secret'}] if recovery_secret_present(payload) else []
        return {'path':name,'bytes':len(payload),'sha256':entry['sha256']},issues
    except ValueError as exc:return None,[{'path':name,'error':str(exc)}]


def restore_recovery(root,destination,entries=None):
    root=Path(root).resolve();destination=Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('destination_already_exists')
    if destination.resolve().is_relative_to(root):
        raise ValueError('destination_must_be_outside_source_repository')
    if entries is None:
        entries,issues=load_recovery_manifest(ROOT)
        if issues or not entries:raise ValueError('invalid_or_missing_recovery_manifest')
    # A corrupt or missing source fails before any destination is created.
    for name,entry in sorted(entries.items()):
        if name!=entry.get('repo_path'):raise ValueError('invalid_recovery_entry')
        try:read_recovery_payload(root,entry)
        except ValueError as exc:raise ValueError(f'{name}: {exc}') from exc
    destination.mkdir(parents=True,exist_ok=False)
    restored=0;total=0
    for name,entry in sorted(entries.items()):
        # Recheck immediately before writing; no existing file can be overwritten.
        payload=read_recovery_payload(root,entry)
        target=destination/entry['archive_path']
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as output:output.write(payload)
        restored+=1;total+=len(payload)
    return {'ok':True,'destination':str(destination),'restored_objects':restored,
            'restored_bytes':total,'direct_objects':sum(e['storage']=='file' for e in entries.values()),
            'reconstructed_objects':sum(e['storage']=='chunks' for e in entries.values()),
            'source_fragments':sum(len(e.get('parts',[])) for e in entries.values())}


def verify_recovery(source):
    entries,issues=load_recovery_manifest(ROOT)
    if issues or not entries:raise ValueError('invalid_or_missing_recovery_manifest')
    total=0
    for name,entry in sorted(entries.items()):
        try:total+=len(read_recovery_payload(source,entry))
        except ValueError as exc:raise ValueError(f'{name}: {exc}') from exc
    return {'ok':True,'source':str(source),'verified_objects':len(entries),
            'verified_bytes':total,'direct_objects':sum(e['storage']=='file' for e in entries.values()),
            'reconstructed_objects':sum(e['storage']=='chunks' for e in entries.values()),
            'source_fragments':sum(len(e.get('parts',[])) for e in entries.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT,
                        help='Folder containing BOJART_RECUPERATION_2026-11-01 (default: this script folder).')
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--verify-only',action='store_true',help='Verify all originals without writing files.')
    action.add_argument('--destination',type=Path,help='New output directory; must not already exist.')
    args=parser.parse_args()
    try:
        source=args.source.resolve()
        result=verify_recovery(source) if args.verify_only else restore_recovery(source,args.destination)
    except (OSError,ValueError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));return 1
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':
    sys.exit(main())

