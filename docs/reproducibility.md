# Reproducibility Guide

## Version boundaries

v1.1.0 documents the original OOF, patient-disjoint A1/A2a, same-source held-out, 100/250-Hz sampling sensitivity, and post hoc P3 analyses. These are distinct evidence layers. They are not all validations of a single deployed 95%-sensitivity threshold.

The historical scripts are stored under `provenance/frozen_scripts/`. Two are byte-identical to their sources; the other twelve are sanitized public copies in which machine paths and a private evaluator endpoint were replaced by placeholders. `provenance/frozen_scripts/PUBLIC_SANITIZATION.md` describes the substitutions, and `FROZEN_SCRIPT_SOURCE_FINGERPRINTS.json` lists each original-source SHA-256 beside the sanitized public SHA-256. The scripts preserve the original analysis logic but are inspection artifacts, not cross-platform entry points. Public helpers under `src/recovered/` provide data-free checks and deterministic implementations; they make no claim that the original neural network training was rerun.

## Frozen specification

- Clinical lead order: `I, II, III, aVR, aVL, aVF, V1–V6`
- Clinical sampling: 500 Hz, 10 seconds, 5,000 samples
- Primary development reduction: fixed block mean over 10 samples → 50 Hz, 500 samples
- 100 Hz and 250 Hz reductions: fixed block mean over 5 and 2 samples
- Normalization: per-record, per-lead median centering and SD scaling
- Architecture: TinyECGCNN with 32/64/96 channels and kernels 11/9/7
- Optimizer: AdamW, lr 0.001, weight decay 0.0001, 10 epochs, batch 256
- OOF folds: five patient-grouped folds, seed 20260813
- A1: two training seeds; A2a: one training seed
- Threshold rule: first descending score reaching ≥0.95 sensitivity
- Original OOF bootstrap: 1,000 patient-cluster replicates, seed 20260912
- A2a/P3 paired bootstrap: patient-within-fold, existing stored predictions only

## Distinguishing the evidence layers

| Layer | Threshold source | Estimation/evaluation relationship |
|---|---|---|
| Original OOF | same evaluated pooled records | development estimate; threshold re-estimated within bootstrap |
| A1 | patient-disjoint inner calibration | locked before outer-fold evaluation |
| A2a | patient-disjoint inner calibration | locked; one training seed |
| Held-out | frozen final 80/20 calibration | same-source aggregate evaluation, not external |
| 100/250 Hz | same-rate OOF records | sensitivity analysis, not independent |
| P3 | post hoc empirical-ROC interpolation | not a deployable threshold |

## Installation and tests

Use Python 3.12.10 and the pinned environment files. Data-free checks:

```bash
python -m pytest -q
python -m src.training.train --config examples/config_example.yaml --dry-run
python figures/generate_figures.py --dry-run
```

## OOF workflow

```bash
python -m src.data.preprocessing --config configs/c0_12lead.yaml --split train
bash scripts/train_models.sh oof
bash scripts/evaluate_models.sh
```

The v1.1.0 preprocessing validates lead names and order, 5,000-sample length, mV units, physical-signal status, and input finiteness. The v1.0.0 implementation checked only sampling frequency.

OOF class weights are computed from the complete development frame before the fold loop (1,151 OMI / 17,958 ECG). The official v1.0.0 tag, the historical frozen executor, and this package agree exactly; see `provenance/V1_0_0_RELEASE_IDENTITY.md`.

## Frozen-output verification

```bash
bash scripts/verify_frozen_outputs.sh /path/to/authorized-frozen-project
```

A `FROZEN_OUTPUT_MATCHED` result means the supplied file exactly matches a listed SHA-256. It does not mean a model was retrained.

## A1/A2a

The historical executors are `run_fit_A1_A2a.py` and `run_a2a_fit.py`, retained for provenance. The reconstructed A1/A2a helpers are:

- `src.recovered.a1_a2a.nested`: patient-disjoint inner split and frozen threshold function;
- `src.recovered.a1_a2a.centering`: configuration-local mean-of-medians with a fixed 1-mV scale.

The 60 stored fold/config decision tables were independently recomputed from their per-ECG predictions and match the published TP/FP/TN/FN counts. No refit is claimed.

## P3

```bash
bash scripts/recover_p3_tables.sh /path/to/authorized-frozen-project
```

The deterministic interpolation test recomputes specificity at TPR 0.95 for all 60 fold/configurations from stored predictions; the maximum absolute difference from the frozen table is 8.33e-17. The frozen paired bootstrap intervals are preserved as published files. v1.1.1 adds a corrected patient-cluster bootstrap helper; a separate read-only 2,000-replicate replay from the frozen predictions retained the frozen interval-exclusion count (2/9), with endpoint differences attributable to the bootstrap random sequence. The frozen values remain the reportable estimates.

## 100/250 Hz

```bash
bash scripts/summarize_sampling_sensitivity.sh /path/to/authorized-frozen-project
```

The helper reproduces the window semantics: 10-, 5-, and 2-native-sample blocks at 500 Hz correspond to 20-, 10-, and 4-ms windows. The original pretraining remains a frozen historical process.

## Held-out data

There is no command that sends predictions to the private evaluator. The held-out evaluation is not external validation and returns aggregate metrics only. `FINAL_TABLE_3_BLIND_TEST.csv` is retained in the provenance hash manifest; it is not redistributed with row-level labels.

## Privacy and controlled artifacts

The following must not be committed: patient metadata, waveforms, checkpoints, per-ECG predictions, threshold records containing row identifiers, hidden labels, and local evaluator responses. Tests use synthetic data only.

## Environment caveat

Exact neural-network weights may vary with hardware and numerical libraries even when seeds are fixed. The environment is pinned for auditability, not to assert bitwise training reproducibility.
