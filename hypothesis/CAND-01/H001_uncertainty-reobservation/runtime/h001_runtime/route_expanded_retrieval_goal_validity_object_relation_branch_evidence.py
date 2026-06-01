import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    load_json,
    load_jsonl,
    request_sort_key,
    row_request_id,
    safe_float,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_branch_evidence.v1"
POLICY_NAME = "object_relation_branch_router_v1"

UNIQUE_BRANCH = "unique_support_visibility_not_goal_validity"
MISSING_OWN_BRANCH = "correct_candidate_missing_own_view_support"
PARTIAL_RELATION_BRANCH = "partial_relation_depth_true_goal"
NEGATIVE_GUARD_BRANCH = "negative_missing_support_guard"

PREFERRED_BRANCH_ORDER = [
    UNIQUE_BRANCH,
    PARTIAL_RELATION_BRANCH,
    MISSING_OWN_BRANCH,
    NEGATIVE_GUARD_BRANCH,
]

BRANCH_ACTIONS = {
    UNIQUE_BRANCH: "request_contrastive_goal_region_evidence",
    MISSING_OWN_BRANCH: "request_missing_own_view_recheck",
    PARTIAL_RELATION_BRANCH: "request_additional_relation_depth_evidence",
    NEGATIVE_GUARD_BRANCH: "guard_negative_missing_support",
}

BRANCH_REASONS = {
    UNIQUE_BRANCH: (
        "unique independent own-view support is a visible-object signal, "
        "not a goal-validity proof"
    ),
    MISSING_OWN_BRANCH: (
        "relation-depth-plausible candidates without own-view support need "
        "candidate-centered re-observation before rejection"
    ),
    PARTIAL_RELATION_BRANCH: (
        "partial relation-depth evidence should be completed before treating "
        "candidate invalidity as established"
    ),
    NEGATIVE_GUARD_BRANCH: (
        "unsupported candidates should be guarded, while positives require "
        "separate branch evidence"
    ),
}

TAG_TO_BRANCH = {
    "unique_independent_support_selects_wrong_goal": UNIQUE_BRANCH,
    "object_visibility_preferred_over_true_goal_validity": UNIQUE_BRANCH,
    "semantic_top_can_be_wrong_visible_object": UNIQUE_BRANCH,
    "correct_goal_rejected_by_missing_strong_own_view": MISSING_OWN_BRANCH,
    "correct_goal_relation_depth_partial": PARTIAL_RELATION_BRANCH,
    "true_candidate_support_blocked_by_relation_depth_partial": PARTIAL_RELATION_BRANCH,
    "negative_candidates_blocked_by_missing_support": NEGATIVE_GUARD_BRANCH,
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


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    return grouped


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


def relation_depth_partial(row: Dict[str, Any]) -> bool:
    status = str(row.get("relation_depth_evidence_status") or "")
    action = str(row.get("arbitration_action") or "")
    return "partial" in status or action.startswith("defer_relation_depth_unresolved_or_partial")


def missing_independent_support(row: Dict[str, Any]) -> bool:
    action = str(row.get("arbitration_action") or "")
    return action.startswith("reject_relation_depth_resolved_without_independent_candidate_support")


def provisional_unique_support(row: Dict[str, Any]) -> bool:
    action = str(row.get("arbitration_action") or "")
    return action.startswith("provisional_unique_goal_validity_candidate")


def branch_names_for_candidate(row: Dict[str, Any]) -> List[str]:
    branches: List[str] = []
    if provisional_unique_support(row):
        branches.append(UNIQUE_BRANCH)
    if missing_independent_support(row):
        branches.append(MISSING_OWN_BRANCH)
        branches.append(NEGATIVE_GUARD_BRANCH)
    if relation_depth_partial(row):
        branches.append(PARTIAL_RELATION_BRANCH)
    if not branches:
        branches.append("defer_goal_validity_terminal_policy")
    return [branch for branch in PREFERRED_BRANCH_ORDER if branch in branches] + [
        branch for branch in branches if branch not in PREFERRED_BRANCH_ORDER
    ]


def action_time_input_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "arbitration_action": row.get("arbitration_action"),
        "arbitration_reason": row.get("arbitration_reason"),
        "relation_depth_evidence_status": row.get("relation_depth_evidence_status"),
        "relation_associated_heading_count": row.get("relation_associated_heading_count"),
        "relation_depth_consistent_count": row.get("relation_depth_consistent_count"),
        "relation_inside_mask_count": row.get("relation_inside_mask_count"),
        "relation_resolved_direction_source_count": row.get("relation_resolved_direction_source_count"),
        "base_candidate_evidence_class": row.get("base_candidate_evidence_class"),
        "base_candidate_role": row.get("base_candidate_role"),
        "base_candidate_specific_support": row.get("base_candidate_specific_support"),
        "base_has_candidate_association": row.get("base_has_candidate_association"),
        "base_consistent_depth_count": row.get("base_consistent_depth_count"),
        "base_depth_mismatch_count": row.get("base_depth_mismatch_count"),
        "base_mask_hit_count": row.get("base_mask_hit_count"),
        "base_best_box_score": row.get("base_best_box_score"),
        "base_min_depth_error_m": row.get("base_min_depth_error_m"),
        "base_is_source_top": row.get("base_is_source_top"),
        "base_is_detector_strong_candidate": row.get("base_is_detector_strong_candidate"),
        "base_is_detector_strong_rival": row.get("base_is_detector_strong_rival"),
        "base_is_local_context_candidate": row.get("base_is_local_context_candidate"),
        "support_saturation_eligible_candidate_count": row.get("support_saturation_eligible_candidate_count"),
        "support_saturation_total_candidate_count": row.get("support_saturation_total_candidate_count"),
        "support_saturation_rate": row.get("support_saturation_rate"),
    }


