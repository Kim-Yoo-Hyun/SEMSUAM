#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
MODEL_ROOT=${MODEL_ROOT:-${ROOT}/local_dataset/models}
OPENVOCAB_IMG=${OPENVOCAB_IMG:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

PLAN_OUT=${PLAN_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_detector_plan_projection_anchor_v1}
FRAME_OUT=${FRAME_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_detector_frames_v1}
FRAMES=${FRAMES:-${FRAME_OUT}/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl}
FRAME_ROOT=${FRAME_ROOT:-${FRAME_OUT}}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${PLAN_OUT}/expanded_retrieval_detector_candidate_artifact.jsonl}
OUT=${OUT:-${RUNS_ROOT}/h001_expanded_retrieval_detector_substrate_projection_anchor_v1}
DETECTOR_OUT=${DETECTOR_OUT:-${OUT}/detector_v3c}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
MAX_FRAMES=${MAX_FRAMES:-42}
EXPECTED_FRAME_ROWS=${EXPECTED_FRAME_ROWS:-42}
EXPECTED_POLICY=${EXPECTED_POLICY:-ExpandedRetrievalDetectorObservation}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-grounded_position}
PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M:-0.0,0.4,0.8,1.2,1.6}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
MIN_DETECTOR_BOX_RATE=${MIN_DETECTOR_BOX_RATE:-0.80}
MIN_SAM2_MASK_RATE=${MIN_SAM2_MASK_RATE:-0.80}
MIN_CANDIDATE_ASSOCIATION_RATE=${MIN_CANDIDATE_ASSOCIATION_RATE:-0.40}
MAX_DEBUG_IMAGES=${MAX_DEBUG_IMAGES:-180}
LOG=${LOG:-${HYP}/runtime/logs/expanded-retrieval-detector-substrate-${TS}.log}
STATUS=${STATUS:-${OUT}/job_status.json}

mkdir -p "$(dirname "${LOG}")" "${OUT}" "${DETECTOR_OUT}"
exec > >(tee -a "${LOG}") 2>&1

