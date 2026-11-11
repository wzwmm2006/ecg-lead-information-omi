# Validation Report — v1.1.0 Release Candidate

## Data-free validation

| Check | Result |
|---|---|
| Python syntax compilation of `src/**/*.py` | PASS |
| Import of data, model, evaluation, recovered, and figure modules | PASS |
| Unit/synthetic tests | 13 passed |
| Model forward dry run | PASS |
| Figure rendering dry run | PASS |
| Metadata YAML/JSON parsing | PASS |

## Frozen-output verification

`src.evaluation.frozen_verification` checked the 16 files in `provenance/FROZEN_OUTPUT_HASHES.json`. All 16 matched. This result is classified `FROZEN_OUTPUT_MATCHED`.

## Deterministic result checks

| Check | Classification | Result |
|---|---|---|
| Original OOF AUROC/AUPRC from stored probabilities | EXECUTABLE_VERIFIED + FROZEN_OUTPUT_MATCHED | all point estimates match exactly or to floating-point precision |
| A1/A2a 60 rows: TP/FP/TN/FN recomputed from probabilities at stored thresholds | EXECUTABLE_VERIFIED | all 60 counts match; zero deltas |
| A1/A2a sensitivity range | EXECUTABLE_VERIFIED | 0.900000 to 0.982684 |
| OOF class weights: official v1.0.0 vs. frozen executor vs. RC | EXECUTABLE_VERIFIED + FROZEN_OUTPUT_MATCHED | three-way exact equality; maximum absolute difference 0.0 |
| P3 60 rows: ROC interpolation at TPR 0.95 | EXECUTABLE_VERIFIED + FROZEN_OUTPUT_MATCHED | maximum absolute difference 8.33e-17 |
| P3 nine bootstrap intervals | PROVENANCE_ONLY | frozen intervals retained; not replayed |
| Original OOF paired bootstrap interval | NOT_VERIFIED | patient/threshold code implemented; the exact frozen percentile interval was not reproduced and is not claimed |
| 100/250 Hz results | FROZEN_OUTPUT_MATCHED (output files); PROVENANCE_ONLY (training) | output hashes match; no retraining |
| Held-out aggregate metrics | FROZEN_OUTPUT_MATCHED for source file | no evaluator access |
| STAFF III | PROVENANCE_ONLY | no inference |

## Release meaning

A `FROZEN_OUTPUT_MATCHED` result shows that an authorized local file is byte-identical to the hash recorded for the revision. It does not prove that a fresh neural-network training run would reproduce the file.

## Remaining release conditions

- Author approval of the candidate archive.
- The v1.0.0 tag identity question is resolved: the official tag resolves to commit `5b75a385b9c69d467005527f93c0f92aa78cd61a` both remotely and locally, and was fetched rather than recreated. Zenodo v1.0.0 archive contents remain to be checked against that commit before v1.1.0 is archived.
- Verification of the concept and version DOI records.
- Verification that the GitHub/Zenodo archive contains the same commit and versioned metadata.
