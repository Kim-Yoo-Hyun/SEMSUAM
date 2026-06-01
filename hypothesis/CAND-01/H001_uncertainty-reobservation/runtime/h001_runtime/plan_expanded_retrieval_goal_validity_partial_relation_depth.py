import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
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


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_partial_relation_depth_plan.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1.json"
)
INPUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1"
)
OUT_ROOT_DEFAULT = INPUT_ROOT_DEFAULT
POLICY_NAME = "ExpandedRetrievalGoalValidityPartialRelationDepthObservation"
PLANNER_NAME = "partial_relation_depth_completion_v1"
VIEWPOINT_POLICY = "failed_relation_direction_completion_standoff_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
        item = str(value)
        if not item or item in seen:
            continue
        output.append(item)
        seen.add(item)
    return output


def number_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def rows_by_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = row_key(row)
        if all(key):
            grouped[key].append(dict(row))
    return grouped


def candidate_position(row: Dict[str, Any]) -> Optional[List[float]]:
    return vector(row.get("target_position")) or vector(row.get("position")) or vector(row.get("target_visit_position"))


def candidate_visit_position(row: Dict[str, Any]) -> Optional[List[float]]:
    return vector(row.get("target_visit_position")) or vector(row.get("visit_position")) or candidate_position(row)


def candidate_floor_y(row: Dict[str, Any]) -> Optional[float]:
    visit = candidate_visit_position(row)
    if visit is not None:
        return float(visit[1])
    pos = candidate_position(row)
    return None if pos is None else float(pos[1])


def context_position(row: Dict[str, Any]) -> Optional[List[float]]:
    return vector(row.get("context_position")) or vector(row.get("context_visit_position"))


def direction_vectors(target_pos: List[float], anchor_pos: Optional[List[float]], source: str) -> List[Tuple[float, float, str]]:
    directions: List[Tuple[float, float, str]] = []

    def add(dx: float, dz: float, label: str) -> None:
        unit = normalize_xz(dx, dz)
        if unit is None:
            return
        ux, uz = unit
        if any(abs(ux - old_x) < 1e-3 and abs(uz - old_z) < 1e-3 for old_x, old_z, _ in directions):
            return
        directions.append((ux, uz, label))

    if anchor_pos is not None:
        anchor_to_target_x = float(target_pos[0]) - float(anchor_pos[0])
        anchor_to_target_z = float(target_pos[2]) - float(anchor_pos[2])
        if source == "relation_anchor_to_target":
            add(anchor_to_target_x, anchor_to_target_z, source)
            add(-anchor_to_target_x, -anchor_to_target_z, "target_to_relation_anchor_secondary")
        elif source == "target_to_relation_anchor":
            add(-anchor_to_target_x, -anchor_to_target_z, source)
            add(anchor_to_target_x, anchor_to_target_z, "relation_anchor_to_target_secondary")
        elif source == "orthogonal_relation_axis":
            add(-anchor_to_target_z, anchor_to_target_x, source)
            add(anchor_to_target_z, -anchor_to_target_x, source)
            add(anchor_to_target_x, anchor_to_target_z, "relation_anchor_to_target_secondary")
        else:
            add(anchor_to_target_x, anchor_to_target_z, "relation_anchor_to_target")
            add(-anchor_to_target_x, -anchor_to_target_z, "target_to_relation_anchor")

    for degrees in (0, 45, 90, 135, 180, 225, 270, 315):
        radians = math.radians(float(degrees))
        add(math.sin(radians), math.cos(radians), f"compass_{degrees}")
    return directions


