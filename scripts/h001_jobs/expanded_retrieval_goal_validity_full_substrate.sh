#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
DATA_ROOT=${DATA_ROOT:-${ROOT}/local_dataset/data}
MODEL_ROOT=${MODEL_ROOT:-${ROOT}/local_dataset/models}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
OPENVOCAB_IMG=${OPENVOCAB_IMG:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

PLAN_OUT=${PLAN_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_evidence_plan_v1}
PLAN=${PLAN:-${PLAN_OUT}/goal_validity_evidence_plan.jsonl}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${PLAN_OUT}/goal_validity_evidence_candidate_artifact.jsonl}
FRAME_OUT=${FRAME_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1}
NONBLANK_OUT=${NONBLANK_OUT:-${FRAME_OUT}/nonblank_filter_v1}
FRAMES=${FRAMES:-${NONBLANK_OUT}/rival_identity_frame_summary_nonblank.jsonl}
PROJECTION_OUT=${PROJECTION_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_evidence_projection_full_v1}
DETECTOR_OUT=${DETECTOR_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1}
DETECTOR_RAW_OUT=${DETECTOR_RAW_OUT:-${DETECTOR_OUT}/detector_v3c}

EXPECTED_ROWS=${EXPECTED_ROWS:-158}
EXPECTED_POLICY=${EXPECTED_POLICY:-ExpandedRetrievalGoalValidityEvidence}
EXPECTED_REQUEST_IDS=${EXPECTED_REQUEST_IDS:-rival_identity:12,rival_identity:14}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-grounded_position}
PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M:-0.0,0.4,0.8,1.2,1.6,2.0,2.4}
YAW_OFFSETS=${YAW_OFFSETS:--30,0,30}
WIDTH=${WIDTH:-160}
HEIGHT=${HEIGHT:-120}
CAMERA_HEIGHT=${CAMERA_HEIGHT:-1.5}
HFOV=${HFOV:-90}

DEVICE=${DEVICE:-cuda}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
MIN_DETECTOR_BOX_RATE=${MIN_DETECTOR_BOX_RATE:-0.80}
MIN_SAM2_MASK_RATE=${MIN_SAM2_MASK_RATE:-0.80}
MIN_CANDIDATE_ASSOCIATION_RATE=${MIN_CANDIDATE_ASSOCIATION_RATE:-0.40}
MAX_DEBUG_IMAGES=${MAX_DEBUG_IMAGES:-180}

LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/goal-validity-full-substrate-${TS}.log}
PIPELINE_STATUS=${PIPELINE_STATUS:-${DETECTOR_OUT}/full_substrate_job_status.json}
DETECTOR_STATUS=${DETECTOR_STATUS:-${DETECTOR_OUT}/job_status.json}

mkdir -p "$(dirname "${LOG}")" "${FRAME_OUT}" "${PROJECTION_OUT}" "${DETECTOR_OUT}"
chmod 0777 "${FRAME_OUT}" "${PROJECTION_OUT}" "${DETECTOR_OUT}"
exec > >(tee -a "${LOG}") 2>&1

write_pipeline_status() {
  local job_state="$1"
  local stage="$2"
  python - "$PIPELINE_STATUS" "$job_state" "$stage" <<PY
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "status": sys.argv[2],
    "stage": sys.argv[3],
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "command": "TS=${TS} bash scripts/h001_jobs/expanded_retrieval_goal_validity_full_substrate.sh",
    "working_directory": "${ROOT}",
    "log": "${LOG}",
    "plan": "${PLAN}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "frame_out": "${FRAME_OUT}",
    "nonblank_out": "${NONBLANK_OUT}",
    "projection_out": "${PROJECTION_OUT}",
    "detector_out": "${DETECTOR_OUT}",
    "detector_raw_out": "${DETECTOR_RAW_OUT}",
    "expected_rows": int("${EXPECTED_ROWS}"),
    "expected_policy": "${EXPECTED_POLICY}",
    "expected_request_ids": "${EXPECTED_REQUEST_IDS}".split(","),
    "verification_command": "jq '{gate:.gate.passes_detector_substrate_gate, rows:.detector_rows, box:.detector_box_rate, sam2:.sam2_mask_rate, assoc:.candidate_association_rate, gt:.uses_gt_for_action, paper:.paper_claim_allowed}' ${DETECTOR_OUT}/expanded_retrieval_detector_substrate_summary.json",
}
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
}

