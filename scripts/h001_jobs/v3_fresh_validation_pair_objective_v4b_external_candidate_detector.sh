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

PAIR_OBJECTIVE_ROWS=${PAIR_OBJECTIVE_ROWS:-${RUNS_ROOT}/h001_v3_fresh_validation_pair_objective_v4_revised_geometry_v1/pair_observation_objective_v4b_rows.jsonl}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
OBJECT_NODE_FEATURES=${OBJECT_NODE_FEATURES:-${RUNS_ROOT}/h001_v3_fresh_validation_pair_objective_v4_revised_geometry_v1/association_recovery/candidate_object_node_features_after_second.jsonl}
OUT=${OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1}
PLAN_OUT=${PLAN_OUT:-${OUT}/external_candidate_plan}
FRAMES_OUT=${FRAMES_OUT:-${OUT}/external_candidate_frames}
DETECTOR_OUT=${DETECTOR_OUT:-${OUT}/external_candidate_detector}
EVIDENCE_OUT=${EVIDENCE_OUT:-${OUT}/external_candidate_evidence}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
EXTERNAL_BUDGET=${EXTERNAL_BUDGET:-6}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-position}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
RUN_ID=${RUN_ID:-h001_v3_fresh_pair_v4b_external_candidate_detector_v1}
EXPECTED_TRIGGERED_ROWS=${EXPECTED_TRIGGERED_ROWS:-8}
LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/v3-fresh-validation-pair-v4b-external-candidate-detector-${TS}.log}
STATUS=${STATUS:-${OUT}/job_status.json}

mkdir -p "${ROOT}/archive/logs/h001_runtime" "${OUT}" "${PLAN_OUT}" "${FRAMES_OUT}" "${DETECTOR_OUT}" "${EVIDENCE_OUT}"
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
    "pair_objective_rows": "${PAIR_OBJECTIVE_ROWS}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "out": "${OUT}",
    "plan_out": "${PLAN_OUT}",
    "frames_out": "${FRAMES_OUT}",
    "detector_out": "${DETECTOR_OUT}",
    "evidence_out": "${EVIDENCE_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "external_budget": int("${EXTERNAL_BUDGET}"),
    "max_headings_per_frame": int("${MAX_HEADINGS_PER_FRAME}"),
    "run_id": "${RUN_ID}",
    "expected_triggered_rows": "${EXPECTED_TRIGGERED_ROWS}",
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
echo "pair_objective_rows=${PAIR_OBJECTIVE_ROWS}"
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "object_node_features=${OBJECT_NODE_FEATURES}"
echo "out=${OUT}"
echo "plan_out=${PLAN_OUT}"
echo "frames_out=${FRAMES_OUT}"
echo "detector_out=${DETECTOR_OUT}"
echo "evidence_out=${EVIDENCE_OUT}"
echo "log=${LOG}"
echo "run_id=${RUN_ID}"
echo "expected_triggered_rows=${EXPECTED_TRIGGERED_ROWS}"
echo "expected_files=${PLAN_OUT}/external_candidate_observation_plan.jsonl ${FRAMES_OUT}/postview_frames_v2.jsonl ${DETECTOR_OUT}/summary.json ${EVIDENCE_OUT}/external_candidate_evidence_summary.json"
echo "verification_command=cat ${STATUS} && cat ${OUT}/external_candidate_detector_validation_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path
paths = {
    "pair_objective_rows": Path("${PAIR_OBJECTIVE_ROWS}"),
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

CURRENT_STAGE=external_candidate_plan
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.plan_external_candidate_observation \
    --objective-version pair_v4b \
    --pair-objective-rows "$(to_runs_path "${PAIR_OBJECTIVE_ROWS}")" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --object-node-features "$(to_runs_path "${OBJECT_NODE_FEATURES}")" \
    --out-root "$(to_runs_path "${PLAN_OUT}")" \
    --run-id "${RUN_ID}" \
    --external-selection-mode rank_bands \
    --external-budget "${EXTERNAL_BUDGET}"

CURRENT_STAGE=external_frame_export
write_status running "${CURRENT_STAGE}"
docker run --rm --gpus all --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions "$(to_runs_path "${PLAN_OUT}")/external_candidate_observation_plan.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${FRAMES_OUT}")" \
    --policy ExternalCandidateObservation \
    --max-decisions 0 \
    --max-candidates-per-decision 1 \
    --yaw-offsets=-30,0,30 \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}"

