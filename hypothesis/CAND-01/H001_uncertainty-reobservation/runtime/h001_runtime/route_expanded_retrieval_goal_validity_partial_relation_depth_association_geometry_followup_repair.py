import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys
from h001_runtime.diagnose_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy import (
    compact_counter,
    load_json,
    load_jsonl,
    request_id,
    safe_int,
    sort_request_id,
)


SCHEMA_VERSION = (
    "h001.expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_"
    "followup_repair.v1"
)
POLICY_NAME = "partial_relation_depth_association_geometry_followup_repair_router_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_"
    "followup_repair_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_"
    "followup_repair_v1"
)
UNKNOWN_FOLLOWUP_ACTION = "fail_closed_defer_unmapped_association_geometry_repair_action"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def route_mapping(contract: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapping = contract.get("followup_route_mapping") or {}
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("contract followup_route_mapping is empty")
    return {str(key): dict(value) for key, value in mapping.items()}


def sort_repair_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            sort_request_id(request_id(row)),
            safe_int(row.get("failed_evidence_index"), 999999),
            candidate_id(row),
        ),
    )


def sort_request_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted([dict(row) for row in rows], key=lambda row: sort_request_id(request_id(row)))


def route_for_action(action: str, mapping: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    route = mapping.get(action)
    if route is None:
        return {
            "followup_repair_action": UNKNOWN_FOLLOWUP_ACTION,
            "followup_repair_reason": "repair diagnostic action is not covered by frozen route mapping",
            "allowed_next_evidence": [],
            "blocked_shortcuts": ["terminal_commit_unknown_association_geometry_repair_action"],
            "mapped": False,
        }
    return {
        "followup_repair_action": str(route.get("branch_action")),
        "followup_repair_reason": str(route.get("branch_reason")),
        "allowed_next_evidence": list(route.get("allowed_next_evidence") or []),
        "blocked_shortcuts": list(route.get("blocked_shortcuts") or []),
        "mapped": True,
    }


def build_followup_rows(
    repair_rows: Sequence[Dict[str, Any]],
    mapping: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in sort_repair_rows(repair_rows):
        source_action = str(row.get("repair_diagnostic_action") or "")
        route = route_for_action(source_action, mapping)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": (
                    "action_partial_relation_depth_association_geometry_followup_repair_row"
                ),
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": candidate_id(row),
                "target_candidate_id": candidate_id(row),
                "failed_evidence_index": row.get("failed_evidence_index"),
                "source_branch_action": row.get("source_branch_action"),
                "source_residual_failure_class": row.get("source_residual_failure_class"),
                "source_prior_standoff_direction_source": row.get(
                    "source_prior_standoff_direction_source"
                ),
                "source_repair_diagnostic_action": source_action,
                "source_repair_diagnostic_reason": row.get("repair_diagnostic_reason"),
                "source_completion_inside_mask_count": row.get(
                    "source_completion_inside_mask_count"
                ),
                "source_completion_associated_heading_count": row.get(
                    "source_completion_associated_heading_count"
                ),
                "source_completion_depth_consistent_count": row.get(
                    "source_completion_depth_consistent_count"
                ),
                "exact_failed_completion_frame": row.get("exact_failed_completion_frame") or {},
                "exact_failed_completion_association": row.get(
                    "exact_failed_completion_association"
                )
                or {},
                "same_requested_direction_association": row.get(
                    "same_requested_direction_association"
                )
                or {},
                "other_requested_direction_association": row.get(
                    "other_requested_direction_association"
                )
                or {},
                "followup_repair_action": route["followup_repair_action"],
                "followup_repair_reason": route["followup_repair_reason"],
                "allowed_next_evidence": route["allowed_next_evidence"],
                "blocked_shortcuts": route["blocked_shortcuts"],
                "route_mapping_status": "mapped" if route["mapped"] else "unmapped_fail_closed",
                "terminal_arbitration_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[request_id(row)].append(dict(row))
    return grouped


def build_followup_request_rows(
    source_request_rows: Sequence[Dict[str, Any]],
    followup_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows_by_request = group_by_request(followup_rows)
    output: List[Dict[str, Any]] = []
    for row in sort_request_rows(source_request_rows):
        rid = request_id(row)
        routed_rows = rows_by_request.get(rid, [])
        action_counts = compact_counter(item.get("followup_repair_action") for item in routed_rows)
        mapping_status_counts = compact_counter(item.get("route_mapping_status") for item in routed_rows)
        if len(action_counts) == 1:
            request_action = next(iter(action_counts))
            request_status = "routed"
        elif action_counts:
            request_action = "mixed_followup_repair_actions"
            request_status = "routed_mixed"
        else:
            request_action = UNKNOWN_FOLLOWUP_ACTION
            request_status = "unmapped_fail_closed"
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": (
                    "action_partial_relation_depth_association_geometry_followup_repair_request"
                ),
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_ids": list(row.get("candidate_ids") or []),
                "source_repair_branch_rows": row.get("repair_branch_rows"),
                "source_repair_diagnostic_action_counts": row.get(
                    "repair_diagnostic_action_counts"
                )
                or {},
                "source_request_repair_next_action": row.get("request_repair_next_action"),
                "exact_failed_completion_associated_heading_count": row.get(
                    "exact_failed_completion_associated_heading_count"
                ),
                "same_requested_direction_associated_heading_count": row.get(
                    "same_requested_direction_associated_heading_count"
                ),
                "other_requested_direction_associated_heading_count": row.get(
                    "other_requested_direction_associated_heading_count"
                ),
                "routed_followup_rows": len(routed_rows),
                "followup_repair_action": request_action,
                "followup_repair_action_counts": action_counts,
                "route_mapping_status_counts": mapping_status_counts,
                "request_route_status": request_status,
                "terminal_arbitration_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def nested_count(rows: Sequence[Dict[str, Any]], field: str, key: str) -> int:
    return sum(safe_int((row.get(field) or {}).get(key), 0) for row in rows)


def summarize(
    *,
    contract: Dict[str, Any],
    source_summary: Dict[str, Any],
    source_repair_rows: Sequence[Dict[str, Any]],
    source_request_rows: Sequence[Dict[str, Any]],
    followup_rows: Sequence[Dict[str, Any]],
    followup_request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    mapping = route_mapping(contract)
    action_rows = [*followup_rows, *followup_request_rows]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [
        row
        for row in action_rows
        if row.get("terminal_commit") is True or row.get("terminal_arbitration_allowed") is True
    ]
    candidate_rejection_rows = [
        row
        for row in action_rows
        if row.get("candidate_rejection_allowed") is True
        or str(row.get("followup_repair_action") or "").startswith("reject_")
    ]
    candidate_commit_rows = [
        row
        for row in action_rows
        if row.get("candidate_commit_allowed") is True
        or str(row.get("followup_repair_action") or "").startswith("commit_")
    ]
    source_gate_summary = source_summary.get("gate") or {}
    expected_query_counts = {
        str(key): safe_int(value) for key, value in source_gate.get("expected_query_counts", {}).items()
    }
    expected_action_counts = {
        str(key): safe_int(value)
        for key, value in source_gate.get("expected_repair_diagnostic_action_counts", {}).items()
    }
    expected_request_next_action_counts = {
        str(key): safe_int(value)
        for key, value in source_gate.get("expected_request_repair_next_action_counts", {}).items()
    }
    expected_candidate_ids = sorted(str(value) for value in source_gate.get("expected_candidate_ids", []))
    query_counts = compact_counter(row.get("query") for row in followup_rows)
    candidate_ids = sorted({str(row.get("candidate_id")) for row in followup_rows})
    source_action_counts = compact_counter(row.get("source_repair_diagnostic_action") for row in followup_rows)
    request_next_action_counts = compact_counter(
        row.get("source_request_repair_next_action") for row in followup_request_rows
    )
    followup_action_counts = compact_counter(row.get("followup_repair_action") for row in followup_rows)
    followup_request_action_counts = compact_counter(
        row.get("followup_repair_action") for row in followup_request_rows
    )
    route_mapping_status_counts = compact_counter(row.get("route_mapping_status") for row in followup_rows)
    request_route_status_counts = compact_counter(row.get("request_route_status") for row in followup_request_rows)
    source_residual_class_counts = compact_counter(
        row.get("source_residual_failure_class") for row in followup_rows
    )
    exact_associated = nested_count(
        followup_rows, "exact_failed_completion_association", "associated_heading_count"
    )
    exact_depth_consistent = nested_count(
        followup_rows, "exact_failed_completion_association", "depth_consistent_count"
    )
    exact_inside_mask = nested_count(
        followup_rows, "exact_failed_completion_association", "inside_mask_count"
    )
    same_requested_associated = nested_count(
        followup_rows, "same_requested_direction_association", "associated_heading_count"
    )
    other_requested_associated = nested_count(
        followup_rows, "other_requested_direction_association", "associated_heading_count"
    )
    mapped_actions = set(mapping.keys())
    observed_source_actions = set(source_action_counts.keys())
    gate = {
        "source_association_geometry_repair_diagnostic_gate_passed": source_gate_summary.get(
            "association_geometry_repair_diagnostic_gate_passed"
        )
        is True,
        "expected_source_repair_rows_passed": len(source_repair_rows)
        == safe_int(source_gate.get("expected_repair_rows"), -1),
        "expected_source_request_rows_passed": len(source_request_rows)
        == safe_int(source_gate.get("expected_repair_request_rows"), -1),
        "expected_followup_rows_passed": len(followup_rows)
        == safe_int(source_gate.get("expected_repair_rows"), -1),
        "expected_followup_request_rows_passed": len(followup_request_rows)
        == safe_int(source_gate.get("expected_repair_request_rows"), -1),
        "expected_query_counts_passed": query_counts == expected_query_counts,
        "expected_candidate_ids_passed": candidate_ids == expected_candidate_ids,
        "expected_repair_diagnostic_action_counts_passed": source_action_counts
        == expected_action_counts,
        "expected_request_repair_next_action_counts_passed": request_next_action_counts
        == expected_request_next_action_counts,
        "expected_exact_failed_completion_associated_heading_count_passed": exact_associated
        == safe_int(source_gate.get("expected_exact_failed_completion_associated_heading_count"), -1),
        "expected_exact_failed_completion_depth_consistent_count_passed": exact_depth_consistent
        == safe_int(source_gate.get("expected_exact_failed_completion_depth_consistent_count"), -1),
        "expected_exact_failed_completion_inside_mask_count_passed": exact_inside_mask
        == safe_int(source_gate.get("expected_exact_failed_completion_inside_mask_count"), -1),
        "minimum_same_requested_direction_associated_heading_count_passed": same_requested_associated
        >= safe_int(source_gate.get("minimum_same_requested_direction_associated_heading_count"), -1),
        "minimum_other_requested_direction_associated_heading_count_passed": other_requested_associated
        >= safe_int(source_gate.get("minimum_other_requested_direction_associated_heading_count"), -1),
        "all_repair_rows_routed_passed": route_mapping_status_counts == {"mapped": len(followup_rows)},
        "all_known_repair_actions_mapped_passed": observed_source_actions <= mapped_actions,
        "all_request_rows_routed_passed": request_route_status_counts == {"routed": len(followup_request_rows)},
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(source_gate.get("max_terminal_commit_rows"), -1),
        "terminal_commits_blocked_passed": all(row.get("terminal_commit") is False for row in action_rows),
        "candidate_commit_rows_passed": len(candidate_commit_rows) == 0,
        "candidate_rejection_rows_passed": len(candidate_rejection_rows) == 0,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows)
        and source_summary.get("uses_gt_for_action") is source_gate.get("requires_uses_gt_for_action"),
        "uses_gt_for_analysis_passed": source_summary.get("uses_gt_for_analysis")
        is source_gate.get("requires_uses_gt_for_analysis"),
        "paper_claim_allowed": False,
    }
    pass_keys = [key for key in gate if key.endswith("_passed")]
    gate["association_geometry_followup_repair_gate_passed"] = all(gate[key] is True for key in pass_keys)
    next_task = (
        "design_relation_anchor_selection_repair_probe_contract"
        if followup_action_counts.get("route_to_relation_anchor_selection_repair", 0)
        else "design_direction_specific_reobservation_repair_probe_contract"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "source_summary": str(args.source_summary),
            "source_repair_rows": str(args.source_repair_rows),
            "source_request_rows": str(args.source_request_rows),
        },
        "followup_rows": len(followup_rows),
        "followup_request_rows": len(followup_request_rows),
        "query_counts": query_counts,
        "candidate_ids": candidate_ids,
        "source_residual_failure_class_counts": source_residual_class_counts,
        "source_repair_diagnostic_action_counts": source_action_counts,
        "source_request_repair_next_action_counts": request_next_action_counts,
        "followup_repair_action_counts": followup_action_counts,
        "followup_request_action_counts": followup_request_action_counts,
        "route_mapping_status_counts": route_mapping_status_counts,
        "request_route_status_counts": request_route_status_counts,
        "exact_failed_completion_associated_heading_count": exact_associated,
        "exact_failed_completion_depth_consistent_count": exact_depth_consistent,
        "exact_failed_completion_inside_mask_count": exact_inside_mask,
        "same_requested_direction_associated_heading_count": same_requested_associated,
        "other_requested_direction_associated_heading_count": other_requested_associated,
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "terminal_commit_rows": len(terminal_rows),
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "association_geometry_followup_repair_signal_ready": gate[
                "association_geometry_followup_repair_gate_passed"
            ],
            "recommended_next_task": next_task,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
        },
        "blocked_downstream_tasks": [
            "terminal_utility_contract",
            "candidate_commit_rule",
            "candidate_rejection_rule",
            "first_eval_rerun",
            "policy_scale_comparison",
            "paper_claim",
        ],
        "output_files": {
            "followup_rows": (
                "partial_relation_depth_association_geometry_followup_repair_rows.jsonl"
            ),
            "followup_request_rows": (
                "partial_relation_depth_association_geometry_followup_repair_request_rows.jsonl"
            ),
            "summary": "partial_relation_depth_association_geometry_followup_repair_summary.json",
        },
        "interpretation": {
            "fact": (
                "This router consumes association-geometry repair diagnostic rows and does not "
                "join evaluation labels."
            ),
            "agent_inference": (
                "The association-geometry underlink is now split into relation-anchor selection "
                "repair and direction-specific re-observation repair. These are nonterminal repair "
                "routes, not ObjectNav goal-validity evidence."
            ),
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.source_summary = source_path(
        args, contract, "source_summary", "association_geometry_repair_summary"
    )
    args.source_repair_rows = source_path(
        args, contract, "source_repair_rows", "association_geometry_repair_rows"
    )
    args.source_request_rows = source_path(
        args, contract, "source_request_rows", "association_geometry_repair_request_rows"
    )

    source_summary = load_json(args.source_summary)
    source_repair_rows = load_jsonl(args.source_repair_rows)
    source_request_rows = load_jsonl(args.source_request_rows)
    mapping = route_mapping(contract)
    followup_rows = build_followup_rows(source_repair_rows, mapping)
    followup_request_rows = build_followup_request_rows(source_request_rows, followup_rows)
    summary = summarize(
        contract=contract,
        source_summary=source_summary,
        source_repair_rows=source_repair_rows,
        source_request_rows=source_request_rows,
        followup_rows=followup_rows,
        followup_request_rows=followup_request_rows,
        args=args,
    )

    out_root = Path(args.out_root)
    write_jsonl(
        out_root / "partial_relation_depth_association_geometry_followup_repair_rows.jsonl",
        followup_rows,
    )
    write_jsonl(
        out_root / "partial_relation_depth_association_geometry_followup_repair_request_rows.jsonl",
        followup_request_rows,
    )
    write_json(
        out_root / "partial_relation_depth_association_geometry_followup_repair_summary.json",
        summary,
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Route frozen association-geometry repair diagnostic rows into nonterminal follow-up "
            "repair branches without terminal commit or evaluation-label join."
        )
    )
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--source-summary", type=Path)
    parser.add_argument("--source-repair-rows", type=Path)
    parser.add_argument("--source-request-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["association_geometry_followup_repair_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
