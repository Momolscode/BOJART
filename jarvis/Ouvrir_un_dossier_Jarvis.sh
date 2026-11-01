#!/usr/bin/env bash
set -euo pipefail
exec bash "$(dirname "$0")/Lancer_Jarvis.sh" --choose-state "$@"
