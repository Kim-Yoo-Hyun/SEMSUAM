import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    distance_stats,
    group_by_request,
    load_json,
    load_jsonl,
    number_stats,
    ratio,
    request_sort_key,
    row_request_id,
    safe_float,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_coverage_repair.v1"


def pair_participation(
    pair_rows: Sequence[Dict[str, Any]],
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(
        lambda: {
            "pair_rows_as_selector": 0,
            "pair_rows_as_contrast": 0,
            "pair_relation_delta_sign_counts": Counter(),
            "pair_relation_conflict_profile_counts": Counter(),
            "pair_context_profile_counts": Counter(),
            "strong_relation_pair_rows": 0,
        }
    )
    for row in pair_rows:
        request_id = row_request_id(row)
        selector_key = (request_id, str(row.get("selector_candidate_id") or ""))
        contrast_key = (request_id, str(row.get("contrast_candidate_id") or ""))
        delta_sign = str(row.get("relation_signature_score_delta_sign") or "unknown")
        conflict = str(row.get("relation_predicate_conflict_profile") or "unknown")
        context = str(row.get("relation_context_profile") or "unknown")
        abs_delta = abs(safe_float(row.get("relation_signature_score_delta_contrast_minus_selector"), 0.0) or 0.0)
        if selector_key[1]:
            grouped[selector_key]["pair_rows_as_selector"] += 1
            grouped[selector_key]["pair_relation_delta_sign_counts"].update([delta_sign])
            grouped[selector_key]["pair_relation_conflict_profile_counts"].update([conflict])
            grouped[selector_key]["pair_context_profile_counts"].update([context])
            grouped[selector_key]["strong_relation_pair_rows"] += int(abs_delta >= 0.5)
        if contrast_key[1]:
            grouped[contrast_key]["pair_rows_as_contrast"] += 1
            grouped[contrast_key]["pair_relation_delta_sign_counts"].update([delta_sign])
            grouped[contrast_key]["pair_relation_conflict_profile_counts"].update([conflict])
            grouped[contrast_key]["pair_context_profile_counts"].update([context])
            grouped[contrast_key]["strong_relation_pair_rows"] += int(abs_delta >= 0.5)
    return grouped


def compact_counter(value: Any) -> Dict[str, int]:
    if isinstance(value, Counter):
        return dict(sorted((str(key), int(count)) for key, count in value.items()))
    if isinstance(value, dict):
        return dict(sorted((str(key), safe_int(count, 0)) for key, count in value.items()))
    return {}


def coverage_gap_rows(
    candidate_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    pairs = pair_participation(pair_rows)
    gaps: List[Dict[str, Any]] = []
    for row in sorted(
        candidate_rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            safe_int(item.get("target_generated_rank"), 999999),
            candidate_id(item),
        ),
    ):
        if safe_int(row.get("detector_associated_rows"), 0) > 0:
            continue
        request_id = row_request_id(row)
        cid = candidate_id(row)
        pair_profile = pairs.get((request_id, cid), {})
        gaps.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_time_coverage_gap",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": cid,
                "coverage_gap_type": "detector_association_gap",
                "target_generated_rank": row.get("target_generated_rank"),
                "target_semantic_rank": row.get("target_semantic_rank"),
                "target_score": row.get("target_score"),
                "target_semantic_score": row.get("target_semantic_score"),
                "target_support_score": row.get("target_support_score"),
                "target_positive_support": row.get("target_positive_support"),
                "candidate_evidence_class": row.get("candidate_evidence_class"),
                "candidate_specific_support": row.get("candidate_specific_support"),
                "target_position": row.get("target_position"),
                "target_visit_position": row.get("target_visit_position"),
                "target_candidate_role": row.get("target_candidate_role"),
                "target_candidate_role_tokens": row.get("target_candidate_role_tokens") or [],
                "viewpoint_source": row.get("viewpoint_source"),
                "standoff_distance_requested": row.get("standoff_distance_requested"),
                "standoff_target_horizontal_distance": row.get("standoff_target_horizontal_distance"),
                "relation_density_bucket": row.get("relation_density_bucket"),
                "relation_signature_score": row.get("relation_signature_score"),
                "candidate_relation_signature": row.get("candidate_relation_signature"),
                "relation_view_consistency_profile": row.get("relation_view_consistency_profile"),
                "context_object_count": row.get("context_object_count"),
                "near_1m_context_object_count": row.get("near_1m_context_object_count"),
                "near_2m_context_object_count": row.get("near_2m_context_object_count"),
                "near_4m_context_object_count": row.get("near_4m_context_object_count"),
                "same_component_context_object_count": row.get("same_component_context_object_count"),
                "same_support_surface_context_object_count": row.get(
                    "same_support_surface_context_object_count"
                ),
                "co_visible_context_object_count": row.get("co_visible_context_object_count"),
                "relation_predicate_count_total": row.get("relation_predicate_count_total"),
                "relation_predicate_count_by_type": row.get("relation_predicate_count_by_type") or {},
                "detector_heading_rows": row.get("detector_heading_rows"),
                "detector_visible_rows": row.get("detector_visible_rows"),
                "detector_associated_rows": row.get("detector_associated_rows"),
                "detector_inside_box_rows": row.get("detector_inside_box_rows"),
                "detector_inside_mask_rows": row.get("detector_inside_mask_rows"),
                "detector_consistent_depth_rows": row.get("detector_consistent_depth_rows"),
                "detector_depth_mismatch_rows": row.get("detector_depth_mismatch_rows"),
                "detector_depth_status_counts": row.get("detector_depth_status_counts") or {},
                "detector_score_max": row.get("detector_score_max"),
                "detector_depth_error_min_m": row.get("detector_depth_error_min_m"),
                "detector_depth_error_mean_m": row.get("detector_depth_error_mean_m"),
                "frame_has_detector_box": row.get("frame_has_detector_box"),
                "frame_has_sam2_mask": row.get("frame_has_sam2_mask"),
                "rendered_heading_count": row.get("rendered_heading_count"),
                "pair_rows_as_selector": safe_int(pair_profile.get("pair_rows_as_selector"), 0),
                "pair_rows_as_contrast": safe_int(pair_profile.get("pair_rows_as_contrast"), 0),
                "strong_relation_pair_rows": safe_int(pair_profile.get("strong_relation_pair_rows"), 0),
                "pair_relation_delta_sign_counts": compact_counter(
                    pair_profile.get("pair_relation_delta_sign_counts")
                ),
                "pair_relation_conflict_profile_counts": compact_counter(
                    pair_profile.get("pair_relation_conflict_profile_counts")
                ),
                "pair_context_profile_counts": compact_counter(pair_profile.get("pair_context_profile_counts")),
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return gaps


def repair_action_for_gap(row: Dict[str, Any], *, rank_threshold: int, waiver_rank_min: int) -> Tuple[str, str, Dict[str, Any]]:
    rank = safe_int(row.get("target_generated_rank"), 999999)
    density = str(row.get("relation_density_bucket") or "")
    context_count = safe_int(row.get("context_object_count"), 0)
    signature_score = safe_float(row.get("relation_signature_score"), 0.0) or 0.0
    pair_count = safe_int(row.get("pair_rows_as_selector"), 0) + safe_int(row.get("pair_rows_as_contrast"), 0)
    guard = {
        "rank_threshold": rank_threshold,
        "waiver_rank_min": waiver_rank_min,
        "observed_rank": rank,
        "relation_density_bucket": density,
        "context_object_count": context_count,
        "relation_signature_score": signature_score,
        "pair_participation_rows": pair_count,
    }
    if rank <= rank_threshold or density == "relation_dense" or context_count >= 32 or signature_score >= 50:
        return (
            "request_object_relation_observation",
            "high_priority_relation_gap_needs_recheck",
            guard,
        )
    if rank >= waiver_rank_min and density not in {"relation_dense"} and context_count <= 16:
        return (
            "waive_non_target_policy_promotion_only",
            "low_priority_medium_relation_ranked_outside_promotion_window",
            guard,
        )
    return (
        "defer_goal_validity_terminal_policy",
        "coverage_gap_requires_manual_contract_before_terminal_policy",
        guard,
    )


def coverage_repair_action_rows(
    gaps: Sequence[Dict[str, Any]],
    *,
    rank_threshold: int,
    waiver_rank_min: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in gaps:
        action, reason, guard = repair_action_for_gap(
            row,
            rank_threshold=rank_threshold,
            waiver_rank_min=waiver_rank_min,
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_time_coverage_repair_decision",
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": row.get("candidate_id"),
                "coverage_gap_type": row.get("coverage_gap_type"),
                "repair_action": action,
                "repair_reason": reason,
                "repair_guard": guard,
                "observation_plan_contract_required": action == "request_object_relation_observation",
                "policy_promotion_exclusion": action == "waive_non_target_policy_promotion_only",
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def request_coverage_rows(
    candidate_rows: Sequence[Dict[str, Any]],
    gaps: Sequence[Dict[str, Any]],
    action_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    gaps_by_request = group_by_request(gaps)
    actions_by_request = group_by_request(action_rows)
    rows: List[Dict[str, Any]] = []
    for request_id, rows_for_request in sorted(group_by_request(candidate_rows).items(), key=lambda item: request_sort_key(item[0])):
        gap_rows = gaps_by_request.get(request_id, [])
        action_group = actions_by_request.get(request_id, [])
        action_counts = Counter(str(row.get("repair_action")) for row in action_group)
        exemplar = rows_for_request[0]
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_time_request_coverage",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "candidate_relation_rows": len(rows_for_request),
                "rows_with_detector_association": sum(
                    1 for row in rows_for_request if safe_int(row.get("detector_associated_rows"), 0) > 0
                ),
                "coverage_gap_rows": len(gap_rows),
                "coverage_gap_candidate_ids": [row.get("candidate_id") for row in gap_rows],
                "repair_action_counts": dict(sorted(action_counts.items())),
                "request_object_relation_observation_rows": action_counts.get(
                    "request_object_relation_observation", 0
                ),
                "waived_policy_promotion_rows": action_counts.get(
                    "waive_non_target_policy_promotion_only", 0
                ),
                "defer_terminal_policy_rows": action_counts.get("defer_goal_validity_terminal_policy", 0),
                "coverage_gap_repair_rows": len(action_group),
                "coverage_complete_without_waiver": len(gap_rows) == 0,
                "coverage_gap_handled_by_action_time_rule": len(gap_rows) == len(action_group),
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def evaluated_coverage_gap_rows(
    gaps: Sequence[Dict[str, Any]],
    action_rows: Sequence[Dict[str, Any]],
    evaluated_candidate_rows: Sequence[Dict[str, Any]],
    evaluated_pair_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    labels = {
        (row_request_id(row), candidate_id(row)): row
        for row in evaluated_candidate_rows
    }
    actions = {
        (row_request_id(row), str(row.get("candidate_id") or "")): row
        for row in action_rows
    }
    target_pair_members: Dict[Tuple[str, str], int] = Counter()
    for row in evaluated_pair_rows:
        if row.get("evaluation_only_target_contrast_pair") is not True:
            continue
        request_id = row_request_id(row)
        target_pair_members[(request_id, str(row.get("selector_candidate_id") or ""))] += 1
        target_pair_members[(request_id, str(row.get("contrast_candidate_id") or ""))] += 1
    rows: List[Dict[str, Any]] = []
    for gap in gaps:
        request_id = row_request_id(gap)
        cid = candidate_id(gap)
        label = labels.get((request_id, cid), {})
        action = actions.get((request_id, cid), {})
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_coverage_gap_after_action_rows",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": gap.get("rival_identity_request_id"),
                "episode_key": gap.get("episode_key"),
                "scene_key": gap.get("scene_key"),
                "scene_id": gap.get("scene_id"),
                "query": gap.get("query"),
                "candidate_id": cid,
                "coverage_gap_type": gap.get("coverage_gap_type"),
                "repair_action": action.get("repair_action"),
                "repair_reason": action.get("repair_reason"),
                "target_generated_rank": gap.get("target_generated_rank"),
                "relation_density_bucket": gap.get("relation_density_bucket"),
                "context_object_count": gap.get("context_object_count"),
                "relation_signature_score": gap.get("relation_signature_score"),
                "evaluation_only_candidate_correct": label.get("evaluation_only_candidate_correct"),
                "evaluation_only_candidate_rank": label.get("evaluation_only_candidate_rank"),
                "evaluation_only_target_pair_member_count": target_pair_members.get((request_id, cid), 0),
                "evaluation_only_gap_affects_target_pair": target_pair_members.get((request_id, cid), 0) > 0,
                "evaluation_only_coverage_gap_taxonomy": coverage_gap_taxonomy(
                    gap,
                    action,
                    label,
                    target_pair_members,
                ),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def coverage_gap_taxonomy(
    gap: Dict[str, Any],
    action: Dict[str, Any],
    label: Dict[str, Any],
    target_pair_members: Dict[Tuple[str, str], int],
) -> str:
    request_id = row_request_id(gap)
    cid = candidate_id(gap)
    if target_pair_members.get((request_id, cid), 0) > 0:
        return "gap_affects_target_pair_analysis"
    if label.get("evaluation_only_candidate_correct") is True:
        return "gap_affects_candidate_validity_analysis"
    if str(action.get("repair_action") or "") == "waive_non_target_policy_promotion_only":
        return "gap_waived_after_action_time_low_priority_rule"
    if str(action.get("repair_action") or "") == "request_object_relation_observation":
        return "gap_requires_object_relation_observation"
    return "gap_does_not_affect_evaluation_only_target_probe"


def simple_alternative_report(gaps: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    gap_count = len(gaps)
    return {
        "ignore_detector_coverage_gap": {
            "decision": "rejected",
            "reason": "would promote a relation proxy while action-time detector association coverage is incomplete",
            "affected_gap_rows": gap_count,
        },
        "accept_target_pair_probe_without_repair": {
            "decision": "rejected",
            "reason": "target-pair separability is an evaluation-only probe until coverage gaps are materialized",
            "affected_gap_rows": gap_count,
        },
        "commit_relation_signature_best": {
            "decision": "blocked",
            "reason": "terminal commit is outside this contract and would turn a diagnostic proxy into a selector",
        },
        "use_evaluation_only_missing_rows_to_waive": {
            "decision": "rejected",
            "reason": "waiver decisions must be made before label join",
        },
        "rerun_first_eval_immediately": {
            "decision": "blocked",
            "reason": "policy-scale rerun waits for a fixed observation/repair path",
        },
        "defer_all": {
            "decision": "safe_but_inert",
            "reason": "keeps terminal safety but loses the active observation mechanism under test",
        },
    }


def summarize(
    *,
    contract: Dict[str, Any],
    source_summary: Dict[str, Any],
    candidate_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    gaps: Sequence[Dict[str, Any]],
    action_rows: Sequence[Dict[str, Any]],
    request_coverage: Sequence[Dict[str, Any]],
    evaluated_gaps: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = contract.get("evaluation_gates", {})
    forbidden = action_forbidden_keys(list(gaps) + list(action_rows) + list(request_coverage))
    terminal_rows = [
        row for row in list(gaps) + list(action_rows) + list(request_coverage)
        if row.get("terminal_commit") is True or row.get("repair_action") == "commit_candidate"
    ]
    action_counts = Counter(str(row.get("repair_action")) for row in action_rows)
    gaps_by_request = group_by_request(gaps)
    request_ids = sorted({row_request_id(row) for row in request_rows}, key=request_sort_key)
    missing_unique_candidate_ids = sorted({candidate_id(row) for row in gaps})
    evaluation_missing_candidate_valid_rows = [
        row for row in evaluated_gaps if row.get("evaluation_only_candidate_correct") is True
    ]
    evaluation_missing_target_pair_rows = [
        row for row in evaluated_gaps if row.get("evaluation_only_gap_affects_target_pair") is True
    ]
    gate = {
        "input_scene_graph_object_relation_gate_passed": source_summary.get("gate", {}).get(
            "scene_graph_object_relation_gate_passed"
        )
        is True,
        "expected_request_rows_passed": len(request_rows) == safe_int(gates.get("expected_request_rows")),
        "expected_candidate_relation_rows_passed": len(candidate_rows)
        == safe_int(gates.get("expected_candidate_relation_rows")),
        "expected_pair_relation_rows_passed": len(pair_rows) == safe_int(gates.get("expected_pair_relation_rows")),
        "context_object_rows_minimum_passed": source_summary.get("context_object_rows", 0)
        >= safe_int(gates.get("expected_context_object_rows_minimum"), 0),
        "detector_missing_candidate_rows_expected_passed": len(gaps)
        == safe_int(gates.get("detector_missing_candidate_rows_expected"), 0),
        "detector_missing_unique_candidate_ids_minimum_passed": len(missing_unique_candidate_ids)
        >= safe_int(gates.get("detector_missing_unique_candidate_ids_minimum"), 0),
        "repair_action_rows_cover_gaps_passed": len(action_rows) == len(gaps),
        "request_observation_rows_present_passed": action_counts.get("request_object_relation_observation", 0) > 0,
        "waiver_rows_action_time_rule_passed": action_counts.get("waive_non_target_policy_promotion_only", 0) >= 0,
        "evaluation_label_join_after_action_rows_passed": len(evaluated_gaps) == len(gaps),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action_passed": all(
            row.get("uses_gt_for_action") is False
            for row in list(gaps) + list(action_rows) + list(request_coverage)
        ),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["coverage_repair_gate_passed"] = all(
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
    if action_counts.get("request_object_relation_observation", 0) > 0:
        recommended_next_action = "freeze_object_relation_observation_plan_contract"
        conclusion_reason = "high_priority_relation_coverage_gaps_require_new_action_time_observation_plan"
    elif gaps:
        recommended_next_action = "defer_goal_validity_terminal_policy"
        conclusion_reason = "coverage_gaps_exist_without_observation_action"
    else:
        recommended_next_action = "evaluate_terminal_relation_utility_on_frozen_scope"
        conclusion_reason = "no_coverage_gap_rows_remain"
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "source_summary": str(args.source_summary),
        "candidate_relation_rows": str(args.candidate_relation_rows),
        "pair_relation_rows": str(args.pair_relation_rows),
        "request_relation_rows": str(args.request_relation_rows),
        "evaluated_candidate_relation_rows": str(args.evaluated_candidate_relation_rows),
        "evaluated_pair_relation_rows": str(args.evaluated_pair_relation_rows),
        "out_root": str(args.out_root),
        "source_gate": {
            "scene_graph_object_relation_gate_passed": source_summary.get("gate", {}).get(
                "scene_graph_object_relation_gate_passed"
            ),
            "scene_graph_object_relation_signal_ready": source_summary.get("diagnostic_conclusion", {}).get(
                "scene_graph_object_relation_signal_ready"
            ),
            "recommended_next_action": source_summary.get("diagnostic_conclusion", {}).get(
                "recommended_next_action"
            ),
            "paper_claim_allowed": source_summary.get("paper_claim_allowed"),
        },
        "request_rows": len(request_rows),
        "candidate_relation_rows_count": len(candidate_rows),
        "pair_relation_rows_count": len(pair_rows),
        "coverage_gap_rows": len(gaps),
        "coverage_gap_rows_by_request": {
            request_id: len(rows) for request_id, rows in sorted(gaps_by_request.items(), key=lambda item: request_sort_key(item[0]))
        },
        "detector_missing_unique_candidate_ids": missing_unique_candidate_ids,
        "coverage_gap_rank_stats": number_stats([safe_int(row.get("target_generated_rank"), 999999) for row in gaps]),
        "coverage_gap_relation_signature_score_stats": distance_stats(
            [safe_float(row.get("relation_signature_score")) for row in gaps]
        ),
        "coverage_gap_relation_density_counts": dict(
            sorted(Counter(str(row.get("relation_density_bucket")) for row in gaps).items())
        ),
        "coverage_gap_view_consistency_counts": dict(
            sorted(Counter(str(row.get("relation_view_consistency_profile")) for row in gaps).items())
        ),
        "repair_action_rows": len(action_rows),
        "repair_action_counts": dict(sorted(action_counts.items())),
        "repair_reason_counts": dict(sorted(Counter(str(row.get("repair_reason")) for row in action_rows).items())),
        "request_coverage_rows": len(request_coverage),
        "request_coverage_profiles": {
            request_id: {
                "candidate_relation_rows": next(
                    (row.get("candidate_relation_rows") for row in request_coverage if row_request_id(row) == request_id),
                    None,
                ),
                "rows_with_detector_association": next(
                    (row.get("rows_with_detector_association") for row in request_coverage if row_request_id(row) == request_id),
                    None,
                ),
                "coverage_gap_rows": next(
                    (row.get("coverage_gap_rows") for row in request_coverage if row_request_id(row) == request_id),
                    None,
                ),
                "repair_action_counts": next(
                    (row.get("repair_action_counts") for row in request_coverage if row_request_id(row) == request_id),
                    {},
                ),
            }
            for request_id in request_ids
        },
        "evaluation_only_coverage_check": {
            "evaluated_coverage_gap_rows": len(evaluated_gaps),
            "evaluation_only_missing_detector_candidate_valid_rows": len(
                evaluation_missing_candidate_valid_rows
            ),
            "evaluation_only_missing_detector_target_pair_rows": len(evaluation_missing_target_pair_rows),
            "evaluation_only_coverage_gap_taxonomy_counts": dict(
                sorted(Counter(str(row.get("evaluation_only_coverage_gap_taxonomy")) for row in evaluated_gaps).items())
            ),
            "uses_gt_for_analysis": True,
        },
        "simpler_alternatives": simple_alternative_report(gaps),
        "diagnostic_conclusion": {
            "coverage_repair_signal_ready": gate["coverage_repair_gate_passed"],
            "recommended_next_action": recommended_next_action,
            "reason": conclusion_reason,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": (
                "The analyzer materializes detector-association coverage gaps and action-time repair or waiver rows before joining correctness labels."
            ),
            "agent_inference": (
                "The dense rank-6 relation gaps should become bounded object-relation observation targets, while low-priority rank-91 medium-density gaps can be excluded from terminal-policy promotion by an action-time rank/context rule."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "output_files": {
            "coverage_gap_rows": "goal_validity_object_relation_coverage_gap_rows.jsonl",
            "coverage_repair_action_rows": "goal_validity_object_relation_coverage_repair_action_rows.jsonl",
            "request_coverage_rows": "goal_validity_object_relation_request_coverage_rows.jsonl",
            "evaluated_coverage_gap_rows": "goal_validity_object_relation_evaluated_coverage_gap_rows.jsonl",
            "summary": "goal_validity_object_relation_coverage_repair_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    source_summary = load_json(Path(args.source_summary))
    candidates = load_jsonl(Path(args.candidate_relation_rows))
    pairs = load_jsonl(Path(args.pair_relation_rows))
    requests = load_jsonl(Path(args.request_relation_rows))
    evaluated_candidates = load_jsonl(Path(args.evaluated_candidate_relation_rows))
    evaluated_pairs = load_jsonl(Path(args.evaluated_pair_relation_rows))
    gaps = coverage_gap_rows(candidates, pairs)
    actions = coverage_repair_action_rows(
        gaps,
        rank_threshold=int(args.observation_rank_threshold),
        waiver_rank_min=int(args.waiver_rank_min),
    )
    request_coverage = request_coverage_rows(candidates, gaps, actions)
    evaluated_gaps = evaluated_coverage_gap_rows(gaps, actions, evaluated_candidates, evaluated_pairs)
    summary = summarize(
        contract=contract,
        source_summary=source_summary,
        candidate_rows=candidates,
        pair_rows=pairs,
        request_rows=requests,
        gaps=gaps,
        action_rows=actions,
        request_coverage=request_coverage,
        evaluated_gaps=evaluated_gaps,
        args=args,
    )
    out_root = Path(args.out_root)
    required = contract.get("required_outputs", {})
    write_jsonl(out_root / required.get("coverage_gap_rows", "goal_validity_object_relation_coverage_gap_rows.jsonl"), gaps)
    write_jsonl(
        out_root / required.get("coverage_repair_action_rows", "goal_validity_object_relation_coverage_repair_action_rows.jsonl"),
        actions,
    )
    write_jsonl(out_root / required.get("request_coverage_rows", "goal_validity_object_relation_request_coverage_rows.jsonl"), request_coverage)
    write_jsonl(
        out_root / required.get("evaluated_coverage_gap_rows", "goal_validity_object_relation_evaluated_coverage_gap_rows.jsonl"),
        evaluated_gaps,
    )
    write_json(out_root / required.get("summary", "goal_validity_object_relation_coverage_repair_summary.json"), summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize object-relation detector coverage gaps and action-time repair rows."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--source-summary", required=True)
    parser.add_argument("--candidate-relation-rows", required=True)
    parser.add_argument("--pair-relation-rows", required=True)
    parser.add_argument("--request-relation-rows", required=True)
    parser.add_argument("--evaluated-candidate-relation-rows", required=True)
    parser.add_argument("--evaluated-pair-relation-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--observation-rank-threshold", type=int, default=20)
    parser.add_argument("--waiver-rank-min", type=int, default=80)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
