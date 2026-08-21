from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def specificity_at_sensitivity(labels: np.ndarray, probabilities: np.ndarray, target: float = 0.95) -> tuple[float, float, float]:
    """Return specificity, threshold, and achieved sensitivity using the frozen rule."""
    labels = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    if labels.shape != probabilities.shape or labels.ndim != 1:
        raise ValueError("Labels and probabilities must be one-dimensional arrays of equal length")
    order = np.argsort(-probabilities)
    ordered_labels = labels[order]
    ordered_probabilities = probabilities[order]
    eligible = np.flatnonzero(np.cumsum(ordered_labels) / max(ordered_labels.sum(), 1) >= target)
    if not len(eligible):
        return float("nan"), float("nan"), float("nan")
    threshold = ordered_probabilities[eligible[0]]
    predicted = probabilities >= threshold
    specificity = (predicted[labels == 0] == 0).mean()
    sensitivity = predicted[labels == 1].mean()
    return float(specificity), float(threshold), float(sensitivity)


def main() -> None:
    parser = argparse.ArgumentParser(description="Select the frozen high-sensitivity threshold")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--label-column", default="omi_label")
    parser.add_argument("--probability-column", default="oof_probability")
    parser.add_argument("--target", type=float, default=0.95)
    args = parser.parse_args()
    frame = pd.read_csv(args.predictions)
    specificity, threshold, sensitivity = specificity_at_sensitivity(
        frame[args.label_column].to_numpy(),
        frame[args.probability_column].to_numpy(),
        args.target,
    )
    print(json.dumps({"target_sensitivity": args.target, "threshold": threshold, "sensitivity": sensitivity, "specificity": specificity}, indent=2))


if __name__ == "__main__":
    main()

