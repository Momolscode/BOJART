#!/usr/bin/env python3
"""Vérifier et restaurer exactement les fichiers de la partie 2, sans réseau."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def safe_path(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or not relative.parts or any(p in {"..", ".git"} for p in relative.parts):
        raise ValueError(f"Chemin non autorisé : {name}")
    path = root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Chemin hors destination : {name}")
    return path


def chunks(entry):
    for name in entry["repository_paths"]:
        path = safe_path(ROOT, name)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Fichier absent ou lien symbolique : {name}")
        with path.open("rb") as source:
            while data := source.read(1024 * 1024):
                yield data


def digest(entry, output=None):
    checksum = hashlib.sha256()
    size = 0
    for data in chunks(entry):
        checksum.update(data)
        size += len(data)
        if output is not None:
            output.write(data)
    if size != entry["size"] or checksum.hexdigest() != entry["sha256"]:
        raise ValueError(f"Empreinte incorrecte : {entry['archive_path']}")
    return size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--verify-only", action="store_true")
    actions.add_argument("--destination", type=Path)
    args = parser.parse_args()
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest["entries"]
    if len(entries) != manifest["file_count"]:
        raise ValueError("Nombre de fichiers incohérent")
    names = [entry["archive_path"] for entry in entries]
    if len(set(names)) != len(names):
        raise ValueError("Chemin de restauration en double")
    if args.destination is not None and args.destination.exists():
        raise ValueError("La destination doit être un nouveau dossier")
    total = 0
    for entry in entries:
        safe_path(args.destination or ROOT, entry["archive_path"])
        total += digest(entry)
    if total != manifest["uncompressed_bytes"]:
        raise ValueError("Taille totale incohérente")
    if args.destination is not None:
        args.destination.mkdir(parents=True, exist_ok=False)
        for entry in entries:
            target = safe_path(args.destination, entry["archive_path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                digest(entry, output)
    print(json.dumps({"ok": True, "files": len(entries), "bytes": total,
                      "restored": args.destination is not None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
