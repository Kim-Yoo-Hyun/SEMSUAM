import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    artifact_index,
    candidate_floor_y,
    candidate_target_position,
    candidate_viewpoint,
    horizontal_distance,
    plan_standoff_viewpoint,
    quaternion_xyzw_from_yaw,
    standoff_directions,
    vector,
    yaw_to_point,
)


SCHEMA_VERSION = "h001.external_candidate_second_stage_identity_plan.v1"
POLICY_NAME = "ExternalCandidateSecondStageIdentityConfirmation"
REQUEST_ACTION = "followup_evidence_v1_request_identity_confirmation"
DEFAULT_GROUNDED_POINT_HEIGHT_M = 0.8
DEFAULT_GROUNDED_POINT_MAX_VERTICAL_GAP_M = 2.0


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def candidate_rank(candidate_id: str) -> Optional[int]:
    try:
        return int(candidate_id.rsplit(":", 1)[-1]) + 1
    except (TypeError, ValueError):
        return None


def evidence_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    values = row.get("followup_candidate_evidence") or []
    return [value for value in values if isinstance(value, dict) and value.get("candidate_id") is not None]


def evidence_by_id(row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(candidate.get("candidate_id")): candidate for candidate in evidence_candidates(row)}


def strongest_positive_rivals(row: Dict[str, Any], selected_id: str, max_rivals: int) -> List[str]:
    rivals = [
        candidate
        for candidate in evidence_candidates(row)
        if str(candidate.get("candidate_id")) != selected_id and candidate.get("positive_support") is True
    ]
    rivals.sort(
        key=lambda candidate: (
            safe_float(candidate.get("S_ext")) or 0.0,
            safe_float(candidate.get("strict_association_count")) or 0.0,
            safe_float(candidate.get("mask_hit_count")) or 0.0,
        ),
        reverse=True,
    )
    return [str(candidate.get("candidate_id")) for candidate in rivals[:max_rivals]]


def strongest_rivals(row: Dict[str, Any], selected_id: str, max_rivals: int) -> List[str]:
    positive = strongest_positive_rivals(row, selected_id, max_rivals)
    strong = [
        candidate
        for candidate in evidence_candidates(row)
        if str(candidate.get("candidate_id")) != selected_id
        and candidate.get("followup_strong_depth_evidence") is True
    ]
    strong.sort(
        key=lambda candidate: (
            safe_float(candidate.get("S_ext")) or 0.0,
            safe_float(candidate.get("strict_association_count")) or 0.0,
        ),
        reverse=True,
    )
    return ordered_unique([*positive, *(candidate.get("candidate_id") for candidate in strong)])[:max_rivals]


def semantic_neighbor_ids(
    row: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    selected_id: str,
    max_neighbors: int,
) -> List[str]:
    if max_neighbors <= 0:
        return []
    allowed_ids = ordered_unique(
        row.get("followup_candidate_ids")
        or [candidate.get("candidate_id") for candidate in evidence_candidates(row)]
        or candidates.keys()
    )
    allowed = set(allowed_ids)
    ranked = sorted(
        candidates.values(),
        key=lambda candidate: (
            safe_float(candidate.get("score")) or -math.inf,
            -(candidate_rank(str(candidate.get("candidate_id"))) or 9999),
        ),
        reverse=True,
    )
    return ordered_unique(
        candidate.get("candidate_id")
        for candidate in ranked
        if candidate.get("candidate_id") is not None
        and str(candidate.get("candidate_id")) != selected_id
        and str(candidate.get("candidate_id")) in allowed
    )[:max_neighbors]


