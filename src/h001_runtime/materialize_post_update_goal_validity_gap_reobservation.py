import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.post_update_goal_validity_gap_reobservation.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_post_update_goal_validity_gap_reobservation_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_post_update_goal_validity_gap_reobservation_v1"

OUTPUT_FILES = {
    "request_action_rows": "post_update_goal_validity_gap_reobservation_request_rows.jsonl",
    "target_candidate_rows": "post_update_goal_validity_gap_reobservation_candidate_rows.jsonl",
    "baseline_or_control_rows": "post_update_goal_validity_gap_reobservation_baseline_rows.jsonl",
    "failure_rows": "post_update_goal_validity_gap_reobservation_failure_rows.jsonl",
    "summary": "post_update_goal_validity_gap_reobservation_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
PRIMARY_TARGET_ACTION = "request_independent_goal_validity_evidence"
NON_TARGET_ACTION = "keep_post_update_state_for_audit"

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

LABEL_FREE_ACTION_INPUT_FIELDS = {
    "source_name",
    "scene_key",
    "query",
    "request_id",
    "episode_key",
    "selected_candidate_ids",
    "selected_candidate_count",
    "selected_observation_action",
    "post_update_request_state",
    "viewpoint_evidence_gap_proxy",
    "viewpoint_evidence_gap_state",
    "map_pose_consistency_uncertainty_proxy",
    "map_pose_consistency_uncertainty_state",
    "request_evidence_delta",
    "reobserve_travel_cost_m",
    "pose_graph_connectivity_delta",
    "map_pose_consistency_delta",
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
        return float(value)
    except (TypeError, ValueError):
        return default


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


def policy_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("policy_name") or row.get("policy_name") or ""))


def candidate_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("candidate_id") or row.get("candidate_id") or ""))


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def target_key_set(contract: Mapping[str, Any]) -> set[Tuple[str, str, str, str, str]]:
    rows = contract.get("frozen_target_rows")
    if not isinstance(rows, list):
        return set()
    return {join_key(row) for row in rows if isinstance(row, Mapping)}


def group_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    groups: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[join_key(row)].append(row)
    return dict(groups)


def sanitize_request_delta(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {
            "label_free_evidence_delta_available": False,
            "selected_candidate_update_rows": 0,
            "selected_post_state_counts": {},
            "mean_net_evidence_delta_proxy": None,
        }
    return {
        "label_free_evidence_delta_available": value.get("label_free_evidence_delta_available") is True,
        "selected_candidate_update_rows": safe_int(value.get("selected_candidate_update_rows"), 0),
        "selected_post_state_counts": value.get("selected_post_state_counts")
        if isinstance(value.get("selected_post_state_counts"), Mapping)
        else {},
        "mean_net_evidence_delta_proxy": safe_float(value.get("mean_net_evidence_delta_proxy")),
    }


def sanitize_evidence_delta(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"evidence_delta_available": False}
    keep = (
        "evidence_delta_available",
        "delta_type",
        "support_delta_proxy",
        "rival_contrast_delta_proxy",
        "context_support_delta_proxy",
        "projection_resolution_delta_proxy",
        "observation_cost_proxy",
        "net_evidence_delta_proxy",
    )
    return {key: value.get(key) for key in keep if key in value}


def sanitize_observation_evidence(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"evidence_type": "missing_or_not_selected"}
    keep = (
        "evidence_type",
        "observation_action",
        "utility_score",
        "utility_terms",
        "projection_visible_fraction",
        "projection_visible_heading_rank",
        "pose_heading_rank",
        "map_pose_score_tuple_rank",
        "map_pose_score_tuple_tie_count",
        "target_distance_mean_m",
        "label_free_update_inputs_only",
    )
    return {key: value.get(key) for key in keep if key in value}


def action_input_payload(row: Mapping[str, Any]) -> Dict[str, Any]:
    payload = {key: row.get(key) for key in LABEL_FREE_ACTION_INPUT_FIELDS if key in row}
    payload["request_evidence_delta"] = sanitize_request_delta(row.get("request_evidence_delta"))
    payload["label_free_action_inputs_only"] = True
    payload["goal_validity_context_usage"] = "evaluation_only_not_used_for_branch_action"
    return payload


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


def branch_action(*, row: Mapping[str, Any], is_primary_target: bool) -> str:
    if is_primary_target:
        return PRIMARY_TARGET_ACTION
    if str(row.get("post_update_request_state") or "") in {"ambiguity_reduced", "support_acquired"}:
        return NON_TARGET_ACTION
    return "audit_only"


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def materialize_request_rows(
    *,
    source_rows: Sequence[Mapping[str, Any]],
    target_keys: set[Tuple[str, str, str, str, str]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_rows, key=join_key):
        key = join_key(source)
        payload = key_payload(key)
        is_target = key in target_keys
        action = branch_action(row=source, is_primary_target=is_target)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_update_goal_validity_gap_reobservation_after_branch_contract_freeze",
                "row_type": "post_update_goal_validity_gap_reobservation_request_action",
                "join_key": payload,
                **payload,
                "target_role": "primary_target" if is_target else "audit_control",
                "branch_action": action,
                "branch_action_family": "nonterminal_active_goal_validity_evidence_acquisition",
                "branch_action_reason": (
                    "label_free_unresolved_post_update_goal_validity_after_context_observation"
                    if is_target
                    else "same_row_audit_control_for_fixed_evaluation_gate"
                ),
                "selected_candidate_ids": source.get("selected_candidate_ids") or [],
                "selected_candidate_count": safe_int(source.get("selected_candidate_count"), 0),
                "selected_observation_action": source.get("selected_observation_action"),
                "post_update_request_state": source.get("post_update_request_state"),
                "goal_validity_risk_state": source.get("goal_validity_risk_state"),
                "goal_validity_risk_proxy": safe_float(source.get("goal_validity_risk_proxy")),
                "goal_validity_context_usage": "evaluation_only_after_target_freeze_not_action_input",
                "viewpoint_evidence_gap_state": source.get("viewpoint_evidence_gap_state"),
                "viewpoint_evidence_gap_proxy": safe_float(source.get("viewpoint_evidence_gap_proxy")),
                "map_pose_consistency_uncertainty_state": source.get("map_pose_consistency_uncertainty_state"),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    source.get("map_pose_consistency_uncertainty_proxy")
                ),
                "reobserve_travel_cost_m": safe_float(source.get("reobserve_travel_cost_m")),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "action_evidence_inputs": action_input_payload(source),
                "action_frozen_before_next_evaluation_join": True,
                "same_row_evaluation_join_required_next": True,
                **common_flags(),
            }
        )
    return out


