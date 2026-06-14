#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
DATA_ROOT=${DATA_ROOT:-${ROOT}/local_dataset/data}
MODEL_ROOT=${MODEL_ROOT:-${ROOT}/local_dataset/models}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

CONTRACT=${CONTRACT:-${HYP}/manifests/h001_expanded_retrieval_pool_validity_branch_v1.json}
BRANCH_ROWS=${BRANCH_ROWS:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_confirmation_v1/backend_pool_validity_branch_rows.jsonl}
DEEPER_GENERATION_ROWS=${DEEPER_GENERATION_ROWS:-${RUNS_ROOT}/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_rows.jsonl}
DEEPER_GENERATION_EVALUATED_ROWS=${DEEPER_GENERATION_EVALUATED_ROWS:-${RUNS_ROOT}/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_evaluated_rows.jsonl}
EPISODE_MANIFEST=${EPISODE_MANIFEST:-${HYP}/manifests/h001_v3_fresh_validation_v1.json}
EPISODE_MANIFEST_SPLIT=${EPISODE_MANIFEST_SPLIT:-v3_fresh_validation_v1}
SCENE_SPEC_SOURCE=${SCENE_SPEC_SOURCE:-${HYP}/manifests/v3_fresh_validation_v1_scenes.txt}

OUT_ROOT=${OUT_ROOT:-${RUNS_ROOT}/h001_expanded_retrieval_pool_validity_branch_v1}
SCENE_SPECS_FILE=${SCENE_SPECS_FILE:-${OUT_ROOT}/pool_validity_scene_specs.txt}
ARTIFACT_OUT=${ARTIFACT_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_pool_validity_artifact_spatial_nms_p80_k200_d3_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${ARTIFACT_OUT}/all_scenes_aligned.jsonl}
LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/expanded-retrieval-pool-validity-branch-${TS}.log}
PIPELINE_STATUS=${PIPELINE_STATUS:-${OUT_ROOT}/job_status.json}

HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
ARTIFACT_ID=${ARTIFACT_ID:-expanded_retrieval_pool_validity_spatial_nms_p80_k200_d3_v1}
TRAJECTORY_SUFFIX=${TRAJECTORY_SUFFIX:-expanded_retrieval_pool_validity_spatial_nms_p80_k200_d3_v1}
FRAMES=${FRAMES:-256}
WIDTH=${WIDTH:-320}
HEIGHT=${HEIGHT:-240}
DEPTH_SAMPLE_RATE=${DEPTH_SAMPLE_RATE:-8}
TOP_PERCENTILE=${TOP_PERCENTILE:-80.0}
MAX_CANDIDATES=${MAX_CANDIDATES:-200}
CANDIDATE_SELECTION_MODE=${CANDIDATE_SELECTION_MODE:-spatial_nms}
SPATIAL_NMS_MIN_DISTANCE_CELLS=${SPATIAL_NMS_MIN_DISTANCE_CELLS:-3.0}
MIN_COMPONENT_CELLS=${MIN_COMPONENT_CELLS:-1}
EXPECTED_SCENE_COUNT=${EXPECTED_SCENE_COUNT:-1}
EXPECTED_QUERY_ROWS=${EXPECTED_QUERY_ROWS:-6}

