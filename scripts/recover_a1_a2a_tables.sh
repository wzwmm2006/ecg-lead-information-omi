#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "usage: $0 <project-root-with-authorized-frozen-files>" >&2
  exit 2
fi
python -m src.recovered.a1_a2a.cli --root "$1" --output outputs/recovered/a1_a2a_fold_metrics.csv
