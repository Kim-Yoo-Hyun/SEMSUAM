import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    load_json,
    load_jsonl,
    ratio,
    request_sort_key,
    safe_float,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.repeated_object_relation_anchor_consistency_detector_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_repeated_object_relation_anchor_consistency_detector_evidence_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_repeated_object_relation_anchor_consistency_detector_evidence_v1"
)

REQUIRED_ROLES = (
    "candidate_own_view",
    "relation_anchor_context_view",
    "orthogonal_axis_challenge_view",
)


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


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


def row_request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def row_decision_id(row: Dict[str, Any]) -> str:
    return str(row.get("decision_id") or "")


def target_candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def selected_candidate_ids(row: Dict[str, Any]) -> List[str]:
    value = row.get("selected_candidate_ids")
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def group_by_decision(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_decision_id(row)].append(dict(row))
    return grouped


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    return grouped


def role_sort_key(role: str) -> Tuple[int, str]:
    try:
        return (REQUIRED_ROLES.index(role), role)
    except ValueError:
        return (len(REQUIRED_ROLES), role)


def candidate_sort_key(candidate_id: str) -> Tuple[int, str]:
    tail = candidate_id.rsplit(":", 1)[-1]
    if tail.isdigit():
        return (safe_int(tail, 999999), candidate_id)
    return (999999, candidate_id)


def association_stats(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
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
    associated_depth_errors = [safe_float(row.get("depth_error_m")) for row in associated]
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
        "associated_depth_error_stats_m": finite_stats(associated_depth_errors),
        "depth_agreement_stats_m": finite_stats(depth_agreements),
    }


