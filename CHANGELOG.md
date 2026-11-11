# Changelog

## 1.1.0 — Release candidate (2026-11-11)

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
