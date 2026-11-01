#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
BOJART_PYTHON=python3
if [ -x .venv/bin/python ]; then BOJART_PYTHON=.venv/bin/python; fi
exec "$BOJART_PYTHON" tools/start_jarvis.py "$@"
