#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yoohyun/research3}"
RUNS_ROOT="${RUNS_ROOT:-${ROOT}/local_dataset/runs}"
DATA_ROOT="${DATA_ROOT:-${ROOT}/local_dataset/data}"
HABITAT_IMG="${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}"
DOCKER_GPU_ARGS="${DOCKER_GPU_ARGS:---gpus all}"
DOCKER_USER_ARGS="${DOCKER_USER_ARGS:---user $(id -u):$(id -g)}"

PLAN_OUT="${PLAN_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1}"
FRAME_OUT="${FRAME_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_frames_v1}"
PROJECTION_OUT="${PROJECTION_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_projection_v1}"
STATUS="${STATUS:-${PROJECTION_OUT}/frame_projection_job_status.json}"

EXPECTED_FRAME_ROWS="${EXPECTED_FRAME_ROWS:-48}"
MAX_DECISIONS="${MAX_DECISIONS:-0}"
MAX_CANDIDATES_PER_DECISION="${MAX_CANDIDATES_PER_DECISION:-1}"
MAX_CANDIDATES_PER_FRAME="${MAX_CANDIDATES_PER_FRAME:-1}"
MIN_VISIBLE_ROW_RATE="${MIN_VISIBLE_ROW_RATE:-0.95}"
POLICY="${POLICY:-ExpandedRetrievalGoalValidityPartialRelationDepthObservation}"
PYTHON_BIN="${PYTHON_BIN:-/opt/conda/bin/python}"
PYTHONPATH_IN_CONTAINER="/workspace/src"

mkdir -p "${FRAME_OUT}" "${PROJECTION_OUT}" "$(dirname "${STATUS}")"
chmod -R ugo+rwX "${FRAME_OUT}" "${PROJECTION_OUT}"

write_status() {
  local status="$1"
  cat > "${STATUS}" <<EOF
{
  "status": "${status}",
  "plan_out": "${PLAN_OUT}",
  "frame_out": "${FRAME_OUT}",
  "projection_out": "${PROJECTION_OUT}",
  "expected_frame_rows": ${EXPECTED_FRAME_ROWS},
  "policy": "${POLICY}",
  "uses_gt_for_action": false
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
  -v "${ROOT}:/workspace" \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  "${PYTHON_BIN}" -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1/partial_relation_depth_observation_plan.jsonl \
    --candidate-artifact /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1/partial_relation_depth_candidate_artifact.jsonl \
    --out-root /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_frames_v1 \
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
  -v "${ROOT}:/workspace" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  "${PYTHON_BIN}" -m h001_runtime.filter_nonblank_frame_summary \
    --frame-summary /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_frames_v1/rival_identity_frame_summary.jsonl \
    --frame-root /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_frames_v1 \
    --out-root /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_frames_v1/nonblank_filter_v1 \
    --min-stddev 0.0

# shellcheck disable=SC2086
docker run --rm --ipc=host ${DOCKER_USER_ARGS} \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH="${PYTHONPATH_IN_CONTAINER}" \
  -v "${ROOT}:/workspace" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  "${PYTHON_BIN}" -m h001_runtime.smoke_expanded_retrieval_projection_anchor \
    --frames /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl \
    --frame-root /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_frames_v1 \
    --candidate-artifact /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1/partial_relation_depth_candidate_artifact.jsonl \
    --out-root /runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_projection_v1 \
    --projection-anchor-height-offsets-m 0.0,0.4,0.8,1.2,1.6,2.0,2.4 \
    --candidate-point-field grounded_position \
    --max-candidates-per-frame "${MAX_CANDIDATES_PER_FRAME}" \
    --expected-rows "${EXPECTED_FRAME_ROWS}" \
    --min-visible-row-rate "${MIN_VISIBLE_ROW_RATE}"

write_status "completed"
