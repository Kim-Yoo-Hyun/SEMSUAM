import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys
from h001_runtime.diagnose_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy import (
    compact_counter,
    load_json,
    load_jsonl,
    request_id,
    safe_int,
)


SCHEMA_VERSION = "h001.direction_specific_reobservation_repair.v1"
POLICY_NAME = "direction_specific_reobservation_repair_probe_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_direction_specific_reobservation_repair_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_direction_specific_reobservation_repair_v1"


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


def matches_nullable(value: Any, expected: Any) -> bool:
    if expected is None:
        return value is None or str(value) in {"", "None", "null"}
    return str(value) == str(expected)


def row_by_decision(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        decision = str(row.get("decision_id") or "")
        if decision:
            indexed[decision] = dict(row)
    return indexed


def association_rows_by_decision(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    indexed: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        decision = str(row.get("decision_id") or "")
        if decision:
            indexed.setdefault(decision, []).append(dict(row))
    return indexed


def association_profile(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    visible = [row for row in rows if str(row.get("projection_status")) == "visible"]
    inside_mask = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    inside_box = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    associated_inside_mask = [
        row
        for row in rows
        if row.get("associated_to_candidate") is True and row.get("projected_pixel_inside_mask") is True
    ]
    depth_consistent = [
        row for row in rows if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    associated_depth_consistent = [
        row
        for row in rows
        if row.get("associated_to_candidate") is True
        and str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    depth_mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    return {
        "association_rows": len(rows),
        "associated_heading_count": len(associated),
        "visible_count": len(visible),
        "inside_box_count": len(inside_box),
        "inside_mask_count": len(inside_mask),
        "associated_inside_mask_count": len(associated_inside_mask),
        "depth_consistent_count": len(depth_consistent),
        "associated_depth_consistent_count": len(associated_depth_consistent),
        "depth_mismatch_count": len(depth_mismatch),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in rows),
        "projection_anchor_offset_counts": compact_counter(
            row.get("projection_anchor_height_offset_m") for row in rows
        ),
        "associated_projection_anchor_offset_counts": compact_counter(
            row.get("projection_anchor_height_offset_m") for row in associated
        ),
    }


def target_followup_rows(
    rows: Sequence[Dict[str, Any]],
    source_gate: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [
        dict(row)
        for row in rows
        if request_id(row) == str(source_gate.get("expected_request_id"))
        and candidate_id(row) == str(source_gate.get("expected_candidate_id"))
        and str(row.get("query")) == str(source_gate.get("expected_query"))
        and str(row.get("scene_key")) == str(source_gate.get("expected_scene_key"))
        and str(row.get("followup_repair_action")) == str(source_gate.get("target_followup_repair_action"))
        and str(row.get("source_repair_diagnostic_action"))
        == str(source_gate.get("expected_source_repair_diagnostic_action"))
    ]


def target_request_rows(
    rows: Sequence[Dict[str, Any]],
    source_gate: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [
        dict(row)
        for row in rows
        if request_id(row) == str(source_gate.get("expected_request_id"))
        and str(row.get("followup_repair_action")) == str(source_gate.get("target_followup_repair_action"))
    ]


def row_specs(source_gate: Dict[str, Any]) -> List[Dict[str, Any]]:
    failed = source_gate.get("expected_failed_requested_direction") or {}
    recovered = source_gate.get("expected_recovered_direction") or {}
    return [
        {
            "role": "failed_requested_direction_explicit_anchor_row",
            "reason": "relation-anchor-to-target requested direction fell back to compass standoff and did not associate candidate",
            "decision_id": failed.get("explicit_anchor_decision_id"),
            "requested_direction_source": failed.get("requested_direction_source"),
            "standoff_direction_source": failed.get("actual_standoff_direction_source"),
            "relation_anchor_candidate_id": failed.get("explicit_anchor_relation_anchor_candidate_id"),
            "context_candidate_id": failed.get("explicit_anchor_context_candidate_id"),
            "expected_associated_heading_count": failed.get("explicit_anchor_associated_heading_count"),
            "expected_depth_consistent_count": failed.get("explicit_anchor_depth_consistent_count"),
            "expected_inside_mask_count": failed.get("explicit_anchor_inside_mask_count"),
            "minimum": False,
        },
        {
            "role": "failed_requested_direction_anchorless_row",
            "reason": "anchorless same requested direction also failed to associate candidate",
            "decision_id": failed.get("anchorless_decision_id"),
            "requested_direction_source": failed.get("requested_direction_source"),
            "standoff_direction_source": failed.get("actual_standoff_direction_source"),
            "relation_anchor_candidate_id": failed.get("anchorless_relation_anchor_candidate_id"),
            "context_candidate_id": failed.get("anchorless_context_candidate_id"),
            "expected_associated_heading_count": failed.get("anchorless_associated_heading_count"),
            "expected_depth_consistent_count": failed.get("anchorless_depth_consistent_count"),
            "expected_inside_mask_count": failed.get("anchorless_inside_mask_count"),
            "minimum": False,
        },
        {
            "role": "recovered_target_to_relation_anchor_explicit_anchor_row",
            "reason": "target-to-relation-anchor requested direction recovered candidate association with explicit anchor",
            "decision_id": recovered.get("explicit_anchor_decision_id"),
            "requested_direction_source": recovered.get("requested_direction_source"),
            "standoff_direction_source": recovered.get("actual_standoff_direction_source"),
            "relation_anchor_candidate_id": recovered.get("explicit_anchor_relation_anchor_candidate_id"),
            "context_candidate_id": recovered.get("explicit_anchor_context_candidate_id"),
            "expected_associated_heading_count": recovered.get(
                "explicit_anchor_minimum_associated_heading_count"
            ),
            "expected_depth_consistent_count": recovered.get("explicit_anchor_minimum_depth_consistent_count"),
            "expected_inside_mask_count": recovered.get("explicit_anchor_minimum_inside_mask_count"),
            "expected_associated_projection_anchor_offset_m": recovered.get(
                "expected_associated_projection_anchor_offset_m"
            ),
            "minimum": True,
        },
        {
            "role": "recovered_target_to_relation_anchor_anchorless_row",
            "reason": "target-to-relation-anchor requested direction recovered candidate association with anchorless context",
            "decision_id": recovered.get("anchorless_decision_id"),
            "requested_direction_source": recovered.get("requested_direction_source"),
            "standoff_direction_source": recovered.get("actual_standoff_direction_source"),
            "relation_anchor_candidate_id": recovered.get("anchorless_relation_anchor_candidate_id"),
            "context_candidate_id": recovered.get("anchorless_context_candidate_id"),
            "expected_associated_heading_count": recovered.get(
                "anchorless_minimum_associated_heading_count"
            ),
            "expected_depth_consistent_count": recovered.get("anchorless_minimum_depth_consistent_count"),
            "expected_inside_mask_count": recovered.get("anchorless_minimum_inside_mask_count"),
            "expected_associated_projection_anchor_offset_m": recovered.get(
                "expected_associated_projection_anchor_offset_m"
            ),
            "minimum": True,
        },
    ]


def find_plan_row(
    *,
    plan_rows: Sequence[Dict[str, Any]],
    request: str,
    target_candidate: str,
    spec: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for row in plan_rows:
        if request_id(row) != request:
            continue
        if candidate_id(row) != target_candidate:
            continue
        if str(row.get("requested_direction_source")) != str(spec.get("requested_direction_source")):
            continue
        if str(row.get("standoff_direction_source")) != str(spec.get("standoff_direction_source")):
            continue
        if not matches_nullable(
            row.get("standoff_relation_anchor_candidate_id"),
            spec.get("relation_anchor_candidate_id"),
        ):
            continue
        if not matches_nullable(row.get("context_candidate_id"), spec.get("context_candidate_id")):
            continue
        matches.append(dict(row))
    if len(matches) > 1:
        raise ValueError(
            "ambiguous direction-specific plan rows for "
            f"request={request} candidate={target_candidate} role={spec.get('role')}"
        )
    return matches[0] if matches else None


def build_probe_row(
    *,
    spec: Dict[str, Any],
    followup_row: Dict[str, Any],
    plan_row: Optional[Dict[str, Any]],
    frame_row: Optional[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
    nonterminal_action: str,
    allowed_next_evidence: Sequence[str],
    blocked_shortcuts: Sequence[str],
) -> Dict[str, Any]:
    profile = association_profile(association_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_direction_specific_reobservation_repair_probe_row",
        "policy": POLICY_NAME,
        "probe_role": spec.get("role"),
        "expanded_retrieval_request_id": request_id(followup_row),
        "rival_identity_request_id": followup_row.get("rival_identity_request_id"),
        "episode_key": followup_row.get("episode_key"),
        "scene_key": followup_row.get("scene_key"),
        "scene_id": followup_row.get("scene_id"),
        "query": followup_row.get("query"),
        "candidate_id": candidate_id(followup_row),
        "target_candidate_id": candidate_id(followup_row),
        "source_followup_repair_action": followup_row.get("followup_repair_action"),
        "source_repair_diagnostic_action": followup_row.get("source_repair_diagnostic_action"),
        "decision_id": spec.get("decision_id"),
        "viewpoint_id": None if plan_row is None else plan_row.get("viewpoint_id"),
        "failed_evidence_index": None if plan_row is None else plan_row.get("failed_evidence_index"),
        "completion_index": None if plan_row is None else plan_row.get("completion_index"),
        "requested_direction_source": spec.get("requested_direction_source"),
        "standoff_direction_source": spec.get("standoff_direction_source"),
        "relation_anchor_candidate_id": spec.get("relation_anchor_candidate_id"),
        "context_candidate_id": spec.get("context_candidate_id"),
        "plan_row_found": plan_row is not None,
        "frame_row_found": frame_row is not None,
        "frame_has_candidate_association": None
        if frame_row is None
        else frame_row.get("has_candidate_association"),
        "frame_associated_candidate_heading_count": None
        if frame_row is None
        else frame_row.get("associated_candidate_heading_count"),
        "standoff_navmesh_navigable": None if plan_row is None else plan_row.get("standoff_navmesh_navigable"),
        "standoff_navmesh_snapped": None if plan_row is None else plan_row.get("standoff_navmesh_snapped"),
        "standoff_score": None if plan_row is None else plan_row.get("standoff_score"),
        "standoff_snap_distance": None if plan_row is None else plan_row.get("standoff_snap_distance"),
        "association_profile": profile,
        "expected_associated_heading_count": spec.get("expected_associated_heading_count"),
        "expected_depth_consistent_count": spec.get("expected_depth_consistent_count"),
        "expected_inside_mask_count": spec.get("expected_inside_mask_count"),
        "expected_associated_projection_anchor_offset_m": spec.get(
            "expected_associated_projection_anchor_offset_m"
        ),
        "expected_count_is_minimum": spec.get("minimum") is True,
        "nonterminal_probe_action": nonterminal_action,
        "probe_reason": spec.get("reason"),
        "allowed_next_evidence": list(allowed_next_evidence),
        "blocked_shortcuts": list(blocked_shortcuts),
        "terminal_arbitration_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_outputs(
    *,
    contract: Dict[str, Any],
    followup_rows: Sequence[Dict[str, Any]],
    followup_request_rows: Sequence[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
    detector_associations: Sequence[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    source_gate = contract.get("source_gate") or {}
    probe_contract = contract.get("probe_contract") or {}
    targets = target_followup_rows(followup_rows, source_gate)
    if len(targets) != 1:
        raise ValueError(f"expected one target followup row, found {len(targets)}")
    target = targets[0]
    request = str(source_gate.get("expected_request_id"))
    target_candidate = str(source_gate.get("expected_candidate_id"))
    frame_by_decision = row_by_decision(frame_rows)
    associations_by_decision = association_rows_by_decision(detector_associations)
    probe_rows: List[Dict[str, Any]] = []
    for spec in row_specs(source_gate):
        decision = str(spec.get("decision_id") or "")
        plan_row = find_plan_row(
            plan_rows=plan_rows,
            request=request,
            target_candidate=target_candidate,
            spec=spec,
        )
        probe_rows.append(
            build_probe_row(
                spec=spec,
                followup_row=target,
                plan_row=plan_row,
                frame_row=frame_by_decision.get(decision),
                association_rows=associations_by_decision.get(decision, []),
                nonterminal_action=str(probe_contract.get("expected_nonterminal_probe_action")),
                allowed_next_evidence=list(probe_contract.get("allowed_next_evidence") or []),
                blocked_shortcuts=list(probe_contract.get("blocked_shortcuts") or []),
            )
        )
    target_requests = target_request_rows(followup_request_rows, source_gate)
    request_row = {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_direction_specific_reobservation_repair_request",
        "policy": POLICY_NAME,
        "expanded_retrieval_request_id": request,
        "rival_identity_request_id": target.get("rival_identity_request_id"),
        "episode_key": target.get("episode_key"),
        "scene_key": target.get("scene_key"),
        "scene_id": target.get("scene_id"),
        "query": target.get("query"),
        "candidate_id": target_candidate,
        "target_candidate_id": target_candidate,
        "source_followup_repair_action": target.get("followup_repair_action"),
        "source_repair_diagnostic_action": target.get("source_repair_diagnostic_action"),
        "target_followup_request_rows": len(target_requests),
        "probe_row_count": len(probe_rows),
        "probe_role_counts": compact_counter(row.get("probe_role") for row in probe_rows),
        "nonterminal_probe_action": str(probe_contract.get("expected_nonterminal_probe_action")),
        "blocked_shortcuts": list(probe_contract.get("blocked_shortcuts") or []),
        "request_probe_status": "direction_specific_reobservation_replay_ready",
        "terminal_arbitration_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }
    return {"probe_rows": probe_rows, "probe_request_rows": [request_row]}


def profile_value(rows: Sequence[Dict[str, Any]], role: str, key: str) -> int:
    for row in rows:
        if row.get("probe_role") == role:
            return safe_int((row.get("association_profile") or {}).get(key), 0)
    return 0


def row_for_role(rows: Sequence[Dict[str, Any]], role: str) -> Optional[Dict[str, Any]]:
    for row in rows:
        if row.get("probe_role") == role:
            return row
    return None


def profile_matches(row: Optional[Dict[str, Any]]) -> bool:
    if not row:
        return False
    profile = row.get("association_profile") or {}
    expected_assoc = safe_int(row.get("expected_associated_heading_count"), -1)
    expected_depth = safe_int(row.get("expected_depth_consistent_count"), -1)
    expected_mask = safe_int(row.get("expected_inside_mask_count"), -1)
    actual_assoc = safe_int(profile.get("associated_heading_count"), 0)
    actual_depth = safe_int(profile.get("associated_depth_consistent_count"), 0)
    actual_mask = safe_int(profile.get("inside_mask_count"), 0)
    if row.get("expected_count_is_minimum") is True:
        return actual_assoc >= expected_assoc and actual_depth >= expected_depth and actual_mask >= expected_mask
    return actual_assoc == expected_assoc and actual_depth == expected_depth and actual_mask == expected_mask


def offset_matches(row: Optional[Dict[str, Any]]) -> bool:
    if not row:
        return False
    expected = row.get("expected_associated_projection_anchor_offset_m")
    if expected is None:
        return True
    counts = (row.get("association_profile") or {}).get("associated_projection_anchor_offset_counts") or {}
    return safe_int(counts.get(str(expected)), 0) > 0


def summarize(
    *,
    contract: Dict[str, Any],
    followup_summary: Dict[str, Any],
    followup_rows: Sequence[Dict[str, Any]],
    followup_request_rows: Sequence[Dict[str, Any]],
    probe_rows: Sequence[Dict[str, Any]],
    probe_request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    probe_contract = contract.get("probe_contract") or {}
    action_rows = [*probe_rows, *probe_request_rows]
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
        or str(row.get("nonterminal_probe_action") or "").startswith("commit_")
    ]
    candidate_rejection_rows = [
        row
        for row in action_rows
        if row.get("candidate_rejection_allowed") is True
        or str(row.get("nonterminal_probe_action") or "").startswith("reject_")
    ]
    target_rows = target_followup_rows(followup_rows, source_gate)
    target_requests = target_request_rows(followup_request_rows, source_gate)
    roles = list(probe_contract.get("required_probe_rows") or [])
    rows_by_role = {role: row_for_role(probe_rows, role) for role in roles}
    followup_gate = followup_summary.get("gate") or {}
    gate = {
        "source_followup_gate_passed": followup_gate.get(
            "association_geometry_followup_repair_gate_passed"
        )
        is source_gate.get("association_geometry_followup_repair_gate_passed"),
        "expected_target_followup_rows_passed": len(target_rows)
        == safe_int(source_gate.get("expected_target_followup_rows"), -1),
        "expected_target_request_rows_passed": len(target_requests)
        == safe_int(source_gate.get("expected_target_request_rows"), -1),
        "expected_probe_rows_passed": len(probe_rows) == len(roles),
        "expected_probe_request_rows_passed": len(probe_request_rows)
        == safe_int(probe_contract.get("target_request_rows"), -1),
        "all_plan_and_frame_rows_found_passed": all(
            bool(row) and row.get("plan_row_found") is True and row.get("frame_row_found") is True
            for row in rows_by_role.values()
        ),
        "all_probe_profiles_match_contract_passed": all(
            profile_matches(row) for row in rows_by_role.values()
        ),
        "recovered_projection_anchor_offset_passed": all(
            offset_matches(rows_by_role.get(role))
            for role in [
                "recovered_target_to_relation_anchor_explicit_anchor_row",
                "recovered_target_to_relation_anchor_anchorless_row",
            ]
        ),
        "same_requested_direction_zero_association_passed": (
            profile_value(
                probe_rows,
                "failed_requested_direction_explicit_anchor_row",
                "associated_heading_count",
            )
            + profile_value(
                probe_rows,
                "failed_requested_direction_anchorless_row",
                "associated_heading_count",
            )
        )
        == safe_int(source_gate.get("expected_same_requested_direction_associated_heading_count"), -1),
        "other_requested_direction_association_passed": (
            profile_value(
                probe_rows,
                "recovered_target_to_relation_anchor_explicit_anchor_row",
                "associated_heading_count",
            )
            + profile_value(
                probe_rows,
                "recovered_target_to_relation_anchor_anchorless_row",
                "associated_heading_count",
            )
        )
        >= safe_int(source_gate.get("minimum_other_requested_direction_associated_heading_count"), -1),
        "other_requested_direction_depth_passed": (
            profile_value(
                probe_rows,
                "recovered_target_to_relation_anchor_explicit_anchor_row",
                "associated_depth_consistent_count",
            )
            + profile_value(
                probe_rows,
                "recovered_target_to_relation_anchor_anchorless_row",
                "associated_depth_consistent_count",
            )
        )
        >= safe_int(source_gate.get("minimum_other_requested_direction_depth_consistent_count"), -1),
        "other_requested_direction_inside_mask_passed": (
            profile_value(
                probe_rows,
                "recovered_target_to_relation_anchor_explicit_anchor_row",
                "associated_inside_mask_count",
            )
            + profile_value(
                probe_rows,
                "recovered_target_to_relation_anchor_anchorless_row",
                "associated_inside_mask_count",
            )
        )
        >= safe_int(source_gate.get("minimum_other_requested_direction_inside_mask_count"), -1),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(source_gate.get("max_terminal_commit_rows"), -1),
        "candidate_commit_rows_passed": len(candidate_commit_rows)
        <= safe_int(source_gate.get("max_candidate_commit_rows"), -1),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        <= safe_int(source_gate.get("max_candidate_rejection_rows"), -1),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows)
        and followup_summary.get("uses_gt_for_action") is source_gate.get("requires_uses_gt_for_action"),
        "uses_gt_for_analysis_passed": followup_summary.get("uses_gt_for_analysis")
        is source_gate.get("requires_uses_gt_for_analysis"),
        "paper_claim_allowed": False,
    }
    pass_keys = [key for key in gate if key.endswith("_passed")]
    gate["direction_specific_reobservation_repair_probe_gate_passed"] = all(
        gate[key] is True for key in pass_keys
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "followup_summary": str(args.followup_summary),
            "followup_rows": str(args.followup_rows),
            "followup_request_rows": str(args.followup_request_rows),
            "observation_plan_rows": str(args.observation_plan_rows),
            "detector_frame_summary": str(args.detector_frame_summary),
            "detector_associations": str(args.detector_associations),
        },
        "probe_rows": len(probe_rows),
        "probe_request_rows": len(probe_request_rows),
        "target_followup_rows": len(target_rows),
        "target_request_rows": len(target_requests),
        "probe_role_counts": compact_counter(row.get("probe_role") for row in probe_rows),
        "nonterminal_probe_action_counts": compact_counter(
            row.get("nonterminal_probe_action") for row in probe_rows
        ),
        "failed_requested_direction_explicit_anchor_associated_heading_count": profile_value(
            probe_rows, "failed_requested_direction_explicit_anchor_row", "associated_heading_count"
        ),
        "failed_requested_direction_explicit_anchor_depth_consistent_count": profile_value(
            probe_rows, "failed_requested_direction_explicit_anchor_row", "associated_depth_consistent_count"
        ),
        "failed_requested_direction_explicit_anchor_inside_mask_count": profile_value(
            probe_rows, "failed_requested_direction_explicit_anchor_row", "inside_mask_count"
        ),
        "failed_requested_direction_anchorless_associated_heading_count": profile_value(
            probe_rows, "failed_requested_direction_anchorless_row", "associated_heading_count"
        ),
        "failed_requested_direction_anchorless_depth_consistent_count": profile_value(
            probe_rows, "failed_requested_direction_anchorless_row", "associated_depth_consistent_count"
        ),
        "failed_requested_direction_anchorless_inside_mask_count": profile_value(
            probe_rows, "failed_requested_direction_anchorless_row", "inside_mask_count"
        ),
        "recovered_explicit_anchor_associated_heading_count": profile_value(
            probe_rows,
            "recovered_target_to_relation_anchor_explicit_anchor_row",
            "associated_heading_count",
        ),
        "recovered_explicit_anchor_depth_consistent_count": profile_value(
            probe_rows,
            "recovered_target_to_relation_anchor_explicit_anchor_row",
            "associated_depth_consistent_count",
        ),
        "recovered_explicit_anchor_inside_mask_count": profile_value(
            probe_rows,
            "recovered_target_to_relation_anchor_explicit_anchor_row",
            "associated_inside_mask_count",
        ),
        "recovered_anchorless_associated_heading_count": profile_value(
            probe_rows,
            "recovered_target_to_relation_anchor_anchorless_row",
            "associated_heading_count",
        ),
        "recovered_anchorless_depth_consistent_count": profile_value(
            probe_rows,
            "recovered_target_to_relation_anchor_anchorless_row",
            "associated_depth_consistent_count",
        ),
        "recovered_anchorless_inside_mask_count": profile_value(
            probe_rows,
            "recovered_target_to_relation_anchor_anchorless_row",
            "associated_inside_mask_count",
        ),
        "same_requested_direction_associated_heading_count": (
            profile_value(
                probe_rows,
                "failed_requested_direction_explicit_anchor_row",
                "associated_heading_count",
            )
            + profile_value(
                probe_rows,
                "failed_requested_direction_anchorless_row",
                "associated_heading_count",
            )
        ),
        "other_requested_direction_associated_heading_count": (
            profile_value(
                probe_rows,
                "recovered_target_to_relation_anchor_explicit_anchor_row",
                "associated_heading_count",
            )
            + profile_value(
                probe_rows,
                "recovered_target_to_relation_anchor_anchorless_row",
                "associated_heading_count",
            )
        ),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "direction_specific_reobservation_repair_probe_ready": gate[
                "direction_specific_reobservation_repair_probe_gate_passed"
            ],
            "recommended_next_task": "design_depth_stagnation_or_repeated_anchor_branch_contract",
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
        },
        "blocked_downstream_tasks": list(contract.get("blocked_downstream_tasks") or []),
        "output_files": {
            "probe_rows": "direction_specific_reobservation_repair_probe_rows.jsonl",
            "probe_request_rows": "direction_specific_reobservation_repair_request_rows.jsonl",
            "summary": "direction_specific_reobservation_repair_summary.json",
        },
        "interpretation": {
            "fact": (
                "This probe materializes two failed relation-anchor-to-target rows and two recovered "
                "target-to-relation-anchor rows without joining evaluation labels."
            ),
            "agent_inference": (
                "Direction-specific re-observation is now a reproducible nonterminal repair target. "
                "It does not establish ObjectNav goal validity and must not trigger candidate commit "
                "or rejection."
            ),
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.followup_summary = source_path(args, contract, "followup_summary", "followup_summary")
    args.followup_rows = source_path(args, contract, "followup_rows", "followup_rows")
    args.followup_request_rows = source_path(
        args, contract, "followup_request_rows", "followup_request_rows"
    )
    args.observation_plan_rows = source_path(
        args, contract, "observation_plan_rows", "observation_plan_rows"
    )
    args.detector_frame_summary = source_path(
        args, contract, "detector_frame_summary", "detector_frame_summary"
    )
    args.detector_associations = source_path(
        args, contract, "detector_associations", "detector_associations"
    )

    followup_summary = load_json(args.followup_summary)
    followup_rows = load_jsonl(args.followup_rows)
    followup_request_rows = load_jsonl(args.followup_request_rows)
    plan_rows = load_jsonl(args.observation_plan_rows)
    frame_rows = load_jsonl(args.detector_frame_summary)
    detector_associations = load_jsonl(args.detector_associations)
    outputs = build_outputs(
        contract=contract,
        followup_rows=followup_rows,
        followup_request_rows=followup_request_rows,
        plan_rows=plan_rows,
        frame_rows=frame_rows,
        detector_associations=detector_associations,
    )
    probe_rows = outputs["probe_rows"]
    probe_request_rows = outputs["probe_request_rows"]
    summary = summarize(
        contract=contract,
        followup_summary=followup_summary,
        followup_rows=followup_rows,
        followup_request_rows=followup_request_rows,
        probe_rows=probe_rows,
        probe_request_rows=probe_request_rows,
        args=args,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "direction_specific_reobservation_repair_probe_rows.jsonl", probe_rows)
    write_jsonl(out_root / "direction_specific_reobservation_repair_request_rows.jsonl", probe_request_rows)
    write_json(out_root / "direction_specific_reobservation_repair_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a frozen direction-specific re-observation repair probe without terminal "
            "commit or evaluation-label join."
        )
    )
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--followup-summary", type=Path)
    parser.add_argument("--followup-rows", type=Path)
    parser.add_argument("--followup-request-rows", type=Path)
    parser.add_argument("--observation-plan-rows", type=Path)
    parser.add_argument("--detector-frame-summary", type=Path)
    parser.add_argument("--detector-associations", type=Path)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["direction_specific_reobservation_repair_probe_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
