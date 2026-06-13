#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-${ROOT}/local_dataset/runs}
TS=${TS:-$(date +%Y%m%d-%H%M%S)}

export PLAN_OUT=${PLAN_OUT:-${RUNS_ROOT}/h001_rival_contradiction_region_contamination_multi_case_frame_plan_v1}
export FRAME_OUT=${FRAME_OUT:-${RUNS_ROOT}/h001_rival_contradiction_region_contamination_multi_case_frames_v1}
export FRAMES=${FRAMES:-${FRAME_OUT}/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl}
export FRAME_ROOT=${FRAME_ROOT:-${FRAME_OUT}}
export CANDIDATE_ARTIFACT=${CANDIDATE_ARTIFACT:-${PLAN_OUT}/rival_contradiction_region_contamination_multi_case_candidate_artifact.jsonl}
export OUT=${OUT:-${RUNS_ROOT}/h001_rival_contradiction_region_contamination_multi_case_detector_substrate_v1}
export DETECTOR_OUT=${DETECTOR_OUT:-${OUT}/detector_v3c}
export LOG=${LOG:-${HYP}/runtime/logs/rival-contradiction-region-contamination-multi-case-detector-substrate-${TS}.log}
export STATUS=${STATUS:-${OUT}/job_status.json}

export EXPECTED_POLICY=${EXPECTED_POLICY:-RivalContradictionRegionContaminationEvidenceMultiCase}
export EXPECTED_FRAME_ROWS=${EXPECTED_FRAME_ROWS:-72}
export MAX_FRAMES=${MAX_FRAMES:-72}
export MAX_CANDIDATES_PER_FRAME=${MAX_CANDIDATES_PER_FRAME:-2}
export CANDIDATE_POINT_FIELD=${CANDIDATE_POINT_FIELD:-grounded_position}
export PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=${PROJECTION_ANCHOR_HEIGHT_OFFSETS_M:-0.0,0.4,0.8,1.2,1.6,2.0,2.4}
export MIN_DETECTOR_BOX_RATE=${MIN_DETECTOR_BOX_RATE:-0.80}
export MIN_SAM2_MASK_RATE=${MIN_SAM2_MASK_RATE:-0.80}
export MIN_CANDIDATE_ASSOCIATION_RATE=${MIN_CANDIDATE_ASSOCIATION_RATE:-0.40}
export MIN_ROWS_WITH_CANDIDATE_ASSOCIATION=${MIN_ROWS_WITH_CANDIDATE_ASSOCIATION:-29}
export MIN_ASSOCIATED_CANDIDATE_HEADING_COUNT=${MIN_ASSOCIATED_CANDIDATE_HEADING_COUNT:-36}
export MIN_ROWS_WITH_CANDIDATE_ASSOCIATION_PER_ROLE=${MIN_ROWS_WITH_CANDIDATE_ASSOCIATION_PER_ROLE:-2}
export MIN_ASSOCIATED_SCENE_COUNT=${MIN_ASSOCIATED_SCENE_COUNT:-5}
export MIN_ASSOCIATED_QUERY_COUNT=${MIN_ASSOCIATED_QUERY_COUNT:-3}
export MAX_DEBUG_IMAGES=${MAX_DEBUG_IMAGES:-240}

write_status() {
  local job_state="$1"
  local stage="$2"
  python - "$STATUS" "$job_state" "$stage" <<PY
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
if path.exists():
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = {}
else:
    payload = {}
payload.update(
    {
        "status": sys.argv[2],
        "stage": sys.argv[3],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "multi_case_wrapper": "rival_contradiction_region_contamination_multi_case_detector_substrate.sh",
        "diagnostic": "${OUT}/rival_contradiction_region_contamination_multi_case_detector_substrate_diagnostic.json",
    }
)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
}

