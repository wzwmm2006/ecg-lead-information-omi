# Validation status by analysis

| Analysis | Public entry point | Status | What was actually verified |
|---|---|---|---|
| Original OOF metrics | `src.evaluation.metrics` | EXECUTABLE_VERIFIED; FROZEN_OUTPUT_MATCHED for source aggregates | AUROC/AUPRC point estimates recompute exactly from frozen OOF probabilities; frozen aggregate hashes match |
| Original OOF paired bootstrap | `src.evaluation.bootstrap` | EXECUTABLE_VERIFIED method; NOT independently exact for frozen CI | Patient resampling and threshold re-estimation implemented; pinned environment currently produces a different percentile interval, so the frozen interval remains historical output |
| A1/A2a per-fold predictions | `provenance/frozen_scripts/run_fit_A1_A2a.py`, `run_a2a_fit.py`; helpers in `src.recovered.a1_a2a` | FROZEN_OUTPUT_MATCHED for 60 decision tables; EXECUTABLE_VERIFIED for deterministic counts | Stored TP/FP/TN/FN match per-ECG threshold decisions exactly; no neural network refit was run |
| A1/A2a split | `src.recovered.a1_a2a.nested` | EXECUTABLE_VERIFIED on synthetic data | Patient-disjoint inner split and calibration target unit tested |
| A2a centering | `src.recovered.a1_a2a.centering` | EXECUTABLE_VERIFIED on synthetic data | Configuration-local mean-of-medians and fixed 1-mV scaling |
| P3 interpolation | `src.recovered.p3.matched_tpr` | EXECUTABLE_VERIFIED; FROZEN_OUTPUT_MATCHED | All 60 fold/config-specificities recompute from stored predictions with max absolute difference 8.33e-17 |
| P3 bootstrap | `src.recovered.p3.bootstrap` | PROVENANCE_ONLY for frozen intervals; synthetic implementation tested | Implementation is deterministic and inspectable; frozen nine intervals remain the reportable values and were not claimed as exactly regenerated |
| 100/250 Hz | `provenance/frozen_scripts/r2_sampling_run.py`; `src.recovered.sampling` | FROZEN_OUTPUT_MATCHED; PROVENANCE_ONLY training | Output hashes match; block durations unit tested; no model retrained |
| Clinical baseline and timing | source metadata CSV | FROZEN_OUTPUT_MATCHED; EXECUTABLE_VERIFIED counts | Patient/ECG counts and denominators recomputed from frozen metadata |
| Staff III | `provenance/frozen_scripts/gate_0g_staffiii_frozen_triangulation.py` | PROVENANCE_ONLY; no inference | No STAFF III records or models were re-run |
| Figures | `figures/generate_figures.py` | EXECUTABLE dry-run only | Rendering works; R2 aggregate input files not included, so exact image equality was not claimed |

All neural-network training, held-out inference and STAFF III inference are explicitly outside this verification. The public package does not include patient data, hidden predictions, or model weights.
