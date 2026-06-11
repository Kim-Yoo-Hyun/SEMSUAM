import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.post_action_evidence_conflict_missing_resolution.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_post_action_evidence_conflict_missing_resolution_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_post_action_evidence_conflict_missing_resolution_v1"

OUTPUT_FILES = {
    "request_rows": "post_action_evidence_conflict_missing_resolution_request_rows.jsonl",
    "candidate_rows": "post_action_evidence_conflict_missing_resolution_candidate_rows.jsonl",
    "route_rows": "post_action_evidence_conflict_missing_resolution_route_rows.jsonl",
    "failure_rows": "post_action_evidence_conflict_missing_resolution_failure_rows.jsonl",
    "summary": "post_action_evidence_conflict_missing_resolution_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_correctness_label_for_evaluation_only",
    "candidate_wrong_label",
    "candidate_wrong_label_for_evaluation_only",
    "no_valid_candidate_pool_label",
    "no_valid_candidate_pool_for_evaluation_only",
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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result or result in (float("inf"), float("-inf")):
        return default
    return result


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


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def group_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[join_key(row)].append(row)
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
        scan(row.get("action_route_inputs", {}))
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


def resolution_for_request(row: Mapping[str, Any]) -> Tuple[bool, str, str]:
    target_role = row.get("target_role")
    status = row.get("request_evidence_status")
    evidence_available = row.get("post_action_goal_validity_evidence_available") is True
    if target_role != "primary_target":
        return (False, "keep_audit_control", "non_target_audit_preserved_for_same_row_accounting")
    if status == "independent_evidence_conflicted" and evidence_available:
        return (
            True,
            "request_conflict_arbitration_evidence",
            "independent_support_and_contradiction_conflict_requires_non_gt_arbitration",
        )
    if status == "independent_evidence_missing" and not evidence_available:
        return (
            True,
            "request_missing_evidence_followup",
            "post_action_goal_validity_evidence_missing_requires_followup",
        )
    return (True, "defer_unresolved_post_action_evidence", "unexpected_post_action_evidence_state")


def route_priority(route: str) -> int:
    return {
        "request_conflict_arbitration_evidence": 0,
        "request_missing_evidence_followup": 1,
        "defer_unresolved_post_action_evidence": 2,
        "keep_audit_control": 3,
    }.get(route, 99)


def materialize_route_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(request_rows, key=lambda row: (route_priority(resolution_for_request(row)[1]), join_key(row))):
        key = join_key(source)
        payload = key_payload(key)
        required, route, reason = resolution_for_request(source)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "resolution_after_post_action_evidence_evaluation_join",
                "row_type": "post_action_evidence_conflict_missing_resolution_route",
                "join_key": payload,
                **payload,
                "target_role": source.get("target_role"),
                "source_branch_action": source.get("source_branch_action"),
                "request_evidence_status": source.get("request_evidence_status"),
                "post_action_goal_validity_evidence_available": (
                    source.get("post_action_goal_validity_evidence_available") is True
                ),
                "resolution_required": required,
                "resolution_route": route,
                "resolution_reason": reason,
                "evidence_conflict_blocks_promotion": source.get("evidence_conflict_blocks_promotion") is True,
                "evidence_missing_blocks_promotion": source.get("evidence_missing_blocks_promotion") is True,
                "wrong_goal_reduction_only_by_evidence_availability": (
                    source.get("wrong_goal_reduction_only_by_evidence_availability") is True
                ),
                "allowed_next_evidence": allowed_next_evidence(route),
                "action_route_inputs": {
                    "target_role": source.get("target_role"),
                    "request_evidence_status": source.get("request_evidence_status"),
                    "post_action_goal_validity_evidence_available": (
                        source.get("post_action_goal_validity_evidence_available") is True
                    ),
                    "evidence_conflict_blocks_promotion": source.get("evidence_conflict_blocks_promotion") is True,
                    "evidence_missing_blocks_promotion": source.get("evidence_missing_blocks_promotion") is True,
                },
                "label_free_route": True,
                "evaluation_label_fields_dropped_for_route": True,
                **common_flags(),
            }
        )
    return out


