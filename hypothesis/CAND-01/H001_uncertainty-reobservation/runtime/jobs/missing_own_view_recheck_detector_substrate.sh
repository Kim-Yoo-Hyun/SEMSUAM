#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

export PLAN_OUT=${PLAN_OUT:-${RUNS_ROOT}/h001_missing_own_view_recheck_observation_v1}
export FRAME_OUT=${FRAME_OUT:-${RUNS_ROOT}/h001_missing_own_view_recheck_observation_frames_v1}
export FRAMES=${FRAMES:-${FRAME_OUT}/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl}
export FRAME_ROOT=${FRAME_ROOT:-${FRAME_OUT}}
export CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${PLAN_OUT}/missing_own_view_candidate_artifact.jsonl}
export OUT=${OUT:-${RUNS_ROOT}/h001_missing_own_view_recheck_observation_detector_substrate_v1}
export DETECTOR_OUT=${DETECTOR_OUT:-${OUT}/detector_v3c}
export LOG=${LOG:-${HYP}/runtime/logs/missing-own-view-recheck-detector-substrate-${TS}.log}
export STATUS=${STATUS:-${OUT}/job_status.json}

export EXPECTED_POLICY=${EXPECTED_POLICY:-MissingOwnViewRecheckObservation}
export EXPECTED_FRAME_ROWS=${EXPECTED_FRAME_ROWS:-80}
export MAX_FRAMES=${MAX_FRAMES:-80}
export MAX_CANDIDATES_PER_FRAME=${MAX_CANDIDATES_PER_FRAME:-1}
export CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-grounded_position}
export PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M:-0.0,0.4,0.8,1.2,1.6,2.0,2.4}
export MIN_DETECTOR_BOX_RATE=${MIN_DETECTOR_BOX_RATE:-0.80}
export MIN_SAM2_MASK_RATE=${MIN_SAM2_MASK_RATE:-0.80}
export MIN_CANDIDATE_ASSOCIATION_RATE=${MIN_CANDIDATE_ASSOCIATION_RATE:-0.40}
export MAX_DEBUG_IMAGES=${MAX_DEBUG_IMAGES:-240}

exec bash "${HYP}/runtime/jobs/expanded_retrieval_detector_substrate.sh"