on_error() {
  local code="$?"
  write_pipeline_status failed "${CURRENT_STAGE:-unknown}"
  echo "failed_stage=${CURRENT_STAGE:-unknown}"
  echo "exit_code=${code}"
  exit "$code"
}
trap on_error ERR

cd "${ROOT}"
echo "started_at=$(date -Is)"
echo "working_directory=${ROOT}"
echo "habitat_image=${HABITAT_IMG}"
echo "openvocab_image=${OPENVOCAB_IMG}"
echo "plan=${PLAN}"
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "frame_out=${FRAME_OUT}"
echo "projection_out=${PROJECTION_OUT}"
echo "detector_out=${DETECTOR_OUT}"
echo "log=${LOG}"
echo "expected_files=${FRAME_OUT}/summary.json ${NONBLANK_OUT}/nonblank_frame_filter_summary.json ${PROJECTION_OUT}/projection_anchor_smoke_summary.json ${DETECTOR_OUT}/expanded_retrieval_detector_substrate_summary.json"
echo "verification_command=jq '{gate:.gate.passes_detector_substrate_gate, rows:.detector_rows, box:.detector_box_rate, sam2:.sam2_mask_rate, assoc:.candidate_association_rate, gt:.uses_gt_for_action, paper:.paper_claim_allowed}' ${DETECTOR_OUT}/expanded_retrieval_detector_substrate_summary.json"

CURRENT_STAGE=preflight
write_pipeline_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

plan = Path("${PLAN}")
artifact = Path("${CANDIDATE_ARTIFACT}")
missing = [str(path) for path in (plan, artifact, Path("${DATA_ROOT}"), Path("${MODEL_ROOT}")) if not path.exists()]
if missing:
    raise FileNotFoundError(missing)
rows = [json.loads(line) for line in plan.read_text(encoding="utf-8").splitlines() if line.strip()]
if len(rows) != int("${EXPECTED_ROWS}"):
    raise RuntimeError({"unexpected_plan_rows": len(rows), "expected": int("${EXPECTED_ROWS}")})
request_ids = sorted({row.get("expanded_retrieval_request_id") for row in rows})
expected = sorted("${EXPECTED_REQUEST_IDS}".split(","))
if request_ids != expected:
    raise RuntimeError({"unexpected_request_ids": request_ids, "expected": expected})
if any(row.get("uses_gt_for_action") is True for row in rows):
    raise RuntimeError("GT leakage in plan rows")
print({"stage": "preflight_passed", "plan_rows": len(rows), "request_ids": request_ids})
PY

CURRENT_STAGE=frame_export
write_pipeline_status running "${CURRENT_STAGE}"
docker run --rm --gpus all --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions "/runs/${PLAN#${RUNS_ROOT}/}" \
    --candidate-artifact "/runs/${CANDIDATE_ARTIFACT#${RUNS_ROOT}/}" \
    --out-root "/runs/${FRAME_OUT#${RUNS_ROOT}/}" \
    --policy "${EXPECTED_POLICY}" \
    --max-decisions 0 \
    --max-candidates-per-decision 1 \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}" \
    --yaw-offsets="${YAW_OFFSETS}" \
    --width "${WIDTH}" \
    --height "${HEIGHT}" \
    --camera-height "${CAMERA_HEIGHT}" \
    --hfov "${HFOV}"

CURRENT_STAGE=nonblank_filter
write_pipeline_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.filter_nonblank_frame_summary \
    --frame-summary "/runs/${FRAME_OUT#${RUNS_ROOT}/}/rival_identity_frame_summary.jsonl" \
    --frame-root "/runs/${FRAME_OUT#${RUNS_ROOT}/}" \
    --out-root "/runs/${NONBLANK_OUT#${RUNS_ROOT}/}" \
    --min-stddev 0.0

