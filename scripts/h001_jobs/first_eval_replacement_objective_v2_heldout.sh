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
DERIVATION_MANIFEST=${DERIVATION_MANIFEST:-${HYP}/manifests/h001_v3_fresh_validation_v1.json}
CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${RUNS_ROOT}/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl}
COVERAGE_SUMMARY=${COVERAGE_SUMMARY:-${RUNS_ROOT}/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json}
BASE_OBJECT_NODE_FEATURES=${BASE_OBJECT_NODE_FEATURES:-${RUNS_ROOT}/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl}
PAIR_OUT=${PAIR_OUT:-${RUNS_ROOT}/h001_first_eval_replacement_pair_objective_v4b_heldout_v1}
OBJECT_NODE_FEATURES=${OBJECT_NODE_FEATURES:-${PAIR_OUT}/association_recovery/candidate_object_node_features_after_second.jsonl}
EXTERNAL_OUT=${EXTERNAL_OUT:-${RUNS_ROOT}/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1}
EXTERNAL_EVIDENCE_V4_OUT=${EXTERNAL_EVIDENCE_V4_OUT:-${EXTERNAL_OUT}/external_candidate_evidence_v4}
FOLLOWUP_PLAN_OUT=${FOLLOWUP_PLAN_OUT:-${EXTERNAL_OUT}/external_candidate_followup_plan_v3_heldout}
FOLLOWUP_FRAMES_OUT=${FOLLOWUP_FRAMES_OUT:-${EXTERNAL_OUT}/external_candidate_followup_frames_v3_heldout}
FOLLOWUP_DETECTOR_OUT=${FOLLOWUP_DETECTOR_OUT:-${EXTERNAL_OUT}/external_candidate_followup_detector_v3_heldout}
FOLLOWUP_EVIDENCE_OUT=${FOLLOWUP_EVIDENCE_OUT:-${EXTERNAL_OUT}/external_candidate_followup_evidence_v3_heldout}
STAGE2_PLAN_OUT=${STAGE2_PLAN_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_v2_heldout_plan}
STAGE2_FRAMES_OUT=${STAGE2_FRAMES_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_v2_heldout_frames}
STAGE2_DETECTOR_OUT=${STAGE2_DETECTOR_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_v2_heldout_detector}
STAGE2_EVIDENCE_OUT=${STAGE2_EVIDENCE_OUT:-${EXTERNAL_OUT}/external_candidate_followup_identity_stage2_v2_heldout_evidence}
INTEGRATED_OUT=${INTEGRATED_OUT:-${EXTERNAL_OUT}/external_candidate_followup_v3_stage2_objective_v2_heldout_validation}
GROUNDINGDINO_DIR=${GROUNDINGDINO_DIR:-${MODEL_ROOT}/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny}
SAM2_CHECKPOINT=${SAM2_CHECKPOINT:-${MODEL_ROOT}/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt}
DEVICE=${DEVICE:-cuda}
EPISODES=${EPISODES:-100}
EXTERNAL_BUDGET=${EXTERNAL_BUDGET:-6}
VALIDATION_SCOPE=${VALIDATION_SCOPE:-heldout_validation}
RUN_ID=${RUN_ID:-h001_first_eval_replacement_objective_v2_heldout_${TS}}
LOG=${LOG:-${ROOT}/archive/logs/h001_runtime/first-eval-replacement-objective-v2-heldout-${TS}.log}
STATUS=${STATUS:-${EXTERNAL_OUT}/objective_v2_heldout_job_status.json}

