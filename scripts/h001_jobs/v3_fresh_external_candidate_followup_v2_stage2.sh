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

EXTERNAL_OUT=${EXTERNAL_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
EXTERNAL_EVIDENCE_V4_ROWS=${EXTERNAL_EVIDENCE_V4_ROWS:-${EXTERNAL_OUT}/external_candidate_evidence_v4/external_candidate_evidence_v4_rows.jsonl}
OBJECT_NODE_FEATURES=${OBJECT_NODE_FEATURES:-${RUNS_ROOT}/h001_v3_fresh_validation_pair_objective_v4_revised_geometry_v1/association_recovery/candidate_object_node_features_after_second.jsonl}
FOLLOWUP_PLAN_OUT=${FOLLOWUP_PLAN_OUT:-${EXTERNAL_OUT}/external_candidate_followup_plan}
FOLLOWUP_FRAMES_OUT=${FOLLOWUP_FRAMES_OUT:-${EXTERNAL_OUT}/external_candidate_followup_frames}
FOLLOWUP_DETECTOR_OUT=${FOLLOWUP_DETECTOR_OUT:-${EXTERNAL_OUT}/external_candidate_followup_detector}
FOLLOWUP_EVIDENCE_V2_OUT=${FOLLOWUP_EVIDENCE_V2_OUT:-${EXTERNAL_OUT}/external_candidate_followup_evidence_v2}
STAGE2_PLAN_OUT=${STAGE2_PLAN_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_plan}
STAGE2_FRAMES_OUT=${STAGE2_FRAMES_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_frames}
STAGE2_DETECTOR_OUT=${STAGE2_DETECTOR_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_detector}
STAGE2_EVIDENCE_OUT=${STAGE2_EVIDENCE_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_evidence}
INTEGRATED_OUT=${INTEGRATED_OUT:-${EXTERNAL_OUT}/external_candidate_followup_v2_stage2_validation}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
RUN_ID=${RUN_ID:-h001_v3_fresh_external_candidate_followup_v2_stage2}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
MAX_CANDIDATES_PER_DECISION=${MAX_CANDIDATES_PER_DECISION:-6}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-position}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
EXPECTED_FOLLOWUP_PLAN_ROWS=${EXPECTED_FOLLOWUP_PLAN_ROWS:-39}
EXPECTED_SOURCE_REQUEST_ROWS=${EXPECTED_SOURCE_REQUEST_ROWS:-7}
EXPECTED_STAGE2_REQUEST_ROWS=${EXPECTED_STAGE2_REQUEST_ROWS:-any}
FOLLOWUP_OBJECTIVE_VERSION=${FOLLOWUP_OBJECTIVE_VERSION:-v2}
SECOND_STAGE_OBJECTIVE_VERSION=${SECOND_STAGE_OBJECTIVE_VERSION:-v1}
VALIDATION_SCOPE=${VALIDATION_SCOPE:-unspecified}
LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/v3-fresh-external-candidate-followup-v2-stage2-${TS}.log}
STATUS=${STATUS:-${EXTERNAL_OUT}/external_candidate_followup_v2_stage2_job_status.json}

