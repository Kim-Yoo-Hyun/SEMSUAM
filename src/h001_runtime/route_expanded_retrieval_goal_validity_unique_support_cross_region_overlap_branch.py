import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    load_json,
    load_jsonl,
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch.v1"
POLICY_NAME = "unique_support_cross_region_overlap_branch_router_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch_v1.json"
)
INSPECTION_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_inspection_v1"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch_v1"
)

CROSS_REGION_BRANCH = "cross_region_overlap_failure_branch"
SHARED_COMMON_BRANCH = "shared_common_view_support_pending_branch"
CLEAN_CONTRASTIVE_BRANCH = "clean_contrastive_pending_branch"
COVERAGE_DIAGNOSTIC_BRANCH = "second_pass_coverage_diagnostic_branch"

BRANCH_ACTIONS = {
    CROSS_REGION_BRANCH: "route_to_cross_region_overlap_failure_branch",
    SHARED_COMMON_BRANCH: "route_to_shared_common_view_support_inspection",
    CLEAN_CONTRASTIVE_BRANCH: "hold_for_non_gt_arbitration_design_review",
    COVERAGE_DIAGNOSTIC_BRANCH: "diagnose_second_pass_evidence_coverage",
}

BRANCH_REASONS = {
    CROSS_REGION_BRANCH: (
        "second-pass evidence still links focus and rival candidate regions, "
        "so region separation is not established"
    ),
    SHARED_COMMON_BRANCH: (
        "the request has no cross-region overlap pairs, but a rival remains "
        "supported from a shared common view"
    ),
    CLEAN_CONTRASTIVE_BRANCH: (
        "only pure contrastive evidence remains; terminal design review is "
        "still separate from this branch freeze"
    ),
    COVERAGE_DIAGNOSTIC_BRANCH: "second-pass detector or role evidence is incomplete",
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


def sorted_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            safe_int(row.get("pair_index"), 999999),
            str(row.get("pair_id")),
        ),
    )


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    return grouped


def branch_for_request(row: Dict[str, Any]) -> Tuple[str, str, str]:
    cross_region = safe_int(row.get("cross_region_overlap_pair_count"), 0)
    shared_common = safe_int(row.get("shared_common_view_rival_support_pair_count"), 0)
    contrastive = safe_int(row.get("second_pass_rival_region_contrastive_pair_count"), 0)
    insufficient = safe_int(row.get("insufficient_second_pass_detector_pair_count"), 0)
    if cross_region > 0:
        branch = CROSS_REGION_BRANCH
    elif shared_common > 0:
        branch = SHARED_COMMON_BRANCH
    elif contrastive > 0 and insufficient == 0:
        branch = CLEAN_CONTRASTIVE_BRANCH
    else:
        branch = COVERAGE_DIAGNOSTIC_BRANCH
    return branch, BRANCH_ACTIONS[branch], BRANCH_REASONS[branch]


def branch_for_pair(row: Dict[str, Any]) -> str:
    if row.get("is_cross_region_overlap_blocker") is True:
        return CROSS_REGION_BRANCH
    if row.get("is_shared_common_view_blocker") is True:
        return SHARED_COMMON_BRANCH
    if row.get("is_later_arbitration_candidate") is True:
        return CLEAN_CONTRASTIVE_BRANCH
    return COVERAGE_DIAGNOSTIC_BRANCH


