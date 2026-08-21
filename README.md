# ECG Lead Information for OMI: Reproducibility Package

Version 1.0.0

This repository contains the analysis code for "The Diagnostic Cost of Reducing ECG Lead Information for High-Sensitivity Detection of Occlusion Myocardial Infarction." It does not contain clinical ECGs, patient metadata, hidden labels, or trained checkpoints.

## Study overview

The study evaluated AI ECG detection of angiography-defined occlusion myocardial infarction (OMI) and compared the diagnostic cost of four prespecified ECG lead-information configurations:

| Configuration | Input information |
| --- | --- |
| C0 | Standard 12-lead ECG |
| C1 | Six limb-information leads: I, II, III, aVR, aVL, aVF |
| C2 | Six precordial leads: V1-V6 |
| C3 | I, II, III |

The primary endpoint was specificity at approximately 95% sensitivity (Spec95). The evidence architecture comprised:

1. Patient-grouped five-fold out-of-fold (OOF) analysis for primary effect estimation.
2. Frozen blind held-out confirmation using provider-controlled labels and aggregate evaluation.
3. STAFF III controlled coronary occlusion analysis of within-patient physiological score changes.

The code preserves the reported preprocessing, model architecture, random seeds, optimization settings, threshold rule, and bootstrap procedures. It is a reproducibility implementation, not a revised model or re-analysis.

## Data access

The datasets are not included in this repository.

The acute coronary syndrome ECG dataset is available through Figshare:  
doi:10.6084/m9.figshare.29925314

STAFF III Database v1.0.0 is available through PhysioNet:  
doi:10.13026/C20P4H

Users must obtain access according to the original data provider policies.

See [docs/data_access.md](docs/data_access.md) for the expected local layout. Hidden test labels and private evaluator responses are not required for OOF reproduction and are not redistributed.

## Installation

Python 3.12.10 is the frozen reference interpreter. Create either environment from the repository root:

```bash
conda env create -f environment.yml
conda activate ecg-lead-omi-reproducibility
```

or:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the virtual environment with `.venv\Scripts\Activate.ps1`.

## Reproduction workflow

All paths in the supplied YAML files are relative to the repository root.

1. Install the environment.
2. Obtain the authorized Figshare and PhysioNet datasets.
3. Place or link the datasets under the paths described in `docs/data_access.md`, or edit the relative paths in each YAML file.
4. Preprocess the clinical development data:

   ```bash
   python -m src.data.preprocessing --config configs/c0_12lead.yaml --split train
   ```

5. Train the four patient-grouped OOF model sets:

   ```bash
   bash scripts/train_models.sh oof
   ```

6. Calculate Spec95, global metrics, and paired bootstrap intervals:

   ```bash
   bash scripts/evaluate_models.sh
   ```

7. Train the frozen 80/20 model-fit/calibration models when local held-out inference or STAFF III analysis is required:

   ```bash
   bash scripts/train_models.sh final
   ```

8. Run STAFF III analysis using authorized local records and the locally generated C0-C3 checkpoints:

   ```bash
   python -m src.evaluation.staffiii --config configs/c0_12lead.yaml
   ```

9. Generate figures from locally produced aggregate analysis files:

   ```bash
   bash scripts/reproduce_figures.sh
   ```

Complete command descriptions, output files, controlled-output warnings, and reproducibility limits are in [docs/reproducibility.md](docs/reproducibility.md).

Release validation results are recorded in [VALIDATION_REPORT.md](VALIDATION_REPORT.md), and publication steps are listed in [docs/release_checklist.md](docs/release_checklist.md).

## Data-free validation

Validate configuration loading, model construction, imports, and a synthetic forward pass without patient data:

```bash
python -m src.training.train --config examples/config_example.yaml --dry-run
python figures/generate_figures.py --dry-run
```

Dry runs do not train a model, estimate performance, or reproduce manuscript results.

## Repository contents

- `configs/`: one frozen YAML configuration for each C0-C3 lead set
- `src/data/`: clinical WFDB loading and deterministic preprocessing
- `src/models/`: frozen CNN definition
- `src/training/`: patient-grouped OOF and final model training
- `src/evaluation/`: metrics, threshold, bootstrap, and STAFF III analysis
- `figures/`: figure generation from local aggregate outputs
- `scripts/`: shell wrappers for the full workflow
- `docs/`: data access and reproducibility instructions
- `provenance/`: frozen analysis specification and source-code checksums

## Reproducibility and privacy boundary

Local outputs can contain patient or record identifiers and must remain under ignored `outputs/`, `models/`, and `data/` directories. Do not commit these directories. The software logs version and configuration information but does not upload data or contact the private blind evaluator.

Deep-learning results can vary across hardware and low-level numerical libraries even with fixed random seeds. The reference versions are pinned, and each command records run metadata to support comparison with the frozen analysis.

## Citation

The reproducibility package for this study is archived on Zenodo:

https://doi.org/10.5281/zenodo.22046832

Please cite the Zenodo release when using this software package. Citation metadata are provided in `CITATION.cff`.

GitHub repository: https://github.com/wzwmm2006/ecg-lead-information-omi

## License

The code is released under the MIT License.
