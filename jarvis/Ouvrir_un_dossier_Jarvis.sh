#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$0")/Lancer_Jarvis.sh" --choose-state "$@"
