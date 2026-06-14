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


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_goal_region_evidence.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1"
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


def candidate_id(row: Dict[str, Any], key: str = "target_candidate_id") -> str:
    return str(row.get(key) or row.get("candidate_id") or "")


def decision_id(row: Dict[str, Any]) -> str:
    return str(row.get("decision_id") or "")


def role_from_view(row: Dict[str, Any]) -> str:
    if str(row.get("viewpoint_source")) == "common_pair_navmesh":
        return "common_pair_view"
    target = candidate_id(row, "target_candidate_id")
    if target and target == str(row.get("focus_candidate_id")):
        return "focus_own_view"
    if target and target == str(row.get("rival_candidate_id")):
        return "rival_own_view"
    return "unknown_goal_region_view"


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
        row
        for row in rows
        if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    depth_mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    out_of_fov = [row for row in rows if str(row.get("projection_status")) == "out_of_fov"]
    box_scores = [safe_float(row.get("best_box_score")) for row in rows]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
    associated_depth_errors = [safe_float(row.get("depth_error_m")) for row in associated]
    camera_forward = [safe_float(row.get("camera_forward_m")) for row in rows]
    mask_depths = [safe_float(row.get("mask_depth_median")) for row in rows]
    return {
        "association_rows": len(rows),
        "associated_heading_count_from_rows": len(associated),
        "visible_count": len(visible),
        "inside_box_count": len(inside_box),
        "inside_mask_count": len(inside_mask),
        "depth_consistent_count": len(depth_consistent),
        "depth_match_count": len(depth_consistent),
        "depth_mismatch_count": len(depth_mismatch),
        "out_of_fov_count": len(out_of_fov),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in rows),
        "projection_anchor_offset_counts": compact_counter(row.get("projection_anchor_height_offset_m") for row in rows),
        "best_box_score_max": max([score for score in box_scores if score is not None], default=None),
        "best_box_score_mean": mean(box_scores),
        "depth_error_stats_m": finite_stats(depth_errors),
        "associated_depth_error_stats_m": finite_stats(associated_depth_errors),
        "camera_forward_stats_m": finite_stats(camera_forward),
        "mask_depth_stats_m": finite_stats(mask_depths),
    }


def view_evidence_row(frame_row: Dict[str, Any], association_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    role = role_from_view(frame_row)
    stats = association_stats(association_rows)
    support = frame_row.get("has_candidate_association") is True
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_goal_region_view_evidence",
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
        "view_role": role,
        "viewpoint_source": frame_row.get("viewpoint_source"),
        "planner_name": frame_row.get("planner_name"),
        "focus_candidate_id": frame_row.get("focus_candidate_id"),
        "rival_candidate_id": frame_row.get("rival_candidate_id"),
        "target_candidate_id": frame_row.get("target_candidate_id"),
        "target_candidate_role": role,
        "selected_candidate_ids": frame_row.get("selected_candidate_ids"),
        "selected_candidate_count": frame_row.get("selected_candidate_count"),
        "candidate_selection_source": frame_row.get("candidate_selection_source"),
        "focus_rival_span_m": frame_row.get("focus_rival_span_m"),
        "focus_position": frame_row.get("focus_position"),
        "rival_position": frame_row.get("rival_position"),
        "pair_midpoint": frame_row.get("pair_midpoint"),
        "target_position": frame_row.get("target_position"),
        "target_visit_position": frame_row.get("target_visit_position"),
        "target_distance_from_viewpoint_m": frame_row.get("target_distance_from_viewpoint_m"),
        "focus_distance_from_viewpoint_m": frame_row.get("focus_distance_from_viewpoint_m"),
        "rival_distance_from_viewpoint_m": frame_row.get("rival_distance_from_viewpoint_m"),
        "standoff_direction_source": frame_row.get("standoff_direction_source"),
        "standoff_distance_requested": frame_row.get("standoff_distance_requested"),
        "standoff_target_horizontal_distance": frame_row.get("standoff_target_horizontal_distance"),
        "standoff_navmesh_navigable": frame_row.get("standoff_navmesh_navigable"),
        "standoff_navmesh_snapped": frame_row.get("standoff_navmesh_snapped"),
        "standoff_projection_sane": frame_row.get("standoff_projection_sane"),
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
        **stats,
        "goal_region_view_evidence_status": "supported_candidate_view" if support else "unsupported_candidate_view",
        "recommended_nonterminal_action": "aggregate_pair_goal_region_evidence",
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
    rows = [
        view_evidence_row(frame_row, associations_by_decision.get(decision_id(frame_row), []))
        for frame_row in frame_rows
    ]
    rows.sort(
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            safe_int(row.get("pair_index"), 999999),
            {"focus_own_view": 0, "rival_own_view": 1, "common_pair_view": 2}.get(str(row.get("role")), 99),
            str(row.get("decision_id")),
        )
    )
    return rows


