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
FOLLOWUP_EVIDENCE_OUT=${FOLLOWUP_EVIDENCE_OUT:-${EXTERNAL_OUT}/external_candidate_followup_evidence_v4_selected_local_cluster_margin}
STAGE2_PLAN_OUT=${STAGE2_PLAN_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_semantic_neighbor_validation_plan}
STAGE2_FRAMES_OUT=${STAGE2_FRAMES_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_semantic_neighbor_validation_frames}
STAGE2_DETECTOR_OUT=${STAGE2_DETECTOR_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_semantic_neighbor_validation_detector}
STAGE2_EVIDENCE_OUT=${STAGE2_EVIDENCE_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_semantic_neighbor_validation_evidence_objective_v2}
INTEGRATED_OUT=${INTEGRATED_OUT:-${EXTERNAL_OUT}/external_candidate_followup_v4_stage2_semantic_neighbor_validation}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
RUN_ID=${RUN_ID:-h001_v4_semantic_neighbor_stage2_validation}
TARGET_SELECTION_MODE=${TARGET_SELECTION_MODE:-semantic_neighbor}
TARGET_POINT_MODE=${TARGET_POINT_MODE:-position}
MAX_SEMANTIC_NEIGHBORS=${MAX_SEMANTIC_NEIGHBORS:-1}
MAX_RIVALS=${MAX_RIVALS:-1}
MAX_LOCAL_CONTEXTS=${MAX_LOCAL_CONTEXTS:-0}
MAX_LOCAL_CONTEXT_DISTANCE_M=${MAX_LOCAL_CONTEXT_DISTANCE_M:-2.5}
MAX_TARGETS_PER_REQUEST=${MAX_TARGETS_PER_REQUEST:-3}
MAX_CANDIDATES_PER_DECISION=${MAX_CANDIDATES_PER_DECISION:-6}
MAX_VIEWPOINTS_PER_TARGET=${MAX_VIEWPOINTS_PER_TARGET:-1}
SEMANTIC_NEIGHBOR_VIEWPOINTS_PER_TARGET=${SEMANTIC_NEIGHBOR_VIEWPOINTS_PER_TARGET:-1}
GROUNDED_POINT_HEIGHT_M=${GROUNDED_POINT_HEIGHT_M:-0.8}
GROUNDED_POINT_MAX_VERTICAL_GAP_M=${GROUNDED_POINT_MAX_VERTICAL_GAP_M:-2.0}
EXTERNAL_BRANCH_IDS=${EXTERNAL_BRANCH_IDS:-}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-position}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
SECOND_STAGE_OBJECTIVE_VERSION=${SECOND_STAGE_OBJECTIVE_VERSION:-v2}
VALIDATION_SCOPE=${VALIDATION_SCOPE:-v4_semantic_neighbor_diagnostic}
FOLLOWUP_LABEL=${FOLLOWUP_LABEL:-followup_v4}
INTEGRATED_SCHEMA_VERSION=${INTEGRATED_SCHEMA_VERSION:-h001.external_candidate_followup_v4_stage2_semantic_neighbor_validation.v1}
TERMINAL_ROWS_FILE=${TERMINAL_ROWS_FILE:-external_candidate_followup_v4_stage2_semantic_neighbor_terminal_rows.jsonl}
SUMMARY_FILE=${SUMMARY_FILE:-external_candidate_followup_v4_stage2_semantic_neighbor_summary.json}
LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/v4-semantic-neighbor-stage2-validation-${TS}.log}
STATUS=${STATUS:-${EXTERNAL_OUT}/v4_semantic_neighbor_stage2_validation_job_status.json}

mkdir -p \
  "${ROOT}/archive/logs/h001_runtime" \
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
    "exact_command": "TS=${TS} bash ${HYP}/scripts/h001_jobs/v4_semantic_neighbor_stage2_validation.sh",
    "followup_evidence_out": "${FOLLOWUP_EVIDENCE_OUT}",
    "stage2_plan_out": "${STAGE2_PLAN_OUT}",
    "stage2_frames_out": "${STAGE2_FRAMES_OUT}",
    "stage2_detector_out": "${STAGE2_DETECTOR_OUT}",
    "stage2_evidence_out": "${STAGE2_EVIDENCE_OUT}",
    "integrated_out": "${INTEGRATED_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "target_selection_mode": "${TARGET_SELECTION_MODE}",
    "target_point_mode": "${TARGET_POINT_MODE}",
    "max_local_contexts": "${MAX_LOCAL_CONTEXTS}",
    "max_local_context_distance_m": "${MAX_LOCAL_CONTEXT_DISTANCE_M}",
    "max_viewpoints_per_target": "${MAX_VIEWPOINTS_PER_TARGET}",
    "semantic_neighbor_viewpoints_per_target": "${SEMANTIC_NEIGHBOR_VIEWPOINTS_PER_TARGET}",
    "candidate_point_field": "${CANDIDATE_POINT_FIELD}",
    "grounded_point_height_m": "${GROUNDED_POINT_HEIGHT_M}",
    "grounded_point_max_vertical_gap_m": "${GROUNDED_POINT_MAX_VERTICAL_GAP_M}",
    "external_branch_ids": "${EXTERNAL_BRANCH_IDS}",
    "validation_scope": "${VALIDATION_SCOPE}",
    "verification_command": "cat ${STATUS} && cat ${INTEGRATED_OUT}/${SUMMARY_FILE}",
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
echo "exact_command=TS=${TS} bash ${HYP}/scripts/h001_jobs/v4_semantic_neighbor_stage2_validation.sh"
echo "followup_evidence_out=${FOLLOWUP_EVIDENCE_OUT}"
echo "stage2_plan_out=${STAGE2_PLAN_OUT}"
echo "stage2_frames_out=${STAGE2_FRAMES_OUT}"
echo "stage2_detector_out=${STAGE2_DETECTOR_OUT}"
echo "stage2_evidence_out=${STAGE2_EVIDENCE_OUT}"
echo "integrated_out=${INTEGRATED_OUT}"
echo "log=${LOG}"
echo "verification_command=cat ${STATUS} && cat ${INTEGRATED_OUT}/${SUMMARY_FILE}"