to_runs_path() {
  local path="$1"
  if [[ "$path" == "${RUNS_ROOT}"/* ]]; then
    echo "/runs/${path#${RUNS_ROOT}/}"
  elif [[ "$path" == /tmp/research3-runs/* ]]; then
    echo "/runs/${path#/tmp/research3-runs/}"
  else
    echo "$path"
  fi
}

write_status() {
  local job_state="$1"
  local stage="$2"
  python - "$STATUS" "$job_state" "$stage" <<PY
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "status": sys.argv[2],
    "stage": sys.argv[3],
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "frames": "${FRAMES}",
    "frame_root": "${FRAME_ROOT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "out": "${OUT}",
    "detector_out": "${DETECTOR_OUT}",
    "log": "${LOG}",
    "image": "${OPENVOCAB_IMG}",
    "device": "${DEVICE}",
    "max_frames": int("${MAX_FRAMES}"),
    "expected_frame_rows": int("${EXPECTED_FRAME_ROWS}"),
    "expected_policy": "${EXPECTED_POLICY}",
    "candidate_point_field": "${CANDIDATE_POINT_FIELD}",
    "projection_anchor_height_offsets_m": "${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M}",
    "query_template": "${QUERY_TEMPLATE}",
    "box_threshold": float("${BOX_THRESHOLD}"),
    "text_threshold": float("${TEXT_THRESHOLD}"),
    "association_depth_tolerance_m": float("${ASSOCIATION_DEPTH_TOLERANCE_M}"),
}
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
}

on_error() {
  local code="$?"
  write_status failed "${CURRENT_STAGE:-unknown}"
  echo "failed_stage=${CURRENT_STAGE:-unknown}"
  echo "exit_code=${code}"
  exit "$code"
}
trap on_error ERR

cd "${ROOT}"
echo "started_at=$(date -Is)"
echo "working_directory=${ROOT}"
echo "image=${OPENVOCAB_IMG}"
echo "frames=${FRAMES}"
echo "frame_root=${FRAME_ROOT}"
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "projection_anchor_height_offsets_m=${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M}"
echo "groundingdino_dir=${GROUNDINGDINO_DIR}"
echo "sam2_checkpoint=${SAM2_CHECKPOINT}"
echo "out=${OUT}"
echo "detector_out=${DETECTOR_OUT}"
echo "log=${LOG}"
echo "expected_policy=${EXPECTED_POLICY}"
echo "expected_files=${DETECTOR_OUT}/summary.json ${DETECTOR_OUT}/detector_candidate_associations.jsonl ${OUT}/expanded_retrieval_detector_associations.jsonl ${OUT}/expanded_retrieval_detector_substrate_summary.json"
echo "verification_command=cat ${STATUS} && cat ${OUT}/expanded_retrieval_detector_substrate_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

paths = {
    "frames": Path("${FRAMES}"),
    "frame_root": Path("${FRAME_ROOT}"),
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "groundingdino_config": Path("${GROUNDINGDINO_DIR}") / "config.json",
    "groundingdino_weights": Path("${GROUNDINGDINO_DIR}") / "model.safetensors",
    "sam2_checkpoint": Path("${SAM2_CHECKPOINT}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
frames = [json.loads(line) for line in paths["frames"].read_text(encoding="utf-8").splitlines() if line.strip()]
if len(frames) != int("${EXPECTED_FRAME_ROWS}"):
    raise RuntimeError({"unexpected_frame_rows": len(frames), "expected": int("${EXPECTED_FRAME_ROWS}")})
if any(row.get("uses_gt_for_action") is True for row in frames):
    raise RuntimeError("GT leakage in frame rows")
expected_policy = "${EXPECTED_POLICY}"
unexpected_policies = sorted({row.get("policy") for row in frames if row.get("policy") != expected_policy})
if unexpected_policies:
    raise RuntimeError({"unexpected_policy": unexpected_policies, "expected": expected_policy})
if any("expanded_retrieval_request_id" not in row for row in frames):
    raise RuntimeError("missing expanded_retrieval_request_id in frame rows")
print({"stage": "prerequisite_check_passed", "frame_rows": len(frames)})
PY

if [[ "${DEVICE}" == "cuda" ]]; then
  GPU_FLAG="--gpus all"
else
  GPU_FLAG=""
fi

CURRENT_STAGE=detector_mask_scoring
write_status running "${CURRENT_STAGE}"
docker run --rm ${GPU_FLAG} \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${MODEL_ROOT}:/models:ro" \
  -w /workspace \
  "${OPENVOCAB_IMG}" \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames "$(to_runs_path "${FRAMES}")" \
    --frame-root "$(to_runs_path "${FRAME_ROOT}")" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root "$(to_runs_path "${DETECTOR_OUT}")" \
    --debug-root "$(to_runs_path "${DETECTOR_OUT}")/debug_images" \
    --device "${DEVICE}" \
    --max-frames "${MAX_FRAMES}" \
    --max-headings-per-frame "${MAX_HEADINGS_PER_FRAME}" \
    --max-detector-boxes-per-heading "${MAX_DETECTOR_BOXES_PER_HEADING}" \
    --max-masks-per-heading "${MAX_MASKS_PER_HEADING}" \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 1 \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}" \
    --projection-anchor-height-offsets-m "${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M}" \
    --box-threshold "${BOX_THRESHOLD}" \
    --text-threshold "${TEXT_THRESHOLD}" \
    --query-template "${QUERY_TEMPLATE}" \
    --box-padding-px 4 \
    --association-depth-tolerance-m "${ASSOCIATION_DEPTH_TOLERANCE_M}" \
    --max-debug-images "${MAX_DEBUG_IMAGES}"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
import shutil
from pathlib import Path

out = Path("${OUT}")
detector_out = Path("${DETECTOR_OUT}")
detector = json.loads((detector_out / "summary.json").read_text(encoding="utf-8"))
shutil.copyfile(detector_out / "detector_candidate_associations.jsonl", out / "expanded_retrieval_detector_associations.jsonl")
shutil.copyfile(detector_out / "frame_summary.jsonl", out / "expanded_retrieval_detector_frame_summary.jsonl")
payload = {
    "schema_version": "h001.expanded_retrieval_detector_substrate.v1",
    "frames": "${FRAMES}",
    "frame_root": "${FRAME_ROOT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "detector_out": "${DETECTOR_OUT}",
    "frame_rows": int("${EXPECTED_FRAME_ROWS}"),
    "detector_rows": detector.get("rows"),
    "detector_box_rate": detector.get("rows_with_detector_box_rate"),
    "sam2_mask_rate": detector.get("rows_with_sam2_mask_rate"),
    "candidate_association_rate": detector.get("rows_with_candidate_association_rate"),
    "rows_with_candidate_association": detector.get("rows_with_candidate_association"),
    "associated_candidate_heading_count": detector.get("associated_candidate_heading_count"),
    "candidate_point_field": detector.get("candidate_point_field"),
    "projection_anchor_height_offsets_m": detector.get("projection_anchor_height_offsets_m"),
    "projection_anchor_policy_counts": detector.get("projection_anchor_policy_counts"),
    "projection_anchor_status_counts": detector.get("projection_anchor_status_counts"),
    "projection_anchor_selected_offset_counts": detector.get("projection_anchor_selected_offset_counts"),
    "query_template": detector.get("query_template"),
    "uses_gt_for_action": bool(detector.get("uses_gt_for_action")),
    "uses_gt_for_analysis": False,
    "paper_claim_allowed": False,
    "gate": {
        "detector_rows_match": detector.get("rows") == int("${EXPECTED_FRAME_ROWS}"),
        "detector_box_rate_pass": (detector.get("rows_with_detector_box_rate") or 0.0) >= float("${MIN_DETECTOR_BOX_RATE}"),
        "sam2_mask_rate_pass": (detector.get("rows_with_sam2_mask_rate") or 0.0) >= float("${MIN_SAM2_MASK_RATE}"),
        "candidate_association_rate_pass": (detector.get("rows_with_candidate_association_rate") or 0.0) >= float("${MIN_CANDIDATE_ASSOCIATION_RATE}"),
        "no_gt_action_pass": not bool(detector.get("uses_gt_for_action")),
    },
    "output_files": {
        "detector_summary": "detector_v3c/summary.json",
        "detector_associations": "detector_v3c/detector_candidate_associations.jsonl",
        "expanded_retrieval_detector_associations": "expanded_retrieval_detector_associations.jsonl",
        "expanded_retrieval_detector_frame_summary": "expanded_retrieval_detector_frame_summary.jsonl",
        "summary": "expanded_retrieval_detector_substrate_summary.json",
    },
}
payload["gate"]["passes_detector_substrate_gate"] = all(payload["gate"].values())
(out / "expanded_retrieval_detector_substrate_summary.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in detector substrate")
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
