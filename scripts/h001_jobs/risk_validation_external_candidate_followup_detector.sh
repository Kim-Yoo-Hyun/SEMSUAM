#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
MODEL_ROOT=${MODEL_ROOT:-/tmp/research3-models}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
OPENVOCAB_IMG=${OPENVOCAB_IMG:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

EXTERNAL_OUT=${EXTERNAL_OUT:-${RUNS_ROOT}/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
EXTERNAL_EVIDENCE_V4_ROWS=${EXTERNAL_EVIDENCE_V4_ROWS:-${EXTERNAL_OUT}/external_candidate_evidence_v4/external_candidate_evidence_v4_rows.jsonl}
OBJECT_NODE_FEATURES=${OBJECT_NODE_FEATURES:-${RUNS_ROOT}/h001_risk_validation_pair_objective_v4b_revised_geometry_v1/association_recovery/candidate_object_node_features_after_second.jsonl}
FOLLOWUP_PLAN_OUT=${FOLLOWUP_PLAN_OUT:-${EXTERNAL_OUT}/external_candidate_followup_plan}
FOLLOWUP_FRAMES_OUT=${FOLLOWUP_FRAMES_OUT:-${EXTERNAL_OUT}/external_candidate_followup_frames}
FOLLOWUP_DETECTOR_OUT=${FOLLOWUP_DETECTOR_OUT:-${EXTERNAL_OUT}/external_candidate_followup_detector}
FOLLOWUP_EVIDENCE_OUT=${FOLLOWUP_EVIDENCE_OUT:-${EXTERNAL_OUT}/external_candidate_followup_evidence}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
RUN_ID=${RUN_ID:-h001_risk_validation_external_candidate_followup_detector_v1}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
MAX_CANDIDATES_PER_DECISION=${MAX_CANDIDATES_PER_DECISION:-6}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-position}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
EXPECTED_PLAN_ROWS=${EXPECTED_PLAN_ROWS:-28}
EXPECTED_SOURCE_REQUEST_ROWS=${EXPECTED_SOURCE_REQUEST_ROWS:-8}
LOG=${LOG:-${ROOT}/logs/risk-validation-external-candidate-followup-detector-${TS}.log}
STATUS=${STATUS:-${EXTERNAL_OUT}/external_candidate_followup_job_status.json}

mkdir -p "${ROOT}/logs" "${EXTERNAL_OUT}" "${FOLLOWUP_PLAN_OUT}" "${FOLLOWUP_FRAMES_OUT}" "${FOLLOWUP_DETECTOR_OUT}" "${FOLLOWUP_EVIDENCE_OUT}"
exec > >(tee -a "${LOG}") 2>&1

to_runs_path() {
  local path="$1"
  if [[ "$path" == /tmp/research3-runs/* ]]; then
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
    "external_out": "${EXTERNAL_OUT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "external_evidence_v4_rows": "${EXTERNAL_EVIDENCE_V4_ROWS}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "followup_plan_out": "${FOLLOWUP_PLAN_OUT}",
    "followup_frames_out": "${FOLLOWUP_FRAMES_OUT}",
    "followup_detector_out": "${FOLLOWUP_DETECTOR_OUT}",
    "followup_evidence_out": "${FOLLOWUP_EVIDENCE_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "run_id": "${RUN_ID}",
    "expected_plan_rows": "${EXPECTED_PLAN_ROWS}",
    "expected_source_request_rows": "${EXPECTED_SOURCE_REQUEST_ROWS}",
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
echo "external_out=${EXTERNAL_OUT}"
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "external_evidence_v4_rows=${EXTERNAL_EVIDENCE_V4_ROWS}"
echo "object_node_features=${OBJECT_NODE_FEATURES}"
echo "followup_plan_out=${FOLLOWUP_PLAN_OUT}"
echo "followup_frames_out=${FOLLOWUP_FRAMES_OUT}"
echo "followup_detector_out=${FOLLOWUP_DETECTOR_OUT}"
echo "followup_evidence_out=${FOLLOWUP_EVIDENCE_OUT}"
echo "log=${LOG}"
echo "run_id=${RUN_ID}"
echo "expected_files=${FOLLOWUP_PLAN_OUT}/external_candidate_followup_observation_plan.jsonl ${FOLLOWUP_FRAMES_OUT}/postview_frames_v2.jsonl ${FOLLOWUP_DETECTOR_OUT}/summary.json ${FOLLOWUP_EVIDENCE_OUT}/external_candidate_followup_evidence_summary.json ${EXTERNAL_OUT}/external_candidate_followup_validation_summary.json"
echo "verification_command=cat ${STATUS} && cat ${EXTERNAL_OUT}/external_candidate_followup_validation_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
docker image inspect "${HABITAT_IMG}" "${OPENVOCAB_IMG}" >/dev/null
python - <<PY
from pathlib import Path
paths = {
    "data_root": Path("${DATA_ROOT}"),
    "hm3d": Path("${DATA_ROOT}") / "scene_datasets" / "hm3d",
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "external_evidence_v4_rows": Path("${EXTERNAL_EVIDENCE_V4_ROWS}"),
    "object_node_features": Path("${OBJECT_NODE_FEATURES}"),
    "groundingdino_config": Path("${GROUNDINGDINO_DIR}") / "config.json",
    "groundingdino_weights": Path("${GROUNDINGDINO_DIR}") / "model.safetensors",
    "sam2_checkpoint": Path("${SAM2_CHECKPOINT}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
print({"stage": "prerequisite_check_passed", "paths": {name: str(path) for name, path in paths.items()}})
PY

CURRENT_STAGE=followup_plan
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.plan_external_candidate_followup_observation \
    --data-root /data \
    --external-evidence-v4-rows "$(to_runs_path "${EXTERNAL_EVIDENCE_V4_ROWS}")" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${FOLLOWUP_PLAN_OUT}")" \
    --run-id "${RUN_ID}"

CURRENT_STAGE=followup_frame_export
write_status running "${CURRENT_STAGE}"
docker run --rm --gpus all --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions "$(to_runs_path "${FOLLOWUP_PLAN_OUT}")/external_candidate_followup_observation_plan.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${FOLLOWUP_FRAMES_OUT}")" \
    --policy ExternalCandidateFollowupObservation \
    --max-decisions 0 \
    --max-candidates-per-decision "${MAX_CANDIDATES_PER_DECISION}" \
    --yaw-offsets=-30,0,30 \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}"

FRAME_ROWS="$(python - <<PY
from pathlib import Path
path = Path("${FOLLOWUP_FRAMES_OUT}") / "postview_frames_v2.jsonl"
rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)"
if [[ "${FRAME_ROWS}" -le 0 ]]; then
  echo "no follow-up frame rows exported" >&2
  exit 1
fi

if [[ "${DEVICE}" == "cuda" ]]; then
  GPU_FLAG="--gpus all"
else
  GPU_FLAG=""
fi

CURRENT_STAGE=followup_detector
write_status running "${CURRENT_STAGE}"
docker run --rm ${GPU_FLAG} \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${MODEL_ROOT}:/models:ro" \
  -w /workspace \
  "${OPENVOCAB_IMG}" \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames "$(to_runs_path "${FOLLOWUP_FRAMES_OUT}")/postview_frames_v2.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root "$(to_runs_path "${FOLLOWUP_DETECTOR_OUT}")" \
    --debug-root "$(to_runs_path "${FOLLOWUP_DETECTOR_OUT}")/debug_images" \
    --device "${DEVICE}" \
    --max-frames "${FRAME_ROWS}" \
    --max-headings-per-frame "${MAX_HEADINGS_PER_FRAME}" \
    --max-detector-boxes-per-heading "${MAX_DETECTOR_BOXES_PER_HEADING}" \
    --max-masks-per-heading "${MAX_MASKS_PER_HEADING}" \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame "${MAX_CANDIDATES_PER_DECISION}" \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}" \
    --box-threshold "${BOX_THRESHOLD}" \
    --text-threshold "${TEXT_THRESHOLD}" \
    --query-template "${QUERY_TEMPLATE}" \
    --box-padding-px 4 \
    --association-depth-tolerance-m "${ASSOCIATION_DEPTH_TOLERANCE_M}" \
    --max-debug-images 160

CURRENT_STAGE=followup_evidence_analysis
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_external_candidate_followup_evidence \
    --external-evidence-v4-rows "$(to_runs_path "${EXTERNAL_EVIDENCE_V4_ROWS}")" \
    --followup-observation-plan "$(to_runs_path "${FOLLOWUP_PLAN_OUT}")/external_candidate_followup_observation_plan.jsonl" \
    --detector-root "$(to_runs_path "${FOLLOWUP_DETECTOR_OUT}")" \
    --object-node-features "$(to_runs_path "${OBJECT_NODE_FEATURES}")" \
    --out-root "$(to_runs_path "${FOLLOWUP_EVIDENCE_OUT}")" \
    --observed-only

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

external_out = Path("${EXTERNAL_OUT}")
plan = json.loads((Path("${FOLLOWUP_PLAN_OUT}") / "external_candidate_followup_observation_summary.json").read_text(encoding="utf-8"))
frames = json.loads((Path("${FOLLOWUP_FRAMES_OUT}") / "summary.json").read_text(encoding="utf-8"))
detector = json.loads((Path("${FOLLOWUP_DETECTOR_OUT}") / "summary.json").read_text(encoding="utf-8"))
evidence = json.loads((Path("${FOLLOWUP_EVIDENCE_OUT}") / "external_candidate_followup_evidence_summary.json").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.risk_validation_external_candidate_followup_detector.v1",
    "external_out": "${EXTERNAL_OUT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "external_evidence_v4_rows": "${EXTERNAL_EVIDENCE_V4_ROWS}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "followup_plan_out": "${FOLLOWUP_PLAN_OUT}",
    "followup_frames_out": "${FOLLOWUP_FRAMES_OUT}",
    "followup_detector_out": "${FOLLOWUP_DETECTOR_OUT}",
    "followup_evidence_out": "${FOLLOWUP_EVIDENCE_OUT}",
    "plan_rows": plan.get("plan_rows"),
    "skipped_rows": plan.get("skipped_rows"),
    "source_action_counts": plan.get("source_action_counts"),
    "followup_action_counts": plan.get("followup_action_counts"),
    "frame_rows_exported": frames.get("rows_exported"),
    "rendered_heading_count": frames.get("rendered_heading_count"),
    "detector_summary": {
        "rows": detector.get("rows"),
        "rows_with_detector_box_rate": detector.get("rows_with_detector_box_rate"),
        "rows_with_sam2_mask_rate": detector.get("rows_with_sam2_mask_rate"),
        "rows_with_candidate_association_rate": detector.get("rows_with_candidate_association_rate"),
    },
    "followup_evidence_gate": evidence.get("gate"),
    "followup_evidence_action_counts": evidence.get("action_counts"),
    "followup_evidence_reason_counts": evidence.get("reason_counts"),
    "source_request_rows": evidence.get("source_request_rows"),
    "source_rows_analyzed": evidence.get("source_rows_analyzed"),
    "uses_gt_for_action": bool(
        plan.get("uses_gt_for_action")
        or frames.get("uses_gt_for_action")
        or detector.get("uses_gt_for_action")
        or evidence.get("uses_gt_for_action")
    ),
    "uses_gt_for_analysis": bool(plan.get("uses_gt_for_analysis") or evidence.get("uses_gt_for_analysis")),
}
(external_out / "external_candidate_followup_validation_summary.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in action path")
if payload["frame_rows_exported"] != payload["plan_rows"]:
    raise RuntimeError({"frame_plan_mismatch": [payload["frame_rows_exported"], payload["plan_rows"]]})
expected_plan_rows = "${EXPECTED_PLAN_ROWS}"
if expected_plan_rows.lower() not in {"", "any"} and payload["plan_rows"] != int(expected_plan_rows):
    raise RuntimeError({"unexpected_plan_rows": payload["plan_rows"], "expected": int(expected_plan_rows)})
expected_source_request_rows = "${EXPECTED_SOURCE_REQUEST_ROWS}"
if expected_source_request_rows.lower() not in {"", "any"} and payload["source_request_rows"] != int(expected_source_request_rows):
    raise RuntimeError({
        "unexpected_source_request_rows": payload["source_request_rows"],
        "expected": int(expected_source_request_rows),
    })
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
