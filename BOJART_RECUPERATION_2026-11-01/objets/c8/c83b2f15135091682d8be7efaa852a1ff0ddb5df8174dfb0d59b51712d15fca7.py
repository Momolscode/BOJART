"""Read-only check of Marwin's declared memory dependencies, not semantic truth."""
import argparse
import hashlib
import json
from pathlib import Path

BASE_PATHS = (
    "status", "delivered_film", "current_production", "active_production",
    "next_creative_brief", "creative_control_latest",
    "context_governance.current_coordination", "feedback", "identity_correction",
    "identity_reference_policy_latest", "distribution_policy",
    "context_governance.session_limits",
)
CLAIM_PATHS = {
    "integration": (
        "reference_learning.toolchain_integration_latest",
        "reference_learning.reverse_api_integration_latest",
    ),
    "review_support": ("reference_learning.identity_review_support_latest",),
}


def resolve(document, path):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def fingerprint(document, paths):
    values = {path: resolve(document, path) for path in paths}
    raw = json.dumps(values, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def audit(document):
    resume = document.get("memory_resume")
    if not isinstance(resume, dict):
        return {"ok": False, "errors": ["memory_resume_missing"]}
    paths = resume.get("dependency_paths")
    if not isinstance(paths, list) or not all(isinstance(p, str) and p for p in paths):
        return {"ok": False, "errors": ["dependency_paths_invalid"]}
    errors = []
    if len(set(paths)) != len(paths):
        errors.append("duplicate_dependency_paths")
    if any(p == "memory_resume" or p.startswith("memory_resume.") for p in paths):
        errors.append("self_dependency")
    required = set(BASE_PATHS)
    for claim, sources in CLAIM_PATHS.items():
        if claim in resume:
            required.update(sources)
    uncovered = sorted(required - set(paths))
    if uncovered:
        errors.append("source_coverage_incomplete")
    missing = []
    for path in paths:
        try:
            resolve(document, path)
        except KeyError:
            missing.append(path)
    if missing:
        errors.append("source_path_missing")
    actual = None
    if not missing and "self_dependency" not in errors:
        try:
            actual = fingerprint(document, paths)
        except (ValueError, TypeError):
            errors.append("source_not_canonical_json")
        if actual is not None and actual != resume.get("dependency_sha256"):
            errors.append("dependency_hash_mismatch")
    return {
        "ok": not errors, "errors": errors,
        "uncovered_paths": uncovered, "missing_paths": missing,
        "dependency_count": len(paths), "computed_sha256": actual,
        "scope": "Declared source coverage and hash only; no semantic, artistic, permission or live-service validation.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path, help="Explicit current JSON; never defaults to bundled historical fixtures")
    args = parser.parse_args()
    try:
        result = audit(json.loads(args.document.read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        result = {"ok": False, "errors": [type(error).__name__]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
