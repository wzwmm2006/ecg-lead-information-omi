from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy
import pandas
import scipy
import sklearn
import torch
import wfdb

from src import __version__


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def version_information() -> dict[str, str]:
    return {
        "package": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": numpy.__version__,
        "pandas": pandas.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "torch": torch.__version__,
        "wfdb": wfdb.__version__,
        "matplotlib": matplotlib.__version__,
    }


def write_run_metadata(path: Path, details: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "versions": version_information(),
        **details,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create SHA-256 manifest for public repository files")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    excluded = {"data", "outputs", "models", "logs", ".git", ".venv", "__pycache__"}
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == output or any(part in excluded for part in path.relative_to(root).parts):
            continue
        rows.append({"path": path.relative_to(root).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(f"{row['sha256']}  {row['path']}" for row in rows) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()

