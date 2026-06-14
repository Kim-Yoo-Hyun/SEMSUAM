import argparse
import json
from collections import Counter, defaultdict
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


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_partial_relation_depth_branch_handling.v1"
POLICY_NAME = "partial_relation_depth_branch_handling_router_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1"
)

UNKNOWN_BRANCH_ACTION = "fail_closed_defer_unmapped_partial_relation_depth_status"


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def branch_mapping(contract: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapping = contract.get("branch_mapping") or {}
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("contract branch_mapping is empty")
    return {str(key): dict(value) for key, value in mapping.items()}


def grouped_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[request_id(row)].append(dict(row))
    return grouped


def sort_taxonomy_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            sort_request_id(request_id(row)),
            safe_int(row.get("failed_evidence_index"), 999999),
            str(row.get("target_candidate_id") or row.get("candidate_id") or ""),
        ),
    )


def sort_request_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted([dict(row) for row in rows], key=lambda row: sort_request_id(request_id(row)))


def route_for_status(status: str, mapping: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    route = mapping.get(status)
    if route is None:
        return {
            "branch_action": UNKNOWN_BRANCH_ACTION,
            "branch_reason": "request residual status is not covered by frozen branch mapping",
            "allowed_next_evidence": [],
            "blocked_shortcuts": ["terminal_commit_unknown_partial_relation_depth_status"],
            "mapped": False,
        }
    return {
        "branch_action": str(route.get("branch_action")),
        "branch_reason": str(route.get("branch_reason")),
        "allowed_next_evidence": list(route.get("allowed_next_evidence") or []),
        "blocked_shortcuts": list(route.get("blocked_shortcuts") or []),
        "mapped": True,
    }


def build_request_branch_rows(
    request_taxonomy_rows: Sequence[Dict[str, Any]],
    taxonomy_rows_by_request: Dict[str, List[Dict[str, Any]]],
    mapping: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sort_request_rows(request_taxonomy_rows):
        request_status = str(row.get("request_residual_status") or "")
        route = route_for_status(request_status, mapping)
        taxonomy_rows = taxonomy_rows_by_request.get(request_id(row), [])
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_branch_request_router",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "request_residual_status": request_status,
                "source_recommended_next_action": row.get("recommended_next_action"),
                "residual_rows": row.get("residual_rows"),
                "routed_residual_rows": len(taxonomy_rows),
                "residual_failure_class_counts": row.get("residual_failure_class_counts") or {},
                "residual_failure_tag_counts": row.get("residual_failure_tag_counts") or {},
                "rows_with_inside_mask": row.get("rows_with_inside_mask"),
                "rows_with_completion_association": row.get("rows_with_completion_association"),
                "rows_with_zero_completion_association": row.get("rows_with_zero_completion_association"),
                "rows_with_completion_depth_consistent": row.get("rows_with_completion_depth_consistent"),
                "branch_action": route["branch_action"],
                "branch_reason": route["branch_reason"],
                "allowed_next_evidence": route["allowed_next_evidence"],
                "blocked_shortcuts": route["blocked_shortcuts"],
                "branch_mapping_status": "mapped" if route["mapped"] else "unmapped_fail_closed",
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_branch_rows(
    taxonomy_rows: Sequence[Dict[str, Any]],
    request_branch_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sort_taxonomy_rows(taxonomy_rows):
        request_branch = request_branch_by_id.get(request_id(row))
        if request_branch is None:
            branch_action = UNKNOWN_BRANCH_ACTION
            branch_reason = "taxonomy row has no request-level branch row"
            mapping_status = "unmapped_fail_closed"
            allowed_next_evidence: List[str] = []
            blocked_shortcuts = ["terminal_commit_missing_request_branch"]
        else:
            branch_action = str(request_branch.get("branch_action"))
            branch_reason = str(request_branch.get("branch_reason"))
            mapping_status = str(request_branch.get("branch_mapping_status"))
            allowed_next_evidence = list(request_branch.get("allowed_next_evidence") or [])
            blocked_shortcuts = list(request_branch.get("blocked_shortcuts") or [])
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_branch_row_router",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": row.get("candidate_id"),
                "target_candidate_id": row.get("target_candidate_id"),
                "failed_evidence_index": row.get("failed_evidence_index"),
                "prior_standoff_direction_source": row.get("prior_standoff_direction_source"),
                "completion_status": row.get("completion_status"),
                "unresolved_reason": row.get("unresolved_reason"),
                "residual_failure_class": row.get("residual_failure_class"),
                "residual_failure_tags": list(row.get("residual_failure_tags") or []),
                "completion_associated_heading_count": row.get("completion_associated_heading_count"),
                "completion_depth_consistent_count": row.get("completion_depth_consistent_count"),
                "completion_inside_mask_count": row.get("completion_inside_mask_count"),
                "branch_action": branch_action,
                "branch_reason": branch_reason,
                "allowed_next_evidence": allowed_next_evidence,
                "blocked_shortcuts": blocked_shortcuts,
                "branch_mapping_status": mapping_status,
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def summarize(
    *,
    contract: Dict[str, Any],
    taxonomy_summary: Dict[str, Any],
    branch_rows: Sequence[Dict[str, Any]],
    request_branch_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    branch_gate_contract = contract.get("branch_handling_gate") or {}
    expected_request_status_counts = {
        str(key): safe_int(value)
        for key, value in source_gate.get("expected_request_residual_status_counts", {}).items()
    }
    expected_class_counts = {
        str(key): safe_int(value)
        for key, value in source_gate.get("expected_residual_failure_class_counts", {}).items()
    }
    action_rows = [*branch_rows, *request_branch_rows]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [
        row
        for row in action_rows
        if row.get("terminal_commit") is True or row.get("terminal_arbitration_allowed") is True
    ]
    unmapped_request_rows = [
        row for row in request_branch_rows if row.get("branch_mapping_status") != "mapped"
    ]
    branch_action_counts = compact_counter(row.get("branch_action") for row in request_branch_rows)
    request_status_counts = compact_counter(row.get("request_residual_status") for row in request_branch_rows)
    residual_class_counts = compact_counter(row.get("residual_failure_class") for row in branch_rows)
    taxonomy_gate = taxonomy_summary.get("gate") or {}
    gate = {
        "source_taxonomy_gate_passed": taxonomy_gate.get(
            "partial_relation_depth_residual_taxonomy_gate_passed"
        )
        is True,
        "expected_branch_rows_passed": len(branch_rows)
        == safe_int(source_gate.get("expected_taxonomy_rows"), -1),
        "expected_request_branch_rows_passed": len(request_branch_rows)
        == safe_int(source_gate.get("expected_request_taxonomy_rows"), -1),
        "expected_residual_failure_class_counts_passed": residual_class_counts
        == expected_class_counts,
        "expected_request_residual_status_counts_passed": request_status_counts
        == expected_request_status_counts,
        "all_request_rows_routed_passed": len(unmapped_request_rows) == 0,
        "all_known_request_statuses_mapped_passed": set(request_status_counts)
        <= set((contract.get("branch_mapping") or {}).keys()),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(source_gate.get("max_terminal_commit_rows"), -1),
        "terminal_commits_blocked_passed": branch_gate_contract.get("terminal_commits_allowed")
        is False
        and all(row.get("terminal_commit") is False for row in action_rows),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed": False,
    }
    gate["partial_relation_depth_branch_handling_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    next_task = (
        "design_association_geometry_repair_branch_contract"
        if branch_action_counts.get("route_to_association_geometry_repair_branch", 0)
        else "define_terminal_utility_contract_after_validated_non_gt_arbitration_rule"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source_files": {
            "taxonomy_summary": str(args.taxonomy_summary),
            "taxonomy_rows": str(args.taxonomy_rows),
            "request_taxonomy_rows": str(args.request_taxonomy_rows),
        },
        "branch_rows": len(branch_rows),
        "request_branch_rows": len(request_branch_rows),
        "request_status_counts": request_status_counts,
        "residual_failure_class_counts": residual_class_counts,
        "branch_action_counts": branch_action_counts,
        "unmapped_request_rows": len(unmapped_request_rows),
        "unmapped_request_ids": [request_id(row) for row in unmapped_request_rows],
        "terminal_commit_rows": len(terminal_rows),
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gate": gate,
        "recommended_next_task": next_task,
        "blocked_downstream_tasks": [
            "terminal_utility_contract",
            "first_eval_rerun",
            "policy_scale_comparison",
            "paper_claim",
        ],
        "interpretation": {
            "fact": (
                "This router consumes request-level residual taxonomy rows and does not join "
                "correctness labels."
            ),
            "agent_inference": (
                "Residual partial relation-depth is now routed into nonterminal association-geometry, "
                "depth-stagnation, and repeated-object relation-anchor branches. Terminal utility remains "
                "blocked until a later non-GT arbitration rule validates a branch outcome."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "branch_rows": "partial_relation_depth_branch_rows.jsonl",
            "request_branch_rows": "partial_relation_depth_branch_request_rows.jsonl",
            "summary": "partial_relation_depth_branch_handling_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.taxonomy_summary = source_path(args, contract, "taxonomy_summary", "taxonomy_summary")
    args.taxonomy_rows = source_path(args, contract, "taxonomy_rows", "taxonomy_rows")
    args.request_taxonomy_rows = source_path(args, contract, "request_taxonomy_rows", "request_taxonomy_rows")

    taxonomy_summary = load_json(args.taxonomy_summary)
    taxonomy_rows = load_jsonl(args.taxonomy_rows)
    request_taxonomy_rows = load_jsonl(args.request_taxonomy_rows)
    mapping = branch_mapping(contract)
    taxonomy_by_request = grouped_by_request(taxonomy_rows)
    request_branch_rows = build_request_branch_rows(request_taxonomy_rows, taxonomy_by_request, mapping)
    request_branch_by_id = {request_id(row): row for row in request_branch_rows}
    branch_rows = build_branch_rows(taxonomy_rows, request_branch_by_id)
    summary = summarize(
        contract=contract,
        taxonomy_summary=taxonomy_summary,
        branch_rows=branch_rows,
        request_branch_rows=request_branch_rows,
        args=args,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "partial_relation_depth_branch_rows.jsonl", branch_rows)
    write_jsonl(out_root / "partial_relation_depth_branch_request_rows.jsonl", request_branch_rows)
    write_json(out_root / "partial_relation_depth_branch_handling_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route residual partial relation-depth taxonomy rows into frozen nonterminal branches."
    )
    parser.add_argument("--contract", default=Path(CONTRACT_DEFAULT), type=Path)
    parser.add_argument("--out-root", default=Path(OUT_ROOT_DEFAULT), type=Path)
    parser.add_argument("--taxonomy-summary", type=Path)
    parser.add_argument("--taxonomy-rows", type=Path)
    parser.add_argument("--request-taxonomy-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["partial_relation_depth_branch_handling_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
