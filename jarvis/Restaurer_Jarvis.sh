#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY=python3
if [ -f ../tools/start_jarvis.py ] && [ -x ../.venv/bin/python ]; then
  PY=../.venv/bin/python
elif [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
fi
if [ "$#" -eq 0 ]; then exec "$PY" tools/restore_workspace.py --choose; fi
exec "$PY" tools/restore_workspace.py "$@"
