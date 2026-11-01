#!/usr/bin/env python3
"""Rebuild and verify the original BOJART ZIP using Python's standard library."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


def restore(root, destination, verify_only=False):
    root = Path(root).resolve()
    manifest = json.loads((root / "MANIFESTE.json").read_text(encoding="utf-8"))
    output = Path(destination).resolve()
    if not verify_only and output.exists():
        raise FileExistsError(f"Destination déjà présente : {output}")
    full_hash = hashlib.sha256()
    total = 0
    temporary = None
    stream = None
    try:
        if not verify_only:
            output.parent.mkdir(parents=True, exist_ok=True)
            stream = tempfile.NamedTemporaryFile(dir=output.parent, prefix=".bojart-", delete=False)
            temporary = Path(stream.name)
        for part in manifest["parts"]:
            source = (root / part["path"]).resolve()
            if not source.is_relative_to(root) or source.is_symlink():
                raise ValueError("Chemin de bloc non autorisé")
            part_hash = hashlib.sha256()
            size = 0
            with source.open("rb") as incoming:
                while block := incoming.read(1024 * 1024):
                    part_hash.update(block)
                    full_hash.update(block)
                    size += len(block)
                    if stream is not None:
                        stream.write(block)
            if size != part["bytes"] or part_hash.hexdigest() != part["sha256"]:
                raise ValueError(f"Bloc manquant ou altéré : {part['path']}")
            total += size
        if total != manifest["archive"]["bytes"] or full_hash.hexdigest() != manifest["archive"]["sha256"]:
            raise ValueError("L'archive reconstruite diffère de l'original")
        if stream is not None:
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            stream = None
            # Exclusive destination creation: never overwrite an existing archive.
            created = False
            try:
                with output.open("xb") as target, temporary.open("rb") as incoming:
                    created = True
                    while block := incoming.read(1024 * 1024):
                        target.write(block)
            except Exception:
                if created:
                    output.unlink(missing_ok=True)
                raise
        return {"ok": True, "parts": len(manifest["parts"]), "bytes": total,
                "sha256": full_hash.hexdigest(), "mode": "verify" if verify_only else "restore"}
    finally:
        if stream is not None:
            stream.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Vérifier les blocs sans écrire le ZIP")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    metadata = json.loads((here / "MANIFESTE.json").read_text(encoding="utf-8"))
    destination = args.output or here / metadata["archive"]["filename"]
    print(json.dumps(restore(here, destination, args.verify), ensure_ascii=False, indent=2))
