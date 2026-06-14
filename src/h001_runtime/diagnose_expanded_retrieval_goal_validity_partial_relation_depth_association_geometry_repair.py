import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_partial_relation_depth_evidence import (
    attach_plan_rows,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys
from h001_runtime.diagnose_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy import (
    compact_counter,
    load_json,
    load_jsonl,
    request_id,
    safe_int,
    sort_request_id,
)


SCHEMA_VERSION = (
    "h001.expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair.v1"
)
POLICY_NAME = "partial_relation_depth_association_geometry_repair_diagnostic_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1"
)
PLAN_ROWS_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1/"
    "partial_relation_depth_observation_plan.jsonl"
)
DETECTOR_SUMMARY_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_detector_substrate_v1/"
    "expanded_retrieval_detector_substrate_summary.json"
)
DETECTOR_ASSOCIATIONS_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_detector_substrate_v1/"
    "expanded_retrieval_detector_associations.jsonl"
)
DETECTOR_FRAME_SUMMARY_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_detector_substrate_v1/"
    "expanded_retrieval_detector_frame_summary.jsonl"
)
PROJECTION_SUMMARY_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_projection_v1/"
    "projection_anchor_smoke_summary.json"
)
PROJECTION_ROWS_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_projection_v1/"
    "projection_anchor_smoke_rows.jsonl"
)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def decision_id(row: Dict[str, Any]) -> str:
    return str(row.get("decision_id") or "")


def failed_index(row: Dict[str, Any]) -> Optional[int]:
    if row.get("failed_evidence_index") is None:
        return None
    return safe_int(row.get("failed_evidence_index"))


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def finite_stats(values: Sequence[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(clean), "mean": sum(clean) / len(clean), "max": max(clean)}


def target_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (request_id(row), candidate_id(row))


def frame_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (request_id(row), candidate_id(row))


def sort_branch_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            sort_request_id(request_id(row)),
            safe_int(row.get("failed_evidence_index"), 999999),
            candidate_id(row),
        ),
    )


