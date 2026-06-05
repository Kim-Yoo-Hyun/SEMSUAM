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


SCHEMA_VERSION = "h001.instance_arbitration_detector_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_instance_arbitration_detector_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_instance_arbitration_detector_evidence_v1"

REQUIRED_ROLES = (
    "candidate_own_view_refresh",
    "source_top_contrast_view",
    "local_context_contrast_view",
    "pair_common_view_or_dual_standoff",
)


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def row_request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def row_decision_id(row: Mapping[str, Any]) -> str:
    return str(row.get("decision_id") or "")


def row_candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def selected_candidate_ids(row: Mapping[str, Any]) -> List[str]:
    value = row.get("selected_candidate_ids")
    if not isinstance(value, list):
        value = row.get("candidate_ids")
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def candidate_sort_key(candidate_id: Any) -> Tuple[str, int, str]:
    text = str(candidate_id or "")
    head, _, tail = text.rpartition(":")
    return head, safe_int(tail, 999999), text


def role_sort_key(role: Any) -> Tuple[int, str]:
    text = str(role or "")
    try:
        return REQUIRED_ROLES.index(text), text
    except ValueError:
        return len(REQUIRED_ROLES), text


def group_by_decision(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_decision_id(row)].append(dict(row))
    return grouped


def group_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    return grouped


def group_by_candidate(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for candidate_id in selected_candidate_ids(row):
            grouped[(row_request_id(row), candidate_id)].append(dict(row))
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
    depth_mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    box_scores = [safe_float(row.get("best_box_score")) for row in rows]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
    depth_agreements = [safe_float(row.get("depth_agreement_m")) for row in rows]
    return {
        "association_rows": len(rows),
        "associated_heading_count": len(associated),
        "visible_count": len(visible),
        "projected_inside_box_count": len(inside_box),
        "projected_inside_mask_count": len(inside_mask),
        "depth_consistent_count": len(depth_consistent),
        "depth_mismatch_count": len(depth_mismatch),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in rows),
        "projection_anchor_offset_counts": compact_counter(
            row.get("projection_anchor_height_offset_m") for row in rows
        ),
        "best_box_score_max": max([score for score in box_scores if score is not None], default=None),
        "best_box_score_mean": mean(box_scores),
        "depth_error_stats_m": finite_stats(depth_errors),
        "depth_agreement_stats_m": finite_stats(depth_agreements),
    }


