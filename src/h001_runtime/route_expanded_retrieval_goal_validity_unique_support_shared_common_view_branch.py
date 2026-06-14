import argparse
import json
from collections import Counter
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


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_shared_common_view_branch.v1"
POLICY_NAME = "unique_support_shared_common_view_branch_router_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_branch_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_branch_v1"
)

SHARED_COMMON_BRANCH = "shared_common_view_support_failure_branch"
CONTAMINATED_CONTRASTIVE_BRANCH = "contaminated_clean_contrastive_pair_branch"

BRANCH_ACTIONS = {
    SHARED_COMMON_BRANCH: "route_to_shared_common_view_support_failure_branch",
    CONTAMINATED_CONTRASTIVE_BRANCH: "hold_clean_contrastive_pair_until_request_level_blocker_resolved",
}

BRANCH_REASONS = {
    SHARED_COMMON_BRANCH: (
        "rival support from the shared common view remains a request-level blocker"
    ),
    CONTAMINATED_CONTRASTIVE_BRANCH: (
        "clean contrastive pair cannot justify terminal arbitration while the same request "
        "has shared common-view rival support"
    ),
}


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


def pair_sort_key(row: Dict[str, Any]) -> tuple:
    return (
        request_sort_key(row_request_id(row)),
        safe_int(row.get("pair_index"), 999999),
        str(row.get("pair_id")),
    )


def pair_branch_name(row: Dict[str, Any]) -> str:
    status = str(row.get("shared_common_view_inspection_status") or "")
    if status == "shared_common_view_rival_support_blocks_terminal":
        return SHARED_COMMON_BRANCH
    return CONTAMINATED_CONTRASTIVE_BRANCH