def attach_plan_index(
    plan_rows: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    attached = attach_plan_rows(plan_rows, frame_rows)
    output: Dict[str, Dict[str, Any]] = {}
    for item in attached:
        frame = dict(item["frame"])
        plan = dict(item["plan"])
        output[decision_id(frame)] = {"plan": plan, "frame": frame}
    return output


def group_by_decision(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[decision_id(row)].append(dict(row))
    return grouped


def count_rows(rows: Sequence[Dict[str, Any]], key: str, value: Any = True) -> int:
    return sum(row.get(key) is value for row in rows)


def status_counts(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, int]:
    return compact_counter(row.get(key) for row in rows)


def association_profile(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    inside_mask = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    inside_box = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    visible = [row for row in rows if str(row.get("projection_status")) == "visible"]
    depth_consistent = [
        row for row in rows if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    depth_mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
    depth_agreements = [safe_float(row.get("depth_agreement_m")) for row in rows]
    associated_depth_errors = [safe_float(row.get("depth_error_m")) for row in associated]
    return {
        "association_rows": len(rows),
        "associated_heading_count": len(associated),
        "visible_count": len(visible),
        "inside_box_count": len(inside_box),
        "inside_mask_count": len(inside_mask),
        "depth_consistent_count": len(depth_consistent),
        "depth_mismatch_count": len(depth_mismatch),
        "projection_status_counts": status_counts(rows, "projection_status"),
        "depth_check_status_counts": status_counts(rows, "depth_check_status"),
        "projection_anchor_offset_counts": status_counts(rows, "projection_anchor_height_offset_m"),
        "associated_offsets_m": sorted(
            {
                safe_float(row.get("projection_anchor_height_offset_m"))
                for row in associated
                if safe_float(row.get("projection_anchor_height_offset_m")) is not None
            }
        ),
        "inside_mask_offsets_m": sorted(
            {
                safe_float(row.get("projection_anchor_height_offset_m"))
                for row in inside_mask
                if safe_float(row.get("projection_anchor_height_offset_m")) is not None
            }
        ),
        "depth_error_stats_m": finite_stats(depth_errors),
        "depth_agreement_stats_m": finite_stats(depth_agreements),
        "associated_depth_error_stats_m": finite_stats(associated_depth_errors),
    }


def projection_profile(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    anchor_rows = [anchor for row in rows for anchor in list(row.get("projection_anchor_rows") or [])]
    return {
        "projection_rows": len(rows),
        "projection_anchor_rows": len(anchor_rows),
        "projection_anchor_visible_rows": count_rows(rows, "projection_anchor_visible", True),
        "projection_anchor_visible_heading_rows": sum(
            safe_int(row.get("projection_anchor_visible_heading_rows"), 0) for row in rows
        ),
        "projection_status_counts": status_counts(anchor_rows, "projection_status"),
        "projection_axis_counts": status_counts(anchor_rows, "projection_axis_status"),
    }


def plan_frame_slice(
    *,
    branch_row: Dict[str, Any],
    plan_by_decision: Dict[str, Dict[str, Any]],
    exact_failed_index: bool,
) -> List[Dict[str, Dict[str, Any]]]:
    rid, cid = target_key(branch_row)
    target_failed_index = failed_index(branch_row)
    items = []
    for item in plan_by_decision.values():
        plan = item["plan"]
        frame = item["frame"]
        if frame_key(plan) != (rid, cid):
            continue
        if exact_failed_index and failed_index(plan) != target_failed_index:
            continue
        if not exact_failed_index and failed_index(plan) == target_failed_index:
            continue
        items.append({"plan": plan, "frame": frame})
    return sorted(
        items,
        key=lambda item: (
            safe_int(item["plan"].get("failed_evidence_index"), 999999),
            safe_int(item["plan"].get("completion_index"), 999999),
            decision_id(item["frame"]),
        ),
    )


def decision_ids(items: Sequence[Dict[str, Dict[str, Any]]]) -> List[str]:
    return [decision_id(item["frame"]) for item in items if decision_id(item["frame"])]


def rows_for_decisions(
    rows_by_decision: Dict[str, List[Dict[str, Any]]],
    ids: Sequence[str],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for did in ids:
        output.extend(rows_by_decision.get(did, []))
    return output


def frame_profile(items: Sequence[Dict[str, Dict[str, Any]]]) -> Dict[str, Any]:
    frames = [item["frame"] for item in items]
    plans = [item["plan"] for item in items]
    return {
        "frame_rows": len(frames),
        "decision_ids": decision_ids(items),
        "requested_direction_sources": sorted({str(row.get("requested_direction_source")) for row in plans}),
        "actual_standoff_direction_sources": sorted({str(row.get("standoff_direction_source")) for row in plans}),
        "relation_anchor_candidate_ids": sorted(
            {str(row.get("standoff_relation_anchor_candidate_id")) for row in plans}
        ),
        "viewpoint_sources": sorted({str(row.get("viewpoint_source")) for row in plans}),
        "fallback_direction_rows": sum(
            str(row.get("requested_direction_source") or "")
            != str(row.get("standoff_direction_source") or "")
            for row in plans
        ),
        "navmesh_snapped_rows": count_rows(frames, "standoff_navmesh_snapped", True),
        "navmesh_navigable_rows": count_rows(frames, "standoff_navmesh_navigable", True),
        "has_candidate_association_rows": count_rows(frames, "has_candidate_association", True),
        "associated_candidate_heading_count": sum(
            safe_int(row.get("associated_candidate_heading_count"), 0) for row in frames
        ),
    }


def classify_repair(
    *,
    exact_association: Dict[str, Any],
    exact_projection: Dict[str, Any],
    other_same_requested_association_count: int,
    other_direction_association_count: int,
    fallback_direction_rows: int,
) -> Tuple[str, str]:
    if safe_int(exact_association.get("associated_heading_count"), 0) > 0:
        if safe_int(exact_association.get("depth_consistent_count"), 0) > 0:
            return (
                "repair_candidate_association_recovered",
                "exact failed completion view already has candidate association and depth-consistent signal",
            )
        return (
            "request_mask_depth_agreement_recheck",
            "exact failed completion view has candidate association but no depth-consistent completion",
        )
    if other_same_requested_association_count > 0:
        return (
            "request_anchor_selection_repair_for_association_geometry",
            "same requested direction can associate the candidate under another relation-anchor or completion row",
        )
    if other_direction_association_count > 0:
        return (
            "request_direction_specific_reobservation_repair",
            "candidate is associable from another standoff direction but not from the failed completion view",
        )
    if fallback_direction_rows > 0:
        return (
            "request_navmesh_fallback_viewpoint_repair",
            "requested relation direction fell back to a different standoff direction without candidate association",
        )
    if safe_int(exact_association.get("inside_mask_count"), 0) > 0:
        return (
            "request_mask_depth_agreement_repair_for_association_geometry",
            "failed completion view has inside-mask evidence but no candidate association",
        )
    if safe_int(exact_projection.get("projection_anchor_visible_heading_rows"), 0) > 0:
        return (
            "request_projection_anchor_or_viewpoint_repair",
            "projection anchor is visible but detector-mask association is not available",
        )
    return (
        "defer_association_geometry_unresolved",
        "no repairable projection or association evidence is available in this diagnostic substrate",
    )


def build_repair_rows(
    *,
    branch_rows: Sequence[Dict[str, Any]],
    plan_by_decision: Dict[str, Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
    projection_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    association_by_decision = group_by_decision(association_rows)
    projection_by_decision = group_by_decision(projection_rows)
    output: List[Dict[str, Any]] = []
    for branch_row in sort_branch_rows(branch_rows):
        exact_items = plan_frame_slice(
            branch_row=branch_row,
            plan_by_decision=plan_by_decision,
            exact_failed_index=True,
        )
        other_items = plan_frame_slice(
            branch_row=branch_row,
            plan_by_decision=plan_by_decision,
            exact_failed_index=False,
        )
        exact_ids = decision_ids(exact_items)
        other_ids = decision_ids(other_items)
        exact_associations = rows_for_decisions(association_by_decision, exact_ids)
        other_associations = rows_for_decisions(association_by_decision, other_ids)
        exact_projections = rows_for_decisions(projection_by_decision, exact_ids)
        exact_profile = association_profile(exact_associations)
        other_profile = association_profile(other_associations)
        exact_frame_profile = frame_profile(exact_items)
        other_frame_profile = frame_profile(other_items)
        requested_directions = set(exact_frame_profile["requested_direction_sources"])
        other_same_requested_ids = [
            decision_id(item["frame"])
            for item in other_items
            if str(item["plan"].get("requested_direction_source")) in requested_directions
        ]
        other_direction_ids = [
            decision_id(item["frame"])
            for item in other_items
            if str(item["plan"].get("requested_direction_source")) not in requested_directions
        ]
        same_requested_assoc = association_profile(rows_for_decisions(association_by_decision, other_same_requested_ids))
        other_direction_assoc = association_profile(rows_for_decisions(association_by_decision, other_direction_ids))
        exact_projection = projection_profile(exact_projections)
        repair_action, repair_reason = classify_repair(
            exact_association=exact_profile,
            exact_projection=exact_projection,
            other_same_requested_association_count=safe_int(
                same_requested_assoc.get("associated_heading_count"), 0
            ),
            other_direction_association_count=safe_int(
                other_direction_assoc.get("associated_heading_count"), 0
            ),
            fallback_direction_rows=safe_int(exact_frame_profile.get("fallback_direction_rows"), 0),
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_association_geometry_repair_row",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id(branch_row),
                "rival_identity_request_id": branch_row.get("rival_identity_request_id"),
                "episode_key": branch_row.get("episode_key"),
                "scene_key": branch_row.get("scene_key"),
                "scene_id": branch_row.get("scene_id"),
                "query": branch_row.get("query"),
                "candidate_id": candidate_id(branch_row),
                "target_candidate_id": candidate_id(branch_row),
                "failed_evidence_index": branch_row.get("failed_evidence_index"),
                "source_branch_action": branch_row.get("branch_action"),
                "source_residual_failure_class": branch_row.get("residual_failure_class"),
                "source_prior_standoff_direction_source": branch_row.get("prior_standoff_direction_source"),
                "source_completion_inside_mask_count": branch_row.get("completion_inside_mask_count"),
                "source_completion_associated_heading_count": branch_row.get(
                    "completion_associated_heading_count"
                ),
                "source_completion_depth_consistent_count": branch_row.get(
                    "completion_depth_consistent_count"
                ),
                "exact_failed_completion_frame": exact_frame_profile,
                "exact_failed_completion_association": exact_profile,
                "exact_failed_completion_projection": exact_projection,
                "other_completion_frame": other_frame_profile,
                "other_completion_association": other_profile,
                "same_requested_direction_association": same_requested_assoc,
                "other_requested_direction_association": other_direction_assoc,
                "repair_diagnostic_action": repair_action,
                "repair_diagnostic_reason": repair_reason,
                "allowed_repair_checks": [
                    "projection_anchor_replay",
                    "mask_depth_agreement_recheck",
                    "candidate_geometry_sanity_check",
                ],
                "blocked_shortcuts": [
                    "commit_partial_relation_depth_candidate",
                    "reject_partial_relation_depth_candidate_as_invalid",
                    "commit_by_inside_mask_presence",
                    "label_tuned_threshold_change",
                ],
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_request_rows(repair_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in repair_rows:
        grouped[request_id(row)].append(row)
    output: List[Dict[str, Any]] = []
    for rid, rows in sorted(grouped.items(), key=lambda item: sort_request_id(item[0])):
        exemplar = rows[0]
        action_counts = compact_counter(row.get("repair_diagnostic_action") for row in rows)
        exact_assoc_total = sum(
            safe_int(row["exact_failed_completion_association"].get("associated_heading_count"), 0)
            for row in rows
        )
        same_requested_total = sum(
            safe_int(row["same_requested_direction_association"].get("associated_heading_count"), 0)
            for row in rows
        )
        other_direction_total = sum(
            safe_int(row["other_requested_direction_association"].get("associated_heading_count"), 0)
            for row in rows
        )
        if same_requested_total > 0:
            next_action = "design_relation_anchor_selection_repair_contract"
        elif other_direction_total > 0:
            next_action = "design_direction_specific_reobservation_repair_contract"
        elif exact_assoc_total > 0:
            next_action = "design_mask_depth_agreement_recheck_contract"
        else:
            next_action = "defer_association_geometry_branch_unresolved"
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_association_geometry_repair_request",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "repair_branch_rows": len(rows),
                "candidate_ids": sorted({str(row.get("candidate_id")) for row in rows}),
                "repair_diagnostic_action_counts": action_counts,
                "exact_failed_completion_associated_heading_count": exact_assoc_total,
                "same_requested_direction_associated_heading_count": same_requested_total,
                "other_requested_direction_associated_heading_count": other_direction_total,
                "request_repair_next_action": next_action,
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def summarize(
    *,
    contract: Dict[str, Any],
    branch_summary: Dict[str, Any],
    detector_summary: Dict[str, Any],
    projection_summary: Dict[str, Any],
    repair_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    minimum = contract.get("minimum_repair_gate") or {}
    action_rows = [*repair_rows, *request_rows]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [
        row
        for row in action_rows
        if row.get("terminal_commit") is True or row.get("terminal_arbitration_allowed") is True
    ]
    branch_gate = branch_summary.get("gate") or {}
    detector_gate = detector_summary.get("gate") or {}
    projection_gate = projection_summary.get("gate") or {}
    expected_queries = {
        str(key): safe_int(value)
        for key, value in source_gate.get("expected_target_queries", {}).items()
    }
    expected_candidate_ids = sorted(str(value) for value in source_gate.get("expected_target_candidate_ids", []))
    candidate_ids = sorted({str(row.get("candidate_id")) for row in repair_rows})
    query_counts = compact_counter(row.get("query") for row in repair_rows)
    source_class_counts = compact_counter(row.get("source_residual_failure_class") for row in repair_rows)
    repair_action_counts = compact_counter(row.get("repair_diagnostic_action") for row in repair_rows)
    request_action_counts = compact_counter(row.get("request_repair_next_action") for row in request_rows)
    exact_associated = sum(
        safe_int(row["exact_failed_completion_association"].get("associated_heading_count"), 0)
        for row in repair_rows
    )
    exact_inside_mask = sum(
        safe_int(row["exact_failed_completion_association"].get("inside_mask_count"), 0)
        for row in repair_rows
    )
    exact_depth_consistent = sum(
        safe_int(row["exact_failed_completion_association"].get("depth_consistent_count"), 0)
        for row in repair_rows
    )
    same_requested_associated = sum(
        safe_int(row["same_requested_direction_association"].get("associated_heading_count"), 0)
        for row in repair_rows
    )
    other_direction_associated = sum(
        safe_int(row["other_requested_direction_association"].get("associated_heading_count"), 0)
        for row in repair_rows
    )
    gate = {
        "source_branch_handling_gate_passed": branch_gate.get(
            "partial_relation_depth_branch_handling_gate_passed"
        )
        is bool(source_gate.get("partial_relation_depth_branch_handling_gate_passed", True)),
        "detector_substrate_gate_passed": detector_gate.get("passes_detector_substrate_gate") is True,
        "projection_anchor_smoke_gate_passed": projection_gate.get("projection_anchor_smoke_passed") is True,
        "expected_target_branch_rows_passed": len(repair_rows)
        == safe_int(source_gate.get("expected_target_branch_rows"), -1),
        "expected_target_request_rows_passed": len(request_rows)
        == safe_int(source_gate.get("expected_target_request_rows"), -1),
        "expected_target_queries_passed": query_counts == expected_queries,
        "expected_target_candidate_ids_passed": candidate_ids == expected_candidate_ids,
        "expected_target_residual_failure_class_counts_passed": source_class_counts
        == {
            str(key): safe_int(value)
            for key, value in (
                source_gate.get("expected_target_residual_failure_class_counts") or {}
            ).items()
        },
        "exact_failed_completion_rows_accounted_passed": all(
            safe_int(row["exact_failed_completion_frame"].get("frame_rows"), 0) > 0 for row in repair_rows
        ),
        "all_target_requests_accounted_passed": bool(minimum.get("all_target_requests_accounted", True))
        is (len(request_rows) == safe_int(source_gate.get("expected_target_request_rows"), -1)),
        "all_target_branch_rows_accounted_passed": bool(minimum.get("all_target_branch_rows_accounted", True))
        is (len(repair_rows) == safe_int(source_gate.get("expected_target_branch_rows"), -1)),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(minimum.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows)
        and detector_summary.get("uses_gt_for_action") is False
        and projection_summary.get("uses_gt_for_action") is False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["association_geometry_repair_diagnostic_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key not in {"terminal_utility_validation_allowed", "paper_claim_allowed"}
    )
    if same_requested_associated:
        next_task = "design_relation_anchor_selection_repair_contract"
    elif other_direction_associated:
        next_task = "design_direction_specific_reobservation_repair_contract"
    else:
        next_task = "defer_association_geometry_branch_and_design_depth_stagnation_branch_contract"
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "branch_summary": str(args.branch_summary),
            "branch_rows": str(args.branch_rows),
            "request_branch_rows": str(args.request_branch_rows),
            "plan_rows": str(args.plan_rows),
            "detector_summary": str(args.detector_summary),
            "detector_associations": str(args.detector_associations),
            "detector_frame_summary": str(args.detector_frame_summary),
            "projection_summary": str(args.projection_summary),
            "projection_rows": str(args.projection_rows),
        },
        "repair_rows": len(repair_rows),
        "repair_request_rows": len(request_rows),
        "query_counts": query_counts,
        "candidate_ids": candidate_ids,
        "source_residual_failure_class_counts": source_class_counts,
        "repair_diagnostic_action_counts": repair_action_counts,
        "request_repair_next_action_counts": request_action_counts,
        "exact_failed_completion_associated_heading_count": exact_associated,
        "exact_failed_completion_inside_mask_count": exact_inside_mask,
        "exact_failed_completion_depth_consistent_count": exact_depth_consistent,
        "same_requested_direction_associated_heading_count": same_requested_associated,
        "other_requested_direction_associated_heading_count": other_direction_associated,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "association_geometry_repair_signal_ready": gate[
                "association_geometry_repair_diagnostic_gate_passed"
            ],
            "recommended_next_task": next_task,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
        },
        "blocked_downstream_tasks": [
            "terminal_utility_contract",
            "first_eval_rerun",
            "policy_scale_comparison",
            "paper_claim",
        ],
        "output_files": {
            "repair_rows": "partial_relation_depth_association_geometry_repair_rows.jsonl",
            "repair_request_rows": "partial_relation_depth_association_geometry_repair_request_rows.jsonl",
            "summary": "partial_relation_depth_association_geometry_repair_summary.json",
        },
        "interpretation": {
            "fact": (
                "The diagnostic consumes nonterminal branch rows and detector/projection artifacts. "
                "It does not join evaluation labels."
            ),
            "agent_inference": (
                "The exact failed completion views still do not justify terminal goal validity. "
                "Their repair signal should be used to design another nonterminal observation or "
                "relation-anchor repair contract."
            ),
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.branch_summary = source_path(args, contract, "branch_summary", "branch_handling_summary")
    args.branch_rows = source_path(args, contract, "branch_rows", "branch_rows")
    args.request_branch_rows = source_path(args, contract, "request_branch_rows", "request_branch_rows")

    branch_summary = load_json(args.branch_summary)
    branch_rows = load_jsonl(args.branch_rows)
    load_jsonl(args.request_branch_rows)
    plan_rows = load_jsonl(args.plan_rows)
    detector_summary = load_json(args.detector_summary)
    detector_associations = load_jsonl(args.detector_associations)
    detector_frame_summary = load_jsonl(args.detector_frame_summary)
    projection_summary = load_json(args.projection_summary)
    projection_rows = load_jsonl(args.projection_rows)

    target_action = str((contract.get("source_gate") or {}).get("target_branch_action"))
    target_branch_rows = [
        row for row in branch_rows if str(row.get("branch_action")) == target_action
    ]
    plan_by_decision = attach_plan_index(plan_rows, detector_frame_summary)
    repair_rows = build_repair_rows(
        branch_rows=target_branch_rows,
        plan_by_decision=plan_by_decision,
        association_rows=detector_associations,
        projection_rows=projection_rows,
    )
    request_rows = build_request_rows(repair_rows)
    summary = summarize(
        contract=contract,
        branch_summary=branch_summary,
        detector_summary=detector_summary,
        projection_summary=projection_summary,
        repair_rows=repair_rows,
        request_rows=request_rows,
        args=args,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "partial_relation_depth_association_geometry_repair_rows.jsonl", repair_rows)
    write_jsonl(
        out_root / "partial_relation_depth_association_geometry_repair_request_rows.jsonl",
        request_rows,
    )
    write_json(out_root / "partial_relation_depth_association_geometry_repair_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose frozen partial relation-depth association-geometry underlink rows "
            "without terminal commit or evaluation-label join."
        )
    )
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--branch-summary", type=Path)
    parser.add_argument("--branch-rows", type=Path)
    parser.add_argument("--request-branch-rows", type=Path)
    parser.add_argument("--plan-rows", type=Path, default=Path(PLAN_ROWS_DEFAULT))
    parser.add_argument("--detector-summary", type=Path, default=Path(DETECTOR_SUMMARY_DEFAULT))
    parser.add_argument("--detector-associations", type=Path, default=Path(DETECTOR_ASSOCIATIONS_DEFAULT))
    parser.add_argument("--detector-frame-summary", type=Path, default=Path(DETECTOR_FRAME_SUMMARY_DEFAULT))
    parser.add_argument("--projection-summary", type=Path, default=Path(PROJECTION_SUMMARY_DEFAULT))
    parser.add_argument("--projection-rows", type=Path, default=Path(PROJECTION_ROWS_DEFAULT))
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["association_geometry_repair_diagnostic_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
