import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.post_update_goal_validity_gap_reobservation_evaluation_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_post_update_goal_validity_gap_reobservation_evaluation_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_post_update_goal_validity_gap_reobservation_evaluation_join_v1"

OUTPUT_FILES = {
    "request_eval_rows": "post_update_goal_validity_gap_reobservation_evaluation_join_request_rows.jsonl",
    "candidate_eval_rows": "post_update_goal_validity_gap_reobservation_evaluation_join_candidate_rows.jsonl",
    "baseline_eval_rows": "post_update_goal_validity_gap_reobservation_evaluation_join_baseline_rows.jsonl",
    "promotion_probe_rows": "post_update_goal_validity_gap_reobservation_evaluation_join_promotion_probe_rows.jsonl",
    "failure_rows": "post_update_goal_validity_gap_reobservation_evaluation_join_failure_rows.jsonl",
    "summary": "post_update_goal_validity_gap_reobservation_evaluation_join_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
POLICIES = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")
REFERENCE_WRONG_GOAL_POLICIES = ("NoReobserveReference", "SemanticOnly")

FORBIDDEN_ACTION_INPUTS = {
    "candidate_correctness_label",
    "candidate_wrong_label",
    "wrong_goal_visit_proxy",
    "success_commit_proxy",
    "terminal_commit_proxy",
    "no_valid_pool_proxy_as_label",
    "oracle_shortest_path_to_target",
    "GTTargetOracle_action",
    "GTCandidateOracle_action",
    "GTViewOracle_action",
    "post_join_baseline_outcome",
    "paper_claim_allowed",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def join_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return tuple(str(source.get(key) or row.get(key) or "") for key in JOIN_KEYS)  # type: ignore[return-value]


def candidate_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("candidate_id") or row.get("candidate_id") or ""))


def policy_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("policy_name") or row.get("policy_name") or ""))


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def group_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    groups: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[join_key(row)].append(row)
    return dict(groups)


def index_one(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {join_key(row): row for row in rows}


def index_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {candidate_key(row): row for row in rows}


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def scan_forbidden_action_inputs(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_ACTION_INPUTS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row.get("action_evidence_inputs", {}))
    return sorted(found)


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def policy_lookup(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = join_key(row)
        policy = policy_key(row)[-1]
        grouped[key][policy] = row
    return dict(grouped)


def baseline_wrong_goal_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("wrong_goal_visit_proxy") is True) for policy in POLICIES}


def baseline_success_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("success_commit_proxy") is True) for policy in POLICIES}


def baseline_terminal_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("terminal_commit_proxy") is True) for policy in POLICIES}


def baseline_wasted_path_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, Optional[float]]:
    return {policy: safe_float((policy_rows.get(policy) or {}).get("wasted_path_proxy_m")) for policy in POLICIES}


def reference_wrong_goal(exposure: Mapping[str, bool]) -> bool:
    return any(exposure.get(policy) is True for policy in REFERENCE_WRONG_GOAL_POLICIES)


