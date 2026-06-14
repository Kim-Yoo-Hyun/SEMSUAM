#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

MANIFEST=${MANIFEST:-${HYP}/manifests/h001_dense_conflict_v1.json}
MANIFEST_SPLIT=${MANIFEST_SPLIT:-dense_conflict_v1}
SCENE_SPECS_FILE=${SCENE_SPECS_FILE:-${HYP}/manifests/dense_conflict_v1_scenes.txt}
ARTIFACT_OUT=${ARTIFACT_OUT:-${RUNS_ROOT}/h001_dense_conflict_artifacts_spatial_nms_p95_k100_d10_v1}
RECALL_OUT=${RECALL_OUT:-${RUNS_ROOT}/h001_dense_conflict_recall_gate_spatial_nms_p95_k100_d10_v1}
LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/dense-conflict-artifact-p95-k100-d10-${TS}.log}
PIPELINE_STATUS=${PIPELINE_STATUS:-${ARTIFACT_OUT}/pipeline_status.json}

HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
ARTIFACT_ID=${ARTIFACT_ID:-dense_conflict_spatial_nms_p95_k100_d10_v1}
TRAJECTORY_SUFFIX=${TRAJECTORY_SUFFIX:-dense_conflict_spatial_nms_p95_k100_d10_v1}
FRAMES=${FRAMES:-256}
WIDTH=${WIDTH:-320}
HEIGHT=${HEIGHT:-240}
DEPTH_SAMPLE_RATE=${DEPTH_SAMPLE_RATE:-8}
TOP_PERCENTILE=${TOP_PERCENTILE:-95.0}
MAX_CANDIDATES=${MAX_CANDIDATES:-100}
CANDIDATE_SELECTION_MODE=${CANDIDATE_SELECTION_MODE:-spatial_nms}
SPATIAL_NMS_MIN_DISTANCE_CELLS=${SPATIAL_NMS_MIN_DISTANCE_CELLS:-10.0}
EXPECTED_SCENE_COUNT=${EXPECTED_SCENE_COUNT:-4}
EXPECTED_QUERY_ROWS=${EXPECTED_QUERY_ROWS:-24}

mkdir -p "$(dirname "${LOG}")" "${ARTIFACT_OUT}" "${RECALL_OUT}"
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
    "schema_version": "h001.dense_conflict_candidate_artifact_job.v1",
    "status": sys.argv[2],
    "stage": sys.argv[3],
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "scene_specs_file": "${SCENE_SPECS_FILE}",
    "artifact_out": "${ARTIFACT_OUT}",
    "candidate_artifact": "${ARTIFACT_OUT}/all_scenes_aligned.jsonl",
    "recall_out": "${RECALL_OUT}",
    "recall_summary": "${RECALL_OUT}/dense_conflict_recall_summary.json",
    "log": "${LOG}",
    "artifact_id": "${ARTIFACT_ID}",
    "frames": int("${FRAMES}"),
    "width": int("${WIDTH}"),
    "height": int("${HEIGHT}"),
    "depth_sample_rate": int("${DEPTH_SAMPLE_RATE}"),
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

cat > "${ARTIFACT_OUT}/run_contract.txt" <<EOF
job: dense_conflict_candidate_artifact
working_directory: ${ROOT}
command: TS=${TS} bash ${HYP}/scripts/h001_jobs/dense_conflict_candidate_artifact.sh
manifest: ${MANIFEST}
manifest_split: ${MANIFEST_SPLIT}
scene_specs_file: ${SCENE_SPECS_FILE}
artifact_out: ${ARTIFACT_OUT}
candidate_artifact: ${ARTIFACT_OUT}/all_scenes_aligned.jsonl
recall_out: ${RECALL_OUT}
expected_files:
  - ${ARTIFACT_OUT}/pipeline_status.json
  - ${ARTIFACT_OUT}/job_status.json
  - ${ARTIFACT_OUT}/coverage_check.json
  - ${ARTIFACT_OUT}/all_scenes_aligned.jsonl
  - ${RECALL_OUT}/dense_conflict_recall_summary.json
verification_command:
  cat ${PIPELINE_STATUS}
  cat ${ARTIFACT_OUT}/job_status.json
  cat ${ARTIFACT_OUT}/coverage_check.json
  cat ${RECALL_OUT}/dense_conflict_recall_summary.json
EOF

echo "started_at=$(date -Is)"
echo "working_directory=${ROOT}"
echo "log=${LOG}"
echo "artifact_out=${ARTIFACT_OUT}"
echo "recall_out=${RECALL_OUT}"
echo "verification_command=cat ${PIPELINE_STATUS} && cat ${RECALL_OUT}/dense_conflict_recall_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path

paths = {
    "manifest": Path("${MANIFEST}"),
    "scene_specs_file": Path("${SCENE_SPECS_FILE}"),
    "calibration_artifact_job": Path("${HYP}/runtime/calibration_artifact_job.sh"),
    "recall_gate": Path("${HYP}/src/h001_runtime/probe_dense_conflict_recall.py"),
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
WIDTH="${WIDTH}" \
HEIGHT="${HEIGHT}" \
DEPTH_SAMPLE_RATE="${DEPTH_SAMPLE_RATE}" \
TOP_PERCENTILE="${TOP_PERCENTILE}" \
MAX_CANDIDATES="${MAX_CANDIDATES}" \
CANDIDATE_SELECTION_MODE="${CANDIDATE_SELECTION_MODE}" \
SPATIAL_NMS_MIN_DISTANCE_CELLS="${SPATIAL_NMS_MIN_DISTANCE_CELLS}" \
EXPECTED_SCENE_COUNT="${EXPECTED_SCENE_COUNT}" \
EXPECTED_QUERY_ROWS="${EXPECTED_QUERY_ROWS}" \
"${HYP}/runtime/calibration_artifact_job.sh"

CURRENT_STAGE=final_recall_gate
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.probe_dense_conflict_recall \
    --data-root /data \
    --manifest "/workspace/configs/h001/manifests/h001_dense_conflict_v1.json" \
    --manifest-split "${MANIFEST_SPLIT}" \
    --roles all \
    --candidate-artifact "spatial_nms_p95_k100_d10=/runs/$(basename "${ARTIFACT_OUT}")/all_scenes_aligned.jsonl" \
    --out-root "/runs/$(basename "${RECALL_OUT}")"

python - "${RECALL_OUT}/dense_conflict_recall_summary.json" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps({
    "passes_any_dense_recall_gate": summary.get("passes_any_dense_recall_gate"),
    "selected_artifact_for_next_detector_step": summary.get("selected_artifact_for_next_detector_step"),
    "role_counts": summary.get("role_counts"),
    "by_artifact": summary.get("by_artifact"),
}, indent=2, sort_keys=True))
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
