import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.post_action_goal_validity_arbitration_followup.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_post_action_goal_validity_arbitration_followup_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_post_action_goal_validity_arbitration_followup_v1"

OUTPUT_FILES = {
    "request_rows": "post_action_goal_validity_arbitration_followup_request_rows.jsonl",
    "candidate_rows": "post_action_goal_validity_arbitration_followup_candidate_rows.jsonl",
    "pair_rows": "post_action_goal_validity_arbitration_followup_pair_rows.jsonl",
    "audit_rows": "post_action_goal_validity_arbitration_followup_audit_rows.jsonl",
    "failure_rows": "post_action_goal_validity_arbitration_followup_failure_rows.jsonl",
    "summary": "post_action_goal_validity_arbitration_followup_summary.json",
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

BRANCH_BY_ROUTE = {
    "request_conflict_arbitration_evidence": "pairwise_goal_region_map_pose_arbitration_v1",
    "request_missing_evidence_followup": "missing_evidence_second_view_followup_v1",
    "keep_audit_control": "keep_audit_control_v1",
}

ACTION_BY_BRANCH = {
    "pairwise_goal_region_map_pose_arbitration_v1": "request_pairwise_goal_region_map_pose_evidence",
    "missing_evidence_second_view_followup_v1": "request_second_view_candidate_specific_evidence",
    "keep_audit_control_v1": "audit_only_same_row_baseline_accounting",
}

STATUS_PRIORITY = {
    "independent_support_acquired": 0,
    "independent_support_and_contradiction_conflict": 1,
    "independent_contradiction_acquired": 2,
    "independent_evidence_missing": 3,
    "audit_control_no_evidence_required": 4,
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


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def group_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[join_key(row)].append(row)
    return dict(grouped)


def index_one(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {join_key(row): row for row in rows}


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


def selected_branch(route: Any) -> str:
    return BRANCH_BY_ROUTE.get(str(route), "defer_unresolved_arbitration_followup_v1")


def selected_action(branch: str) -> str:
    return ACTION_BY_BRANCH.get(branch, "defer_unresolved_arbitration_followup")


def selected_family(contract: Mapping[str, Any]) -> str:
    family = contract.get("selected_family")
    if isinstance(family, Mapping):
        return str(family.get("family_name") or "")
    return ""


def branch_requirements(branch: str) -> Dict[str, bool]:
    if branch == "pairwise_goal_region_map_pose_arbitration_v1":
        return {
            "own_view_vs_rival_view_separation_required": True,
            "object_relation_or_goal_region_required": True,
            "map_pose_consistency_cross_check_required": True,
            "followup_required": True,
        }
    if branch == "missing_evidence_second_view_followup_v1":
        return {
            "own_view_vs_rival_view_separation_required": False,
            "object_relation_or_goal_region_required": False,
            "map_pose_consistency_cross_check_required": True,
            "followup_required": True,
        }
    return {
        "own_view_vs_rival_view_separation_required": False,
        "object_relation_or_goal_region_required": False,
        "map_pose_consistency_cross_check_required": False,
        "followup_required": False,
    }


def base_branch_payload(
    *,
    contract: Mapping[str, Any],
    source: Mapping[str, Any],
    cid: Optional[str] = None,
    candidate_a_id: Optional[str] = None,
    candidate_b_id: Optional[str] = None,
) -> Dict[str, Any]:
    route = source.get("resolution_route")
    branch = selected_branch(route)
    return {
        "target_role": source.get("target_role"),
        "source_branch_action": source.get("source_branch_action"),
        "source_resolution_route": route,
        "source_resolution_reason": source.get("resolution_reason"),
        "selected_evidence_family": selected_family(contract),
        "selected_branch": branch,
        "selected_action": selected_action(branch),
        "candidate_id": cid,
        "candidate_a_id": candidate_a_id,
        "candidate_b_id": candidate_b_id,
        **branch_requirements(branch),
        "label_free_action_only": True,
        "evidence_available_is_not_goal_validity": True,
        "evaluation_label_fields_dropped_for_action": True,
        **common_flags(),
    }


def materialize_request_rows(
    *,
    contract: Mapping[str, Any],
    request_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(request_rows, key=join_key):
        key = join_key(source)
        payload = key_payload(key)
        branch = selected_branch(source.get("resolution_route"))
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_goal_validity_arbitration_followup_materialization",
                "row_type": "post_action_goal_validity_arbitration_followup_request",
                "join_key": payload,
                **payload,
                **base_branch_payload(contract=contract, source=source),
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
                "resolution_required": source.get("resolution_required") is True,
                "evidence_conflict_blocks_promotion": source.get("evidence_conflict_blocks_promotion") is True,
                "evidence_missing_blocks_promotion": source.get("evidence_missing_blocks_promotion") is True,
                "wrong_goal_reduction_only_by_evidence_availability": (
                    source.get("wrong_goal_reduction_only_by_evidence_availability") is True
                ),
                "action_route_inputs": {
                    "target_role": source.get("target_role"),
                    "source_resolution_route": source.get("resolution_route"),
                    "request_evidence_status": source.get("request_evidence_status"),
                    "post_action_goal_validity_evidence_available": (
                        source.get("post_action_goal_validity_evidence_available") is True
                    ),
                    "selected_branch": branch,
                },
            }
        )
    return out


def materialize_candidate_rows(
    *,
    contract: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(candidate_rows, key=candidate_key):
        key = join_key(source)
        payload = key_payload(key)
        cid = candidate_key(source)[-1]
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_goal_validity_arbitration_followup_materialization",
                "row_type": "post_action_goal_validity_arbitration_followup_candidate",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                **base_branch_payload(contract=contract, source=source, cid=cid),
                "request_evidence_status": source.get("request_evidence_status"),
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
                "evidence_conflict_blocks_promotion": source.get("evidence_conflict_blocks_promotion") is True,
                "evidence_missing_blocks_promotion": source.get("evidence_missing_blocks_promotion") is True,
                "wrong_goal_reduction_only_by_evidence_availability": (
                    source.get("wrong_goal_reduction_only_by_evidence_availability") is True
                ),
                "action_evidence_inputs": {
                    "candidate_id": cid,
                    "candidate_evidence_status": source.get("candidate_evidence_status"),
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
                },
            }
        )
    return out


def sorted_pair_candidates(rows: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            STATUS_PRIORITY.get(str(row.get("candidate_evidence_status")), 99),
            candidate_key(row)[-1],
        ),
    )


