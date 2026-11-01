#!/usr/bin/env python3
"""Read-only readiness; no credentials, installation or network calls."""
import importlib.metadata
import json
import platform
import shutil
import sqlite3
import sys

def main():
    packages={}
    for name in ['cadquery','trimesh','langgraph','langgraph-checkpoint-sqlite','faster-whisper','ctranslate2']:
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    with sqlite3.connect(':memory:') as db:
        try:db.execute('CREATE VIRTUAL TABLE t USING fts5(text)');fts=True
        except sqlite3.OperationalError:fts=False
    data={'python':platform.python_version(),'platform':platform.system(),'sqlite':sqlite3.sqlite_version,'fts5':fts,'packages':packages,'ffmpeg':bool(shutil.which('ffmpeg')),'ffprobe':bool(shutil.which('ffprobe')),'memory_ready':sys.version_info>=(3,11) and fts,'physical_hardware_qualified':False,'models_installed_by_this_command':False}
    print(json.dumps(data,indent=2))
    return 0 if data['memory_ready'] else 1

if __name__=='__main__':raise SystemExit(main())