mkdir -p "${ROOT}/archive/logs/h001_runtime" "${PAIR_OUT}" "${EXTERNAL_OUT}" "${EXTERNAL_EVIDENCE_V4_OUT}"
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
    "working_directory": "${ROOT}",
    "exact_command": "TS=${TS} bash ${HYP}/scripts/h001_jobs/first_eval_replacement_objective_v2_heldout.sh",
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "derivation_manifest": "${DERIVATION_MANIFEST}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "coverage_summary": "${COVERAGE_SUMMARY}",
    "base_object_node_features": "${BASE_OBJECT_NODE_FEATURES}",
    "pair_out": "${PAIR_OUT}",
    "object_node_features": "${OBJECT_NODE_FEATURES}",
    "external_out": "${EXTERNAL_OUT}",
    "external_evidence_v4_out": "${EXTERNAL_EVIDENCE_V4_OUT}",
    "followup_evidence_out": "${FOLLOWUP_EVIDENCE_OUT}",
    "stage2_evidence_out": "${STAGE2_EVIDENCE_OUT}",
    "integrated_out": "${INTEGRATED_OUT}",
    "log": "${LOG}",
    "device": "${DEVICE}",
    "validation_scope": "${VALIDATION_SCOPE}",
    "verification_command": "cat ${STATUS} && cat ${EXTERNAL_OUT}/objective_v2_heldout_validation_summary.json",
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
echo "exact_command=TS=${TS} bash ${HYP}/scripts/h001_jobs/first_eval_replacement_objective_v2_heldout.sh"
echo "manifest=${MANIFEST}"
echo "manifest_split=${MANIFEST_SPLIT}"
echo "derivation_manifest=${DERIVATION_MANIFEST}"
echo "candidate_artifact=${CANDIDATE_ARTIFACT}"
echo "coverage_summary=${COVERAGE_SUMMARY}"
echo "base_object_node_features=${BASE_OBJECT_NODE_FEATURES}"
echo "pair_out=${PAIR_OUT}"
echo "external_out=${EXTERNAL_OUT}"
echo "external_evidence_v4_out=${EXTERNAL_EVIDENCE_V4_OUT}"
echo "followup_evidence_out=${FOLLOWUP_EVIDENCE_OUT}"
echo "stage2_evidence_out=${STAGE2_EVIDENCE_OUT}"
echo "integrated_out=${INTEGRATED_OUT}"
echo "validation_scope=${VALIDATION_SCOPE}"
echo "log=${LOG}"
echo "expected_files=${PAIR_OUT}/pair_observation_objective_v4b_rows.jsonl ${EXTERNAL_EVIDENCE_V4_OUT}/external_candidate_evidence_v4_rows.jsonl ${FOLLOWUP_EVIDENCE_OUT}/external_candidate_followup_evidence_summary.json ${STAGE2_EVIDENCE_OUT}/external_candidate_second_stage_identity_evidence_summary.json ${INTEGRATED_OUT}/external_candidate_followup_v2_stage2_validation_summary.json"
echo "verification_command=cat ${STATUS} && cat ${EXTERNAL_OUT}/objective_v2_heldout_validation_summary.json"

CURRENT_STAGE=prerequisite_check
write_status running "${CURRENT_STAGE}"
docker image inspect "${HABITAT_IMG}" "${OPENVOCAB_IMG}" >/dev/null
python - <<PY
import json
from pathlib import Path

paths = {
    "manifest": Path("${MANIFEST}"),
    "derivation_manifest": Path("${DERIVATION_MANIFEST}"),
    "data_root": Path("${DATA_ROOT}"),
    "hm3d": Path("${DATA_ROOT}") / "scene_datasets" / "hm3d",
    "candidate_artifact": Path("${CANDIDATE_ARTIFACT}"),
    "coverage_summary": Path("${COVERAGE_SUMMARY}"),
    "base_object_node_features": Path("${BASE_OBJECT_NODE_FEATURES}"),
    "groundingdino_config": Path("${GROUNDINGDINO_DIR}") / "config.json",
    "groundingdino_weights": Path("${GROUNDINGDINO_DIR}") / "model.safetensors",
    "sam2_checkpoint": Path("${SAM2_CHECKPOINT}"),
}
missing = {name: str(path) for name, path in paths.items() if not path.exists()}
if missing:
    raise FileNotFoundError(missing)
coverage = json.loads(paths["coverage_summary"].read_text(encoding="utf-8"))
checks = coverage.get("checks") or {}
if checks.get("overall_pass") is not True:
    raise RuntimeError({"coverage_gate_not_passed": checks})
heldout = json.loads(paths["manifest"].read_text(encoding="utf-8"))
derivation = json.loads(paths["derivation_manifest"].read_text(encoding="utf-8"))
heldout_scenes = {
    row.get("scene_key")
    for row in heldout.get("rows", [])
    if row.get("selected_split") == "${MANIFEST_SPLIT}"
}
derivation_scenes = {
    row.get("scene_key")
    for row in derivation.get("rows", [])
    if row.get("selected_split") == "v3_fresh_validation_v1"
}
overlap = sorted(heldout_scenes & derivation_scenes)
if overlap:
    raise RuntimeError({"scene_overlap_with_derivation_split": overlap})
print({
    "stage": "prerequisite_check_passed",
    "coverage_overall_pass": checks.get("overall_pass"),
    "heldout_scene_count": len(heldout_scenes),
    "derivation_scene_count": len(derivation_scenes),
    "scene_overlap": overlap,
})
PY

