from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.data.dataset import finalization_split, load_processed, oof_folds, patient_training_weights
from src.evaluation.threshold import specificity_at_sensitivity
from src.models.cnn import TinyECGCNN
from src.utils.config import load_config, repository_path
from src.utils.logging import configure_logging
from src.utils.provenance import sha256, version_information, write_run_metadata


LOGGER = logging.getLogger(__name__)


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_model(
    waveforms: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
    channels: list[int],
    seed: int,
    training: dict,
) -> TinyECGCNN:
    seed_all(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TinyECGCNN(len(channels)).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=training["learning_rate"],
        weight_decay=training["weight_decay"],
    )
    dataset = TensorDataset(
        torch.from_numpy(waveforms[:, channels]).float(),
        torch.from_numpy(labels).float(),
        torch.from_numpy(weights).float(),
    )
    loader = DataLoader(
        dataset,
        batch_size=training["batch_size"],
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
        num_workers=0,
    )
    model.train()
    for epoch in range(training["epochs"]):
        for inputs, targets, sample_weights in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            sample_weights = sample_weights.to(device)
            loss = (
                nn.functional.binary_cross_entropy_with_logits(model(inputs), targets, reduction="none")
                * sample_weights
            ).sum() / sample_weights.sum()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        LOGGER.info("Completed epoch %d/%d", epoch + 1, training["epochs"])
    return model


def predict(model: TinyECGCNN, waveforms: np.ndarray, channels: list[int], batch_size: int) -> np.ndarray:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval().to(device)
    output = []
    with torch.no_grad():
        for start in range(0, len(waveforms), batch_size):
            inputs = torch.from_numpy(waveforms[start : start + batch_size][:, channels]).float().to(device)
            output.append(torch.sigmoid(model(inputs)).cpu().numpy())
    return np.concatenate(output)


def run_oof(config: dict) -> Path:
    frame, waveforms = load_processed(config, "train")
    base_seed = config["study"]["base_seed"]
    assignment = oof_folds(frame, config["training"]["folds"], base_seed)
    weights = patient_training_weights(frame)
    labels = frame.omi.to_numpy()
    channels = config["configuration"]["lead_indices"]
    position = config["configuration"]["position"]
    probabilities = np.full(len(frame), np.nan, dtype=float)
    for fold in range(config["training"]["folds"]):
        train_index = np.flatnonzero(assignment != fold)
        validation_index = np.flatnonzero(assignment == fold)
        seed = base_seed + fold + 100 * position
        LOGGER.info("Training %s fold %d with seed %d", config["configuration"]["id"], fold, seed)
        model = train_model(
            waveforms[train_index],
            labels[train_index],
            weights[train_index],
            channels,
            seed,
            config["training"],
        )
        probabilities[validation_index] = predict(
            model,
            waveforms[validation_index],
            channels,
            config["training"]["batch_size"],
        )
    output_dir = repository_path(config, "outputs") / "oof"
    output_dir.mkdir(parents=True, exist_ok=True)
    config_id = config["configuration"]["id"]
    output_path = output_dir / f"{config_id}_predictions.csv"
    pd.DataFrame(
        {
            "ecg_id": frame.ecg_id,
            "patient_id": frame.patient_id,
            "omi_label": labels,
            "fold": assignment,
            "configuration": config_id,
            "oof_probability": probabilities,
        }
    ).to_csv(output_path, index=False)
    split_path = output_dir / "patient_fold_assignment.csv"
    pd.DataFrame({"patient_id": frame.patient_id, "fold": assignment}).drop_duplicates().sort_values("patient_id").to_csv(split_path, index=False)
    write_run_metadata(
        output_dir / f"{config_id}_run_metadata.json",
        {"mode": "oof", "configuration": config_id, "base_seed": base_seed, "lead_indices": channels},
    )
    return output_path


