#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKER_DIR="$ROOT_DIR/configs/docker"
OUTPUT_ROOT="${OUTPUT_ROOT:-$ROOT_DIR/local_dataset/runs/openvocab_perception_v3c_groundingdino_sam2_setup}"
MODEL_BASE="${MODEL_BASE:-$ROOT_DIR/local_dataset/models}"
MODEL_ROOT="$MODEL_BASE/openvocab"
GDINO_MODEL_ID="IDEA-Research/grounding-dino-tiny"
GDINO_DIR="$MODEL_ROOT/groundingdino/IDEA-Research_grounding-dino-tiny"
SAM2_DIR="$MODEL_ROOT/sam2/sam2.1_hiera_tiny"
SAM2_CKPT="$SAM2_DIR/sam2.1_hiera_tiny.pt"
SAM2_CKPT_URL="https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt"
IMAGE="research3/openvocab-perception:20260513-v3c-gdino-sam2"
STATUS_FILE="$OUTPUT_ROOT/job_status.json"
LOG_FILE="${LOG_FILE:-$ROOT_DIR/archive/logs/root/openvocab-perception-v3c-groundingdino-sam2-$(date +%Y%m%d-%H%M%S).log}"

mkdir -p "$OUTPUT_ROOT" "$GDINO_DIR" "$SAM2_DIR" "$(dirname "$LOG_FILE")"

write_status() {
  local status="$1"
  local stage="$2"
  python - "$STATUS_FILE" "$status" "$stage" "$IMAGE" "$GDINO_MODEL_ID" "$GDINO_DIR" "$SAM2_CKPT" "$OUTPUT_ROOT" "$LOG_FILE" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

status_path, status, stage, image, gdino_model_id, gdino_dir, sam2_ckpt, output_root, log_file = sys.argv[1:]
payload = {
    "status": status,
    "stage": stage,
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "image": image,
    "groundingdino_model_id": gdino_model_id,
    "groundingdino_dir": gdino_dir,
    "sam2_checkpoint": sam2_ckpt,
    "output_root": output_root,
    "log": log_file,
}
Path(status_path).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
PY
}

on_error() {
  local exit_code="$?"
  write_status "failed" "${CURRENT_STAGE:-unknown}"
  echo "failed_stage=${CURRENT_STAGE:-unknown}"
  echo "exit_code=$exit_code"
  exit "$exit_code"
}
trap on_error ERR

exec > >(tee -a "$LOG_FILE") 2>&1

echo "working_directory=$ROOT_DIR"
echo "docker_dir=$DOCKER_DIR"
echo "output_root=$OUTPUT_ROOT"
echo "image=$IMAGE"
echo "groundingdino_model_id=$GDINO_MODEL_ID"
echo "groundingdino_dir=$GDINO_DIR"
echo "sam2_checkpoint=$SAM2_CKPT"
echo "sam2_checkpoint_url=$SAM2_CKPT_URL"
echo "verification_command=docker run offline import/load check for GroundingDINO and SAM2"

CURRENT_STAGE="build_image"
write_status "running" "$CURRENT_STAGE"
sg docker -c "docker build -f '$DOCKER_DIR/Dockerfile.openvocab-perception-v3c' -t '$IMAGE' '$ROOT_DIR'"

CURRENT_STAGE="verify_imports"
write_status "running" "$CURRENT_STAGE"
sg docker -c "docker run --rm \
  -e HF_HOME=/models/.cache/huggingface \
  -v '$MODEL_BASE':/models \
  '$IMAGE' \
  python - <<'PY'
import cv2
import numpy
import PIL
import torch
import transformers
from transformers import AutoProcessor, GroundingDinoForObjectDetection
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
print({
    'status': 'imports_ok',
    'torch': torch.__version__,
    'transformers': transformers.__version__,
})
PY"

CURRENT_STAGE="download_groundingdino"
write_status "running" "$CURRENT_STAGE"
sg docker -c "docker run --rm \
  -e HF_HOME=/models/.cache/huggingface \
  -v '$MODEL_BASE':/models \
  '$IMAGE' \
  huggingface-cli download '$GDINO_MODEL_ID' \
    --local-dir '/models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny' \
    --local-dir-use-symlinks False"

CURRENT_STAGE="download_sam2"
write_status "running" "$CURRENT_STAGE"
sg docker -c "docker run --rm \
  -v '$MODEL_BASE':/models \
  '$IMAGE' \
  bash -lc 'mkdir -p /models/openvocab/sam2/sam2.1_hiera_tiny && wget -c \"$SAM2_CKPT_URL\" -O /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt'"

CURRENT_STAGE="verify_offline_load"
write_status "running" "$CURRENT_STAGE"
sg docker -c "docker run --rm \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e HF_HOME=/models/.cache/huggingface \
  -v '$MODEL_BASE':/models \
  '$IMAGE' \
  python - <<'PY'
from pathlib import Path

import torch
from transformers import AutoProcessor, GroundingDinoForObjectDetection
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

gdino_dir = Path('/models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny')
sam2_ckpt = Path('/models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt')

processor = AutoProcessor.from_pretrained(str(gdino_dir), local_files_only=True)
model = GroundingDinoForObjectDetection.from_pretrained(str(gdino_dir), local_files_only=True)
sam2_model = build_sam2('configs/sam2.1/sam2.1_hiera_t.yaml', str(sam2_ckpt), device='cpu', mode='eval')
predictor = SAM2ImagePredictor(sam2_model)

print({
    'status': 'v3c_offline_load_ok',
    'groundingdino_processor': processor.__class__.__name__,
    'groundingdino_model': model.__class__.__name__,
    'sam2_predictor': predictor.__class__.__name__,
    'sam2_checkpoint_exists': sam2_ckpt.exists(),
    'torch': torch.__version__,
})
PY"

write_status "completed" "verified"
echo "completed"
