import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    distance_stats,
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


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_evidence.v1"


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(explicit)
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def optional_path(args: argparse.Namespace, attr: str, fallback: str) -> Optional[Path]:
    explicit = getattr(args, attr)
    if explicit:
        return Path(explicit)
    path = Path(fallback)
    return path if path.exists() else None


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def finite_stats(values: Sequence[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(clean), "mean": sum(clean) / len(clean), "max": max(clean)}


def mean(values: Sequence[Optional[float]]) -> Optional[float]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def target_candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def direction_key(row: Dict[str, Any]) -> str:
    return str(row.get("standoff_direction_source") or "unknown_direction_source")


def evidence_group_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (row_request_id(row), target_candidate_id(row), direction_key(row))


def request_group_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (row_request_id(row), target_candidate_id(row))


def group_rows_by_evidence_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[evidence_group_key(row)].append(dict(row))
    return grouped


def group_rows_by_request_candidate(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[request_group_key(row)].append(dict(row))
    return grouped


def first_by_evidence_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        key = evidence_group_key(row)
        if key not in indexed:
            indexed[key] = dict(row)
    return indexed


def bool_count(rows: Sequence[Dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def status_from_counts(
    *,
    associated_count: int,
    depth_consistent_count: int,
    inside_mask_count: int,
    min_associated: int,
    min_depth_consistent: int,
) -> str:
    if associated_count >= min_associated and depth_consistent_count >= min_depth_consistent:
        return "relation_depth_recheck_resolved"
    if associated_count > 0 or depth_consistent_count > 0 or inside_mask_count > 0:
        return "relation_depth_recheck_partial"
    return "relation_depth_recheck_unresolved"


def evidence_row(
    rows: Sequence[Dict[str, Any]],
    frame_row: Optional[Dict[str, Any]],
    *,
    min_associated_per_direction: int,
    min_depth_consistent_per_direction: int,
) -> Dict[str, Any]:
    exemplar = rows[0]
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    visible = [row for row in rows if row.get("projection_status") == "visible"]
    inside_box = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    inside_mask = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    depth_consistent = [
        row for row in rows if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    depth_mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    out_of_fov = [row for row in rows if str(row.get("projection_status")) == "out_of_fov"]
    box_scores = [safe_float(row.get("best_box_score")) for row in rows]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
    associated_depth_errors = [safe_float(row.get("depth_error_m")) for row in associated]
    camera_forward = [safe_float(row.get("camera_forward_m")) for row in rows]
    mask_depths = [safe_float(row.get("mask_depth_median")) for row in rows]
    offsets = [row.get("projection_anchor_height_offset_m") for row in rows]
    target_distances = [safe_float(row.get("target_distance_from_viewpoint_m")) for row in rows]
    relation_anchor_ids = list(exemplar.get("goal_validity_relation_anchor_candidate_ids") or [])
    status = status_from_counts(
        associated_count=len(associated),
        depth_consistent_count=len(depth_consistent),
        inside_mask_count=len(inside_mask),
        min_associated=min_associated_per_direction,
        min_depth_consistent=min_depth_consistent_per_direction,
    )
    frame = frame_row or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_object_relation_detector_depth_evidence",
        "expanded_retrieval_request_id": row_request_id(exemplar),
        "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
        "episode_key": exemplar.get("episode_key"),
        "scene_key": exemplar.get("scene_key"),
        "scene_id": exemplar.get("scene_id"),
        "query": exemplar.get("query"),
        "candidate_id": target_candidate_id(exemplar),
        "target_candidate_id": target_candidate_id(exemplar),
        "target_candidate_role": exemplar.get("target_candidate_role"),
        "target_generated_rank": exemplar.get("target_generated_rank"),
        "target_semantic_rank": exemplar.get("target_semantic_rank"),
        "target_score": exemplar.get("target_score"),
        "target_semantic_score": exemplar.get("target_semantic_score"),
        "target_support_score": exemplar.get("target_support_score"),
        "target_positive_support": exemplar.get("target_positive_support"),
        "target_position": exemplar.get("target_position"),
        "target_visit_position": exemplar.get("target_visit_position"),
        "target_relation_density_bucket": exemplar.get("target_relation_density_bucket"),
        "target_relation_signature_score": exemplar.get("target_relation_signature_score"),
        "target_relation_view_consistency_profile": exemplar.get("target_relation_view_consistency_profile"),
        "object_relation_observation_action": exemplar.get("object_relation_observation_action"),
        "object_relation_observation_reason": exemplar.get("object_relation_observation_reason"),
        "planner_name": exemplar.get("planner_name"),
        "standoff_direction_source": direction_key(exemplar),
        "standoff_relation_anchor_candidate_id": exemplar.get("standoff_relation_anchor_candidate_id"),
        "standoff_distance_requested": exemplar.get("standoff_distance_requested"),
        "standoff_target_horizontal_distance": exemplar.get("standoff_target_horizontal_distance"),
        "target_distance_from_viewpoint_m": exemplar.get("target_distance_from_viewpoint_m"),
        "relation_anchor_count": safe_int(exemplar.get("goal_validity_relation_anchor_count"), 0),
        "relation_anchor_candidate_ids": relation_anchor_ids,
        "direction_source_coverage_count": 1,
        "heading_rows": len(rows),
        "heading_id_count": len({str(row.get("heading_id")) for row in rows if row.get("heading_id")}),
        "detector_box_count": frame.get("detector_box_count"),
        "sam2_mask_count": frame.get("sam2_mask_count"),
        "candidate_association_count": len(associated),
        "associated_heading_count": len(associated),
        "visible_count": len(visible),
        "inside_box_count": len(inside_box),
        "inside_mask_count": len(inside_mask),
        "depth_consistent_count": len(depth_consistent),
        "depth_match_count": len(depth_consistent),
        "depth_mismatch_count": len(depth_mismatch),
        "out_of_fov_count": len(out_of_fov),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in rows),
        "projection_anchor_offset_counts": compact_counter(offsets),
        "projection_anchor_offset_profile": sorted(
            [safe_float(value) for value in offsets if safe_float(value) is not None]
        ),
        "best_box_score_max": max([score for score in box_scores if score is not None], default=None),
        "best_box_score_mean": mean(box_scores),
        "depth_error_stats_m": finite_stats(depth_errors),
        "associated_depth_error_stats_m": finite_stats(associated_depth_errors),
        "camera_forward_stats_m": finite_stats(camera_forward),
        "mask_depth_stats_m": finite_stats(mask_depths),
        "target_distance_from_viewpoint_stats_m": finite_stats(target_distances),
        "evidence_status": status,
        "terminal_policy_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
    }


def build_evidence_rows(
    association_rows: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
    *,
    min_associated_per_direction: int,
    min_depth_consistent_per_direction: int,
) -> List[Dict[str, Any]]:
    grouped = group_rows_by_evidence_key(association_rows)
    frame_index = first_by_evidence_key(frame_rows)
    rows: List[Dict[str, Any]] = []
    for key, group in sorted(
        grouped.items(),
        key=lambda item: (
            request_sort_key(item[0][0]),
            safe_int(item[1][0].get("target_generated_rank"), 999999),
            item[0][2],
        ),
    ):
        rows.append(
            evidence_row(
                group,
                frame_index.get(key),
                min_associated_per_direction=min_associated_per_direction,
                min_depth_consistent_per_direction=min_depth_consistent_per_direction,
            )
        )
    return rows


def request_status(
    rows: Sequence[Dict[str, Any]],
    *,
    min_associated_per_request: int,
    min_depth_consistent_per_request: int,
    min_resolved_directions: int,
    min_direction_sources: int,
) -> str:
    direction_sources = {str(row.get("standoff_direction_source")) for row in rows}
    resolved = [row for row in rows if row.get("evidence_status") == "relation_depth_recheck_resolved"]
    associated = sum(safe_int(row.get("associated_heading_count"), 0) for row in rows)
    depth_consistent = sum(safe_int(row.get("depth_consistent_count"), 0) for row in rows)
    inside_mask = sum(safe_int(row.get("inside_mask_count"), 0) for row in rows)
    if (
        len(direction_sources) >= min_direction_sources
        and len(resolved) >= min_resolved_directions
        and associated >= min_associated_per_request
        and depth_consistent >= min_depth_consistent_per_request
    ):
        return "relation_depth_recheck_resolved"
    if associated > 0 or depth_consistent > 0 or inside_mask > 0:
        return "relation_depth_recheck_partial"
    return "relation_depth_recheck_unresolved"


def build_request_rows(
    evidence_rows: Sequence[Dict[str, Any]],
    *,
    min_associated_per_request: int,
    min_depth_consistent_per_request: int,
    min_resolved_directions: int,
    min_direction_sources: int,
) -> List[Dict[str, Any]]:
    grouped = group_rows_by_request_candidate(evidence_rows)
    rows: List[Dict[str, Any]] = []
    for (request_id, cid), group in sorted(
        grouped.items(),
        key=lambda item: (
            request_sort_key(item[0][0]),
            safe_int(item[1][0].get("target_generated_rank"), 999999),
            item[0][1],
        ),
    ):
        exemplar = group[0]
        direction_sources = sorted({str(row.get("standoff_direction_source")) for row in group})
        status = request_status(
            group,
            min_associated_per_request=min_associated_per_request,
            min_depth_consistent_per_request=min_depth_consistent_per_request,
            min_resolved_directions=min_resolved_directions,
            min_direction_sources=min_direction_sources,
        )
        associated = sum(safe_int(row.get("associated_heading_count"), 0) for row in group)
        visible = sum(safe_int(row.get("visible_count"), 0) for row in group)
        inside_mask = sum(safe_int(row.get("inside_mask_count"), 0) for row in group)
        depth_consistent = sum(safe_int(row.get("depth_consistent_count"), 0) for row in group)
        depth_mismatch = sum(safe_int(row.get("depth_mismatch_count"), 0) for row in group)
        out_of_fov = sum(safe_int(row.get("out_of_fov_count"), 0) for row in group)
        if status == "relation_depth_recheck_resolved":
            next_action = "defer_terminal_goal_validity_pending_support_saturation_arbitration"
            reason = "relation_depth_gap_resolved_but_terminal_utility_requires_separate_gate"
        elif status == "relation_depth_recheck_partial":
            next_action = "request_additional_relation_depth_evidence_or_defer"
            reason = "relation_depth_gap_has_partial_support"
        else:
            next_action = "defer_goal_validity_terminal_policy"
            reason = "relation_depth_gap_unresolved"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_object_relation_request_evidence",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "candidate_id": cid,
                "target_candidate_id": cid,
                "target_generated_rank": exemplar.get("target_generated_rank"),
                "target_semantic_rank": exemplar.get("target_semantic_rank"),
                "target_relation_density_bucket": exemplar.get("target_relation_density_bucket"),
                "target_relation_signature_score": exemplar.get("target_relation_signature_score"),
                "target_relation_view_consistency_profile": exemplar.get("target_relation_view_consistency_profile"),
                "evidence_rows": len(group),
                "direction_source_count": len(direction_sources),
                "direction_sources": direction_sources,
                "resolved_direction_source_count": sum(
                    1 for row in group if row.get("evidence_status") == "relation_depth_recheck_resolved"
                ),
                "partial_direction_source_count": sum(
                    1 for row in group if row.get("evidence_status") == "relation_depth_recheck_partial"
                ),
                "unresolved_direction_source_count": sum(
                    1 for row in group if row.get("evidence_status") == "relation_depth_recheck_unresolved"
                ),
                "heading_rows": sum(safe_int(row.get("heading_rows"), 0) for row in group),
                "associated_heading_count": associated,
                "visible_count": visible,
                "inside_mask_count": inside_mask,
                "depth_consistent_count": depth_consistent,
                "depth_match_count": depth_consistent,
                "depth_mismatch_count": depth_mismatch,
                "out_of_fov_count": out_of_fov,
                "candidate_association_rate_on_headings": ratio(associated, sum(safe_int(row.get("heading_rows"), 0) for row in group)),
                "depth_consistent_rate_on_headings": ratio(depth_consistent, sum(safe_int(row.get("heading_rows"), 0) for row in group)),
                "inside_mask_rate_on_visible": ratio(inside_mask, visible),
                "evidence_status": status,
                "next_evidence_action": next_action,
                "next_evidence_reason": reason,
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def evaluation_label_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        indexed[(row_request_id(row), candidate_id(row))] = dict(row)
    return indexed


def build_evaluation_rows(
    request_rows: Sequence[Dict[str, Any]],
    labels: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    indexed = evaluation_label_index(labels)
    rows: List[Dict[str, Any]] = []
    for row in request_rows:
        label = indexed.get((row_request_id(row), candidate_id(row))) or {}
        rows.append(
            {
                **row,
                "validation_stage": "evaluation_only_object_relation_evidence_after_action_rows",
                "evaluation_only_candidate_correct": label.get("evaluation_only_candidate_correct"),
                "evaluation_only_candidate_rank": label.get("evaluation_only_candidate_rank"),
                "evaluation_only_coverage_gap_taxonomy": label.get("evaluation_only_coverage_gap_taxonomy"),
                "evaluation_only_interpretation": evaluation_interpretation(row, label),
                "uses_gt_for_analysis": bool(label),
            }
        )
    return rows


def evaluation_interpretation(action_row: Dict[str, Any], label: Dict[str, Any]) -> str:
    status = str(action_row.get("evidence_status") or "")
    candidate_correct = label.get("evaluation_only_candidate_correct")
    if not label:
        return "no_evaluation_label_joined"
    if status == "relation_depth_recheck_resolved" and candidate_correct is True:
        return "resolved_detector_depth_gap_for_evaluation_positive_candidate"
    if status == "relation_depth_recheck_resolved" and candidate_correct is False:
        return "resolved_detector_depth_gap_for_evaluation_negative_candidate"
    if status == "relation_depth_recheck_partial":
        return "partial_detector_depth_gap_after_relation_observation"
    return "unresolved_detector_depth_gap_after_relation_observation"


def simpler_alternative_report(request_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    resolved_rows = [row for row in request_rows if row.get("evidence_status") == "relation_depth_recheck_resolved"]
    partial_rows = [row for row in request_rows if row.get("evidence_status") == "relation_depth_recheck_partial"]
    unresolved_rows = [row for row in request_rows if row.get("evidence_status") == "relation_depth_recheck_unresolved"]
    return {
        "defer_all_after_detector_substrate": {
            "decision": "safe_but_inert",
            "resolved_rows_lost": len(resolved_rows),
            "reason": "keeps terminal safety but cannot test whether relation-aware re-observation resolves the detector-depth gap",
        },
        "detector_box_presence_only": {
            "decision": "insufficient_as_terminal_rule",
            "reason": "box availability is category-level perception support and does not separate repeated goal instances",
        },
        "sam2_mask_presence_only": {
            "decision": "insufficient_as_terminal_rule",
            "reason": "mask availability confirms visible object evidence, not ObjectNav goal validity",
        },
        "association_count_threshold_only": {
            "decision": "diagnostic_only",
            "resolved_rows": len(resolved_rows),
            "partial_rows": len(partial_rows),
            "unresolved_rows": len(unresolved_rows),
            "reason": "association count can describe the repaired gap but cannot authorize direct commit without a separate terminal gate",
        },
        "depth_match_threshold_only": {
            "decision": "diagnostic_only",
            "reason": "depth consistency is necessary evidence for the repaired gap, but support saturation remains a separate ambiguity mechanism",
        },
        "relation_anchor_count_only": {
            "decision": "rejected",
            "reason": "relation-anchor availability is planning context, not post-detector evidence",
        },
    }


def summarize(
    *,
    contract: Dict[str, Any],
    plan_summary: Dict[str, Any],
    projection_summary: Dict[str, Any],
    detector_substrate_summary: Dict[str, Any],
    detector_summary: Dict[str, Any],
    association_rows: Sequence[Dict[str, Any]],
    evidence_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    evaluation_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    minimum = contract.get("minimum_evidence_gate") or {}
    action_rows = list(evidence_rows) + list(request_rows)
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    request_ids = sorted({row_request_id(row) for row in request_rows}, key=request_sort_key)
    direction_counts_by_request = {
        request_id: len(
            {
                str(row.get("standoff_direction_source"))
                for row in evidence_rows
                if row_request_id(row) == request_id
            }
        )
        for request_id in request_ids
    }
    associated_heading_count = sum(safe_int(row.get("associated_heading_count"), 0) for row in evidence_rows)
    depth_consistent_count = sum(safe_int(row.get("depth_consistent_count"), 0) for row in evidence_rows)
    rows_with_association = safe_int(detector_substrate_summary.get("rows_with_candidate_association"), 0)
    status_counts = Counter(str(row.get("evidence_status")) for row in request_rows)
    detector_gate = detector_substrate_summary.get("gate") or {}
    plan_gate = plan_summary.get("gate") or {}
    projection_gate = projection_summary.get("gate") or {}
    gate = {
        "source_observation_plan_gate_passed": plan_gate.get("object_relation_observation_plan_gate_passed")
        is bool(minimum.get("source_observation_plan_gate_passed", True)),
        "source_projection_anchor_smoke_passed": projection_gate.get("projection_anchor_smoke_passed")
        is bool(minimum.get("source_projection_anchor_smoke_passed", True)),
        "source_detector_substrate_gate_passed": detector_gate.get("passes_detector_substrate_gate")
        is bool(minimum.get("source_detector_substrate_gate_passed", True)),
        "expected_request_rows_passed": len(request_rows) == safe_int(minimum.get("expected_request_rows"), 0),
        "expected_plan_rows_passed": safe_int(plan_summary.get("plan_rows"), -1)
        == safe_int(minimum.get("expected_plan_rows"), 0),
        "expected_detector_rows_passed": safe_int(detector_substrate_summary.get("detector_rows"), -1)
        == safe_int(minimum.get("expected_detector_rows"), 0),
        "expected_association_rows_passed": len(association_rows)
        == safe_int(minimum.get("expected_association_rows"), 0),
        "minimum_evidence_rows_passed": len(evidence_rows) >= safe_int(minimum.get("minimum_evidence_rows"), 0),
        "minimum_request_rows_passed": len(request_rows) >= safe_int(minimum.get("minimum_request_rows"), 0),
        "minimum_rows_with_candidate_association_passed": rows_with_association
        >= safe_int(minimum.get("minimum_rows_with_candidate_association"), 0),
        "minimum_associated_candidate_heading_count_passed": associated_heading_count
        >= safe_int(minimum.get("minimum_associated_candidate_heading_count"), 0),
        "minimum_depth_consistent_rows_passed": depth_consistent_count
        >= safe_int(minimum.get("minimum_depth_consistent_rows"), 0),
        "minimum_direction_source_count_per_request_passed": all(
            count >= safe_int(minimum.get("minimum_direction_source_count_per_request"), 0)
            for count in direction_counts_by_request.values()
        ),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(minimum.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(evaluation_rows),
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["object_relation_evidence_gate_passed"] = all(
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
    if status_counts.get("relation_depth_recheck_resolved", 0) == len(request_rows) and request_rows:
        recommended_next_action = "validate_object_relation_evidence_output_before_terminal_contract"
        reason = "relation_depth_recheck_resolved_for_all_requests_but_terminal_utility_is_separate"
    elif status_counts.get("relation_depth_recheck_partial", 0) > 0:
        recommended_next_action = "inspect_partial_relation_depth_evidence"
        reason = "some request-candidate rows remain partial after observation"
    else:
        recommended_next_action = "defer_goal_validity_terminal_policy"
        reason = "relation_depth_recheck_unresolved"
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "observation_plan_summary": str(args.plan_summary or contract.get("source", {}).get("observation_plan_summary")),
            "projection_summary": str(args.projection_summary or contract.get("source", {}).get("projection_summary")),
            "detector_substrate_summary": str(args.detector_substrate_summary or contract.get("source", {}).get("detector_substrate_summary")),
            "detector_summary": str(args.detector_summary or contract.get("source", {}).get("detector_summary")),
            "detector_associations": str(args.detector_associations or contract.get("source", {}).get("detector_associations")),
            "detector_frame_summary": str(args.detector_frame_summary or contract.get("source", {}).get("detector_frame_summary")),
            "evaluated_coverage_gap_rows": str(args.evaluated_coverage_gap_rows),
        },
        "source_gate": {
            "object_relation_observation_plan_gate_passed": plan_gate.get("object_relation_observation_plan_gate_passed"),
            "projection_anchor_smoke_passed": projection_gate.get("projection_anchor_smoke_passed"),
            "passes_detector_substrate_gate": detector_gate.get("passes_detector_substrate_gate"),
            "detector_rows": detector_substrate_summary.get("detector_rows"),
            "detector_box_rate": detector_substrate_summary.get("detector_box_rate"),
            "sam2_mask_rate": detector_substrate_summary.get("sam2_mask_rate"),
            "candidate_association_rate": detector_substrate_summary.get("candidate_association_rate"),
            "paper_claim_allowed": detector_substrate_summary.get("paper_claim_allowed"),
        },
        "request_rows": len(request_rows),
        "request_ids": request_ids,
        "evidence_rows": len(evidence_rows),
        "association_rows": len(association_rows),
        "detector_rows": detector_substrate_summary.get("detector_rows"),
        "rows_with_candidate_association": rows_with_association,
        "associated_candidate_heading_count": associated_heading_count,
        "depth_consistent_rows": depth_consistent_count,
        "depth_mismatch_rows": sum(safe_int(row.get("depth_mismatch_count"), 0) for row in evidence_rows),
        "out_of_fov_rows": sum(safe_int(row.get("out_of_fov_count"), 0) for row in evidence_rows),
        "detector_box_rows": detector_summary.get("detector_box_rows"),
        "detector_mask_rows": detector_summary.get("detector_mask_rows"),
        "evidence_status_counts": dict(sorted(status_counts.items())),
        "evidence_status_counts_by_direction": dict(
            sorted(Counter(str(row.get("evidence_status")) for row in evidence_rows).items())
        ),
        "direction_source_counts": dict(
            sorted(Counter(str(row.get("standoff_direction_source")) for row in evidence_rows).items())
        ),
        "direction_source_count_by_request": direction_counts_by_request,
        "request_evidence_profiles": {
            row_request_id(row): {
                "candidate_id": candidate_id(row),
                "evidence_status": row.get("evidence_status"),
                "associated_heading_count": row.get("associated_heading_count"),
                "depth_consistent_count": row.get("depth_consistent_count"),
                "depth_mismatch_count": row.get("depth_mismatch_count"),
                "direction_source_count": row.get("direction_source_count"),
                "next_evidence_action": row.get("next_evidence_action"),
            }
            for row in request_rows
        },
        "post_label_analysis": {
            "evaluation_only_rows": len(evaluation_rows),
            "evaluation_only_candidate_correct_counts": dict(
                sorted(Counter(str(row.get("evaluation_only_candidate_correct")) for row in evaluation_rows).items())
            ),
            "evaluation_only_interpretation_counts": dict(
                sorted(Counter(str(row.get("evaluation_only_interpretation")) for row in evaluation_rows).items())
            ),
            "uses_gt_for_analysis": bool(evaluation_rows),
        },
        "simpler_alternatives": simpler_alternative_report(request_rows),
        "diagnostic_conclusion": {
            "object_relation_evidence_signal_ready": gate["object_relation_evidence_gate_passed"],
            "recommended_next_action": recommended_next_action,
            "reason": reason,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": "The analyzer aggregates relation-aware detector-depth observations into nonterminal action-time evidence rows.",
            "agent_inference": "Detector-depth recheck can resolve relation coverage gaps, but it does not by itself solve repeated-object goal-validity arbitration.",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(evaluation_rows),
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "output_files": {
            "evidence_rows": "goal_validity_object_relation_evidence_rows.jsonl",
            "request_rows": "goal_validity_object_relation_request_rows.jsonl",
            "evaluation_only_rows": "goal_validity_object_relation_evaluated_rows.jsonl",
            "summary": "goal_validity_object_relation_evidence_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    plan_summary = load_json(source_path(args, contract, "plan_summary", "observation_plan_summary"))
    projection_summary = load_json(source_path(args, contract, "projection_summary", "projection_summary"))
    detector_substrate_summary = load_json(
        source_path(args, contract, "detector_substrate_summary", "detector_substrate_summary")
    )
    detector_summary = load_json(source_path(args, contract, "detector_summary", "detector_summary"))
    association_rows = load_jsonl(source_path(args, contract, "detector_associations", "detector_associations"))
    frame_rows = load_jsonl(source_path(args, contract, "detector_frame_summary", "detector_frame_summary"))
    eval_path = optional_path(
        args,
        "evaluated_coverage_gap_rows",
        "local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1/goal_validity_object_relation_evaluated_coverage_gap_rows.jsonl",
    )
    if eval_path is not None:
        args.evaluated_coverage_gap_rows = str(eval_path)
    evaluation_labels = load_jsonl(eval_path) if eval_path else []

    evidence_rows = build_evidence_rows(
        association_rows,
        frame_rows,
        min_associated_per_direction=int(args.min_associated_per_direction),
        min_depth_consistent_per_direction=int(args.min_depth_consistent_per_direction),
    )
    request_rows = build_request_rows(
        evidence_rows,
        min_associated_per_request=int(args.min_associated_per_request),
        min_depth_consistent_per_request=int(args.min_depth_consistent_per_request),
        min_resolved_directions=int(args.min_resolved_directions),
        min_direction_sources=int(args.min_direction_sources),
    )
    evaluated_rows = build_evaluation_rows(request_rows, evaluation_labels)
    summary = summarize(
        contract=contract,
        plan_summary=plan_summary,
        projection_summary=projection_summary,
        detector_substrate_summary=detector_substrate_summary,
        detector_summary=detector_summary,
        association_rows=association_rows,
        evidence_rows=evidence_rows,
        request_rows=request_rows,
        evaluation_rows=evaluated_rows,
        args=args,
    )
    out_root = Path(args.out_root)
    required = contract.get("required_outputs") or {}
    write_jsonl(out_root / required.get("evidence_rows", "goal_validity_object_relation_evidence_rows.jsonl"), evidence_rows)
    write_jsonl(out_root / required.get("request_rows", "goal_validity_object_relation_request_rows.jsonl"), request_rows)
    write_jsonl(
        out_root / required.get("evaluation_only_rows", "goal_validity_object_relation_evaluated_rows.jsonl"),
        evaluated_rows,
    )
    write_json(out_root / required.get("summary", "goal_validity_object_relation_evidence_summary.json"), summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate object-relation post-detector evidence before terminal utility validation."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--plan-summary")
    parser.add_argument("--projection-summary")
    parser.add_argument("--detector-substrate-summary")
    parser.add_argument("--detector-summary")
    parser.add_argument("--detector-associations")
    parser.add_argument("--detector-frame-summary")
    parser.add_argument("--evaluated-coverage-gap-rows")
    parser.add_argument("--min-associated-per-direction", type=int, default=2)
    parser.add_argument("--min-depth-consistent-per-direction", type=int, default=2)
    parser.add_argument("--min-associated-per-request", type=int, default=20)
    parser.add_argument("--min-depth-consistent-per-request", type=int, default=16)
    parser.add_argument("--min-resolved-directions", type=int, default=3)
    parser.add_argument("--min-direction-sources", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