def selected_split(
    frame_row: Dict[str, Any],
    association_rows: Sequence[Dict[str, Any]],
) -> Tuple[str, List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    target = target_candidate_id(frame_row)
    selected = selected_candidate_ids(frame_row)
    context_ids = [candidate_id for candidate_id in selected if candidate_id != target]
    target_rows = [row for row in association_rows if str(row.get("candidate_id")) == target]
    context_rows = [
        row
        for row in association_rows
        if str(row.get("candidate_id")) in set(context_ids)
    ]
    return target, context_ids, target_rows, context_rows


def view_status(target_support: bool, context_support: bool, view_role: str) -> str:
    if target_support and context_support:
        return "target_context_mixed_support"
    if context_support:
        return "context_leakage_support"
    if target_support:
        return "target_supported"
    if view_role == "orthogonal_axis_challenge_view":
        return "orthogonal_axis_target_missing"
    return "target_unsupported"


def pair_status(target_support: bool, context_support: bool, view_role: str) -> str:
    if view_role == "orthogonal_axis_challenge_view" and (not target_support or context_support):
        return "orthogonal_axis_contradiction"
    if target_support and context_support:
        return "target_and_context_support"
    if target_support:
        return "target_only_support"
    if context_support:
        return "context_only_support"
    return "no_candidate_support"


def build_view_rows(
    frame_rows: Sequence[Dict[str, Any]],
    associations_by_decision: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    view_rows: List[Dict[str, Any]] = []
    for frame in sorted(
        frame_rows,
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            candidate_sort_key(target_candidate_id(row)),
            role_sort_key(str(row.get("view_role") or "")),
            row_decision_id(row),
        ),
    ):
        decision_rows = associations_by_decision.get(row_decision_id(frame), [])
        target, context_ids, target_rows, context_rows = selected_split(frame, decision_rows)
        target_stats = association_stats(target_rows)
        context_stats = association_stats(context_rows)
        target_support = target_stats["associated_heading_count"] > 0
        context_support = context_stats["associated_heading_count"] > 0
        role = str(frame.get("view_role") or "")
        target_candidates_in_assoc = sorted(
            {str(row.get("candidate_id")) for row in target_rows if row.get("associated_to_candidate") is True}
        )
        context_candidates_in_assoc = sorted(
            {str(row.get("candidate_id")) for row in context_rows if row.get("associated_to_candidate") is True}
        )
        view_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "view_evidence",
                "contract_name": "repeated_object_relation_anchor_consistency_detector_evidence_v1",
                "expanded_retrieval_request_id": row_request_id(frame),
                "rival_identity_request_id": row_request_id(frame),
                "episode_key": frame.get("episode_key"),
                "episode_id": frame.get("episode_id"),
                "scene_id": frame.get("scene_id"),
                "scene_key": frame.get("scene_key"),
                "query": frame.get("query"),
                "decision_id": row_decision_id(frame),
                "source_viewpoint_id": frame.get("source_viewpoint_id"),
                "target_candidate_id": target,
                "context_candidate_ids": context_ids,
                "selected_candidate_ids": selected_candidate_ids(frame),
                "selected_candidate_count": len(selected_candidate_ids(frame)),
                "view_role": role,
                "viewpoint_source": frame.get("viewpoint_source"),
                "standoff_direction_source": frame.get("standoff_direction_source"),
                "standoff_distance_requested": frame.get("standoff_distance_requested"),
                "standoff_target_horizontal_distance": frame.get("standoff_target_horizontal_distance"),
                "target_distance_from_viewpoint_m": frame.get("target_distance_from_viewpoint_m"),
                "rendered_heading_count": frame.get("rendered_heading_count"),
                "detector_box_count": frame.get("detector_box_count"),
                "sam2_mask_count": frame.get("sam2_mask_count"),
                "has_detector_box": frame.get("has_detector_box") is True,
                "has_sam2_mask": frame.get("has_sam2_mask") is True,
                "has_candidate_association": frame.get("has_candidate_association") is True,
                "target_associated_heading_count": target_stats["associated_heading_count"],
                "context_associated_heading_count": context_stats["associated_heading_count"],
                "target_projected_inside_mask_count": target_stats["projected_inside_mask_count"],
                "context_projected_inside_mask_count": context_stats["projected_inside_mask_count"],
                "target_depth_consistent_count": target_stats["depth_consistent_count"],
                "context_depth_consistent_count": context_stats["depth_consistent_count"],
                "target_associated_candidate_ids": target_candidates_in_assoc,
                "context_associated_candidate_ids": context_candidates_in_assoc,
                "target_support": target_support,
                "context_support": context_support,
                "candidate_specific_support_role": target_support and not context_support,
                "context_leakage_role": context_support,
                "orthogonal_axis_contradiction": (
                    role == "orthogonal_axis_challenge_view" and (not target_support or context_support)
                ),
                "view_evidence_status": view_status(target_support, context_support, role),
                "target_association_stats": target_stats,
                "context_association_stats": context_stats,
                "recommended_nonterminal_action": "aggregate_relation_anchor_consistency_candidate",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return view_rows


def build_pair_rows(view_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in view_rows:
        target_support = row.get("target_support") is True
        context_support = row.get("context_support") is True
        role = str(row.get("view_role") or "")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "candidate_context_pair_evidence",
                "contract_name": row.get("contract_name"),
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_id": row.get("scene_id"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "decision_id": row.get("decision_id"),
                "source_viewpoint_id": row.get("source_viewpoint_id"),
                "target_candidate_id": row.get("target_candidate_id"),
                "context_candidate_ids": row.get("context_candidate_ids"),
                "view_role": role,
                "target_support": target_support,
                "context_support": context_support,
                "target_associated_heading_count": row.get("target_associated_heading_count"),
                "context_associated_heading_count": row.get("context_associated_heading_count"),
                "target_projected_inside_mask_count": row.get("target_projected_inside_mask_count"),
                "context_projected_inside_mask_count": row.get("context_projected_inside_mask_count"),
                "target_depth_consistent_count": row.get("target_depth_consistent_count"),
                "context_depth_consistent_count": row.get("context_depth_consistent_count"),
                "candidate_context_pair_status": pair_status(target_support, context_support, role),
                "target_only_support": target_support and not context_support,
                "target_context_mixed_support": target_support and context_support,
                "context_only_support": context_support and not target_support,
                "no_candidate_support": not target_support and not context_support,
                "orthogonal_axis_contradiction": row.get("orthogonal_axis_contradiction") is True,
                "recommended_nonterminal_action": "aggregate_relation_anchor_consistency_candidate",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def role_metric(rows: Sequence[Dict[str, Any]], role: str, key: str) -> int:
    return sum(safe_int(row.get(key), 0) for row in rows if row.get("view_role") == role)


def bool_by_role(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, bool]:
    return {role: any(row.get(key) is True for row in rows if row.get("view_role") == role) for role in REQUIRED_ROLES}


def count_by_role(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, int]:
    return {role: role_metric(rows, role, key) for role in REQUIRED_ROLES}


def candidate_preliminary_status(
    target_support_by_role: Dict[str, bool],
    context_support_by_role: Dict[str, bool],
) -> Tuple[str, List[str], bool]:
    required_missing = [role for role, support in target_support_by_role.items() if not support]
    context_leakage_roles = [role for role, support in context_support_by_role.items() if support]
    orthogonal_contradiction = (
        not target_support_by_role.get("orthogonal_axis_challenge_view", False)
        or context_support_by_role.get("orthogonal_axis_challenge_view", False)
    )
    stable_rule_passed = (
        target_support_by_role.get("candidate_own_view", False)
        and target_support_by_role.get("relation_anchor_context_view", False)
        and target_support_by_role.get("orthogonal_axis_challenge_view", False)
        and not context_support_by_role.get("relation_anchor_context_view", False)
        and not context_support_by_role.get("orthogonal_axis_challenge_view", False)
        and not orthogonal_contradiction
    )
    if orthogonal_contradiction:
        return "contradicted_candidate_evidence", required_missing, stable_rule_passed
    if required_missing:
        return "insufficient_candidate_evidence", required_missing, stable_rule_passed
    if context_leakage_roles:
        return "ambiguous_repeated_object_candidate", required_missing, stable_rule_passed
    if stable_rule_passed:
        return "stable_relation_anchor_consistency_candidate", required_missing, stable_rule_passed
    return "partial_relation_anchor_consistency_candidate", required_missing, stable_rule_passed


def build_candidate_rows(view_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in view_rows:
        grouped[(str(row.get("expanded_retrieval_request_id")), str(row.get("target_candidate_id")))].append(dict(row))

    candidate_rows: List[Dict[str, Any]] = []
    for (request_id, candidate_id), rows in sorted(
        grouped.items(), key=lambda item: (request_sort_key(item[0][0]), candidate_sort_key(item[0][1]))
    ):
        rows = sorted(rows, key=lambda row: role_sort_key(str(row.get("view_role") or "")))
        first = rows[0]
        target_support_by_role = bool_by_role(rows, "target_support")
        context_support_by_role = bool_by_role(rows, "context_support")
        context_leakage_roles = [
            role for role, support in context_support_by_role.items() if support
        ]
        candidate_specific_support_by_role = bool_by_role(rows, "candidate_specific_support_role")
        contradiction_roles = [
            role for role in REQUIRED_ROLES if any(
                item.get("view_role") == role and item.get("orthogonal_axis_contradiction") is True
                for item in rows
            )
        ]
        status, missing_roles, stable_rule_passed = candidate_preliminary_status(
            target_support_by_role,
            context_support_by_role,
        )
        if status == "stable_relation_anchor_consistency_candidate":
            action = "record_promotable_relation_anchor_consistency_candidate"
        elif status == "ambiguous_repeated_object_candidate":
            action = "request_repeated_object_ambiguity_followup"
        elif status == "insufficient_candidate_evidence":
            action = "request_candidate_own_view_recovery"
        elif status == "contradicted_candidate_evidence":
            action = "defer_relation_anchor_consistency_contradicted"
        else:
            action = "defer_partial_relation_anchor_consistency"
        candidate_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "candidate_consistency",
                "contract_name": first.get("contract_name"),
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": request_id,
                "episode_key": first.get("episode_key"),
                "scene_id": first.get("scene_id"),
                "scene_key": first.get("scene_key"),
                "query": first.get("query"),
                "target_candidate_id": candidate_id,
                "view_role_count": len(rows),
                "view_roles": [str(row.get("view_role")) for row in rows],
                "required_view_roles_present": sorted({str(row.get("view_role")) for row in rows}) == sorted(REQUIRED_ROLES),
                "own_view_target_support": target_support_by_role["candidate_own_view"],
                "relation_anchor_context_target_support": target_support_by_role[
                    "relation_anchor_context_view"
                ],
                "orthogonal_axis_target_support": target_support_by_role[
                    "orthogonal_axis_challenge_view"
                ],
                "target_support_by_role": target_support_by_role,
                "context_support_by_role": context_support_by_role,
                "candidate_specific_support_by_role": candidate_specific_support_by_role,
                "target_associated_heading_count_by_role": count_by_role(
                    rows, "target_associated_heading_count"
                ),
                "context_associated_heading_count_by_role": count_by_role(
                    rows, "context_associated_heading_count"
                ),
                "target_projected_inside_mask_count_by_role": count_by_role(
                    rows, "target_projected_inside_mask_count"
                ),
                "context_projected_inside_mask_count_by_role": count_by_role(
                    rows, "context_projected_inside_mask_count"
                ),
                "target_depth_consistent_count_by_role": count_by_role(
                    rows, "target_depth_consistent_count"
                ),
                "context_depth_consistent_count_by_role": count_by_role(
                    rows, "context_depth_consistent_count"
                ),
                "context_leakage_support": bool(context_leakage_roles),
                "context_leakage_roles": context_leakage_roles,
                "required_target_support_missing_roles": missing_roles,
                "candidate_specific_support_role_count": sum(
                    1 for support in candidate_specific_support_by_role.values() if support
                ),
                "contradiction_role_count": len(contradiction_roles),
                "contradiction_roles": contradiction_roles,
                "stable_rule_passed": stable_rule_passed,
                "candidate_consistency_status": status,
                "recommended_nonterminal_action": action,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return candidate_rows


def finalize_candidate_rows(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_request = group_by_request(candidate_rows)
    finalized: List[Dict[str, Any]] = []
    for request_id in sorted(by_request, key=request_sort_key):
        rows = by_request[request_id]
        stable_rule_count = sum(1 for row in rows if row.get("stable_rule_passed") is True)
        for row in rows:
            out = dict(row)
            if row.get("stable_rule_passed") is True and stable_rule_count > 1:
                out["same_request_multiple_stable_candidates"] = True
                out["candidate_consistency_status"] = "ambiguous_repeated_object_candidate"
                out["recommended_nonterminal_action"] = "request_repeated_object_ambiguity_followup"
            else:
                out["same_request_multiple_stable_candidates"] = False
            finalized.append(out)
    return sorted(
        finalized,
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            candidate_sort_key(str(row.get("target_candidate_id") or "")),
        ),
    )


def build_request_rows(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = group_by_request(candidate_rows)
    request_rows: List[Dict[str, Any]] = []
    for request_id in sorted(grouped, key=request_sort_key):
        rows = sorted(
            grouped[request_id],
            key=lambda row: candidate_sort_key(str(row.get("target_candidate_id") or "")),
        )
        first = rows[0]
        status_counts = Counter(str(row.get("candidate_consistency_status")) for row in rows)
        stable_rows = [
            row
            for row in rows
            if row.get("candidate_consistency_status") == "stable_relation_anchor_consistency_candidate"
        ]
        contradicted_rows = [
            row
            for row in rows
            if row.get("candidate_consistency_status") == "contradicted_candidate_evidence"
        ]
        promotable = len(stable_rows) == 1 and len(contradicted_rows) == 0
        if promotable:
            action = "record_promotable_branch_outcome_for_terminal_contract_review"
        elif len(stable_rows) > 1 or status_counts.get("ambiguous_repeated_object_candidate", 0) > 0:
            action = "request_additional_repeated_object_disambiguation"
        else:
            action = "defer_relation_anchor_consistency_unresolved"
        request_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "request_consistency",
                "contract_name": first.get("contract_name"),
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": request_id,
                "episode_key": first.get("episode_key"),
                "scene_id": first.get("scene_id"),
                "scene_key": first.get("scene_key"),
                "query": first.get("query"),
                "candidate_count": len(rows),
                "candidate_ids": [row.get("target_candidate_id") for row in rows],
                "stable_candidate_count": status_counts.get(
                    "stable_relation_anchor_consistency_candidate", 0
                ),
                "ambiguous_candidate_count": status_counts.get(
                    "ambiguous_repeated_object_candidate", 0
                ),
                "insufficient_candidate_count": status_counts.get(
                    "insufficient_candidate_evidence", 0
                ),
                "contradicted_candidate_count": status_counts.get(
                    "contradicted_candidate_evidence", 0
                ),
                "partial_candidate_count": status_counts.get(
                    "partial_relation_anchor_consistency_candidate", 0
                ),
                "candidate_consistency_status_counts": dict(sorted(status_counts.items())),
                "stable_candidate_ids": [row.get("target_candidate_id") for row in stable_rows],
                "ambiguous_candidate_ids": [
                    row.get("target_candidate_id")
                    for row in rows
                    if row.get("candidate_consistency_status") == "ambiguous_repeated_object_candidate"
                ],
                "insufficient_candidate_ids": [
                    row.get("target_candidate_id")
                    for row in rows
                    if row.get("candidate_consistency_status") == "insufficient_candidate_evidence"
                ],
                "contradicted_candidate_ids": [
                    row.get("target_candidate_id") for row in contradicted_rows
                ],
                "promotable_branch_outcome_count": 1 if promotable else 0,
                "promotable_branch_outcome": promotable,
                "recommended_nonterminal_action": action,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return request_rows


def role_fraction_counts(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, str]:
    counts: Dict[str, str] = {}
    for role in REQUIRED_ROLES:
        role_rows = [row for row in rows if row.get("view_role") == role]
        positives = sum(1 for row in role_rows if row.get(key) is True)
        counts[role] = f"{positives}/{len(role_rows)}"
    return counts


def selected_candidate_count_rows(frame_rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return compact_counter(row.get("selected_candidate_count") for row in frame_rows)


def requested_outputs(contract: Dict[str, Any]) -> Dict[str, str]:
    expected = contract.get("expected_outputs") or {}
    return {
        "view_evidence_rows": expected.get(
            "view_evidence_rows", "relation_anchor_consistency_view_evidence_rows.jsonl"
        ),
        "candidate_context_pair_rows": expected.get(
            "candidate_context_pair_rows",
            "relation_anchor_consistency_candidate_context_pair_rows.jsonl",
        ),
        "candidate_consistency_rows": expected.get(
            "candidate_consistency_rows", "relation_anchor_consistency_candidate_rows.jsonl"
        ),
        "request_consistency_rows": expected.get(
            "request_consistency_rows", "relation_anchor_consistency_request_rows.jsonl"
        ),
        "summary": expected.get(
            "summary", "relation_anchor_consistency_detector_evidence_summary.json"
        ),
    }


def gate_summary(
    contract: Dict[str, Any],
    planner_summary: Dict[str, Any],
    projection_summary: Dict[str, Any],
    detector_summary: Dict[str, Any],
    frame_rows: Sequence[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
    view_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, bool]:
    gates = contract.get("required_gates") or {}
    detector_gate = detector_summary.get("gate") or {}
    planner_gate = planner_summary.get("gate") or {}
    projection_gate = projection_summary.get("gate") or {}
    return {
        "source_planner_gate_passed": bool(
            planner_gate.get("repeated_object_relation_anchor_consistency_plan_gate_passed")
            is True
            and gates.get("source_planner_gate_passed") is True
        ),
        "source_projection_gate_passed": bool(
            projection_gate.get("projection_anchor_smoke_passed") is True
            and gates.get("source_projection_gate_passed") is True
        ),
        "source_detector_substrate_gate_passed": bool(
            detector_gate.get("passes_detector_substrate_gate") is True
            and gates.get("source_detector_substrate_gate_passed") is True
        ),
        "expected_view_evidence_rows_passed": len(view_rows)
        == safe_int(gates.get("expected_view_evidence_rows"), -1),
        "expected_candidate_context_pair_rows_passed": len(pair_rows)
        == safe_int(gates.get("expected_candidate_context_pair_rows"), -1),
        "expected_candidate_consistency_rows_passed": len(candidate_rows)
        == safe_int(gates.get("expected_candidate_consistency_rows"), -1),
        "expected_request_consistency_rows_passed": len(request_rows)
        == safe_int(gates.get("expected_request_consistency_rows"), -1),
        "minimum_detector_association_rows_passed": len(association_rows)
        >= safe_int(gates.get("minimum_detector_association_rows"), 0),
        "minimum_candidate_association_rate_passed": safe_float(
            detector_summary.get("candidate_association_rate"), 0.0
        )
        >= safe_float(gates.get("minimum_candidate_association_rate"), 0.0),
        "minimum_rows_with_candidate_association_passed": safe_int(
            detector_summary.get("rows_with_candidate_association"), 0
        )
        >= safe_int(gates.get("minimum_rows_with_candidate_association"), 0),
        "minimum_associated_candidate_heading_count_passed": safe_int(
            detector_summary.get("associated_candidate_heading_count"), 0
        )
        >= safe_int(gates.get("minimum_associated_candidate_heading_count"), 0),
        "all_views_have_two_selected_candidates_passed": all(
            len(selected_candidate_ids(row)) == 2 for row in frame_rows
        ),
        "all_requests_have_three_required_view_roles_per_candidate_passed": all(
            row.get("required_view_roles_present") is True for row in candidate_rows
        ),
        "action_evidence_forbidden_key_gate_passed": len(forbidden_keys) == safe_int(
            gates.get("action_evidence_forbidden_key_count"), 0
        ),
        "terminal_commit_rows_passed": sum(
            1 for row in [*view_rows, *pair_rows, *candidate_rows, *request_rows] if row.get("terminal_commit") is True
        )
        == safe_int(gates.get("terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": sum(
            1 for row in [*candidate_rows, *request_rows] if row.get("candidate_commit") is True
        )
        == safe_int(gates.get("candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": sum(
            1 for row in [*candidate_rows, *request_rows] if row.get("candidate_rejection") is True
        )
        == safe_int(gates.get("candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": not any(
            row.get("uses_gt_for_action") is True
            for row in [*view_rows, *pair_rows, *candidate_rows, *request_rows]
        )
        and detector_summary.get("uses_gt_for_action") is False,
        "terminal_utility_validation_allowed_passed": not any(
            row.get("terminal_utility_validation_allowed") is True
            for row in [*view_rows, *pair_rows, *candidate_rows, *request_rows]
        ),
        "paper_claim_allowed_passed": not any(
            row.get("paper_claim_allowed") is True
            for row in [*view_rows, *pair_rows, *candidate_rows, *request_rows]
        )
        and contract.get("paper_claim_allowed") is False,
    }


def build_summary(
    args: argparse.Namespace,
    contract: Dict[str, Any],
    planner_summary: Dict[str, Any],
    projection_summary: Dict[str, Any],
    detector_summary: Dict[str, Any],
    frame_rows: Sequence[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
    view_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    action_rows: List[Dict[str, Any]] = [
        *[dict(row) for row in view_rows],
        *[dict(row) for row in pair_rows],
        *[dict(row) for row in candidate_rows],
        *[dict(row) for row in request_rows],
    ]
    forbidden = action_forbidden_keys(action_rows)
    gates = gate_summary(
        contract,
        planner_summary,
        projection_summary,
        detector_summary,
        frame_rows,
        association_rows,
        view_rows,
        pair_rows,
        candidate_rows,
        request_rows,
        forbidden,
    )
    candidate_status_counts = compact_counter(row.get("candidate_consistency_status") for row in candidate_rows)
    request_action_counts = compact_counter(row.get("recommended_nonterminal_action") for row in request_rows)
    candidate_action_counts = compact_counter(row.get("recommended_nonterminal_action") for row in candidate_rows)
    outputs = requested_outputs(contract)
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-01",
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "output_files": {
            key: str(Path(str(args.out_root)) / value)
            for key, value in outputs.items()
        },
        "source": {
            "planner_summary": str(args.planner_summary),
            "projection_summary": str(args.projection_summary),
            "detector_summary": str(args.detector_summary),
            "detector_frame_summary": str(args.detector_frame_summary),
            "detector_associations": str(args.detector_associations),
        },
        "view_evidence_rows": len(view_rows),
        "candidate_context_pair_rows": len(pair_rows),
        "candidate_consistency_rows": len(candidate_rows),
        "request_consistency_rows": len(request_rows),
        "detector_frame_rows": len(frame_rows),
        "detector_association_rows": len(association_rows),
        "detector_box_rate": detector_summary.get("detector_box_rate"),
        "sam2_mask_rate": detector_summary.get("sam2_mask_rate"),
        "candidate_association_rate": detector_summary.get("candidate_association_rate"),
        "rows_with_candidate_association": detector_summary.get("rows_with_candidate_association"),
        "associated_candidate_heading_count": detector_summary.get("associated_candidate_heading_count"),
        "selected_candidate_count_rows": selected_candidate_count_rows(frame_rows),
        "view_role_counts": compact_counter(row.get("view_role") for row in frame_rows),
        "target_association_frames_by_role": role_fraction_counts(view_rows, "target_support"),
        "context_association_frames_by_role": role_fraction_counts(view_rows, "context_support"),
        "candidate_specific_support_frames_by_role": role_fraction_counts(
            view_rows, "candidate_specific_support_role"
        ),
        "candidate_consistency_status_counts": candidate_status_counts,
        "candidate_recommended_action_counts": candidate_action_counts,
        "request_recommended_action_counts": request_action_counts,
        "stable_candidate_rows": candidate_status_counts.get("stable_relation_anchor_consistency_candidate", 0),
        "ambiguous_candidate_rows": candidate_status_counts.get("ambiguous_repeated_object_candidate", 0),
        "insufficient_candidate_rows": candidate_status_counts.get("insufficient_candidate_evidence", 0),
        "contradicted_candidate_rows": candidate_status_counts.get("contradicted_candidate_evidence", 0),
        "promotable_branch_outcome_rows": sum(
            1 for row in request_rows if row.get("promotable_branch_outcome") is True
        ),
        "promotable_branch_outcome_request_ids": [
            row.get("expanded_retrieval_request_id")
            for row in request_rows
            if row.get("promotable_branch_outcome") is True
        ],
        "terminal_commit_rows": sum(1 for row in action_rows if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in action_rows if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in action_rows if row.get("candidate_rejection") is True),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": list(forbidden),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in action_rows),
        "uses_gt_for_analysis": any(row.get("uses_gt_for_analysis") is True for row in action_rows),
        "terminal_utility_validation_allowed": any(
            row.get("terminal_utility_validation_allowed") is True for row in action_rows
        ),
        "paper_claim_allowed": any(row.get("paper_claim_allowed") is True for row in action_rows),
        "gate": {
            **gates,
            "relation_anchor_consistency_detector_evidence_gate_passed": all(gates.values()),
        },
        "next_allowed_task": (
            "design_terminal_utility_contract_only_if_promotable_branch_outcome_is_accepted"
            if sum(1 for row in request_rows if row.get("promotable_branch_outcome") is True) > 0
            else "diagnose_repeated_object_relation_anchor_consistency_residual"
        ),
        "interpretation": {
            "fact": "This analyzer writes nonterminal relation-anchor consistency evidence from detector/SAM2 association rows.",
            "agent_inference": "Stable repeated-object relation-anchor consistency is a candidate branch outcome, not a terminal ObjectNav goal-validity proof.",
            "paper_claim": "No paper claim is allowed from this analyzer alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    args.planner_summary = source_path(args, contract, "planner_summary", "planner_summary")
    args.projection_summary = source_path(args, contract, "projection_summary", "projection_summary")
    args.detector_summary = source_path(args, contract, "detector_summary", "detector_summary")
    args.detector_frame_summary = source_path(
        args, contract, "detector_frame_summary", "detector_frame_summary"
    )
    args.detector_associations = source_path(
        args, contract, "detector_associations", "detector_associations"
    )

    out_root = Path(args.out_root)
    planner_summary = load_json(args.planner_summary)
    projection_summary = load_json(args.projection_summary)
    detector_summary = load_json(args.detector_summary)
    frame_rows = load_jsonl(args.detector_frame_summary)
    association_rows = load_jsonl(args.detector_associations)

    associations_by_decision = group_by_decision(association_rows)
    view_rows = build_view_rows(frame_rows, associations_by_decision)
    pair_rows = build_pair_rows(view_rows)
    candidate_rows = finalize_candidate_rows(build_candidate_rows(view_rows))
    request_rows = build_request_rows(candidate_rows)
    summary = build_summary(
        args,
        contract,
        planner_summary,
        projection_summary,
        detector_summary,
        frame_rows,
        association_rows,
        view_rows,
        pair_rows,
        candidate_rows,
        request_rows,
    )

    outputs = requested_outputs(contract)
    write_jsonl(out_root / outputs["view_evidence_rows"], view_rows)
    write_jsonl(out_root / outputs["candidate_context_pair_rows"], pair_rows)
    write_jsonl(out_root / outputs["candidate_consistency_rows"], candidate_rows)
    write_jsonl(out_root / outputs["request_consistency_rows"], request_rows)
    write_json(out_root / outputs["summary"], summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze repeated-object relation-anchor consistency detector evidence."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--planner-summary", default=None)
    parser.add_argument("--projection-summary", default=None)
    parser.add_argument("--detector-summary", default=None)
    parser.add_argument("--detector-frame-summary", default=None)
    parser.add_argument("--detector-associations", default=None)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(
        json.dumps(
            {
                "gate": summary["gate"]["relation_anchor_consistency_detector_evidence_gate_passed"],
                "view_rows": summary["view_evidence_rows"],
                "candidate_rows": summary["candidate_consistency_rows"],
                "request_rows": summary["request_consistency_rows"],
                "candidate_status_counts": summary["candidate_consistency_status_counts"],
                "promotable_branch_outcome_rows": summary["promotable_branch_outcome_rows"],
                "uses_gt_for_action": summary["uses_gt_for_action"],
                "paper_claim_allowed": summary["paper_claim_allowed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
