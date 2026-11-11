"""Confusion-matrix metrics for frozen ECG-level tables."""
from __future__ import annotations

import numpy as np


def confusion_metrics(labels, predicted) -> dict[str, float | int]:
    labels = np.asarray(labels, dtype=int)
    predicted = np.asarray(predicted, dtype=int)
    if labels.shape != predicted.shape:
        raise ValueError("labels and predicted must have equal length")
    tp = int(((labels == 1) & (predicted == 1)).sum())
    fp = int(((labels == 0) & (predicted == 1)).sum())
    tn = int(((labels == 0) & (predicted == 0)).sum())
    fn = int(((labels == 1) & (predicted == 0)).sum())
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "sensitivity": tp / (tp + fn) if tp + fn else float("nan"),
        "specificity": tn / (tn + fp) if tn + fp else float("nan"),
    }