def build_candidate_rows(candidate_failure_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted_candidate_rows(candidate_failure_rows):
        branches = branch_names_for_candidate(row)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_object_relation_goal_validity_branch_candidate_router",
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
                "candidate_branch_names": branches,
                "candidate_branch_actions": [BRANCH_ACTIONS.get(branch, branch) for branch in branches],
                "preferred_candidate_branch": branches[0],
                "preferred_candidate_action": BRANCH_ACTIONS.get(branches[0], branches[0]),
                "routing_inputs": action_time_input_payload(row),
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def branch_count_items(branches: Sequence[str]) -> List[Dict[str, Any]]:
    counts = Counter(branches)
    return [
        {"branch_name": branch, "candidate_count": counts[branch]}
        for branch in PREFERRED_BRANCH_ORDER
        if branch in counts
    ] + [
        {"branch_name": branch, "candidate_count": count}
        for branch, count in sorted(counts.items())
        if branch not in PREFERRED_BRANCH_ORDER
    ]


def branch_candidate_items(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[str]] = defaultdict(list)
    for row in candidate_rows:
        for branch in row.get("candidate_branch_names") or []:
            grouped[branch].append(str(row.get("candidate_id")))
    ordered = [branch for branch in PREFERRED_BRANCH_ORDER if branch in grouped]
    ordered.extend(sorted(branch for branch in grouped if branch not in PREFERRED_BRANCH_ORDER))
    return [
        {
            "branch_name": branch,
            "candidate_ids": sorted(set(grouped[branch])),
        }
        for branch in ordered
    ]


def request_exemplar(request_rows: Sequence[Dict[str, Any]], request_id: str) -> Dict[str, Any]:
    for row in request_rows:
        if row_request_id(row) == request_id:
            return dict(row)
    return {}


def build_request_rows(
    request_failure_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_request = group_by_request(candidate_rows)
    source_by_id = {row_request_id(row): row for row in request_failure_rows}
    rows: List[Dict[str, Any]] = []
    for request_id, request_candidate_rows in sorted(by_request.items(), key=lambda item: request_sort_key(item[0])):
        exemplar = request_exemplar(request_candidate_rows, request_id) or source_by_id.get(request_id, {})
        branch_names = [
            branch
            for candidate_row in request_candidate_rows
            for branch in candidate_row.get("candidate_branch_names") or []
        ]
        unique_branch_names = [
            branch for branch in PREFERRED_BRANCH_ORDER if branch in set(branch_names)
        ] + sorted(branch for branch in set(branch_names) if branch not in PREFERRED_BRANCH_ORDER)
        preferred = unique_branch_names[0] if unique_branch_names else "defer_goal_validity_terminal_policy"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_object_relation_goal_validity_branch_request_router",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "candidate_rows": len(request_candidate_rows),
                "request_branch_names": unique_branch_names,
                "request_branch_actions": [
                    BRANCH_ACTIONS.get(branch, branch) for branch in unique_branch_names
                ],
                "preferred_request_branch": preferred,
                "preferred_request_action": BRANCH_ACTIONS.get(preferred, preferred),
                "preferred_request_reason": BRANCH_REASONS.get(preferred, "defer terminal policy"),
                "branch_count_items": branch_count_items(branch_names),
                "branch_candidate_items": branch_candidate_items(request_candidate_rows),
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def source_request_index(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {row_request_id(row): dict(row) for row in rows}


def build_evaluated_request_rows(
    request_rows: Sequence[Dict[str, Any]],
    request_failure_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    source = source_request_index(request_failure_rows)
    rows: List[Dict[str, Any]] = []
    for row in request_rows:
        request_id = row_request_id(row)
        label = source.get(request_id, {})
        branch_names = set(row.get("request_branch_names") or [])
        source_tags = list(label.get("request_failure_tags") or [])
        coverage = []
        for tag in source_tags:
            target_branch = TAG_TO_BRANCH.get(tag, "manual_review")
            coverage.append(
                {
                    "failure_tag": tag,
                    "target_branch": target_branch,
                    "covered": target_branch in branch_names,
                }
            )
        rows.append(
            {
                **row,
                "validation_stage": "evaluation_only_object_relation_goal_validity_branch_request_router",
                "evaluation_only_request_failure_tags": source_tags,
                "evaluation_only_branch_coverage": coverage,
                "evaluation_only_all_failure_tags_covered": all(item["covered"] for item in coverage),
                "evaluation_only_candidate_rows": label.get("candidate_rows"),
                "evaluation_only_provisional_wrong_rows": label.get("provisional_wrong_rows"),
                "evaluation_only_rejected_positive_rows": label.get("rejected_positive_rows"),
                "evaluation_only_deferred_positive_rows": label.get("deferred_positive_rows"),
                "evaluation_only_rejected_negative_rows": label.get("rejected_negative_rows"),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def coverage_summary(evaluated_rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    tags = sorted(
        {
            item["failure_tag"]
            for row in evaluated_rows
            for item in row.get("evaluation_only_branch_coverage") or []
        }
    )
    summary: Dict[str, Dict[str, Any]] = {}
    for tag in tags:
        relevant = [
            (row, item)
            for row in evaluated_rows
            for item in row.get("evaluation_only_branch_coverage") or []
            if item.get("failure_tag") == tag
        ]
        covered = [row for row, item in relevant if item.get("covered") is True]
        uncovered = [row for row, item in relevant if item.get("covered") is not True]
        target_branch = TAG_TO_BRANCH.get(tag, "manual_review")
        summary[tag] = {
            "target_branch": target_branch,
            "source_request_rows": len(relevant),
            "covered_request_rows": len(covered),
            "uncovered_request_rows": len(uncovered),
            "uncovered_request_ids": [row_request_id(row) for row in uncovered],
        }
    return summary


def branch_request_count(evaluated_rows: Sequence[Dict[str, Any]], branch: str) -> int:
    return sum(branch in set(row.get("request_branch_names") or []) for row in evaluated_rows)


def count_covered_tag(evaluated_rows: Sequence[Dict[str, Any]], tag: str) -> int:
    count = 0
    for row in evaluated_rows:
        for item in row.get("evaluation_only_branch_coverage") or []:
            if item.get("failure_tag") == tag and item.get("covered") is True:
                count += 1
    return count


def summarize(
    *,
    contract: Dict[str, Any],
    failure_summary: Dict[str, Any],
    request_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = contract.get("evaluation_gates") or {}
    action_rows = list(request_rows) + list(candidate_rows)
    forbidden = action_forbidden_keys(action_rows)
    terminal_commit_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    branch_counts = compact_counter(
        branch
        for row in request_rows
        for branch in row.get("request_branch_names") or []
    )
    candidate_branch_counts = compact_counter(
        branch
        for row in candidate_rows
        for branch in row.get("candidate_branch_names") or []
    )
    tag_coverage = coverage_summary(evaluated_rows)
    uncovered_tags = sorted(
        tag for tag, payload in tag_coverage.items() if safe_int(payload.get("uncovered_request_rows"), 0) > 0
    )
    selected_next_branch = next(
        (branch for branch in PREFERRED_BRANCH_ORDER if branch_request_count(request_rows, branch) > 0),
        "defer_goal_validity_terminal_policy",
    )
    gate = {
        "input_failure_diagnostic_gate_passed": bool(
            ((failure_summary.get("gate") or {}).get("fresh_arbitration_failure_diagnostic_gate_passed"))
        ),
        "expected_request_rows_passed": len(request_rows) == safe_int(gates.get("expected_request_rows"), 0),
        "expected_candidate_rows_passed": len(candidate_rows) == safe_int(gates.get("expected_candidate_rows"), 0),
        "minimum_branch_routed_request_rows_passed": len(request_rows)
        >= safe_int(gates.get("minimum_branch_routed_request_rows"), 0),
        "minimum_unique_support_branch_requests_after_label_join_passed": count_covered_tag(
            evaluated_rows, "unique_independent_support_selects_wrong_goal"
        )
        >= safe_int(gates.get("minimum_unique_support_branch_requests_after_label_join"), 0),
        "minimum_missing_own_view_branch_requests_after_label_join_passed": count_covered_tag(
            evaluated_rows, "correct_goal_rejected_by_missing_strong_own_view"
        )
        >= safe_int(gates.get("minimum_missing_own_view_branch_requests_after_label_join"), 0),
        "minimum_partial_relation_depth_branch_requests_after_label_join_passed": count_covered_tag(
            evaluated_rows, "correct_goal_relation_depth_partial"
        )
        >= safe_int(gates.get("minimum_partial_relation_depth_branch_requests_after_label_join"), 0),
        "minimum_negative_missing_support_guard_requests_after_label_join_passed": count_covered_tag(
            evaluated_rows, "negative_candidates_blocked_by_missing_support"
        )
        >= safe_int(gates.get("minimum_negative_missing_support_guard_requests_after_label_join"), 0),
        "all_failure_tags_covered": len(uncovered_tags) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_commit_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_analysis": bool(evaluated_rows),
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["branch_evidence_router_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "terminal_utility_validation_allowed",
            "paper_claim_allowed",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "request_failure_rows": str(args.request_failure_rows),
            "candidate_failure_rows": str(args.candidate_failure_rows),
            "failure_summary": str(args.failure_summary),
        },
        "request_rows": len(request_rows),
        "candidate_rows": len(candidate_rows),
        "evaluated_branch_request_rows": len(evaluated_rows),
        "request_branch_counts": branch_counts,
        "candidate_branch_counts": candidate_branch_counts,
        "selected_next_branch": selected_next_branch,
        "selected_next_action": BRANCH_ACTIONS.get(selected_next_branch, selected_next_branch),
        "terminal_commit_rows": len(terminal_commit_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "failure_tag_branch_coverage": tag_coverage,
        "uncovered_failure_tags": uncovered_tags,
        "gate": gate,
        "diagnostic_conclusion": {
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "paper_claim_allowed": False,
            "recommended_next_action": "freeze_first_branch_specific_observation_contract_after_router_coverage_audit",
            "preferred_first_branch": selected_next_branch,
            "main_mechanism": "route_object_visibility_goal_validity_failures_into_nonterminal_evidence_requests",
        },
        "interpretation": {
            "fact": "The router writes request and candidate branch rows before joining failure tags for audit.",
            "agent_inference": (
                "Branch routing covers the fresh failure taxonomy without terminal commits. "
                "The next evidence contract should prioritize the unique-support branch because "
                "it explains why visible-object support can still choose a wrong ObjectNav goal."
            ),
        },
        "output_files": {
            "branch_request_rows": "goal_validity_object_relation_branch_request_rows.jsonl",
            "branch_candidate_rows": "goal_validity_object_relation_branch_candidate_rows.jsonl",
            "evaluated_branch_request_rows": "goal_validity_object_relation_evaluated_branch_request_rows.jsonl",
            "summary": "goal_validity_object_relation_branch_evidence_summary.json",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--request-failure-rows", type=Path)
    parser.add_argument("--candidate-failure-rows", type=Path)
    parser.add_argument("--failure-summary", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.request_failure_rows = source_path(args, contract, "request_failure_rows", "request_failure_rows")
    args.candidate_failure_rows = source_path(args, contract, "candidate_failure_rows", "candidate_failure_rows")
    args.failure_summary = source_path(args, contract, "failure_summary", "failure_summary")

    request_failure_rows = load_jsonl(args.request_failure_rows)
    candidate_failure_rows = load_jsonl(args.candidate_failure_rows)
    failure_summary = load_json(args.failure_summary)

    candidate_rows = build_candidate_rows(candidate_failure_rows)
    request_rows = build_request_rows(request_failure_rows, candidate_rows)
    evaluated_rows = build_evaluated_request_rows(request_rows, request_failure_rows)
    summary = summarize(
        contract=contract,
        failure_summary=failure_summary,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        evaluated_rows=evaluated_rows,
        args=args,
    )

    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "goal_validity_object_relation_branch_request_rows.jsonl", request_rows)
    write_jsonl(args.out_root / "goal_validity_object_relation_branch_candidate_rows.jsonl", candidate_rows)
    write_jsonl(
        args.out_root / "goal_validity_object_relation_evaluated_branch_request_rows.jsonl",
        evaluated_rows,
    )
    write_json(args.out_root / "goal_validity_object_relation_branch_evidence_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
