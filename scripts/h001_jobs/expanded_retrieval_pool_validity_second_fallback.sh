#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
DATA_ROOT=${DATA_ROOT:-${ROOT}/local_dataset/data}
MODEL_ROOT=${MODEL_ROOT:-${ROOT}/local_dataset/models}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

CONTRACT=${CONTRACT:-${HYP}/manifests/h001_expanded_retrieval_pool_validity_second_fallback_v1.json}
BRANCH_ROWS=${BRANCH_ROWS:-${RUNS_ROOT}/h001_expanded_retrieval_goal_validity_confirmation_v1/backend_pool_validity_branch_rows.jsonl}
PREVIOUS_GENERATION_ROWS=${PREVIOUS_GENERATION_ROWS:-${RUNS_ROOT}/h001_expanded_retrieval_pool_validity_branch_v1/pool_validity_fallback_generation_rows.jsonl}
PREVIOUS_EVALUATED_ROWS=${PREVIOUS_EVALUATED_ROWS:-${RUNS_ROOT}/h001_expanded_retrieval_pool_validity_branch_v1/pool_validity_fallback_evaluated_rows.jsonl}
DEEPER_GENERATION_ROWS=${DEEPER_GENERATION_ROWS:-${RUNS_ROOT}/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_rows.jsonl}
EPISODE_MANIFEST=${EPISODE_MANIFEST:-${HYP}/manifests/h001_v3_fresh_validation_v1.json}
EPISODE_MANIFEST_SPLIT=${EPISODE_MANIFEST_SPLIT:-v3_fresh_validation_v1}
SCENE_SPEC_SOURCE=${SCENE_SPEC_SOURCE:-${HYP}/manifests/v3_fresh_validation_v1_scenes.txt}

OUT_ROOT=${OUT_ROOT:-${RUNS_ROOT}/h001_expanded_retrieval_pool_validity_second_fallback_v1}
SCENE_SPECS_FILE=${SCENE_SPECS_FILE:-${OUT_ROOT}/second_fallback_scene_specs.txt}
ARTIFACT_OUT=${ARTIFACT_OUT:-${RUNS_ROOT}/h001_expanded_retrieval_pool_validity_artifact_components_p80_min1_k200_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${ARTIFACT_OUT}/all_scenes_aligned.jsonl}
REUSE_ARTIFACT_ROOT=${REUSE_ARTIFACT_ROOT:-${RUNS_ROOT}/h001_expanded_retrieval_pool_validity_artifact_spatial_nms_p80_k200_d3_v1}
LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/expanded-retrieval-pool-validity-second-fallback-${TS}.log}
PIPELINE_STATUS=${PIPELINE_STATUS:-${OUT_ROOT}/job_status.json}

HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
ARTIFACT_ID=${ARTIFACT_ID:-expanded_retrieval_pool_validity_components_p80_min1_k200_v1}
TRAJECTORY_SUFFIX=${TRAJECTORY_SUFFIX:-expanded_retrieval_pool_validity_components_p80_min1_k200_v1}
FRAMES=${FRAMES:-256}
WIDTH=${WIDTH:-320}
HEIGHT=${HEIGHT:-240}
DEPTH_SAMPLE_RATE=${DEPTH_SAMPLE_RATE:-8}
TOP_PERCENTILE=${TOP_PERCENTILE:-80.0}
MAX_CANDIDATES=${MAX_CANDIDATES:-200}
CANDIDATE_SELECTION_MODE=${CANDIDATE_SELECTION_MODE:-components}
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
    "schema_version": "h001.expanded_retrieval_pool_validity_second_fallback_job.v1",
    "status": sys.argv[2],
    "stage": sys.argv[3],
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "working_directory": "${ROOT}",
    "command": "TS=${TS} bash ${HYP}/scripts/h001_jobs/expanded_retrieval_pool_validity_second_fallback.sh",
    "contract": "${CONTRACT}",
    "branch_rows": "${BRANCH_ROWS}",
    "previous_generation_rows": "${PREVIOUS_GENERATION_ROWS}",
    "previous_evaluated_rows": "${PREVIOUS_EVALUATED_ROWS}",
    "deeper_generation_rows": "${DEEPER_GENERATION_ROWS}",
    "episode_manifest": "${EPISODE_MANIFEST}",
    "episode_manifest_split": "${EPISODE_MANIFEST_SPLIT}",
    "scene_spec_source": "${SCENE_SPEC_SOURCE}",
    "scene_specs_file": "${SCENE_SPECS_FILE}",
    "output_root": "${OUT_ROOT}",
    "artifact_out": "${ARTIFACT_OUT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "reuse_artifact_root": "${REUSE_ARTIFACT_ROOT}",
    "log": "${LOG}",
    "expected_files": [
        "${SCENE_SPECS_FILE}",
        "${ARTIFACT_OUT}/coverage_check.json",
        "${CANDIDATE_ARTIFACT}",
        "${OUT_ROOT}/second_fallback_branch_rows.jsonl",
        "${OUT_ROOT}/second_fallback_generation_rows.jsonl",
        "${OUT_ROOT}/second_fallback_evaluated_rows.jsonl",
        "${OUT_ROOT}/second_fallback_summary.json",
        "${OUT_ROOT}/second_fallback_scene_query_artifacts.jsonl"
    ],
    "verification_command": "cat ${PIPELINE_STATUS} && cat ${ARTIFACT_OUT}/coverage_check.json && cat ${OUT_ROOT}/second_fallback_summary.json",
    "artifact_id": "${ARTIFACT_ID}",
    "frames": int("${FRAMES}"),
    "width": int("${WIDTH}"),
    "height": int("${HEIGHT}"),
    "depth_sample_rate": int("${DEPTH_SAMPLE_RATE}"),
    "top_percentile": float("${TOP_PERCENTILE}"),
    "max_candidates": int("${MAX_CANDIDATES}"),
    "candidate_selection_mode": "${CANDIDATE_SELECTION_MODE}",
    "spatial_nms_min_distance_cells": float("${SPATIAL_NMS_MIN_DISTANCE_CELLS}"),
    "min_component_cells": int("${MIN_COMPONENT_CELLS}"),
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
job: expanded_retrieval_pool_validity_second_fallback
working_directory: ${ROOT}
command: TS=${TS} bash ${HYP}/scripts/h001_jobs/expanded_retrieval_pool_validity_second_fallback.sh
contract: ${CONTRACT}
branch_rows: ${BRANCH_ROWS}
previous_generation_rows: ${PREVIOUS_GENERATION_ROWS}
previous_evaluated_rows: ${PREVIOUS_EVALUATED_ROWS}
deeper_generation_rows: ${DEEPER_GENERATION_ROWS}
episode_manifest: ${EPISODE_MANIFEST}
episode_manifest_split: ${EPISODE_MANIFEST_SPLIT}
scene_spec_source: ${SCENE_SPEC_SOURCE}
scene_specs_file: ${SCENE_SPECS_FILE}
artifact_out: ${ARTIFACT_OUT}
candidate_artifact: ${CANDIDATE_ARTIFACT}
reuse_artifact_root: ${REUSE_ARTIFACT_ROOT}
output_root: ${OUT_ROOT}
expected_files:
  - ${SCENE_SPECS_FILE}
  - ${ARTIFACT_OUT}/coverage_check.json
  - ${CANDIDATE_ARTIFACT}
  - ${OUT_ROOT}/second_fallback_branch_rows.jsonl
  - ${OUT_ROOT}/second_fallback_generation_rows.jsonl
  - ${OUT_ROOT}/second_fallback_evaluated_rows.jsonl
  - ${OUT_ROOT}/second_fallback_summary.json
  - ${OUT_ROOT}/second_fallback_scene_query_artifacts.jsonl
verification_command:
  cat ${PIPELINE_STATUS}
  cat ${ARTIFACT_OUT}/coverage_check.json
  cat ${OUT_ROOT}/second_fallback_summary.json
EOF

echo "started_at=$(date -Is)"
echo "working_directory=${ROOT}"
echo "log=${LOG}"
echo "output_root=${OUT_ROOT}"
echo "artifact_out=${ARTIFACT_OUT}"
echo "verification_command=cat ${PIPELINE_STATUS} && cat ${OUT_ROOT}/second_fallback_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path

