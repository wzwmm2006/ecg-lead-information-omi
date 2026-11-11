# Changelog

## 1.1.1 - Patch under preparation

- Corrected `src/recovered/p3/bootstrap.py`: each fold now has a persistent random stream that advances across bootstrap replicates.
- Preserved all ECG rows and repeated patient selections, using patient multiplicity rather than collapsing sampled patients through a pivot.
- Weighted folds by the original non-OMI ECG count and retained incomplete replicates as explicit invalid outcomes.
- Added synthetic regression tests for varying draws, patient multiplicity, fixed-seed replay, non-degenerate interval width, and explicit all-invalid handling.
- Verified the corrected bootstrap in read-only mode against the frozen P3 predictions: all nine point estimates matched; a 2,000-replicate replay kept every interval endpoint within 0.00875 and retained the 2/9 intervals excluding zero.
- Updated the README, code availability statement, release checklist, citation metadata, internal validation references, and Zenodo metadata for the v1.1.1 patch.
- Corrected stale version-DOI and release-status text in the repository; the v1.1.0 Git tag and Zenodo record remain unchanged.

## 1.1.0 - Released

- Updated the title to the final R2 manuscript title.
- Separated original pooled OOF, patient-disjoint A1/A2a calibration, same-source held-out, 100/250-Hz sensitivity, and post hoc P3 evidence layers.
- Added sanitized historical revision scripts under `provenance/frozen_scripts/`, with original-source and sanitized SHA-256 fingerprints.
- Added frozen protocols and output-hash manifests under `provenance/`.
- Corrected the class-weight audit: v1.0.0 and the historical frozen executor both compute class prevalence over the complete development frame before the OOF loop, and v1.1.0 keeps that behavior unchanged.
- Made the weighting path explicit (`prevalence = labels.mean()` on the supplied frame); removed a redundant forced full-development constant introduced during the audit.
- Documented one remaining v1.0.0 implementation difference: incomplete WFDB lead/length validation.
- Expanded WFDB lead/order/length/unit/physical-signal validation.
- Added deterministic A1/A2a split and A2a centering helpers, P3 ROC interpolation and bootstrap helpers, and sampling-rate preprocessing helpers.
- Updated Figure 1 to separate evidence layers and Figure 4 to show within-patient logit change.
- Added data-free and synthetic-data unit tests.
- Added a read-only frozen-output hash verifier.
- Preserved v1.0.0 code in Git history; no data, model weights, or row-level predictions were added.
