#!/usr/bin/env python3
"""Verify and restore the BOJART content-addressed vault. No network and no overwrites."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, stat, tempfile, zipfile
from pathlib import Path, PurePosixPath

MAX_TOTAL=4*1024**3

def digest_file(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()

def safe_path(name):
 if not isinstance(name,str) or not name or '\\' in name or '\x00' in name:raise ValueError('Unsafe path')
 p=PurePosixPath(name)
 if p.is_absolute() or any(x in ('..','.') for x in name.split('/')) or any(':' in x for x in p.parts):raise ValueError('Unsafe path')
 return p

def load_inventory(z):
 info=z.getinfo('inventory.json')
 if info.file_size>16_000_000:raise ValueError('Inventory too large')
 d=json.loads(z.read(info)); rows=d.get('files')
 if d.get('schema')!=1 or not isinstance(rows,list) or len(rows)>100000:raise ValueError('Bad inventory')
 seen=set();total=0;objects={}
 for r in rows:
  name=str(safe_path(r['original_path']))
  if name in seen:raise ValueError('Duplicate path')
  seen.add(name)
  if not re.fullmatch('[0-9a-f]{64}',r['sha256']):raise ValueError('Bad digest')
  if r['object']!='objects/'+r['sha256']:raise ValueError('Bad object path')
  if type(r['bytes'])is not int or r['bytes']<0:raise ValueError('Bad size')
  total+=r['bytes']
  if r['sha256'] in objects and objects[r['sha256']]!=r['bytes']:raise ValueError('Contradictory metadata')
  objects[r['sha256']]=r['bytes']
 if total>MAX_TOTAL:raise ValueError('Vault exceeds size policy')
 allowed={'inventory.json'}|{'objects/'+k for k in objects}
 names=z.namelist()
 if len(names)!=len(set(names)) or set(names)!=allowed:raise ValueError('Unexpected or duplicate ZIP entries')
 for i in z.infolist():
  safe_path(i.filename)
  if stat.S_ISLNK(i.external_attr>>16) or i.is_dir():raise ValueError('Links/directories forbidden')
 return d,objects

def verify_vault(archive):
 with zipfile.ZipFile(archive) as z:
  d,objects=load_inventory(z)
  for sha,size in objects.items():
   inf=z.getinfo('objects/'+sha)
   if inf.file_size!=size:raise ValueError('Size mismatch: '+sha)
   h=hashlib.sha256();n=0
   with z.open(inf) as f:
    for chunk in iter(lambda:f.read(1048576),b''):
     h.update(chunk);n+=len(chunk)
   if n!=size or h.hexdigest()!=sha:raise ValueError('Corrupt object: '+sha)
 return {'verified':True,'paths':len(d['files']),'objects':len(objects),'bytes_with_aliases':sum(r['bytes'] for r in d['files']),'sha256':digest_file(archive)}

def restore_vault(archive,destination):
 dest=Path(destination).resolve()
 if dest.exists():raise FileExistsError('Refusing to overwrite any destination')
 report=verify_vault(archive)
 dest.parent.mkdir(parents=True,exist_ok=True)
 tmp=Path(tempfile.mkdtemp(prefix='.bojart-restore-',dir=dest.parent))
 try:
  with zipfile.ZipFile(archive) as z:
   d,_=load_inventory(z)
   for r in d['files']:
    p=tmp.joinpath(*safe_path(r['original_path']).parts);p.parent.mkdir(parents=True,exist_ok=True)
    with z.open(r['object']) as src,p.open('xb') as out:shutil.copyfileobj(src,out,1048576)
    if digest_file(p)!=r['sha256']:raise ValueError('Restoration mismatch')
  if dest.exists():raise FileExistsError('Destination appeared during restore')
  os.rename(tmp,dest)
 except Exception:
  shutil.rmtree(tmp,ignore_errors=True);raise
 return {**report,'restored_to':str(dest)}

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('archive',type=Path);ap.add_argument('--restore',type=Path)
 a=ap.parse_args(); print(json.dumps(restore_vault(a.archive,a.restore) if a.restore else verify_vault(a.archive),ensure_ascii=False,indent=2))
