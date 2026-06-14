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

PLAN_ROOT=${PLAN_ROOT:-${RUNS_ROOT}/h001_pair_observation_plan_docker_smoke}
RISK_RUN=${RISK_RUN:-${RUNS_ROOT}/h001_risk_validation_risk_resolution_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
OUT=${OUT:-${RUNS_ROOT}/h001_pair_observation_detector_evidence_v1}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
PAIR_EVIDENCE_MARGIN=${PAIR_EVIDENCE_MARGIN:-0.05}
LOG=${LOG:-${ROOT}/logs/pair-observation-detector-evidence-v1-${TS}.log}
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
    "plan_root": "${PLAN_ROOT}",
    "risk_run": "${RISK_RUN}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "out": "${OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "query_template": "${QUERY_TEMPLATE}",
    "max_headings_per_frame": int("${MAX_HEADINGS_PER_FRAME}"),
    "pair_evidence_margin": float("${PAIR_EVIDENCE_MARGIN}"),
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
echo "plan_root=${PLAN_ROOT}"
echo "risk_run=${RISK_RUN}"
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "out=${OUT}"
echo "log=${LOG}"
echo "expected_files=${OUT}/pair_observation_plan.jsonl ${OUT}/pair_observation_frames.jsonl ${OUT}/detector_candidate_associations.jsonl ${OUT}/pair_observation_evidence_rows.jsonl ${OUT}/pair_observation_evidence_summary.json"
echo "verification_command=cat ${STATUS} && cat ${OUT}/summary.json && cat ${OUT}/pair_observation_evidence_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path

paths = {
    "pair_observation_plan": Path("${PLAN_ROOT}") / "pair_observation_plan.jsonl",
    "candidate_decisions": Path("${RISK_RUN}") / "candidate_decisions.jsonl",
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "groundingdino_config": Path("${GROUNDINGDINO_DIR}") / "config.json",
    "groundingdino_weights": Path("${GROUNDINGDINO_DIR}") / "model.safetensors",
    "sam2_checkpoint": Path("${SAM2_CHECKPOINT}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
print({"stage": "prerequisite_check_passed", "paths": {name: str(path) for name, path in paths.items()}})
PY

cp "${PLAN_ROOT}/pair_observation_plan.jsonl" "${OUT}/pair_observation_plan.jsonl"
cp "${PLAN_ROOT}/pair_observation_plan_summary.json" "${OUT}/pair_observation_plan_summary.json"
if [[ -f "${PLAN_ROOT}/pair_observation_skipped.jsonl" ]]; then
  cp "${PLAN_ROOT}/pair_observation_skipped.jsonl" "${OUT}/pair_observation_skipped.jsonl"
fi

CURRENT_STAGE=frame_export
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

FRAME_ROWS="$(python - <<PY
import json
from pathlib import Path

rows = [json.loads(line) for line in (Path("${OUT}") / "pair_observation_frames.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
assert rows, "pair_observation_frames.jsonl is empty"
assert all(row.get("uses_gt_for_action") is False for row in rows)
assert all(row.get("pair_observation_id") for row in rows)
assert all(row.get("candidate_set_rule") == "explicit_candidate_ids" for row in rows)
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
    --max-frames "${FRAME_ROWS}" \
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
    --candidate-decisions "$(to_runs_path "${RISK_RUN}")/candidate_decisions.jsonl" \
    --out-root "$(to_runs_path "${OUT}")" \
    --label-policy RiskResolutionReobserve \
    --pair-evidence-margin "${PAIR_EVIDENCE_MARGIN}"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

root = Path("${OUT}")
detector_summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
pair_summary = json.loads((root / "pair_observation_evidence_summary.json").read_text(encoding="utf-8"))
required = [
    "pair_observation_plan.jsonl",
    "pair_observation_frames.jsonl",
    "detector_candidate_associations.jsonl",
    "pair_observation_evidence_rows.jsonl",
    "pair_observation_evidence_summary.json",
]
missing = [name for name in required if not (root / name).exists()]
if missing:
    raise FileNotFoundError(missing)
assert detector_summary["uses_gt_for_action"] is False, detector_summary
assert pair_summary["uses_gt_for_action"] is False, pair_summary
assert pair_summary["pair_rows"] > 0, pair_summary
payload = {
    "detector_rows": detector_summary["rows"],
    "detector_box_rate": detector_summary["rows_with_detector_box_rate"],
    "sam2_mask_rate": detector_summary["rows_with_sam2_mask_rate"],
    "candidate_association_rate": detector_summary["rows_with_candidate_association_rate"],
    "pair_rows": pair_summary["pair_rows"],
    "pair_action_counts": pair_summary["pair_evidence_action_counts"],
    "gate": pair_summary["gate"],
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY

CURRENT_STAGE=verified
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
