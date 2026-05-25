#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

MANIFEST=${MANIFEST:-${HYP}/manifests/h001_dense_conflict_v1.json}
RECALL_ROOT=${RECALL_ROOT:-${RUNS_ROOT}/h001_dense_conflict_recall_gate_v3_fresh_spatial_p97_k20_primary_final_v1}
RECALL_ROWS=${RECALL_ROWS:-${RECALL_ROOT}/dense_conflict_recall_rows.jsonl}
RECALL_SUMMARY=${RECALL_SUMMARY:-${RECALL_ROOT}/dense_conflict_recall_summary.json}
SOURCE_ROOT=${SOURCE_ROOT:-${RUNS_ROOT}/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1}
SOURCE_EVIDENCE_ROWS=${SOURCE_EVIDENCE_ROWS:-${SOURCE_ROOT}/external_candidate_followup_identity_stage2_semantic_neighbor_multiview_v3_full_evidence/external_candidate_second_stage_identity_evidence_rows.jsonl}
DETECTOR_SUMMARY=${DETECTOR_SUMMARY:-${SOURCE_ROOT}/external_candidate_followup_identity_stage2_semantic_neighbor_multiview_v3_full_detector/summary.json}
OUT=${OUT:-${RUNS_ROOT}/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1}
LOG=${LOG:-${HYP}/runtime/logs/dense-conflict-validation-from-source-${TS}.log}
STATUS=${STATUS:-${OUT}/job_status.json}

mkdir -p "${HYP}/runtime/logs" "${OUT}"
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
    "recall_rows": "${RECALL_ROWS}",
    "recall_summary": "${RECALL_SUMMARY}",
    "source_evidence_rows": "${SOURCE_EVIDENCE_ROWS}",
    "detector_summary": "${DETECTOR_SUMMARY}",
    "out": "${OUT}",
    "log": "${LOG}",
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
echo "recall_rows=${RECALL_ROWS}"
echo "recall_summary=${RECALL_SUMMARY}"
echo "source_evidence_rows=${SOURCE_EVIDENCE_ROWS}"
echo "detector_summary=${DETECTOR_SUMMARY}"
echo "out=${OUT}"
echo "log=${LOG}"
echo "expected_files=${OUT}/dense_terminal_arbitration_summary.json ${OUT}/dense_terminal_arbitration_rows.jsonl ${OUT}/failure_taxonomy.json"
echo "verification_command=cat ${STATUS} && cat ${OUT}/dense_terminal_arbitration_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
from pathlib import Path
paths = {
    "manifest": Path("${MANIFEST}"),
    "recall_rows": Path("${RECALL_ROWS}"),
    "recall_summary": Path("${RECALL_SUMMARY}"),
    "source_evidence_rows": Path("${SOURCE_EVIDENCE_ROWS}"),
    "detector_summary": Path("${DETECTOR_SUMMARY}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
print({"stage": "prerequisite_check_passed", "paths": {name: str(path) for name, path in paths.items()}})
PY

CURRENT_STAGE=dense_conflict_validation
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_dense_conflict_validation \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/$(basename "${MANIFEST}") \
    --source-evidence-rows "$(to_runs_path "${SOURCE_EVIDENCE_ROWS}")" \
    --recall-rows "$(to_runs_path "${RECALL_ROWS}")" \
    --recall-summary "$(to_runs_path "${RECALL_SUMMARY}")" \
    --detector-summary "$(to_runs_path "${DETECTOR_SUMMARY}")" \
    --out-root "$(to_runs_path "${OUT}")" \
    --source-name v3_fresh_stage2_multiview_v3_full \
    --roles primary

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path
summary = json.loads((Path("${OUT}") / "dense_terminal_arbitration_summary.json").read_text(encoding="utf-8"))
gate = summary["gate"]
if summary["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in action path")
if not gate["passes_dense_conflict_validation_gate"]:
    raise RuntimeError({"dense_conflict_validation_gate_failed": gate})
print({
    "stage": "dense_conflict_validation_verified",
    "rows": summary["rows"],
    "gate_pass": gate["passes_dense_conflict_validation_gate"],
    "success_commit_rows": gate["success_commit_rows"],
    "wrong_goal_commit_rows": gate["wrong_goal_commit_rows"],
})
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
