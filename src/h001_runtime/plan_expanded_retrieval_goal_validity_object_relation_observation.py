import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys
from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    horizontal_distance,
    parse_float_list,
    quaternion_xyzw_from_yaw,
    safe_float,
    vector,
    yaw_to_point,
)


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_observation_plan.v1"
POLICY_NAME = "ExpandedRetrievalGoalValidityObjectRelationObservation"
PLANNER_NAME = "object_relation_depth_recheck_standoff_v1"
VIEWPOINT_POLICY = "relation_multiview_depth_recheck_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"
REQUEST_ACTION = "request_object_relation_observation"
WAIVER_ACTION = "waive_non_target_policy_promotion_only"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def number_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def request_sort_key(request_id: str) -> Tuple[int, str]:
    suffix = str(request_id).split(":")[-1]
    return (int(suffix), str(request_id)) if suffix.isdigit() else (999999, str(request_id))


def row_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id")), str(row.get("candidate_id")))


def target_position(row: Dict[str, Any]) -> Optional[List[float]]:
    return vector(row.get("target_position")) or vector(row.get("position")) or vector(row.get("target_visit_position"))


def target_floor_y(row: Dict[str, Any]) -> Optional[float]:
    visit = vector(row.get("target_visit_position")) or vector(row.get("visit_position"))
    if visit is not None:
        return float(visit[1])
    position = target_position(row)
    return None if position is None else float(position[1])


def normalized_direction(dx: float, dz: float) -> Optional[Tuple[float, float]]:
    norm = math.hypot(float(dx), float(dz))
    if norm < 1e-6:
        return None
    return (float(dx) / norm, float(dz) / norm)


def rotate_direction(dx: float, dz: float, degrees: float) -> Tuple[float, float]:
    radians = math.radians(float(degrees))
    cosine = math.cos(radians)
    sine = math.sin(radians)
    return (dx * cosine - dz * sine, dx * sine + dz * cosine)


def direction_duplicate(direction: Tuple[float, float], existing: Sequence[Tuple[float, float]], tolerance: float = 1e-3) -> bool:
    return any(abs(direction[0] - old[0]) < tolerance and abs(direction[1] - old[1]) < tolerance for old in existing)


def context_anchor_position(target: Dict[str, Any], anchor: Dict[str, Any]) -> Optional[List[float]]:
    position = target_position(target)
    if position is None:
        return None
    dx = safe_float(anchor.get("x_delta_context_minus_candidate_m"))
    dy = safe_float(anchor.get("y_delta_context_minus_candidate_m")) or 0.0
    dz = safe_float(anchor.get("z_delta_context_minus_candidate_m"))
    if dx is None or dz is None:
        return None
    return [float(position[0]) + dx, float(position[1]) + dy, float(position[2]) + dz]


def relation_anchor_sort_key(anchor: Dict[str, Any]) -> Tuple[int, float, int, str]:
    detector_rows = safe_int(anchor.get("context_detector_associated_rows"), default=0)
    distance = safe_float(anchor.get("horizontal_distance_m"))
    if distance is None:
        distance = math.inf
    return (-detector_rows, float(distance), safe_int(anchor.get("context_generated_rank")), str(anchor.get("context_candidate_id")))


def anchor_passes_required_predicates(anchor: Dict[str, Any], required: Sequence[str]) -> bool:
    predicates = set(str(item) for item in (anchor.get("relation_predicates") or []))
    return all(str(predicate) in predicates or anchor.get(str(predicate)) is True for predicate in required)


def select_relation_anchors(
    *,
    target: Dict[str, Any],
    context_rows: Sequence[Dict[str, Any]],
    required_predicates: Sequence[str],
    max_anchors: int,
) -> List[Dict[str, Any]]:
    request_id, candidate_id = row_key(target)
    filtered: List[Dict[str, Any]] = []
    for row in context_rows:
        if str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id")) != request_id:
            continue
        if str(row.get("candidate_id")) != candidate_id:
            continue
        if row.get("context_candidate_id") is None:
            continue
        if str(row.get("context_candidate_id")) == candidate_id:
            continue
        if not anchor_passes_required_predicates(row, required_predicates):
            continue
        if context_anchor_position(target, row) is None:
            continue
        filtered.append(dict(row))
    filtered.sort(key=relation_anchor_sort_key)
    return filtered[: max(1, int(max_anchors))]


