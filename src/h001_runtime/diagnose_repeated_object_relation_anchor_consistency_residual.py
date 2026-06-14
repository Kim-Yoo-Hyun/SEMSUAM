import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    load_json,
    load_jsonl,
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.repeated_object_relation_anchor_consistency_residual_diagnostic.v1"
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_repeated_object_relation_anchor_consistency_residual_diagnostic_v1"
)
SOURCE_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_repeated_object_relation_anchor_consistency_detector_evidence_v1"
)


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def row_request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_sort_key(candidate_id: str) -> Tuple[int, str]:
    tail = str(candidate_id).rsplit(":", 1)[-1]
    if tail.isdigit():
        return (safe_int(tail, 999999), str(candidate_id))
    return (999999, str(candidate_id))


def bool_map(row: Mapping[str, Any], key: str) -> Dict[str, bool]:
    value = row.get(key)
    if not isinstance(value, dict):
        return {}
    return {str(k): bool(v) for k, v in value.items()}


def int_map(row: Mapping[str, Any], key: str) -> Dict[str, int]:
    value = row.get(key)
    if not isinstance(value, dict):
        return {}
    return {str(k): safe_int(v, 0) for k, v in value.items()}


def classify_candidate(row: Mapping[str, Any]) -> str:
    status = str(row.get("candidate_consistency_status") or "")
    missing = [str(item) for item in row.get("required_target_support_missing_roles") or []]
    leakage = [str(item) for item in row.get("context_leakage_roles") or []]
    if "candidate_own_view" in missing:
        return "missing_own_view_target_support"
    if "orthogonal_axis_challenge_view" in missing or row.get("contradiction_role_count"):
        return "orthogonal_axis_or_required_role_contradiction"
    if "candidate_own_view" in leakage:
        return "own_view_context_leakage"
    if row.get("same_request_multiple_stable_candidates") is True:
        return "same_request_stable_rule_tie"
    if status == "ambiguous_repeated_object_candidate":
        return "ambiguous_repeated_object_unclassified"
    if status == "insufficient_candidate_evidence":
        return "insufficient_candidate_evidence_unclassified"
    return "manual_review_unexpected_relation_anchor_residual"


def residual_tags(row: Mapping[str, Any], residual_class: str) -> List[str]:
    target_support = bool_map(row, "target_support_by_role")
    context_support = bool_map(row, "context_support_by_role")
    target_counts = int_map(row, "target_associated_heading_count_by_role")
    context_counts = int_map(row, "context_associated_heading_count_by_role")
    tags = {residual_class}
    if all(target_support.values()) and len(target_support) >= 3:
        tags.add("target_supported_all_required_roles")
    if target_support.get("candidate_own_view") is False:
        tags.add("own_view_target_missing")
    if target_support.get("relation_anchor_context_view") is True:
        tags.add("relation_anchor_context_target_supported")
    if target_support.get("orthogonal_axis_challenge_view") is True:
        tags.add("orthogonal_axis_target_supported")
    if context_support.get("candidate_own_view") is True:
        tags.add("own_view_context_candidate_associated")
    if context_support.get("relation_anchor_context_view") is True:
        tags.add("relation_anchor_context_leakage")
    if context_support.get("orthogonal_axis_challenge_view") is True:
        tags.add("orthogonal_axis_context_leakage")
    if row.get("same_request_multiple_stable_candidates") is True:
        tags.add("same_request_multiple_stable_rule_candidates")
    if target_counts.get("candidate_own_view", 0) == 0:
        tags.add("zero_own_view_target_association")
    if context_counts.get("candidate_own_view", 0) > 0:
        tags.add("own_view_context_association_positive")
    return sorted(tags)


def recommended_action(residual_class: str) -> str:
    if residual_class in {"own_view_context_leakage", "same_request_stable_rule_tie"}:
        return "close_repeated_object_as_same_request_ambiguity"
    if residual_class == "missing_own_view_target_support":
        return "close_repeated_object_as_own_view_insufficient"
    if residual_class == "orthogonal_axis_or_required_role_contradiction":
        return "close_repeated_object_as_contradicted"
    return "defer_repeated_object_residual_manual_review"


