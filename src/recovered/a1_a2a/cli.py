"""Reproduce A1/A2a fold decisions from stored frozen predictions.

No model fitting, hidden TEST access, or STAFF III inference.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.evaluation.confusion import confusion_metrics


def collect(root: Path) -> list[dict]:
    rows = []
    a1_root = root / "10_gate2_r2/runs/RUN_20261110_A1A2a"
    a2_root = root / "10_gate2_a2a_integration/runs/RUN_20261110_A2a_ONLY"
    jobs = [
        ("A1_seedA", a1_root, "A1_seedA"),
        ("A1_seedB", a1_root, "A1_seedB"),
    ]
    for analysis, base, directory in jobs:
        for fold in range(5):
            for config in ["C0", "C1", "C2", "C3"]:
                path = base / f"fold{fold}" / directory / f"{config}_eval_predictions.csv"
                frame = pd.read_csv(path)
                counts = confusion_metrics(frame.omi_label, frame.probability >= frame.threshold)
                rows.append({"analysis": analysis, "outer_fold": fold, "configuration": config, **counts})
    for fold in range(5):
        for config in ["C0", "C1", "C2", "C3"]:
            path = a2_root / f"fold{fold}" / "A2a" / f"{config}_eval_predictions.csv"
            frame = pd.read_csv(path)
            counts = confusion_metrics(frame.omi_label, frame.probability >= frame.threshold)
            rows.append({"analysis": "A2a", "outer_fold": fold, "configuration": config, **counts})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/recovered/a1_a2a_fold_metrics.csv"))
    args = parser.parse_args()
    rows = collect(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
