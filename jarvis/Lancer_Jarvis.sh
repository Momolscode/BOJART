#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -f ../tools/start_jarvis.py ] && [ -f ../Lancer_BOJART.sh ]; then
  exec bash ../Lancer_BOJART.sh "$@"
fi
PY=python3
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; fi
exec "$PY" apps/jarvis/app/consolidated_workbench.py "$@"
