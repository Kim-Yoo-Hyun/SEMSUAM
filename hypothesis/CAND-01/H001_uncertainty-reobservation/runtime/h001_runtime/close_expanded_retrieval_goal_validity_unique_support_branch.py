import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    load_json,
    load_jsonl,
    request_sort_key,
    row_request_id,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_branch_closure.v1"
POLICY_NAME = "unique_support_branch_closure_router_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_unique_support_branch_closure_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_branch_closure_v1"
)

UNIQUE_BRANCH = "unique_support_visibility_not_goal_validity"
CROSS_REGION_BRANCH = "cross_region_overlap_failure_branch"
SHARED_COMMON_BRANCH = "shared_common_view_support_failure_branch"
PARTIAL_RELATION_BRANCH = "partial_relation_depth_true_goal"
MISSING_OWN_BRANCH = "correct_candidate_missing_own_view_support"
NEGATIVE_GUARD_BRANCH = "negative_missing_support_guard"

REMAINING_BRANCH_ORDER = [
    PARTIAL_RELATION_BRANCH,
    MISSING_OWN_BRANCH,
    NEGATIVE_GUARD_BRANCH,
]

BRANCH_ACTIONS = {
    PARTIAL_RELATION_BRANCH: "request_additional_relation_depth_evidence",
    MISSING_OWN_BRANCH: "request_missing_own_view_recheck",
    NEGATIVE_GUARD_BRANCH: "guard_negative_missing_support",
}


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(explicit)
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def request_branches(row: Dict[str, Any]) -> List[str]:
    return [str(branch) for branch in row.get("request_branch_names") or []]


def candidate_branches(row: Dict[str, Any]) -> List[str]:
    return [str(branch) for branch in row.get("candidate_branch_names") or []]


def first_remaining_branch(branches: Sequence[str]) -> str:
    branch_set = set(branches)
    for branch in REMAINING_BRANCH_ORDER:
        if branch in branch_set:
            return branch
    return "defer_goal_validity_terminal_policy"


def row_index_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {row_request_id(row): dict(row) for row in rows}


def sorted_request_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(rows, key=lambda row: request_sort_key(row_request_id(row)))


def sorted_candidate_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            safe_int(row.get("target_generated_rank"), 999999),
            candidate_id(row),
        ),
    )


