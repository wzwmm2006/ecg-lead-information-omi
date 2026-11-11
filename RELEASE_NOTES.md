# Release Notes — v1.1.0 Release Candidate

This release has not yet been published. It is a candidate prepared for author review before any GitHub tag, GitHub Release, or Zenodo version is created.

## Scope

v1.1.0 preserves the original clinical question and does not add new model training or new clinical analysis. It adds provenance and executable verification for the revision analyses:

- patient-disjoint A1 calibration with two seeds;
- A2a configuration-local amplitude-preserving preprocessing;
- P3 post hoc matched-TPR interpolation and paired bootstrap;
- 100/250-Hz preprocessing sensitivity;
- source-derived clinical baseline and timing utilities;
- final manuscript table and figure generation.

## Required review before publication

- Read `provenance/V1_0_0_RELEASE_IDENTITY.md`, the audit documents, and the validation report.
- Confirm that no controlled artifacts are included in the release archive.
- Confirm the parent commit and release-history policy with the repository owner.
- Confirm the Zenodo concept record and version chain.
- Do not publish a version-specific DOI until the archived files can be verified.
