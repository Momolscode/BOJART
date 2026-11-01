#!/usr/bin/env python3
"""Reconstruct checksum-verified BOJART binary assets from this Git repository.

Usage:
    python tools/restore_archive_2026_11_01.py --destination ./restored-bojart
No network access, no overwrites. Each payload is SHA-256 verified.
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
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Unsafe archive path")
    return target

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--destination",required=True,type=Path)
    args=parser.parse_args()
    destination=args.destination.resolve()
    if destination.exists(): raise FileExistsError("Use a new empty destination")
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    destination.mkdir(parents=True)
    done=[]
    for entry in manifest["direct_files"]:
        p=ensure_inside(ROOT,entry["source_path"])
        if p.stat().st_size != entry["bytes"] or checksum(p)!=entry["sha256"]:
            raise ValueError(f"Corrupt source {p}")
        out=ensure_inside(destination,p.name)
        shutil.copyfile(p,out)
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