run_multi_case_diagnostic() {
  python - <<'PY'
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

out = Path(os.environ["OUT"])
summary_path = out / "expanded_retrieval_detector_substrate_summary.json"
frame_summary_path = out / "expanded_retrieval_detector_frame_summary.jsonl"
associations_path = out / "expanded_retrieval_detector_associations.jsonl"
diagnostic_path = out / "rival_contradiction_region_contamination_multi_case_detector_substrate_diagnostic.json"

required_roles = [
    "candidate_a_own_view",
    "candidate_b_own_view",
    "shared_region_or_relation_anchor_view",
    "cross_candidate_challenge_view",
]
expected_frame_rows = int(os.environ["EXPECTED_FRAME_ROWS"])
min_rows = int(os.environ["MIN_ROWS_WITH_CANDIDATE_ASSOCIATION"])
min_headings = int(os.environ["MIN_ASSOCIATED_CANDIDATE_HEADING_COUNT"])
min_per_role = int(os.environ["MIN_ROWS_WITH_CANDIDATE_ASSOCIATION_PER_ROLE"])
min_scenes = int(os.environ["MIN_ASSOCIATED_SCENE_COUNT"])
min_queries = int(os.environ["MIN_ASSOCIATED_QUERY_COUNT"])

def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

summary = json.loads(summary_path.read_text(encoding="utf-8"))
frame_rows = read_jsonl(frame_summary_path)
assoc_rows = read_jsonl(associations_path)

role_counts = Counter(row.get("role") or row.get("view_role") or row.get("rival_observation_role") for row in frame_rows)
role_candidate_association_counts = Counter()
role_row_association_counts = Counter()
scene_association_counts = Counter()
query_association_counts = Counter()
candidate_tuple_association_counts = Counter()
candidate_tuple_frame_counts = Counter()
selected_depth_check_status_counts = Counter()
all_anchor_depth_check_status_counts = Counter()
projection_anchor_status_counts = Counter()
terminal_commit_rows = 0
candidate_commit_rows = 0
candidate_rejection_rows = 0
paper_claim_allowed_rows = 0
gt_action_rows = 0
action_forbidden_key_count = 0
forbidden_action_keys = {
    "candidate_correct",
    "correct_candidate",
    "valid_candidate",
    "wrong_goal",
    "evaluation_only",
    "gt_object_id",
    "gt_instance_id",
}

def tuple_key(row: dict) -> str:
    candidate_ids = row.get("selected_candidate_ids") or row.get("candidate_ids") or []
    return "|".join(
        [
            str(row.get("scene_key")),
            str(row.get("query")),
            str(row.get("expanded_retrieval_request_id")),
            ",".join(sorted(map(str, candidate_ids))),
        ]
    )

associated_decision_ids = set()
for row in frame_rows:
    key = tuple_key(row)
    candidate_tuple_frame_counts[key] += 1
    role = row.get("role") or row.get("view_role") or row.get("rival_observation_role") or "unknown"
    if row.get("has_candidate_association"):
        associated_decision_ids.add(row.get("decision_id"))
        role_row_association_counts[role] += 1
        scene_association_counts[str(row.get("scene_key"))] += 1
        query_association_counts[str(row.get("query"))] += 1
        candidate_tuple_association_counts[key] += 1
    if row.get("uses_gt_for_action") is True:
        gt_action_rows += 1
    if row.get("paper_claim_allowed") is True:
        paper_claim_allowed_rows += 1
    if row.get("terminal_commit") or row.get("terminal_action") == "commit":
        terminal_commit_rows += 1
    if row.get("candidate_commit"):
        candidate_commit_rows += 1
    if row.get("candidate_rejection"):
        candidate_rejection_rows += 1
    action_forbidden_key_count += sum(1 for key in forbidden_action_keys if key in row)

for row in assoc_rows:
    role = row.get("role") or row.get("view_role") or row.get("rival_observation_role") or "unknown"
    if row.get("associated_to_candidate"):
        role_candidate_association_counts[f"{role}|{row.get('candidate_id')}"] += 1
    if row.get("depth_check_status") is not None:
        selected_depth_check_status_counts[str(row.get("depth_check_status"))] += 1
    for anchor in row.get("projection_anchor_results") or []:
        if anchor.get("depth_check_status") is not None:
            all_anchor_depth_check_status_counts[str(anchor.get("depth_check_status"))] += 1
        if anchor.get("projection_status") is not None:
            projection_anchor_status_counts[str(anchor.get("projection_status"))] += 1
    if row.get("uses_gt_for_action") is True:
        gt_action_rows += 1
    if row.get("paper_claim_allowed") is True:
        paper_claim_allowed_rows += 1
    if row.get("terminal_commit") or row.get("terminal_action") == "commit":
        terminal_commit_rows += 1
    if row.get("candidate_commit"):
        candidate_commit_rows += 1
    if row.get("candidate_rejection"):
        candidate_rejection_rows += 1
    action_forbidden_key_count += sum(1 for key in forbidden_action_keys if key in row)

associated_scene_count = len(scene_association_counts)
associated_query_count = len(query_association_counts)
role_rows_pass = {
    role: role_row_association_counts.get(role, 0) >= min_per_role
    for role in required_roles
}
role_count_pass = {
    role: role_counts.get(role, 0) == expected_frame_rows // len(required_roles)
    for role in required_roles
}
base_gate = summary.get("gate", {})
gate = {
    "base_detector_substrate_gate_passed": bool(base_gate.get("passes_detector_substrate_gate")),
    "frame_rows_match": len(frame_rows) == expected_frame_rows,
    "association_rows_nonempty": len(assoc_rows) > 0,
    "required_role_counts_pass": all(role_count_pass.values()),
    "rows_with_candidate_association_pass": (summary.get("rows_with_candidate_association") or 0) >= min_rows,
    "associated_candidate_heading_count_pass": (summary.get("associated_candidate_heading_count") or 0) >= min_headings,
    "rows_with_candidate_association_per_role_pass": all(role_rows_pass.values()),
    "associated_scene_count_pass": associated_scene_count >= min_scenes,
    "associated_query_count_pass": associated_query_count >= min_queries,
    "no_terminal_commit_pass": terminal_commit_rows == 0,
    "no_candidate_commit_pass": candidate_commit_rows == 0,
    "no_candidate_rejection_pass": candidate_rejection_rows == 0,
    "no_gt_action_pass": gt_action_rows == 0 and not bool(summary.get("uses_gt_for_action")),
    "paper_claim_blocked_pass": paper_claim_allowed_rows == 0 and summary.get("paper_claim_allowed") is False,
    "forbidden_action_key_absent_pass": action_forbidden_key_count == 0,
}
gate["passes_multi_case_detector_substrate_gate"] = all(gate.values())

failure_taxonomy = []
if not gate["base_detector_substrate_gate_passed"]:
    for key, value in sorted(base_gate.items()):
        if value is False:
            failure_taxonomy.append(f"base_gate_failed:{key}")
if not gate["frame_rows_match"]:
    failure_taxonomy.append(f"frame_rows_mismatch:{len(frame_rows)}_of_{expected_frame_rows}")
if not gate["required_role_counts_pass"]:
    for role, passed in role_count_pass.items():
        if not passed:
            failure_taxonomy.append(f"role_count_mismatch:{role}:{role_counts.get(role, 0)}")
if not gate["rows_with_candidate_association_pass"]:
    failure_taxonomy.append(
        f"insufficient_associated_rows:{summary.get('rows_with_candidate_association')}_lt_{min_rows}"
    )
if not gate["associated_candidate_heading_count_pass"]:
    failure_taxonomy.append(
        f"insufficient_associated_headings:{summary.get('associated_candidate_heading_count')}_lt_{min_headings}"
    )
if not gate["rows_with_candidate_association_per_role_pass"]:
    for role, passed in role_rows_pass.items():
        if not passed:
            failure_taxonomy.append(f"role_under_associated:{role}:{role_row_association_counts.get(role, 0)}")
if not gate["associated_scene_count_pass"]:
    failure_taxonomy.append(f"scene_coverage_low:{associated_scene_count}_lt_{min_scenes}")
if not gate["associated_query_count_pass"]:
    failure_taxonomy.append(f"query_coverage_low:{associated_query_count}_lt_{min_queries}")
if not gate["no_terminal_commit_pass"]:
    failure_taxonomy.append(f"terminal_commit_rows:{terminal_commit_rows}")
if not gate["no_candidate_commit_pass"]:
    failure_taxonomy.append(f"candidate_commit_rows:{candidate_commit_rows}")
if not gate["no_candidate_rejection_pass"]:
    failure_taxonomy.append(f"candidate_rejection_rows:{candidate_rejection_rows}")
if not gate["no_gt_action_pass"]:
    failure_taxonomy.append(f"gt_action_rows:{gt_action_rows}")
if not gate["paper_claim_blocked_pass"]:
    failure_taxonomy.append(f"paper_claim_allowed_rows:{paper_claim_allowed_rows}")
if not gate["forbidden_action_key_absent_pass"]:
    failure_taxonomy.append(f"action_forbidden_key_count:{action_forbidden_key_count}")
if not gate["association_rows_nonempty"]:
    failure_taxonomy.append("association_rows_empty")

diagnostic = {
    "schema_version": "h001.rival_contradiction_region_contamination_multi_case_detector_substrate_diagnostic.v1",
    "contract_name": "rival_contradiction_region_contamination_multi_case_detector_substrate_v1",
    "source_summary": str(summary_path),
    "frame_summary": str(frame_summary_path),
    "associations": str(associations_path),
    "frame_rows": len(frame_rows),
    "association_rows": len(assoc_rows),
    "role_counts": dict(sorted(role_counts.items())),
    "role_row_association_counts": dict(sorted(role_row_association_counts.items())),
    "role_candidate_association_counts": dict(sorted(role_candidate_association_counts.items())),
    "scene_association_counts": dict(sorted(scene_association_counts.items())),
    "query_association_counts": dict(sorted(query_association_counts.items())),
    "candidate_tuple_frame_counts": dict(sorted(candidate_tuple_frame_counts.items())),
    "candidate_tuple_association_counts": dict(sorted(candidate_tuple_association_counts.items())),
    "associated_scene_count": associated_scene_count,
    "associated_query_count": associated_query_count,
    "associated_decision_rows": len(associated_decision_ids),
    "projection_anchor_status_counts": dict(sorted(projection_anchor_status_counts.items())),
    "selected_depth_check_status_counts": dict(sorted(selected_depth_check_status_counts.items())),
    "all_anchor_depth_check_status_counts": dict(sorted(all_anchor_depth_check_status_counts.items())),
    "terminal_commit_rows": terminal_commit_rows,
    "candidate_commit_rows": candidate_commit_rows,
    "candidate_rejection_rows": candidate_rejection_rows,
    "gt_action_rows": gt_action_rows,
    "paper_claim_allowed_rows": paper_claim_allowed_rows,
    "action_forbidden_key_count": action_forbidden_key_count,
    "minimum_gate": {
        "min_rows_with_candidate_association": min_rows,
        "min_associated_candidate_heading_count": min_headings,
        "min_rows_with_candidate_association_per_role": min_per_role,
        "min_associated_scene_count": min_scenes,
        "min_associated_query_count": min_queries,
    },
    "gate": gate,
    "failure_taxonomy": failure_taxonomy,
    "uses_gt_for_action": False,
    "paper_claim_allowed": False,
}
diagnostic_path.write_text(json.dumps(diagnostic, indent=2, sort_keys=True), encoding="utf-8")

summary["multi_case_diagnostic"] = {
    "diagnostic_file": diagnostic_path.name,
    "role_counts": diagnostic["role_counts"],
    "role_row_association_counts": diagnostic["role_row_association_counts"],
    "scene_association_counts": diagnostic["scene_association_counts"],
    "query_association_counts": diagnostic["query_association_counts"],
    "associated_scene_count": associated_scene_count,
    "associated_query_count": associated_query_count,
    "selected_depth_check_status_counts": diagnostic["selected_depth_check_status_counts"],
    "all_anchor_depth_check_status_counts": diagnostic["all_anchor_depth_check_status_counts"],
    "failure_taxonomy": failure_taxonomy,
}
summary["multi_case_gate"] = gate
summary["paper_claim_allowed"] = False
summary["uses_gt_for_action"] = False
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

print(json.dumps(diagnostic, indent=2, sort_keys=True))
if not gate["passes_multi_case_detector_substrate_gate"]:
    raise SystemExit(1)
PY
}