mkdir -p "$(dirname "${LOG}")" "${OUT_ROOT}" "${ARTIFACT_OUT}"
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
    "schema_version": "h001.expanded_retrieval_pool_validity_branch_job.v1",
    "status": sys.argv[2],
    "stage": sys.argv[3],
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "working_directory": "${ROOT}",
    "command": "TS=${TS} bash ${HYP}/scripts/h001_jobs/expanded_retrieval_pool_validity_branch.sh",
    "contract": "${CONTRACT}",
    "branch_rows": "${BRANCH_ROWS}",
    "deeper_generation_rows": "${DEEPER_GENERATION_ROWS}",
    "deeper_generation_evaluated_rows": "${DEEPER_GENERATION_EVALUATED_ROWS}",
    "episode_manifest": "${EPISODE_MANIFEST}",
    "episode_manifest_split": "${EPISODE_MANIFEST_SPLIT}",
    "scene_spec_source": "${SCENE_SPEC_SOURCE}",
    "scene_specs_file": "${SCENE_SPECS_FILE}",
    "output_root": "${OUT_ROOT}",
    "artifact_out": "${ARTIFACT_OUT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "log": "${LOG}",
    "expected_files": [
        "${SCENE_SPECS_FILE}",
        "${ARTIFACT_OUT}/coverage_check.json",
        "${CANDIDATE_ARTIFACT}",
        "${OUT_ROOT}/pool_validity_branch_rows.jsonl",
        "${OUT_ROOT}/pool_validity_fallback_generation_rows.jsonl",
        "${OUT_ROOT}/pool_validity_fallback_evaluated_rows.jsonl",
        "${OUT_ROOT}/pool_validity_summary.json",
        "${OUT_ROOT}/pool_validity_scene_query_artifacts.jsonl"
    ],
    "verification_command": "cat ${PIPELINE_STATUS} && cat ${ARTIFACT_OUT}/coverage_check.json && cat ${OUT_ROOT}/pool_validity_summary.json",
    "artifact_id": "${ARTIFACT_ID}",
    "frames": int("${FRAMES}"),
    "width": int("${WIDTH}"),
    "height": int("${HEIGHT}"),
    "depth_sample_rate": int("${DEPTH_SAMPLE_RATE}"),
    "top_percentile": float("${TOP_PERCENTILE}"),
    "max_candidates": int("${MAX_CANDIDATES}"),
    "candidate_selection_mode": "${CANDIDATE_SELECTION_MODE}",
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

cat > "${OUT_ROOT}/run_contract.txt" <<EOF
job: expanded_retrieval_pool_validity_branch
working_directory: ${ROOT}
command: TS=${TS} bash ${HYP}/scripts/h001_jobs/expanded_retrieval_pool_validity_branch.sh
contract: ${CONTRACT}
branch_rows: ${BRANCH_ROWS}
deeper_generation_rows: ${DEEPER_GENERATION_ROWS}
deeper_generation_evaluated_rows: ${DEEPER_GENERATION_EVALUATED_ROWS}
episode_manifest: ${EPISODE_MANIFEST}
episode_manifest_split: ${EPISODE_MANIFEST_SPLIT}
scene_spec_source: ${SCENE_SPEC_SOURCE}
scene_specs_file: ${SCENE_SPECS_FILE}
artifact_out: ${ARTIFACT_OUT}
candidate_artifact: ${CANDIDATE_ARTIFACT}
output_root: ${OUT_ROOT}
expected_files:
  - ${SCENE_SPECS_FILE}
  - ${ARTIFACT_OUT}/coverage_check.json
  - ${CANDIDATE_ARTIFACT}
  - ${OUT_ROOT}/pool_validity_branch_rows.jsonl
  - ${OUT_ROOT}/pool_validity_fallback_generation_rows.jsonl
  - ${OUT_ROOT}/pool_validity_fallback_evaluated_rows.jsonl
  - ${OUT_ROOT}/pool_validity_summary.json
  - ${OUT_ROOT}/pool_validity_scene_query_artifacts.jsonl
verification_command:
  cat ${PIPELINE_STATUS}
  cat ${ARTIFACT_OUT}/coverage_check.json
  cat ${OUT_ROOT}/pool_validity_summary.json
EOF

echo "started_at=$(date -Is)"
echo "working_directory=${ROOT}"
echo "log=${LOG}"
echo "output_root=${OUT_ROOT}"
echo "artifact_out=${ARTIFACT_OUT}"
echo "verification_command=cat ${PIPELINE_STATUS} && cat ${OUT_ROOT}/pool_validity_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path

