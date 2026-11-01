#!/usr/bin/env python3
"""Generate a non-executing orchestration report from BOJART's existing audit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bojart_ops.audit import strict_json
from bojart_ops.orchestration import markdown, plan

LIMIT = 16 * 1024 * 1024


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError("Input missing, unsafe or too large.")
    raw = path.read_bytes()
    return strict_json(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "ops/orchestration.json")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / ".bojart-audit")
    args = parser.parse_args()
    audit, audit_sha = read_json(args.audit)
    config, config_sha = read_json(args.config)
    # Prevent an old report from masquerading as the checked-out revision.
    revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                       text=True).strip()
    if audit.get("revision") != revision:
        raise ValueError("Audit revision differs from checkout; regenerate the audit.")
    checkpoint, checkpoint_sha, checkpoint_error = None, None, None
    if args.checkpoint is not None:
        try:
            checkpoint, checkpoint_sha = read_json(args.checkpoint)
        except (OSError, UnicodeError, ValueError):
            checkpoint_error = "Checkpoint unavailable or invalid; current coverage is unknown."
    report = plan(audit, config, checkpoint, checkpoint_error)
    report["input_sha256"] = {"audit": audit_sha, "configuration": config_sha,
                              "checkpoint": checkpoint_sha}
    output = args.output.resolve()
    # Reports may only be written under the ignored audit folder.
    destination = (ROOT / ".bojart-audit").resolve()
    if not output.is_relative_to(destination) or (ROOT / ".bojart-audit").is_symlink():
        raise ValueError("Output must be inside .bojart-audit.")
    targets = [output / "orchestration.json", output / "orchestration.md"]
    if any(p.is_symlink() for p in targets):
        raise ValueError("Report destination is a symlink.")
    inputs = [p.resolve() for p in (args.audit, args.config, args.checkpoint) if p is not None]
    if any(p in inputs for p in targets):
        raise ValueError("Report would replace an input.")
    output.mkdir(parents=True, exist_ok=True)
    targets[0].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    targets[1].write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    print(json.dumps({"checkpoint_state": report["context_audit"]["state"],
                      "same_revision": report["context_audit"]["same_revision"],
                      "tasks_executed": 0}))
    return 0 if report["structural_audit_ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print("Orchestration refused: " + type(exc).__name__, file=sys.stderr)
        raise SystemExit(2)