def candidate_snapshot(target: Dict[str, Any], role: str) -> Dict[str, Any]:
    return {
        "candidate_id": str(target.get("candidate_id")),
        "candidate_role": role,
        "category": target.get("query") or target.get("category"),
        "generated_rank": target.get("target_generated_rank"),
        "semantic_rank": target.get("target_semantic_rank"),
        "semantic_score": target.get("target_semantic_score"),
        "support_score": target.get("target_support_score"),
        "score": target.get("target_score"),
        "positive_support": target.get("target_positive_support"),
        "position": target.get("target_position"),
        "visit_position": target.get("target_visit_position"),
        "relation_density_bucket": target.get("relation_density_bucket"),
        "relation_view_consistency_profile": target.get("relation_view_consistency_profile"),
        "detector_visible_rows": target.get("detector_visible_rows"),
        "detector_inside_mask_rows": target.get("detector_inside_mask_rows"),
        "detector_depth_mismatch_rows": target.get("detector_depth_mismatch_rows"),
        "uses_gt_for_action": False,
    }


def relation_anchor_snapshot(target: Dict[str, Any], anchor: Dict[str, Any], role: str) -> Dict[str, Any]:
    position = context_anchor_position(target, anchor)
    return {
        "candidate_id": str(anchor.get("context_candidate_id")),
        "candidate_role": role,
        "category": target.get("query") or target.get("category"),
        "generated_rank": anchor.get("context_generated_rank"),
        "semantic_rank": anchor.get("context_generated_rank"),
        "score": None,
        "position": position,
        "visit_position": position,
        "relation_predicates": anchor.get("relation_predicates"),
        "relation_anchor_distance_m": anchor.get("horizontal_distance_m"),
        "context_detector_associated_rows": anchor.get("context_detector_associated_rows"),
        "same_component_proxy": anchor.get("same_component_proxy"),
        "same_support_surface_proxy": anchor.get("same_support_surface_proxy"),
        "near_2m_proxy": anchor.get("near_2m_proxy"),
        "uses_gt_for_action": False,
    }


def artifact_candidate(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": str(snapshot.get("candidate_id")),
        "category": snapshot.get("category"),
        "score": snapshot.get("score"),
        "semantic_rank": snapshot.get("semantic_rank"),
        "semantic_score": snapshot.get("semantic_score"),
        "support_score": snapshot.get("support_score"),
        "positive_support": snapshot.get("positive_support"),
        "candidate_backend": "object_relation_context",
        "candidate_reachable": None,
        "position": snapshot.get("position"),
        "visit_position": snapshot.get("visit_position"),
        "source": "expanded_retrieval_goal_validity_object_relation_observation_plan",
        "candidate_role": snapshot.get("candidate_role"),
        "relation_predicates": snapshot.get("relation_predicates"),
        "relation_anchor_distance_m": snapshot.get("relation_anchor_distance_m"),
        "uses_gt_for_action": False,
    }