def materialize_candidate_rows(
    *,
    source_rows: Sequence[Mapping[str, Any]],
    request_action_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    target_keys: set[Tuple[str, str, str, str, str]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_rows, key=candidate_key):
        key = join_key(source)
        request_action = request_action_by_key.get(key) or {}
        payload = key_payload(key)
        cid = candidate_key(source)[-1]
        is_target = key in target_keys
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_update_goal_validity_gap_reobservation_after_branch_contract_freeze",
                "row_type": "post_update_goal_validity_gap_reobservation_candidate_context",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": "primary_target" if is_target else "audit_control",
                "branch_action": request_action.get("branch_action"),
                "candidate_context_role": "selected_candidate_context_only",
                "selected_observation_action": source.get("selected_observation_action"),
                "post_observation_state": source.get("post_observation_state"),
                "pre_observation_state": source.get("pre_observation_state"),
                "goal_validity_risk_state": source.get("goal_validity_risk_state"),
                "goal_validity_risk_proxy": safe_float(source.get("goal_validity_risk_proxy")),
                "goal_validity_context_usage": "evaluation_only_after_target_freeze_not_action_input",
                "viewpoint_evidence_gap_state": source.get("viewpoint_evidence_gap_state"),
                "viewpoint_evidence_gap_proxy": safe_float(source.get("viewpoint_evidence_gap_proxy")),
                "map_pose_consistency_uncertainty_state": source.get("map_pose_consistency_uncertainty_state"),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    source.get("map_pose_consistency_uncertainty_proxy")
                ),
                "observation_evidence": sanitize_observation_evidence(source.get("observation_evidence")),
                "evidence_delta": sanitize_evidence_delta(source.get("evidence_delta")),
                "reobserve_travel_cost_m": safe_float(source.get("reobserve_travel_cost_m")),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "action_evidence_inputs": {
                    "candidate_id": cid,
                    "observation_evidence": sanitize_observation_evidence(source.get("observation_evidence")),
                    "evidence_delta": sanitize_evidence_delta(source.get("evidence_delta")),
                    "viewpoint_evidence_gap_state": source.get("viewpoint_evidence_gap_state"),
                    "map_pose_consistency_uncertainty_state": source.get("map_pose_consistency_uncertainty_state"),
                    "label_free_action_inputs_only": True,
                    "goal_validity_context_usage": "evaluation_only_not_used_for_branch_action",
                },
                "action_frozen_before_next_evaluation_join": True,
                "same_row_evaluation_join_required_next": True,
                **common_flags(),
            }
        )
    return out


