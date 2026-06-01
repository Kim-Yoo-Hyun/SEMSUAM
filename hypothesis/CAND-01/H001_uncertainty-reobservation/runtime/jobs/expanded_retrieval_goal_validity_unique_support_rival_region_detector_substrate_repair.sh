#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

export PLAN_OUT=${PLAN_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_unique_support_rival_region_v1}
export FRAME_OUT=${FRAME_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_unique_support_rival_region_frames_v1}
export FRAMES=${FRAMES:-${FRAME_OUT}/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl}
export FRAME_ROOT=${FRAME_ROOT:-${FRAME_OUT}}
export CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${PLAN_OUT}/unique_support_rival_region_candidate_artifact.jsonl}
export OUT=${OUT:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair_v1}
export DETECTOR_OUT=${DETECTOR_OUT:-${OUT}/detector_v3c}
export LOG=${LOG:-${HYP}/runtime/logs/unique-support-rival-region-detector-substrate-repair-${TS}.log}
export STATUS=${STATUS:-${OUT}/job_status.json}

export EXPECTED_POLICY=${EXPECTED_POLICY:-ExpandedRetrievalGoalValidityUniqueSupportRivalRegion}
export EXPECTED_FRAME_ROWS=${EXPECTED_FRAME_ROWS:-30}
export MAX_FRAMES=${MAX_FRAMES:-30}
export CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-grounded_position}
export PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M:-0.0,0.4,0.8,1.2,1.6,2.0,2.4}
export ASSOCIATION_REPAIR_VARIANT=${ASSOCIATION_REPAIR_VARIANT:-mask_depth_1_25_v1}
export ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.25}
export MIN_DETECTOR_BOX_RATE=${MIN_DETECTOR_BOX_RATE:-0.80}
export MIN_SAM2_MASK_RATE=${MIN_SAM2_MASK_RATE:-0.80}
export MIN_CANDIDATE_ASSOCIATION_RATE=${MIN_CANDIDATE_ASSOCIATION_RATE:-0.40}
export MAX_DEBUG_IMAGES=${MAX_DEBUG_IMAGES:-160}

exec bash "${HYP}/runtime/jobs/expanded_retrieval_detector_substrate.sh"
