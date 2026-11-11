from __future__ import annotations
import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ECG-Lead-Information-OMI-Reproducibility"))
sys.path.insert(0, str(ROOT / "10_gate2_r2"))

from src.models.cnn import TinyECGCNN  # noqa: E402
from src.evaluation.threshold import specificity_at_sensitivity  # noqa: E402
from a2a_centering import center_config  # noqa: E402

CONFIGS = {"C0": list(range(12)), "C1": list(range(6)), "C2": list(range(6, 12)), "C3": [0, 1, 2]}
SEED_BASES = {"A": 20260813, "B": 20270313}
EPOCHS = 10
BATCH = 256
LR = 1e-3
WD = 1e-4
TARGET = 0.95


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def patient_weights(patient_ids: np.ndarray, labels: np.ndarray) -> np.ndarray:
    frame = pd.DataFrame({"p": patient_ids, "y": labels})
    counts = frame.groupby("p").size()
    base = frame["p"].map(1.0 / counts).to_numpy(dtype=float)
    prevalence = labels.mean()
    class_w = np.where(labels == 1, 1.0 / prevalence, 1.0 / (1.0 - prevalence))
    return base * class_w


def train_one(x, y, w, channels, seed, rows):
    """x is the full normalized array, shape (N, 12, 500); rows selects the fit set."""
    seed_all(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TinyECGCNN(len(channels)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    dataset = TensorDataset(
        torch.from_numpy(np.asarray(x[rows][:, channels])).float(),
        torch.from_numpy(np.asarray(y)).float(),
        torch.from_numpy(np.asarray(w)).float(),
    )
    loader = DataLoader(dataset, batch_size=BATCH, shuffle=True, generator=torch.Generator().manual_seed(seed), num_workers=0)
    model.train()
    losses = []
    for epoch in range(EPOCHS):
        total = 0.0
        n = 0
        for xb, yb, wb in loader:
            xb, yb, wb = xb.to(device), yb.to(device), wb.to(device)
            logits = model(xb)
            loss = (nn.functional.binary_cross_entropy_with_logits(logits, yb, reduction="none") * wb).sum() / wb.sum()
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss.detach().cpu()) * len(yb)
            n += len(yb)
        losses.append(total / n)
        print(f"  epoch {epoch+1}/{EPOCHS} loss={losses[-1]:.6f}", flush=True)
    return model, losses


def predict(model, x, channels):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval().to(device)
    out = []
    with torch.no_grad():
        for start in range(0, len(x), BATCH):
            xb = torch.from_numpy(np.asarray(x[start:start + BATCH][:, channels])).float().to(device)
            out.append(torch.sigmoid(model(xb)).cpu().numpy())
    return np.concatenate(out)


def normalize_per_lead_z(arr):
    med = np.nanmedian(arr, axis=2, keepdims=True)
    sd = np.nanstd(arr, axis=2, keepdims=True)
    return np.nan_to_num((arr - med) / np.maximum(sd, 1e-3), nan=0.0, posinf=0.0, neginf=0.0)


def normalize_a2a(arr, channels):
    z, _ = center_config(np.asarray(arr, dtype=np.float64), channels)
    # center_config returns only the selected channels; expand back into 12-channel layout.
    full = np.zeros_like(arr, dtype=np.float32)
    full[:, channels, :] = z.astype(np.float32)
    return full


def metrics(y, p, threshold):
    pred = p >= threshold
    tp = int(((y == 1) & pred).sum())
    fp = int(((y == 0) & pred).sum())
    tn = int(((y == 0) & ~pred).sum())
    fn = int(((y == 1) & ~pred).sum())
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "sensitivity": tp / max(tp + fn, 1),
        "specificity": tn / max(tn + fp, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", choices=["A1_seedA", "A1_seedB", "A2a"], required=True)
    ap.add_argument("--outer-fold", type=int, required=True)
    ap.add_argument("--config", choices=list(CONFIGS), required=True)
    ap.add_argument("--run-root", type=Path, required=True)
    if len(sys.argv) == 1:
        ap.print_help()
    args = ap.parse_args()

    started = time.time()
    metadata = pd.read_csv(ROOT / "02_data/metadata_raw/CSV/train.csv", dtype={"Patient_id": str})
    metadata["ecg_id"] = metadata.ecg_row_record.str.replace(".dat", "", regex=False).str.zfill(5)
    metadata = metadata[~metadata.ecg_id.isin(["03228", "14262"])].reset_index(drop=True)

    folds = pd.read_csv(ROOT / "03_results/gate_0e_oof_predictions.csv", dtype={"ecg_id": str, "patient_id": str})
    folds = folds.query("configuration=='C0'")[["ecg_id", "patient_id", "omi_label", "fold"]].copy()
    folds["ecg_id"] = folds.ecg_id.str.zfill(5)

    assignment = pd.read_csv(ROOT / "10_gate1_5_r2/INNER_SPLIT_ASSIGNMENT.csv", dtype={"patient_id": str})

    frame = metadata.merge(folds, on="ecg_id", how="left", validate="one_to_one", suffixes=("", "_oof"))
    if frame.omi_label.isna().any():
        raise RuntimeError("metadata/OOF join lost rows")
    if (frame.Patient_id != frame.patient_id).any():
        raise RuntimeError("patient mismatch")

    if args.analysis.startswith("A1"):
        seed_base = SEED_BASES["A" if args.analysis.endswith("seedA") else "B"]
        amp_path = ROOT / "10_gate2_r2/cache_amplitude_50hz.npy"
        mode = "A1"
    else:
        seed_base = SEED_BASES["A"]
        amp_path = ROOT / "10_gate2_r2/cache_amplitude_50hz.npy"
        mode = "A2a"

    amplitude = np.load(amp_path, mmap_mode="r")
    if mode == "A1":
        x = normalize_per_lead_z(np.asarray(amplitude, dtype=np.float32))
    else:
        x = normalize_a2a(amplitude, CONFIGS[args.config])

    role = assignment[assignment.outer_fold == args.outer_fold]
    if role.patient_id.duplicated().any():
        raise RuntimeError("duplicate patient role")

    fit_ids = set(role[role.inner_role == "INNER_MODEL_FIT"].patient_id)
    cal_ids = set(role[role.inner_role == "INNER_THRESHOLD_CALIBRATION"].patient_id)
    eval_ids = set(role[role.inner_role == "OUTER_EVALUATION"].patient_id)
    if fit_ids & cal_ids or fit_ids & eval_ids or cal_ids & eval_ids:
        raise RuntimeError("role leakage")

    # Assign roles on the combined frame, retaining global row positions for indexing x.
    frame = frame.assign(inner_role=None)
    frame.loc[frame.patient_id.isin(fit_ids), "inner_role"] = "INNER_MODEL_FIT"
    frame.loc[frame.patient_id.isin(cal_ids), "inner_role"] = "INNER_THRESHOLD_CALIBRATION"
    frame.loc[frame.patient_id.isin(eval_ids), "inner_role"] = "OUTER_EVALUATION"
    if frame.inner_role.isna().any():
        raise RuntimeError("unassigned role")
    if frame.inner_role.nunique() != 3:
        raise RuntimeError("role assignment incomplete")

    fit = frame[frame.inner_role == "INNER_MODEL_FIT"]
    cal = frame[frame.inner_role == "INNER_THRESHOLD_CALIBRATION"]
    ev = frame[frame.inner_role == "OUTER_EVALUATION"]
    expected_eval = frame[frame.fold == args.outer_fold]
    if set(ev.ecg_id) != set(expected_eval.ecg_id):
        raise RuntimeError("outer evaluation set mismatch")
    if set(fit.patient_id) & set(cal.patient_id) or set(fit.patient_id) & set(ev.patient_id) or set(cal.patient_id) & set(ev.patient_id):
        raise RuntimeError("patient role leakage")

    pos = list(CONFIGS).index(args.config)
    seed = seed_base + args.outer_fold + 100 * pos
    channels = CONFIGS[args.config]

    y_fit = fit.omi_label.to_numpy(dtype=int)
    w_fit = patient_weights(fit.patient_id.to_numpy(), y_fit)
    fit_rows = fit.index.to_numpy()
    cal_rows = cal.index.to_numpy()
    ev_rows = ev.index.to_numpy()
    if len(set(fit_rows) & set(cal_rows)) or len(set(fit_rows) & set(ev_rows)) or len(set(cal_rows) & set(ev_rows)):
        raise RuntimeError("row leakage")
    model, losses = train_one(x, y_fit, w_fit, channels, seed, fit_rows)
    p_cal = predict(model, x[cal_rows], channels)
    y_cal = cal.omi_label.to_numpy(dtype=int)
    spec_cal, threshold, sens_cal = specificity_at_sensitivity(y_cal, p_cal, TARGET)
    if not np.isfinite(threshold):
        raise RuntimeError("threshold selection failed")
    p_ev = predict(model, x[ev_rows], channels)
    y_ev = ev.omi_label.to_numpy(dtype=int)
    out = metrics(y_ev, p_ev, threshold)

    out.update({
        "analysis": args.analysis, "outer_fold": args.outer_fold, "configuration": args.config,
        "seed": seed, "threshold_locked": threshold,
        "calibration_specificity": spec_cal, "calibration_sensitivity": sens_cal,
        "n_fit_patients": len(fit_ids), "n_cal_patients": len(cal_ids), "n_eval_patients": len(eval_ids),
        "n_fit_ecg": len(fit), "n_cal_ecg": len(cal), "n_eval_ecg": len(ev),
        "n_eval_omi_ecg": int(y_ev.sum()), "n_eval_non_omi_ecg": int((y_ev == 0).sum()),
        "elapsed_seconds": time.time() - started, "losses": "|".join(f"{v:.8f}" for v in losses),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    })

    run_dir = args.run_root / f"fold{args.outer_fold}" / args.analysis
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([out]).to_csv(run_dir / f"{args.config}_metrics.csv", index=False)
    pd.DataFrame({"ecg_id": ev.ecg_id, "patient_id": ev.patient_id, "omi_label": y_ev,
                  "probability": p_ev, "threshold": threshold}).to_csv(run_dir / f"{args.config}_eval_predictions.csv", index=False)
    torch.save({"state_dict": model.state_dict(), "configuration": channels, "seed": seed},
               run_dir / f"{args.config}_model.pt")
    print(json.dumps({k: (float(v) if isinstance(v, (np.floating,)) else v) for k, v in out.items() if k != "losses"}), flush=True)


if __name__ == "__main__":
    main()