CURRENT_STAGE=projection_smoke
write_pipeline_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.smoke_expanded_retrieval_projection_anchor \
    --frames "/runs/${FRAMES#${RUNS_ROOT}/}" \
    --frame-root "/runs/${FRAME_OUT#${RUNS_ROOT}/}" \
    --candidate-artifact "/runs/${CANDIDATE_ARTIFACT#${RUNS_ROOT}/}" \
    --out-root "/runs/${PROJECTION_OUT#${RUNS_ROOT}/}" \
    --projection-anchor-height-offsets-m "${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M}" \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}" \
    --max-candidates-per-frame 1 \
    --expected-rows "${EXPECTED_ROWS}" \
    --min-visible-row-rate 0.95

CURRENT_STAGE=detector_substrate
write_pipeline_status running "${CURRENT_STAGE}"
TS="${TS}" \
ROOT="${ROOT}" \
HYP="${HYP}" \
RUNS_ROOT="${RUNS_ROOT}" \
MODEL_ROOT="${MODEL_ROOT}" \
PLAN_OUT="${PLAN_OUT}" \
FRAME_OUT="${FRAME_OUT}" \
FRAMES="${FRAMES}" \
FRAME_ROOT="${FRAME_OUT}" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
OUT="${DETECTOR_OUT}" \
DETECTOR_OUT="${DETECTOR_RAW_OUT}" \
OPENVOCAB_IMG="${OPENVOCAB_IMG}" \
DEVICE="${DEVICE}" \
MAX_FRAMES="${EXPECTED_ROWS}" \
EXPECTED_FRAME_ROWS="${EXPECTED_ROWS}" \
EXPECTED_POLICY="${EXPECTED_POLICY}" \
MAX_HEADINGS_PER_FRAME="${MAX_HEADINGS_PER_FRAME}" \
MAX_DETECTOR_BOXES_PER_HEADING="${MAX_DETECTOR_BOXES_PER_HEADING}" \
MAX_MASKS_PER_HEADING="${MAX_MASKS_PER_HEADING}" \
CANDIDATE_POINT_FIELD="${CANDIDATE_POINT_FIELD}" \
PROJECTION_ANCHOR_HEIGHT_OFFSETS_M="${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M}" \
BOX_THRESHOLD="${BOX_THRESHOLD}" \
TEXT_THRESHOLD="${TEXT_THRESHOLD}" \
ASSOCIATION_DEPTH_TOLERANCE_M="${ASSOCIATION_DEPTH_TOLERANCE_M}" \
MIN_DETECTOR_BOX_RATE="${MIN_DETECTOR_BOX_RATE}" \
MIN_SAM2_MASK_RATE="${MIN_SAM2_MASK_RATE}" \
MIN_CANDIDATE_ASSOCIATION_RATE="${MIN_CANDIDATE_ASSOCIATION_RATE}" \
MAX_DEBUG_IMAGES="${MAX_DEBUG_IMAGES}" \
LOG="${LOG}" \
STATUS="${DETECTOR_STATUS}" \
bash scripts/h001_jobs/expanded_retrieval_detector_substrate.sh

CURRENT_STAGE=final_verification
write_pipeline_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

summary = Path("${DETECTOR_OUT}") / "expanded_retrieval_detector_substrate_summary.json"
payload = json.loads(summary.read_text(encoding="utf-8"))
checks = {
    "rows": payload.get("detector_rows") == int("${EXPECTED_ROWS}"),
    "gate": bool(payload.get("gate", {}).get("passes_detector_substrate_gate")),
    "gt": payload.get("uses_gt_for_action") is False,
    "paper": payload.get("paper_claim_allowed") is False,
}
if not all(checks.values()):
    raise RuntimeError({"checks": checks, "summary": str(summary)})
print({
    "stage": "final_verification_passed",
    "detector_rows": payload.get("detector_rows"),
    "detector_box_rate": payload.get("detector_box_rate"),
    "sam2_mask_rate": payload.get("sam2_mask_rate"),
    "candidate_association_rate": payload.get("candidate_association_rate"),
})
PY

write_pipeline_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
