#!/usr/bin/env zsh
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
IMAGE=${IMAGE:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
FRAMES=${FRAMES:-/tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-/tmp/research3-models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-/tmp/research3-models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
ABLATION_NAME=${ABLATION_NAME:-A1_query_only_prompt}
OUT=${OUT:-/tmp/research3-runs/h001_postview_detector_v3c_${ABLATION_NAME}_smoke}
MAX_FRAMES=${MAX_FRAMES:-12}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-2}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-position}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
MAX_DEBUG_IMAGES=${MAX_DEBUG_IMAGES:-40}
PROMOTION_ASSOCIATION_RATE=${PROMOTION_ASSOCIATION_RATE:-0.50}
LOG=${LOG:-$ROOT/logs/postview-evidence-v3c-${ABLATION_NAME:l}-$(date +%Y%m%d-%H%M%S).log}
STATUS="$OUT/job_status.json"

mkdir -p "$ROOT/logs" "$OUT"
exec > >(tee -a "$LOG") 2>&1

write_status() {
  local job_state="$1"
  local stage="$2"
  local now
  now="$(date -Is)"
  python - "$STATUS" <<PY
import json
import sys
from pathlib import Path

status_path = Path(sys.argv[1])
payload = {
    "status": "$job_state",
    "stage": "$stage",
    "updated_at": "$now",
    "ablation": "$ABLATION_NAME",
    "image": "$IMAGE",
    "device": "$DEVICE",
    "frames": "$FRAMES",
    "candidate_artifact": "$CANDIDATE_ARTIFACT",
    "groundingdino_dir": "$GROUNDINGDINO_DIR",
    "sam2_checkpoint": "$SAM2_CHECKPOINT",
    "output_root": "$OUT",
    "log": "$LOG",
    "max_frames": int("$MAX_FRAMES"),
    "max_headings_per_frame": int("$MAX_HEADINGS_PER_FRAME"),
    "candidate_point_field": "$CANDIDATE_POINT_FIELD",
    "query_template": "$QUERY_TEMPLATE",
}
status_path.parent.mkdir(parents=True, exist_ok=True)
status_path.write_text(json.dumps(payload, ensure_ascii=False) + "\\n", encoding="utf-8")
PY
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
echo "ablation=$ABLATION_NAME"
echo "image=$IMAGE"
echo "device=$DEVICE"
echo "frames=$FRAMES"
echo "candidate_artifact=$CANDIDATE_ARTIFACT"
echo "groundingdino_dir=$GROUNDINGDINO_DIR"
echo "sam2_checkpoint=$SAM2_CHECKPOINT"
echo "output_root=$OUT"
echo "log=$LOG"
echo "query_template=$QUERY_TEMPLATE"
echo "max_headings_per_frame=$MAX_HEADINGS_PER_FRAME"
echo "candidate_point_field=$CANDIDATE_POINT_FIELD"
echo "verification_command=cat $OUT/job_status.json && cat $OUT/summary.json"

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
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace \
  -v /tmp/research3-runs:/runs \
  -v /tmp/research3-models:/models \
  -w /workspace \
  $IMAGE \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames /runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root /runs/$(basename "$OUT") \
    --debug-root /runs/$(basename "$OUT")/debug_images \
    --device $DEVICE \
    --max-frames $MAX_FRAMES \
    --max-headings-per-frame $MAX_HEADINGS_PER_FRAME \
    --max-detector-boxes-per-heading $MAX_DETECTOR_BOXES_PER_HEADING \
    --max-masks-per-heading $MAX_MASKS_PER_HEADING \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 5 \
    --candidate-point-field $CANDIDATE_POINT_FIELD \
    --box-threshold $BOX_THRESHOLD \
    --text-threshold $TEXT_THRESHOLD \
    --query-template '$QUERY_TEMPLATE' \
    --box-padding-px 4 \
    --association-depth-tolerance-m $ASSOCIATION_DEPTH_TOLERANCE_M \
    --max-debug-images $MAX_DEBUG_IMAGES"

CURRENT_STAGE=verification
write_status running "$CURRENT_STAGE"
python - <<PY
import json
from collections import Counter, defaultdict
from pathlib import Path

root = Path("$OUT")
summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
frames = [
    json.loads(line)
    for line in (root / "frame_summary.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
boxes = [
    json.loads(line)
    for line in (root / "detector_boxes.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
query_rows = defaultdict(lambda: {"rows": 0, "association_rows": 0, "associated_heading_count": 0})
for row in frames:
    item = query_rows[row["query"]]
    item["rows"] += 1
    item["association_rows"] += int(bool(row.get("has_candidate_association")))
    item["associated_heading_count"] += int(row.get("associated_candidate_heading_count", 0))

assert summary["rows"] == int("$MAX_FRAMES"), summary
assert summary["uses_gt_for_action"] is False, summary
assert summary["rows_with_detector_box_rate"] >= 0.80, summary
assert summary["rows_with_sam2_mask_rate"] >= 0.80, summary

chair_or_plant_nonzero = any(
    query_rows[name]["association_rows"] > 0 for name in ("chair", "plant") if name in query_rows
)
label_counts = Counter(box.get("label_text") for box in boxes)
promotion_pass = (
    summary["rows_with_candidate_association_rate"] >= float("$PROMOTION_ASSOCIATION_RATE")
    and chair_or_plant_nonzero
)
diagnostic = {
    "ablation": "$ABLATION_NAME",
    "rows": summary["rows"],
    "rows_with_detector_box_rate": summary["rows_with_detector_box_rate"],
    "rows_with_sam2_mask_rate": summary["rows_with_sam2_mask_rate"],
    "rows_with_candidate_association_rate": summary["rows_with_candidate_association_rate"],
    "rows_with_candidate_association": summary["rows_with_candidate_association"],
    "associated_candidate_heading_count": summary["associated_candidate_heading_count"],
    "query_rows": dict(sorted(query_rows.items())),
    "top_label_text": label_counts.most_common(20),
    "chair_or_plant_nonzero": chair_or_plant_nonzero,
    "promotion_association_rate": float("$PROMOTION_ASSOCIATION_RATE"),
    "promotion_pass": promotion_pass,
    "uses_gt_for_action": summary["uses_gt_for_action"],
}
(root / "ablation_diagnostic.json").write_text(json.dumps(diagnostic, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(diagnostic, indent=2, sort_keys=True))
PY

CURRENT_STAGE=verified
python - "$STATUS" "$OUT" <<PY
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

status_path = Path(sys.argv[1])
root = Path(sys.argv[2])
status = json.loads(status_path.read_text(encoding="utf-8"))
summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
diagnostic = json.loads((root / "ablation_diagnostic.json").read_text(encoding="utf-8"))
status.update({
    "status": "completed",
    "stage": "verified",
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "rows": summary["rows"],
    "rows_with_detector_box_rate": summary["rows_with_detector_box_rate"],
    "rows_with_sam2_mask_rate": summary["rows_with_sam2_mask_rate"],
    "rows_with_candidate_association_rate": summary["rows_with_candidate_association_rate"],
    "rows_with_candidate_association": summary["rows_with_candidate_association"],
    "associated_candidate_heading_count": summary["associated_candidate_heading_count"],
    "chair_or_plant_nonzero": diagnostic["chair_or_plant_nonzero"],
    "promotion_pass": diagnostic["promotion_pass"],
    "uses_gt_for_action": summary["uses_gt_for_action"],
})
status_path.write_text(json.dumps(status, ensure_ascii=False) + "\\n", encoding="utf-8")
PY
echo "completed_at=$(date -Is)"
