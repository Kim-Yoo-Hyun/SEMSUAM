import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.missing_own_view_recheck_inputs.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_missing_own_view_recheck_observation_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_missing_own_view_recheck_observation_v1"
TARGET_BRANCH = "correct_candidate_missing_own_view_support"
TARGET_ACTION = "request_missing_own_view_recheck"
COMPANION_GUARD_BRANCH = "negative_missing_support_guard"
POLICY_NAME = "MissingOwnViewRecheckObservation"
BUILDER_NAME = "missing_own_view_recheck_inputs_v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(explicit)
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        text = str(value).split(":")[-1]
        try:
            return int(text)
        except (TypeError, ValueError):
            return default


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def request_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    if ":" in text:
        prefix, suffix = text.rsplit(":", 1)
        return prefix, safe_int(suffix), text
    return text, -1, text


def candidate_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    return text.rsplit(":", 1)[0], safe_int(text.rsplit(":", 1)[-1]), text


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("target_candidate_id") or "")


def row_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (request_id(row), candidate_id(row))


def unique_preserve_order(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def rows_by_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = row_key(row)
        if all(key):
            grouped[key].append(dict(row))
    return grouped


def first_by_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        key = row_key(row)
        if all(key) and key not in indexed:
            indexed[key] = dict(row)
    return indexed


def target_request_ids(contract: Dict[str, Any]) -> List[str]:
    scope = contract.get("target_scope") or {}
    return sorted(
        [str(row.get("expanded_retrieval_request_id")) for row in scope.get("target_requests") or []],
        key=request_sort_key,
    )


def target_candidate_source_rows(
    *,
    contract: Dict[str, Any],
    candidate_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    expected_ids = set(target_request_ids(contract))
    rows = [
        dict(row)
        for row in candidate_rows
        if request_id(row) in expected_ids
        and str(row.get("preferred_candidate_branch")) == TARGET_BRANCH
        and str(row.get("preferred_candidate_action")) == TARGET_ACTION
    ]
    rows.sort(
        key=lambda row: (
            request_sort_key(request_id(row)),
            safe_int(row.get("target_generated_rank")),
            candidate_sort_key(candidate_id(row)),
        )
    )
    return rows


def target_position_from_plan(plan: Optional[Dict[str, Any]]) -> Optional[List[float]]:
    if not plan:
        return None
    value = plan.get("target_position") or plan.get("standoff_target_position")
    if isinstance(value, list) and len(value) == 3 and all(safe_float(item) is not None for item in value):
        return [float(item) for item in value]
    return None


def target_visit_position_from_plan(plan: Optional[Dict[str, Any]]) -> Optional[List[float]]:
    if not plan:
        return None
    value = plan.get("target_visit_position") or plan.get("target_position") or plan.get("standoff_target_position")
    if isinstance(value, list) and len(value) == 3 and all(safe_float(item) is not None for item in value):
        return [float(item) for item in value]
    return None


def scan_forbidden_keys(value: Any, prefix: str = "") -> List[str]:
    findings: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if lowered != "uses_gt_for_action" and any(term in lowered for term in ("correct", "wrong_goal", "evaluation_only", "gt_")):
                findings.append(child_path)
            findings.extend(scan_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan_forbidden_keys(child, f"{prefix}[{index}]"))
    return findings


def count_forbidden(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def make_request_rows(
    *,
    branch_request_rows: Sequence[Dict[str, Any]],
    target_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> List[Dict[str, Any]]:
    by_request = {request_id(row): row for row in branch_request_rows if request_id(row)}
    candidate_ids_by_request: Dict[str, List[str]] = defaultdict(list)
    for row in target_rows:
        candidate_ids_by_request[request_id(row)].append(candidate_id(row))

    output: List[Dict[str, Any]] = []
    for request_index, rid in enumerate(target_request_ids(contract)):
        source = by_request.get(rid)
        if source is None:
            continue
        selected_ids = unique_preserve_order(candidate_ids_by_request.get(rid, []))
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_missing_own_view_recheck_request",
                "policy": POLICY_NAME,
                "builder_name": BUILDER_NAME,
                "request_index": request_index,
                "episode_key": source.get("episode_key"),
                "scene_id": source.get("scene_id"),
                "scene_key": source.get("scene_key"),
                "query": source.get("query"),
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": source.get("rival_identity_request_id") or rid,
                "source_request_branch_names": list(source.get("request_branch_names") or []),
                "source_request_branch_actions": list(source.get("request_branch_actions") or []),
                "source_preferred_request_branch": source.get("preferred_request_branch"),
                "source_preferred_request_action": source.get("preferred_request_action"),
                "target_branch": TARGET_BRANCH,
                "target_action": TARGET_ACTION,
                "companion_guard_branch": COMPANION_GUARD_BRANCH,
                "companion_guard_role": "deferred_safety_counterfactual_not_rejection",
                "selected_target_candidate_ids": selected_ids,
                "selected_target_candidate_rows": len(selected_ids),
                "terminal_arbitration_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def make_target_candidate_row(
    *,
    source: Dict[str, Any],
    base: Optional[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
    target_index: int,
) -> Dict[str, Any]:
    base = base or {}
    first_plan = plan_rows[0] if plan_rows else {}
    routing = dict(source.get("routing_inputs") or {})
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_missing_own_view_recheck_target_candidate",
        "policy": POLICY_NAME,
        "builder_name": BUILDER_NAME,
        "target_index": target_index,
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "scene_key": source.get("scene_key"),
        "query": source.get("query"),
        "expanded_retrieval_request_id": request_id(source),
        "rival_identity_request_id": source.get("rival_identity_request_id") or request_id(source),
        "candidate_id": candidate_id(source),
        "target_candidate_id": candidate_id(source),
        "target_generated_rank": source.get("target_generated_rank") or base.get("target_generated_rank"),
        "target_semantic_rank": source.get("target_semantic_rank") or base.get("target_semantic_rank") or base.get("semantic_rank"),
        "target_semantic_score": base.get("semantic_score"),
        "target_support_score": base.get("support_score"),
        "target_score": base.get("support_score") or base.get("semantic_score"),
        "target_candidate_role": base.get("candidate_role") or first_plan.get("target_candidate_role"),
        "target_position": target_position_from_plan(first_plan),
        "target_visit_position": target_visit_position_from_plan(first_plan),
        "target_branch": TARGET_BRANCH,
        "target_action": TARGET_ACTION,
        "source_candidate_branch_names": list(source.get("candidate_branch_names") or []),
        "source_candidate_branch_actions": list(source.get("candidate_branch_actions") or []),
        "preferred_candidate_branch": source.get("preferred_candidate_branch"),
        "preferred_candidate_action": source.get("preferred_candidate_action"),
        "companion_guard_present": COMPANION_GUARD_BRANCH in set(source.get("candidate_branch_names") or []),
        "companion_guard_branch": COMPANION_GUARD_BRANCH,
        "companion_guard_role": "deferred_safety_counterfactual_not_rejection",
        "base_support_source": base.get("base_support_source"),
        "base_candidate_evidence_class": base.get("candidate_evidence_class") or routing.get("base_candidate_evidence_class"),
        "base_candidate_specific_support": bool(base.get("candidate_specific_support")),
        "base_strong_own_view_evidence": bool(base.get("strong_own_view_evidence")),
        "base_has_candidate_association": bool(base.get("has_candidate_association")),
        "base_visible_count": base.get("visible_count"),
        "base_mask_hit_count": base.get("mask_hit_count"),
        "base_box_hit_count": base.get("box_hit_count"),
        "base_consistent_depth_count": base.get("consistent_depth_count"),
        "base_depth_mismatch_count": base.get("depth_mismatch_count"),
        "base_best_box_score": base.get("best_box_score"),
        "base_min_depth_error_m": base.get("min_depth_error_m"),
        "relation_depth_evidence_status": routing.get("relation_depth_evidence_status"),
        "relation_associated_heading_count": routing.get("relation_associated_heading_count"),
        "relation_depth_consistent_count": routing.get("relation_depth_consistent_count"),
        "relation_inside_mask_count": routing.get("relation_inside_mask_count"),
        "relation_resolved_direction_source_count": routing.get("relation_resolved_direction_source_count"),
        "source_plan_rows": len(plan_rows),
        "source_plan_direction_counts": compact_counter(row.get("standoff_direction_source") for row in plan_rows),
        "source_plan_standoff_distance_counts": compact_counter(row.get("standoff_distance_requested") for row in plan_rows),
        "terminal_arbitration_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_source_plan_row(row: Dict[str, Any], source_plan_index: int) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_missing_own_view_recheck_source_plan_reference",
        "policy": POLICY_NAME,
        "builder_name": BUILDER_NAME,
        "source_plan_index": source_plan_index,
        "source_contract_name": row.get("contract_name"),
        "source_planner_name": row.get("planner_name"),
        "source_viewpoint_id": row.get("viewpoint_id"),
        "source_viewpoint_index": row.get("viewpoint_index"),
        "episode_key": row.get("episode_key"),
        "scene_id": row.get("scene_id"),
        "scene_key": row.get("scene_key"),
        "query": row.get("query"),
        "expanded_retrieval_request_id": request_id(row),
        "rival_identity_request_id": row.get("rival_identity_request_id") or request_id(row),
        "candidate_id": candidate_id(row),
        "target_candidate_id": candidate_id(row),
        "candidate_ids": unique_preserve_order(row.get("candidate_ids") or [candidate_id(row)]),
        "goal_validity_context_candidate_ids": unique_preserve_order(row.get("goal_validity_context_candidate_ids") or []),
        "goal_validity_relation_anchor_candidate_ids": unique_preserve_order(row.get("goal_validity_relation_anchor_candidate_ids") or []),
        "goal_validity_relation_anchor_count": row.get("goal_validity_relation_anchor_count"),
        "target_candidate_role": row.get("target_candidate_role"),
        "target_generated_rank": row.get("target_generated_rank"),
        "target_semantic_rank": row.get("target_semantic_rank"),
        "target_semantic_score": row.get("target_semantic_score"),
        "target_support_score": row.get("target_support_score"),
        "target_score": row.get("target_score"),
        "target_positive_support": row.get("target_positive_support"),
        "target_position": row.get("target_position"),
        "target_visit_position": row.get("target_visit_position"),
        "source_viewpoint_policy": row.get("viewpoint_policy"),
        "source_viewpoint_source": row.get("viewpoint_source"),
        "source_viewpoint_position": row.get("viewpoint_position"),
        "source_viewpoint_rotation": row.get("viewpoint_rotation"),
        "source_standoff_direction_source": row.get("standoff_direction_source"),
        "source_standoff_distance_requested": row.get("standoff_distance_requested"),
        "source_standoff_relation_anchor_candidate_id": row.get("standoff_relation_anchor_candidate_id"),
        "source_standoff_target_horizontal_distance": row.get("standoff_target_horizontal_distance"),
        "source_target_distance_from_viewpoint_m": row.get("target_distance_from_viewpoint_m"),
        "source_standoff_navmesh_navigable": row.get("standoff_navmesh_navigable"),
        "source_standoff_navmesh_snapped": row.get("standoff_navmesh_snapped"),
        "source_standoff_snap_distance": row.get("standoff_snap_distance"),
        "source_standoff_projection_sane": row.get("standoff_projection_sane"),
        "source_standoff_viewpoint_yaw_rad": row.get("standoff_viewpoint_yaw_rad"),
        "source_standoff_score": row.get("standoff_score"),
        "revision_projection_anchor_policy": row.get("revision_projection_anchor_policy"),
        "revision_projection_anchor_height_offsets_m": row.get("revision_projection_anchor_height_offsets_m"),
        "revision_projection_anchor_source": row.get("revision_projection_anchor_source"),
        "revision_projection_anchor_label_free": row.get("revision_projection_anchor_label_free"),
        "source_plan_reference_only": True,
        "source_relation_depth_evidence_not_reused": True,
        "terminal_arbitration_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_base_support_row(row: Dict[str, Any], base_index: int) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_missing_own_view_recheck_base_support_reference",
        "policy": POLICY_NAME,
        "builder_name": BUILDER_NAME,
        "base_support_index": base_index,
        "base_support_source": row.get("base_support_source"),
        "episode_key": row.get("episode_key"),
        "scene_id": row.get("scene_id"),
        "scene_key": row.get("scene_key"),
        "query": row.get("query"),
        "expanded_retrieval_request_id": request_id(row),
        "rival_identity_request_id": row.get("rival_identity_request_id") or request_id(row),
        "candidate_id": candidate_id(row),
        "target_candidate_id": candidate_id(row),
        "candidate_role": row.get("candidate_role"),
        "candidate_evidence_class": row.get("candidate_evidence_class"),
        "candidate_specific_support": bool(row.get("candidate_specific_support")),
        "strong_own_view_evidence": bool(row.get("strong_own_view_evidence")),
        "has_candidate_association": bool(row.get("has_candidate_association")),
        "visible_count": row.get("visible_count"),
        "mask_hit_count": row.get("mask_hit_count"),
        "box_hit_count": row.get("box_hit_count"),
        "consistent_depth_count": row.get("consistent_depth_count"),
        "depth_mismatch_count": row.get("depth_mismatch_count"),
        "best_box_score": row.get("best_box_score"),
        "min_depth_error_m": row.get("min_depth_error_m"),
        "semantic_rank": row.get("semantic_rank"),
        "semantic_score": row.get("semantic_score"),
        "support_score": row.get("support_score"),
        "target_generated_rank": row.get("target_generated_rank"),
        "target_semantic_rank": row.get("target_semantic_rank"),
        "terminal_arbitration_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_outputs(
    *,
    contract: Dict[str, Any],
    branch_request_rows: Sequence[Dict[str, Any]],
    branch_candidate_rows: Sequence[Dict[str, Any]],
    base_support_rows: Sequence[Dict[str, Any]],
    source_plan_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    target_sources = target_candidate_source_rows(contract=contract, candidate_rows=branch_candidate_rows)
    target_keys = {row_key(row) for row in target_sources}
    base_first = first_by_key(base_support_rows)
    plan_grouped = rows_by_key(source_plan_rows)
    matched_plan_source_rows = [
        row
        for row in source_plan_rows
        if row_key(row) in target_keys
    ]
    matched_plan_source_rows.sort(
        key=lambda row: (
            request_sort_key(request_id(row)),
            candidate_sort_key(candidate_id(row)),
            safe_int(row.get("viewpoint_index")),
            str(row.get("viewpoint_id") or ""),
        )
    )

    target_rows = [
        make_target_candidate_row(
            source=row,
            base=base_first.get(row_key(row)),
            plan_rows=sorted(
                plan_grouped.get(row_key(row), []),
                key=lambda item: (safe_int(item.get("viewpoint_index")), str(item.get("viewpoint_id") or "")),
            ),
            target_index=index,
        )
        for index, row in enumerate(target_sources)
    ]
    request_rows_out = make_request_rows(
        branch_request_rows=branch_request_rows,
        target_rows=target_sources,
        contract=contract,
    )
    source_plan_out = [make_source_plan_row(row, index) for index, row in enumerate(matched_plan_source_rows)]
    base_out = [
        make_base_support_row(base_first[key], index)
        for index, key in enumerate(sorted(target_keys, key=lambda item: (request_sort_key(item[0]), candidate_sort_key(item[1]))))
        if key in base_first
    ]
    return {
        "request_rows": request_rows_out,
        "target_candidate_rows": target_rows,
        "source_plan_rows": source_plan_out,
        "base_support_rows": base_out,
        "target_source_rows": target_sources,
    }


def summarize(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    selection_summary: Dict[str, Any],
    branch_candidate_rows: Sequence[Dict[str, Any]],
    outputs: Dict[str, Any],
) -> Dict[str, Any]:
    request_rows = outputs["request_rows"]
    target_rows = outputs["target_candidate_rows"]
    source_plan_rows = outputs["source_plan_rows"]
    base_rows = outputs["base_support_rows"]
    target_source_rows = outputs["target_source_rows"]
    all_action_rows = [*request_rows, *target_rows, *source_plan_rows, *base_rows]
    forbidden = count_forbidden(all_action_rows)
    gates = contract.get("evaluation_gates") or {}
    scope = contract.get("target_scope") or {}
    expected_query_counts = dict(scope.get("expected_query_counts") or {})
    expected_scene_counts = dict(scope.get("expected_scene_counts") or {})
    expected_direction_counts = dict(scope.get("expected_existing_plan_direction_counts") or {})
    plan_by_target = Counter(row_key(row) for row in source_plan_rows)
    companion_guard_rows = [
        row
        for row in branch_candidate_rows
        if row_key(row) in {row_key(target) for target in target_source_rows}
        and COMPANION_GUARD_BRANCH in set(row.get("candidate_branch_names") or [])
    ]
    terminal_rows = [
        row
        for row in all_action_rows
        if row.get("terminal_commit") is True
        or row.get("terminal_arbitration_allowed") is True
        or row.get("candidate_rejection_allowed") is True
    ]
    candidate_rejection_rows = [row for row in all_action_rows if row.get("candidate_rejection_allowed") is True]
    missing_position_rows = [row for row in target_rows if not row.get("target_position") or not row.get("target_visit_position")]
    query_counts = compact_counter(row.get("query") for row in target_rows)
    scene_counts = compact_counter(row.get("scene_key") for row in target_rows)
    direction_counts = compact_counter(row.get("source_standoff_direction_source") for row in source_plan_rows)
    gate = {
        "source_selection_gate_passed": bool(
            ((selection_summary.get("gate") or {}).get("next_label_free_evidence_family_selection_gate_passed"))
        ),
        "selected_branch_passed": selection_summary.get("diagnostic_conclusion", {}).get("selected_branch") == TARGET_BRANCH,
        "selected_action_passed": selection_summary.get("diagnostic_conclusion", {}).get("selected_action") == TARGET_ACTION,
        "expected_request_rows_passed": len(request_rows) == safe_int(gates.get("expected_request_rows")),
        "expected_target_candidate_rows_passed": len(target_rows) == safe_int(gates.get("expected_target_candidate_rows")),
        "expected_companion_guard_candidate_rows_passed": len(companion_guard_rows)
        == safe_int(scope.get("expected_companion_guard_candidate_rows")),
        "expected_base_support_rows_passed": len(base_rows) == safe_int(gates.get("expected_base_support_rows")),
        "all_base_support_rows_weak_or_partial_passed": compact_counter(row.get("candidate_evidence_class") for row in base_rows)
        == {"weak_or_partial_candidate_specific_support": len(base_rows)},
        "base_candidate_specific_support_false_passed": all(row.get("candidate_specific_support") is False for row in base_rows),
        "base_strong_own_view_false_passed": all(row.get("strong_own_view_evidence") is False for row in base_rows),
        "expected_existing_plan_rows_passed": len(source_plan_rows) == safe_int(gates.get("expected_existing_plan_rows")),
        "minimum_source_plan_rows_per_target_candidate_passed": bool(plan_by_target)
        and min(plan_by_target.values()) >= safe_int((contract.get("input_builder_contract") or {}).get("minimum_source_plan_rows_per_target_candidate")),
        "expected_query_counts_passed": query_counts == expected_query_counts,
        "expected_scene_counts_passed": scene_counts == expected_scene_counts,
        "expected_existing_plan_direction_counts_passed": direction_counts == expected_direction_counts,
        "candidate_positions_available_passed": len(missing_position_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum")),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(gates.get("terminal_commit_rows_maximum")),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        <= safe_int(gates.get("candidate_rejection_rows_maximum")),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in all_action_rows),
        "paper_claim_allowed": False,
    }
    gate["missing_own_view_input_gate_passed"] = all(
        value is True for key, value in gate.items() if key not in {"uses_gt_for_action", "paper_claim_allowed"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "selection_summary": str(args.selection_summary),
            "selection_rows": str(args.selection_rows),
            "object_relation_branch_request_rows": str(args.object_relation_branch_request_rows),
            "object_relation_branch_candidate_rows": str(args.object_relation_branch_candidate_rows),
            "fresh_base_support_candidate_rows": str(args.fresh_base_support_candidate_rows),
            "fresh_object_relation_plan_rows": str(args.fresh_object_relation_plan_rows),
        },
        "target_branch": TARGET_BRANCH,
        "target_action": TARGET_ACTION,
        "companion_guard_branch": COMPANION_GUARD_BRANCH,
        "request_rows": len(request_rows),
        "target_candidate_rows": len(target_rows),
        "base_support_rows": len(base_rows),
        "source_plan_rows": len(source_plan_rows),
        "request_ids": sorted({request_id(row) for row in request_rows}, key=request_sort_key),
        "target_candidate_rows_by_request": dict(
            sorted(Counter(request_id(row) for row in target_rows).items(), key=lambda item: request_sort_key(item[0]))
        ),
        "source_plan_rows_by_request": dict(
            sorted(Counter(request_id(row) for row in source_plan_rows).items(), key=lambda item: request_sort_key(item[0]))
        ),
        "source_plan_rows_by_target": {
            f"{key[0]}::{key[1]}": value
            for key, value in sorted(plan_by_target.items(), key=lambda item: (request_sort_key(item[0][0]), candidate_sort_key(item[0][1])))
        },
        "query_counts": query_counts,
        "scene_counts": scene_counts,
        "base_support_class_counts": compact_counter(row.get("candidate_evidence_class") for row in base_rows),
        "base_has_candidate_association_counts": compact_counter(row.get("has_candidate_association") for row in base_rows),
        "source_plan_direction_counts": direction_counts,
        "source_plan_standoff_distance_counts": compact_counter(row.get("source_standoff_distance_requested") for row in source_plan_rows),
        "candidate_positions_missing": len(missing_position_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "request_rows": "missing_own_view_request_rows.jsonl",
            "target_candidate_rows": "missing_own_view_target_candidate_rows.jsonl",
            "source_plan_rows": "missing_own_view_source_plan_rows.jsonl",
            "base_support_rows": "missing_own_view_base_support_rows.jsonl",
            "summary": "missing_own_view_input_summary.json",
        },
        "interpretation": {
            "fact": "The materializer writes missing-own-view recheck request, candidate, base-support, and source-plan reference rows before any evaluation-label join.",
            "agent_inference": "Passing this gate means all selected missing-own-view candidates are ready for a nonterminal candidate-centered planner smoke, not terminal ObjectNav utility.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--selection-summary", type=Path)
    parser.add_argument("--selection-rows", type=Path)
    parser.add_argument("--object-relation-branch-request-rows", type=Path)
    parser.add_argument("--object-relation-branch-candidate-rows", type=Path)
    parser.add_argument("--fresh-base-support-candidate-rows", type=Path)
    parser.add_argument("--fresh-object-relation-plan-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.selection_summary = source_path(args, contract, "selection_summary", "selection_summary")
    args.selection_rows = source_path(args, contract, "selection_rows", "selection_rows")
    args.object_relation_branch_request_rows = source_path(
        args,
        contract,
        "object_relation_branch_request_rows",
        "object_relation_branch_request_rows",
    )
    args.object_relation_branch_candidate_rows = source_path(
        args,
        contract,
        "object_relation_branch_candidate_rows",
        "object_relation_branch_candidate_rows",
    )
    args.fresh_base_support_candidate_rows = source_path(
        args,
        contract,
        "fresh_base_support_candidate_rows",
        "fresh_base_support_candidate_rows",
    )
    args.fresh_object_relation_plan_rows = source_path(
        args,
        contract,
        "fresh_object_relation_plan_rows",
        "fresh_object_relation_plan_rows",
    )
    # The selection rows file is loaded to enforce source availability, while the summary carries the gate.
    load_jsonl(args.selection_rows)
    branch_request_rows = load_jsonl(args.object_relation_branch_request_rows)
    branch_candidate_rows = load_jsonl(args.object_relation_branch_candidate_rows)
    outputs = build_outputs(
        contract=contract,
        branch_request_rows=branch_request_rows,
        branch_candidate_rows=branch_candidate_rows,
        base_support_rows=load_jsonl(args.fresh_base_support_candidate_rows),
        source_plan_rows=load_jsonl(args.fresh_object_relation_plan_rows),
    )
    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "missing_own_view_request_rows.jsonl", outputs["request_rows"])
    write_jsonl(args.out_root / "missing_own_view_target_candidate_rows.jsonl", outputs["target_candidate_rows"])
    write_jsonl(args.out_root / "missing_own_view_source_plan_rows.jsonl", outputs["source_plan_rows"])
    write_jsonl(args.out_root / "missing_own_view_base_support_rows.jsonl", outputs["base_support_rows"])
    summary = summarize(
        args=args,
        contract=contract,
        selection_summary=load_json(args.selection_summary),
        branch_candidate_rows=branch_candidate_rows,
        outputs=outputs,
    )
    write_json(args.out_root / "missing_own_view_input_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["missing_own_view_input_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