mkdir -p "${OUT}" "$(dirname "${LOG}")"
echo "multi_case_wrapper_started_at=$(date -Is)" >> "${LOG}"
echo "working_directory=${ROOT}" >> "${LOG}"
echo "command=TS=${TS} ROOT=${ROOT} ${HYP}/runtime/jobs/rival_contradiction_region_contamination_multi_case_detector_substrate.sh" >> "${LOG}"
echo "output_path=${OUT}" >> "${LOG}"
echo "expected_files=${OUT}/job_status.json ${OUT}/detector_v3c/summary.json ${OUT}/expanded_retrieval_detector_associations.jsonl ${OUT}/expanded_retrieval_detector_frame_summary.jsonl ${OUT}/expanded_retrieval_detector_substrate_summary.json ${OUT}/rival_contradiction_region_contamination_multi_case_detector_substrate_diagnostic.json" >> "${LOG}"
echo "verification_command=cat ${OUT}/job_status.json && cat ${OUT}/expanded_retrieval_detector_substrate_summary.json && cat ${OUT}/rival_contradiction_region_contamination_multi_case_detector_substrate_diagnostic.json" >> "${LOG}"

write_status running detector_mask_scoring
bash "${HYP}/runtime/jobs/expanded_retrieval_detector_substrate.sh"

write_status running multi_case_diagnostic
set +e
run_multi_case_diagnostic 2>&1 | tee -a "${LOG}"
diagnostic_status=${PIPESTATUS[0]}
set -e

if [[ "${diagnostic_status}" -ne 0 ]]; then
  write_status failed multi_case_diagnostic
  exit "${diagnostic_status}"
fi

write_status completed completed
echo "multi_case_wrapper_completed_at=$(date -Is)" >> "${LOG}"
