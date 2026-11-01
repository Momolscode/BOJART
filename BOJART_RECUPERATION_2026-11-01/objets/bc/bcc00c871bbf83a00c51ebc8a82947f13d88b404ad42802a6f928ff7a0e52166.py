#!/usr/bin/env python3
"""Install pinned REA locally; optionally register Codex with backups."""
import argparse, json, subprocess, shutil
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument('--prefix',required=True,type=Path)
ap.add_argument('--register-codex',action='store_true')
ap.add_argument('--dry-run',action='store_true')
a=ap.parse_args(); prefix=a.prefix.resolve()
here=Path(__file__).resolve().parent
lock=json.loads((here/'package-lock.json').read_text())
if lock['packages']['node_modules/rea-agents']['version']!='6.8.0':
    raise SystemExit('Unexpected locked REA version')
node=subprocess.check_output(['node','--version'],text=True).strip()
v=tuple(int(n) for n in node.lstrip('v').split('-')[0].split('.'))
if not ((v[0]==22 and v>=(22,23,4)) or (v[0]==24 and v>=(24,22,1)) or v>=(26,12,1)):
    raise SystemExit('This package requires Node ^22.23.4, ^24.22.1 or >=26.12.1')
if prefix.exists() and any(prefix.iterdir()):
    raise SystemExit('Use an empty destination; existing installation left unchanged')
if a.dry_run:
    print(json.dumps({'destination':str(prefix),'node':node,'version':'6.8.0','operation':'npm ci from bundled lockfile','register_codex':a.register_codex}))
    raise SystemExit(0)
prefix.mkdir(parents=True,exist_ok=True)
for name in ['package.json','package-lock.json']:
    shutil.copyfile(here/name,prefix/name)
subprocess.run(['npm','ci','--prefix',str(prefix),'--no-audit','--no-fund'],check=True)
rea=prefix/('node_modules/.bin/rea.cmd' if __import__('os').name=='nt' else 'node_modules/.bin/rea')
subprocess.run([str(rea),'--version'],check=True)
if a.register_codex:
    subprocess.run([str(rea),'setup','--client','codex','--skill=false','--yes','--json'],check=True)
print(json.dumps({'installed_command':str(rea),'registered_codex':a.register_codex,'note':'Restart a client to load a new registration; installation is not a complete analysis test.'}))