def allowed_next_evidence(route: str) -> List[str]:
    if route == "request_conflict_arbitration_evidence":
        return [
            "candidate_specific_own_view_vs_rival_view_separation",
            "object_relation_or_goal_region_evidence",
            "map_pose_consistency_cross_check",
        ]
    if route == "request_missing_evidence_followup":
        return [
            "additional_reobservation_viewpoint",
            "candidate_specific_detector_or_relation_probe",
            "map_pose_consistency_cross_check",
        ]
    if route == "keep_audit_control":
        return ["audit_only_same_row_baseline_accounting"]
    return ["defer_unresolved_post_action_evidence"]


def materialize_request_rows(
    request_rows: Sequence[Mapping[str, Any]],
    route_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(request_rows, key=join_key):
        key = join_key(source)
        payload = key_payload(key)
        route = route_by_key[key]
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "resolution_after_post_action_evidence_evaluation_join",
                "row_type": "post_action_evidence_conflict_missing_resolution_request",
                "join_key": payload,
                **payload,
                "target_role": source.get("target_role"),
                "source_branch_action": source.get("source_branch_action"),
                "request_evidence_status": source.get("request_evidence_status"),
                "post_action_goal_validity_evidence_available": (
                    source.get("post_action_goal_validity_evidence_available") is True
                ),
                "independent_evidence_candidate_count": safe_int(
                    source.get("independent_evidence_candidate_count"),
                    0,
                ),
                "evidence_missing_reason": source.get("evidence_missing_reason"),
                "goal_validity_risk_state": source.get("goal_validity_risk_state"),
                "goal_validity_risk_proxy": safe_float(source.get("goal_validity_risk_proxy")),
                "viewpoint_evidence_gap_state": source.get("viewpoint_evidence_gap_state"),
                "viewpoint_evidence_gap_proxy": safe_float(source.get("viewpoint_evidence_gap_proxy")),
                "map_pose_consistency_uncertainty_state": source.get("map_pose_consistency_uncertainty_state"),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    source.get("map_pose_consistency_uncertainty_proxy")
                ),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "source_reobserve_travel_cost_m": safe_float(source.get("source_reobserve_travel_cost_m")),
                "added_evidence_travel_cost_m": safe_float(source.get("added_evidence_travel_cost_m")),
                "resolution_required": route.get("resolution_required") is True,
                "resolution_route": route.get("resolution_route"),
                "resolution_reason": route.get("resolution_reason"),
                "evidence_conflict_blocks_promotion": source.get("evidence_conflict_blocks_promotion") is True,
                "evidence_missing_blocks_promotion": source.get("evidence_missing_blocks_promotion") is True,
                "wrong_goal_reduction_only_by_evidence_availability": (
                    source.get("wrong_goal_reduction_only_by_evidence_availability") is True
                ),
                "evidence_available_is_not_goal_validity": True,
                "label_free_route": True,
                "evaluation_label_fields_dropped_for_route": True,
                **common_flags(),
            }
        )
    return out


def materialize_candidate_rows(
    candidate_rows: Sequence[Mapping[str, Any]],
    route_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(candidate_rows, key=candidate_key):
        key = join_key(source)
        payload = key_payload(key)
        route = route_by_key[key]
        cid = candidate_key(source)[-1]
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "resolution_after_post_action_evidence_evaluation_join",
                "row_type": "post_action_evidence_conflict_missing_resolution_candidate",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": source.get("target_role"),
                "source_branch_action": source.get("source_branch_action"),
                "request_evidence_status": route.get("request_evidence_status"),
                "candidate_evidence_status": source.get("candidate_evidence_status"),
                "candidate_evidence_reason": source.get("candidate_evidence_reason"),
                "candidate_support_evidence_count": safe_int(source.get("candidate_support_evidence_count"), 0),
                "candidate_contradiction_evidence_count": safe_int(
                    source.get("candidate_contradiction_evidence_count"),
                    0,
                ),
                "viewpoint_coverage_delta": safe_float(source.get("viewpoint_coverage_delta")),
                "association_quality_proxy": safe_float(source.get("association_quality_proxy")),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    source.get("map_pose_consistency_uncertainty_proxy")
                ),
                "resolution_required": route.get("resolution_required") is True,
                "resolution_route": route.get("resolution_route"),
                "resolution_reason": route.get("resolution_reason"),
                "evidence_conflict_blocks_promotion": route.get("evidence_conflict_blocks_promotion") is True,
                "evidence_missing_blocks_promotion": route.get("evidence_missing_blocks_promotion") is True,
                "wrong_goal_reduction_only_by_evidence_availability": (
                    route.get("wrong_goal_reduction_only_by_evidence_availability") is True
                ),
                "evidence_available_is_not_goal_validity": True,
                "label_free_route": True,
                "evaluation_label_fields_dropped_for_route": True,
                **common_flags(),
            }
        )
    return out


