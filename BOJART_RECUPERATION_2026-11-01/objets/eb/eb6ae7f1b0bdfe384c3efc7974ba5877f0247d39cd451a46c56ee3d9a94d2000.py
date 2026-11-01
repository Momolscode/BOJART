#!/usr/bin/env python3
"""Observe namespace/process prerequisites without changing or bypassing them."""
import json, os, platform, subprocess
from pathlib import Path
r={'platform':platform.system(),'pid_api':os.getpid()}
if platform.system()=='Linux':
    try:
        r['pid_proc_self']=int(Path('/proc/self/stat').read_text().split(' ',1)[0])
        r['pid_namespaces_consistent']=r['pid_api']==r['pid_proc_self']
    except (OSError,ValueError) as e: r['proc_error']=str(e)
    p=subprocess.run(['ps','-axo','pid=,ppid=,pgid=,uid=,stat=,command='],capture_output=True,text=True)
    r['ps_exit_code']=p.returncode; r['ps_stderr']=p.stderr.strip()
    r['ps_lists_api_pid']=any(line.split() and line.split()[0]==str(os.getpid()) for line in p.stdout.splitlines())
    r['static_js_preflight']='unverified' if r.get('pid_namespaces_consistent') and p.returncode==0 else 'blocked_inconsistent_process_namespace'
print(json.dumps(r,ensure_ascii=False,indent=2))
