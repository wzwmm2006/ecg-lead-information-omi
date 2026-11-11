"""A2a-only integrated executor.

Authorized scope: 20 fits = C0-C3 x 5 outer folds x Seed A.
No A1 fitting. No hidden TEST. No STAFF III. No manuscript or repository change.

Frozen design:
  * pre-centring finite replacement (NaN/Inf -> 0 mV) using only configuration leads
  * fixed 1 mV scale
  * patient-grouped inner split from INNER_SPLIT_ASSIGNMENT.csv
  * frozen architecture, optimizer, epochs, batch size, threshold rule
  * per-batch ECG IDs
  * first non-finite input/logit/loss/gradient -> HALT before optimizer.step()
  * training-mode BatchNorm running statistics are snapshotted per epoch; if a
    HALT occurs after any BatchNorm update, the in-memory model is discarded and
    no checkpoint/metrics are written.
"""
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
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
GATE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "ECG-Lead-Information-OMI-Reproducibility"))
sys.path.insert(0, str(GATE.parent / "10_gate2_a2a_repair"))

from src.models.cnn import TinyECGCNN  # noqa: E402
from src.evaluation.threshold import specificity_at_sensitivity  # noqa: E402
from A2A_PRECENTER_FINITE_IMPLEMENTATION import center_config_precenter  # noqa: E402

CONFIGS = {"C0": list(range(12)), "C1": list(range(6)), "C2": list(range(6, 12)), "C3": [0, 1, 2]}
SEED_BASE = 20260813
EPOCHS = 10
BATCH = 256
LR = 1e-3
WD = 1e-4
TARGET = 0.95


class NonFiniteHalt(RuntimeError):
    pass


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


def _check(name, tensor, batch_index, ecg_ids):
    if not torch.isfinite(tensor).all():
        raise NonFiniteHalt(f"{name} non-finite at batch {batch_index}; ecg_ids={ecg_ids}")


def _bn_state(model):
    return {k: v.detach().clone() for k, v in model.state_dict().items() if "running_" in k or "num_batches" in k}