def build_pair_rows(pair_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted_rows(pair_rows):
        branch = branch_for_pair(row)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_cross_region_overlap_pair_branch_router",
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
                "inspection_blocker": row.get("inspection_blocker"),
                "rival_region_evidence_status": row.get("rival_region_evidence_status"),
                "support_pattern": row.get("support_pattern"),
                "second_pass_support_role_count": row.get("second_pass_support_role_count"),
                "branch_name": branch,
                "branch_action": BRANCH_ACTIONS[branch],
                "branch_reason": BRANCH_REASONS[branch],
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_request_rows(
    request_rows: Sequence[Dict[str, Any]],
    pair_branch_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    pairs_by_request = group_by_request(pair_branch_rows)
    rows: List[Dict[str, Any]] = []
    for row in sorted(request_rows, key=lambda item: request_sort_key(row_request_id(item))):
        request_id = row_request_id(row)
        branch, action, reason = branch_for_request(row)
        branch_pairs = pairs_by_request.get(request_id, [])
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_cross_region_overlap_request_branch_router",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "focus_candidate_id": row.get("focus_candidate_id"),
                "pair_count": row.get("pair_count"),
                "cross_region_overlap_pair_count": row.get("cross_region_overlap_pair_count"),
                "shared_common_view_rival_support_pair_count": row.get(
                    "shared_common_view_rival_support_pair_count"
                ),
                "second_pass_rival_region_contrastive_pair_count": row.get(
                    "second_pass_rival_region_contrastive_pair_count"
                ),
                "insufficient_second_pass_detector_pair_count": row.get(
                    "insufficient_second_pass_detector_pair_count"
                ),
                "cross_region_pair_ids": row.get("cross_region_pair_ids") or [],
                "shared_common_pair_ids": row.get("shared_common_pair_ids") or [],
                "contrastive_pair_ids": row.get("contrastive_pair_ids") or [],
                "request_level_blocker": row.get("request_level_blocker"),
                "source_recommended_next_evidence": row.get("recommended_next_evidence"),
                "pair_branch_counts": compact_counter(pair.get("branch_name") for pair in branch_pairs),
                "branch_name": branch,
                "branch_action": action,
                "branch_reason": reason,
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def simpler_alternatives(
    request_branch_rows: Sequence[Dict[str, Any]],
    pair_branch_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    contrastive_requests = [
        row for row in request_branch_rows if safe_int(row.get("second_pass_rival_region_contrastive_pair_count"), 0) > 0
    ]
    no_cross_requests = [
        row for row in request_branch_rows if safe_int(row.get("cross_region_overlap_pair_count"), 0) == 0
    ]
    return {
        "commit_if_any_contrastive_pair": {
            "decision": "rejected_as_terminal_rule",
            "eligible_request_rows": len(contrastive_requests),
            "reason": "contrastive evidence coexists with shared common-view rival support",
        },
        "commit_if_no_cross_region_overlap": {
            "decision": "diagnostic_only_not_terminal",
            "eligible_request_rows": len(no_cross_requests),
            "reason": "the only no-cross-overlap request remains blocked by shared common-view support",
        },
        "association_count_best": {
            "decision": "diagnostic_only_not_terminal",
            "supported_pair_rows": sum(
                safe_int(row.get("second_pass_support_role_count"), 0) > 0 for row in pair_branch_rows
            ),
            "reason": "visibility support is not an ObjectNav goal-validity proof",
        },
        "defer_all_cross_region": {
            "decision": "safe_but_inert",
            "deferred_request_rows": sum(
                row.get("branch_name") == CROSS_REGION_BRANCH for row in request_branch_rows
            ),
            "reason": "freezes unsafe terminal commitments but does not resolve over-deferral",
        },
    }


def summarize(
    *,
    contract: Dict[str, Any],
    inspection_summary: Dict[str, Any],
    pair_branch_rows: Sequence[Dict[str, Any]],
    request_branch_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    action_rows = list(pair_branch_rows) + list(request_branch_rows)
    forbidden = action_forbidden_keys(action_rows)
    terminal_commit_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    cross_region_rows = [row for row in request_branch_rows if row.get("branch_name") == CROSS_REGION_BRANCH]
    shared_common_rows = [row for row in request_branch_rows if row.get("branch_name") == SHARED_COMMON_BRANCH]
    clean_contrastive_rows = [row for row in request_branch_rows if row.get("branch_name") == CLEAN_CONTRASTIVE_BRANCH]
    gates = contract.get("required_gates") or {}
    source_gate = inspection_summary.get("gate") or {}
    gate = {
        "source_inspection_gate_passed": source_gate.get("inspection_gate_passed") is True,
        "expected_pair_branch_rows_passed": len(pair_branch_rows)
        == safe_int(gates.get("expected_pair_branch_rows"), -1),
        "expected_request_branch_rows_passed": len(request_branch_rows)
        == safe_int(gates.get("expected_request_branch_rows"), -1),
        "expected_cross_region_overlap_failure_request_rows_passed": len(cross_region_rows)
        == safe_int(gates.get("expected_cross_region_overlap_failure_request_rows"), -1),
        "expected_shared_common_view_pending_request_rows_passed": len(shared_common_rows)
        == safe_int(gates.get("expected_shared_common_view_pending_request_rows"), -1),
        "clean_contrastive_terminal_branch_absent_passed": len(clean_contrastive_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        == safe_int(gates.get("action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_commit_rows)
        == safe_int(gates.get("terminal_commit_rows"), -1),
        "terminal_contract_blocked_passed": all(
            row.get("terminal_arbitration_allowed") is False for row in request_branch_rows
        )
        and inspection_summary.get("terminal_contract_allowed") is False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed": False,
    }
    gate["cross_region_overlap_branch_freeze_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "inspection_root": str(args.inspection_root),
        "out_root": str(args.out_root),
        "source_summary": str(args.inspection_summary),
        "pair_branch_rows": len(pair_branch_rows),
        "request_branch_rows": len(request_branch_rows),
        "cross_region_overlap_failure_request_rows": len(cross_region_rows),
        "shared_common_view_pending_request_rows": len(shared_common_rows),
        "clean_contrastive_pending_request_rows": len(clean_contrastive_rows),
        "pair_branch_counts": compact_counter(row.get("branch_name") for row in pair_branch_rows),
        "request_branch_counts": compact_counter(row.get("branch_name") for row in request_branch_rows),
        "request_action_counts": compact_counter(row.get("branch_action") for row in request_branch_rows),
        "cross_region_request_ids": [row_request_id(row) for row in cross_region_rows],
        "shared_common_pending_request_ids": [row_request_id(row) for row in shared_common_rows],
        "query_counts": compact_counter(row.get("query") for row in request_branch_rows),
        "scene_counts": compact_counter(row.get("scene_key") for row in request_branch_rows),
        "simpler_alternatives": simpler_alternatives(request_branch_rows, pair_branch_rows),
        "terminal_contract_allowed": False,
        "recommended_next_task": "inspect_shared_common_view_support_before_terminal_arbitration",
        "recommended_next_task_reason": (
            "cross-region overlap requests are frozen as terminal-blocked, "
            "and one non-cross-overlap request still has shared common-view rival support"
        ),
        "blocked_downstream_tasks": [
            "terminal_goal_region_arbitration_contract",
            "first_eval_rerun",
            "policy_scale_comparison",
            "paper_claim",
        ],
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_commit_rows),
        "gate": gate,
        "interpretation": {
            "fact": (
                "This branch router consumes rival-region inspection rows and does not join "
                "correctness labels."
            ),
            "agent_inference": (
                "Cross-region overlap is now a frozen nonterminal failure branch; "
                "terminal arbitration should wait until shared common-view support is separately inspected."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "pair_branch_rows": "unique_support_cross_region_overlap_branch_pair_rows.jsonl",
            "request_branch_rows": "unique_support_cross_region_overlap_branch_request_rows.jsonl",
            "cross_region_overlap_failure_rows": "unique_support_cross_region_overlap_failure_rows.jsonl",
            "shared_common_view_pending_rows": "unique_support_shared_common_view_pending_rows.jsonl",
            "summary": "unique_support_cross_region_overlap_branch_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.inspection_summary = source_path(args, contract, "inspection_summary", "inspection_summary")
    args.pair_inspection_rows = source_path(args, contract, "pair_inspection_rows", "pair_inspection_rows")
    args.request_inspection_rows = source_path(args, contract, "request_inspection_rows", "request_inspection_rows")

    inspection_summary = load_json(args.inspection_summary)
    pair_inspections = load_jsonl(args.pair_inspection_rows)
    request_inspections = load_jsonl(args.request_inspection_rows)
    pair_branch_rows = build_pair_rows(pair_inspections)
    request_branch_rows = build_request_rows(request_inspections, pair_branch_rows)
    summary = summarize(
        contract=contract,
        inspection_summary=inspection_summary,
        pair_branch_rows=pair_branch_rows,
        request_branch_rows=request_branch_rows,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "unique_support_cross_region_overlap_branch_pair_rows.jsonl", pair_branch_rows)
    write_jsonl(out_root / "unique_support_cross_region_overlap_branch_request_rows.jsonl", request_branch_rows)
    write_jsonl(
        out_root / "unique_support_cross_region_overlap_failure_rows.jsonl",
        [row for row in request_branch_rows if row.get("branch_name") == CROSS_REGION_BRANCH],
    )
    write_jsonl(
        out_root / "unique_support_shared_common_view_pending_rows.jsonl",
        [row for row in request_branch_rows if row.get("branch_name") == SHARED_COMMON_BRANCH],
    )
    write_json(out_root / "unique_support_cross_region_overlap_branch_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze cross-region overlap failure branch from unique-support rival-region inspection."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT, type=Path)
    parser.add_argument("--inspection-root", default=INSPECTION_ROOT_DEFAULT, type=Path)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT, type=Path)
    parser.add_argument("--inspection-summary", type=Path)
    parser.add_argument("--pair-inspection-rows", type=Path)
    parser.add_argument("--request-inspection-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