def grounded_target_position(candidate: Dict[str, Any], source_row: Dict[str, Any], args: argparse.Namespace) -> Optional[List[float]]:
    position = vector(candidate.get("position"))
    visit_position = vector(candidate.get("visit_position"))
    if position is None and visit_position is None:
        return None
    if position is None:
        return [
            float(visit_position[0]),
            float(visit_position[1]) + float(args.grounded_point_height_m),
            float(visit_position[2]),
        ]
    if visit_position is None:
        source = vector(source_row.get("viewpoint_position"))
        if source is not None and abs(float(position[1]) - float(source[1])) > float(args.grounded_point_max_vertical_gap_m):
            return [
                float(position[0]),
                float(source[1]) + float(args.grounded_point_height_m),
                float(position[2]),
            ]
        return position
    if abs(float(position[1]) - float(visit_position[1])) > float(args.grounded_point_max_vertical_gap_m):
        return [
            float(position[0]),
            float(visit_position[1]) + float(args.grounded_point_height_m),
            float(position[2]),
        ]
    return position


def target_position_for_mode(
    candidate: Dict[str, Any],
    source_row: Dict[str, Any],
    args: argparse.Namespace,
) -> Optional[List[float]]:
    mode = str(args.target_point_mode)
    if mode == "visit_position":
        return vector(candidate.get("visit_position")) or candidate_target_position(candidate)
    if mode == "grounded_position":
        return grounded_target_position(candidate, source_row, args)
    return candidate_target_position(candidate)


def min_horizontal_distance_to_anchors(
    candidate: Dict[str, Any],
    anchors: List[Dict[str, Any]],
) -> Optional[float]:
    point = candidate_target_position(candidate)
    if point is None:
        return None
    distances = [
        horizontal_distance(point, anchor_point)
        for anchor in anchors
        for anchor_point in [candidate_target_position(anchor)]
        if anchor_point is not None
    ]
    return min(distances) if distances else None


def local_context_ids(
    row: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    selected_id: str,
    semantic_neighbors: List[str],
    rivals: List[str],
    args: argparse.Namespace,
) -> List[str]:
    max_contexts = int(args.max_local_contexts)
    if max_contexts <= 0:
        return []
    allowed_ids = ordered_unique(
        row.get("followup_candidate_ids")
        or [candidate.get("candidate_id") for candidate in evidence_candidates(row)]
        or candidates.keys()
    )
    allowed = set(allowed_ids)
    excluded = {selected_id, *semantic_neighbors, *rivals}
    anchors = [candidates[candidate_id] for candidate_id in [selected_id, *rivals] if candidate_id in candidates]
    ranked: List[Tuple[float, float, float, str]] = []
    for candidate in candidates.values():
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id in excluded or candidate_id not in allowed:
            continue
        distance = min_horizontal_distance_to_anchors(candidate, anchors)
        if distance is None or distance > float(args.max_local_context_distance_m):
            continue
        ranked.append(
            (
                float(distance),
                -(safe_float(candidate.get("score")) or 0.0),
                float(candidate_rank(candidate_id) or 9999),
                candidate_id,
            )
        )
    ranked.sort()
    return [candidate_id for _distance, _score, _rank, candidate_id in ranked[:max_contexts]]


def identity_targets_for_request(
    row: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    selected_id: str,
    args: argparse.Namespace,
) -> Tuple[List[Tuple[str, str]], List[str], List[str], List[str]]:
    rivals = strongest_rivals(row, selected_id, int(args.max_rivals))
    semantic_neighbors = semantic_neighbor_ids(row, candidates, selected_id, int(args.max_semantic_neighbors))
    local_contexts = local_context_ids(row, candidates, selected_id, semantic_neighbors, rivals, args)
    mode = str(args.target_selection_mode)
    if mode == "strongest_rival":
        target_ids = [selected_id, *rivals]
    elif mode == "semantic_neighbor":
        target_ids = [selected_id, *semantic_neighbors, *rivals]
    elif mode == "strongest_plus_semantic_neighbor":
        target_ids = [selected_id, *semantic_neighbors, *rivals]
    elif mode == "local_rival_expanded":
        target_ids = [selected_id, *semantic_neighbors, *rivals, *local_contexts]
    else:
        raise ValueError(f"unsupported target selection mode: {mode}")

    target_ids = ordered_unique(target_ids)
    contrast_ids = ordered_unique([*semantic_neighbors, *rivals, *local_contexts])
    role_pairs: List[Tuple[str, str]] = []
    for candidate_id in target_ids:
        if candidate_id == selected_id:
            role = "selected_standoff"
        elif candidate_id in semantic_neighbors:
            role = f"semantic_neighbor_{semantic_neighbors.index(candidate_id) + 1}_standoff"
        elif candidate_id in rivals:
            role = f"rival_{rivals.index(candidate_id) + 1}_standoff"
        elif candidate_id in local_contexts:
            role = f"local_context_{local_contexts.index(candidate_id) + 1}_standoff"
        else:
            role = "context_standoff"
        role_pairs.append((role, candidate_id))
    return role_pairs, contrast_ids, semantic_neighbors, rivals


