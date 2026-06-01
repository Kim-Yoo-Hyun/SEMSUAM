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
    normalize_xz,
    parse_float_list,
    quaternion_xyzw_from_yaw,
    safe_float,
    vector,
    yaw_to_point,
)


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_goal_region_plan.v1"
POLICY_NAME = "ExpandedRetrievalGoalValidityUniqueSupportGoalRegion"
PLANNER_NAME = "unique_support_goal_region_v1"
VIEWPOINT_POLICY = "contrastive_goal_region_standoff_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"
TARGET_BRANCH = "unique_support_visibility_not_goal_validity"
TARGET_ACTION = "request_contrastive_goal_region_evidence"
DEFAULT_GEOMETRY_PLAN = (
    "local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1/"
    "goal_validity_object_relation_observation_plan.jsonl"
)


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


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def request_sort_key(value: str) -> Tuple[int, str]:
    suffix = str(value).split(":")[-1]
    return (int(suffix), str(value)) if suffix.isdigit() else (999999, str(value))


def unique_preserve_order(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        item = str(value)
        if not item or item in seen:
            continue
        output.append(item)
        seen.add(item)
    return output


def branch_candidate_ids(row: Dict[str, Any], branch_name: str) -> List[str]:
    ids: List[str] = []
    for item in row.get("branch_candidate_items") or []:
        if str(item.get("branch_name")) == str(branch_name):
            ids.extend(str(value) for value in item.get("candidate_ids") or [] if value is not None)
    return unique_preserve_order(ids)


def index_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        rid = request_id(row)
        if rid and rid not in indexed:
            indexed[rid] = dict(row)
    return indexed


def candidate_snapshot_from_plan(plan_row: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
    candidate_id = str(snapshot.get("candidate_id"))
    return {
        "candidate_id": candidate_id,
        "category": snapshot.get("category") or plan_row.get("query"),
        "score": snapshot.get("score"),
        "semantic_rank": snapshot.get("semantic_rank") or snapshot.get("generated_rank"),
        "semantic_score": snapshot.get("semantic_score"),
        "support_score": snapshot.get("support_score"),
        "positive_support": snapshot.get("positive_support"),
        "candidate_role": snapshot.get("candidate_role"),
        "generated_rank": snapshot.get("generated_rank"),
        "position": snapshot.get("position"),
        "visit_position": snapshot.get("visit_position"),
        "relation_predicates": snapshot.get("relation_predicates"),
        "relation_anchor_distance_m": snapshot.get("relation_anchor_distance_m"),
        "context_detector_associated_rows": snapshot.get("context_detector_associated_rows"),
        "detector_visible_rows": snapshot.get("detector_visible_rows"),
        "detector_inside_mask_rows": snapshot.get("detector_inside_mask_rows"),
        "detector_depth_mismatch_rows": snapshot.get("detector_depth_mismatch_rows"),
        "scene_id": plan_row.get("scene_id"),
        "scene_key": plan_row.get("scene_key"),
        "query": plan_row.get("query"),
        "episode_key": plan_row.get("episode_key"),
        "expanded_retrieval_request_id": request_id(plan_row),
        "rival_identity_request_id": plan_row.get("rival_identity_request_id"),
        "uses_gt_for_action": False,
    }


def target_snapshot_from_plan(plan_row: Dict[str, Any]) -> Dict[str, Any]:
    candidate_id = str(plan_row.get("candidate_id") or plan_row.get("target_candidate_id"))
    return {
        "candidate_id": candidate_id,
        "category": plan_row.get("query"),
        "score": plan_row.get("target_score"),
        "semantic_rank": plan_row.get("target_semantic_rank"),
        "semantic_score": plan_row.get("target_semantic_score"),
        "support_score": plan_row.get("target_support_score"),
        "positive_support": plan_row.get("target_positive_support"),
        "candidate_role": plan_row.get("target_candidate_role") or "target_candidate",
        "generated_rank": plan_row.get("target_generated_rank"),
        "position": plan_row.get("target_position"),
        "visit_position": plan_row.get("target_visit_position"),
        "relation_predicates": None,
        "relation_anchor_distance_m": None,
        "context_detector_associated_rows": None,
        "detector_visible_rows": plan_row.get("target_detector_visible_rows"),
        "detector_inside_mask_rows": plan_row.get("target_detector_inside_mask_rows"),
        "detector_depth_mismatch_rows": plan_row.get("target_detector_depth_mismatch_rows"),
        "scene_id": plan_row.get("scene_id"),
        "scene_key": plan_row.get("scene_key"),
        "query": plan_row.get("query"),
        "episode_key": plan_row.get("episode_key"),
        "expanded_retrieval_request_id": request_id(plan_row),
        "rival_identity_request_id": plan_row.get("rival_identity_request_id"),
        "uses_gt_for_action": False,
    }


def geometry_index(plan_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in plan_rows:
        rid = request_id(row)
        candidate_id = row.get("candidate_id") or row.get("target_candidate_id")
        if rid and candidate_id is not None:
            indexed[(rid, str(candidate_id))] = target_snapshot_from_plan(row)
        for snapshot in row.get("goal_validity_context_candidate_snapshots") or []:
            candidate_id = snapshot.get("candidate_id")
            if rid and candidate_id is not None:
                indexed[(rid, str(candidate_id))] = candidate_snapshot_from_plan(row, snapshot)
    return indexed


def candidate_position(candidate: Dict[str, Any]) -> Optional[List[float]]:
    return vector(candidate.get("position")) or vector(candidate.get("visit_position"))


def candidate_floor_y(candidate: Dict[str, Any]) -> Optional[float]:
    visit = vector(candidate.get("visit_position"))
    if visit is not None:
        return float(visit[1])
    position = candidate_position(candidate)
    return None if position is None else float(position[1])


def candidate_artifact_payload(candidate: Dict[str, Any], role: str) -> Dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "category": candidate.get("category"),
        "score": candidate.get("score"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_backend": "unique_support_goal_region",
        "candidate_reachable": None,
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "candidate_role": role,
        "relation_predicates": candidate.get("relation_predicates"),
        "source": "expanded_retrieval_goal_validity_unique_support_goal_region_plan",
        "uses_gt_for_action": False,
    }


def candidate_artifact_rows(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    scene_keys: Dict[Tuple[str, str, str], str] = {}
    for row in candidate_rows:
        key = (str(row.get("scene_id")), str(row.get("query")), str(row.get("expanded_retrieval_request_id")))
        scene_keys[key] = str(row.get("scene_key") or "")
        grouped[key][str(row.get("candidate_id"))] = candidate_artifact_payload(row, str(row.get("goal_region_candidate_role")))

    output: List[Dict[str, Any]] = []
    for (scene_id, query, rid), candidates_by_id in sorted(grouped.items(), key=lambda item: request_sort_key(item[0][2])):
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
                "artifact_type": "unique_support_goal_region_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": scene_keys.get((scene_id, query, rid)),
                "query": query,
                "expanded_retrieval_request_id": rid,
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return output


def standoff_directions(target: Dict[str, Any], alt: Optional[Dict[str, Any]]) -> List[Tuple[float, float, str]]:
    target_pos = candidate_position(target)
    directions: List[Tuple[float, float, str]] = []
    if target_pos is None:
        return directions

    def add(dx: float, dz: float, source: str) -> None:
        direction = normalize_xz(dx, dz)
        if direction is None:
            return
        ux, uz = direction
        if any(abs(ux - old_x) < 1e-3 and abs(uz - old_z) < 1e-3 for old_x, old_z, _ in directions):
            return
        directions.append((ux, uz, source))

    alt_pos = candidate_position(alt or {})
    if alt_pos is not None:
        add(alt_pos[0] - target_pos[0], alt_pos[2] - target_pos[2], "alt_candidate_to_target")
        add(target_pos[0] - alt_pos[0], target_pos[2] - alt_pos[2], "target_to_alt_candidate")
        add(-(alt_pos[2] - target_pos[2]), alt_pos[0] - target_pos[0], "pair_orthogonal_axis")
        add(alt_pos[2] - target_pos[2], -(alt_pos[0] - target_pos[0]), "pair_orthogonal_axis")

    for degrees in (0, 45, 90, 135, 180, 225, 270, 315):
        radians = math.radians(float(degrees))
        add(math.sin(radians), math.cos(radians), f"compass_{degrees}")
    return directions


def standoff_viewpoint(
    *,
    target: Dict[str, Any],
    alt: Optional[Dict[str, Any]],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    target_pos = candidate_position(target)
    floor_y = candidate_floor_y(target)
    if target_pos is None or floor_y is None:
        return None
    scene_id = str(target.get("scene_id"))
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for distance in args.standoff_distances:
        for dx, dz, direction_source in standoff_directions(target, alt):
            desired = [
                float(target_pos[0]) + dx * float(distance),
                float(floor_y),
                float(target_pos[2]) + dz * float(distance),
            ]
            snapped, navigable, snap_distance = snapper.snap(scene_id, desired)
            if bool(args.require_navmesh_standoff) and not navigable:
                continue
            target_distance = horizontal_distance(snapped, target_pos)
            if target_distance < float(args.min_standoff_distance_m):
                continue
            if target_distance > float(args.max_standoff_distance_m):
                continue
            yaw = yaw_to_point(snapped, target_pos)
            if yaw is None:
                continue
            snap_penalty = snap_distance if snap_distance is not None else 0.0
            score = abs(target_distance - float(args.preferred_standoff_distance_m)) + 0.20 * snap_penalty
            viewpoint = {
                "position": [float(value) for value in snapped],
                "rotation": quaternion_xyzw_from_yaw(yaw),
                "yaw": float(yaw),
                "target_position": target_pos,
                "desired_position": desired,
                "target_horizontal_distance": float(target_distance),
                "snap_distance": snap_distance,
                "navmesh_snapped": snap_distance is not None,
                "navmesh_navigable": bool(navigable),
                "direction_source": direction_source,
                "standoff_distance_requested": float(distance),
                "viewpoint_source": "standoff_navmesh" if snap_distance is not None else "standoff_geometry",
                "projection_sane": True,
                "score": float(score),
            }
            if best is None or score < best[0]:
                best = (score, viewpoint)
    return None if best is None else best[1]


def common_pair_viewpoint(
    *,
    focus: Dict[str, Any],
    rival: Dict[str, Any],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    focus_pos = candidate_position(focus)
    rival_pos = candidate_position(rival)
    if focus_pos is None or rival_pos is None:
        return None
    dx = rival_pos[0] - focus_pos[0]
    dz = rival_pos[2] - focus_pos[2]
    unit = normalize_xz(dx, dz)
    if unit is None:
        return None
    ux, uz = unit
    perpendiculars = [(-uz, ux, "pair_perpendicular_left"), (uz, -ux, "pair_perpendicular_right")]
    midpoint = [
        (float(focus_pos[0]) + float(rival_pos[0])) / 2.0,
        candidate_floor_y(focus) if candidate_floor_y(focus) is not None else float(focus_pos[1]),
        (float(focus_pos[2]) + float(rival_pos[2])) / 2.0,
    ]
    scene_id = str(focus.get("scene_id"))
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for distance in args.common_pair_distances:
        for px, pz, source in perpendiculars:
            desired = [
                float(midpoint[0]) + px * float(distance),
                float(midpoint[1]),
                float(midpoint[2]) + pz * float(distance),
            ]
            snapped, navigable, snap_distance = snapper.snap(scene_id, desired)
            if bool(args.require_navmesh_standoff) and not navigable:
                continue
            focus_distance = horizontal_distance(snapped, focus_pos)
            rival_distance = horizontal_distance(snapped, rival_pos)
            if focus_distance < float(args.min_standoff_distance_m) or rival_distance < float(args.min_standoff_distance_m):
                continue
            if focus_distance > float(args.max_pair_view_distance_m) or rival_distance > float(args.max_pair_view_distance_m):
                continue
            yaw = yaw_to_point(snapped, midpoint)
            if yaw is None:
                continue
            snap_penalty = snap_distance if snap_distance is not None else 0.0
            balance_penalty = abs(focus_distance - rival_distance)
            distance_penalty = abs(max(focus_distance, rival_distance) - float(args.preferred_standoff_distance_m))
            score = balance_penalty + 0.5 * distance_penalty + 0.20 * snap_penalty
            viewpoint = {
                "position": [float(value) for value in snapped],
                "rotation": quaternion_xyzw_from_yaw(yaw),
                "yaw": float(yaw),
                "target_position": midpoint,
                "desired_position": desired,
                "pair_midpoint": midpoint,
                "focus_distance_m": float(focus_distance),
                "rival_distance_m": float(rival_distance),
                "target_horizontal_distance": float(max(focus_distance, rival_distance)),
                "snap_distance": snap_distance,
                "navmesh_snapped": snap_distance is not None,
                "navmesh_navigable": bool(navigable),
                "direction_source": source,
                "standoff_distance_requested": float(distance),
                "viewpoint_source": "common_pair_navmesh" if snap_distance is not None else "common_pair_geometry",
                "projection_sane": True,
                "score": float(score),
            }
            if best is None or score < best[0]:
                best = (score, viewpoint)
    return None if best is None else best[1]


def make_request_row(
    *,
    source: Dict[str, Any],
    focus_id: str,
    rival_ids: Sequence[str],
    request_index: int,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_goal_region_request",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "scene_key": source.get("scene_key"),
        "query": source.get("query"),
        "expanded_retrieval_request_id": request_id(source),
        "rival_identity_request_id": source.get("rival_identity_request_id"),
        "preferred_request_branch": source.get("preferred_request_branch"),
        "preferred_request_action": source.get("preferred_request_action"),
        "focus_candidate_id": focus_id,
        "contrastive_rival_candidate_ids": list(rival_ids),
        "contrastive_rival_count": len(rival_ids),
        "candidate_target_count": 1 + len(rival_ids),
        "pair_count": len(rival_ids),
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_candidate_target_row(
    *,
    source: Dict[str, Any],
    candidate: Dict[str, Any],
    role: str,
    request_index: int,
    candidate_target_index: int,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_goal_region_candidate_target",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "candidate_target_index": candidate_target_index,
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "scene_key": source.get("scene_key"),
        "query": source.get("query"),
        "expanded_retrieval_request_id": request_id(source),
        "rival_identity_request_id": source.get("rival_identity_request_id"),
        "candidate_id": candidate.get("candidate_id"),
        "target_candidate_id": candidate.get("candidate_id"),
        "goal_region_candidate_role": role,
        "semantic_rank": candidate.get("semantic_rank"),
        "generated_rank": candidate.get("generated_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "score": candidate.get("score"),
        "positive_support": candidate.get("positive_support"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "detector_visible_rows": candidate.get("detector_visible_rows"),
        "detector_inside_mask_rows": candidate.get("detector_inside_mask_rows"),
        "detector_depth_mismatch_rows": candidate.get("detector_depth_mismatch_rows"),
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_pair_row(
    *,
    source: Dict[str, Any],
    focus: Dict[str, Any],
    rival: Dict[str, Any],
    pair_index: int,
    request_index: int,
) -> Dict[str, Any]:
    focus_pos = candidate_position(focus)
    rival_pos = candidate_position(rival)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_goal_region_pair",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "pair_index": pair_index,
        "pair_id": f"unique_support_goal_region:{request_id(source)}:p{pair_index:02d}",
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "scene_key": source.get("scene_key"),
        "query": source.get("query"),
        "expanded_retrieval_request_id": request_id(source),
        "rival_identity_request_id": source.get("rival_identity_request_id"),
        "focus_candidate_id": focus.get("candidate_id"),
        "rival_candidate_id": rival.get("candidate_id"),
        "candidate_ids": [str(focus.get("candidate_id")), str(rival.get("candidate_id"))],
        "focus_position": focus.get("position"),
        "rival_position": rival.get("position"),
        "focus_generated_rank": focus.get("generated_rank"),
        "rival_generated_rank": rival.get("generated_rank"),
        "focus_semantic_rank": focus.get("semantic_rank"),
        "rival_semantic_rank": rival.get("semantic_rank"),
        "focus_rival_distance_m": None if focus_pos is None or rival_pos is None else horizontal_distance(focus_pos, rival_pos),
        "goal_region_pair_action": TARGET_ACTION,
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_observation_target(
    *,
    args: argparse.Namespace,
    source: Dict[str, Any],
    focus: Dict[str, Any],
    rival: Dict[str, Any],
    pair: Dict[str, Any],
    role: str,
    target: Dict[str, Any],
    viewpoint: Dict[str, Any],
    request_index: int,
    observation_index: int,
) -> Dict[str, Any]:
    target_pos = candidate_position(target)
    focus_pos = candidate_position(focus)
    rival_pos = candidate_position(rival)
    position = [float(value) for value in viewpoint["position"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "validation_stage": "action_unique_support_goal_region_observation_target",
        "contract_name": "expanded_retrieval_goal_validity_unique_support_goal_region_v1",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "request_index": request_index,
        "observation_index": observation_index,
        "pair_index": pair.get("pair_index"),
        "pair_id": pair.get("pair_id"),
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "scene_key": source.get("scene_key"),
        "query": source.get("query"),
        "expanded_retrieval_request_id": request_id(source),
        "rival_identity_request_id": source.get("rival_identity_request_id"),
        "focus_candidate_id": focus.get("candidate_id"),
        "rival_candidate_id": rival.get("candidate_id"),
        "candidate_id": target.get("candidate_id"),
        "target_candidate_id": target.get("candidate_id"),
        "candidate_ids": [str(focus.get("candidate_id")), str(rival.get("candidate_id"))],
        "view_role": role,
        "viewpoint_id": f"unique_support_goal_region:{request_id(source)}:{pair.get('pair_index'):02d}:{role}",
        "viewpoint_position": position,
        "viewpoint_rotation": [float(value) for value in viewpoint["rotation"]],
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "target_position": target.get("position"),
        "target_visit_position": target.get("visit_position"),
        "focus_position": focus.get("position"),
        "rival_position": rival.get("position"),
        "pair_midpoint": viewpoint.get("pair_midpoint"),
        "focus_rival_span_m": None if focus_pos is None or rival_pos is None else horizontal_distance(focus_pos, rival_pos),
        "target_distance_from_viewpoint_m": None if target_pos is None else horizontal_distance(position, target_pos),
        "focus_distance_from_viewpoint_m": viewpoint.get("focus_distance_m"),
        "rival_distance_from_viewpoint_m": viewpoint.get("rival_distance_m"),
        "standoff_target_position": viewpoint.get("target_position"),
        "standoff_desired_position": viewpoint.get("desired_position"),
        "standoff_target_horizontal_distance": viewpoint.get("target_horizontal_distance"),
        "standoff_snap_distance": viewpoint.get("snap_distance"),
        "standoff_navmesh_snapped": viewpoint.get("navmesh_snapped"),
        "standoff_navmesh_navigable": viewpoint.get("navmesh_navigable"),
        "standoff_direction_source": viewpoint.get("direction_source"),
        "standoff_distance_requested": viewpoint.get("standoff_distance_requested"),
        "standoff_projection_sane": viewpoint.get("projection_sane"),
        "standoff_viewpoint_yaw_rad": viewpoint.get("yaw"),
        "standoff_score": viewpoint.get("score"),
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_label_free": True,
        "goal_region_observation_action": "collect_contrastive_goal_region_evidence",
        "goal_region_observation_reason": "unique_support_candidate_requires_contrastive_goal_region_evidence",
        "terminal_commit_allowed": False,
        "commit_after_goal_region_observation": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_skip_row(
    *,
    source: Dict[str, Any],
    request_index: int,
    reason: str,
    focus_id: Optional[str] = None,
    rival_id: Optional[str] = None,
    view_role: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_goal_region_skipped",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "scene_key": source.get("scene_key"),
        "query": source.get("query"),
        "expanded_retrieval_request_id": request_id(source),
        "rival_identity_request_id": source.get("rival_identity_request_id"),
        "focus_candidate_id": focus_id,
        "rival_candidate_id": rival_id,
        "view_role": view_role,
        "skip_reason": reason,
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def target_requests_from_contract(contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    scope = contract.get("target_scope") or {}
    return sorted(scope.get("target_requests") or [], key=lambda row: request_sort_key(str(row.get("expanded_retrieval_request_id"))))


def materialize_request(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    contract_request: Dict[str, Any],
    branch_request: Dict[str, Any],
    branch_candidates: Dict[Tuple[str, str], Dict[str, Any]],
    geometries: Dict[Tuple[str, str], Dict[str, Any]],
    snapper: NavmeshSnapper,
    request_index: int,
    observation_start: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    rid = str(contract_request.get("expanded_retrieval_request_id"))
    focus_ids = branch_candidate_ids(branch_request, TARGET_BRANCH)
    focus_id = str(contract_request.get("focus_candidate_id") or (focus_ids[0] if focus_ids else ""))
    rival_ids = unique_preserve_order(contract_request.get("contrastive_rival_candidate_ids") or [])
    if not rival_ids:
        for item in branch_request.get("branch_candidate_items") or []:
            if str(item.get("branch_name")) == TARGET_BRANCH:
                continue
            rival_ids.extend(str(value) for value in item.get("candidate_ids") or [] if value is not None)
        rival_ids = unique_preserve_order(candidate_id for candidate_id in rival_ids if candidate_id != focus_id)

    source = dict(branch_request)
    request_rows: List[Dict[str, Any]] = []
    candidate_rows: List[Dict[str, Any]] = []
    pair_rows: List[Dict[str, Any]] = []
    observation_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []

    focus = geometries.get((rid, focus_id))
    if focus is None:
        skipped_rows.append(make_skip_row(source=source, request_index=request_index, reason="missing_focus_geometry", focus_id=focus_id))
        return request_rows, candidate_rows, pair_rows, observation_rows, skipped_rows

    valid_rivals: List[Dict[str, Any]] = []
    for rival_id in rival_ids:
        rival = geometries.get((rid, rival_id))
        if rival is None:
            skipped_rows.append(
                make_skip_row(
                    source=source,
                    request_index=request_index,
                    reason="missing_rival_geometry",
                    focus_id=focus_id,
                    rival_id=rival_id,
                )
            )
            continue
        valid_rivals.append(rival)
    if len(valid_rivals) < int((contract.get("evaluation_gates") or {}).get("minimum_contrastive_rivals_per_request", 2)):
        skipped_rows.append(
            make_skip_row(
                source=source,
                request_index=request_index,
                reason="insufficient_contrastive_rivals",
                focus_id=focus_id,
            )
        )
        return request_rows, candidate_rows, pair_rows, observation_rows, skipped_rows

    request_rows.append(make_request_row(source=source, focus_id=focus_id, rival_ids=[str(row["candidate_id"]) for row in valid_rivals], request_index=request_index))
    all_candidates = [focus, *valid_rivals]
    for candidate_index, candidate in enumerate(all_candidates):
        role = "focus_unique_support" if str(candidate.get("candidate_id")) == focus_id else "contrastive_rival"
        candidate_row = make_candidate_target_row(
            source=source,
            candidate=candidate,
            role=role,
            request_index=request_index,
            candidate_target_index=candidate_index,
        )
        branch_row = branch_candidates.get((rid, str(candidate.get("candidate_id"))))
        if branch_row:
            candidate_row["branch_candidate_names"] = branch_row.get("candidate_branch_names")
            candidate_row["branch_candidate_actions"] = branch_row.get("candidate_branch_actions")
            candidate_row["routing_inputs"] = branch_row.get("routing_inputs")
        candidate_rows.append(candidate_row)

    observation_index = observation_start
    for pair_index, rival in enumerate(valid_rivals):
        pair = make_pair_row(source=source, focus=focus, rival=rival, pair_index=pair_index, request_index=request_index)
        pair_rows.append(pair)
        plans = [
            ("focus_own_view", focus, standoff_viewpoint(target=focus, alt=rival, snapper=snapper, args=args)),
            ("rival_own_view", rival, standoff_viewpoint(target=rival, alt=focus, snapper=snapper, args=args)),
            ("common_pair_view", focus, common_pair_viewpoint(focus=focus, rival=rival, snapper=snapper, args=args)),
        ]
        for role, target, viewpoint in plans:
            if viewpoint is None:
                skipped_rows.append(
                    make_skip_row(
                        source=source,
                        request_index=request_index,
                        reason=f"{role}_unavailable",
                        focus_id=focus_id,
                        rival_id=str(rival.get("candidate_id")),
                        view_role=role,
                    )
                )
                continue
            observation_rows.append(
                make_observation_target(
                    args=args,
                    source=source,
                    focus=focus,
                    rival=rival,
                    pair=pair,
                    role=role,
                    target=target,
                    viewpoint=viewpoint,
                    request_index=request_index,
                    observation_index=observation_index,
                )
            )
            observation_index += 1
    return request_rows, candidate_rows, pair_rows, observation_rows, skipped_rows


def count_forbidden(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        for finding in scan_forbidden_keys(row):
            findings.append(f"row[{index}].{finding}")
    return findings


def summarize(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    branch_summary: Dict[str, Any],
    request_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    observation_rows: Sequence[Dict[str, Any]],
    skipped_rows: Sequence[Dict[str, Any]],
    artifact_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    gates = contract.get("evaluation_gates") or {}
    router_gate = (branch_summary.get("gate") or {}).get("branch_evidence_router_gate_passed")
    if router_gate is None:
        router_gate = branch_summary.get("branch_evidence_router_gate_passed")
    terminal_rows = [
        row
        for row in [*request_rows, *candidate_rows, *pair_rows, *observation_rows, *skipped_rows]
        if row.get("terminal_commit_allowed") is True or row.get("commit_after_reobserve") is True
    ]
    forbidden = count_forbidden([*request_rows, *candidate_rows, *pair_rows, *observation_rows, *skipped_rows])
    request_ids = sorted({request_id(row) for row in request_rows}, key=request_sort_key)
    pair_rows_by_request = Counter(request_id(row) for row in pair_rows)
    candidate_rows_by_request = Counter(request_id(row) for row in candidate_rows)
    observation_rows_by_request = Counter(request_id(row) for row in observation_rows)
    view_roles_by_request: Dict[str, set[str]] = defaultdict(set)
    for row in observation_rows:
        view_roles_by_request[request_id(row)].add(str(row.get("view_role")))
    target_distances = [
        float(value)
        for value in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in observation_rows)
        if value is not None
    ]
    gate = {
        "input_branch_router_gate_passed": bool(router_gate) == bool(gates.get("input_branch_router_gate_passed", True)),
        "expected_target_request_rows_passed": len(request_rows) == int(gates.get("expected_target_request_rows", 0)),
        "expected_focus_candidate_rows_passed": sum(1 for row in candidate_rows if row.get("goal_region_candidate_role") == "focus_unique_support")
        == int(gates.get("expected_focus_candidate_rows", 0)),
        "minimum_pair_rows_passed": len(pair_rows) >= int(gates.get("minimum_pair_rows", 0)),
        "minimum_candidate_target_rows_passed": len(candidate_rows) >= int(gates.get("minimum_candidate_target_rows", 0)),
        "minimum_contrastive_rivals_per_request_passed": bool(pair_rows_by_request)
        and min(pair_rows_by_request.values()) >= int(gates.get("minimum_contrastive_rivals_per_request", 0)),
        "minimum_view_roles_per_request_passed": bool(view_roles_by_request)
        and min(len(values) for values in view_roles_by_request.values()) >= int(gates.get("minimum_view_roles_per_request", 0)),
        "skipped_request_rows_maximum_passed": len({request_id(row) for row in skipped_rows}) <= int(gates.get("skipped_request_rows_maximum", 0)),
        "action_evidence_forbidden_key_count_passed": len(forbidden) == int(gates.get("action_evidence_forbidden_key_count_maximum", 0)),
        "terminal_commit_rows_passed": len(terminal_rows) == int(gates.get("terminal_commit_rows_maximum", 0)),
        "uses_gt_for_action_passed": not any(row.get("uses_gt_for_action") is True for row in [*request_rows, *candidate_rows, *pair_rows, *observation_rows, *skipped_rows]),
        "paper_claim_allowed": False,
    }
    gate["unique_support_goal_region_plan_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "branch_summary": str(args.branch_summary),
        "branch_request_rows": str(args.branch_request_rows),
        "branch_candidate_rows": str(args.branch_candidate_rows),
        "geometry_plan_rows": str(args.geometry_plan_rows),
        "out_root": str(args.out_root),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "branch_evidence_router_gate_passed": bool(router_gate),
        "request_rows": len(request_rows),
        "candidate_target_rows": len(candidate_rows),
        "focus_candidate_rows": sum(1 for row in candidate_rows if row.get("goal_region_candidate_role") == "focus_unique_support"),
        "pair_rows": len(pair_rows),
        "observation_target_rows": len(observation_rows),
        "skipped_rows": len(skipped_rows),
        "skipped_request_rows": len({request_id(row) for row in skipped_rows}),
        "request_ids": request_ids,
        "pair_rows_by_request": dict(sorted(pair_rows_by_request.items(), key=lambda item: request_sort_key(item[0]))),
        "candidate_target_rows_by_request": dict(sorted(candidate_rows_by_request.items(), key=lambda item: request_sort_key(item[0]))),
        "observation_rows_by_request": dict(sorted(observation_rows_by_request.items(), key=lambda item: request_sort_key(item[0]))),
        "view_role_counts": dict(sorted(Counter(str(row.get("view_role")) for row in observation_rows).items())),
        "viewpoint_source_counts": dict(sorted(Counter(str(row.get("viewpoint_source")) for row in observation_rows).items())),
        "direction_source_counts": dict(sorted(Counter(str(row.get("standoff_direction_source")) for row in observation_rows).items())),
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "candidate_artifact_rows": len(artifact_rows),
        "candidate_artifact_candidate_count": sum(int(row.get("candidate_count") or 0) for row in artifact_rows),
        "terminal_commit_rows": len(terminal_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "request_rows": "unique_support_goal_region_request_rows.jsonl",
            "candidate_targets": "unique_support_goal_region_candidate_targets.jsonl",
            "pair_rows": "unique_support_goal_region_pair_rows.jsonl",
            "observation_targets": "unique_support_goal_region_observation_targets.jsonl",
            "skipped_rows": "unique_support_goal_region_skipped.jsonl",
            "candidate_artifact": "unique_support_goal_region_candidate_artifact.jsonl",
            "summary": "unique_support_goal_region_summary.json",
        },
        "interpretation": {
            "fact": "The planner writes nonterminal contrastive goal-region observation rows from branch-router outputs before label joins.",
            "agent_inference": "If this planner passes a Docker smoke, the next evidence step can test whether unique visible-object support should trigger active goal-region observation instead of terminal commitment.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    branch_summary = load_json(Path(args.branch_summary))
    branch_requests = load_jsonl(Path(args.branch_request_rows))
    branch_candidates_rows = load_jsonl(Path(args.branch_candidate_rows))
    geometry_rows = load_jsonl(Path(args.geometry_plan_rows))
    requests_by_id = index_by_request(branch_requests)
    branch_candidates = {
        (request_id(row), str(row.get("candidate_id"))): dict(row)
        for row in branch_candidates_rows
        if request_id(row) and row.get("candidate_id") is not None
    }
    geometries = geometry_index(geometry_rows)

    snapper = NavmeshSnapper(args.data_root)
    request_rows: List[Dict[str, Any]] = []
    candidate_rows: List[Dict[str, Any]] = []
    pair_rows: List[Dict[str, Any]] = []
    observation_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    try:
        for request_index, contract_request in enumerate(target_requests_from_contract(contract)):
            if int(args.max_requests) > 0 and request_index >= int(args.max_requests):
                break
            rid = str(contract_request.get("expanded_retrieval_request_id"))
            branch_request = requests_by_id.get(rid)
            if branch_request is None:
                skipped_rows.append(
                    make_skip_row(
                        source={
                            "expanded_retrieval_request_id": rid,
                            "rival_identity_request_id": rid,
                            "scene_key": contract_request.get("scene_key"),
                            "query": contract_request.get("query"),
                            "episode_key": contract_request.get("episode_key"),
                        },
                        request_index=request_index,
                        reason="missing_branch_request_row",
                    )
                )
                continue
            rows = materialize_request(
                args=args,
                contract=contract,
                contract_request=contract_request,
                branch_request=branch_request,
                branch_candidates=branch_candidates,
                geometries=geometries,
                snapper=snapper,
                request_index=request_index,
                observation_start=len(observation_rows),
            )
            new_requests, new_candidates, new_pairs, new_observations, new_skipped = rows
            request_rows.extend(new_requests)
            candidate_rows.extend(new_candidates)
            pair_rows.extend(new_pairs)
            observation_rows.extend(new_observations)
            skipped_rows.extend(new_skipped)
    finally:
        snapper.close()

    out_root = Path(args.out_root)
    artifact_rows = candidate_artifact_rows(candidate_rows)
    write_jsonl(out_root / "unique_support_goal_region_request_rows.jsonl", request_rows)
    write_jsonl(out_root / "unique_support_goal_region_candidate_targets.jsonl", candidate_rows)
    write_jsonl(out_root / "unique_support_goal_region_pair_rows.jsonl", pair_rows)
    write_jsonl(out_root / "unique_support_goal_region_observation_targets.jsonl", observation_rows)
    write_jsonl(out_root / "unique_support_goal_region_skipped.jsonl", skipped_rows)
    write_jsonl(out_root / "unique_support_goal_region_candidate_artifact.jsonl", artifact_rows)
    summary = summarize(
        args=args,
        contract=contract,
        branch_summary=branch_summary,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        observation_rows=observation_rows,
        skipped_rows=skipped_rows,
        artifact_rows=artifact_rows,
    )
    write_json(out_root / "unique_support_goal_region_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default="hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
        "h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1.json",
    )
    parser.add_argument(
        "--branch-summary",
        default="local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1/"
        "goal_validity_object_relation_branch_evidence_summary.json",
    )
    parser.add_argument(
        "--branch-request-rows",
        default="local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1/"
        "goal_validity_object_relation_branch_request_rows.jsonl",
    )
    parser.add_argument(
        "--branch-candidate-rows",
        default="local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1/"
        "goal_validity_object_relation_branch_candidate_rows.jsonl",
    )
    parser.add_argument("--geometry-plan-rows", default=DEFAULT_GEOMETRY_PLAN)
    parser.add_argument(
        "--out-root",
        default="local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1",
    )
    parser.add_argument("--data-root", default="local_dataset/data")
    parser.add_argument("--run-id", default="unique_support_goal_region_v1")
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument("--standoff-distances", type=parse_float_list, default=parse_float_list("1.25,1.75,2.25"))
    parser.add_argument("--common-pair-distances", type=parse_float_list, default=parse_float_list("1.75,2.25,2.75,3.25"))
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--max-pair-view-distance-m", type=float, default=4.5)
    parser.add_argument("--projection-anchor-height-offsets-m", type=parse_float_list, default=parse_float_list("0.0,0.4,0.8,1.2,1.6,2.0,2.4"))
    parser.add_argument("--require-navmesh-standoff", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