def materialize_request_rows(
    *,
    branch_rows: Sequence[Mapping[str, Any]],
    eval_rows_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    baselines_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for branch in sorted(branch_rows, key=join_key):
        key = join_key(branch)
        payload = key_payload(key)
        eval_row = eval_rows_by_key.get(key) or {}
        policy_rows = baselines_by_key.get(key) or {}
        wrong_exposure = baseline_wrong_goal_exposure(policy_rows)
        wasted_exposure = baseline_wasted_path_exposure(policy_rows)
        is_primary = branch.get("target_role") == "primary_target"
        no_post_action_evidence = is_primary and branch.get("branch_action") == "request_independent_goal_validity_evidence"
        defer_only_failure = no_post_action_evidence and reference_wrong_goal(wrong_exposure)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_goal_validity_gap_branch_action_freeze",
                "row_type": "post_update_goal_validity_gap_reobservation_evaluation_join_request",
                "join_key": payload,
                **payload,
                "target_role": branch.get("target_role"),
                "branch_action": branch.get("branch_action"),
                "branch_action_family": branch.get("branch_action_family"),
                "branch_action_reason": branch.get("branch_action_reason"),
                "action_frozen_before_evaluation_join": True,
                "selected_candidate_ids": branch.get("selected_candidate_ids") or [],
                "selected_candidate_count": safe_int(branch.get("selected_candidate_count"), 0),
                "post_update_request_state": branch.get("post_update_request_state"),
                "goal_validity_risk_state": eval_row.get("goal_validity_risk_state", branch.get("goal_validity_risk_state")),
                "goal_validity_risk_proxy": safe_float(
                    eval_row.get("goal_validity_risk_proxy", branch.get("goal_validity_risk_proxy"))
                ),
                "goal_validity_label_join_available": eval_row.get("goal_validity_label_join_available") is True,
                "selected_candidate_clean_correct_count": safe_int(eval_row.get("selected_candidate_clean_correct_count"), 0),
                "selected_candidate_wrong_or_no_valid_count": safe_int(
                    eval_row.get("selected_candidate_wrong_or_no_valid_count"),
                    0,
                ),
                "viewpoint_evidence_gap_state": branch.get("viewpoint_evidence_gap_state"),
                "viewpoint_evidence_gap_proxy": safe_float(branch.get("viewpoint_evidence_gap_proxy")),
                "map_pose_consistency_uncertainty_state": branch.get("map_pose_consistency_uncertainty_state"),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    branch.get("map_pose_consistency_uncertainty_proxy")
                ),
                "pose_graph_connectivity_delta": safe_float(branch.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(branch.get("map_pose_consistency_delta")),
                "reobserve_travel_cost_m": safe_float(branch.get("reobserve_travel_cost_m")),
                "baseline_wrong_goal_exposure": wrong_exposure,
                "baseline_success_exposure": baseline_success_exposure(policy_rows),
                "baseline_terminal_commit_exposure": baseline_terminal_exposure(policy_rows),
                "baseline_wasted_path_exposure_m": wasted_exposure,
                "reference_wrong_goal_exposure": reference_wrong_goal(wrong_exposure),
                "post_action_goal_validity_evidence_available": False,
                "branch_wrong_goal_claim_allowed": False,
                "wrong_goal_reduction_only_by_defer_or_request_evidence": bool(defer_only_failure),
                "promotion_probe_row_required": bool(is_primary),
                **common_flags(),
            }
        )
    return out


def materialize_candidate_rows(
    *,
    branch_rows: Sequence[Mapping[str, Any]],
    eval_rows_by_candidate: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for branch in sorted(branch_rows, key=candidate_key):
        key = join_key(branch)
        payload = key_payload(key)
        ckey = candidate_key(branch)
        cid = ckey[-1]
        eval_row = eval_rows_by_candidate.get(ckey) or {}
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_goal_validity_gap_branch_action_freeze",
                "row_type": "post_update_goal_validity_gap_reobservation_evaluation_join_candidate",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": branch.get("target_role"),
                "branch_action": branch.get("branch_action"),
                "candidate_context_role": branch.get("candidate_context_role"),
                "action_frozen_before_evaluation_join": True,
                "post_observation_state": branch.get("post_observation_state"),
                "pre_observation_state": branch.get("pre_observation_state"),
                "goal_validity_risk_state": eval_row.get("goal_validity_risk_state", branch.get("goal_validity_risk_state")),
                "goal_validity_risk_proxy": safe_float(
                    eval_row.get("goal_validity_risk_proxy", branch.get("goal_validity_risk_proxy"))
                ),
                "goal_validity_label_join_available": eval_row.get("goal_validity_label_join_available") is True,
                "candidate_correctness_label": eval_row.get("candidate_correctness_label"),
                "candidate_wrong_label": eval_row.get("candidate_wrong_label"),
                "no_valid_pool_proxy": eval_row.get("no_valid_pool_proxy") is True,
                "viewpoint_evidence_gap_state": branch.get("viewpoint_evidence_gap_state"),
                "viewpoint_evidence_gap_proxy": safe_float(branch.get("viewpoint_evidence_gap_proxy")),
                "map_pose_consistency_uncertainty_state": branch.get("map_pose_consistency_uncertainty_state"),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    branch.get("map_pose_consistency_uncertainty_proxy")
                ),
                "pose_graph_connectivity_delta": safe_float(branch.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(branch.get("map_pose_consistency_delta")),
                "reobserve_travel_cost_m": safe_float(branch.get("reobserve_travel_cost_m")),
                "evaluation_only_candidate_label_join": True,
                "branch_wrong_goal_claim_allowed": False,
                **common_flags(),
            }
        )
    return out


