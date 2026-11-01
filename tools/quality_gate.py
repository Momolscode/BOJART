#!/usr/bin/env python3
"""Validate a shot review without external dependencies.

Usage:
  python tools/quality_gate.py reviews/example.json
Exit code 0 = approved; 1 = blocked or invalid review.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATES = json.loads((ROOT / "configs/quality_gates.json").read_text(encoding="utf-8"))["gates"]
MANDATORY = {gate["id"] for gate in GATES if gate["required"]}


def validate(review):
    if not isinstance(review, dict) or not isinstance(review.get("shot_id"), str) or not review["shot_id"].strip():
        return False, ["shot_id missing"]
    checks = review.get("checks")
    if not isinstance(checks, dict):
        return False, ["checks must be an object"]
    problems = []
    for gate_id in sorted(MANDATORY):
        if checks.get(gate_id) is not True:
            problems.append(f"{gate_id}: not approved")
    if review.get("status") != "approved":
        problems.append("status must be approved")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        problems.append("human reviewer missing")
    unknown = set(checks) - {gate["id"] for gate in GATES}
    if unknown:
        problems.append("unknown quality gates: " + ", ".join(sorted(unknown)))
    return not problems, problems


def main():
    if len(sys.argv) != 2:
        print("Usage: python tools/quality_gate.py reviews/example.json")
        return 1
    try:
        review = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Review cannot be read: {exc}")
        return 1
    passed, problems = validate(review)
    print("APPROVED" if passed else "BLOCKED")
    for problem in problems:
        print(" -", problem)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

