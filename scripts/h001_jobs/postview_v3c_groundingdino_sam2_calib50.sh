#!/usr/bin/env zsh
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
IMAGE=${IMAGE:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
FRAMES=${FRAMES:-/tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-/tmp/research3-models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-/tmp/research3-models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
OUT=${OUT:-/tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_calib50_gpu}
DEVICE=${DEVICE:-cuda}
MAX_FRAMES=${MAX_FRAMES:-50}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-2}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
LOG=${LOG:-$ROOT/archive/logs/root/postview-evidence-v3c-groundingdino-sam2-calib50-$(date +%Y%m%d-%H%M%S).log}
STATUS="$OUT/job_status.json"

mkdir -p "$ROOT/archive/logs/root" "$OUT"
exec > >(tee -a "$LOG") 2>&1

to_runs_path() {
  local path="$1"
  if [[ "$path" == /tmp/research3-runs/* ]]; then
    echo "/runs/${path#/tmp/research3-runs/}"
  else
    echo "$path"
  fi
}

FRAMES_CONTAINER="$(to_runs_path "$FRAMES")"
CANDIDATE_ARTIFACT_CONTAINER="$(to_runs_path "$CANDIDATE_ARTIFACT")"
OUT_CONTAINER="$(to_runs_path "$OUT")"

write_status() {
  local job_state="$1"
  local stage="$2"
  local now
  now="$(date -Is)"
  printf '{"status":"%s","stage":"%s","updated_at":"%s","image":"%s","device":"%s","frames":"%s","candidate_artifact":"%s","groundingdino_dir":"%s","sam2_checkpoint":"%s","output_root":"%s","log":"%s"}\n' \
    "$job_state" "$stage" "$now" "$IMAGE" "$DEVICE" "$FRAMES" "$CANDIDATE_ARTIFACT" "$GROUNDINGDINO_DIR" "$SAM2_CHECKPOINT" "$OUT" "$LOG" > "$STATUS"
}

on_error() {
  local code="$?"
  write_status failed "${CURRENT_STAGE:-unknown}"
  echo "failed_stage=${CURRENT_STAGE:-unknown}"
  echo "exit_code=$code"
  exit "$code"
}
trap on_error ERR

cd "$ROOT"
echo "started_at=$(date -Is)"
echo "image=$IMAGE"
echo "device=$DEVICE"
echo "frames=$FRAMES"
echo "candidate_artifact=$CANDIDATE_ARTIFACT"
echo "groundingdino_dir=$GROUNDINGDINO_DIR"
echo "sam2_checkpoint=$SAM2_CHECKPOINT"
echo "output_root=$OUT"
echo "log=$LOG"
echo "verification_command=cat $OUT/summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "$CURRENT_STAGE"
python - <<PY
from pathlib import Path
paths = {
    "frames": Path("$FRAMES"),
    "candidate_artifact": Path("$CANDIDATE_ARTIFACT"),
    "groundingdino_config": Path("$GROUNDINGDINO_DIR") / "config.json",
    "groundingdino_weights": Path("$GROUNDINGDINO_DIR") / "model.safetensors",
    "sam2_checkpoint": Path("$SAM2_CHECKPOINT"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
print({"stage": "prerequisite_check_passed", "paths": {name: str(path) for name, path in paths.items()}})
PY

if [[ "$DEVICE" == "cuda" ]]; then
  GPU_FLAG="--gpus all"
else
  GPU_FLAG=""
fi

CURRENT_STAGE=detector_mask_scoring
write_status running "$CURRENT_STAGE"
sg docker -c "docker run --rm $GPU_FLAG \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONPATH=/workspace/src \
  -v /home/yoohyun/research3:/workspace \
  -v /tmp/research3-runs:/runs \
  -v /tmp/research3-models:/models \
  -w /workspace \
  $IMAGE \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames $FRAMES_CONTAINER \
    --candidate-artifact $CANDIDATE_ARTIFACT_CONTAINER \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root $OUT_CONTAINER \
    --debug-root $OUT_CONTAINER/debug_images \
    --device $DEVICE \
    --max-frames $MAX_FRAMES \
    --max-headings-per-frame $MAX_HEADINGS_PER_FRAME \
    --max-detector-boxes-per-heading $MAX_DETECTOR_BOXES_PER_HEADING \
    --max-masks-per-heading $MAX_MASKS_PER_HEADING \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 5 \
    --candidate-point-field position \
    --box-threshold 0.10 \
    --text-threshold 0.10 \
    --query-template 'a photo of a {query}.' \
    --box-padding-px 4 \
    --association-depth-tolerance-m 1.0 \
    --max-debug-images 80"

CURRENT_STAGE=verification
write_status running "$CURRENT_STAGE"
python - <<PY
import json
from pathlib import Path
root = Path("$OUT")
summary = json.loads((root / "summary.json").read_text())
assert summary["rows"] == int("$MAX_FRAMES"), summary
assert summary["uses_gt_for_action"] is False, summary
assert summary["rows_with_detector_box_rate"] >= 0.80, summary
assert summary["rows_with_sam2_mask_rate"] >= 0.80, summary
assert summary["rows_with_candidate_association_rate"] >= 0.60, summary
print({
    "stage": "verification_passed",
    "rows": summary["rows"],
    "rows_with_detector_box_rate": summary["rows_with_detector_box_rate"],
    "rows_with_sam2_mask_rate": summary["rows_with_sam2_mask_rate"],
    "rows_with_candidate_association_rate": summary["rows_with_candidate_association_rate"],
    "associated_candidate_heading_count": summary["associated_candidate_heading_count"],
})
PY

CURRENT_STAGE=verified
write_status completed "$CURRENT_STAGE"
echo "completed_at=$(date -Is)"
