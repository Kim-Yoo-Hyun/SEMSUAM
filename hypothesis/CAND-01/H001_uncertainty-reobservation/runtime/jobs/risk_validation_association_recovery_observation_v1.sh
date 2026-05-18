#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
MODEL_ROOT=${MODEL_ROOT:-/tmp/research3-models}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
OPENVOCAB_IMG=${OPENVOCAB_IMG:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

RISK_RUN=${RISK_RUN:-${RUNS_ROOT}/h001_risk_validation_risk_resolution_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
OBJECT_NODE_FEATURES=${OBJECT_NODE_FEATURES:-${RUNS_ROOT}/h001_risk_validation_object_node_evidence_objective_v1/candidate_object_node_features.jsonl}
OUT=${OUT:-${RUNS_ROOT}/h001_risk_validation_association_recovery_observation_v1}
RUN_ID=${RUN_ID:-h001_risk_validation_association_recovery_observation_v1_${TS}}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
MAX_ROWS=${MAX_ROWS:-20}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
LOG=${LOG:-${ROOT}/logs/risk-validation-association-recovery-observation-v1-${TS}.log}
STATUS=${STATUS:-${OUT}/job_status.json}

mkdir -p "${ROOT}/logs" "${OUT}"
exec > >(tee -a "${LOG}") 2>&1

to_runs_path() {
  local path="$1"
  if [[ "$path" == /tmp/research3-runs/* ]]; then
    echo "/runs/${path#/tmp/research3-runs/}"
  else
    echo "$path"
  fi
}

write_status() {
  local job_state="$1"
  local stage="$2"
  python - "$STATUS" "$job_state" "$stage" <<PY
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "status": sys.argv[2],
    "stage": sys.argv[3],
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "risk_run": "${RISK_RUN}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "out": "${OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "max_rows": int("${MAX_ROWS}"),
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
echo "risk_run=${RISK_RUN}"
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "object_node_features=${OBJECT_NODE_FEATURES}"
echo "out=${OUT}"
echo "log=${LOG}"
echo "expected_files=${OUT}/second_observation_plan.jsonl ${OUT}/second_observation_frames.jsonl ${OUT}/detector_candidate_associations.jsonl ${OUT}/candidate_object_node_features_after_second.jsonl ${OUT}/risk_resolution_after_second_summary.json ${OUT}/association_recovery_arbitration_summary.json"
echo "verification_command=cat ${STATUS} && cat ${OUT}/risk_resolution_after_second_summary.json && cat ${OUT}/association_recovery_arbitration_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path
paths = {
    "risk_viewpoints": Path("${RISK_RUN}") / "viewpoint_decisions.jsonl",
    "risk_candidates": Path("${RISK_RUN}") / "candidate_decisions.jsonl",
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "object_node_features": Path("${OBJECT_NODE_FEATURES}"),
    "groundingdino_config": Path("${GROUNDINGDINO_DIR}") / "config.json",
    "groundingdino_weights": Path("${GROUNDINGDINO_DIR}") / "model.safetensors",
    "sam2_checkpoint": Path("${SAM2_CHECKPOINT}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
print({"stage": "prerequisite_check_passed", "paths": {name: str(path) for name, path in paths.items()}})
PY

CURRENT_STAGE=plan_second_observation
write_status running "${CURRENT_STAGE}"
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v ${DATA_ROOT}:/data:ro \
  -v ${RUNS_ROOT}:/runs \
  -v ${ROOT}:/workspace:ro \
  ${HABITAT_IMG} \
  micromamba run -n base python -m h001_runtime.plan_association_recovery_observation \
    --viewpoint-decisions $(to_runs_path "${RISK_RUN}")/viewpoint_decisions.jsonl \
    --candidate-artifact $(to_runs_path "${CANDIDATE_ARTIFACT}") \
    --object-node-features $(to_runs_path "${OBJECT_NODE_FEATURES}") \
    --out-root $(to_runs_path "${OUT}") \
    --data-root /data \
    --run-id ${RUN_ID} \
    --max-rows ${MAX_ROWS} \
    --standoff-distances 1.25,1.75,2.25 \
    --preferred-standoff-distance-m 1.75 \
    --min-standoff-distance-m 0.75 \
    --max-standoff-distance-m 3.25"

CURRENT_STAGE=frame_export
write_status running "${CURRENT_STAGE}"
sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v ${DATA_ROOT}:/data:ro \
  -v ${RUNS_ROOT}:/runs \
  -v ${ROOT}:/workspace:ro \
  ${HABITAT_IMG} \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions $(to_runs_path "${OUT}")/second_observation_plan.jsonl \
    --candidate-artifact $(to_runs_path "${CANDIDATE_ARTIFACT}") \
    --out-root $(to_runs_path "${OUT}") \
    --policy AssociationRecoveryObservation \
    --max-decisions 0 \
    --max-candidates-per-decision 5 \
    --yaw-offsets=-30,0,30 \
    --candidate-point-field position"
cp "${OUT}/postview_frames_v2.jsonl" "${OUT}/second_observation_frames.jsonl"

FRAME_ROWS="$(python - <<PY
from pathlib import Path
rows = [line for line in (Path("${OUT}") / "second_observation_frames.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)"

if [[ "${DEVICE}" == "cuda" ]]; then
  GPU_FLAG="--gpus all"
else
  GPU_FLAG=""
fi

CURRENT_STAGE=detector_mask_scoring
write_status running "${CURRENT_STAGE}"
sg docker -c "docker run --rm ${GPU_FLAG} \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v ${ROOT}:/workspace \
  -v ${RUNS_ROOT}:/runs \
  -v ${MODEL_ROOT}:/models \
  -w /workspace \
  ${OPENVOCAB_IMG} \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames $(to_runs_path "${OUT}")/second_observation_frames.jsonl \
    --candidate-artifact $(to_runs_path "${CANDIDATE_ARTIFACT}") \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root $(to_runs_path "${OUT}") \
    --debug-root $(to_runs_path "${OUT}")/debug_images \
    --device ${DEVICE} \
    --max-frames ${FRAME_ROWS} \
    --max-headings-per-frame ${MAX_HEADINGS_PER_FRAME} \
    --max-detector-boxes-per-heading ${MAX_DETECTOR_BOXES_PER_HEADING} \
    --max-masks-per-heading ${MAX_MASKS_PER_HEADING} \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 5 \
    --candidate-point-field position \
    --box-threshold ${BOX_THRESHOLD} \
    --text-threshold ${TEXT_THRESHOLD} \
    --query-template '${QUERY_TEMPLATE}' \
    --box-padding-px 4 \
    --association-depth-tolerance-m ${ASSOCIATION_DEPTH_TOLERANCE_M} \
    --max-debug-images 80"

CURRENT_STAGE=after_second_analysis
write_status running "${CURRENT_STAGE}"
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v ${RUNS_ROOT}:/runs \
  -v ${ROOT}:/workspace:ro \
  ${HABITAT_IMG} \
  micromamba run -n base python -m h001_runtime.analyze_association_recovery_observation \
    --second-observation-plan $(to_runs_path "${OUT}")/second_observation_plan.jsonl \
    --detector-root $(to_runs_path "${OUT}") \
    --candidate-decisions $(to_runs_path "${RISK_RUN}")/candidate_decisions.jsonl \
    --original-object-node-features $(to_runs_path "${OBJECT_NODE_FEATURES}") \
    --out-root $(to_runs_path "${OUT}") \
    --policy RiskResolutionReobserve"

CURRENT_STAGE=verified
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
