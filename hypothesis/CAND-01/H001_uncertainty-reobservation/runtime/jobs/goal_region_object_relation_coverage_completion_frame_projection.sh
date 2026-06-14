#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yoohyun/research3}"
RUNS_ROOT="${RUNS_ROOT:-${ROOT}/local_dataset/runs}"
DATA_ROOT="${DATA_ROOT:-${ROOT}/local_dataset/data}"
HABITAT_IMG="${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}"
DOCKER_GPU_ARGS="${DOCKER_GPU_ARGS:---gpus all}"
DOCKER_USER_ARGS="${DOCKER_USER_ARGS:---user $(id -u):$(id -g)}"

SOURCE_NAME="${SOURCE_NAME:-h001_goal_region_object_relation_coverage_completion_v1}"
GEOMETRY_NAME="${GEOMETRY_NAME:-h001_expanded_retrieval_paper_scale_local_context_plan_v1}"
PLAN_OUT="${PLAN_OUT:-${RUNS_ROOT}/h001_goal_region_object_relation_coverage_completion_frame_plan_v1}"
FRAME_OUT="${FRAME_OUT:-${RUNS_ROOT}/h001_goal_region_object_relation_coverage_completion_frames_v1}"
PROJECTION_OUT="${PROJECTION_OUT:-${RUNS_ROOT}/h001_goal_region_object_relation_coverage_completion_projection_v1}"
STATUS="${STATUS:-${PROJECTION_OUT}/frame_projection_job_status.json}"

EXPECTED_FRAME_ROWS="${EXPECTED_FRAME_ROWS:-48}"
MAX_DECISIONS="${MAX_DECISIONS:-0}"
MAX_CANDIDATES_PER_DECISION="${MAX_CANDIDATES_PER_DECISION:-2}"
MAX_CANDIDATES_PER_FRAME="${MAX_CANDIDATES_PER_FRAME:-2}"
MIN_VISIBLE_ROW_RATE="${MIN_VISIBLE_ROW_RATE:-0.95}"
POLICY="${POLICY:-GoalRegionObjectRelationCoverageCompletion}"
PYTHON_BIN="${PYTHON_BIN:-/opt/conda/bin/python}"
PYTHONPATH_IN_CONTAINER="/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime"

SOURCE_ROOT="/runs/${SOURCE_NAME}"
GEOMETRY_ARTIFACT="/runs/${GEOMETRY_NAME}/expanded_retrieval_local_context_candidate_artifact.jsonl"
PLAN_NAME="$(basename "${PLAN_OUT}")"
FRAME_NAME="$(basename "${FRAME_OUT}")"
PROJECTION_NAME="$(basename "${PROJECTION_OUT}")"
PLAN_ROWS_FILE="goal_region_object_relation_coverage_completion_frame_plan_rows.jsonl"
CANDIDATE_ARTIFACT_FILE="goal_region_object_relation_coverage_completion_candidate_artifact.jsonl"
FRAME_SUMMARY_FILE="${FRAME_SUMMARY_FILE:-postview_frames_v2.jsonl}"
NONBLANK_FRAME_SUMMARY_FILE="rival_identity_frame_summary_nonblank.jsonl"

mkdir -p "${PLAN_OUT}" "${FRAME_OUT}" "${PROJECTION_OUT}" "$(dirname "${STATUS}")"

docker run --rm --user 0:0 \
  -v "${RUNS_ROOT}:/runs" \
  "${HABITAT_IMG}" \
  /bin/sh -lc "chmod -R ugo+rwX /runs/${PLAN_NAME} /runs/${FRAME_NAME} /runs/${PROJECTION_NAME} 2>/dev/null || true"

chmod -R ugo+rwX "${PLAN_OUT}" "${FRAME_OUT}" "${PROJECTION_OUT}" 2>/dev/null || true

