# Code Audit — v1.0.0 to v1.1.0

## Scope

This audit compares the frozen execution logic with the public v1.0.0 code. It does not retrain models or inspect hidden labels. The source files are retained under `provenance/frozen_scripts/`.

## Findings

| Area | v1.0.0 public implementation | Historical frozen implementation | v1.1.0 treatment | Scientific impact |
|---|---|---|---|---|
| OOF class weighting | `patient_training_weights(frame)` called once before the fold loop; prevalence from the complete development frame (1,151 OMI / 17,958 ECG) | same complete-frame prevalence | `patient_training_weights()` computes prevalence from `labels.mean()` of the supplied frame; no forced constant | v1.0.0, frozen executor, and RC agree exactly (maximum absolute weight difference 0.0); no weighting discrepancy exists |
| WFDB validation | sampling rate only | waveform read and 12×5,000 shape check | validates lead names/order, units, 5,000-sample length, d_signal, finiteness | stronger input validation; no inference results changed |
| OOF bootstrap seed | documented `base_seed+99`; configuration intervals used configuration-specific seeds | paired seed 20260912, threshold re-estimated per replicate | public paired bootstrap uses the frozen seed; frozen historical table retained | an exact seeded replay does not reproduce the frozen interval, so it is not claimed |
| A1/A2a workflow | absent from v1.0.0 | nested inner split, locked threshold, outer evaluation | historical executors plus synthetic-tested split/centering helpers | deterministic decisions reproduced; neural-network refit not claimed |
| P3 workflow | absent | empirical ROC interpolation and paired patient-within-fold bootstrap | deterministic interpolation helper; 60-row recomputation matches | exact interpolation verified; bootstrap not replayed |
| 100/250 Hz | absent | fixed 5- and 2-sample block means; same folds | preprocessing helper, 20/10/4-ms window metadata, frozen-output hash check | training remains provenance-only |
| Figure 1 | three boxes; no A1/A2a layer | R2 revised evidence architecture | five distinct evidence layers in generator | no numerical values changed |
| Figure 4 | paired probability plot | R2 manuscript describes logit-change boxplot | generator now plots occlusion-minus-baseline logit | image/legend reconciled |
| Held-out workflow | 80/20 finalization present | same 80/20, frozen thresholds and one-shot submission | finalization text retained; no evaluator command present | no TEST access; aggregate evidence hash checked |
| C1/C3 interpretation | not explicit | algebraically related frontal-plane representations | README/Methods wording preserves this scope | no independent-energy interpretation |

## Methodological caveat

The original OOF bootstrap does not exactly reproduce the frozen percentile interval in the pinned environment. The bootstrap code is documented, but its interval is classified as historical output, not as an exact executable reproduction. No attempt was made to tune seeds, resampling order, or finalization to force agreement.

## Integrity boundary

No patient data, waveforms, checkpoints, or per-record predictions are included in the public release. The frozen scripts are published as sanitized copies of the historical sources: machine paths and a private evaluator endpoint are replaced by placeholders. `provenance/frozen_scripts/PUBLIC_SANITIZATION.md` records the substitutions, and `FROZEN_SCRIPT_SOURCE_FINGERPRINTS.json` records the SHA-256 of each original source beside the sanitized public copy. Portable functionality is implemented under `src/recovered/` and tested with synthetic data.