paths = {
    "contract": Path("${CONTRACT}"),
    "branch_rows": Path("${BRANCH_ROWS}"),
    "deeper_generation_rows": Path("${DEEPER_GENERATION_ROWS}"),
    "deeper_generation_evaluated_rows": Path("${DEEPER_GENERATION_EVALUATED_ROWS}"),
    "episode_manifest": Path("${EPISODE_MANIFEST}"),
    "scene_spec_source": Path("${SCENE_SPEC_SOURCE}"),
    "calibration_artifact_job": Path("${HYP}/runtime/calibration_artifact_job.sh"),
    "analyzer": Path("${HYP}/src/h001_runtime/analyze_expanded_retrieval_pool_validity_branch.py"),
    "data_root": Path("${DATA_ROOT}"),
    "model_root": Path("${MODEL_ROOT}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
print({"stage": "prerequisite_check_passed", "paths": {name: str(path) for name, path in paths.items()}})
PY

CURRENT_STAGE=target_spec_generation
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${DATA_ROOT}:/data:ro" \
  -w /workspace \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_pool_validity_branch \
    --contract "/workspace/configs/h001/manifests/$(basename "${CONTRACT}")" \
    --branch-rows "/runs/$(basename "$(dirname "${BRANCH_ROWS}")")/$(basename "${BRANCH_ROWS}")" \
    --deeper-generation-rows "/runs/$(basename "$(dirname "${DEEPER_GENERATION_ROWS}")")/$(basename "${DEEPER_GENERATION_ROWS}")" \
    --deeper-generation-evaluated-rows "/runs/$(basename "$(dirname "${DEEPER_GENERATION_EVALUATED_ROWS}")")/$(basename "${DEEPER_GENERATION_EVALUATED_ROWS}")" \
    --episode-manifest "/workspace/configs/h001/manifests/$(basename "${EPISODE_MANIFEST}")" \
    --episode-manifest-split "${EPISODE_MANIFEST_SPLIT}" \
    --data-root /data \
    --scene-spec-source "/workspace/configs/h001/manifests/$(basename "${SCENE_SPEC_SOURCE}")" \
    --scene-spec-output "/runs/$(basename "${OUT_ROOT}")/$(basename "${SCENE_SPECS_FILE}")" \
    --out-root "/runs/$(basename "${OUT_ROOT}")"

CURRENT_STAGE=candidate_artifact_generation
write_status running "${CURRENT_STAGE}"
OUT_ROOT="${ARTIFACT_OUT}" \
DATA_ROOT="${DATA_ROOT}" \
MODEL_ROOT="${MODEL_ROOT}" \
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
MIN_COMPONENT_CELLS="${MIN_COMPONENT_CELLS}" \
EXPECTED_SCENE_COUNT="${EXPECTED_SCENE_COUNT}" \
EXPECTED_QUERY_ROWS="${EXPECTED_QUERY_ROWS}" \
"${HYP}/runtime/calibration_artifact_job.sh"

CURRENT_STAGE=final_analysis
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${DATA_ROOT}:/data:ro" \
  -w /workspace \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_pool_validity_branch \
    --contract "/workspace/configs/h001/manifests/$(basename "${CONTRACT}")" \
    --branch-rows "/runs/$(basename "$(dirname "${BRANCH_ROWS}")")/$(basename "${BRANCH_ROWS}")" \
    --deeper-generation-rows "/runs/$(basename "$(dirname "${DEEPER_GENERATION_ROWS}")")/$(basename "${DEEPER_GENERATION_ROWS}")" \
    --deeper-generation-evaluated-rows "/runs/$(basename "$(dirname "${DEEPER_GENERATION_EVALUATED_ROWS}")")/$(basename "${DEEPER_GENERATION_EVALUATED_ROWS}")" \
    --candidate-artifact "/runs/$(basename "${ARTIFACT_OUT}")/$(basename "${CANDIDATE_ARTIFACT}")" \
    --episode-manifest "/workspace/configs/h001/manifests/$(basename "${EPISODE_MANIFEST}")" \
    --episode-manifest-split "${EPISODE_MANIFEST_SPLIT}" \
    --data-root /data \
    --scene-spec-source "/workspace/configs/h001/manifests/$(basename "${SCENE_SPEC_SOURCE}")" \
    --scene-spec-output "/runs/$(basename "${OUT_ROOT}")/$(basename "${SCENE_SPECS_FILE}")" \
    --out-root "/runs/$(basename "${OUT_ROOT}")"

python - "${OUT_ROOT}/pool_validity_summary.json" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps({
    "pool_validity_fallback_gate_passed": summary.get("gate", {}).get("pool_validity_fallback_gate_passed"),
    "goal_validity_confirmation_unblocked": summary.get("gate", {}).get("goal_validity_confirmation_unblocked"),
    "second_fallback_backend_required": summary.get("gate", {}).get("second_fallback_backend_required"),
    "fallback_generated_candidate_rows": summary.get("fallback_generated_candidate_rows"),
    "evaluation_only_contains_valid_rows": summary.get("evaluation_only_contains_valid_rows"),
    "evaluation_only_no_valid_rows": summary.get("evaluation_only_no_valid_rows"),
    "fallback_generation_status_counts": summary.get("fallback_generation_status_counts"),
}, indent=2, sort_keys=True))
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
