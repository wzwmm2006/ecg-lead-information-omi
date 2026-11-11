# CORRECTED_A1_A2a_PROTOCOL

Topic890 / Gate 1.5 final pre-execution correction
Status: **FROZEN CANDIDATE — NOT AUTHORIZED TO TRAIN**
Date: 2026-11-10 (Asia/Shanghai)
Supersedes the A1/A2 planning content of `GATE1_5_A1_A2_PROTOCOL.md`.

This document fixes three errors in the earlier Gate 1.5 protocol: the inner-calibration OMI count, the A2a centring definition, and the A1 seed plan. It does not change the original primary analysis, any frozen result, any manuscript, or any repository.

---

## 0. Changes from the earlier protocol

| Item | Earlier text | Corrected text |
|---|---|---|
| Inner calibration size | ~46 OMI ECGs per fold | **182–187 OMI ECGs and 182 OMI patients per fold** (see `INNER_SPLIT_COUNT_QC.csv`) |
| Inner split basis | 80/20 of the outer *evaluation* patient count (wrong denominator) | 80/20 of the **outer-training** patient count |
| A2a centring | "median of all 12 leads concatenated" (ambiguous and mixed definitions) | Per-configuration, using only that configuration's own input leads, with one exact formula (Section 3) |
| A1 seeds | one training seed | **two pre-specified training seeds** |
| Total fits | 40 (A1 + A2a) | **60 = A1 × 2 seeds × 20 + A2a × 1 seed × 20** |
| Low-sensitivity handling | could trigger a stop rule | **must be reported; only technical defects can trigger HALT** |

---

## 1. Fixed scope

### 1.1 Data

- Metadata: `02_data/metadata_raw/CSV/train.csv`, SHA-256 `15fdb9b576da88acc31d07612e457848a3d3502ea4955ffd3fed845968310907`.
- Waveforms: `02_data/interim/waveforms_raw/row_data`, 500 Hz, 10 s, 12 leads.
- Excluded records: exactly `03228`, `14262`.
- Frozen cohort: 17,958 ECGs; 17,016 patients; 1,151 OMI ECGs; 1,139 OMI patients.
- Labels: the source `OMI` column. No relabeling.

### 1.2 Configurations (unchanged)

C0 = I, II, III, aVR, aVL, aVF, V1–V6; C1 = I, II, III, aVR, aVL, aVF; C2 = V1–V6; C3 = I, II, III.

No aVR-only arm, no new lead subset, no new architecture.

### 1.3 Architecture/training (unchanged)

`TinyECGCNN`, Conv1d(32, k=11) → BN → ReLU → MaxPool(4) → Conv1d(64, k=9) → BN → ReLU → MaxPool(4) → Conv1d(96, k=7) → BN → ReLU → AdaptiveAvgPool(1) → Linear(96→1).

AdamW, lr 0.001, weight decay 0.0001, 10 epochs, batch 256, weighted BCE (inverse record count × inverse class prevalence), no early stopping, no hyperparameter search.

### 1.4 Metric and threshold rule (unchanged)

Target sensitivity ≥0.95 with the original first-descending-rank rule. Primary endpoint: specificity at the transported threshold, with the actually achieved sensitivity reported. ECG-level denominator.

---

## 2. A1: nested threshold validation

### 2.1 Outer loop

Five outer folds from `02_data/interim/gate_0e_patient_fold_assignment.csv` (SHA-256 `de06a73b48552f6572ac4923d22c70b5443fc1e58b416f0201e3a760f9905c52`).

Outer evaluation patients never enter that fold's training, threshold selection, or model selection.

| Outer fold | Outer-training patients | Outer-training OMI patients | Outer-training OMI ECGs | Outer-evaluation patients |
|---:|---:|---:|---:|---:|
| 0 | 13,613 | 911 | 921 | 3,403 |
| 1 | 13,609 | 911 | 921 | 3,407 |
| 2 | 13,614 | 910 | 920 | 3,402 |
| 3 | 13,618 | 912 | 921 | 3,398 |
| 4 | 13,610 | 912 | 921 | 3,406 |