def build_closure_rows(
    object_branch_rows: Sequence[Dict[str, Any]],
    cross_region_rows: Sequence[Dict[str, Any]],
    shared_common_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    cross_by_request = row_index_by_request(cross_region_rows)
    shared_by_request = row_index_by_request(shared_common_rows)
    rows: List[Dict[str, Any]] = []
    unique_rows = [
        row for row in object_branch_rows if UNIQUE_BRANCH in set(request_branches(row))
    ]
    for row in sorted_request_rows(unique_rows):
        request_id = row_request_id(row)
        original_branches = request_branches(row)
        remaining = [branch for branch in original_branches if branch != UNIQUE_BRANCH]
        selected_next = first_remaining_branch(remaining)
        if request_id in cross_by_request:
            blocker_row = cross_by_request[request_id]
            closure_mechanism = CROSS_REGION_BRANCH
            closure_reason = blocker_row.get("branch_reason")
            blocker_counts = blocker_row.get("pair_branch_counts") or {}
        elif request_id in shared_by_request:
            blocker_row = shared_by_request[request_id]
            closure_mechanism = SHARED_COMMON_BRANCH
            closure_reason = blocker_row.get("branch_reason")
            blocker_counts = {SHARED_COMMON_BRANCH: 1}
        else:
            blocker_row = {}
            closure_mechanism = "unclosed_unique_support_request"
            closure_reason = "missing cross-region or shared-common closure row"
            blocker_counts = {}
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_branch_closure_request",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "closed_branch": UNIQUE_BRANCH,
                "closure_status": "terminal_blocked"
                if closure_mechanism != "unclosed_unique_support_request"
                else "closure_missing",
                "closure_action": "close_unique_support_visibility_branch_as_terminal_blocked",
                "closure_mechanism": closure_mechanism,
                "closure_reason": closure_reason,
                "closure_blocker_counts": blocker_counts,
                "original_request_branch_names": original_branches,
                "remaining_request_branch_names": remaining,
                "selected_next_branch_after_closure": selected_next,
                "selected_next_action_after_closure": BRANCH_ACTIONS.get(selected_next, selected_next),
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def next_branch_request_rows(object_branch_rows: Sequence[Dict[str, Any]], selected_branch: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted_request_rows(object_branch_rows):
        branches = request_branches(row)
        if selected_branch not in set(branches):
            continue
        remaining = [branch for branch in branches if branch != UNIQUE_BRANCH]
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_next_branch_specific_evidence_request",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "selected_next_branch": selected_branch,
                "selected_next_action": BRANCH_ACTIONS.get(selected_branch, selected_branch),
                "original_request_branch_names": branches,
                "remaining_request_branch_names": remaining,
                "branch_is_preferred_after_unique_closure": first_remaining_branch(remaining) == selected_branch,
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def next_branch_candidate_rows(
    object_branch_candidate_rows: Sequence[Dict[str, Any]],
    selected_branch: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted_candidate_rows(object_branch_candidate_rows):
        branches = candidate_branches(row)
        if selected_branch not in set(branches):
            continue
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_next_branch_specific_evidence_candidate",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": candidate_id(row),
                "target_generated_rank": row.get("target_generated_rank"),
                "target_semantic_rank": row.get("target_semantic_rank"),
                "selected_next_branch": selected_branch,
                "selected_next_action": BRANCH_ACTIONS.get(selected_branch, selected_branch),
                "candidate_branch_names": branches,
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
    object_branch_summary: Dict[str, Any],
    cross_region_summary: Dict[str, Any],
    shared_common_summary: Dict[str, Any],
    closure_rows: Sequence[Dict[str, Any]],
    next_requests: Sequence[Dict[str, Any]],
    next_candidates: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = contract.get("required_gates") or {}
    action_rows = list(closure_rows) + list(next_requests) + list(next_candidates)
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    closed_rows = [
        row for row in closure_rows if row.get("closure_status") == "terminal_blocked"
    ]
    cross_closed_rows = [
        row for row in closure_rows if row.get("closure_mechanism") == CROSS_REGION_BRANCH
    ]
    shared_closed_rows = [
        row for row in closure_rows if row.get("closure_mechanism") == SHARED_COMMON_BRANCH
    ]
    unclosed_rows = [
        row for row in closure_rows if row.get("closure_status") != "terminal_blocked"
    ]
    selected_branch = (contract.get("next_branch_selection") or {}).get(
        "selected_next_branch", PARTIAL_RELATION_BRANCH
    )
    gate = {
        "source_object_relation_branch_gate_passed": (
            (object_branch_summary.get("gate") or {}).get("branch_evidence_router_gate_passed")
            is True
        ),
        "source_cross_region_branch_gate_passed": (
            (cross_region_summary.get("gate") or {}).get("cross_region_overlap_branch_freeze_gate_passed")
            is True
        ),
        "source_shared_common_view_branch_gate_passed": (
            (shared_common_summary.get("gate") or {}).get("shared_common_view_branch_freeze_gate_passed")
            is True
        ),
        "expected_unique_support_closed_request_rows_passed": len(closed_rows)
        == safe_int(gates.get("expected_unique_support_closed_request_rows"), -1),
        "expected_cross_region_closed_request_rows_passed": len(cross_closed_rows)
        == safe_int(gates.get("expected_cross_region_closed_request_rows"), -1),
        "expected_shared_common_closed_request_rows_passed": len(shared_closed_rows)
        == safe_int(gates.get("expected_shared_common_closed_request_rows"), -1),
        "expected_unclosed_unique_support_request_rows_passed": len(unclosed_rows)
        == safe_int(gates.get("expected_unclosed_unique_support_request_rows"), -1),
        "expected_next_branch_request_rows_passed": len(next_requests)
        == safe_int(gates.get("expected_next_branch_request_rows"), -1),
        "expected_next_branch_candidate_rows_passed": len(next_candidates)
        == safe_int(gates.get("expected_next_branch_candidate_rows"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        == safe_int(gates.get("terminal_commit_rows"), -1),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        == safe_int(gates.get("action_evidence_forbidden_key_count"), -1),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed": False,
    }
    gate["unique_support_branch_closure_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source_summaries": {
            "object_relation_branch_summary": str(args.object_relation_branch_summary),
            "cross_region_branch_summary": str(args.cross_region_branch_summary),
            "shared_common_view_branch_summary": str(args.shared_common_view_branch_summary),
        },
        "closed_branch": UNIQUE_BRANCH,
        "closure_status": "terminal_blocked" if len(unclosed_rows) == 0 else "needs_diagnosis",
        "closure_request_rows": len(closure_rows),
        "closed_request_rows": len(closed_rows),
        "closure_mechanism_counts": compact_counter(row.get("closure_mechanism") for row in closure_rows),
        "unclosed_unique_support_request_rows": len(unclosed_rows),
        "unclosed_unique_support_request_ids": [row_request_id(row) for row in unclosed_rows],
        "selected_next_branch": selected_branch,
        "selected_next_action": BRANCH_ACTIONS.get(selected_branch, selected_branch),
        "selected_next_request_rows": len(next_requests),
        "selected_next_candidate_rows": len(next_candidates),
        "selected_next_request_ids": [row_request_id(row) for row in next_requests],
        "selected_next_candidate_counts_by_request": compact_counter(
            row_request_id(row) for row in next_candidates
        ),
        "next_request_preferred_after_closure_rows": sum(
            row.get("branch_is_preferred_after_unique_closure") is True for row in next_requests
        ),
        "terminal_contract_allowed": False,
        "terminal_utility_validation_allowed": False,
        "blocked_downstream_tasks": [
            "terminal_goal_region_arbitration_contract",
            "first_eval_rerun",
            "policy_scale_comparison",
            "paper_claim",
        ],
        "recommended_next_task": "freeze_partial_relation_depth_true_goal_observation_contract",
        "recommended_next_task_reason": (
            "unique-support visibility is closed as terminal-blocked; partial relation-depth true-goal "
            "is the highest-priority remaining branch with observation-utility relevance"
        ),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": (
                "The closure consumes action-time branch rows and frozen cross-region/shared-common "
                "branch outputs; it does not join correctness labels."
            ),
            "agent_inference": (
                "The unique-support visibility branch no longer supports a clean request-level "
                "terminal arbitration case. The next branch-specific evidence route should test "
                "whether additional relation-depth observation can recover true-goal candidates that "
                "were blocked by partial relation-depth evidence."
            ),
        },
        "output_files": {
            "closure_request_rows": "unique_support_branch_closure_request_rows.jsonl",
            "next_branch_request_rows": "unique_support_branch_closure_next_branch_request_rows.jsonl",
            "next_branch_candidate_rows": "unique_support_branch_closure_next_branch_candidate_rows.jsonl",
            "summary": "unique_support_branch_closure_summary.json",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.object_relation_branch_summary = source_path(
        args, contract, "object_relation_branch_summary", "object_relation_branch_summary"
    )
    args.object_relation_branch_request_rows = source_path(
        args, contract, "object_relation_branch_request_rows", "object_relation_branch_request_rows"
    )
    args.object_relation_branch_candidate_rows = source_path(
        args, contract, "object_relation_branch_candidate_rows", "object_relation_branch_candidate_rows"
    )
    args.cross_region_branch_summary = source_path(
        args, contract, "cross_region_branch_summary", "cross_region_branch_summary"
    )
    args.cross_region_failure_rows = source_path(
        args, contract, "cross_region_failure_rows", "cross_region_failure_rows"
    )
    args.shared_common_view_branch_summary = source_path(
        args, contract, "shared_common_view_branch_summary", "shared_common_view_branch_summary"
    )
    args.shared_common_view_failure_rows = source_path(
        args, contract, "shared_common_view_failure_rows", "shared_common_view_failure_rows"
    )

    object_branch_summary = load_json(args.object_relation_branch_summary)
    object_request_rows = load_jsonl(args.object_relation_branch_request_rows)
    object_candidate_rows = load_jsonl(args.object_relation_branch_candidate_rows)
    cross_region_summary = load_json(args.cross_region_branch_summary)
    cross_region_rows = load_jsonl(args.cross_region_failure_rows)
    shared_common_summary = load_json(args.shared_common_view_branch_summary)
    shared_common_rows = load_jsonl(args.shared_common_view_failure_rows)

    selected_branch = (contract.get("next_branch_selection") or {}).get(
        "selected_next_branch", PARTIAL_RELATION_BRANCH
    )
    closure_rows = build_closure_rows(object_request_rows, cross_region_rows, shared_common_rows)
    next_requests = next_branch_request_rows(object_request_rows, selected_branch)
    next_candidates = next_branch_candidate_rows(object_candidate_rows, selected_branch)
    summary = summarize(
        contract=contract,
        object_branch_summary=object_branch_summary,
        cross_region_summary=cross_region_summary,
        shared_common_summary=shared_common_summary,
        closure_rows=closure_rows,
        next_requests=next_requests,
        next_candidates=next_candidates,
        args=args,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "unique_support_branch_closure_request_rows.jsonl", closure_rows)
    write_jsonl(out_root / "unique_support_branch_closure_next_branch_request_rows.jsonl", next_requests)
    write_jsonl(out_root / "unique_support_branch_closure_next_branch_candidate_rows.jsonl", next_candidates)
    write_json(out_root / "unique_support_branch_closure_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Close unique-support visibility branch and select the next branch-specific evidence route."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT, type=Path)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT, type=Path)
    parser.add_argument("--object-relation-branch-summary", type=Path)
    parser.add_argument("--object-relation-branch-request-rows", type=Path)
    parser.add_argument("--object-relation-branch-candidate-rows", type=Path)
    parser.add_argument("--cross-region-branch-summary", type=Path)
    parser.add_argument("--cross-region-failure-rows", type=Path)
    parser.add_argument("--shared-common-view-branch-summary", type=Path)
    parser.add_argument("--shared-common-view-failure-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
