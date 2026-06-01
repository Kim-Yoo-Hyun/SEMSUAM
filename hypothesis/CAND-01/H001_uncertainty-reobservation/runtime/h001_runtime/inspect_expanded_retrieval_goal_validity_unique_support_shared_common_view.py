import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    load_json,
    load_jsonl,
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection_v1"
)

SHARED_COMMON_BRANCH = "shared_common_view_support_pending_branch"
CLEAN_CONTRASTIVE_BRANCH = "clean_contrastive_pending_branch"


def row_request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


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


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    return grouped


def sorted_pair_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            safe_int(row.get("pair_index"), 999999),
            str(row.get("pair_id")),
        ),
    )


def shared_common_status(row: Dict[str, Any]) -> str:
    branch = str(row.get("branch_name") or "")
    if branch == SHARED_COMMON_BRANCH:
        return "shared_common_view_rival_support_blocks_terminal"
    if branch == CLEAN_CONTRASTIVE_BRANCH:
        return "clean_contrastive_pair_contaminated_by_request_level_shared_common_support"
    return "not_in_shared_common_inspection_scope"


def build_pair_rows(
    pending_request_rows: Sequence[Dict[str, Any]],
    pair_branch_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    pending_ids = {row_request_id(row) for row in pending_request_rows}
    rows: List[Dict[str, Any]] = []
    for row in sorted_pair_rows([row for row in pair_branch_rows if row_request_id(row) in pending_ids]):
        status = shared_common_status(row)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "analysis_unique_support_shared_common_view_pair_inspection",
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "pair_id": row.get("pair_id"),
                "pair_index": row.get("pair_index"),
                "focus_candidate_id": row.get("focus_candidate_id"),
                "rival_candidate_id": row.get("rival_candidate_id"),
                "source_branch_name": row.get("branch_name"),
                "source_branch_action": row.get("branch_action"),
                "inspection_blocker": row.get("inspection_blocker"),
                "rival_region_evidence_status": row.get("rival_region_evidence_status"),
                "support_pattern": row.get("support_pattern"),
                "second_pass_support_role_count": row.get("second_pass_support_role_count"),
                "shared_common_view_inspection_status": status,
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_request_rows(
    pending_request_rows: Sequence[Dict[str, Any]],
    pair_inspection_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    pairs_by_request = group_by_request(pair_inspection_rows)
    rows: List[Dict[str, Any]] = []
    for row in sorted(pending_request_rows, key=lambda item: request_sort_key(row_request_id(item))):
        request_id = row_request_id(row)
        pair_rows = pairs_by_request.get(request_id, [])
        shared_pairs = [
            item
            for item in pair_rows
            if item.get("shared_common_view_inspection_status")
            == "shared_common_view_rival_support_blocks_terminal"
        ]
        clean_pairs = [
            item
            for item in pair_rows
            if item.get("shared_common_view_inspection_status")
            == "clean_contrastive_pair_contaminated_by_request_level_shared_common_support"
        ]
        terminal_allowed = len(shared_pairs) == 0 and len(clean_pairs) == len(pair_rows) and len(pair_rows) > 0
        recommendation = (
            "design_fixed_non_gt_goal_region_arbitration_contract"
            if terminal_allowed
            else "freeze_shared_common_view_support_failure_branch"
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "analysis_unique_support_shared_common_view_request_inspection",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "focus_candidate_id": row.get("focus_candidate_id"),
                "pair_count": row.get("pair_count"),
                "shared_common_view_rival_support_pair_count": len(shared_pairs),
                "clean_contrastive_pair_count": len(clean_pairs),
                "cross_region_overlap_pair_count": row.get("cross_region_overlap_pair_count"),
                "source_pair_branch_counts": row.get("pair_branch_counts") or {},
                "shared_common_pair_ids": [item.get("pair_id") for item in shared_pairs],
                "clean_contrastive_pair_ids": [item.get("pair_id") for item in clean_pairs],
                "terminal_arbitration_allowed": terminal_allowed,
                "terminal_blocker": None if terminal_allowed else "shared_common_view_rival_support_present",
                "recommended_next_evidence": recommendation,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def simpler_alternatives(request_rows: Sequence[Dict[str, Any]], pair_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    any_clean = [
        row for row in request_rows if safe_int(row.get("clean_contrastive_pair_count"), 0) > 0
    ]
    no_cross = [
        row for row in request_rows if safe_int(row.get("cross_region_overlap_pair_count"), 0) == 0
    ]
    return {
        "commit_if_any_clean_contrastive_pair": {
            "decision": "rejected_as_terminal_rule",
            "eligible_request_rows": len(any_clean),
            "reason": "the only clean-contrastive-containing request also has shared common-view rival support",
        },
        "commit_if_no_cross_region_overlap": {
            "decision": "rejected_as_terminal_rule",
            "eligible_request_rows": len(no_cross),
            "reason": "absence of cross-region overlap does not remove shared common-view rival support",
        },
        "association_count_best": {
            "decision": "diagnostic_only_not_terminal",
            "supported_pair_rows": sum(
                safe_int(row.get("second_pass_support_role_count"), 0) > 0 for row in pair_rows
            ),
            "reason": "common-view visibility is not target-specific ObjectNav goal-validity evidence",
        },
        "defer_shared_common_view": {
            "decision": "safe_but_inert",
            "deferred_request_rows": len(request_rows),
            "reason": "blocks unsafe commit but does not recover utility",
        },
    }


def summarize(
    *,
    contract: Dict[str, Any],
    branch_summary: Dict[str, Any],
    pair_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    action_rows = list(pair_rows) + list(request_rows)
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    shared_pairs = [
        row
        for row in pair_rows
        if row.get("shared_common_view_inspection_status") == "shared_common_view_rival_support_blocks_terminal"
    ]
    clean_pairs = [
        row
        for row in pair_rows
        if row.get("shared_common_view_inspection_status")
        == "clean_contrastive_pair_contaminated_by_request_level_shared_common_support"
    ]
    gates = contract.get("required_gates") or {}
    source_gate = branch_summary.get("gate") or {}
    terminal_allowed = any(row.get("terminal_arbitration_allowed") is True for row in request_rows)
    gate = {
        "source_cross_region_branch_gate_passed": source_gate.get(
            "cross_region_overlap_branch_freeze_gate_passed"
        )
        is True,
        "expected_request_inspection_rows_passed": len(request_rows)
        == safe_int(gates.get("expected_request_inspection_rows"), -1),
        "expected_pair_inspection_rows_passed": len(pair_rows)
        == safe_int(gates.get("expected_pair_inspection_rows"), -1),
        "expected_shared_common_pair_rows_passed": len(shared_pairs)
        == safe_int(gates.get("expected_shared_common_pair_rows"), -1),
        "expected_clean_contrastive_pair_rows_passed": len(clean_pairs)
        == safe_int(gates.get("expected_clean_contrastive_pair_rows"), -1),
        "terminal_contract_blocked_passed": terminal_allowed is False,
        "terminal_commit_rows_passed": len(terminal_rows) == safe_int(gates.get("terminal_commit_rows"), -1),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        == safe_int(gates.get("action_evidence_forbidden_key_count"), -1),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed": False,
    }
    gate["shared_common_view_inspection_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source_summary": str(args.cross_region_branch_summary),
        "request_inspection_rows": len(request_rows),
        "pair_inspection_rows": len(pair_rows),
        "shared_common_pair_rows": len(shared_pairs),
        "clean_contrastive_pair_rows": len(clean_pairs),
        "request_ids": [row_request_id(row) for row in request_rows],
        "shared_common_pair_ids": [row.get("pair_id") for row in shared_pairs],
        "clean_contrastive_pair_ids": [row.get("pair_id") for row in clean_pairs],
        "pair_status_counts": compact_counter(row.get("shared_common_view_inspection_status") for row in pair_rows),
        "request_recommendation_counts": compact_counter(row.get("recommended_next_evidence") for row in request_rows),
        "query_counts": compact_counter(row.get("query") for row in request_rows),
        "scene_counts": compact_counter(row.get("scene_key") for row in request_rows),
        "simpler_alternatives": simpler_alternatives(request_rows, pair_rows),
        "terminal_contract_allowed": False,
        "recommended_next_task": "freeze_shared_common_view_support_failure_branch",
        "recommended_next_task_reason": (
            "the remaining request has one clean contrastive pair but also one shared-common-view "
            "rival support pair"
        ),
        "blocked_downstream_tasks": [
            "terminal_goal_region_arbitration_contract",
            "first_eval_rerun",
            "policy_scale_comparison",
            "paper_claim",
        ],
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": (
                "The inspection consumes only branch and pair evidence rows from the prior "
                "cross-region branch freeze."
            ),
            "agent_inference": (
                "A clean contrastive pair is not enough for terminal arbitration when the same "
                "request also contains shared common-view rival support."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "pair_inspection_rows": "unique_support_shared_common_view_pair_inspection_rows.jsonl",
            "request_inspection_rows": "unique_support_shared_common_view_request_inspection_rows.jsonl",
            "summary": "unique_support_shared_common_view_inspection_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.cross_region_branch_summary = source_path(
        args, contract, "cross_region_branch_summary", "cross_region_branch_summary"
    )
    args.pair_branch_rows = source_path(args, contract, "pair_branch_rows", "pair_branch_rows")
    args.request_branch_rows = source_path(args, contract, "request_branch_rows", "request_branch_rows")
    args.shared_common_pending_rows = source_path(
        args, contract, "shared_common_pending_rows", "shared_common_pending_rows"
    )
    branch_summary = load_json(args.cross_region_branch_summary)
    pair_branch_rows = load_jsonl(args.pair_branch_rows)
    pending_request_rows = load_jsonl(args.shared_common_pending_rows)
    pair_rows = build_pair_rows(pending_request_rows, pair_branch_rows)
    request_rows = build_request_rows(pending_request_rows, pair_rows)
    summary = summarize(
        contract=contract,
        branch_summary=branch_summary,
        pair_rows=pair_rows,
        request_rows=request_rows,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "unique_support_shared_common_view_pair_inspection_rows.jsonl", pair_rows)
    write_jsonl(out_root / "unique_support_shared_common_view_request_inspection_rows.jsonl", request_rows)
    write_json(out_root / "unique_support_shared_common_view_inspection_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect shared common-view support for the remaining unique-support request."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT, type=Path)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT, type=Path)
    parser.add_argument("--cross-region-branch-summary", type=Path)
    parser.add_argument("--pair-branch-rows", type=Path)
    parser.add_argument("--request-branch-rows", type=Path)
    parser.add_argument("--shared-common-pending-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