def build_pair_rows(pair_inspection_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted([dict(item) for item in pair_inspection_rows], key=pair_sort_key):
        branch_name = pair_branch_name(row)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_shared_common_view_pair_branch_router",
                "policy": POLICY_NAME,
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
                "source_inspection_status": row.get("shared_common_view_inspection_status"),
                "inspection_blocker": row.get("inspection_blocker"),
                "rival_region_evidence_status": row.get("rival_region_evidence_status"),
                "support_pattern": row.get("support_pattern"),
                "second_pass_support_role_count": row.get("second_pass_support_role_count"),
                "branch_name": branch_name,
                "branch_action": BRANCH_ACTIONS[branch_name],
                "branch_reason": BRANCH_REASONS[branch_name],
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_request_rows(request_inspection_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted(request_inspection_rows, key=lambda item: request_sort_key(row_request_id(item))):
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_shared_common_view_request_branch_router",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "focus_candidate_id": row.get("focus_candidate_id"),
                "pair_count": row.get("pair_count"),
                "shared_common_view_rival_support_pair_count": row.get(
                    "shared_common_view_rival_support_pair_count"
                ),
                "clean_contrastive_pair_count": row.get("clean_contrastive_pair_count"),
                "cross_region_overlap_pair_count": row.get("cross_region_overlap_pair_count"),
                "shared_common_pair_ids": row.get("shared_common_pair_ids") or [],
                "clean_contrastive_pair_ids": row.get("clean_contrastive_pair_ids") or [],
                "source_terminal_blocker": row.get("terminal_blocker"),
                "source_recommended_next_evidence": row.get("recommended_next_evidence"),
                "branch_name": SHARED_COMMON_BRANCH,
                "branch_action": BRANCH_ACTIONS[SHARED_COMMON_BRANCH],
                "branch_reason": BRANCH_REASONS[SHARED_COMMON_BRANCH],
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def simpler_alternatives(request_rows: Sequence[Dict[str, Any]], pair_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "commit_if_any_clean_contrastive_pair": {
            "decision": "rejected_as_terminal_rule",
            "eligible_request_rows": sum(safe_int(row.get("clean_contrastive_pair_count"), 0) > 0 for row in request_rows),
            "reason": "request-level shared common-view support remains present",
        },
        "commit_if_no_cross_region_overlap": {
            "decision": "rejected_as_terminal_rule",
            "eligible_request_rows": sum(safe_int(row.get("cross_region_overlap_pair_count"), 0) == 0 for row in request_rows),
            "reason": "no cross-region overlap is insufficient when common-view rival support remains",
        },
        "association_count_best": {
            "decision": "diagnostic_only_not_terminal",
            "supported_pair_rows": sum(safe_int(row.get("second_pass_support_role_count"), 0) > 0 for row in pair_rows),
            "reason": "visibility support is not target-specific ObjectNav goal validity",
        },
        "defer_shared_common_view": {
            "decision": "safe_but_inert",
            "deferred_request_rows": len(request_rows),
            "reason": "blocks unsafe terminal commit but does not recover utility",
        },
    }


def summarize(
    *,
    contract: Dict[str, Any],
    inspection_summary: Dict[str, Any],
    pair_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    action_rows = list(pair_rows) + list(request_rows)
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    shared_common_failure_rows = [
        row for row in request_rows if row.get("branch_name") == SHARED_COMMON_BRANCH
    ]
    contaminated_pair_rows = [
        row for row in pair_rows if row.get("branch_name") == CONTAMINATED_CONTRASTIVE_BRANCH
    ]
    gates = contract.get("required_gates") or {}
    source_gate = inspection_summary.get("gate") or {}
    gate = {
        "source_shared_common_view_inspection_gate_passed": source_gate.get(
            "shared_common_view_inspection_gate_passed"
        )
        is True,
        "expected_request_branch_rows_passed": len(request_rows)
        == safe_int(gates.get("expected_request_branch_rows"), -1),
        "expected_pair_branch_rows_passed": len(pair_rows)
        == safe_int(gates.get("expected_pair_branch_rows"), -1),
        "expected_shared_common_view_support_failure_request_rows_passed": len(shared_common_failure_rows)
        == safe_int(gates.get("expected_shared_common_view_support_failure_request_rows"), -1),
        "expected_contaminated_clean_contrastive_pair_rows_passed": len(contaminated_pair_rows)
        == safe_int(gates.get("expected_contaminated_clean_contrastive_pair_rows"), -1),
        "terminal_contract_blocked_passed": all(
            row.get("terminal_arbitration_allowed") is False for row in request_rows
        )
        and inspection_summary.get("terminal_contract_allowed") is False,
        "terminal_commit_rows_passed": len(terminal_rows) == safe_int(gates.get("terminal_commit_rows"), -1),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        == safe_int(gates.get("action_evidence_forbidden_key_count"), -1),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed": False,
    }
    gate["shared_common_view_branch_freeze_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source_summary": str(args.shared_common_view_inspection_summary),
        "pair_branch_rows": len(pair_rows),
        "request_branch_rows": len(request_rows),
        "shared_common_view_support_failure_request_rows": len(shared_common_failure_rows),
        "contaminated_clean_contrastive_pair_rows": len(contaminated_pair_rows),
        "request_ids": [row_request_id(row) for row in request_rows],
        "pair_branch_counts": compact_counter(row.get("branch_name") for row in pair_rows),
        "request_branch_counts": compact_counter(row.get("branch_name") for row in request_rows),
        "request_action_counts": compact_counter(row.get("branch_action") for row in request_rows),
        "simpler_alternatives": simpler_alternatives(request_rows, pair_rows),
        "terminal_contract_allowed": False,
        "recommended_next_task": "close_unique_support_visibility_branch_as_terminal_blocked_and_select_next_branch_specific_evidence_route",
        "recommended_next_task_reason": (
            "cross-region and shared-common support branches are now terminal-blocked, "
            "and no clean request-level contrastive terminal case remains"
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
                "The branch router consumes shared-common-view inspection rows and does not join "
                "correctness labels."
            ),
            "agent_inference": (
                "The unique-support visibility branch has no clean terminal arbitration case after "
                "cross-region and shared-common blockers are frozen."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "pair_branch_rows": "unique_support_shared_common_view_branch_pair_rows.jsonl",
            "request_branch_rows": "unique_support_shared_common_view_branch_request_rows.jsonl",
            "shared_common_view_failure_rows": "unique_support_shared_common_view_failure_rows.jsonl",
            "summary": "unique_support_shared_common_view_branch_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.shared_common_view_inspection_summary = source_path(
        args, contract, "shared_common_view_inspection_summary", "shared_common_view_inspection_summary"
    )
    args.pair_inspection_rows = source_path(args, contract, "pair_inspection_rows", "pair_inspection_rows")
    args.request_inspection_rows = source_path(args, contract, "request_inspection_rows", "request_inspection_rows")
    inspection_summary = load_json(args.shared_common_view_inspection_summary)
    pair_inspection_rows = load_jsonl(args.pair_inspection_rows)
    request_inspection_rows = load_jsonl(args.request_inspection_rows)
    pair_rows = build_pair_rows(pair_inspection_rows)
    request_rows = build_request_rows(request_inspection_rows)
    summary = summarize(
        contract=contract,
        inspection_summary=inspection_summary,
        pair_rows=pair_rows,
        request_rows=request_rows,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "unique_support_shared_common_view_branch_pair_rows.jsonl", pair_rows)
    write_jsonl(out_root / "unique_support_shared_common_view_branch_request_rows.jsonl", request_rows)
    write_jsonl(
        out_root / "unique_support_shared_common_view_failure_rows.jsonl",
        [row for row in request_rows if row.get("branch_name") == SHARED_COMMON_BRANCH],
    )
    write_json(out_root / "unique_support_shared_common_view_branch_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze shared common-view support failure branch from unique-support inspection."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT, type=Path)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT, type=Path)
    parser.add_argument("--shared-common-view-inspection-summary", type=Path)
    parser.add_argument("--pair-inspection-rows", type=Path)
    parser.add_argument("--request-inspection-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
