#!/usr/bin/env python3
"""Verify a local extracted BOJART archive without network or remote modifications."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    source = ROOT / "MANIFEST_SHA256.json"
    if not source.is_file():
        print("MANIFEST_SHA256.json is absent (private archive not imported).")
        return 2
    manifest = json.loads(source.read_text(encoding="utf-8"))
    failures, expected = [], set()
    for entry in manifest["files"]:
        relative = entry["path"]
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT):
            failures.append("Unsafe path: " + relative)
            continue
        expected.add(relative)
        if not path.is_file():
            failures.append("Missing: " + relative)
        elif path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            failures.append("Modified: " + relative)
    actual = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*") if p.is_file()
        and ".git" not in p.relative_to(ROOT).parts
        and "__pycache__" not in p.relative_to(ROOT).parts
        and p.name != "MANIFEST_SHA256.json"
    }
    extras = sorted(actual - expected)
    for entry in failures:
        print(entry)
    for path in extras:
        print("Extra (not covered by manifest): " + path)
    print(f"Checked: {len(expected)}; errors: {len(failures)}; extras: {len(extras)}")
    return 1 if failures or extras else 0


if __name__ == "__main__":
    sys.exit(main())
