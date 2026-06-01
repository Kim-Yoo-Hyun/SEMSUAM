import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

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


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_rival_region_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_evidence_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_evidence_v1"
)
REQUIRED_ROLES = [
    "rival_from_common_pair_view",
    "rival_from_focus_own_view",
    "focus_from_rival_own_view",
]


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


def decision_id(row: Dict[str, Any]) -> str:
    return str(row.get("decision_id") or "")


def group_by_decision(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[decision_id(row)].append(dict(row))
    return grouped


def group_by_pair(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("pair_id") or "")].append(dict(row))
    return grouped


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    return grouped


def association_stats(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
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
    depth_agreements = [safe_float(row.get("depth_agreement_m")) for row in rows]
    associated_depth_agreements = [safe_float(row.get("depth_agreement_m")) for row in associated]
    camera_forward = [safe_float(row.get("camera_forward_m")) for row in rows]
    mask_depths = [safe_float(row.get("mask_depth_median")) for row in rows]
    return {
        "association_rows": len(rows),
        "associated_heading_count_from_rows": len(associated),
        "visible_count": len(visible),
        "inside_box_count": len(inside_box),
        "inside_mask_count": len(inside_mask),
        "depth_consistent_count": len(depth_consistent),
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
        "camera_forward_stats_m": finite_stats(camera_forward),
        "mask_depth_stats_m": finite_stats(mask_depths),
    }


def view_evidence_row(frame_row: Dict[str, Any], association_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    role = str(frame_row.get("second_pass_view_role") or frame_row.get("view_role") or "")
    support = frame_row.get("has_candidate_association") is True
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_rival_region_view_evidence",
        "expanded_retrieval_request_id": row_request_id(frame_row),
        "rival_identity_request_id": frame_row.get("rival_identity_request_id"),
        "episode_key": frame_row.get("episode_key"),
        "scene_key": frame_row.get("scene_key"),
        "scene_id": frame_row.get("scene_id"),
        "query": frame_row.get("query"),
        "request_index": frame_row.get("request_index"),
        "pair_id": frame_row.get("pair_id"),
        "pair_index": frame_row.get("pair_index"),
        "decision_id": frame_row.get("decision_id"),
        "role": role,
        "second_pass_view_role": role,
        "second_stage_source_view_role": frame_row.get("second_stage_source_view_role"),
        "source_view_role": frame_row.get("source_view_role"),
        "viewpoint_source": frame_row.get("viewpoint_source"),
        "planner_name": frame_row.get("planner_name"),
        "focus_candidate_id": frame_row.get("focus_candidate_id"),
        "rival_candidate_id": frame_row.get("rival_candidate_id"),
        "target_candidate_id": frame_row.get("target_candidate_id"),
        "target_candidate_role": frame_row.get("target_candidate_role"),
        "selected_candidate_ids": frame_row.get("selected_candidate_ids"),
        "candidate_selection_source": frame_row.get("candidate_selection_source"),
        "focus_rival_span_m": frame_row.get("focus_rival_span_m"),
        "target_distance_from_viewpoint_m": frame_row.get("target_distance_from_viewpoint_m"),
        "focus_distance_from_viewpoint_m": frame_row.get("focus_distance_from_viewpoint_m"),
        "rival_distance_from_viewpoint_m": frame_row.get("rival_distance_from_viewpoint_m"),
        "standoff_direction_source": frame_row.get("standoff_direction_source"),
        "standoff_distance_requested": frame_row.get("standoff_distance_requested"),
        "standoff_target_horizontal_distance": frame_row.get("standoff_target_horizontal_distance"),
        "standoff_navmesh_navigable": frame_row.get("standoff_navmesh_navigable"),
        "standoff_navmesh_snapped": frame_row.get("standoff_navmesh_snapped"),
        "projection_anchor_policy": frame_row.get("projection_anchor_policy"),
        "projection_anchor_height_offsets_m": frame_row.get("projection_anchor_height_offsets_m"),
        "rendered_heading_count": frame_row.get("rendered_heading_count"),
        "detector_box_count": frame_row.get("detector_box_count"),
        "sam2_mask_count": frame_row.get("sam2_mask_count"),
        "has_detector_box": frame_row.get("has_detector_box"),
        "has_sam2_mask": frame_row.get("has_sam2_mask"),
        "has_candidate_association": support,
        "candidate_supported": support,
        "support_boolean": support,
        "associated_candidate_heading_count": safe_int(frame_row.get("associated_candidate_heading_count"), 0),
        **association_stats(association_rows),
        "rival_region_view_evidence_status": "supported_candidate_view" if support else "unsupported_candidate_view",
        "recommended_nonterminal_action": "aggregate_pair_rival_region_evidence",
        "terminal_policy_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_view_rows(
    frame_rows: Sequence[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    associations_by_decision = group_by_decision(association_rows)
    role_order = {role: index for index, role in enumerate(REQUIRED_ROLES)}
    rows = [
        view_evidence_row(frame_row, associations_by_decision.get(decision_id(frame_row), []))
        for frame_row in frame_rows
    ]
    rows.sort(
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            safe_int(row.get("pair_index"), 999999),
            role_order.get(str(row.get("role")), 99),
            str(row.get("decision_id")),
        )
    )
    return rows


def pair_status(role_rows: Dict[str, Dict[str, Any]], missing_roles: Sequence[str]) -> str:
    if missing_roles:
        return "insufficient_second_pass_detector_pair"
    rival_from_focus = role_rows.get("rival_from_focus_own_view", {}).get("has_candidate_association") is True
    focus_from_rival = role_rows.get("focus_from_rival_own_view", {}).get("has_candidate_association") is True
    rival_from_common = role_rows.get("rival_from_common_pair_view", {}).get("has_candidate_association") is True
    if rival_from_focus or focus_from_rival:
        return "cross_region_overlap_pair"
    if rival_from_common:
        return "shared_common_view_rival_support_pair"
    return "second_pass_rival_region_contrastive_pair"


def pair_action(status: str) -> str:
    if status == "cross_region_overlap_pair":
        return "defer_goal_region_unresolved_cross_region_overlap"
    if status == "shared_common_view_rival_support_pair":
        return "request_goal_region_arbitration_after_shared_common_evidence"
    if status == "second_pass_rival_region_contrastive_pair":
        return "design_fixed_non_gt_goal_region_arbitration_contract"
    return "defer_goal_region_unresolved"


def pair_reason(status: str) -> str:
    if status == "cross_region_overlap_pair":
        return "rival support from focus view or focus support from rival view indicates unresolved cross-region overlap"
    if status == "shared_common_view_rival_support_pair":
        return "the rival is still supported from the common pair view, so common-view evidence is not unique"
    if status == "second_pass_rival_region_contrastive_pair":
        return "no second-pass rival/common cross support is present; terminal commit still requires a fixed arbitration contract"
    return "required second-pass role evidence is missing"


def build_pair_rows(view_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    role_order = {role: index for index, role in enumerate(REQUIRED_ROLES)}
    for pair_id, group in sorted(
        group_by_pair(view_rows).items(),
        key=lambda item: (
            request_sort_key(row_request_id(item[1][0]) if item[1] else ""),
            safe_int(item[1][0].get("pair_index"), 999999) if item[1] else 999999,
            item[0],
        ),
    ):
        if not pair_id:
            continue
        exemplar = group[0]
        by_role: Dict[str, Dict[str, Any]] = {}
        duplicate_roles: Dict[str, int] = {}
        for row in sorted(group, key=lambda item: role_order.get(str(item.get("role")), 99)):
            role = str(row.get("role"))
            if role in by_role:
                duplicate_roles[role] = duplicate_roles.get(role, 1) + 1
            else:
                by_role[role] = row
        missing_roles = [role for role in REQUIRED_ROLES if role not in by_role]
        status = pair_status(by_role, missing_roles)
        role_supports = {
            role: by_role.get(role, {}).get("has_candidate_association") is True for role in REQUIRED_ROLES
        }
        role_heading_counts = {
            role: safe_int(by_role.get(role, {}).get("associated_candidate_heading_count"), 0)
            for role in REQUIRED_ROLES
        }
        role_detector_boxes = {role: by_role.get(role, {}).get("detector_box_count") for role in REQUIRED_ROLES}
        role_sam2_masks = {role: by_role.get(role, {}).get("sam2_mask_count") for role in REQUIRED_ROLES}
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_rival_region_pair_evidence",
                "expanded_retrieval_request_id": row_request_id(exemplar),
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "request_index": exemplar.get("request_index"),
                "pair_id": pair_id,
                "pair_index": exemplar.get("pair_index"),
                "focus_candidate_id": exemplar.get("focus_candidate_id"),
                "rival_candidate_id": exemplar.get("rival_candidate_id"),
                "required_roles": REQUIRED_ROLES,
                "present_roles": sorted(by_role.keys()),
                "missing_roles": missing_roles,
                "duplicate_role_counts": duplicate_roles,
                "rival_from_common_pair_view_support": role_supports["rival_from_common_pair_view"],
                "rival_from_focus_own_view_support": role_supports["rival_from_focus_own_view"],
                "focus_from_rival_own_view_support": role_supports["focus_from_rival_own_view"],
                "role_associated_heading_counts": role_heading_counts,
                "role_detector_box_counts": role_detector_boxes,
                "role_sam2_mask_counts": role_sam2_masks,
                "second_pass_support_role_count": sum(1 for value in role_supports.values() if value),
                "cross_region_support": role_supports["rival_from_focus_own_view"]
                or role_supports["focus_from_rival_own_view"],
                "shared_common_view_rival_support": role_supports["rival_from_common_pair_view"],
                "rival_region_evidence_status": status,
                "recommended_nonterminal_action": pair_action(status),
                "recommended_nonterminal_reason": pair_reason(status),
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def request_action(counts: Counter) -> str:
    if counts.get("cross_region_overlap_pair", 0) > 0:
        return "defer_goal_region_unresolved_cross_region_overlap"
    if counts.get("shared_common_view_rival_support_pair", 0) > 0:
        return "request_goal_region_arbitration_after_shared_common_evidence"
    if counts.get("second_pass_rival_region_contrastive_pair", 0) > 0:
        return "design_fixed_non_gt_goal_region_arbitration_contract"
    return "defer_goal_region_unresolved"


def request_reason(counts: Counter) -> str:
    if counts.get("cross_region_overlap_pair", 0) > 0:
        return "at least one ambiguous pair has cross-region overlap support after second-pass observation"
    if counts.get("shared_common_view_rival_support_pair", 0) > 0:
        return "no cross-region overlap is detected, but common-view rival support remains"
    if counts.get("second_pass_rival_region_contrastive_pair", 0) > 0:
        return "contrastive second-pass evidence exists, but terminal commit still requires a fixed arbitration contract"
    return "second-pass evidence is insufficient"


def build_request_rows(pair_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for request_id, group in sorted(group_by_request(pair_rows).items(), key=lambda item: request_sort_key(item[0])):
        if not request_id:
            continue
        exemplar = group[0]
        status_counts = Counter(str(row.get("rival_region_evidence_status")) for row in group)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_rival_region_request_evidence",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "request_index": exemplar.get("request_index"),
                "focus_candidate_id": exemplar.get("focus_candidate_id"),
                "pair_count": len(group),
                "rival_candidate_ids": [row.get("rival_candidate_id") for row in group],
                "cross_region_overlap_pair_count": status_counts.get("cross_region_overlap_pair", 0),
                "shared_common_view_rival_support_pair_count": status_counts.get(
                    "shared_common_view_rival_support_pair", 0
                ),
                "second_pass_rival_region_contrastive_pair_count": status_counts.get(
                    "second_pass_rival_region_contrastive_pair", 0
                ),
                "insufficient_second_pass_detector_pair_count": status_counts.get(
                    "insufficient_second_pass_detector_pair", 0
                ),
                "rival_region_evidence_status_counts": dict(sorted(status_counts.items())),
                "recommended_nonterminal_action": request_action(status_counts),
                "recommended_nonterminal_reason": request_reason(status_counts),
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def simpler_alternative_report(pair_rows: Sequence[Dict[str, Any]], request_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    status_counts = Counter(str(row.get("rival_region_evidence_status")) for row in pair_rows)
    no_rival_from_focus = sum(
        1 for row in pair_rows if row.get("rival_from_focus_own_view_support") is not True
    )
    no_cross_region = sum(1 for row in pair_rows if row.get("cross_region_support") is not True)
    action_counts = Counter(str(row.get("recommended_nonterminal_action")) for row in request_rows)
    return {
        "commit_if_rival_absent_from_focus_view": {
            "decision": "rejected_as_terminal_rule",
            "eligible_pair_rows": no_rival_from_focus,
            "reason": "it ignores focus_from_rival_own_view and common-view rival support",
        },
        "commit_if_no_cross_region_overlap": {
            "decision": "diagnostic_only",
            "eligible_pair_rows": no_cross_region,
            "reason": "absence of cross-region support is not yet ObjectNav goal validity",
        },
        "association_count_best": {
            "decision": "diagnostic_only",
            "pair_status_counts": dict(sorted(status_counts.items())),
            "reason": "association count measures view evidence, not target-goal identity",
        },
        "defer_all": {
            "decision": "safe_but_inert",
            "nonterminal_actions_lost": dict(sorted(action_counts.items())),
            "reason": "keeps safety but cannot test whether second-pass evidence reduces over-deferral",
        },
    }


def summarize(
    *,
    contract: Dict[str, Any],
    detector_summary: Dict[str, Any],
    association_rows: Sequence[Dict[str, Any]],
    view_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    required = contract.get("required_gates") or {}
    action_rows = list(view_rows) + list(pair_rows) + list(request_rows)
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    role_counts = Counter(str(row.get("role")) for row in view_rows)
    associated_rows_by_role = Counter(
        str(row.get("role")) for row in view_rows if row.get("has_candidate_association") is True
    )
    associated_heading_by_role: Dict[str, int] = defaultdict(int)
    for row in view_rows:
        associated_heading_by_role[str(row.get("role"))] += safe_int(
            row.get("associated_candidate_heading_count"), 0
        )
    status_counts = Counter(str(row.get("rival_region_evidence_status")) for row in pair_rows)
    request_action_counts = Counter(str(row.get("recommended_nonterminal_action")) for row in request_rows)
    detector_gate = detector_summary.get("gate") or {}
    all_pairs_have_three_roles = all(not row.get("missing_roles") for row in pair_rows)
    actual_uses_gt_for_action = any(row.get("uses_gt_for_action") is True for row in action_rows)
    gate = {
        "source_detector_substrate_gate_passed": detector_gate.get("passes_detector_substrate_gate")
        is bool(required.get("source_detector_substrate_gate_passed", True)),
        "expected_view_evidence_rows_passed": len(view_rows)
        == safe_int(required.get("expected_view_evidence_rows"), 0),
        "expected_pair_evidence_rows_passed": len(pair_rows)
        == safe_int(required.get("expected_pair_evidence_rows"), 0),
        "expected_request_evidence_rows_passed": len(request_rows)
        == safe_int(required.get("expected_request_evidence_rows"), 0),
        "all_pairs_have_three_roles_passed": all_pairs_have_three_roles
        is bool(required.get("all_pairs_have_three_roles", True)),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(required.get("action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(required.get("terminal_commit_rows"), 0),
        "uses_gt_for_action_passed": actual_uses_gt_for_action
        is bool(required.get("uses_gt_for_action", False)),
        "paper_claim_allowed_passed": False is bool(required.get("paper_claim_allowed", False)),
        "pair_status_accounting_passed": sum(status_counts.values()) == len(pair_rows),
        "request_status_accounting_passed": len(request_rows) == len({row_request_id(row) for row in pair_rows}),
        "uses_gt_for_action": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["unique_support_rival_region_evidence_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "uses_gt_for_action",
            "terminal_utility_validation_allowed",
            "paper_claim_allowed",
        }
    )
    if status_counts.get("cross_region_overlap_pair", 0) > 0:
        recommended_next_action = "inspect_cross_region_overlap_before_terminal_arbitration"
        reason = "second-pass evidence still shows cross-region overlap for most ambiguous pairs"
    elif status_counts.get("shared_common_view_rival_support_pair", 0) > 0:
        recommended_next_action = "design_shared_common_view_arbitration_contract"
        reason = "common-view rival support remains without cross-region overlap"
    elif status_counts.get("second_pass_rival_region_contrastive_pair", 0) > 0:
        recommended_next_action = "design_fixed_non_gt_goal_region_arbitration_contract"
        reason = "contrastive second-pass evidence exists, but it is not a terminal rule"
    else:
        recommended_next_action = "diagnose_second_pass_detector_coverage"
        reason = "second-pass evidence is insufficient"
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "frame_summary": str(args.frame_summary or contract.get("source", {}).get("frame_summary")),
            "detector_associations": str(
                args.detector_associations or contract.get("source", {}).get("detector_associations")
            ),
            "detector_summary": str(args.detector_summary or contract.get("source", {}).get("detector_summary")),
        },
        "source_gate": {
            "passes_detector_substrate_gate": detector_gate.get("passes_detector_substrate_gate"),
            "detector_rows": detector_summary.get("detector_rows"),
            "detector_box_rate": detector_summary.get("detector_box_rate"),
            "sam2_mask_rate": detector_summary.get("sam2_mask_rate"),
            "candidate_association_rate": detector_summary.get("candidate_association_rate"),
            "rows_with_candidate_association": detector_summary.get("rows_with_candidate_association"),
            "associated_candidate_heading_count": detector_summary.get("associated_candidate_heading_count"),
            "association_depth_tolerance_m": detector_summary.get("association_depth_tolerance_m"),
            "paper_claim_allowed": detector_summary.get("paper_claim_allowed"),
        },
        "view_evidence_rows": len(view_rows),
        "pair_evidence_rows": len(pair_rows),
        "request_evidence_rows": len(request_rows),
        "detector_rows": detector_summary.get("detector_rows"),
        "association_rows": len(association_rows),
        "role_counts": dict(sorted(role_counts.items())),
        "associated_rows_by_role": dict(sorted(associated_rows_by_role.items())),
        "associated_heading_count_by_role": dict(sorted(associated_heading_by_role.items())),
        "pair_rows_by_request": {
            request_id: len(group)
            for request_id, group in sorted(group_by_request(pair_rows).items(), key=lambda item: request_sort_key(item[0]))
        },
        "rival_region_pair_status_counts": dict(sorted(status_counts.items())),
        "request_nonterminal_action_counts": dict(sorted(request_action_counts.items())),
        "missing_role_pair_count": sum(1 for row in pair_rows if row.get("missing_roles")),
        "all_pairs_have_three_roles": all_pairs_have_three_roles,
        "terminal_commit_rows": len(terminal_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "simpler_alternatives": simpler_alternative_report(pair_rows, request_rows),
        "diagnostic_conclusion": {
            "unique_support_rival_region_signal_ready": gate["unique_support_rival_region_evidence_gate_passed"],
            "recommended_next_action": recommended_next_action,
            "reason": reason,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
        },
        "gate": gate,
        "interpretation": {
            "fact": "The analyzer aggregates second-pass swapped candidate-view detector associations into nonterminal rival-region evidence rows.",
            "agent_inference": "Second-pass support mostly indicates unresolved cross-region overlap rather than a safe terminal goal-validity rule.",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "output_files": {
            "view_evidence_rows": "unique_support_rival_region_view_evidence_rows.jsonl",
            "pair_evidence_rows": "unique_support_rival_region_pair_evidence_rows.jsonl",
            "request_evidence_rows": "unique_support_rival_region_request_evidence_rows.jsonl",
            "summary": "unique_support_rival_region_evidence_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    frame_rows = load_jsonl(source_path(args, contract, "frame_summary", "frame_summary"))
    association_rows = load_jsonl(source_path(args, contract, "detector_associations", "detector_associations"))
    detector_summary = load_json(source_path(args, contract, "detector_summary", "detector_summary"))
    view_rows = build_view_rows(frame_rows, association_rows)
    pair_rows = build_pair_rows(view_rows)
    request_rows = build_request_rows(pair_rows)
    summary = summarize(
        contract=contract,
        detector_summary=detector_summary,
        association_rows=association_rows,
        view_rows=view_rows,
        pair_rows=pair_rows,
        request_rows=request_rows,
        args=args,
    )
    out_root = Path(args.out_root)
    expected_outputs = contract.get("expected_outputs") or {}
    write_jsonl(
        out_root / expected_outputs.get("view_evidence_rows", "unique_support_rival_region_view_evidence_rows.jsonl"),
        view_rows,
    )
    write_jsonl(
        out_root / expected_outputs.get("pair_evidence_rows", "unique_support_rival_region_pair_evidence_rows.jsonl"),
        pair_rows,
    )
    write_jsonl(
        out_root / expected_outputs.get("request_evidence_rows", "unique_support_rival_region_request_evidence_rows.jsonl"),
        request_rows,
    )
    write_json(
        out_root / expected_outputs.get("summary", "unique_support_rival_region_evidence_summary.json"),
        summary,
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate unique-support rival-region post-detector evidence without terminal commits."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--frame-summary")
    parser.add_argument("--detector-associations")
    parser.add_argument("--detector-summary")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
