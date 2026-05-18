#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
MANIFEST=${MANIFEST:-${HYP}/manifests/h001_splits_sr1.json}
MANIFEST_SPLIT=${MANIFEST_SPLIT:-first_eval}
EPISODES=${EPISODES:-100}
ARTIFACT_NAME=${ARTIFACT_NAME:-h001_first_eval_artifacts_spatial_nms_p97_k20_v1}
POLICY_NAME=${POLICY_NAME:-h001_first_eval_policy_spatial_nms_p97_k20_v1}
RUN_ID=${RUN_ID:-h001_first_eval_spatial_nms_p97_k20_coverage_sanity_20260515}
HOST_UID=${HOST_UID:-$(id -u)}
HOST_GID=${HOST_GID:-$(id -g)}

OUT_ROOT=${OUT_ROOT:-${RUNS_ROOT}/${POLICY_NAME}/coverage_sanity}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/${ARTIFACT_NAME}/all_scenes_aligned.jsonl}

if [[ ! -s "${CANDIDATE_ARTIFACT}" ]]; then
  echo "missing candidate artifact: ${CANDIDATE_ARTIFACT}" >&2
  exit 1
fi
if [[ ! -s "${MANIFEST}" ]]; then
  echo "missing manifest: ${MANIFEST}" >&2
  exit 1
fi

mkdir -p "${OUT_ROOT}"
cat > "${OUT_ROOT}/run_contract.txt" <<EOF
working_directory: ${ROOT}
output_root: ${OUT_ROOT}
candidate_artifact: ${CANDIDATE_ARTIFACT}
manifest: ${MANIFEST}
manifest_split: ${MANIFEST_SPLIT}
episodes: ${EPISODES}
policies:
  - GTTargetOracle
  - NoReobserve
expected_files:
  - ${OUT_ROOT}/summary.json
  - ${OUT_ROOT}/artifact_coverage.json
verification_command:
  cat ${OUT_ROOT}/artifact_coverage.json
EOF

sg docker -c "docker run --rm --ipc=host \
  --user ${HOST_UID}:${HOST_GID} \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v ${DATA_ROOT}:/data:ro \
  -v ${RUNS_ROOT}:/runs \
  -v ${ROOT}:/workspace:ro \
  ${HABITAT_IMG} \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/$(basename "${MANIFEST}") \
    --manifest-split ${MANIFEST_SPLIT} \
    --episodes ${EPISODES} \
    --candidate-backend artifact_jsonl \
    --policies GTTargetOracle NoReobserve \
    --out /runs/${POLICY_NAME}/coverage_sanity \
    --run-id ${RUN_ID} \
    --candidate-artifact /runs/$(basename "$(dirname "${CANDIDATE_ARTIFACT}")")/$(basename "${CANDIDATE_ARTIFACT}")"

sg docker -c "docker run --rm --ipc=host \
  --user ${HOST_UID}:${HOST_GID} \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v ${DATA_ROOT}:/data:ro \
  -v ${RUNS_ROOT}:/runs \
  -v ${ROOT}:/workspace:ro \
  ${HABITAT_IMG} \
  micromamba run -n base python -m h001_runtime.analyze_artifact_coverage \
    --data-root /data \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/$(basename "${MANIFEST}") \
    --manifest-split ${MANIFEST_SPLIT} \
    --episodes ${EPISODES} \
    --candidate-artifact /runs/$(basename "$(dirname "${CANDIDATE_ARTIFACT}")")/$(basename "${CANDIDATE_ARTIFACT}") \
    --summary /runs/${POLICY_NAME}/coverage_sanity/summary.json \
    --out /runs/${POLICY_NAME}/coverage_sanity/artifact_coverage.json"
