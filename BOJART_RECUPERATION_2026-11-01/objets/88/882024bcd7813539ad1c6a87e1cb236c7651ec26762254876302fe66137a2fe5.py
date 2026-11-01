#!/usr/bin/env python3
"""Optional isolated original-DLL oracle, pinned to the tested Linux x64 runtime."""
import argparse
import hashlib
import json
import platform
import subprocess
import tarfile
import urllib.request
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    if platform.system() != 'Linux' or platform.machine().lower() not in ['x86_64', 'amd64']:
        ap.error('This helper is pinned to Linux x64; the Python primitives do not need this runtime')
    if a.out.exists() and any(a.out.iterdir()):
        ap.error('Choose an empty directory')
    a.out.mkdir(parents=True, exist_ok=True)
    runtime = json.loads((ROOT / 'provenance/runtime_install.json').read_text())
    package = a.out / 'runtime.tar.gz'
    urllib.request.urlretrieve(runtime['download_url'], package)
    if hashlib.sha512(package.read_bytes()).hexdigest() != runtime['sha512']:
        raise ValueError('Runtime identity mismatch')
    dotnet = a.out / 'dotnet'
    dotnet.mkdir()
    with tarfile.open(package) as t:
        t.extractall(dotnet, filter='data')
    env = a.out / 'venv'
    venv.create(env, with_pip=True)
    subprocess.run([str(env / 'bin/python'), '-m', 'pip', 'install',
                    '-r', str(ROOT / 'tooling/requirements-oracle.txt')], check=True)
    config = a.out / 'oracle.runtimeconfig.json'
    config.write_text((ROOT / 'tooling/oracle.runtimeconfig.json').read_text())
    print(json.dumps({'python': str((env/'bin/python').resolve()),
                      'runtime_config': str(config.resolve()),
                      'dotnet_root': str(dotnet.resolve()),
                      'system_or_client_configuration_modified': False}, indent=2))


if __name__ == '__main__':
    main()