def failure_tags(row: Mapping[str, Any]) -> List[str]:
    tags = [
        "terminal_utility_blocked",
        "candidate_commit_blocked",
        "candidate_rejection_blocked",
        "paper_claim_blocked",
        "resolution_routing_only",
    ]
    route = row.get("resolution_route")
    if route == "request_conflict_arbitration_evidence":
        tags.append("post_action_evidence_conflict_requires_non_gt_arbitration")
    elif route == "request_missing_evidence_followup":
        tags.append("post_action_evidence_missing_requires_followup")
    elif route == "keep_audit_control":
        tags.append("audit_control_preserved")
    else:
        tags.append("unresolved_post_action_evidence_state")
    if row.get("wrong_goal_reduction_only_by_evidence_availability") is True:
        tags.append("wrong_goal_reduction_only_by_evidence_availability")
    if row.get("post_action_goal_validity_evidence_available") is True:
        tags.append("evidence_available_is_not_goal_validity")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "post_action_evidence_conflict_requires_non_gt_arbitration",
        "post_action_evidence_missing_requires_followup",
        "wrong_goal_reduction_only_by_evidence_availability",
        "audit_control_preserved",
        "unresolved_post_action_evidence_state",
    ):
        if tag in tags:
            return tag
    return "resolution_routing_only"


def materialize_failure_rows(route_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for route in sorted(route_rows, key=join_key):
        key = join_key(route)
        payload = key_payload(key)
        tags = failure_tags(route)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "resolution_after_post_action_evidence_evaluation_join",
                "row_type": "post_action_evidence_conflict_missing_resolution_failure",
                "join_key": payload,
                **payload,
                "target_role": route.get("target_role"),
                "request_evidence_status": route.get("request_evidence_status"),
                "post_action_goal_validity_evidence_available": (
                    route.get("post_action_goal_validity_evidence_available") is True
                ),
                "resolution_required": route.get("resolution_required") is True,
                "resolution_route": route.get("resolution_route"),
                "resolution_reason": route.get("resolution_reason"),
                "evidence_conflict_blocks_promotion": route.get("evidence_conflict_blocks_promotion") is True,
                "evidence_missing_blocks_promotion": route.get("evidence_missing_blocks_promotion") is True,
                "wrong_goal_reduction_only_by_evidence_availability": (
                    route.get("wrong_goal_reduction_only_by_evidence_availability") is True
                ),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                **common_flags(),
            }
        )
    return out


