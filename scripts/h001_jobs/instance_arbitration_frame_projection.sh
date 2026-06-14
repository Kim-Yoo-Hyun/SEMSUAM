#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yoohyun/research3}"
RUNS_ROOT="${RUNS_ROOT:-${ROOT}/local_dataset/runs}"
DATA_ROOT="${DATA_ROOT:-${ROOT}/local_dataset/data}"
HABITAT_IMG="${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}"
DOCKER_GPU_ARGS="${DOCKER_GPU_ARGS:---gpus all}"
DOCKER_USER_ARGS="${DOCKER_USER_ARGS:---user $(id -u):$(id -g)}"

PLAN_OUT="${PLAN_OUT:-${RUNS_ROOT}/h001_instance_arbitration_evidence_v1}"
FRAME_OUT="${FRAME_OUT:-${RUNS_ROOT}/h001_instance_arbitration_evidence_frames_v1}"
PROJECTION_OUT="${PROJECTION_OUT:-${RUNS_ROOT}/h001_instance_arbitration_evidence_projection_v1}"
STATUS="${STATUS:-${PROJECTION_OUT}/frame_projection_job_status.json}"

EXPECTED_FRAME_ROWS="${EXPECTED_FRAME_ROWS:-172}"
MAX_DECISIONS="${MAX_DECISIONS:-0}"
MAX_CANDIDATES_PER_DECISION="${MAX_CANDIDATES_PER_DECISION:-2}"
MAX_CANDIDATES_PER_FRAME="${MAX_CANDIDATES_PER_FRAME:-2}"
MIN_VISIBLE_ROW_RATE="${MIN_VISIBLE_ROW_RATE:-0.95}"
POLICY="${POLICY:-InstanceArbitrationPairEvidence}"
PYTHON_BIN="${PYTHON_BIN:-/opt/conda/bin/python}"
PYTHONPATH_IN_CONTAINER="/workspace/src"

PLAN_NAME="$(basename "${PLAN_OUT}")"
FRAME_NAME="$(basename "${FRAME_OUT}")"
PROJECTION_NAME="$(basename "${PROJECTION_OUT}")"

mkdir -p "${FRAME_OUT}" "${PROJECTION_OUT}" "$(dirname "${STATUS}")"

# Previous Docker runs can leave artifacts owned by root on the host.
docker run --rm --user 0:0 \
  -v "${RUNS_ROOT}:/runs" \
  "${HABITAT_IMG}" \
  /bin/sh -lc "chmod -R ugo+rwX /runs/${FRAME_NAME} /runs/${PROJECTION_NAME} 2>/dev/null || true"

chmod -R ugo+rwX "${FRAME_OUT}" "${PROJECTION_OUT}" 2>/dev/null || true

write_status() {
  local status="$1"
  cat > "${STATUS}" <<EOF
{
  "status": "${status}",
  "plan_out": "${PLAN_OUT}",
  "frame_out": "${FRAME_OUT}",
  "projection_out": "${PROJECTION_OUT}",
  "expected_frame_rows": ${EXPECTED_FRAME_ROWS},
  "max_candidates_per_decision": ${MAX_CANDIDATES_PER_DECISION},
  "max_candidates_per_frame": ${MAX_CANDIDATES_PER_FRAME},
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
  -v "${ROOT}:/workspace:ro" \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -w /workspace \
  "${HABITAT_IMG}" \
  "${PYTHON_BIN}" -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions "/runs/${PLAN_NAME}/instance_arbitration_observation_plan.jsonl" \
    --candidate-artifact "/runs/${PLAN_NAME}/instance_arbitration_candidate_artifact_rows.jsonl" \
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
    --frame-summary "/runs/${FRAME_NAME}/rival_identity_frame_summary.jsonl" \
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
    --frames "/runs/${FRAME_NAME}/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl" \
    --frame-root "/runs/${FRAME_NAME}" \
    --candidate-artifact "/runs/${PLAN_NAME}/instance_arbitration_candidate_artifact_rows.jsonl" \
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
  /bin/sh -lc "chmod -R ugo+rwX /runs/${FRAME_NAME} /runs/${PROJECTION_NAME} 2>/dev/null || true"