def materialize_baseline_rows(source_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_rows, key=policy_key):
        key = join_key(source)
        payload = key_payload(key)
        policy = policy_key(source)[-1]
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_goal_validity_gap_branch_action_freeze",
                "row_type": "post_update_goal_validity_gap_reobservation_evaluation_join_baseline",
                "join_key": {**payload, "policy_name": policy},
                **payload,
                "policy_name": policy,
                "target_role": source.get("target_role"),
                "policy_selected_candidate_id": source.get("policy_selected_candidate_id"),
                "selector_id": source.get("selector_id"),
                "selector_action": source.get("selector_action"),
                "terminal_commit_proxy": source.get("terminal_commit_proxy"),
                "success_commit_proxy": source.get("success_commit_proxy"),
                "wrong_goal_visit_proxy": source.get("wrong_goal_visit_proxy"),
                "wasted_path_proxy_m": safe_float(source.get("wasted_path_proxy_m")),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "evaluation_only_baseline_context": True,
                "not_used_for_branch_action": True,
                **common_flags(),
            }
        )
    return out


def materialize_promotion_probe_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for request in sorted((row for row in request_rows if row.get("target_role") == "primary_target"), key=join_key):
        key = join_key(request)
        payload = key_payload(key)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_goal_validity_gap_branch_action_freeze",
                "row_type": "post_update_goal_validity_gap_reobservation_evaluation_join_promotion_probe",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "branch_action": request.get("branch_action"),
                "action_frozen_before_evaluation_join": True,
                "goal_validity_risk_state": request.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": request.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": request.get("map_pose_consistency_uncertainty_state"),
                "baseline_wrong_goal_exposure": request.get("baseline_wrong_goal_exposure"),
                "baseline_wasted_path_exposure_m": request.get("baseline_wasted_path_exposure_m"),
                "reobserve_travel_cost_m": request.get("reobserve_travel_cost_m"),
                "post_action_goal_validity_evidence_available": request.get("post_action_goal_validity_evidence_available"),
                "wrong_goal_reduction_only_by_defer_or_request_evidence": request.get(
                    "wrong_goal_reduction_only_by_defer_or_request_evidence"
                ),
                "promotion_probe_gate_passed": False,
                "promotion_probe_primary_blocker": "wrong_goal_reduction_only_by_defer_or_request_evidence"
                if request.get("wrong_goal_reduction_only_by_defer_or_request_evidence") is True
                else "post_action_goal_validity_evidence_missing",
                "branch_wrong_goal_claim_allowed": False,
                **common_flags(),
            }
        )
    return out


def failure_tags(row: Mapping[str, Any]) -> List[str]:
    tags = [
        "evaluation_join_only",
        "terminal_utility_blocked",
        "candidate_commit_blocked",
        "candidate_rejection_blocked",
        "paper_claim_blocked",
    ]
    if row.get("target_role") == "primary_target":
        tags.append("post_action_goal_validity_evidence_missing")
    else:
        tags.append("non_target_audit_control_preserved")
    if row.get("wrong_goal_reduction_only_by_defer_or_request_evidence") is True:
        tags.append("wrong_goal_reduction_only_by_defer_or_request_evidence")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "wrong_goal_reduction_only_by_defer_or_request_evidence",
        "post_action_goal_validity_evidence_missing",
        "non_target_audit_control_preserved",
        "evaluation_join_only",
    ):
        if tag in tags:
            return tag
    return "unknown"


