#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPOSITORY_ROOT}"

python -m src.evaluation.metrics --config configs/c0_12lead.yaml
python -m src.evaluation.bootstrap --config configs/c0_12lead.yaml