mkdir -p \
  "${ROOT}/archive/logs/h001_runtime" \
  "${EXTERNAL_OUT}" \
  "${FOLLOWUP_PLAN_OUT}" \
  "${FOLLOWUP_FRAMES_OUT}" \
  "${FOLLOWUP_DETECTOR_OUT}" \
  "${FOLLOWUP_EVIDENCE_V2_OUT}" \
  "${STAGE2_PLAN_OUT}" \
  "${STAGE2_FRAMES_OUT}" \
  "${STAGE2_DETECTOR_OUT}" \
  "${STAGE2_EVIDENCE_OUT}" \
  "${INTEGRATED_OUT}"
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
    "working_directory": "${ROOT}",
    "exact_command": "TS=${TS} bash ${HYP}/scripts/h001_jobs/v3_fresh_external_candidate_followup_v2_stage2.sh",
    "external_out": "${EXTERNAL_OUT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "external_evidence_v4_rows": "${EXTERNAL_EVIDENCE_V4_ROWS}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "followup_plan_out": "${FOLLOWUP_PLAN_OUT}",
    "followup_frames_out": "${FOLLOWUP_FRAMES_OUT}",
    "followup_detector_out": "${FOLLOWUP_DETECTOR_OUT}",
    "followup_evidence_v2_out": "${FOLLOWUP_EVIDENCE_V2_OUT}",
    "stage2_plan_out": "${STAGE2_PLAN_OUT}",
    "stage2_frames_out": "${STAGE2_FRAMES_OUT}",
    "stage2_detector_out": "${STAGE2_DETECTOR_OUT}",
    "stage2_evidence_out": "${STAGE2_EVIDENCE_OUT}",
    "integrated_out": "${INTEGRATED_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "run_id": "${RUN_ID}",
    "expected_followup_plan_rows": "${EXPECTED_FOLLOWUP_PLAN_ROWS}",
    "expected_source_request_rows": "${EXPECTED_SOURCE_REQUEST_ROWS}",
    "expected_stage2_request_rows": "${EXPECTED_STAGE2_REQUEST_ROWS}",
    "followup_objective_version": "${FOLLOWUP_OBJECTIVE_VERSION}",
    "second_stage_objective_version": "${SECOND_STAGE_OBJECTIVE_VERSION}",
    "validation_scope": "${VALIDATION_SCOPE}",
    "verification_command": "cat ${STATUS} && cat ${INTEGRATED_OUT}/external_candidate_followup_v2_stage2_validation_summary.json",
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
echo "exact_command=TS=${TS} bash ${HYP}/scripts/h001_jobs/v3_fresh_external_candidate_followup_v2_stage2.sh"
echo "external_out=${EXTERNAL_OUT}"
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "external_evidence_v4_rows=${EXTERNAL_EVIDENCE_V4_ROWS}"
echo "object_node_features=${OBJECT_NODE_FEATURES}"
echo "followup_plan_out=${FOLLOWUP_PLAN_OUT}"
echo "followup_frames_out=${FOLLOWUP_FRAMES_OUT}"
echo "followup_detector_out=${FOLLOWUP_DETECTOR_OUT}"
echo "followup_evidence_v2_out=${FOLLOWUP_EVIDENCE_V2_OUT}"
echo "stage2_plan_out=${STAGE2_PLAN_OUT}"
echo "stage2_frames_out=${STAGE2_FRAMES_OUT}"
echo "stage2_detector_out=${STAGE2_DETECTOR_OUT}"
echo "stage2_evidence_out=${STAGE2_EVIDENCE_OUT}"
echo "integrated_out=${INTEGRATED_OUT}"
echo "log=${LOG}"
echo "run_id=${RUN_ID}"
echo "expected_files=${FOLLOWUP_PLAN_OUT}/external_candidate_followup_observation_plan.jsonl ${FOLLOWUP_DETECTOR_OUT}/summary.json ${FOLLOWUP_EVIDENCE_V2_OUT}/external_candidate_followup_evidence_summary.json ${STAGE2_PLAN_OUT}/external_candidate_second_stage_identity_summary.json ${STAGE2_DETECTOR_OUT}/summary.json ${STAGE2_EVIDENCE_OUT}/external_candidate_second_stage_identity_evidence_summary.json ${INTEGRATED_OUT}/external_candidate_followup_v2_stage2_validation_summary.json"
echo "verification_command=cat ${STATUS} && cat ${INTEGRATED_OUT}/external_candidate_followup_v2_stage2_validation_summary.json"
echo "followup_objective_version=${FOLLOWUP_OBJECTIVE_VERSION}"
echo "second_stage_objective_version=${SECOND_STAGE_OBJECTIVE_VERSION}"
echo "validation_scope=${VALIDATION_SCOPE}"

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

FOLLOWUP_FRAME_ROWS="$(python - <<PY
from pathlib import Path
path = Path("${FOLLOWUP_FRAMES_OUT}") / "postview_frames_v2.jsonl"
rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)"
if [[ "${FOLLOWUP_FRAME_ROWS}" -le 0 ]]; then
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
    --max-frames "${FOLLOWUP_FRAME_ROWS}" \
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

