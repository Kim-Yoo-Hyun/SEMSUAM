import argparse
import json
from collections import Counter
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


SCHEMA_VERSION = "h001.missing_own_view_guard_branch_closure.v1"
POLICY_NAME = "missing_own_view_guard_branch_closure_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_missing_own_view_guard_branch_closure_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_missing_own_view_guard_branch_closure_v1"

SELECTED_BRANCH = "correct_candidate_missing_own_view_support"
GUARD_BRANCH = "negative_missing_support_guard"
GUARD_DEACTIVATED = "deactivate_negative_missing_support_guard_after_recheck"


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


def branch_count(rows: Sequence[Mapping[str, Any]], branch_name: str) -> int:
    count = 0
    for row in rows:
        branches = {str(item) for item in row.get("request_branch_names") or []}
        if branch_name in branches:
            count += 1
    return count


def candidate_branch_count(rows: Sequence[Mapping[str, Any]], branch_name: str) -> int:
    count = 0
    for row in rows:
        branches = {str(item) for item in row.get("candidate_branch_names") or []}
        if branch_name in branches:
            count += 1
    return count


def request_index(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {row_request_id(row): row for row in rows if row_request_id(row)}


def candidate_index(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str], Mapping[str, Any]]:
    return {
        (row_request_id(row), row_candidate_id(row)): row
        for row in rows
        if row_request_id(row) and row_candidate_id(row)
    }


def branch_names(row: Mapping[str, Any], key: str) -> List[str]:
    return [str(item) for item in row.get(key) or []]


def build_branch_status_rows(
    *,
    contract: Mapping[str, Any],
    object_request_rows: Sequence[Mapping[str, Any]],
    object_candidate_rows: Sequence[Mapping[str, Any]],
    guard_summary: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    closure = contract.get("closure_scope") or {}
    selected_request_rows = branch_count(object_request_rows, SELECTED_BRANCH)
    guard_request_rows = branch_count(object_request_rows, GUARD_BRANCH)
    selected_candidate_rows = candidate_branch_count(object_candidate_rows, SELECTED_BRANCH)
    guard_candidate_rows = candidate_branch_count(object_candidate_rows, GUARD_BRANCH)
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "action_missing_own_view_branch_status_closure",
            "row_type": "branch_status",
            "policy": POLICY_NAME,
            "branch_name": SELECTED_BRANCH,
            "closure_status": closure.get("selected_branch_closure_status"),
            "closure_reason": "own_view_support_was_acquired_but_goal_validity_remains_unresolved",
            "source_request_rows": selected_request_rows,
            "source_candidate_rows": selected_candidate_rows,
            "closed_request_rows": safe_int(guard_summary.get("request_guard_summary_rows"), 0),
            "closed_candidate_rows": safe_int(guard_summary.get("candidate_guard_decision_rows"), 0),
            "promotable_terminal_outcome_rows": 0,
            "terminal_commit": False,
            "candidate_commit": False,
            "candidate_rejection": False,
            "uses_gt_for_action": False,
            "paper_claim_allowed": False,
        },
        {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "action_missing_own_view_branch_status_closure",
            "row_type": "branch_status",
            "policy": POLICY_NAME,
            "branch_name": GUARD_BRANCH,
            "closure_status": closure.get("guard_branch_closure_status"),
            "closure_reason": "negative_missing_support_guard_deactivated_after_recheck_support_acquisition",
            "source_request_rows": guard_request_rows,
            "source_candidate_rows": guard_candidate_rows,
            "closed_request_rows": safe_int(guard_summary.get("guard_deactivated_request_rows"), 0),
            "closed_candidate_rows": safe_int(guard_summary.get("guard_deactivated_candidate_rows"), 0),
            "promotable_terminal_outcome_rows": 0,
            "terminal_commit": False,
            "candidate_commit": False,
            "candidate_rejection": False,
            "uses_gt_for_action": False,
            "paper_claim_allowed": False,
        },
    ]


