"""Patient-disjoint A1/A2a nested calibration support.

The full historical executors are retained under provenance/frozen_scripts.
This module exposes the auditable split and threshold logic without embedding
any patient data or checkpoints.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.evaluation.threshold import specificity_at_sensitivity


def build_inner_split(patient_fold: pd.DataFrame, patient_omi: pd.DataFrame, *, outer_fold: int, seed: int = 20260813, calibration_fraction: float = 0.2) -> pd.DataFrame:
    """Build the frozen 80/20 inner split from outer-training patients only."""
    fold_lookup = patient_fold.drop_duplicates("patient_id").set_index("patient_id")["fold"]
    labels = patient_omi.drop_duplicates("patient_id").set_index("patient_id")["omi"]
    outer_train_ids = sorted(fold_lookup[fold_lookup != outer_fold].index)
    patients = pd.DataFrame({"patient_id": outer_train_ids})
    patients["omi"] = patients.patient_id.map(labels)
    fit, calibration = train_test_split(
        patients,
        test_size=calibration_fraction,
        random_state=seed + 1000 + outer_fold,
        stratify=patients.omi,
    )
    result = pd.concat(
        [
            fit.assign(inner_role="INNER_MODEL_FIT"),
            calibration.assign(inner_role="INNER_THRESHOLD_CALIBRATION"),
        ],
        ignore_index=True,
    )
    result["outer_fold"] = int(outer_fold)
    return result.sort_values(["inner_role", "patient_id"]).reset_index(drop=True)


def choose_locked_threshold(labels, calibration_probabilities, target: float = 0.95):
    """Return specificity, threshold, and achieved calibration sensitivity."""
    return specificity_at_sensitivity(labels, calibration_probabilities, target)