def build_candidate_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in sorted(
        rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            candidate_sort_key(str(item.get("target_candidate_id") or "")),
        ),
    ):
        residual_class = classify_candidate(row)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "candidate_residual_diagnostic",
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row_request_id(row),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "target_candidate_id": row.get("target_candidate_id"),
                "source_candidate_consistency_status": row.get("candidate_consistency_status"),
                "source_recommended_nonterminal_action": row.get("recommended_nonterminal_action"),
                "residual_failure_class": residual_class,
                "residual_failure_tags": residual_tags(row, residual_class),
                "target_support_by_role": row.get("target_support_by_role"),
                "context_support_by_role": row.get("context_support_by_role"),
                "candidate_specific_support_by_role": row.get("candidate_specific_support_by_role"),
                "target_associated_heading_count_by_role": row.get("target_associated_heading_count_by_role"),
                "context_associated_heading_count_by_role": row.get("context_associated_heading_count_by_role"),
                "required_target_support_missing_roles": row.get("required_target_support_missing_roles"),
                "context_leakage_roles": row.get("context_leakage_roles"),
                "stable_rule_passed": row.get("stable_rule_passed") is True,
                "same_request_multiple_stable_candidates": row.get("same_request_multiple_stable_candidates") is True,
                "recommended_nonterminal_action": recommended_action(residual_class),
                "branch_promotable": False,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "terminal_utility_validation_allowed": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def group_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(row)
    return grouped


def request_status(rows: Sequence[Mapping[str, Any]]) -> str:
    classes = Counter(str(row.get("residual_failure_class")) for row in rows)
    if classes.get("same_request_stable_rule_tie", 0) and classes.get("own_view_context_leakage", 0):
        return "same_request_stable_tie_with_own_view_context_leakage"
    if classes.get("same_request_stable_rule_tie", 0):
        return "same_request_stable_rule_tie"
    if classes.get("own_view_context_leakage", 0):
        return "own_view_context_leakage_unresolved"
    if classes.get("missing_own_view_target_support", 0):
        return "own_view_target_support_insufficient"
    return "manual_review_unexpected_repeated_object_residual"


