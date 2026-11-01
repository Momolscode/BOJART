#!/usr/bin/env python3
"""Check the private source files required to reproduce the public edit recipe."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
manifest = json.loads((root / "ASSETS.json").read_text())
failures = []
for item in manifest["assets"]:
    path = root / item["path"]
    if not path.is_file():
        failures.append({"path": item["path"], "status": "missing"})
    elif path.stat().st_size != item["bytes"]:
        failures.append({"path": item["path"], "status": "size_mismatch"})
    else:
        with path.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != item["sha256"]:
            failures.append({"path": item["path"], "status": "sha256_mismatch"})
print(json.dumps({"checked": len(manifest["assets"]), "ok": not failures, "failures": failures}, ensure_ascii=False, indent=2))
raise SystemExit(1 if failures else 0)
