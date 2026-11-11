"""Post hoc empirical-ROC interpolation at TPR 95%."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_curve


def specificity_at_tpr(labels, probabilities, target_tpr: float = 0.95) -> dict[str, float]:
    """Return interpolated specificity and the deterministic first-crossing values.

    This is an estimated ROC operating point. It does not define a threshold
    selected independently of the evaluated records.
    """
    labels = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    if labels.shape != probabilities.shape or labels.ndim != 1:
        raise ValueError("labels and probabilities must be one-dimensional and equal length")
    if not 0.0 < target_tpr <= 1.0:
        raise ValueError("target_tpr must be in (0, 1]")

    fpr, tpr, thresholds = roc_curve(labels, probabilities)
    crossing = np.flatnonzero(tpr >= target_tpr)
    if len(crossing) == 0:
        return {
            "specificity_at_tpr": float("nan"),
            "fpr_at_tpr": float("nan"),
            "det_threshold": float("nan"),
            "det_sensitivity": float("nan"),
            "det_specificity": float("nan"),
        }
    j = int(crossing[0])
    if j == 0:
        i_fpr = fpr[j]
        i_tpr = tpr[j]
    else:
        tpr_lo, tpr_hi = tpr[j - 1], tpr[j]
        if tpr_hi == tpr_lo:
            weight = 0.0
        else:
            weight = (target_tpr - tpr_lo) / (tpr_hi - tpr_lo)
        i_fpr = fpr[j - 1] + weight * (fpr[j] - fpr[j - 1])
        i_tpr = tpr_lo + weight * (tpr_hi - tpr_lo)

    threshold = thresholds[j]
    predicted = probabilities >= threshold
    sensitivity = predicted[labels == 1].mean() if (labels == 1).any() else float("nan")
    specificity = (predicted[labels == 0] == 0).mean() if (labels == 0).any() else float("nan")
    return {
        "specificity_at_tpr": float(1.0 - i_fpr),
        "fpr_at_tpr": float(i_fpr),
        "interpolated_tpr": float(i_tpr),
        "det_threshold": float(threshold),
        "det_sensitivity": float(sensitivity),
        "det_specificity": float(specificity),
    }
