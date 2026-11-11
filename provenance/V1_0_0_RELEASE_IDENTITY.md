# v1.0.0 release identity and implementation audit

## Identity

- Public repository: https://github.com/wzwmm2006/ecg-lead-information-omi
- Reported GitHub Release: `v1.0.0`
- Reported Zenodo version DOI: `10.5281/zenodo.22046833`
- Reported Zenodo concept DOI: `10.5281/zenodo.22046832`
- Local clone HEAD at audit: `c0407059dc32585f14d56219ee1f2c2da344d1fb` (`Add Zenodo DOI metadata`)
- Local repository tag listing: none. The GitHub server tag/release must be treated as a release identity separate from the local clone. This file does not invent a local tag.

## Implementation differences found in v1.0.0

1. **OOF class weighting.** `src/data/dataset.py` in v1.0.0 calculated class weights from the training-fold prevalence. The historical frozen executor `gate_0e_spatial_pilot.py` calculated them from the full development prevalence (1,151/17,958). v1.1.0 implements the full-development rule and preserves the v1.0.0 behavior in Git history.
2. **WFDB validation.** v1.0.0 checked only sampling frequency. v1.1.0 additionally validates 5,000-sample length, lead names and order (`I, II, III, AVR, AVL, AVF, V1–V6`), mV units, physical-sample status, and pre-normalization finiteness.
3. **OOF bootstrap seed.** The historical frozen paired bootstrap used seed 20260912. v1.0.0 documented a legacy `base_seed + 99` seed and computed configuration intervals with configuration-specific seeds. v1.1.0 uses seed 20260912 for the public OOF paired bootstrap and records the legacy v1.0.0 behavior separately. The frozen historical percentile interval is retained but is not claimed as exactly reproduced.
4. **Figure generation.** v1.0.0 generated three evidence nodes and used "confirmation" wording. v1.1.0 separates development OOF, patient-disjoint calibration, same-source held-out, 100/250 Hz, and STAFF III. Figure 4 now shows the within-patient logit change, matching the final manuscript.

## Interpretation

These are implementation and documentation findings. They do not change the frozen result files. v1.1.0 must not be described as a byte-for-byte restoration of the historical execution environment.

## Unloaded evidence

No patient data, model checkpoints, hidden predictions, or hidden TEST labels are included in this repository. The historical frozen scripts are retained under `provenance/frozen_scripts/` for auditing their exact execution logic.
