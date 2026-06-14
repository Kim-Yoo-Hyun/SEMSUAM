#!/usr/bin/env bash
set -euo pipefail

IMG="${IMG:-research3/openvocab-perception:20260513-v3c-gdino-sam2}"
OUT_ROOT="${OUT_ROOT:-local_dataset/runs/h001_fully_covered_candidate_conditioned_contrast_v1}"

mkdir -p local_dataset/runs

docker run --rm --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/src \
  -v "$PWD":/workspace:ro \
  -v "$PWD/local_dataset/runs":/runs \
  -w /workspace \
  "$IMG" \
  python -B -m h001_runtime.materialize_fully_covered_candidate_conditioned_contrast \
  --contract configs/h001/manifests/h001_fully_covered_candidate_conditioned_contrast_v1.json \
  --out-root "/runs/${OUT_ROOT#local_dataset/runs/}"