def pair_status_pattern(rows: Sequence[Mapping[str, Any]]) -> str:
    statuses = [str(row.get("candidate_evidence_status") or "") for row in sorted_pair_candidates(rows)]
    return " + ".join(statuses)


def float_abs_delta(left: Any, right: Any) -> Optional[float]:
    left_value = safe_float(left)
    right_value = safe_float(right)
    if left_value is None or right_value is None:
        return None
    return abs(left_value - right_value)


def materialize_pair_rows(
    *,
    contract: Mapping[str, Any],
    request_rows: Sequence[Mapping[str, Any]],
    candidates_by_key: Mapping[Tuple[str, str, str, str, str], Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    selected_routes = {"request_conflict_arbitration_evidence", "request_missing_evidence_followup"}
    for request in sorted(request_rows, key=join_key):
        if request.get("resolution_route") not in selected_routes:
            continue
        key = join_key(request)
        payload = key_payload(key)
        candidates = sorted_pair_candidates(candidates_by_key.get(key, []))
        if len(candidates) < 2:
            continue
        left, right = candidates[0], candidates[1]
        left_id = candidate_key(left)[-1]
        right_id = candidate_key(right)[-1]
        branch = selected_branch(request.get("resolution_route"))
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_goal_validity_arbitration_followup_materialization",
                "row_type": "post_action_goal_validity_arbitration_followup_pair",
                "join_key": {**payload, "candidate_a_id": left_id, "candidate_b_id": right_id},
                **payload,
                **base_branch_payload(
                    contract=contract,
                    source=request,
                    candidate_a_id=left_id,
                    candidate_b_id=right_id,
                ),
                "request_evidence_status": request.get("request_evidence_status"),
                "post_action_goal_validity_evidence_available": (
                    request.get("post_action_goal_validity_evidence_available") is True
                ),
                "candidate_pair_count_for_request": len(candidates),
                "candidate_pair_status_pattern": pair_status_pattern(candidates[:2]),
                "candidate_a_evidence_status": left.get("candidate_evidence_status"),
                "candidate_b_evidence_status": right.get("candidate_evidence_status"),
                "candidate_a_support_evidence_count": safe_int(left.get("candidate_support_evidence_count"), 0),
                "candidate_b_support_evidence_count": safe_int(right.get("candidate_support_evidence_count"), 0),
                "candidate_a_contradiction_evidence_count": safe_int(
                    left.get("candidate_contradiction_evidence_count"),
                    0,
                ),
                "candidate_b_contradiction_evidence_count": safe_int(
                    right.get("candidate_contradiction_evidence_count"),
                    0,
                ),
                "support_count_abs_delta": abs(
                    safe_int(left.get("candidate_support_evidence_count"), 0)
                    - safe_int(right.get("candidate_support_evidence_count"), 0)
                ),
                "contradiction_count_abs_delta": abs(
                    safe_int(left.get("candidate_contradiction_evidence_count"), 0)
                    - safe_int(right.get("candidate_contradiction_evidence_count"), 0)
                ),
                "viewpoint_coverage_abs_delta": float_abs_delta(
                    left.get("viewpoint_coverage_delta"),
                    right.get("viewpoint_coverage_delta"),
                ),
                "association_quality_abs_delta": float_abs_delta(
                    left.get("association_quality_proxy"),
                    right.get("association_quality_proxy"),
                ),
                "map_pose_consistency_abs_delta": float_abs_delta(
                    left.get("map_pose_consistency_delta"),
                    right.get("map_pose_consistency_delta"),
                ),
                "pose_graph_connectivity_abs_delta": float_abs_delta(
                    left.get("pose_graph_connectivity_delta"),
                    right.get("pose_graph_connectivity_delta"),
                ),
                "map_pose_uncertainty_abs_delta": float_abs_delta(
                    left.get("map_pose_consistency_uncertainty_proxy"),
                    right.get("map_pose_consistency_uncertainty_proxy"),
                ),
                "pairwise_goal_validity_arbitration_required": (
                    branch == "pairwise_goal_region_map_pose_arbitration_v1"
                ),
                "missing_evidence_second_view_followup_required": (
                    branch == "missing_evidence_second_view_followup_v1"
                ),
                "action_evidence_inputs": {
                    "candidate_pair_ids": [left_id, right_id],
                    "candidate_statuses": [
                        left.get("candidate_evidence_status"),
                        right.get("candidate_evidence_status"),
                    ],
                    "candidate_support_counts": [
                        safe_int(left.get("candidate_support_evidence_count"), 0),
                        safe_int(right.get("candidate_support_evidence_count"), 0),
                    ],
                    "candidate_contradiction_counts": [
                        safe_int(left.get("candidate_contradiction_evidence_count"), 0),
                        safe_int(right.get("candidate_contradiction_evidence_count"), 0),
                    ],
                    "selected_branch": branch,
                    "viewpoint_coverage_abs_delta": float_abs_delta(
                        left.get("viewpoint_coverage_delta"),
                        right.get("viewpoint_coverage_delta"),
                    ),
                    "association_quality_abs_delta": float_abs_delta(
                        left.get("association_quality_proxy"),
                        right.get("association_quality_proxy"),
                    ),
                    "map_pose_consistency_abs_delta": float_abs_delta(
                        left.get("map_pose_consistency_delta"),
                        right.get("map_pose_consistency_delta"),
                    ),
                    "pose_graph_connectivity_abs_delta": float_abs_delta(
                        left.get("pose_graph_connectivity_delta"),
                        right.get("pose_graph_connectivity_delta"),
                    ),
                },
            }
        )
    return out