def build_request_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for rid, rows in sorted(group_by_request(candidate_rows).items(), key=lambda item: request_sort_key(item[0])):
        rows = sorted(
            rows,
            key=lambda item: candidate_sort_key(str(item.get("target_candidate_id") or "")),
        )
        first = rows[0]
        status = request_status(rows)
        class_counts = compact_counter(row.get("residual_failure_class") for row in rows)
        stable_rule_candidates = [
            row.get("target_candidate_id") for row in rows if row.get("stable_rule_passed") is True
        ]
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "request_residual_diagnostic",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": rid,
                "episode_key": first.get("episode_key"),
                "scene_key": first.get("scene_key"),
                "scene_id": first.get("scene_id"),
                "query": first.get("query"),
                "candidate_count": len(rows),
                "candidate_ids": [row.get("target_candidate_id") for row in rows],
                "stable_rule_candidate_count": len(stable_rule_candidates),
                "stable_rule_candidate_ids": stable_rule_candidates,
                "residual_failure_class_counts": class_counts,
                "residual_failure_tag_counts": compact_counter(
                    tag for row in rows for tag in row.get("residual_failure_tags", [])
                ),
                "request_residual_status": status,
                "promotable_branch_outcome": False,
                "recommended_nonterminal_action": "close_repeated_object_priority_branch_without_promotion",
                "next_branch_after_closure": "association_geometry_underlink",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "terminal_utility_validation_allowed": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_summary(
    args: argparse.Namespace,
    source_summary: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    action_rows = [*candidate_rows, *request_rows]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    candidate_commits = [row for row in action_rows if row.get("candidate_commit") is True]
    candidate_rejections = [row for row in action_rows if row.get("candidate_rejection") is True]
    promotable_rows = [row for row in request_rows if row.get("promotable_branch_outcome") is True]
    source_gate = (source_summary.get("gate") or {}).get(
        "relation_anchor_consistency_detector_evidence_gate_passed"
    )
    gate = {
        "source_detector_evidence_gate_passed": source_gate is True,
        "expected_candidate_rows_passed": len(candidate_rows) == 9,
        "expected_request_rows_passed": len(request_rows) == 3,
        "all_requests_diagnosed_passed": all(
            row.get("request_residual_status") != "manual_review_unexpected_repeated_object_residual"
            for row in request_rows
        ),
        "no_promotable_branch_outcome_passed": len(promotable_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
        "terminal_commit_rows_passed": len(terminal_rows) == 0,
        "candidate_commit_rows_passed": len(candidate_commits) == 0,
        "candidate_rejection_rows_passed": len(candidate_rejections) == 0,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed_passed": all(row.get("paper_claim_allowed") is False for row in action_rows),
    }
    gate["residual_diagnostic_gate_passed"] = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "source_root": str(args.source_root),
        "out_root": str(args.out_root),
        "source_summary": str(args.source_summary),
        "candidate_rows": len(candidate_rows),
        "request_rows": len(request_rows),
        "source_candidate_status_counts": source_summary.get("candidate_consistency_status_counts"),
        "residual_failure_class_counts": compact_counter(
            row.get("residual_failure_class") for row in candidate_rows
        ),
        "request_residual_status_counts": compact_counter(
            row.get("request_residual_status") for row in request_rows
        ),
        "recommended_request_action_counts": compact_counter(
            row.get("recommended_nonterminal_action") for row in request_rows
        ),
        "next_branch_after_closure_counts": compact_counter(
            row.get("next_branch_after_closure") for row in request_rows
        ),
        "stable_rule_candidate_count_by_request": {
            str(row.get("expanded_retrieval_request_id")): safe_int(
                row.get("stable_rule_candidate_count"), 0
            )
            for row in request_rows
        },
        "promotable_branch_outcome_rows": len(promotable_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": list(forbidden),
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commits),
        "candidate_rejection_rows": len(candidate_rejections),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in action_rows),
        "terminal_utility_validation_allowed": any(
            row.get("terminal_utility_validation_allowed") is True for row in action_rows
        ),
        "paper_claim_allowed": any(row.get("paper_claim_allowed") is True for row in action_rows),
        "gate": gate,
        "next_allowed_task": "design_association_geometry_underlink_repair_followup_evidence_contract",
        "interpretation": {
            "fact": "The residual diagnostic closes this repeated-object priority branch without a promotable outcome.",
            "agent_inference": "The branch failure is driven by same-request stable-rule ties, own-view context leakage, and one missing own-view target-support candidate per request.",
            "paper_claim": "No paper claim is allowed from this residual diagnostic alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    source_root = Path(args.source_root)
    out_root = Path(args.out_root)
    args.source_summary = Path(args.source_summary) if args.source_summary else (
        source_root / "relation_anchor_consistency_detector_evidence_summary.json"
    )
    candidate_path = Path(args.candidate_rows) if args.candidate_rows else (
        source_root / "relation_anchor_consistency_candidate_rows.jsonl"
    )

    source_summary = load_json(args.source_summary)
    source_candidate_rows = load_jsonl(candidate_path)
    candidate_rows = build_candidate_rows(source_candidate_rows)
    request_rows = build_request_rows(candidate_rows)
    summary = build_summary(args, source_summary, candidate_rows, request_rows)

    write_jsonl(out_root / "relation_anchor_consistency_residual_candidate_rows.jsonl", candidate_rows)
    write_jsonl(out_root / "relation_anchor_consistency_residual_request_rows.jsonl", request_rows)
    write_json(out_root / "relation_anchor_consistency_residual_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose residual repeated-object relation-anchor consistency failures."
    )
    parser.add_argument("--source-root", default=SOURCE_ROOT_DEFAULT)
    parser.add_argument("--source-summary", default=None)
    parser.add_argument("--candidate-rows", default=None)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(
        json.dumps(
            {
                "gate": summary["gate"]["residual_diagnostic_gate_passed"],
                "candidate_rows": summary["candidate_rows"],
                "request_rows": summary["request_rows"],
                "residual_failure_class_counts": summary["residual_failure_class_counts"],
                "request_residual_status_counts": summary["request_residual_status_counts"],
                "promotable_branch_outcome_rows": summary["promotable_branch_outcome_rows"],
                "next_allowed_task": summary["next_allowed_task"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
