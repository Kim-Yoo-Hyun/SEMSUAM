import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys
from h001_runtime.diagnose_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy import (
    compact_counter,
    load_json,
    load_jsonl,
    request_id,
    safe_int,
)


SCHEMA_VERSION = "h001.association_geometry_underlink_repair_followup_evidence.v1"
POLICY_NAME = "association_geometry_underlink_repair_followup_evidence_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_association_geometry_underlink_repair_followup_evidence_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_association_geometry_underlink_repair_followup_evidence_v1"
)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_path(args: argparse.Namespace, contract: Mapping[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def row_request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def request_sort_key(value: str) -> Tuple[int, str]:
    tail = str(value).rsplit(":", 1)[-1]
    return (safe_int(tail, 999999), str(value))


def probe_sort_key(row: Mapping[str, Any]) -> Tuple[int, int, str, str]:
    route_order = {
        "route_to_relation_anchor_selection_repair": 0,
        "route_to_direction_specific_reobservation_repair": 1,
    }
    role_order = {
        "failed_explicit_relation_anchor_row": 0,
        "same_direction_anchorless_recovery_row": 1,
        "failed_requested_direction_explicit_anchor_row": 2,
        "failed_requested_direction_anchorless_row": 3,
        "recovered_target_to_relation_anchor_explicit_anchor_row": 4,
        "recovered_target_to_relation_anchor_anchorless_row": 5,
    }
    return (
        route_order.get(str(row.get("source_followup_repair_action")), 99),
        role_order.get(str(row.get("probe_role")), 99),
        row_request_id(row),
        str(row.get("decision_id") or ""),
    )


def association_profile(row: Mapping[str, Any]) -> Dict[str, Any]:
    profile = dict(row.get("association_profile") or {})
    associated = safe_int(profile.get("associated_heading_count"), 0)
    depth = safe_int(
        profile.get("associated_depth_consistent_count", profile.get("depth_consistent_count")),
        0,
    )
    inside_mask = safe_int(profile.get("inside_mask_count"), 0)
    associated_inside_mask = safe_int(profile.get("associated_inside_mask_count"), 0)
    return {
        "associated_heading_count": associated,
        "associated_depth_consistent_count": depth,
        "inside_mask_count": inside_mask,
        "associated_inside_mask_count": associated_inside_mask,
        "projection_status_counts": profile.get("projection_status_counts") or {},
        "depth_check_status_counts": profile.get("depth_check_status_counts") or {},
        "projection_anchor_offset_counts": profile.get("projection_anchor_offset_counts") or {},
        "associated_projection_anchor_offset_counts": profile.get(
            "associated_projection_anchor_offset_counts"
        )
        or {},
    }


def route_family(row: Mapping[str, Any]) -> str:
    action = str(row.get("source_followup_repair_action") or "")
    if action == "route_to_relation_anchor_selection_repair":
        return "relation_anchor_selection_repair"
    if action == "route_to_direction_specific_reobservation_repair":
        return "direction_specific_reobservation_repair"
    return "unknown_association_geometry_repair_route"


def evidence_class(row: Mapping[str, Any]) -> str:
    role = str(row.get("probe_role") or "")
    if role == "failed_explicit_relation_anchor_row":
        return "explicit_anchor_underlink"
    if role == "same_direction_anchorless_recovery_row":
        return "same_direction_anchorless_recovery"
    if role in {"failed_requested_direction_explicit_anchor_row", "failed_requested_direction_anchorless_row"}:
        return "requested_direction_underlink"
    if role in {
        "recovered_target_to_relation_anchor_explicit_anchor_row",
        "recovered_target_to_relation_anchor_anchorless_row",
    }:
        return "target_to_relation_anchor_recovery"
    return "manual_review_unexpected_probe_role"


def evidence_status(row: Mapping[str, Any]) -> str:
    profile = association_profile(row)
    associated = safe_int(profile.get("associated_heading_count"), 0)
    depth = safe_int(profile.get("associated_depth_consistent_count"), 0)
    inside_mask = safe_int(profile.get("inside_mask_count"), 0)
    if associated > 0 and depth > 0:
        return "repair_recovered_association_and_depth"
    if associated > 0:
        return "repair_recovered_association_partial_depth"
    if inside_mask > 0:
        return "underlink_inside_mask_without_candidate_association"
    return "underlink_no_candidate_support"


def repair_direction(row: Mapping[str, Any]) -> str:
    if route_family(row) == "relation_anchor_selection_repair":
        if evidence_class(row) == "explicit_anchor_underlink":
            return "explicit_relation_anchor_failed"
        return "same_direction_anchorless_or_alternative_context_recovered"
    if evidence_class(row) == "requested_direction_underlink":
        return "relation_anchor_to_target_failed"
    if evidence_class(row) == "target_to_relation_anchor_recovery":
        return "target_to_relation_anchor_recovered"
    return "manual_review_unexpected_repair_direction"


def build_evidence_row(
    row: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    profile = association_profile(row)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_association_geometry_underlink_repair_followup_evidence_row",
        "policy": POLICY_NAME,
        "source_policy": row.get("policy"),
        "branch_family": "association_geometry_underlink",
        "route_family": route_family(row),
        "source_followup_repair_action": row.get("source_followup_repair_action"),
        "source_repair_diagnostic_action": row.get("source_repair_diagnostic_action"),
        "nonterminal_probe_action": row.get("nonterminal_probe_action"),
        "expanded_retrieval_request_id": row_request_id(row),
        "rival_identity_request_id": row.get("rival_identity_request_id") or row_request_id(row),
        "episode_key": row.get("episode_key"),
        "scene_key": row.get("scene_key"),
        "scene_id": row.get("scene_id"),
        "query": row.get("query"),
        "candidate_id": candidate_id(row),
        "target_candidate_id": candidate_id(row),
        "context_candidate_id": row.get("context_candidate_id"),
        "relation_anchor_candidate_id": row.get("relation_anchor_candidate_id"),
        "probe_role": row.get("probe_role"),
        "evidence_class": evidence_class(row),
        "family_classification": "repairable_association_geometry_underlink",
        "terminal_status": "nonpromotable_repair_without_goal_validity",
        "evidence_status": evidence_status(row),
        "repair_direction": repair_direction(row),
        "decision_id": row.get("decision_id"),
        "viewpoint_id": row.get("viewpoint_id"),
        "requested_direction_source": row.get("requested_direction_source"),
        "standoff_direction_source": row.get("standoff_direction_source"),
        "plan_row_found": row.get("plan_row_found") is True,
        "frame_row_found": row.get("frame_row_found") is True,
        "frame_has_candidate_association": row.get("frame_has_candidate_association") is True,
        "frame_associated_candidate_heading_count": safe_int(
            row.get("frame_associated_candidate_heading_count"),
            0,
        ),
        "associated_heading_count": profile["associated_heading_count"],
        "associated_depth_consistent_count": profile["associated_depth_consistent_count"],
        "inside_mask_count": profile["inside_mask_count"],
        "associated_inside_mask_count": profile["associated_inside_mask_count"],
        "association_profile": profile,
        "blocked_shortcuts": list((contract.get("evidence_contract") or {}).get("blocked_shortcuts") or []),
        "simpler_alternatives_to_report": list(
            (contract.get("evidence_contract") or {}).get("simpler_alternatives_to_report") or []
        ),
        "recommended_nonterminal_action": "audit_association_geometry_underlink_repair_without_commit",
        "branch_promotable": False,
        "terminal_arbitration_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def group_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(row)
    return grouped


def request_outcome(rows: Sequence[Mapping[str, Any]]) -> str:
    families = {str(row.get("route_family") or "") for row in rows}
    classes = Counter(str(row.get("evidence_class") or "") for row in rows)
    if "relation_anchor_selection_repair" in families:
        if classes.get("explicit_anchor_underlink", 0) and classes.get("same_direction_anchorless_recovery", 0):
            return "anchor_selection_repair_supported_but_nonterminal"
    if "direction_specific_reobservation_repair" in families:
        if classes.get("requested_direction_underlink", 0) and classes.get("target_to_relation_anchor_recovery", 0):
            return "direction_specific_reobservation_supported_but_nonterminal"
    return "manual_review_association_geometry_underlink_followup"


def build_request_rows(evidence_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for rid, rows in sorted(group_by_request(evidence_rows).items(), key=lambda item: request_sort_key(item[0])):
        rows = sorted(rows, key=probe_sort_key)
        first = rows[0]
        failed_rows = [row for row in rows if str(row.get("evidence_status")).startswith("underlink_")]
        recovered_rows = [
            row for row in rows if str(row.get("evidence_status")).startswith("repair_recovered_")
        ]
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_association_geometry_underlink_repair_followup_request_row",
                "policy": POLICY_NAME,
                "branch_family": "association_geometry_underlink",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": first.get("rival_identity_request_id") or rid,
                "episode_key": first.get("episode_key"),
                "scene_key": first.get("scene_key"),
                "scene_id": first.get("scene_id"),
                "query": first.get("query"),
                "candidate_id": first.get("candidate_id"),
                "target_candidate_id": first.get("target_candidate_id"),
                "route_family": first.get("route_family"),
                "source_followup_repair_action": first.get("source_followup_repair_action"),
                "evidence_row_count": len(rows),
                "failed_probe_row_count": len(failed_rows),
                "recovered_probe_row_count": len(recovered_rows),
                "evidence_class_counts": compact_counter(row.get("evidence_class") for row in rows),
                "evidence_status_counts": compact_counter(row.get("evidence_status") for row in rows),
                "total_associated_heading_count": sum(
                    safe_int(row.get("associated_heading_count"), 0) for row in rows
                ),
                "total_associated_depth_consistent_count": sum(
                    safe_int(row.get("associated_depth_consistent_count"), 0) for row in rows
                ),
                "recovered_associated_heading_count": sum(
                    safe_int(row.get("associated_heading_count"), 0) for row in recovered_rows
                ),
                "recovered_associated_depth_consistent_count": sum(
                    safe_int(row.get("associated_depth_consistent_count"), 0) for row in recovered_rows
                ),
                "request_outcome": request_outcome(rows),
                "recommended_nonterminal_action": "keep_association_geometry_underlink_nonterminal",
                "promotable_branch_outcome": False,
                "terminal_arbitration_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def family_row(rows: Sequence[Mapping[str, Any]], family: str) -> Optional[Dict[str, Any]]:
    for row in rows:
        if str(row.get("branch_family")) == family:
            return dict(row)
    return None


def row_count_for_status(rows: Sequence[Mapping[str, Any]], status: str) -> int:
    return sum(1 for row in rows if str(row.get("requirement_status")) == status)


def source_gate_value(summary: Mapping[str, Any], key: str) -> Any:
    return (summary.get("gate") or {}).get(key)


def build_source_summary(
    *,
    repeated_residual_summary: Mapping[str, Any],
    promotion_summary: Mapping[str, Any],
    promotion_rows: Sequence[Mapping[str, Any]],
    synthesis_summary: Mapping[str, Any],
    synthesis_rows: Sequence[Mapping[str, Any]],
    followup_summary: Mapping[str, Any],
    relation_anchor_summary: Mapping[str, Any],
    direction_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    association_family = family_row(synthesis_rows, "association_geometry_underlink") or {}
    return {
        "repeated_object_residual_diagnostic_gate_passed": source_gate_value(
            repeated_residual_summary,
            "residual_diagnostic_gate_passed",
        )
        is True,
        "repeated_object_promotable_branch_outcome_rows": safe_int(
            repeated_residual_summary.get("promotable_branch_outcome_rows"),
            0,
        ),
        "next_branch_after_repeated_object_closure": repeated_residual_summary.get(
            "next_branch_after_closure_counts"
        )
        or {},
        "promotion_requirement_gate_passed": source_gate_value(
            promotion_summary,
            "promotion_requirement_gate_passed",
        )
        is True,
        "association_geometry_requirement_status": "defined_not_satisfied"
        if row_count_for_status(promotion_rows, "defined_not_satisfied") >= 1
        else "missing_or_unexpected",
        "branch_synthesis_gate_passed": source_gate_value(
            synthesis_summary,
            "residual_branch_synthesis_gate_passed",
        )
        is True,
        "association_geometry_source_branch_rows": safe_int(
            association_family.get("source_branch_rows"),
            0,
        ),
        "association_geometry_source_request_rows": safe_int(association_family.get("request_rows"), 0),
        "association_geometry_materialized_output_rows": safe_int(
            association_family.get("materialized_output_rows"),
            0,
        ),
        "association_geometry_followup_repair_gate_passed": source_gate_value(
            followup_summary,
            "association_geometry_followup_repair_gate_passed",
        )
        is True,
        "association_geometry_followup_rows": safe_int(followup_summary.get("followup_rows"), 0),
        "association_geometry_followup_request_rows": safe_int(
            followup_summary.get("followup_request_rows"),
            0,
        ),
        "association_geometry_followup_route_counts": followup_summary.get(
            "followup_repair_action_counts"
        )
        or {},
        "relation_anchor_selection_repair_probe_gate_passed": source_gate_value(
            relation_anchor_summary,
            "relation_anchor_selection_repair_probe_gate_passed",
        )
        is True,
        "relation_anchor_selection_probe_rows": safe_int(
            relation_anchor_summary.get("probe_rows"),
            0,
        ),
        "relation_anchor_selection_probe_request_rows": safe_int(
            relation_anchor_summary.get("probe_request_rows"),
            0,
        ),
        "direction_specific_reobservation_repair_probe_gate_passed": source_gate_value(
            direction_summary,
            "direction_specific_reobservation_repair_probe_gate_passed",
        )
        is True,
        "direction_specific_probe_rows": safe_int(direction_summary.get("probe_rows"), 0),
        "direction_specific_probe_request_rows": safe_int(
            direction_summary.get("probe_request_rows"),
            0,
        ),
    }


def role_count(rows: Sequence[Mapping[str, Any]], role: str) -> int:
    return sum(1 for row in rows if str(row.get("probe_role")) == role)


def summarize(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    repeated_residual_summary: Mapping[str, Any],
    promotion_summary: Mapping[str, Any],
    promotion_rows: Sequence[Mapping[str, Any]],
    synthesis_summary: Mapping[str, Any],
    synthesis_rows: Sequence[Mapping[str, Any]],
    followup_summary: Mapping[str, Any],
    followup_rows: Sequence[Mapping[str, Any]],
    followup_request_rows: Sequence[Mapping[str, Any]],
    relation_anchor_summary: Mapping[str, Any],
    direction_summary: Mapping[str, Any],
    evidence_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    evidence_contract = contract.get("evidence_contract") or {}
    action_rows = [*evidence_rows, *request_rows]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [
        row
        for row in action_rows
        if row.get("terminal_commit") is True or row.get("terminal_arbitration_allowed") is True
    ]
    candidate_commit_rows = [
        row
        for row in action_rows
        if row.get("candidate_commit_allowed") is True
        or str(row.get("recommended_nonterminal_action") or "").startswith("commit_")
    ]
    candidate_rejection_rows = [
        row
        for row in action_rows
        if row.get("candidate_rejection_allowed") is True
        or str(row.get("recommended_nonterminal_action") or "").startswith("reject_")
    ]
    source_summary = build_source_summary(
        repeated_residual_summary=repeated_residual_summary,
        promotion_summary=promotion_summary,
        promotion_rows=promotion_rows,
        synthesis_summary=synthesis_summary,
        synthesis_rows=synthesis_rows,
        followup_summary=followup_summary,
        relation_anchor_summary=relation_anchor_summary,
        direction_summary=direction_summary,
    )
    route_counts = compact_counter(row.get("source_followup_repair_action") for row in request_rows)
    required_roles = sorted(str(role) for role in evidence_contract.get("required_probe_roles") or [])
    actual_roles = sorted(str(row.get("probe_role")) for row in evidence_rows)
    failed_probe_rows = [
        row for row in evidence_rows if str(row.get("evidence_status")).startswith("underlink_")
    ]
    recovered_rows = [
        row for row in evidence_rows if str(row.get("evidence_status")).startswith("repair_recovered_")
    ]
    recovered_association_count = sum(
        safe_int(row.get("associated_heading_count"), 0) for row in recovered_rows
    )
    recovered_depth_count = sum(
        safe_int(row.get("associated_depth_consistent_count"), 0) for row in recovered_rows
    )
    promotable_rows = [row for row in request_rows if row.get("promotable_branch_outcome") is True]
    gate = {
        "repeated_object_residual_diagnostic_gate_passed": source_summary[
            "repeated_object_residual_diagnostic_gate_passed"
        ]
        is source_gate.get("repeated_object_residual_diagnostic_gate_passed"),
        "repeated_object_promotable_branch_outcome_rows_passed": source_summary[
            "repeated_object_promotable_branch_outcome_rows"
        ]
        == safe_int(source_gate.get("repeated_object_promotable_branch_outcome_rows"), -1),
        "next_branch_after_repeated_object_closure_passed": safe_int(
            source_summary["next_branch_after_repeated_object_closure"].get(
                source_gate.get("next_branch_after_repeated_object_closure"),
                0,
            ),
            0,
        )
        > 0,
        "promotion_requirement_gate_passed": source_summary["promotion_requirement_gate_passed"]
        is source_gate.get("promotion_requirement_gate_passed"),
        "branch_synthesis_gate_passed": source_summary["branch_synthesis_gate_passed"]
        is source_gate.get("branch_synthesis_gate_passed"),
        "association_geometry_followup_repair_gate_passed": source_summary[
            "association_geometry_followup_repair_gate_passed"
        ]
        is source_gate.get("association_geometry_followup_repair_gate_passed"),
        "relation_anchor_selection_repair_probe_gate_passed": source_summary[
            "relation_anchor_selection_repair_probe_gate_passed"
        ]
        is source_gate.get("relation_anchor_selection_repair_probe_gate_passed"),
        "direction_specific_reobservation_repair_probe_gate_passed": source_summary[
            "direction_specific_reobservation_repair_probe_gate_passed"
        ]
        is source_gate.get("direction_specific_reobservation_repair_probe_gate_passed"),
        "expected_source_branch_rows_passed": source_summary["association_geometry_source_branch_rows"]
        == safe_int(source_gate.get("expected_source_branch_rows"), -1),
        "expected_request_rows_passed": len(request_rows)
        == safe_int(source_gate.get("expected_request_rows"), -1),
        "expected_materialized_output_rows_passed": source_summary[
            "association_geometry_materialized_output_rows"
        ]
        == safe_int(source_gate.get("expected_materialized_output_rows"), -1),
        "expected_probe_rows_passed": len(evidence_rows)
        == safe_int(source_gate.get("expected_probe_rows"), -1),
        "expected_probe_request_rows_passed": len(request_rows)
        == safe_int(source_gate.get("expected_probe_request_rows"), -1),
        "expected_route_counts_passed": route_counts == dict(source_gate.get("expected_route_counts") or {}),
        "required_probe_roles_passed": actual_roles == required_roles,
        "expected_failed_probe_rows_passed": len(failed_probe_rows)
        == safe_int(source_gate.get("expected_failed_probe_rows"), -1),
        "minimum_recovered_associated_heading_count_passed": recovered_association_count
        >= safe_int(source_gate.get("minimum_recovered_associated_heading_count"), -1),
        "minimum_recovered_depth_consistent_count_passed": recovered_depth_count
        >= safe_int(source_gate.get("minimum_recovered_depth_consistent_count"), -1),
        "request_outcomes_passed": sorted(str(row.get("request_outcome")) for row in request_rows)
        == sorted(str(item) for item in evidence_contract.get("required_request_outcomes") or []),
        "promotable_branch_outcome_rows_passed": len(promotable_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(source_gate.get("max_terminal_commit_rows"), -1),
        "candidate_commit_rows_passed": len(candidate_commit_rows)
        <= safe_int(source_gate.get("max_candidate_commit_rows"), -1),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        <= safe_int(source_gate.get("max_candidate_rejection_rows"), -1),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_analysis_passed": True,
        "paper_claim_allowed": False,
    }
    pass_keys = [key for key in gate if key.endswith("_passed")]
    gate["association_geometry_underlink_repair_followup_evidence_gate_passed"] = all(
        gate[key] is True for key in pass_keys
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "repeated_object_residual_summary": str(args.repeated_object_residual_summary),
            "promotion_requirement_summary": str(args.promotion_requirement_summary),
            "promotion_requirement_rows": str(args.promotion_requirement_rows),
            "branch_synthesis_summary": str(args.branch_synthesis_summary),
            "branch_synthesis_rows": str(args.branch_synthesis_rows),
            "association_geometry_followup_summary": str(args.association_geometry_followup_summary),
            "association_geometry_followup_rows": str(args.association_geometry_followup_rows),
            "association_geometry_followup_request_rows": str(
                args.association_geometry_followup_request_rows
            ),
            "relation_anchor_selection_summary": str(args.relation_anchor_selection_summary),
            "relation_anchor_selection_probe_rows": str(args.relation_anchor_selection_probe_rows),
            "direction_specific_summary": str(args.direction_specific_summary),
            "direction_specific_probe_rows": str(args.direction_specific_probe_rows),
        },
        "source_summary": source_summary,
        "evidence_rows": len(evidence_rows),
        "request_rows": len(request_rows),
        "source_followup_rows": len(followup_rows),
        "source_followup_request_rows": len(followup_request_rows),
        "route_counts": route_counts,
        "route_family_counts": compact_counter(row.get("route_family") for row in evidence_rows),
        "probe_role_counts": compact_counter(row.get("probe_role") for row in evidence_rows),
        "evidence_class_counts": compact_counter(row.get("evidence_class") for row in evidence_rows),
        "evidence_status_counts": compact_counter(row.get("evidence_status") for row in evidence_rows),
        "request_outcome_counts": compact_counter(row.get("request_outcome") for row in request_rows),
        "failed_probe_rows": len(failed_probe_rows),
        "recovered_probe_rows": len(recovered_rows),
        "recovered_associated_heading_count": recovered_association_count,
        "recovered_associated_depth_consistent_count": recovered_depth_count,
        "promotable_branch_outcome_rows": len(promotable_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "association_geometry_underlink_repair_followup_evidence_ready": gate[
                "association_geometry_underlink_repair_followup_evidence_gate_passed"
            ],
            "promotable_branch_outcome_rows": len(promotable_rows),
            "recommended_next_task": "design_depth_stagnation_independent_support_or_close_residual_branches",
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
        },
        "blocked_downstream_tasks": list(contract.get("blocked_downstream_tasks") or []),
        "output_files": dict(contract.get("required_future_outputs") or {}),
        "interpretation": {
            "fact": (
                "The analyzer aggregates the relation-anchor selection and direction-specific "
                "repair probes without joining evaluation labels or emitting terminal actions."
            ),
            "agent_inference": (
                "Association-geometry underlink is repairable as an evidence-acquisition failure, "
                "but repaired association/depth evidence is still not a valid ObjectNav goal proof."
            ),
            "paper_claim": "No paper claim is allowed from this analyzer alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.repeated_object_residual_summary = source_path(
        args, contract, "repeated_object_residual_summary", "repeated_object_residual_summary"
    )
    args.promotion_requirement_summary = source_path(
        args, contract, "promotion_requirement_summary", "promotion_requirement_summary"
    )
    args.promotion_requirement_rows = source_path(
        args, contract, "promotion_requirement_rows", "promotion_requirement_rows"
    )
    args.branch_synthesis_summary = source_path(
        args, contract, "branch_synthesis_summary", "branch_synthesis_summary"
    )
    args.branch_synthesis_rows = source_path(
        args, contract, "branch_synthesis_rows", "branch_synthesis_rows"
    )
    args.association_geometry_followup_summary = source_path(
        args,
        contract,
        "association_geometry_followup_summary",
        "association_geometry_followup_summary",
    )
    args.association_geometry_followup_rows = source_path(
        args, contract, "association_geometry_followup_rows", "association_geometry_followup_rows"
    )
    args.association_geometry_followup_request_rows = source_path(
        args,
        contract,
        "association_geometry_followup_request_rows",
        "association_geometry_followup_request_rows",
    )
    args.relation_anchor_selection_summary = source_path(
        args, contract, "relation_anchor_selection_summary", "relation_anchor_selection_summary"
    )
    args.relation_anchor_selection_probe_rows = source_path(
        args,
        contract,
        "relation_anchor_selection_probe_rows",
        "relation_anchor_selection_probe_rows",
    )
    args.direction_specific_summary = source_path(
        args, contract, "direction_specific_summary", "direction_specific_summary"
    )
    args.direction_specific_probe_rows = source_path(
        args, contract, "direction_specific_probe_rows", "direction_specific_probe_rows"
    )

    repeated_residual_summary = load_json(args.repeated_object_residual_summary)
    promotion_summary = load_json(args.promotion_requirement_summary)
    promotion_rows = load_jsonl(args.promotion_requirement_rows)
    synthesis_summary = load_json(args.branch_synthesis_summary)
    synthesis_rows = load_jsonl(args.branch_synthesis_rows)
    followup_summary = load_json(args.association_geometry_followup_summary)
    followup_rows = load_jsonl(args.association_geometry_followup_rows)
    followup_request_rows = load_jsonl(args.association_geometry_followup_request_rows)
    relation_anchor_summary = load_json(args.relation_anchor_selection_summary)
    relation_anchor_rows = load_jsonl(args.relation_anchor_selection_probe_rows)
    direction_summary = load_json(args.direction_specific_summary)
    direction_rows = load_jsonl(args.direction_specific_probe_rows)

    evidence_rows = [
        build_evidence_row(row, contract=contract)
        for row in sorted([*relation_anchor_rows, *direction_rows], key=probe_sort_key)
    ]
    request_rows = build_request_rows(evidence_rows)
    summary = summarize(
        args=args,
        contract=contract,
        repeated_residual_summary=repeated_residual_summary,
        promotion_summary=promotion_summary,
        promotion_rows=promotion_rows,
        synthesis_summary=synthesis_summary,
        synthesis_rows=synthesis_rows,
        followup_summary=followup_summary,
        followup_rows=followup_rows,
        followup_request_rows=followup_request_rows,
        relation_anchor_summary=relation_anchor_summary,
        direction_summary=direction_summary,
        evidence_rows=evidence_rows,
        request_rows=request_rows,
    )

    out_root = Path(args.out_root)
    outputs = contract.get("required_future_outputs") or {}
    write_jsonl(out_root / str(outputs.get("evidence_rows")), evidence_rows)
    write_jsonl(out_root / str(outputs.get("request_rows")), request_rows)
    write_json(out_root / str(outputs.get("summary")), summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate association-geometry underlink repair follow-up probes into a label-free "
            "nonterminal evidence audit."
        )
    )
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--repeated-object-residual-summary", type=Path)
    parser.add_argument("--promotion-requirement-summary", type=Path)
    parser.add_argument("--promotion-requirement-rows", type=Path)
    parser.add_argument("--branch-synthesis-summary", type=Path)
    parser.add_argument("--branch-synthesis-rows", type=Path)
    parser.add_argument("--association-geometry-followup-summary", type=Path)
    parser.add_argument("--association-geometry-followup-rows", type=Path)
    parser.add_argument("--association-geometry-followup-request-rows", type=Path)
    parser.add_argument("--relation-anchor-selection-summary", type=Path)
    parser.add_argument("--relation-anchor-selection-probe-rows", type=Path)
    parser.add_argument("--direction-specific-summary", type=Path)
    parser.add_argument("--direction-specific-probe-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["association_geometry_underlink_repair_followup_evidence_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
