"""Paired patient-within-fold bootstrap for post hoc matched-TPR contrasts."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.recovered.p3.matched_tpr import specificity_at_tpr


def _complete_configuration_frame(group: pd.DataFrame, configurations: list[str]) -> pd.DataFrame:
    """Keep patients whose configuration rows have complete and unchanged labels."""
    required = ["patient_id", "configuration", "omi_label", "probability"]
    rows = group[required].copy()
    counts = rows.groupby(["patient_id", "configuration"], observed=True).size().unstack(fill_value=0)
    counts = counts.reindex(columns=configurations, fill_value=0)
    complete = counts[(counts > 0).all(axis=1)].index
    rows = rows[rows.patient_id.isin(complete)]
    label_counts = rows.groupby("patient_id", observed=True).omi_label.nunique()
    rows = rows[rows.patient_id.isin(label_counts[label_counts == 1].index)]
    return rows


def _sample_patient_rows(rows: pd.DataFrame, chosen: np.ndarray) -> pd.DataFrame:
    """Copy every ECG row of each sampled patient once per selection."""
    chosen_series = pd.Series([str(value) for value in chosen], name="patient_id")
    counts = chosen_series.value_counts().rename("sample_count")
    sampled = rows.merge(counts.rename(index=lambda value: str(value)), left_on="patient_id", right_index=True, how="inner")
    return sampled.loc[sampled.index.repeat(sampled.sample_count.astype(int))].drop(columns="sample_count")


def _specificity_tables(rows: pd.DataFrame, configurations: list[str]) -> dict[str, tuple]:
    tables = {}
    for config in configurations:
        config_rows = rows.loc[rows.configuration == config]
        labels = config_rows.omi_label.to_numpy(dtype=int)
        probabilities = config_rows.probability.to_numpy(dtype=float)
        order = np.argsort(-probabilities, kind="mergesort")
        labels = labels[order]
        probabilities = probabilities[order]
        positives = int(labels.sum())
        negatives = int(len(labels) - positives)
        thresholds = np.unique(probabilities)[::-1]
        end = np.searchsorted(-probabilities, -thresholds, side="right")
        true_positives = np.cumsum(labels)[end - 1] if len(end) else np.array([], dtype=int)
        false_positives = end - true_positives
        finite = positives > 0 and negatives > 0
        tables[config] = (positives, negatives, thresholds, true_positives, false_positives, finite)
    return tables


def _specificity_from_counts(tables: dict[str, tuple], target_tpr: float) -> dict[str, float]:
    values = {}
    for config, (positives, negatives, thresholds, true_positives, false_positives, finite) in tables.items():
        if not finite:
            values[config] = float("nan")
            continue
        tpr = true_positives / positives
        crossing = np.flatnonzero(tpr >= target_tpr)
        if len(crossing) == 0:
            values[config] = float("nan")
            continue
        j = int(crossing[0])
        if j == 0:
            fpr = 0.0
        else:
            tpr_lo, tpr_hi = tpr[j - 1], tpr[j]
            fpr_lo, fpr_hi = false_positives[j - 1] / negatives, false_positives[j] / negatives
            weight = (target_tpr - tpr_lo) / (tpr_hi - tpr_lo)
            fpr = fpr_lo + weight * (fpr_hi - fpr_lo)
        values[config] = float(1.0 - fpr)
    return values


def paired_tpr95_bootstrap(
    frame: pd.DataFrame,
    replicate_count: int = 2000,
    seed: int = 20261110,
    target_tpr: float = 0.95,
    fold_rng_seeds: dict | None = None,
) -> tuple[list[dict], pd.DataFrame, dict[int, int]]:
    """Bootstrap patients within each fold, retaining all ECG rows and patient multiplicity.

    Each fold has an independent random stream that advances across replicates. The same
    sampled patients are used for all configurations. Fold weights are the original
    non-OMI ECG counts, and only replicates with a valid ROC crossing in every fold and
    configuration enter the percentile intervals.
    """
    required = {"patient_id", "outer_fold", "configuration", "omi_label", "probability"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(frame.columns))}")
    if replicate_count < 1:
        raise ValueError("replicate_count must be positive")
    configurations = sorted(frame.configuration.unique())
    if "C0" not in configurations or len(configurations) < 2:
        raise ValueError("At least one contrast against C0 is required")
    contrasts = [config for config in configurations if config != "C0"]
    if fold_rng_seeds is None:
        fold_rng_seeds = frame.attrs.get("fold_rng_seeds", {})
    rngs = {}

    by_fold = {}
    fold_weights = {}
    point_by_fold = {}
    for fold_value, raw_group in frame.groupby("outer_fold", sort=True):
        fold = int(fold_value)
        group = _complete_configuration_frame(raw_group, configurations)
        if group.empty:
            raise ValueError(f"No complete patients in fold {fold}")
        by_fold[fold] = group
        fold_weights[fold] = int((group.omi_label == 0).sum())
        point_by_fold[fold] = _specificity_from_counts(_specificity_tables(group, configurations), target_tpr)
        rng_seed = int(fold_rng_seeds[fold]) if fold in fold_rng_seeds else int(fold_rng_seeds.get(str(fold), seed + fold))
        rngs[fold] = np.random.default_rng(rng_seed)

    point_failure = ""
    for fold, values in point_by_fold.items():
        if not np.isfinite(values["C0"]):
            point_failure = f"Point estimate has no TPR {target_tpr:g} crossing in fold {fold} C0"
            break
        missing = [config for config, value in values.items() if config != "C0" and not np.isfinite(value)]
        if missing:
            point_failure = f"Point estimate has no TPR {target_tpr:g} crossing in fold {fold} {', '.join(missing)}"
            break

    records = []
    if point_failure:
        records.append({
            "replicate": 0,
            "valid": False,
            "contrast": "",
            "delta_specificity": np.nan,
            "reason": point_failure,
        })
    for replicate in range(0 if point_failure else replicate_count):
        fold_deltas = {config: 0.0 for config in contrasts}
        valid = True
        failure_reason = ""
        for fold, group in by_fold.items():
            patients = np.array(sorted(group.patient_id.unique()), dtype=object)
            chosen = rngs[fold].choice(patients, len(patients), replace=True)
            sampled = _sample_patient_rows(group, chosen)
            values = _specificity_from_counts(_specificity_tables(sampled, configurations), target_tpr)
            for config in configurations:
                if sampled.loc[sampled.configuration == config, "omi_label"].eq(0).sum() == 0:
                    valid = False
                    failure_reason = f"fold {fold} {config} has no non-OMI ECGs"
                    break
                if not np.isfinite(values[config]):
                    valid = False
                    failure_reason = f"fold {fold} {config} has no ROC crossing at TPR {target_tpr:g}"
                    break
            if not valid:
                break
            for config in contrasts:
                fold_deltas[config] += fold_weights[fold] * (values[config] - values["C0"])
        total_weight = sum(fold_weights.values())
        if valid and total_weight:
            for config in contrasts:
                records.append({
                    "replicate": int(replicate),
                    "valid": True,
                    "contrast": f"{config}-C0",
                    "delta_specificity": fold_deltas[config] / total_weight,
                    "reason": "",
                })
        else:
            records.append({
                "replicate": int(replicate),
                "valid": False,
                "contrast": "",
                "delta_specificity": np.nan,
                "reason": failure_reason or "no non-OMI ECGs across folds",
            })

    raw = pd.DataFrame.from_records(records)
    summary = []
    total_weight = sum(fold_weights.values())
    for config in contrasts:
        if total_weight and not point_failure:
            point = sum(fold_weights[fold] * (point_by_fold[fold][config] - point_by_fold[fold]["C0"]) for fold in by_fold) / total_weight
        else:
            point = np.nan
        values = raw.loc[(raw.valid) & (raw.contrast == f"{config}-C0"), "delta_specificity"].to_numpy(dtype=float)
        if len(values):
            lower, upper = np.quantile(values, [0.025, 0.975])
        else:
            lower = upper = np.nan
        summary.append({
            "contrast": f"{config}-C0",
            "point_estimate": float(point),
            "ci_low": float(lower),
            "ci_high": float(upper),
            "valid_replicates": int(len(values)),
            "invalid_replicates": int(replicate_count - len(values)),
        })
    return summary, raw, fold_weights