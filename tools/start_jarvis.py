#!/usr/bin/env python3
"""Index selected project context, then start the existing local Jarvis service."""
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    state=Path(os.environ.get('BOJART_MEMORY_STATE',str(Path.home()/'BOJART/memory'))).expanduser().resolve()
    env=dict(os.environ,BOJART_MEMORY_STATE=str(state))
    subprocess.run([sys.executable,'-m','bojart_memory.agent_cli','--state',str(state),'index'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
    os.chdir(ROOT/'jarvis')
    os.execve(sys.executable,[sys.executable,str(ROOT/'jarvis/apps/jarvis/app/consolidated_workbench.py'),*sys.argv[1:]],env)

if __name__=='__main__':main()