def build_candidate_rows(
    guard_candidate_rows: Sequence[Mapping[str, Any]],
    object_candidate_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    object_by_candidate = candidate_index(object_candidate_rows)
    rows: List[Dict[str, Any]] = []
    for row in sorted(
        guard_candidate_rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            candidate_sort_key(row_candidate_id(item)),
        ),
    ):
        request_id = row_request_id(row)
        candidate_id = row_candidate_id(row)
        object_row = object_by_candidate.get((request_id, candidate_id), {})
        object_branches = branch_names(object_row, "candidate_branch_names")
        guard_deactivated = row.get("guard_arbitration_decision") == GUARD_DEACTIVATED
        selected_present = SELECTED_BRANCH in set(object_branches)
        guard_present = GUARD_BRANCH in set(object_branches)
        closed = guard_deactivated and selected_present and guard_present
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_guard_branch_candidate_closure",
                "row_type": "candidate_branch_closure",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id") or request_id,
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": candidate_id,
                "target_candidate_id": candidate_id,
                "source_candidate_branch_names": object_branches,
                "closed_branch_names": [SELECTED_BRANCH, GUARD_BRANCH] if closed else [],
                "selected_branch_closure_status": (
                    "closed_as_evidence_acquired_but_nonpromotable_goal_validity"
                    if closed
                    else "closure_deferred_missing_selected_branch_or_guard_deactivation"
                ),
                "guard_branch_closure_status": (
                    "closed_as_deactivated_after_recheck_support_acquisition"
                    if closed
                    else "closure_deferred_missing_guard_branch_or_deactivation"
                ),
                "closure_reason": (
                    "own_view_support_acquired_and_negative_guard_deactivated_without_terminal_action"
                    if closed
                    else "candidate_branch_closure_requirements_not_satisfied"
                ),
                "own_view_support_status": row.get("own_view_support_status"),
                "guard_arbitration_decision": row.get("guard_arbitration_decision"),
                "guard_arbitration_reason": row.get("guard_arbitration_reason"),
                "guard_deactivated": row.get("guard_deactivated") is True,
                "guard_deferred": row.get("guard_deferred") is True,
                "recheck_view_count": safe_int(row.get("recheck_view_count"), 0),
                "recheck_candidate_associated_view_count": safe_int(
                    row.get("recheck_candidate_associated_view_count"), 0
                ),
                "recheck_unassociated_view_count": safe_int(row.get("recheck_unassociated_view_count"), 0),
                "promotable_terminal_outcome": False,
                "recommended_nonterminal_action": "close_missing_own_view_guard_candidate_branch_as_nonterminal",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_request_rows(
    guard_request_rows: Sequence[Mapping[str, Any]],
    object_request_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    object_by_request = request_index(object_request_rows)
    rows: List[Dict[str, Any]] = []
    for row in sorted(guard_request_rows, key=lambda item: request_sort_key(row_request_id(item))):
        request_id = row_request_id(row)
        object_row = object_by_request.get(request_id, {})
        object_branches = branch_names(object_row, "request_branch_names")
        closed = (
            row.get("request_guard_status") == "missing_own_view_guard_closed_as_nonterminal_evidence"
            and SELECTED_BRANCH in set(object_branches)
            and GUARD_BRANCH in set(object_branches)
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_guard_branch_request_closure",
                "row_type": "request_branch_closure",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id") or request_id,
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "source_request_branch_names": object_branches,
                "closed_branch_names": [SELECTED_BRANCH, GUARD_BRANCH] if closed else [],
                "request_closure_status": (
                    "missing_own_view_and_negative_guard_branches_closed_nonterminal"
                    if closed
                    else "missing_own_view_guard_branch_closure_deferred"
                ),
                "closure_reason": (
                    "all selected branch candidates acquired support and all negative guard rows were deactivated"
                    if closed
                    else "request_branch_closure_requirements_not_satisfied"
                ),
                "target_candidate_count": safe_int(row.get("target_candidate_count"), 0),
                "target_candidate_ids": list(row.get("target_candidate_ids") or []),
                "guard_deactivated_candidate_count": safe_int(row.get("guard_deactivated_candidate_count"), 0),
                "guard_deferred_candidate_count": safe_int(row.get("guard_deferred_candidate_count"), 0),
                "own_view_support_acquired_candidate_count": safe_int(
                    row.get("own_view_support_acquired_candidate_count"), 0
                ),
                "unassociated_frame_count": safe_int(row.get("unassociated_frame_count"), 0),
                "promotable_terminal_outcome_count": 0,
                "recommended_nonterminal_action": "close_missing_own_view_guard_request_branch_as_nonterminal",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def requested_outputs(contract: Mapping[str, Any]) -> Dict[str, str]:
    outputs = contract.get("expected_outputs") or {}
    return {
        "branch_status_rows": str(outputs.get("branch_status_rows", "missing_own_view_guard_branch_status_rows.jsonl")),
        "request_closure_rows": str(outputs.get("request_closure_rows", "missing_own_view_guard_branch_request_rows.jsonl")),
        "candidate_closure_rows": str(outputs.get("candidate_closure_rows", "missing_own_view_guard_branch_candidate_rows.jsonl")),
        "summary": str(outputs.get("summary", "missing_own_view_guard_branch_closure_summary.json")),
    }


def gate_value(summary: Mapping[str, Any], key: str) -> Any:
    return (summary.get("gate") or {}).get(key)


def build_summary(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    object_summary: Mapping[str, Any],
    guard_summary: Mapping[str, Any],
    unique_summary: Mapping[str, Any],
    residual_summary: Mapping[str, Any],
    object_request_rows: Sequence[Mapping[str, Any]],
    object_candidate_rows: Sequence[Mapping[str, Any]],
    branch_status_rows: Sequence[Mapping[str, Any]],
    request_closure_rows: Sequence[Mapping[str, Any]],
    candidate_closure_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    required = contract.get("required_gates") or {}
    action_rows = [*branch_status_rows, *request_closure_rows, *candidate_closure_rows]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    candidate_commit_rows = [row for row in action_rows if row.get("candidate_commit") is True]
    candidate_rejection_rows = [row for row in action_rows if row.get("candidate_rejection") is True]
    promotable_rows = [row for row in action_rows if row.get("promotable_terminal_outcome") is True]
    selected_request_rows = branch_count(object_request_rows, SELECTED_BRANCH)
    selected_candidate_rows = candidate_branch_count(object_candidate_rows, SELECTED_BRANCH)
    guard_request_rows = branch_count(object_request_rows, GUARD_BRANCH)
    guard_candidate_rows = candidate_branch_count(object_candidate_rows, GUARD_BRANCH)
    closed_request_rows = [
        row
        for row in request_closure_rows
        if row.get("request_closure_status")
        == "missing_own_view_and_negative_guard_branches_closed_nonterminal"
    ]
    closed_candidate_rows = [
        row
        for row in candidate_closure_rows
        if row.get("closed_branch_names") == [SELECTED_BRANCH, GUARD_BRANCH]
    ]
    gate = {
        "object_relation_branch_router_gate_passed": gate_value(
            object_summary, "branch_evidence_router_gate_passed"
        )
        is required.get("object_relation_branch_router_gate_passed"),
        "missing_own_view_guard_arbitration_gate_passed": gate_value(
            guard_summary, "missing_own_view_guard_arbitration_gate_passed"
        )
        is required.get("missing_own_view_guard_arbitration_gate_passed"),
        "expected_selected_branch_request_rows_passed": selected_request_rows
        == safe_int(required.get("expected_selected_branch_request_rows"), -1),
        "expected_selected_branch_candidate_rows_passed": selected_candidate_rows
        == safe_int(required.get("expected_selected_branch_candidate_rows"), -1),
        "expected_guard_branch_request_rows_passed": guard_request_rows
        == safe_int(required.get("expected_guard_branch_request_rows"), -1),
        "expected_guard_branch_candidate_rows_passed": guard_candidate_rows
        == safe_int(required.get("expected_guard_branch_candidate_rows"), -1),
        "expected_request_closure_rows_passed": len(closed_request_rows)
        == safe_int(required.get("expected_request_closure_rows"), -1),
        "expected_candidate_closure_rows_passed": len(closed_candidate_rows)
        == safe_int(required.get("expected_candidate_closure_rows"), -1),
        "expected_branch_status_rows_passed": len(branch_status_rows)
        == safe_int(required.get("expected_branch_status_rows"), -1),
        "expected_guard_deactivated_candidate_rows_passed": safe_int(
            guard_summary.get("guard_deactivated_candidate_rows"), 0
        )
        == safe_int(required.get("expected_guard_deactivated_candidate_rows"), -1),
        "expected_guard_deactivated_request_rows_passed": safe_int(
            guard_summary.get("guard_deactivated_request_rows"), 0
        )
        == safe_int(required.get("expected_guard_deactivated_request_rows"), -1),
        "expected_guard_deferred_candidate_rows_passed": safe_int(
            guard_summary.get("guard_deferred_candidate_rows"), 0
        )
        == safe_int(required.get("expected_guard_deferred_candidate_rows"), -1),
        "expected_promotable_terminal_outcome_rows_passed": len(promotable_rows)
        == safe_int(required.get("expected_promotable_terminal_outcome_rows"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        == safe_int(required.get("terminal_commit_rows"), -1),
        "candidate_commit_rows_passed": len(candidate_commit_rows)
        == safe_int(required.get("candidate_commit_rows"), -1),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        == safe_int(required.get("candidate_rejection_rows"), -1),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        == safe_int(required.get("action_evidence_forbidden_key_count"), -1),
        "uses_gt_for_action_passed": not any(row.get("uses_gt_for_action") is True for row in action_rows)
        and required.get("uses_gt_for_action") is False,
        "paper_claim_allowed": False,
    }
    gate["missing_own_view_guard_branch_closure_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source": {
            "object_relation_branch_summary": str(args.object_relation_branch_summary),
            "object_relation_branch_request_rows": str(args.object_relation_branch_request_rows),
            "object_relation_branch_candidate_rows": str(args.object_relation_branch_candidate_rows),
            "missing_own_view_guard_arbitration_summary": str(
                args.missing_own_view_guard_arbitration_summary
            ),
            "missing_own_view_guard_candidate_rows": str(args.missing_own_view_guard_candidate_rows),
            "missing_own_view_guard_request_rows": str(args.missing_own_view_guard_request_rows),
            "unique_support_branch_closure_summary": str(args.unique_support_branch_closure_summary),
            "residual_branch_closure_summary": str(args.residual_branch_closure_summary),
        },
        "context_gates": {
            "unique_support_branch_closure_gate_passed": gate_value(
                unique_summary, "unique_support_branch_closure_gate_passed"
            ),
            "residual_branch_closure_gate_passed": gate_value(
                residual_summary, "residual_branch_closure_gate_passed"
            ),
        },
        "selected_branch": SELECTED_BRANCH,
        "paired_guard_branch": GUARD_BRANCH,
        "selected_branch_request_rows": selected_request_rows,
        "selected_branch_candidate_rows": selected_candidate_rows,
        "guard_branch_request_rows": guard_request_rows,
        "guard_branch_candidate_rows": guard_candidate_rows,
        "branch_status_rows": len(branch_status_rows),
        "request_closure_rows": len(request_closure_rows),
        "candidate_closure_rows": len(candidate_closure_rows),
        "closed_request_rows": len(closed_request_rows),
        "closed_candidate_rows": len(closed_candidate_rows),
        "branch_status_counts": compact_counter(row.get("closure_status") for row in branch_status_rows),
        "request_closure_status_counts": compact_counter(
            row.get("request_closure_status") for row in request_closure_rows
        ),
        "candidate_selected_branch_closure_status_counts": compact_counter(
            row.get("selected_branch_closure_status") for row in candidate_closure_rows
        ),
        "guard_arbitration_decision_counts": guard_summary.get("guard_arbitration_decision_counts") or {},
        "guard_deactivated_candidate_rows": safe_int(guard_summary.get("guard_deactivated_candidate_rows"), 0),
        "guard_deactivated_request_rows": safe_int(guard_summary.get("guard_deactivated_request_rows"), 0),
        "guard_deferred_candidate_rows": safe_int(guard_summary.get("guard_deferred_candidate_rows"), 0),
        "unassociated_frame_audit_rows_preserved": safe_int(
            guard_summary.get("unassociated_frame_audit_rows_preserved"), 0
        ),
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "promotable_terminal_outcome_rows": len(promotable_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "missing_own_view_guard_branch_closed": gate[
                "missing_own_view_guard_branch_closure_gate_passed"
            ],
            "recommended_next_task": "select_next_label_free_evidence_family_after_object_relation_branch_family_closure"
            if gate["missing_own_view_guard_branch_closure_gate_passed"]
            else "diagnose_missing_own_view_guard_branch_closure_mismatch",
            "reason": "missing-own-view evidence acquisition and negative guard deactivation are closed as nonterminal evidence"
            if gate["missing_own_view_guard_branch_closure_gate_passed"]
            else "missing-own-view guard branch closure did not satisfy the frozen gate",
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
        },
        "output_files": {
            key: str(Path(str(args.out_root)) / value)
            for key, value in requested_outputs(contract).items()
        },
        "interpretation": {
            "fact": "The analyzer closes the missing-own-view selected branch and paired negative guard branch after guard arbitration passed.",
            "agent_inference": "This branch explains why missing evidence should trigger active observation before rejection, but it still produces zero promotable terminal outcomes.",
            "paper_claim": "No paper claim is allowed from this analyzer alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    args.object_relation_branch_summary = source_path(
        args, contract, "object_relation_branch_summary", "object_relation_branch_summary"
    )
    args.object_relation_branch_request_rows = source_path(
        args, contract, "object_relation_branch_request_rows", "object_relation_branch_request_rows"
    )
    args.object_relation_branch_candidate_rows = source_path(
        args, contract, "object_relation_branch_candidate_rows", "object_relation_branch_candidate_rows"
    )
    args.missing_own_view_guard_arbitration_summary = source_path(
        args,
        contract,
        "missing_own_view_guard_arbitration_summary",
        "missing_own_view_guard_arbitration_summary",
    )
    args.missing_own_view_guard_candidate_rows = source_path(
        args, contract, "missing_own_view_guard_candidate_rows", "missing_own_view_guard_candidate_rows"
    )
    args.missing_own_view_guard_request_rows = source_path(
        args, contract, "missing_own_view_guard_request_rows", "missing_own_view_guard_request_rows"
    )
    args.unique_support_branch_closure_summary = source_path(
        args, contract, "unique_support_branch_closure_summary", "unique_support_branch_closure_summary"
    )
    args.residual_branch_closure_summary = source_path(
        args, contract, "residual_branch_closure_summary", "residual_branch_closure_summary"
    )
    object_summary = load_json(args.object_relation_branch_summary)
    object_request_rows = load_jsonl(args.object_relation_branch_request_rows)
    object_candidate_rows = load_jsonl(args.object_relation_branch_candidate_rows)
    guard_summary = load_json(args.missing_own_view_guard_arbitration_summary)
    guard_candidate_rows = load_jsonl(args.missing_own_view_guard_candidate_rows)
    guard_request_rows = load_jsonl(args.missing_own_view_guard_request_rows)
    unique_summary = load_json(args.unique_support_branch_closure_summary)
    residual_summary = load_json(args.residual_branch_closure_summary)

    branch_status_rows = build_branch_status_rows(
        contract=contract,
        object_request_rows=object_request_rows,
        object_candidate_rows=object_candidate_rows,
        guard_summary=guard_summary,
    )
    candidate_closure_rows = build_candidate_rows(guard_candidate_rows, object_candidate_rows)
    request_closure_rows = build_request_rows(guard_request_rows, object_request_rows)
    summary = build_summary(
        args=args,
        contract=contract,
        object_summary=object_summary,
        guard_summary=guard_summary,
        unique_summary=unique_summary,
        residual_summary=residual_summary,
        object_request_rows=object_request_rows,
        object_candidate_rows=object_candidate_rows,
        branch_status_rows=branch_status_rows,
        request_closure_rows=request_closure_rows,
        candidate_closure_rows=candidate_closure_rows,
    )
    out_root = Path(args.out_root)
    outputs = requested_outputs(contract)
    write_jsonl(out_root / outputs["branch_status_rows"], branch_status_rows)
    write_jsonl(out_root / outputs["request_closure_rows"], request_closure_rows)
    write_jsonl(out_root / outputs["candidate_closure_rows"], candidate_closure_rows)
    write_json(out_root / outputs["summary"], summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Close missing-own-view recheck and negative guard branches as nonterminal evidence."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--object-relation-branch-summary")
    parser.add_argument("--object-relation-branch-request-rows")
    parser.add_argument("--object-relation-branch-candidate-rows")
    parser.add_argument("--missing-own-view-guard-arbitration-summary")
    parser.add_argument("--missing-own-view-guard-candidate-rows")
    parser.add_argument("--missing-own-view-guard-request-rows")
    parser.add_argument("--unique-support-branch-closure-summary")
    parser.add_argument("--residual-branch-closure-summary")
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["missing_own_view_guard_branch_closure_gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
