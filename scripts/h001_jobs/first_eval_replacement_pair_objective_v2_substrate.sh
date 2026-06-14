#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
MODEL_ROOT=${MODEL_ROOT:-/tmp/research3-models}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
OPENVOCAB_IMG=${OPENVOCAB_IMG:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

MANIFEST=${MANIFEST:-${HYP}/manifests/h001_first_eval_replacement_v1.json}
MANIFEST_SPLIT=${MANIFEST_SPLIT:-first_eval_replacement_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
OBJECT_NODE_FEATURES=${OBJECT_NODE_FEATURES:-${RUNS_ROOT}/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl}
OUT=${OUT:-${RUNS_ROOT}/h001_first_eval_replacement_pair_objective_v2_validation_v1}
RISK_OUT=${RISK_OUT:-${OUT}/risk_resolution}
ASSOC_OUT=${ASSOC_OUT:-${OUT}/association_recovery}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
EPISODES=${EPISODES:-100}
RUN_PREFIX=${RUN_PREFIX:-h001_first_eval_replacement}
MAX_ASSOC_ROWS=${MAX_ASSOC_ROWS:-40}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
PAIR_EVIDENCE_MARGIN=${PAIR_EVIDENCE_MARGIN:-0.05}
PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON=${PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON:-1}
LOG=${LOG:-${ROOT}/logs/first-eval-replacement-pair-objective-v2-substrate-${TS}.log}
STATUS=${STATUS:-${OUT}/job_status.json}

PAIR_COMMON_FALLBACK_ARGS=()
if [[ "${PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON}" == "1" || "${PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON}" == "true" ]]; then
  PAIR_COMMON_FALLBACK_ARGS+=(--include-dual-fallback-for-common)
fi

mkdir -p "${ROOT}/logs" "${OUT}" "${RISK_OUT}" "${ASSOC_OUT}"
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
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "out": "${OUT}",
    "risk_out": "${RISK_OUT}",
    "association_recovery_out": "${ASSOC_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "episodes": int("${EPISODES}"),
    "max_assoc_rows": int("${MAX_ASSOC_ROWS}"),
    "pair_include_dual_fallback_for_common": "${PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON}",
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
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "object_node_features=${OBJECT_NODE_FEATURES}"
echo "out=${OUT}"
echo "risk_out=${RISK_OUT}"
echo "association_recovery_out=${ASSOC_OUT}"
echo "log=${LOG}"
echo "pair_include_dual_fallback_for_common=${PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON}"
echo "expected_files=${OUT}/risk_resolution_summary.json ${OUT}/association_recovery_arbitration_summary.json ${OUT}/pair_observation_plan_summary.json ${OUT}/summary.json ${OUT}/pair_observation_evidence_summary.json ${OUT}/pair_observation_failure_mode_summary.json ${OUT}/heldout_pair_substrate_summary.json"
echo "verification_command=cat ${STATUS} && cat ${OUT}/heldout_pair_substrate_summary.json && cat ${OUT}/pair_observation_evidence_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path
paths = {
    "manifest": Path("${MANIFEST}"),
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

CURRENT_STAGE=risk_resolution_policy
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest "/workspace/configs/h001/manifests/$(basename "${MANIFEST}")" \
    --manifest-split "${MANIFEST_SPLIT}" \
    --episodes "${EPISODES}" \
    --candidate-backend artifact_jsonl \
    --policies RiskResolutionReobserve \
    --out "$(to_runs_path "${RISK_OUT}")" \
    --run-id "${RUN_PREFIX}_pair_objective_v2_risk_${TS}" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --risk-object-node-features "$(to_runs_path "${OBJECT_NODE_FEATURES}")"
cp "${RISK_OUT}/summary.json" "${OUT}/risk_resolution_summary.json"

CURRENT_STAGE=association_recovery_plan
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.plan_association_recovery_observation \
    --viewpoint-decisions "$(to_runs_path "${RISK_OUT}")/viewpoint_decisions.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --object-node-features "$(to_runs_path "${OBJECT_NODE_FEATURES}")" \
    --out-root "$(to_runs_path "${ASSOC_OUT}")" \
    --data-root /data \
    --run-id "${RUN_PREFIX}_association_recovery_${TS}" \
    --max-rows "${MAX_ASSOC_ROWS}" \
    --standoff-distances 1.25,1.75,2.25 \
    --preferred-standoff-distance-m 1.75 \
    --min-standoff-distance-m 0.75 \
    --max-standoff-distance-m 3.25

CURRENT_STAGE=association_recovery_frame_export
write_status running "${CURRENT_STAGE}"
docker run --rm --gpus all --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions "$(to_runs_path "${ASSOC_OUT}")/second_observation_plan.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${ASSOC_OUT}")" \
    --policy AssociationRecoveryObservation \
    --max-decisions 0 \
    --max-candidates-per-decision 5 \
    --yaw-offsets=-30,0,30 \
    --candidate-point-field position
cp "${ASSOC_OUT}/postview_frames_v2.jsonl" "${ASSOC_OUT}/second_observation_frames.jsonl"

ASSOC_FRAME_ROWS="$(python - <<PY
from pathlib import Path
rows = [line for line in (Path("${ASSOC_OUT}") / "second_observation_frames.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)"

if [[ "${DEVICE}" == "cuda" ]]; then
  GPU_FLAG="--gpus all"
else
  GPU_FLAG=""
fi

CURRENT_STAGE=association_recovery_detector
write_status running "${CURRENT_STAGE}"
docker run --rm ${GPU_FLAG} \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${MODEL_ROOT}:/models:ro" \
  -w /workspace \
  "${OPENVOCAB_IMG}" \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames "$(to_runs_path "${ASSOC_OUT}")/second_observation_frames.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root "$(to_runs_path "${ASSOC_OUT}")" \
    --debug-root "$(to_runs_path "${ASSOC_OUT}")/debug_images" \
    --device "${DEVICE}" \
    --max-frames "${ASSOC_FRAME_ROWS}" \
    --max-headings-per-frame "${MAX_HEADINGS_PER_FRAME}" \
    --max-detector-boxes-per-heading "${MAX_DETECTOR_BOXES_PER_HEADING}" \
    --max-masks-per-heading "${MAX_MASKS_PER_HEADING}" \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 5 \
    --candidate-point-field position \
    --box-threshold "${BOX_THRESHOLD}" \
    --text-threshold "${TEXT_THRESHOLD}" \
    --query-template "${QUERY_TEMPLATE}" \
    --box-padding-px 4 \
    --association-depth-tolerance-m "${ASSOCIATION_DEPTH_TOLERANCE_M}" \
    --max-debug-images 120

CURRENT_STAGE=association_recovery_analysis
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_association_recovery_observation \
    --second-observation-plan "$(to_runs_path "${ASSOC_OUT}")/second_observation_plan.jsonl" \
    --detector-root "$(to_runs_path "${ASSOC_OUT}")" \
    --candidate-decisions "$(to_runs_path "${RISK_OUT}")/candidate_decisions.jsonl" \
    --original-object-node-features "$(to_runs_path "${OBJECT_NODE_FEATURES}")" \
    --out-root "$(to_runs_path "${ASSOC_OUT}")" \
    --policy RiskResolutionReobserve
cp "${ASSOC_OUT}/association_recovery_arbitration_summary.json" "${OUT}/association_recovery_arbitration_summary.json"
cp "${ASSOC_OUT}/association_recovery_arbitration_rows.jsonl" "${OUT}/association_recovery_arbitration_rows.jsonl"

CURRENT_STAGE=pair_observation_plan
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.plan_pair_observation \
    --arbitration-rows "$(to_runs_path "${ASSOC_OUT}")/association_recovery_arbitration_rows.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${OUT}")" \
    --data-root /data \
    --run-id "${RUN_PREFIX}_pair_observation_${TS}" \
    --max-pairs 0 \
    --standoff-distances 1.25,1.75,2.25 \
    --preferred-standoff-distance-m 1.75 \
    --min-standoff-distance-m 0.75 \
    --max-standoff-distance-m 3.25 \
    "${PAIR_COMMON_FALLBACK_ARGS[@]}"

CURRENT_STAGE=pair_frame_export
write_status running "${CURRENT_STAGE}"
docker run --rm --gpus all --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions "$(to_runs_path "${OUT}")/pair_observation_plan.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${OUT}")" \
    --policy PairTopAltObservation \
    --max-decisions 0 \
    --max-candidates-per-decision 2 \
    --yaw-offsets=-30,0,30 \
    --candidate-point-field position
cp "${OUT}/postview_frames_v2.jsonl" "${OUT}/pair_observation_frames.jsonl"

PAIR_FRAME_ROWS="$(python - <<PY
from pathlib import Path
rows = [line for line in (Path("${OUT}") / "pair_observation_frames.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)"

CURRENT_STAGE=pair_detector
write_status running "${CURRENT_STAGE}"
docker run --rm ${GPU_FLAG} \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${MODEL_ROOT}:/models:ro" \
  -w /workspace \
  "${OPENVOCAB_IMG}" \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames "$(to_runs_path "${OUT}")/pair_observation_frames.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root "$(to_runs_path "${OUT}")" \
    --debug-root "$(to_runs_path "${OUT}")/debug_images" \
    --device "${DEVICE}" \
    --max-frames "${PAIR_FRAME_ROWS}" \
    --max-headings-per-frame "${MAX_HEADINGS_PER_FRAME}" \
    --max-detector-boxes-per-heading "${MAX_DETECTOR_BOXES_PER_HEADING}" \
    --max-masks-per-heading "${MAX_MASKS_PER_HEADING}" \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 2 \
    --candidate-point-field position \
    --box-threshold "${BOX_THRESHOLD}" \
    --text-threshold "${TEXT_THRESHOLD}" \
    --query-template "${QUERY_TEMPLATE}" \
    --box-padding-px 4 \
    --association-depth-tolerance-m "${ASSOCIATION_DEPTH_TOLERANCE_M}" \
    --max-debug-images 120

CURRENT_STAGE=pair_evidence_analysis
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_pair_observation_evidence \
    --pair-observation-plan "$(to_runs_path "${OUT}")/pair_observation_plan.jsonl" \
    --detector-root "$(to_runs_path "${OUT}")" \
    --candidate-decisions "$(to_runs_path "${RISK_OUT}")/candidate_decisions.jsonl" \
    --out-root "$(to_runs_path "${OUT}")" \
    --label-policy RiskResolutionReobserve \
    --pair-evidence-margin "${PAIR_EVIDENCE_MARGIN}"

CURRENT_STAGE=pair_failure_taxonomy
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_pair_observation_failure_modes \
    --pair-evidence-rows "$(to_runs_path "${OUT}")/pair_observation_evidence_rows.jsonl" \
    --detector-associations "$(to_runs_path "${OUT}")/detector_candidate_associations.jsonl" \
    --out-root "$(to_runs_path "${OUT}")"

CURRENT_STAGE=substrate_verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

out = Path("${OUT}")
risk = json.loads((out / "risk_resolution_summary.json").read_text(encoding="utf-8"))
assoc = json.loads((out / "association_recovery_arbitration_summary.json").read_text(encoding="utf-8"))
plan = json.loads((out / "pair_observation_plan_summary.json").read_text(encoding="utf-8"))
detector = json.loads((out / "summary.json").read_text(encoding="utf-8"))
pair = json.loads((out / "pair_observation_evidence_summary.json").read_text(encoding="utf-8"))
failure = json.loads((out / "pair_observation_failure_mode_summary.json").read_text(encoding="utf-8"))
risk_rows = sum(
    1 for line in (Path("${RISK_OUT}") / "viewpoint_decisions.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip() and json.loads(line).get("policy") == "RiskResolutionReobserve"
)
assoc_rows = sum(
    1 for line in (Path("${ASSOC_OUT}") / "risk_resolution_after_second_rows.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
)
gate = {
    "risk_resolution_rows": risk_rows,
    "min_risk_resolution_rows": 80,
    "association_recovery_rows": assoc_rows,
    "min_association_recovery_rows": 20,
    "pair_trigger_rows": plan.get("pair_count"),
    "min_pair_trigger_rows": 10,
    "pair_observation_rows": pair.get("pair_rows"),
    "min_pair_observation_rows": 10,
    "detector_box_rate": detector.get("rows_with_detector_box_rate"),
    "min_detector_box_rate": 0.80,
    "sam2_mask_rate": detector.get("rows_with_sam2_mask_rate"),
    "min_sam2_mask_rate": 0.80,
    "pair_evidence_available_rate": pair.get("gate", {}).get("pair_evidence_available_rate"),
    "min_pair_evidence_available_rate": 0.50,
}
gate["passes_substrate_validity_gate"] = bool(
    gate["risk_resolution_rows"] >= gate["min_risk_resolution_rows"]
    and gate["association_recovery_rows"] >= gate["min_association_recovery_rows"]
    and (gate["pair_trigger_rows"] or 0) >= gate["min_pair_trigger_rows"]
    and (gate["pair_observation_rows"] or 0) >= gate["min_pair_observation_rows"]
    and (gate["detector_box_rate"] or 0.0) >= gate["min_detector_box_rate"]
    and (gate["sam2_mask_rate"] or 0.0) >= gate["min_sam2_mask_rate"]
    and (gate["pair_evidence_available_rate"] or 0.0) >= gate["min_pair_evidence_available_rate"]
)
payload = {
    "schema_version": "h001.heldout_pair_substrate.v1",
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "risk_out": "${RISK_OUT}",
    "association_recovery_out": "${ASSOC_OUT}",
    "out": "${OUT}",
    "risk_summary": "risk_resolution_summary.json",
    "association_recovery_arbitration_summary": "association_recovery_arbitration_summary.json",
    "pair_observation_plan_summary": "pair_observation_plan_summary.json",
    "detector_summary": "summary.json",
    "pair_observation_evidence_summary": "pair_observation_evidence_summary.json",
    "pair_observation_failure_mode_summary": "pair_observation_failure_mode_summary.json",
    "association_recovery_action_counts": assoc.get("arbitration_action_counts"),
    "pair_plan_mode_counts": plan.get("mode_counts"),
    "pair_evidence_action_counts": pair.get("pair_evidence_action_counts"),
    "pair_primary_failure_mode_counts": failure.get("primary_failure_mode_counts"),
    "gate": gate,
    "uses_gt_for_action": bool(
        risk.get("candidate_backend_uses_gt_for_action")
        or assoc.get("uses_gt_for_action")
        or plan.get("uses_gt_for_action")
        or detector.get("uses_gt_for_action")
        or pair.get("uses_gt_for_action")
        or failure.get("uses_gt_for_action")
    ),
    "next_expected_file": "pair_observation_objective_v2_summary.json",
}
(out / "heldout_pair_substrate_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
PY

CURRENT_STAGE=verified
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