### 2.2 Frozen inner split

The 80/20 inner split is generated from the **outer-training** patients with patient-level stratification on OMI, using `sklearn.model_selection.train_test_split(test_size=0.20, random_state=20260813+1000+outer_fold, stratify=patient_level_OMI)`.

The resulting assignment is written to `10_gate1_5_r2/INNER_SPLIT_ASSIGNMENT.csv` (SHA-256 `17f44e781a0e5dfbf0096da93aa05b72c3c30a47cb4937f9d59ebf4cb1349557`), and its counts to `INNER_SPLIT_COUNT_QC.csv` (SHA-256 `75a8a0a53c2354f92328a2b96c9977de09155741e75ea785142528ca1691a993`).

| Outer fold | Inner-fit patients | Inner-fit OMI patients | Inner-fit OMI ECGs | Inner-cal patients | Inner-cal OMI patients | Inner-cal OMI ECGs | Inner-cal non-OMI patients | Inner-cal non-OMI ECGs |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 10,890 | 729 | 737 | 2,723 | 182 | 184 | 2,557 | 2,683 |
| 1 | 10,887 | 729 | 739 | 2,722 | 182 | 182 | 2,561 | 2,690 |
| 2 | 10,891 | 728 | 733 | 2,723 | 182 | 187 | 2,560 | 2,707 |
| 3 | 10,894 | 730 | 738 | 2,724 | 182 | 183 | 2,562 | 2,690 |
| 4 | 10,888 | 730 | 737 | 2,722 | 182 | 184 | 2,555 | 2,678 |

QC: zero patient overlap between inner-fit, inner-calibration, and outer-evaluation sets within every fold.

### 2.3 Threshold selection and one-shot evaluation

For each outer fold k and configuration c:

1. Fit on inner-fit patients only.
2. Predict inner-calibration ECGs.
3. Select τ_k,c by the frozen first-crossing ≥0.95 rule on the calibration ECGs.
4. Lock model weights and τ_k,c.
5. Score the outer-evaluation ECGs once.
6. Record TP/FP/TN/FN, achieved sensitivity, specificity, threshold.

All ECG rows of a calibration patient remain in calibration; no downweighting at the threshold step. Report the achieved sensitivity, which may exceed 0.95.

### 2.4 Two pre-specified training seeds

A1 is run with **two pre-specified training seeds**:

- Seed A: `20260813 + outer_fold + 100 × configuration_position` (the original Gate 0E policy).
- Seed B: `20270313 + outer_fold + 100 × configuration_position` (a single pre-declared offset, fixed before any run).

Both seeds share the same outer folds, inner split, architecture, epochs, batch size, optimizer, and threshold rule. Neither seed may be selected or discarded based on its result.

Total A1 fits: 2 seeds × 4 configurations × 5 outer folds = **40**.

### 2.5 Uncertainty

- Primary: report the **mean and range across the two seeds** of each contrast, and the per-fold spread.
- Patient-level bootstrap over the pooled outer-evaluation predictions, 1,000 replicates, seed 20260813+99, locked thresholds:
  - run separately for each seed;
  - report both seed-specific intervals.
- A combined interval that incorporates both seeds and patient sampling is a secondary descriptive range; do not call it a formal training-variability confidence interval unless a larger seed set is run.
- Per-fold spread is descriptive and not a confidence interval.

### 2.6 Corrected expectation about sensitivity and specificity

The inner-calibration set has **182 OMI patients and 182–187 OMI ECGs per fold**, not 46. A read-only re-sampling of the frozen OOF predictions, matched to this size (183 OMI ECGs, 2,690 non-OMI ECGs, 300 subsets), gave:

| Configuration | Median specificity at ≥0.95 sensitivity | IQR | Median achieved sensitivity | Achieved sensitivity range |
|---|---:|---:|---:|---|
| C0 | 0.409 | 0.365–0.445 | 0.953 | 0.950–0.956 |
| C1 | 0.154 | 0.145–0.161 | 0.953 | 0.950–0.956 |
| C2 | 0.275 | 0.247–0.302 | 0.952 | 0.950–0.956 |
| C3 | 0.207 | 0.171–0.239 | 0.952 | 0.950–0.956 |

This is a planning simulation on frozen OOF predictions, **not** a new-model result. It supports the feasibility of the nested design and shows a smaller threshold-sampling spread than the erroneous ~46-OMI estimate implied. It does not predict the A1 results.

### 2.7 What A1 can and cannot resolve

Can resolve:
- specificity at an independently selected threshold, with the outer-evaluation patients excluded from all selection steps;
- actual achieved sensitivity per fold and pooled;
- whether the direction survives nested calibration across two seeds.

Cannot resolve:
- external generalization;
- true device-level reduced-lead acquisition;
- formal training-variability intervals beyond the two reported seeds;
- exact equivalence to the original pooled OOF estimand.

Training A1 fits on ~10,890 patients, fewer than the 13,612 in the original finalization fits. This is an intentional different estimand, not an error.

---

## 3. A2a: relative-amplitude-preserving, per-configuration centring

### 3.1 Single 50 Hz preprocessing path

Start from the same 500 Hz, 5,000-sample, 12-lead record and apply the same non-overlapping 10-sample block mean used in the primary analysis to obtain 50 Hz, 500 samples per lead.

### 3.2 Exact common-centring constant, per configuration

For configuration S (one of C0, C1, C2, C3) and record i:

- Let `x_{i,l,t}` be the 50 Hz value of lead `l ∈ S` at time `t`, in mV.
- Define `m_{i,l} = median_t(x_{i,l,t})` for each lead in S.
- Define the common centring constant exactly as the **unweighted mean of the per-lead medians**:

`c_{i,S} = (1/|S|) · Σ_{l∈S} m_{i,l}`

- Define the model input for every lead in S as:

`z_{i,l,t} = (x_{i,l,t} − c_{i,S}) / 1.0 mV`

- No per-lead centring, no per-lead scaling, no percentile or IQR normalization.

This `c_{i,S}` uses **only the leads actually present in configuration S**. It never references I, II, III, aVR, aVL, aVF, V1–V6 channels that are excluded from S. Therefore C1 and C3 do not use V1–V6, and C2 does not use limb leads.

The concatenated 12-lead sample median and the mean-of-12-lead-medians are different quantities and are **not** interchangeable. This protocol uses only the mean-of-medians formula above.

### 3.3 Fixed scale and QC

- Scale: exactly `1.0 mV` for all channels, all configurations, all records.
- Non-finite values → 0, as in the primary pipeline.
- No new morphology-based exclusion. Only `03228`, `14262` remain excluded.
- The 10-sample block mean is still a boxcar operation and is not a dedicated anti-alias filter; that limitation remains.

### 3.4 Same nested structure

A2a uses the same outer folds, the same frozen inner split, the same seed A policy (`20260813 + outer_fold + 100 × configuration_position`), the same epochs, batch size, optimizer, and threshold rule as A1.

A1 seed A differs from A2a only in the input normalization. This makes the preprocessing comparison auditable.

A2a runs: 1 seed × 4 configurations × 5 outer folds = **20**.

### 3.5 What A2a can and cannot resolve

Can resolve:
- whether the reduced-configuration specificity cost survives removal of per-lead z-scoring;
- the C1/C3 gap under a common scale, as a representation finding;
- whether relative-amplitude preservation changes the direction.

Cannot resolve:
- actual device acquisition;
- baseline offsets produced by a specific commercial device;
- universal normalization claims;
- information content beyond the tested representation.

---

## 4. Joint run plan and fit count