write_status() {
  local status="$1"
  cat > "${STATUS}" <<EOF
{
  "status": "${status}",
  "source_root": "${RUNS_ROOT}/${SOURCE_NAME}",
  "geometry_artifact": "${RUNS_ROOT}/${GEOMETRY_NAME}/expanded_retrieval_local_context_candidate_artifact.jsonl",
  "plan_out": "${PLAN_OUT}",
  "frame_out": "${FRAME_OUT}",
  "projection_out": "${PROJECTION_OUT}",
  "expected_frame_rows": ${EXPECTED_FRAME_ROWS},
  "max_candidates_per_decision": ${MAX_CANDIDATES_PER_DECISION},
  "max_candidates_per_frame": ${MAX_CANDIDATES_PER_FRAME},
  "min_visible_row_rate": ${MIN_VISIBLE_ROW_RATE},
  "policy": "${POLICY}",
  "uses_gt_for_action": false,
  "paper_claim_allowed": false
}
EOF
}

write_status "running"
trap 'write_status "failed"' ERR

# shellcheck disable=SC2086
docker run --rm --ipc=host ${DOCKER_GPU_ARGS} ${DOCKER_USER_ARGS} \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH="${PYTHONPATH_IN_CONTAINER}" \
  -v "${ROOT}:/workspace:ro" \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  "${PYTHON_BIN}" -m h001_runtime.plan_goal_region_object_relation_coverage_completion_frame_projection \
    --data-root /data \
    --input-root "${SOURCE_ROOT}" \
    --geometry-candidate-artifact "${GEOMETRY_ARTIFACT}" \
    --out-root "/runs/${PLAN_NAME}"

# shellcheck disable=SC2086
docker run --rm --ipc=host ${DOCKER_GPU_ARGS} ${DOCKER_USER_ARGS} \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH="${PYTHONPATH_IN_CONTAINER}" \
  -v "${ROOT}:/workspace:ro" \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  "${PYTHON_BIN}" -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions "/runs/${PLAN_NAME}/${PLAN_ROWS_FILE}" \
    --candidate-artifact "/runs/${PLAN_NAME}/${CANDIDATE_ARTIFACT_FILE}" \
    --out-root "/runs/${FRAME_NAME}" \
    --policy "${POLICY}" \
    --max-decisions "${MAX_DECISIONS}" \
    --max-candidates-per-decision "${MAX_CANDIDATES_PER_DECISION}" \
    --candidate-point-field grounded_position \
    --yaw-offsets=-30,0,30 \
    --width 160 \
    --height 120 \
    --camera-height 1.5 \
    --hfov 90

# shellcheck disable=SC2086
docker run --rm --ipc=host ${DOCKER_USER_ARGS} \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH="${PYTHONPATH_IN_CONTAINER}" \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  "${PYTHON_BIN}" -m h001_runtime.filter_nonblank_frame_summary \
    --frame-summary "/runs/${FRAME_NAME}/${FRAME_SUMMARY_FILE}" \
    --frame-root "/runs/${FRAME_NAME}" \
    --out-root "/runs/${FRAME_NAME}/nonblank_filter_v1" \
    --min-stddev 0.0

# shellcheck disable=SC2086
docker run --rm --ipc=host ${DOCKER_USER_ARGS} \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH="${PYTHONPATH_IN_CONTAINER}" \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  "${PYTHON_BIN}" -m h001_runtime.smoke_expanded_retrieval_projection_anchor \
    --frames "/runs/${FRAME_NAME}/nonblank_filter_v1/${NONBLANK_FRAME_SUMMARY_FILE}" \
    --frame-root "/runs/${FRAME_NAME}" \
    --candidate-artifact "/runs/${PLAN_NAME}/${CANDIDATE_ARTIFACT_FILE}" \
    --out-root "/runs/${PROJECTION_NAME}" \
    --projection-anchor-height-offsets-m 0.0,0.4,0.8,1.2,1.6,2.0,2.4 \
    --candidate-point-field grounded_position \
    --max-candidates-per-frame "${MAX_CANDIDATES_PER_FRAME}" \
    --expected-rows "${EXPECTED_FRAME_ROWS}" \
    --min-visible-row-rate "${MIN_VISIBLE_ROW_RATE}"

write_status "completed"

docker run --rm --user 0:0 \
  -v "${RUNS_ROOT}:/runs" \
  "${HABITAT_IMG}" \
  /bin/sh -lc "chmod -R ugo+rwX /runs/${PLAN_NAME} /runs/${FRAME_NAME} /runs/${PROJECTION_NAME} 2>/dev/null || true"
