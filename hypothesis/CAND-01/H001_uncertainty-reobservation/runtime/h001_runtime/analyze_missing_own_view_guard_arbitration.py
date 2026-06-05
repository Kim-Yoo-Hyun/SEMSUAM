import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys
from h001_runtime.analyze_missing_own_view_recheck_evidence import (
    load_json,
    load_jsonl,
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)


SCHEMA_VERSION = "h001.missing_own_view_guard_arbitration.v1"
POLICY_NAME = "negative_missing_support_guard_after_recheck_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_missing_own_view_guard_arbitration_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_missing_own_view_guard_arbitration_v1"

NEGATIVE_GUARD_BRANCH = "negative_missing_support_guard"
GUARD_DEACTIVATED = "deactivate_negative_missing_support_guard_after_recheck"
GUARD_DEFER_PARTIAL = "defer_guard_interpretation_pending_partial_own_view_support_audit"
GUARD_DEFER_ABSENT = "defer_guard_interpretation_pending_absent_own_view_support_audit"
GUARD_DEFER_MISSING = "defer_guard_interpretation_missing_companion_guard"


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def source_path(args: argparse.Namespace, contract: Mapping[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def row_request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def row_candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def candidate_sort_key(candidate_id: str) -> Tuple[int, str]:
    tail = str(candidate_id).rsplit(":", 1)[-1]
    if tail.isdigit():
        return (safe_int(tail, 999999), str(candidate_id))
    return (999999, str(candidate_id))


def group_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(row)
    return grouped


def object_branch_index(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str], Mapping[str, Any]]:
    indexed: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        key = (row_request_id(row), row_candidate_id(row))
        if key[0] and key[1]:
            indexed[key] = row
    return indexed


def has_negative_guard_branch(row: Mapping[str, Any]) -> bool:
    branches = {str(item) for item in row.get("candidate_branch_names") or []}
    actions = {str(item) for item in row.get("candidate_branch_actions") or []}
    return NEGATIVE_GUARD_BRANCH in branches or "guard_negative_missing_support" in actions


def guard_decision(row: Mapping[str, Any], branch_row: Mapping[str, Any]) -> Tuple[str, str, str]:
    status = str(row.get("own_view_support_status") or "")
    companion_branch = str(row.get("companion_guard_branch") or "")
    guard_ready = row.get("negative_missing_support_guard_ready") is True
    branch_ready = has_negative_guard_branch(branch_row)
    if (
        status == "candidate_own_view_support_acquired"
        and companion_branch == NEGATIVE_GUARD_BRANCH
        and guard_ready
        and branch_ready
    ):
        if safe_int(row.get("recheck_unassociated_view_count"), 0) > 0:
            return (
                GUARD_DEACTIVATED,
                "own_view_support_acquired_after_recheck_with_unassociated_frame_audit_preserved",
                "keep_guard_deactivated_but_report_unassociated_view_audit",
            )
        return (
            GUARD_DEACTIVATED,
            "own_view_support_acquired_after_recheck",
            "deactivate_negative_missing_support_guard_after_recheck",
        )
    if status == "candidate_own_view_support_partial":
        return (
            GUARD_DEFER_PARTIAL,
            "candidate_support_remains_partial_after_recheck",
            "defer_guard_interpretation_pending_partial_own_view_support_audit",
        )
    if status == "candidate_own_view_support_absent":
        return (
            GUARD_DEFER_ABSENT,
            "candidate_support_absent_after_recheck",
            "defer_guard_interpretation_pending_absent_own_view_support_audit",
        )
    return (
        GUARD_DEFER_MISSING,
        "missing_or_mismatched_companion_negative_guard_metadata",
        "defer_guard_interpretation_missing_companion_guard",
    )


def build_candidate_rows(
    candidate_rows: Sequence[Mapping[str, Any]],
    object_branch_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    branch_by_candidate = object_branch_index(object_branch_rows)
    output: List[Dict[str, Any]] = []
    for row in sorted(
        candidate_rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            candidate_sort_key(row_candidate_id(item)),
        ),
    ):
        request_id = row_request_id(row)
        candidate_id = row_candidate_id(row)
        branch_row = branch_by_candidate.get((request_id, candidate_id), {})
        decision, reason, action = guard_decision(row, branch_row)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_guard_candidate_arbitration",
                "row_type": "candidate_guard_decision",
                "contract_name": "missing_own_view_guard_arbitration_v1",
                "source_contract_name": row.get("contract_name"),
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id") or request_id,
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "target_candidate_id": candidate_id,
                "candidate_id": candidate_id,
                "target_candidate_role": row.get("target_candidate_role"),
                "target_generated_rank": row.get("target_generated_rank"),
                "target_semantic_rank": row.get("target_semantic_rank"),
                "base_candidate_evidence_class": row.get("base_candidate_evidence_class"),
                "base_candidate_specific_support": row.get("base_candidate_specific_support") is True,
                "base_strong_own_view_evidence": row.get("base_strong_own_view_evidence") is True,
                "relation_depth_evidence_status": row.get("relation_depth_evidence_status"),
                "relation_associated_heading_count": safe_int(row.get("relation_associated_heading_count"), 0),
                "relation_depth_consistent_count": safe_int(row.get("relation_depth_consistent_count"), 0),
                "own_view_support_status": row.get("own_view_support_status"),
                "companion_guard_branch": row.get("companion_guard_branch"),
                "companion_guard_present": row.get("companion_guard_present") is True,
                "companion_guard_role": row.get("companion_guard_role"),
                "object_relation_negative_guard_present": has_negative_guard_branch(branch_row),
                "negative_missing_support_guard_ready": row.get("negative_missing_support_guard_ready") is True,
                "source_guard_interpretation_status": row.get("guard_interpretation_status"),
                "recheck_view_count": safe_int(row.get("recheck_view_count"), 0),
                "recheck_candidate_associated_view_count": safe_int(
                    row.get("recheck_candidate_associated_view_count"), 0
                ),
                "recheck_unassociated_view_count": safe_int(row.get("recheck_unassociated_view_count"), 0),
                "recheck_depth_consistent_association_count": safe_int(
                    row.get("recheck_depth_consistent_association_count"), 0
                ),
                "recheck_associated_heading_count": safe_int(row.get("recheck_associated_heading_count"), 0),
                "recheck_projected_pixel_inside_mask_count": safe_int(
                    row.get("recheck_projected_pixel_inside_mask_count"), 0
                ),
                "unassociated_source_plan_indices": list(row.get("unassociated_source_plan_indices") or []),
                "guard_arbitration_decision": decision,
                "guard_arbitration_reason": reason,
                "guard_deactivated": decision == GUARD_DEACTIVATED,
                "guard_deferred": decision != GUARD_DEACTIVATED,
                "promotable_terminal_outcome": False,
                "promotable_branch_outcome": False,
                "recommended_nonterminal_action": action,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def request_status(group: Sequence[Mapping[str, Any]]) -> Tuple[str, str]:
    deactivated = sum(1 for row in group if row.get("guard_arbitration_decision") == GUARD_DEACTIVATED)
    deferred = len(group) - deactivated
    if len(group) > 0 and deferred == 0:
        return (
            "missing_own_view_guard_closed_as_nonterminal_evidence",
            "close_missing_own_view_guard_as_nonterminal_evidence",
        )
    if deactivated > 0:
        return (
            "missing_own_view_guard_partially_deactivated_with_deferred_candidates",
            "audit_deferred_guard_candidates_before_terminal_utility",
        )
    return (
        "missing_own_view_guard_deferred_without_deactivation",
        "defer_missing_own_view_guard_arbitration",
    )


def build_request_rows(candidate_guard_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for request_id, group in sorted(
        group_by_request(candidate_guard_rows).items(),
        key=lambda item: request_sort_key(item[0]),
    ):
        group = sorted(group, key=lambda item: candidate_sort_key(row_candidate_id(item)))
        first = group[0]
        decision_counts = Counter(str(row.get("guard_arbitration_decision")) for row in group)
        deactivated = decision_counts.get(GUARD_DEACTIVATED, 0)
        deferred = len(group) - deactivated
        status, action = request_status(group)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_guard_request_arbitration",
                "row_type": "request_guard_summary",
                "contract_name": "missing_own_view_guard_arbitration_v1",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": first.get("rival_identity_request_id") or request_id,
                "episode_key": first.get("episode_key"),
                "scene_key": first.get("scene_key"),
                "scene_id": first.get("scene_id"),
                "query": first.get("query"),
                "target_candidate_count": len(group),
                "target_candidate_ids": [row_candidate_id(row) for row in group],
                "guard_deactivated_candidate_count": deactivated,
                "guard_deferred_candidate_count": deferred,
                "negative_missing_support_guard_ready_count": sum(
                    1 for row in group if row.get("negative_missing_support_guard_ready") is True
                ),
                "object_relation_negative_guard_present_count": sum(
                    1 for row in group if row.get("object_relation_negative_guard_present") is True
                ),
                "own_view_support_acquired_candidate_count": sum(
                    1
                    for row in group
                    if row.get("own_view_support_status") == "candidate_own_view_support_acquired"
                ),
                "unassociated_frame_count": sum(
                    safe_int(row.get("recheck_unassociated_view_count"), 0) for row in group
                ),
                "candidate_rejection_count": 0,
                "candidate_commit_count": 0,
                "terminal_commit_count": 0,
                "promotable_terminal_outcome_count": 0,
                "guard_arbitration_decision_counts": dict(sorted(decision_counts.items())),
                "request_guard_status": status,
                "recommended_nonterminal_action": action,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_unassociated_audit_summary(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in rows:
        output.append(
            {
                "expanded_retrieval_request_id": row_request_id(row),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "target_candidate_id": row_candidate_id(row),
                "source_plan_index": row.get("source_plan_index"),
                "audit_reason": row.get("audit_reason"),
                "preserved_as": "nonterminal_unassociated_frame_audit",
            }
        )
    return output


def simpler_alternatives(candidate_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    acquired = [
        row
        for row in candidate_rows
        if row.get("own_view_support_status") == "candidate_own_view_support_acquired"
    ]
    any_unassociated = [
        row for row in candidate_rows if safe_int(row.get("recheck_unassociated_view_count"), 0) > 0
    ]
    all_associated = [
        row
        for row in candidate_rows
        if safe_int(row.get("recheck_view_count"), 0) > 0
        and safe_int(row.get("recheck_candidate_associated_view_count"), 0)
        == safe_int(row.get("recheck_view_count"), 0)
    ]
    best_by_request = 0
    for _, group in group_by_request(candidate_rows).items():
        if group:
            best_by_request += 1
    return {
        "reject_missing_own_view_without_recheck": {
            "decision": "blocked_by_contract",
            "would_reject_candidate_rows_before_recheck": len(candidate_rows),
            "failure_reason": "absence of own-view support is the trigger for active observation, not rejection",
        },
        "reject_if_any_recheck_view_unassociated": {
            "decision": "rejected_as_terminal_shortcut",
            "would_reject_candidate_rows": len(any_unassociated),
            "failure_reason": "single unassociated recheck views are audit rows after support acquisition",
        },
        "commit_if_candidate_own_view_support_acquired": {
            "decision": "diagnostic_only_rejected_as_goal_validity_shortcut",
            "would_commit_candidate_rows": len(acquired),
            "failure_reason": "own-view support acquisition is evidence availability, not ObjectNav goal validity",
        },
        "commit_if_all_recheck_views_associated": {
            "decision": "diagnostic_only_rejected_as_goal_validity_shortcut",
            "would_commit_candidate_rows": len(all_associated),
            "failure_reason": "full association still lacks a goal-validity arbitration rule",
        },
        "association_count_best_after_recheck": {
            "decision": "diagnostic_only_rejected_as_ranking_shortcut",
            "would_select_request_rows": best_by_request,
            "failure_reason": "association count alone cannot distinguish valid goal instance from visible wrong instance",
        },
        "defer_all_guard_rows": {
            "decision": "safe_but_inert",
            "would_defer_candidate_rows": len(candidate_rows),
            "failure_reason": "it preserves safety but discards the reviewer-facing evidence that recheck support deactivates the guard",
        },
    }


def requested_outputs(contract: Mapping[str, Any]) -> Dict[str, str]:
    outputs = contract.get("required_outputs") or {}
    return {
        "candidate_guard_decision_rows": str(
            outputs.get("candidate_guard_decision_rows", "missing_own_view_guard_candidate_rows.jsonl")
        ),
        "request_guard_summary_rows": str(
            outputs.get("request_guard_summary_rows", "missing_own_view_guard_request_rows.jsonl")
        ),
        "summary": str(outputs.get("summary", "missing_own_view_guard_arbitration_summary.json")),
    }


def gate_value(summary: Mapping[str, Any], key: str) -> Any:
    return (summary.get("gate") or {}).get(key)


def build_summary(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    source_summary: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    unassociated_rows: Sequence[Mapping[str, Any]],
    candidate_guard_rows: Sequence[Mapping[str, Any]],
    request_guard_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    minimum = contract.get("minimum_rule_gate") or {}
    action_rows = [*candidate_guard_rows, *request_guard_rows]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    candidate_commit_rows = [row for row in action_rows if row.get("candidate_commit") is True]
    candidate_rejection_rows = [row for row in action_rows if row.get("candidate_rejection") is True]
    promotable_terminal_rows = [
        row for row in action_rows if row.get("promotable_terminal_outcome") is True
    ]
    deactivated_candidate_rows = [
        row for row in candidate_guard_rows if row.get("guard_arbitration_decision") == GUARD_DEACTIVATED
    ]
    deferred_candidate_rows = [
        row for row in candidate_guard_rows if row.get("guard_arbitration_decision") != GUARD_DEACTIVATED
    ]
    deactivated_request_rows = [
        row
        for row in request_guard_rows
        if row.get("request_guard_status") == "missing_own_view_guard_closed_as_nonterminal_evidence"
    ]
    uses_gt_for_action = any(row.get("uses_gt_for_action") is True for row in action_rows)
    source_gate_passed = bool(gate_value(source_summary, "missing_own_view_recheck_evidence_gate_passed"))
    gate = {
        "source_missing_own_view_recheck_evidence_gate_passed": source_gate_passed
        is bool(minimum.get("source_missing_own_view_recheck_evidence_gate_passed", True)),
        "expected_candidate_guard_decision_rows_passed": len(candidate_guard_rows)
        == safe_int(minimum.get("expected_candidate_guard_decision_rows"), -1),
        "expected_request_guard_summary_rows_passed": len(request_guard_rows)
        == safe_int(minimum.get("expected_request_guard_summary_rows"), -1),
        "expected_unassociated_frame_audit_rows_preserved_passed": len(unassociated_rows)
        == safe_int(minimum.get("expected_unassociated_frame_audit_rows_preserved"), -1),
        "expected_guard_deactivated_candidate_rows_passed": len(deactivated_candidate_rows)
        == safe_int(minimum.get("expected_guard_deactivated_candidate_rows"), -1),
        "expected_guard_deactivated_request_rows_passed": len(deactivated_request_rows)
        == safe_int(minimum.get("expected_guard_deactivated_request_rows"), -1),
        "expected_guard_deferred_candidate_rows_passed": len(deferred_candidate_rows)
        == safe_int(minimum.get("expected_guard_deferred_candidate_rows"), -1),
        "expected_candidate_rejection_rows_passed": len(candidate_rejection_rows)
        == safe_int(minimum.get("expected_candidate_rejection_rows"), -1),
        "expected_candidate_commit_rows_passed": len(candidate_commit_rows)
        == safe_int(minimum.get("expected_candidate_commit_rows"), -1),
        "expected_terminal_commit_rows_passed": len(terminal_rows)
        == safe_int(minimum.get("expected_terminal_commit_rows"), -1),
        "expected_promotable_terminal_outcome_rows_passed": len(promotable_terminal_rows)
        == safe_int(minimum.get("expected_promotable_terminal_outcome_rows"), -1),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "uses_gt_for_action_passed": (not uses_gt_for_action) is bool(
            minimum.get("uses_gt_for_action") is False
        ),
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["missing_own_view_guard_arbitration_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key not in {"terminal_utility_validation_allowed", "paper_claim_allowed"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source": {
            "missing_own_view_recheck_summary": str(args.missing_own_view_recheck_summary),
            "candidate_evidence_rows": str(args.candidate_evidence_rows),
            "request_summary_rows": str(args.request_summary_rows),
            "unassociated_frame_audit_rows": str(args.unassociated_frame_audit_rows),
            "object_relation_branch_candidate_rows": str(args.object_relation_branch_candidate_rows),
        },
        "source_missing_own_view_recheck_evidence_gate_passed": source_gate_passed,
        "source_candidate_evidence_rows": len(candidate_rows),
        "source_request_summary_rows": len(request_rows),
        "source_unassociated_frame_audit_rows": len(unassociated_rows),
        "candidate_guard_decision_rows": len(candidate_guard_rows),
        "request_guard_summary_rows": len(request_guard_rows),
        "unassociated_frame_audit_rows_preserved": len(unassociated_rows),
        "guard_deactivated_candidate_rows": len(deactivated_candidate_rows),
        "guard_deactivated_request_rows": len(deactivated_request_rows),
        "guard_deferred_candidate_rows": len(deferred_candidate_rows),
        "candidate_status_counts": compact_counter(row.get("own_view_support_status") for row in candidate_rows),
        "guard_arbitration_decision_counts": compact_counter(
            row.get("guard_arbitration_decision") for row in candidate_guard_rows
        ),
        "candidate_nonterminal_action_counts": compact_counter(
            row.get("recommended_nonterminal_action") for row in candidate_guard_rows
        ),
        "request_guard_status_counts": compact_counter(
            row.get("request_guard_status") for row in request_guard_rows
        ),
        "request_nonterminal_action_counts": compact_counter(
            row.get("recommended_nonterminal_action") for row in request_guard_rows
        ),
        "negative_missing_support_guard_ready_candidate_rows": sum(
            1 for row in candidate_guard_rows if row.get("negative_missing_support_guard_ready") is True
        ),
        "object_relation_negative_guard_present_candidate_rows": sum(
            1 for row in candidate_guard_rows if row.get("object_relation_negative_guard_present") is True
        ),
        "target_candidates_with_full_4_of_4_association": sum(
            1
            for row in candidate_rows
            if safe_int(row.get("recheck_view_count"), 0) > 0
            and safe_int(row.get("recheck_candidate_associated_view_count"), 0)
            == safe_int(row.get("recheck_view_count"), 0)
        ),
        "target_candidates_with_partial_3_of_4_association": sum(
            1
            for row in candidate_rows
            if safe_int(row.get("recheck_candidate_associated_view_count"), 0) == 3
        ),
        "unassociated_frame_audit_rows": build_unassociated_audit_summary(unassociated_rows),
        "simpler_alternatives": simpler_alternatives(candidate_guard_rows),
        "diagnostic_conclusion": {
            "missing_own_view_guard_arbitration_signal_ready": gate[
                "missing_own_view_guard_arbitration_gate_passed"
            ],
            "recommended_next_task": "freeze_missing_own_view_guard_branch_closure_or_select_next_label_free_family"
            if gate["missing_own_view_guard_arbitration_gate_passed"]
            else "diagnose_missing_own_view_guard_arbitration_mismatch",
            "reason": "negative_missing_support_guard is deactivated after recheck support acquisition while terminal commit/rejection remains blocked"
            if gate["missing_own_view_guard_arbitration_gate_passed"]
            else "guard arbitration did not satisfy the frozen nonterminal rule gate",
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "promotable_terminal_outcome_rows": len(promotable_terminal_rows),
        "uses_gt_for_action": uses_gt_for_action,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            key: str(Path(str(args.out_root)) / value)
            for key, value in requested_outputs(contract).items()
        },
        "interpretation": {
            "fact": "The analyzer interprets the deferred missing-support guard after recheck evidence has been written.",
            "agent_inference": "Acquired own-view support deactivates the negative guard but does not justify candidate commit, candidate rejection, terminal utility, or paper claims.",
            "paper_claim": "No paper claim is allowed from this analyzer alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    args.missing_own_view_recheck_summary = source_path(
        args, contract, "missing_own_view_recheck_summary", "missing_own_view_recheck_summary"
    )
    args.candidate_evidence_rows = source_path(
        args, contract, "candidate_evidence_rows", "candidate_evidence_rows"
    )
    args.request_summary_rows = source_path(args, contract, "request_summary_rows", "request_summary_rows")
    args.unassociated_frame_audit_rows = source_path(
        args, contract, "unassociated_frame_audit_rows", "unassociated_frame_audit_rows"
    )
    args.object_relation_branch_candidate_rows = source_path(
        args,
        contract,
        "object_relation_branch_candidate_rows",
        "object_relation_branch_candidate_rows",
    )
    source_summary = load_json(args.missing_own_view_recheck_summary)
    candidate_rows = load_jsonl(args.candidate_evidence_rows)
    request_rows = load_jsonl(args.request_summary_rows)
    unassociated_rows = load_jsonl(args.unassociated_frame_audit_rows)
    object_branch_rows = load_jsonl(args.object_relation_branch_candidate_rows)
    candidate_guard_rows = build_candidate_rows(candidate_rows, object_branch_rows)
    request_guard_rows = build_request_rows(candidate_guard_rows)
    summary = build_summary(
        args=args,
        contract=contract,
        source_summary=source_summary,
        candidate_rows=candidate_rows,
        request_rows=request_rows,
        unassociated_rows=unassociated_rows,
        candidate_guard_rows=candidate_guard_rows,
        request_guard_rows=request_guard_rows,
    )
    out_root = Path(args.out_root)
    outputs = requested_outputs(contract)
    write_jsonl(out_root / outputs["candidate_guard_decision_rows"], candidate_guard_rows)
    write_jsonl(out_root / outputs["request_guard_summary_rows"], request_guard_rows)
    write_json(out_root / outputs["summary"], summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interpret deferred missing-own-view negative guard after recheck evidence."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--missing-own-view-recheck-summary")
    parser.add_argument("--candidate-evidence-rows")
    parser.add_argument("--request-summary-rows")
    parser.add_argument("--unassociated-frame-audit-rows")
    parser.add_argument("--object-relation-branch-candidate-rows")
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["missing_own_view_guard_arbitration_gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
