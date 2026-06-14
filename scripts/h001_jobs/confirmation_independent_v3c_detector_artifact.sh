#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

export MANIFEST=${MANIFEST:-${HYP}/manifests/h001_confirmation_independent_v1.json}
export MANIFEST_SPLIT=${MANIFEST_SPLIT:-confirmation_independent_v1}
export CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_replacement_probe_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
export POLICY_OUT=${POLICY_OUT:-${RUNS_ROOT}/h001_confirmation_independent_policy_spatial_nms_p97_k20_v1/policy_revision}
export FRAMES_OUT=${FRAMES_OUT:-${RUNS_ROOT}/h001_confirmation_independent_postview_frames_v2_spatial_nms_p97_k20_v1}
export DETECTOR_OUT=${DETECTOR_OUT:-${RUNS_ROOT}/h001_confirmation_independent_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1}
export RUN_ID=${RUN_ID:-h001_confirmation_independent_v1_policy_revision_${TS}}
export EPISODES=${EPISODES:-20}
export MAX_FRAMES=${MAX_FRAMES:-20}
export MIN_FRAME_ROWS=${MIN_FRAME_ROWS:-18}
export PROMOTION_ASSOCIATION_RATE=${PROMOTION_ASSOCIATION_RATE:-0.0}
export LOG=${LOG:-${ROOT}/logs/confirmation-independent-v3c-detector-artifact-${TS}.log}

exec "${HYP}/scripts/h001_jobs/first_eval_replacement_v3c_detector_artifact.sh"