def completion_viewpoint(
    *,
    target: Dict[str, Any],
    anchor: Optional[Dict[str, Any]],
    requested_direction_source: str,
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    target_pos = candidate_position(target)
    floor_y = candidate_floor_y(target)
    if target_pos is None or floor_y is None:
        return None
    anchor_pos = context_position(anchor or {})
    scene_id = str(target.get("scene_id"))
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    requested_distances = unique_preserve_order(
        [args.preferred_standoff_distance_m, *(args.standoff_distances or [])]
    )
    for distance in requested_distances:
        distance_float = float(distance)
        for dx, dz, direction_source in direction_vectors(target_pos, anchor_pos, requested_direction_source):
            desired = [
                float(target_pos[0]) + float(dx) * distance_float,
                float(floor_y),
                float(target_pos[2]) + float(dz) * distance_float,
            ]
            snapped, navigable, snap_distance = snapper.snap(scene_id, desired)
            if bool(args.require_navmesh_standoff) and not navigable:
                continue
            target_distance = horizontal_distance(snapped, target_pos)
            if target_distance is None:
                continue
            if target_distance < float(args.min_standoff_distance_m):
                continue
            if target_distance > float(args.max_standoff_distance_m):
                continue
            yaw = yaw_to_point(snapped, target_pos)
            if yaw is None:
                continue
            snap_penalty = snap_distance if snap_distance is not None else 0.0
            source_penalty = 0.0 if direction_source == requested_direction_source else 0.35
            score = abs(target_distance - float(args.preferred_standoff_distance_m)) + 0.20 * snap_penalty + source_penalty
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
                "requested_direction_source": requested_direction_source,
                "direction_source": direction_source,
                "standoff_distance_requested": distance_float,
                "viewpoint_source": "partial_relation_depth_navmesh_standoff",
                "projection_sane": True,
                "score": float(score),
            }
            if best is None or score < best[0]:
                best = (score, viewpoint)
    return None if best is None else best[1]