paths = {
    "contract": Path("${CONTRACT}"),
    "branch_rows": Path("${BRANCH_ROWS}"),
    "previous_generation_rows": Path("${PREVIOUS_GENERATION_ROWS}"),
    "previous_evaluated_rows": Path("${PREVIOUS_EVALUATED_ROWS}"),
    "deeper_generation_rows": Path("${DEEPER_GENERATION_ROWS}"),
    "episode_manifest": Path("${EPISODE_MANIFEST}"),
    "scene_spec_source": Path("${SCENE_SPEC_SOURCE}"),
    "calibration_artifact_job": Path("${HYP}/runtime/calibration_artifact_job.sh"),
    "analyzer": Path("${HYP}/src/h001_runtime/analyze_expanded_retrieval_pool_validity_second_fallback.py"),
    "data_root": Path("${DATA_ROOT}"),
    "model_root": Path("${MODEL_ROOT}"),
    "reuse_artifact_root": Path("${REUSE_ARTIFACT_ROOT}"),
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
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_pool_validity_second_fallback \
    --contract "/workspace/configs/h001/manifests/$(basename "${CONTRACT}")" \
    --branch-rows "/runs/$(basename "$(dirname "${BRANCH_ROWS}")")/$(basename "${BRANCH_ROWS}")" \
    --previous-generation-rows "/runs/$(basename "$(dirname "${PREVIOUS_GENERATION_ROWS}")")/$(basename "${PREVIOUS_GENERATION_ROWS}")" \
    --previous-evaluated-rows "/runs/$(basename "$(dirname "${PREVIOUS_EVALUATED_ROWS}")")/$(basename "${PREVIOUS_EVALUATED_ROWS}")" \
    --deeper-generation-rows "/runs/$(basename "$(dirname "${DEEPER_GENERATION_ROWS}")")/$(basename "${DEEPER_GENERATION_ROWS}")" \
    --episode-manifest "/workspace/configs/h001/manifests/$(basename "${EPISODE_MANIFEST}")" \
    --episode-manifest-split "${EPISODE_MANIFEST_SPLIT}" \
    --data-root /data \
    --scene-spec-source "/workspace/configs/h001/manifests/$(basename "${SCENE_SPEC_SOURCE}")" \
    --scene-spec-output "/runs/$(basename "${OUT_ROOT}")/$(basename "${SCENE_SPECS_FILE}")" \
    --out-root "/runs/$(basename "${OUT_ROOT}")"

CURRENT_STAGE=reuse_first_fallback_exports
write_status running "${CURRENT_STAGE}"
if [[ -d "${REUSE_ARTIFACT_ROOT}/embeddings" && ! -s "${ARTIFACT_OUT}/embeddings/manifest.json" ]]; then
  mkdir -p "${ARTIFACT_OUT}"
  cp -a "${REUSE_ARTIFACT_ROOT}/embeddings" "${ARTIFACT_OUT}/"
fi
if [[ -d "${REUSE_ARTIFACT_ROOT}/scenes" ]]; then
  for scene_dir in "${REUSE_ARTIFACT_ROOT}"/scenes/*; do
    [[ -d "${scene_dir}" ]] || continue
    scene_name="$(basename "${scene_dir}")"
    mkdir -p "${ARTIFACT_OUT}/scenes/${scene_name}"
    if [[ -d "${scene_dir}/export" && ! -d "${ARTIFACT_OUT}/scenes/${scene_name}/export" ]]; then
      cp -a "${scene_dir}/export" "${ARTIFACT_OUT}/scenes/${scene_name}/export"
    fi
    if [[ -s "${scene_dir}/verify_map.json" && ! -s "${ARTIFACT_OUT}/scenes/${scene_name}/verify_map.json" ]]; then
      cp -a "${scene_dir}/verify_map.json" "${ARTIFACT_OUT}/scenes/${scene_name}/verify_map.json"
    fi
  done
fi

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
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_pool_validity_second_fallback \
    --contract "/workspace/configs/h001/manifests/$(basename "${CONTRACT}")" \
    --branch-rows "/runs/$(basename "$(dirname "${BRANCH_ROWS}")")/$(basename "${BRANCH_ROWS}")" \
    --previous-generation-rows "/runs/$(basename "$(dirname "${PREVIOUS_GENERATION_ROWS}")")/$(basename "${PREVIOUS_GENERATION_ROWS}")" \
    --previous-evaluated-rows "/runs/$(basename "$(dirname "${PREVIOUS_EVALUATED_ROWS}")")/$(basename "${PREVIOUS_EVALUATED_ROWS}")" \
    --deeper-generation-rows "/runs/$(basename "$(dirname "${DEEPER_GENERATION_ROWS}")")/$(basename "${DEEPER_GENERATION_ROWS}")" \
    --candidate-artifact "/runs/$(basename "${ARTIFACT_OUT}")/$(basename "${CANDIDATE_ARTIFACT}")" \
    --episode-manifest "/workspace/configs/h001/manifests/$(basename "${EPISODE_MANIFEST}")" \
    --episode-manifest-split "${EPISODE_MANIFEST_SPLIT}" \
    --data-root /data \
    --scene-spec-source "/workspace/configs/h001/manifests/$(basename "${SCENE_SPEC_SOURCE}")" \
    --scene-spec-output "/runs/$(basename "${OUT_ROOT}")/$(basename "${SCENE_SPECS_FILE}")" \
    --out-root "/runs/$(basename "${OUT_ROOT}")"

python - "${OUT_ROOT}/second_fallback_summary.json" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps({
    "second_fallback_gate_passed": summary.get("gate", {}).get("second_fallback_gate_passed"),
    "goal_validity_confirmation_unblocked": summary.get("gate", {}).get("goal_validity_confirmation_unblocked"),
    "backend_source_map_blind_spot_after_second_fallback": summary.get("gate", {}).get("backend_source_map_blind_spot_after_second_fallback"),
    "component_generated_candidate_rows": summary.get("component_generated_candidate_rows"),
    "evaluation_only_contains_valid_rows": summary.get("evaluation_only_contains_valid_rows"),
    "evaluation_only_no_valid_rows": summary.get("evaluation_only_no_valid_rows"),
    "second_fallback_status_counts": summary.get("second_fallback_status_counts"),
}, indent=2, sort_keys=True))
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
