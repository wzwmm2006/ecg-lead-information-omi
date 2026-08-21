from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb

from src.utils.config import load_config, repository_path
from src.utils.logging import configure_logging


LOGGER = logging.getLogger(__name__)
CANONICAL_LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]


def record_id(value: object) -> str:
    return Path(str(value)).stem.zfill(5)


def downsample_and_normalize(signal: np.ndarray, output_samples: int = 500, scale_floor: float = 1e-3) -> np.ndarray:
    """Apply the frozen clinical 500-to-50-Hz reduction and normalization."""
    signal = np.asarray(signal, dtype=np.float32)
    if signal.shape != (12, 5000):
        raise ValueError(f"Expected signal shape (12, 5000), received {signal.shape}")
    reduced = signal.reshape(12, output_samples, 5000 // output_samples).mean(axis=2)
    median = np.nanmedian(reduced, axis=1, keepdims=True)
    scale = np.nanstd(reduced, axis=1, keepdims=True)
    normalized = (reduced - median) / np.maximum(scale, scale_floor)
    return np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)


def prepare_metadata(metadata_path: Path, split: str, excluded: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(metadata_path)
    if "ecg_row_record" not in frame:
        raise ValueError("Metadata must contain ecg_row_record")
    frame["ecg_id"] = frame["ecg_row_record"].map(record_id)
    if split == "train":
        frame = frame[~frame.ecg_id.isin(excluded)].reset_index(drop=True)
    return frame


def preprocess(config: dict, split: str) -> tuple[Path, Path]:
    metadata_path = repository_path(config, f"{split}_metadata")
    output_path = repository_path(config, f"processed_{split}")
    waveform_dir = repository_path(config, "clinical_waveforms")
    excluded = set(config["data"]["excluded_train_records"])
    frame = prepare_metadata(metadata_path, split, excluded)
    output = np.empty((len(frame), 12, config["data"]["output_samples"]), dtype=np.float32)
    for index, ecg_id in enumerate(frame.ecg_id):
        record = wfdb.rdrecord(str(waveform_dir / ecg_id))
        if float(record.fs) != float(config["data"]["sampling_rate_hz"]):
            raise ValueError(f"{ecg_id}: expected 500 Hz, received {record.fs}")
        signal = np.asarray(record.p_signal, dtype=np.float32).T
        output[index] = downsample_and_normalize(
            signal,
            output_samples=config["data"]["output_samples"],
            scale_floor=config["data"]["scale_floor"],
        )
        if (index + 1) % 1000 == 0:
            LOGGER.info("Loaded %d/%d waveforms", index + 1, len(frame))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, output)
    index_path = output_path.with_suffix(".index.csv")
    frame[["ecg_id"]].to_csv(index_path, index=False)
    LOGGER.info("Wrote %s and %s", output_path.relative_to(config["_repository_root"]), index_path.relative_to(config["_repository_root"]))
    return output_path, index_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess authorized clinical ECG waveforms")
    parser.add_argument("--config", required=True)
    parser.add_argument("--split", choices=["train", "test"], required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    configure_logging(args.verbose)
    preprocess(load_config(args.config), args.split)


if __name__ == "__main__":
    main()

