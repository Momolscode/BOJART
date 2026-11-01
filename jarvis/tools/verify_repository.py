#!/usr/bin/env python3
"""Monorepo wrapper; the original M07 manifest stays in its source archive."""
import runpy
from pathlib import Path
if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/validate_repository.py'),run_name='__main__')