def materialize_failure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for request in sorted(request_rows, key=join_key):
        key = join_key(request)
        payload = key_payload(key)
        tags = failure_tags(request)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_goal_validity_gap_branch_action_freeze",
                "row_type": "post_update_goal_validity_gap_reobservation_evaluation_join_failure",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "branch_action": request.get("branch_action"),
                "goal_validity_risk_state": request.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": request.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": request.get("map_pose_consistency_uncertainty_state"),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                "wrong_goal_reduction_only_by_defer_or_request_evidence": request.get(
                    "wrong_goal_reduction_only_by_defer_or_request_evidence"
                ),
                **common_flags(),
            }
        )
    return out


def baseline_policy_counts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        policy: {
            "rows": sum(1 for row in rows if row.get("policy_name") == policy),
            "primary_target_rows": sum(
                1 for row in rows if row.get("policy_name") == policy and row.get("target_role") == "primary_target"
            ),
            "terminal_commit_proxy_rows": sum(
                1 for row in rows if row.get("policy_name") == policy and row.get("terminal_commit_proxy") is True
            ),
            "success_commit_proxy_rows": sum(
                1 for row in rows if row.get("policy_name") == policy and row.get("success_commit_proxy") is True
            ),
            "wrong_goal_visit_proxy_rows": sum(
                1 for row in rows if row.get("policy_name") == policy and row.get("wrong_goal_visit_proxy") is True
            ),
            "primary_target_wrong_goal_visit_proxy_rows": sum(
                1
                for row in rows
                if row.get("policy_name") == policy
                and row.get("target_role") == "primary_target"
                and row.get("wrong_goal_visit_proxy") is True
            ),
            "wasted_path_proxy_m_stats": number_stats(
                row.get("wasted_path_proxy_m") for row in rows if row.get("policy_name") == policy
            ),
            "primary_target_wasted_path_proxy_m_stats": number_stats(
                row.get("wasted_path_proxy_m")
                for row in rows
                if row.get("policy_name") == policy and row.get("target_role") == "primary_target"
            ),
        }
        for policy in POLICIES
    }


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    promotion_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    gate_contract = contract.get("evaluation_gate")
    gate_contract = gate_contract if isinstance(gate_contract, Mapping) else {}
    all_action_rows = [*request_rows, *candidate_rows, *promotion_rows, *failure_rows]
    primary_request_rows = [row for row in request_rows if row.get("target_role") == "primary_target"]
    non_target_request_rows = [row for row in request_rows if row.get("target_role") != "primary_target"]
    primary_candidate_rows = [row for row in candidate_rows if row.get("target_role") == "primary_target"]
    primary_baseline_rows = [row for row in baseline_rows if row.get("target_role") == "primary_target"]
    defer_only_rows = [
        row for row in promotion_rows if row.get("wrong_goal_reduction_only_by_defer_or_request_evidence") is True
    ]
    post_action_missing_rows = [
        row for row in promotion_rows if row.get("post_action_goal_validity_evidence_available") is not True
    ]
    actual_counts = {
        "request_rows": len(request_rows),
        "primary_target_rows": len(primary_request_rows),
        "non_target_audit_rows": len(non_target_request_rows),
        "candidate_rows": len(candidate_rows),
        "primary_target_candidate_rows": len(primary_candidate_rows),
        "baseline_rows": len(baseline_rows),
        "primary_target_baseline_rows": len(primary_baseline_rows),
        "promotion_probe_rows": len(promotion_rows),
        "failure_rows": len(failure_rows),
        "wrong_goal_reduction_only_by_defer_or_request_evidence_rows": len(defer_only_rows),
        "post_action_goal_validity_evidence_missing_rows": len(post_action_missing_rows),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_action_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_action_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_action_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_action_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_action_rows, "paper_claim_allowed"),
    }
    gate = {
        "request_rows_expected_passed": actual_counts["request_rows"]
        == safe_int(gate_contract.get("request_rows_expected"), 50),
        "primary_target_rows_expected_passed": actual_counts["primary_target_rows"]
        == safe_int(gate_contract.get("primary_target_rows_expected"), 21),
        "non_target_audit_rows_expected_passed": actual_counts["non_target_audit_rows"]
        == safe_int(gate_contract.get("non_target_audit_rows_expected"), 29),
        "candidate_rows_expected_passed": actual_counts["candidate_rows"]
        == safe_int(gate_contract.get("candidate_rows_expected"), 97),
        "primary_target_candidate_rows_expected_passed": actual_counts["primary_target_candidate_rows"]
        == safe_int(gate_contract.get("primary_target_candidate_rows_expected"), 42),
        "baseline_rows_expected_passed": actual_counts["baseline_rows"]
        == safe_int(gate_contract.get("baseline_rows_expected"), 150),
        "primary_target_baseline_rows_expected_passed": actual_counts["primary_target_baseline_rows"]
        == safe_int(gate_contract.get("primary_target_baseline_rows_expected"), 63),
        "promotion_probe_rows_minimum_passed": actual_counts["promotion_probe_rows"]
        >= safe_int(gate_contract.get("minimum_promotion_probe_rows"), 21),
        "action_evidence_forbidden_key_count_passed": actual_counts["action_evidence_forbidden_key_count"]
        == safe_int(gate_contract.get("action_evidence_forbidden_key_count_expected"), 0),
        "terminal_commit_rows_passed": actual_counts["terminal_commit_rows"]
        == safe_int(gate_contract.get("terminal_commit_rows_expected"), 0),
        "candidate_commit_rows_passed": actual_counts["candidate_commit_rows"]
        == safe_int(gate_contract.get("candidate_commit_rows_expected"), 0),
        "candidate_rejection_rows_passed": actual_counts["candidate_rejection_rows"]
        == safe_int(gate_contract.get("candidate_rejection_rows_expected"), 0),
        "uses_gt_for_action_passed": actual_counts["uses_gt_for_action_true_rows"]
        == safe_int(gate_contract.get("uses_gt_for_action_true_rows_expected"), 0),
        "paper_claim_blocked_passed": actual_counts["paper_claim_allowed_true_rows"]
        == safe_int(gate_contract.get("paper_claim_allowed_true_rows_expected"), 0),
    }
    join_gate_passed = all(gate.values())
    active_promotion_passed = False
    baseline_counts = baseline_policy_counts(baseline_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "evaluation_join_gate_passed_promotion_blocked"
        if join_gate_passed
        else "evaluation_join_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        "request_rows": actual_counts["request_rows"],
        "primary_target_rows": actual_counts["primary_target_rows"],
        "non_target_audit_rows": actual_counts["non_target_audit_rows"],
        "candidate_rows": actual_counts["candidate_rows"],
        "primary_target_candidate_rows": actual_counts["primary_target_candidate_rows"],
        "baseline_rows": actual_counts["baseline_rows"],
        "primary_target_baseline_rows": actual_counts["primary_target_baseline_rows"],
        "promotion_probe_rows": actual_counts["promotion_probe_rows"],
        "failure_rows": actual_counts["failure_rows"],
        "branch_action_counts": compact_counter(row.get("branch_action") for row in request_rows),
        "baseline_wrong_goal_rows": {
            "all_rows": {
                policy: baseline_counts[policy]["wrong_goal_visit_proxy_rows"] for policy in POLICIES
            },
            "primary_target_rows": {
                policy: baseline_counts[policy]["primary_target_wrong_goal_visit_proxy_rows"] for policy in POLICIES
            },
        },
        "baseline_wasted_path_stats": {
            policy: {
                "all_rows": baseline_counts[policy]["wasted_path_proxy_m_stats"],
                "primary_target_rows": baseline_counts[policy]["primary_target_wasted_path_proxy_m_stats"],
            }
            for policy in POLICIES
        },
        "wrong_goal_reduction_only_by_defer_or_request_evidence_rows": actual_counts[
            "wrong_goal_reduction_only_by_defer_or_request_evidence_rows"
        ],
        "post_action_goal_validity_evidence_missing_rows": actual_counts[
            "post_action_goal_validity_evidence_missing_rows"
        ],
        "request_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in request_rows
        ),
        "primary_target_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in primary_request_rows
        ),
        "request_viewpoint_evidence_gap_state_counts": compact_counter(
            row.get("viewpoint_evidence_gap_state") for row in request_rows
        ),
        "request_map_pose_uncertainty_state_counts": compact_counter(
            row.get("map_pose_consistency_uncertainty_state") for row in request_rows
        ),
        "candidate_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in candidate_rows
        ),
        "candidate_correctness_label_counts": {
            "correct": sum(1 for row in candidate_rows if row.get("candidate_correctness_label") is True),
            "wrong": sum(1 for row in candidate_rows if row.get("candidate_wrong_label") is True),
            "no_valid_pool": sum(1 for row in candidate_rows if row.get("no_valid_pool_proxy") is True),
            "label_missing": sum(1 for row in candidate_rows if row.get("goal_validity_label_join_available") is not True),
        },
        "baseline_policy_counts": baseline_counts,
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_key_count": actual_counts["action_evidence_forbidden_key_count"],
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "terminal_commit_rows": actual_counts["terminal_commit_rows"],
        "candidate_commit_rows": actual_counts["candidate_commit_rows"],
        "candidate_rejection_rows": actual_counts["candidate_rejection_rows"],
        "uses_gt_for_action_true_rows": actual_counts["uses_gt_for_action_true_rows"],
        "paper_claim_allowed_true_rows": actual_counts["paper_claim_allowed_true_rows"],
        "evaluation_join_gate": gate,
        "evaluation_join_gate_passed": join_gate_passed,
        "active_reobservation_promotion_gate_passed": active_promotion_passed,
        "promotion_gate_attempted": True,
        "promotion_gate_primary_failure_conditions": [
            "wrong_goal_reduction_only_by_defer_or_request_evidence"
            if actual_counts["wrong_goal_reduction_only_by_defer_or_request_evidence_rows"] > 0
            else "post_action_goal_validity_evidence_missing"
        ],
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": "wrong_goal_reduction_only_by_defer_or_request_evidence"
        if actual_counts["wrong_goal_reduction_only_by_defer_or_request_evidence_rows"] > 0
        else "post_action_goal_validity_evidence_missing",
        "next_task": "freeze_post_action_independent_goal_validity_evidence_contract",
        "interpretation": {
            "fact": (
                "The materializer joins frozen goal-validity-gap branch actions to evaluation-only baseline and "
                "candidate labels on the same 50 rows."
            ),
            "agent_inference": (
                "The artifact is useful as a measurement gate, but the promotion gate stays blocked because "
                "the current branch requests evidence without materialized post-action goal-validity evidence."
            ),
            "paper_claim": (
                "No ObjectNav improvement, Semantic-SLAM complementarity, terminal utility, formula revision, "
                "first_eval rerun, policy-scale comparison, Step 4-5 promotion, or paper claim is allowed."
            ),
        },
    }