PLAN_EXTRA_ARGS=()
if [[ -n "${EXTERNAL_BRANCH_IDS}" ]]; then
  PLAN_EXTRA_ARGS+=(--external-branch-ids "${EXTERNAL_BRANCH_IDS}")
fi

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
docker image inspect "${HABITAT_IMG}" "${OPENVOCAB_IMG}" >/dev/null
python - <<PY
from pathlib import Path
paths = {
    "data_root": Path("${DATA_ROOT}"),
    "hm3d": Path("${DATA_ROOT}") / "scene_datasets" / "hm3d",
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "followup_rows": Path("${FOLLOWUP_EVIDENCE_OUT}") / "external_candidate_followup_evidence_rows.jsonl",
    "followup_summary": Path("${FOLLOWUP_EVIDENCE_OUT}") / "external_candidate_followup_evidence_summary.json",
    "groundingdino_config": Path("${GROUNDINGDINO_DIR}") / "config.json",
    "groundingdino_weights": Path("${GROUNDINGDINO_DIR}") / "model.safetensors",
    "sam2_checkpoint": Path("${SAM2_CHECKPOINT}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
print({"stage": "prerequisite_check_passed", "paths": {name: str(path) for name, path in paths.items()}})
PY

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
    --followup-evidence-rows "$(to_runs_path "${FOLLOWUP_EVIDENCE_OUT}")/external_candidate_followup_evidence_rows.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${STAGE2_PLAN_OUT}")" \
    --run-id "${RUN_ID}" \
    --target-selection-mode "${TARGET_SELECTION_MODE}" \
    --target-point-mode "${TARGET_POINT_MODE}" \
    --max-semantic-neighbors "${MAX_SEMANTIC_NEIGHBORS}" \
    --max-rivals "${MAX_RIVALS}" \
    --max-local-contexts "${MAX_LOCAL_CONTEXTS}" \
    --max-local-context-distance-m "${MAX_LOCAL_CONTEXT_DISTANCE_M}" \
    --max-targets-per-request "${MAX_TARGETS_PER_REQUEST}" \
    --max-candidate-ids "${MAX_CANDIDATES_PER_DECISION}" \
    --max-viewpoints-per-target "${MAX_VIEWPOINTS_PER_TARGET}" \
    --semantic-neighbor-viewpoints-per-target "${SEMANTIC_NEIGHBOR_VIEWPOINTS_PER_TARGET}" \
    --grounded-point-height-m "${GROUNDED_POINT_HEIGHT_M}" \
    --grounded-point-max-vertical-gap-m "${GROUNDED_POINT_MAX_VERTICAL_GAP_M}" \
    "${PLAN_EXTRA_ARGS[@]}"

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
    --candidate-point-field "${CANDIDATE_POINT_FIELD}" \
    --grounded-point-height-m "${GROUNDED_POINT_HEIGHT_M}" \
    --grounded-point-max-vertical-gap-m "${GROUNDED_POINT_MAX_VERTICAL_GAP_M}"

STAGE2_FRAME_ROWS="$(python - <<PY
from pathlib import Path
path = Path("${STAGE2_FRAMES_OUT}") / "postview_frames_v2.jsonl"
rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)"

if [[ "${DEVICE}" == "cuda" ]]; then
  GPU_FLAG="--gpus all"
else
  GPU_FLAG=""
