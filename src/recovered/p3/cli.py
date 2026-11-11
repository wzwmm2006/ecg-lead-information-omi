"""Run the P3 held-out matched-TPR analysis from frozen prediction CSVs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.recovered.p3.matched_tpr import specificity_at_tpr


ANALYSES = {
    "A1_seedA": Path("10_gate2_r2/runs/RUN_20261110_A1A2a/fold{fold}/A1_seedA/{config}_eval_predictions.csv"),
    "A1_seedB": Path("10_gate2_r2/runs/RUN_20261110_A1A2a/fold{fold}/A1_seedB/{config}_eval_predictions.csv"),
    "A2a": Path("10_gate2_a2a_integration/runs/RUN_20261110_A2a_ONLY/fold{fold}/A2a/{config}_eval_predictions.csv"),
}


def run(root: Path, output: Path) -> None:
    rows = []
    for analysis, template in ANALYSES.items():
        for fold in range(5):
            for config in ["C0", "C1", "C2", "C3"]:
                path = root / template.format(fold=fold, config=config)
                frame = pd.read_csv(path)
                result = specificity_at_tpr(frame.omi_label.to_numpy(), frame.probability.to_numpy(), 0.95)
                rows.append({"analysis": analysis, "outer_fold": fold, "configuration": config, "n_ecg": len(frame), **result})
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(json.dumps({"rows": len(rows), "output": str(output)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/recovered/p3_matched_tpr.csv"))
    args = parser.parse_args()
    run(args.root, args.output)


if __name__ == "__main__":
    main()
