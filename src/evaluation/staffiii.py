from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import resample_poly
import torch
import wfdb

from src.models.cnn import TinyECGCNN
from src.training.train import predict
from src.utils.config import load_config, repository_path
from src.utils.logging import configure_logging
from src.utils.provenance import write_run_metadata


LOGGER = logging.getLogger(__name__)
PRIMARY_CONFIGS = ["C0", "C1", "C2", "C3"]
CONFIG_FILES = {
    "C0": "c0_12lead.yaml",
    "C1": "c1_limb.yaml",
    "C2": "c2_precordial.yaml",
    "C3": "c3_i_ii_iii.yaml",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_record_id(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    match = re.fullmatch(r"(\d+)([a-z])", text)
    return match.group(1).zfill(3) + match.group(2) if match else text


def parse_timing(value: object) -> dict[str, float] | None:
    if pd.isna(value):
        return None
    try:
        parts = [float(item) for item in str(value).split(";")]
    except ValueError:
        return None
    if len(parts) != 3:
        return None
    return {"start": parts[0], "duration": parts[1], "tail": parts[2]}


def artery_territory(value: object) -> str:
    text = str(value).lower()
    if "lad" in text:
        return "LAD"
    if "rca" in text:
        return "RCA"
    if "circ" in text or "lcx" in text:
        return "LCx"
    if "lm" in text or "left main" in text:
        return "LM"
    return "OTHER"


def contrast_contaminated(value: object) -> bool:
    if pd.isna(value):
        return False
    try:
        return any(55 <= float(item) <= 75 for item in str(value).split(";"))
    except ValueError:
        return True


def verify_provider_files(data_dir: Path) -> pd.DataFrame:
    checksum_path = data_dir / "SHA256SUMS.txt"
    if not checksum_path.exists():
        LOGGER.warning("Provider checksum file is absent; skipping STAFF III hash verification")
        return pd.DataFrame(columns=["relative_path", "expected_sha256", "status"])
    rows = []
    for line in checksum_path.read_text(encoding="ascii").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        expected, relative = parts
        path = data_dir / relative
        status = "PASS" if path.exists() and sha256(path) == expected else ("MISSING" if not path.exists() else "FAIL")
        rows.append({"relative_path": relative, "expected_sha256": expected, "status": status})
    audit = pd.DataFrame(rows)
    critical = audit[
        (audit.relative_path == "RECORDS")
        | audit.relative_path.str.startswith("data/")
        | (audit.relative_path == "STAFF-III-Database-Annotations.xlsx")
    ]
    if len(critical) and not (critical.status == "PASS").all():
        raise RuntimeError("STAFF III provider checksum verification failed")
    records_path = data_dir / "RECORDS"
    if records_path.exists():
        expected_records = {Path(item.strip()).name for item in records_path.read_text().splitlines() if item.strip()}
        actual_records = {str(path.relative_to(data_dir / "data").with_suffix("")) for path in (data_dir / "data").rglob("*.hea")}
        if expected_records != actual_records:
            raise RuntimeError("STAFF III RECORDS/header inventory mismatch")
    return audit


def select_events(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_excel(data_dir / "STAFF-III-Database-Annotations.xlsx", header=None)
    annotations = []
    selected = []
    for _, row in raw.iloc[10:].iterrows():
        patient_raw = row.iloc[0]
        if pd.isna(patient_raw):
            continue
        try:
            patient_id = str(int(float(patient_raw)))
        except (TypeError, ValueError):
            continue
        baseline = normalized_record_id(row.iloc[3])
        patient_events = []
        columns = [(6, 7, 8, 9), (10, 11, 12, 13), (14, 15, 16, 17), (18, 19, 20, None), (21, 22, 23, None)]
        for inflation_number, (record_col, artery_col, timing_col, injection_col) in enumerate(columns, 1):
            record_id = normalized_record_id(row.iloc[record_col])
            timing = parse_timing(row.iloc[timing_col])
            quality = "EXCLUDE_PRIMARY"
            reason = ""
            if record_id and timing and timing["duration"] >= 90 and baseline:
                quality = "CLEAR"
                reason = "first-line spreadsheet timing"
                if injection_col is not None and contrast_contaminated(row.iloc[injection_col]):
                    quality = "EXCLUDE_PRIMARY"
                    reason = "contrast within 55-75s after inflation"
            if record_id and not (data_dir / "data" / f"{record_id}.hea").exists():
                quality = "EXCLUDE_PRIMARY"
                reason = "missing record"
            event = {
                "patient_id": patient_id,
                "record_id": record_id,
                "measurement_type": f"BI{inflation_number}",
                "artery_raw": normalized_record_id(row.iloc[artery_col]),
                "artery": artery_territory(row.iloc[artery_col]),
                "inflation_number": inflation_number,
                "inflation_start": timing["start"] if timing else None,
                "inflation_end": timing["start"] + timing["duration"] if timing else None,
                "inflation_duration": timing["duration"] if timing else None,
                "contrast_injection": normalized_record_id(row.iloc[injection_col]) if injection_col is not None else None,
                "baseline_record": baseline,
                "annotation_source": "official XLSX",
                "annotation_quality": quality,
                "reason": reason,
            }
            annotations.append(event)
            patient_events.append(event)
        candidates = [event for event in patient_events if event["annotation_quality"] == "CLEAR"]
        if candidates:
            event = sorted(candidates, key=lambda item: item["inflation_number"])[0].copy()
            event.update(
                {
                    "selected": True,
                    "baseline_window_start": 60,
                    "occlusion_window_start": event["inflation_start"] + 60,
                    "selection_rule": "first CLEAR BI1-BI5; duration >=90s; baseline BR; no primary contrast 55-75s",
                }
            )
            selected.append(event)
    return pd.DataFrame(annotations), pd.DataFrame(selected)


def read_window(data_dir: Path, record: str, start_seconds: float, scale_floor: float) -> tuple[np.ndarray, list[str]]:
    source = wfdb.rdrecord(
        str(data_dir / "data" / record),
        sampfrom=int(round(start_seconds * 1000)),
        sampto=int(round((start_seconds + 10) * 1000)),
    )
    if source.fs != 1000 or source.p_signal.shape[0] != 10000:
        raise ValueError("Unexpected STAFF III sampling rate or window length")
    names = [str(name) for name in source.sig_name]
    canonical = {name.lower().replace(" ", ""): index for index, name in enumerate(names)}
    required = ["i", "ii", "iii", "v1", "v2", "v3", "v4", "v5", "v6"]
    if not all(name in canonical for name in required):
        raise ValueError("Missing required STAFF III measured lead")
    raw = np.asarray(source.p_signal, dtype=np.float32)
    lead_i = raw[:, canonical["i"]]
    lead_ii = raw[:, canonical["ii"]]
    signal = np.vstack(
        [
            lead_i,
            lead_ii,
            raw[:, canonical["iii"]],
            -(lead_i + lead_ii) / 2,
            lead_i - lead_ii / 2,
            lead_ii - lead_i / 2,
            raw[:, canonical["v1"]],
            raw[:, canonical["v2"]],
            raw[:, canonical["v3"]],
            raw[:, canonical["v4"]],
            raw[:, canonical["v5"]],
            raw[:, canonical["v6"]],
        ]
    )
    reduced = resample_poly(signal, up=1, down=2, axis=1).reshape(12, 500, 10).mean(axis=2)
    median = np.nanmedian(reduced, axis=1, keepdims=True)
    scale = np.nanstd(reduced, axis=1, keepdims=True)
    normalized = np.nan_to_num((reduced - median) / np.maximum(scale, scale_floor), nan=0.0, posinf=0.0, neginf=0.0)
    return normalized.astype(np.float32, copy=False), names


def load_models(config: dict) -> tuple[dict[str, TinyECGCNN], dict[str, list[int]]]:
    config_dir = config["_repository_root"] / "configs"
    model_dir = repository_path(config, "models")
    models = {}
    channels = {}
    for config_id in PRIMARY_CONFIGS:
        specific = load_config(config_dir / CONFIG_FILES[config_id])
        channels[config_id] = specific["configuration"]["lead_indices"]
        state = torch.load(model_dir / f"{config_id}.pt", map_location="cpu", weights_only=False)
        model = TinyECGCNN(len(channels[config_id]))
        model.load_state_dict(state["state_dict"])
        models[config_id] = model
    return models, channels


def model_scores(models: dict[str, TinyECGCNN], channels: dict[str, list[int]], signal: np.ndarray, batch_size: int) -> dict[str, float]:
    return {config_id: float(predict(model, signal[None, :, :], channels[config_id], batch_size)[0]) for config_id, model in models.items()}


def logit(probability: float, epsilon: float) -> float:
    clipped = np.clip(probability, epsilon, 1 - epsilon)
    return float(np.log(clipped / (1 - clipped)))


def bootstrap_summary(values: np.ndarray, seed: int, replicates: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    medians = []
    concordances = []
    for _ in range(replicates):
        sample = values[rng.integers(0, len(values), len(values))]
        medians.append(np.median(sample))
        concordances.append(np.mean(sample > 0))
    return np.quantile(medians, [0.025, 0.975]), np.quantile(concordances, [0.025, 0.975])


def paired_concordance_bootstrap(baseline: np.ndarray, comparison: np.ndarray, seed: int, replicates: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    differences = []
    for _ in range(replicates):
        index = rng.integers(0, len(baseline), len(baseline))
        differences.append(np.mean(comparison[index]) - np.mean(baseline[index]))
    return np.quantile(differences, [0.025, 0.975])


def run(config: dict) -> None:
    data_dir = repository_path(config, "staffiii")
    output_dir = repository_path(config, "outputs") / "staffiii"
    output_dir.mkdir(parents=True, exist_ok=True)
    hash_audit = verify_provider_files(data_dir)
    hash_audit.to_csv(output_dir / "provider_hash_audit.csv", index=False)
    annotations, selected = select_events(data_dir)
    annotations.to_csv(output_dir / "annotation_audit.csv", index=False)
    selected.to_csv(output_dir / "selected_events.csv", index=False)
    models, channels = load_models(config)
    scores = []
    excluded = []
    for event in selected.to_dict("records"):
        try:
            baseline, baseline_names = read_window(data_dir, event["baseline_record"], 60, config["data"]["scale_floor"])
            occlusion, occlusion_names = read_window(data_dir, event["record_id"], event["inflation_start"] + 60, config["data"]["scale_floor"])
            if baseline_names != occlusion_names:
                raise ValueError("Lead-order mismatch")
            baseline_scores = model_scores(models, channels, baseline, config["training"]["batch_size"])
            occlusion_scores = model_scores(models, channels, occlusion, config["training"]["batch_size"])
            for config_id in PRIMARY_CONFIGS:
                scores.append(
                    {
                        "patient_id": event["patient_id"],
                        "record_id": event["record_id"],
                        "artery": event["artery"],
                        "configuration": config_id,
                        "p_baseline": baseline_scores[config_id],
                        "p_occlusion": occlusion_scores[config_id],
                        "baseline_window_start": 60,
                        "occlusion_window_start": event["inflation_start"] + 60,
                        "lead_mapping": "measured I,II,III,V1-V6; derived aVR=-(I+II)/2,aVL=I-II/2,aVF=II-I/2",
                    }
                )
        except Exception as error:
            excluded.append({"patient_id": event["patient_id"], "record_id": event["record_id"], "reason": str(error)})
    score_frame = pd.DataFrame(scores)
    if score_frame.empty:
        raise RuntimeError("No STAFF III events were scored")
    epsilon = config["evaluation"]["probability_clip_epsilon"]
    score_frame["delta_probability"] = score_frame.p_occlusion - score_frame.p_baseline
    score_frame["delta_logit"] = score_frame.apply(lambda row: logit(row.p_occlusion, epsilon) - logit(row.p_baseline, epsilon), axis=1)
    score_frame.to_csv(output_dir / "within_patient_scores.csv", index=False)
    if excluded:
        pd.DataFrame(excluded).to_csv(output_dir / "scoring_exclusions.csv", index=False)
    seed = config["study"]["base_seed"]
    replicates = config["evaluation"]["bootstrap_replicates"]
    wide = score_frame.pivot(index="patient_id", columns="configuration", values="delta_logit").reset_index()
    baseline_positive = (wide.C0.to_numpy() > 0).astype(float)
    summary = []
    for config_id in PRIMARY_CONFIGS:
        values = wide[config_id].to_numpy()
        median_interval, concordance_interval = bootstrap_summary(values, seed, replicates)
        concordance = float(np.mean(values > 0))
        if config_id == "C0":
            difference = None
            difference_interval = [None, None]
        else:
            comparison_positive = (values > 0).astype(float)
            difference = float(np.mean(comparison_positive) - np.mean(baseline_positive))
            difference_interval = paired_concordance_bootstrap(baseline_positive, comparison_positive, seed + 91, replicates)
        summary.append(
            {
                "configuration": config_id,
                "n_patients": len(values),
                "median_delta_logit": float(np.median(values)),
                "delta_logit_ci_low": median_interval[0],
                "delta_logit_ci_high": median_interval[1],
                "positive_shift_concordance": concordance,
                "concordance_ci_low": concordance_interval[0],
                "concordance_ci_high": concordance_interval[1],
                "delta_concordance_vs_C0": difference,
                "delta_concordance_ci_low": difference_interval[0],
                "delta_concordance_ci_high": difference_interval[1],
            }
        )
    pd.DataFrame(summary).to_csv(output_dir / "configuration_summary.csv", index=False)
    territory_rows = []
    for artery in ["LAD", "RCA", "LCx", "LM"]:
        for config_id in PRIMARY_CONFIGS:
            subset = score_frame[(score_frame.artery == artery) & (score_frame.configuration == config_id)]
            if len(subset):
                territory_rows.append(
                    {
                        "territory": artery,
                        "configuration": config_id,
                        "n_patients": subset.patient_id.nunique(),
                        "median_delta_logit": float(subset.delta_logit.median()),
                        "positive_shift_concordance": float((subset.delta_logit > 0).mean()),
                    }
                )
    pd.DataFrame(territory_rows).to_csv(output_dir / "territory_summary.csv", index=False)
    threshold_rows = []
    model_dir = repository_path(config, "models")
    for config_id in PRIMARY_CONFIGS:
        threshold_path = model_dir / f"{config_id}_threshold.json"
        if not threshold_path.exists():
            continue
        threshold = json.loads(threshold_path.read_text(encoding="utf-8"))["threshold"]
        subset = score_frame[score_frame.configuration == config_id]
        threshold_rows.append(
            {
                "configuration": config_id,
                "n_patients": subset.patient_id.nunique(),
                "baseline_positive_fraction": float((subset.p_baseline >= threshold).mean()),
                "occlusion_positive_fraction": float((subset.p_occlusion >= threshold).mean()),
                "threshold": threshold,
                "analysis_role": "secondary domain-shift stress test",
            }
        )
    pd.DataFrame(threshold_rows).to_csv(output_dir / "frozen_threshold_stress_test.csv", index=False)
    write_run_metadata(
        output_dir / "staffiii_run_metadata.json",
        {"selected_events": len(selected), "scored_patients": int(score_frame.patient_id.nunique()), "excluded": excluded, "bootstrap_replicates": replicates},
    )
    LOGGER.info("STAFF III analysis complete for %d patients", score_frame.patient_id.nunique())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen STAFF III controlled-occlusion analysis")
    parser.add_argument("--config", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    configure_logging(args.verbose)
    run(load_config(args.config))


if __name__ == "__main__":
    main()