def candidate_ids_for_request(
    row: Dict[str, Any],
    selected_id: str,
    semantic_neighbors: List[str],
    rivals: List[str],
    max_ids: int,
) -> List[str]:
    return ordered_unique([selected_id, *semantic_neighbors, *rivals, *(row.get("followup_candidate_ids") or [])])[:max_ids]


def angular_distance(a: float, b: float) -> float:
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


def is_viewpoint_diverse(
    selected: List[Dict[str, Any]],
    item: Dict[str, Any],
    args: argparse.Namespace,
) -> bool:
    item_position = item.get("position")
    item_yaw = safe_float(item.get("yaw"))
    if not isinstance(item_position, list) or item_yaw is None:
        return True
    min_position_sep = float(args.min_viewpoint_position_separation_m)
    min_yaw_sep = math.radians(float(args.min_viewpoint_yaw_separation_deg))
    for old in selected:
        old_position = old.get("position")
        old_yaw = safe_float(old.get("yaw"))
        if not isinstance(old_position, list) or old_yaw is None:
            continue
        if horizontal_distance(old_position, item_position) < min_position_sep and angular_distance(old_yaw, item_yaw) < min_yaw_sep:
            return False
    return True


def ranked_standoff_viewpoints(
    source: Dict[str, Any],
    candidate: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    alt_id: Optional[str],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    target_position = target_position_for_mode(candidate, source, args)
    floor_y = candidate_floor_y(candidate, source)
    if target_position is None or floor_y is None:
        return []

    source_position = vector(source.get("viewpoint_position"))
    scene_id = str(source.get("scene_id"))
    options: List[Dict[str, Any]] = []
    for distance in args.standoff_distances:
        for dx, dz, direction_source in standoff_directions(source, target_position, candidates, alt_id):
            desired = [
                float(target_position[0]) + dx * float(distance),
                float(floor_y),
                float(target_position[2]) + dz * float(distance),
            ]
            snapped, navigable, snap_distance = snapper.snap(scene_id, desired)
            target_horizontal_distance = horizontal_distance(snapped, target_position)
            if target_horizontal_distance < float(args.min_standoff_distance_m):
                continue
            if target_horizontal_distance > float(args.max_standoff_distance_m):
                continue
            yaw = yaw_to_point(snapped, target_position)
            if yaw is None:
                continue
            travel_proxy = horizontal_distance(source_position, snapped) if source_position is not None else 0.0
            snap_penalty = snap_distance if snap_distance is not None else 0.0
            navigable_bonus = -0.25 if navigable else 0.0
            score = (
                abs(target_horizontal_distance - float(args.preferred_standoff_distance_m))
                + 0.20 * snap_penalty
                + 0.03 * travel_proxy
                + navigable_bonus
            )
            options.append(
                {
                    "position": snapped,
                    "rotation": quaternion_xyzw_from_yaw(yaw),
                    "yaw": float(yaw),
                    "target_position": target_position,
                    "target_horizontal_distance": float(target_horizontal_distance),
                    "desired_position": desired,
                    "snap_distance": snap_distance,
                    "navmesh_snapped": snap_distance is not None,
                    "navmesh_navigable": navigable,
                    "direction_source": direction_source,
                    "standoff_distance_requested": float(distance),
                    "viewpoint_source": "standoff_navmesh" if snap_distance is not None else "standoff_geometry",
                    "projection_sane": True,
                    "target_point_mode": str(args.target_point_mode),
                    "grounded_point_height_m": float(args.grounded_point_height_m),
                    "grounded_point_max_vertical_gap_m": float(args.grounded_point_max_vertical_gap_m),
                    "score": float(score),
                }
            )
    options.sort(
        key=lambda item: (
            safe_float(item.get("score")) or math.inf,
            str(item.get("direction_source")),
            safe_float(item.get("standoff_distance_requested")) or math.inf,
        )
    )
    return options


def viewpoints_for_candidate(
    source: Dict[str, Any],
    candidate: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    alt_id: Optional[str],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
    max_viewpoints: int,
) -> List[Tuple[List[float], List[float], str, Dict[str, Any]]]:
    if max_viewpoints <= 1:
        if str(args.target_point_mode) == "position":
            standoff = plan_standoff_viewpoint(
                {"scene_id": source.get("scene_id"), "viewpoint_position": source.get("viewpoint_position")},
                candidate,
                candidates,
                alt_id,
                snapper,
                args,
            )
            if standoff is not None:
                standoff["target_point_mode"] = str(args.target_point_mode)
                return [(standoff["position"], standoff["rotation"], str(standoff.get("viewpoint_source")), standoff)]
        else:
            ranked = ranked_standoff_viewpoints(source, candidate, candidates, alt_id, snapper, args)
            if ranked:
                item = ranked[0]
                return [(item["position"], item["rotation"], str(item.get("viewpoint_source")), item)]

    selected: List[Dict[str, Any]] = []
    for option in ranked_standoff_viewpoints(source, candidate, candidates, alt_id, snapper, args):
        if not is_viewpoint_diverse(selected, option, args):
            continue
        selected.append(option)
        if len(selected) >= max_viewpoints:
            break
    if selected:
        return [(item["position"], item["rotation"], str(item.get("viewpoint_source")), item) for item in selected]

    fallback = candidate_viewpoint(candidate)
    if fallback is None:
        return []
    position, rotation = fallback
    return [(position, rotation, "candidate_visit_position_fallback", {})]


def max_viewpoints_for_role(role: str, args: argparse.Namespace) -> int:
    if role.startswith("semantic_neighbor_") or role.startswith("local_context_"):
        return max(1, int(args.semantic_neighbor_viewpoints_per_target))
    return max(1, int(args.max_viewpoints_per_target))


def make_plan_row(
    source: Dict[str, Any],
    args: argparse.Namespace,
    source_index: int,
    role: str,
    candidate_id: str,
    candidate_ids: List[str],
    position: List[float],
    rotation: List[float],
    viewpoint_source: str,
    extra: Dict[str, Any],
    selected_id: str,
    rival_ids: List[str],
    viewpoint_index: int,
) -> Dict[str, Any]:
    suffix = candidate_id.rsplit(":", 1)[-1]
    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "source_index": source_index,
        "source_schema_version": source.get("schema_version"),
        "policy": POLICY_NAME,
        "viewpoint_policy": POLICY_NAME,
        "viewpoint_id": f"{source.get('external_branch_id')}:stage2_identity:{role}:{suffix}:v{viewpoint_index}",
        "candidate_id": candidate_id,
        "candidate_ids": candidate_ids,
        "viewpoint_position": position,
        "viewpoint_rotation": rotation,
        "commit_after_reobserve": False,
        "observation_success": True,
        "uses_gt_for_action": False,
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "query": source.get("query"),
        "property_group": source.get("property_group"),
        "label_case": source.get("label_case"),
        "external_branch_id": source.get("external_branch_id"),
        "source_external_branch_id": source.get("external_branch_id"),
        "source_followup_action": source.get("followup_evidence_v1_action"),
        "source_followup_reason": source.get("followup_evidence_v1_reason"),
        "source_external_evidence_v4_action": source.get("source_external_evidence_v4_action"),
        "source_external_evidence_v4_reason": source.get("source_external_evidence_v4_reason"),
        "followup_evidence_v1_action": source.get("followup_evidence_v1_action"),
        "followup_evidence_v1_reason": source.get("followup_evidence_v1_reason"),
        "followup_set_contains_correct": source.get("followup_set_contains_correct"),
        "selected_candidate_id": selected_id,
        "selected_score": source.get("selected_score"),
        "score_margin": source.get("score_margin"),
        "second_stage_policy": POLICY_NAME,
        "second_stage_action": "identity_confirmation",
        "second_stage_reason": "confirm_v2_request_identity_candidate_against_rival",
        "second_stage_role": role,
        "second_stage_candidate_id": candidate_id,
        "second_stage_viewpoint_index": int(viewpoint_index),
        "second_stage_selected_candidate_id": selected_id,
        "second_stage_rival_candidate_ids": rival_ids,
        "second_stage_viewpoint_source": viewpoint_source,
        "second_stage_direct_commit_allowed": False,
        "second_stage_visit_position_only_commit_allowed": False,
    }
    for key, value in extra.items():
        row[f"second_stage_{key}"] = value
    return row


