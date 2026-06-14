#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

MANIFEST=${MANIFEST:-${HYP}/manifests/h001_v3_fresh_validation_v1.json}
MANIFEST_SPLIT=${MANIFEST_SPLIT:-v3_fresh_validation_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
COVERAGE_SUMMARY=${COVERAGE_SUMMARY:-${RUNS_ROOT}/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json}
POLICY_OUT=${POLICY_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/policy_revision}
FRAMES_OUT=${FRAMES_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_postview_frames_v2_spatial_nms_p97_k20_v1}
DETECTOR_OUT=${DETECTOR_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1}
OBJECT_NODE_OUT=${OBJECT_NODE_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_object_node_evidence_objective_v1}
PAIR_OUT=${PAIR_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_pair_objective_v3_fixed_v1}
RISK_OUT=${RISK_OUT:-${PAIR_OUT}/risk_resolution}
ASSOC_OUT=${ASSOC_OUT:-${PAIR_OUT}/association_recovery}
LOG=${LOG:-${ROOT}/logs/v3-fresh-validation-pair-objective-v3-${TS}.log}
STATUS=${STATUS:-${PAIR_OUT}/pipeline_status.json}
DEVICE=${DEVICE:-cuda}
EPISODES=${EPISODES:-100}
MAX_FRAMES=${MAX_FRAMES:-100}
MIN_FRAME_ROWS=${MIN_FRAME_ROWS:-95}
PROMOTION_ASSOCIATION_RATE=${PROMOTION_ASSOCIATION_RATE:-0.0}

mkdir -p "${ROOT}/logs" "${PAIR_OUT}" "${OBJECT_NODE_OUT}"
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
    "coverage_summary": "${COVERAGE_SUMMARY}",
    "policy_out": "${POLICY_OUT}",
    "frames_out": "${FRAMES_OUT}",
    "detector_out": "${DETECTOR_OUT}",
    "object_node_out": "${OBJECT_NODE_OUT}",
    "object_node_features": "${OBJECT_NODE_OUT}/candidate_object_node_features.jsonl",
    "pair_out": "${PAIR_OUT}",
    "risk_out": "${RISK_OUT}",
    "association_recovery_out": "${ASSOC_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "episodes": int("${EPISODES}"),
    "max_frames": int("${MAX_FRAMES}"),
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
echo "coverage_summary=${COVERAGE_SUMMARY}"
echo "policy_out=${POLICY_OUT}"
echo "frames_out=${FRAMES_OUT}"
echo "detector_out=${DETECTOR_OUT}"
echo "object_node_out=${OBJECT_NODE_OUT}"
echo "pair_out=${PAIR_OUT}"
echo "risk_out=${RISK_OUT}"
echo "association_recovery_out=${ASSOC_OUT}"
echo "log=${LOG}"
echo "expected_files=${OBJECT_NODE_OUT}/candidate_object_node_features.jsonl ${PAIR_OUT}/heldout_pair_substrate_summary.json ${PAIR_OUT}/pair_observation_objective_v3_summary.json"
echo "verification_command=cat ${STATUS} && cat ${PAIR_OUT}/heldout_pair_substrate_summary.json && cat ${PAIR_OUT}/pair_observation_objective_v3_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

paths = {
    "manifest": Path("${MANIFEST}"),
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "coverage_summary": Path("${COVERAGE_SUMMARY}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
coverage = json.loads(paths["coverage_summary"].read_text(encoding="utf-8"))
checks = coverage.get("checks") or {}
if checks.get("overall_pass") is not True:
    raise RuntimeError({"coverage_gate_not_passed": checks})
print({"stage": "prerequisite_check_passed", "coverage_overall_pass": checks.get("overall_pass")})
PY

CURRENT_STAGE=detector_artifact_generation
write_status running "${CURRENT_STAGE}"
TS="${TS}" \
MANIFEST="${MANIFEST}" \
MANIFEST_SPLIT="${MANIFEST_SPLIT}" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
POLICY_OUT="${POLICY_OUT}" \
FRAMES_OUT="${FRAMES_OUT}" \
DETECTOR_OUT="${DETECTOR_OUT}" \
RUN_ID="h001_v3_fresh_validation_v1_policy_revision_${TS}" \
DEVICE="${DEVICE}" \
EPISODES="${EPISODES}" \
MAX_FRAMES="${MAX_FRAMES}" \
MIN_FRAME_ROWS="${MIN_FRAME_ROWS}" \
PROMOTION_ASSOCIATION_RATE="${PROMOTION_ASSOCIATION_RATE}" \
LOG="${ROOT}/logs/v3-fresh-validation-v3c-detector-${TS}.log" \
STATUS="${DETECTOR_OUT}/job_status.json" \
"${HYP}/scripts/h001_jobs/first_eval_replacement_v3c_detector_artifact.sh"

CURRENT_STAGE=object_node_features
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_object_node_evidence_objective \
    --detector-root "$(to_runs_path "${DETECTOR_OUT}")" \
    --candidate-decisions "$(to_runs_path "${POLICY_OUT}")/candidate_decisions.jsonl" \
    --out "$(to_runs_path "${OBJECT_NODE_OUT}")" \
    --policy NoReobserve \
    --switch-margin 0.05

CURRENT_STAGE=pair_substrate_generation
write_status running "${CURRENT_STAGE}"
TS="${TS}" \
MANIFEST="${MANIFEST}" \
MANIFEST_SPLIT="${MANIFEST_SPLIT}" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
OBJECT_NODE_FEATURES="${OBJECT_NODE_OUT}/candidate_object_node_features.jsonl" \
OUT="${PAIR_OUT}" \
RISK_OUT="${RISK_OUT}" \
ASSOC_OUT="${ASSOC_OUT}" \
RUN_PREFIX="h001_v3_fresh_validation_v1" \
DEVICE="${DEVICE}" \
EPISODES="${EPISODES}" \
LOG="${ROOT}/logs/v3-fresh-validation-pair-substrate-${TS}.log" \
STATUS="${PAIR_OUT}/job_status.json" \
"${HYP}/scripts/h001_jobs/first_eval_replacement_pair_objective_v2_substrate.sh"

CURRENT_STAGE=pair_objective_v3
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_pair_observation_objective_v3 \
    --pair-evidence-rows "$(to_runs_path "${PAIR_OUT}")/pair_observation_evidence_rows.jsonl" \
    --pair-observation-plan "$(to_runs_path "${PAIR_OUT}")/pair_observation_plan.jsonl" \
    --out-root "$(to_runs_path "${PAIR_OUT}")"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

pair_out = Path("${PAIR_OUT}")
substrate = json.loads((pair_out / "heldout_pair_substrate_summary.json").read_text(encoding="utf-8"))
objective = json.loads((pair_out / "pair_observation_objective_v3_summary.json").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.v3_fresh_pair_objective_v3.fixed_validation.v1",
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "coverage_summary": "${COVERAGE_SUMMARY}",
    "detector_out": "${DETECTOR_OUT}",
    "object_node_out": "${OBJECT_NODE_OUT}",
    "pair_out": "${PAIR_OUT}",
    "substrate_gate": substrate.get("gate"),
    "objective_gate": objective.get("gate"),
    "objective_action_counts": objective.get("action_counts"),
    "objective_action_by_label_case": objective.get("action_by_label_case"),
    "uses_gt_for_action": bool(substrate.get("uses_gt_for_action") or objective.get("uses_gt_for_action")),
    "uses_gt_for_analysis": bool(objective.get("uses_gt_for_analysis")),
}
(pair_out / "fixed_rule_pair_v3_validation_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in action path")
if not substrate.get("gate", {}).get("passes_substrate_validity_gate"):
    raise RuntimeError({"substrate_gate_failed": substrate.get("gate")})
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
