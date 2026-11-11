"""Paired patient-within-fold bootstrap for post hoc matched-TPR contrasts."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.recovered.p3.matched_tpr import specificity_at_tpr


def paired_tpr95_bootstrap(frame: pd.DataFrame, replicate_count: int = 2000, seed: int = 20261110, target_tpr: float = 0.95):
    """Resample patients within each fold and retain the same patients across configurations."""
    required = {"patient_id", "outer_fold", "configuration", "omi_label", "probability"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(frame.columns))}")
    rng = np.random.default_rng(seed)
    if "fold_rng_seeds" in frame.attrs:
        fold_seeds = frame.attrs["fold_rng_seeds"]
    else:
        fold_seeds = {}
    by_fold = {fold: group for fold, group in frame.groupby("outer_fold")}
    point_by_fold = {}
    for fold, group in by_fold.items():
        wide = group.pivot_table(index=["patient_id"], columns="configuration", values="probability", aggfunc="first")
        labels = group.groupby("patient_id")["omi_label"].first()
        point_by_fold[fold] = {config: specificity_at_tpr(labels, wide[config], target_tpr)["specificity_at_tpr"] for config in wide.columns}
    results = {config: [] for config in sorted(frame.configuration.unique()) if config != "C0"}
    for replicate in range(replicate_count):
        fold_specificities = {config: 0.0 for config in results}
        total_weight = 0
        for fold, group in by_fold.items():
            fold_rng = np.random.default_rng(fold_seeds.get(fold, seed + int(fold)))
            patients = group.patient_id.unique()
            chosen = fold_rng.choice(patients, len(patients), replace=True)
            by_patient = {patient: group[group.patient_id == patient] for patient in patients}
            sampled = pd.concat([by_patient[p] for p in chosen], ignore_index=True)
            wide = sampled.pivot_table(index=["patient_id"], columns="configuration", values="probability", aggfunc="first")
            labels = sampled.groupby("patient_id")["omi_label"].first()
            non_omi_count = int((labels == 0).sum())
            values = {config: specificity_at_tpr(labels, wide[config], target_tpr)["specificity_at_tpr"] for config in wide.columns}
            for config in results:
                fold_specificities[config] += non_omi_count * (values[config] - values["C0"])
            total_weight += non_omi_count
        if total_weight:
            for config in results:
                results[config].append(fold_specificities[config] / total_weight)
    summary = []
    for config, values in results.items():
        point = sum(
            int((group.groupby("patient_id")["omi_label"].first() == 0).sum()) * (point_by_fold[fold][config] - point_by_fold[fold]["C0"])
            for fold, group in by_fold.items()
        ) / sum(int((group.groupby("patient_id")["omi_label"].first() == 0).sum()) for group in by_fold.values())
        lower, upper = np.quantile(values, [0.025, 0.975])
        summary.append({"contrast": f"{config}-C0", "point_estimate": point, "ci_low": float(lower), "ci_high": float(upper), "valid_replicates": len(values)})
    return summary
