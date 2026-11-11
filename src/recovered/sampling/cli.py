"""Summarize the 100/250-Hz frozen sensitivity outputs without retraining."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd


def summarize(root: Path, output: Path) -> None:
    rows = []
    for rate in (100, 250):
        path = root / f"revision_r2_sampling/SAMPLING_{rate}HZ_RESULTS.csv"
        frame = pd.read_csv(path)
        for row in frame.to_dict("records"):
            rows.append({"sampling_rate_hz": rate, **row})
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(f"wrote {len(rows)} rows to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/recovered/sampling_sensitivity.csv"))
    args = parser.parse_args()
    summarize(args.root, args.output)


if __name__ == "__main__":
    main()
