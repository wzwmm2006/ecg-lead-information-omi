#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "usage: $0 <project-root-with-authorized-frozen-files>" >&2
  exit 2
fi
python -m src.evaluation.frozen_verification --root "$1" --manifest provenance/FROZEN_OUTPUT_HASHES.json