def per_candidate_stats(
    selected_ids: Sequence[str],
    association_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    by_candidate: Dict[str, List[Mapping[str, Any]]] = {candidate_id: [] for candidate_id in selected_ids}
    for row in association_rows:
        candidate_id = str(row.get("candidate_id") or "")
        if candidate_id in by_candidate:
            by_candidate[candidate_id].append(row)
    return {candidate_id: association_stats(rows) for candidate_id, rows in by_candidate.items()}


def view_status(target_support: bool, rival_support: bool, has_detector: bool) -> str:
    if target_support and rival_support:
        return "target_and_rival_support"
    if target_support:
        return "target_only_support"
    if rival_support:
        return "rival_only_support"
    if has_detector:
        return "detector_visible_no_candidate_support"
    return "detector_absent"


def build_view_rows(
    frame_rows: Sequence[Dict[str, Any]],
    associations_by_decision: Mapping[str, Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for frame in sorted(
        frame_rows,
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            role_sort_key(row.get("view_role")),
            candidate_sort_key(row_candidate_id(row)),
            row_decision_id(row),
        ),
    ):
        decision_rows = list(associations_by_decision.get(row_decision_id(frame), []))
        selected_ids = selected_candidate_ids(frame)
        target_id = row_candidate_id(frame)
        non_target_ids = [candidate_id for candidate_id in selected_ids if candidate_id != target_id]
        candidate_stats = per_candidate_stats(selected_ids, decision_rows)
        target_stats = candidate_stats.get(target_id, association_stats([]))
        non_target_associated = sum(
            safe_int(candidate_stats.get(candidate_id, {}).get("associated_heading_count"), 0)
            for candidate_id in non_target_ids
        )
        non_target_inside_mask = sum(
            safe_int(candidate_stats.get(candidate_id, {}).get("projected_inside_mask_count"), 0)
            for candidate_id in non_target_ids
        )
        non_target_depth_consistent = sum(
            safe_int(candidate_stats.get(candidate_id, {}).get("depth_consistent_count"), 0)
            for candidate_id in non_target_ids
        )
        target_support = safe_int(target_stats.get("associated_heading_count"), 0) > 0
        rival_support = non_target_associated > 0
        role = str(frame.get("view_role") or "")
        status = view_status(
            target_support,
            rival_support,
            frame.get("has_detector_box") is True or frame.get("has_sam2_mask") is True,
        )
        support_by_candidate = {
            candidate_id: safe_int(stats.get("associated_heading_count"), 0) > 0
            for candidate_id, stats in candidate_stats.items()
        }
        associated_heading_by_candidate = {
            candidate_id: safe_int(stats.get("associated_heading_count"), 0)
            for candidate_id, stats in candidate_stats.items()
        }
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "view_evidence",
                "contract_name": "instance_arbitration_detector_evidence_v1",
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
                "target_candidate_id": target_id,
                "selected_candidate_ids": selected_ids,
                "selected_candidate_count": len(selected_ids),
                "candidate_selection_source": frame.get("candidate_selection_source"),
                "view_role": role,
                "pair_probe_type": frame.get("pair_probe_type"),
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
                "target_associated_heading_count": target_stats.get("associated_heading_count", 0),
                "non_target_associated_heading_count": non_target_associated,
                "target_projected_inside_mask_count": target_stats.get("projected_inside_mask_count", 0),
                "non_target_projected_inside_mask_count": non_target_inside_mask,
                "target_depth_consistent_count": target_stats.get("depth_consistent_count", 0),
                "non_target_depth_consistent_count": non_target_depth_consistent,
                "support_by_candidate": support_by_candidate,
                "associated_heading_by_candidate": associated_heading_by_candidate,
                "target_support": target_support,
                "rival_support": rival_support,
                "target_only_support": target_support and not rival_support,
                "rival_leakage": rival_support,
                "view_evidence_status": status,
                "candidate_stats": candidate_stats,
                "recommended_nonterminal_action": "aggregate_instance_arbitration_candidate_and_pair_evidence",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def candidate_source_flags(row: Mapping[str, Any]) -> Dict[str, bool]:
    return {
        "source_top_candidate": row.get("source_top_candidate") is True,
        "strong_own_view_candidate": row.get("strong_own_view_candidate") is True,
        "detector_strong_candidate": row.get("detector_strong_candidate") is True,
        "local_context_candidate": row.get("local_context_candidate") is True,
    }


def candidate_status(
    own_view_support: bool,
    contrast_support: bool,
    pair_support_count: int,
    pair_contradiction_count: int,
    rival_leakage_count: int,
) -> str:
    if own_view_support and contrast_support and pair_support_count > 0 and pair_contradiction_count == 0 and rival_leakage_count == 0:
        return "candidate_specific_instance_support"
    if pair_contradiction_count > 0:
        return "contradicted_by_pair_or_contrast_evidence"
    if rival_leakage_count > 0:
        return "ambiguous_rival_leakage_candidate"
    if own_view_support or contrast_support or pair_support_count > 0:
        return "partial_instance_support"
    return "insufficient_instance_evidence"


def build_candidate_rows(
    source_candidate_rows: Sequence[Mapping[str, Any]],
    view_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    views_by_candidate = group_by_candidate(view_rows)
    output: List[Dict[str, Any]] = []
    for source in sorted(
        source_candidate_rows,
        key=lambda row: (request_sort_key(row_request_id(row)), candidate_sort_key(row_candidate_id(row))),
    ):
        rid = row_request_id(source)
        cid = row_candidate_id(source)
        views = views_by_candidate.get((rid, cid), [])
        own_views = [row for row in views if str(row.get("view_role")) == "candidate_own_view_refresh"]
        source_views = [row for row in views if str(row.get("view_role")) == "source_top_contrast_view"]
        local_views = [row for row in views if str(row.get("view_role")) == "local_context_contrast_view"]
        pair_views = [row for row in views if str(row.get("view_role")) == "pair_common_view_or_dual_standoff"]

        def support_in(row: Mapping[str, Any]) -> bool:
            return bool((row.get("support_by_candidate") or {}).get(cid))

        def rival_support_in(row: Mapping[str, Any]) -> bool:
            support = row.get("support_by_candidate") or {}
            return any(bool(value) for candidate_id, value in support.items() if str(candidate_id) != cid)

        own_view_support = any(support_in(row) for row in own_views)
        source_top_contrast_support = any(support_in(row) for row in source_views)
        local_context_contrast_support = any(support_in(row) for row in local_views)
        pair_support_count = sum(1 for row in pair_views if support_in(row) and not rival_support_in(row))
        pair_both_support_count = sum(1 for row in pair_views if support_in(row) and rival_support_in(row))
        pair_no_support_count = sum(
            1 for row in pair_views if not support_in(row) and not rival_support_in(row)
        )
        pair_contradiction_count = sum(1 for row in pair_views if not support_in(row) and rival_support_in(row))
        rival_leakage_count = sum(
            1
            for row in views
            if (
                (str(row.get("target_candidate_id")) == cid and rival_support_in(row))
                or (str(row.get("target_candidate_id")) != cid and support_in(row))
            )
        )
        contrast_support = source_top_contrast_support or local_context_contrast_support
        status = candidate_status(
            own_view_support=own_view_support,
            contrast_support=contrast_support,
            pair_support_count=pair_support_count,
            pair_contradiction_count=pair_contradiction_count,
            rival_leakage_count=rival_leakage_count,
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "candidate_evidence",
                "contract_name": "instance_arbitration_detector_evidence_v1",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": source.get("rival_identity_request_id") or rid,
                "episode_key": source.get("episode_key"),
                "scene_key": source.get("scene_key"),
                "scene_id": source.get("scene_id"),
                "query": source.get("query"),
                "request_index": source.get("request_index"),
                "target_candidate_id": cid,
                "candidate_id": cid,
                "candidate_index": source.get("candidate_index"),
                "semantic_rank": source.get("semantic_rank"),
                "semantic_score": source.get("semantic_score"),
                "support_score": source.get("support_score"),
                "detector_evidence_score": source.get("detector_evidence_score"),
                **candidate_source_flags(source),
                "own_view_support": own_view_support,
                "source_top_contrast_support": source_top_contrast_support,
                "local_context_contrast_support": local_context_contrast_support,
                "pair_support_count": pair_support_count,
                "pair_both_support_count": pair_both_support_count,
                "pair_no_support_count": pair_no_support_count,
                "pair_contradiction_count": pair_contradiction_count,
                "rival_leakage_count": rival_leakage_count,
                "view_evidence_count": len(views),
                "candidate_evidence_status": status,
                "candidate_specific_instance_support": status == "candidate_specific_instance_support",
                "recommended_nonterminal_action": (
                    "keep_instance_arbitration_candidate_as_nonterminal_evidence"
                    if status == "candidate_specific_instance_support"
                    else "keep_instance_arbitration_candidate_unresolved"
                ),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def pair_key(row: Mapping[str, Any]) -> Tuple[str, str, str]:
    a = str(row.get("candidate_id_a") or "")
    b = str(row.get("candidate_id_b") or "")
    first, second = sorted([a, b], key=candidate_sort_key)
    return row_request_id(row), first, second


def view_pair_key(row: Mapping[str, Any]) -> Optional[Tuple[str, str, str]]:
    ids = selected_candidate_ids(row)
    if len(ids) != 2:
        return None
    first, second = sorted(ids, key=candidate_sort_key)
    return row_request_id(row), first, second


def pair_status(a_support: bool, b_support: bool) -> str:
    if a_support and b_support:
        return "ambiguous_both_candidates_supported"
    if a_support:
        return "resolved_in_favor_of_candidate_a_nonterminal"
    if b_support:
        return "resolved_in_favor_of_candidate_b_nonterminal"
    return "ambiguous_no_candidate_support"


def build_pair_rows(
    source_pair_rows: Sequence[Mapping[str, Any]],
    view_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    views_by_pair: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in view_rows:
        key = view_pair_key(row)
        if key is not None:
            views_by_pair[key].append(row)

    output: List[Dict[str, Any]] = []
    for source in sorted(
        source_pair_rows,
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            candidate_sort_key(row.get("candidate_id_a")),
            candidate_sort_key(row.get("candidate_id_b")),
        ),
    ):
        rid, a, b = pair_key(source)
        views = views_by_pair.get((rid, a, b), [])
        a_support = sum(1 for row in views if bool((row.get("support_by_candidate") or {}).get(a)))
        b_support = sum(1 for row in views if bool((row.get("support_by_candidate") or {}).get(b)))
        a_leakage = sum(
            1
            for row in views
            if str(row.get("target_candidate_id")) != a and bool((row.get("support_by_candidate") or {}).get(a))
        )
        b_leakage = sum(
            1
            for row in views
            if str(row.get("target_candidate_id")) != b and bool((row.get("support_by_candidate") or {}).get(b))
        )
        status = pair_status(a_support > 0, b_support > 0)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "pair_evidence",
                "contract_name": "instance_arbitration_detector_evidence_v1",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": source.get("rival_identity_request_id") or rid,
                "episode_key": source.get("episode_key"),
                "scene_key": source.get("scene_key"),
                "scene_id": source.get("scene_id"),
                "query": source.get("query"),
                "request_index": source.get("request_index"),
                "pair_index": source.get("pair_index"),
                "request_pair_index": source.get("request_pair_index"),
                "candidate_id_a": a,
                "candidate_id_b": b,
                "candidate_a_roles": source.get("candidate_a_roles"),
                "candidate_b_roles": source.get("candidate_b_roles"),
                "candidate_a_semantic_rank": source.get("candidate_a_semantic_rank"),
                "candidate_b_semantic_rank": source.get("candidate_b_semantic_rank"),
                "pair_distance_m": source.get("pair_distance_m"),
                "pair_probe_type": (views[0].get("pair_probe_type") if views else None),
                "view_evidence_count": len(views),
                "candidate_a_support_count": a_support,
                "candidate_b_support_count": b_support,
                "candidate_a_leakage_count": a_leakage,
                "candidate_b_leakage_count": b_leakage,
                "pair_evidence_status": status,
                "pair_resolved_nonterminal": status.startswith("resolved_in_favor"),
                "recommended_nonterminal_action": "aggregate_request_instance_arbitration_evidence",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_request_rows(
    source_request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    candidates_by_request = group_by_request(candidate_rows)
    pairs_by_request = group_by_request(pair_rows)
    output: List[Dict[str, Any]] = []
    for source in sorted(source_request_rows, key=lambda row: request_sort_key(row_request_id(row))):
        rid = row_request_id(source)
        candidates = candidates_by_request.get(rid, [])
        pairs = pairs_by_request.get(rid, [])
        supported = [
            row
            for row in candidates
            if row.get("candidate_evidence_status") == "candidate_specific_instance_support"
        ]
        contradicted = [
            row
            for row in candidates
            if row.get("candidate_evidence_status") == "contradicted_by_pair_or_contrast_evidence"
        ]
        ambiguous = [
            row
            for row in candidates
            if row.get("candidate_evidence_status")
            in {"ambiguous_rival_leakage_candidate", "partial_instance_support", "insufficient_instance_evidence"}
        ]
        unresolved_pairs = [row for row in pairs if not row.get("pair_resolved_nonterminal")]
        promotable = len(supported) == 1 and not unresolved_pairs and not contradicted
        if promotable:
            action = "candidate_specific_instance_support_ready_for_terminal_utility_contract"
        else:
            action = "diagnose_instance_arbitration_residual_evidence"
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "request_evidence",
                "contract_name": "instance_arbitration_detector_evidence_v1",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": source.get("rival_identity_request_id") or rid,
                "episode_key": source.get("episode_key"),
                "scene_key": source.get("scene_key"),
                "scene_id": source.get("scene_id"),
                "query": source.get("query"),
                "request_index": source.get("request_index"),
                "candidate_count": len(candidates),
                "pair_count": len(pairs),
                "supported_candidate_count": len(supported),
                "contradicted_candidate_count": len(contradicted),
                "ambiguous_candidate_count": len(ambiguous),
                "unresolved_pair_count": len(unresolved_pairs),
                "promotable_branch_outcome": promotable,
                "promotable_branch_outcome_count": int(promotable),
                "recommended_nonterminal_action": action,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_unresolved_rows(
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    candidates_by_request = group_by_request(candidate_rows)
    pairs_by_request = group_by_request(pair_rows)
    rows: List[Dict[str, Any]] = []
    for request in request_rows:
        if request.get("promotable_branch_outcome") is True:
            continue
        rid = row_request_id(request)
        candidate_status_counts = compact_counter(
            row.get("candidate_evidence_status") for row in candidates_by_request.get(rid, [])
        )
        pair_status_counts = compact_counter(row.get("pair_evidence_status") for row in pairs_by_request.get(rid, []))
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "unresolved_case",
                "contract_name": "instance_arbitration_detector_evidence_v1",
                "expanded_retrieval_request_id": rid,
                "scene_key": request.get("scene_key"),
                "scene_id": request.get("scene_id"),
                "query": request.get("query"),
                "candidate_status_counts": candidate_status_counts,
                "pair_status_counts": pair_status_counts,
                "unresolved_reason": "no_unique_candidate_specific_support_with_all_pairs_resolved",
                "recommended_nonterminal_action": "diagnose_instance_arbitration_residual_evidence",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def output_path(default_out_root: Path, value: str) -> Path:
    path = Path(str(value))
    if str(path).startswith(str(default_out_root)):
        return path
    return default_out_root / path.name


def output_paths(contract: Mapping[str, Any], out_root: Path) -> Dict[str, Path]:
    outputs = contract.get("expected_outputs") or {}
    return {key: output_path(out_root, str(value)) for key, value in outputs.items()}


def gate_summary(
    contract: Mapping[str, Any],
    detector_summary: Mapping[str, Any],
    frame_rows: Sequence[Mapping[str, Any]],
    association_rows: Sequence[Mapping[str, Any]],
    view_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    unresolved_rows: Sequence[Mapping[str, Any]],
    forbidden: Sequence[str],
) -> Dict[str, bool]:
    gates = contract.get("required_gates") or {}
    action_rows = [*view_rows, *candidate_rows, *pair_rows, *request_rows, *unresolved_rows]
    selected_count = Counter(len(selected_candidate_ids(row)) for row in frame_rows)
    detector_gate = detector_summary.get("gate") or {}
    result = {
        "source_materializer_planner_gate_passed": bool(gates.get("source_materializer_planner_gate_passed")),
        "source_frame_projection_gate_passed": bool(gates.get("source_frame_projection_gate_passed")),
        "source_detector_substrate_gate_passed": bool(detector_gate.get("passes_detector_substrate_gate")),
        "expected_view_evidence_rows_passed": len(view_rows) == safe_int(gates.get("expected_view_evidence_rows"), -1),
        "expected_candidate_evidence_rows_passed": len(candidate_rows) == safe_int(gates.get("expected_candidate_evidence_rows"), -1),
        "expected_pair_evidence_rows_passed": len(pair_rows) == safe_int(gates.get("expected_pair_evidence_rows"), -1),
        "expected_request_evidence_rows_passed": len(request_rows) == safe_int(gates.get("expected_request_evidence_rows"), -1),
        "minimum_detector_association_rows_passed": len(association_rows) >= safe_int(gates.get("minimum_detector_association_rows"), 0),
        "minimum_candidate_association_rate_passed": safe_float(detector_summary.get("candidate_association_rate"), 0.0) >= safe_float(gates.get("minimum_candidate_association_rate"), 0.0),
        "minimum_rows_with_candidate_association_passed": safe_int(detector_summary.get("rows_with_candidate_association"), 0) >= safe_int(gates.get("minimum_rows_with_candidate_association"), 0),
        "minimum_associated_candidate_heading_count_passed": safe_int(detector_summary.get("associated_candidate_heading_count"), 0) >= safe_int(gates.get("minimum_associated_candidate_heading_count"), 0),
        "all_candidate_views_have_one_selected_candidate_passed": selected_count.get(1, 0) == 51,
        "all_pair_views_have_two_selected_candidates_passed": selected_count.get(2, 0) == 121,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == safe_int(gates.get("action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": sum(1 for row in action_rows if row.get("terminal_commit") is True) == safe_int(gates.get("terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": sum(1 for row in action_rows if row.get("candidate_commit") is True) == safe_int(gates.get("candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": sum(1 for row in action_rows if row.get("candidate_rejection") is True) == safe_int(gates.get("candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": not any(row.get("uses_gt_for_action") is True for row in action_rows) and detector_summary.get("uses_gt_for_action") is False,
        "terminal_utility_validation_allowed_passed": not any(row.get("terminal_utility_validation_allowed") is True for row in action_rows),
        "paper_claim_allowed_passed": not any(row.get("paper_claim_allowed") is True for row in action_rows) and contract.get("paper_claim_allowed") is False,
    }
    result["instance_arbitration_detector_evidence_gate_passed"] = all(result.values())
    return result


def build_summary(
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    detector_summary: Mapping[str, Any],
    frame_rows: Sequence[Mapping[str, Any]],
    association_rows: Sequence[Mapping[str, Any]],
    view_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    unresolved_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    action_rows: List[Mapping[str, Any]] = [*view_rows, *candidate_rows, *pair_rows, *request_rows, *unresolved_rows]
    forbidden = action_forbidden_keys([dict(row) for row in action_rows])
    gate = gate_summary(
        contract,
        detector_summary,
        frame_rows,
        association_rows,
        view_rows,
        candidate_rows,
        pair_rows,
        request_rows,
        unresolved_rows,
        forbidden,
    )
    candidate_status_counts = compact_counter(row.get("candidate_evidence_status") for row in candidate_rows)
    pair_status_counts = compact_counter(row.get("pair_evidence_status") for row in pair_rows)
    request_action_counts = compact_counter(row.get("recommended_nonterminal_action") for row in request_rows)
    promotable_rows = [row for row in request_rows if row.get("promotable_branch_outcome") is True]
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-02",
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source": {
            "request_rows": str(args.request_rows),
            "candidate_rows": str(args.candidate_rows),
            "pair_rows": str(args.pair_rows),
            "detector_summary": str(args.detector_summary),
            "detector_frame_summary": str(args.detector_frame_summary),
            "detector_associations": str(args.detector_associations),
        },
        "view_evidence_rows": len(view_rows),
        "candidate_evidence_rows": len(candidate_rows),
        "pair_evidence_rows": len(pair_rows),
        "request_evidence_rows": len(request_rows),
        "unresolved_case_rows": len(unresolved_rows),
        "detector_frame_rows": len(frame_rows),
        "detector_association_rows": len(association_rows),
        "detector_box_rate": detector_summary.get("detector_box_rate"),
        "sam2_mask_rate": detector_summary.get("sam2_mask_rate"),
        "candidate_association_rate": detector_summary.get("candidate_association_rate"),
        "rows_with_candidate_association": detector_summary.get("rows_with_candidate_association"),
        "associated_candidate_heading_count": detector_summary.get("associated_candidate_heading_count"),
        "view_role_counts": compact_counter(row.get("view_role") for row in view_rows),
        "selected_candidate_count_rows": compact_counter(len(selected_candidate_ids(row)) for row in frame_rows),
        "frame_has_candidate_association_by_role": {
            role: f"{sum(1 for row in rows if row.get('has_candidate_association') is True)}/{len(rows)}"
            for role, rows in group_by_role(frame_rows).items()
        },
        "candidate_evidence_status_counts": candidate_status_counts,
        "pair_evidence_status_counts": pair_status_counts,
        "request_recommended_action_counts": request_action_counts,
        "promotable_branch_outcome_rows": len(promotable_rows),
        "promotable_branch_outcome_request_ids": [row.get("expanded_retrieval_request_id") for row in promotable_rows],
        "unresolved_request_ids": [row.get("expanded_retrieval_request_id") for row in unresolved_rows],
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": sum(1 for row in action_rows if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in action_rows if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in action_rows if row.get("candidate_rejection") is True),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in action_rows),
        "uses_gt_for_analysis": any(row.get("uses_gt_for_analysis") is True for row in action_rows),
        "terminal_utility_validation_allowed": any(
            row.get("terminal_utility_validation_allowed") is True for row in action_rows
        ),
        "paper_claim_allowed": any(row.get("paper_claim_allowed") is True for row in action_rows),
        "gate": gate,
        "next_allowed_task": (
            "design_terminal_utility_contract_only_if_promotable_branch_outcome_is_accepted"
            if promotable_rows
            else "diagnose_instance_arbitration_residual_evidence"
        ),
        "interpretation": {
            "fact": "The analyzer aggregates nonterminal instance-arbitration detector/SAM2 evidence before any evaluation-label join.",
            "agent_inference": "Repeated-instance ambiguity remains a branch-level uncertainty state unless one candidate has unique support and all pair contexts resolve without shortcut evidence.",
            "paper_claim": "No paper claim is allowed from this analyzer alone.",
        },
    }


def group_by_role(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("view_role") or "")].append(row)
    return dict(sorted(grouped.items(), key=lambda item: role_sort_key(item[0])))


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    args.request_rows = source_path(args, contract, "request_rows", "request_rows")
    args.candidate_rows = source_path(args, contract, "candidate_rows", "candidate_rows")
    args.pair_rows = source_path(args, contract, "pair_rows", "pair_rows")
    args.detector_summary = source_path(args, contract, "detector_summary", "detector_summary")
    args.detector_frame_summary = source_path(args, contract, "detector_frame_summary", "detector_frame_summary")
    args.detector_associations = source_path(args, contract, "detector_associations", "detector_associations")

    source_request_rows = load_jsonl(args.request_rows)
    source_candidate_rows = load_jsonl(args.candidate_rows)
    source_pair_rows = load_jsonl(args.pair_rows)
    detector_summary = load_json(args.detector_summary)
    frame_rows = load_jsonl(args.detector_frame_summary)
    association_rows = load_jsonl(args.detector_associations)

    associations_by_decision = group_by_decision(association_rows)
    view_rows = build_view_rows(frame_rows, associations_by_decision)
    candidate_rows = build_candidate_rows(source_candidate_rows, view_rows)
    pair_rows = build_pair_rows(source_pair_rows, view_rows)
    request_rows = build_request_rows(source_request_rows, candidate_rows, pair_rows)
    unresolved_rows = build_unresolved_rows(request_rows, candidate_rows, pair_rows)
    summary = build_summary(
        args,
        contract,
        detector_summary,
        frame_rows,
        association_rows,
        view_rows,
        candidate_rows,
        pair_rows,
        request_rows,
        unresolved_rows,
    )

    outputs = output_paths(contract, Path(str(args.out_root)))
    write_jsonl(outputs["view_evidence_jsonl"], view_rows)
    write_jsonl(outputs["candidate_evidence_jsonl"], candidate_rows)
    write_jsonl(outputs["pair_evidence_jsonl"], pair_rows)
    write_jsonl(outputs["request_evidence_jsonl"], request_rows)
    write_jsonl(outputs["unresolved_case_jsonl"], unresolved_rows)
    write_json(outputs["summary_json"], summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate instance-arbitration detector evidence without terminal commits."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--request-rows")
    parser.add_argument("--candidate-rows")
    parser.add_argument("--pair-rows")
    parser.add_argument("--detector-summary")
    parser.add_argument("--detector-frame-summary")
    parser.add_argument("--detector-associations")
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(
        json.dumps(
            {
                "gate": summary["gate"]["instance_arbitration_detector_evidence_gate_passed"],
                "view_rows": summary["view_evidence_rows"],
                "candidate_rows": summary["candidate_evidence_rows"],
                "pair_rows": summary["pair_evidence_rows"],
                "request_rows": summary["request_evidence_rows"],
                "unresolved_case_rows": summary["unresolved_case_rows"],
                "promotable_branch_outcome_rows": summary["promotable_branch_outcome_rows"],
                "candidate_status_counts": summary["candidate_evidence_status_counts"],
                "uses_gt_for_action": summary["uses_gt_for_action"],
                "paper_claim_allowed": summary["paper_claim_allowed"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if not summary["gate"]["instance_arbitration_detector_evidence_gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