CURRENT_STAGE=pair_v4b_revised_geometry
write_status running "${CURRENT_STAGE}"
MANIFEST="${MANIFEST}" \
MANIFEST_SPLIT="${MANIFEST_SPLIT}" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
COVERAGE_SUMMARY="${COVERAGE_SUMMARY}" \
OBJECT_NODE_FEATURES="${BASE_OBJECT_NODE_FEATURES}" \
PAIR_OUT="${PAIR_OUT}" \
RISK_OUT="${PAIR_OUT}/risk_resolution" \
ASSOC_OUT="${PAIR_OUT}/association_recovery" \
LOG="${ROOT}/archive/logs/h001_runtime/first-eval-replacement-pair-v4b-heldout-${TS}.log" \
STATUS="${PAIR_OUT}/pipeline_status.json" \
DEVICE="${DEVICE}" \
EPISODES="${EPISODES}" \
RUN_PREFIX="h001_first_eval_replacement_v1_v4b_heldout" \
bash "${HYP}/scripts/h001_jobs/v3_fresh_validation_pair_objective_v4_revised_geometry.sh"

CURRENT_STAGE=external_candidate_detector
write_status running "${CURRENT_STAGE}"
PAIR_OBJECTIVE_ROWS="${PAIR_OUT}/pair_observation_objective_v4b_rows.jsonl" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
OBJECT_NODE_FEATURES="${OBJECT_NODE_FEATURES}" \
OUT="${EXTERNAL_OUT}" \
PLAN_OUT="${EXTERNAL_OUT}/external_candidate_plan" \
FRAMES_OUT="${EXTERNAL_OUT}/external_candidate_frames" \
DETECTOR_OUT="${EXTERNAL_OUT}/external_candidate_detector" \
EVIDENCE_OUT="${EXTERNAL_OUT}/external_candidate_evidence_v1" \
LOG="${ROOT}/archive/logs/h001_runtime/first-eval-replacement-external-detector-heldout-${TS}.log" \
STATUS="${EXTERNAL_OUT}/external_detector_job_status.json" \
DEVICE="${DEVICE}" \
EXTERNAL_BUDGET="${EXTERNAL_BUDGET}" \
EXPECTED_TRIGGERED_ROWS=any \
RUN_ID="${RUN_ID}_external_detector" \
bash "${HYP}/scripts/h001_jobs/v3_fresh_validation_pair_objective_v4b_external_candidate_detector.sh"

CURRENT_STAGE=external_evidence_v4
write_status running "${CURRENT_STAGE}"
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src \
  -v "${RUNS_ROOT}:/runs" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.analyze_external_candidate_observation_evidence_v4 \
    --external-observation-plan "$(to_runs_path "${EXTERNAL_OUT}")/external_candidate_plan/external_candidate_observation_plan.jsonl" \
    --external-branch-rows "$(to_runs_path "${EXTERNAL_OUT}")/external_candidate_plan/external_candidate_branch_rows.jsonl" \
    --detector-root "$(to_runs_path "${EXTERNAL_OUT}")/external_candidate_detector" \
    --out-root "$(to_runs_path "${EXTERNAL_EVIDENCE_V4_OUT}")"

CURRENT_STAGE=followup_v3_stage2_objective_v2
write_status running "${CURRENT_STAGE}"
EXTERNAL_OUT="${EXTERNAL_OUT}" \
CANDIDATE_ARTIFACT="${CANDIDATE_ARTIFACT}" \
EXTERNAL_EVIDENCE_V4_ROWS="${EXTERNAL_EVIDENCE_V4_OUT}/external_candidate_evidence_v4_rows.jsonl" \
OBJECT_NODE_FEATURES="${OBJECT_NODE_FEATURES}" \
FOLLOWUP_PLAN_OUT="${FOLLOWUP_PLAN_OUT}" \
FOLLOWUP_FRAMES_OUT="${FOLLOWUP_FRAMES_OUT}" \
FOLLOWUP_DETECTOR_OUT="${FOLLOWUP_DETECTOR_OUT}" \
FOLLOWUP_EVIDENCE_V2_OUT="${FOLLOWUP_EVIDENCE_OUT}" \
STAGE2_PLAN_OUT="${STAGE2_PLAN_OUT}" \
STAGE2_FRAMES_OUT="${STAGE2_FRAMES_OUT}" \
STAGE2_DETECTOR_OUT="${STAGE2_DETECTOR_OUT}" \
STAGE2_EVIDENCE_OUT="${STAGE2_EVIDENCE_OUT}" \
INTEGRATED_OUT="${INTEGRATED_OUT}" \
FOLLOWUP_OBJECTIVE_VERSION=v3 \
SECOND_STAGE_OBJECTIVE_VERSION=v2 \
VALIDATION_SCOPE="${VALIDATION_SCOPE}" \
LOG="${ROOT}/archive/logs/h001_runtime/first-eval-replacement-followup-v3-stage2-objective-v2-heldout-${TS}.log" \
STATUS="${EXTERNAL_OUT}/followup_v3_stage2_objective_v2_heldout_job_status.json" \
DEVICE="${DEVICE}" \
RUN_ID="${RUN_ID}_followup_v3_stage2_v2" \
EXPECTED_FOLLOWUP_PLAN_ROWS=any \
EXPECTED_SOURCE_REQUEST_ROWS=any \
EXPECTED_STAGE2_REQUEST_ROWS=any \
bash "${HYP}/scripts/h001_jobs/v3_fresh_external_candidate_followup_v2_stage2.sh"

