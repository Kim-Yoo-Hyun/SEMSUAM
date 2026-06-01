import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    load_json,
    load_jsonl,
    ratio,
    request_sort_key,
    row_request_id,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_arbitration.v1"


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


def candidate_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (row_request_id(row), candidate_id(row))


def request_groups(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    return grouped


def candidate_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        indexed[candidate_key(row)] = dict(row)
    return indexed


def eligible_base_candidates(rows: Sequence[Dict[str, Any]], *, min_base_depth_consistent: int) -> List[Dict[str, Any]]:
    eligible = []
    for row in rows:
        if row.get("candidate_specific_support") is not True:
            continue
        if row.get("has_candidate_association") is not True:
            continue
        if safe_int(row.get("consistent_depth_count"), 0) < min_base_depth_consistent:
            continue
        eligible.append(dict(row))
    return eligible


def decision_for_request(
    request_row: Dict[str, Any],
    base_row: Dict[str, Any],
    eligible_rows: Sequence[Dict[str, Any]],
    *,
    min_base_depth_consistent: int,
) -> Tuple[str, str]:
    if request_row.get("evidence_status") != "relation_depth_recheck_resolved":
        return (
            "defer_relation_depth_unresolved_or_partial",
            "relation_depth_recheck_not_resolved",
        )
    if not base_row:
        return (
            "defer_missing_base_candidate_support_row",
            "candidate_missing_from_full_candidate_specific_substrate",
        )
    if base_row.get("candidate_specific_support") is not True:
        return (
            "reject_relation_depth_resolved_without_independent_candidate_support",
            "relation_depth_evidence_cannot_override_missing_independent_candidate_specific_support",
        )
    if base_row.get("has_candidate_association") is not True:
        return (
            "reject_relation_depth_resolved_without_base_detector_association",
            "relation_depth_evidence_repaired_candidate_but_base_candidate_specific_substrate_did_not_associate_it",
        )
    if safe_int(base_row.get("consistent_depth_count"), 0) < min_base_depth_consistent:
        return (
            "reject_relation_depth_resolved_without_base_depth_consistency",
            "base_candidate_specific_substrate_lacks_minimum_depth_consistency",
        )
    if len(eligible_rows) != 1:
        return (
            "defer_support_saturation_no_unique_goal_identity",
            "multiple_candidate_specific_supported_candidates_remain_after_non_gt_filters",
        )
    if candidate_id(eligible_rows[0]) != candidate_id(request_row):
        return (
            "defer_candidate_not_unique_eligible_goal_identity",
            "another_candidate_is_the_only_non_gt_eligible_candidate",
        )
    return (
        "provisional_unique_goal_validity_candidate_requires_fresh_validation",
        "unique_non_gt_eligible_candidate_found_but_terminal_utility_is_not_allowed_in_this_smoke",
    )


def build_decision_rows(
    request_rows: Sequence[Dict[str, Any]],
    base_candidate_rows: Sequence[Dict[str, Any]],
    *,
    min_base_depth_consistent: int,
) -> List[Dict[str, Any]]:
    base_index = candidate_index(base_candidate_rows)
    grouped = request_groups(base_candidate_rows)
    rows: List[Dict[str, Any]] = []
    for request_row in sorted(
        request_rows,
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            safe_int(row.get("target_generated_rank"), 999999),
            candidate_id(row),
        ),
    ):
        request_id = row_request_id(request_row)
        cid = candidate_id(request_row)
        base_row = base_index.get((request_id, cid), {})
        eligible = eligible_base_candidates(
            grouped.get(request_id, []),
            min_base_depth_consistent=min_base_depth_consistent,
        )
        action, reason = decision_for_request(
            request_row,
            base_row,
            eligible,
            min_base_depth_consistent=min_base_depth_consistent,
        )
        terminal_commit = False
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_object_relation_goal_validity_arbitration",
                "policy": "relation_depth_guarded_non_gt_arbitration_v1",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": request_row.get("rival_identity_request_id"),
                "episode_key": request_row.get("episode_key"),
                "scene_key": request_row.get("scene_key"),
                "scene_id": request_row.get("scene_id"),
                "query": request_row.get("query"),
                "candidate_id": cid,
                "target_candidate_id": cid,
                "target_generated_rank": request_row.get("target_generated_rank"),
                "target_semantic_rank": request_row.get("target_semantic_rank"),
                "relation_depth_evidence_status": request_row.get("evidence_status"),
                "relation_direction_source_count": request_row.get("direction_source_count"),
                "relation_resolved_direction_source_count": request_row.get("resolved_direction_source_count"),
                "relation_associated_heading_count": request_row.get("associated_heading_count"),
                "relation_depth_consistent_count": request_row.get("depth_consistent_count"),
                "relation_inside_mask_count": request_row.get("inside_mask_count"),
                "base_candidate_evidence_class": base_row.get("candidate_evidence_class"),
                "base_candidate_role": base_row.get("candidate_role"),
                "base_is_source_top": base_row.get("is_source_top"),
                "base_is_detector_strong_candidate": base_row.get("is_detector_strong_candidate"),
                "base_is_detector_strong_rival": base_row.get("is_detector_strong_rival"),
                "base_is_local_context_candidate": base_row.get("is_local_context_candidate"),
                "base_candidate_specific_support": base_row.get("candidate_specific_support"),
                "base_has_candidate_association": base_row.get("has_candidate_association"),
                "base_associated_heading_count": base_row.get("associated_heading_count"),
                "base_consistent_depth_count": base_row.get("consistent_depth_count"),
                "base_depth_mismatch_count": base_row.get("depth_mismatch_count"),
                "base_mask_hit_count": base_row.get("mask_hit_count"),
                "base_best_box_score": base_row.get("best_box_score"),
                "base_min_depth_error_m": base_row.get("min_depth_error_m"),
                "support_saturation_eligible_candidate_count": len(eligible),
                "support_saturation_total_candidate_count": len(grouped.get(request_id, [])),
                "support_saturation_rate": ratio(len(eligible), len(grouped.get(request_id, []))),
                "arbitration_action": action,
                "arbitration_reason": reason,
                "terminal_policy_allowed": False,
                "terminal_commit": terminal_commit,
                "uses_gt_for_action": False,
            }
        )
    return rows