CURRENT_STAGE=followup_v2_evidence_analysis
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
    --out-root "$(to_runs_path "${FOLLOWUP_EVIDENCE_V2_OUT}")" \
    --observed-only \
    --objective-version "${FOLLOWUP_OBJECTIVE_VERSION}" \
    --large-repeated-expanded-retrieval-guard auto

CURRENT_STAGE=second_stage_identity_plan
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
  micromamba run -n base python -m h001_runtime.plan_external_candidate_second_stage_identity_confirmation \
    --data-root /data \
    --followup-evidence-rows "$(to_runs_path "${FOLLOWUP_EVIDENCE_V2_OUT}")/external_candidate_followup_evidence_rows.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${STAGE2_PLAN_OUT}")" \
    --run-id "${RUN_ID}_stage2"

STAGE2_PLAN_ROWS="$(python - <<PY
from pathlib import Path
path = Path("${STAGE2_PLAN_OUT}") / "external_candidate_second_stage_identity_plan.jsonl"
rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)"

CURRENT_STAGE=second_stage_frame_export
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
    --viewpoint-decisions "$(to_runs_path "${STAGE2_PLAN_OUT}")/external_candidate_second_stage_identity_plan.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${STAGE2_FRAMES_OUT}")" \
    --policy ExternalCandidateSecondStageIdentityConfirmation \
    --max-decisions 0 \
    --max-candidates-per-decision "${MAX_CANDIDATES_PER_DECISION}" \
    --yaw-offsets=-30,0,30 \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}"

STAGE2_FRAME_ROWS="$(python - <<PY
from pathlib import Path
path = Path("${STAGE2_FRAMES_OUT}") / "postview_frames_v2.jsonl"
rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)"

CURRENT_STAGE=second_stage_detector
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
    --frames "$(to_runs_path "${STAGE2_FRAMES_OUT}")/postview_frames_v2.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root "$(to_runs_path "${STAGE2_DETECTOR_OUT}")" \
    --debug-root "$(to_runs_path "${STAGE2_DETECTOR_OUT}")/debug_images" \
    --device "${DEVICE}" \
    --max-frames "${STAGE2_FRAME_ROWS}" \
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

CURRENT_STAGE=second_stage_evidence_analysis
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_external_candidate_second_stage_identity_evidence \
    --followup-evidence-rows "$(to_runs_path "${FOLLOWUP_EVIDENCE_V2_OUT}")/external_candidate_followup_evidence_rows.jsonl" \
    --second-stage-plan "$(to_runs_path "${STAGE2_PLAN_OUT}")/external_candidate_second_stage_identity_plan.jsonl" \
    --detector-root "$(to_runs_path "${STAGE2_DETECTOR_OUT}")" \
    --out-root "$(to_runs_path "${STAGE2_EVIDENCE_OUT}")" \
    --observed-only \
    --objective-version "${SECOND_STAGE_OBJECTIVE_VERSION}"

CURRENT_STAGE=integrated_summary
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.summarize_followup_v2_stage2 \
    --base-validation-summary "$(to_runs_path "${EXTERNAL_OUT}")/external_candidate_detector_validation_summary.json" \
    --followup-v2-summary "$(to_runs_path "${FOLLOWUP_EVIDENCE_V2_OUT}")/external_candidate_followup_evidence_summary.json" \
    --followup-v2-rows "$(to_runs_path "${FOLLOWUP_EVIDENCE_V2_OUT}")/external_candidate_followup_evidence_rows.jsonl" \
    --second-stage-plan-summary "$(to_runs_path "${STAGE2_PLAN_OUT}")/external_candidate_second_stage_identity_summary.json" \
    --second-stage-frame-summary "$(to_runs_path "${STAGE2_FRAMES_OUT}")/summary.json" \
    --second-stage-detector-summary "$(to_runs_path "${STAGE2_DETECTOR_OUT}")/summary.json" \
    --second-stage-evidence-summary "$(to_runs_path "${STAGE2_EVIDENCE_OUT}")/external_candidate_second_stage_identity_evidence_summary.json" \
    --second-stage-evidence-rows "$(to_runs_path "${STAGE2_EVIDENCE_OUT}")/external_candidate_second_stage_identity_evidence_rows.jsonl" \
    --out-root "$(to_runs_path "${INTEGRATED_OUT}")" \
    --validation-scope "${VALIDATION_SCOPE}"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