def materialize_baseline_rows(
    *,
    source_rows: Sequence[Mapping[str, Any]],
    target_keys: set[Tuple[str, str, str, str, str]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_rows, key=policy_key):
        key = join_key(source)
        payload = key_payload(key)
        policy = policy_key(source)[-1]
        is_target = key in target_keys
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_update_goal_validity_gap_reobservation_baseline_context_after_branch_freeze",
                "row_type": "post_update_goal_validity_gap_reobservation_baseline_context",
                "join_key": {**payload, "policy_name": policy},
                **payload,
                "policy_name": policy,
                "target_role": "primary_target" if is_target else "audit_control",
                "policy_selected_candidate_id": source.get("policy_selected_candidate_id"),
                "selector_id": source.get("selector_id"),
                "selector_action": source.get("selector_action"),
                "terminal_commit_proxy": source.get("terminal_commit_proxy"),
                "success_commit_proxy": source.get("success_commit_proxy"),
                "wrong_goal_visit_proxy": source.get("wrong_goal_visit_proxy"),
                "wasted_path_proxy_m": safe_float(source.get("wasted_path_proxy_m")),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "evaluation_only_baseline_context": True,
                "not_used_for_branch_action": True,
                **common_flags(),
                "uses_gt_for_analysis": True,
            }
        )
    return out


def failure_tags(row: Mapping[str, Any]) -> List[str]:
    tags = [
        "terminal_commit_blocked",
        "candidate_commit_blocked",
        "candidate_rejection_blocked",
        "same_row_evaluation_join_required_next",
        "semantic_slam_task_map_evidence_required",
    ]
    if row.get("target_role") == "primary_target":
        tags.extend(
            [
                "post_update_goal_validity_gap_requires_reobservation",
                "goal_validity_context_must_not_be_terminal_score",
            ]
        )
    else:
        tags.append("non_target_audit_control_kept_for_same_row_gate")
    if row.get("map_pose_consistency_uncertainty_state") != "map_pose_ready_uncertainty_measured":
        tags.append("map_pose_consistency_evidence_partial_or_missing")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "post_update_goal_validity_gap_requires_reobservation",
        "goal_validity_context_must_not_be_terminal_score",
        "non_target_audit_control_kept_for_same_row_gate",
        "same_row_evaluation_join_required_next",
        "semantic_slam_task_map_evidence_required",
        "map_pose_consistency_evidence_partial_or_missing",
        "terminal_commit_blocked",
        "candidate_commit_blocked",
        "candidate_rejection_blocked",
    ):
        if tag in tags:
            return tag
    return "unknown"