CURRENT_STAGE=verification
write_status running "${CURRENT_STAGE}"
python - <<PY
import json
from pathlib import Path

pair = json.loads((Path("${PAIR_OUT}") / "fixed_rule_pair_v4b_revised_geometry_validation_summary.json").read_text(encoding="utf-8"))
external = json.loads((Path("${EXTERNAL_OUT}") / "external_candidate_detector_validation_summary.json").read_text(encoding="utf-8"))
external_v4 = json.loads((Path("${EXTERNAL_EVIDENCE_V4_OUT}") / "external_candidate_evidence_v4_summary.json").read_text(encoding="utf-8"))
followup_job = json.loads((Path("${EXTERNAL_OUT}") / "external_candidate_followup_v2_stage2_job_summary.json").read_text(encoding="utf-8"))
integrated = json.loads((Path("${INTEGRATED_OUT}") / "external_candidate_followup_v2_stage2_validation_summary.json").read_text(encoding="utf-8"))
payload = {
    "schema_version": "h001.first_eval_replacement_objective_v2_heldout.v1",
    "manifest": "${MANIFEST}",
    "manifest_split": "${MANIFEST_SPLIT}",
    "derivation_manifest": "${DERIVATION_MANIFEST}",
    "candidate_artifact": "${CANDIDATE_ARTIFACT}",
    "pair_out": "${PAIR_OUT}",
    "external_out": "${EXTERNAL_OUT}",
    "external_evidence_v4_out": "${EXTERNAL_EVIDENCE_V4_OUT}",
    "integrated_out": "${INTEGRATED_OUT}",
    "validation_scope": "${VALIDATION_SCOPE}",
    "pair_objective_gate": pair.get("objective_gate"),
    "pair_action_counts": pair.get("objective_action_counts"),
    "external_detector_summary": external.get("detector_summary"),
    "external_v4_gate": external_v4.get("gate"),
    "external_v4_action_counts": external_v4.get("action_counts"),
    "followup_job_summary": {
        "followup_objective_version": followup_job.get("followup_objective_version"),
        "second_stage_objective_version": followup_job.get("second_stage_objective_version"),
        "followup_v2_action_counts": followup_job.get("followup_v2_action_counts"),
        "stage2_action_counts": followup_job.get("stage2_action_counts"),
        "terminal_action_counts": followup_job.get("terminal_action_counts"),
    },
    "integrated_gate": integrated.get("integrated", {}).get("gate"),
    "integrated_counts": {
        "terminal_rows": integrated.get("integrated", {}).get("terminal_rows"),
        "commit_rows": integrated.get("integrated", {}).get("commit_rows"),
        "success_commit_rows": integrated.get("integrated", {}).get("success_commit_rows"),
        "wrong_goal_commit_rows": integrated.get("integrated", {}).get("wrong_goal_commit_rows"),
        "no_valid_commit_rows": integrated.get("integrated", {}).get("no_valid_commit_rows"),
        "visit_position_only_commit_rows": integrated.get("integrated", {}).get("visit_position_only_commit_rows"),
    },
    "interpretation": integrated.get("interpretation"),
    "uses_gt_for_action": bool(
        pair.get("uses_gt_for_action")
        or external.get("uses_gt_for_action")
        or external_v4.get("uses_gt_for_action")
        or followup_job.get("uses_gt_for_action")
        or integrated.get("uses_gt_for_action")
    ),
    "uses_gt_for_analysis": bool(
        pair.get("uses_gt_for_analysis")
        or external.get("uses_gt_for_analysis")
        or external_v4.get("uses_gt_for_analysis")
        or followup_job.get("uses_gt_for_analysis")
        or integrated.get("uses_gt_for_analysis")
    ),
}
(Path("${EXTERNAL_OUT}") / "objective_v2_heldout_validation_summary.json").write_text(
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
