#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python app/consolidated_workbench.py "$@"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 app/consolidated_workbench.py "$@"
fi
printf '%s\n' 'Python absent. Aucun logiciel téléchargé. Ouvrez APERCU_STUDIO_M03.html.'
exit 1