external_out = Path("${EXTERNAL_OUT}")
followup_plan = json.loads((Path("${FOLLOWUP_PLAN_OUT}") / "external_candidate_followup_observation_summary.json").read_text(encoding="utf-8"))
followup_frames = json.loads((Path("${FOLLOWUP_FRAMES_OUT}") / "summary.json").read_text(encoding="utf-8"))
followup_detector = json.loads((Path("${FOLLOWUP_DETECTOR_OUT}") / "summary.json").read_text(encoding="utf-8"))
followup_v2 = json.loads((Path("${FOLLOWUP_EVIDENCE_V2_OUT}") / "external_candidate_followup_evidence_summary.json").read_text(encoding="utf-8"))
stage2_plan = json.loads((Path("${STAGE2_PLAN_OUT}") / "external_candidate_second_stage_identity_summary.json").read_text(encoding="utf-8"))
stage2_frames = json.loads((Path("${STAGE2_FRAMES_OUT}") / "summary.json").read_text(encoding="utf-8"))
stage2_detector = json.loads((Path("${STAGE2_DETECTOR_OUT}") / "summary.json").read_text(encoding="utf-8"))
stage2_evidence = json.loads((Path("${STAGE2_EVIDENCE_OUT}") / "external_candidate_second_stage_identity_evidence_summary.json").read_text(encoding="utf-8"))
integrated = json.loads((Path("${INTEGRATED_OUT}") / "external_candidate_followup_v2_stage2_validation_summary.json").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.v3_fresh_external_candidate_followup_v2_stage2_job.v1",
    "external_out": "${EXTERNAL_OUT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "external_evidence_v4_rows": "${EXTERNAL_EVIDENCE_V4_ROWS}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "followup_plan_out": "${FOLLOWUP_PLAN_OUT}",
    "followup_frames_out": "${FOLLOWUP_FRAMES_OUT}",
    "followup_detector_out": "${FOLLOWUP_DETECTOR_OUT}",
    "followup_evidence_v2_out": "${FOLLOWUP_EVIDENCE_V2_OUT}",
    "stage2_plan_out": "${STAGE2_PLAN_OUT}",
    "stage2_frames_out": "${STAGE2_FRAMES_OUT}",
    "stage2_detector_out": "${STAGE2_DETECTOR_OUT}",
    "stage2_evidence_out": "${STAGE2_EVIDENCE_OUT}",
    "integrated_out": "${INTEGRATED_OUT}",
    "followup_objective_version": "${FOLLOWUP_OBJECTIVE_VERSION}",
    "second_stage_objective_version": "${SECOND_STAGE_OBJECTIVE_VERSION}",
    "validation_scope": "${VALIDATION_SCOPE}",
    "followup_plan_rows": followup_plan.get("plan_rows"),
    "followup_source_action_counts": followup_plan.get("source_action_counts"),
    "followup_action_counts": followup_plan.get("followup_action_counts"),
    "followup_frame_rows_exported": followup_frames.get("rows_exported"),
    "followup_rendered_heading_count": followup_frames.get("rendered_heading_count"),
    "followup_detector_summary": {
        "rows": followup_detector.get("rows"),
        "rows_with_detector_box_rate": followup_detector.get("rows_with_detector_box_rate"),
        "rows_with_sam2_mask_rate": followup_detector.get("rows_with_sam2_mask_rate"),
        "rows_with_candidate_association_rate": followup_detector.get("rows_with_candidate_association_rate"),
    },
    "followup_v2_gate": followup_v2.get("gate"),
    "followup_v2_action_counts": followup_v2.get("action_counts"),
    "followup_v2_reason_counts": followup_v2.get("reason_counts"),
    "followup_v2_source_request_rows": followup_v2.get("source_request_rows"),
    "followup_v2_source_rows_analyzed": followup_v2.get("source_rows_analyzed"),
    "stage2_request_rows": stage2_plan.get("request_rows"),
    "stage2_plan_rows": stage2_plan.get("plan_rows"),
    "stage2_skipped_rows": stage2_plan.get("skipped_rows"),
    "stage2_frame_rows_exported": stage2_frames.get("rows_exported"),
    "stage2_rendered_heading_count": stage2_frames.get("rendered_heading_count"),
    "stage2_detector_summary": {
        "rows": stage2_detector.get("rows"),
        "rows_with_detector_box_rate": stage2_detector.get("rows_with_detector_box_rate"),
        "rows_with_sam2_mask_rate": stage2_detector.get("rows_with_sam2_mask_rate"),
        "rows_with_candidate_association_rate": stage2_detector.get("rows_with_candidate_association_rate"),
    },
    "stage2_evidence_gate": stage2_evidence.get("gate"),
    "stage2_action_counts": stage2_evidence.get("action_counts"),
    "integrated_gate": integrated.get("integrated", {}).get("gate"),
    "terminal_action_counts": integrated.get("integrated", {}).get("terminal_action_counts"),
    "first_eval_rerun_blocked": integrated.get("interpretation", {}).get("first_eval_rerun_blocked"),
    "uses_gt_for_action": bool(
        followup_plan.get("uses_gt_for_action")
        or followup_frames.get("uses_gt_for_action")
        or followup_detector.get("uses_gt_for_action")
        or followup_v2.get("uses_gt_for_action")
        or stage2_plan.get("uses_gt_for_action")
        or stage2_frames.get("uses_gt_for_action")
        or stage2_detector.get("uses_gt_for_action")
        or stage2_evidence.get("uses_gt_for_action")
        or integrated.get("uses_gt_for_action")
    ),
    "uses_gt_for_analysis": bool(
        followup_plan.get("uses_gt_for_analysis")
        or followup_v2.get("uses_gt_for_analysis")
        or stage2_plan.get("uses_gt_for_analysis")
        or stage2_evidence.get("uses_gt_for_analysis")
        or integrated.get("uses_gt_for_analysis")
    ),
}
(external_out / "external_candidate_followup_v2_stage2_job_summary.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in action path")
if payload["followup_frame_rows_exported"] != payload["followup_plan_rows"]:
    raise RuntimeError({"followup_frame_plan_mismatch": [payload["followup_frame_rows_exported"], payload["followup_plan_rows"]]})
