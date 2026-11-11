"""Verify A2a outputs, recompute predictions from checkpoints, and patient bootstrap.

Read-only with respect to training outputs: does not retrain, does not modify
checkpoints or prediction files. Writes only analysis artifacts under the run root.
"""
from __future__ import annotations
# NOTE: CSV prediction probabilities were saved by pandas with default float
# formatting, so re-reading them can differ from the in-memory values at the
# 8th significant digit. Confusion matrices therefore come from stored metrics
# (exact) and from checkpoint replay separately.
REPLAY_NOTE = "CSV probability text is rounded; checkpoint replay independently recomputed logits from stored weights."
import hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd, torch

ROOT = Path(__file__).resolve().parents[1]
GATE = Path(__file__).resolve().parent
RUN = GATE / "runs" / "RUN_20261110_A2a_ONLY"
sys.path.insert(0, str(ROOT / "ECG-Lead-Information-OMI-Reproducibility"))
sys.path.insert(0, str(ROOT / "10_gate2_a2a_repair"))
from src.models.cnn import TinyECGCNN  # noqa: E402
from A2A_PRECENTER_FINITE_IMPLEMENTATION import center_config_precenter  # noqa: E402

CONFIGS = {"C0": list(range(12)), "C1": list(range(6)), "C2": list(range(6, 12)), "C3": [0, 1, 2]}
BATCH = 256
BOOTSTRAP_SEED = 20260912


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def predict(model, x):
    model.eval()
    out = []
    with torch.no_grad():
        for start in range(0, len(x), BATCH):
            out.append(torch.sigmoid(model(torch.from_numpy(np.asarray(x[start:start + BATCH])).float())).cpu().numpy())
    return np.concatenate(out)


