#!/usr/bin/env python3
"""Reconstruct checksum-verified BOJART binary assets from this Git repository.

Usage:
    python tools/restore_archive_2026_11_01.py --destination ./restored-bojart
No network access, no overwrites. Each payload is SHA-256 verified.
All inputs, output paths and combined hashes are checked before creating the
destination. A disk failure or concurrent source mutation during copying can
still leave an incomplete destination; only the final receipt means success.
"""
from pathlib import Path
import hashlib, json, argparse, shutil, sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "archive/2026-11-01/MANIFEST.json"

def checksum(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_inside(root, relative):
    # Compare canonical paths: a Windows short name (RUNNER~1) or a junction must not look like an escape.
    root = root.resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Unsafe archive path")
    return target

def verify_inputs(manifest, destination):
    """Reject corrupt/inconsistent input without creating partial output."""
    outputs = []
    for entry in manifest["direct_files"]:
        outputs.append(ensure_inside(destination, Path(entry["source_path"]).name))
    for entry in manifest["split_files"]:
        outputs.append(ensure_inside(destination, entry["path"]))
    for i, output in enumerate(outputs):
        if output == destination or any(
            output.is_relative_to(previous) or previous.is_relative_to(output)
            for previous in outputs[:i]
        ):
            raise ValueError("Conflicting archive output paths")
    for entry in manifest["direct_files"]:
        source = ensure_inside(ROOT, entry["source_path"])
        if source.stat().st_size != entry["bytes"] or checksum(source) != entry["sha256"]:
            raise ValueError(f"Corrupt source {source}")
    for entry in manifest["split_files"]:
        combined = hashlib.sha256()
        total = 0
        for part in entry["parts"]:
            source = ensure_inside(ROOT, part["path"])
            digest = hashlib.sha256()
            size = 0
            with source.open("rb") as reader:
                for data in iter(lambda: reader.read(1024 * 1024), b""):
                    size += len(data)
                    digest.update(data)
                    combined.update(data)
            if size != part["bytes"] or digest.hexdigest() != part["sha256"]:
                raise ValueError(f"Corrupt chunk {source}")
            total += size
        if total != entry["bytes"] or combined.hexdigest() != entry["sha256"]:
            raise ValueError("Invalid combined payload " + entry["path"])

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--destination",required=True,type=Path)
    args=parser.parse_args()
    destination=args.destination.resolve()
    if destination.exists(): raise FileExistsError("Use a new empty destination")
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    verify_inputs(manifest, destination)
    destination.mkdir(parents=True)
    done=[]
    for entry in manifest["direct_files"]:
        p=ensure_inside(ROOT,entry["source_path"])
        if p.stat().st_size != entry["bytes"] or checksum(p)!=entry["sha256"]:
            raise ValueError(f"Corrupt source {p}")
        out=ensure_inside(destination,p.name)
        shutil.copyfile(p,out)
        if out.stat().st_size != entry["bytes"] or checksum(out) != entry["sha256"]:
            raise ValueError(f"Invalid copied file {out}")
        done.append(out)
    for entry in manifest["split_files"]:
        out=ensure_inside(destination,entry["path"])
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open("xb") as writer:
            for part in entry["parts"]:
                chunk=ensure_inside(ROOT,part["path"])
                if chunk.stat().st_size!=part["bytes"] or checksum(chunk)!=part["sha256"]:
                    raise ValueError(f"Corrupt chunk {chunk}")
                with chunk.open("rb") as reader:
                    shutil.copyfileobj(reader,writer)
        if out.stat().st_size!=entry["bytes"] or checksum(out)!=entry["sha256"]:
            raise ValueError(f"Invalid reconstructed file {out}")
        done.append(out)
    print(json.dumps({"result":"verified","files":[str(x) for x in done]},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":sys.exit(main())
