#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "usage: $0 <project-root-with-authorized-frozen-files>" >&2
  exit 2
fi
python -m src.recovered.p3.cli --root "$1" --output outputs/recovered/p3_matched_tpr.csv
