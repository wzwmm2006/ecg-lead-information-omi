# GATE1_THRESHOLD_AUDIT

Audit date: 2026-11-10 (Asia/Shanghai)
Scope: read-only audit of the frozen C0-C3 OOF predictions, thresholds, confusion matrices and patient-level bootstrap implementation.
No model retraining, no manuscript edit, no journal submission.

## 1. Evidence sources

| Item | Path | SHA-256 (current) |
|---|---|---|
| C0-C3 OOF predictions | `03_results/gate_0e_oof_predictions.csv` | `3fcba114f4c6792a54734b831be6c5b9c6cfde25a0283acfcf90abc82c384c53` |
| Configuration performance | `03_results/gate_0e_configuration_performance.csv` | `679319ee8803c3896882483da7bd7b5c2a514efb6eb90c4c3f39fe062bb81d3` |
| Paired contrasts | `03_results/gate_0e_paired_contrasts.csv` | `2f1ccd13ae9f49bc884437a9ab77da6536550ea5d9e3c9e6c93e3a82f4f437e8` |
| High-sensitivity tradeoff | `03_results/gate_0e_high_sensitivity_tradeoff.csv` | `f2a486573c585f03aa05dd690585cea7ad45684b213e0b7f0f8f947340d39dc4` |
| Final table 2 (paper) | `03_results/FINAL_TABLE_2_OOF_PERFORMANCE.csv` | `1871b1b06c89e7829bf8042112bf0afeaf02f45465802158dd2186e30164213d` |
| Final table 3 (blind) | `03_results/FINAL_TABLE_3_BLIND_TEST.csv` | `5d737ca850848a1de4c89cad6179e79576794940a84ffc2d609425699cb8bbd5` |
| Fold assignment | `02_data/interim/gate_0e_patient_fold_assignment.csv` | `de06a73b48552f6572ac4923d22c70b5443fc1e58b416f0201e3a760f9905c52` |
| Finalization split | `02_data/interim/gate_0f_finalization_split.csv` | `398a4070cf802752a8608e2374b20a0e98189d55a124ec30078e30188ff2125b` |
| Freeze manifest | `00_admin/GATE_0F_FREEZE_MANIFEST.md` | `2a5469441a939b03b832b3fc4690c1bc043635a2c510490ee965d546cdedc0be` |
| Threshold code (OOF) | `05_code/gate_0e_spatial_pilot.py` | `b8bcea13450daa29904fb6d78646d9ca9305bab2f772ad62dbc9a8a16fbb6922` |
| Threshold/bootstrap code (evidence lock) | `05_code/stage_1_evidence_lock.py` | `7d63ace0afd3288ebfdf844a2fbe0a34ced45acf2e01d9353a87544056b94430` |
| Finalization code | `05_code/gate_0f_finalize_and_submit.py` | `8a68778c4915a14bfa6f62892537616c98ff15c4f979ef492a7ca15ef1871b14` |

Cohort: 17,958 readable development ECGs from 17,016 patients, including 1,151 OMI-positive ECGs from 1,139 OMI-positive patients. These are **ECG-level** rows; the patient bootstrap is an uncertainty procedure, not a patient-weighted point estimate.

## 2. What the original code actually does

### 2.1 OOF threshold (Gate 0E)

`05_code/gate_0e_spatial_pilot.py`, `spec_at_sens(y, p, 0.95)`:

1. Sort the **same pooled OOF probability vector** that will be evaluated in descending order.
2. Take the first index where cumulative sensitivity reaches 0.95.
3. Set that probability as the threshold and compute sensitivity/specificity on the same full OOF vector.

So the point estimate is an **empirically optimized OOF operating-point statistic**. It is not a threshold fixed on separate patients before evaluation.

### 2.2 Patient bootstrap (Gate 0E)

`05_code/stage_1_evidence_lock.py`, `paired_spec_bootstrap`:

- Samples 1,000 times at the patient level, retaining all ECGs of each sampled patient.
- In each replicate re-runs `spec_at_sens` for C0 and for the reduced configuration.
- Therefore **each replicate re-estimates the threshold inside the resample**, then evaluates specificity on that same resample.

This estimates uncertainty of the optimized same-sample operating-point statistic. It **does not** capture threshold-selection uncertainty conditional on a pre-fixed threshold, and it does not capture model-training variability.

