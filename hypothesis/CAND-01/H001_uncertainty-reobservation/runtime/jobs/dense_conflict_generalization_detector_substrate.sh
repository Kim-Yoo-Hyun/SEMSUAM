#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
DATA_ROOT=${DATA_ROOT:-${ROOT}/local_dataset/data}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
MODEL_ROOT=${MODEL_ROOT:-${ROOT}/local_dataset/models}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
OPENVOCAB_IMG=${OPENVOCAB_IMG:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

MANIFEST=${MANIFEST:-${HYP}/manifests/h001_dense_conflict_generalization_v1.json}
MANIFEST_SPLIT=${MANIFEST_SPLIT:-dense_conflict_generalization_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
RECALL_SUMMARY=${RECALL_SUMMARY:-${RUNS_ROOT}/h001_dense_conflict_recall_gate_generalization_v1/dense_conflict_recall_summary.json}
OUT=${OUT:-${RUNS_ROOT}/h001_dense_conflict_generalization_detector_substrate_v1}
POLICY_OUT=${POLICY_OUT:-${OUT}/policy_revision}
FRAMES_OUT=${FRAMES_OUT:-${OUT}/postview_frames}
DETECTOR_OUT=${DETECTOR_OUT:-${OUT}/detector_v3c}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
EPISODES=${EPISODES:-20}
MAX_FRAMES=${MAX_FRAMES:-20}
MIN_FRAME_ROWS=${MIN_FRAME_ROWS:-18}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-position}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
RUN_ID=${RUN_ID:-h001_dense_conflict_generalization_detector_substrate_v1}
LOG=${LOG:-${HYP}/runtime/logs/dense-conflict-generalization-detector-substrate-${TS}.log}
STATUS=${STATUS:-${OUT}/job_status.json}

mkdir -p "$(dirname "${LOG}")" "${OUT}" "${POLICY_OUT}" "${FRAMES_OUT}" "${DETECTOR_OUT}"
exec > >(tee -a "${LOG}") 2>&1

to_runs_path() {
  local path="$1"
  if [[ "$path" == "${RUNS_ROOT}"/* ]]; then
    echo "/runs/${path#${RUNS_ROOT}/}"
  elif [[ "$path" == /tmp/research3-runs/* ]]; then
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
    "recall_summary": "${RECALL_SUMMARY}",
    "out": "${OUT}",
    "policy_out": "${POLICY_OUT}",
    "frames_out": "${FRAMES_OUT}",
    "detector_out": "${DETECTOR_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "episodes": int("${EPISODES}"),
    "max_frames": int("${MAX_FRAMES}"),
    "association_depth_tolerance_m": float("${ASSOCIATION_DEPTH_TOLERANCE_M}"),
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
echo "recall_summary=${RECALL_SUMMARY}"
echo "out=${OUT}"
echo "policy_out=${POLICY_OUT}"
echo "frames_out=${FRAMES_OUT}"
echo "detector_out=${DETECTOR_OUT}"
echo "log=${LOG}"
echo "expected_files=${POLICY_OUT}/viewpoint_decisions.jsonl ${FRAMES_OUT}/postview_frames_v2.jsonl ${DETECTOR_OUT}/summary.json ${OUT}/generalization_detector_substrate_summary.json"
echo "verification_command=cat ${STATUS} && cat ${OUT}/generalization_detector_substrate_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

paths = {
    "manifest": Path("${MANIFEST}"),
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "recall_summary": Path("${RECALL_SUMMARY}"),
    "groundingdino_config": Path("${GROUNDINGDINO_DIR}") / "config.json",
    "groundingdino_weights": Path("${GROUNDINGDINO_DIR}") / "model.safetensors",
    "sam2_checkpoint": Path("${SAM2_CHECKPOINT}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
recall = json.loads(paths["recall_summary"].read_text(encoding="utf-8"))
if recall.get("passes_any_dense_recall_gate") is not True:
    raise RuntimeError({"recall_gate_not_passed": str(paths["recall_summary"])})
print({"stage": "prerequisite_check_passed", "recall_gate_passed": True})
PY

CURRENT_STAGE=policy_revision
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest "/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/$(basename "${MANIFEST}")" \
    --manifest-split "${MANIFEST_SPLIT}" \
    --episodes "${EPISODES}" \
    --candidate-backend artifact_jsonl \
    --policies GTTargetOracle NoReobserve EvidenceGatedSemanticOnly \
    --out "$(to_runs_path "${POLICY_OUT}")" \
    --run-id "${RUN_ID}" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")"

python - <<PY
import json
from pathlib import Path

root = Path("${POLICY_OUT}")
summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
viewpoints = [
    json.loads(line)
    for line in (root / "viewpoint_decisions.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if summary["candidate_backend_uses_gt_for_action"] is not False:
    raise RuntimeError("candidate backend used GT for action")
if len(viewpoints) < int("${MIN_FRAME_ROWS}"):
    raise RuntimeError({"too_few_viewpoints": len(viewpoints)})
if any(row.get("policy") != "EvidenceGatedSemanticOnly" for row in viewpoints):
    raise RuntimeError({"unexpected_policy_rows": viewpoints[:3]})
print({"stage": "policy_revision_verified", "viewpoint_rows": len(viewpoints)})
PY

CURRENT_STAGE=frame_export
write_status running "${CURRENT_STAGE}"
docker run --rm --gpus all --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions "$(to_runs_path "${POLICY_OUT}")/viewpoint_decisions.jsonl" \
    --candidate-artifact "$(to_runs_path "${CANDIDATE_ARTIFACT}")" \
    --out-root "$(to_runs_path "${FRAMES_OUT}")" \
    --policy EvidenceGatedSemanticOnly \
    --max-decisions 0 \
    --max-candidates-per-decision 5 \
    --yaw-offsets=-30,0,30 \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}"

FRAME_ROWS="$(python - <<PY
import json
from pathlib import Path

root = Path("${FRAMES_OUT}")
rows = [
    json.loads(line)
    for line in (root / "postview_frames_v2.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if len(rows) < int("${MIN_FRAME_ROWS}"):
    raise RuntimeError({"too_few_frame_rows": len(rows)})
if any(row.get("uses_gt_for_action") is True for row in rows):
    raise RuntimeError("GT leakage in frame export")
print(len(rows))
PY
)"
echo "frame_rows=${FRAME_ROWS}"

if [[ "${DEVICE}" == "cuda" ]]; then
  GPU_FLAG="--gpus all"
else
  GPU_FLAG=""
fi

CURRENT_STAGE=detector_mask_scoring
write_status running "${CURRENT_STAGE}"
docker run --rm ${GPU_FLAG} \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
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
    --max-candidates-per-frame 5 \
    --candidate-point-field "${CANDIDATE_POINT_FIELD}" \
    --box-threshold "${BOX_THRESHOLD}" \
    --text-threshold "${TEXT_THRESHOLD}" \
    --query-template "${QUERY_TEMPLATE}" \
    --box-padding-px 4 \
    --association-depth-tolerance-m "${ASSOCIATION_DEPTH_TOLERANCE_M}" \
    --max-debug-images 120

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

out = Path("${OUT}")
policy = json.loads((Path("${POLICY_OUT}") / "summary.json").read_text(encoding="utf-8"))
frames = json.loads((Path("${FRAMES_OUT}") / "summary.json").read_text(encoding="utf-8"))
detector = json.loads((Path("${DETECTOR_OUT}") / "summary.json").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.dense_conflict_generalization_detector_substrate.v1",
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "recall_summary": "${RECALL_SUMMARY}",
    "policy_out": "${POLICY_OUT}",
    "frames_out": "${FRAMES_OUT}",
    "detector_out": "${DETECTOR_OUT}",
    "policy_success_rate": policy.get("aggregate", {}).get("EvidenceGatedSemanticOnly", {}).get("success_rate"),
    "policy_wrong_goal_visit_rate": policy.get("aggregate", {}).get("EvidenceGatedSemanticOnly", {}).get("wrong_goal_visit_rate"),
    "frame_rows_exported": frames.get("rows_exported"),
    "rendered_heading_count": frames.get("rendered_heading_count"),
    "detector_rows": detector.get("rows"),
    "rows_with_detector_box_rate": detector.get("rows_with_detector_box_rate"),
    "rows_with_sam2_mask_rate": detector.get("rows_with_sam2_mask_rate"),
    "rows_with_candidate_association_rate": detector.get("rows_with_candidate_association_rate"),
    "rows_with_candidate_association": detector.get("rows_with_candidate_association"),
    "associated_candidate_heading_count": detector.get("associated_candidate_heading_count"),
    "uses_gt_for_action": bool(
        policy.get("candidate_backend_uses_gt_for_action")
        or frames.get("uses_gt_for_action")
        or detector.get("uses_gt_for_action")
    ),
    "uses_gt_for_analysis": True,
    "gate": {
        "detector_box_rate_pass": (detector.get("rows_with_detector_box_rate") or 0.0) >= 0.80,
        "sam2_mask_rate_pass": (detector.get("rows_with_sam2_mask_rate") or 0.0) >= 0.80,
        "candidate_association_rate_pass": (detector.get("rows_with_candidate_association_rate") or 0.0) >= 0.30,
        "no_gt_action_pass": not bool(
            policy.get("candidate_backend_uses_gt_for_action")
            or frames.get("uses_gt_for_action")
            or detector.get("uses_gt_for_action")
        ),
    },
}
payload["gate"]["passes_detector_substrate_gate"] = all(payload["gate"].values())
(out / "generalization_detector_substrate_summary.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in action path")
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