def plan_rows_for_source(
    source: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    snapper: NavmeshSnapper,
    source_index: int,
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    selected_id = str(source.get("selected_candidate_id") or "")
    if selected_id not in candidates:
        return [], [{"source_index": source_index, "skip_reason": "missing_selected_candidate", **source}]
    targets, contrast_ids, semantic_neighbors, rivals = identity_targets_for_request(source, candidates, selected_id, args)
    if not contrast_ids:
        return [], [{"source_index": source_index, "skip_reason": "missing_contrast_candidate", **source}]

    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    candidate_ids = candidate_ids_for_request(source, selected_id, semantic_neighbors, rivals, int(args.max_candidate_ids))
    for role, candidate_id in targets[: int(args.max_targets_per_request)]:
        candidate = candidates.get(candidate_id)
        if candidate is None:
            skipped.append({"source_index": source_index, "candidate_id": candidate_id, "skip_reason": "missing_candidate"})
            continue
        alt_ids = [value for value in candidate_ids if value != candidate_id]
        viewpoints = viewpoints_for_candidate(
            source,
            candidate,
            candidates,
            alt_ids[0] if alt_ids else None,
            snapper,
            args,
            max_viewpoints_for_role(role, args),
        )
        if not viewpoints:
            skipped.append({"source_index": source_index, "candidate_id": candidate_id, "skip_reason": "no_viewpoint"})
            continue
        for viewpoint_index, viewpoint in enumerate(viewpoints):
            position, rotation, viewpoint_source, extra = viewpoint
            rows.append(
                make_plan_row(
                    source,
                    args,
                    source_index,
                    role,
                    candidate_id,
                    candidate_ids,
                    position,
                    rotation,
                    viewpoint_source,
                    extra,
                    selected_id,
                    contrast_ids,
                    viewpoint_index,
                )
            )
    return rows, skipped


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    rows = load_jsonl(Path(args.followup_evidence_rows))
    candidates_by_key = artifact_index(Path(args.candidate_artifact))
    request_rows = [row for row in rows if row.get("followup_evidence_v1_action") == REQUEST_ACTION]
    external_branch_ids = set(ordered_unique(str(args.external_branch_ids).split(",")))
    if external_branch_ids:
        request_rows = [row for row in request_rows if str(row.get("external_branch_id")) in external_branch_ids]
    if int(args.max_requests) > 0:
        request_rows = request_rows[: int(args.max_requests)]

    snapper = NavmeshSnapper(args.data_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    role_counts: Counter[str] = Counter()
    viewpoint_source_counts: Counter[str] = Counter()
    rows_by_branch: Dict[str, int] = defaultdict(int)
    request_query_counts: Counter[str] = Counter()

    try:
        for source_index, source in enumerate(request_rows):
            key = (str(source.get("scene_id")), str(source.get("query")))
            candidates = candidates_by_key.get(key, {})
            request_query_counts[str(source.get("query"))] += 1
            if not candidates:
                skipped_rows.append({"source_index": source_index, "skip_reason": "missing_scene_query_candidates", **source})
                continue
            rows_for_source, skipped = plan_rows_for_source(source, candidates, snapper, source_index, args)
            plan_rows.extend(rows_for_source)
            skipped_rows.extend(skipped)
            for row in rows_for_source:
                role_counts[str(row.get("second_stage_role"))] += 1
                viewpoint_source_counts[str(row.get("second_stage_viewpoint_source"))] += 1
                rows_by_branch[str(row.get("external_branch_id"))] += 1
    finally:
        snapper.close()

    write_jsonl(out_root / "external_candidate_second_stage_identity_plan.jsonl", plan_rows)
    write_jsonl(out_root / "external_candidate_second_stage_identity_skipped.jsonl", skipped_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "followup_evidence_rows": str(args.followup_evidence_rows),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "policy": POLICY_NAME,
        "source_rows": len(rows),
        "request_rows": len(request_rows),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "request_query_counts": dict(sorted(request_query_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "viewpoint_source_counts": dict(sorted(viewpoint_source_counts.items())),
        "rows_by_external_branch_id": dict(sorted(rows_by_branch.items())),
        "target_selection_mode": str(args.target_selection_mode),
        "target_point_mode": str(args.target_point_mode),
        "max_rivals": int(args.max_rivals),
        "max_semantic_neighbors": int(args.max_semantic_neighbors),
        "max_local_contexts": int(args.max_local_contexts),
        "max_local_context_distance_m": float(args.max_local_context_distance_m),
        "max_candidate_ids": int(args.max_candidate_ids),
        "max_targets_per_request": int(args.max_targets_per_request),
        "max_viewpoints_per_target": int(args.max_viewpoints_per_target),
        "semantic_neighbor_viewpoints_per_target": int(args.semantic_neighbor_viewpoints_per_target),
        "grounded_point_height_m": float(args.grounded_point_height_m),
        "grounded_point_max_vertical_gap_m": float(args.grounded_point_max_vertical_gap_m),
        "external_branch_ids_filter": sorted(external_branch_ids),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "output_files": {
            "plan_rows": "external_candidate_second_stage_identity_plan.jsonl",
            "skipped_rows": "external_candidate_second_stage_identity_skipped.jsonl",
            "summary": "external_candidate_second_stage_identity_summary.json",
        },
    }
    write_json(out_root / "external_candidate_second_stage_identity_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan H001 second-stage identity confirmation for V2 follow-up requests.")
    parser.add_argument("--followup-evidence-rows", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--run-id", default="h001_external_candidate_second_stage_identity_v1")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument(
        "--target-selection-mode",
        choices=["strongest_rival", "semantic_neighbor", "strongest_plus_semantic_neighbor", "local_rival_expanded"],
        default="strongest_rival",
    )
    parser.add_argument(
        "--target-point-mode",
        choices=["position", "visit_position", "grounded_position"],
        default="position",
    )
    parser.add_argument("--max-rivals", type=int, default=1)
    parser.add_argument("--max-semantic-neighbors", type=int, default=1)
    parser.add_argument("--max-local-contexts", type=int, default=0)
    parser.add_argument("--max-local-context-distance-m", type=float, default=2.5)
    parser.add_argument("--max-candidate-ids", type=int, default=6)
    parser.add_argument("--max-targets-per-request", type=int, default=2)
    parser.add_argument("--max-viewpoints-per-target", type=int, default=1)
    parser.add_argument("--semantic-neighbor-viewpoints-per-target", type=int, default=1)
    parser.add_argument("--grounded-point-height-m", type=float, default=DEFAULT_GROUNDED_POINT_HEIGHT_M)
    parser.add_argument(
        "--grounded-point-max-vertical-gap-m",
        type=float,
        default=DEFAULT_GROUNDED_POINT_MAX_VERTICAL_GAP_M,
    )
    parser.add_argument("--external-branch-ids", default="")
    parser.add_argument("--standoff-distances", type=lambda text: [float(x) for x in text.split(",") if x], default=[1.25, 1.75, 2.25])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--min-viewpoint-position-separation-m", type=float, default=0.35)
    parser.add_argument("--min-viewpoint-yaw-separation-deg", type=float, default=15.0)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
