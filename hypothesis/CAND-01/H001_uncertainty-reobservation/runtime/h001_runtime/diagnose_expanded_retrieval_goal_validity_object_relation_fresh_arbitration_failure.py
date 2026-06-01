import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    load_json,
    load_jsonl,
    ratio,
    request_sort_key,
    row_request_id,
    safe_float,
    safe_int,
    write_json,
    write_jsonl,
)
SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_fresh_arbitration_failure.v1"


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


def primary_failure_class(row: Dict[str, Any]) -> str:
    action = str(row.get("arbitration_action") or "")
    correct = row.get("evaluation_only_candidate_correct")
    status = row.get("relation_depth_evidence_status")
    if action.startswith("provisional_") and correct is False:
        return "wrong_provisional_unique_support"
    if action.startswith("provisional_") and correct is True:
        return "positive_provisional_unique_support"
    if action.startswith("reject_") and correct is True:
        return "positive_rejected_missing_independent_support"
    if action.startswith("reject_") and correct is False:
        return "negative_rejected_missing_independent_support"
    if action.startswith("defer_") and correct is True and status != "relation_depth_recheck_resolved":
        return "positive_deferred_partial_relation_depth"
    if action.startswith("defer_") and correct is False and status != "relation_depth_recheck_resolved":
        return "negative_deferred_partial_relation_depth"
    if action.startswith("defer_") and correct is True:
        return "positive_deferred_other"
    if action.startswith("defer_") and correct is False:
        return "negative_deferred_other"
    return "manual_review"


def row_tags(row: Dict[str, Any]) -> List[str]:
    tags = [primary_failure_class(row)]
    correct = row.get("evaluation_only_candidate_correct")
    status = row.get("relation_depth_evidence_status")
    action = str(row.get("arbitration_action") or "")
    base_support = row.get("base_candidate_specific_support") is True
    relation_depth = safe_int(row.get("relation_depth_consistent_count"), 0)
    base_depth = safe_int(row.get("base_consistent_depth_count"), 0)

    if correct is True and status == "relation_depth_recheck_resolved" and not base_support:
        tags.append("correct_relation_resolved_but_no_strong_own_view_support")
    if correct is True and status != "relation_depth_recheck_resolved":
        tags.append("correct_relation_depth_not_resolved")
    if correct is True and base_support and status != "relation_depth_recheck_resolved":
        tags.append("correct_has_independent_support_but_relation_depth_partial")
    if correct is False and base_support and status == "relation_depth_recheck_resolved":
        tags.append("wrong_has_independent_support_and_relation_depth_resolved")
    if correct is False and row.get("base_is_source_top") is True:
        tags.append("semantic_top_false_positive")
    if correct is True and row.get("base_is_source_top") is True and action.startswith(("reject_", "defer_")):
        tags.append("correct_source_top_not_sufficient_for_rule")
    if row.get("base_is_detector_strong_candidate") is True and correct is False:
        tags.append("detector_strong_candidate_false_positive")
    if row.get("base_is_detector_strong_rival") is True and correct is True:
        tags.append("correct_labeled_as_detector_strong_rival_or_context")
    if row.get("base_is_detector_strong_rival") is True and correct is False:
        tags.append("wrong_detector_strong_rival_visible")
    if relation_depth >= 8 and correct is False:
        tags.append("high_relation_depth_wrong_candidate")
    if relation_depth >= 8 and correct is True and action.startswith("reject_"):
        tags.append("high_relation_depth_positive_rejected")
    if base_depth == 0 and correct is True:
        tags.append("correct_missing_base_depth_association")
    return sorted(set(tags))


def build_failure_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in sorted(
        rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            safe_int(item.get("target_generated_rank"), 999999),
            candidate_id(item),
        ),
    ):
        tags = row_tags(row)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_fresh_object_relation_arbitration_failure_diagnostic",
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": candidate_id(row),
                "target_generated_rank": row.get("target_generated_rank"),
                "target_semantic_rank": row.get("target_semantic_rank"),
                "evaluation_only_candidate_correct": row.get("evaluation_only_candidate_correct"),
                "evaluation_only_candidate_rank": row.get("evaluation_only_candidate_rank"),
                "arbitration_action": row.get("arbitration_action"),
                "arbitration_reason": row.get("arbitration_reason"),
                "evaluation_only_interpretation": row.get("evaluation_only_interpretation"),
                "primary_failure_class": primary_failure_class(row),
                "failure_tags": tags,
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
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )
    return output


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(row)
    return grouped


def max_field(rows: Sequence[Dict[str, Any]], field: str) -> Any:
    values = [safe_float(row.get(field)) for row in rows]
    finite = [value for value in values if value is not None]
    return None if not finite else max(finite)