### 2.3 Blind held-out finalization (Gate 0F)

`05_code/gate_0f_finalize_and_submit.py`:

- Patient-level 80/20 MODEL_FIT / THRESHOLD_CALIBRATION split, fixed before model fitting (seed 20260813, stratified on patient OMI).
- Final thresholds are selected on the 20% calibration subset.
- The freeze manifest was written **before** TEST inference; submission hashes were recorded and the single evaluation had no adaptive resubmission.

This part is a genuine **threshold-calibration / evaluation separation**, at the patient level, for the blind held-out evaluation. It is not external validation: development and blind held-out are from the same source dataset.

## 3. Point estimates: actual threshold, counts, sensitivity, specificity

Recomputed from `gate_0e_oof_predictions.csv`; these reproduce `FINAL_TABLE_2_OOF_PERFORMANCE.csv` to six decimals.

| Configuration | Threshold | TP | FP | TN | FN | Sensitivity | Specificity | Denominator |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| C0 | 0.0007638259558007 | 1,094 | 9,933 | 6,874 | 57 | 0.950478 | 0.408996 | 1,151 OMI / 16,807 non-OMI ECGs |
| C1 | 4.500634167925455e-05 | 1,094 | 14,233 | 2,574 | 57 | 0.950478 | 0.153150 | same |
| C2 | 0.0045852931216359 | 1,094 | 12,204 | 4,603 | 57 | 0.950478 | 0.273874 | same |
| C3 | 0.0009411954088136 | 1,094 | 13,196 | 3,611 | 57 | 0.950478 | 0.214851 | same |

These are **ECG-weighted** estimates: every ECG row contributes one classification. They are not patient-weighted; repeated ECGs are retained.

## 4. Paired contrasts and uncertainty

| Contrast | ΔSpec95 (reduced − C0) | 95% CI | ΔAUROC (point) | ΔFPR (= −ΔSpec95) |
|---|---:|---|---:|---:|
| C1 − C0 | −0.2558 | −0.2977 to −0.1993 | −0.1143 | +0.2394 |
| C2 − C0 | −0.1351 | −0.2000 to −0.0717 | −0.0684 | +0.1265 |
| C3 − C0 | −0.1941 | −0.2581 to −0.1264 | −0.0833 | +0.1817 |

Source of point values and confidence intervals: `gate_0e_paired_contrasts.csv`. The intervals are the **original** paired patient-bootstrap intervals (threshold re-estimated in each replicate).

An independently computed paired patient bootstrap for ΔAUROC (1,000 replicates, fresh deterministic seed, current frozen predictions, read-only) gave:

| Contrast | ΔAUROC | 95% CI |
|---|---:|---|
| C1 − C0 | −0.1143 | −0.1298 to −0.0994 |
| C2 − C0 | −0.0684 | −0.0846 to −0.0528 |
| C3 − C0 | −0.0833 | −0.1001 to −0.0668 |

These intervals are descriptive. The three contrasts are **not multiplicatively adjusted**; they are exploratory in the multiplicity sense.

## 5. Threshold-decoupled sensitivity analyses using the frozen predictions

The following reuses frozen OOF predictions. It is a **post-hoc threshold sensitivity analysis**, not a nested training procedure.

### 5.1 Bootstrap with the global threshold held fixed

Using the same patient-level resampling and holding the observed global threshold fixed:

| Configuration | Fixed-threshold specificity 95% CI | Re-estimated-threshold specificity 95% CI |
|---|---|---|
| C0 | 0.4014 to 0.4170 | 0.3552 to 0.4520 |
| C1 | 0.1476 to 0.1594 | 0.1424 to 0.1648 |
| C2 | 0.2668 to 0.2808 | 0.2273 to 0.3072 |
| C3 | 0.2081 to 0.2212 | 0.1658 to 0.2495 |

The fixed-threshold intervals are narrow because they condition on the observed threshold. The wider re-estimated intervals reflect threshold variability, including prevalence differences across resamples.

### 5.2 Threshold fitted on one patient half, evaluated on the other

Post-hoc two-way split of patients, threshold fitted on one half and applied to the other, using the frozen OOF probabilities:

| Threshold fitted on | Evaluated on | C0 spec / sens | C1 spec / sens | C2 spec / sens | C3 spec / sens |
|---|---|---:|---:|---:|---:|
| A | B | 0.3566 / 0.9702 | 0.1631 / 0.9372 | 0.2702 / 0.9521 | 0.2299 / 0.9421 |
| B | A | 0.4526 / 0.9212 | 0.1486 / 0.9597 | 0.2786 / 0.9469 | 0.2004 / 0.9560 |

Direction in both splits: all reduced configurations had lower specificity than C0. Sensitivity was numerically close to but not exactly 0.95 because the threshold was transported across patient groups. The exact magnitudes are split-dependent.

Limitation: this split reuses OOF predictions from models that saw neither patient in the relevant fold pair only in the OOF sense. It does **not** re-fit models; therefore it can test threshold transport, not full nested training.

### 5.3 Per-fold threshold fitted within each OOF fold

Using each fold's own patient-grouped OOF predictions to set a threshold for that fold:

| Configuration | Pooled specificity | Pooled sensitivity |
|---|---:|---:|
| C0 | 0.4952 | 0.9522 |
| C1 | 0.3677 | 0.9522 |
| C2 | 0.3726 | 0.9522 |
| C3 | 0.3639 | 0.9522 |

This is a more independent threshold-selection analogue than the pooled re-estimation, but **still not nested model training**: the OOF probabilities within a fold come from a model fitted without that fold's patients, but they are used twice—once for threshold choice and once for evaluation within the same fold. It is informative about threshold optimism, not model-training independence.

## 6. Independence of the 80/20 calibration and blind held-out evaluation

| Property | Finding |
|---|---|
| Split type | Patient-level, stratified OMI, fixed with seed 20260813 |
| MODEL_FIT patients | 13,612 |
| THRESHOLD_CALIBRATION patients | 3,404 |
| OOF folds | Five patient-grouped folds, same 17,016 patients |
| Calibration subset coverage across OOF folds | Present in every fold (649–710 patients per fold) |
| Threshold selected before TEST inference | Yes; freeze manifest timestamp precedes held-out scoring |
| Held-out labels used locally | Not accessed; evaluator returned aggregate metrics only |
| Adaptive resubmission | None |
| External independent cohort | None |

Interpretation:
- The blind held-out **threshold calibration and evaluation** are separated, and thresholds were locked before TEST scoring. That supports the held-out aggregate results as **blind concordant-direction confirmation within the same source dataset**.
- The OOF **primary** estimates are not separated in that way: threshold and evaluation share the same pooled predictions.
- The 80/20 calibration subset is not a nested training split: final models were fitted on 80% and thresholds on the held-out 20%, but that 20% is not reused as an independent external test.

## 7. OOF versus blind held-out ordering

| Configuration | OOF specificity | OOF rank | Blind specificity | Blind rank |
|---|---:|---:|---:|---:|
| C0 | 0.4090 | 1 | 0.4488 | 1 |
| C2 | 0.2739 | 2 | 0.2646 | 4 |
| C3 | 0.2149 | 3 | 0.3990 | 2 |
| C1 | 0.1532 | 4 | 0.3589 | 3 |

What is stable: C0 was highest in both, and all reduced configurations were lower than C0.

What is unstable: the C1/C2/C3 ordering reversed; the blind C1 specificity decrement was −0.0899 versus −0.2558 in OOF; C3 was −0.0498 versus −0.1941. The blind data did **not** support a stable magnitude or a stable rank.

## 8. Classification of the threshold issue

- **Not supported by the frozen evidence:** a fully nested, model-refit, patient-grouped threshold selection for the primary OOF estimates. That design requires retraining and a new execution plan.
- **Supported with narrower claims:** the direction of lower specificity for reduced configurations is robust to threshold fixed at the global value, to a patient-half threshold transport, to per-fold threshold refitting, and to the internally calibrated blind held-out evaluation.
- **Supported numerical comparison:** ΔAUROC intervals can be computed directly from the frozen OOF predictions; they are exploratory unless corrected for multiplicity.
- **Not a data-integrity failure:** the discrepancy is a design/estimand issue, not evidence that the data were corrupted.

**Threshold verdict:** `CORE_SUPPORTED_WITH_NARROWER_CLAIMS`.