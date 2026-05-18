#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

MANIFEST=${MANIFEST:-${HYP}/manifests/h001_v3_fresh_validation_v1.json}
MANIFEST_SPLIT=${MANIFEST_SPLIT:-v3_fresh_validation_v1}
SCENE_SPECS_FILE=${SCENE_SPECS_FILE:-${HYP}/manifests/v3_fresh_validation_v1_scenes.txt}
ARTIFACT_OUT=${ARTIFACT_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1}
COVERAGE_OUT=${COVERAGE_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity}
LOG=${LOG:-${ROOT}/logs/v3-fresh-validation-artifact-coverage-${TS}.log}
PIPELINE_STATUS=${PIPELINE_STATUS:-${ARTIFACT_OUT}/pipeline_status.json}

ARTIFACT_ID=${ARTIFACT_ID:-v3_fresh_validation_spatial_nms_p97_k20_v1}
TRAJECTORY_SUFFIX=${TRAJECTORY_SUFFIX:-v3_fresh_validation_spatial_nms_p97_k20_v1}
FRAMES=${FRAMES:-256}
TOP_PERCENTILE=${TOP_PERCENTILE:-97.0}
MAX_CANDIDATES=${MAX_CANDIDATES:-20}
CANDIDATE_SELECTION_MODE=${CANDIDATE_SELECTION_MODE:-spatial_nms}
SPATIAL_NMS_MIN_DISTANCE_CELLS=${SPATIAL_NMS_MIN_DISTANCE_CELLS:-20.0}
EXPECTED_SCENE_COUNT=${EXPECTED_SCENE_COUNT:-13}
EXPECTED_QUERY_ROWS=${EXPECTED_QUERY_ROWS:-78}
EPISODES=${EPISODES:-100}
POLICY_NAME=${POLICY_NAME:-h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1}
RUN_ID=${RUN_ID:-h001_v3_fresh_validation_spatial_nms_p97_k20_coverage_sanity_${TS}}

mkdir -p "${ROOT}/logs" "${ARTIFACT_OUT}" "${COVERAGE_OUT}"
exec > >(tee -a "${LOG}") 2>&1

write_status() {
  local status="$1"
  local stage="$2"
  python - "$PIPELINE_STATUS" "$status" "$stage" <<PY
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "status": sys.argv[2],
    "stage": sys.argv[3],
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "scene_specs_file": "${SCENE_SPECS_FILE}",
    "artifact_out": "${ARTIFACT_OUT}",
    "candidate_artifact": "${ARTIFACT_OUT}/all_scenes_aligned.jsonl",
    "coverage_out": "${COVERAGE_OUT}",
    "log": "${LOG}",
    "artifact_id": "${ARTIFACT_ID}",
    "frames": int("${FRAMES}"),
    "top_percentile": float("${TOP_PERCENTILE}"),
    "max_candidates": int("${MAX_CANDIDATES}"),
    "spatial_nms_min_distance_cells": float("${SPATIAL_NMS_MIN_DISTANCE_CELLS}"),
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
echo "manifest=${MANIFEST}"
echo "manifest_split=${MANIFEST_SPLIT}"
echo "scene_specs_file=${SCENE_SPECS_FILE}"
echo "artifact_out=${ARTIFACT_OUT}"
echo "coverage_out=${COVERAGE_OUT}"
echo "log=${LOG}"
echo "expected_files=${ARTIFACT_OUT}/all_scenes_aligned.jsonl ${ARTIFACT_OUT}/coverage_check.json ${COVERAGE_OUT}/artifact_coverage.json"
echo "verification_command=cat ${PIPELINE_STATUS} && cat ${ARTIFACT_OUT}/job_status.json && cat ${ARTIFACT_OUT}/coverage_check.json && cat ${COVERAGE_OUT}/artifact_coverage.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path
paths = {
    "manifest": Path("${MANIFEST}"),
    "scene_specs_file": Path("${SCENE_SPECS_FILE}"),
    "calibration_artifact_job": Path("${HYP}/runtime/calibration_artifact_job.sh"),
    "coverage_sanity_job": Path("${HYP}/runtime/jobs/first_eval_coverage_sanity.sh"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
print({"stage": "prerequisite_check_passed", "paths": {name: str(path) for name, path in paths.items()}})
PY

CURRENT_STAGE=candidate_artifact_generation
write_status running "${CURRENT_STAGE}"
OUT_ROOT="${ARTIFACT_OUT}" \
ARTIFACT_ID="${ARTIFACT_ID}" \
TRAJECTORY_SUFFIX="${TRAJECTORY_SUFFIX}" \
SCENE_SPECS_FILE="${SCENE_SPECS_FILE}" \
FRAMES="${FRAMES}" \
TOP_PERCENTILE="${TOP_PERCENTILE}" \
MAX_CANDIDATES="${MAX_CANDIDATES}" \
CANDIDATE_SELECTION_MODE="${CANDIDATE_SELECTION_MODE}" \
SPATIAL_NMS_MIN_DISTANCE_CELLS="${SPATIAL_NMS_MIN_DISTANCE_CELLS}" \
EXPECTED_SCENE_COUNT="${EXPECTED_SCENE_COUNT}" \
EXPECTED_QUERY_ROWS="${EXPECTED_QUERY_ROWS}" \
"${HYP}/runtime/calibration_artifact_job.sh"

CURRENT_STAGE=coverage_gate
write_status running "${CURRENT_STAGE}"
MANIFEST="${MANIFEST}" \
MANIFEST_SPLIT="${MANIFEST_SPLIT}" \
EPISODES="${EPISODES}" \
CANDIDATE_ARTIFACT="${ARTIFACT_OUT}/all_scenes_aligned.jsonl" \
POLICY_NAME="${POLICY_NAME}" \
RUN_ID="${RUN_ID}" \
OUT_ROOT="${COVERAGE_OUT}" \
"${HYP}/runtime/jobs/first_eval_coverage_sanity.sh"

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
