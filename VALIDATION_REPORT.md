# Release Validation Report

Validation date: 2026-08-21

## Passed checks

- Repository structure: all requested top-level files, configurations, source modules, workflow scripts, figure generator, documentation, example configuration, release metadata, and provenance specification are present.
- Python syntax: all 19 Python files compiled in memory without errors.
- Imports: data, model, training, evaluation, STAFF III, figure, and provenance modules imported successfully.
- Core tests: 4/4 passed for C0-C3 lead indices, preprocessing shape and scaling, threshold selection, and CNN output shape.
- Configuration validation: C0-C3 resolve to the frozen lead indices and all configured filesystem paths are relative.
- Model dry run: the example configuration produced a finite two-record synthetic forward pass with input shape `(2, 12, 500)` and output shape `(2,)`.
- Figure dry run: Matplotlib rendered a synthetic PNG in memory.
- Dependency resolution: `pip install --dry-run -r requirements.txt` resolved every pinned dependency without changing the environment.
- Metadata parsing: `CITATION.cff`, `environment.yml`, all YAML configurations, and `.zenodo.json` parsed successfully.
- Release-boundary scan: no personal absolute path, private evaluator endpoint, patient data file, trained checkpoint, waveform file, or patient-level output is present.

## Environment notes

The validation host used Python 3.14.3 with NumPy 2.4.2, pandas 2.3.3, SciPy 1.17.1, scikit-learn 1.8.0, Torch 2.13.0+cu126, WFDB 4.3.1, and Matplotlib 3.11.1. The release environment pins the frozen reference Python 3.12.10 and Torch 2.12.1 environment. Dependency resolution confirmed that the pinned packages are available, but the current host environment was not modified.

`bash` was not installed on the Windows validation host, so `bash -n` could not be executed. The three shell files are thin POSIX Bash wrappers around Python entry points; the underlying entry points passed syntax, import, and dry-run checks.

## Checks intentionally not run

No patient-data preprocessing, model training, hidden-test inference, bootstrap re-estimation, STAFF III inference, or manuscript-result recalculation was run. Those operations require controlled datasets and would constitute a scientific rerun outside this repository-packaging task. Authorized users can execute them using the documented workflow.

