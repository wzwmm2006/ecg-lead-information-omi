# Reproducibility Guide

## Frozen analysis specification

The public modules preserve the original scientific behavior:

- canonical lead order: I, II, III, aVR, aVL, aVF, V1-V6;
- 500-Hz clinical input reduced to 50 Hz by fixed ten-sample averaging;
- per-record, per-lead median centering and standard-deviation scaling with a `1e-3` floor;
- three convolutional blocks with output widths 32, 64, and 96 and kernels 11, 9, and 7;
- AdamW with learning rate `0.001`, weight decay `0.0001`, 10 epochs, and batch size 256;
- patient-level inverse recording-count weighting and inverse class-prevalence weighting;
- five shuffled stratified patient-grouped OOF folds;
- base random seed `20260813` and the original fold/configuration seed offsets;
- Spec95 selected at the first descending-score operating point reaching sensitivity at least 0.95;
- 1,000 patient-level bootstrap replicates for paired Spec95 contrasts;
- frozen patient-level 80/20 model-fit/threshold-calibration finalization;
- STAFF III 1000-to-500-Hz polyphase resampling followed by the clinical 500-to-50-Hz reduction;
- within-patient occlusion-minus-baseline logits, clipped at `1e-6`, with 1,000 patient bootstraps.

The machine-readable version is `provenance/FROZEN_ANALYSIS_SPEC.yaml`.

## Configuration

Each file in `configs/` contains one primary configuration. Scientific constants are duplicated intentionally so that each run has a complete, inspectable record. `examples/config_example.yaml` has the same schema and uses synthetic paths for dry-run validation.

Paths are resolved from the repository root. Absolute paths are rejected. Do not change the model, preprocessing, seed, threshold, split, or bootstrap fields when reproducing the reported analysis.

## Clinical preprocessing

Run once for each dataset split:

```bash
python -m src.data.preprocessing --config configs/c0_12lead.yaml --split train
python -m src.data.preprocessing --config configs/c0_12lead.yaml --split test
```

The command validates WFDB shape and sampling rate, writes a float32 NumPy array, and writes a companion row-index CSV. These outputs contain controlled record identifiers and remain under ignored `data/processed/`.

## OOF training

`scripts/train_models.sh oof` trains one configuration at a time. All ECGs from a patient remain in one of five shared folds. Output prediction CSVs are written under `outputs/oof/` and contain record IDs, patient IDs, labels, fold assignments, and probabilities. Treat them as controlled local artifacts.

The original seed for OOF fold `f` and configuration position `c` is:

```text
20260813 + f + 100*c
```

where C0-C3 have positions 0-3.

## OOF evaluation and statistical inference

`scripts/evaluate_models.sh` performs two steps:

1. `src.evaluation.metrics` computes AUROC, AUPRC, Brier score, threshold, sensitivity, specificity, PPV, and NPV for each configuration.
2. `src.evaluation.bootstrap` joins the four predictions by ECG and performs the paired patient-level bootstrap for C1-C0, C2-C0, and C3-C0.

Each bootstrap replicate samples patients with replacement and retains all rows belonging to each selected patient. The seed is `20260813 + 99`, with 1,000 replicates and percentile 95% intervals.

## Frozen model finalization

`scripts/train_models.sh final` recreates the original patient-level stratified 80% model-fit / 20% threshold-calibration split. Each configuration is trained once using seed `20260813 + c`. The calibration subset determines a configuration-specific Spec95 threshold. The command records locally calculated thresholds and checks them against the frozen reference values in the YAML file.

The resulting checkpoints are patient-data-derived artifacts and remain under ignored `models/`. They are needed for authorized local held-out inference and STAFF III analysis but are not part of the public release.

This repository deliberately contains no command that submits predictions to the private blind evaluator. Provider-authorized held-out inference can be performed locally with `python -m src.training.train --config configs/c0_12lead.yaml --mode predict` (and the corresponding C1-C3 files). Each run writes a probability file and the original provider-compatible `ecg_row_record`, `ecg_med_record`, and binary `OMI` layout. These row-level files must not be committed.

## STAFF III analysis

After final checkpoints exist, run:

```bash
python -m src.evaluation.staffiii --config configs/c0_12lead.yaml
```

The command verifies available provider hashes, parses the original annotation spreadsheet, selects the first eligible clear inflation per patient using the frozen rule, extracts 60-70-second baseline and occlusion windows, derives augmented limb leads, applies the frozen C0-C3 models without retraining, and calculates within-patient logit changes and bootstrap summaries.

Patient-level event selections and scores remain in ignored output directories. The command also writes aggregate configuration, coronary-territory, and frozen-threshold stress-test summaries. Only researcher-generated aggregate summaries should be used for figure generation or comparison.

## Figure generation

`scripts/reproduce_figures.sh` reads locally generated aggregate files. The blind held-out figure is generated only when an authorized aggregate results CSV is present at the configured path. No hidden row-level labels are required.

## Run metadata and provenance

Training and evaluation commands log the Python, package, platform, seed, configuration, and resolved relative inputs. `python -m src.utils.provenance` creates SHA-256 records for public source files or local run artifacts. Do not publish a local manifest if it references controlled outputs.

## Expected limitations

Fixed seeds reproduce data splits, sampling, and loader order. Exact neural-network weights can still vary across CPU/GPU types, CUDA/cuDNN releases, and nondeterministic low-level kernels. The package does not enable a new deterministic-algorithm mode because that was not part of the original frozen training procedure. Use the pinned reference environment and compare aggregate outputs and generated run metadata.
