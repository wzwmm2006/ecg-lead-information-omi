# Data Access

The public package does not redistribute patient data, ECG waveforms, model weights, row-level predictions, private evaluator outputs, or hidden labels.

## Clinical dataset

Dataset: *A large-scale 12-lead electrocardiogram dataset for acute coronary syndrome prediction containing 19,955 ECGs*

- DOI: `10.6084/m9.figshare.29925314`
- Content required: released `train.csv`, `test.csv`, and the corresponding WFDB waveforms.
- Access and reuse are governed by the provider's terms.

The historical analysis cohort retained 17,958 readable development ECGs from 17,016 patients after excluding two unreadable records. It used 1,151 OMI ECGs from 1,139 OMI patients.

## STAFF III

STAFF III Database v1.0.0:

- DOI: `10.13026/C20P4H`
- PhysioNet page: https://physionet.org/content/staff-iii/1.0.0/

The package has no STAFF III data and does not rerun inference.

## Expected local layout for OOF reproduction

Paths in the YAML files are repository-relative:

```text
data/figshare/train.csv
data/figshare/test.csv
data/figshare/waveforms/00001.dat
data/figshare/waveforms/00001.hea
...
data/processed/train_waveforms.npy
data/processed/train_waveforms.index.csv
```

Do not commit any of these files. They may contain controlled identifiers.

## Frozen-output checks against an existing authorized project

If an investigator already has the frozen results in a private project directory, the source hashes can be checked without copying those files into the repository:

```bash
bash scripts/verify_frozen_outputs.sh /path/to/authorized-frozen-project
```

Only aggregate files described in `provenance/FROZEN_OUTPUT_HASHES.json` are checked. The hash manifest does not include raw waveforms or model checkpoints.

## Website and archive checks

The corresponding author must verify the live Figshare, PhysioNet, GitHub, and Zenodo records before submission. This package does not embed private evaluator credentials or invoke the evaluator.