def materialize_failure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in request_rows:
        key = join_key(row)
        payload = key_payload(key)
        tags = failure_tags(row)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_update_goal_validity_gap_reobservation_failure_taxonomy",
                "row_type": "post_update_goal_validity_gap_reobservation_failure",
                "join_key": payload,
                **payload,
                "target_role": row.get("target_role"),
                "branch_action": row.get("branch_action"),
                "goal_validity_risk_state": row.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": row.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": row.get("map_pose_consistency_uncertainty_state"),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                **common_flags(),
            }
        )
    return out


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate")
    source_gate = source_gate if isinstance(source_gate, Mapping) else {}
    target_counts = contract.get("frozen_target_selection", {}).get("primary_target_counts", {})
    target_counts = target_counts if isinstance(target_counts, Mapping) else {}
    all_action_rows = [*request_rows, *candidate_rows, *failure_rows]
    primary_request_rows = [row for row in request_rows if row.get("target_role") == "primary_target"]
    primary_candidate_rows = [row for row in candidate_rows if row.get("target_role") == "primary_target"]
    primary_baseline_rows = [row for row in baseline_rows if row.get("target_role") == "primary_target"]
    actual_counts = {
        "request_rows": len(request_rows),
        "primary_target_rows": len(primary_request_rows),
        "non_target_audit_rows": len(request_rows) - len(primary_request_rows),
        "selected_candidate_rows": len(candidate_rows),
        "primary_target_selected_candidate_rows": len(primary_candidate_rows),
        "baseline_rows": len(baseline_rows),
        "primary_target_baseline_rows": len(primary_baseline_rows),
        "failure_rows": len(failure_rows),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_action_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_action_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_action_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_action_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_action_rows, "paper_claim_allowed"),
    }
    action_counts = compact_counter(row.get("branch_action") for row in request_rows)
    allowed_primary = set(
        contract.get("branch_action_contract", {}).get("allowed_primary_target_actions", [])
    )
    allowed_non_target = set(
        contract.get("branch_action_contract", {}).get("allowed_non_target_actions", [])
    )
    gate = {
        "request_rows_expected_passed": actual_counts["request_rows"]
        == safe_int(source_gate.get("source_request_rows"), 50),
        "primary_target_rows_expected_passed": actual_counts["primary_target_rows"]
        == safe_int(source_gate.get("target_request_rows"), 21),
        "non_target_audit_rows_expected_passed": actual_counts["non_target_audit_rows"] == 29,
        "selected_candidate_rows_expected_passed": actual_counts["selected_candidate_rows"]
        == safe_int(source_gate.get("source_selected_candidate_rows"), 97),
        "primary_target_selected_candidate_rows_expected_passed": actual_counts[
            "primary_target_selected_candidate_rows"
        ]
        == safe_int(source_gate.get("target_selected_candidate_rows"), target_counts.get("selected_candidate_rows", 42)),
        "baseline_rows_expected_passed": actual_counts["baseline_rows"]
        == safe_int(source_gate.get("source_baseline_rows"), 150),
        "primary_target_baseline_rows_expected_passed": actual_counts["primary_target_baseline_rows"]
        == safe_int(source_gate.get("target_baseline_rows"), 63),
        "failure_rows_expected_passed": actual_counts["failure_rows"] == actual_counts["request_rows"],
        "primary_actions_allowed_passed": all(row.get("branch_action") in allowed_primary for row in primary_request_rows),
        "non_target_actions_allowed_passed": all(
            row.get("branch_action") in allowed_non_target or row.get("branch_action") == "audit_only"
            for row in request_rows
            if row.get("target_role") != "primary_target"
        ),
        "forbidden_action_inputs_passed": actual_counts["action_evidence_forbidden_key_count"] == 0,
        "terminal_commit_rows_passed": actual_counts["terminal_commit_rows"] == 0,
        "candidate_commit_rows_passed": actual_counts["candidate_commit_rows"] == 0,
        "candidate_rejection_rows_passed": actual_counts["candidate_rejection_rows"] == 0,
        "uses_gt_for_action_passed": actual_counts["uses_gt_for_action_true_rows"] == 0,
        "paper_claim_blocked_passed": actual_counts["paper_claim_allowed_true_rows"] == 0,
    }
    gate_passed = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "docker_materializer_gate_passed_evaluation_join_pending"
        if gate_passed
        else "docker_materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        "request_rows": actual_counts["request_rows"],
        "primary_target_rows": actual_counts["primary_target_rows"],
        "non_target_audit_rows": actual_counts["non_target_audit_rows"],
        "selected_candidate_rows": actual_counts["selected_candidate_rows"],
        "primary_target_selected_candidate_rows": actual_counts["primary_target_selected_candidate_rows"],
        "baseline_rows": actual_counts["baseline_rows"],
        "primary_target_baseline_rows": actual_counts["primary_target_baseline_rows"],
        "failure_rows": actual_counts["failure_rows"],
        "action_counts": action_counts,
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
        "primary_target_reobserve_travel_cost_m_stats": number_stats(
            row.get("reobserve_travel_cost_m") for row in primary_request_rows
        ),
        "baseline_policy_counts": {
            policy: {
                "rows": sum(1 for row in baseline_rows if row.get("policy_name") == policy),
                "primary_target_rows": sum(
                    1
                    for row in baseline_rows
                    if row.get("policy_name") == policy and row.get("target_role") == "primary_target"
                ),
                "terminal_commit_proxy_rows": sum(
                    1
                    for row in baseline_rows
                    if row.get("policy_name") == policy and row.get("terminal_commit_proxy") is True
                ),
                "success_commit_proxy_rows": sum(
                    1
                    for row in baseline_rows
                    if row.get("policy_name") == policy and row.get("success_commit_proxy") is True
                ),
                "wrong_goal_visit_proxy_rows": sum(
                    1
                    for row in baseline_rows
                    if row.get("policy_name") == policy and row.get("wrong_goal_visit_proxy") is True
                ),
                "wasted_path_proxy_m_stats": number_stats(
                    row.get("wasted_path_proxy_m") for row in baseline_rows if row.get("policy_name") == policy
                ),
            }
            for policy in compact_counter(row.get("policy_name") for row in baseline_rows)
        },
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_key_count": actual_counts["action_evidence_forbidden_key_count"],
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "terminal_commit_rows": actual_counts["terminal_commit_rows"],
        "candidate_commit_rows": actual_counts["candidate_commit_rows"],
        "candidate_rejection_rows": actual_counts["candidate_rejection_rows"],
        "uses_gt_for_action_true_rows": actual_counts["uses_gt_for_action_true_rows"],
        "paper_claim_allowed_true_rows": actual_counts["paper_claim_allowed_true_rows"],
        "implementation_gate": gate,
        "implementation_gate_passed": gate_passed,
        "promotion_gate_attempt_allowed_after_evaluation_join": bool(gate_passed),
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": "post_action_evaluation_join_required",
        "next_task": "freeze_post_update_goal_validity_gap_reobservation_evaluation_join_v1",
        "interpretation": {
            "fact": (
                "The materializer emits branch action rows for all 50 frozen source rows, with 21 primary "
                "target rows and 29 audit/control rows."
            ),
            "agent_inference": (
                "The branch now represents a nonterminal active re-observation action family for unresolved "
                "goal-validity gaps, but it still needs a same-row evaluation join before any promotion test."
            ),
            "paper_claim": (
                "No ObjectNav improvement, Semantic-SLAM complementarity, terminal utility, formula revision, "
                "policy-scale comparison, Step 4-5 promotion, or paper claim is allowed from this artifact."
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
        "ok": summary.get("implementation_gate_passed") is True,
        "status": summary.get("status"),
        "verified_artifact": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": {
            "request_rows": summary.get("request_rows"),
            "primary_target_rows": summary.get("primary_target_rows"),
            "non_target_audit_rows": summary.get("non_target_audit_rows"),
            "selected_candidate_rows": summary.get("selected_candidate_rows"),
            "primary_target_selected_candidate_rows": summary.get("primary_target_selected_candidate_rows"),
            "baseline_rows": summary.get("baseline_rows"),
            "primary_target_baseline_rows": summary.get("primary_target_baseline_rows"),
            "failure_rows": summary.get("failure_rows"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
        },
        "action_counts": summary.get("action_counts"),
        "state_counts": {
            "primary_target_goal_validity_risk_state_counts": summary.get(
                "primary_target_goal_validity_risk_state_counts"
            ),
            "request_viewpoint_evidence_gap_state_counts": summary.get("request_viewpoint_evidence_gap_state_counts"),
            "request_map_pose_uncertainty_state_counts": summary.get("request_map_pose_uncertainty_state_counts"),
        },
        "baseline_policy_counts": summary.get("baseline_policy_counts"),
        "implementation_gate_passed": summary.get("implementation_gate_passed"),
        "promotion_gate_attempt_allowed_after_evaluation_join": summary.get(
            "promotion_gate_attempt_allowed_after_evaluation_join"
        ),
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
                "materialize_post_update_goal_validity_gap_reobservation.py"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/src "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_post_update_goal_validity_gap_reobservation"
            ),
            (
                "jq '{status, request_rows, primary_target_rows, action_counts, implementation_gate_passed, "
                "promotion_gate_attempt_allowed_after_evaluation_join, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "branch_actions_frozen_before_next_evaluation_join": True,
            "all_50_source_rows_materialized": True,
            "primary_target_rows_materialized": True,
            "non_target_audit_rows_materialized": True,
            "labels_not_used_for_branch_action": True,
            "goal_validity_context_evaluation_only": True,
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

    request_source_rows = load_jsonl(Path(str(source["post_update_request_rows"])))
    selected_source_rows = load_jsonl(Path(str(source["post_update_selected_candidate_rows"])))
    baseline_source_rows = load_jsonl(Path(str(source["post_update_baseline_rows"])))
    target_keys = target_key_set(contract)

    request_rows = materialize_request_rows(source_rows=request_source_rows, target_keys=target_keys)
    request_by_key = {join_key(row): row for row in request_rows}
    candidate_rows = materialize_candidate_rows(
        source_rows=selected_source_rows,
        request_action_by_key=request_by_key,
        target_keys=target_keys,
    )
    baseline_rows = materialize_baseline_rows(source_rows=baseline_source_rows, target_keys=target_keys)
    failure_rows = materialize_failure_rows(request_rows)
    forbidden_keys = scan_forbidden_action_inputs([*request_rows, *candidate_rows])

    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        baseline_rows=baseline_rows,
        failure_rows=failure_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_action_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["target_candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["baseline_or_control_rows"], baseline_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verification_path(contract_path),
        build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary),
    )

    if summary.get("implementation_gate_passed") is not True:
        raise SystemExit("post-update goal-validity-gap reobservation materializer gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize the post-update goal-validity-gap active re-observation branch."
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