def make_skip_row(
    *,
    target: Dict[str, Any],
    request_index: int,
    reason: str,
    failed_evidence: Optional[Dict[str, Any]] = None,
    context_anchor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_partial_relation_depth_observation_skipped",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "episode_key": target.get("episode_key"),
        "scene_id": target.get("scene_id"),
        "scene_key": target.get("scene_key"),
        "query": target.get("query"),
        "expanded_retrieval_request_id": request_id(target),
        "rival_identity_request_id": target.get("rival_identity_request_id"),
        "candidate_id": candidate_id(target),
        "target_candidate_id": candidate_id(target),
        "failed_evidence_index": None if failed_evidence is None else failed_evidence.get("failed_evidence_index"),
        "relation_depth_evidence_status": None if failed_evidence is None else failed_evidence.get("relation_depth_evidence_status"),
        "standoff_direction_source": None if failed_evidence is None else failed_evidence.get("standoff_direction_source"),
        "standoff_relation_anchor_candidate_id": None
        if failed_evidence is None
        else failed_evidence.get("standoff_relation_anchor_candidate_id"),
        "context_candidate_id": None if context_anchor is None else context_anchor.get("context_candidate_id"),
        "skip_reason": reason,
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_plan_row(
    *,
    args: argparse.Namespace,
    target: Dict[str, Any],
    failed_evidence: Optional[Dict[str, Any]],
    context_anchor: Optional[Dict[str, Any]],
    viewpoint: Dict[str, Any],
    request_index: int,
    observation_index: int,
    completion_index: int,
) -> Dict[str, Any]:
    target_pos = candidate_position(target)
    anchor_pos = context_position(context_anchor or {})
    context_id = None if context_anchor is None else context_anchor.get("context_candidate_id")
    failed_index = None if failed_evidence is None else failed_evidence.get("failed_evidence_index")
    anchor_ids = unique_preserve_order(
        [
            context_id,
            *list((failed_evidence or {}).get("relation_anchor_candidate_ids") or []),
        ]
    )
    position = [float(value) for value in viewpoint["position"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "validation_stage": "action_partial_relation_depth_observation_target",
        "contract_name": "expanded_retrieval_goal_validity_partial_relation_depth_observation_v1",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "request_index": request_index,
        "observation_index": observation_index,
        "completion_index": completion_index,
        "episode_key": target.get("episode_key"),
        "scene_id": target.get("scene_id"),
        "scene_key": target.get("scene_key"),
        "query": target.get("query"),
        "expanded_retrieval_request_id": request_id(target),
        "rival_identity_request_id": target.get("rival_identity_request_id"),
        "candidate_id": candidate_id(target),
        "target_candidate_id": candidate_id(target),
        "candidate_ids": unique_preserve_order([candidate_id(target), *anchor_ids]),
        "target_candidate_role": target.get("target_candidate_role") or "partial_relation_depth_target_candidate",
        "target_generated_rank": target.get("target_generated_rank"),
        "target_semantic_rank": target.get("target_semantic_rank"),
        "target_semantic_score": target.get("target_semantic_score"),
        "target_support_score": target.get("target_support_score"),
        "target_score": target.get("target_score"),
        "target_positive_support": target.get("target_positive_support"),
        "target_position": target.get("target_position"),
        "target_visit_position": target.get("target_visit_position"),
        "target_distance_from_viewpoint_m": None if target_pos is None else horizontal_distance(position, target_pos),
        "viewpoint_id": f"partial_relation_depth:{request_id(target)}:{safe_int(target.get('target_index')):02d}:{completion_index:02d}",
        "viewpoint_position": position,
        "viewpoint_rotation": [float(value) for value in viewpoint["rotation"]],
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "failed_evidence_index": failed_index,
        "relation_depth_evidence_status": None if failed_evidence is None else failed_evidence.get("relation_depth_evidence_status"),
        "failed_standoff_direction_source": None if failed_evidence is None else failed_evidence.get("standoff_direction_source"),
        "standoff_direction_source": viewpoint.get("direction_source"),
        "requested_direction_source": viewpoint.get("requested_direction_source"),
        "standoff_relation_anchor_candidate_id": None
        if failed_evidence is None
        else failed_evidence.get("standoff_relation_anchor_candidate_id"),
        "relation_anchor_candidate_ids": anchor_ids,
        "context_candidate_id": context_id,
        "context_position": None if context_anchor is None else context_anchor.get("context_position"),
        "context_visit_position": None if context_anchor is None else context_anchor.get("context_visit_position"),
        "context_target_distance_m": None if target_pos is None or anchor_pos is None else horizontal_distance(anchor_pos, target_pos),
        "standoff_target_position": viewpoint.get("target_position"),
        "standoff_desired_position": viewpoint.get("desired_position"),
        "standoff_target_horizontal_distance": viewpoint.get("target_horizontal_distance"),
        "standoff_snap_distance": viewpoint.get("snap_distance"),
        "standoff_navmesh_snapped": viewpoint.get("navmesh_snapped"),
        "standoff_navmesh_navigable": viewpoint.get("navmesh_navigable"),
        "standoff_distance_requested": viewpoint.get("standoff_distance_requested"),
        "standoff_projection_sane": viewpoint.get("projection_sane"),
        "standoff_viewpoint_yaw_rad": viewpoint.get("yaw"),
        "standoff_score": viewpoint.get("score"),
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_label_free": True,
        "partial_relation_depth_observation_action": "collect_relation_depth_completion_evidence",
        "partial_relation_depth_observation_reason": "partial_or_unresolved_relation_depth_blocks_goal_validity",
        "terminal_commit_allowed": False,
        "commit_after_relation_depth_observation": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def context_by_id(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        cid = str(row.get("context_candidate_id") or "")
        if cid and cid not in indexed:
            indexed[cid] = dict(row)
    return indexed


def target_fill_specs(
    *,
    target: Dict[str, Any],
    failed_rows: Sequence[Dict[str, Any]],
    context_rows: Sequence[Dict[str, Any]],
    minimum_rows: int,
) -> List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]]:
    contexts_by_id = context_by_id(context_rows)
    specs: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]] = []
    for failed in failed_rows:
        anchor_id = str(failed.get("standoff_relation_anchor_candidate_id") or "")
        anchor = contexts_by_id.get(anchor_id)
        if anchor is None and context_rows:
            anchor = context_rows[0]
        specs.append((failed, anchor, str(failed.get("standoff_direction_source") or "relation_anchor_to_target")))

    fill_directions = [
        "relation_anchor_to_target",
        "target_to_relation_anchor",
        "orthogonal_relation_axis",
        "orthogonal_relation_axis",
    ]
    cursor = 0
    while len(specs) < minimum_rows and context_rows:
        anchor = context_rows[cursor % len(context_rows)]
        direction = fill_directions[cursor % len(fill_directions)]
        specs.append((None, anchor, direction))
        cursor += 1
    if len(specs) < minimum_rows:
        while len(specs) < minimum_rows:
            specs.append((None, None, "relation_anchor_to_target"))
    return specs