def verification_path(contract_path: Path) -> Path:
    return contract_path.with_name(f"{contract_path.stem}.verify.json")


def build_verify_payload(
    *,
    contract_path: Path,
    out_root: Path,
    summary: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "schema_version": f"{SCHEMA_VERSION}.verify",
        "date_checked": "2026-06-11",
        "ok": summary.get("evaluation_join_gate_passed") is True,
        "status": summary.get("status"),
        "verified_artifact": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": {
            "request_rows": summary.get("request_rows"),
            "primary_target_rows": summary.get("primary_target_rows"),
            "non_target_audit_rows": summary.get("non_target_audit_rows"),
            "candidate_rows": summary.get("candidate_rows"),
            "primary_target_candidate_rows": summary.get("primary_target_candidate_rows"),
            "baseline_rows": summary.get("baseline_rows"),
            "primary_target_baseline_rows": summary.get("primary_target_baseline_rows"),
            "promotion_probe_rows": summary.get("promotion_probe_rows"),
            "failure_rows": summary.get("failure_rows"),
            "wrong_goal_reduction_only_by_defer_or_request_evidence_rows": summary.get(
                "wrong_goal_reduction_only_by_defer_or_request_evidence_rows"
            ),
            "post_action_goal_validity_evidence_missing_rows": summary.get(
                "post_action_goal_validity_evidence_missing_rows"
            ),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "branch_action_counts": summary.get("branch_action_counts"),
        "baseline_wrong_goal_rows": summary.get("baseline_wrong_goal_rows"),
        "candidate_correctness_label_counts": summary.get("candidate_correctness_label_counts"),
        "evaluation_join_gate_passed": summary.get("evaluation_join_gate_passed"),
        "active_reobservation_promotion_gate_passed": summary.get("active_reobservation_promotion_gate_passed"),
        "primary_blocker": summary.get("primary_blocker"),
        "next_task": summary.get("next_task"),
        "paper_claim_allowed": False,
        "verified_output_files": {name: str(out_root / filename) for name, filename in OUTPUT_FILES.items()},
        "verification_commands": [
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m py_compile "
                "hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/"
                "materialize_post_update_goal_validity_gap_reobservation_evaluation_join.py"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_post_update_goal_validity_gap_reobservation_evaluation_join"
            ),
            (
                "jq '{status, request_rows, primary_target_rows, promotion_probe_rows, "
                "wrong_goal_reduction_only_by_defer_or_request_evidence_rows, evaluation_join_gate_passed, "
                "active_reobservation_promotion_gate_passed, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "branch_actions_frozen_before_labels": True,
            "same_row_comparison_required": True,
            "same_candidate_pool_required": True,
            "same_reobservation_budget_required": True,
            "commit_based_wrong_goal_required": True,
            "wrong_goal_reduction_by_defer_only_marked_failure": True,
            "terminal_commit_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "terminal_utility_validation_allowed": False,
            "formula_revision_allowed": False,
            "first_eval_rerun_allowed": False,
            "policy_scale_comparison_allowed": False,
            "step_4_5_promotion_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": summary.get("interpretation"),
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")

    branch_request_rows = load_jsonl(Path(str(source["branch_request_rows"])))
    branch_candidate_rows = load_jsonl(Path(str(source["branch_candidate_rows"])))
    branch_baseline_rows = load_jsonl(Path(str(source["branch_baseline_rows"])))
    post_update_request_rows = load_jsonl(Path(str(source["post_update_evaluation_join_request_rows"])))
    post_update_candidate_rows = load_jsonl(Path(str(source["post_update_evaluation_join_selected_candidate_rows"])))

    eval_rows_by_key = index_one(post_update_request_rows)
    eval_rows_by_candidate = index_candidates(post_update_candidate_rows)
    baselines_by_key = policy_lookup(branch_baseline_rows)

    request_rows = materialize_request_rows(
        branch_rows=branch_request_rows,
        eval_rows_by_key=eval_rows_by_key,
        baselines_by_key=baselines_by_key,
    )
    candidate_rows = materialize_candidate_rows(
        branch_rows=branch_candidate_rows,
        eval_rows_by_candidate=eval_rows_by_candidate,
    )
    baseline_rows = materialize_baseline_rows(branch_baseline_rows)
    promotion_rows = materialize_promotion_probe_rows(request_rows)
    failure_rows = materialize_failure_rows(request_rows)
    forbidden_keys = scan_forbidden_action_inputs([*branch_request_rows, *branch_candidate_rows])

    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        baseline_rows=baseline_rows,
        promotion_rows=promotion_rows,
        failure_rows=failure_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_eval_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_eval_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["baseline_eval_rows"], baseline_rows)
    write_jsonl(out_root / OUTPUT_FILES["promotion_probe_rows"], promotion_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verification_path(contract_path),
        build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary),
    )

    if summary.get("evaluation_join_gate_passed") is not True:
        raise SystemExit("post-update goal-validity-gap reobservation evaluation join gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize the post-update goal-validity-gap re-observation evaluation join."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
