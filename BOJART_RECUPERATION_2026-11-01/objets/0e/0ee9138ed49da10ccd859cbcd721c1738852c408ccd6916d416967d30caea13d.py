#!/usr/bin/env python3
"""Download known completed remote video jobs into a PRIVATE local archive.

Requires runs/remote-media.json, intentionally not committed to a public repo.
Does not create, regenerate, charge or publish video.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
APPROVED_HOST = "d8j0ntlcm91z4.cloudfront.net"
MAX_BYTES = 250 * 1024 * 1024


def download(entry: dict) -> dict:
    url = entry["url"]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != APPROVED_HOST:
        raise ValueError("Unexpected source host")
    render_root = (ROOT / "renders").resolve()
    dest = (ROOT / entry["destination"]).resolve()
    if not dest.is_relative_to(render_root) or dest.suffix.lower() != ".mp4":
        raise ValueError("Unexpected destination")
    if dest.exists():
        return {"job_id": entry["job_id"], "status": "already_exists", "path": entry["destination"]}
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".mp4.part")
    if tmp.exists():
        raise FileExistsError("Partial file exists; check before retry")
    size = 0
    digest = hashlib.sha256()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "BOJART-archive/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response, tmp.open("xb") as handle:
            redirected = urllib.parse.urlparse(response.url)
            if redirected.scheme != "https" or redirected.hostname != APPROVED_HOST:
                raise ValueError("Unexpected redirect")
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Download exceeds limit")
                digest.update(chunk)
                handle.write(chunk)
        if size < 1024 or b"ftyp" not in tmp.read_bytes()[:32]:
            raise ValueError("Invalid MP4 container")
        tmp.rename(dest)
        return {"job_id": entry["job_id"], "status": "downloaded", "bytes": size, "sha256": digest.hexdigest()}
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def main() -> int:
    manifest = ROOT / "runs/remote-media.json"
    if not manifest.is_file():
        print("Private remote-media.json is absent.")
        return 2
    jobs = json.loads(manifest.read_text(encoding="utf-8"))
    failed = False
    for job in jobs:
        try:
            result = download(job)
        except Exception as exc:
            result = {"job_id": job.get("job_id"), "status": "failed", "error": str(exc)}
            failed = True
        print(json.dumps(result, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
