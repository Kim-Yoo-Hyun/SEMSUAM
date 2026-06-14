#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
MODEL_ROOT=${MODEL_ROOT:-/tmp/research3-models}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
OPENVOCAB_IMG=${OPENVOCAB_IMG:-research3/openvocab-perception:20260513-v3c-gdino-sam2}
MANIFEST=${MANIFEST:-${HYP}/manifests/h001_first_eval_replacement_v1.json}
MANIFEST_SPLIT=${MANIFEST_SPLIT:-first_eval_replacement_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
POLICY_OUT=${POLICY_OUT:-${RUNS_ROOT}/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision}
FRAMES_OUT=${FRAMES_OUT:-${RUNS_ROOT}/h001_first_eval_replacement_postview_frames_v2_spatial_nms_p97_k20_v1}
DETECTOR_OUT=${DETECTOR_OUT:-${RUNS_ROOT}/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1}
RUN_ID=${RUN_ID:-h001_first_eval_replacement_v1_policy_revision_20260515}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
EPISODES=${EPISODES:-100}
MAX_FRAMES=${MAX_FRAMES:-100}
MIN_FRAME_ROWS=${MIN_FRAME_ROWS:-95}
MAX_HEADINGS_PER_FRAME=${MAX_HEADINGS_PER_FRAME:-0}
MAX_DETECTOR_BOXES_PER_HEADING=${MAX_DETECTOR_BOXES_PER_HEADING:-3}
MAX_MASKS_PER_HEADING=${MAX_MASKS_PER_HEADING:-3}
CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-position}
QUERY_TEMPLATE=${QUERY_TEMPLATE:-"{query}"}
BOX_THRESHOLD=${BOX_THRESHOLD:-0.10}
TEXT_THRESHOLD=${TEXT_THRESHOLD:-0.10}
ASSOCIATION_DEPTH_TOLERANCE_M=${ASSOCIATION_DEPTH_TOLERANCE_M:-1.0}
PROMOTION_ASSOCIATION_RATE=${PROMOTION_ASSOCIATION_RATE:-0.60}
LOG=${LOG:-${ROOT}/logs/first-eval-replacement-v3c-detector-artifact-$(date +%Y%m%d-%H%M%S).log}
STATUS=${STATUS:-${DETECTOR_OUT}/job_status.json}

