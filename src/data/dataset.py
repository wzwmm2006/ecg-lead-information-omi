from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, train_test_split

from src.data.preprocessing import prepare_metadata
from src.utils.config import repository_path


def load_processed(config: dict, split: str) -> tuple[pd.DataFrame, np.ndarray]:
    metadata = prepare_metadata(
        repository_path(config, f"{split}_metadata"),
        split,
        set(config["data"]["excluded_train_records"]),
    )
    cache = repository_path(config, f"processed_{split}")
    index_path = cache.with_suffix(".index.csv")
    if not cache.exists() or not index_path.exists():
        raise FileNotFoundError(f"Run preprocessing first: missing {cache} or {index_path}")
    index = pd.read_csv(index_path, dtype={"ecg_id": str})
    index["ecg_id"] = index.ecg_id.str.zfill(5)
    if index.ecg_id.tolist() != metadata.ecg_id.tolist():
        raise ValueError("Processed waveform index does not match metadata order")
    waveforms = np.asarray(np.load(cache, mmap_mode="r"), dtype=np.float32)
    expected = (len(metadata), 12, config["data"]["output_samples"])
    if waveforms.shape != expected:
        raise ValueError(f"Expected processed shape {expected}, received {waveforms.shape}")
    if split == "train":
        required = {"Patient_id", "OMI"}
        if not required.issubset(metadata.columns):
            raise ValueError(f"Development metadata missing columns: {sorted(required - set(metadata.columns))}")
        metadata["patient_id"] = metadata.Patient_id.astype(str)
        metadata["omi"] = metadata.OMI.astype(int)
    return metadata, waveforms


def patient_training_weights(frame: pd.DataFrame) -> np.ndarray:
    """Return inverse-patient-count weights times inverse-class weights.

    The class prevalence is calculated over every record in ``frame``. During
    OOF training, ``frame`` is the complete development set, matching both the
    v1.0.0 public code and the historical frozen executor. For final 80/20
    fitting, ``frame`` is the model-fit subset; that behavior is reported
    separately and is not the OOF weighting rule.
    """
    counts = frame.patient_id.value_counts()
    patient_weight = frame.patient_id.map(1 / counts).to_numpy()
    labels = frame.omi.to_numpy()
    prevalence = labels.mean()
    class_weight = np.where(labels == 1, 1.0 / prevalence, 1.0 / (1.0 - prevalence))
    return patient_weight * class_weight


def oof_folds(frame: pd.DataFrame, folds: int, seed: int) -> np.ndarray:
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    assignment = np.full(len(frame), -1, dtype=int)
    for fold, (_, validation) in enumerate(splitter.split(frame, frame.omi, frame.patient_id)):
        assignment[validation] = fold
    if (assignment < 0).any():
        raise RuntimeError("Incomplete OOF fold assignment")
    return assignment


def finalization_split(frame: pd.DataFrame, calibration_fraction: float, seed: int) -> np.ndarray:
    patients = frame[["patient_id", "omi"]].groupby("patient_id", as_index=False).agg(omi=("omi", "max"))
    fit_patients, _ = train_test_split(
        patients,
        test_size=calibration_fraction,
        random_state=seed,
        stratify=patients.omi,
    )
    fit_set = set(fit_patients.patient_id)
    return frame.patient_id.isin(fit_set).to_numpy()


def inner_split(
    frame: pd.DataFrame,
    outer_fold: int,
    fold_column: str = "fold",
    calibration_fraction: float = 0.2,
    seed: int = 20260813,
) -> pd.DataFrame:
    """Return the frozen patient-disjoint A1/A2a roles for one outer fold.

    Outer-evaluation patients are excluded entirely from inner fitting and
    calibration. The split is generated from outer-training patients only.
    """
    required = {"patient_id", "omi", fold_column}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(frame.columns))}")
    if not frame.groupby("patient_id")[fold_column].nunique().eq(1).all():
        raise ValueError("Each patient must map to exactly one outer fold")
    if not frame.groupby("patient_id")["omi"].nunique().eq(1).all():
        raise ValueError("Patient OMI status must be consistent across records")
    patient_frame = (
        frame[["patient_id", "omi", fold_column]]
        .groupby("patient_id", as_index=False)
        .agg(omi=("omi", "max"), fold=(fold_column, "first"))
    )
    outer = patient_frame[patient_frame.fold == outer_fold]
    training = patient_frame[patient_frame.fold != outer_fold]
    if set(outer.patient_id) & set(training.patient_id):
        raise RuntimeError("outer-fold patient leakage")
    fit, calibration = train_test_split(
        training,
        test_size=calibration_fraction,
        random_state=seed + 1000 + outer_fold,
        stratify=training.omi,
    )
    fit = fit.assign(inner_role="INNER_MODEL_FIT")
    calibration = calibration.assign(inner_role="INNER_THRESHOLD_CALIBRATION")
    outer = outer.assign(inner_role="OUTER_EVALUATION")
    roles = pd.concat([fit, calibration, outer], ignore_index=True)
    roles["outer_fold"] = int(outer_fold)
    return roles.sort_values(["inner_role", "patient_id"]).reset_index(drop=True)

