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
OBJECT_NODE_FEATURES=${OBJECT_NODE_FEATURES:-${RUNS_ROOT}/h001_v3_fresh_validation_object_node_evidence_objective_v1/candidate_object_node_features.jsonl}
PAIR_OUT=${PAIR_OUT:-${RUNS_ROOT}/h001_v3_fresh_validation_pair_objective_v4_revised_geometry_v1}
RISK_OUT=${RISK_OUT:-${PAIR_OUT}/risk_resolution}
ASSOC_OUT=${ASSOC_OUT:-${PAIR_OUT}/association_recovery}
LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/v3-fresh-validation-pair-objective-v4-revised-geometry-${TS}.log}
STATUS=${STATUS:-${PAIR_OUT}/pipeline_status.json}
DEVICE=${DEVICE:-cuda}
EPISODES=${EPISODES:-100}
RUN_PREFIX=${RUN_PREFIX:-h001_v3_fresh_validation_v1_v4_revised_geometry}

mkdir -p "${ROOT}/archive/logs/h001_runtime" "${PAIR_OUT}"
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
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "pair_out": "${PAIR_OUT}",
    "risk_out": "${RISK_OUT}",
    "association_recovery_out": "${ASSOC_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "episodes": int("${EPISODES}"),
    "pair_include_dual_fallback_for_common": True,
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
echo "object_node_features=${OBJECT_NODE_FEATURES}"
echo "pair_out=${PAIR_OUT}"
echo "risk_out=${RISK_OUT}"
echo "association_recovery_out=${ASSOC_OUT}"
echo "log=${LOG}"
echo "expected_files=${PAIR_OUT}/heldout_pair_substrate_summary.json ${PAIR_OUT}/pair_observation_objective_v4b_summary.json ${PAIR_OUT}/fixed_rule_pair_v4b_revised_geometry_validation_summary.json"
echo "verification_command=cat ${STATUS} && cat ${PAIR_OUT}/heldout_pair_substrate_summary.json && cat ${PAIR_OUT}/pair_observation_objective_v4b_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

paths = {
    "manifest": Path("${MANIFEST}"),
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "coverage_summary": Path("${COVERAGE_SUMMARY}"),
    "object_node_features": Path("${OBJECT_NODE_FEATURES}"),
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

CURRENT_STAGE=revised_geometry_pair_substrate
write_status running "${CURRENT_STAGE}"
TS="${TS}" \
MANIFEST="${MANIFEST}" \
MANIFEST_SPLIT="${MANIFEST_SPLIT}" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
OBJECT_NODE_FEATURES="${OBJECT_NODE_FEATURES}" \
OUT="${PAIR_OUT}" \
RISK_OUT="${RISK_OUT}" \
ASSOC_OUT="${ASSOC_OUT}" \
RUN_PREFIX="${RUN_PREFIX}" \
DEVICE="${DEVICE}" \
EPISODES="${EPISODES}" \
PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON=1 \
LOG="${ROOT}/archive/logs/h001_runtime/v3-fresh-validation-pair-v4-revised-geometry-substrate-${TS}.log" \
STATUS="${PAIR_OUT}/job_status.json" \
"${HYP}/scripts/h001_jobs/first_eval_replacement_pair_objective_v2_substrate.sh"

CURRENT_STAGE=pair_objective_v4b
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_pair_observation_objective_v4b \
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
objective = json.loads((pair_out / "pair_observation_objective_v4b_summary.json").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.v3_fresh_pair_objective_v4b.revised_geometry_validation.v1",
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "coverage_summary": "${COVERAGE_SUMMARY}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "pair_out": "${PAIR_OUT}",
    "substrate_gate": substrate.get("gate"),
    "pair_plan_mode_counts": substrate.get("pair_plan_mode_counts"),
    "objective_gate": objective.get("gate"),
    "objective_action_counts": objective.get("action_counts"),
    "objective_action_by_label_case": objective.get("action_by_label_case"),
    "uses_gt_for_action": bool(substrate.get("uses_gt_for_action") or objective.get("uses_gt_for_action")),
    "uses_gt_for_analysis": bool(objective.get("uses_gt_for_analysis")),
}
(pair_out / "fixed_rule_pair_v4b_revised_geometry_validation_summary.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["uses_gt_for_action"]:
    raise RuntimeError("GT leakage in action path")
if not substrate.get("gate", {}).get("passes_substrate_validity_gate"):
    raise RuntimeError({"substrate_gate_failed": substrate.get("gate")})
PY

CURRENT_STAGE=completed
write_status completed "${CURRENT_STAGE}"
echo "completed_at=$(date -Is)"
