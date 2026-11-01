#!/usr/bin/env python3
"""Publish a verified BOJART delivery via an already authenticated GitHub CLI.
Default is a plan only. --execute allows writes to a PRIVATE repository explicitly named.
Never force-push, delete, overwrite assets, or open a public repository.
"""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, tempfile
from pathlib import Path

ALLOWED_OWNERS={'momolscode','eaglemic'}

def run(args,cwd=None):
 p=subprocess.run(args,cwd=cwd,text=True,capture_output=True,timeout=600)
 if p.returncode:raise RuntimeError('Command failed: '+args[0]+' '+args[1]+'\n'+p.stderr[-1500:])
 return p.stdout.strip()

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def validate_repo(value):
 if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]{0,99}',value):raise ValueError('owner/repository required')
 if value.split('/')[0].lower() not in ALLOWED_OWNERS:raise ValueError('Choose the explicitly approved owner (Momolscode or eaglemic)')
 return value

def require_private(meta,repo):
 if meta.get('full_name','').lower()!=repo.lower() or meta.get('private') is not True:raise ValueError('Private destination required; visibility will NOT be changed')

def validate_delivery(folder):
 doc=json.loads((folder/'DELIVERY_MANIFEST.json').read_text())
 if doc.get('schema')!='bojart.delivery.v1':raise ValueError('Unexpected manifest')
 if not isinstance(doc.get('files'),list) or not 1<=len(doc['files'])<=30:raise ValueError('Invalid delivery files')
 if not re.fullmatch(r'[0-9a-f]{40}',str(doc.get('commit',''))):raise ValueError('Exact commit required')
 for key in ['branch','tag']:
  value=doc.get(key,'')
  if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,119}',value) or '..' in value or '//' in value or value.endswith(('/', '.', '.lock')):raise ValueError('Unsafe Git reference')
 seen=set()
 for item in doc['files']:
  name=item['name']
  if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,149}',name) or name in seen:raise ValueError('Unsafe or duplicate file')
  if type(item.get('bytes')) is not int or item['bytes']<0 or not re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))):raise ValueError('Invalid file metadata')
  seen.add(name);p=folder/name
  if not p.is_file() or p.is_symlink() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise ValueError('Delivery integrity failure: '+name)
 if doc.get('bundle') not in seen or not doc['bundle'].endswith('.bundle'):raise ValueError('Bundle must be a verified delivery asset')
 return doc

def publish(repo,delivery,execute=False,allow_create=False):
 repo=validate_repo(repo);doc=validate_delivery(delivery)
 manifest_path=delivery/'DELIVERY_MANIFEST.json'
 assets=[*doc['files'],{'name':'DELIVERY_MANIFEST.json','bytes':manifest_path.stat().st_size,'sha256':sha(manifest_path)}]
 plan={'destination':repo,'visibility':'private_required','branch':doc['branch'],'tag':doc['tag'],
       'commit':doc['commit'],'assets':[x['name'] for x in assets],
       'overwrite':False,'delete':False,'status':'plan_only'}
 if not execute:return plan
 for tool in ['git','gh']:
  if not shutil.which(tool):raise RuntimeError(tool+' is required; no automatic installation will be performed')
 run(['gh','auth','status'])
 login=run(['gh','api','user','--jq','.login'])
 if login.lower()!=repo.split('/')[0].lower():raise ValueError('Authenticated account differs from chosen repository owner; select the correct account in gh')
 metadata=subprocess.run(['gh','api','repos/'+repo],text=True,capture_output=True,timeout=30)
 if metadata.returncode:
  if '404' not in metadata.stderr or not allow_create:raise RuntimeError('Destination not readable. --create-private is required for an explicitly new repository')
  run(['gh','repo','create',repo,'--private'])
  meta=json.loads(run(['gh','api','repos/'+repo]))
 else:meta=json.loads(metadata.stdout)
 require_private(meta,repo)
 if meta.get('permissions',{}).get('push') is not True:raise ValueError('Push permission not confirmed')
 url='https://github.com/'+repo+'.git'
 # gh handles credentials; none are requested, printed, stored in URLs, or placed in Git.
 git=['git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential']
 with tempfile.TemporaryDirectory(prefix='bojart-publish-') as temp:
  work=Path(temp)/'repo';run(['git','clone',str(delivery/doc['bundle']),str(work)])
  if run(['git','rev-parse','HEAD'],work)!=doc['commit']:raise ValueError('Bundle commit mismatch')
  run(git+['push',url,'HEAD:refs/heads/'+doc['branch'],'refs/tags/'+doc['tag']],work)
  refs=run(git+['ls-remote',url,'refs/heads/'+doc['branch']],work)
  if not refs.startswith(doc['commit']+'\t'):raise ValueError('Remote branch did not verify')
  existing=subprocess.run(['gh','release','view',doc['tag'],'--repo',repo,'--json','tagName,isDraft,assets'],capture_output=True,text=True,timeout=30)
  if existing.returncode:
   if not any(word in existing.stderr.lower() for word in ['not found','404']):raise RuntimeError('Cannot inspect release; no write attempted')
   run(['gh','release','create',doc['tag'],'--repo',repo,'--draft','--verify-tag','--title','BOJ.ART — récupération vérifiée','--notes','Sources consolidées et coffre des fichiers récupérés. Lire COVERAGE.md : la récupération ne comprend pas les données des sites ou du PC cible.'])
   release={'assets':[],'isDraft':True}
  else:release=json.loads(existing.stdout)
  already={a['name'] for a in release.get('assets',[])}
  for item in assets:
   if item['name'] not in already:run(['gh','release','upload',doc['tag'],str(delivery/item['name']),'--repo',repo])
  check=Path(temp)/'downloaded';check.mkdir()
  for item in assets:
   run(['gh','release','download',doc['tag'],'--repo',repo,'--pattern',item['name'],'--dir',str(check)])
   if sha(check/item['name'])!=item['sha256']:raise ValueError('Remote asset failed byte verification; retained without overwriting')
  if release.get('isDraft'):run(['gh','release','edit',doc['tag'],'--repo',repo,'--draft=false'])
  # Read back repository privacy, do not silently accept an exposure change.
  require_private(json.loads(run(['gh','api','repos/'+repo])),repo)
 result={**plan,'status':'pushed_and_redownload_verified','url':'https://github.com/'+repo+'/tree/'+doc['branch']}
 (delivery/'delivery_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 return result

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',required=True);ap.add_argument('--delivery',type=Path,required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--create-private',action='store_true');a=ap.parse_args()
 try:print(json.dumps(publish(a.repo,a.delivery.resolve(),a.execute,a.create_private),ensure_ascii=False,indent=2))
 except Exception as exc:raise SystemExit(str(exc))
