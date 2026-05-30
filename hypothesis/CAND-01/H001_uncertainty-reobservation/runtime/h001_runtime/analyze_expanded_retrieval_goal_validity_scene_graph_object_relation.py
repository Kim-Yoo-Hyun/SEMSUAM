import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    distance_stats,
    group_by_request,
    horizontal_distance,
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
from h001_runtime.analyze_expanded_retrieval_goal_validity_relation_spatial_context import (
    delta,
    delta_sign,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_scene_graph_object_relation.v1"
RELATION_PREDICATE_KEYS = [
    "near_1m_proxy",
    "near_2m_proxy",
    "near_4m_proxy",
    "overlap_proxy",
    "same_component_proxy",
    "same_support_surface_proxy",
    "global_left_proxy",
    "global_right_proxy",
    "global_front_proxy",
    "global_behind_proxy",
    "co_visible_context_proxy",
]


def vector3(value: Any) -> Optional[Tuple[float, float, float]]:
    if not isinstance(value, list) or len(value) < 3:
        return None
    xyz = [safe_float(item) for item in value[:3]]
    if any(item is None for item in xyz):
        return None
    return (float(xyz[0]), float(xyz[1]), float(xyz[2]))


def mean(values: Sequence[float]) -> Optional[float]:
    clean = [value for value in values if math.isfinite(value)]
    return None if not clean else sum(clean) / len(clean)


def bool_count(rows: Sequence[Dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def relation_count_bucket(count: int) -> str:
    if count >= 16:
        return "relation_dense"
    if count >= 6:
        return "relation_medium"
    if count > 0:
        return "relation_sparse"
    return "relation_missing"


def relation_delta_bucket(value: Optional[float], margin: float) -> str:
    if value is None:
        return "relation_delta_unknown"
    if value > margin:
        return "contrast_relation_higher"
    if value < -margin:
        return "selector_relation_higher"
    return "relation_tie_or_small_delta"


def association_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        request_id = row_request_id(row)
        cid = str(row.get("candidate_id") or row.get("target_candidate_id") or "")
        if request_id and cid:
            grouped[(request_id, cid)].append(dict(row))
    return grouped


def frame_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        request_id = row_request_id(row)
        cid = str(row.get("target_candidate_id") or row.get("candidate_id") or "")
        if request_id and cid and (request_id, cid) not in indexed:
            indexed[(request_id, cid)] = dict(row)
    return indexed


def detector_stats(
    association_rows: Sequence[Dict[str, Any]],
    frame_row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    associated = [row for row in association_rows if row.get("associated_to_candidate") is True]
    visible = [row for row in association_rows if row.get("projection_status") == "visible"]
    inside_box = [row for row in association_rows if row.get("projected_pixel_inside_box") is True]
    inside_mask = [row for row in association_rows if row.get("projected_pixel_inside_mask") is True]
    consistent = [
        row
        for row in association_rows
        if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    depth_mismatch = [row for row in association_rows if row.get("depth_check_status") == "depth_mismatch"]
    detector_scores = [safe_float(row.get("best_box_score")) for row in association_rows]
    detector_scores = [float(score) for score in detector_scores if score is not None]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in association_rows]
    depth_errors = [float(value) for value in depth_errors if value is not None]
    mask_depths = [safe_float(row.get("mask_depth_median")) for row in association_rows]
    mask_depths = [float(value) for value in mask_depths if value is not None]
    camera_forward = [safe_float(row.get("camera_forward_m")) for row in association_rows]
    camera_forward = [float(value) for value in camera_forward if value is not None]
    heading_ids = sorted({str(row.get("heading_id")) for row in association_rows if row.get("heading_id")})
    associated_heading_ids = sorted({str(row.get("heading_id")) for row in associated if row.get("heading_id")})
    frame = frame_row or {}
    return {
        "detector_heading_rows": len(association_rows),
        "detector_visible_rows": len(visible),
        "detector_associated_rows": len(associated),
        "detector_inside_box_rows": len(inside_box),
        "detector_inside_mask_rows": len(inside_mask),
        "detector_consistent_depth_rows": len(consistent),
        "detector_depth_mismatch_rows": len(depth_mismatch),
        "detector_heading_id_count": len(heading_ids),
        "detector_associated_heading_id_count": len(associated_heading_ids),
        "detector_box_count": frame.get("detector_box_count"),
        "sam2_mask_count": frame.get("sam2_mask_count"),
        "rendered_heading_count": frame.get("rendered_heading_count"),
        "frame_has_candidate_association": frame.get("has_candidate_association"),
        "frame_has_detector_box": frame.get("has_detector_box"),
        "frame_has_sam2_mask": frame.get("has_sam2_mask"),
        "detector_score_max": max(detector_scores, default=None),
        "detector_score_mean": mean(detector_scores),
        "detector_depth_error_min_m": min(depth_errors, default=None),
        "detector_depth_error_mean_m": mean(depth_errors),
        "detector_mask_depth_mean_m": mean(mask_depths),
        "detector_camera_forward_mean_m": mean(camera_forward),
        "detector_depth_status_counts": dict(
            sorted(Counter(str(row.get("depth_check_status")) for row in association_rows).items())
        ),
    }


def candidate_sort_key(row: Dict[str, Any]) -> Tuple[int, int, str]:
    return (
        safe_int(row.get("target_generated_rank"), 999999),
        safe_int(row.get("target_semantic_rank"), 999999),
        candidate_id(row),
    )


def candidate_relation_base_rows(
    candidate_context_rows: Sequence[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    associations = association_index(association_rows)
    frames = frame_index(frame_rows)
    rows: List[Dict[str, Any]] = []
    for row in sorted(
        candidate_context_rows,
        key=lambda item: (request_sort_key(row_request_id(item)), *candidate_sort_key(item)),
    ):
        request_id = row_request_id(row)
        cid = candidate_id(row)
        stats = detector_stats(associations.get((request_id, cid), []), frames.get((request_id, cid)))
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_candidate_object_relation",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": cid,
                "target_generated_rank": row.get("target_generated_rank"),
                "target_semantic_rank": row.get("target_semantic_rank"),
                "target_score": row.get("target_score"),
                "target_semantic_score": row.get("target_semantic_score"),
                "target_support_score": row.get("target_support_score"),
                "target_positive_support": row.get("target_positive_support"),
                "candidate_evidence_class": row.get("candidate_evidence_class"),
                "candidate_specific_support": row.get("candidate_specific_support"),
                "visual_support_score": row.get("visual_support_score"),
                "simple_selector_selected": row.get("simple_selector_selected"),
                "simple_selector_variants": row.get("simple_selector_variants") or [],
                "target_position": row.get("target_position"),
                "target_visit_position": row.get("target_visit_position"),
                "target_candidate_role": row.get("target_candidate_role"),
                "target_candidate_role_tokens": row.get("target_candidate_role_tokens") or [],
                "spatial_component_id": row.get("spatial_component_id"),
                "spatial_component_size": row.get("spatial_component_size"),
                "local_density_bucket": row.get("local_density_bucket"),
                "local_neighbor_count_1m": row.get("local_neighbor_count_1m"),
                "local_neighbor_count_2m": row.get("local_neighbor_count_2m"),
                "local_neighbor_count_4m": row.get("local_neighbor_count_4m"),
                "spatial_context_score": row.get("spatial_context_score"),
                "nearest_candidate_distance_m": row.get("nearest_candidate_distance_m"),
                "viewpoint_source": row.get("viewpoint_source"),
                "standoff_distance_requested": row.get("standoff_distance_requested"),
                "standoff_target_horizontal_distance": row.get("standoff_target_horizontal_distance"),
                **stats,
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def relation_predicates(
    candidate: Dict[str, Any],
    context: Dict[str, Any],
    *,
    support_height_tolerance_m: float,
) -> Dict[str, Any]:
    candidate_pos = vector3(candidate.get("target_position"))
    context_pos = vector3(context.get("target_position"))
    distance = horizontal_distance(candidate.get("target_position"), context.get("target_position"))
    dx = dz = dy = None
    if candidate_pos is not None and context_pos is not None:
        dx = context_pos[0] - candidate_pos[0]
        dy = context_pos[1] - candidate_pos[1]
        dz = context_pos[2] - candidate_pos[2]
    same_component = (
        candidate.get("spatial_component_id") is not None
        and candidate.get("spatial_component_id") == context.get("spatial_component_id")
    )
    context_has_detector = safe_int(context.get("detector_associated_rows"), 0) > 0
    candidate_has_detector = safe_int(candidate.get("detector_associated_rows"), 0) > 0
    near_1 = distance is not None and distance <= 1.0
    near_2 = distance is not None and distance <= 2.0
    near_4 = distance is not None and distance <= 4.0
    overlap = distance is not None and distance <= 0.75
    same_surface = (
        dy is not None
        and abs(dy) <= support_height_tolerance_m
        and distance is not None
        and distance <= 2.0
    )
    co_visible_proxy = bool(candidate_has_detector and context_has_detector and (near_2 or same_component))
    predicate_values = {
        "near_1m_proxy": near_1,
        "near_2m_proxy": near_2,
        "near_4m_proxy": near_4,
        "overlap_proxy": overlap,
        "same_component_proxy": same_component,
        "same_support_surface_proxy": same_surface,
        "global_left_proxy": dx is not None and dx < 0,
        "global_right_proxy": dx is not None and dx > 0,
        "global_front_proxy": dz is not None and dz > 0,
        "global_behind_proxy": dz is not None and dz < 0,
        "co_visible_context_proxy": co_visible_proxy,
    }
    active = [key for key in RELATION_PREDICATE_KEYS if predicate_values.get(key) is True]
    return {
        "horizontal_distance_m": distance,
        "x_delta_context_minus_candidate_m": dx,
        "y_delta_context_minus_candidate_m": dy,
        "z_delta_context_minus_candidate_m": dz,
        **predicate_values,
        "relation_predicates": active,
        "relation_predicate_count": len(active),
    }


def build_context_object_rows(
    candidate_rows: Sequence[Dict[str, Any]],
    *,
    context_radius_m: float,
    support_height_tolerance_m: float,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    grouped = group_by_request(candidate_rows)
    for request_id, request_rows in sorted(grouped.items(), key=lambda item: request_sort_key(item[0])):
        for candidate in sorted(request_rows, key=candidate_sort_key):
            for context in sorted(request_rows, key=candidate_sort_key):
                if candidate_id(candidate) == candidate_id(context):
                    continue
                predicates = relation_predicates(
                    candidate,
                    context,
                    support_height_tolerance_m=support_height_tolerance_m,
                )
                distance = predicates.get("horizontal_distance_m")
                if distance is None or distance > context_radius_m:
                    continue
                rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "validation_stage": "action_context_object_relation",
                        "expanded_retrieval_request_id": request_id,
                        "episode_key": candidate.get("episode_key"),
                        "scene_key": candidate.get("scene_key"),
                        "scene_id": candidate.get("scene_id"),
                        "query": candidate.get("query"),
                        "candidate_id": candidate_id(candidate),
                        "context_candidate_id": candidate_id(context),
                        "candidate_generated_rank": candidate.get("target_generated_rank"),
                        "context_generated_rank": context.get("target_generated_rank"),
                        "candidate_role_tokens": candidate.get("target_candidate_role_tokens") or [],
                        "context_role_tokens": context.get("target_candidate_role_tokens") or [],
                        "candidate_spatial_component_id": candidate.get("spatial_component_id"),
                        "context_spatial_component_id": context.get("spatial_component_id"),
                        "candidate_detector_associated_rows": candidate.get("detector_associated_rows"),
                        "context_detector_associated_rows": context.get("detector_associated_rows"),
                        **predicates,
                        "terminal_commit": False,
                        "uses_gt_for_action": False,
                    }
                )
    return rows


def context_rows_by_candidate(
    context_rows: Sequence[Dict[str, Any]]
) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in context_rows:
        grouped[(row_request_id(row), str(row.get("candidate_id")))].append(dict(row))
    return grouped


def relation_signature_score(row: Dict[str, Any]) -> float:
    return (
        safe_int(row.get("near_1m_context_object_count"), 0) * 1.0
        + safe_int(row.get("near_2m_context_object_count"), 0) * 0.6
        + safe_int(row.get("same_component_context_object_count"), 0) * 0.25
        + safe_int(row.get("same_support_surface_context_object_count"), 0) * 0.75
        + safe_int(row.get("co_visible_context_object_count"), 0) * 0.75
        + min(3, safe_int(row.get("detector_associated_rows"), 0)) * 1.0
        + min(3, safe_int(row.get("detector_consistent_depth_rows"), 0)) * 0.5
        + (safe_float(row.get("detector_score_max"), 0.0) or 0.0)
    )


def enrich_candidate_relation_rows(
    base_rows: Sequence[Dict[str, Any]],
    context_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped = context_rows_by_candidate(context_rows)
    output: List[Dict[str, Any]] = []
    for row in base_rows:
        context = grouped.get((row_request_id(row), candidate_id(row)), [])
        predicate_counts = Counter(
            predicate for context_row in context for predicate in context_row.get("relation_predicates") or []
        )
        relation_object_count = len(context)
        enriched = {
            **row,
            "context_object_count": relation_object_count,
            "near_1m_context_object_count": predicate_counts.get("near_1m_proxy", 0),
            "near_2m_context_object_count": predicate_counts.get("near_2m_proxy", 0),
            "near_4m_context_object_count": predicate_counts.get("near_4m_proxy", 0),
            "overlap_context_object_count": predicate_counts.get("overlap_proxy", 0),
            "same_component_context_object_count": predicate_counts.get("same_component_proxy", 0),
            "same_support_surface_context_object_count": predicate_counts.get(
                "same_support_surface_proxy", 0
            ),
            "co_visible_context_object_count": predicate_counts.get("co_visible_context_proxy", 0),
            "relation_predicate_count_total": sum(predicate_counts.values()),
            "relation_predicate_count_by_type": dict(sorted(predicate_counts.items())),
            "context_object_distance_stats": distance_stats(
                [safe_float(context_row.get("horizontal_distance_m")) for context_row in context]
            ),
        }
        score = relation_signature_score(enriched)
        enriched["relation_signature_score"] = score
        enriched["relation_density_bucket"] = relation_count_bucket(relation_object_count)
        enriched["candidate_relation_signature"] = "|".join(
            [
                str(enriched.get("relation_density_bucket")),
                f"component={enriched.get('spatial_component_size')}",
                f"near2={enriched.get('near_2m_context_object_count')}",
                f"surface={enriched.get('same_support_surface_context_object_count')}",
                f"covisible={enriched.get('co_visible_context_object_count')}",
                f"detector={enriched.get('detector_associated_rows')}",
            ]
        )
        enriched["relation_view_consistency_profile"] = (
            "detector_consistent_multi_heading"
            if safe_int(enriched.get("detector_consistent_depth_rows"), 0) >= 2
            else "detector_visible_but_depth_weak"
            if safe_int(enriched.get("detector_visible_rows"), 0) > 0
            else "detector_relation_missing"
        )
        output.append(enriched)
    return output


def candidate_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {(row_request_id(row), candidate_id(row)): row for row in rows}


def build_pair_relation_rows(
    relation_spatial_pair_rows: Sequence[Dict[str, Any]],
    candidate_relation_rows: Sequence[Dict[str, Any]],
    *,
    relation_delta_margin: float,
) -> List[Dict[str, Any]]:
    indexed = candidate_index(candidate_relation_rows)
    rows: List[Dict[str, Any]] = []
    for row in sorted(
        relation_spatial_pair_rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            safe_int(item.get("selector_generated_rank"), 999999),
            safe_int(item.get("contrast_generated_rank"), 999999),
            str(item.get("contrast_candidate_id")),
        ),
    ):
        request_id = row_request_id(row)
        selector = indexed.get((request_id, str(row.get("selector_candidate_id")))) or {}
        contrast = indexed.get((request_id, str(row.get("contrast_candidate_id")))) or {}
        relation_delta = delta(
            contrast.get("relation_signature_score"),
            selector.get("relation_signature_score"),
        )
        detector_delta = delta(
            contrast.get("detector_associated_rows"),
            selector.get("detector_associated_rows"),
        )
        support_surface_delta = safe_int(contrast.get("same_support_surface_context_object_count"), 0) - safe_int(
            selector.get("same_support_surface_context_object_count"), 0
        )
        co_visible_delta = safe_int(contrast.get("co_visible_context_object_count"), 0) - safe_int(
            selector.get("co_visible_context_object_count"), 0
        )
        relation_delta_sign = relation_delta_bucket(relation_delta, relation_delta_margin)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_pair_object_relation",
                "expanded_retrieval_request_id": request_id,
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "selector_candidate_id": row.get("selector_candidate_id"),
                "contrast_candidate_id": row.get("contrast_candidate_id"),
                "selector_candidate_variants": row.get("selector_candidate_variants") or [],
                "selector_generated_rank": row.get("selector_generated_rank"),
                "contrast_generated_rank": row.get("contrast_generated_rank"),
                "rank_delta_contrast_minus_selector": row.get("rank_delta_contrast_minus_selector"),
                "visual_delta_sign": row.get("visual_delta_sign"),
                "visual_support_delta_contrast_minus_selector": row.get(
                    "visual_support_delta_contrast_minus_selector"
                ),
                "same_spatial_component": row.get("same_spatial_component"),
                "relation_context_profile": row.get("relation_context_profile"),
                "selector_relation_signature": selector.get("candidate_relation_signature"),
                "contrast_relation_signature": contrast.get("candidate_relation_signature"),
                "selector_relation_signature_score": selector.get("relation_signature_score"),
                "contrast_relation_signature_score": contrast.get("relation_signature_score"),
                "relation_signature_score_delta_contrast_minus_selector": relation_delta,
                "relation_signature_score_delta_sign": relation_delta_sign,
                "selector_context_object_count": selector.get("context_object_count"),
                "contrast_context_object_count": contrast.get("context_object_count"),
                "selector_relation_density_bucket": selector.get("relation_density_bucket"),
                "contrast_relation_density_bucket": contrast.get("relation_density_bucket"),
                "selector_detector_associated_rows": selector.get("detector_associated_rows"),
                "contrast_detector_associated_rows": contrast.get("detector_associated_rows"),
                "detector_association_delta_contrast_minus_selector": detector_delta,
                "detector_association_delta_sign": delta_sign(
                    detector_delta,
                    "contrast_detector_higher",
                    "selector_detector_higher",
                ),
                "same_support_surface_delta_contrast_minus_selector": support_surface_delta,
                "co_visible_context_delta_contrast_minus_selector": co_visible_delta,
                "selector_relation_view_consistency_profile": selector.get(
                    "relation_view_consistency_profile"
                ),
                "contrast_relation_view_consistency_profile": contrast.get(
                    "relation_view_consistency_profile"
                ),
                "relation_predicate_conflict_profile": relation_conflict_profile(
                    row,
                    relation_delta_sign,
                    detector_delta,
                ),
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def relation_conflict_profile(
    row: Dict[str, Any],
    relation_delta_sign: str,
    detector_delta: Optional[float],
) -> str:
    if row.get("same_spatial_component") is True and row.get("visual_delta_sign") == "selector_visual_higher":
        if relation_delta_sign == "contrast_relation_higher":
            return "same_component_relation_counteracts_selector_visual"
        return "same_component_relation_not_discriminative"
    if relation_delta_sign == "contrast_relation_higher" and row.get("visual_delta_sign") == "selector_visual_higher":
        return "relation_counteracts_selector_visual"
    if detector_delta is not None and detector_delta < 0:
        return "selector_detector_stronger_than_contrast"
    return "relation_context_for_followup"


def build_request_relation_rows(
    candidate_relation_rows: Sequence[Dict[str, Any]],
    pair_relation_rows: Sequence[Dict[str, Any]],
    context_object_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    candidates_by_request = group_by_request(candidate_relation_rows)
    pairs_by_request = group_by_request(pair_relation_rows)
    context_by_request = group_by_request(context_object_rows)
    for request_id, candidates in sorted(candidates_by_request.items(), key=lambda item: request_sort_key(item[0])):
        pairs = pairs_by_request.get(request_id, [])
        context = context_by_request.get(request_id, [])
        relation_delta_counts = Counter(str(row.get("relation_signature_score_delta_sign")) for row in pairs)
        conflict_counts = Counter(str(row.get("relation_predicate_conflict_profile")) for row in pairs)
        predicate_counts = Counter(
            predicate for row in context for predicate in row.get("relation_predicates") or []
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_request_object_relation",
                "expanded_retrieval_request_id": request_id,
                "episode_key": candidates[0].get("episode_key") if candidates else None,
                "scene_key": candidates[0].get("scene_key") if candidates else None,
                "scene_id": candidates[0].get("scene_id") if candidates else None,
                "query": candidates[0].get("query") if candidates else None,
                "candidate_relation_rows": len(candidates),
                "pair_relation_rows": len(pairs),
                "context_object_rows": len(context),
                "relation_density_bucket_counts": dict(
                    sorted(Counter(str(row.get("relation_density_bucket")) for row in candidates).items())
                ),
                "relation_signature_score_stats": distance_stats(
                    [safe_float(row.get("relation_signature_score")) for row in candidates]
                ),
                "relation_signature_delta_sign_counts": dict(sorted(relation_delta_counts.items())),
                "relation_predicate_conflict_profile_counts": dict(sorted(conflict_counts.items())),
                "relation_predicate_count_by_type": dict(sorted(predicate_counts.items())),
                "candidate_rows_with_detector_association": sum(
                    1 for row in candidates if safe_int(row.get("detector_associated_rows"), 0) > 0
                ),
                "candidate_rows_with_context_objects": sum(
                    1 for row in candidates if safe_int(row.get("context_object_count"), 0) > 0
                ),
                "next_relation_action": "profile_scene_graph_object_relation",
                "next_relation_reason": "diagnostic_only_before_terminal_policy",
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def evaluated_candidate_relation_rows(
    action_rows: Sequence[Dict[str, Any]],
    evaluated_candidate_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    labels = {
        (row_request_id(row), candidate_id(row)): {
            "evaluation_only_candidate_correct": row.get("evaluation_only_candidate_correct"),
            "evaluation_only_candidate_rank": row.get("evaluation_only_candidate_rank"),
        }
        for row in evaluated_candidate_rows
    }
    rows: List[Dict[str, Any]] = []
    for row in action_rows:
        label = labels.get((row_request_id(row), candidate_id(row))) or {}
        rows.append(
            {
                **row,
                "validation_stage": "evaluated_candidate_object_relation_after_action_rows",
                "evaluation_only_candidate_correct": label.get("evaluation_only_candidate_correct"),
                "evaluation_only_candidate_rank": label.get("evaluation_only_candidate_rank"),
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def evaluated_pair_relation_rows(
    action_rows: Sequence[Dict[str, Any]],
    evaluated_pair_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    labels = {
        (
            row_request_id(row),
            str(row.get("selector_candidate_id")),
            str(row.get("contrast_candidate_id")),
        ): {
            "evaluation_only_selector_candidate_correct": row.get(
                "evaluation_only_selector_candidate_correct"
            ),
            "evaluation_only_contrast_candidate_correct": row.get(
                "evaluation_only_contrast_candidate_correct"
            ),
            "evaluation_only_target_contrast_pair": row.get("evaluation_only_target_contrast_pair"),
        }
        for row in evaluated_pair_rows
    }
    rows: List[Dict[str, Any]] = []
    for row in action_rows:
        label = labels.get(
            (
                row_request_id(row),
                str(row.get("selector_candidate_id")),
                str(row.get("contrast_candidate_id")),
            )
        ) or {}
        rows.append(
            {
                **row,
                "validation_stage": "evaluated_pair_object_relation_after_action_rows",
                "evaluation_only_selector_candidate_correct": label.get(
                    "evaluation_only_selector_candidate_correct"
                ),
                "evaluation_only_contrast_candidate_correct": label.get(
                    "evaluation_only_contrast_candidate_correct"
                ),
                "evaluation_only_target_contrast_pair": label.get(
                    "evaluation_only_target_contrast_pair"
                ),
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def relation_failure_taxonomy(row: Dict[str, Any]) -> str:
    if row.get("evaluation_only_target_contrast_pair") is not True:
        return "not_target_contrast_pair"
    relation_delta_sign = str(row.get("relation_signature_score_delta_sign"))
    if row.get("same_spatial_component") is True and row.get("visual_delta_sign") == "selector_visual_higher":
        if relation_delta_sign == "contrast_relation_higher":
            return "same_component_relation_counteracts_selector_visual"
        return "same_component_relation_not_discriminative"
    if relation_delta_sign == "selector_relation_higher":
        return "selector_relation_higher_on_target_pair"
    if relation_delta_sign == "relation_tie_or_small_delta":
        return "relation_delta_too_small_on_target_pair"
    return "relation_context_candidate_for_followup"


def simpler_alternative_report(
    target_pairs: Sequence[Dict[str, Any]],
    relation_delta_margin: float,
) -> Dict[str, Any]:
    selector_visual = sum(1 for row in target_pairs if row.get("visual_delta_sign") == "selector_visual_higher")
    selector_relation = sum(
        1 for row in target_pairs if row.get("relation_signature_score_delta_sign") == "selector_relation_higher"
    )
    contrast_relation = sum(
        1 for row in target_pairs if row.get("relation_signature_score_delta_sign") == "contrast_relation_higher"
    )
    small_delta = sum(
        1 for row in target_pairs if row.get("relation_signature_score_delta_sign") == "relation_tie_or_small_delta"
    )
    return {
        "defer_all": {
            "terminal_commit_rows": 0,
            "status": "safe_but_no_utility_claim",
        },
        "semantic_top_observed": {
            "blocked_by": "unsafe_selector_rows_exist_in_source_diagnostic",
            "target_pairs_with_selector_visual_advantage": selector_visual,
        },
        "detector_score_best_observed": {
            "blocked_by": "detector_visibility_is_not_goal_validity",
            "target_pairs_with_selector_visual_advantage": selector_visual,
        },
        "candidate_specific_support_best_observed": {
            "blocked_by": "candidate_specific_support_saturates_many_candidates",
        },
        "context_score_best": {
            "blocked_by": "static_context_did_not_resolve_same_component_selector_cases",
        },
        "same_component_context_score_best": {
            "blocked_by": "same_component_relation_delta_requires_object_relation_check",
        },
        "nearest_context_object_count_best": {
            "blocked_by": "relation count alone ignores detector and support-surface proxies",
        },
        "single_relation_predicate_best": {
            "blocked_by": "single predicate cannot cover detector, geometry, and context conflicts",
            "relation_delta_margin": relation_delta_margin,
            "target_pairs_contrast_relation_higher": contrast_relation,
            "target_pairs_selector_relation_higher": selector_relation,
            "target_pairs_small_relation_delta": small_delta,
        },
    }


def summarize(
    *,
    contract: Dict[str, Any],
    relation_summary: Dict[str, Any],
    detector_summary: Dict[str, Any],
    source_request_rows: Sequence[Dict[str, Any]],
    candidate_relation_rows: Sequence[Dict[str, Any]],
    pair_relation_rows: Sequence[Dict[str, Any]],
    request_relation_rows: Sequence[Dict[str, Any]],
    context_object_rows: Sequence[Dict[str, Any]],
    evaluated_candidate_rows: Sequence[Dict[str, Any]],
    evaluated_pair_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = dict(contract.get("evaluation_gates") or {})
    action_rows = [
        *candidate_relation_rows,
        *pair_relation_rows,
        *request_relation_rows,
        *context_object_rows,
    ]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    request_ids = sorted({row_request_id(row) for row in candidate_relation_rows}, key=request_sort_key)
    target_pairs = [
        {**row, "relation_failure_taxonomy": relation_failure_taxonomy(row)}
        for row in evaluated_pair_rows
        if row.get("evaluation_only_target_contrast_pair") is True
    ]
    same_component_target_pairs = [row for row in target_pairs if row.get("same_spatial_component") is True]
    same_component_selector_visual_pairs = [
        row
        for row in same_component_target_pairs
        if row.get("visual_delta_sign") == "selector_visual_higher"
    ]
    relation_delta_counts = Counter(str(row.get("relation_signature_score_delta_sign")) for row in target_pairs)
    same_component_delta_counts = Counter(
        str(row.get("relation_signature_score_delta_sign")) for row in same_component_target_pairs
    )
    taxonomy_counts = Counter(str(row.get("relation_failure_taxonomy")) for row in target_pairs)
    relation_coverage_rows = [
        row for row in candidate_relation_rows if safe_int(row.get("context_object_count"), 0) > 0
    ]
    detector_coverage_rows = [
        row for row in candidate_relation_rows if safe_int(row.get("detector_associated_rows"), 0) > 0
    ]
    separability_probe_supports_relation_signal = (
        len(target_pairs)
        >= safe_int(gates.get("target_contrast_pair_rows_minimum_after_label_join"), 0)
        and len(same_component_target_pairs)
        >= safe_int(gates.get("same_component_target_pair_rows_minimum_after_label_join"), 0)
        and len(same_component_selector_visual_pairs)
        >= safe_int(gates.get("same_component_selector_visual_dominates_minimum_after_label_join"), 0)
        and all(
            row.get("relation_signature_score_delta_sign") == "contrast_relation_higher"
            for row in same_component_selector_visual_pairs
        )
    )
    relation_coverage_complete = len(relation_coverage_rows) == len(candidate_relation_rows)
    detector_coverage_complete = len(detector_coverage_rows) == len(candidate_relation_rows)
    relation_signal_ready = (
        separability_probe_supports_relation_signal
        and relation_coverage_complete
        and detector_coverage_complete
    )
    if not relation_coverage_complete or not detector_coverage_complete:
        recommended_next_action = "request_object_relation_observation"
    elif relation_signal_ready:
        recommended_next_action = "request_language_conditioned_relation_evidence"
    else:
        recommended_next_action = "defer_goal_validity_terminal_policy"
    if relation_signal_ready:
        conclusion_reason = "same_component_selector_visual_pairs_have_contrast_relation_advantage"
    elif separability_probe_supports_relation_signal:
        conclusion_reason = "target_pair_relation_probe_positive_but_relation_coverage_incomplete"
    else:
        conclusion_reason = "candidate_local_object_relation_proxy_not_terminal_separator"

    gate = {
        "input_relation_spatial_context_gate_passed": relation_summary.get("gate", {}).get(
            "relation_spatial_context_gate_passed"
        )
        is True,
        "expected_request_rows_passed": len(request_ids) == safe_int(gates.get("expected_request_rows")),
        "expected_candidate_context_rows_passed": len(candidate_relation_rows)
        == safe_int(gates.get("expected_candidate_context_rows")),
        "expected_pair_context_rows_passed": len(pair_relation_rows)
        == safe_int(gates.get("expected_pair_context_rows")),
        "target_contrast_pair_rows_minimum_after_label_join_passed": len(target_pairs)
        >= safe_int(gates.get("target_contrast_pair_rows_minimum_after_label_join"), 0),
        "same_component_target_pair_rows_minimum_after_label_join_passed": len(same_component_target_pairs)
        >= safe_int(gates.get("same_component_target_pair_rows_minimum_after_label_join"), 0),
        "same_component_selector_visual_dominates_minimum_after_label_join_passed": len(
            same_component_selector_visual_pairs
        )
        >= safe_int(gates.get("same_component_selector_visual_dominates_minimum_after_label_join"), 0),
        "spatial_context_group_count_minimum_passed": relation_summary.get("spatial_context_group_count", 0)
        >= safe_int(gates.get("spatial_context_group_count_minimum"), 0),
        "relation_candidate_rows_minimum_passed": len(candidate_relation_rows)
        >= safe_int(gates.get("relation_candidate_rows_minimum"), 0),
        "relation_pair_rows_minimum_passed": len(pair_relation_rows)
        >= safe_int(gates.get("relation_pair_rows_minimum"), 0),
        "context_object_rows_present_passed": len(context_object_rows) > 0,
        "detector_substrate_gate_passed": detector_summary.get("gate", {}).get("passes_detector_substrate_gate")
        is True,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["scene_graph_object_relation_gate_passed"] = all(
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
        "relation_summary": str(args.relation_summary),
        "candidate_context_rows": str(args.candidate_context_rows),
        "pair_context_rows": str(args.pair_context_rows),
        "request_context_rows": str(args.request_context_rows),
        "detector_associations": str(args.detector_associations),
        "detector_frame_summary": str(args.detector_frame_summary),
        "detector_summary": str(args.detector_summary),
        "out_root": str(args.out_root),
        "source_request_rows": len(source_request_rows),
        "request_rows": len(request_relation_rows),
        "candidate_relation_rows": len(candidate_relation_rows),
        "pair_relation_rows": len(pair_relation_rows),
        "context_object_rows": len(context_object_rows),
        "evaluated_candidate_relation_rows": len(evaluated_candidate_rows),
        "evaluated_pair_relation_rows": len(evaluated_pair_rows),
        "relation_coverage_by_request": {
            request_id: {
                "candidate_relation_rows": len(rows),
                "rows_with_context_objects": sum(
                    1 for row in rows if safe_int(row.get("context_object_count"), 0) > 0
                ),
                "rows_with_detector_association": sum(
                    1 for row in rows if safe_int(row.get("detector_associated_rows"), 0) > 0
                ),
                "context_object_rows": sum(
                    1 for row in context_object_rows if row_request_id(row) == request_id
                ),
            }
            for request_id, rows in group_by_request(candidate_relation_rows).items()
        },
        "action_time_relation_profile": {
            "relation_density_bucket_counts": dict(
                sorted(Counter(str(row.get("relation_density_bucket")) for row in candidate_relation_rows).items())
            ),
            "relation_view_consistency_counts": dict(
                sorted(
                    Counter(
                        str(row.get("relation_view_consistency_profile"))
                        for row in candidate_relation_rows
                    ).items()
                )
            ),
            "candidate_relation_signature_score_stats": distance_stats(
                [safe_float(row.get("relation_signature_score")) for row in candidate_relation_rows]
            ),
            "context_object_distance_stats": distance_stats(
                [safe_float(row.get("horizontal_distance_m")) for row in context_object_rows]
            ),
            "relation_predicate_count_by_context_row_stats": number_stats(
                [safe_int(row.get("relation_predicate_count"), 0) for row in context_object_rows]
            ),
            "relation_predicate_count_by_type": dict(
                sorted(
                    Counter(
                        predicate
                        for row in context_object_rows
                        for predicate in row.get("relation_predicates") or []
                    ).items()
                )
            ),
            "pair_relation_delta_sign_counts": dict(
                sorted(
                    Counter(
                        str(row.get("relation_signature_score_delta_sign"))
                        for row in pair_relation_rows
                    ).items()
                )
            ),
            "pair_relation_conflict_profile_counts": dict(
                sorted(
                    Counter(
                        str(row.get("relation_predicate_conflict_profile"))
                        for row in pair_relation_rows
                    ).items()
                )
            ),
        },
        "post_label_relation_separability_probe": {
            "evaluation_only_target_contrast_pair_rows": len(target_pairs),
            "evaluation_only_same_component_target_pair_rows": len(same_component_target_pairs),
            "evaluation_only_same_component_selector_visual_dominates_rows": len(
                same_component_selector_visual_pairs
            ),
            "evaluation_only_target_pair_relation_delta_sign_counts": dict(
                sorted(relation_delta_counts.items())
            ),
            "evaluation_only_same_component_target_pair_relation_delta_sign_counts": dict(
                sorted(same_component_delta_counts.items())
            ),
            "evaluation_only_relation_failure_taxonomy_counts": dict(sorted(taxonomy_counts.items())),
            "relation_separability_probe_supports_signal": separability_probe_supports_relation_signal,
            "relation_coverage_complete": relation_coverage_complete,
            "detector_coverage_complete": detector_coverage_complete,
            "scene_graph_object_relation_signal_ready": relation_signal_ready,
        },
        "simpler_alternatives": simpler_alternative_report(target_pairs, float(args.relation_delta_margin)),
        "diagnostic_conclusion": {
            "scene_graph_object_relation_signal_ready": relation_signal_ready,
            "recommended_next_action": recommended_next_action,
            "reason": conclusion_reason,
            "terminal_policy_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": "The analyzer materializes candidate-local object-relation proxy rows before joining correctness labels.",
            "agent_inference": (
                "If the same-component selector failures still do not separate under relation signatures, the current evidence should remain nonterminal rather than becoming a threshold-tuned commit rule."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "candidate_relation_rows": "goal_validity_scene_graph_candidate_relation_rows.jsonl",
            "pair_relation_rows": "goal_validity_scene_graph_pair_relation_rows.jsonl",
            "request_relation_rows": "goal_validity_scene_graph_request_relation_rows.jsonl",
            "evaluated_candidate_relation_rows": "goal_validity_scene_graph_evaluated_candidate_relation_rows.jsonl",
            "evaluated_pair_relation_rows": "goal_validity_scene_graph_evaluated_pair_relation_rows.jsonl",
            "context_object_rows": "goal_validity_scene_graph_context_object_rows.jsonl",
            "summary": "goal_validity_scene_graph_object_relation_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    relation_summary = load_json(Path(args.relation_summary))
    detector_summary = load_json(Path(args.detector_summary))
    candidate_context = load_jsonl(Path(args.candidate_context_rows))
    pair_context = load_jsonl(Path(args.pair_context_rows))
    request_context = load_jsonl(Path(args.request_context_rows))
    evaluated_candidates_source = load_jsonl(Path(args.evaluated_candidate_context_rows))
    evaluated_pairs_source = load_jsonl(Path(args.evaluated_pair_context_rows))
    detector_associations = load_jsonl(Path(args.detector_associations))
    detector_frames = load_jsonl(Path(args.detector_frame_summary))
    base_candidates = candidate_relation_base_rows(
        candidate_context,
        detector_associations,
        detector_frames,
    )
    context_objects = build_context_object_rows(
        base_candidates,
        context_radius_m=float(args.context_radius_m),
        support_height_tolerance_m=float(args.support_height_tolerance_m),
    )
    candidates = enrich_candidate_relation_rows(base_candidates, context_objects)
    pairs = build_pair_relation_rows(
        pair_context,
        candidates,
        relation_delta_margin=float(args.relation_delta_margin),
    )
    requests = build_request_relation_rows(candidates, pairs, context_objects)
    evaluated_candidates = evaluated_candidate_relation_rows(candidates, evaluated_candidates_source)
    evaluated_pairs = evaluated_pair_relation_rows(pairs, evaluated_pairs_source)
    summary = summarize(
        contract=contract,
        relation_summary=relation_summary,
        detector_summary=detector_summary,
        source_request_rows=request_context,
        candidate_relation_rows=candidates,
        pair_relation_rows=pairs,
        request_relation_rows=requests,
        context_object_rows=context_objects,
        evaluated_candidate_rows=evaluated_candidates,
        evaluated_pair_rows=evaluated_pairs,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "goal_validity_scene_graph_candidate_relation_rows.jsonl", candidates)
    write_jsonl(out_root / "goal_validity_scene_graph_pair_relation_rows.jsonl", pairs)
    write_jsonl(out_root / "goal_validity_scene_graph_request_relation_rows.jsonl", requests)
    write_jsonl(out_root / "goal_validity_scene_graph_evaluated_candidate_relation_rows.jsonl", evaluated_candidates)
    write_jsonl(out_root / "goal_validity_scene_graph_evaluated_pair_relation_rows.jsonl", evaluated_pairs)
    write_jsonl(out_root / "goal_validity_scene_graph_context_object_rows.jsonl", context_objects)
    write_json(out_root / "goal_validity_scene_graph_object_relation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze candidate-local scene-graph/object-relation proxy evidence after relation/spatial ambiguity."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--relation-summary", required=True)
    parser.add_argument("--candidate-context-rows", required=True)
    parser.add_argument("--pair-context-rows", required=True)
    parser.add_argument("--request-context-rows", required=True)
    parser.add_argument("--evaluated-candidate-context-rows", required=True)
    parser.add_argument("--evaluated-pair-context-rows", required=True)
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--detector-frame-summary", required=True)
    parser.add_argument("--detector-summary", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--context-radius-m", type=float, default=4.0)
    parser.add_argument("--support-height-tolerance-m", type=float, default=0.35)
    parser.add_argument("--relation-delta-margin", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