def candidate_artifact_payload(candidate: Dict[str, Any], role: str) -> Dict[str, Any]:
    is_context = role == "relation_depth_context_anchor"
    position = candidate.get("context_position") if is_context else candidate.get("target_position")
    visit_position = candidate.get("context_visit_position") if is_context else candidate.get("target_visit_position")
    cid = candidate.get("context_candidate_id") if is_context else (candidate.get("candidate_id") or candidate.get("target_candidate_id"))
    return {
        "candidate_id": str(cid),
        "category": candidate.get("query"),
        "score": candidate.get("target_score") if role == "partial_relation_depth_target" else 0.0,
        "semantic_rank": candidate.get("target_semantic_rank") or candidate.get("context_generated_rank"),
        "semantic_score": candidate.get("target_semantic_score"),
        "support_score": candidate.get("target_support_score"),
        "positive_support": candidate.get("target_positive_support"),
        "candidate_backend": "partial_relation_depth_observation",
        "candidate_role": role,
        "generated_rank": candidate.get("target_generated_rank") or candidate.get("context_generated_rank"),
        "position": position,
        "visit_position": visit_position,
        "source": "expanded_retrieval_goal_validity_partial_relation_depth_plan",
        "uses_gt_for_action": False,
    }


def candidate_artifact_rows(
    target_rows: Sequence[Dict[str, Any]],
    context_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    scene_keys: Dict[Tuple[str, str], str] = {}
    request_ids: Dict[Tuple[str, str], set[str]] = defaultdict(set)
    for row in target_rows:
        key = (str(row.get("scene_id")), str(row.get("query")))
        scene_keys[key] = str(row.get("scene_key") or "")
        request_ids[key].add(request_id(row))
        grouped[key][candidate_id(row)] = candidate_artifact_payload(row, "partial_relation_depth_target")
    for row in context_rows:
        key = (str(row.get("scene_id")), str(row.get("query")))
        scene_keys[key] = str(row.get("scene_key") or "")
        request_ids[key].add(request_id(row))
        payload = candidate_artifact_payload(row, "relation_depth_context_anchor")
        cid = str(payload.get("candidate_id"))
        if cid and cid not in grouped[key]:
            grouped[key][cid] = payload

    output: List[Dict[str, Any]] = []
    for (scene_id, query), candidates_by_id in sorted(grouped.items()):
        candidates = list(candidates_by_id.values())
        candidates.sort(
            key=lambda candidate: (
                -(safe_float(candidate.get("score")) or 0.0),
                safe_int(candidate.get("semantic_rank")),
                str(candidate.get("candidate_id")),
            )
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "partial_relation_depth_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": scene_keys.get((scene_id, query)),
                "query": query,
                "expanded_retrieval_request_ids": sorted(request_ids[(scene_id, query)], key=request_sort_key),
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return output


def materialize_plan(
    *,
    args: argparse.Namespace,
    target_rows: Sequence[Dict[str, Any]],
    failed_by_target: Dict[Tuple[str, str], List[Dict[str, Any]]],
    context_by_target: Dict[Tuple[str, str], List[Dict[str, Any]]],
    snapper: NavmeshSnapper,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    minimum_per_target = int(args.minimum_plan_rows_per_target_candidate)
    request_index_by_id: Dict[str, int] = {}
    for target in sorted(
        target_rows,
        key=lambda row: (
            request_sort_key(request_id(row)),
            safe_int(row.get("target_generated_rank")),
            candidate_id(row),
        ),
    ):
        rid = request_id(target)
        if rid not in request_index_by_id:
            request_index_by_id[rid] = len(request_index_by_id)
        request_index = request_index_by_id[rid]
        key = row_key(target)
        failed_rows = sorted(
            failed_by_target.get(key, []),
            key=lambda row: (
                safe_int(row.get("failed_evidence_index")),
                str(row.get("standoff_direction_source") or ""),
            ),
        )
        context_rows = sorted(
            context_by_target.get(key, []),
            key=lambda row: (
                safe_int(row.get("context_generated_rank")),
                str(row.get("context_candidate_id") or ""),
            ),
        )
        specs = target_fill_specs(
            target=target,
            failed_rows=failed_rows,
            context_rows=context_rows,
            minimum_rows=minimum_per_target,
        )
        for completion_index, (failed, context_anchor, direction_source) in enumerate(specs):
            viewpoint = completion_viewpoint(
                target=target,
                anchor=context_anchor,
                requested_direction_source=direction_source,
                snapper=snapper,
                args=args,
            )
            if viewpoint is None:
                skipped_rows.append(
                    make_skip_row(
                        target=target,
                        request_index=request_index,
                        reason="navmesh_relation_depth_completion_view_unavailable",
                        failed_evidence=failed,
                        context_anchor=context_anchor,
                    )
                )
                continue
            plan_rows.append(
                make_plan_row(
                    args=args,
                    target=target,
                    failed_evidence=failed,
                    context_anchor=context_anchor,
                    viewpoint=viewpoint,
                    request_index=request_index,
                    observation_index=len(plan_rows),
                    completion_index=completion_index,
                )
            )
    return plan_rows, skipped_rows


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
    input_summary: Dict[str, Any],
    request_rows: Sequence[Dict[str, Any]],
    target_rows: Sequence[Dict[str, Any]],
    failed_rows: Sequence[Dict[str, Any]],
    context_rows: Sequence[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
    skipped_rows: Sequence[Dict[str, Any]],
    artifact_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    gates = contract.get("evaluation_gates") or {}
    all_action_rows = [*plan_rows, *skipped_rows, *artifact_rows]
    forbidden = count_forbidden(all_action_rows)
    terminal_rows = [
        row
        for row in all_action_rows
        if row.get("terminal_commit") is True
        or row.get("terminal_commit_allowed") is True
        or row.get("commit_after_reobserve") is True
        or row.get("commit_after_relation_depth_observation") is True
    ]
    plan_by_target = Counter(row_key(row) for row in plan_rows)
    failed_ids = {safe_int(row.get("failed_evidence_index")) for row in failed_rows}
    mapped_failed_ids = {
        safe_int(row.get("failed_evidence_index"))
        for row in plan_rows
        if row.get("failed_evidence_index") is not None
    }
    skipped_failed_ids = {
        safe_int(row.get("failed_evidence_index"))
        for row in skipped_rows
        if row.get("failed_evidence_index") is not None
    }
    request_ids = sorted({request_id(row) for row in request_rows}, key=request_sort_key)
    target_distances = [
        float(value)
        for value in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if value is not None
    ]
    skipped_request_rows = len({request_id(row) for row in skipped_rows})
    gate = {
        "input_materializer_gate_passed": bool(
            ((input_summary.get("gate") or {}).get("partial_relation_depth_input_gate_passed"))
        ),
        "expected_request_rows_passed": len(request_rows) == safe_int(gates.get("expected_request_rows"), 0),
        "expected_target_candidate_rows_passed": len(target_rows) == safe_int(gates.get("expected_target_candidate_rows"), 0),
        "expected_failed_relation_depth_evidence_rows_passed": len(failed_rows)
        == safe_int(gates.get("expected_failed_relation_depth_evidence_rows"), 0),
        "expected_context_anchor_rows_passed": len(context_rows) == safe_int(gates.get("expected_context_anchor_rows"), 0),
        "minimum_plan_rows_passed": len(plan_rows) >= safe_int(gates.get("minimum_plan_rows"), 0),
        "minimum_plan_rows_per_target_candidate_passed": bool(plan_by_target)
        and min(plan_by_target.values()) >= safe_int(gates.get("minimum_plan_rows_per_target_candidate"), 0),
        "skipped_request_rows_maximum_passed": skipped_request_rows <= safe_int(gates.get("skipped_request_rows_maximum"), 0),
        "failed_direction_rows_mapped_or_skipped_passed": failed_ids <= (mapped_failed_ids | skipped_failed_ids),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(gates.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in all_action_rows),
        "paper_claim_allowed": False,
    }
    gate["partial_relation_depth_observation_plan_gate_passed"] = all(
        value is True for key, value in gate.items() if key not in {"uses_gt_for_action", "paper_claim_allowed"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "input_root": str(args.input_root),
        "out_root": str(args.out_root),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "request_rows": len(request_rows),
        "target_candidate_rows": len(target_rows),
        "failed_relation_depth_evidence_rows": len(failed_rows),
        "context_anchor_rows": len(context_rows),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "skipped_request_rows": skipped_request_rows,
        "request_ids": request_ids,
        "plan_rows_by_request": dict(sorted(Counter(request_id(row) for row in plan_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "plan_rows_by_target": {
            f"{key[0]}::{key[1]}": value
            for key, value in sorted(plan_by_target.items(), key=lambda item: (request_sort_key(item[0][0]), item[0][1]))
        },
        "failed_evidence_rows_mapped": len(mapped_failed_ids),
        "failed_evidence_rows_skipped": len(skipped_failed_ids),
        "failed_evidence_rows_unmapped": len(failed_ids - (mapped_failed_ids | skipped_failed_ids)),
        "failed_direction_counts": compact_counter(row.get("failed_standoff_direction_source") for row in plan_rows if row.get("failed_evidence_index") is not None),
        "completion_direction_counts": compact_counter(row.get("standoff_direction_source") for row in plan_rows),
        "viewpoint_source_counts": compact_counter(row.get("viewpoint_source") for row in plan_rows),
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "candidate_artifact_rows": len(artifact_rows),
        "candidate_artifact_candidate_count": sum(safe_int(row.get("candidate_count"), 0) for row in artifact_rows),
        "terminal_commit_rows": len(terminal_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "plan": "partial_relation_depth_observation_plan.jsonl",
            "skipped": "partial_relation_depth_observation_skipped.jsonl",
            "candidate_artifact": "partial_relation_depth_candidate_artifact.jsonl",
            "summary": "partial_relation_depth_observation_plan_summary.json",
        },
        "interpretation": {
            "fact": "The planner writes nonterminal relation-depth completion views from partial/unresolved evidence rows.",
            "agent_inference": "Passing this smoke means the branch can proceed to frame/projection and detector evidence, not terminal ObjectNav utility.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    input_root = Path(args.input_root)
    request_rows = load_jsonl(input_root / "partial_relation_depth_request_rows.jsonl")
    target_rows = load_jsonl(input_root / "partial_relation_depth_target_candidate_rows.jsonl")
    failed_rows = load_jsonl(input_root / "partial_relation_depth_failed_evidence_rows.jsonl")
    context_rows = load_jsonl(input_root / "partial_relation_depth_context_anchor_rows.jsonl")
    input_summary = load_json(input_root / "partial_relation_depth_input_summary.json")
    failed_by_target = rows_by_key(failed_rows)
    context_by_target = rows_by_key(context_rows)
    snapper = NavmeshSnapper(args.data_root)
    try:
        plan_rows, skipped_rows = materialize_plan(
            args=args,
            target_rows=target_rows,
            failed_by_target=failed_by_target,
            context_by_target=context_by_target,
            snapper=snapper,
        )
    finally:
        snapper.close()

    artifact_rows = candidate_artifact_rows(target_rows, context_rows)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "partial_relation_depth_observation_plan.jsonl", plan_rows)
    write_jsonl(out_root / "partial_relation_depth_observation_skipped.jsonl", skipped_rows)
    write_jsonl(out_root / "partial_relation_depth_candidate_artifact.jsonl", artifact_rows)
    summary = summarize(
        args=args,
        contract=contract,
        input_summary=input_summary,
        request_rows=request_rows,
        target_rows=target_rows,
        failed_rows=failed_rows,
        context_rows=context_rows,
        plan_rows=plan_rows,
        skipped_rows=skipped_rows,
        artifact_rows=artifact_rows,
    )
    write_json(out_root / "partial_relation_depth_observation_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--data-root", default="local_dataset/data")
    parser.add_argument("--run-id", default="partial_relation_depth_observation_v1")
    parser.add_argument("--standoff-distances", type=parse_float_list, default=parse_float_list("1.25,1.75,2.25"))
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--minimum-plan-rows-per-target-candidate", type=int, default=4)
    parser.add_argument("--projection-anchor-height-offsets-m", type=parse_float_list, default=parse_float_list("0.0,0.4,0.8,1.2,1.6,2.0,2.4"))
    parser.add_argument("--require-navmesh-standoff", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["partial_relation_depth_observation_plan_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
