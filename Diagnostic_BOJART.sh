#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
BOJART_PYTHON=python3
if command -v python3.12 >/dev/null 2>&1; then BOJART_PYTHON=python3.12; fi
if [ -x .venv/bin/python ]; then BOJART_PYTHON=.venv/bin/python; fi
exec "$BOJART_PYTHON" tools/diagnose_environment.py --save --summary "$@"
