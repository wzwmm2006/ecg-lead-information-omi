# Release Notes - v1.1.0

Version 1.1.0 of the Topic890 reproducibility package accompanies the revised Scientific Reports manuscript. It preserves the original clinical question and adds no new model training or new clinical analysis. Version-specific archival identifiers are recorded only after publication and direct verification.

## Scope

v1.1.0 adds provenance and executable verification for the revision analyses:

- patient-disjoint A1 calibration with two seeds;
- A2a configuration-local amplitude-preserving preprocessing;
- P3 post hoc matched-TPR interpolation and paired bootstrap;
- 100/250-Hz preprocessing sensitivity;
- source-derived clinical baseline and timing utilities;
- table generation helpers, plus figure generators for the package's own aggregate inputs.

## Evidence labels

The package distinguishes four labels:

- `EXECUTABLE_VERIFIED`: a deterministic helper or test ran on synthetic or already-frozen data.
- `FROZEN_OUTPUT_MATCHED`: a supplied artifact byte-matched its recorded SHA-256.
- `PROVENANCE_ONLY`: source or frozen result is retained, but the producing computation was not re-executed.
- `NOT_VERIFIED`: no successful check supports the claim.

## Research boundary

The release does not claim a fresh neural-network refit, byte-identical re-execution, hidden TEST access, STAFF III re-inference, or external clinical validation. The original OOF paired bootstrap interval is retained as historical evidence and is not claimed as exactly reproduced. Figure generators produce package figures from authorized aggregate inputs; pixel-identical reproduction of the final manuscript artwork is not claimed.

## Review

Before citing a version-specific DOI, read `provenance/V1_0_0_RELEASE_IDENTITY.md`, `R2_V1_1_CODE_AUDIT.md`, and `R2_V1_1_VALIDATION_REPORT.md`. Confirm that no controlled artifacts are present and that the Zenodo concept record and version chain resolve as expected.