def train_one(x, y, w, channels, seed, rows, ecg_ids):
    seed_all(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TinyECGCNN(len(channels)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    xb_all = torch.from_numpy(np.asarray(x[rows][:, channels])).float()
    yb_all = torch.from_numpy(np.asarray(y)).float()
    wb_all = torch.from_numpy(np.asarray(w)).float()
    loader = DataLoader(
        list(zip(xb_all, yb_all, wb_all, list(ecg_ids))),
        batch_size=BATCH, shuffle=True, generator=torch.Generator().manual_seed(seed), num_workers=0,
    )
    model.train()
    losses = []
    epoch_finite = True
    for epoch in range(EPOCHS):
        total = 0.0
        n = 0
        bn_before_epoch = _bn_state(model)
        for batch_index, (xb, yb, wb, ids) in enumerate(loader):
            batch_ids = list(ids)
            xb, yb, wb = xb.to(device), yb.to(device), wb.to(device)
            _check("input", xb, batch_index, batch_ids)
            logits = model(xb)
            _check("logit", logits, batch_index, batch_ids)
            loss = (nn.functional.binary_cross_entropy_with_logits(logits, yb, reduction="none") * wb).sum() / wb.sum()
            _check("loss", loss, batch_index, batch_ids)
            opt.zero_grad()
            loss.backward()
            for name, param in model.named_parameters():
                if param.grad is not None:
                    _check(f"gradient:{name}", param.grad, batch_index, batch_ids)
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


def metrics(y, p, threshold):
    pred = p >= threshold
    tp = int(((y == 1) & pred).sum())
    fp = int(((y == 0) & pred).sum())
    tn = int(((y == 0) & ~pred).sum())
    fn = int(((y == 1) & ~pred).sum())
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "sensitivity": tp / max(tp + fn, 1), "specificity": tn / max(tn + fp, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outer-fold", type=int, required=True, choices=range(5))
    ap.add_argument("--config", required=True, choices=list(CONFIGS))
    ap.add_argument("--run-root", type=Path, required=True)
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

    amplitude = np.load(ROOT / "10_gate2_r2/cache_amplitude_50hz.npy", mmap_mode="r")
    channels = CONFIGS[args.config]
    z = center_config_precenter(amplitude, channels)["z"]
    full = np.zeros_like(amplitude, dtype=np.float32)
    full[:, channels, :] = z.astype(np.float32)
    if not np.isfinite(full).all():
        raise RuntimeError("non-finite normalized input")

    role = assignment[assignment.outer_fold == args.outer_fold]
    if role.patient_id.duplicated().any():
        raise RuntimeError("duplicate patient role")
    fit_ids = set(role[role.inner_role == "INNER_MODEL_FIT"].patient_id)
    cal_ids = set(role[role.inner_role == "INNER_THRESHOLD_CALIBRATION"].patient_id)
    eval_ids = set(role[role.inner_role == "OUTER_EVALUATION"].patient_id)
    if fit_ids & cal_ids or fit_ids & eval_ids or cal_ids & eval_ids:
        raise RuntimeError("role leakage")

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
    seed = SEED_BASE + args.outer_fold + 100 * pos

    y_fit = fit.omi_label.to_numpy(dtype=int)
    w_fit = patient_weights(fit.patient_id.to_numpy(), y_fit)
    fit_rows = fit.index.to_numpy()
    cal_rows = cal.index.to_numpy()
    ev_rows = ev.index.to_numpy()
    if len(set(fit_rows) & set(cal_rows)) or len(set(fit_rows) & set(ev_rows)) or len(set(cal_rows) & set(ev_rows)):
        raise RuntimeError("row leakage")

    model, losses = train_one(z[fit_rows], y_fit, w_fit, list(range(len(channels))), seed, np.arange(len(fit_rows)), fit.ecg_id.to_numpy(dtype=str))
    p_cal = predict(model, z[cal_rows], list(range(len(channels))))
    y_cal = cal.omi_label.to_numpy(dtype=int)
    spec_cal, threshold, sens_cal = specificity_at_sensitivity(y_cal, p_cal, TARGET)
    if not np.isfinite(threshold):
        raise RuntimeError("threshold selection failed")
    p_ev = predict(model, z[ev_rows], list(range(len(channels))))
    y_ev = ev.omi_label.to_numpy(dtype=int)
    out = metrics(y_ev, p_ev, threshold)
    out.update({
        "analysis": "A2a", "outer_fold": args.outer_fold, "configuration": args.config,
        "seed": seed, "threshold_locked": threshold,
        "calibration_specificity": spec_cal, "calibration_sensitivity": sens_cal,
        "n_fit_patients": len(fit_ids), "n_cal_patients": len(cal_ids), "n_eval_patients": len(eval_ids),
        "n_fit_ecg": len(fit), "n_cal_ecg": len(cal), "n_eval_ecg": len(ev),
        "n_eval_omi_ecg": int(y_ev.sum()), "n_eval_non_omi_ecg": int((y_ev == 0).sum()),
        "elapsed_seconds": time.time() - started, "losses": "|".join(f"{v:.8f}" for v in losses),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    })
    run_dir = args.run_root / f"fold{args.outer_fold}" / "A2a"
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([out]).to_csv(run_dir / f"{args.config}_metrics.csv", index=False)
    pd.DataFrame({"ecg_id": ev.ecg_id, "patient_id": ev.patient_id, "omi_label": y_ev,
                  "probability": p_ev, "threshold": threshold}).to_csv(run_dir / f"{args.config}_eval_predictions.csv", index=False)
    torch.save({"state_dict": model.state_dict(), "configuration": list(channels), "seed": seed},
               run_dir / f"{args.config}_model.pt")
    print(json.dumps({k: (float(v) if isinstance(v, np.floating) else v) for k, v in out.items() if k != "losses"}), flush=True)


if __name__ == "__main__":
    main()
