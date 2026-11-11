#!/usr/bin/env bash
set -euo pipefail
mode="${1:-oof}"
for config in configs/c0_12lead.yaml configs/c1_limb.yaml configs/c2_precordial.yaml configs/c3_i_ii_iii.yaml; do
  python -m src.training.train --config "$config" --mode "$mode"
done
