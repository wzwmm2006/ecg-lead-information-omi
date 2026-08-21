# Existing Project Audit for Public Release

Audit date: 2026-08-21

The private Topic890 workspace was reviewed before this repository was created. The scientific source of truth was `gate_0e_spatial_pilot.py` for clinical OOF analysis, `gate_0f_finalize_and_submit.py` for frozen model finalization and threshold calibration, `gate_0g_staffiii_frozen_triangulation.py` for controlled-occlusion analysis, and `stage_1_evidence_lock.py` plus `stage_1_provenance.py` for result regeneration and provenance.

## Reusable components

- WFDB waveform loading and validation
- fixed 500-to-50-Hz mean downsampling
- per-record, per-lead normalization
- C0-C3 lead selection
- the three-block `TinyECGCNN`
- AdamW training with patient and class weights
- patient-grouped five-fold OOF prediction
- patient-level 80/20 finalization and threshold calibration
- Spec95 threshold selection and diagnostic metrics
- individual and paired patient-level bootstrap procedures
- STAFF III integrity checks, annotation parsing, event selection, resampling, derived limb leads, frozen inference, and within-patient analysis
- final figure generation and SHA-256 provenance

## Cleanup required

The original scripts combined multiple stages, used absolute personal paths, and wrote into private data and result directories. The public implementation separates these responsibilities, resolves only repository-relative configured paths, adds logging and version capture, and prevents evaluator submission. No model architecture, preprocessing rule, threshold rule, seed, optimization setting, exclusion, or statistical procedure was changed.

## Excluded private material

The workspace contains raw Figshare waveforms and metadata, the STAFF III provider release, patient and record identifiers, hidden-test metadata and predictions, private evaluator responses, fold and calibration assignments, patient-level OOF and STAFF III scores, trained checkpoints, institutional files, and prior submission packages. None is included in this repository.

## Missing documentation addressed here

The private workspace lacked a single public installation guide, provider-neutral data layout, configuration schema, controlled-output warning, end-to-end command sequence, data-free dry run, environment lock, code citation, license, release metadata, Zenodo metadata, and public source manifest. These are supplied in `README.md`, `docs/`, the environment files, `CITATION.cff`, `.zenodo.json`, and `provenance/`.

The detailed pre-construction inventory remains in the parent project as `AUDIT_REPORT.md` and identifies every primary script, manifest class, frozen scientific constant, and public-release disposition.
