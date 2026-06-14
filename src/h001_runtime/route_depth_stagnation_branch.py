import argparse
import json
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


SCHEMA_VERSION = "h001.depth_stagnation_branch.v1"
POLICY_NAME = "depth_stagnation_branch_router_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_depth_stagnation_branch_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_depth_stagnation_branch_v1"


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


def sort_branch_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            sort_request_id(request_id(row)),
            safe_int(row.get("failed_evidence_index"), 999999),
            candidate_id(row),
            str(row.get("prior_standoff_direction_source") or ""),
        ),
    )


def sort_request_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted([dict(row) for row in rows], key=lambda row: sort_request_id(request_id(row)))


def unique_values(rows: Sequence[Dict[str, Any]], key: str) -> List[str]:
    return sorted({str(row.get(key) or "") for row in rows if row.get(key) is not None})


def count_rows_gt_zero(rows: Sequence[Dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if safe_int(row.get(key), 0) > 0)


def count_rows_eq_zero(rows: Sequence[Dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if safe_int(row.get(key), 0) == 0)


def source_gate_value(source_gate: Dict[str, Any], key: str) -> str:
    return str(source_gate.get(key) or "")


def target_branch_rows(rows: Sequence[Dict[str, Any]], source_gate: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sort_branch_rows(
        [
            dict(row)
            for row in rows
            if str(row.get("branch_action")) == source_gate_value(source_gate, "target_branch_action")
            and request_id(row) == source_gate_value(source_gate, "expected_request_id")
            and str(row.get("scene_key")) == source_gate_value(source_gate, "expected_scene_key")
            and str(row.get("query")) == source_gate_value(source_gate, "expected_query")
            and candidate_id(row) == source_gate_value(source_gate, "expected_candidate_id")
        ]
    )


def target_request_branch_rows(
    rows: Sequence[Dict[str, Any]], source_gate: Dict[str, Any]
) -> List[Dict[str, Any]]:
    return sort_request_rows(
        [
            dict(row)
            for row in rows
            if str(row.get("branch_action")) == source_gate_value(source_gate, "target_branch_action")
            and request_id(row) == source_gate_value(source_gate, "expected_request_id")
            and str(row.get("scene_key")) == source_gate_value(source_gate, "expected_scene_key")
            and str(row.get("query")) == source_gate_value(source_gate, "expected_query")
        ]
    )


def target_taxonomy_rows(rows: Sequence[Dict[str, Any]], source_gate: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sort_branch_rows(
        [
            dict(row)
            for row in rows
            if request_id(row) == source_gate_value(source_gate, "expected_request_id")
            and str(row.get("scene_key")) == source_gate_value(source_gate, "expected_scene_key")
            and str(row.get("query")) == source_gate_value(source_gate, "expected_query")
            and candidate_id(row) == source_gate_value(source_gate, "expected_candidate_id")
        ]
    )


def target_request_taxonomy_rows(
    rows: Sequence[Dict[str, Any]], source_gate: Dict[str, Any]
) -> List[Dict[str, Any]]:
    return sort_request_rows(
        [
            dict(row)
            for row in rows
            if request_id(row) == source_gate_value(source_gate, "expected_request_id")
            and str(row.get("scene_key")) == source_gate_value(source_gate, "expected_scene_key")
            and str(row.get("query")) == source_gate_value(source_gate, "expected_query")
            and str(row.get("request_residual_status"))
            == source_gate_value(source_gate, "expected_request_residual_status")
        ]
    )


def index_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {request_id(row): dict(row) for row in rows}


def depth_signal_role(taxonomy_row: Dict[str, Any]) -> str:
    prior_depth = safe_int(taxonomy_row.get("prior_depth_consistent_count"), 0)
    completion_depth = safe_int(taxonomy_row.get("completion_depth_consistent_count"), 0)
    associated = safe_int(taxonomy_row.get("completion_associated_heading_count"), 0)
    if associated > 0 and completion_depth <= prior_depth:
        return "association_present_depth_stagnant"
    if associated > 0 and completion_depth > prior_depth:
        return "association_present_depth_improved_manual_review"
    return "manual_review_unexpected_depth_stagnation_pattern"


def build_branch_rows(
    *,
    source_rows: Sequence[Dict[str, Any]],
    taxonomy_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> List[Dict[str, Any]]:
    branch_contract = contract.get("branch_contract") or {}
    nonterminal_action = str(branch_contract.get("expected_nonterminal_branch_action"))
    required_actions = list(branch_contract.get("required_branch_actions") or [])
    required_comparisons = list(branch_contract.get("required_comparisons") or [])
    blocked_shortcuts = list(branch_contract.get("blocked_shortcuts") or [])
    taxonomy_by_request = index_by_request(taxonomy_rows)
    output: List[Dict[str, Any]] = []
    for row in sort_branch_rows(source_rows):
        taxonomy = taxonomy_by_request.get(request_id(row), {})
        prior_assoc = safe_int(taxonomy.get("prior_candidate_association_count"), 0)
        prior_depth = safe_int(taxonomy.get("prior_depth_consistent_count"), 0)
        prior_mismatch = safe_int(taxonomy.get("prior_depth_mismatch_count"), 0)
        prior_inside = safe_int(taxonomy.get("prior_inside_mask_count"), 0)
        completion_assoc = safe_int(row.get("completion_associated_heading_count"), 0)
        completion_assoc_depth = safe_int(
            taxonomy.get("completion_associated_depth_consistent_count"),
            safe_int(row.get("completion_depth_consistent_count"), 0),
        )
        completion_depth = safe_int(row.get("completion_depth_consistent_count"), 0)
        completion_inside = safe_int(row.get("completion_inside_mask_count"), 0)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_depth_stagnation_branch_row",
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
                "source_branch_action": row.get("branch_action"),
                "source_branch_reason": row.get("branch_reason"),
                "source_residual_failure_class": row.get("residual_failure_class"),
                "source_residual_failure_tags": list(row.get("residual_failure_tags") or []),
                "prior_relation_depth_evidence_status": taxonomy.get("prior_relation_depth_evidence_status"),
                "prior_standoff_direction_source": row.get("prior_standoff_direction_source"),
                "prior_candidate_association_count": prior_assoc,
                "prior_depth_consistent_count": prior_depth,
                "prior_depth_mismatch_count": prior_mismatch,
                "prior_inside_mask_count": prior_inside,
                "completion_status": row.get("completion_status"),
                "unresolved_reason": row.get("unresolved_reason"),
                "completion_associated_heading_count": completion_assoc,
                "completion_associated_depth_consistent_count": completion_assoc_depth,
                "completion_depth_consistent_count": completion_depth,
                "completion_inside_mask_count": completion_inside,
                "association_present_after_completion": completion_assoc > 0,
                "depth_consistent_signal_present": completion_depth > 0,
                "mask_projection_available": completion_inside > 0,
                "depth_signal_role": depth_signal_role(taxonomy),
                "depth_consistency_improved": completion_depth > prior_depth,
                "depth_consistency_delta": completion_depth - prior_depth,
                "association_delta": completion_assoc - prior_assoc,
                "inside_mask_delta": completion_inside - prior_inside,
                "nonterminal_branch_action": nonterminal_action,
                "branch_status": "depth_stagnation_audit_ready",
                "required_audit_actions": required_actions,
                "required_comparisons": required_comparisons,
                "blocked_shortcuts": blocked_shortcuts,
                "terminal_arbitration_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_request_rows(
    *,
    branch_rows: Sequence[Dict[str, Any]],
    source_request_rows: Sequence[Dict[str, Any]],
    taxonomy_request_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> List[Dict[str, Any]]:
    branch_contract = contract.get("branch_contract") or {}
    nonterminal_action = str(branch_contract.get("expected_nonterminal_branch_action"))
    source_request_by_id = index_by_request(source_request_rows)
    taxonomy_request_by_id = index_by_request(taxonomy_request_rows)
    output: List[Dict[str, Any]] = []
    for row in sort_branch_rows(branch_rows):
        rid = request_id(row)
        source_request = source_request_by_id.get(rid, {})
        taxonomy_request = taxonomy_request_by_id.get(rid, {})
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_depth_stagnation_branch_request",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": source_request.get("rival_identity_request_id") or rid,
                "episode_key": source_request.get("episode_key") or row.get("episode_key"),
                "scene_key": source_request.get("scene_key") or row.get("scene_key"),
                "scene_id": source_request.get("scene_id") or row.get("scene_id"),
                "query": source_request.get("query") or row.get("query"),
                "source_branch_action": source_request.get("branch_action"),
                "source_request_residual_status": source_request.get("request_residual_status")
                or taxonomy_request.get("request_residual_status"),
                "source_recommended_next_action": source_request.get("source_recommended_next_action")
                or taxonomy_request.get("recommended_next_action"),
                "branch_row_count": 1,
                "candidate_ids": [row.get("candidate_id")],
                "residual_failure_class_counts": compact_counter([row.get("source_residual_failure_class")]),
                "direction_counts": compact_counter([row.get("prior_standoff_direction_source")]),
                "prior_candidate_association_count": row.get("prior_candidate_association_count"),
                "prior_depth_consistent_count": row.get("prior_depth_consistent_count"),
                "prior_depth_mismatch_count": row.get("prior_depth_mismatch_count"),
                "prior_inside_mask_count": row.get("prior_inside_mask_count"),
                "completion_associated_heading_count": row.get("completion_associated_heading_count"),
                "completion_associated_depth_consistent_count": row.get(
                    "completion_associated_depth_consistent_count"
                ),
                "completion_depth_consistent_count": row.get("completion_depth_consistent_count"),
                "completion_inside_mask_count": row.get("completion_inside_mask_count"),
                "depth_consistency_delta": row.get("depth_consistency_delta"),
                "association_delta": row.get("association_delta"),
                "depth_stagnation_status": row.get("depth_signal_role"),
                "nonterminal_branch_action": nonterminal_action,
                "request_branch_status": "depth_stagnation_audit_ready",
                "required_audit_actions": list(branch_contract.get("required_branch_actions") or []),
                "required_comparisons": list(branch_contract.get("required_comparisons") or []),
                "blocked_shortcuts": list(branch_contract.get("blocked_shortcuts") or []),
                "terminal_arbitration_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def summarize(
    *,
    contract: Dict[str, Any],
    branch_summary: Dict[str, Any],
    taxonomy_summary: Dict[str, Any],
    source_branch_rows: Sequence[Dict[str, Any]],
    source_request_rows: Sequence[Dict[str, Any]],
    source_taxonomy_rows: Sequence[Dict[str, Any]],
    source_taxonomy_request_rows: Sequence[Dict[str, Any]],
    branch_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    branch_contract = contract.get("branch_contract") or {}
    action_rows = [*branch_rows, *request_rows]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [
        row
        for row in action_rows
        if row.get("terminal_commit") is True or row.get("terminal_arbitration_allowed") is True
    ]
    candidate_commit_rows = [
        row
        for row in action_rows
        if row.get("candidate_commit_allowed") is True
        or str(row.get("nonterminal_branch_action") or "").startswith("commit_")
    ]
    candidate_rejection_rows = [
        row
        for row in action_rows
        if row.get("candidate_rejection_allowed") is True
        or str(row.get("nonterminal_branch_action") or "").startswith("reject_")
    ]

    branch_summary_gate = branch_summary.get("gate") or {}
    taxonomy_gate = taxonomy_summary.get("gate") or {}
    target = branch_rows[0] if branch_rows else {}
    request = request_rows[0] if request_rows else {}
    expected_prior = source_gate.get("expected_prior_counts") or {}
    expected_completion = source_gate.get("expected_completion_counts") or {}
    residual_failure_class_counts = compact_counter(
        row.get("source_residual_failure_class") for row in branch_rows
    )
    direction_counts = compact_counter(row.get("prior_standoff_direction_source") for row in branch_rows)
    nonterminal_counts = compact_counter(row.get("nonterminal_branch_action") for row in branch_rows)
    scene_query = sorted({f"{row.get('scene_key')}/{row.get('query')}" for row in branch_rows})

    gate = {
        "source_branch_handling_gate_passed": branch_summary_gate.get(
            "partial_relation_depth_branch_handling_gate_passed"
        )
        is source_gate.get("partial_relation_depth_branch_handling_gate_passed"),
        "source_taxonomy_gate_passed": taxonomy_gate.get(
            "partial_relation_depth_residual_taxonomy_gate_passed"
        )
        is True,
        "expected_source_branch_rows_passed": len(source_branch_rows)
        == safe_int(source_gate.get("expected_source_branch_rows"), -1),
        "expected_source_request_branch_rows_passed": len(source_request_rows)
        == safe_int(source_gate.get("expected_source_request_branch_rows"), -1),
        "expected_target_branch_rows_passed": len(branch_rows)
        == safe_int(source_gate.get("expected_target_branch_rows"), -1),
        "expected_target_request_rows_passed": len(request_rows)
        == safe_int(source_gate.get("expected_target_request_rows"), -1),
        "expected_target_branch_action_passed": target.get("source_branch_action")
        == source_gate.get("target_branch_action"),
        "expected_request_id_passed": target.get("expanded_retrieval_request_id")
        == source_gate.get("expected_request_id"),
        "expected_episode_key_passed": target.get("episode_key")
        == source_gate.get("expected_episode_key"),
        "expected_scene_query_passed": scene_query
        == [f"{source_gate.get('expected_scene_key')}/{source_gate.get('expected_query')}"],
        "expected_candidate_id_passed": target.get("candidate_id")
        == source_gate.get("expected_candidate_id"),
        "expected_request_residual_status_passed": request.get("source_request_residual_status")
        == source_gate.get("expected_request_residual_status"),
        "expected_recommended_next_action_passed": request.get("source_recommended_next_action")
        == source_gate.get("expected_recommended_next_action"),
        "expected_residual_failure_class_counts_passed": residual_failure_class_counts
        == dict(source_gate.get("expected_residual_failure_class_counts") or {}),
        "expected_residual_failure_tags_passed": sorted(target.get("source_residual_failure_tags") or [])
        == sorted(source_gate.get("expected_residual_failure_tags") or []),
        "expected_direction_counts_passed": direction_counts
        == dict(source_gate.get("expected_direction_counts") or {}),
        "expected_prior_counts_passed": {
            "candidate_association_count": target.get("prior_candidate_association_count"),
            "depth_consistent_count": target.get("prior_depth_consistent_count"),
            "depth_mismatch_count": target.get("prior_depth_mismatch_count"),
            "inside_mask_count": target.get("prior_inside_mask_count"),
            "relation_depth_evidence_status": target.get("prior_relation_depth_evidence_status"),
        }
        == expected_prior,
        "expected_completion_counts_passed": {
            "associated_heading_count": target.get("completion_associated_heading_count"),
            "associated_depth_consistent_count": target.get(
                "completion_associated_depth_consistent_count"
            ),
            "depth_consistent_count": target.get("completion_depth_consistent_count"),
            "inside_mask_count": target.get("completion_inside_mask_count"),
            "completion_status": target.get("completion_status"),
        }
        == expected_completion,
        "expected_rows_with_completion_association_passed": count_rows_gt_zero(
            branch_rows, "completion_associated_heading_count"
        )
        == safe_int(source_gate.get("expected_rows_with_completion_association"), -1),
        "expected_rows_with_zero_completion_association_passed": count_rows_eq_zero(
            branch_rows, "completion_associated_heading_count"
        )
        == safe_int(source_gate.get("expected_rows_with_zero_completion_association"), -1),
        "expected_rows_with_completion_depth_consistent_passed": count_rows_gt_zero(
            branch_rows, "completion_depth_consistent_count"
        )
        == safe_int(source_gate.get("expected_rows_with_completion_depth_consistent"), -1),
        "expected_rows_with_inside_mask_passed": count_rows_gt_zero(
            branch_rows, "completion_inside_mask_count"
        )
        == safe_int(source_gate.get("expected_rows_with_inside_mask"), -1),
        "association_present_gate_passed": all(
            safe_int(row.get("completion_associated_heading_count"), 0) > 0 for row in branch_rows
        ),
        "depth_consistent_signal_gate_passed": all(
            safe_int(row.get("completion_depth_consistent_count"), 0) > 0 for row in branch_rows
        ),
        "depth_stagnation_gate_passed": all(
            row.get("depth_consistency_improved") is False for row in branch_rows
        ),
        "nonterminal_branch_action_passed": nonterminal_counts
        == {str(branch_contract.get("expected_nonterminal_branch_action")): len(branch_rows)},
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(source_gate.get("max_terminal_commit_rows"), -1),
        "candidate_commit_rows_passed": len(candidate_commit_rows)
        <= safe_int(source_gate.get("max_candidate_commit_rows"), -1),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        <= safe_int(source_gate.get("max_candidate_rejection_rows"), -1),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed": False,
    }
    pass_keys = [key for key in gate if key.endswith("_passed")]
    gate["depth_stagnation_branch_gate_passed"] = all(gate[key] is True for key in pass_keys)

    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "branch_summary": str(args.branch_summary),
            "branch_rows": str(args.branch_rows),
            "request_branch_rows": str(args.request_branch_rows),
            "taxonomy_rows": str(args.taxonomy_rows),
            "request_taxonomy_rows": str(args.request_taxonomy_rows),
            "taxonomy_summary": str(args.taxonomy_summary),
        },
        "source_branch_rows": len(source_branch_rows),
        "source_request_branch_rows": len(source_request_rows),
        "source_taxonomy_rows": len(source_taxonomy_rows),
        "source_taxonomy_request_rows": len(source_taxonomy_request_rows),
        "branch_rows": len(branch_rows),
        "request_rows": len(request_rows),
        "target_branch_action": source_gate.get("target_branch_action"),
        "scene_query": scene_query,
        "request_ids": unique_values(branch_rows, "expanded_retrieval_request_id"),
        "episode_keys": unique_values(branch_rows, "episode_key"),
        "candidate_ids": unique_values(branch_rows, "candidate_id"),
        "residual_failure_class_counts": residual_failure_class_counts,
        "direction_counts": direction_counts,
        "prior_counts": {
            "candidate_association_count": target.get("prior_candidate_association_count"),
            "depth_consistent_count": target.get("prior_depth_consistent_count"),
            "depth_mismatch_count": target.get("prior_depth_mismatch_count"),
            "inside_mask_count": target.get("prior_inside_mask_count"),
        },
        "completion_counts": {
            "associated_heading_count": target.get("completion_associated_heading_count"),
            "associated_depth_consistent_count": target.get(
                "completion_associated_depth_consistent_count"
            ),
            "depth_consistent_count": target.get("completion_depth_consistent_count"),
            "inside_mask_count": target.get("completion_inside_mask_count"),
        },
        "depth_consistency_delta": target.get("depth_consistency_delta"),
        "association_delta": target.get("association_delta"),
        "rows_with_completion_association": count_rows_gt_zero(
            branch_rows, "completion_associated_heading_count"
        ),
        "rows_with_zero_completion_association": count_rows_eq_zero(
            branch_rows, "completion_associated_heading_count"
        ),
        "rows_with_completion_depth_consistent": count_rows_gt_zero(
            branch_rows, "completion_depth_consistent_count"
        ),
        "rows_with_inside_mask": count_rows_gt_zero(branch_rows, "completion_inside_mask_count"),
        "nonterminal_branch_action_counts": nonterminal_counts,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "depth_stagnation_audit_ready": gate["depth_stagnation_branch_gate_passed"],
            "recommended_next_task": "define_terminal_utility_contract_only_after_validated_non_gt_branch_outcomes",
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
        },
        "blocked_downstream_tasks": list(contract.get("blocked_downstream_tasks") or []),
        "output_files": {
            "branch_rows": "depth_stagnation_branch_rows.jsonl",
            "request_rows": "depth_stagnation_branch_request_rows.jsonl",
            "summary": "depth_stagnation_branch_summary.json",
        },
        "interpretation": {
            "fact": (
                "This branch materializes one 4ok3usBNeis/sofa depth-stagnation request "
                "without joining evaluation labels."
            ),
            "agent_inference": (
                "Candidate association and depth consistency are present, but relation-depth evidence "
                "remains partial and stagnant. This does not establish ObjectNav goal validity and must "
                "not trigger candidate commit or rejection."
            ),
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.branch_summary = source_path(args, contract, "branch_summary", "branch_handling_summary")
    args.branch_rows = source_path(args, contract, "branch_rows", "branch_rows")
    args.request_branch_rows = source_path(args, contract, "request_branch_rows", "request_branch_rows")
    args.taxonomy_rows = source_path(args, contract, "taxonomy_rows", "taxonomy_rows")
    args.request_taxonomy_rows = source_path(args, contract, "request_taxonomy_rows", "request_taxonomy_rows")
    args.taxonomy_summary = source_path(args, contract, "taxonomy_summary", "taxonomy_summary")

    source_gate = contract.get("source_gate") or {}
    branch_summary = load_json(args.branch_summary)
    taxonomy_summary = load_json(args.taxonomy_summary)
    source_branch_rows = load_jsonl(args.branch_rows)
    source_request_rows = load_jsonl(args.request_branch_rows)
    source_taxonomy_rows = load_jsonl(args.taxonomy_rows)
    source_taxonomy_request_rows = load_jsonl(args.request_taxonomy_rows)
    target_source_branch_rows = target_branch_rows(source_branch_rows, source_gate)
    target_source_request_rows = target_request_branch_rows(source_request_rows, source_gate)
    target_source_taxonomy_rows = target_taxonomy_rows(source_taxonomy_rows, source_gate)
    target_source_taxonomy_request_rows = target_request_taxonomy_rows(
        source_taxonomy_request_rows, source_gate
    )
    branch_rows = build_branch_rows(
        source_rows=target_source_branch_rows,
        taxonomy_rows=target_source_taxonomy_rows,
        contract=contract,
    )
    request_rows = build_request_rows(
        branch_rows=branch_rows,
        source_request_rows=target_source_request_rows,
        taxonomy_request_rows=target_source_taxonomy_request_rows,
        contract=contract,
    )
    summary = summarize(
        contract=contract,
        branch_summary=branch_summary,
        taxonomy_summary=taxonomy_summary,
        source_branch_rows=source_branch_rows,
        source_request_rows=source_request_rows,
        source_taxonomy_rows=source_taxonomy_rows,
        source_taxonomy_request_rows=source_taxonomy_request_rows,
        branch_rows=branch_rows,
        request_rows=request_rows,
        args=args,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "depth_stagnation_branch_rows.jsonl", branch_rows)
    write_jsonl(out_root / "depth_stagnation_branch_request_rows.jsonl", request_rows)
    write_json(out_root / "depth_stagnation_branch_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize frozen nonterminal depth-stagnation branch rows."
    )
    parser.add_argument("--contract", default=Path(CONTRACT_DEFAULT), type=Path)
    parser.add_argument("--out-root", default=Path(OUT_ROOT_DEFAULT), type=Path)
    parser.add_argument("--branch-summary", type=Path)
    parser.add_argument("--branch-rows", type=Path)
    parser.add_argument("--request-branch-rows", type=Path)
    parser.add_argument("--taxonomy-rows", type=Path)
    parser.add_argument("--request-taxonomy-rows", type=Path)
    parser.add_argument("--taxonomy-summary", type=Path)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["depth_stagnation_branch_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