def request_tags(rows: Sequence[Dict[str, Any]]) -> List[str]:
    classes = {row["primary_failure_class"] for row in rows}
    tags: List[str] = []
    if "wrong_provisional_unique_support" in classes:
        tags.append("unique_independent_support_selects_wrong_goal")
    if "positive_rejected_missing_independent_support" in classes:
        tags.append("correct_goal_rejected_by_missing_strong_own_view")
    if "positive_deferred_partial_relation_depth" in classes:
        tags.append("correct_goal_relation_depth_partial")
    if "negative_rejected_missing_independent_support" in classes:
        tags.append("negative_candidates_blocked_by_missing_support")
    if (
        "wrong_provisional_unique_support" in classes
        and (
            "positive_rejected_missing_independent_support" in classes
            or "positive_deferred_partial_relation_depth" in classes
        )
    ):
        tags.append("object_visibility_preferred_over_true_goal_validity")
    if any("semantic_top_false_positive" in row["failure_tags"] for row in rows):
        tags.append("semantic_top_can_be_wrong_visible_object")
    if any("correct_has_independent_support_but_relation_depth_partial" in row["failure_tags"] for row in rows):
        tags.append("true_candidate_support_blocked_by_relation_depth_partial")
    if not tags:
        tags.append("manual_review")
    return sorted(set(tags))


def build_request_rows(failure_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    request_rows: List[Dict[str, Any]] = []
    for request_id, rows in sorted(group_by_request(failure_rows).items(), key=lambda item: request_sort_key(item[0])):
        correct_rows = [row for row in rows if row.get("evaluation_only_candidate_correct") is True]
        wrong_rows = [row for row in rows if row.get("evaluation_only_candidate_correct") is False]
        provisional_wrong = [row for row in rows if row["primary_failure_class"] == "wrong_provisional_unique_support"]
        rejected_positive = [row for row in rows if row["primary_failure_class"] == "positive_rejected_missing_independent_support"]
        deferred_positive = [row for row in rows if row["primary_failure_class"] == "positive_deferred_partial_relation_depth"]
        rejected_negative = [row for row in rows if row["primary_failure_class"] == "negative_rejected_missing_independent_support"]
        support_correct = [row for row in correct_rows if row.get("base_candidate_specific_support") is True]
        support_wrong = [row for row in wrong_rows if row.get("base_candidate_specific_support") is True]
        exemplar = rows[0]
        request_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_fresh_object_relation_arbitration_request_failure_diagnostic",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "candidate_rows": len(rows),
                "correct_candidate_rows": len(correct_rows),
                "wrong_candidate_rows": len(wrong_rows),
                "provisional_wrong_rows": len(provisional_wrong),
                "rejected_positive_rows": len(rejected_positive),
                "deferred_positive_rows": len(deferred_positive),
                "rejected_negative_rows": len(rejected_negative),
                "correct_candidate_specific_support_rows": len(support_correct),
                "wrong_candidate_specific_support_rows": len(support_wrong),
                "correct_candidate_ids": [row["candidate_id"] for row in correct_rows],
                "provisional_wrong_candidate_ids": [row["candidate_id"] for row in provisional_wrong],
                "rejected_positive_candidate_ids": [row["candidate_id"] for row in rejected_positive],
                "deferred_positive_candidate_ids": [row["candidate_id"] for row in deferred_positive],
                "max_correct_relation_depth_consistent_count": max_field(
                    correct_rows, "relation_depth_consistent_count"
                ),
                "max_wrong_relation_depth_consistent_count": max_field(
                    wrong_rows, "relation_depth_consistent_count"
                ),
                "max_correct_base_consistent_depth_count": max_field(correct_rows, "base_consistent_depth_count"),
                "max_wrong_base_consistent_depth_count": max_field(wrong_rows, "base_consistent_depth_count"),
                "request_failure_tags": request_tags(rows),
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )
    return request_rows