def pair_status(focus_support: bool, rival_support: bool, missing_roles: Sequence[str]) -> str:
    if missing_roles or not focus_support:
        return "insufficient_detector_pair"
    if rival_support:
        return "ambiguous_goal_region_pair"
    return "contrastive_goal_region_pair"


def pair_action(status: str) -> str:
    if status == "contrastive_goal_region_pair":
        return "request_goal_region_arbitration"
    if status == "ambiguous_goal_region_pair":
        return "request_additional_rival_region_evidence"
    return "defer_goal_region_unresolved"


def build_pair_rows(view_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    required_roles = ["focus_own_view", "rival_own_view", "common_pair_view"]
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
        for row in group:
            role = str(row.get("role"))
            if role in by_role:
                duplicate_roles[role] = duplicate_roles.get(role, 1) + 1
            else:
                by_role[role] = row
        missing_roles = [role for role in required_roles if role not in by_role]
        focus = by_role.get("focus_own_view") or {}
        rival = by_role.get("rival_own_view") or {}
        common = by_role.get("common_pair_view") or {}
        focus_support = focus.get("has_candidate_association") is True
        rival_support = rival.get("has_candidate_association") is True
        common_support = common.get("has_candidate_association") is True
        status = pair_status(focus_support, rival_support, missing_roles)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_goal_region_pair_evidence",
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
                "required_roles": required_roles,
                "present_roles": sorted(by_role.keys()),
                "missing_roles": missing_roles,
                "duplicate_role_counts": duplicate_roles,
                "focus_own_support": focus_support,
                "rival_own_support": rival_support,
                "common_focus_support": common_support,
                "focus_own_associated_heading_count": safe_int(focus.get("associated_candidate_heading_count"), 0),
                "rival_own_associated_heading_count": safe_int(rival.get("associated_candidate_heading_count"), 0),
                "common_focus_associated_heading_count": safe_int(common.get("associated_candidate_heading_count"), 0),
                "focus_own_detector_box_count": focus.get("detector_box_count"),
                "rival_own_detector_box_count": rival.get("detector_box_count"),
                "common_focus_detector_box_count": common.get("detector_box_count"),
                "focus_own_sam2_mask_count": focus.get("sam2_mask_count"),
                "rival_own_sam2_mask_count": rival.get("sam2_mask_count"),
                "common_focus_sam2_mask_count": common.get("sam2_mask_count"),
                "focus_own_view_decision_id": focus.get("decision_id"),
                "rival_own_view_decision_id": rival.get("decision_id"),
                "common_pair_view_decision_id": common.get("decision_id"),
                "focus_rival_span_m": exemplar.get("focus_rival_span_m"),
                "goal_region_evidence_status": status,
                "recommended_nonterminal_action": pair_action(status),
                "recommended_nonterminal_reason": reason_for_pair_status(status),
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def reason_for_pair_status(status: str) -> str:
    if status == "contrastive_goal_region_pair":
        return "focus own-view support is present while rival own-view support is absent; this can only request nonterminal arbitration."
    if status == "ambiguous_goal_region_pair":
        return "both focus and rival own-views are supported, so detector evidence cannot disambiguate the pair."
    return "required role evidence is missing or focus own-view support is absent."


def request_action(contrastive_count: int, ambiguous_count: int, insufficient_count: int) -> str:
    if ambiguous_count > 0:
        return "request_additional_rival_region_evidence"
    if contrastive_count > 0:
        return "request_goal_region_arbitration"
    if insufficient_count > 0:
        return "defer_goal_region_unresolved"
    return "defer_goal_region_unresolved"


def request_reason(contrastive_count: int, ambiguous_count: int, insufficient_count: int) -> str:
    if ambiguous_count > 0:
        return "at least one rival pair also has own-view support, so unique support is not goal-validity evidence yet"
    if contrastive_count > 0:
        return "contrastive pair evidence exists but terminal commit still requires a separate fixed arbitration contract"
    if insufficient_count > 0:
        return "detector support is insufficient for the focus or required pair roles"
    return "no pair-level evidence rows were available"


def build_request_rows(pair_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for request_id, group in sorted(group_by_request(pair_rows).items(), key=lambda item: request_sort_key(item[0])):
        if not request_id:
            continue
        exemplar = group[0]
        status_counts = Counter(str(row.get("goal_region_evidence_status")) for row in group)
        contrastive_count = status_counts.get("contrastive_goal_region_pair", 0)
        ambiguous_count = status_counts.get("ambiguous_goal_region_pair", 0)
        insufficient_count = status_counts.get("insufficient_detector_pair", 0)
        action = request_action(contrastive_count, ambiguous_count, insufficient_count)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_unique_support_goal_region_request_evidence",
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
                "focus_own_supported_pair_count": sum(1 for row in group if row.get("focus_own_support") is True),
                "rival_own_supported_pair_count": sum(1 for row in group if row.get("rival_own_support") is True),
                "common_focus_supported_pair_count": sum(1 for row in group if row.get("common_focus_support") is True),
                "contrastive_goal_region_pair_count": contrastive_count,
                "ambiguous_goal_region_pair_count": ambiguous_count,
                "insufficient_detector_pair_count": insufficient_count,
                "goal_region_evidence_status_counts": dict(sorted(status_counts.items())),
                "recommended_nonterminal_action": action,
                "recommended_nonterminal_reason": request_reason(
                    contrastive_count,
                    ambiguous_count,
                    insufficient_count,
                ),
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def simpler_alternative_report(pair_rows: Sequence[Dict[str, Any]], request_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    pair_status_counts = Counter(str(row.get("goal_region_evidence_status")) for row in pair_rows)
    focus_supported = sum(1 for row in pair_rows if row.get("focus_own_support") is True)
    rival_supported = sum(1 for row in pair_rows if row.get("rival_own_support") is True)
    common_supported = sum(1 for row in pair_rows if row.get("common_focus_support") is True)
    request_action_counts = Counter(str(row.get("recommended_nonterminal_action")) for row in request_rows)
    return {
        "direct_unique_support_commit": {
            "decision": "blocked",
            "would_emit_terminal_commit_rows": len(request_rows),
            "reason": "the source branch is visibility-not-goal-validity; direct commit would repeat the diagnosed failure mechanism",
        },
        "focus_own_support_only": {
            "decision": "rejected_as_terminal_rule",
            "focus_supported_pairs": focus_supported,
            "pair_rows": len(pair_rows),
            "reason": "focus own-view support is saturated in this substrate and cannot distinguish goal validity",
        },
        "rival_absence_as_goal_validity": {
            "decision": "diagnostic_only",
            "contrastive_pairs": pair_status_counts.get("contrastive_goal_region_pair", 0),
            "ambiguous_pairs": pair_status_counts.get("ambiguous_goal_region_pair", 0),
            "reason": "missing rival association may indicate detector/viewpoint failure rather than true region separation",
        },
        "association_count_best": {
            "decision": "diagnostic_only",
            "focus_supported_pairs": focus_supported,
            "rival_supported_pairs": rival_supported,
            "common_focus_supported_pairs": common_supported,
            "reason": "association count measures view evidence strength, not ObjectNav goal identity",
        },
        "defer_all": {
            "decision": "safe_but_inert",
            "nonterminal_actions_lost": dict(sorted(request_action_counts.items())),
            "reason": "keeps safety but cannot test whether goal-region evidence can reduce over-deferral",
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
    required_gates = contract.get("required_gates") or {}
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
    pair_status_counts = Counter(str(row.get("goal_region_evidence_status")) for row in pair_rows)
    request_action_counts = Counter(str(row.get("recommended_nonterminal_action")) for row in request_rows)
    missing_role_pair_count = sum(1 for row in pair_rows if row.get("missing_roles"))
    detector_gate = detector_summary.get("gate") or {}
    all_pairs_have_three_roles = all(not row.get("missing_roles") for row in pair_rows)
    actual_uses_gt_for_action = any(row.get("uses_gt_for_action") is True for row in action_rows)
    source_gate_passed = (
        detector_gate.get("passes_detector_substrate_gate")
        is bool(required_gates.get("source_detector_substrate_gate_passed", True))
    )
    gate = {
        "source_detector_substrate_gate_passed": source_gate_passed,
        "expected_view_evidence_rows_passed": len(view_rows)
        == safe_int(required_gates.get("expected_view_evidence_rows"), 0),
        "expected_pair_evidence_rows_passed": len(pair_rows)
        == safe_int(required_gates.get("expected_pair_evidence_rows"), 0),
        "expected_request_evidence_rows_passed": len(request_rows)
        == safe_int(required_gates.get("expected_request_evidence_rows"), 0),
        "all_pairs_have_three_roles_passed": all_pairs_have_three_roles
        is bool(required_gates.get("all_pairs_have_three_roles", True)),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(required_gates.get("action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(required_gates.get("terminal_commit_rows"), 0),
        "uses_gt_for_action_passed": actual_uses_gt_for_action
        is bool(required_gates.get("uses_gt_for_action", False)),
        "paper_claim_allowed_passed": False is bool(required_gates.get("paper_claim_allowed", False)),
        "pair_status_accounting_passed": sum(pair_status_counts.values()) == len(pair_rows),
        "request_status_accounting_passed": len(request_rows) == len({row_request_id(row) for row in pair_rows}),
        "uses_gt_for_action": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["unique_support_goal_region_evidence_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "uses_gt_for_action",
            "terminal_utility_validation_allowed",
            "paper_claim_allowed",
        }
    )
    if pair_status_counts.get("ambiguous_goal_region_pair", 0) > 0:
        recommended_next_action = "inspect_ambiguous_goal_region_pairs_before_terminal_arbitration"
        reason = "rival own-view support exists for some pairs, so unique support is not yet a direct goal-validity signal"
    elif pair_status_counts.get("contrastive_goal_region_pair", 0) > 0:
        recommended_next_action = "design_fixed_non_gt_goal_region_arbitration_contract"
        reason = "contrastive nonterminal evidence exists, but terminal commit is still blocked"
    else:
        recommended_next_action = "diagnose_goal_region_detector_association_coverage"
        reason = "goal-region evidence is insufficient"
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
        "goal_region_pair_status_counts": dict(sorted(pair_status_counts.items())),
        "request_nonterminal_action_counts": dict(sorted(request_action_counts.items())),
        "missing_role_pair_count": missing_role_pair_count,
        "all_pairs_have_three_roles": all_pairs_have_three_roles,
        "terminal_commit_rows": len(terminal_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "simpler_alternatives": simpler_alternative_report(pair_rows, request_rows),
        "diagnostic_conclusion": {
            "unique_support_goal_region_signal_ready": gate["unique_support_goal_region_evidence_gate_passed"],
            "recommended_next_action": recommended_next_action,
            "reason": reason,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
        },
        "gate": gate,
        "interpretation": {
            "fact": "The analyzer aggregates focus/rival/common-view detector associations into nonterminal goal-region evidence rows.",
            "agent_inference": "Focus own-view support is saturated, while rival own-view support is still present in many pairs; therefore goal-region evidence should be inspected before any terminal arbitration contract.",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "output_files": {
            "view_evidence_rows": "unique_support_goal_region_view_evidence_rows.jsonl",
            "pair_evidence_rows": "unique_support_goal_region_pair_evidence_rows.jsonl",
            "request_evidence_rows": "unique_support_goal_region_request_evidence_rows.jsonl",
            "summary": "unique_support_goal_region_evidence_summary.json",
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
        out_root / expected_outputs.get("view_evidence_rows", "unique_support_goal_region_view_evidence_rows.jsonl"),
        view_rows,
    )
    write_jsonl(
        out_root / expected_outputs.get("pair_evidence_rows", "unique_support_goal_region_pair_evidence_rows.jsonl"),
        pair_rows,
    )
    write_jsonl(
        out_root / expected_outputs.get("request_evidence_rows", "unique_support_goal_region_request_evidence_rows.jsonl"),
        request_rows,
    )
    write_json(
        out_root / expected_outputs.get("summary", "unique_support_goal_region_evidence_summary.json"),
        summary,
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate unique-support goal-region post-detector evidence without terminal commits."
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
