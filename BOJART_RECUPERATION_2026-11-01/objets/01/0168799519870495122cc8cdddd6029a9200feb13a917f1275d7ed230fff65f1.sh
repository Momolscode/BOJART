#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
printf '%s\n' 'BOJ.ART - Publication privee vers Momolscode/bojart-jarvis'
printf '%s\n' 'Prerequis : Python 3, Git et GitHub CLI connecte a Momolscode.'
python3 PUBLIER_GITHUB.py --delivery "$PWD" --execute --create-private
