import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    candidate_target_position,
    horizontal_distance,
    parse_float_list,
    plan_standoff_viewpoint,
    safe_float,
)


SCHEMA_VERSION = "h001.expanded_retrieval_local_context_plan.v1"
POLICY_NAME = "ExpandedRetrievalLocalContextDisambiguation"
PLANNER_NAME = "expanded_retrieval_local_context_disambiguation_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"
FORBIDDEN_ACTION_KEYS = {
    "candidate_correct",
    "selected_for_goal",
    "wrong_goal_visit",
    "success",
    "evaluation_only_candidate_correct",
    "evaluation_only_goal_visit",
    "evaluation_only_wrong_goal_visit",
    "evaluation_only_wasted_path_from_candidate",
    "analysis_only_target_route",
    "analysis_only_target_taxonomy",
    "analysis_only_proxy_matches_target_route",
    "oracle_shortest_path",
    "gt_object_id",
    "gt_goal_id",
}


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


def row_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (str(row.get("episode_key")), str(row.get("query")))


def candidate_set_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {row_key(row): row for row in rows}


def detector_candidate_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        candidate_id = row.get("candidate_id")
        if candidate_id is not None:
            grouped[row_key(row)][str(candidate_id)] = row
    return grouped


def rank_candidate(candidate: Dict[str, Any]) -> Tuple[int, int, float, str]:
    return (
        safe_int(candidate.get("selection_rank")),
        safe_int(candidate.get("semantic_rank")),
        -(safe_float(candidate.get("support_score")) or safe_float(candidate.get("semantic_score")) or -math.inf),
        str(candidate.get("candidate_id")),
    )


def detector_rank(row: Dict[str, Any]) -> Tuple[int, float, int, int, int, str]:
    return (
        0 if str(row.get("detector_support_class")) == "strong_detector_support" else 1,
        -(safe_float(row.get("evidence_score")) or -math.inf),
        -safe_int(row.get("strict_association_heading_rows"), default=0),
        -safe_int(row.get("mask_hit_heading_rows"), default=0),
        safe_int(row.get("expanded_candidate_rank")),
        str(row.get("candidate_id")),
    )


def finite_candidate(candidate: Dict[str, Any]) -> bool:
    return candidate_target_position(candidate) is not None


def nearest_distance(candidate: Dict[str, Any], references: Sequence[Dict[str, Any]]) -> Optional[float]:
    position = candidate_target_position(candidate)
    if position is None:
        return None
    distances = [
        horizontal_distance(position, other_position)
        for other_position in (candidate_target_position(reference) for reference in references)
        if other_position is not None
    ]
    if not distances:
        return None
    return min(distances)


