import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.post_action_evidence_evaluation_join.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_post_action_evidence_evaluation_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_post_action_evidence_evaluation_join_v1"

OUTPUT_FILES = {
    "request_eval_rows": "post_action_evidence_evaluation_join_request_rows.jsonl",
    "candidate_eval_rows": "post_action_evidence_evaluation_join_candidate_rows.jsonl",
    "baseline_eval_rows": "post_action_evidence_evaluation_join_baseline_rows.jsonl",
    "promotion_probe_rows": "post_action_evidence_evaluation_join_promotion_probe_rows.jsonl",
    "failure_rows": "post_action_evidence_evaluation_join_failure_rows.jsonl",
    "summary": "post_action_evidence_evaluation_join_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
POLICIES = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")
REFERENCE_WRONG_GOAL_POLICIES = ("NoReobserveReference", "SemanticOnly")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_wrong_label",
    "no_valid_candidate_pool_label",
    "success_commit_proxy",
    "wrong_goal_visit_proxy",
    "wasted_path_proxy_m",
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "oracle_shortest_path",
    "label_tuned_threshold",
    "post_hoc_dropped_row_flag",
    "oracle",
    "ground_truth",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
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


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


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


def index_one(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {join_key(row): row for row in rows}


def index_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {candidate_key(row): row for row in rows}


def policy_lookup(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[join_key(row)][policy_key(row)[-1]] = row
    return dict(grouped)


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def scan_forbidden_action_inputs(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_ACTION_KEYS:
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


def evidence_conflict(row: Mapping[str, Any]) -> bool:
    return row.get("evidence_status") == "independent_evidence_conflicted"


def evidence_missing(row: Mapping[str, Any]) -> bool:
    return row.get("evidence_status") == "independent_evidence_missing"


def materialize_request_rows(
    *,
    evidence_rows: Sequence[Mapping[str, Any]],
    previous_eval_rows_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    baselines_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for evidence in sorted(evidence_rows, key=join_key):
        key = join_key(evidence)
        payload = key_payload(key)
        previous = previous_eval_rows_by_key.get(key) or {}
        policy_rows = baselines_by_key.get(key) or {}
        wrong_exposure = baseline_wrong_goal_exposure(policy_rows)
        wasted_exposure = baseline_wasted_path_exposure(policy_rows)
        is_primary = evidence.get("target_role") == "primary_target"
        conflict_blocks = is_primary and evidence_conflict(evidence)
        missing_blocks = is_primary and evidence_missing(evidence)
        evidence_available = evidence.get("post_action_goal_validity_evidence_available") is True
        reduction_only_by_evidence = bool(is_primary and evidence_available and reference_wrong_goal(wrong_exposure))
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_post_action_evidence_freeze",
                "row_type": "post_action_evidence_evaluation_join_request",
                "join_key": payload,
                **payload,
                "target_role": evidence.get("target_role"),
                "source_branch_action": evidence.get("source_branch_action"),
                "post_action_evidence_frozen_before_evaluation_join": True,
                "post_action_goal_validity_evidence_available": evidence_available,
                "request_evidence_status": evidence.get("evidence_status"),
                "independent_evidence_candidate_count": safe_int(
                    evidence.get("independent_evidence_candidate_count"),
                    0,
                ),
                "evidence_missing_reason": evidence.get("evidence_missing_reason"),
                "goal_validity_risk_state": previous.get(
                    "goal_validity_risk_state",
                    evidence.get("goal_validity_risk_state_pre"),
                ),
                "goal_validity_risk_proxy": safe_float(previous.get("goal_validity_risk_proxy")),
                "goal_validity_label_join_available": previous.get("goal_validity_label_join_available") is True,
                "viewpoint_evidence_gap_state": previous.get(
                    "viewpoint_evidence_gap_state",
                    evidence.get("viewpoint_evidence_gap_state_pre"),
                ),
                "viewpoint_evidence_gap_proxy": safe_float(previous.get("viewpoint_evidence_gap_proxy")),
                "map_pose_consistency_uncertainty_state": previous.get(
                    "map_pose_consistency_uncertainty_state",
                    evidence.get("map_pose_consistency_uncertainty_state_pre"),
                ),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    previous.get("map_pose_consistency_uncertainty_proxy")
                ),
                "pose_graph_connectivity_delta": safe_float(previous.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(previous.get("map_pose_consistency_delta")),
                "source_reobserve_travel_cost_m": safe_float(evidence.get("source_reobserve_travel_cost_m")),
                "added_evidence_travel_cost_m": safe_float(evidence.get("added_evidence_travel_cost_m")),
                "baseline_wrong_goal_exposure": wrong_exposure,
                "baseline_success_exposure": baseline_success_exposure(policy_rows),
                "baseline_terminal_commit_exposure": baseline_terminal_exposure(policy_rows),
                "baseline_wasted_path_exposure_m": wasted_exposure,
                "reference_wrong_goal_exposure": reference_wrong_goal(wrong_exposure),
                "selected_candidate_count": safe_int(previous.get("selected_candidate_count"), 0),
                "selected_candidate_clean_correct_count": safe_int(
                    previous.get("selected_candidate_clean_correct_count"),
                    0,
                ),
                "selected_candidate_wrong_or_no_valid_count": safe_int(
                    previous.get("selected_candidate_wrong_or_no_valid_count"),
                    0,
                ),
                "post_action_wrong_goal_claim_allowed": False,
                "wrong_goal_reduction_only_by_evidence_availability": reduction_only_by_evidence,
                "evidence_conflict_blocks_promotion": bool(conflict_blocks),
                "evidence_missing_blocks_promotion": bool(missing_blocks),
                **common_flags(),
            }
        )
    return out


def materialize_candidate_rows(
    *,
    evidence_rows: Sequence[Mapping[str, Any]],
    previous_eval_rows_by_candidate: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for evidence in sorted(evidence_rows, key=candidate_key):
        key = join_key(evidence)
        payload = key_payload(key)
        ckey = candidate_key(evidence)
        cid = ckey[-1]
        previous = previous_eval_rows_by_candidate.get(ckey) or {}
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_post_action_evidence_freeze",
                "row_type": "post_action_evidence_evaluation_join_candidate",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": evidence.get("target_role"),
                "source_branch_action": evidence.get("source_branch_action"),
                "post_action_evidence_frozen_before_evaluation_join": True,
                "candidate_evidence_status": evidence.get("candidate_evidence_status"),
                "candidate_evidence_reason": evidence.get("candidate_evidence_reason"),
                "candidate_support_evidence_count": safe_int(evidence.get("candidate_support_evidence_count"), 0),
                "candidate_contradiction_evidence_count": safe_int(
                    evidence.get("candidate_contradiction_evidence_count"),
                    0,
                ),
                "candidate_correctness_label_for_evaluation_only": previous.get("candidate_correctness_label"),
                "candidate_wrong_label_for_evaluation_only": previous.get("candidate_wrong_label"),
                "no_valid_candidate_pool_for_evaluation_only": previous.get("no_valid_pool_proxy") is True,
                "goal_validity_label_join_available": previous.get("goal_validity_label_join_available") is True,
                "goal_validity_risk_state": previous.get("goal_validity_risk_state"),
                "goal_validity_risk_proxy": safe_float(previous.get("goal_validity_risk_proxy")),
                "viewpoint_coverage_delta": safe_float(evidence.get("viewpoint_coverage_delta")),
                "association_quality_proxy": safe_float(evidence.get("association_quality_proxy")),
                "map_pose_consistency_delta": safe_float(evidence.get("map_pose_consistency_delta")),
                "pose_graph_connectivity_delta": safe_float(evidence.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    evidence.get("map_pose_consistency_uncertainty_proxy")
                ),
                "evidence_available_is_not_goal_validity": True,
                "evaluation_only_candidate_label_join": True,
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
                "validation_stage": "evaluation_join_after_post_action_evidence_freeze",
                "row_type": "post_action_evidence_evaluation_join_baseline",
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
                "not_used_for_post_action_evidence": True,
                **common_flags(),
            }
        )
    return out


def promotion_blocker(row: Mapping[str, Any]) -> str:
    if row.get("evidence_conflict_blocks_promotion") is True:
        return "post_action_evidence_conflict_requires_non_gt_arbitration"
    if row.get("evidence_missing_blocks_promotion") is True:
        return "post_action_evidence_missing"
    if row.get("wrong_goal_reduction_only_by_evidence_availability") is True:
        return "wrong_goal_reduction_only_by_evidence_availability"
    return "post_action_evaluation_join_only_terminal_utility_blocked"


def materialize_promotion_probe_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for request in sorted((row for row in request_rows if row.get("target_role") == "primary_target"), key=join_key):
        key = join_key(request)
        payload = key_payload(key)
        blocker = promotion_blocker(request)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_post_action_evidence_freeze",
                "row_type": "post_action_evidence_evaluation_join_promotion_probe",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "source_branch_action": request.get("source_branch_action"),
                "post_action_evidence_frozen_before_evaluation_join": True,
                "post_action_goal_validity_evidence_available": request.get(
                    "post_action_goal_validity_evidence_available"
                ),
                "request_evidence_status": request.get("request_evidence_status"),
                "goal_validity_risk_state": request.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": request.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": request.get("map_pose_consistency_uncertainty_state"),
                "baseline_wrong_goal_exposure": request.get("baseline_wrong_goal_exposure"),
                "baseline_wasted_path_exposure_m": request.get("baseline_wasted_path_exposure_m"),
                "source_reobserve_travel_cost_m": request.get("source_reobserve_travel_cost_m"),
                "added_evidence_travel_cost_m": request.get("added_evidence_travel_cost_m"),
                "wrong_goal_reduction_only_by_evidence_availability": request.get(
                    "wrong_goal_reduction_only_by_evidence_availability"
                ),
                "evidence_conflict_blocks_promotion": request.get("evidence_conflict_blocks_promotion"),
                "evidence_missing_blocks_promotion": request.get("evidence_missing_blocks_promotion"),
                "promotion_probe_gate_passed": False,
                "promotion_probe_primary_blocker": blocker,
                "post_action_wrong_goal_claim_allowed": False,
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
    if row.get("target_role") != "primary_target":
        tags.append("audit_control_preserved")
    else:
        if row.get("evidence_conflict_blocks_promotion") is True:
            tags.append("post_action_evidence_conflict_requires_non_gt_arbitration")
        if row.get("evidence_missing_blocks_promotion") is True:
            tags.append("post_action_evidence_missing")
        if row.get("wrong_goal_reduction_only_by_evidence_availability") is True:
            tags.append("wrong_goal_reduction_only_by_evidence_availability")
        tags.append("evidence_available_is_not_goal_validity")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "post_action_evidence_conflict_requires_non_gt_arbitration",
        "post_action_evidence_missing",
        "wrong_goal_reduction_only_by_evidence_availability",
        "audit_control_preserved",
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
                "validation_stage": "evaluation_join_after_post_action_evidence_freeze",
                "row_type": "post_action_evidence_evaluation_join_failure",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "source_branch_action": request.get("source_branch_action"),
                "request_evidence_status": request.get("request_evidence_status"),
                "post_action_goal_validity_evidence_available": request.get(
                    "post_action_goal_validity_evidence_available"
                ),
                "goal_validity_risk_state": request.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": request.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": request.get("map_pose_consistency_uncertainty_state"),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
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
    primary_requests = [row for row in request_rows if row.get("target_role") == "primary_target"]
    audit_requests = [row for row in request_rows if row.get("target_role") != "primary_target"]
    primary_candidates = [row for row in candidate_rows if row.get("target_role") == "primary_target"]
    evidence_available_rows = [
        row for row in primary_requests if row.get("post_action_goal_validity_evidence_available") is True
    ]
    evidence_conflicted_rows = [row for row in primary_requests if row.get("request_evidence_status") == "independent_evidence_conflicted"]
    evidence_missing_rows = [row for row in primary_requests if row.get("request_evidence_status") == "independent_evidence_missing"]
    support_rows = [
        row for row in primary_candidates if row.get("candidate_evidence_status") == "independent_support_acquired"
    ]
    contradiction_rows = [
        row
        for row in primary_candidates
        if row.get("candidate_evidence_status") == "independent_contradiction_acquired"
    ]
    conflict_candidate_rows = [
        row
        for row in primary_candidates
        if row.get("candidate_evidence_status") == "independent_support_and_contradiction_conflict"
    ]
    missing_candidate_rows = [
        row for row in primary_candidates if row.get("candidate_evidence_status") == "independent_evidence_missing"
    ]
    actual_counts = {
        "request_rows": len(request_rows),
        "primary_target_rows": len(primary_requests),
        "non_target_audit_rows": len(audit_requests),
        "candidate_rows": len(candidate_rows),
        "primary_candidate_evidence_targets": len(primary_candidates),
        "baseline_rows": len(baseline_rows),
        "promotion_probe_rows": len(promotion_rows),
        "failure_rows": len(failure_rows),
        "request_evidence_available_rows": len(evidence_available_rows),
        "request_evidence_conflicted_rows": len(evidence_conflicted_rows),
        "request_evidence_missing_rows": len(evidence_missing_rows),
        "candidate_support_evidence_rows": len(support_rows),
        "candidate_contradiction_evidence_rows": len(contradiction_rows),
        "candidate_conflict_evidence_rows": len(conflict_candidate_rows),
        "candidate_missing_evidence_rows": len(missing_candidate_rows),
        "wrong_goal_reduction_only_by_evidence_availability_rows": sum(
            1 for row in promotion_rows if row.get("wrong_goal_reduction_only_by_evidence_availability") is True
        ),
        "evidence_conflict_blocks_promotion_rows": sum(
            1 for row in promotion_rows if row.get("evidence_conflict_blocks_promotion") is True
        ),
        "evidence_missing_blocks_promotion_rows": sum(
            1 for row in promotion_rows if row.get("evidence_missing_blocks_promotion") is True
        ),
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
        "primary_candidate_evidence_targets_expected_passed": actual_counts["primary_candidate_evidence_targets"]
        == safe_int(gate_contract.get("primary_candidate_evidence_targets_expected"), 42),
        "baseline_rows_expected_passed": actual_counts["baseline_rows"]
        == safe_int(gate_contract.get("baseline_rows_expected"), 150),
        "promotion_probe_rows_minimum_passed": actual_counts["promotion_probe_rows"]
        >= safe_int(gate_contract.get("minimum_promotion_probe_rows"), 21),
        "request_evidence_available_rows_expected_passed": actual_counts["request_evidence_available_rows"]
        == safe_int(gate_contract.get("request_evidence_available_rows_expected"), 18),
        "request_evidence_conflicted_rows_expected_passed": actual_counts["request_evidence_conflicted_rows"]
        == safe_int(gate_contract.get("request_evidence_conflicted_rows_expected"), 18),
        "request_evidence_missing_rows_expected_passed": actual_counts["request_evidence_missing_rows"]
        == safe_int(gate_contract.get("request_evidence_missing_rows_expected"), 3),
        "candidate_support_evidence_rows_expected_passed": actual_counts["candidate_support_evidence_rows"]
        == safe_int(gate_contract.get("candidate_support_evidence_rows_expected"), 27),
        "candidate_contradiction_evidence_rows_expected_passed": actual_counts["candidate_contradiction_evidence_rows"]
        == safe_int(gate_contract.get("candidate_contradiction_evidence_rows_expected"), 1),
        "candidate_conflict_evidence_rows_expected_passed": actual_counts["candidate_conflict_evidence_rows"]
        == safe_int(gate_contract.get("candidate_conflict_evidence_rows_expected"), 7),
        "candidate_missing_evidence_rows_expected_passed": actual_counts["candidate_missing_evidence_rows"]
        == safe_int(gate_contract.get("candidate_missing_evidence_rows_expected"), 7),
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
    baseline_counts = baseline_policy_counts(baseline_rows)
    primary_blocker = (
        "post_action_evidence_conflict_requires_non_gt_arbitration"
        if actual_counts["evidence_conflict_blocks_promotion_rows"] > 0
        else "post_action_evidence_missing"
        if actual_counts["evidence_missing_blocks_promotion_rows"] > 0
        else "wrong_goal_reduction_only_by_evidence_availability"
    )
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
        **actual_counts,
        "request_evidence_status_counts": compact_counter(row.get("request_evidence_status") for row in request_rows),
        "primary_request_evidence_status_counts": compact_counter(
            row.get("request_evidence_status") for row in primary_requests
        ),
        "candidate_evidence_status_counts": compact_counter(
            row.get("candidate_evidence_status") for row in candidate_rows
        ),
        "primary_candidate_evidence_status_counts": compact_counter(
            row.get("candidate_evidence_status") for row in primary_candidates
        ),
        "request_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in request_rows
        ),
        "primary_target_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in primary_requests
        ),
        "request_viewpoint_evidence_gap_state_counts": compact_counter(
            row.get("viewpoint_evidence_gap_state") for row in request_rows
        ),
        "request_map_pose_uncertainty_state_counts": compact_counter(
            row.get("map_pose_consistency_uncertainty_state") for row in request_rows
        ),
        "candidate_correctness_label_counts": {
            "correct": sum(
                1 for row in candidate_rows if row.get("candidate_correctness_label_for_evaluation_only") is True
            ),
            "wrong": sum(
                1 for row in candidate_rows if row.get("candidate_wrong_label_for_evaluation_only") is True
            ),
            "no_valid_pool": sum(
                1 for row in candidate_rows if row.get("no_valid_candidate_pool_for_evaluation_only") is True
            ),
            "label_missing": sum(
                1 for row in candidate_rows if row.get("goal_validity_label_join_available") is not True
            ),
        },
        "baseline_policy_counts": baseline_counts,
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
        "added_evidence_travel_cost_m_stats": number_stats(
            row.get("added_evidence_travel_cost_m") for row in request_rows
        ),
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "evaluation_join_gate": gate,
        "evaluation_join_gate_passed": join_gate_passed,
        "active_reobservation_promotion_gate_passed": False,
        "promotion_gate_attempted": True,
        "promotion_gate_primary_failure_conditions": [
            condition
            for condition, count_key in (
                ("post_action_evidence_conflict_requires_non_gt_arbitration", "evidence_conflict_blocks_promotion_rows"),
                ("post_action_evidence_missing", "evidence_missing_blocks_promotion_rows"),
                (
                    "wrong_goal_reduction_only_by_evidence_availability",
                    "wrong_goal_reduction_only_by_evidence_availability_rows",
                ),
            )
            if actual_counts[count_key] > 0
        ],
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": primary_blocker,
        "next_task": "freeze_post_action_evidence_conflict_and_missing_resolution_contract",
        "interpretation": {
            "fact": (
                "The materializer joins frozen post-action evidence rows to evaluation-only baseline, "
                "candidate-label, wrong-goal, wasted-path, and map/pose fields on the same 50 rows."
            ),
            "agent_inference": (
                "The join is measurable and action-safe, but promotion remains blocked because primary evidence "
                "is conflicted or missing and evidence availability alone is not goal validity."
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
            "primary_candidate_evidence_targets": summary.get("primary_candidate_evidence_targets"),
            "baseline_rows": summary.get("baseline_rows"),
            "promotion_probe_rows": summary.get("promotion_probe_rows"),
            "failure_rows": summary.get("failure_rows"),
            "request_evidence_available_rows": summary.get("request_evidence_available_rows"),
            "request_evidence_conflicted_rows": summary.get("request_evidence_conflicted_rows"),
            "request_evidence_missing_rows": summary.get("request_evidence_missing_rows"),
            "candidate_support_evidence_rows": summary.get("candidate_support_evidence_rows"),
            "candidate_contradiction_evidence_rows": summary.get("candidate_contradiction_evidence_rows"),
            "candidate_conflict_evidence_rows": summary.get("candidate_conflict_evidence_rows"),
            "candidate_missing_evidence_rows": summary.get("candidate_missing_evidence_rows"),
            "wrong_goal_reduction_only_by_evidence_availability_rows": summary.get(
                "wrong_goal_reduction_only_by_evidence_availability_rows"
            ),
            "evidence_conflict_blocks_promotion_rows": summary.get("evidence_conflict_blocks_promotion_rows"),
            "evidence_missing_blocks_promotion_rows": summary.get("evidence_missing_blocks_promotion_rows"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "request_evidence_status_counts": summary.get("request_evidence_status_counts"),
        "primary_request_evidence_status_counts": summary.get("primary_request_evidence_status_counts"),
        "candidate_evidence_status_counts": summary.get("candidate_evidence_status_counts"),
        "primary_candidate_evidence_status_counts": summary.get("primary_candidate_evidence_status_counts"),
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
                "-e PYTHONPATH=/workspace/src "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m py_compile "
                "src/h001_runtime/"
                "materialize_post_action_evidence_evaluation_join.py"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/src "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_post_action_evidence_evaluation_join"
            ),
            (
                "jq '{status, request_rows, primary_target_rows, request_evidence_available_rows, "
                "request_evidence_conflicted_rows, request_evidence_missing_rows, "
                "evaluation_join_gate_passed, active_reobservation_promotion_gate_passed, "
                "primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "post_action_evidence_rows_frozen_before_labels": True,
            "same_row_comparison_required": True,
            "same_candidate_pool_required": True,
            "same_reobservation_budget_required": True,
            "commit_based_wrong_goal_required": True,
            "evidence_available_not_goal_validity": True,
            "evidence_conflict_preserved": True,
            "evidence_missing_preserved": True,
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

    evidence_request_rows = load_jsonl(Path(str(source["post_action_evidence_request_rows"])))
    evidence_candidate_rows = load_jsonl(Path(str(source["post_action_evidence_candidate_rows"])))
    previous_request_rows = load_jsonl(Path(str(source["previous_evaluation_join_request_rows"])))
    previous_candidate_rows = load_jsonl(Path(str(source["previous_evaluation_join_candidate_rows"])))
    previous_baseline_rows = load_jsonl(Path(str(source["previous_evaluation_join_baseline_rows"])))

    previous_eval_rows_by_key = index_one(previous_request_rows)
    previous_eval_rows_by_candidate = index_candidates(previous_candidate_rows)
    baselines_by_key = policy_lookup(previous_baseline_rows)

    request_rows = materialize_request_rows(
        evidence_rows=evidence_request_rows,
        previous_eval_rows_by_key=previous_eval_rows_by_key,
        baselines_by_key=baselines_by_key,
    )
    candidate_rows = materialize_candidate_rows(
        evidence_rows=evidence_candidate_rows,
        previous_eval_rows_by_candidate=previous_eval_rows_by_candidate,
    )
    baseline_rows = materialize_baseline_rows(previous_baseline_rows)
    promotion_rows = materialize_promotion_probe_rows(request_rows)
    failure_rows = materialize_failure_rows(request_rows)
    forbidden_keys = scan_forbidden_action_inputs([*evidence_request_rows, *evidence_candidate_rows])

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
        raise SystemExit("post-action evidence evaluation join gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize the post-action evidence evaluation join.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