mkdir -p "${ROOT}/logs" "${POLICY_OUT}" "${FRAMES_OUT}" "${DETECTOR_OUT}"
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
    "policy_out": "${POLICY_OUT}",
    "frames_out": "${FRAMES_OUT}",
    "detector_out": "${DETECTOR_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "max_frames": int("${MAX_FRAMES}"),
    "query_template": "${QUERY_TEMPLATE}",
    "max_headings_per_frame": int("${MAX_HEADINGS_PER_FRAME}"),
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
echo "policy_out=${POLICY_OUT}"
echo "frames_out=${FRAMES_OUT}"
echo "detector_out=${DETECTOR_OUT}"
echo "log=${LOG}"
echo "expected_files=${POLICY_OUT}/viewpoint_decisions.jsonl ${FRAMES_OUT}/postview_frames_v2.jsonl ${DETECTOR_OUT}/summary.json"
echo "verification_command=cat ${STATUS} && cat ${DETECTOR_OUT}/summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path
paths = {
    "manifest": Path("${MANIFEST}"),
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

CURRENT_STAGE=policy_revision
write_status running "${CURRENT_STAGE}"
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v ${DATA_ROOT}:/data:ro \
  -v ${RUNS_ROOT}:/runs \
  -v ${ROOT}:/workspace:ro \
  ${HABITAT_IMG} \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest /workspace/configs/h001/manifests/$(basename "${MANIFEST}") \
    --manifest-split ${MANIFEST_SPLIT} \
    --episodes ${EPISODES} \
    --candidate-backend artifact_jsonl \
    --policies GTTargetOracle NoReobserve EvidenceGatedSemanticOnly \
    --out $(to_runs_path "${POLICY_OUT}") \
    --run-id ${RUN_ID} \
    --candidate-artifact $(to_runs_path "${CANDIDATE_ARTIFACT}")"

python - <<PY
import json
from pathlib import Path
root = Path("${POLICY_OUT}")
summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
viewpoints = [json.loads(line) for line in (root / "viewpoint_decisions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
assert summary["candidate_backend_uses_gt_for_action"] is False, summary
assert len(viewpoints) == int("${EPISODES}"), len(viewpoints)
assert all(row.get("policy") == "EvidenceGatedSemanticOnly" for row in viewpoints), viewpoints[:3]
print({"stage": "policy_revision_verified", "viewpoint_rows": len(viewpoints)})
PY

CURRENT_STAGE=frame_export
write_status running "${CURRENT_STAGE}"
sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v ${DATA_ROOT}:/data:ro \
  -v ${RUNS_ROOT}:/runs \
  -v ${ROOT}:/workspace:ro \
  ${HABITAT_IMG} \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions $(to_runs_path "${POLICY_OUT}")/viewpoint_decisions.jsonl \
    --candidate-artifact $(to_runs_path "${CANDIDATE_ARTIFACT}") \
    --out-root $(to_runs_path "${FRAMES_OUT}") \
    --policy EvidenceGatedSemanticOnly \
    --max-decisions 0 \
    --max-candidates-per-decision 5 \
    --yaw-offsets=-30,0,30"

python - <<PY
import json
from pathlib import Path
root = Path("${FRAMES_OUT}")
rows = [json.loads(line) for line in (root / "postview_frames_v2.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
assert len(rows) >= int("${MIN_FRAME_ROWS}"), len(rows)
assert all(row.get("uses_gt_for_action") is False for row in rows)
assert min(len(row.get("rendered_headings", [])) for row in rows) >= 1
print({"stage": "frame_export_verified", "rows": len(rows), "heading_count": sum(len(row.get("rendered_headings", [])) for row in rows)})
PY
FRAME_ROWS="$(python - <<PY
import json
from pathlib import Path
root = Path("${FRAMES_OUT}")
rows = [line for line in (root / "postview_frames_v2.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
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
  -e PYTHONPATH=/workspace/src \
  -v ${ROOT}:/workspace \
  -v ${RUNS_ROOT}:/runs \
  -v ${MODEL_ROOT}:/models \
  -w /workspace \
  ${OPENVOCAB_IMG} \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames $(to_runs_path "${FRAMES_OUT}")/postview_frames_v2.jsonl \
    --candidate-artifact $(to_runs_path "${CANDIDATE_ARTIFACT}") \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root $(to_runs_path "${DETECTOR_OUT}") \
    --debug-root $(to_runs_path "${DETECTOR_OUT}")/debug_images \
    --device ${DEVICE} \
    --max-frames ${FRAME_ROWS} \
    --max-headings-per-frame ${MAX_HEADINGS_PER_FRAME} \
    --max-detector-boxes-per-heading ${MAX_DETECTOR_BOXES_PER_HEADING} \
    --max-masks-per-heading ${MAX_MASKS_PER_HEADING} \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 5 \
    --candidate-point-field ${CANDIDATE_POINT_FIELD} \
    --box-threshold ${BOX_THRESHOLD} \
    --text-threshold ${TEXT_THRESHOLD} \
    --query-template '${QUERY_TEMPLATE}' \
    --box-padding-px 4 \
    --association-depth-tolerance-m ${ASSOCIATION_DEPTH_TOLERANCE_M} \
    --max-debug-images 120"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from collections import defaultdict
from pathlib import Path

root = Path("${DETECTOR_OUT}")
summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
frames = [json.loads(line) for line in (root / "frame_summary.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
query_rows = defaultdict(lambda: {"rows": 0, "association_rows": 0, "associated_heading_count": 0})
for row in frames:
    item = query_rows[row["query"]]
    item["rows"] += 1
    item["association_rows"] += int(bool(row.get("has_candidate_association")))
    item["associated_heading_count"] += int(row.get("associated_candidate_heading_count", 0))

diagnostic = {
    "rows": summary["rows"],
    "rows_with_detector_box_rate": summary["rows_with_detector_box_rate"],
    "rows_with_sam2_mask_rate": summary["rows_with_sam2_mask_rate"],
    "rows_with_candidate_association_rate": summary["rows_with_candidate_association_rate"],
    "rows_with_candidate_association": summary["rows_with_candidate_association"],
    "associated_candidate_heading_count": summary["associated_candidate_heading_count"],
    "query_rows": dict(sorted(query_rows.items())),
    "promotion_association_rate": float("${PROMOTION_ASSOCIATION_RATE}"),
    "promotion_pass": (
        summary["rows"] == int("${MAX_FRAMES}")
        and summary["uses_gt_for_action"] is False
        and summary["rows_with_detector_box_rate"] >= 0.80
        and summary["rows_with_sam2_mask_rate"] >= 0.80
        and summary["rows_with_candidate_association_rate"] >= float("${PROMOTION_ASSOCIATION_RATE}")
    ),
    "uses_gt_for_action": summary["uses_gt_for_action"],
}
(root / "heldout_detector_diagnostic.json").write_text(json.dumps(diagnostic, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(diagnostic, indent=2, sort_keys=True))
assert summary["rows"] == int("${FRAME_ROWS}"), summary
assert summary["uses_gt_for_action"] is False, summary
assert summary["rows_with_detector_box_rate"] >= 0.80, summary
assert summary["rows_with_sam2_mask_rate"] >= 0.80, summary
assert summary["rows_with_candidate_association_rate"] >= float("${PROMOTION_ASSOCIATION_RATE}"), summary
PY

CURRENT_STAGE=verified
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
