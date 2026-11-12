# Release Notes - v1.1.1

Version 1.1.1 is a patch to the Topic890 reproducibility package. It corrects the public P3 patient-cluster bootstrap helper and release metadata; it does not retrain a model, rerun inference, or recompute the manuscript's frozen P3 confidence intervals.

## Corrections

- **P3 bootstrap sampling.** v1.1.0 reset a fold-specific RNG inside every replicate, so successive replicates could draw identical patients. The corrected helper uses one persistent random stream per fold that advances across replicates.
- **Patient multiplicity.** The corrected helper samples patients with replacement and retains every ECG row of each selected patient, including repeated patient selections. It no longer collapses repeated patients through a pivot.
- **Fold weighting.** Fold weights use the original non-OMI ECG count, as in the frozen P3 analysis plan.
- **Invalid replicates.** Incomplete replicates are counted and reported rather than entering percentile intervals.
- **Regression tests.** Synthetic-data tests check varying replicate draws, patient multiplicity, deterministic replay with a fixed seed, non-degenerate interval width, and explicit reporting when no replicate is valid.
- **Release metadata.** The README, code availability statement, release checklist, citation metadata, and internal report references now match the published v1.1.0 archive and the v1.1.1 patch.

## Published identity

| Item | Value |
|---|---|
| v1.1.0 GitHub tag | `v1.1.0` |
| v1.1.0 commit | `6064e366bb853c3557b89189c783d6568b69a391` |
| v1.1.0 Zenodo DOI | `10.5281/zenodo.24126410` |
| v1.1.1 GitHub tag | `v1.1.1` |
| v1.1.1 GitHub commit | `0f73c396e245e91ba20a1e47e8ea95c5d77d809f` |
| v1.1.1 Zenodo DOI | `10.5281/zenodo.24132879` |
| v1.1.1 Zenodo record | https://zenodo.org/records/24132879 |
| Zenodo concept DOI | `10.5281/zenodo.22046832` |

The v1.1.0 tag and Zenodo record remain unchanged. The v1.1.0 public P3 bootstrap helper is defective; use the v1.1.1 helper for patient-cluster bootstrap.

Zenodo record 24132879 is published as version 1.1.1 and contains `wzwmm2006/ecg-lead-information-omi-v1.1.1.zip` (159,790 bytes; MD5 `deeff03a034d4b503df4e6a13f89f12b`; SHA-256 `4f6ccaa5b53e496dfa28d926cd1030e7d2f10e3f7d0720f0951b099d537fc5b6`). The immutable GitHub tag `v1.1.1` was created before the version DOI was assigned; its snapshot retains the v1.1.0 DOI in `CITATION.cff` and `CODE_AVAILABILITY.md`. The public `main` branch and this Release record identify the archived v1.1.1 DOI. The tag and Zenodo archive were not rewritten.

## Research boundary

The P3 point estimates and the frozen nine confidence intervals are retained as historical results from `provenance/frozen_scripts/P3_MATCHED_SENSITIVITY_ANALYSIS.py`. A read-only 2,000-replicate replay from the frozen predictions reproduced all nine point estimates and kept every confidence-interval endpoint within 0.00875; 2/9 intervals excluded zero in both the frozen and replayed results. The corrected helper implements the public, auditable path for applying the same patient-within-fold sampling and non-OMI ECG weighting. The package does not claim a new neural-network fit, hidden TEST access, STAFF III re-inference, or external clinical validation. Figure generators use authorized aggregate inputs and do not claim pixel-exact reproduction of manuscript artwork.

## Evidence labels

- `EXECUTABLE_VERIFIED`: a deterministic helper or test ran on synthetic or already-frozen data.
- `FROZEN_OUTPUT_MATCHED`: a supplied artifact byte-matched its recorded SHA-256.
- `PROVENANCE_ONLY`: source or frozen result is retained, but the producing computation was not re-executed.
- `NOT_VERIFIED`: no successful check supports the claim.

## Review

Read `provenance/VALIDATION_STATUS.md`, `provenance/V1_0_0_RELEASE_IDENTITY.md`, and the external project release record. Confirm that no controlled artifacts are present and that the Zenodo concept record and version chain resolve as expected.