def run_final(config: dict) -> Path:
    frame, waveforms = load_processed(config, "train")
    base_seed = config["study"]["base_seed"]
    fit = finalization_split(
        frame,
        config["training"]["final_calibration_fraction"],
        base_seed,
    )
    fit_frame = frame.loc[fit].copy()
    fit_waveforms = waveforms[fit]
    weights = patient_training_weights(fit_frame)
    channels = config["configuration"]["lead_indices"]
    config_id = config["configuration"]["id"]
    seed = base_seed + config["configuration"]["position"]
    model = train_model(
        fit_waveforms,
        fit_frame.omi.to_numpy(),
        weights,
        channels,
        seed,
        config["training"],
    )
    model_dir = repository_path(config, "models")
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = model_dir / f"{config_id}.pt"
    torch.save({"state_dict": model.state_dict(), "configuration": channels, "seed": seed}, checkpoint_path)
    calibration_probabilities = predict(
        model,
        waveforms[~fit],
        channels,
        config["training"]["batch_size"],
    )
    specificity, threshold, sensitivity = specificity_at_sensitivity(
        frame.loc[~fit, "omi"].to_numpy(),
        calibration_probabilities,
        config["evaluation"]["target_sensitivity"],
    )
    threshold_record = {
        "configuration": config_id,
        "seed": seed,
        "threshold": threshold,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "frozen_reference_threshold": config["evaluation"]["frozen_calibration_threshold"],
        "matches_frozen_reference": bool(np.isclose(threshold, config["evaluation"]["frozen_calibration_threshold"], rtol=0, atol=1e-12)),
        "checkpoint_sha256": sha256(checkpoint_path),
    }
    threshold_path = model_dir / f"{config_id}_threshold.json"
    threshold_path.write_text(json.dumps(threshold_record, indent=2) + "\n", encoding="utf-8")
    output_dir = repository_path(config, "outputs") / "finalization"
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"patient_id": frame.patient_id, "finalization_split": np.where(fit, "MODEL_FIT", "THRESHOLD_CALIBRATION")}).drop_duplicates().sort_values("patient_id").to_csv(output_dir / "patient_split.csv", index=False)
    write_run_metadata(
        output_dir / f"{config_id}_run_metadata.json",
        {"mode": "final", "configuration": config_id, "seed": seed, **threshold_record},
    )
    return checkpoint_path


def run_predict(config: dict) -> Path:
    frame, waveforms = load_processed(config, "test")
    config_id = config["configuration"]["id"]
    channels = config["configuration"]["lead_indices"]
    model_dir = repository_path(config, "models")
    checkpoint = torch.load(model_dir / f"{config_id}.pt", map_location="cpu", weights_only=False)
    model = TinyECGCNN(len(channels))
    model.load_state_dict(checkpoint["state_dict"])
    threshold_record = json.loads((model_dir / f"{config_id}_threshold.json").read_text(encoding="utf-8"))
    probabilities = predict(model, waveforms, channels, config["training"]["batch_size"])
    output_dir = repository_path(config, "outputs") / "heldout"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{config_id}_probabilities.csv"
    pd.DataFrame(
        {
            "ecg_row_record": frame.ecg_row_record,
            "probability": probabilities,
            "threshold": threshold_record["threshold"],
            "binary_prediction": (probabilities >= threshold_record["threshold"]).astype(int),
        }
    ).to_csv(output_path, index=False)
    required_submission_columns = {"ecg_row_record", "ecg_med_record"}
    if not required_submission_columns.issubset(frame.columns):
        raise ValueError(f"Held-out metadata missing columns: {sorted(required_submission_columns - set(frame.columns))}")
    pd.DataFrame(
        {
            "ecg_row_record": frame.ecg_row_record,
            "ecg_med_record": frame.ecg_med_record,
            "OMI": (probabilities >= threshold_record["threshold"]).astype(int),
        }
    ).to_csv(output_dir / f"{config_id}_binary_submission.csv", index=False)
    return output_path


def dry_run(config: dict) -> None:
    seed_all(config["study"]["base_seed"])
    channels = config["configuration"]["lead_indices"]
    model = TinyECGCNN(len(channels)).eval()
    synthetic = torch.zeros(2, len(channels), config["data"]["output_samples"])
    with torch.no_grad():
        output = model(synthetic)
    if output.shape != (2,) or not torch.isfinite(output).all():
        raise RuntimeError("Synthetic model forward pass failed")
    print(json.dumps({"status": "PASS", "configuration": config["configuration"]["id"], "input_shape": list(synthetic.shape), "output_shape": list(output.shape), "versions": version_information()}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train or apply the frozen ECG CNN")
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", choices=["oof", "final", "predict"], default="oof")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    configure_logging(args.verbose)
    config = load_config(args.config)
    if args.dry_run:
        dry_run(config)
        return
    output = {"oof": run_oof, "final": run_final, "predict": run_predict}[args.mode](config)
    LOGGER.info("Completed %s: %s", args.mode, output.relative_to(config["_repository_root"]))


if __name__ == "__main__":
    main()
