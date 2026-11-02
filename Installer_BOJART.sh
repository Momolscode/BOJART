#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
BOJART_PYTHON=python3
if command -v python3.12 >/dev/null 2>&1; then BOJART_PYTHON=python3.12; fi
exec "$BOJART_PYTHON" tools/prepare_installation.py "$@"
