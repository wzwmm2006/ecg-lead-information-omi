# ECG Lead Information for OMI: Reproducibility Package

Patch version **1.1.1**. The published v1.1.0 archive is available at `10.5281/zenodo.24126410`. Version 1.1.1 corrects the public P3 patient-cluster bootstrap helper, adds regression tests for sampling and patient multiplicity, and updates release metadata. Its version-specific DOI will be recorded here after archival.

This repository contains the analysis code and provenance for:

*The Specificity Cost of Reducing ECG Lead Information for High-Sensitivity Detection of Occlusion Myocardial Infarction*

It does not contain clinical ECGs, patient metadata, hidden labels, model checkpoints, or row-level predictions.

## Study question and evidence layers

The study compares four prespecified ECG lead-information configurations for AI detection of source-defined angiography-linked occlusion myocardial infarction (OMI):

| Configuration | Input information |
|---|---|
| C0 | Standard 12 leads |
| C1 | Six displayed limb leads: I, II, III, aVR, aVL, aVF |
| C2 | V1-V6 |
| C3 | I, II, III |

C1 and C3 are algebraically related frontal-plane representations. The package does **not** treat them as independent information doses.

The results are organized by threshold source and are not pooled:

1. **Original pooled OOF** — threshold selected and evaluated on the same pooled out-of-fold records. This is a development estimate; its interval includes threshold re-estimation.
2. **A1** — patient-disjoint inner calibration and locked threshold, evaluated once on each outer fold. Two training seeds are included.
3. **A2a** — the same nested design with configuration-local amplitude-preserving preprocessing (one seed).
4. **Same-source blind held-out** — final models fit on a frozen 80/20 model-fit/threshold-calibration split and evaluated once by the provider. Aggregate metrics only; not external validation.
5. **100/250 Hz** — within-rate OOF sensitivity analyses with same-record thresholds, not independent replication.
6. **P3** — post hoc empirical-ROC interpolation at TPR 0.95 with paired patient-within-fold bootstrap; not a deployable threshold.

## Data access

The datasets are not included in this repository.

- Acute coronary syndrome ECG dataset: doi:10.6084/m9.figshare.29925314
- STAFF III Database v1.0.0: doi:10.13026/C20P4H

Users must obtain access under the original providers' terms. Hidden TEST labels and private evaluator responses are not redistributed.

See [docs/data_access.md](docs/data_access.md) for the expected local layout.

## Installation

The frozen reference interpreter is Python 3.12.10.

```bash
conda env create -f environment.yml
conda activate ecg-lead-omi-reproducibility
```

Or:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Data-free validation

```bash
python -m pytest -q
python -m src.training.train --config examples/config_example.yaml --dry-run
python figures/generate_figures.py --dry-run
python -m src.evaluation.frozen_verification --help
```

The data-free tests do not train a model or reproduce manuscript results.

## Original OOF workflow

```bash
python -m src.data.preprocessing --config configs/c0_12lead.yaml --split train
bash scripts/train_models.sh oof
bash scripts/evaluate_models.sh
```

The OOF class weights are computed once from the complete development frame before the fold loop, matching both the official v1.0.0 tag and the historical frozen executor (1,151 OMI / 17,958 ECG; recomputed maximum absolute difference 0.0). The final 80/20 path calls the same function on its model-fit subset, which is a separate estimand and not the OOF rule. See [provenance/V1_0_0_RELEASE_IDENTITY.md](provenance/V1_0_0_RELEASE_IDENTITY.md).

## Frozen revision workflows

The original revision scripts are preserved under `provenance/frozen_scripts/` as sanitized public copies, with a sanitization record and original/public hash fingerprints. Their outputs can be checked against `provenance/FROZEN_OUTPUT_HASHES.json`.

```bash
bash scripts/verify_frozen_outputs.sh /path/to/authorized-frozen-project
bash scripts/recover_p3_tables.sh /path/to/authorized-frozen-project
bash scripts/summarize_sampling_sensitivity.sh /path/to/authorized-frozen-project
```

A matching hash is classified `FROZEN_OUTPUT_MATCHED`. It does not mean that a model was retrained. Executable helpers for synthetic and deterministic checks are classified separately in `provenance/VALIDATION_STATUS.md`. Do not publish patient identifiers, predictions, checkpoints, or local run metadata.

## Figures

`python figures/generate_figures.py` reads authorized local aggregate files. Figure 1 separates the evidence layers. Figure 2 shows the development OOF specificity. Figure 3 is generated only from an authorized same-source held-out aggregate file. Figure 4 shows the within-patient logit change from STAFF III baseline to occlusion.

## Repository contents

- `configs/`: frozen C0-C3 configurations
- `src/data/`: preprocessing, WFDB validation, frozen-label constants
- `src/models/`: fixed CNN definition
- `src/training/`: OOF and finalization code
- `src/evaluation/`: metrics, threshold selection, bootstrap, held-out aggregate utilities
- `src/recovered/`: auditable A1/A2a, P3, and sampling helpers; historical scripts remain under `provenance/`
- `figures/`: figure generation
- `scripts/`: workflow wrappers
- `tests/`: data-free unit and synthetic tests
- `provenance/`: release identity, frozen scripts, protocols, and output hashes

## Reproducibility boundary

Exact neural-network weights can vary across hardware, CUDA/cuDNN, and low-level numerical kernels even with fixed seeds. The package records versions and provenance, but it does not claim byte-identical refits or reproduction of hidden TEST. Patient-level intermediates must remain in ignored local directories.

## Citation and license

Cite the Zenodo version DOI corresponding to the release used. `CITATION.cff` carries the v1.1.0 version DOI and the concept DOI, repository, version, and software extent; `CODE_AVAILABILITY.md` lists the published archival identifiers and will list the v1.1.1 DOI after archival. The code is released under the MIT License.