FRAME_ROWS="$(python - <<PY
from pathlib import Path
rows = [
    line for line in (Path("${FRAMES_OUT}") / "postview_frames_v2.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
print(len(rows))
PY
)"

if [[ "${DEVICE}" == "cuda" ]]; then
  GPU_FLAG="--gpus all"
else
  GPU_FLAG=""
fi

CURRENT_STAGE=external_detector
write_status running "${CURRENT_STAGE}"
docker run --rm ${GPU_FLAG} \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${ROOT}:/workspace:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${MODEL_ROOT}:/models:ro" \
  -w /workspace \
  "${OPENVOCAB_IMG}" \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames "$(to_runs_path "${FRAMES_OUT}")/postview_frames_v2.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root "$(to_runs_path "${DETECTOR_OUT}")" \
    --debug-root "$(to_runs_path "${DETECTOR_OUT}")/debug_images" \
    --device "${DEVICE}" \
    --max-frames "${FRAME_ROWS}" \
    --max-headings-per-frame "${MAX_HEADINGS_PER_FRAME}" \
    --max-detector-boxes-per-heading "${MAX_DETECTOR_BOXES_PER_HEADING}" \
    --max-masks-per-heading "${MAX_MASKS_PER_HEADING}" \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 1 \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}" \
    --box-threshold "${BOX_THRESHOLD}" \
    --text-threshold "${TEXT_THRESHOLD}" \
    --query-template "${QUERY_TEMPLATE}" \
    --box-padding-px 4 \
    --association-depth-tolerance-m "${ASSOCIATION_DEPTH_TOLERANCE_M}" \
    --max-debug-images 120

CURRENT_STAGE=external_evidence_analysis
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_external_candidate_observation_evidence \
    --external-observation-plan "$(to_runs_path "${PLAN_OUT}")/external_candidate_observation_plan.jsonl" \
    --external-branch-rows "$(to_runs_path "${PLAN_OUT}")/external_candidate_branch_rows.jsonl" \
    --detector-root "$(to_runs_path "${DETECTOR_OUT}")" \
    --out-root "$(to_runs_path "${EVIDENCE_OUT}")"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

out = Path("${OUT}")
plan = json.loads((Path("${PLAN_OUT}") / "external_candidate_branch_summary.json").read_text(encoding="utf-8"))
frames = json.loads((Path("${FRAMES_OUT}") / "summary.json").read_text(encoding="utf-8"))
detector = json.loads((Path("${DETECTOR_OUT}") / "summary.json").read_text(encoding="utf-8"))
evidence = json.loads((Path("${EVIDENCE_OUT}") / "external_candidate_evidence_summary.json").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.v3_fresh_pair_v4b_external_candidate_detector_validation.v1",
    "pair_objective_rows": "${PAIR_OBJECTIVE_ROWS}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "plan_out": "${PLAN_OUT}",
    "frames_out": "${FRAMES_OUT}",
    "detector_out": "${DETECTOR_OUT}",
    "evidence_out": "${EVIDENCE_OUT}",
    "triggered_rows": plan.get("triggered_rows"),
    "plan_rows": plan.get("plan_rows"),
    "frame_rows_exported": frames.get("rows_exported"),
    "rendered_heading_count": frames.get("rendered_heading_count"),
    "detector_summary": {
        "rows": detector.get("rows"),
        "rows_with_detector_box_rate": detector.get("rows_with_detector_box_rate"),
        "rows_with_sam2_mask_rate": detector.get("rows_with_sam2_mask_rate"),
        "rows_with_candidate_association_rate": detector.get("rows_with_candidate_association_rate"),
    },
    "evidence_gate": evidence.get("gate"),
    "evidence_action_counts": evidence.get("action_counts"),
    "uses_gt_for_action": bool(
        plan.get("diagnosis", {}).get("uses_gt_for_action")
        or frames.get("uses_gt_for_action")
        or detector.get("uses_gt_for_action")
        or evidence.get("uses_gt_for_action")
    ),
    "uses_gt_for_analysis": bool(evidence.get("uses_gt_for_analysis")),
}
(out / "external_candidate_detector_validation_summary.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in action path")
expected_triggered_rows = "${EXPECTED_TRIGGERED_ROWS}"
if expected_triggered_rows.lower() not in {"", "any"}:
    expected = int(expected_triggered_rows)
    if payload["triggered_rows"] != expected:
        raise RuntimeError({"unexpected_triggered_rows": payload["triggered_rows"], "expected": expected})
if payload["frame_rows_exported"] != payload["plan_rows"]:
    raise RuntimeError({"frame_plan_mismatch": [payload["frame_rows_exported"], payload["plan_rows"]]})
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