| Analysis | Seed | Configurations | Outer folds | Fits |
|---|---|---:|---:|---:|
| A1 seed A | 20260813+fold+100·pos | 4 | 5 | 20 |
| A1 seed B | 20270313+fold+100·pos | 4 | 5 | 20 |
| A2a | 20260813+fold+100·pos | 4 | 5 | 20 |
| **Total** | | | | **60** |

No A2b. No A3/A4/A5. No aVR-only arm. No hidden TEST. No STAFF III re-inference.

---

## 5. Reporting template (pre-specified)

For every analysis, seed, outer fold, and configuration:

| Field | Definition |
|---|---|
| `analysis` | A1_seedA / A1_seedB / A2a |
| `outer_fold` | 0–4 |
| `configuration` | C0–C3 |
| `n_inner_fit_patients` | from `INNER_SPLIT_COUNT_QC.csv` |
| `n_inner_cal_patients`, `n_inner_cal_omi_ecg` | from the frozen split |
| `threshold_locked` | τ_k,c,seed |
| `n_outer_eval_ecg`, `n_outer_eval_omi_ecg` | outer fold |
| `TP`, `FP`, `TN`, `FN` | outer evaluation |
| `sensitivity_achieved` | TP/(TP+FN) |
| `specificity` | TN/(TN+FP) |
| `delta_spec_vs_C0` | paired, same analysis/seed/fold |
| `delta_fpr_vs_C0` | −ΔSpecificity |
| `bootstrap_ci_locked` | patient bootstrap, locked thresholds |

Pooled summaries separate A1 seed A, A1 seed B, and A2a. No averaging of A1 and A2a into one "primary" number.

---

## 6. Analysis-freeze conditions

Before the first fit, the following must be true:

1. Both `INNER_SPLIT_COUNT_QC.csv` and `INNER_SPLIT_ASSIGNMENT.csv` have the SHA-256 recorded in Section 2.2.
2. Zero-overlap QC passes for all five folds.
3. The A2a formula is the per-configuration mean-of-medians; the code hard-asserts that no excluded lead enters `c_{i,S}`.
4. Both A1 seeds and the A2a seed are recorded in a run manifest.
5. All outputs go to a new run directory outside `02_data`, `03_results`, `10_gate0_r2`, `10_gate1_r2`, `10_gate1_5_r2`, and any public release.
6. No hidden TEST, evaluator, STAFF III, GitHub, Zenodo, manuscript, or response-letter interaction.

---

## 7. HALT and report rules

### 7.1 Technical defects that must HALT

- Patient leakage between outer-evaluation, inner-fit, or inner-calibration sets.
- Any patient in more than one role within the same outer fold.
- A configuration's A2a centring constant using a lead outside that configuration.
- Non-finite model input or output in more than 0.1% of an ECG set.
- A threshold, prediction, or label file that does not match its recorded SHA-256.
- Any access to hidden TEST or the evaluator.
- A code path that silently selects a seed, preprocessing, or threshold based on outer-evaluation results.

On HALT: stop the run, preserve logs, write a QC failure report, and do not resume without a corrected frozen protocol.

### 7.2 Low sensitivity is not a HALT

If outer-evaluation sensitivity is below 0.80 for any configuration or fold, this is a **result**, not an error. It must be reported. It can trigger a separate technical QC review (to confirm the threshold and scoring code), but it must not be used to erase, exclude, or reselect that configuration.

### 7.3 No result-based selection

No selection of a "best" seed, fold, preprocessing, or operating point after seeing results. A1/A2a are fixed analyses whose only allowed reporting is the pre-specified table plus a descriptive commentary.

---

## 8. What this protocol explicitly does not do

- It does not modify the original primary OOF estimand or its reported values.
- It does not replace the original paper's threshold-re-estimating bootstrap CIs.
- It does not touch hidden TEST, STAFF III, GitHub, Zenodo, the manuscript, or the response letter.
- It does not claim that the two A1 seeds provide a formal training-variability CI.
- It does not claim external or real-device validity.