def source_top_candidate(candidates: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ranked = sorted((dict(candidate) for candidate in candidates if finite_candidate(candidate)), key=rank_candidate)
    return ranked[0] if ranked else None


def candidate_snapshot(
    candidate: Dict[str, Any],
    *,
    role: str,
    detector_row: Optional[Dict[str, Any]],
    local_context_distance_m: Optional[float],
) -> Dict[str, Any]:
    score = safe_float(candidate.get("score"))
    if score is None:
        score = safe_float(candidate.get("support_score")) or safe_float(candidate.get("semantic_score"))
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "candidate_backend": candidate.get("candidate_backend"),
        "candidate_role": role,
        "category": candidate.get("category"),
        "score": score,
        "selection_rank": candidate.get("selection_rank"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "path_to_candidate": candidate.get("path_to_candidate"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "local_context_distance_m": local_context_distance_m,
        "detector_support_class": None if detector_row is None else detector_row.get("detector_support_class"),
        "detector_evidence_score": None if detector_row is None else detector_row.get("evidence_score"),
        "detector_strict_association_heading_rows": None
        if detector_row is None
        else detector_row.get("strict_association_heading_rows"),
        "detector_mask_hit_heading_rows": None if detector_row is None else detector_row.get("mask_hit_heading_rows"),
        "detector_visible_heading_rows": None if detector_row is None else detector_row.get("visible_heading_rows"),
        "uses_gt_for_action": False,
    }


def select_local_context_candidates(
    candidate_set_row: Dict[str, Any],
    detector_rows_by_id: Dict[str, Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, Optional[float]]]:
    candidates = [dict(candidate) for candidate in candidate_set_row.get("expanded_candidates") or [] if finite_candidate(candidate)]
    by_id = {str(candidate.get("candidate_id")): candidate for candidate in candidates if candidate.get("candidate_id") is not None}

    roles: Dict[str, str] = {}
    local_distances: Dict[str, Optional[float]] = {}
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def add(candidate: Optional[Dict[str, Any]], role: str, distance: Optional[float] = None) -> None:
        if candidate is None or candidate.get("candidate_id") is None or not finite_candidate(candidate):
            return
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id not in seen:
            selected.append(candidate)
            seen.add(candidate_id)
            roles[candidate_id] = role
            local_distances[candidate_id] = distance
            return
        old = roles.get(candidate_id, "")
        if role not in old.split("+"):
            roles[candidate_id] = f"{old}+{role}" if old else role
        if distance is not None:
            previous = local_distances.get(candidate_id)
            local_distances[candidate_id] = distance if previous is None else min(previous, distance)

    source_top = source_top_candidate(candidates)
    add(source_top, "source_top", 0.0)

    strong_detector_rows = [
        row
        for row in detector_rows_by_id.values()
        if str(row.get("detector_support_class")) == "strong_detector_support"
        and str(row.get("candidate_id")) in by_id
    ]
    strong_detector_rows.sort(key=detector_rank)
    for index, detector_row in enumerate(strong_detector_rows[: int(args.max_detector_strong_candidates_per_request)]):
        role = "detector_strong_candidate" if index == 0 else "detector_strong_rival"
        add(by_id.get(str(detector_row.get("candidate_id"))), role, None)

    cluster_refs = list(selected)
    local_candidates: List[Tuple[float, Tuple[int, int, float, str], Dict[str, Any]]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id in seen:
            continue
        distance = nearest_distance(candidate, cluster_refs)
        if distance is None or distance > float(args.max_local_context_distance_m):
            continue
        local_candidates.append((distance, rank_candidate(candidate), candidate))

    local_candidates.sort(key=lambda item: (item[0], item[1]))
    for distance, _rank, candidate in local_candidates[: int(args.max_local_context_candidates_per_request)]:
        add(candidate, "local_context_candidate", float(distance))

    if len(selected) > int(args.max_total_candidates_per_request):
        selected = selected[: int(args.max_total_candidates_per_request)]
        kept = {str(candidate.get("candidate_id")) for candidate in selected}
        roles = {candidate_id: role for candidate_id, role in roles.items() if candidate_id in kept}
        local_distances = {
            candidate_id: distance for candidate_id, distance in local_distances.items() if candidate_id in kept
        }

    return selected, roles, local_distances


def artifact_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "category": candidate.get("category"),
        "score": candidate.get("score"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_backend": candidate.get("candidate_backend"),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "path_to_candidate": candidate.get("path_to_candidate"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "source": "expanded_retrieval_local_context_disambiguation_plan",
        "candidate_role": candidate.get("candidate_role"),
        "local_context_distance_m": candidate.get("local_context_distance_m"),
        "detector_support_class": candidate.get("detector_support_class"),
        "detector_evidence_score": candidate.get("detector_evidence_score"),
        "uses_gt_for_action": False,
    }


def candidate_artifact_rows(plan_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    scene_keys: Dict[Tuple[str, str], str] = {}
    for row in plan_rows:
        key = (str(row.get("scene_id")), str(row.get("query")))
        scene_keys[key] = str(row.get("scene_key") or "")
        for candidate in row.get("local_context_candidate_snapshots") or []:
            grouped[key][str(candidate.get("candidate_id"))] = artifact_candidate(candidate)

    output: List[Dict[str, Any]] = []
    for (scene_id, query), candidates_by_id in sorted(grouped.items()):
        candidates = list(candidates_by_id.values())
        candidates.sort(
            key=lambda candidate: (
                safe_int(candidate.get("semantic_rank")),
                -(safe_float(candidate.get("score")) or -math.inf),
                str(candidate.get("candidate_id")),
            )
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "expanded_retrieval_local_context_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": scene_keys.get((scene_id, query)),
                "query": query,
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return output


def nearest_alternative_id(candidate_id: str, candidates_by_id: Dict[str, Dict[str, Any]]) -> Optional[str]:
    candidate = candidates_by_id.get(candidate_id)
    if candidate is None:
        return None
    position = candidate_target_position(candidate)
    if position is None:
        return None
    best: Optional[Tuple[float, str]] = None
    for other_id, other in candidates_by_id.items():
        if other_id == candidate_id:
            continue
        other_position = candidate_target_position(other)
        if other_position is None:
            continue
        distance = horizontal_distance(position, other_position)
        if best is None or distance < best[0]:
            best = (distance, other_id)
    return None if best is None else best[1]


def count_consumed_forbidden_fields() -> int:
    consumed = {
        "episode_key",
        "scene_key",
        "scene_id",
        "query",
        "rival_identity_request_id",
        "objective_action",
        "evidence_topology",
        "terminal_objective_risk",
        "expanded_candidates.candidate_id",
        "expanded_candidates.selection_rank",
        "expanded_candidates.semantic_rank",
        "expanded_candidates.semantic_score",
        "expanded_candidates.support_score",
        "expanded_candidates.positive_support",
        "expanded_candidates.position",
        "expanded_candidates.visit_position",
        "detector_support_class",
        "evidence_score",
        "strict_association_heading_rows",
        "mask_hit_heading_rows",
        "visible_heading_rows",
    }
    return sum(1 for key in consumed if key in FORBIDDEN_ACTION_KEYS or key.startswith("analysis_only_"))


def forbidden_key_count(rows: Sequence[Dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        for key in FORBIDDEN_ACTION_KEYS:
            if key in row:
                count += 1
    return count


def make_plan_row(
    *,
    args: argparse.Namespace,
    request_row: Dict[str, Any],
    candidate_set_row: Dict[str, Any],
    request_index: int,
    target_index: int,
    candidate: Dict[str, Any],
    selected_candidates: Sequence[Dict[str, Any]],
    selected_roles: Dict[str, str],
    detector_rows_by_id: Dict[str, Dict[str, Any]],
    local_distances: Dict[str, Optional[float]],
    viewpoint: Dict[str, Any],
) -> Dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id"))
    selected_ids = [str(item.get("candidate_id")) for item in selected_candidates if item.get("candidate_id") is not None]
    source_top_id = next((candidate_id for candidate_id, role in selected_roles.items() if "source_top" in role), None)
    strong_ids = [
        candidate_id
        for candidate_id, role in selected_roles.items()
        if "detector_strong_candidate" in role or "detector_strong_rival" in role
    ]
    local_ids = [candidate_id for candidate_id, role in selected_roles.items() if "local_context_candidate" in role]
    snapshots = [
        candidate_snapshot(
            item,
            role=selected_roles.get(str(item.get("candidate_id")), "local_context_candidate"),
            detector_row=detector_rows_by_id.get(str(item.get("candidate_id"))),
            local_context_distance_m=local_distances.get(str(item.get("candidate_id"))),
        )
        for item in selected_candidates
    ]
    target_position = candidate_target_position(candidate)
    position = [float(item) for item in viewpoint["position"]]
    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "contract_name": "expanded_retrieval_local_context_disambiguation_v1",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": PLANNER_NAME,
        "request_index": request_index,
        "target_index": target_index,
        "episode_key": request_row.get("episode_key"),
        "scene_id": candidate_set_row.get("scene_id"),
        "scene_key": request_row.get("scene_key") or candidate_set_row.get("scene_key"),
        "query": request_row.get("query"),
        "rival_identity_request_id": request_row.get("rival_identity_request_id"),
        "expanded_retrieval_request_id": request_row.get("rival_identity_request_id"),
        "local_context_request_id": f"local_context:{request_row.get('rival_identity_request_id')}",
        "viewpoint_id": f"local_context:{request_row.get('rival_identity_request_id')}:{target_index + 1}",
        "candidate_id": candidate_id,
        "target_candidate_id": candidate_id,
        "candidate_ids": selected_ids,
        "local_context_candidate_ids": selected_ids,
        "source_top_candidate_id": source_top_id,
        "detector_strong_candidate_ids": strong_ids,
        "local_context_added_candidate_ids": local_ids,
        "candidate_role": selected_roles.get(candidate_id),
        "target_semantic_rank": candidate.get("semantic_rank"),
        "target_semantic_score": candidate.get("semantic_score"),
        "target_support_score": candidate.get("support_score"),
        "target_positive_support": candidate.get("positive_support"),
        "target_detector_support_class": None
        if detector_rows_by_id.get(candidate_id) is None
        else detector_rows_by_id[candidate_id].get("detector_support_class"),
        "target_detector_evidence_score": None
        if detector_rows_by_id.get(candidate_id) is None
        else detector_rows_by_id[candidate_id].get("evidence_score"),
        "target_position": target_position,
        "target_visit_position": candidate.get("visit_position"),
        "local_context_candidate_snapshots": snapshots,
        "expanded_retrieval_candidate_set_ids": selected_ids,
        "expanded_retrieval_candidate_snapshots": snapshots,
        "viewpoint_position": position,
        "viewpoint_rotation": [float(item) for item in viewpoint["rotation"]],
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "target_distance_from_viewpoint_m": None if target_position is None else horizontal_distance(position, target_position),
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
        "evidence_topology": request_row.get("evidence_topology"),
        "terminal_objective_risk": request_row.get("terminal_objective_risk"),
        "source_top_associated": request_row.get("source_top_associated"),
        "source_top_strong": request_row.get("source_top_strong"),
        "lower_rank_only_association": request_row.get("lower_rank_only_association"),
        "objective_action": request_row.get("objective_action"),
        "objective_reason": request_row.get("objective_reason"),
        "revision_contract_name": "expanded_retrieval_local_context_disambiguation_v1",
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_uses_gt_for_action": False,
        "terminal_commit_allowed": False,
        "commit_after_local_context": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }
    return row


def plan_request(
    *,
    args: argparse.Namespace,
    request_row: Dict[str, Any],
    candidate_set_row: Dict[str, Any],
    detector_rows_by_id: Dict[str, Dict[str, Any]],
    request_index: int,
    snapper: NavmeshSnapper,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    selected, roles, local_distances = select_local_context_candidates(candidate_set_row, detector_rows_by_id, args)
    selected_ids = [str(candidate.get("candidate_id")) for candidate in selected if candidate.get("candidate_id") is not None]
    candidates_by_id = {str(candidate.get("candidate_id")): candidate for candidate in selected}
    source_row = {"scene_id": candidate_set_row.get("scene_id"), "viewpoint_position": None}
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    if len(selected) < int(args.min_candidate_set_size_per_request):
        skipped.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": request_row.get("episode_key"),
                "scene_id": candidate_set_row.get("scene_id"),
                "scene_key": request_row.get("scene_key") or candidate_set_row.get("scene_key"),
                "query": request_row.get("query"),
                "rival_identity_request_id": request_row.get("rival_identity_request_id"),
                "selected_candidate_ids": selected_ids,
                "skip_reason": "insufficient_local_context_candidate_set",
                "uses_gt_for_action": False,
            }
        )
        return rows, skipped

    for target_index, candidate in enumerate(selected):
        candidate_id = str(candidate.get("candidate_id"))
        alt_id = nearest_alternative_id(candidate_id, candidates_by_id)
        viewpoint = plan_standoff_viewpoint(source_row, candidate, candidates_by_id, alt_id, snapper, args)
        skip_reason: Optional[str] = None
        if viewpoint is None:
            skip_reason = "standoff_unavailable"
        elif "fallback" in str(viewpoint.get("viewpoint_source") or ""):
            skip_reason = "standoff_fallback_forbidden"
        elif bool(args.require_navmesh_standoff) and (
            viewpoint.get("viewpoint_source") != "standoff_navmesh" or viewpoint.get("navmesh_navigable") is not True
        ):
            skip_reason = "standoff_navmesh_required"
        elif viewpoint.get("projection_sane") is not True:
            skip_reason = "standoff_no_valid_yaw"
        else:
            target_distance = safe_float(viewpoint.get("target_horizontal_distance"))
            if target_distance is None:
                skip_reason = "standoff_missing_target_distance"
            elif target_distance < float(args.min_standoff_distance_m):
                skip_reason = "standoff_all_too_close"
            elif target_distance > float(args.max_standoff_distance_m):
                skip_reason = "standoff_all_too_far"

        if skip_reason:
            skipped.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "episode_key": request_row.get("episode_key"),
                    "scene_id": candidate_set_row.get("scene_id"),
                    "scene_key": request_row.get("scene_key") or candidate_set_row.get("scene_key"),
                    "query": request_row.get("query"),
                    "rival_identity_request_id": request_row.get("rival_identity_request_id"),
                    "candidate_id": candidate_id,
                    "candidate_ids": selected_ids,
                    "candidate_role": roles.get(candidate_id),
                    "target_index": target_index,
                    "skip_reason": skip_reason,
                    "uses_gt_for_action": False,
                }
            )
            continue

        rows.append(
            make_plan_row(
                args=args,
                request_row=request_row,
                candidate_set_row=candidate_set_row,
                request_index=request_index,
                target_index=target_index,
                candidate=candidate,
                selected_candidates=selected,
                selected_roles=roles,
                detector_rows_by_id=detector_rows_by_id,
                local_distances=local_distances,
                viewpoint=viewpoint,
            )
        )
    return rows, skipped


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    candidate_rows = load_jsonl(Path(args.candidate_set))
    ambiguity_rows_all = load_jsonl(Path(args.ambiguity_rows))
    detector_candidate_rows = load_jsonl(Path(args.detector_candidate_rows))

    candidate_by_key = candidate_set_index(candidate_rows)
    detector_by_key = detector_candidate_index(detector_candidate_rows)
    request_rows = [
        row
        for row in ambiguity_rows_all
        if str(row.get("objective_action")) == "request_local_context_disambiguation"
    ]
    request_rows.sort(key=lambda row: str(row.get("rival_identity_request_id")))

    out_root = Path(args.out_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    missing_candidate_set_rows: List[Dict[str, Any]] = []
    snapper = NavmeshSnapper(args.data_root)
    try:
        for request_index, request_row in enumerate(request_rows):
            key = row_key(request_row)
            candidate_set_row = candidate_by_key.get(key)
            if candidate_set_row is None:
                missing = {
                    "schema_version": SCHEMA_VERSION,
                    "episode_key": request_row.get("episode_key"),
                    "scene_key": request_row.get("scene_key"),
                    "query": request_row.get("query"),
                    "rival_identity_request_id": request_row.get("rival_identity_request_id"),
                    "skip_reason": "missing_candidate_set_row",
                    "uses_gt_for_action": False,
                }
                missing_candidate_set_rows.append(missing)
                skipped_rows.append(missing)
                continue
            rows, skipped = plan_request(
                args=args,
                request_row=request_row,
                candidate_set_row=candidate_set_row,
                detector_rows_by_id=detector_by_key.get(key, {}),
                request_index=request_index,
                snapper=snapper,
            )
            plan_rows.extend(rows)
            skipped_rows.extend(skipped)
    finally:
        snapper.close()

    artifact_rows = candidate_artifact_rows(plan_rows)
    write_jsonl(out_root / "expanded_retrieval_local_context_plan.jsonl", plan_rows)
    write_jsonl(out_root / "expanded_retrieval_local_context_skipped.jsonl", skipped_rows)
    write_jsonl(out_root / "expanded_retrieval_local_context_candidate_artifact.jsonl", artifact_rows)

    planned_request_keys = {str(row.get("episode_key")) for row in plan_rows}
    target_distances = [
        float(distance)
        for distance in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if distance is not None
    ]
    plan_rows_by_request = Counter(str(row.get("episode_key")) for row in plan_rows)
    viewpoint_sources = Counter(str(row.get("viewpoint_source")) for row in plan_rows)
    role_counts = Counter(str(row.get("candidate_role")) for row in plan_rows)
    skipped_reasons = Counter(str(row.get("skip_reason")) for row in skipped_rows)
    zero_standoff = sum(1 for distance in target_distances if distance < 1e-4)
    near_standoff = sum(1 for distance in target_distances if distance < float(args.min_standoff_distance_m))
    rotation_fallback = sum(1 for row in plan_rows if "rotation_fallback" in str(row.get("viewpoint_source") or ""))
    fallback_rows = sum(1 for row in plan_rows if "fallback" in str(row.get("viewpoint_source") or ""))
    nonfinite_candidate_rows = sum(
        1
        for row in plan_rows
        for candidate in row.get("local_context_candidate_snapshots") or []
        if candidate_target_position(candidate) is None
    )
    consumed_forbidden = count_consumed_forbidden_fields()
    output_forbidden = forbidden_key_count(plan_rows) + forbidden_key_count(skipped_rows)
    planned_coverage = ratio(len(planned_request_keys), len(request_rows)) or 0.0
    minimum_plan_gate = contract.get("minimum_plan_gate", {})
    request_rows_minimum = int(args.min_request_rows or minimum_plan_gate.get("request_rows_minimum", 20))
    planned_request_rows_minimum = int(
        args.min_planned_request_rows or minimum_plan_gate.get("planned_request_rows_minimum", 18)
    )
    planned_coverage_minimum = float(
        args.min_planned_request_coverage or minimum_plan_gate.get("planned_request_coverage_minimum", 0.85)
    )
    plan_rows_per_planned_request_minimum = int(
        args.min_plan_rows_per_request or minimum_plan_gate.get("plan_rows_per_planned_request_minimum", 2)
    )
    gate = {
        "request_rows_minimum_pass": len(request_rows) >= request_rows_minimum,
        "missing_candidate_set_rows_pass": len(missing_candidate_set_rows) == 0,
        "planned_request_rows_minimum_pass": len(planned_request_keys) >= planned_request_rows_minimum,
        "planned_request_coverage_pass": planned_coverage >= planned_coverage_minimum,
        "plan_rows_per_planned_request_minimum_pass": bool(plan_rows_by_request)
        and min(plan_rows_by_request.values()) >= plan_rows_per_planned_request_minimum,
        "zero_standoff_rows_pass": zero_standoff == int(minimum_plan_gate.get("zero_standoff_rows", 0)),
        "near_standoff_rows_pass": near_standoff == int(minimum_plan_gate.get("near_standoff_rows", 0)),
        "rotation_fallback_rows_pass": rotation_fallback == int(minimum_plan_gate.get("rotation_fallback_rows", 0)),
        "fallback_rows_pass": fallback_rows == int(minimum_plan_gate.get("fallback_rows", 0)),
        "nonfinite_candidate_position_rows_pass": nonfinite_candidate_rows
        == int(minimum_plan_gate.get("nonfinite_candidate_position_rows", 0)),
        "consumed_forbidden_action_fields_pass": consumed_forbidden
        == int(minimum_plan_gate.get("consumed_forbidden_action_fields", 0)),
        "output_forbidden_action_fields_pass": output_forbidden == 0,
        "no_terminal_commit_pass": not any(row.get("terminal_commit_allowed") is True for row in plan_rows),
        "no_gt_action_pass": not any(row.get("uses_gt_for_action") is True for row in plan_rows + skipped_rows),
    }
    gate["expanded_retrieval_local_context_plan_gate_passed"] = all(gate.values())
    summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "candidate_set": str(args.candidate_set),
        "ambiguity_rows": str(args.ambiguity_rows),
        "detector_candidate_rows": str(args.detector_candidate_rows),
        "out_root": str(out_root),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_rows": len(request_rows),
        "planned_request_rows": len(planned_request_keys),
        "planned_request_coverage": planned_coverage,
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "missing_candidate_set_rows": len(missing_candidate_set_rows),
        "plan_rows_per_request_min": min(plan_rows_by_request.values()) if plan_rows_by_request else 0,
        "plan_rows_per_request_max": max(plan_rows_by_request.values()) if plan_rows_by_request else 0,
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "zero_standoff_rows": zero_standoff,
        "near_standoff_rows": near_standoff,
        "rotation_fallback_rows": rotation_fallback,
        "fallback_rows": fallback_rows,
        "nonfinite_candidate_position_rows": nonfinite_candidate_rows,
        "viewpoint_source_counts": dict(sorted(viewpoint_sources.items())),
        "candidate_role_counts": dict(sorted(role_counts.items())),
        "skipped_reason_counts": dict(sorted(skipped_reasons.items())),
        "candidate_artifact_rows": len(artifact_rows),
        "consumed_forbidden_action_field_count": consumed_forbidden,
        "output_forbidden_action_field_count": output_forbidden,
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": [
            float(value) for value in args.projection_anchor_height_offsets_m
        ],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "interpretation": {
            "facts": (
                "Planner consumes paper-scale ambiguity-objective rows, expanded candidate geometry, and "
                "detector evidence diagnostics without correctness labels."
            ),
            "inference": (
                "This is a local-context active-observation planner gate, not terminal ObjectNav utility. "
                "It enables frame/projection smoke only after the plan gate passes."
            ),
        },
        "output_files": {
            "plan": "expanded_retrieval_local_context_plan.jsonl",
            "skipped": "expanded_retrieval_local_context_skipped.jsonl",
            "candidate_artifact": "expanded_retrieval_local_context_candidate_artifact.jsonl",
            "summary": "expanded_retrieval_local_context_plan_summary.json",
        },
    }
    write_json(out_root / "expanded_retrieval_local_context_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan local-context active observations for paper-scale expanded-retrieval ambiguity rows."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--ambiguity-rows", required=True)
    parser.add_argument("--candidate-set", required=True)
    parser.add_argument("--detector-candidate-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--run-id", default="h001_expanded_retrieval_local_context_disambiguation_v1")
    parser.add_argument("--max-detector-strong-candidates-per-request", type=int, default=4)
    parser.add_argument("--max-local-context-candidates-per-request", type=int, default=3)
    parser.add_argument("--max-total-candidates-per-request", type=int, default=6)
    parser.add_argument("--min-candidate-set-size-per-request", type=int, default=2)
    parser.add_argument("--max-local-context-distance-m", type=float, default=2.5)
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
    parser.add_argument("--min-request-rows", type=int, default=None)
    parser.add_argument("--min-planned-request-rows", type=int, default=None)
    parser.add_argument("--min-planned-request-coverage", type=float, default=None)
    parser.add_argument("--min-plan-rows-per-request", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["expanded_retrieval_local_context_plan_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