fi

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
    --grounded-point-height-m "${GROUNDED_POINT_HEIGHT_M}" \
    --grounded-point-max-vertical-gap-m "${GROUNDED_POINT_MAX_VERTICAL_GAP_M}" \
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
    --followup-evidence-rows "$(to_runs_path "${FOLLOWUP_EVIDENCE_OUT}")/external_candidate_followup_evidence_rows.jsonl" \
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
    --followup-v2-summary "$(to_runs_path "${FOLLOWUP_EVIDENCE_OUT}")/external_candidate_followup_evidence_summary.json" \
    --followup-v2-rows "$(to_runs_path "${FOLLOWUP_EVIDENCE_OUT}")/external_candidate_followup_evidence_rows.jsonl" \
    --second-stage-plan-summary "$(to_runs_path "${STAGE2_PLAN_OUT}")/external_candidate_second_stage_identity_summary.json" \
    --second-stage-frame-summary "$(to_runs_path "${STAGE2_FRAMES_OUT}")/summary.json" \
    --second-stage-detector-summary "$(to_runs_path "${STAGE2_DETECTOR_OUT}")/summary.json" \
    --second-stage-evidence-summary "$(to_runs_path "${STAGE2_EVIDENCE_OUT}")/external_candidate_second_stage_identity_evidence_summary.json" \
    --second-stage-evidence-rows "$(to_runs_path "${STAGE2_EVIDENCE_OUT}")/external_candidate_second_stage_identity_evidence_rows.jsonl" \
    --out-root "$(to_runs_path "${INTEGRATED_OUT}")" \
    --validation-scope "${VALIDATION_SCOPE}" \
    --schema-version "${INTEGRATED_SCHEMA_VERSION}" \
    --followup-label "${FOLLOWUP_LABEL}" \
    --terminal-rows-file "${TERMINAL_ROWS_FILE}" \
    --summary-file "${SUMMARY_FILE}"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

plan = json.loads((Path("${STAGE2_PLAN_OUT}") / "external_candidate_second_stage_identity_summary.json").read_text(encoding="utf-8"))
frames = json.loads((Path("${STAGE2_FRAMES_OUT}") / "summary.json").read_text(encoding="utf-8"))
detector = json.loads((Path("${STAGE2_DETECTOR_OUT}") / "summary.json").read_text(encoding="utf-8"))
evidence = json.loads((Path("${STAGE2_EVIDENCE_OUT}") / "external_candidate_second_stage_identity_evidence_summary.json").read_text(encoding="utf-8"))
integrated = json.loads((Path("${INTEGRATED_OUT}") / "${SUMMARY_FILE}").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.v4_semantic_neighbor_stage2_validation_job.v1",
    "stage2_plan_out": "${STAGE2_PLAN_OUT}",
    "stage2_frames_out": "${STAGE2_FRAMES_OUT}",
    "stage2_detector_out": "${STAGE2_DETECTOR_OUT}",
    "stage2_evidence_out": "${STAGE2_EVIDENCE_OUT}",
    "integrated_out": "${INTEGRATED_OUT}",
    "target_selection_mode": plan.get("target_selection_mode"),
    "target_point_mode": plan.get("target_point_mode"),
    "max_local_contexts": plan.get("max_local_contexts"),
    "max_local_context_distance_m": plan.get("max_local_context_distance_m"),
    "stage2_request_rows": plan.get("request_rows"),
    "stage2_plan_rows": plan.get("plan_rows"),
    "stage2_role_counts": plan.get("role_counts"),
    "stage2_frame_rows": frames.get("rows_exported"),
    "stage2_rendered_heading_count": frames.get("rendered_heading_count"),
    "stage2_detector": {
        "rows": detector.get("rows"),
        "rows_with_detector_box_rate": detector.get("rows_with_detector_box_rate"),
        "rows_with_sam2_mask_rate": detector.get("rows_with_sam2_mask_rate"),
        "rows_with_candidate_association_rate": detector.get("rows_with_candidate_association_rate"),
        "candidate_point_field": detector.get("candidate_point_field"),
    },
    "stage2_action_counts": evidence.get("action_counts"),
    "stage2_gate": evidence.get("gate"),
    "integrated_gate": integrated.get("integrated", {}).get("gate"),
    "terminal_action_counts": integrated.get("integrated", {}).get("terminal_action_counts"),
    "first_eval_rerun_blocked": integrated.get("interpretation", {}).get("first_eval_rerun_blocked"),
    "utility_proof_passed": integrated.get("interpretation", {}).get("utility_proof_passed"),
    "uses_gt_for_action": bool(
        plan.get("uses_gt_for_action")
        or frames.get("uses_gt_for_action")
        or detector.get("uses_gt_for_action")
        or evidence.get("uses_gt_for_action")
        or integrated.get("uses_gt_for_action")
    ),
    "uses_gt_for_analysis": bool(
        plan.get("uses_gt_for_analysis")
        or evidence.get("uses_gt_for_analysis")
        or integrated.get("uses_gt_for_analysis")
    ),
}
(Path("${EXTERNAL_OUT}") / "v4_semantic_neighbor_stage2_validation_job_summary.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in action path")
if payload["stage2_plan_rows"] != payload["stage2_frame_rows"]:
    raise RuntimeError({"stage2_plan_frame_mismatch": [payload["stage2_plan_rows"], payload["stage2_frame_rows"]]})
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
