# v1.0.0 release identity and implementation audit

## Identity

- Public repository: https://github.com/wzwmm2006/ecg-lead-information-omi
- Reported GitHub Release: `v1.0.0`
- Reported Zenodo version DOI: `10.5281/zenodo.22046833`
- Reported Zenodo concept DOI: `10.5281/zenodo.22046832`
- Official v1.0.0 tag: `refs/tags/v1.0.0` -> commit `5b75a385b9c69d467005527f93c0f92aa78cd61a` ("Clean release metadata before Zenodo archive")
- The tag exists remotely and resolves identically after `git fetch --no-tags origin tag v1.0.0`. It was fetched, not created, recreated, or moved.
- Later `main` HEAD: `c0407059dc32585f14d56219ee1f2c2da344d1fb` ("Add Zenodo DOI metadata"). This is not the v1.0.0 tagged commit; it differs from the tag only in `CITATION.cff`, `CODE_AVAILABILITY.md`, `README.md`, and `docs/release_checklist.md`.

## Implementation findings

1. **OOF class weighting: no discrepancy.** The official v1.0.0 `train.py` calls `patient_training_weights(frame)` once inside `run_oof` and before the fold loop, where `frame` is the complete readable development set. Its `dataset.py` sets `prevalence = labels.mean()`. The historical frozen `gate_0e_spatial_pilot.py` computes the same class weight from `train.omi.mean()` over the complete frame, and v1.1.0 keeps that rule. Recomputed on all 17,958 ECGs (1,151 OMI): prevalence 0.0640939971, maximum absolute weight difference 0.0 among v1.0.0, the frozen executor, and the RC. An earlier audit described a training-fold rule; that description was incorrect. The separate `run_final` path applies the same function to the 80% model-fit subset and is not the OOF estimand.
2. **WFDB validation.** v1.0.0 checked only sampling frequency. v1.1.0 additionally validates 5,000-sample length, lead names and order (I, II, III, AVR, AVL, AVF, V1-V6), mV units, physical-sample status, and pre-normalization finiteness.
3. **OOF bootstrap seed.** The historical frozen paired bootstrap used seed 20260912. v1.0.0 documented a legacy `base_seed + 99` seed and computed configuration intervals with configuration-specific seeds. v1.1.0 uses seed 20260912 for the public OOF paired bootstrap and records the legacy v1.0.0 behavior separately. The frozen historical percentile interval is retained but is not claimed as exactly reproduced.
4. **Figure generation.** v1.0.0 generated three evidence nodes and used "confirmation" wording. v1.1.0 separates development OOF, patient-disjoint calibration, same-source held-out, 100/250 Hz, and STAFF III. Figure 4 shows the within-patient logit change, matching the final manuscript.

## Public sanitization

The historical scripts are published as public sanitized copies. Machine-specific paths and a private evaluator endpoint are replaced by placeholders; the substitutions and both hash sets are recorded in `provenance/frozen_scripts/PUBLIC_SANITIZATION.md` and `FROZEN_SCRIPT_SOURCE_FINGERPRINTS.json`.

## Interpretation

These are implementation and documentation findings. They do not change the frozen result files. v1.1.0 is not a byte-for-byte restoration of the historical execution environment.

## Unreleased evidence

No patient data, model checkpoints, hidden predictions, or hidden TEST labels are included in this repository.