if payload["stage2_frame_rows_exported"] != payload["stage2_plan_rows"]:
    raise RuntimeError({"stage2_frame_plan_mismatch": [payload["stage2_frame_rows_exported"], payload["stage2_plan_rows"]]})
expected_followup_plan_rows = "${EXPECTED_FOLLOWUP_PLAN_ROWS}"
if expected_followup_plan_rows.lower() not in {"", "any"} and payload["followup_plan_rows"] != int(expected_followup_plan_rows):
    raise RuntimeError({"unexpected_followup_plan_rows": payload["followup_plan_rows"], "expected": int(expected_followup_plan_rows)})
expected_source_request_rows = "${EXPECTED_SOURCE_REQUEST_ROWS}"
if expected_source_request_rows.lower() not in {"", "any"} and payload["followup_v2_source_request_rows"] != int(expected_source_request_rows):
    raise RuntimeError({"unexpected_source_request_rows": payload["followup_v2_source_request_rows"], "expected": int(expected_source_request_rows)})
expected_stage2_request_rows = "${EXPECTED_STAGE2_REQUEST_ROWS}"
if expected_stage2_request_rows.lower() not in {"", "any"} and payload["stage2_request_rows"] != int(expected_stage2_request_rows):
    raise RuntimeError({"unexpected_stage2_request_rows": payload["stage2_request_rows"], "expected": int(expected_stage2_request_rows)})
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
