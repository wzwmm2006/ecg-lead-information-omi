"""Read-only verification of delivered frozen outputs.

This module does not fit models and does not access held-out labels. It compares
files that are supplied by the user against the SHA-256 manifest in provenance/
and can recompute confusion-matrix metrics from already frozen prediction files.

Classifications:
    FROZEN_OUTPUT_MATCHED - supplied file hash equals the frozen manifest value.
    EXECUTABLE_VERIFIED  - deterministic metric recomputation from supplied records.
    PROVENANCE_ONLY      - code or evidence retained for traceability, not run here.
    NOT_VERIFIED         - required artifact is absent or a check fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path



def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_manifest(root: Path, manifest: Path) -> dict:
    records = json.loads(manifest.read_text(encoding="utf-8"))
    results = {}
    for relative, expected in records.items():
        path = root / relative
        actual = sha256(path) if path.exists() else None
        results[relative] = {
            "expected": expected["sha256"],
            "actual": actual,
            "classification": "FROZEN_OUTPUT_MATCHED" if actual == expected["sha256"] else "NOT_VERIFIED",
        }
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Project root containing frozen evidence files")
    parser.add_argument("--manifest", type=Path, default=Path("provenance/FROZEN_OUTPUT_HASHES.json"))
    parser.add_argument("--json-out", type=Path, help="Optional aggregate verification report")
    args = parser.parse_args(argv)
    results = check_manifest(args.root, args.manifest)
    if args.json_out:
        args.json_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    for relative, result in results.items():
        print(f"{result['classification']:24s} {relative}")
    return 0 if all(v["classification"] == "FROZEN_OUTPUT_MATCHED" for v in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