def candidate_artifact_rows(plan_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    scene_keys: Dict[Tuple[str, str], str] = {}
    for row in plan_rows:
        key = (str(row.get("scene_id")), str(row.get("query")))
        scene_keys[key] = str(row.get("scene_key") or "")
        for snapshot in row.get("goal_validity_context_candidate_snapshots") or []:
            grouped[key][str(snapshot.get("candidate_id"))] = artifact_candidate(snapshot)

    output: List[Dict[str, Any]] = []
    for (scene_id, query), candidates_by_id in sorted(grouped.items()):
        candidates = list(candidates_by_id.values())
        candidates.sort(
            key=lambda candidate: (
                safe_int(candidate.get("semantic_rank")),
                str(candidate.get("candidate_id")),
            )
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "expanded_retrieval_goal_validity_object_relation_observation_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": scene_keys.get((scene_id, query)),
                "query": query,
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return output


def relation_directions(target: Dict[str, Any], anchors: Sequence[Dict[str, Any]]) -> List[Tuple[float, float, str, Optional[str]]]:
    position = target_position(target)
    if position is None:
        return []

    directions: List[Tuple[float, float, str, Optional[str]]] = []
    seen: List[Tuple[float, float]] = []

    def add(dx: float, dz: float, source: str, anchor_id: Optional[str]) -> None:
        direction = normalized_direction(dx, dz)
        if direction is None or direction_duplicate(direction, seen):
            return
        directions.append((direction[0], direction[1], source, anchor_id))
        seen.append(direction)

    visit = vector(target.get("target_visit_position")) or vector(target.get("visit_position"))
    if visit is not None:
        add(visit[0] - position[0], visit[2] - position[2], "source_viewpoint_to_target", None)

    for anchor in anchors:
        anchor_position = context_anchor_position(target, anchor)
        if anchor_position is None:
            continue
        anchor_id = str(anchor.get("context_candidate_id"))
        dx = anchor_position[0] - position[0]
        dz = anchor_position[2] - position[2]
        add(dx, dz, "target_to_relation_anchor", anchor_id)
        add(-dx, -dz, "relation_anchor_to_target", anchor_id)
        add(-dz, dx, "orthogonal_relation_axis", anchor_id)
        add(dz, -dx, "orthogonal_relation_axis", anchor_id)

    for degrees in (0, 45, 90, 135, 180, 225, 270, 315):
        radians = math.radians(degrees)
        add(math.sin(radians), math.cos(radians), "relation_anchor_completion_axis", None)
    return directions


def make_viewpoint(
    *,
    target: Dict[str, Any],
    direction: Tuple[float, float, str, Optional[str]],
    distance: float,
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    position = target_position(target)
    floor_y = target_floor_y(target)
    if position is None or floor_y is None:
        return None
    dx, dz, direction_source, anchor_id = direction
    desired = [
        float(position[0]) + dx * float(distance),
        float(floor_y),
        float(position[2]) + dz * float(distance),
    ]
    scene_id = str(target.get("scene_id"))
    snapped, navigable, snap_distance = snapper.snap(scene_id, desired)
    if bool(args.require_navmesh_standoff) and not navigable:
        return None
    target_distance = horizontal_distance(snapped, position)
    if target_distance < float(args.min_standoff_distance_m) or target_distance > float(args.max_standoff_distance_m):
        return None
    yaw = yaw_to_point(snapped, position)
    if yaw is None:
        return None
    snap_penalty = snap_distance if snap_distance is not None else 0.0
    score = abs(target_distance - float(args.preferred_standoff_distance_m)) + 0.20 * snap_penalty
    return {
        "position": [float(value) for value in snapped],
        "rotation": quaternion_xyzw_from_yaw(yaw),
        "yaw": float(yaw),
        "target_position": position,
        "target_horizontal_distance": float(target_distance),
        "desired_position": desired,
        "snap_distance": snap_distance,
        "navmesh_snapped": snap_distance is not None,
        "navmesh_navigable": bool(navigable),
        "direction_source": direction_source,
        "relation_anchor_candidate_id": anchor_id,
        "standoff_distance_requested": float(distance),
        "viewpoint_source": "standoff_navmesh" if snap_distance is not None else "standoff_geometry",
        "projection_sane": True,
        "score": float(score),
    }


def plan_viewpoints(
    *,
    target: Dict[str, Any],
    anchors: Sequence[Dict[str, Any]],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    used_keys: set[Tuple[str, Optional[str]]] = set()
    for direction in relation_directions(target, anchors):
        for distance in args.standoff_distances:
            viewpoint = make_viewpoint(target=target, direction=direction, distance=float(distance), snapper=snapper, args=args)
            if viewpoint is None:
                continue
            key = (str(viewpoint.get("direction_source")), viewpoint.get("relation_anchor_candidate_id"))
            if key in used_keys:
                continue
            selected.append(viewpoint)
            used_keys.add(key)
            break
        if len(selected) >= int(args.minimum_viewpoints_per_target):
            break
    return selected[: int(args.minimum_viewpoints_per_target)]


def count_output_forbidden(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def make_plan_row(
    *,
    args: argparse.Namespace,
    target: Dict[str, Any],
    anchors: Sequence[Dict[str, Any]],
    request_index: int,
    target_index: int,
    viewpoint_index: int,
    viewpoint: Dict[str, Any],
) -> Dict[str, Any]:
    target_id = str(target.get("candidate_id"))
    snapshots = [candidate_snapshot(target, "target_candidate")]
    snapshots.extend(
        relation_anchor_snapshot(target, anchor, "relation_anchor_candidate") for anchor in anchors
    )
    context_ids = [str(snapshot.get("candidate_id")) for snapshot in snapshots if snapshot.get("candidate_id") is not None]
    anchor_ids = [str(anchor.get("context_candidate_id")) for anchor in anchors if anchor.get("context_candidate_id") is not None]
    position = [float(item) for item in viewpoint["position"]]
    target_pos = target_position(target)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "contract_name": "expanded_retrieval_goal_validity_object_relation_observation_plan_v1",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "request_index": request_index,
        "target_index": target_index,
        "viewpoint_index": viewpoint_index,
        "episode_key": target.get("episode_key"),
        "scene_id": target.get("scene_id"),
        "scene_key": target.get("scene_key"),
        "query": target.get("query"),
        "rival_identity_request_id": target.get("rival_identity_request_id"),
        "expanded_retrieval_request_id": target.get("expanded_retrieval_request_id"),
        "viewpoint_id": (
            f"goal_validity_object_relation:{target.get('expanded_retrieval_request_id')}:"
            f"{target_id}:v{viewpoint_index:02d}"
        ),
        "candidate_id": target_id,
        "target_candidate_id": target_id,
        "candidate_ids": context_ids,
        "goal_validity_context_candidate_ids": context_ids,
        "goal_validity_relation_anchor_candidate_ids": anchor_ids,
        "goal_validity_relation_anchor_count": len(anchor_ids),
        "goal_validity_context_candidate_snapshots": snapshots,
        "target_candidate_role": "target_candidate",
        "target_generated_rank": target.get("target_generated_rank"),
        "target_semantic_rank": target.get("target_semantic_rank"),
        "target_semantic_score": target.get("target_semantic_score"),
        "target_support_score": target.get("target_support_score"),
        "target_score": target.get("target_score"),
        "target_positive_support": target.get("target_positive_support"),
        "target_position": target.get("target_position"),
        "target_visit_position": target.get("target_visit_position"),
        "target_relation_density_bucket": target.get("relation_density_bucket"),
        "target_relation_signature_score": target.get("relation_signature_score"),
        "target_relation_view_consistency_profile": target.get("relation_view_consistency_profile"),
        "target_detector_visible_rows": target.get("detector_visible_rows"),
        "target_detector_inside_mask_rows": target.get("detector_inside_mask_rows"),
        "target_detector_depth_mismatch_rows": target.get("detector_depth_mismatch_rows"),
        "viewpoint_position": position,
        "viewpoint_rotation": [float(item) for item in viewpoint["rotation"]],
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "target_distance_from_viewpoint_m": None if target_pos is None else horizontal_distance(position, target_pos),
        "standoff_target_position": viewpoint.get("target_position"),
        "standoff_desired_position": viewpoint.get("desired_position"),
        "standoff_target_horizontal_distance": viewpoint.get("target_horizontal_distance"),
        "standoff_snap_distance": viewpoint.get("snap_distance"),
        "standoff_navmesh_snapped": viewpoint.get("navmesh_snapped"),
        "standoff_navmesh_navigable": viewpoint.get("navmesh_navigable"),
        "standoff_direction_source": viewpoint.get("direction_source"),
        "standoff_relation_anchor_candidate_id": viewpoint.get("relation_anchor_candidate_id"),
        "standoff_distance_requested": viewpoint.get("standoff_distance_requested"),
        "standoff_projection_sane": viewpoint.get("projection_sane"),
        "standoff_viewpoint_yaw_rad": viewpoint.get("yaw"),
        "standoff_score": viewpoint.get("score"),
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_label_free": True,
        "object_relation_observation_action": "collect_relation_aware_depth_recheck",
        "object_relation_observation_reason": "detector_visible_but_depth_weak_relation_dense_gap",
        "terminal_commit_allowed": False,
        "commit_after_object_relation_observation": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_skip_row(
    *,
    target: Dict[str, Any],
    request_index: int,
    target_index: int,
    reason: str,
    anchor_ids: Sequence[str],
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_name": "expanded_retrieval_goal_validity_object_relation_observation_plan_v1",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "target_index": target_index,
        "episode_key": target.get("episode_key"),
        "scene_id": target.get("scene_id"),
        "scene_key": target.get("scene_key"),
        "query": target.get("query"),
        "expanded_retrieval_request_id": target.get("expanded_retrieval_request_id"),
        "rival_identity_request_id": target.get("rival_identity_request_id"),
        "candidate_id": target.get("candidate_id"),
        "target_candidate_id": target.get("candidate_id"),
        "target_generated_rank": target.get("target_generated_rank"),
        "target_semantic_rank": target.get("target_semantic_rank"),
        "goal_validity_relation_anchor_candidate_ids": list(anchor_ids),
        "skip_reason": reason,
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def contract_expected_ids(contract: Dict[str, Any]) -> List[str]:
    scope = contract.get("target_scope") or {}
    return sorted([str(value) for value in scope.get("expected_request_ids") or []], key=request_sort_key)


def observation_targets(
    *,
    coverage_gap_rows: Sequence[Dict[str, Any]],
    repair_action_rows: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    gap_by_key = {row_key(row): dict(row) for row in coverage_gap_rows}
    targets: List[Dict[str, Any]] = []
    waivers: List[Dict[str, Any]] = []
    for action in repair_action_rows:
        action_name = str(action.get("repair_action"))
        key = row_key(action)
        joined = dict(gap_by_key.get(key, {}))
        joined.update({key_name: value for key_name, value in action.items() if value is not None})
        if action_name == REQUEST_ACTION:
            targets.append(joined)
        elif action_name == WAIVER_ACTION:
            waivers.append(joined)
    targets.sort(key=lambda row: (request_sort_key(row_key(row)[0]), safe_int(row.get("target_generated_rank")), row_key(row)[1]))
    waivers.sort(key=lambda row: (request_sort_key(row_key(row)[0]), safe_int(row.get("target_generated_rank")), row_key(row)[1]))
    return targets, waivers


def summarize(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    coverage_gap_rows: Sequence[Dict[str, Any]],
    repair_action_rows: Sequence[Dict[str, Any]],
    target_rows: Sequence[Dict[str, Any]],
    waiver_rows: Sequence[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
    skipped_rows: Sequence[Dict[str, Any]],
    artifact_rows: Sequence[Dict[str, Any]],
    source_summary: Dict[str, Any],
) -> Dict[str, Any]:
    minimum = contract.get("minimum_plan_gate") or {}
    planned_request_ids = sorted(
        {
            str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
            for row in plan_rows
        },
        key=request_sort_key,
    )
    plan_rows_by_request = Counter(
        str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id")) for row in plan_rows
    )
    target_ids = sorted({row_key(row)[0] for row in target_rows}, key=request_sort_key)
    expected_ids = contract_expected_ids(contract)
    relation_anchor_counts = [len(row.get("goal_validity_relation_anchor_candidate_ids") or []) for row in plan_rows]
    target_distances = [
        float(value)
        for value in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if value is not None
    ]
    terminal_rows = [row for row in [*plan_rows, *skipped_rows] if row.get("terminal_commit_allowed") is True]
    forbidden = count_output_forbidden([*plan_rows, *skipped_rows])
    source_gate = (source_summary.get("gate") or {}).get("coverage_repair_gate_passed")
    if source_gate is None:
        source_gate = source_summary.get("coverage_repair_gate_passed")

    gate = {
        "coverage_repair_gate_passed": bool(source_gate) == bool(minimum.get("coverage_repair_gate_passed", True)),
        "source_coverage_gap_rows_passed": len(coverage_gap_rows) == int(minimum.get("source_coverage_gap_rows", 0)),
        "source_repair_action_rows_passed": len(repair_action_rows) == int(minimum.get("source_repair_action_rows", 0)),
        "observation_target_rows_passed": len(target_rows) == int(minimum.get("observation_target_rows", 0)),
        "waiver_rows_passed": len(waiver_rows) == int(minimum.get("waiver_rows", 0)),
        "request_ids_passed": target_ids == expected_ids,
        "planned_request_rows_passed": len(planned_request_ids) == int(minimum.get("planned_request_rows", 0)),
        "plan_rows_minimum_passed": len(plan_rows) >= int(minimum.get("plan_rows_minimum", 0)),
        "plan_rows_per_request_minimum_passed": bool(plan_rows_by_request)
        and min(plan_rows_by_request.values()) >= int(minimum.get("plan_rows_per_request_minimum", 0)),
        "skipped_rows_maximum_passed": len(skipped_rows) <= int(minimum.get("skipped_rows_maximum", 0)),
        "candidate_artifact_rows_minimum_passed": len(artifact_rows)
        >= int(minimum.get("candidate_artifact_rows_minimum", 1)),
        "relation_anchor_candidates_per_plan_minimum_passed": bool(relation_anchor_counts)
        and min(relation_anchor_counts) >= int(minimum.get("relation_anchor_candidates_per_plan_minimum", 0)),
        "output_forbidden_action_fields_passed": len(forbidden) == int(minimum.get("output_forbidden_action_fields", 0)),
        "terminal_commit_rows_passed": len(terminal_rows) == int(minimum.get("terminal_commit_rows", 0)),
        "uses_gt_for_action_passed": not any(row.get("uses_gt_for_action") is True for row in [*plan_rows, *skipped_rows]),
        "paper_claim_allowed": False,
    }
    gate["object_relation_observation_plan_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "coverage_gap_rows": str(args.coverage_gap_rows),
        "coverage_repair_action_rows": str(args.coverage_repair_action_rows),
        "context_object_rows": str(args.context_object_rows),
        "source_summary": str(args.coverage_repair_summary),
        "out_root": str(args.out_root),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "coverage_repair_gate_passed": bool(source_gate),
        "source_coverage_gap_rows": len(coverage_gap_rows),
        "source_repair_action_rows": len(repair_action_rows),
        "observation_target_rows": len(target_rows),
        "waiver_rows": len(waiver_rows),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "planned_request_ids": planned_request_ids,
        "target_request_ids": target_ids,
        "expected_request_ids": expected_ids,
        "plan_rows_by_request": dict(sorted(plan_rows_by_request.items())),
        "plan_rows_per_request_min": min(plan_rows_by_request.values()) if plan_rows_by_request else 0,
        "plan_rows_per_request_max": max(plan_rows_by_request.values()) if plan_rows_by_request else 0,
        "skipped_reason_counts": dict(sorted(Counter(str(row.get("skip_reason")) for row in skipped_rows).items())),
        "viewpoint_source_counts": dict(sorted(Counter(str(row.get("viewpoint_source")) for row in plan_rows).items())),
        "direction_source_counts": dict(sorted(Counter(str(row.get("standoff_direction_source")) for row in plan_rows).items())),
        "relation_anchor_candidates_per_plan": number_stats([float(value) for value in relation_anchor_counts]),
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "candidate_artifact_rows": len(artifact_rows),
        "candidate_artifact_candidate_count": sum(int(row.get("candidate_count") or 0) for row in artifact_rows),
        "terminal_commit_rows": len(terminal_rows),
        "output_forbidden_action_field_count": len(forbidden),
        "output_forbidden_action_fields": forbidden[:50],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "interpretation": {
            "facts": (
                "Planner consumes coverage-repair action rows and relation context rows, then writes relation-aware "
                "multiview standoff observations without evaluation labels."
            ),
            "inference": (
                "This is a planner substrate. It can support the next frame/projection/detector smoke test, but it "
                "does not yet prove terminal navigation utility."
            ),
        },
        "output_files": {
            "plan": "goal_validity_object_relation_observation_plan.jsonl",
            "skipped": "goal_validity_object_relation_observation_skipped.jsonl",
            "candidate_artifact": "goal_validity_object_relation_observation_candidate_artifact.jsonl",
            "summary": "goal_validity_object_relation_observation_plan_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    source_summary = load_json(Path(args.coverage_repair_summary))
    coverage_gap_rows = load_jsonl(Path(args.coverage_gap_rows))
    repair_action_rows = load_jsonl(Path(args.coverage_repair_action_rows))
    context_rows = load_jsonl(Path(args.context_object_rows))
    targets, waivers = observation_targets(
        coverage_gap_rows=coverage_gap_rows,
        repair_action_rows=repair_action_rows,
    )

    expected_ids = contract_expected_ids(contract)
    target_ids = sorted({row_key(row)[0] for row in targets}, key=request_sort_key)
    if target_ids != expected_ids:
        raise ValueError(f"unexpected observation target request ids: observed={target_ids} expected={expected_ids}")

    required_predicates = (
        ((contract.get("planner") or {}).get("relation_anchor_rule") or {}).get("required_action_time_predicates")
        or ["same_component_proxy", "same_support_surface_proxy", "near_2m_proxy"]
    )
    max_anchors = int(
        ((contract.get("planner") or {}).get("relation_anchor_rule") or {}).get(
            "max_relation_anchor_candidates_per_target",
            args.max_relation_anchor_candidates_per_target,
        )
    )

    out_root = Path(args.out_root)
    snapper = NavmeshSnapper(args.data_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    try:
        for request_index, request_id in enumerate(expected_ids):
            request_targets = [row for row in targets if row_key(row)[0] == request_id]
            for target_index, target in enumerate(request_targets):
                anchors = select_relation_anchors(
                    target=target,
                    context_rows=context_rows,
                    required_predicates=required_predicates,
                    max_anchors=max_anchors,
                )
                anchor_ids = [str(anchor.get("context_candidate_id")) for anchor in anchors]
                if len(anchor_ids) < int(args.min_relation_anchor_candidates_per_plan):
                    skipped_rows.append(
                        make_skip_row(
                            target=target,
                            request_index=request_index,
                            target_index=target_index,
                            reason="insufficient_relation_anchor_candidates",
                            anchor_ids=anchor_ids,
                        )
                    )
                    continue
                viewpoints = plan_viewpoints(target=target, anchors=anchors, snapper=snapper, args=args)
                if len(viewpoints) < int(args.minimum_viewpoints_per_target):
                    skipped_rows.append(
                        make_skip_row(
                            target=target,
                            request_index=request_index,
                            target_index=target_index,
                            reason="insufficient_navmesh_relation_viewpoints",
                            anchor_ids=anchor_ids,
                        )
                    )
                    continue
                for viewpoint_index, viewpoint in enumerate(viewpoints):
                    plan_rows.append(
                        make_plan_row(
                            args=args,
                            target=target,
                            anchors=anchors,
                            request_index=request_index,
                            target_index=target_index,
                            viewpoint_index=viewpoint_index,
                            viewpoint=viewpoint,
                        )
                    )
    finally:
        snapper.close()

    artifact_rows = candidate_artifact_rows(plan_rows)
    write_jsonl(out_root / "goal_validity_object_relation_observation_plan.jsonl", plan_rows)
    write_jsonl(out_root / "goal_validity_object_relation_observation_skipped.jsonl", skipped_rows)
    write_jsonl(out_root / "goal_validity_object_relation_observation_candidate_artifact.jsonl", artifact_rows)
    summary = summarize(
        args=args,
        contract=contract,
        coverage_gap_rows=coverage_gap_rows,
        repair_action_rows=repair_action_rows,
        target_rows=targets,
        waiver_rows=waivers,
        plan_rows=plan_rows,
        skipped_rows=skipped_rows,
        artifact_rows=artifact_rows,
        source_summary=source_summary,
    )
    write_json(out_root / "goal_validity_object_relation_observation_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan relation-aware object observation for expanded-retrieval goal-validity gaps."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--coverage-repair-summary", required=True)
    parser.add_argument("--coverage-gap-rows", required=True)
    parser.add_argument("--coverage-repair-action-rows", required=True)
    parser.add_argument("--context-object-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--run-id", default="h001_expanded_retrieval_goal_validity_object_relation_observation_v1")
    parser.add_argument("--max-relation-anchor-candidates-per-target", type=int, default=8)
    parser.add_argument("--min-relation-anchor-candidates-per-plan", type=int, default=2)
    parser.add_argument("--minimum-viewpoints-per-target", type=int, default=4)
    parser.add_argument("--standoff-distances", type=parse_float_list, default=[1.25, 1.75, 2.25, 2.75])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--require-navmesh-standoff", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--projection-anchor-height-offsets-m",
        type=parse_float_list,
        default=[0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4],
    )
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["object_relation_observation_plan_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
