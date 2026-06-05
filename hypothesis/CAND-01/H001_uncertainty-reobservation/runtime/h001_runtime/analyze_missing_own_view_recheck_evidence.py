import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    load_json,
    load_jsonl,
    request_sort_key,
    safe_float,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.missing_own_view_recheck_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_missing_own_view_recheck_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_missing_own_view_recheck_evidence_v1"


def source_path(args: argparse.Namespace, contract: Mapping[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def row_request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def row_candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def row_decision_id(row: Mapping[str, Any]) -> str:
    return str(row.get("decision_id") or "")


def candidate_sort_key(candidate_id: str) -> Tuple[int, str]:
    tail = str(candidate_id).rsplit(":", 1)[-1]
    if tail.isdigit():
        return (safe_int(tail, 999999), str(candidate_id))
    return (999999, str(candidate_id))


def group_by_decision(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_decision_id(row)].append(dict(row))
    return grouped


def group_by_candidate(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row_request_id(row), row_candidate_id(row))].append(row)
    return grouped


def group_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(row)
    return grouped


def mean(values: Sequence[Optional[float]]) -> Optional[float]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def finite_stats(values: Sequence[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(clean), "mean": sum(clean) / len(clean), "max": max(clean)}


def association_stats(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    visible = [row for row in rows if str(row.get("projection_status")) == "visible"]
    inside_box = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    inside_mask = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    depth_consistent = [
        row
        for row in rows
        if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    associated_depth_consistent = [
        row
        for row in associated
        if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    depth_mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    out_of_fov = [row for row in rows if str(row.get("projection_status")) == "out_of_fov"]
    box_scores = [safe_float(row.get("best_box_score")) for row in rows]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
    depth_agreements = [safe_float(row.get("depth_agreement_m")) for row in rows]
    associated_depth_agreements = [safe_float(row.get("depth_agreement_m")) for row in associated]
    return {
        "association_rows": len(rows),
        "associated_heading_count": len(associated),
        "visible_count": len(visible),
        "projected_pixel_inside_box_count": len(inside_box),
        "projected_pixel_inside_mask_count": len(inside_mask),
        "depth_consistent_count": len(depth_consistent),
        "associated_depth_consistent_count": len(associated_depth_consistent),
        "depth_mismatch_count": len(depth_mismatch),
        "out_of_fov_count": len(out_of_fov),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in rows),
        "projection_anchor_offset_counts": compact_counter(row.get("projection_anchor_height_offset_m") for row in rows),
        "best_box_score_max": max([score for score in box_scores if score is not None], default=None),
        "best_box_score_mean": mean(box_scores),
        "depth_error_stats_m": finite_stats(depth_errors),
        "depth_agreement_stats_m": finite_stats(depth_agreements),
        "associated_depth_agreement_stats_m": finite_stats(associated_depth_agreements),
    }


def view_status(frame: Mapping[str, Any], stats: Mapping[str, Any]) -> str:
    if frame.get("has_candidate_association") is True and safe_int(stats.get("projected_pixel_inside_mask_count"), 0) > 0:
        return "candidate_own_view_support_observed"
    if frame.get("has_detector_box") is True and frame.get("has_sam2_mask") is True:
        return "detector_visible_but_candidate_unassociated"
    if frame.get("has_detector_box") is True:
        return "detector_box_without_sam2_mask"
    return "detector_absent"


def build_view_rows(
    frame_rows: Sequence[Dict[str, Any]],
    associations_by_decision: Mapping[str, Sequence[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for frame in sorted(
        frame_rows,
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            candidate_sort_key(row_candidate_id(row)),
            safe_int(row.get("source_plan_index"), 999999),
            row_decision_id(row),
        ),
    ):
        associations = list(associations_by_decision.get(row_decision_id(frame), []))
        stats = association_stats(associations)
        status = view_status(frame, stats)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_recheck_view_evidence",
                "row_type": "view_evidence",
                "contract_name": "missing_own_view_recheck_evidence_v1",
                "source_contract_name": frame.get("contract_name"),
                "expanded_retrieval_request_id": row_request_id(frame),
                "rival_identity_request_id": frame.get("rival_identity_request_id") or row_request_id(frame),
                "episode_key": frame.get("episode_key"),
                "episode_id": frame.get("episode_id"),
                "scene_key": frame.get("scene_key"),
                "scene_id": frame.get("scene_id"),
                "query": frame.get("query"),
                "request_index": frame.get("request_index"),
                "decision_id": row_decision_id(frame),
                "target_candidate_id": row_candidate_id(frame),
                "candidate_id": row_candidate_id(frame),
                "target_candidate_role": frame.get("target_candidate_role"),
                "target_generated_rank": frame.get("target_generated_rank"),
                "target_semantic_rank": frame.get("target_semantic_rank"),
                "target_score": frame.get("target_score"),
                "target_semantic_score": frame.get("target_semantic_score"),
                "target_support_score": frame.get("target_support_score"),
                "view_role": frame.get("view_role"),
                "source_plan_index": frame.get("source_plan_index"),
                "source_viewpoint_id": frame.get("source_viewpoint_id"),
                "viewpoint_source": frame.get("viewpoint_source"),
                "standoff_direction_source": frame.get("standoff_direction_source"),
                "standoff_distance_requested": frame.get("standoff_distance_requested"),
                "standoff_target_horizontal_distance": frame.get("standoff_target_horizontal_distance"),
                "target_distance_from_viewpoint_m": frame.get("target_distance_from_viewpoint_m"),
                "projection_anchor_policy": frame.get("projection_anchor_policy"),
                "projection_anchor_height_offsets_m": frame.get("projection_anchor_height_offsets_m"),
                "rendered_heading_count": frame.get("rendered_heading_count"),
                "detector_box_count": safe_int(frame.get("detector_box_count"), 0),
                "sam2_mask_count": safe_int(frame.get("sam2_mask_count"), 0),
                "has_detector_box": frame.get("has_detector_box") is True,
                "has_sam2_mask": frame.get("has_sam2_mask") is True,
                "has_candidate_association": frame.get("has_candidate_association") is True,
                "associated_candidate_heading_count": safe_int(frame.get("associated_candidate_heading_count"), 0),
                "candidate_associated_depth_consistent_count": stats["associated_depth_consistent_count"],
                "projected_pixel_inside_mask_count": stats["projected_pixel_inside_mask_count"],
                "view_own_view_support": status == "candidate_own_view_support_observed",
                "view_evidence_status": status,
                "association_stats": stats,
                "recommended_nonterminal_action": "aggregate_missing_own_view_candidate_evidence",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def target_row_index(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str], Mapping[str, Any]]:
    indexed: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        indexed[(row_request_id(row), row_candidate_id(row))] = row
    return indexed


def own_view_support_status(view_count: int, associated_views: int, depth_consistent: int, detector_box_views: int, sam2_mask_views: int) -> str:
    if associated_views >= 3 and depth_consistent > 0:
        return "candidate_own_view_support_acquired"
    if associated_views > 0 or detector_box_views > 0 or sam2_mask_views > 0:
        return "candidate_own_view_support_partial"
    return "candidate_own_view_support_absent"


def candidate_action(status: str) -> str:
    if status == "candidate_own_view_support_acquired":
        return "keep_nonterminal_acquired_own_view_support_for_later_arbitration"
    if status == "candidate_own_view_support_partial":
        return "audit_partial_own_view_support_before_guard_interpretation"
    return "audit_absent_own_view_support_without_rejection"


def build_candidate_rows(
    view_rows: Sequence[Mapping[str, Any]],
    target_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    targets = target_row_index(target_rows)
    grouped = group_by_candidate(view_rows)
    rows: List[Dict[str, Any]] = []
    for key, group in sorted(
        grouped.items(),
        key=lambda item: (request_sort_key(item[0][0]), candidate_sort_key(item[0][1])),
    ):
        rid, cid = key
        group = sorted(group, key=lambda row: safe_int(row.get("source_plan_index"), 999999))
        target = targets.get(key, {})
        first = group[0]
        view_count = len(group)
        associated_views = sum(1 for row in group if row.get("has_candidate_association") is True)
        detector_box_views = sum(1 for row in group if row.get("has_detector_box") is True)
        sam2_mask_views = sum(1 for row in group if row.get("has_sam2_mask") is True)
        associated_headings = sum(safe_int(row.get("associated_candidate_heading_count"), 0) for row in group)
        inside_mask = sum(safe_int(row.get("projected_pixel_inside_mask_count"), 0) for row in group)
        depth_consistent = sum(safe_int(row.get("candidate_associated_depth_consistent_count"), 0) for row in group)
        unassociated = [row for row in group if row.get("has_candidate_association") is not True]
        status = own_view_support_status(
            view_count,
            associated_views,
            depth_consistent,
            detector_box_views,
            sam2_mask_views,
        )
        guard_status = (
            "negative_missing_support_guard_ready_for_later_arbitration"
            if status == "candidate_own_view_support_acquired"
            else "negative_missing_support_guard_not_promotable"
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_recheck_candidate_evidence",
                "row_type": "target_candidate_evidence",
                "contract_name": "missing_own_view_recheck_evidence_v1",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": target.get("rival_identity_request_id") or rid,
                "episode_key": first.get("episode_key"),
                "scene_key": first.get("scene_key"),
                "scene_id": first.get("scene_id"),
                "query": first.get("query"),
                "target_candidate_id": cid,
                "candidate_id": cid,
                "target_candidate_role": target.get("target_candidate_role") or first.get("target_candidate_role"),
                "target_generated_rank": target.get("target_generated_rank") or first.get("target_generated_rank"),
                "target_semantic_rank": target.get("target_semantic_rank") or first.get("target_semantic_rank"),
                "target_score": target.get("target_score") or first.get("target_score"),
                "target_semantic_score": target.get("target_semantic_score") or first.get("target_semantic_score"),
                "target_support_score": target.get("target_support_score") or first.get("target_support_score"),
                "base_candidate_evidence_class": target.get("base_candidate_evidence_class"),
                "base_candidate_specific_support": target.get("base_candidate_specific_support") is True,
                "base_strong_own_view_evidence": target.get("base_strong_own_view_evidence") is True,
                "base_has_candidate_association": target.get("base_has_candidate_association") is True,
                "base_visible_count": safe_int(target.get("base_visible_count"), 0),
                "base_mask_hit_count": safe_int(target.get("base_mask_hit_count"), 0),
                "base_consistent_depth_count": safe_int(target.get("base_consistent_depth_count"), 0),
                "base_depth_mismatch_count": safe_int(target.get("base_depth_mismatch_count"), 0),
                "relation_depth_evidence_status": target.get("relation_depth_evidence_status"),
                "relation_associated_heading_count": safe_int(target.get("relation_associated_heading_count"), 0),
                "relation_depth_consistent_count": safe_int(target.get("relation_depth_consistent_count"), 0),
                "companion_guard_branch": target.get("companion_guard_branch"),
                "companion_guard_present": target.get("companion_guard_present") is True,
                "companion_guard_role": target.get("companion_guard_role"),
                "recheck_view_count": view_count,
                "recheck_candidate_associated_view_count": associated_views,
                "recheck_detector_box_view_count": detector_box_views,
                "recheck_sam2_mask_view_count": sam2_mask_views,
                "recheck_unassociated_view_count": len(unassociated),
                "recheck_associated_heading_count": associated_headings,
                "recheck_projected_pixel_inside_mask_count": inside_mask,
                "recheck_depth_consistent_association_count": depth_consistent,
                "recheck_view_evidence_status_counts": compact_counter(row.get("view_evidence_status") for row in group),
                "unassociated_source_plan_indices": [row.get("source_plan_index") for row in unassociated],
                "own_view_support_status": status,
                "guard_interpretation_status": guard_status,
                "negative_missing_support_guard_ready": guard_status
                == "negative_missing_support_guard_ready_for_later_arbitration",
                "promotable_branch_outcome": False,
                "recommended_nonterminal_action": candidate_action(status),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def request_action(status_counts: Counter) -> str:
    if status_counts.get("candidate_own_view_support_partial", 0) or status_counts.get(
        "candidate_own_view_support_absent", 0
    ):
        return "audit_partial_own_view_support_before_terminal_utility"
    if status_counts.get("candidate_own_view_support_acquired", 0):
        return "keep_nonterminal_own_view_support_for_guard_arbitration_contract"
    return "defer_missing_own_view_recheck_unresolved"


def build_request_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rid, group in sorted(group_by_request(candidate_rows).items(), key=lambda item: request_sort_key(item[0])):
        group = sorted(group, key=lambda row: candidate_sort_key(str(row.get("target_candidate_id") or "")))
        first = group[0]
        status_counts = Counter(str(row.get("own_view_support_status")) for row in group)
        unassociated_frame_count = sum(safe_int(row.get("recheck_unassociated_view_count"), 0) for row in group)
        acquired = status_counts.get("candidate_own_view_support_acquired", 0)
        partial = status_counts.get("candidate_own_view_support_partial", 0)
        absent = status_counts.get("candidate_own_view_support_absent", 0)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_recheck_request_evidence",
                "row_type": "request_summary",
                "contract_name": "missing_own_view_recheck_evidence_v1",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": first.get("rival_identity_request_id") or rid,
                "episode_key": first.get("episode_key"),
                "scene_key": first.get("scene_key"),
                "scene_id": first.get("scene_id"),
                "query": first.get("query"),
                "target_candidate_count": len(group),
                "target_candidate_ids": [row.get("target_candidate_id") for row in group],
                "own_view_support_acquired_candidate_count": acquired,
                "partial_own_view_support_candidate_count": partial,
                "absent_own_view_support_candidate_count": absent,
                "unassociated_frame_count": unassociated_frame_count,
                "negative_missing_support_guard_ready_count": sum(
                    1 for row in group if row.get("negative_missing_support_guard_ready") is True
                ),
                "own_view_support_status_counts": dict(sorted(status_counts.items())),
                "promotable_branch_outcome_count": 0,
                "promotable_branch_outcome": False,
                "recommended_nonterminal_action": request_action(status_counts),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_unassociated_rows(view_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in view_rows:
        if row.get("has_candidate_association") is True:
            continue
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_recheck_unassociated_frame_audit",
                "row_type": "unassociated_frame_audit",
                "contract_name": "missing_own_view_recheck_evidence_v1",
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "target_candidate_id": row.get("target_candidate_id"),
                "decision_id": row.get("decision_id"),
                "source_plan_index": row.get("source_plan_index"),
                "source_viewpoint_id": row.get("source_viewpoint_id"),
                "detector_box_count": row.get("detector_box_count"),
                "sam2_mask_count": row.get("sam2_mask_count"),
                "projected_pixel_inside_mask_count": row.get("projected_pixel_inside_mask_count"),
                "candidate_associated_depth_consistent_count": row.get(
                    "candidate_associated_depth_consistent_count"
                ),
                "audit_reason": "detector_and_sam2_visible_but_candidate_unassociated",
                "recommended_nonterminal_action": "audit_unassociated_recheck_frame_without_candidate_rejection",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def requested_outputs(contract: Mapping[str, Any]) -> Dict[str, str]:
    outputs = contract.get("required_outputs") or {}
    return {
        "view_evidence_rows": str(outputs.get("view_evidence_rows", "missing_own_view_recheck_view_evidence_rows.jsonl")),
        "target_candidate_evidence_rows": str(outputs.get("target_candidate_evidence_rows", "missing_own_view_recheck_candidate_rows.jsonl")),
        "request_summary_rows": str(outputs.get("request_summary_rows", "missing_own_view_recheck_request_rows.jsonl")),
        "unassociated_frame_audit_rows": str(outputs.get("unassociated_frame_audit_rows", "missing_own_view_recheck_unassociated_frame_rows.jsonl")),
        "summary": str(outputs.get("summary", "missing_own_view_recheck_evidence_summary.json")),
    }


def simpler_alternatives(candidate_rows: Sequence[Mapping[str, Any]], request_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    acquired = sum(1 for row in candidate_rows if row.get("own_view_support_status") == "candidate_own_view_support_acquired")
    all_four = sum(
        1
        for row in candidate_rows
        if safe_int(row.get("recheck_candidate_associated_view_count"), 0)
        == safe_int(row.get("recheck_view_count"), 0)
    )
    any_assoc = sum(
        1 for row in candidate_rows if safe_int(row.get("recheck_candidate_associated_view_count"), 0) > 0
    )
    partial = sum(1 for row in candidate_rows if safe_int(row.get("recheck_unassociated_view_count"), 0) > 0)
    return {
        "defer_all_missing_own_view_rows": {
            "decision": "safe_but_inert",
            "candidate_evidence_rows_lost": len(candidate_rows),
            "request_rows_lost": len(request_rows),
        },
        "reject_missing_own_view_without_recheck": {
            "decision": "blocked_by_contract",
            "reason": "all candidates were actively re-observed before guard interpretation",
        },
        "reject_if_any_recheck_view_unassociated": {
            "decision": "rejected_as_terminal_rule",
            "would_reject_candidate_rows": partial,
            "reason": "single-view unassociation occurs with detector/SAM2 visibility and is an audit state, not invalidity",
        },
        "commit_if_any_recheck_view_associated": {
            "decision": "diagnostic_only",
            "eligible_candidate_rows": any_assoc,
            "reason": "any association measures evidence availability, not ObjectNav goal validity",
        },
        "commit_if_all_recheck_views_associated": {
            "decision": "diagnostic_only",
            "eligible_candidate_rows": all_four,
            "reason": "full own-view support still requires later label-free arbitration",
        },
        "support_acquired_gate": {
            "decision": "nonterminal_evidence_state_only",
            "eligible_candidate_rows": acquired,
            "reason": "the analyzer records acquired support but does not commit or reject candidates",
        },
    }


def build_summary(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    plan_summary: Mapping[str, Any],
    detector_summary: Mapping[str, Any],
    frame_rows: Sequence[Mapping[str, Any]],
    association_rows: Sequence[Mapping[str, Any]],
    view_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    unassociated_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    minimum = contract.get("minimum_evidence_gate") or {}
    action_rows = [
        *[dict(row) for row in view_rows],
        *[dict(row) for row in candidate_rows],
        *[dict(row) for row in request_rows],
        *[dict(row) for row in unassociated_rows],
    ]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    candidate_commit_rows = [row for row in action_rows if row.get("candidate_commit") is True]
    candidate_rejection_rows = [row for row in action_rows if row.get("candidate_rejection") is True]
    associated_frames = [row for row in view_rows if row.get("has_candidate_association") is True]
    associated_heading_count = sum(safe_int(row.get("associated_candidate_heading_count"), 0) for row in view_rows)
    inside_mask_count = sum(safe_int(row.get("projected_pixel_inside_mask_count"), 0) for row in view_rows)
    candidate_with_any = sum(
        1 for row in candidate_rows if safe_int(row.get("recheck_candidate_associated_view_count"), 0) > 0
    )
    candidate_with_three = sum(
        1 for row in candidate_rows if safe_int(row.get("recheck_candidate_associated_view_count"), 0) >= 3
    )
    candidate_status_counts = Counter(str(row.get("own_view_support_status")) for row in candidate_rows)
    detector_gate = detector_summary.get("gate") or {}
    plan_gate = plan_summary.get("gate") or {}
    actual_uses_gt_for_action = any(row.get("uses_gt_for_action") is True for row in action_rows)
    gate = {
        "input_materializer_gate_passed": bool(plan_gate.get("input_materializer_gate_passed")) is bool(minimum.get("input_materializer_gate_passed", True)),
        "observation_plan_gate_passed": bool(plan_gate.get("missing_own_view_observation_plan_gate_passed")) is bool(minimum.get("observation_plan_gate_passed", True)),
        "detector_substrate_gate_passed": bool(detector_gate.get("passes_detector_substrate_gate")) is bool(minimum.get("detector_substrate_gate_passed", True)),
        "expected_request_rows_passed": len(request_rows) == safe_int(minimum.get("expected_request_rows"), -1),
        "expected_target_candidate_rows_passed": len(candidate_rows) == safe_int(minimum.get("expected_target_candidate_rows"), -1),
        "expected_plan_rows_passed": len(frame_rows) == safe_int(minimum.get("expected_plan_rows"), -1),
        "expected_detector_rows_passed": safe_int(detector_summary.get("detector_rows"), -1) == safe_int(minimum.get("expected_detector_rows"), -1),
        "expected_view_evidence_rows_passed": len(view_rows) == safe_int(minimum.get("expected_view_evidence_rows"), -1),
        "expected_target_candidate_evidence_rows_passed": len(candidate_rows) == safe_int(minimum.get("expected_target_candidate_evidence_rows"), -1),
        "expected_request_summary_rows_passed": len(request_rows) == safe_int(minimum.get("expected_request_summary_rows"), -1),
        "expected_unassociated_frame_audit_rows_passed": len(unassociated_rows) == safe_int(minimum.get("expected_unassociated_frame_audit_rows"), -1),
        "minimum_rows_with_candidate_association_passed": len(associated_frames) >= safe_int(minimum.get("minimum_rows_with_candidate_association"), 0),
        "minimum_candidate_association_rate_passed": (len(associated_frames) / len(view_rows) if view_rows else 0.0) >= safe_float(minimum.get("minimum_candidate_association_rate"), 0.0),
        "minimum_target_candidates_with_any_association_passed": candidate_with_any >= safe_int(minimum.get("minimum_target_candidates_with_any_association"), 0),
        "minimum_target_candidates_with_at_least_three_associated_views_passed": candidate_with_three >= safe_int(minimum.get("minimum_target_candidates_with_at_least_three_associated_views"), 0),
        "minimum_associated_candidate_heading_count_passed": associated_heading_count >= safe_int(minimum.get("minimum_associated_candidate_heading_count"), 0),
        "minimum_projected_pixel_inside_mask_count_passed": inside_mask_count >= safe_int(minimum.get("minimum_projected_pixel_inside_mask_count"), 0),
        "unassociated_frame_rows_explicitly_audited_passed": bool(unassociated_rows) is bool(minimum.get("unassociated_frame_rows_explicitly_audited", True)),
        "action_evidence_forbidden_key_gate_passed": len(forbidden) <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(minimum.get("terminal_commit_rows_maximum"), 0),
        "candidate_commit_rows_passed": len(candidate_commit_rows) <= safe_int(minimum.get("candidate_commit_rows_maximum"), 0),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows) <= safe_int(minimum.get("candidate_rejection_rows_maximum"), 0),
        "uses_gt_for_action_passed": (not actual_uses_gt_for_action) and detector_summary.get("uses_gt_for_action") is False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["missing_own_view_recheck_evidence_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key not in {"terminal_utility_validation_allowed", "paper_claim_allowed"}
    )
    if candidate_status_counts.get("candidate_own_view_support_partial", 0) or candidate_status_counts.get(
        "candidate_own_view_support_absent", 0
    ):
        recommended = "inspect_partial_missing_own_view_support_before_guard_arbitration"
        reason = "some candidates still have partial or absent own-view support after recheck"
    else:
        recommended = "design_missing_own_view_guard_arbitration_contract"
        reason = "all target candidates have acquired own-view support state, but goal validity remains unresolved"
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source": {
            "plan_summary": str(args.plan_summary),
            "detector_summary": str(args.detector_summary),
            "detector_frame_summary": str(args.detector_frame_summary),
            "detector_associations": str(args.detector_associations),
        },
        "view_evidence_rows": len(view_rows),
        "target_candidate_evidence_rows": len(candidate_rows),
        "request_summary_rows": len(request_rows),
        "unassociated_frame_audit_rows": len(unassociated_rows),
        "detector_rows": detector_summary.get("detector_rows"),
        "association_rows": len(association_rows),
        "rows_with_candidate_association": len(associated_frames),
        "candidate_association_rate": len(associated_frames) / len(view_rows) if view_rows else None,
        "target_candidates_with_any_association": candidate_with_any,
        "target_candidates_with_at_least_three_associated_views": candidate_with_three,
        "target_candidates_with_full_4_of_4_association": sum(
            1
            for row in candidate_rows
            if safe_int(row.get("recheck_candidate_associated_view_count"), 0)
            == safe_int(row.get("recheck_view_count"), 0)
        ),
        "target_candidates_with_partial_3_of_4_association": sum(
            1 for row in candidate_rows if safe_int(row.get("recheck_candidate_associated_view_count"), 0) == 3
        ),
        "target_candidates_with_zero_association": sum(
            1 for row in candidate_rows if safe_int(row.get("recheck_candidate_associated_view_count"), 0) == 0
        ),
        "associated_candidate_heading_count": associated_heading_count,
        "projected_pixel_inside_mask_count": inside_mask_count,
        "candidate_status_counts": dict(sorted(candidate_status_counts.items())),
        "candidate_nonterminal_action_counts": compact_counter(
            row.get("recommended_nonterminal_action") for row in candidate_rows
        ),
        "request_nonterminal_action_counts": compact_counter(
            row.get("recommended_nonterminal_action") for row in request_rows
        ),
        "query_candidate_status_counts": {
            query: dict(sorted(Counter(str(row.get("own_view_support_status")) for row in rows).items()))
            for query, rows in sorted(group_by_query(candidate_rows).items())
        },
        "request_profiles": {
            row_request_id(row): {
                "target_candidate_count": row.get("target_candidate_count"),
                "own_view_support_acquired_candidate_count": row.get("own_view_support_acquired_candidate_count"),
                "partial_own_view_support_candidate_count": row.get("partial_own_view_support_candidate_count"),
                "unassociated_frame_count": row.get("unassociated_frame_count"),
                "negative_missing_support_guard_ready_count": row.get("negative_missing_support_guard_ready_count"),
                "recommended_nonterminal_action": row.get("recommended_nonterminal_action"),
            }
            for row in request_rows
        },
        "unassociated_frame_rows": [
            {
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "target_candidate_id": row.get("target_candidate_id"),
                "source_plan_index": row.get("source_plan_index"),
            }
            for row in unassociated_rows
        ],
        "simpler_alternatives": simpler_alternatives(candidate_rows, request_rows),
        "diagnostic_conclusion": {
            "missing_own_view_recheck_signal_ready": gate["missing_own_view_recheck_evidence_gate_passed"],
            "recommended_next_action": recommended,
            "reason": reason,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            key: str(Path(str(args.out_root)) / value)
            for key, value in requested_outputs(contract).items()
        },
        "interpretation": {
            "fact": "The analyzer aggregates candidate-centered own-view recheck detector/SAM2 evidence before any evaluation-label join.",
            "agent_inference": "Missing own-view uncertainty has been converted into explicit support state, but acquired support is not ObjectNav goal validity.",
            "paper_claim": "No paper claim is allowed from this analyzer alone.",
        },
    }


def group_by_query(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("query") or "")].append(row)
    return grouped


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    args.plan_summary = source_path(args, contract, "plan_summary", "plan_summary")
    args.target_candidate_rows = source_path(args, contract, "target_candidate_rows", "target_candidate_rows")
    args.detector_summary = source_path(args, contract, "detector_summary", "detector_substrate_summary")
    args.detector_frame_summary = source_path(args, contract, "detector_frame_summary", "detector_frame_summary")
    args.detector_associations = source_path(args, contract, "detector_associations", "detector_associations")

    plan_summary = load_json(args.plan_summary)
    detector_summary = load_json(args.detector_summary)
    target_rows = load_jsonl(args.target_candidate_rows)
    frame_rows = load_jsonl(args.detector_frame_summary)
    association_rows = load_jsonl(args.detector_associations)

    associations_by_decision = group_by_decision(association_rows)
    view_rows = build_view_rows(frame_rows, associations_by_decision)
    candidate_rows = build_candidate_rows(view_rows, target_rows)
    request_rows = build_request_rows(candidate_rows)
    unassociated_rows = build_unassociated_rows(view_rows)
    summary = build_summary(
        args=args,
        contract=contract,
        plan_summary=plan_summary,
        detector_summary=detector_summary,
        frame_rows=frame_rows,
        association_rows=association_rows,
        view_rows=view_rows,
        candidate_rows=candidate_rows,
        request_rows=request_rows,
        unassociated_rows=unassociated_rows,
    )

    out_root = Path(args.out_root)
    outputs = requested_outputs(contract)
    write_jsonl(out_root / outputs["view_evidence_rows"], view_rows)
    write_jsonl(out_root / outputs["target_candidate_evidence_rows"], candidate_rows)
    write_jsonl(out_root / outputs["request_summary_rows"], request_rows)
    write_jsonl(out_root / outputs["unassociated_frame_audit_rows"], unassociated_rows)
    write_json(out_root / outputs["summary"], summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate missing-own-view recheck detector evidence without terminal commits."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--plan-summary")
    parser.add_argument("--target-candidate-rows")
    parser.add_argument("--detector-summary")
    parser.add_argument("--detector-frame-summary")
    parser.add_argument("--detector-associations")
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["missing_own_view_recheck_evidence_gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