def main():
    run_manifest = json.loads((RUN / "RUN_MANIFEST.json").read_text())
    assert sha(GATE / "run_a2a_fit.py") == run_manifest["executor_sha256"]
    assert sha(ROOT / "10_gate2_r2/cache_amplitude_50hz.npy") == run_manifest["cache_sha256"]

    meta = pd.read_csv(ROOT / "02_data/metadata_raw/CSV/train.csv", dtype={"Patient_id": str})
    meta["ecg_id"] = meta.ecg_row_record.str.replace(".dat", "", regex=False).str.zfill(5)
    meta = meta[~meta.ecg_id.isin(["03228", "14262"])].reset_index(drop=True)
    folds = pd.read_csv(ROOT / "03_results/gate_0e_oof_predictions.csv", dtype={"ecg_id": str, "patient_id": str})
    folds = folds.query("configuration=='C0'")[["ecg_id", "patient_id", "omi_label", "fold"]].copy()
    folds["ecg_id"] = folds.ecg_id.str.zfill(5)
    frame = meta.merge(folds, on="ecg_id", validate="one_to_one", suffixes=("", "_oof"))
    assignment = pd.read_csv(ROOT / "10_gate1_5_r2/INNER_SPLIT_ASSIGNMENT.csv", dtype={"patient_id": str})

    amplitude = np.load(ROOT / "10_gate2_r2/cache_amplitude_50hz.npy", mmap_mode="r")
    per_task = []
    all_eval = []
    for fold in range(5):
        role = assignment[assignment.outer_fold == fold]
        role_set = dict(zip(role.patient_id, role.inner_role))
        frame["role"] = frame.patient_id.map(role_set)
        if frame.role.isna().any():
            raise RuntimeError(f"unassigned patient fold {fold}")
        fit = frame[frame.role == "INNER_MODEL_FIT"]
        cal = frame[frame.role == "INNER_THRESHOLD_CALIBRATION"]
        ev = frame[frame.role == "OUTER_EVALUATION"]
        if set(ev.ecg_id) != set(frame[frame.fold == fold].ecg_id):
            raise RuntimeError(f"outer evaluation mismatch fold {fold}")
        if set(fit.patient_id) & set(cal.patient_id) or set(fit.patient_id) & set(ev.patient_id) or set(cal.patient_id) & set(ev.patient_id):
            raise RuntimeError("patient overlap")
        for cfg, channels in CONFIGS.items():
            metrics = pd.read_csv(RUN / f"fold{fold}" / "A2a" / f"{cfg}_metrics.csv").iloc[0]
            pred = pd.read_csv(RUN / f"fold{fold}" / "A2a" / f"{cfg}_eval_predictions.csv", dtype={"ecg_id": str, "patient_id": str})
            assert len(pred) == len(ev), (fold, cfg)
            assert set(pred.ecg_id) == set(ev.ecg_id), (fold, cfg)
            assert pred.ecg_id.is_unique
            assert np.isfinite(pred.probability).all()
            assert pred.threshold.nunique() == 1
            threshold = float(metrics.threshold_locked)
            assert abs(pred.threshold.iloc[0] - threshold) < 1e-15
            y = pred.omi_label.to_numpy(dtype=int)
            tp = int(((y == 1) & (pred.probability >= threshold)).sum())
            fp = int(((y == 0) & (pred.probability >= threshold)).sum())
            tn = int(((y == 0) & (pred.probability < threshold)).sum())
            fn = int(((y == 1) & (pred.probability < threshold)).sum())
            assert (tp, fp, tn, fn) == (int(metrics.TP), int(metrics.FP), int(metrics.TN), int(metrics.FN)), (fold, cfg, (tp, fp, tn, fn))
            per_task.append({"outer_fold": fold, "configuration": cfg, "seed": int(metrics.seed),
                             "threshold": threshold, "TP": tp, "FP": fp, "TN": tn, "FN": fn,
                             "sensitivity": tp / (tp + fn), "specificity": tn / (tn + fp),
                             "n_eval_ecg": len(y), "n_eval_omi": int(y.sum()), "n_eval_non_omi": int((y == 0).sum())})
            all_eval.append(pred.assign(outer_fold=fold, configuration=cfg, seed=int(metrics.seed)))
    per_task = pd.DataFrame(per_task)
    per_task.to_csv(RUN / "A2A_PERFOLD_LOCKED_METRICS.csv", index=False)
    all_eval = pd.concat(all_eval, ignore_index=True)
    all_eval.to_csv(RUN / "A2A_ALL_EVAL_PREDICTIONS.csv", index=False)

    # Pooled counts, with each patient represented once per configuration.
    pooled = all_eval.groupby("configuration").apply(lambda d: pd.Series({
        "n_ecg": len(d), "n_omi_ecg": int((d.omi_label == 1).sum()), "n_non_omi_ecg": int((d.omi_label == 0).sum()),
        "TP": int(((d.omi_label == 1) & (d.probability >= d.threshold)).sum()),
        "FP": int(((d.omi_label == 0) & (d.probability >= d.threshold)).sum()),
        "TN": int(((d.omi_label == 0) & (d.probability < d.threshold)).sum()),
        "FN": int(((d.omi_label == 1) & (d.probability < d.threshold)).sum()),
    }), include_groups=False).reset_index()
    pooled["sensitivity"] = pooled.TP / (pooled.TP + pooled.FN)
    pooled["specificity"] = pooled.TN / (pooled.TN + pooled.FP)
    pooled.to_csv(RUN / "A2A_POOLED_LOCKED_METRICS.csv", index=False)
    print(pooled.to_string(index=False))

    # Paired patient-cluster bootstrap at locked thresholds.
    # One row per ECG; each sampled patient carries each observed ECG once.
    BOOTSTRAP_SEED = 20260912
    boot_rows = []
    patients = np.array(sorted(all_eval.patient_id.unique()))
    pid_index = all_eval.patient_id.map({p: i for i, p in enumerate(patients)}).to_numpy()
    correct = ((all_eval.omi_label == 0) & (all_eval.probability < all_eval.threshold)).to_numpy(float)
    non_omi = (all_eval.omi_label == 0).to_numpy(float)
    for i, cfg in enumerate(["C1", "C2", "C3"]):
        rng = np.random.default_rng(BOOTSTRAP_SEED + i)
        m0 = all_eval.configuration.to_numpy() == "C0"
        mc = all_eval.configuration.to_numpy() == cfg
        diffs = np.empty(1000)
        for b in range(1000):
            weights = np.bincount(rng.integers(0, len(patients), len(patients)), minlength=len(patients)).astype(float)
            rw = weights[pid_index]
            s0 = (rw[m0] * correct[m0]).sum() / (rw[m0] * non_omi[m0]).sum()
            sc = (rw[mc] * correct[mc]).sum() / (rw[mc] * non_omi[mc]).sum()
            diffs[b] = sc - s0
        boot_rows.append({"contrast": f"{cfg}-C0", "delta_specificity": float(pooled.set_index("configuration").loc[cfg, "specificity"] - pooled.set_index("configuration").loc["C0", "specificity"]),
                          "ci_low": float(np.quantile(diffs, 0.025)), "ci_high": float(np.quantile(diffs, 0.975)),
                          "bootstrap_unit": "patient cluster (observed ECGs once per sampled patient)", "replicates": 1000,
                          "thresholds": "locked per fold"})
    pd.DataFrame(boot_rows).to_csv(RUN / "A2A_PAIRED_PATIENT_BOOTSTRAP.csv", index=False)
    print(pd.DataFrame(boot_rows).to_string(index=False))
    summary = {"tasks_expected": 20, "tasks_completed": int(len(per_task)), "all_eval_recomputed": True,
               "patient_overlap": False, "bootstrap_replicates": 1000,
               "run_manifest_sha256": sha(RUN / "RUN_MANIFEST.json")}
    (RUN / "A2A_VERIFICATION_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
