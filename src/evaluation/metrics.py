from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src.evaluation.threshold import specificity_at_sensitivity
from src.utils.config import load_config, repository_path
from src.utils.logging import configure_logging
from src.utils.provenance import write_run_metadata


LOGGER = logging.getLogger(__name__)


def calculate_metrics(labels: np.ndarray, probabilities: np.ndarray, target: float) -> dict[str, float]:
    specificity, threshold, sensitivity = specificity_at_sensitivity(labels, probabilities, target)
    predicted = probabilities >= threshold
    true_positive = int(((predicted == 1) & (labels == 1)).sum())
    true_negative = int(((predicted == 0) & (labels == 0)).sum())
    positive = int(predicted.sum())
    negative = int((~predicted).sum())
    return {
        "auroc": float(roc_auc_score(labels, probabilities)),
        "auprc": float(average_precision_score(labels, probabilities)),
        "brier": float(brier_score_loss(labels, probabilities)),
        "tau95": threshold,
        "sensitivity_at_tau95": sensitivity,
        "specificity_at_tau95": specificity,
        "ppv_at_tau95": true_positive / max(positive, 1),
        "npv_at_tau95": true_negative / max(negative, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate frozen OOF performance measures")
    parser.add_argument("--config", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    configure_logging(args.verbose)
    config = load_config(args.config)
    prediction_dir = repository_path(config, "outputs") / "oof"
    rows = []
    for config_id in ["C0", "C1", "C2", "C3"]:
        path = prediction_dir / f"{config_id}_predictions.csv"
        frame = pd.read_csv(path)
        labels = frame.omi_label.to_numpy(dtype=int)
        probabilities = frame.oof_probability.to_numpy(dtype=float)
        rows.append(
            {
                "configuration": config_id,
                "n_ecg": len(frame),
                "n_patients": frame.patient_id.nunique(),
                "n_omi_patients": frame.loc[frame.omi_label == 1, "patient_id"].nunique(),
                **calculate_metrics(labels, probabilities, config["evaluation"]["target_sensitivity"]),
            }
        )
    result = pd.DataFrame(rows)
    baseline = result.loc[result.configuration == "C0"].iloc[0]
    result["delta_auroc_vs_C0"] = result.auroc - baseline.auroc
    result["delta_spec95_vs_C0"] = result.specificity_at_tau95 - baseline.specificity_at_tau95
    output_dir = repository_path(config, "outputs") / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_dir / "oof_performance.csv", index=False)
    write_run_metadata(output_dir / "metrics_run_metadata.json", {"target_sensitivity": config["evaluation"]["target_sensitivity"]})
    LOGGER.info("Wrote OOF performance for C0-C3")


if __name__ == "__main__":
    main()

