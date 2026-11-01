#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3 absent. Aperçu autonome : APERCU_MISSION_01.html'; exit 1
fi
if ! python3 -c 'import cadquery,trimesh' >/dev/null 2>&1; then
  echo 'Dépendances absentes. Aucun téléchargement déclenché ; consulter README.md.'; exit 1
fi
exec python3 app/server.py
