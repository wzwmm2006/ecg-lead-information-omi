"""Constants fixed by the historical Topic890 analysis."""

from __future__ import annotations

# Readable labelled development cohort after excluding records 03228 and 14262.
DEVELOPMENT_ECGS = 17958
DEVELOPMENT_OMI_ECGS = 1151
DEVELOPMENT_NON_OMI_ECGS = 16807
DEVELOPMENT_PATIENTS = 17016
DEVELOPMENT_OMI_PATIENTS = 1139

# The original implementation multiplied the inverse-patient-count weight by
# class weights computed from the complete development label distribution,
# not from an individual training fold.
full_development_prevalence = DEVELOPMENT_OMI_ECGS / DEVELOPMENT_ECGS

# OOF bootstrap: patients are resampled with all their ECGs; thresholds are
# re-estimated in each replicate on the same evaluated OOF records.
OOF_BOOTSTRAP_REPLICATES = 1000
OOF_BOOTSTRAP_SEED = 20260912

# A1/A2a nested calibration target and the A2a amplitude scale.
TARGET_SENSITIVITY = 0.95
A2A_FIXED_SCALE_MV = 1.0

# Final 80/20 model-fit/threshold-calibration thresholds, frozen before TEST.
FINALIZATION_THRESHOLDS = {
    "C0": 0.008731307461857796,
    "C1": 0.2916659414768219,
    "C2": 0.5712791681289673,
    "C3": 0.0029015361797064543,
}

# Original pooled OOF empirical thresholds (same-record threshold selection).
ORIGINAL_OOF_THRESHOLDS = {
    "C0": 0.0007638259558007,
    "C1": 0.00004500634167925455,
    "C2": 0.0045852931216359,
    "C3": 0.0009411954088136,
}
