#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

MANIFEST=${MANIFEST:-${HYP}/manifests/h001_risk_validation_v1.json}
MANIFEST_SPLIT=${MANIFEST_SPLIT:-risk_validation_v1}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
COVERAGE_SUMMARY=${COVERAGE_SUMMARY:-${RUNS_ROOT}/h001_risk_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json}
OBJECT_NODE_FEATURES=${OBJECT_NODE_FEATURES:-${RUNS_ROOT}/h001_risk_validation_object_node_evidence_objective_v1/candidate_object_node_features.jsonl}
PAIR_OUT=${PAIR_OUT:-${RUNS_ROOT}/h001_risk_validation_pair_objective_v4b_revised_geometry_v1}
EXTERNAL_OUT=${EXTERNAL_OUT:-${RUNS_ROOT}/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1}
V2_OUT=${V2_OUT:-${EXTERNAL_OUT}/external_candidate_evidence_v2}
LOG=${LOG:-${ROOT}/logs/risk-validation-pair-v4b-external-candidate-v2-holdout-${TS}.log}
STATUS=${STATUS:-${EXTERNAL_OUT}/frozen_v2_holdout_job_status.json}
DEVICE=${DEVICE:-cuda}
EPISODES=${EPISODES:-100}

mkdir -p "${ROOT}/logs" "${EXTERNAL_OUT}" "${V2_OUT}"
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
    "external_out": "${EXTERNAL_OUT}",
    "v2_out": "${V2_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "episodes": int("${EPISODES}"),
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
echo "external_out=${EXTERNAL_OUT}"
echo "v2_out=${V2_OUT}"
echo "log=${LOG}"
echo "expected_files=${PAIR_OUT}/pair_observation_objective_v4b_summary.json ${EXTERNAL_OUT}/external_candidate_detector/summary.json ${V2_OUT}/external_candidate_evidence_v2_summary.json ${EXTERNAL_OUT}/frozen_v2_holdout_validation_summary.json"
echo "verification_command=cat ${STATUS} && cat ${EXTERNAL_OUT}/frozen_v2_holdout_validation_summary.json"

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

CURRENT_STAGE=pair_objective_v4b_revised_geometry
write_status running "${CURRENT_STAGE}"
TS="${TS}" \
MANIFEST="${MANIFEST}" \
MANIFEST_SPLIT="${MANIFEST_SPLIT}" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
COVERAGE_SUMMARY="${COVERAGE_SUMMARY}" \
OBJECT_NODE_FEATURES="${OBJECT_NODE_FEATURES}" \
PAIR_OUT="${PAIR_OUT}" \
RISK_OUT="${PAIR_OUT}/risk_resolution" \
ASSOC_OUT="${PAIR_OUT}/association_recovery" \
RUN_PREFIX=h001_risk_validation_v4b_revised_geometry \
DEVICE="${DEVICE}" \
EPISODES="${EPISODES}" \
LOG="${ROOT}/logs/risk-validation-pair-v4b-revised-geometry-${TS}.log" \
STATUS="${PAIR_OUT}/pipeline_status.json" \
bash "${HYP}/scripts/h001_jobs/v3_fresh_validation_pair_objective_v4_revised_geometry.sh"

CURRENT_STAGE=external_candidate_detector
write_status running "${CURRENT_STAGE}"
TS="${TS}" \
PAIR_OBJECTIVE_ROWS="${PAIR_OUT}/pair_observation_objective_v4b_rows.jsonl" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
OBJECT_NODE_FEATURES="${PAIR_OUT}/association_recovery/candidate_object_node_features_after_second.jsonl" \
OUT="${EXTERNAL_OUT}" \
EVIDENCE_OUT="${EXTERNAL_OUT}/external_candidate_evidence_v1" \
RUN_ID=h001_risk_validation_pair_v4b_external_candidate_detector_v2_holdout_v1 \
EXPECTED_TRIGGERED_ROWS=any \
DEVICE="${DEVICE}" \
LOG="${ROOT}/logs/risk-validation-pair-v4b-external-candidate-detector-${TS}.log" \
STATUS="${EXTERNAL_OUT}/job_status.json" \
bash "${HYP}/scripts/h001_jobs/v3_fresh_validation_pair_objective_v4b_external_candidate_detector.sh"

CURRENT_STAGE=external_evidence_v2
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_external_candidate_observation_evidence_v2 \
    --external-observation-plan "$(to_runs_path "${EXTERNAL_OUT}")/external_candidate_plan/external_candidate_observation_plan.jsonl" \
    --external-branch-rows "$(to_runs_path "${EXTERNAL_OUT}")/external_candidate_plan/external_candidate_branch_rows.jsonl" \
    --detector-root "$(to_runs_path "${EXTERNAL_OUT}")/external_candidate_detector" \
    --out-root "$(to_runs_path "${V2_OUT}")"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

external_out = Path("${EXTERNAL_OUT}")
pair_out = Path("${PAIR_OUT}")
v2_out = Path("${V2_OUT}")
pair_summary = json.loads((pair_out / "fixed_rule_pair_v4b_revised_geometry_validation_summary.json").read_text(encoding="utf-8"))
external_v1 = json.loads((external_out / "external_candidate_detector_validation_summary.json").read_text(encoding="utf-8"))
v2 = json.loads((v2_out / "external_candidate_evidence_v2_summary.json").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.risk_validation_pair_v4b_external_candidate_v2_holdout.v1",
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "coverage_summary": "${COVERAGE_SUMMARY}",
    "pair_out": "${PAIR_OUT}",
    "external_out": "${EXTERNAL_OUT}",
    "v2_out": "${V2_OUT}",
    "pair_objective_gate": pair_summary.get("objective_gate"),
    "external_detector_summary": external_v1.get("detector_summary"),
    "external_v1_gate": external_v1.get("evidence_gate"),
    "external_v2_gate": v2.get("gate"),
    "external_v2_action_counts": v2.get("action_counts"),
    "external_v2_reason_counts": v2.get("reason_counts"),
    "uses_gt_for_action": bool(
        pair_summary.get("uses_gt_for_action")
        or external_v1.get("uses_gt_for_action")
        or v2.get("uses_gt_for_action")
    ),
    "uses_gt_for_analysis": bool(v2.get("uses_gt_for_analysis")),
}
(external_out / "frozen_v2_holdout_validation_summary.json").write_text(
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
