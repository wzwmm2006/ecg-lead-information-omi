#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-oof}"
if [[ "${MODE}" != "oof" && "${MODE}" != "final" && "${MODE}" != "predict" ]]; then
  echo "Usage: $0 [oof|final|predict]" >&2
  exit 2
fi

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPOSITORY_ROOT}"

for CONFIG in \
  configs/c0_12lead.yaml \
  configs/c1_limb.yaml \
  configs/c2_precordial.yaml \
  configs/c3_i_ii_iii.yaml; do
  python -m src.training.train --config "${CONFIG}" --mode "${MODE}"
done

