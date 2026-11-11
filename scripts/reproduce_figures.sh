#!/usr/bin/env bash
set -euo pipefail
python figures/generate_figures.py --config configs/c0_12lead.yaml "$@"
