# Data Access and Local Layout

## Redistribution boundary

The public repository contains code only. Do not commit or redistribute patient ECG waveforms, patient identifiers, source metadata, hidden test labels, Figshare raw files, PhysioNet raw files, restricted spreadsheets, provider-controlled evaluator responses, or institutional files.

## Clinical acute coronary syndrome ECG data

Obtain the dataset from Figshare under the provider's terms:

- DOI: `10.6084/m9.figshare.29925314`

The default configurations expect:

```text
data/
  figshare/
    train.csv
    test.csv
    waveforms/
      00001.hea
      00001.dat
      ...
```

The development metadata must provide `ecg_row_record`, `Patient_id`, and `OMI`. The original analysis also used artery columns for exploratory summaries, but they are not required for the primary C0-C3 Spec95 workflow. The hidden-test metadata are used only to preserve provider row order during authorized local inference; hidden disease labels are neither expected nor read.

Waveform basenames are derived from `ecg_row_record`, zero-padded to five digits, and loaded as WFDB records. Each readable clinical record must contain 12 leads, 5,000 samples per lead, and a sampling rate of 500 Hz.

The frozen analysis excluded exactly two unreadable development records, `03228` and `14262`. The IDs are listed in the YAML configurations so the public pipeline reproduces the same cohort construction.

## STAFF III

Obtain STAFF III Database v1.0.0 from PhysioNet under the provider's terms:

- DOI: `10.13026/C20P4H`

The default configuration expects the provider release without renamed files:

```text
data/
  staffiii-1.0.0/
    RECORDS
    SHA256SUMS.txt
    STAFF-III-Database-Annotations.xlsx
    data/
      001a.hea
      001a.dat
      ...
```

The STAFF III command verifies provider checksums when `SHA256SUMS.txt` is present. It reads the provider spreadsheet locally, applies the frozen event-selection rule, and writes patient-level outputs only to the ignored `outputs/` directory.

## Alternative locations

Dataset paths may be changed in the YAML files, but they must remain relative to the repository root. Symbolic links inside `data/` may point to authorized storage when supported by the operating system. The configuration loader rejects absolute paths to prevent accidental publication of personal directories.