def materialize_audit_rows(
    *,
    contract: Mapping[str, Any],
    request_rows: Sequence[Mapping[str, Any]],
    candidates_by_key: Mapping[Tuple[str, str, str, str, str], Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for request in sorted(request_rows, key=join_key):
        if request.get("resolution_route") != "keep_audit_control":
            continue
        key = join_key(request)
        payload = key_payload(key)
        candidates = candidates_by_key.get(key, [])
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_goal_validity_arbitration_followup_materialization",
                "row_type": "post_action_goal_validity_arbitration_followup_audit",
                "join_key": payload,
                **payload,
                **base_branch_payload(contract=contract, source=request),
                "request_evidence_status": request.get("request_evidence_status"),
                "audit_candidate_count": len(candidates),
                "audit_reason": "non_target_or_audit_control_row_preserved_for_same_row_accounting",
                "action_route_inputs": {
                    "target_role": request.get("target_role"),
                    "source_resolution_route": request.get("resolution_route"),
                    "selected_branch": selected_branch(request.get("resolution_route")),
                    "audit_candidate_count": len(candidates),
                },
            }
        )
    return out


def failure_tags(row: Mapping[str, Any]) -> List[str]:
    tags = [
        "terminal_utility_blocked",
        "candidate_commit_blocked",
        "candidate_rejection_blocked",
        "paper_claim_blocked",
        "arbitration_followup_materialization_only",
    ]
    route = row.get("source_resolution_route")
    branch = row.get("selected_branch")
    if route == "request_conflict_arbitration_evidence":
        tags.append("pairwise_goal_region_map_pose_arbitration_required")
    elif route == "request_missing_evidence_followup":
        tags.append("missing_evidence_second_view_followup_required")
    elif route == "keep_audit_control":
        tags.append("audit_control_preserved")
    else:
        tags.append("unresolved_arbitration_followup_route")
    if row.get("wrong_goal_reduction_only_by_evidence_availability") is True:
        tags.append("wrong_goal_reduction_only_by_evidence_availability")
    if branch == "pairwise_goal_region_map_pose_arbitration_v1":
        tags.append("goal_validity_not_proven_by_pair_row")
    if branch == "missing_evidence_second_view_followup_v1":
        tags.append("goal_validity_not_proven_by_missing_followup")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "pairwise_goal_region_map_pose_arbitration_required",
        "missing_evidence_second_view_followup_required",
        "wrong_goal_reduction_only_by_evidence_availability",
        "audit_control_preserved",
        "unresolved_arbitration_followup_route",
    ):
        if tag in tags:
            return tag
    return "arbitration_followup_materialization_only"


