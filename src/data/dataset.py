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