def evaluation_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        indexed[candidate_key(row)] = dict(row)
    return indexed


def build_evaluated_rows(
    decision_rows: Sequence[Dict[str, Any]],
    evaluation_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    indexed = evaluation_index(evaluation_rows)
    rows: List[Dict[str, Any]] = []
    for row in decision_rows:
        label = indexed.get(candidate_key(row)) or {}
        candidate_correct = label.get("evaluation_only_candidate_correct")
        action = str(row.get("arbitration_action") or "")
        if action.startswith("reject_") and candidate_correct is False:
            interpretation = "rejected_relation_depth_resolved_negative_candidate"
        elif action.startswith("reject_") and candidate_correct is True:
            interpretation = "rejected_relation_depth_resolved_positive_candidate"
        elif action.startswith("provisional_") and candidate_correct is False:
            interpretation = "provisional_relation_depth_resolved_negative_candidate"
        elif action.startswith("provisional_") and candidate_correct is True:
            interpretation = "provisional_relation_depth_resolved_positive_candidate"
        elif action.startswith("defer_") and candidate_correct is False:
            interpretation = "deferred_relation_depth_resolved_negative_candidate"
        elif action.startswith("defer_") and candidate_correct is True:
            interpretation = "deferred_relation_depth_resolved_positive_candidate"
        else:
            interpretation = "no_terminal_utility_label_join"
        rows.append(
            {
                **row,
                "validation_stage": "evaluation_only_object_relation_goal_validity_arbitration",
                "evaluation_only_candidate_correct": candidate_correct,
                "evaluation_only_candidate_rank": label.get("evaluation_only_candidate_rank"),
                "evaluation_only_coverage_gap_taxonomy": label.get("evaluation_only_coverage_gap_taxonomy"),
                "evaluation_only_interpretation": interpretation,
                "uses_gt_for_analysis": bool(label),
            }
        )
    return rows


def simple_alternatives(evaluated_rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    rows = list(evaluated_rows)

    def commit_summary(committed: Sequence[Dict[str, Any]], reason: str) -> Dict[str, Any]:
        wrong = [row for row in committed if row.get("evaluation_only_candidate_correct") is False]
        success = [row for row in committed if row.get("evaluation_only_candidate_correct") is True]
        return {
            "decision": "rejected",
            "counterfactual_commit_rows": len(committed),
            "evaluation_only_success_commit_rows": len(success),
            "evaluation_only_wrong_commit_rows": len(wrong),
            "reason": reason,
        }

    proposed_rejected = [
        row
        for row in rows
        if str(row.get("arbitration_action") or "").startswith("reject_")
    ]
    relation_depth_resolved = [
        row for row in rows if row.get("relation_depth_evidence_status") == "relation_depth_recheck_resolved"
    ]
    return {
        "relation_depth_resolved_commit": commit_summary(
            relation_depth_resolved,
            "commits relation-depth-resolved candidates directly and treats detector-depth repair as terminal goal validity"
        ),
        "box_or_mask_presence_commit": commit_summary(
            rows,
            "treats object visibility as goal validity and would commit visible repeated-object candidates"
        ),
        "high_association_count_commit": commit_summary(
            rows,
            "treats high association/depth support as goal validity without identity arbitration"
        ),
        "relation_depth_guarded_non_gt_arbitration_v1": {
            "decision": "bounded_smoke_rejects_negative_candidates",
            "terminal_commit_rows": 0,
            "rejected_rows": len(proposed_rejected),
            "evaluation_only_rejected_negative_rows": sum(
                1 for row in proposed_rejected if row.get("evaluation_only_candidate_correct") is False
            ),
            "reason_counts": compact_counter(row.get("arbitration_action") for row in rows),
        },
        "defer_all": {
            "decision": "safe_but_inert",
            "terminal_commit_rows": 0,
            "reason": "preserves safety but does not test the non-GT rejection mechanism",
        },
    }


def summarize(
    *,
    contract: Dict[str, Any],
    object_relation_summary: Dict[str, Any],
    full_objective_summary: Dict[str, Any],
    decision_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    base_candidate_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    minimum = contract.get("minimum_rule_gate") or {}
    forbidden = action_forbidden_keys(decision_rows)
    terminal_rows = [row for row in decision_rows if row.get("terminal_commit") is True]
    rejected_rows = [
        row for row in decision_rows if str(row.get("arbitration_action") or "").startswith("reject_")
    ]
    relation_depth_resolved_rows = [
        row for row in decision_rows if row.get("relation_depth_evidence_status") == "relation_depth_recheck_resolved"
    ]
    rejected_negative_rows = [
        row
        for row in evaluated_rows
        if str(row.get("arbitration_action") or "").startswith("reject_")
        and row.get("evaluation_only_candidate_correct") is False
    ]
    rejected_positive_rows = [
        row
        for row in evaluated_rows
        if str(row.get("arbitration_action") or "").startswith("reject_")
        and row.get("evaluation_only_candidate_correct") is True
    ]
    provisional_rows = [
        row for row in evaluated_rows if str(row.get("arbitration_action") or "").startswith("provisional_")
    ]
    provisional_negative_rows = [
        row for row in provisional_rows if row.get("evaluation_only_candidate_correct") is False
    ]
    provisional_positive_rows = [
        row for row in provisional_rows if row.get("evaluation_only_candidate_correct") is True
    ]
    gate = {
        "source_object_relation_evidence_gate_passed": bool(
            ((object_relation_summary.get("gate") or {}).get("object_relation_evidence_gate_passed"))
        ),
        "source_full_objective_gate_passed": bool(
            ((full_objective_summary.get("gate") or {}).get("objective_analyzer_gate_passed"))
        ),
        "expected_request_rows_passed": len(decision_rows)
        == safe_int(minimum.get("expected_request_rows"), 0),
        "expected_relation_depth_resolved_rows_passed": len(relation_depth_resolved_rows)
        == safe_int(minimum.get("expected_relation_depth_resolved_rows"), 0),
        "minimum_rejected_relation_depth_resolved_rows_passed": len(rejected_rows)
        >= safe_int(minimum.get("minimum_rejected_relation_depth_resolved_rows"), 0),
        "minimum_evaluation_only_rejected_negative_rows_passed": len(rejected_negative_rows)
        >= safe_int(minimum.get("minimum_evaluation_only_rejected_negative_rows"), 0),
        "maximum_evaluation_only_rejected_positive_rows_passed": len(rejected_positive_rows)
        <= safe_int(minimum.get("maximum_evaluation_only_rejected_positive_rows"), 0),
        "maximum_evaluation_only_provisional_negative_rows_passed": len(provisional_negative_rows)
        <= safe_int(minimum.get("maximum_evaluation_only_provisional_negative_rows"), 0),
        "minimum_evaluation_only_provisional_positive_rows_passed": len(provisional_positive_rows)
        >= safe_int(minimum.get("minimum_evaluation_only_provisional_positive_rows"), 0),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(minimum.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in decision_rows),
        "uses_gt_for_analysis": bool(evaluated_rows),
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["object_relation_arbitration_rule_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key not in {"uses_gt_for_action", "uses_gt_for_analysis", "terminal_utility_validation_allowed", "paper_claim_allowed"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "object_relation_request_rows": str(args.object_relation_request_rows),
            "object_relation_evaluation_rows": str(args.object_relation_evaluation_rows),
            "object_relation_summary": str(args.object_relation_summary),
            "full_objective_candidate_rows": str(args.full_objective_candidate_rows),
            "full_objective_summary": str(args.full_objective_summary),
        },
        "decision_rows": len(decision_rows),
        "evaluated_rows": len(evaluated_rows),
        "base_candidate_rows": len(base_candidate_rows),
        "relation_depth_resolved_rows": len(relation_depth_resolved_rows),
        "rejected_rows": len(rejected_rows),
        "rejected_negative_rows": len(rejected_negative_rows),
        "rejected_positive_rows": len(rejected_positive_rows),
        "provisional_rows": len(provisional_rows),
        "provisional_negative_rows": len(provisional_negative_rows),
        "provisional_positive_rows": len(provisional_positive_rows),
        "terminal_commit_rows": len(terminal_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden,
        "decision_action_counts": compact_counter(row.get("arbitration_action") for row in decision_rows),
        "evaluation_only_candidate_correct_counts": compact_counter(
            row.get("evaluation_only_candidate_correct") for row in evaluated_rows
        ),
        "evaluation_only_interpretation_counts": compact_counter(
            row.get("evaluation_only_interpretation") for row in evaluated_rows
        ),
        "gate": gate,
        "simpler_alternatives": simple_alternatives(evaluated_rows),
        "diagnostic_conclusion": {
            "non_gt_rule_rejects_relation_depth_resolved_negative_candidates": len(rejected_negative_rows)
            >= safe_int(minimum.get("minimum_evaluation_only_rejected_negative_rows"), 0),
            "non_gt_rule_has_wrong_provisional_candidates": len(provisional_negative_rows) > 0,
            "non_gt_rule_rejects_positive_candidates": len(rejected_positive_rows) > 0,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "recommended_next_action": (
                "diagnose_fresh_arbitration_failure_before_terminal_contract"
                if (len(provisional_negative_rows) > 0 or len(rejected_positive_rows) > 0)
                else "validate_non_gt_arbitration_on_additional_fresh_goal_validity_rows_before_terminal_contract"
            ),
        },
        "interpretation": {
            "fact": "The analyzer applies the non-GT arbitration rule before evaluation labels are joined.",
            "agent_inference": "The rule can be used only as nonterminal diagnostic evidence unless fresh evaluation labels show no rejected positives and no provisional negative candidates.",
        },
        "output_files": {
            "decision_rows": "object_relation_arbitration_decision_rows.jsonl",
            "evaluated_rows": "object_relation_arbitration_evaluated_rows.jsonl",
            "summary": "object_relation_arbitration_summary.json",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(evaluated_rows),
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--object-relation-request-rows", type=Path)
    parser.add_argument("--object-relation-evaluation-rows", type=Path)
    parser.add_argument("--object-relation-summary", type=Path)
    parser.add_argument("--full-objective-candidate-rows", type=Path)
    parser.add_argument("--full-objective-summary", type=Path)
    parser.add_argument("--min-base-depth-consistent", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.object_relation_request_rows = source_path(args, contract, "object_relation_request_rows", "object_relation_request_rows")
    args.object_relation_evaluation_rows = source_path(args, contract, "object_relation_evaluation_rows", "object_relation_evaluation_rows")
    args.object_relation_summary = source_path(args, contract, "object_relation_summary", "object_relation_summary")
    args.full_objective_candidate_rows = source_path(args, contract, "full_objective_candidate_rows", "full_objective_candidate_rows")
    args.full_objective_summary = source_path(args, contract, "full_objective_summary", "full_objective_summary")

    request_rows = load_jsonl(args.object_relation_request_rows)
    evaluation_rows = load_jsonl(args.object_relation_evaluation_rows)
    base_candidate_rows = load_jsonl(args.full_objective_candidate_rows)
    object_relation_summary = load_json(args.object_relation_summary)
    full_objective_summary = load_json(args.full_objective_summary)

    decision_rows = build_decision_rows(
        request_rows,
        base_candidate_rows,
        min_base_depth_consistent=args.min_base_depth_consistent,
    )
    evaluated_rows = build_evaluated_rows(decision_rows, evaluation_rows)
    summary = summarize(
        contract=contract,
        object_relation_summary=object_relation_summary,
        full_objective_summary=full_objective_summary,
        decision_rows=decision_rows,
        evaluated_rows=evaluated_rows,
        base_candidate_rows=base_candidate_rows,
        args=args,
    )

    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "object_relation_arbitration_decision_rows.jsonl", decision_rows)
    write_jsonl(args.out_root / "object_relation_arbitration_evaluated_rows.jsonl", evaluated_rows)
    write_json(args.out_root / "object_relation_arbitration_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