def summarize(
    *,
    contract: Dict[str, Any],
    arbitration_summary: Dict[str, Any],
    failure_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    minimum = contract.get("minimum_diagnostic_gate") or {}
    source_forbidden = list(arbitration_summary.get("action_evidence_forbidden_keys") or [])
    source_forbidden_count = safe_int(
        arbitration_summary.get("action_evidence_forbidden_key_count"),
        len(source_forbidden),
    )
    primary_counts = compact_counter(row["primary_failure_class"] for row in failure_rows)
    tag_counts = compact_counter(tag for row in failure_rows for tag in row["failure_tags"])
    request_tag_counts = compact_counter(tag for row in request_rows for tag in row["request_failure_tags"])
    wrong_provisional_rows = safe_int(primary_counts.get("wrong_provisional_unique_support"), 0)
    rejected_positive_rows = safe_int(primary_counts.get("positive_rejected_missing_independent_support"), 0)
    deferred_positive_rows = safe_int(primary_counts.get("positive_deferred_partial_relation_depth"), 0)
    rejected_negative_rows = safe_int(primary_counts.get("negative_rejected_missing_independent_support"), 0)

    gate = {
        "source_arbitration_gate_failed_as_expected": (
            (arbitration_summary.get("gate") or {}).get("object_relation_arbitration_rule_gate_passed") is False
        ),
        "expected_candidate_rows_passed": len(failure_rows) == safe_int(minimum.get("expected_candidate_rows"), 0),
        "expected_request_rows_passed": len(request_rows) == safe_int(minimum.get("expected_request_rows"), 0),
        "minimum_wrong_provisional_rows_passed": wrong_provisional_rows
        >= safe_int(minimum.get("minimum_wrong_provisional_rows"), 0),
        "minimum_rejected_positive_rows_passed": rejected_positive_rows
        >= safe_int(minimum.get("minimum_rejected_positive_rows"), 0),
        "minimum_deferred_positive_rows_passed": deferred_positive_rows
        >= safe_int(minimum.get("minimum_deferred_positive_rows"), 0),
        "minimum_rejected_negative_rows_passed": rejected_negative_rows
        >= safe_int(minimum.get("minimum_rejected_negative_rows"), 0),
        "action_evidence_forbidden_key_gate_passed": source_forbidden_count
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": all(row.get("terminal_commit") is not True for row in failure_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in failure_rows),
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["fresh_arbitration_failure_diagnostic_gate_passed"] = all(
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
            "arbitration_evaluated_rows": str(args.arbitration_evaluated_rows),
            "arbitration_summary": str(args.arbitration_summary),
        },
        "candidate_failure_rows": len(failure_rows),
        "request_failure_rows": len(request_rows),
        "primary_failure_class_counts": primary_counts,
        "failure_tag_counts": tag_counts,
        "request_failure_tag_counts": request_tag_counts,
        "wrong_provisional_rows": wrong_provisional_rows,
        "rejected_positive_rows": rejected_positive_rows,
        "deferred_positive_rows": deferred_positive_rows,
        "rejected_negative_rows": rejected_negative_rows,
        "defer_all_reference": {
            "terminal_commit_rows": 0,
            "success_commit_rows": 0,
            "wrong_goal_commit_rows": 0,
            "interpretation": "safe_but_inert",
        },
        "failed_rule_reference": {
            "terminal_commit_rows": 0,
            "would_not_be_safe_if_provisional_were_promoted": wrong_provisional_rows > 0,
            "positive_rejection_rows": rejected_positive_rows,
            "negative_rejection_rows": rejected_negative_rows,
        },
        "action_evidence_forbidden_key_count": source_forbidden_count,
        "action_evidence_forbidden_keys": source_forbidden,
        "diagnostic_label_fields_allowed": True,
        "gate": gate,
        "diagnostic_conclusion": {
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
            "main_failure_mechanism": "object_visibility_and_relation_depth_do_not_establish_objectnav_goal_validity",
            "recommended_next_action": "design_branch_specific_goal_validity_evidence_or_keep_active_observation_deferred",
        },
        "interpretation": {
            "fact": "The diagnostic is computed after the fixed arbitration decisions were written; evaluation labels are used only for analysis.",
            "agent_inference": "Fresh failures show the current rule confounds repeated-object visibility with goal validity: unique support can point to a wrong instance, and true goals may lack strong own-view support or have partial relation-depth evidence.",
        },
        "output_files": {
            "candidate_failure_rows": "object_relation_fresh_arbitration_failure_rows.jsonl",
            "request_failure_rows": "object_relation_fresh_arbitration_request_failure_rows.jsonl",
            "summary": "object_relation_fresh_arbitration_failure_summary.json",
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
    parser.add_argument("--arbitration-evaluated-rows", type=Path)
    parser.add_argument("--arbitration-summary", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.arbitration_evaluated_rows = source_path(
        args,
        contract,
        "arbitration_evaluated_rows",
        "arbitration_evaluated_rows",
    )
    args.arbitration_summary = source_path(
        args,
        contract,
        "arbitration_summary",
        "arbitration_summary",
    )

    evaluated_rows = load_jsonl(args.arbitration_evaluated_rows)
    arbitration_summary = load_json(args.arbitration_summary)
    failure_rows = build_failure_rows(evaluated_rows)
    request_rows = build_request_rows(failure_rows)
    summary = summarize(
        contract=contract,
        arbitration_summary=arbitration_summary,
        failure_rows=failure_rows,
        request_rows=request_rows,
        args=args,
    )

    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "object_relation_fresh_arbitration_failure_rows.jsonl", failure_rows)
    write_jsonl(args.out_root / "object_relation_fresh_arbitration_request_failure_rows.jsonl", request_rows)
    write_json(args.out_root / "object_relation_fresh_arbitration_failure_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