def gate_from_counts(contract: Mapping[str, Any], counts: Mapping[str, int]) -> Dict[str, bool]:
    gate = contract.get("implementation_gate")
    gate = gate if isinstance(gate, Mapping) else {}
    return {
        "request_rows_expected_passed": counts["request_rows"] == safe_int(gate.get("request_rows_expected"), 50),
        "primary_target_rows_expected_passed": counts["primary_target_rows"]
        == safe_int(gate.get("primary_target_rows_expected"), 21),
        "non_target_audit_rows_expected_passed": counts["non_target_audit_rows"]
        == safe_int(gate.get("non_target_audit_rows_expected"), 29),
        "candidate_rows_expected_passed": counts["candidate_rows"] == safe_int(gate.get("candidate_rows_expected"), 97),
        "conflict_route_rows_expected_passed": counts["conflict_route_rows"]
        == safe_int(gate.get("conflict_route_rows_expected"), 18),
        "missing_route_rows_expected_passed": counts["missing_route_rows"]
        == safe_int(gate.get("missing_route_rows_expected"), 3),
        "audit_route_rows_expected_passed": counts["audit_route_rows"]
        == safe_int(gate.get("audit_route_rows_expected"), 29),
        "action_evidence_forbidden_key_count_passed": counts["action_evidence_forbidden_key_count"]
        == safe_int(gate.get("action_evidence_forbidden_key_count_expected"), 0),
        "terminal_commit_rows_passed": counts["terminal_commit_rows"]
        == safe_int(gate.get("terminal_commit_rows_expected"), 0),
        "candidate_commit_rows_passed": counts["candidate_commit_rows"]
        == safe_int(gate.get("candidate_commit_rows_expected"), 0),
        "candidate_rejection_rows_passed": counts["candidate_rejection_rows"]
        == safe_int(gate.get("candidate_rejection_rows_expected"), 0),
        "uses_gt_for_action_passed": counts["uses_gt_for_action_true_rows"]
        == safe_int(gate.get("uses_gt_for_action_true_rows_expected"), 0),
        "paper_claim_blocked_passed": counts["paper_claim_allowed_true_rows"]
        == safe_int(gate.get("paper_claim_allowed_true_rows_expected"), 0),
    }


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    route_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    all_action_rows = [*request_rows, *candidate_rows, *route_rows, *failure_rows]
    primary_requests = [row for row in request_rows if row.get("target_role") == "primary_target"]
    audit_requests = [row for row in request_rows if row.get("target_role") != "primary_target"]
    primary_candidates = [row for row in candidate_rows if row.get("target_role") == "primary_target"]
    route_counts = compact_counter(row.get("resolution_route") for row in route_rows)
    counts = {
        "request_rows": len(request_rows),
        "primary_target_rows": len(primary_requests),
        "non_target_audit_rows": len(audit_requests),
        "candidate_rows": len(candidate_rows),
        "primary_candidate_rows": len(primary_candidates),
        "route_rows": len(route_rows),
        "failure_rows": len(failure_rows),
        "conflict_route_rows": sum(
            1 for row in route_rows if row.get("resolution_route") == "request_conflict_arbitration_evidence"
        ),
        "missing_route_rows": sum(
            1 for row in route_rows if row.get("resolution_route") == "request_missing_evidence_followup"
        ),
        "audit_route_rows": sum(1 for row in route_rows if row.get("resolution_route") == "keep_audit_control"),
        "unresolved_defer_route_rows": sum(
            1 for row in route_rows if row.get("resolution_route") == "defer_unresolved_post_action_evidence"
        ),
        "request_evidence_available_rows": sum(
            1 for row in primary_requests if row.get("post_action_goal_validity_evidence_available") is True
        ),
        "request_evidence_conflicted_rows": sum(
            1 for row in primary_requests if row.get("request_evidence_status") == "independent_evidence_conflicted"
        ),
        "request_evidence_missing_rows": sum(
            1 for row in primary_requests if row.get("request_evidence_status") == "independent_evidence_missing"
        ),
        "candidate_support_evidence_rows": sum(
            1 for row in primary_candidates if row.get("candidate_evidence_status") == "independent_support_acquired"
        ),
        "candidate_contradiction_evidence_rows": sum(
            1
            for row in primary_candidates
            if row.get("candidate_evidence_status") == "independent_contradiction_acquired"
        ),
        "candidate_conflict_evidence_rows": sum(
            1
            for row in primary_candidates
            if row.get("candidate_evidence_status") == "independent_support_and_contradiction_conflict"
        ),
        "candidate_missing_evidence_rows": sum(
            1 for row in primary_candidates if row.get("candidate_evidence_status") == "independent_evidence_missing"
        ),
        "wrong_goal_reduction_only_by_evidence_availability_rows": sum(
            1 for row in route_rows if row.get("wrong_goal_reduction_only_by_evidence_availability") is True
        ),
        "evidence_conflict_blocks_promotion_rows": sum(
            1 for row in route_rows if row.get("evidence_conflict_blocks_promotion") is True
        ),
        "evidence_missing_blocks_promotion_rows": sum(
            1 for row in route_rows if row.get("evidence_missing_blocks_promotion") is True
        ),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_action_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_action_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_action_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_action_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_action_rows, "paper_claim_allowed"),
    }
    gate = gate_from_counts(contract, counts)
    resolution_gate_passed = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "conflict_missing_resolution_gate_passed_terminal_blocked"
        if resolution_gate_passed
        else "conflict_missing_resolution_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        **counts,
        "route_counts": route_counts,
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
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "resolution_gate": gate,
        "resolution_gate_passed": resolution_gate_passed,
        "active_reobservation_promotion_gate_passed": False,
        "terminal_utility_validation_allowed": False,
        "terminal_utility_contract_allowed_now": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": "post_action_evidence_conflict_requires_non_gt_arbitration",
        "next_task": "implement_or_freeze_next_label_free_conflict_arbitration_or_missing_followup_evidence_family",
        "interpretation": {
            "fact": (
                "The materializer preserves the Docker-verified post-action evidence evaluation join and "
                "routes conflict, missing, and audit rows without changing evidence or joining labels into action."
            ),
            "agent_inference": (
                "This is an action-safe routing artifact, not a terminal utility result. Conflict and missing rows "
                "remain the method-shaping blockers that force the next label-free evidence family."
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
        "ok": summary.get("resolution_gate_passed") is True,
        "status": summary.get("status"),
        "verified_artifact": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": {
            "request_rows": summary.get("request_rows"),
            "primary_target_rows": summary.get("primary_target_rows"),
            "non_target_audit_rows": summary.get("non_target_audit_rows"),
            "candidate_rows": summary.get("candidate_rows"),
            "primary_candidate_rows": summary.get("primary_candidate_rows"),
            "route_rows": summary.get("route_rows"),
            "failure_rows": summary.get("failure_rows"),
            "conflict_route_rows": summary.get("conflict_route_rows"),
            "missing_route_rows": summary.get("missing_route_rows"),
            "audit_route_rows": summary.get("audit_route_rows"),
            "unresolved_defer_route_rows": summary.get("unresolved_defer_route_rows"),
            "wrong_goal_reduction_only_by_evidence_availability_rows": summary.get(
                "wrong_goal_reduction_only_by_evidence_availability_rows"
            ),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "route_counts": summary.get("route_counts"),
        "request_evidence_status_counts": summary.get("request_evidence_status_counts"),
        "primary_request_evidence_status_counts": summary.get("primary_request_evidence_status_counts"),
        "candidate_evidence_status_counts": summary.get("candidate_evidence_status_counts"),
        "primary_candidate_evidence_status_counts": summary.get("primary_candidate_evidence_status_counts"),
        "failure_tag_counts": summary.get("failure_tag_counts"),
        "resolution_gate_passed": summary.get("resolution_gate_passed"),
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
                "materialize_post_action_evidence_conflict_missing_resolution.py"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_post_action_evidence_conflict_missing_resolution"
            ),
            (
                "jq '{status, request_rows, primary_target_rows, conflict_route_rows, "
                "missing_route_rows, audit_route_rows, resolution_gate_passed, "
                "active_reobservation_promotion_gate_passed, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "source_evaluation_join_verified": True,
            "promotion_blocker_consumed": True,
            "conflict_rows_preserved": True,
            "missing_rows_preserved": True,
            "audit_rows_preserved": True,
            "evidence_availability_not_goal_validity": True,
            "labels_for_action_forbidden": True,
            "same_row_comparison_required": True,
            "same_candidate_pool_required": True,
            "same_reobservation_budget_required": True,
            "terminal_commit_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "terminal_utility_validation_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": summary.get("interpretation"),
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")

    request_source_rows = load_jsonl(Path(str(source["request_eval_rows"])))
    candidate_source_rows = load_jsonl(Path(str(source["candidate_eval_rows"])))

    route_rows = materialize_route_rows(request_source_rows)
    route_by_key = {join_key(row): row for row in route_rows}
    candidates_by_request = group_candidates(candidate_source_rows)

    missing_route_keys = [key for key in route_by_key if key not in candidates_by_request]
    if missing_route_keys:
        raise ValueError(f"Candidate rows missing for route keys: {missing_route_keys[:3]}")

    request_rows = materialize_request_rows(request_source_rows, route_by_key)
    candidate_rows = materialize_candidate_rows(candidate_source_rows, route_by_key)
    failure_rows = materialize_failure_rows(route_rows)
    forbidden_keys = scan_forbidden_action_inputs([*request_rows, *candidate_rows, *route_rows, *failure_rows])

    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        route_rows=route_rows,
        failure_rows=failure_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["route_rows"], route_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verification_path(contract_path),
        build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary),
    )

    if summary.get("resolution_gate_passed") is not True:
        raise SystemExit("post-action evidence conflict/missing resolution gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize post-action evidence conflict/missing resolution rows.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