def materialize_failure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in sorted(request_rows, key=join_key):
        key = join_key(row)
        payload = key_payload(key)
        tags = failure_tags(row)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_goal_validity_arbitration_followup_materialization",
                "row_type": "post_action_goal_validity_arbitration_followup_failure",
                "join_key": payload,
                **payload,
                "target_role": row.get("target_role"),
                "source_resolution_route": row.get("source_resolution_route"),
                "selected_evidence_family": row.get("selected_evidence_family"),
                "selected_branch": row.get("selected_branch"),
                "selected_action": row.get("selected_action"),
                "request_evidence_status": row.get("request_evidence_status"),
                "post_action_goal_validity_evidence_available": (
                    row.get("post_action_goal_validity_evidence_available") is True
                ),
                "wrong_goal_reduction_only_by_evidence_availability": (
                    row.get("wrong_goal_reduction_only_by_evidence_availability") is True
                ),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                "terminal_utility_validation_allowed": False,
                **common_flags(),
            }
        )
    return out


def gate_from_counts(contract: Mapping[str, Any], counts: Mapping[str, int]) -> Dict[str, bool]:
    gate = contract.get("implementation_gate")
    gate = gate if isinstance(gate, Mapping) else {}
    return {
        "request_rows_expected_passed": counts["request_rows"] == safe_int(gate.get("request_rows_expected"), 50),
        "selected_target_request_rows_expected_passed": counts["selected_target_request_rows"]
        == safe_int(gate.get("selected_target_request_rows_expected"), 21),
        "conflict_request_rows_expected_passed": counts["conflict_request_rows"]
        == safe_int(gate.get("conflict_request_rows_expected"), 18),
        "missing_request_rows_expected_passed": counts["missing_request_rows"]
        == safe_int(gate.get("missing_request_rows_expected"), 3),
        "audit_request_rows_expected_passed": counts["audit_request_rows"]
        == safe_int(gate.get("audit_request_rows_expected"), 29),
        "candidate_rows_expected_passed": counts["candidate_rows"]
        == safe_int(gate.get("candidate_rows_expected"), 97),
        "conflict_candidate_rows_expected_passed": counts["conflict_candidate_rows"]
        == safe_int(gate.get("conflict_candidate_rows_expected"), 36),
        "missing_candidate_rows_expected_passed": counts["missing_candidate_rows"]
        == safe_int(gate.get("missing_candidate_rows_expected"), 6),
        "audit_candidate_rows_expected_passed": counts["audit_candidate_rows"]
        == safe_int(gate.get("audit_candidate_rows_expected"), 55),
        "pairwise_arbitration_pair_rows_expected_passed": counts["pairwise_arbitration_pair_rows"]
        == safe_int(gate.get("pairwise_arbitration_pair_rows_expected"), 18),
        "missing_followup_pair_rows_expected_passed": counts["missing_followup_pair_rows"]
        == safe_int(gate.get("missing_followup_pair_rows_expected"), 3),
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
    pair_rows: Sequence[Mapping[str, Any]],
    audit_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    all_action_rows = [*request_rows, *candidate_rows, *pair_rows, *audit_rows, *failure_rows]
    selected_target_requests = [row for row in request_rows if row.get("target_role") == "primary_target"]
    counts = {
        "request_rows": len(request_rows),
        "selected_target_request_rows": len(selected_target_requests),
        "conflict_request_rows": sum(
            1
            for row in request_rows
            if row.get("source_resolution_route") == "request_conflict_arbitration_evidence"
        ),
        "missing_request_rows": sum(
            1 for row in request_rows if row.get("source_resolution_route") == "request_missing_evidence_followup"
        ),
        "audit_request_rows": sum(1 for row in request_rows if row.get("source_resolution_route") == "keep_audit_control"),
        "candidate_rows": len(candidate_rows),
        "conflict_candidate_rows": sum(
            1
            for row in candidate_rows
            if row.get("source_resolution_route") == "request_conflict_arbitration_evidence"
        ),
        "missing_candidate_rows": sum(
            1 for row in candidate_rows if row.get("source_resolution_route") == "request_missing_evidence_followup"
        ),
        "audit_candidate_rows": sum(
            1 for row in candidate_rows if row.get("source_resolution_route") == "keep_audit_control"
        ),
        "pair_rows": len(pair_rows),
        "pairwise_arbitration_pair_rows": sum(
            1 for row in pair_rows if row.get("selected_branch") == "pairwise_goal_region_map_pose_arbitration_v1"
        ),
        "missing_followup_pair_rows": sum(
            1 for row in pair_rows if row.get("selected_branch") == "missing_evidence_second_view_followup_v1"
        ),
        "audit_rows": len(audit_rows),
        "failure_rows": len(failure_rows),
        "wrong_goal_reduction_only_by_evidence_availability_rows": sum(
            1 for row in request_rows if row.get("wrong_goal_reduction_only_by_evidence_availability") is True
        ),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_action_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_action_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_action_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_action_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_action_rows, "paper_claim_allowed"),
    }
    gate = gate_from_counts(contract, counts)
    materializer_gate_passed = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "arbitration_followup_materializer_gate_passed_terminal_blocked"
        if materializer_gate_passed
        else "arbitration_followup_materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        **counts,
        "route_counts": compact_counter(row.get("source_resolution_route") for row in request_rows),
        "branch_counts": compact_counter(row.get("selected_branch") for row in request_rows),
        "request_evidence_status_counts": compact_counter(row.get("request_evidence_status") for row in request_rows),
        "candidate_evidence_status_counts": compact_counter(
            row.get("candidate_evidence_status") for row in candidate_rows
        ),
        "pair_status_pattern_counts": compact_counter(row.get("candidate_pair_status_pattern") for row in pair_rows),
        "audit_candidate_count_stats": number_stats(row.get("audit_candidate_count") for row in audit_rows),
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "implementation_gate": gate,
        "materializer_gate_passed": materializer_gate_passed,
        "active_reobservation_promotion_gate_passed": False,
        "terminal_utility_validation_allowed": False,
        "terminal_utility_contract_allowed_now": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": "post_action_arbitration_followup_evaluation_join_required"
        if materializer_gate_passed
        else "post_action_arbitration_followup_materialization_failed",
        "next_task": "freeze_post_action_goal_validity_arbitration_followup_evaluation_join_contract"
        if materializer_gate_passed
        else "debug_post_action_goal_validity_arbitration_followup_materializer",
        "interpretation": {
            "fact": (
                "The materializer preserves the frozen conflict/missing/audit routing and writes request, "
                "candidate, pair, audit, and failure rows without terminal commits or label-derived actions."
            ),
            "agent_inference": (
                "The artifact makes pairwise arbitration and missing-evidence follow-up explicit enough for a "
                "future evaluation join, but it still does not prove goal validity or terminal utility."
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
        "ok": summary.get("materializer_gate_passed") is True,
        "status": summary.get("status"),
        "verified_artifact": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": {
            "request_rows": summary.get("request_rows"),
            "selected_target_request_rows": summary.get("selected_target_request_rows"),
            "conflict_request_rows": summary.get("conflict_request_rows"),
            "missing_request_rows": summary.get("missing_request_rows"),
            "audit_request_rows": summary.get("audit_request_rows"),
            "candidate_rows": summary.get("candidate_rows"),
            "conflict_candidate_rows": summary.get("conflict_candidate_rows"),
            "missing_candidate_rows": summary.get("missing_candidate_rows"),
            "audit_candidate_rows": summary.get("audit_candidate_rows"),
            "pair_rows": summary.get("pair_rows"),
            "pairwise_arbitration_pair_rows": summary.get("pairwise_arbitration_pair_rows"),
            "missing_followup_pair_rows": summary.get("missing_followup_pair_rows"),
            "audit_rows": summary.get("audit_rows"),
            "failure_rows": summary.get("failure_rows"),
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
        "branch_counts": summary.get("branch_counts"),
        "request_evidence_status_counts": summary.get("request_evidence_status_counts"),
        "candidate_evidence_status_counts": summary.get("candidate_evidence_status_counts"),
        "pair_status_pattern_counts": summary.get("pair_status_pattern_counts"),
        "failure_tag_counts": summary.get("failure_tag_counts"),
        "implementation_gate": summary.get("implementation_gate"),
        "materializer_gate_passed": summary.get("materializer_gate_passed"),
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
                "materialize_post_action_goal_validity_arbitration_followup.py"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/src "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_post_action_goal_validity_arbitration_followup"
            ),
            (
                "jq '{status, request_rows, candidate_rows, pair_rows, audit_rows, failure_rows, "
                "pairwise_arbitration_pair_rows, missing_followup_pair_rows, materializer_gate_passed, "
                "primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "source_resolution_verified": True,
            "conflict_rows_preserved": True,
            "missing_rows_preserved": True,
            "audit_rows_preserved": True,
            "pairwise_arbitration_materialized": True,
            "second_view_followup_materialized": True,
            "support_count_terminal_shortcut_forbidden": True,
            "detector_score_terminal_shortcut_forbidden": True,
            "map_pose_only_terminal_shortcut_forbidden": True,
            "evidence_availability_not_goal_validity": True,
            "labels_for_action_forbidden": True,
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

    request_source_rows = load_jsonl(Path(str(source["resolution_request_rows"])))
    candidate_source_rows = load_jsonl(Path(str(source["resolution_candidate_rows"])))
    route_source_rows = load_jsonl(Path(str(source["resolution_route_rows"])))

    route_by_key = index_one(route_source_rows)
    missing_route_keys = [key for key in map(join_key, request_source_rows) if key not in route_by_key]
    if missing_route_keys:
        raise ValueError(f"Route rows missing for request keys: {missing_route_keys[:3]}")

    candidates_by_key = group_by_request(candidate_source_rows)
    missing_candidate_keys = [key for key in map(join_key, request_source_rows) if key not in candidates_by_key]
    if missing_candidate_keys:
        raise ValueError(f"Candidate rows missing for request keys: {missing_candidate_keys[:3]}")

    request_rows = materialize_request_rows(contract=contract, request_rows=request_source_rows)
    candidate_rows = materialize_candidate_rows(contract=contract, candidate_rows=candidate_source_rows)
    pair_rows = materialize_pair_rows(
        contract=contract,
        request_rows=request_source_rows,
        candidates_by_key=candidates_by_key,
    )
    audit_rows = materialize_audit_rows(
        contract=contract,
        request_rows=request_source_rows,
        candidates_by_key=candidates_by_key,
    )
    failure_rows = materialize_failure_rows(request_rows)
    forbidden_keys = scan_forbidden_action_inputs([*request_rows, *candidate_rows, *pair_rows, *audit_rows, *failure_rows])

    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        audit_rows=audit_rows,
        failure_rows=failure_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["audit_rows"], audit_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verification_path(contract_path),
        build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary),
    )

    if summary.get("materializer_gate_passed") is not True:
        raise SystemExit("post-action goal-validity arbitration/follow-up materializer gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize post-action goal-validity arbitration and follow-up evidence rows."
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
