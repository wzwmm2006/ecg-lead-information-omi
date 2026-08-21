from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from src.evaluation.threshold import specificity_at_sensitivity
from src.utils.config import load_config, repository_path
from src.utils.logging import configure_logging
from src.utils.provenance import write_run_metadata


LOGGER = logging.getLogger(__name__)


def load_wide_predictions(prediction_dir) -> pd.DataFrame:
    frames = [pd.read_csv(prediction_dir / f"{config_id}_predictions.csv") for config_id in ["C0", "C1", "C2", "C3"]]
    long = pd.concat(frames, ignore_index=True)
    return long.pivot(
        index=["ecg_id", "patient_id", "omi_label", "fold"],
        columns="configuration",
        values="oof_probability",
    ).reset_index()


def bootstrap_configuration(data: pd.DataFrame, config_id: str, seed: int, replicates: int, target: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    patients = data.patient_id.unique()
    by_patient = {patient: group.index.to_numpy() for patient, group in data.groupby("patient_id")}
    values = []
    for _ in range(replicates):
        indices = np.concatenate([by_patient[patient] for patient in rng.choice(patients, len(patients), replace=True)])
        sample = data.loc[indices]
        labels = sample.omi_label.to_numpy(dtype=int)
        probabilities = sample[config_id].to_numpy(dtype=float)
        values.append(
            [
                roc_auc_score(labels, probabilities),
                average_precision_score(labels, probabilities),
                specificity_at_sensitivity(labels, probabilities, target)[0],
            ]
        )
    return np.asarray(values)


def paired_spec_bootstrap(data: pd.DataFrame, reduced: str, seed: int, replicates: int, target: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    patients = data.patient_id.unique()
    by_patient = {patient: group.index.to_numpy() for patient, group in data.groupby("patient_id")}
    values = []
    for _ in range(replicates):
        indices = np.concatenate([by_patient[patient] for patient in rng.choice(patients, len(patients), replace=True)])
        sample = data.loc[indices]
        labels = sample.omi_label.to_numpy(dtype=int)
        baseline = specificity_at_sensitivity(labels, sample.C0.to_numpy(), target)[0]
        comparison = specificity_at_sensitivity(labels, sample[reduced].to_numpy(), target)[0]
        values.append(comparison - baseline)
    return np.asarray(values)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen patient-level OOF bootstrap inference")
    parser.add_argument("--config", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    configure_logging(args.verbose)
    config = load_config(args.config)
    prediction_dir = repository_path(config, "outputs") / "oof"
    output_dir = repository_path(config, "outputs") / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_wide_predictions(prediction_dir)
    base_seed = config["study"]["base_seed"]
    replicates = config["evaluation"]["bootstrap_replicates"]
    target = config["evaluation"]["target_sensitivity"]
    uncertainty_rows = []
    for position, config_id in enumerate(["C0", "C1", "C2", "C3"]):
        samples = bootstrap_configuration(data, config_id, base_seed + position + 1, replicates, target)
        interval = np.quantile(samples, [0.025, 0.975], axis=0)
        uncertainty_rows.append(
            {
                "configuration": config_id,
                "auroc_ci_low": interval[0, 0],
                "auroc_ci_high": interval[1, 0],
                "auprc_ci_low": interval[0, 1],
                "auprc_ci_high": interval[1, 1],
                "spec95_ci_low": interval[0, 2],
                "spec95_ci_high": interval[1, 2],
            }
        )
        LOGGER.info("Completed %s uncertainty bootstrap", config_id)
    pd.DataFrame(uncertainty_rows).to_csv(output_dir / "oof_uncertainty.csv", index=False)
    contrast_rows = []
    for reduced in ["C1", "C2", "C3"]:
        values = paired_spec_bootstrap(data, reduced, base_seed + 99, replicates, target)
        low, median, high = np.quantile(values, [0.025, 0.5, 0.975])
        contrast_rows.append({"contrast": f"{reduced}-C0", "ci_low": low, "bootstrap_median": median, "ci_high": high})
        LOGGER.info("Completed %s-C0 paired bootstrap", reduced)
    pd.DataFrame(contrast_rows).to_csv(output_dir / "paired_spec95_contrasts.csv", index=False)
    write_run_metadata(
        output_dir / "bootstrap_run_metadata.json",
        {"replicates": replicates, "individual_seed_rule": "base_seed + configuration_position + 1", "paired_seed": base_seed + 99},
    )


if __name__ == "__main__":
    main()
